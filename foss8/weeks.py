from datetime import date, datetime, timezone, timedelta
import re
from .guide import plain, Catalog

def cell(value):
    value = re.sub(r"([),.\u2192]|\.md|\.py)<br>", r"\1 ", value)
    value = value.replace("<br>", "")
    return re.sub(r"\s+", " ", plain(value)).strip()

def roadmap(catalog):
    doc = catalog.show("calendar#chapter-3")
    section = doc["markdown"].split('<a id="section-3-1"></a>')[0]
    year = int(re.search(r"_(\d{4})-2_", catalog.manifest["source_path"])[1])
    result = []
    for line in section.splitlines():
        columns = [cell(value) for value in line.strip().strip("|").split("|")]
        if len(columns) != 5 or not (week := re.match(r"(\d+)주", columns[0])):
            continue
        makeup = True if "보강" in columns[0] else False
        when = re.search(r"(\d+)/(\d+)", columns[1])
        if not when:
            continue
        week = int(week.group(1))
        month, day = map(int, when.groups())
        id = f"week-{week}" + ("-makeup" if makeup else "")
        tasks = []
        task = columns[3].split("•")
        for line in task:
            line = line.strip()
            if not line:
                continue
            matches = re.findall(r"([^:]+):(.+?)(?=\s+[^\s:]+:|$)",line)
            if matches:
                tasks.extend({"role":role.strip(), "text": text.strip()}for role, text in matches)
            else:
                tasks.append({"role":"공통", "text": line.strip()})
        result.append({"id": id, "week": week, "date":date(year, month, day).isoformat(), "makeup": makeup,
                       "label": f"{week}주차" + (" 보강" if makeup else "") + f" · {date(year, month, day)}",
                       "lesson": columns[2], "tasks": tasks, "turnin": columns[4]})
    return result

def get_this_week(catalog):
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    items = roadmap(catalog)
    return next((item["id"] for item in items if item["date"] >= today), items[-1]["id"])

def get_weekly_item(catalog, selector):
    items = roadmap(catalog)
    if str(selector).isdigit():
        id = "week-"+ str(selector)
        item = next((item for item in items if item["id"]==id), None)
        if item is None:
            raise ValueError("안내서에 없는 주차입니다. week --list로 주차 목록을 확인하세요.")
    elif any(item["id"] == selector for item in items):
        item = next((item for item in items if item["id"] == selector), None)
    elif selector in ("makeup", "보강"):
        target = next((item["week"] for item in items if item["makeup"]), None)
        if target is None:
            raise ValueError("보강 주차가 존재하지 않습니다")
        id = "week-" + str(target) + "-makeup"
        item = next((item for item in items if item["id"]==id), None)
    else:
        raise ValueError("잘못된 입력입니다. 주차 선택시 week 2, 보강 주차 선택시 week makeup으로 입력하세요")
    return item

def result_line(item, week_progress=None):
    tasks = week_progress["tasks"] if week_progress is not None else [
        {"role": task["role"], "text": task["text"], "completed": False}
        for task in item["tasks"]
    ]
    memo = week_progress.get("memo", "") if week_progress is not None else ""
    lines = [f"{item['label']}", f"수업 내용:{item['lesson']}", "", "** 할 일 **"]
    for task_number, task in enumerate(tasks, start=1):
        completed = "[완료]" if task["completed"] else "[--]"
        lines.append(f"{task_number}. {completed} {task['role']}: {task['text']}")
    lines += ["", "** 제출 **", f"• {item['turnin']}", ""]
    if memo != "":
        lines.append(f"메모: {memo}")
    return "\n".join(lines)
