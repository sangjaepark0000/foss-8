from datetime import date, datetime, timezone, timedelta
import re
from .guide import plain, Catalog

def cell(value):
    value = re.sub(r"([),]|\.md|\.py)<br>", r"\1", value)
    value = re.sub(r"&lt;([^&gt;]+)&gt;", r"<\1>", value)
    return value.replace("<br>", "").strip()

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
        for task in columns[3].split("•"):
            task = task.strip()
            if not task:
                continue
            role, _, text = task.partition(":")
            tasks.append({"role": role if _ else "공통", "text": text if _ else task})
        result.append({"id": id, "week": week, "date":date(year, month, day).isoformat(), "makeup": makeup,
                       "label": f"{week}주차" + (" 보강" if makeup else "") + f" · {date(year, month, day)}",
                       "lesson": columns[2], "tasks": tasks, "turnin": columns[4]})
    return result

def get_this_week(catalog):
    today = datetime.now(timezone(timedelta(hours=9))).date().isoformat()
    items = roadmap(catalog)
    return next((item["week"] for item in items if item["date"] >= today), items[-1]["week"])

def get_weekly_item(catalog, selector, makeup=False):
    items = roadmap(catalog)
    if makeup:
        item = next((item for item in items if item["makeup"]==True), None)
        return item
    if str(selector).isdigit():
        week = int(selector)
        item = next((item for item in items if item["week"]==week), None)
    else:
        item = next((item for item in items if item['id']==selector), None)
    if item is None:
        raise ValueError("안내서에 없는 주차입니다. week --list로 주차 목록을 확인하세요.")
    return item

def result_line(item):
    lines = [f"{item['label']}", f"수업 내용:{item['lesson']}", "", "** 할 일 **"]
    lines += [f"- {task['role']}: {task['text']}" for task in item["tasks"]]
    lines += ["", "** 제출 **", f"- {item['turnin']}"]
    return "\n".join(lines)