"""Generate the source-backed architecture atlas. Rendering is a separate step."""
from __future__ import annotations

import html
import json
from pathlib import Path
import textwrap

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/architecture'
SHAS = {
    'main': '8e6ea27b07c7f287aa12d3b927ba3e9acae23732',
    'prototype': '8fc2ae6e6bf3e340067887fbeeb023ec7af65931',
    'guide-tool': 'd1a5a39c963e6ef1f38f2341e3c42259e1ae12a6',
}
INDEX = json.loads((OUT / 'source-index.json').read_text())
DIAGRAMS = []


def add(slug, title, group, question, conclusion, syntax, sources=(), caveat=''):
    DIAGRAMS.append(dict(slug=slug, title=title, group=group, question=question,
                         conclusion=conclusion, syntax=textwrap.dedent(syntax).strip() + '\n',
                         sources=list(sources), caveat=caveat))


add('00-repository-scopes', '현재 저장소의 세 구현 범위', 'current',
    '어느 브랜치의 기능을 현재 구현이라고 부르는가?',
    'main, prototype, guide-tool은 서로 다른 실행 제품이다. 이 문서는 셋을 합쳐 이미 구현된 하나의 앱처럼 표시하지 않는다.', r'''
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
    ''', [('main', 'foss8/cli.py', 'parser'), ('prototype', 'foss8/cli.py', 'parser'), ('guide-tool', 'foss8/cli.py', 'parser')],
    '세 선은 기능 범위의 분기이며 Git ancestry·병합 관계를 뜻하지 않는다. 원격 조회일은 2026-11-15이다.')

add('01-main-modules', 'main의 실제 모듈과 의존성', 'current',
    '현재 CLI 기능은 어떤 모듈을 호출하는가?',
    'CLI main()에 명령 분기와 조립이 모인다. 공통 원문은 Catalog가 읽고, 일정·평가·서식이 각자 표를 해석한다.', r'''
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
    ''', [('main', 'foss8/cli.py', 'main'), ('main', 'foss8/guide.py', 'Catalog'), ('main', 'foss8/minutes.py', 'load_config'), ('main', 'foss8/minutes_pdf.py', 'export')],
    'main에는 TUI 실행 분기가 없다. Catalog의 검색 메서드가 존재하는 것과 CLI에 guide search 명령이 노출되는 것은 별개다.')

add('02-main-information-model', 'main의 실제 정보 모델', 'current',
    '문서에서 추출한 정보가 어떤 형태로 기능별로 흘러가는가?',
    'Document와 Cycle은 명시적 타입이지만 활동·평가·주차는 대부분 기능별 dict이다. 공통 RequirementInstance나 판정 이력 모델은 없다.', r'''
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
    ''', [('main', 'foss8/guide.py', 'Document'), ('main', 'foss8/minutes.py', 'Cycle'), ('main', 'foss8/weeks.py', 'roadmap'), ('main', 'foss8/check.py', 'load_result_items'), ('main', 'foss8/activity.py', 'collect')],
    '개념적 데이터 흐름도다. 저장된 관계형 DB나 이 이름의 테이블이 있다는 뜻이 아니다.')

add('03-main-cli-flow', 'main의 현재 사용자 흐름', 'current',
    '사용자는 현재 무엇을 입력하고 어떤 결과를 받는가?',
    '문서 조회·활동 파일 생성·문서 작성·PDF 변환이 명령별로 나뉘며, 활동 JSON 전달과 실제 제출 확인은 사용자가 이어 붙인다.', r'''
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
    ''', [('main', 'foss8/cli.py', 'parser'), ('main', 'foss8/cli.py', 'main'), ('main', 'foss8/weeks.py', 'get_this_week')],
    '파일 생성 성공은 LMS 제출 성공이나 규칙 충족으로 저장되지 않는다. main의 week는 현재 학사 주차보다 가까운 이후 수업일을 고른다.')

add('04-main-evidence-document-sequence', 'main의 활동 수집·문서 생성 시퀀스', 'current',
    '한 번의 활동 수집과 회의록 생성에서 무엇이 자동이고 무엇이 수동인가?',
    '수집 실패는 항목의 error로 보존한다. 결과는 활동 근거 초안이며 평가 엔진으로 전달되지는 않는다.', r'''
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
    ''', [('main', 'foss8/activity.py', 'collect'), ('main', 'foss8/cli.py', 'main'), ('main', 'foss8/minutes.py', 'draft'), ('main', 'foss8/minutes_pdf.py', 'export')])

add('05-prototype-modules', 'prototype의 실제 모듈 구조', 'current',
    '키보드 TUI의 화면·저장·수집은 어디에서 조립되는가?',
    'tui.App이 화면 상태와 팀 설정, 활동 수집 스레드, 저장 갱신을 함께 조정한다. weeks.py에는 데이터 선택과 텍스트 렌더링·TUI 진입이 함께 있다.', r'''
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
    ''', [('prototype', 'foss8/weeks.py', 'run'), ('prototype', 'foss8/tui.py', 'App'), ('prototype', 'foss8/tui.py', 'start_activity'), ('prototype', 'foss8/team.py', 'save'), ('prototype', 'foss8/github_activity.py', 'collect')],
    'course-project.json은 문서화된 설계 초안이다. 점선은 실행 연결이 없다는 표시다. 현재 check 명령은 준비중을 출력한다.')

add('06-prototype-information-model', 'prototype의 현재 데이터·식별 모델', 'current',
    '완료 표시와 활동 횟수는 무엇을 키로 저장되는가?',
    '주차별 화면 데이터와 수동 완료, 주간 횟수는 분리되어 있다. 다만 기준·작업의 정의는 트리 JSON·코드 상수·원문에 나뉘고 판정 스냅샷은 없다.', r'''
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
    ''', [('prototype', 'foss8/weeks.py', 'load'), ('prototype', 'foss8/progress.py', 'context'), ('prototype', 'foss8/progress.py', 'Progress'), ('prototype', 'foss8/assessments.py', 'WeeklyAssessment'), ('prototype', 'foss8/assessments.py', 'Store')],
    'Task 체크는 사용자의 수동 표시다. WeeklyAssessment.status는 주간 횟수 상태이며 학기 점수나 LMS 제출 판정이 아니다. 서로 다른 집계 구간을 자동 재배분하지 않는다.')

add('07-prototype-user-flow', 'prototype의 현재 사용자 흐름', 'current',
    '주차 선택부터 완료 표시·활동 집계·회의록 작성까지 어떻게 이동하는가?',
    '진입점과 작업 목록의 중심이 선택한 주차다. 사용자는 할 일·평가·팀 설정 탭을 오가며 서로 다른 종류의 상태를 편집한다.', r'''
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
    ''', [('prototype', 'foss8/weeks.py', 'run'), ('prototype', 'foss8/tui.py', 'items'), ('prototype', 'foss8/tui.py', 'handle'), ('prototype', 'foss8/tui.py', 'minutes_action')],
    '할 일의 개인 담당 필터는 아직 연결되지 않았다. 바로 다음 주 이월과 모든 과거 미완료를 계속 보여주는 backlog는 다르다.')

add('08-prototype-sync-state', 'prototype의 현재 집계 상태 전이', 'current',
    '수동 수정과 GitHub 갱신·실패가 만날 때 어떻게 처리되는가?',
    '설정 revision이 바뀐 응답은 버린다. 성공한 항목만 갱신하며 실패 항목의 기존 값은 유지한다. 수동 횟수는 다음 성공 집계에서 바뀔 수 있다.', r'''
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
    ''', [('prototype', 'foss8/tui.py', 'start_activity'), ('prototype', 'foss8/tui.py', 'poll_activity'), ('prototype', 'foss8/assessments.py', 'save'), ('prototype', 'foss8/github_activity.py', 'collect')],
    '구현에서 보이는 동작을 추출한 상태도이며 실제 Enum 선언은 아니다. 성공과 항목별 오류는 한 응답에 공존할 수 있다.')

add('09-target-domain', '목표 도메인: 기준을 적용하고 근거로 설명하기', 'target',
    '사용자가 원하는 점검을 표현하려면 어떤 개념을 분리해야 하는가?',
    '핵심은 주차 트리에서 기준을 복사하는 대신, 기준 정의를 사람·팀·기간에 적용해 생성한 적용 건에 증거와 판정을 연결하는 것이다.', r'''
    flowchart LR
        source["원문·버전·절·쪽수"] --> rule["기준 정의"]
        approval["승인된 팀 변경·근거"] --> binding["적용 정책 확정"]
        rule --> binding
        context["프로젝트·대상 개인 또는 팀"] --> binding
        period["활동 구간·면제·마감"] --> binding
        binding --> obligation["적용 건 · 안정 ID"]
        observation["GitHub 관측·수동 확인·제출 증거"] --> snapshot["증거 스냅샷·수집 범위"]
        obligation --> assessment["판정 · 이유·증거·버전"]
        snapshot --> assessment
        obligation --> action["수행할 작업·담당·선행 조건"]
        assessment --> views["지금 할 일·주차·개인·제출물별 뷰"]
        action --> views
    ''', caveat='이 대화에서 제안한 미구현 모델이다. 승인된 3인·3기능 변경이 곧 배점의 비례 환산을 뜻하지 않는다.')

add('10-target-erd', '목표 ERD: 적용 건·증거·판정의 식별', 'target',
    '과거 판정을 재현하고 여러 뷰에서 같은 기준을 보려면 어떤 관계가 필요한가?',
    '기준과 적용 건을 분리하고 판정은 사용한 정책·증거 버전을 고정한다. 기간 변경이나 재수집으로 과거 판정을 덮어쓰지 않는다.', r'''
    erDiagram
        SOURCE_REVISION ||--o{ RULE_SET : supports
        RULE_SET ||--|{ REQUIREMENT : defines
        PROJECT ||--o{ APPROVED_CHANGE : records
        PROJECT ||--|{ SUBJECT : scopes
        REQUIREMENT ||--o{ OBLIGATION : instantiates
        SUBJECT ||--o{ OBLIGATION : owes
        PERIOD ||--o{ OBLIGATION : bounds
        OBLIGATION ||--o{ ACTION : requires
        OBLIGATION ||--o{ ARTIFACT : produces
        ARTIFACT ||--o{ SUBMISSION : records
        OBLIGATION ||--o{ ASSESSMENT : evaluated
        EVIDENCE_BATCH ||--o{ EVIDENCE : contains
        ASSESSMENT ||--o{ ASSESSMENT_EVIDENCE : cites
        EVIDENCE ||--o{ ASSESSMENT_EVIDENCE : supports
        APPROVED_CHANGE ||--o{ OBLIGATION : adjusts
        SOURCE_REVISION {
            string id PK
            string sha256
            string citation
        }
        RULE_SET {
            string id PK
            string version
        }
        REQUIREMENT {
            string id PK
            string ruleset_id FK
            string predicate
            string source_locator
        }
        PROJECT {
            string id PK
            string repository
        }
        SUBJECT {
            string id PK
            string project_id FK
            string kind
            string external_identity
        }
        PERIOD {
            string id PK
            datetime starts_at
            datetime ends_at_exclusive
            string timezone
        }
        OBLIGATION {
            string id PK
            string requirement_id FK
            string subject_id FK
            string period_id FK
            datetime due_at
            string policy_digest
        }
        APPROVED_CHANGE {
            string id PK
            string project_id FK
            string scope
            string approval_source
        }
        ACTION {
            string id PK
            string obligation_id FK
            string owner_subject_id
            string execution_state
        }
        ARTIFACT {
            string id PK
            string obligation_id FK
            string revision
            string path
        }
        SUBMISSION {
            string id PK
            string artifact_id FK
            string destination
            datetime submitted_at
            string confirmation_evidence_id
        }
        EVIDENCE_BATCH {
            string id PK
            string coverage
            string collection_status
            datetime fetched_at
        }
        EVIDENCE {
            string id PK
            string batch_id FK
            string source_key
            datetime occurred_at
        }
        ASSESSMENT {
            string id PK
            string obligation_id FK
            string policy_digest
            string evidence_snapshot_digest
            datetime evaluated_at
            string verdict
            string reasons
        }
        ASSESSMENT_EVIDENCE {
            string assessment_id FK
            string evidence_id FK
        }
    ''', caveat='개념 ERD이며 DB 선택이나 최종 물리 스키마를 확정하지 않는다. predicate·coverage는 검증된 구조여야 하며 사용자 문자열을 eval하지 않는다. 관계 일부와 보조 조인 테이블은 가독성을 위해 생략했다.')

add('11-target-modules', '목표 모듈과 네 레이어', 'target',
    'CLI와 TUI가 어떤 인터페이스를 공유해야 모델이 화면에 종속되지 않는가?',
    'UI는 요청·출력과 포커스를 담당하고 collect/check/explain이 조립을 담당한다. 판정 모듈은 관측 저장이나 터미널 조작 없이 결과를 반환한다.', r'''
    flowchart TB
        subgraph presentation["표현 · 같은 결과를 다른 방식으로 보기"]
            cli["CLI · 텍스트 / JSON"]
            tui["TUI · 선택 / 상세 / 근거"]
        end
        subgraph usage["사용 사례 · 입력 검증과 실행 조립"]
            query["조회 · now / week / explain"]
            collect["수집 · collect"]
            check["점검 · check"]
            artifact["문서 · draft / export / 제출 기록"]
        end
        subgraph domain["도메인 · 기준과 방법"]
            policy["기준·승인·기간 → 적용 건"]
            evaluator["적용 건·증거 → 판정·이유"]
            workflow["작업·산출물·제출 흐름"]
        end
        subgraph infrastructure["근거·저장 · 구체 구현"]
            sources["원문과 기준 파일"]
            store["프로젝트·증거·판정 저장"]
            github["GitHub 수집 어댑터"]
            local["수동 증거·파일 어댑터"]
            pdf["PDF 출력 어댑터"]
        end
        cli --> query
        cli --> collect
        cli --> check
        cli --> artifact
        tui --> query
        tui --> collect
        tui --> check
        tui --> artifact
        query --> store
        collect --> github
        collect --> local
        collect --> store
        check --> policy
        check --> evaluator
        check --> store
        policy --> sources
        artifact --> workflow
        artifact --> pdf
        artifact --> store
    ''', caveat='미구현 설계안. 단일 로컬 프로그램 내부의 모듈 관계다. 별도 웹 서버·백그라운드 데몬·마이크로서비스 배포를 요구하지 않는다.')

add('12-target-check-sequence', '목표 수집·점검·설명 시퀀스', 'target',
    '수집이 실패해도 사용자가 왜 확인이 필요한지 추적할 수 있는가?',
    'collect와 check는 분리한다. check는 고정된 증거 스냅샷으로 판정하고 explain은 같은 판정의 기준·이유·근거를 다시 읽는다.', r'''
    sequenceDiagram
        actor user as 사용자
        participant ui as CLI 또는 TUI
        participant use as 사용 사례 모듈
        participant collector as 수집 어댑터
        participant store as 기록 저장
        participant policy as 적용 정책
        participant eval as 판정 모듈
        user->>ui: collect(project, period)
        ui->>use: 수집 요청
        use->>collector: 대상·범위·작성자·시각
        collector-->>use: 관측과 범위별 성공·누락·오류
        use->>store: 새 evidence batch 저장
        use-->>ui: 수집 상태와 기존 증거의 최신성
        user->>ui: check(project, period)
        ui->>use: 점검 요청
        use->>policy: 기준 버전·승인·기간으로 적용 건 해석
        policy-->>use: 적용 건 또는 미확정 정책
        use->>store: 사용할 증거 스냅샷 읽기
        store-->>use: 증거와 coverage
        use->>eval: 적용 건·정책·증거·기준 시각
        eval-->>use: 결과·이유·미확정 사항
        use->>store: 판정과 사용 버전 저장
        use-->>ui: 판정 목록과 assessment_id
        user->>ui: explain(assessment_id)
        ui->>store: 판정·정책·근거 조회
        store-->>ui: 재현 가능한 설명
    ''', caveat='네트워크 자동 갱신을 check 내부에 숨기지 않는 초기 인터페이스안이다. collect 실패 시 이전 batch와 실패한 새 시도를 함께 보존한다.')

add('13-target-cli-flow', '목표 CLI의 작업 흐름', 'target',
    '명령을 외우는 사람과 자동화가 같은 도메인 작업을 수행할 수 있는가?',
    '프로젝트 문맥을 고른 뒤 조회·수집·점검·설명·문서 작업을 독립 명령으로 수행한다. 읽기 작업은 상태를 암묵적으로 변경하지 않는다.', r'''
    flowchart TB
        start["프로젝트 선택 또는 현재 폴더에서 문맥 확인"] --> read{"사용 목적"}
        read -->|"지금 할 일"| now["oss now / oss week"]
        read -->|"새 활동 기록"| collect["oss collect --period"]
        read -->|"기준 점검"| check["oss check --period"]
        read -->|"이유 확인"| explain["oss explain 판정ID"]
        read -->|"문서 작업"| draft["oss minutes draft / pdf"]
        collect --> evidence["수집 범위·성공·실패·최신성"]
        evidence --> check
        check --> result["충족·진행 중·미충족·확인 필요·해당 없음"]
        result --> explain
        explain --> action["부족한 작업·근거 보완·정책 확인"]
        draft --> submit["제출은 별도 수행·증거 기록"]
        now --> action
        action --> now
        read -->|"키보드 탐색"| tui["oss tui · 같은 조회·명령 사용"]
    ''', caveat='명령 이름은 제안이다. main의 기존 check와 prototype의 week 동작을 이미 바꿨다는 뜻이 아니다. 모든 CLI 결과에는 텍스트와 JSON 표현을 함께 설계한다.')

add('14-target-tui-flow', '목표 TUI: 사용자 목적에서 근거까지', 'target',
    '주차를 바꿔도 남은 작업·원래 기한·판정 근거를 잃지 않는가?',
    '첫 화면은 현재 실행 가능한 일·막힘·마감·이월을 보여준다. 주차는 여러 조회 축 중 하나이며 같은 적용 건을 계속 참조한다.', r'''
    flowchart TB
        context["프로젝트·개인·기준 시각 선택"] --> home["지금 · 실행 가능 / 막힘 / 기한 임박 / 이월"]
        home --> item["작업 또는 기준 선택"]
        item --> detail["상세 · 담당 / 원래 기한 / 다음 행동"]
        detail --> basis["원문·팀 승인·적용 정책"]
        detail --> evidence["증거·수집 범위·최신성"]
        detail --> assessment["판정 이유·부족한 것"]
        detail --> operation{"명시적 작업"}
        operation --> collect["다시 수집"]
        operation --> manual["수동 관측·정정 기록"]
        operation --> document["초안·PDF·제출 기록"]
        collect --> detail
        manual --> detail
        document --> detail
        home --> views["주차 / 개인·팀 / 제출물별 조회"]
        views -->|"동일한 적용 건"| item
        home --> settings["프로젝트 설정·미확정 정책"]
        settings --> context
    ''', caveat='텍스트 화면 이동 설계이며 완성된 TUI 스크린샷이 아니다. 사용자 체크, 수집 성공, 문서 생성, LMS 제출, 규칙 충족은 각각 별도의 표시다.')

add('15-target-submission-state', '목표 산출물·제출 상태', 'target',
    'PDF를 만들었다는 사실과 제출 완료·기한 준수를 어떻게 구분하는가?',
    '산출물 준비와 외부 제출 확인을 분리한다. 기한 준수는 제출 시각과 고정 마감의 비교값이며 상태를 되돌리는 조건이 아니다.', r'''
    stateDiagram-v2
        [*] --> Planned
        state "준비 전" as Planned
        state "초안 생성" as Draft
        state "내용 작성" as Editing
        state "검토 완료" as Reviewed
        state "제출본 준비" as Ready
        state "제출 사실 확인 필요" as Awaiting
        state "제출 확인" as Confirmed
        Planned --> Draft: 초안 생성
        Draft --> Editing: 실제 내용 작성
        Editing --> Reviewed: 담당자 검토 기록
        Reviewed --> Editing: 수정 요청
        Reviewed --> Ready: PDF 등 제출본 생성
        Ready --> Awaiting: 사용자가 외부 제출했다고 기록
        Awaiting --> Confirmed: 제출처·시각·접수 증거 확인
        Awaiting --> Ready: 미접수 확인
        Confirmed --> Editing: 수정본 준비가 필요함
    ''', caveat='재제출 시 기존 제출 이력은 보존하고 새 산출물 revision·제출 건을 만든다. 파일 생성·체크 표시만으로 Confirmed로 이동하지 않는다. 지각 여부는 별도 속성이다.')

add('16-target-evidence-state', '목표 증거 수집·정정 상태', 'target',
    '실패·누락·오래된 근거·수동 정정을 어떻게 보존할 것인가?',
    '성공한 0건과 미수집을 구분하며 실패로 기존 증거를 덮어쓰지 않는다. 수동 정정도 원래 관측과 나란히 기록한다.', r'''
    stateDiagram-v2
        [*] --> Missing
        state "미수집" as Missing
        state "새 수집 시도" as Fetching
        state "범위 완전·0건 가능" as Complete
        state "일부 수집·누락 있음" as Partial
        state "수집 실패" as Failed
        state "최신성 재확인 필요" as Stale
        state "수동 정정 제안" as Correction
        Missing --> Fetching: collect
        Fetching --> Complete: 요청 범위와 응답 완전성 확인
        Fetching --> Partial: 일부 항목 성공
        Fetching --> Failed: 인증·권한·연결 오류
        Complete --> Stale: 정책의 최신성 기준 초과
        Partial --> Fetching: 누락 범위 재수집
        Failed --> Fetching: 원인 해결 후 재시도
        Stale --> Fetching: 재수집
        Complete --> Correction: 다른 사실을 관측함
        Partial --> Correction: 수동 근거 보완
        Correction --> Complete: 정정 근거·확인자·범위 검증
    ''', caveat='batch마다 새 기록을 만든다는 개념 상태도다. 재수집 중 이전 성공 batch는 계속 남는다. 증거 수집 상태와 규칙 판정값은 별도다. 최신성 기간은 아직 미확정이다.')

add('17-target-decision-flow', '목표 판정 결정 흐름', 'target',
    '어떤 조건에서 충족·미충족·확인 필요라고 설명할 수 있는가?',
    '적용 정책과 증거의 충분성을 먼저 확인한다. 횟수만으로 의미 있는 변경·승인된 리뷰·최종 점수를 자동 확정하지 않는다.', r'''
    flowchart TB
        request["적용 건과 기준 시각"] --> policy{"규칙·승인·기간 정책이 확정됐나"}
        policy -->|"아니오"| unclear["기준 확인 필요 · 질문과 근거"]
        policy -->|"예"| applies{"이 대상·기간에 적용되나"}
        applies -->|"아니오"| na["해당 없음 · 사유"]
        applies -->|"예"| coverage{"증거 범위·최신성·필수 수동 확인이 충분한가"}
        coverage -->|"아니오"| unknown["확인 필요 · 부족한 증거"]
        coverage -->|"예"| satisfied{"완료 조건을 만족하나"}
        satisfied -->|"예"| pass["충족 · 근거 목록"]
        satisfied -->|"아니오"| open{"수행·평가 구간이 남았나"}
        open -->|"예"| ongoing["진행 중 · 남은 행동"]
        open -->|"아니오"| fail["미충족 · 미달 조건"]
        pass --> record["판정·이유·정책 버전·증거 스냅샷 저장"]
        ongoing --> record
        fail --> record
        unknown --> record
        na --> record
        unclear --> record
    ''', caveat='부분 충족·점수 환산은 이 흐름 다음의 별도 정책이며, 원문과 승인 근거가 충분한 항목에만 적용한다. 진행 중에도 충족 조건이 취소될 수 있는 규칙은 평가 시점 정책이 필요하다.')

add('18-migration-map', '현재 구현에서 목표 모델로 옮기는 지도', 'comparison',
    '무엇을 살리고 무엇의 책임을 이동시켜야 하는가?',
    '화면 라이브러리 교체보다 기준·기간·적용 건·증거·판정을 먼저 공통 인터페이스로 모은다. 원문·문서 생성·기존 기록은 단계적으로 연결한다.', r'''
    flowchart LR
        subgraph current["현재 자산"]
            guide["Catalog·원문·source-map"]
            week["주차 JSON·기간 계산·이월 키"]
            criteria["평가표 파서·CRITERIA 상수"]
            collect["두 GitHub 수집 구현"]
            records["progress / assessments JSON"]
            docs["templates·minutes·PDF"]
            ui["CLI 분기·curses·Textual"]
        end
        subgraph target["이동할 책임"]
            source["버전 있는 기준·근거"]
            binding["일정 정책·적용 건"]
            evidence["수집 범위가 있는 증거 스냅샷"]
            state["수동 실행 기록·판정 이력"]
            artifact["산출물·제출 흐름"]
            cases["공통 사용 사례와 조회 뷰"]
        end
        guide --> source
        criteria --> source
        week --> binding
        source --> binding
        collect --> evidence
        records --> state
        evidence --> state
        docs --> artifact
        binding --> cases
        state --> cases
        artifact --> cases
        ui -->|"입출력·포커스만 남김"| cases
    ''', [('main', 'foss8/guide.py', 'Catalog'), ('main', 'foss8/activity.py', 'collect'), ('prototype', 'foss8/assessments.py', 'Store'), ('prototype', 'foss8/tui.py', 'App')],
    '리팩터링 실행 계획의 초안이다. 오래된 횟수·수동 체크를 새 모델의 검증된 증거로 승격시키지 않는다. GitHub 두 구현은 집계 의미가 달라 그대로 합치지 않는다.')


def source_links(diagram):
    links = []
    for branch, path, symbol in diagram['sources']:
        entry = next(d for d in INDEX[branch][path]['definitions'] if d['name'] == symbol)
        url = f'https://github.com/sangjaepark0000/foss-8/blob/{SHAS[branch]}/{path}#L{entry["line"]}'
        links.append(dict(label=f'{branch}: {path}:{entry["line"]} · {symbol}', url=url))
    return links


def render_md(diagram):
    lines = [f'## {diagram["title"]}', '', diagram['question'], '',
             '```mermaid', diagram['syntax'].rstrip(), '```', '', diagram['conclusion'], '']
    if diagram['caveat']: lines += ['범위·주의: ' + diagram['caveat'], '']
    lines += [f'[SVG 크게 보기](rendered/{diagram["slug"]}.svg) · [Mermaid 원본](diagrams/{diagram["slug"]}.mmd)', '']
    if diagram['sources']:
        lines += ['구현 근거:', ''] + [f'- [{x["label"]}]({x["url"]})' for x in source_links(diagram)] + ['']
    else:
        lines += ['설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.', '']
    return '\n'.join(lines)


def build():
    (OUT / 'diagrams').mkdir(parents=True, exist_ok=True)
    (OUT / 'rendered').mkdir(parents=True, exist_ok=True)
    for d in DIAGRAMS:
        d['source_links'] = source_links(d)
        (OUT / 'diagrams' / (d['slug'] + '.mmd')).write_text(d['syntax'])
    (OUT / 'manifest.json').write_text(json.dumps({'date': '2026-11-15', 'commits': SHAS, 'diagrams': DIAGRAMS}, ensure_ascii=False, indent=2))
    current = [d for d in DIAGRAMS if d['group'] == 'current']
    target = [d for d in DIAGRAMS if d['group'] == 'target']
    (OUT / 'CURRENT.md').write_text('# foss-8 현재 구현 다이어그램\n\n[전체 지도](README.md) · [목표 설계](TARGET.md) · [차이와 이동 순서](COMPARISON.md)\n\n'
        '기준: 2026-11-15 원격 조회. 브랜치별 커밋은 [manifest.json](manifest.json)에 고정했다. 노드·호출·저장 경로는 코드에서 확인했으며 실제 사용자의 개인 상태 파일은 조사하지 않았다.\n\n'
        + '\n'.join(render_md(d) for d in current))
    (OUT / 'TARGET.md').write_text('# 목표 설계 다이어그램\n\n[전체 지도](README.md) · [현재 구현](CURRENT.md) · [차이와 이동 순서](COMPARISON.md)\n\n'
        '상태: 이 대화에서 제안한 설계. 구현·DB·명령 이름·화면 프레임워크를 확정하지 않았다.\n\n'
        + '\n'.join(render_md(d) for d in target))
    (OUT / 'COMPARISON.md').write_text(comparison_text() + '\n' + render_md(DIAGRAMS[-1]))
    (OUT / 'README.md').write_text(readme_text())
    (OUT / 'index.html').write_text(viewer_html())
    print(f'Wrote {len(DIAGRAMS)} diagrams and atlas documents to {OUT}')


def comparison_text():
    return '''# 모델과 사용 흐름의 차이

[전체 지도](README.md) · [현재 구현](CURRENT.md) · [목표 설계](TARGET.md)

사용자가 느끼는 차이를 “기능이 적다”로 단정하지 않는다. 아래는 코드를 읽고 도출한 설계 관점의 진단이다. 실제 사용성 테스트 결과는 아니다.

| 관점 | 현재 main | 현재 prototype | 목표안 |
| --- | --- | --- | --- |
| 중심 단위 | 명령별 문서·결과 | 선택한 주차의 작업 트리 | 기준을 대상·기간에 적용한 안정적인 적용 건 |
| 첫 흐름 | 명령과 파일을 사용자가 조합 | 주차 → 할 일/평가/설정 | 지금 해야 할 일 → 기준/증거/판정 상세 |
| 기준 정의 | Markdown 표와 기능별 파서 | 원문·weeks.json·CRITERIA 상수 | 버전과 출처가 있는 기준 정의 |
| 기간 | week는 다음 수업, 회의록은 화~월+제출회차 | 화~월 학사 주차와 활동 제외 날짜 | 수업·활동·기록·마감의 서로 다른 의미를 명시 |
| 활동 수집 | 여러 팀원의 JSON 근거 초안 | 현재 개인의 주간 횟수·링크 | 범위·시각·완전성을 가진 증거 batch |
| 완료 | 자동 판정 안 함; 파일 존재만 검사 | 작업 수동 체크와 주간 횟수 상태 | 실행·산출물·제출·규칙 판정의 분리 |
| 설명 | 원문 링크·수동 확인 안내 | 기준·수집 시각·링크·수동 출처 | 판정 ID → 정책 버전·증거 스냅샷·이유 |
| 미완료 이월 | 통합 backlog 없음 | carry_next_week 항목을 바로 다음 주에 공유 | 기간이 바뀌어도 열린 적용 건과 원래 기한 유지 |
| UI와 조립 | cli.main의 분기·조립 | tui.App의 UI·수집·저장 조정 | CLI/TUI가 동일한 사용 사례 인터페이스 호출 |

## 현재 자산에서 유지할 것

- 원문 48쪽 전사·source-map·PDF 해시·원문과 팀 결정의 구분.
- 기록 기간·제출 회차·수업 회차를 구분한 회의록 생성, 기존 파일 보호, PDF 생성 후 제출로 자동 처리하지 않는 동작.
- 개인/저장소/기간별 상태 구분, 빈 값과 확인된 0의 구분, 항목별 수집 실패 시 기존 값 유지.
- 원문 조회를 GitHub 로그인과 분리한 흐름. 팀 설정 후보를 확인한 뒤 적용하는 방식.

## 먼저 고정할 도메인 불변식

1. 기준 정의를 바꾼다고 과거 적용 건의 정책·판정 이력을 덮어쓰지 않는다.
2. 개인 기준을 팀 합계로 충족 처리하지 않는다. 적용 대상은 개인 또는 팀으로 명시한다.
3. 미수집·수집 실패·부분 수집은 확인된 0과 다르다.
4. 작업 체크·초안 생성·PDF 생성·제출 확인·규칙 충족을 각각 기록한다.
5. 마감 경과와 완료는 다른 축이다. 지각 완료도 표현한다.
6. 기간 변경 시 미완료 적용 건과 원래 마감을 유지한다. 수업 예정일이 지났다고 수행을 추정하지 않는다.
7. 승인된 3인·3기능은 승인된 범위에만 적용한다. 배점·개인 활동 최소치까지 자동 환산하지 않는다.
8. 알려지지 않은 주간 집계 경계는 정책 결정으로 표시한다. prototype의 화~월은 구현된 해석이며 안내서의 유일한 확정 해석으로 취급하지 않는다.
9. 주간 진행량과 학기 점수 계산을 분리한다. PR·커밋 횟수만으로 실질성·리뷰 적정성·최종 점수를 확정하지 않는다.

## 집계 구현을 합치기 전 결정할 차이

| 항목 | main/activity.py | prototype/github_activity.py | 필요한 결정 |
| --- | --- | --- | --- |
| 대상 | 지정 팀원 여러 명 | config.me 한 명 | 개인·팀 조회의 공통 scope |
| 커밋 시각 | commit.author.date 추가 필터 | commit.committer.date 추가 필터 | 기준 시각 정의와 API 필터 의미 |
| 병합 커밋 | parents가 2개 이상이면 제외 | 별도 제외 조건 없음 | 의미 있는 커밋의 계수 정책 |
| PR | 생성·병합을 별도 시각으로 집계 | 같은 활성 구간 안에 생성되고 병합된 PR 검색 | 주간 생성·병합 기준의 해석 |
| 저장 결과 | categories의 error·links | counts·evidence·errors와 로컬 집계 기록 | 관측·집계·판정 스키마 분리 |
| 검색 완전성 | 목록 페이지를 읽음 | search의 incomplete_results·total_count도 확인 | 범위별 coverage 계약 |

각 차이는 구현에서 확인한 사실이다. 어느 쪽이 정답인지는 규칙 해석과 API 의미를 확인해 정한다. 이 문서는 GitHub 실데이터를 재집계하지 않았다.

## 목표 판정 결정표

위에서 아래 순서로 적용한다. 판정은 평가 시점에 대한 설명이며 외부 성적 확정이 아니다.

| 조건 | 결과 | 설명에 반드시 포함할 것 |
| --- | --- | --- |
| 규칙·승인·활동 구간 정책이 미확정 | 기준 확인 필요 | 질문, 충돌하는 근거, 영향 범위 |
| 확정 정책상 해당 대상·기간에 적용되지 않음 | 해당 없음 | 면제·적용 전·적용 밖 등의 사유 |
| 증거 범위·최신성 또는 필수 수동 확인이 부족 | 확인 필요 | 누락한 범위, 마지막 성공 시각, 수집 오류 |
| 충분한 증거가 완료 조건을 만족 | 충족 | 충족한 조건과 증거 링크 |
| 충분한 증거상 아직 미달이며 수행 구간이 남음 | 진행 중 | 남은 행동과 기한 |
| 충분한 증거상 미달이며 수행·판정 구간이 종료됨 | 미충족 | 미달 조건과 해당 기간 |

부분 충족·점수 환산은 별도 정책으로 둔다. 원문이 항목별 계산 방법을 충분히 정의하고 팀 변경의 승인 범위가 확인된 경우에만 적용한다. 확인 필요를 0점으로 바꾸지 않는다.

## 첫 구현에서 필요한 인터페이스

```text
collect(project, period) → CollectionReport
check(project, period, evidence_snapshot, evaluated_at) → Assessment[]
explain(assessment_id) → AssessmentExplanation
now(project, subject, as_of) → ActionView[]
```

CLI는 인자·종료코드·텍스트/JSON, TUI는 포커스·선택·갱신을 맡는다. 계수·기간 해석·수집 오류를 처리하는 코드를 화면별로 다시 작성하지 않는다. 순수 판정 모듈은 터미널이나 네트워크에 접근하지 않는다.

## 이동 순서

| 순서 | 결과물 | 완료 확인 |
| --- | --- | --- |
| 1 | 기준·기간 정책과 안정 ID | PR·커밋·이슈 3개 기준의 출처·scope·주기·면제·미확정 해석을 설명 가능 |
| 2 | 적용 건 생성 | 같은 사람·기준·기간에 안정적인 ID, 다음 주에도 기존 미완료 유지 |
| 3 | 증거 batch | 0·미수집·부분 실패·재시도·수동 정정을 원래 관측과 구분 |
| 4 | 판정·explain | 판정 버전과 증거를 고정하고 결과 이유를 동일하게 재현 |
| 5 | 공통 CLI 흐름 | 조회·수집·점검·설명과 JSON 출력이 같은 사용 사례 사용 |
| 6 | TUI 뷰 교체 | 지금 할 일·주차·개인·제출물에서 같은 적용 건 상세로 이동 |
| 7 | 산출물·제출 연결 | 초안·검토·PDF·실제 제출 확인의 상태를 구분 |

저장 방식은 JSON으로 시작해도 된다. 관계·이력·원자적 갱신 요구가 커질 때 SQLite 등의 저장 구현을 결정한다. 문서화 단계에서 서버나 특정 TUI 프레임워크를 추가 확정하지 않는다.

## 아직 결정하지 않은 것

- 제품의 최우선 대상: 개인의 과제 진행 지원인지, 팀 전체 운영인지. 초기 화면의 기본 scope에 영향.
- 활동 구간 경계·PR 생성/병합·커밋 시각과 의미 있는 변경의 판정 정책.
- LMS·이메일 제출 확인을 수동 증거로 받을지, 추후 연동할지.
- 수동 횟수 정정과 이후 GitHub 관측이 충돌할 때 채택·검토 정책.
- 증거 최신성 기준, 보존 기간, 판정 재실행·무효화 정책.
- CLI 명령의 호환 유지 범위, curses/Textual 선택, JSON 또는 DB 저장 방식.

'''


def readme_text():
    rows = '\n'.join(f'| {d["slug"].split("-")[0]} | {d["title"]} | {"현재 구현" if d["group"] == "current" else "목표 설계" if d["group"] == "target" else "비교"} | [SVG](rendered/{d["slug"]}.svg) · [Mermaid](diagrams/{d["slug"]}.mmd) |' for d in DIAGRAMS)
    return f'''# foss-8 다이어그램 지도

[그림으로 전체 보기](index.html) · [현재 구현](CURRENT.md) · [목표 설계](TARGET.md) · [모델·사용 흐름 비교](COMPARISON.md)

이 문서는 “전체적인 모델과 사용 흐름이 원하는 상태와 다르다”는 문제를 검토하기 위해 만들었다. 현재 구현을 코드에서 추출하고, 대화에서 논의한 목표 설계를 별도로 그렸다. 앱 동작은 변경하지 않았다.

## 먼저 볼 순서

1. **09 목표 도메인**: 기준 정의·적용 건·증거·판정을 나누는 이유.
2. **06 prototype 데이터 모델 → 10 목표 ERD**: 현재 주차·작업·횟수 모델에서 무엇이 달라지는가.
3. **07 현재 사용자 흐름 → 14 목표 TUI 흐름**: 주차 중심 진입과 지금 해야 할 일 중심 진입의 차이.
4. **17 판정 흐름·결정표**: 미수집·진행 중·미충족·기준 미확정을 구분하는 방법.
5. **18 이동 지도**: 유지할 자산과 옮길 책임.

## 범위와 근거

원격 조회일: **2026-11-15**. 출처는 이동하는 브랜치 링크 대신 커밋 SHA에 고정했다.

| 구현 범위 | 기준 커밋 | 읽는 방법 |
| --- | --- | --- |
| main | `{SHAS['main']}` | 현재 합쳐진 CLI·서식·활동·PDF·파일 검사 |
| prototype | `{SHAS['prototype']}` | 별도 curses TUI·팀 설정·수동 완료·주간 집계 |
| feature/guide-tool | `{SHAS['guide-tool']}` | 별도 Textual 안내서 탐색 구현, 범위도에 표시 |
| 목표안 | 미구현 설계 | 이 대화에서 논의한 모델·인터페이스·흐름 |

실선은 각 그림에 설명한 호출·데이터 관계다. 점선의 의미는 각 그림의 주의사항을 따른다. 실제 배포 상태나 개인별 진척을 조사한 자료는 아니다. `data/course-project.json`의 설계 초안과 prototype의 실제 실행 데이터를 구분했다.

## 전체 {len(DIAGRAMS)}개

| 번호 | 그림 | 구분 | 파일 |
| --- | --- | --- | --- |
{rows}

## 추상화의 기준

- **레이어**: 원문·근거 → 기준·구조 → 절차·방법 → 활용 뷰.
- **안내서 모델**: 요구사항, 산출물, 일정, 역할, 절차, 증거.
- **실행 모델**: 프로젝트·대상·기간에 바인딩한 적용 건, 작업 실행, 증거 batch, 판정 이력, 제출 기록.
- **판정 설명**: 언제 어떤 정책·증거로 판정했으며 무엇이 부족하거나 미확정인가.

## 파일과 재생성

- `diagrams/*.mmd`: 수정 가능한 Mermaid 원본.
- `rendered/*.svg`: 실제 렌더링한 그림. 네트워크 없이 열 수 있다.
- `index.html`: SVG·설명·출처를 모은 로컬 탐색 화면. 앱 프로토타입은 아니다.
- `manifest.json`: 도표 내용·출처·기준 커밋.
- `source-index.json`: 해당 커밋들의 함수·클래스 위치.
- `validation.json`: 렌더링·문서 링크·출처 검증 결과.

문서 재생성: `python scripts/build_architecture.py`. SVG 재생성: [렌더링 안내](RENDERING.md). Python 앱 로직을 실행하지 않고 문서만 생성한다.
'''


def viewer_html():
    labels = {'current': '현재 구현', 'target': '목표 설계 · 미구현', 'comparison': '비교·이동'}
    nav = ''.join(f'<a href="#{d["slug"]}" data-group="{d["group"]}">{html.escape(d["title"])}</a>' for d in DIAGRAMS)
    cards = []
    for d in DIAGRAMS:
        sources = ''.join(f'<li><a href="{html.escape(s["url"])}" target="_blank" rel="noreferrer">{html.escape(s["label"])}</a></li>' for s in d['source_links'])
        cards.append(f'''<section id="{d['slug']}" data-group="{d['group']}">
<p class="eyebrow">{labels[d['group']]} · {d['slug'].split('-')[0]}</p>
<h2>{html.escape(d['title'])}</h2><p class="question">{html.escape(d['question'])}</p>
<figure><a href="rendered/{d['slug']}.svg" target="_blank" aria-label="{html.escape(d['title'])} 크게 보기"><img src="rendered/{d['slug']}.svg" alt="{html.escape(d['title'])}" loading="lazy"></a></figure>
<p>{html.escape(d['conclusion'])}</p>
{f'<p class="caveat">{html.escape(d["caveat"])}</p>' if d['caveat'] else ''}
<p class="links"><a href="rendered/{d['slug']}.svg" target="_blank">SVG 크게 보기</a> · <a href="diagrams/{d['slug']}.mmd">Mermaid 원본</a></p>
{f'<details><summary>구현 근거</summary><ul>{sources}</ul></details>' if sources else '<p class="caveat">이 대화의 목표 설계이며 현재 미구현.</p>'}</section>''')
    return '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>foss-8 · 모델과 사용 흐름</title>
<style>
:root { color-scheme:light; --paper:#f7f8fa; --ink:#182334; --muted:#536277; --line:#d9e0e8; --accent:#2458a4; }
* {box-sizing:border-box} html {scroll-behavior:smooth} body {margin:0;background:var(--paper);color:var(--ink);font:16px/1.65 system-ui,'Noto Sans CJK KR',sans-serif}
a {color:var(--accent);text-underline-offset:3px} header {padding:48px clamp(20px,5vw,64px) 28px;border-bottom:1px solid var(--line)}
h1 {font-size:clamp(28px,4vw,44px);line-height:1.2;margin:8px 0 18px;letter-spacing:-.045em} h2 {font-size:25px;line-height:1.4;margin:0 0 10px;letter-spacing:-.025em}
header p {max-width:820px;margin:10px 0}.eyebrow {font-size:12px;font-weight:700;letter-spacing:.08em;color:var(--muted);margin:0 0 10px}
.filters {display:flex;gap:8px;flex-wrap:wrap;margin:22px 0 0} button {font:inherit;border:1px solid var(--line);background:transparent;padding:8px 15px;border-radius:6px;cursor:pointer}button[aria-pressed=true] {background:var(--ink);color:white;border-color:var(--ink)}
.layout {display:grid;grid-template-columns:240px minmax(0,1fr);max-width:1600px;margin:auto} nav {padding:28px 20px;position:sticky;top:0;align-self:start;max-height:100vh;overflow:auto;font-size:13px}nav a {display:block;text-decoration:none;padding:7px 3px;border-bottom:1px solid var(--line)}
main {min-width:0;padding:0 38px 60px}section {padding:40px 0;border-bottom:1px solid var(--line);scroll-margin-top:18px}section[hidden],nav a[hidden] {display:none}
.question {color:var(--muted);margin-top:0} figure {background:white;margin:22px 0;padding:20px 12px;overflow:auto}figure img {display:block;max-width:100%;height:auto;margin:auto}section[id="10-target-erd"] figure img {min-height:520px}
.caveat {font-size:14px;color:var(--muted)} .links {font-size:14px}details {font-size:13px}summary {cursor:pointer}code {font-size:.88em}footer {padding:24px;color:var(--muted);font-size:13px}
@media(max-width:850px){.layout{grid-template-columns:1fr}nav{position:static;max-height:none;display:flex;flex-wrap:wrap;gap:6px;padding:16px}nav a{border:1px solid var(--line);padding:5px 8px}main{padding:0 20px 40px}figure{padding:10px 0}section{padding:26px 0}section[id="10-target-erd"] figure img{min-height:0}}
@media print {nav,.filters,.links{display:none}.layout{display:block}main{padding:0}header{padding:10px}section{break-inside:avoid}section[hidden]{display:block}}
</style></head><body>
<header><p class="eyebrow">FOSS-8 · ARCHITECTURE ATLAS · 2026-11-15</p><h1>모델과 사용 흐름</h1>
<p>현재의 main·prototype과 대화에서 논의한 목표 설계를 함께 본다. 그림은 실제 구현과 미구현 제안을 구분한다.</p>
<p><strong>추천 순서:</strong> 09 목표 도메인 → 06 현재 모델 → 10 목표 ERD → 07 현재 흐름 → 14 목표 흐름 → 17 판정 → 18 이동 지도.</p>
<p><a href="README.md">전체 문서</a> · <a href="COMPARISON.md">모델·사용 흐름 비교와 결정표</a></p>
<div class="filters" role="group" aria-label="도표 범위"><button type="button" data-filter="all" aria-pressed="true">전체 19개</button><button type="button" data-filter="current" aria-pressed="false">현재 구현</button><button type="button" data-filter="target" aria-pressed="false">목표 설계</button><button type="button" data-filter="comparison" aria-pressed="false">비교·이동</button></div></header>
<div class="layout"><nav aria-label="다이어그램 목차">''' + nav + '</nav><main>' + '\n'.join(cards) + '''</main></div>
<footer>현재 구현 기준: main 8e6ea27 · prototype 8fc2ae6 · guide-tool d1a5a39. SVG는 로컬 파일이며 외부 리소스를 불러오지 않는다.</footer>
<script>
document.querySelectorAll('button[data-filter]').forEach(button=>button.addEventListener('click',()=>{
 const group=button.dataset.filter;
 document.querySelectorAll('button[data-filter]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 document.querySelectorAll('section[data-group],nav a[data-group]').forEach(node=>node.hidden=group!=='all'&&node.dataset.group!==group);
}));
</script></body></html>'''


if __name__ == '__main__':
    build()
