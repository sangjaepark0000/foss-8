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
