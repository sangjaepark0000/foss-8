# [부록 C](appendix-c-templates.md). 템플릿 파일

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 41~44쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-41"></a>

## 원문 41쪽

<!-- source-page: 41 -->
## [부록 C](appendix-c-templates.md). 템플릿 파일

[7.3절](07-repository.md#section-7-3)에서 GitHub 웹의 Add file → Create new file로 넣는 파일입니다. moneylog, &lt;팀장아이디&gt; 등은 여러분의 값으로 바꿉니다.

<a id="appendix-c-1"></a>

### C-1. README.md

````markdown
# moneylog

터미널에서 쓰는 가계부 — 거래 입력, 월별 통계, 예산 경고, 그래프 저장

## 스크린샷
![실행 화면](docs/images/demo.png)

## 주요 기능
| 기능 | 설명 | 담당 |
|------|------|------|
| add | 거래 입력·검증 | 홍길동 |
| summary | 월별·분류별 통계 | 김철수 |
| budget | 예산 설정·초과 경고 | 이영희 |
| chart | 그래프 PNG 저장 | 박민수 |

## 설치와 실행 (Python 3.12 이상, 3.13에서 테스트)
```
git clone https://github.com/<팀장아이디>/moneylog.git
cd moneylog
pip install -r requirements.txt
python main.py
```

## 사용법
1. 메뉴에서 `1`을 누르면 거래 입력 — 예: `2026-10-13, 12000, 식비, 점심`
2. `2`를 누르면 이번 달 합계와 분류별 합계 출력
3. `4`를 누르면 `docs/images/` 폴더에 그래프 PNG 저장

## 팀원
| 이름 | 역할 | GitHub |
|------|------|--------|
| 홍길동 | 팀장 | @hong-id |

기여 방법은 [CONTRIBUTING.md](CONTRIBUTING.md), 행동 수칙은 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)
를 참고하세요.

## 라이선스
MIT License — see [LICENSE](LICENSE)
````
<!-- /source-page: 41 -->

<a id="page-42"></a>

## 원문 42쪽

<!-- source-page: 42 -->
<a id="appendix-c-2"></a>

### C-2. CONTRIBUTING.md

```markdown
# 기여 가이드

## 준비
1. Python 3.12 이상 설치 → 저장소 클론 → `pip install -r requirements.txt`
2. 실행: `python main.py`

## 작업 흐름 (팀원)
1. 작업 전에 이슈를 먼저 만들거나 기존 이슈에 댓글로 배정 요청
2. `main`에서 `feature/기능이름` 브랜치를 만들어 작업 (main에 직접 커밋하지 않음)
3. 커밋 메시지: `기능 설명 (#이슈번호)` — 예: `거래 입력 기능 추가 (#12)`
4. 올리기 전에 프로그램을 실행해 확인
5. 풀 리퀘스트 설명에 무엇을/왜(`Closes #이슈`)/어떻게 확인했나 3줄, 리뷰어 1명 지정
6. 승인 1개 뒤 작성자가 `Merge pull request`

## 타 팀·외부 기여자
1. `good first issue` 라벨 이슈에 댓글로 배정을 요청하고, 담당자로 지정된 뒤 시작
2. 이 저장소를 `Fork` → 소스트리로 클론 → 브랜치를 만들어 작업
3. 수정 → 커밋 → Push → fork 페이지의 `Contribute` → `Open pull request` (base는 이 저장소의 `main`)
4. 리뷰·질문 응답은 48시간 이내

## 행동 수칙
- 모든 참여자는 CODE_OF_CONDUCT.md 를 따릅니다

## 코드 규칙
- PEP 8 스타일, 기능마다 파일 1개, 파일 입출력은 `encoding="utf-8"`
- 새 라이브러리는 requirements.txt 에 추가
- 토큰·비밀번호·개인정보는 절대 올리지 않음

## AI 도구
- 사용 가능. 직접 실행해 확인한 코드만 올리고, 풀 리퀘스트 설명에 사용 여부를 적음
```

<a id="appendix-c-3"></a>

### C-3. CODE\_OF\_CONDUCT.md (행동 수칙)

수업 3·13주차에서 '프로젝트에 꼭 포함할 파일'로 배운 행동 수칙입니다. 아래 짧은 버전을 참고해서 써도 되고, 표준 문서인 Contributor Covenant(contributor-covenant.org, 한국어 번역 있음)를 가져와도 됩니다.

```text
# 행동 수칙

이 프로젝트의 모든 참여자(팀원, 타 팀 기여자, 사용자)는 서로를 존중하며 다음을 지킵니다.
```
<!-- /source-page: 42 -->

<a id="page-43"></a>

## 원문 43쪽

<!-- source-page: 43 -->
```markdown
## 환영하는 행동
- 리뷰·이슈·채팅에서 사람이 아닌 코드와 문제에 대해 말합니다.
- 질문을 환영하고, 처음 기여하는 사람에게는 절차를 구체적으로 안내합니다.
- 의견이 다를 때는 근거(실행 결과, 문서)를 들어 설명합니다.
- 요청·리뷰에는 48시간 안에 응답하고, 늦어지면 미리 알립니다.

## 허용하지 않는 행동
- 인신공격, 조롱, 차별적 표현, 비하
- 다른 사람의 작업을 동의 없이 삭제하거나 덮어쓰는 행위(강제 푸시)
- 개인정보·비밀 키를 공개 저장소에 올리는 행위

## 신고와 처리
- 문제가 있으면 팀장에게 알리거나 교수(shoh0320@pknu.ac.kr)에게 이메일로 알립니다.
- 반복되는 위반은 회의록에 기록하고 평가에 반영됩니다.
```

<a id="appendix-c-4"></a>

### C-4. requirements.txt

```text
# 사용하는 라이브러리를 한 줄에 하나씩. 표준 라이브러리(csv, json 등)는 적지 않음.
matplotlib
```

<a id="appendix-c-5"></a>

### C-5. main.py (시작 파일 예시)

```python
"""moneylog — 터미널 가계부. 메뉴를 보여 주고 각 기능을 호출한다."""

def main():
    while True:
        print("\n=== moneylog ===")
        print("1. 거래 입력 2. 월별 통계 3. 예산 관리 4. 그래프 저장 0. 종료")
        choice = input("선택: ").strip()
        if choice == "0":
            break
        elif choice == "1":
            print("준비 중 (담당: 홍길동, #3)") # 기능이 완성되면 add.run() 으로 교체
        elif choice == "2":
            print("준비 중 (담당: 김철수, #4)")
        elif choice == "3":
            print("준비 중 (담당: 이영희, #5)")
        elif choice == "4":
            print("준비 중 (담당: 박민수, #6)")
        else:
            print("0~4 중에서 선택하세요.")

if __name__ == "__main__":
    main()
```
<!-- /source-page: 43 -->

<a id="page-44"></a>

## 원문 44쪽

<!-- source-page: 44 -->
<a id="appendix-c-6"></a>

### C-6. .gitignore에 추가할 줄 (저장소 생성 시 고른 Python 템플릿 아래에)

```text
# ---- 프로젝트 추가 항목 ----
config.py # 토큰·키를 넣는 파일 (config_example.py 만 올림)
data/*.csv
!data/sample.csv
.DS_Store
Thumbs.db
```

<a id="appendix-c-7"></a>

### C-7. 풀 리퀘스트 설명 양식 (선택: .github/PULL\_REQUEST\_TEMPLATE.md 로 저장하면 자동 입력)

```markdown
## 무엇을 바꿨나요?
-

## 왜 바꿨나요? (관련 이슈)
Closes #

## 어떻게 확인했나요?
- 실행 명령:
- 확인한 내용:

## 스크린샷 (화면이 바뀐 경우)

## AI 도구 사용: 없음 / 있음(도구, 범위)
```
<!-- /source-page: 44 -->

[이전: 부록 B. 회의록 양식](appendix-b-minutes-template.md) · [전체 목차](README.md) · [다음: 부록 D. 소스트리·명령어 대응표와 충돌 실습](appendix-d-git-drill.md)
