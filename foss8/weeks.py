"""Offline, week-first handbook browser with nearby task details."""
from datetime import date, datetime, timedelta, timezone
from importlib.resources import files
import json
import re
import shutil
import sys
import unicodedata


def load(team_config=None):
    from .team import apply
    data = json.loads(files("foss8").joinpath("data/weeks.json").read_text(encoding="utf-8"))
    periods = apply(data["periods"], team_config)
    for period in periods:
        references = {}
        for task in period["tasks"]:
            if task.get("kind") == "reference":
                content = {key: value for key, value in task.items() if key not in ("id", "progress_period")}
                references.setdefault(json.dumps(content, ensure_ascii=False, sort_keys=True), task)
        period["references"] = list(references.values())
        period["tasks"] = [t for t in period["tasks"] if t.get("kind") != "reference"]
        period["carryovers"] = []
    for source, following in zip(periods, periods[1:]):
        for task in source["tasks"]:
            if task.get("carry_next_week"):
                following["carryovers"].append({**task, "carryover_from": source["label"],
                                                "progress_period": task.get("progress_period", source["id"])})
    return periods


def view_tasks(period):
    return period["tasks"] + period.get("carryovers", [])


def timing_marker(node):
    return " [이어서]" if node.get("carryover_from") else " [수업 후]" if node.get("after_class") else ""


def timing_notes(node):
    if not node.get("after_class"):
        return []
    day = date.fromisoformat(node["after_class"])
    notes = [f'시작: {day.month}/{day.day} 수업 후']
    if node.get("carryover_from"):
        notes.append(node["carryover_from"] + "에서 이어지는 같은 작업입니다.")
    if node.get("carry_next_week"):
        notes.append("이번 주·다음 주의 완료 표시를 함께 관리합니다.")
    return notes


def today():
    return datetime.now(timezone(timedelta(hours=9))).date()


def select(periods, week=None, on=None):
    if week is not None:
        key = str(week).removesuffix("주차")
        key = "makeup" if key in ("makeup", "보강") else key
        for period in periods:
            if any(str(value) == key for value in period["weeks"]):
                return period
        raise ValueError("조회할 수 없는 주차입니다. week --list로 주차를 확인하세요. 보강 주는 week makeup입니다.")
    if on is None:
        on = today()
    elif isinstance(on, str):
        try:
            on = date.fromisoformat(on)
        except ValueError as error:
            raise ValueError("날짜는 YYYY-MM-DD 형식으로 입력하세요.") from error
    # Academic weeks run Tuesday through Monday; scheduled classes are separate events.
    for period in periods:
        if date.fromisoformat(period["start"]) <= on < date.fromisoformat(period["end"]):
            return period
    return periods[0] if on < date.fromisoformat(periods[0]["start"]) else periods[-1]


def entries(node):
    result = list(node.get("children", []))
    if node.get("details"):
        if result:
            result.append({"title": "방법", "children": node["details"]})
        else:
            result.extend(node["details"])
    if node.get("evaluation"):
        result.append({"title": "평가기준", "children": [{"title": value} for value in node["evaluation"]]})
        result.append({"title": "평가 근거", "children": [{"title": node["evaluation_source"]}]})
    return result


def parse_path(value):
    if not value:
        return ()
    if not re.fullmatch(r"[1-9]\d*(?:\.[1-9]\d*)*", value):
        raise ValueError("항목 번호는 1 또는 1.2처럼 입력하세요.")
    return tuple(int(part) for part in value.split("."))


def resolve(period, path=()):
    node = {"title": period["title"], "children": view_tasks(period)}
    for number in path:
        children = entries(node)
        if number < 1 or number > len(children):
            raise ValueError("없는 항목 번호입니다. 상위 목록의 번호를 확인하세요.")
        node = children[number - 1]
    return node


def plain(text):
    return re.sub(r"`([^`\n]+)`", r"\1", text)


def _width(text):
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in text)


def wrapped(text, prefix="", width=None):
    width = width or min(100, max(28, shutil.get_terminal_size((88, 24)).columns))
    lines = []
    for paragraph in plain(text).splitlines() or [""]:
        line = prefix
        for char in paragraph:
            if _width(line + char) > width and line != prefix:
                lines.append(line.rstrip())
                line = " " * _width(prefix)
            line += char
        lines.append(line.rstrip())
    return lines


def heading(period):
    start, end = date.fromisoformat(period["start"]), date.fromisoformat(period["end"]) - timedelta(days=1)
    return [f'{period["label"]} · {period["title"]}',
            f'  {start.month}/{start.day} ~ {end.month}/{end.day}', ""]


def render(period, path=(), interactive=False):
    node = resolve(period, path)
    lines = heading(period)
    if path:
        if node.get("kind") == "code":
            lines.extend(node["title"].splitlines())
        else:
            lines += wrapped(node["title"] + timing_marker(node) + (" [평가]" if node.get("evaluation") else ""))
        lines += timing_notes(node)
        lines.append("")
    children = entries(node)
    for number, child in enumerate(children, 1):
        expandable = bool(entries(child))
        marker = " [평가]" if child.get("evaluation") else ""
        suffix = "  ›" if expandable else ""
        if child.get("kind") == "code":
            lines.append(f"  {number}. 예시 코드  ›")
        else:
            lines += wrapped(child["title"] + timing_marker(child) + marker + suffix, prefix=f"  {number}. ")
    if not path or children:
        lines.append("")
    if interactive:
        lines.append("번호: 펼치기 · b: 뒤로 · w: 주차 · p/n: 이전/다음 기간 · q: 종료")
    elif any(entries(child) for child in children):
        first_detail = next(i for i, child in enumerate(children, 1) if entries(child))
        next_path = ".".join(map(str, path + (first_detail,)))
        lines.append(f'상세: python main.py week {period["id"]} --task {next_path}')
    return "\n".join(lines).rstrip() + "\n"


def listing(periods):
    lines = []
    for period in periods:
        lines += heading(period)[:2]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def expandable(node):
    return bool(entries(node)) or node.get("kind") == "code"


def open_path(expanded, path):
    """Reveal a path in place, retaining the other open branches."""
    expanded.update(path[:depth] for depth in range(1, len(path) + 1))


def toggle_paths(period, expanded, values):
    paths = [parse_path(value) for value in values]
    nodes = [resolve(period, path) for path in paths]
    for path, node in zip(paths, nodes):
        if not path or not expandable(node):
            continue
        visible = all(path[:depth] in expanded for depth in range(1, len(path)))
        if path in expanded and visible:
            expanded.remove(path)
        else:
            open_path(expanded, path)


def render_tree(period, expanded):
    lines = heading(period)

    def draw(nodes, parent=()):
        for number, node in enumerate(nodes, 1):
            path = parent + (number,)
            key = ".".join(map(str, path))
            opened = path in expanded and expandable(node)
            arrow = "▾" if opened else "▸" if expandable(node) else " "
            marker = " [평가]" if node.get("evaluation") else ""
            title = "예시 코드" if node.get("kind") == "code" else node["title"] + timing_marker(node)
            prefix = "  " * (len(parent) + 1) + key + " " + arrow + " "
            lines.extend(wrapped(title + marker, prefix=prefix))
            if opened:
                if node.get("kind") == "code":
                    lines.extend("  " * (len(path) + 2) + value for value in node["title"].splitlines())
                else:
                    draw(entries(node), path)

    draw(view_tasks(period))
    lines += ["", "번호: 펼치기/접기 · 4.6.1처럼 바로 열기 · 여러 항목: 4 5",
              "w 9: 주차 변경 · p/n: 이전/다음 기간 · c: 모두 접기 · q: 종료"]
    return "\n".join(lines) + "\n"


def browse(periods, period, path=(), input_fn=input, output=None):
    output = output or sys.stdout
    opened_by_period = {}
    expanded = opened_by_period.setdefault(period["id"], set())
    open_path(expanded, path)
    show_weeks = False
    message = ""
    while True:
        if getattr(output, "isatty", lambda: False)():
            # Keep one view instead of appending a new page for every selection.
            print("\033[2J\033[H", end="", file=output)
        if show_weeks:
            print(listing(periods), file=output)
        print(render_tree(period, expanded), file=output)
        if message:
            print(message, file=output)
            message = ""
        try:
            value = input_fn("선택 > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(file=output)
            return 0
        if value in ("q", "quit"):
            return 0
        try:
            if value in ("c", "b", "0"):
                expanded.clear()
            elif value in ("p", "n"):
                index = periods.index(period)
                index = max(0, min(len(periods) - 1, index + (1 if value == "n" else -1)))
                period = periods[index]
                expanded = opened_by_period.setdefault(period["id"], set())
                show_weeks = False
            elif value == "w":
                show_weeks = not show_weeks
            elif value.startswith("w"):
                choice = value[1:].strip()
                period = select(periods, choice)
                expanded = opened_by_period.setdefault(period["id"], set())
                show_weeks = False
            elif value:
                toggle_paths(period, expanded, value.split())
        except ValueError as error:
            message = f"오류: {error}"


def run(args):
    from . import team
    config = team.load()
    periods = load(config)
    if args.number and args.date:
        raise ValueError("주차 번호와 --date 중 하나를 선택하세요.")
    if args.list:
        if args.number or args.date or args.task:
            raise ValueError("--list는 주차·날짜·항목 선택과 함께 사용할 수 없습니다.")
        if args.json:
            from .cli import emit
            emit(data={"periods": periods})
        else:
            print(listing(periods), end="")
        return 0
    period = select(periods, args.number, args.date)
    path = parse_path(args.task)
    resolve(period, path)
    if args.json:
        from .cli import emit
        emit(data={"period": period, "path": list(path), "node": resolve(period, path)})
    elif sys.stdin.isatty() and sys.stdout.isatty() and not args.no_interactive and not args.task:
        try:
            from . import tui
        except ImportError:
            print(render(period, path), end="")
            print("이 환경에서는 키보드 화면을 사용할 수 없습니다.", file=sys.stderr)
            return 0
        return tui.run(periods, period, path=path)
    else:
        print(render(period, path), end="")
    return 0
