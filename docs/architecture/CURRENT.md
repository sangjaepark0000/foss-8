# foss-8 현재 구현 다이어그램

[전체 지도](README.md) · [목표 설계](TARGET.md) · [차이와 이동 순서](COMPARISON.md)

기준: 2026-11-15 원격 조회. 브랜치별 커밋은 [manifest.json](manifest.json)에 고정했다. 노드·호출·저장 경로는 코드에서 확인했으며 실제 사용자의 개인 상태 파일은 조사하지 않았다.

## 현재 저장소의 세 구현 범위

어느 브랜치의 기능을 현재 구현이라고 부르는가?

```mermaid
flowchart TB
    repo["foss-8 저장소"]
    repo --> mainBranch["main · 8e6ea27"]
    repo --> protoBranch["prototype · 8fc2ae6"]
    repo --> toolBranch["feature/guide-tool · d1a5a39"]
    mainBranch --> mainProduct["CLI · 서식 · 활동 JSON · 회의록 PDF · 파일 검사"]
    protoBranch --> protoProduct["curses TUI · 주차 작업 · 수동 완료 · 주간 활동 집계 · 팀 설정"]
    toolBranch --> toolProduct["Textual TUI · 안내서 탐색 · 검색 · 양식 저장"]
    proposal["이 대화의 목표 설계 · 미구현"] -.-> mainProduct
    proposal -.-> protoProduct
    proposal -.-> toolProduct
```

main, prototype, guide-tool은 서로 다른 실행 제품이다. 이 문서는 셋을 합쳐 이미 구현된 하나의 앱처럼 표시하지 않는다.

범위·주의: 세 선은 기능 범위의 분기이며 Git ancestry·병합 관계를 뜻하지 않는다. 원격 조회일은 2026-11-15이다.

[SVG 크게 보기](rendered/00-repository-scopes.svg) · [Mermaid 원본](diagrams/00-repository-scopes.mmd)

구현 근거:

- [main: foss8/cli.py:23 · parser](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/cli.py#L23)
- [prototype: foss8/cli.py:23 · parser](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/cli.py#L23)
- [guide-tool: foss8/cli.py:30 · parser](https://github.com/sangjaepark0000/foss-8/blob/d1a5a39c963e6ef1f38f2341e3c42259e1ae12a6/foss8/cli.py#L30)

## main의 실제 모듈과 의존성

현재 CLI 기능은 어떤 모듈을 호출하는가?

```mermaid
flowchart LR
    entry["main.py / python -m foss8"] --> cli["cli.py · main"]
    cli --> templates["templates.py · 서식 추출"]
    cli --> minutes["minutes.py · 팀 정보와 회의록 조립"]
    cli --> pdf["minutes_pdf.py · PDF 변환"]
    cli --> activity["activity.py · 활동 수집·근거 문장"]
    cli --> check["check.py · 기준 표·파일 검사"]
    cli --> weeks["weeks.py · 로드맵 조회"]
    minutes --> templates
    pdf --> minutes
    templates --> catalog["guide.py · Catalog"]
    minutes --> catalog
    check --> catalog
    weeks --> catalog
    catalog --> docs[("docs/guide · Markdown와 source-map")]
    activity --> gh["gh api → GitHub"]
    pdf --> browser["Chrome / Chromium"]
    minutes --> local[("team.json / Git remote / README")]
```

CLI main()에 명령 분기와 조립이 모인다. 공통 원문은 Catalog가 읽고, 일정·평가·서식이 각자 표를 해석한다.

범위·주의: main에는 TUI 실행 분기가 없다. Catalog의 검색 메서드가 존재하는 것과 CLI에 guide search 명령이 노출되는 것은 별개다.

[SVG 크게 보기](rendered/01-main-modules.svg) · [Mermaid 원본](diagrams/01-main-modules.mmd)

구현 근거:

- [main: foss8/cli.py:68 · main](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/cli.py#L68)
- [main: foss8/guide.py:115 · Catalog](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/guide.py#L115)
- [main: foss8/minutes.py:124 · load_config](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/minutes.py#L124)
- [main: foss8/minutes_pdf.py:141 · export](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/minutes_pdf.py#L141)

## main의 실제 정보 모델

문서에서 추출한 정보가 어떤 형태로 기능별로 흘러가는가?

```mermaid
flowchart TB
    pdf["원문 PDF와 source-map"] --> document["Document · id / title / markdown / pages"]
    document --> roadmap["로드맵 dict · 주차 / 수업일 / tasks / turnin"]
    document --> cycle["Cycle · period_id / WEEK / 기록기간 / due_at"]
    document --> result["결과물 기준 dict · 배점 / 부분점수 / status=미확인"]
    document --> template["서식 dict · content / source"]
    config["팀 정보 dict · name / repository / members"] --> draft["회의록·보고서 Markdown"]
    cycle --> draft
    roadmap --> draft
    template --> draft
    evidence["활동 JSON · 사람별 categories / error / links"] --> draft
    draft --> submission["제출용 PDF"]
    result --> terminal["터미널 표시"]
    files["파일 존재 검사 결과"] --> terminal
```

Document와 Cycle은 명시적 타입이지만 활동·평가·주차는 대부분 기능별 dict이다. 공통 RequirementInstance나 판정 이력 모델은 없다.

범위·주의: 개념적 데이터 흐름도다. 저장된 관계형 DB나 이 이름의 테이블이 있다는 뜻이 아니다.

[SVG 크게 보기](rendered/02-main-information-model.svg) · [Mermaid 원본](diagrams/02-main-information-model.mmd)

구현 근거:

- [main: foss8/guide.py:108 · Document](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/guide.py#L108)
- [main: foss8/minutes.py:21 · Cycle](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/minutes.py#L21)
- [main: foss8/weeks.py:10 · roadmap](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/weeks.py#L10)
- [main: foss8/check.py:38 · load_result_items](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/check.py#L38)
- [main: foss8/activity.py:30 · collect](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/activity.py#L30)

## main의 현재 사용자 흐름

사용자는 현재 무엇을 입력하고 어떤 결과를 받는가?

```mermaid
flowchart TB
    start["python main.py"] --> choose{"하위 명령"}
    choose -->|"없음"| banner["도구 이름 출력 후 종료"]
    choose -->|"week"| period["입력 주차 또는 다가오는 수업 선택"]
    period --> list["할 일과 제출 문구 출력"]
    choose -->|"check"| criteria["결과물 기준은 미확인으로 출력"]
    criteria --> files["로컬 필수 파일 존재 검사"]
    choose -->|"activity"| collect["저장소·기간·팀원으로 수집"]
    collect --> activityFile["활동 JSON 파일"]
    choose -->|"format"| draft["빈 서식 또는 팀·기간을 채운 초안"]
    activityFile -.->|"사용자가 --activity로 전달"| draft
    draft --> edit["사용자가 실제 내용을 작성"]
    edit --> pdf["format minutes --pdf 로 PDF 생성"]
    pdf --> submit["사용자가 LMS 또는 이메일 제출"]
```

문서 조회·활동 파일 생성·문서 작성·PDF 변환이 명령별로 나뉘며, 활동 JSON 전달과 실제 제출 확인은 사용자가 이어 붙인다.

범위·주의: 파일 생성 성공은 LMS 제출 성공이나 규칙 충족으로 저장되지 않는다. main의 week는 현재 학사 주차보다 가까운 이후 수업일을 고른다.

[SVG 크게 보기](rendered/03-main-cli-flow.svg) · [Mermaid 원본](diagrams/03-main-cli-flow.mmd)

구현 근거:

- [main: foss8/cli.py:23 · parser](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/cli.py#L23)
- [main: foss8/cli.py:68 · main](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/cli.py#L68)
- [main: foss8/weeks.py:38 · get_this_week](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/weeks.py#L38)

## main의 활동 수집·문서 생성 시퀀스

한 번의 활동 수집과 회의록 생성에서 무엇이 자동이고 무엇이 수동인가?

```mermaid
sequenceDiagram
    actor user as 사용자
    participant cli as CLI
    participant config as minutes.load_config
    participant collector as activity.collect
    participant gh as gh / GitHub
    participant disk as 로컬 파일
    user->>cli: activity --repo --start --end -o 활동.json
    cli->>config: 팀 정보 읽기
    config-->>cli: members
    cli->>collector: collect(repo, start, end, members)
    collector->>gh: 브랜치·커밋·PR·리뷰·이슈·릴리스·회의록 조회
    gh-->>collector: 페이지 또는 항목별 오류
    collector-->>cli: 사람별 링크와 오류
    cli->>disk: 활동 JSON 저장
    user->>cli: format minutes --activity 활동.json -o 회의록.md
    cli->>config: 제출 회차와 팀 정보로 초안 작성
    disk-->>cli: 활동 JSON
    cli->>disk: 근거 초안을 붙인 Markdown 저장
    user->>disk: 실제 회의 내용 작성
    user->>cli: format minutes --pdf 회의록.md
    cli->>disk: Chrome 변환 후 PDF 저장
```

수집 실패는 항목의 error로 보존한다. 결과는 활동 근거 초안이며 평가 엔진으로 전달되지는 않는다.

[SVG 크게 보기](rendered/04-main-evidence-document-sequence.svg) · [Mermaid 원본](diagrams/04-main-evidence-document-sequence.mmd)

구현 근거:

- [main: foss8/activity.py:30 · collect](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/activity.py#L30)
- [main: foss8/cli.py:68 · main](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/cli.py#L68)
- [main: foss8/minutes.py:202 · draft](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/minutes.py#L202)
- [main: foss8/minutes_pdf.py:141 · export](https://github.com/sangjaepark0000/foss-8/blob/8e6ea27b07c7f287aa12d3b927ba3e9acae23732/foss8/minutes_pdf.py#L141)

## prototype의 실제 모듈 구조

키보드 TUI의 화면·저장·수집은 어디에서 조립되는가?

```mermaid
flowchart LR
    cli["cli.py"] --> weeks["weeks.py · 선택·치환·텍스트 출력"]
    cli --> team["team.py · 검증·설정 저장"]
    cli --> minutes["minutes.py / minutes_pdf.py"]
    weeks --> data[("data/weeks.json · 주차 작업 트리")]
    weeks --> tui["tui.py · curses App"]
    tui --> team
    tui --> discovery["discovery.py · 후보 읽기·비교"]
    tui --> progress["progress.py · 수동 완료"]
    tui --> assessments["assessments.py · 주간 기준·횟수"]
    tui --> github["github_activity.py · 주간 집계"]
    tui --> minutes
    github --> assessments
    github --> discovery
    discovery --> external["로컬 문서·Git·gh / GitHub"]
    github --> external
    team --> state[(".foss8 · team / progress / assessments JSON")]
    progress --> state
    assessments --> state
    design["data/course-project.json · 설계 초안"] -.->|"실행 경로의 입력으로 미사용"| data
```

tui.App이 화면 상태와 팀 설정, 활동 수집 스레드, 저장 갱신을 함께 조정한다. weeks.py에는 데이터 선택과 텍스트 렌더링·TUI 진입이 함께 있다.

범위·주의: course-project.json은 문서화된 설계 초안이다. 점선은 실행 연결이 없다는 표시다. 현재 check 명령은 준비중을 출력한다.

[SVG 크게 보기](rendered/05-prototype-modules.svg) · [Mermaid 원본](diagrams/05-prototype-modules.mmd)

구현 근거:

- [prototype: foss8/weeks.py:268 · run](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/weeks.py#L268)
- [prototype: foss8/tui.py:100 · App](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L100)
- [prototype: foss8/tui.py:297 · start_activity](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L297)
- [prototype: foss8/team.py:126 · save](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/team.py#L126)
- [prototype: foss8/github_activity.py:32 · collect](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/github_activity.py#L32)

## prototype의 현재 데이터·식별 모델

완료 표시와 활동 횟수는 무엇을 키로 저장되는가?

```mermaid
flowchart TB
    team["team.json · repository / me / members / roles / approved_changes"]
    scope["context · repository와 me 또는 local"]
    team --> scope
    tree["weeks.json · period / tasks / children / details / evaluation"]
    tree --> task["task.id와 progress_period"]
    task --> mark["progress.json · context → 작업 키 → completed"]
    scope --> mark
    tree --> period["화~월 period.start / end"]
    constants["CRITERIA 상수 · commits / issues / prs"] --> bundle["WeeklyAssessment · 기간과 counts"]
    period --> bundle
    scope --> counts["assessments.json · context → 시작일 → counts"]
    counts --> bundle
    github["GitHub Result · counts / evidence / errors"] --> counts
    manual["횟수 수동 입력"] --> counts
    counts --> metadata["sources / evidence / synced_at / updated_at"]
    carry["바로 다음 주의 이월 항목"] -->|"같은 작업 키 재사용"| task
```

주차별 화면 데이터와 수동 완료, 주간 횟수는 분리되어 있다. 다만 기준·작업의 정의는 트리 JSON·코드 상수·원문에 나뉘고 판정 스냅샷은 없다.

범위·주의: Task 체크는 사용자의 수동 표시다. WeeklyAssessment.status는 주간 횟수 상태이며 학기 점수나 LMS 제출 판정이 아니다. 서로 다른 집계 구간을 자동 재배분하지 않는다.

[SVG 크게 보기](rendered/06-prototype-information-model.svg) · [Mermaid 원본](diagrams/06-prototype-information-model.mmd)

구현 근거:

- [prototype: foss8/weeks.py:11 · load](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/weeks.py#L11)
- [prototype: foss8/progress.py:8 · context](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/progress.py#L8)
- [prototype: foss8/progress.py:45 · Progress](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/progress.py#L45)
- [prototype: foss8/assessments.py:58 · WeeklyAssessment](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/assessments.py#L58)
- [prototype: foss8/assessments.py:126 · Store](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/assessments.py#L126)

## prototype의 현재 사용자 흐름

주차 선택부터 완료 표시·활동 집계·회의록 작성까지 어떻게 이동하는가?

```mermaid
flowchart TB
    entry["main.py 또는 week"] --> tty{"TTY이며 대화형 요청인가"}
    tty -->|"아니오"| text["텍스트 또는 JSON 조회"]
    tty -->|"예"| week["오늘의 화~월 학사 주차 선택"]
    week --> tabs{"curses 화면"}
    tabs --> tasks["할 일 · 주차 작업과 상세"]
    tabs --> eval["평가 · 주간 실적과 설명"]
    tabs --> settings["팀 설정 · 사람·역할·승인"]
    tasks -->|"Space"| done["수동 완료 표시·취소"]
    tasks -->|"회의록 Enter"| minutes["초안 만들기 / PDF 만들기"]
    tasks -->|"횟수 항목"| edit["Space·Backspace·Enter로 횟수 수정"]
    eval --> edit
    settings --> detect["로컬·GitHub 후보 검토·적용"]
    settings --> save["설정 저장"]
    save --> sync["현재 진행 주차 GitHub 백그라운드 집계"]
    tasks -->|"r"| sync
    eval -->|"r"| sync
    sync --> eval
    tabs -->|"기간 선택"| week
```

진입점과 작업 목록의 중심이 선택한 주차다. 사용자는 할 일·평가·팀 설정 탭을 오가며 서로 다른 종류의 상태를 편집한다.

범위·주의: 할 일의 개인 담당 필터는 아직 연결되지 않았다. 바로 다음 주 이월과 모든 과거 미완료를 계속 보여주는 backlog는 다르다.

[SVG 크게 보기](rendered/07-prototype-user-flow.svg) · [Mermaid 원본](diagrams/07-prototype-user-flow.mmd)

구현 근거:

- [prototype: foss8/weeks.py:268 · run](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/weeks.py#L268)
- [prototype: foss8/tui.py:164 · items](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L164)
- [prototype: foss8/tui.py:591 · handle](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L591)
- [prototype: foss8/tui.py:364 · minutes_action](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L364)

## prototype의 현재 집계 상태 전이

수동 수정과 GitHub 갱신·실패가 만날 때 어떻게 처리되는가?

```mermaid
stateDiagram-v2
    [*] --> Idle
    state "대기" as Idle
    state "집계 중" as Fetching
    state "응답 폐기" as Discarded
    state "성공 항목 저장" as Saved
    state "일부 실패·기존 값 유지" as Partial
    state "횟수 수동 수정" as Manual
    Idle --> Fetching: 설정 충족·현재 진행 주차·아직 시도 안 함 또는 r
    Fetching --> Discarded: 수집 중 config_revision 변경
    Fetching --> Saved: revision 일치·성공 counts 있음
    Fetching --> Partial: 항목별 errors
    Saved --> Idle: 화면 갱신
    Partial --> Idle: 오류 안내
    Discarded --> Idle: r 재집계 안내
    Idle --> Manual: 횟수 입력·증감
    Manual --> Idle: manual 출처로 저장
    Idle --> Fetching: r 재시도
```

설정 revision이 바뀐 응답은 버린다. 성공한 항목만 갱신하며 실패 항목의 기존 값은 유지한다. 수동 횟수는 다음 성공 집계에서 바뀔 수 있다.

범위·주의: 구현에서 보이는 동작을 추출한 상태도이며 실제 Enum 선언은 아니다. 성공과 항목별 오류는 한 응답에 공존할 수 있다.

[SVG 크게 보기](rendered/08-prototype-sync-state.svg) · [Mermaid 원본](diagrams/08-prototype-sync-state.mmd)

구현 근거:

- [prototype: foss8/tui.py:297 · start_activity](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L297)
- [prototype: foss8/tui.py:319 · poll_activity](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/tui.py#L319)
- [prototype: foss8/assessments.py:150 · save](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/assessments.py#L150)
- [prototype: foss8/github_activity.py:32 · collect](https://github.com/sangjaepark0000/foss-8/blob/8fc2ae6e6bf3e340067887fbeeb023ec7af65931/foss8/github_activity.py#L32)
