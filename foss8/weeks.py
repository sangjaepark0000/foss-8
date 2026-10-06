"""Select a handbook week without conflating the two week-4 occurrences."""
from datetime import date, datetime, timezone, timedelta
import re

from .guide import plain


def cell(value):
    value = re.sub(r"([),]|\.md|\.py)<br>", r"\1 ", value)
    return value.replace("<br>", "").strip()


def listing(catalog):
    doc, _ = catalog.resolve("calendar")
    year = int(re.search(r"_(\d{4})-2_", catalog.manifest["source_path"])[1])
    page, result = None, []
    checklist, _ = catalog.resolve("checklist")
    checks = {}
    for line in checklist.markdown.splitlines():
        columns = [cell(value) for value in line.strip().strip("|").split("|")]
        if len(columns) == 3 and (match := re.search(r"(\d+)/(\d+)", columns[0])):
            checks[(int(match[1]), int(match[2]))] = [part.strip() for part in re.split(r"\s+/\s*|(?<=[^\d])/\s+", columns[1])]
    for line in doc.markdown.splitlines():
        marker = re.search(r"<!-- source-page: (\d+) -->", line)
        if marker:
            page = int(marker[1])
        columns = [cell(value) for value in line.strip().strip("|").split("|")]
        if len(columns) != 5 or not (match := re.match(r"(\d+)주", columns[0])):
            continue
        when = re.search(r"(\d+)/(\d+)", columns[1])
        if not when:
            continue
        number = int(match[1])
        month, day = map(int, when.groups())
        kind = "보강" if "보강" in columns[0] else "휴강" if "휴강" in columns[1] else "수업"
        key = f"week-{number:02d}" + ("-makeup" if kind == "보강" else "-break" if kind == "휴강" else "")
        tasks = []
        for task in columns[3].split("•"):
            task = task.strip()
            if not task:
                continue
            role, separator, text = task.partition(":")
            tasks.append({"role": plain(role) if separator else "공통", "text": plain(text if separator else task),
                          "markdown": text.strip() if separator else task})
        source = catalog.reference(doc, f"page-{page}")
        source["pages"] = [page]
        result.append({"id": key, "week": number, "kind": kind, "date": date(year, month, day).isoformat(),
                       "label": f"{number}주차" + (f" {kind}" if kind != "수업" else "") + f" · {month}/{day}",
                       "class": plain(columns[2]), "class_markdown": columns[2], "tasks": tasks,
                       "submission": plain(columns[4]), "submission_markdown": columns[4],
                       "checklist": checks.get((month, day), []), "source": source,
                       "checklist_source": catalog.reference(checklist, "page-39")})
    if len(result) != 15:
        raise ValueError("안내서 로드맵의 15개 일정을 읽지 못했습니다. 원문 형식을 확인하세요.")
    return result


def default(catalog, today=None):
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    items = listing(catalog)
    return next((item["id"] for item in items if item["date"] >= today.isoformat()), items[-1]["id"])


def get(catalog, selector, makeup=False):
    items = listing(catalog)
    if str(selector).isdigit():
        number = int(selector)
        item = next((item for item in items if item["week"] == number and (item["kind"] == "보강") == makeup), None)
    else:
        item = next((item for item in items if item["id"] == selector), None)
    if item is None:
        raise ValueError("안내서에 없는 주차입니다. oss week --list로 확인하세요. 4주차 보강은 --makeup입니다.")
    return item


def markdown(item, checklist=False):
    if checklist:
        lines = [f"# {item['label']} · 개인 점검표", "", "부록 A의 원문 점검 항목입니다. 다음 주 회의록이 포함된 주도 있습니다.", ""]
        lines += ["- " + check for check in item["checklist"]]
    else:
        lines = [f"# {item['label']}", "", item["class_markdown"], "", "## 할 일", ""]
        lines += [f"- **{task['role']}**: {task['markdown']}" for task in item["tasks"]]
        lines += ["", "## 제출", "", item["submission_markdown"]]
        if "회의록" in item["submission"] and "없음" not in item["submission"]:
            lines += ["", "회의록 PDF 제출: 목요일 18:00 · LMS. [정확한 날짜](12-minutes.md#section-12-1)"]
    lines += ["", "[원문 로드맵](03-roadmap.md#" + item["source"]["anchor"] + ") · [활동 기준](10-activity.md) · [foss-8 팀 결정](team-context.md)"]
    return "\n".join(lines)
