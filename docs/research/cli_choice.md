# CLI / TUI 후보 조사

## 목적

CLI/TUI 후보의 사용자 설치·입력 부담과 개발 복잡도를 비교한다.

## 비교

| 방식 | 외부 패키지 사용 | 개발 복잡도 |
|---|---|---|
| argparse | X | 낮음~중간 |
| typer | O | 낮음 |
| textual | O | 중간~높음 |

| 개발 복잡도 비교 항목 | argparse | Typer | Textual |
| - | - | - | - |
| 진입점 작성| 낮음 | 매우 낮음 | 중간 |
| 명령어 정의 | 중간 | 낮음 | 해당 없음 |
| argument/option 추가 | 중간  | 매우 낮음 | 중간 |
| subcommand 구성 | 중간 | 낮음 | 높음 |
| 화면 구성  | 없음 | 없음  | 필수 |
| 사용자 입력 처리 | 낮음 | 낮음 | 중간~높음 |
| 상태 관리 | 거의 없음 | 거의 없음 | 중요 |
| 레이아웃/CSS | 없음 | 없음 | 추가 필요 |
| 코드량 | 적음 | 가장 적은 편 | 가장 많음 |
| 배우기 쉬움 | 쉬움 | 쉬움 | 상대적으로 어려움 |
| 기능 확장 | CLI 수준에서는 좋음 | CLI 수준에서는 매우 좋음 | UI가 복잡해질수록 강함 |

|마크다운 파일 출력 |외부 패키지 사용 |
|---|---|
|파이썬 기본 print|X|
|rich|ㅇ|

### argparse
장점
- Python에 기본 포함되어 별도 설치가 필요 없다.
- CLI의 구조를 세밀하게 직접 제어할 수 있다.
- argument, option, flag, subcommand를 명확하게 정의할 수 있다.
- 간단한 CLI부터 상당히 복잡한 CLI까지 확장 가능하다.
- help와 잘못된 argument에 대한 오류 처리를 기본 제공한다.

단점
- 코드가 비교적 장황하다.
- parser를 직접 생성하고 수정해야 하므로 반복적인 코드가 생기기 쉽다.
- 함수 정의와 CLI 정의가 분리되는 경우가 많다.
- 타입 정보가 함수 시그니처에 자연스럽게 연결되는 Typer보다 작성 - 편의성이 떨어질 수 있다.

### typer
장점
- 코드가 짧고 읽기 쉽다.
- Python 타입 힌트를 적극적으로 활용한다.
- 함수 정의가 곧 CLI 명령어 정의처럼 보인다.
- command와 subcommand를 만들기 쉽다.
- help, completion 등 CLI 개발에 필요한 기능을 편하게 사용할 수 있다.
- calendar.py, checklist.py, templates.py 같은 모듈 분리가 자연스럽다.

단점
- 표준 라이브러리가 아니어서 설치가 필요하다.
- CLI 정의가 간단한 경우에는 편하지만, 아주 세밀한 동작을 직접 통제해야 하는 경우에는 underlying framework/API를 더 이해해야 할 수 있다.
- 타입 힌트와 decorator 중심 방식에 익숙하지 않으면 처음에는 구조가 낯설 수 있다.

### textual
- 터미널 안에서 마우스와 키보드를 사용하는 인터랙티브 UI를 만들 수 있다.
- Button, Input, Checkbox, MarkdownViewer, DataTable 등의 다양한 widget을 조합할 수 있다.
- 화면을 계속 유지하면서 상태를 변경할 수 있다.
- CLI보다 복잡하고 인터랙티브한 프로그램을 만들기 좋다.
- CSS와 layout 시스템을 이용해서 UI 구조를 세밀하게 구성할 수 있다.

단점
- 표준 라이브러리가 아니어서 설치가 필요하다.
- 초기 개발량이 가장 많다.
- UI layout, widget, event, state 등을 이해해야 한다.
- 프로그램이 커지면 화면 상태와 이벤트 흐름까지 관리해야 한다.

### rich ( 터미널 출력 )
rich를 사용해 출력할 수 있는 것
- 색상과 스타일이 적용된 텍스트
- Markdown
- 표
- 진행률 표시줄
- 트리 구조
- 소스 코드 문법 강조
- JSON의 보기 좋은 출력
- 예외 traceback의 가독성 향상

장점
- print보다 CLI의 터미널 출력을 보기 좋게 만들 수 있다

단점
- 표준 라이브러리가 아니어서 설치가 필요하다.
- 터미널 환경에 따라 다르게 출력될 수 있다.

## 공식 문서
typer: https://typer.tiangolo.com/
textual: https://textual.textualize.io/
rich: https://rich.readthedocs.io/