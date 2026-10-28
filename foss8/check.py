from pathlib import Path
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
        raise ValueError(f"검사할 폴더가 존재하지 않습니다: {root}")

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
    lines.append("문서 내용은 직접 확인해 주세요.")

    return "\n".join(lines)