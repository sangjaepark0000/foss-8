from unicodedata import east_asian_width
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from .guide import Catalog, plain

# 평가 항목별 확인 방식과 안내
CHECK_METHODS = {
    "기능 동작(기준 2)": {
        "method": "수동",
        "auto_help": "없음",
        "manual_help": "각 기능을 실행하고 완료 조건과 시연 결과를 확인하세요.",
    },
    "실행 재현(기준 1)": {
        "method": "혼합",
        "auto_help": "v1.0.0 태그 존재 여부",
        "manual_help": "새 폴더에서 README대로 설치하고 실행해 보세요.",
    },
    "문서(기준 3)": {
        "method": "혼합",
        "auto_help": "README·LICENSE·CONTRIBUTING·CODE_OF_CONDUCT 파일 존재 여부",
        "manual_help": "각 문서의 내용과 README 필수 항목을 직접 확인하세요.",
    },
    "협업 절차(기준 4·5)": {
        "method": "혼합",
        "auto_help": "PR·리뷰·병합 기록",
        "manual_help": "모든 기능이 해당 절차를 거쳤는지와 타 팀 이슈 해결 내용을 확인하세요.",
    },
}

# 저장소 루트에서 확인할 기본 파일
REQUIRED_FILES = (
    "README.md",
    "LICENSE",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "requirements.txt",
    "main.py",
)

def load_result_items():
    # 15.5절의 결과물 평가 항목을 리스트로 반환
    catalog = Catalog()
    document = catalog.show("evaluation#section-15-5")
    # 15.6절 앞에서 잘라 15.5절만 남긴다.
    section = document["markdown"].split('<a id="section-15-6"></a>', 1)[0]
    items = []

    for line in section.splitlines():
        if not line.startswith("|"):
            continue

        # 양끝의 |를 제거하고 네 개의 표 셀을 분리
        cells = [plain(cell).strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 4 or not cells[1].isdigit():
            continue  # 표 제목과 구분선은 제외한다.

        name = cells[0]

        # 안내서에 새로운 항목이 생겼는데 확인 방식이 없으면 알려준다.
        if name not in CHECK_METHODS:
            raise ValueError(f"확인 방식이 정의되지 않은 평가 항목입니다: {name}")

        policy = CHECK_METHODS[name]
        
        # 데이터를 딕셔너리로 저장
        items.append({
            "name": name,
            "points": int(cells[1]),
            "criterion": cells[2],
            "partial_credit": cells[3],
            "source": document["source"],
            "method": policy["method"],
            "auto_help": policy["auto_help"],
            "manual_help": policy["manual_help"],
            "status": "미확인",
        })

    # 누락 시 오류 메시지 발생
    if len(items) != 4 or sum(item["points"] for item in items) != 30:
        raise ValueError("결과물 평가 항목은 4개, 배점 합계는 30점이어야 합니다. 원문 표를 확인하세요.")

    return items


def format_result_items(items):
    # 평가 항목 리스트를 화면에 표시할 문자열로 변환
    lines = ["[결과물 평가 기준]", ""]

    for item in items:
        source = item["source"]
        lines.extend([
            f"{item['name']} | 최대 {item['points']}점",
            f"기준: {item['criterion']}",
            f"부분 점수 예: {item['partial_credit']}",
            f"확인 방식: {item['method']}",
            f"자동 확인 대상: {item['auto_help']}",
            f"수동 확인: {item['manual_help']}",
            f"상태: {item['status']}",
            f"근거: {source['document']}#{source['anchor']}",
            "",
        ])

    # 항목별 배점을 더하고 각 줄을 줄바꿈으로 연결
    total_points = sum(item["points"] for item in items)
    lines.append(f"총 배점: {total_points}점")
    return "\n".join(lines)

def check_required_files(repository_path):
    # 입력받은 경로를 절대 경로로 변환
    root = Path(repository_path).expanduser().resolve()

    # 잘못된 폴더를 검사해 모든 파일을 '누락'으로 표시하지 않도록 확인
    if not root.is_dir():
        raise ValueError(f"검사 경로가 존재하는 폴더가 아닙니다: {root}")

    results = []

    for filename in REQUIRED_FILES:
        file_path = root / filename

        try:
            file_path.stat()
        except FileNotFoundError:
            status = "누락"
        except OSError:
            status = "확인 불가"
        else:
            status = "존재" if file_path.is_file() else "파일 아님"

        results.append({
            "name": filename,
            "path": str(file_path),
            "status": status,
        })

    return results

def format_file_results(results):
    lines = []

    for item in results:
        lines.append(f"[{item['status']}] {item['name']}")

    lines.append("")
    lines.append("문서 내용은 직접 확인해주세요.")

    return "\n".join(lines)

ACTIVITY_RULES = (
    ("commits", "커밋", 2, date(2026, 10, 9)),
    ("prs_created", "PR 생성", 1, date(2026, 10, 30)),
    ("prs_merged", "PR 병합", 1, date(2026, 10, 30)),
    ("issues", "이슈 작성", 1, date(2026, 10, 9)),
)
ACTIVITY_END = date(2026, 12, 13)
EXAM_START = date(2026, 10, 19)
EXAM_END = date(2026, 10, 25)


def format_activity_rules():
    lines = ["[주간 활동 기준]", "집계 주간: 월요일~일요일 (한국 시간)"]
    for _, label, minimum, starts_on in ACTIVITY_RULES:
        lines.append(f"- {label}: 주 {minimum}건 이상 ({starts_on}~{ACTIVITY_END})")
    lines.append(f"중간고사 면제: {EXAM_START}~{EXAM_END}")
    return "\n".join(lines)


def collect_activity(last_7_days=False):
    from . import activity, minutes

    team = minutes.load_config()
    remote = urlsplit(team["repository"])
    if remote.hostname != "github.com":
        raise ValueError("GitHub 저장소 폴더에서 실행하세요.")
    repo = remote.path.strip("/").removesuffix(".git")

    members = team["members"]
    if not members:
        raise ValueError("README의 팀원 표에 GitHub ID를 등록하세요.")

    today = minutes.today()
    start = today - timedelta(days=6 if last_7_days else today.weekday())
    return activity.collect(repo, start.isoformat(), today.isoformat(), members)

def activity_cell(category, start, end, starts_on, minimum):
    if category["error"]:
        return "확인 불가"
    if end < starts_on or start > ACTIVITY_END:
        return "대상 아님"
    if EXAM_START <= start and end <= EXAM_END:
        return "면제"
    if start < starts_on or end > ACTIVITY_END or start <= EXAM_END and end >= EXAM_START:
        return "수동 확인"
    return f"{len(category['links'])}/{minimum}"


def terminal_width(text):
    return sum(2 if east_asian_width(char) in ("W", "F") else 1 for char in text)


def format_activity_table(rows):
    widths = [max(map(terminal_width, column)) for column in zip(*rows)]
    lines = []

    for index, row in enumerate(rows):
        cells = [cell + " " * (width - terminal_width(cell)) for cell, width in zip(row, widths)]
        lines.append(" | ".join(cells).rstrip())
        if index == 0:
            lines.append("-+-".join("-" * width for width in widths))

    return lines


def format_activity_results(data, show_links=False, last_7_days=False):
    start = date.fromisoformat(data["start"])
    end = date.fromisoformat(data["end"])
    title = "[최근 7일 활동]" if last_7_days else "[이번 주 활동 점검]"
    lines = [title, f"저장소: {data['repository']}", f"조회 기간: {start}~{end} (한국 시간)", ""]
    rows = [("팀원", "커밋", "PR 생성·병합", "이슈")]
    details = []

    for member in data["members"]:
        name = member["name"]
        cells = {}

        for key, label, minimum, starts_on in ACTIVITY_RULES:
            category = member["categories"][key]
            cells[key] = activity_cell(category, start, end, starts_on, minimum)

            if category["error"]:
                details.append(f"- {name} · {label}: {category['error']}")
            elif show_links:
                details.extend(f"- {name} · {label}: {link}" for link in category["links"])

        prs = f"{cells['prs_created']} · {cells['prs_merged']}"
        rows.append((name, cells["commits"], prs, cells["issues"]))

    lines.extend(format_activity_table(rows))
    lines.append("\n표기: 실적/기준 · PR은 생성, 병합 순서")
    if details:
        lines.extend(["", *details])
    lines.append("수동 확인: 활동의 실질성, 이슈의 작업 전 등록 여부, PR의 병합 전 승인 여부")
    return "\n".join(lines)