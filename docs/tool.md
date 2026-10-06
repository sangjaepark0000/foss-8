# OSS 안내서 도구

전체 안내서 탐색·검색·양식 저장을 오프라인으로 사용할 수 있습니다. TUI와 CLI는 같은 원문을 읽습니다. 원문과 foss-8의 팀 결정은 구분해서 표시합니다.

## 지금 실행

```bash
uv run oss browse
uv run oss guide search 회의록
uv run oss guide show minutes --format text
uv run oss format minutes --output 회의록.md
```

또는 `pip install -r requirements.txt` 후 `python main.py browse`로 실행합니다.

## 설치

uv가 준비된 환경에서, 이 브랜치를 설치할 수 있습니다.

```bash
uv tool install git+https://github.com/sangjaepark0000/foss-8@feature/guide-tool
oss browse
```

Git 소스 설치에는 Git도 필요합니다. 설치 후에는 저장소 클론·로그인·API 토큰·초기 설정이 필요하지 않습니다. 안내서 전체와 양식은 패키지에 함께 포함됩니다. 공개용 안내서는 2026-2 v1.3이며 다른 학기 일정으로 자동 변경하지 않습니다.

개발용 로컬 설치: `uv tool install .`. 업데이트는 같은 소스로 `uv tool install --reinstall .`를 실행합니다. 브랜치 설치는 개발 버전이며, 안정적인 재현에는 커밋 SHA 또는 출시한 태그를 사용합니다.

## 에이전트·자동화

```bash
oss guide list --json
oss guide search "회의록 제출" --json
oss guide show 12-minutes#section-12-1 --json
oss format --list --json
oss format minutes --output 회의록.md --json
```

JSON은 `schema_version`, `ok`, `data`, `error`를 가진 단일 객체입니다. 문서·검색·양식에는 원문 파일·페이지·앵커·SHA-256·근거 링크가 포함됩니다. 정상 종료는 0, 잘못된 요청·파일 오류는 2입니다. 검색은 공백으로 나눈 단어가 같은 줄에 모두 있는 결과를 반환하며 `--limit`으로 표시 수를 조절합니다.

조회 명령은 추가 입력을 요구하지 않습니다. `oss`만 실행하면 명령 안내가 나오며, TUI는 `oss browse`로 명시적으로 엽니다. `--json`을 지정한 요청의 오류는 JSON으로 stdout에 출력하고, 일반 오류는 stderr로 출력합니다.

TUI에서는 분류를 선택하고 목록의 Enter로 본문을 엽니다. `/`로 전체 검색, Tab으로 영역 이동, Esc로 이전 문서, Ctrl+S로 양식·본문 저장, Ctrl+Q로 종료합니다. 외부 링크는 주소를 안내하며 자동으로 웹에 접속하지 않습니다.

## 양식

`minutes`는 원문 부록 B의 제목·표 열을 보존하고 예시 사실과 체크 완료를 비운 작업용 양식입니다. 날짜·주차·팀명·참석자·진행 상황을 직접 채웁니다. `minutes-example`에는 원문 작성 예시가 그대로 있습니다. 나머지 기본 파일과 팀 약속 양식도 원문에서 추출하므로 예시 이름·프로젝트 이름을 실제 값으로 바꿔야 합니다.

저장은 지정한 파일만 생성하며 상위 폴더를 자동 생성하지 않습니다. 기존 파일은 기본적으로 덮어쓰지 않습니다. `--force`를 지정한 경우만 덮어씁니다. TUI 저장도 기본적으로 기존 파일을 보호합니다.

## 개발 구조와 검증

`guide.py`는 원문 읽기·검색·근거 조회, `templates.py`는 양식 추출·저장입니다. `cli.py`와 `tui.py`가 이 두 모듈을 함께 사용합니다. 관리 원문은 `docs/guide/` 한 곳이며 패키지 빌드 때 포함합니다. 원문 HTML 표는 TUI 표시 과정에서 Markdown 표로 바꿉니다. 저장된 원문은 수정하지 않습니다.

```bash
uv run pytest
python3 scripts/check_guide.py
uv build
```

캘린더 계산·완료 상태 저장·평가 자동화는 아직 구현하지 않았습니다. 현재 도구에서는 관련 안내서와 점검 기준을 조회할 수 있습니다.

확인 환경: Linux, Python 3.12, Textual 8.2.8. 설치한 wheel을 저장소 밖에서 실행해 검색·본문 조회·양식 저장을 확인했고, 키보드 탐색·링크 이동·뒤로 가기·기존 파일 보호를 테스트했습니다. 다른 운영체제의 터미널은 아직 검증하지 않았습니다.
