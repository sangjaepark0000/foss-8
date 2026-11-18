# 목표 설계 다이어그램

[전체 지도](README.md) · [현재 구현](CURRENT.md) · [차이와 이동 순서](COMPARISON.md)

상태: 이 대화에서 제안한 설계. 구현·DB·명령 이름·화면 프레임워크를 확정하지 않았다.

## 목표 도메인: 기준을 적용하고 근거로 설명하기

사용자가 원하는 점검을 표현하려면 어떤 개념을 분리해야 하는가?

```mermaid
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
```

핵심은 주차 트리에서 기준을 복사하는 대신, 기준 정의를 사람·팀·기간에 적용해 생성한 적용 건에 증거와 판정을 연결하는 것이다.

범위·주의: 이 대화에서 제안한 미구현 모델이다. 승인된 3인·3기능 변경이 곧 배점의 비례 환산을 뜻하지 않는다.

[SVG 크게 보기](rendered/09-target-domain.svg) · [Mermaid 원본](diagrams/09-target-domain.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 ERD: 적용 건·증거·판정의 식별

과거 판정을 재현하고 여러 뷰에서 같은 기준을 보려면 어떤 관계가 필요한가?

```mermaid
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
```

기준과 적용 건을 분리하고 판정은 사용한 정책·증거 버전을 고정한다. 기간 변경이나 재수집으로 과거 판정을 덮어쓰지 않는다.

범위·주의: 개념 ERD이며 DB 선택이나 최종 물리 스키마를 확정하지 않는다. predicate·coverage는 검증된 구조여야 하며 사용자 문자열을 eval하지 않는다. 관계 일부와 보조 조인 테이블은 가독성을 위해 생략했다.

[SVG 크게 보기](rendered/10-target-erd.svg) · [Mermaid 원본](diagrams/10-target-erd.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 모듈과 네 레이어

CLI와 TUI가 어떤 인터페이스를 공유해야 모델이 화면에 종속되지 않는가?

```mermaid
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
```

UI는 요청·출력과 포커스를 담당하고 collect/check/explain이 조립을 담당한다. 판정 모듈은 관측 저장이나 터미널 조작 없이 결과를 반환한다.

범위·주의: 미구현 설계안. 단일 로컬 프로그램 내부의 모듈 관계다. 별도 웹 서버·백그라운드 데몬·마이크로서비스 배포를 요구하지 않는다.

[SVG 크게 보기](rendered/11-target-modules.svg) · [Mermaid 원본](diagrams/11-target-modules.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 수집·점검·설명 시퀀스

수집이 실패해도 사용자가 왜 확인이 필요한지 추적할 수 있는가?

```mermaid
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
```

collect와 check는 분리한다. check는 고정된 증거 스냅샷으로 판정하고 explain은 같은 판정의 기준·이유·근거를 다시 읽는다.

범위·주의: 네트워크 자동 갱신을 check 내부에 숨기지 않는 초기 인터페이스안이다. collect 실패 시 이전 batch와 실패한 새 시도를 함께 보존한다.

[SVG 크게 보기](rendered/12-target-check-sequence.svg) · [Mermaid 원본](diagrams/12-target-check-sequence.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 CLI의 작업 흐름

명령을 외우는 사람과 자동화가 같은 도메인 작업을 수행할 수 있는가?

```mermaid
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
```

프로젝트 문맥을 고른 뒤 조회·수집·점검·설명·문서 작업을 독립 명령으로 수행한다. 읽기 작업은 상태를 암묵적으로 변경하지 않는다.

범위·주의: 명령 이름은 제안이다. main의 기존 check와 prototype의 week 동작을 이미 바꿨다는 뜻이 아니다. 모든 CLI 결과에는 텍스트와 JSON 표현을 함께 설계한다.

[SVG 크게 보기](rendered/13-target-cli-flow.svg) · [Mermaid 원본](diagrams/13-target-cli-flow.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 TUI: 사용자 목적에서 근거까지

주차를 바꿔도 남은 작업·원래 기한·판정 근거를 잃지 않는가?

```mermaid
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
```

첫 화면은 현재 실행 가능한 일·막힘·마감·이월을 보여준다. 주차는 여러 조회 축 중 하나이며 같은 적용 건을 계속 참조한다.

범위·주의: 텍스트 화면 이동 설계이며 완성된 TUI 스크린샷이 아니다. 사용자 체크, 수집 성공, 문서 생성, LMS 제출, 규칙 충족은 각각 별도의 표시다.

[SVG 크게 보기](rendered/14-target-tui-flow.svg) · [Mermaid 원본](diagrams/14-target-tui-flow.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 산출물·제출 상태

PDF를 만들었다는 사실과 제출 완료·기한 준수를 어떻게 구분하는가?

```mermaid
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
```

산출물 준비와 외부 제출 확인을 분리한다. 기한 준수는 제출 시각과 고정 마감의 비교값이며 상태를 되돌리는 조건이 아니다.

범위·주의: 재제출 시 기존 제출 이력은 보존하고 새 산출물 revision·제출 건을 만든다. 파일 생성·체크 표시만으로 Confirmed로 이동하지 않는다. 지각 여부는 별도 속성이다.

[SVG 크게 보기](rendered/15-target-submission-state.svg) · [Mermaid 원본](diagrams/15-target-submission-state.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 증거 수집·정정 상태

실패·누락·오래된 근거·수동 정정을 어떻게 보존할 것인가?

```mermaid
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
```

성공한 0건과 미수집을 구분하며 실패로 기존 증거를 덮어쓰지 않는다. 수동 정정도 원래 관측과 나란히 기록한다.

범위·주의: batch마다 새 기록을 만든다는 개념 상태도다. 재수집 중 이전 성공 batch는 계속 남는다. 증거 수집 상태와 규칙 판정값은 별도다. 최신성 기간은 아직 미확정이다.

[SVG 크게 보기](rendered/16-target-evidence-state.svg) · [Mermaid 원본](diagrams/16-target-evidence-state.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.

## 목표 판정 결정 흐름

어떤 조건에서 충족·미충족·확인 필요라고 설명할 수 있는가?

```mermaid
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
```

적용 정책과 증거의 충분성을 먼저 확인한다. 횟수만으로 의미 있는 변경·승인된 리뷰·최종 점수를 자동 확정하지 않는다.

범위·주의: 부분 충족·점수 환산은 이 흐름 다음의 별도 정책이며, 원문과 승인 근거가 충분한 항목에만 적용한다. 진행 중에도 충족 조건이 취소될 수 있는 규칙은 평가 시점 정책이 필요하다.

[SVG 크게 보기](rendered/17-target-decision-flow.svg) · [Mermaid 원본](diagrams/17-target-decision-flow.mmd)

설계 근거: 이 대화에서 합의한 기준 정의·적용 건·증거·판정 분리. 현재 미구현 제안.
