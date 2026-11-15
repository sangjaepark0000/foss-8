# foss-8 다이어그램 지도

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
| main | `8e6ea27b07c7f287aa12d3b927ba3e9acae23732` | 현재 합쳐진 CLI·서식·활동·PDF·파일 검사 |
| prototype | `8fc2ae6e6bf3e340067887fbeeb023ec7af65931` | 별도 curses TUI·팀 설정·수동 완료·주간 집계 |
| feature/guide-tool | `d1a5a39c963e6ef1f38f2341e3c42259e1ae12a6` | 별도 Textual 안내서 탐색 구현, 범위도에 표시 |
| 목표안 | 미구현 설계 | 이 대화에서 논의한 모델·인터페이스·흐름 |

실선은 각 그림에 설명한 호출·데이터 관계다. 점선의 의미는 각 그림의 주의사항을 따른다. 실제 배포 상태나 개인별 진척을 조사한 자료는 아니다. `data/course-project.json`의 설계 초안과 prototype의 실제 실행 데이터를 구분했다.

## 전체 19개

| 번호 | 그림 | 구분 | 파일 |
| --- | --- | --- | --- |
| 00 | 현재 저장소의 세 구현 범위 | 현재 구현 | [SVG](rendered/00-repository-scopes.svg) · [Mermaid](diagrams/00-repository-scopes.mmd) |
| 01 | main의 실제 모듈과 의존성 | 현재 구현 | [SVG](rendered/01-main-modules.svg) · [Mermaid](diagrams/01-main-modules.mmd) |
| 02 | main의 실제 정보 모델 | 현재 구현 | [SVG](rendered/02-main-information-model.svg) · [Mermaid](diagrams/02-main-information-model.mmd) |
| 03 | main의 현재 사용자 흐름 | 현재 구현 | [SVG](rendered/03-main-cli-flow.svg) · [Mermaid](diagrams/03-main-cli-flow.mmd) |
| 04 | main의 활동 수집·문서 생성 시퀀스 | 현재 구현 | [SVG](rendered/04-main-evidence-document-sequence.svg) · [Mermaid](diagrams/04-main-evidence-document-sequence.mmd) |
| 05 | prototype의 실제 모듈 구조 | 현재 구현 | [SVG](rendered/05-prototype-modules.svg) · [Mermaid](diagrams/05-prototype-modules.mmd) |
| 06 | prototype의 현재 데이터·식별 모델 | 현재 구현 | [SVG](rendered/06-prototype-information-model.svg) · [Mermaid](diagrams/06-prototype-information-model.mmd) |
| 07 | prototype의 현재 사용자 흐름 | 현재 구현 | [SVG](rendered/07-prototype-user-flow.svg) · [Mermaid](diagrams/07-prototype-user-flow.mmd) |
| 08 | prototype의 현재 집계 상태 전이 | 현재 구현 | [SVG](rendered/08-prototype-sync-state.svg) · [Mermaid](diagrams/08-prototype-sync-state.mmd) |
| 09 | 목표 도메인: 기준을 적용하고 근거로 설명하기 | 목표 설계 | [SVG](rendered/09-target-domain.svg) · [Mermaid](diagrams/09-target-domain.mmd) |
| 10 | 목표 ERD: 적용 건·증거·판정의 식별 | 목표 설계 | [SVG](rendered/10-target-erd.svg) · [Mermaid](diagrams/10-target-erd.mmd) |
| 11 | 목표 모듈과 네 레이어 | 목표 설계 | [SVG](rendered/11-target-modules.svg) · [Mermaid](diagrams/11-target-modules.mmd) |
| 12 | 목표 수집·점검·설명 시퀀스 | 목표 설계 | [SVG](rendered/12-target-check-sequence.svg) · [Mermaid](diagrams/12-target-check-sequence.mmd) |
| 13 | 목표 CLI의 작업 흐름 | 목표 설계 | [SVG](rendered/13-target-cli-flow.svg) · [Mermaid](diagrams/13-target-cli-flow.mmd) |
| 14 | 목표 TUI: 사용자 목적에서 근거까지 | 목표 설계 | [SVG](rendered/14-target-tui-flow.svg) · [Mermaid](diagrams/14-target-tui-flow.mmd) |
| 15 | 목표 산출물·제출 상태 | 목표 설계 | [SVG](rendered/15-target-submission-state.svg) · [Mermaid](diagrams/15-target-submission-state.mmd) |
| 16 | 목표 증거 수집·정정 상태 | 목표 설계 | [SVG](rendered/16-target-evidence-state.svg) · [Mermaid](diagrams/16-target-evidence-state.mmd) |
| 17 | 목표 판정 결정 흐름 | 목표 설계 | [SVG](rendered/17-target-decision-flow.svg) · [Mermaid](diagrams/17-target-decision-flow.mmd) |
| 18 | 현재 구현에서 목표 모델로 옮기는 지도 | 비교 | [SVG](rendered/18-migration-map.svg) · [Mermaid](diagrams/18-migration-map.mmd) |

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
