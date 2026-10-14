from .guide import Catalog, plain

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

        # 데이터를 딕셔너리로 저장
        items.append({
            "name": cells[0],
            "points": int(cells[1]),
            "criterion": cells[2],
            "partial_credit": cells[3],
            "source": document["source"],
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
            "확인 안내: 기준 충족 여부는 직접 확인 필요 (자동 점검 미구현)",
            "상태: 미확인",
            f"근거: {source['document']}#{source['anchor']}",
            "",
        ])

    # 항목별 배점을 더하고 각 줄을 줄바꿈으로 연결
    total_points = sum(item["points"] for item in items)
    lines.append(f"총 배점: {total_points}점")
    return "\n".join(lines)
