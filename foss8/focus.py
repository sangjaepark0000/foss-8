"""A small view of the next submission; dates come from the bundled handbook."""
from datetime import date, datetime, timezone, timedelta
import re

from .guide import plain


def next_submissions(catalog, today=None):
    today = today or datetime.now(timezone(timedelta(hours=9))).date()
    year = int(re.search(r"_(\d{4})-2_", catalog.manifest["source_path"])[1])
    doc, _ = catalog.resolve("minutes")
    schedule = []
    for line in doc.markdown.splitlines():
        cells = [plain(cell).strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 5 or not re.fullmatch(r"\d+/\d+", cells[2]):
            continue
        month, day = map(int, cells[2].split("/"))
        schedule.append({"title": cells[1].replace("_팀명", ""), "date": date(year, month, day).isoformat(),
                         "time": "18:00", "destination": "LMS", "source": catalog.reference(doc, "section-12-1")})
    for selector, title in [("midterm", "중간보고서"), ("final", "최종보고서")]:
        item = catalog.show(selector)
        match = re.search(r"제출 마감</td><td>(\d+)/(\d+)", item["markdown"])
        if match:
            month, day = map(int, match.groups())
            schedule.append({"title": title, "date": date(year, month, day).isoformat(), "time": "18:00",
                             "destination": "LMS", "source": item["source"]})
    upcoming = sorted([item for item in schedule if item["date"] >= today.isoformat()], key=lambda item: (item["date"], item["title"]))
    nearest = [item for item in upcoming if item["date"] == upcoming[0]["date"]] if upcoming else []
    return {"as_of": today.isoformat(), "semester": "2026-2", "next_submissions": nearest,
            "status": "일정 안내 · 실제 제출 여부는 직접 확인", "team_document": "team-context"}


def markdown(data):
    lines = ["# 지금 확인할 것", "", f"기준일: {data['as_of']}", ""]
    if data["next_submissions"]:
        for item in data["next_submissions"]:
            lines += [f"## {item['date']} · {item['time']}", "", f"**{item['title']}** · {item['destination']} 제출", ""]
        if any("회의록" in item["title"] for item in data["next_submissions"]):
            lines += ["- 회의록 작성 확인", "- 전원 확인", "- PDF로 제출", "", "foss-8: 문서 담당 작성 → 전원 확인 → **상재 제출**.", ""]
        lines += ["이미 제출했다면 완료 여부를 확인하고 다음 일정을 보세요.", ""]
    else:
        lines += ["이 안내서의 2026-2 제출 일정에는 이후 마감이 없습니다.", ""]
    lines += ["[전체 제출 날짜](12-minutes.md#section-12-1) · [팀 약속](team-context.md)"]
    return "\n".join(lines)
