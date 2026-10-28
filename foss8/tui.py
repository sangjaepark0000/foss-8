"""Keyboard-first terminal prototype: automatic task preview and editable team settings."""
import copy
import curses
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import queue
import threading

from . import assessments, discovery, github_activity, minutes, progress, team, weeks


TABS = ("할 일", "평가", "팀 설정")
FOCUSES = ("period", "tabs", "list", "detail")
EMPTY = {"schema_version": 1, "name": "", "repository": "", "members": [],
         "me": None, "task_owners": {}, "agreements": {}, "approved_changes": []}


def clip(value, width):
    result = ""
    for char in str(value):
        if weeks._width(result + char) > max(0, width):
            break
        result += char
    return result


def put(screen, y, x, value, attr=0, width=None):
    height, columns = screen.getmaxyx()
    if y < 0 or y >= height or x < 0 or x >= columns - 1:
        return
    try:
        screen.addstr(y, x, clip(value, min(columns - x - 1, width or columns)), attr)
    except curses.error:
        pass  # A resize can occur between measuring and drawing.


def evaluation_groups(node):
    result = []
    if node.get("evaluation"):
        result.append((node["title"], node["evaluation"]))
    for child in node.get("children", []):
        result.extend(evaluation_groups(child))
    return result


def task_detail(node, width, evaluation=False, methods=False):
    lines = []

    def add(value, prefix=""):
        lines.extend(weeks.wrapped(value, prefix=prefix, width=width))

    if evaluation:
        seen = set()
        for title, rules in evaluation_groups(node):
            key = tuple(rules)
            if key in seen:
                continue
            seen.add(key)
            add(title)
            for rule in rules:
                add(rule, "  • ")
            lines.append("")
        return lines or ["별도 평가기준 없음"]

    def walk(children, depth=0):
        for child in children:
            if child.get("kind") == "code":
                if methods:
                    lines.extend(child["title"].splitlines())
                continue
            nested = child.get("children", [])
            if nested:
                if lines and depth == 0:
                    lines.append("")
                add(child["title"], "  " * depth)
                walk(nested, depth + 1)
            else:
                add(child["title"], "  " * depth + "• ")
            if methods and child.get("details"):
                walk(child["details"], depth + 1)
    walk(node.get("children", []))
    if methods and node.get("details"):
        lines.extend(["", "방법"])
        walk(node["details"])
    return lines or [weeks.plain(node["title"])]


@dataclass
class Setting:
    label: str
    value: object
    key: str
    kind: str = "text"
    index: int = -1


class App:
    def __init__(self, periods, period, start_tab=0, config_path=None):
        self.path = Path(config_path or team.config_path())
        self.config = team.load(self.path)
        self.progress = progress.Progress(self.path.with_name("progress.json"))
        self.assessments = assessments.Store(self.path.with_name("assessments.json"))
        self.periods = periods
        self.period_index = next(i for i, p in enumerate(periods) if p["id"] == period["id"])
        self.tab = start_tab
        self.focus = "list"
        self.selected = {}
        self.scroll = 0
        self.methods = False
        self.message = ("완료 기록을 읽지 못했습니다." if self.progress.error else
                        "평가 집계 기록을 읽지 못했습니다." if self.assessments.error else "")
        self.list_rows = {}
        self.tab_regions = []
        self.discovery_queue = queue.Queue()
        self.discovery_running = False
        self.pending_discovery = None
        self.detected_draft = False
        self.config_revision = 0
        self.activity_queue = queue.Queue()
        self.activity_running = False
        self.activity_attempted = set()
        self.activity_errors = {}
        self.minutes_files = {}

    @property
    def period(self):
        return self.periods[self.period_index]

    @property
    def selection_key(self):
        return (self.tab, self.period["id"] if self.tab != 2 else "team")

    def settings(self):
        c = self.config or EMPTY
        result = [Setting("팀 이름", c["name"], "name"),
                  Setting("저장소", c["repository"], "repository"),
                  Setting("내 계정", c["me"] or "미정", "me", "person"),
                  Setting("정기회의", c["agreements"].get("meeting", ""), "meeting"),
                  Setting("채팅 응답 시간", c["agreements"].get("chat_hours", 24), "chat_hours", "number"),
                  Setting("리뷰 응답 시간", c["agreements"].get("review_hours", 48), "review_hours", "number")]
        for i, person in enumerate(c["members"]):
            result.append(Setting(person["name"], "@" + person["github"], "member", "member", i))
        result.append(Setting("+ 팀원 추가", "", "add_member", "member"))
        values = team.bindings(self.config)
        for key, (_, label) in team.OWNERS.items():
            result.append(Setting(label, values["task." + key], key, "owner"))
        for i, change in enumerate(c["approved_changes"]):
            result.append(Setting("승인 기록", change["description"], "change", "change", i))
        result.append(Setting("+ 승인 기록 추가", "", "add_change", "change"))
        changes = discovery.differences(self.config, self.pending_discovery.config) if self.pending_discovery else []
        read = Setting(f"설정 변경 {len(changes)}건 · 검토·적용" if changes else "폴더·GitHub에서 읽기",
                       "읽는 중" if self.discovery_running else "", "discover", "discover")
        if changes:
            result.insert(0, read)
        else:
            result.append(read)
        if self.detected_draft:
            result.append(Setting("자동으로 읽은 설정 저장", "", "save_detected", "save_detected"))
        return result

    def items(self):
        if self.tab == 2:
            return self.settings()
        tasks = self.period["tasks"]
        bundles = self.assessments.for_period(progress.context(self.config), self.period)
        rows = []
        for bundle in bundles:
            if bundle.end < weeks.today():
                continue
            for criterion in bundle.scheduled_criteria:
                if criterion.starts.isoformat() >= self.period["end"]:
                    continue
                status = "주간 최소 횟수 면제" if bundle.exempt else bundle.line(criterion).split("  ", 1)[1]
                rows.append({"kind": "assessment_criterion", "bundle": bundle,
                             "criterion": criterion, "title": criterion.title,
                             "subtitle": f'{bundle.start.month}/{bundle.start.day} ~ {bundle.end.month}/{bundle.end.day}',
                             "status": status})
        shown = [t for t in tasks if evaluation_groups(t)] if self.tab == 1 else tasks
        return rows + shown + self.period.get("references", [])

    def index(self):
        items = self.items()
        default = 0
        return min(self.selected.get(self.selection_key, default), max(0, len(items) - 1))

    def move(self, delta):
        self.selected[self.selection_key] = max(0, min(len(self.items()) - 1, self.index() + delta))
        self.scroll = 0

    def done(self, item):
        if item.get("kind") in ("reference", "assessment_criterion"):
            return False
        return self.progress.done(progress.context(self.config), item.get("progress_period", self.period["id"]) + "/" + item["id"])

    def toggle_completion(self):
        if self.tab != 0 or not self.items():
            return
        item = self.items()[self.index()]
        if item.get("kind") in ("reference", "assessment_criterion"):
            self.message = "이 항목은 완료 체크 대신 집계·기준으로 확인합니다."
            return
        completed = self.progress.toggle(progress.context(self.config), item.get("progress_period", self.period["id"]) + "/" + item["id"])
        self.config_revision += 1
        self.message = "완료 표시 저장됨" if completed else "완료 표시 해제됨"

    def assessment_detail(self, item, width):
        bundle = item["bundle"]
        criterion = item["criterion"]
        lines = weeks.wrapped(bundle.line(criterion), width=width)
        lines += ["", criterion.action, "", f'반복 기준  매주 {criterion.target}회 이상 · 개인별',
                  f'집계 기준  {self.period["label"]}', f'기간 상태  {bundle.lifecycle(weeks.today())}']
        if bundle.exempt:
            return lines + ["중간고사 주간: 주간 최소 횟수 면제", "다른 평가항목 전체가 면제되는 것은 아닙니다."]
        if bundle.exam_overlap:
            lines += ["시험 면제: 10/19~10/25만 제외", "시험 이후 활동·회의록 제출은 면제되지 않습니다."]
        lines += [f'집계 대상  {a.month}/{a.day} ~ {(b - timedelta(days=1)).month}/{(b - timedelta(days=1)).day}'
                  for a, b in bundle.active_ranges(criterion)]
        lines += [f'적용 기간  {criterion.starts.month}/{criterion.starts.day} ~ 12/13']
        record = self.assessments.record(progress.context(self.config), bundle.start)
        source = record.get("sources", {}).get(criterion.id, record.get("source", "미집계"))
        lines += ["", "Space: +1회 · Backspace: -1회", "Enter: 이 항목의 횟수 입력·수정",
                  "빈 값은 미집계, 0은 확인된 0회", "출처: " + {"github": "GitHub", "manual": "수동 입력"}.get(source, source)]
        if record.get("synced_at"):
            lines.append("GitHub 집계: " + record["synced_at"])
        lines += ["r: GitHub에서 다시 집계 (수동 수정값도 갱신)"]
        lines += self.activity_errors.get(self.activity_key(), [])
        lines += record.get("evidence", {}).get(criterion.id, [])
        return lines

    def edit_assessment(self, screen):
        item = self.items()[self.index()]
        if item.get("kind") != "assessment_criterion":
            return
        bundle = item["bundle"]
        if not bundle.criteria:
            self.message = "이 기간은 활동 집계 대상이 아닙니다."
            return
        if assessments.EXAM_START <= weeks.today() <= assessments.EXAM_END:
            self.message = "10/19~10/25 최소 횟수 면제 · 10/26부터 집계 재개"
            return
        if bundle.start > weeks.today():
            self.message = "아직 시작하지 않은 집계 기간입니다."
            return
        if item["criterion"].starts > weeks.today():
            self.message = "아직 적용이 시작되지 않은 평가항목입니다."
            return
        fields = [Setting(f'{c.title} (목표 {c.target}회)',
                          "" if bundle.counts.get(c.id) is None else str(bundle.counts[c.id]), c.id, "number")
                  for c in (item["criterion"],)]
        def submit(values):
            try:
                counts = {key: int(value.strip()) if value.strip() else None for key, value in values.items()}
            except (ValueError, AttributeError) as error:
                raise ValueError("횟수는 0 이상의 정수로 입력하세요. 미집계는 비워두세요.") from error
            self.assessments.save(progress.context(self.config), bundle.start, counts)
            self.config_revision += 1
            self.message = "주간 집계 저장됨"
        edit_form(screen, f'{item["criterion"].title} · {self.period["label"]}', fields, submit)

    def adjust_assessment(self, delta):
        item = self.items()[self.index()]
        bundle, criterion = item["bundle"], item["criterion"]
        if bundle.exempt:
            self.message = "이 주는 주간 최소 횟수 면제입니다."
            return
        if assessments.EXAM_START <= weeks.today() <= assessments.EXAM_END:
            self.message = "10/19~10/25 최소 횟수 면제 · 10/26부터 집계 재개"
            return
        if bundle.start > weeks.today():
            self.message = "아직 시작하지 않은 집계 기간입니다."
            return
        if criterion.starts > weeks.today():
            self.message = "아직 적용이 시작되지 않은 평가항목입니다."
            return
        value = bundle.counts.get(criterion.id)
        if delta < 0 and (value is None or value == 0):
            return
        value = (value or 0) + delta
        self.assessments.save(progress.context(self.config), bundle.start, {criterion.id: value})
        self.config_revision += 1
        self.message = f'{criterion.title} {value}/{criterion.target}회 저장됨'

    def change_period(self, delta):
        self.period_index = max(0, min(len(self.periods) - 1, self.period_index + delta))
        self.scroll = 0

    def activity_key(self):
        return (progress.context(self.config), self.period["id"])

    def start_activity(self, force=False):
        if self.activity_running or github_activity.requirements(self.config):
            return
        key = self.activity_key()
        if not force and key in self.activity_attempted:
            return
        bundles = self.assessments.for_period(progress.context(self.config), self.period)
        if not bundles or bundles[0].exempt or not bundles[0].start <= weeks.today() <= bundles[0].end:
            return
        if not any(a <= weeks.today() for c in bundles[0].criteria for a, _ in bundles[0].active_ranges(c)):
            return
        self.activity_attempted.add(key)
        self.activity_running = True
        revision, config, period = self.config_revision, copy.deepcopy(self.config), copy.deepcopy(self.period)
        def work():
            try:
                result = github_activity.collect(config, period, on=weeks.today())
            except Exception as error:
                result = github_activity.Result(errors=[str(error)])
            self.activity_queue.put((key, revision, period, result))
        threading.Thread(target=work, daemon=True).start()

    def poll_activity(self):
        try:
            key, revision, period, result = self.activity_queue.get_nowait()
        except queue.Empty:
            return
        self.activity_running = False
        if revision != self.config_revision:
            self.message = "집계 중 설정·횟수가 변경됨 · r로 다시 집계"
            return
        self.activity_errors[key] = result.errors
        start = date.fromisoformat(period["start"])
        applicable = {c.id for b in self.assessments.for_period(key[0], period) for c in b.criteria}
        counts = {k: v for k, v in result.counts.items() if k in applicable}
        if counts:
            try:
                self.assessments.save(key[0], start, counts, source="github", evidence=result.evidence)
            except (ValueError, OSError) as error:
                self.activity_errors[key] = result.errors + [str(error)]
        self.message = "GitHub 집계 완료" if not self.activity_errors[key] else "GitHub 일부 집계 실패 · 상세 확인 / r 재시도"

    def open_required_setting(self):
        missing = github_activity.requirements(self.config)
        changes = self.pending_discovery and discovery.differences(self.config, self.pending_discovery.config)
        key = "discover" if changes or not self.config else missing[0][0] if missing else "discover"
        if key == "me" and not self.config.get("members"):
            key = "add_member"
        self.tab, self.focus, self.scroll = 2, "list", 0
        self.selected[self.selection_key] = next((i for i, row in enumerate(self.settings()) if row.key == key), 0)

    def choose_period(self, screen):
        options = [(i, f'{p["label"]} · {p["title"]}  ({weeks.heading(p)[1].strip()})')
                   for i, p in enumerate(self.periods)]
        chosen = choose(screen, "주차 선택", options, self.period_index)
        if chosen is not CANCEL:
            self.period_index, self.scroll, self.focus = chosen, 0, "list"

    def create_minutes(self, screen):
        def submit(values):
            on = date.fromisoformat(values["date"])
            output = self.path.parent.parent / "docs/meetings" / (on.isoformat() + ".md")
            path = minutes.create(on, self.period["id"], self.config, output=output)
            self.minutes_files[self.period["id"]] = path
            self.message = "초안 저장: " + str(path)
        edit_form(screen, "회의록 초안 만들기 · 기존 파일은 보호", [Setting("회의 날짜", weeks.today().isoformat(), "date")], submit)

    def minutes_action(self, screen):
        action = choose(screen, "회의록 작성·제출 준비", [("draft", "작성할 초안 만들기"), ("pdf", "완성한 회의록을 제출용 PDF로 저장")], "draft")
        if action == "draft":
            self.create_minutes(screen)
        elif action == "pdf":
            from . import minutes_pdf
            folder = self.path.parent.parent / "docs/meetings"
            default = self.minutes_files.get(self.period["id"])
            if default is None and folder.is_dir():
                for path in sorted(folder.glob("*.md"), reverse=True):
                    try:
                        cycle, _ = minutes_pdf.submission_info(path.read_text(encoding="utf-8"))
                    except (ValueError, OSError):
                        continue
                    if cycle.period_id == self.period["id"]:
                        default = path
                        break
            value = edit_text(screen, "완성한 회의록 Markdown 경로", str(default or folder / (weeks.today().isoformat() + ".md")))
            if value is not None:
                try:
                    self.message = "제출용 PDF 만드는 중…"
                    self.draw(screen)
                    path = minutes_pdf.export(value, week=self.period["id"])
                    self.message = "제출용 PDF 저장: " + str(path)
                except (ValueError, OSError) as error:
                    self.message = str(error)

    def save(self, raw):
        self.config = team.save(raw, self.path)
        self.config_revision += 1
        self.detected_draft = False
        self.periods = weeks.load(self.config)
        self.message = "저장됨"

    def start_discovery(self, automatic=False):
        if self.discovery_running:
            return
        self.discovery_running = True
        revision = self.config_revision
        root = self.path.parent.parent
        self.message = "현재 폴더·GitHub에서 설정 읽는 중…"
        def work():
            try:
                self.discovery_queue.put((revision, automatic, discovery.detect(root), None))
            except Exception as error:
                self.discovery_queue.put((revision, automatic, None, str(error)))
        threading.Thread(target=work, daemon=True).start()

    def poll_discovery(self):
        try:
            revision, automatic, result, error = self.discovery_queue.get_nowait()
        except queue.Empty:
            return
        self.discovery_running = False
        if error:
            self.message = "설정 자동 읽기 실패. 팀 설정에서 직접 수정할 수 있습니다."
            return
        self.pending_discovery = result
        local_scope = progress.context(None)
        unassigned_records = bool(self.progress.data["contexts"].get(local_scope) or self.assessments.data["contexts"].get(local_scope))
        if automatic and self.config is None and revision == self.config_revision and not unassigned_records:
            self.config = result.config
            self.detected_draft = True
            self.periods = weeks.load(self.config)
            self.message = "폴더·GitHub에서 팀 정보 읽음 · 팀 설정에서 확인·저장"
        else:
            self.message = "설정 읽기 완료 · 팀 설정에서 검토·적용"

    def setting_detail(self, row, width):
        values = row.value
        if row.kind == "discover":
            if self.pending_discovery:
                r = self.pending_discovery
                changes = discovery.differences(self.config, r.config)
                values = [line for _, label, before, after in changes for line in (
                    label, "현재: " + discovery.describe(before), "변경: " + discovery.describe(after), "")] or ["현재 설정과 차이 없음"]
                values += ["", "출처: " + ", ".join(r.sources)] + r.warnings + ["Enter: 변경 적용 여부 선택"]
            else:
                values = ["Git 원격 저장소·gh 로그인·협력자 읽기", "README·팀 약속·팀원 소개에서 역할·기능 읽기", "기존 설정은 자동으로 덮어쓰지 않습니다.", "Enter: 읽기 시작"]
        elif row.kind == "save_detected":
            values = ["자동으로 읽은 정보는 아직 파일에 저장하지 않았습니다.", "Enter: 현재 설정 저장"]
        elif row.kind == "member" and row.index >= 0:
            p = self.config["members"][row.index]
            values = [p["name"], "@" + p["github"],
                      "역할: " + (", ".join(team.ROLES.get(r, r) for r in p["roles"]) or "미정"),
                      "담당 기능: " + (", ".join(p["features"]) or "미정")]
        elif row.kind == "change" and row.index >= 0:
            c = self.config["approved_changes"][row.index]
            values = [c["description"], "근거: " + c["source"], c["date"], "강의 배점은 자동 변경하지 않습니다."]
        else:
            notes = {"name": "제출 파일명과 서식에 사용합니다.",
                     "repository": "HTTPS 주소 또는 GitHub 소유자/저장소",
                     "me": "팀원 목록에서 내 계정을 선택합니다.",
                     "review_hours": "팀의 응답 약속입니다. 강의 평가 규칙은 별도로 유지합니다.",
                     "add_member": "이름·GitHub ID·역할·담당 기능을 입력합니다.",
                     "add_change": "조정 내용·승인 근거·날짜를 기록합니다."}
            values = [str(values or "미설정"), notes.get(row.key, "Enter로 수정합니다.")]
            if row.key == "repository":
                values.append("활동 집계에 필요합니다. 예: 소유자/저장소")
            elif row.key == "me":
                values.append("내 활동을 집계할 GitHub 계정입니다. 명단에 없으면 먼저 팀원을 추가하세요.")
            if row.kind == "owner":
                values.append("역할 기준 또는 특정 팀원을 선택할 수 있습니다.")
        return [line for value in values for line in weeks.wrapped(value, width=width)]

    def draw(self, screen):
        screen.erase()
        h, w = screen.getmaxyx()
        if w < 32 or h < 16:
            put(screen, 0, 0, "터미널을 조금 넓혀주세요. q: 종료")
            screen.refresh()
            return
        put(screen, 0, 2, f'{self.period["label"]} · {self.period["title"]} ▾',
            curses.A_REVERSE if self.focus == "period" else curses.A_BOLD)
        put(screen, 1, 2, weeks.heading(self.period)[1].strip(), curses.A_DIM)
        missing = github_activity.requirements(self.config)
        notice = ("집계 설정 필요: " + " · ".join(label for _, label in missing) + " · s 설정") if missing else (
            "GitHub 집계 중…" if self.activity_running else "GitHub 집계 실패 · r 재시도 / 상세 확인" if self.activity_errors.get(self.activity_key()) else "")
        if self.pending_discovery and discovery.differences(self.config, self.pending_discovery.config):
            notice = (notice + " / " if notice else "") + "설정 변경 발견 · s 검토"
        put(screen, 2, 2, notice, curses.A_BOLD)
        self.tab_regions = []
        x = 2
        for i, label in enumerate(TABS):
            caption = " " + label + " "
            active = curses.A_REVERSE if self.focus == "tabs" else curses.A_BOLD | curses.A_UNDERLINE
            put(screen, 3, x, caption, active if i == self.tab else curses.A_NORMAL)
            self.tab_regions.append((x, x + weeks._width(caption), i))
            x += weeks._width(caption) + 2
        put(screen, 4, 1, "─" * (w - 3), curses.A_DIM)
        items, selected = self.items(), self.index()
        if w >= 90:
            lw = min(43, w // 3)
            ly, lh = 6, h - 9
            dx, dy, dw, dh = lw + 3, 5, w - lw - 5, h - 8
            for y in range(5, h - 3):
                put(screen, y, lw + 1, "│", curses.A_DIM)
        else:
            lw = w - 4
            ly, lh = 6, min(max(3, (h - 12) // 3), max(1, len(items)))
            dx, dy, dw = 2, ly + lh + 1, w - 4
            dh = max(1, h - dy - 3)
            put(screen, dy - 1, 1, "─" * (w - 3), curses.A_DIM)
        heights = [1 for item in items]
        start = selected
        used = heights[selected] if heights else 0
        while start > 0 and used + heights[start - 1] <= lh:
            start -= 1
            used += heights[start]
        self.list_right = lw + 1
        self.detail_rect = (dx, dy, dw, dh)
        put(screen, 5, 2, ("▶ " if self.focus == "list" else "  ") + TABS[self.tab],
            curses.A_REVERSE if self.focus == "list" else curses.A_DIM, width=lw - 1)
        put(screen, dy, dx, ("▶ " if self.focus == "detail" else "  ") + "상세",
            curses.A_REVERSE if self.focus == "detail" else curses.A_DIM, width=dw)
        self.list_rows = {}
        y = ly
        for i in range(start, len(items)):
            if y + heights[i] > ly + lh:
                break
            item = items[i]
            title = item.label if self.tab == 2 else weeks.plain(item["title"])
            if self.tab == 0:
                if item.get("kind") not in ("reference", "assessment_criterion"):
                    title = ("[x] " if self.done(item) else "[ ] ") + title
                if evaluation_groups(item) or item.get("kind") == "assessment_criterion":
                    title += " [평가]"
            if self.tab != 2 and item.get("kind") == "assessment_criterion":
                c, b = item["criterion"], item["bundle"]
                value = b.counts.get(c.id)
                title += "  면제" if b.exempt else f"  {value if value is not None else '?'}/{c.target}회"
            base_attr = curses.A_BOLD if self.tab != 2 and evaluation_groups(item) else curses.A_NORMAL
            put(screen, y, 2, ("› " if i == selected else "  ") + title,
                (curses.A_REVERSE if self.focus == "list" else curses.A_BOLD) if i == selected else base_attr, width=lw - 1)
            self.list_rows[y] = i
            y += heights[i]
        if items:
            item = items[selected]
            title = item.label if self.tab == 2 else weeks.plain(item["title"])
            title_lines = weeks.wrapped(title, width=dw)[:2]
            for offset, line in enumerate(title_lines):
                put(screen, dy + 1 + offset, dx, line, curses.A_BOLD, width=dw)
            if self.tab == 2:
                lines = self.setting_detail(item, dw)
            elif item.get("kind") == "assessment_criterion":
                lines = self.assessment_detail(item, dw)
            else:
                lines = task_detail(item, dw, self.tab == 1 and item.get("kind") != "reference", self.methods)
                if item.get("recording_start"):
                    lines = ["Enter: 초안 만들기 / 제출용 PDF 저장", ""] + lines
                    if self.period["id"] in self.minutes_files:
                        lines += ["", "초안: " + str(self.minutes_files[self.period["id"]])]
            available = max(0, dh - len(title_lines) - 2)
            self.scroll = min(self.scroll, max(0, len(lines) - available))
            for i, line in enumerate(lines[self.scroll:self.scroll + available]):
                put(screen, dy + len(title_lines) + 2 + i, dx, line, width=dw)
        else:
            put(screen, dy + 1, dx, "이 기간에 표시할 항목 없음")
        help_text = {"list": "↑↓ 선택  → 상세  Space 완료 표시", "detail": "↑↓ 스크롤  ← 목록  Space 완료 표시",
                     "period": "←→ 기간  Enter 선택  ↓ 화면 선택", "tabs": "↑ 기간  ↓ 목록  ←→ 화면 선택"}[self.focus]
        extra_help = "q 종료  Tab 포커스  w 기간 선택  PgUp/PgDn 스크롤  m 방법"
        if self.tab == 2:
            if self.focus == "list":
                help_text = "↑↓ 선택  → 상세  Enter 수정"
            elif self.focus == "detail":
                help_text = "↑↓ 스크롤  ← 목록  Enter 수정"
            extra_help = "q 종료  Tab 포커스  Enter 수정  Del 삭제"
        if self.focus == "list" and selected == 0:
            help_text = "↑ 화면 선택  ↓ 항목  " + ("Enter 수정" if self.tab == 2 else "Space 완료 표시")
        if self.tab == 1 and self.focus in ("list", "detail"):
            help_text = "↑↓ 선택/스크롤  Enter 주간 집계 입력"
        if self.tab == 0 and items and self.focus in ("list", "detail"):
            if items[selected].get("kind") == "assessment_criterion":
                help_text = "↑↓ 선택/스크롤  Enter 주간 집계 입력"
            elif items[selected].get("kind") == "reference":
                help_text = "↑↓ 선택/스크롤  평가 기준 확인"
            elif items[selected].get("recording_start"):
                help_text = "Enter 초안/PDF 만들기  Space 완료 표시"
        if self.tab == 2 and items and items[selected].kind == "discover":
            extra_help = "Enter 읽기/검토·적용  r 다시 읽기  q 종료"
        if self.tab in (0, 1) and items and items[selected].get("kind") == "assessment_criterion" and self.focus in ("list", "detail"):
            help_text = "Space +1회  Backspace -1회  Enter 횟수 입력"
        put(screen, h - 2, 1, help_text, curses.A_DIM)
        put(screen, h - 1, 1, self.message or extra_help, curses.A_BOLD if self.message else curses.A_DIM)
        screen.refresh()

    def handle(self, key, screen=None):
        self.message = ""
        if key in ("q", "Q", "\x03"):
            return False
        if key in (curses.KEY_DOWN, "j", curses.KEY_UP, "k"):
            delta = 1 if key in (curses.KEY_DOWN, "j") else -1
            if self.focus == "detail":
                self.scroll = max(0, self.scroll + delta)
            elif self.focus == "tabs":
                self.focus = "list" if delta == 1 else "period"
            elif self.focus == "period" and delta == 1:
                self.focus = "tabs"
            elif self.focus == "list":
                if delta == -1 and self.index() == 0:
                    self.focus = "tabs"
                else:
                    self.move(delta)
        elif key in ("\t", curses.KEY_BTAB):
            self.focus = FOCUSES[(FOCUSES.index(self.focus) + (-1 if key == curses.KEY_BTAB else 1)) % len(FOCUSES)]
        elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
            delta = 1 if key == curses.KEY_RIGHT else -1
            if self.focus == "period":
                self.change_period(delta)
            elif self.focus == "tabs":
                self.tab = (self.tab + delta) % len(TABS)
                self.scroll = 0
            elif self.focus == "list" and delta == 1:
                self.focus = "detail"
            elif self.focus == "detail" and delta == -1:
                self.focus = "list"
        elif key in (curses.KEY_NPAGE, curses.KEY_PPAGE):
            self.scroll = max(0, self.scroll + (6 if key == curses.KEY_NPAGE else -6))
        elif key == "m" and self.tab != 2:
            self.methods = not self.methods
            self.scroll = 0
        elif key == "r" and self.tab == 2:
            self.pending_discovery = None
            self.start_discovery()
        elif key == "r" and self.tab in (0, 1):
            self.start_activity(force=True)
        elif key == "s":
            self.open_required_setting()
        elif key in ("\n", "\r", curses.KEY_ENTER, " ") and self.focus == "period" and screen is not None:
            self.choose_period(screen)
        elif key == "w" and screen is not None:
            self.choose_period(screen)
        elif key in (" ", "\x7f", "\b", curses.KEY_BACKSPACE) and self.focus in ("list", "detail") and self.tab in (0, 1) and self.items() and self.items()[self.index()].get("kind") == "assessment_criterion":
            try:
                self.adjust_assessment(1 if key == " " else -1)
            except (ValueError, OSError) as error:
                self.message = str(error)
        elif key == " " and self.focus in ("list", "detail") and self.tab == 0:
            try:
                self.toggle_completion()
            except (ValueError, OSError) as error:
                self.message = str(error)
        elif key in ("\n", "\r", curses.KEY_ENTER) and self.tab in (0, 1) and self.focus in ("list", "detail") and screen is not None:
            if self.items() and self.items()[self.index()].get("recording_start"):
                self.minutes_action(screen)
            else:
                self.edit_assessment(screen)
        elif key in ("\n", "\r", curses.KEY_ENTER) and self.tab == 2 and self.focus in ("list", "detail") and screen is not None:
            self.edit_setting(screen)
        elif key == curses.KEY_DC and self.tab == 2 and self.focus == "list" and screen is not None:
            self.delete_setting(screen)
        elif key == curses.KEY_MOUSE and screen is not None:
            self.mouse(screen)
        return True

    def mouse(self, screen):
        try:
            _, x, y, _, button = curses.getmouse()
        except curses.error:
            return
        if button & getattr(curses, "BUTTON4_PRESSED", 0):
            self.scroll = max(0, self.scroll - 3)
        elif button & getattr(curses, "BUTTON5_PRESSED", 0):
            self.scroll += 3
        elif button & (curses.BUTTON1_CLICKED | curses.BUTTON1_PRESSED | curses.BUTTON1_DOUBLE_CLICKED):
            if y == 0:
                self.focus = "period"
                self.choose_period(screen)
            elif y == 3:
                for left, right, tab in self.tab_regions:
                    if left <= x < right:
                        self.tab, self.scroll, self.focus = tab, 0, "list"
            elif y in self.list_rows and x <= self.list_right:
                self.selected[self.selection_key] = self.list_rows[y]
                self.scroll, self.focus = 0, "list"
            elif hasattr(self, "detail_rect"):
                dx, dy, dw, dh = self.detail_rect
                if dx <= x < dx + dw and dy <= y < dy + dh:
                    self.focus = "detail"

    def edit_setting(self, screen):
        row = self.settings()[self.index()]
        raw = copy.deepcopy(self.config or EMPTY)
        if row.kind == "discover":
            if self.pending_discovery:
                chosen = choose(screen, "읽어온 설정 적용", [("changes", "표시된 변경 적용"), (True, "빠진 정보만 채우기"), (False, "취소")], False)
                if chosen == "changes":
                    try:
                        self.save(discovery.apply_changes(self.config, self.pending_discovery.config))
                        self.pending_discovery = None
                    except (ValueError, OSError) as error:
                        self.message = str(error)
                if chosen is True:
                    try:
                        self.save(discovery.merge(self.config, self.pending_discovery.config))
                        self.pending_discovery = None
                    except (ValueError, OSError) as error:
                        self.message = str(error)
            else:
                self.start_discovery()
            return
        if row.kind == "save_detected":
            try:
                self.save(raw)
            except (ValueError, OSError) as error:
                self.message = str(error)
            return
        if row.key != "name" and not raw["name"]:
            self.selected[self.selection_key] = 0
            self.message = "팀 이름을 먼저 입력해주세요."
            return
        try:
            if row.kind == "member":
                old = raw["members"][row.index] if row.index >= 0 else {"name": "", "github": "", "roles": [], "features": []}
                fields = [Setting("이름", old["name"], "name"), Setting("GitHub ID", old["github"], "github"),
                          Setting("역할", old["roles"], "roles", "roles"), Setting("담당 기능", ", ".join(old["features"]), "features")]
                def submit(values):
                    candidate = copy.deepcopy(raw)
                    person = {**values, "features": [x.strip() for x in values["features"].split(",") if x.strip()]}
                    person["github"] = person["github"].lstrip("@").lower()
                    if row.index >= 0:
                        candidate["members"][row.index] = person
                        if candidate["me"] == old["github"]:
                            candidate["me"] = person["github"]
                        candidate["task_owners"] = {k: person["github"] if v == old["github"] else v for k, v in candidate["task_owners"].items()}
                    else:
                        candidate["members"].append(person)
                    self.save(candidate)
                edit_form(screen, "팀원 수정" if row.index >= 0 else "팀원 추가", fields, submit)
            elif row.kind == "change":
                old = raw["approved_changes"][row.index] if row.index >= 0 else {"description": "", "source": "", "date": ""}
                fields = [Setting("조정 내용", old["description"], "description"), Setting("승인 근거", old["source"], "source"), Setting("날짜", old["date"], "date")]
                def submit(values):
                    candidate = copy.deepcopy(raw)
                    if row.index >= 0:
                        candidate["approved_changes"][row.index] = values
                    else:
                        candidate["approved_changes"].append(values)
                    self.save(candidate)
                edit_form(screen, "승인 기록", fields, submit)
            elif row.kind in ("person", "owner"):
                options = [(None, "미정")] + [(p["github"], p["name"] + " (@" + p["github"] + ")") for p in raw["members"]]
                current = raw["me"] if row.kind == "person" else raw["task_owners"].get(row.key, "role")
                if row.kind == "owner":
                    options.insert(0, ("role", "역할에 따라 지정"))
                chosen = choose(screen, row.label, options, current)
                if chosen is not CANCEL:
                    if row.kind == "person":
                        raw["me"] = chosen
                    elif chosen == "role":
                        raw["task_owners"].pop(row.key, None)
                    else:
                        raw["task_owners"][row.key] = chosen
                    self.save(raw)
            else:
                value = edit_text(screen, row.label, str(row.value))
                if value is not None:
                    if row.key in ("name", "repository"):
                        raw[row.key] = value
                    else:
                        raw["agreements"][row.key] = int(value) if row.kind == "number" else value
                    self.save(raw)
        except (ValueError, OSError) as error:
            self.message = str(error)

    def delete_setting(self, screen):
        row = self.settings()[self.index()]
        if row.kind not in ("member", "change") or row.index < 0:
            return
        if choose(screen, row.label + " 삭제", [(False, "취소"), (True, "삭제")], False) is not True:
            return
        raw = copy.deepcopy(self.config)
        if row.kind == "member":
            removed = raw["members"].pop(row.index)["github"]
            if raw["me"] == removed:
                raw["me"] = None
            raw["task_owners"] = {k: None if v == removed else v for k, v in raw["task_owners"].items()}
        else:
            raw["approved_changes"].pop(row.index)
        try:
            self.save(raw)
        except (ValueError, OSError) as error:
            self.message = str(error)


CANCEL = object()


def choose(screen, title, options, current=None, multi=False):
    selected = set(current or []) if multi else set()
    index = next((i for i, (value, _) in enumerate(options) if value == current), 0)
    while True:
        screen.erase()
        h, w = screen.getmaxyx()
        put(screen, 1, 2, title, curses.A_BOLD)
        start = max(0, index - max(1, h - 6) + 1)
        for y, i in enumerate(range(start, min(len(options), start + max(1, h - 6))), 3):
            value, label = options[i]
            marker = ("[x] " if value in selected else "[ ] ") if multi else ""
            put(screen, y, 2, marker + label, curses.A_REVERSE if i == index else 0)
        put(screen, h - 2, 1, "↑↓ 이동  " + ("Space 선택  " if multi else "") + "Enter 적용  Esc 취소", curses.A_DIM)
        screen.refresh()
        key = screen.get_wch()
        if key == "\x1b":
            return CANCEL
        if key == curses.KEY_DOWN:
            index = min(len(options) - 1, index + 1)
        elif key == curses.KEY_UP:
            index = max(0, index - 1)
        elif key == " " and multi:
            value = options[index][0]
            selected.symmetric_difference_update({value})
        elif key in ("\n", "\r", curses.KEY_ENTER):
            return [value for value, _ in options if value in selected] if multi else options[index][0]


def edit_text(screen, title, initial=""):
    value, cursor = initial, len(initial)
    try:
        curses.curs_set(1)
    except curses.error:
        pass
    try:
        while True:
            screen.erase()
            h, w = screen.getmaxyx()
            put(screen, 1, 2, title, curses.A_BOLD)
            start = cursor
            while start > 0 and weeks._width(value[start - 1:cursor]) < max(1, w - 5):
                start -= 1
            put(screen, 3, 2, value[start:], curses.A_UNDERLINE)
            put(screen, h - 2, 1, "Enter 적용  Esc 취소  Ctrl+U 비우기", curses.A_DIM)
            try:
                screen.move(min(3, h - 1), min(w - 2, 2 + weeks._width(value[start:cursor])))
            except curses.error:
                pass
            screen.refresh()
            key = screen.get_wch()
            if key == "\x1b":
                return None
            if key in ("\n", "\r", curses.KEY_ENTER):
                return value
            if key in (curses.KEY_BACKSPACE, "\x7f", "\b") and cursor:
                value, cursor = value[:cursor - 1] + value[cursor:], cursor - 1
            elif key == curses.KEY_DC:
                value = value[:cursor] + value[cursor + 1:]
            elif key == curses.KEY_LEFT:
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_RIGHT:
                cursor = min(len(value), cursor + 1)
            elif key in (curses.KEY_HOME, "\x01"):
                cursor = 0
            elif key in (curses.KEY_END, "\x05"):
                cursor = len(value)
            elif key == "\x15":
                value, cursor = "", 0
            elif isinstance(key, str) and key.isprintable():
                value, cursor = value[:cursor] + key + value[cursor:], cursor + len(key)
    finally:
        try:
            curses.curs_set(0)
        except curses.error:
            pass


def edit_form(screen, title, fields, submit):
    values = {f.key: copy.deepcopy(f.value) for f in fields}
    index, message = 0, ""
    while True:
        screen.erase()
        h, w = screen.getmaxyx()
        put(screen, 1, 2, title, curses.A_BOLD)
        rows = [f.label + ": " + (", ".join(team.ROLES.get(v, v) for v in values[f.key]) if f.kind == "roles" else str(values[f.key])) for f in fields] + ["저장", "취소"]
        start = max(0, index - max(1, h - 7) + 1)
        for y, i in enumerate(range(start, min(len(rows), start + max(1, h - 7))), 3):
            put(screen, y, 2, rows[i], curses.A_REVERSE if i == index else 0)
        put(screen, h - 2, 1, "↑↓ 이동  Enter 수정/선택  Esc 취소", curses.A_DIM)
        put(screen, h - 1, 1, message)
        screen.refresh()
        key = screen.get_wch()
        if key == "\x1b":
            return
        if key == curses.KEY_DOWN:
            index = min(len(rows) - 1, index + 1)
        elif key == curses.KEY_UP:
            index = max(0, index - 1)
        elif key in ("\n", "\r", curses.KEY_ENTER):
            if index == len(fields) + 1:
                return
            if index == len(fields):
                try:
                    submit(values)
                    return
                except (ValueError, OSError) as error:
                    message = str(error)
            else:
                field = fields[index]
                if field.kind == "roles":
                    options = list(team.ROLES.items())
                    options += [(v, v) for v in values[field.key] if v not in team.ROLES]
                    value = choose(screen, field.label, options, values[field.key], multi=True)
                    if value is not CANCEL:
                        values[field.key] = value
                else:
                    value = edit_text(screen, field.label, str(values[field.key]))
                    if value is not None:
                        values[field.key] = value


def run(periods, period, start_tab=0, path=()):
    app = App(periods, period, start_tab)
    if path and start_tab == 0:
        app.selected[app.selection_key] = path[0] - 1
    def main(screen):
        curses.set_escdelay(30)
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        screen.keypad(True)
        curses.mousemask(curses.ALL_MOUSE_EVENTS)
        app.start_discovery(automatic=True)
        while True:
            app.poll_discovery()
            app.poll_activity()
            app.start_activity()
            screen.timeout(120 if app.discovery_running or app.activity_running else -1)
            app.draw(screen)
            try:
                key = screen.get_wch()
            except curses.error:
                continue
            if not app.handle(key, screen):
                return 0
    try:
        return curses.wrapper(main)
    except KeyboardInterrupt:
        return 0
