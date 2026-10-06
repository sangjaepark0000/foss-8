# OSS 안내서 도구

주차별 할 일·제출물 조회와 전체 안내서 탐색·검색·양식 저장을 오프라인으로 사용할 수 있습니다. TUI와 CLI는 같은 원문을 읽습니다. 원문과 foss-8의 팀 결정은 구분해서 표시합니다.

## 지금 실행

```bash
uv run oss
uv run oss week 6
uv run oss guide search 회의록
uv run oss guide show minutes --format text
uv run oss format minutes --output 회의록.md
```

또는 `pip install -r requirements.txt` 후 `python main.py`로 실행합니다.

첫 화면에는 **주차별 할 일 / 회의록 양식 저장 / 검색 / 전체 안내서** 네 가지가 있습니다. ↑↓와 Enter로 선택합니다. 주차별 할 일 화면의 선택 상자에서 원하는 주차를 고르면 수업·할 일·제출물이 바뀝니다. 개인 점검표는 버튼으로 따로 펼칩니다. Esc로 돌아가고 Ctrl+Q로 종료합니다.

처음에는 한국 날짜를 기준으로 가장 가까운 이후 수업 일정을 선택합니다. 원하는 주차로 바꿀 수 있습니다. 안내서에는 1주차 항목이 없으며, 4주차의 9/25 휴강과 12/11 보강은 별도 항목입니다. 수업 당일과 제출 마감일은 다르므로 정확한 마감은 제출 날짜 링크에서 확인합니다. 부록 A의 개인 점검표에는 다음 주 회의록을 준비하는 항목도 있어 수업 주차별 제출물과 구분합니다.

## 설치

uv가 준비된 환경에서, 이 브랜치를 설치할 수 있습니다.

```bash
uv tool install git+https://github.com/sangjaepark0000/foss-8@feature/guide-tool
oss
```

Git 소스 설치에는 Git도 필요합니다. 설치 후에는 저장소 클론·로그인·API 토큰·초기 설정이 필요하지 않습니다. 안내서 전체와 양식은 패키지에 함께 포함됩니다. 공개용 안내서는 2026-2 v1.3이며 다른 학기 일정으로 자동 변경하지 않습니다.

개발용 로컬 설치: `uv tool install .`. 업데이트는 같은 소스로 `uv tool install --reinstall .`를 실행합니다. 브랜치 설치는 개발 버전이며, 안정적인 재현에는 커밋 SHA 또는 출시한 태그를 사용합니다.

## 에이전트·자동화

```bash
oss week --list --json
oss week 6 --json
oss week 4 --makeup --json
oss week 6 --checklist
oss now --json
oss guide list --json
oss guide search "회의록 제출" --json
oss guide show 12-minutes#section-12-1 --json
oss format --list --json
oss format minutes --output 회의록.md --json
```

JSON은 `schema_version`, `ok`, `data`, `error`를 가진 단일 객체입니다. 문서·검색·양식에는 원문 파일·페이지·앵커·SHA-256·근거 링크가 포함됩니다. 정상 종료는 0, 잘못된 요청·파일 오류는 2입니다. 검색은 공백으로 나눈 단어가 같은 줄에 모두 있는 결과를 반환하며 `--limit`으로 표시 수를 조절합니다.

조회 명령은 추가 입력을 요구하지 않습니다. `oss`만 실행하면 터미널에서는 첫 화면을 열고, 파이프 등 터미널이 아닌 환경에서는 명령 안내를 출력합니다. `oss browse`로도 TUI를 열 수 있습니다. `oss now`는 가장 가까운 제출 마감을 보여주며 `--date YYYY-MM-DD`로 기준일을 바꿀 수 있습니다. 실제 제출 완료 여부는 추적하지 않습니다. `--json`을 지정한 요청의 오류는 JSON으로 stdout에 출력하고, 일반 오류는 stderr로 출력합니다.

TUI에서는 Tab/Shift+Tab으로 다음/이전 영역으로 이동하면 아래 힌트가 현재 항목에 맞게 바뀝니다. 주차·분류 선택 상자는 Enter/Space로 가능한 값 목록을 펼치고 ↑↓로 골라 Enter로 적용합니다. Esc는 펼친 목록을 닫습니다. 메뉴·문서·양식 목록은 ↑↓와 Enter로 엽니다. 본문 영역에서는 ↑↓/PgUp/PgDn으로 스크롤합니다.

`F1`은 조작법과 검색 예시를 보여줍니다. Esc/F1로 도움말을 닫으면 원래 위치로 돌아갑니다. `/`로 전체 검색, Esc로 이전 문서, Ctrl+S로 양식·본문 저장, Ctrl+Q로 종료합니다. 회의록 이외의 양식은 전체 안내서에서 분류를 양식 저장으로 바꿔 선택합니다. 외부 링크는 주소를 안내하며 자동으로 웹에 접속하지 않습니다.

## 양식

`minutes`는 원문 부록 B의 제목·표 열을 보존하고 예시 사실과 체크 완료를 비운 작업용 양식입니다. 날짜·주차·팀명·참석자·진행 상황을 직접 채웁니다. `minutes-example`에는 원문 작성 예시가 그대로 있습니다. 나머지 기본 파일과 팀 약속 양식도 원문에서 추출하므로 예시 이름·프로젝트 이름을 실제 값으로 바꿔야 합니다.

저장은 지정한 파일만 생성하며 상위 폴더를 자동 생성하지 않습니다. 기존 파일은 기본적으로 덮어쓰지 않습니다. `--force`를 지정한 경우만 덮어씁니다. TUI 저장도 기본적으로 기존 파일을 보호합니다.

## 개발 구조와 검증

`guide.py`는 원문 읽기·검색·근거 조회, `templates.py`는 양식 추출·저장, `weeks.py`는 로드맵·개인 점검표의 주차 선택, `focus.py`는 가까운 제출 마감 조회입니다. `cli.py`와 `tui.py`가 같은 모듈을 함께 사용합니다. 관리 원문은 `docs/guide/` 한 곳이며 패키지 빌드 때 포함합니다. 원문 HTML 표는 TUI 표시 과정에서 Markdown 표로 바꿉니다. 저장된 원문은 수정하지 않습니다.

```bash
uv run pytest
python3 scripts/check_guide.py
uv build
```

완료 상태 저장·평가 자동화는 아직 구현하지 않았습니다. 현재 도구에서는 안내서의 주차별 일정·할 일·점검 기준을 조회할 수 있습니다.

확인 환경: Linux, Python 3.12, Textual 8.2.8. 설치한 wheel을 저장소 밖에서 실행해 검색·본문 조회·양식 저장을 확인했고, 키보드 탐색·링크 이동·뒤로 가기·기존 파일 보호를 테스트했습니다. 다른 운영체제의 터미널은 아직 검증하지 않았습니다.
