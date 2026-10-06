# GitHub 활동 정보 조회 방식 조사

## 목적

사용자의 설치·로그인·토큰 설정 부담을 줄이면서 커밋, 이슈, PR, 리뷰 정보를 조회할 방법을 비교한다.

## 비교

| 방식 | 설정 부담 | 커밋 | 이슈 | PR | 리뷰 |
|---|---|---|---|---|---|
| 로컬 Git | 낮음 | O | X | X | X |
| GitHub CLI (`gh`) | 낮음~중간 | O | O | O | O |
| GitHub REST API | 높음 | O | O | O | O |

### 로컬 Git

- Git만 있으면 바로 사용 가능
- 로컬 저장소의 커밋 조회에 적합
- 이슈, PR, 리뷰는 조회 불가

커밋 확인만 필요하다면 괜찮지만, 프로젝트의 활동 기준 전체를 자동으로 확인하기에는 부족함.

### GitHub CLI (gh)

- 사용자가 직접 gh 설치 & 최초 1회 로그인 필요
- 이슈, PR, 리뷰 모두 조회 가능
- 필요한 경우 gh api로 GitHub API도 사용 가능

예:
gh auth login
gh issue list
gh pr list
gh pr view 12 --json reviews,reviewDecision

커밋 조회 예:
gh api repos/{owner}/{repo}/commits

### GitHub REST API

- 이슈, PR, 리뷰 모두 조회 가능
- 프로그램에서 직접 HTTP 요청으로 데이터를 받을 수 있음
- 인증 토큰 발급 및 권한 설정이 필요해 초기 설정 부담이 큼
- API endpoint, pagination, rate limit 등을 직접 처리해야 함

예:
```bash
GET https://api.github.com/repos/{owner}/{repo}/commits
GET https://api.github.com/repos/{owner}/{repo}/issues
GET https://api.github.com/repos/{owner}/{repo}/pulls
```

기능은 가장 자유롭지만, 사용자 설정과 구현 부담이 큼.


## 추천안

gh 사용을 추천한다.

이유:
- 로컬 Git은 조회 범위가 좁음.
- REST API보다 인증과 토큰 관리가 간단함
- 개발 부담이 적음. REST API와 달리 HTTP 헤더나 토큰 전달 방식을 직접 구현하지 않아도 됨.
- 명령어 결과를 JSON으로 받아 프로그램에서 처리하기 쉬움

## 자동·수동 확인 경계

자동 확인 가능:
- 커밋 수
- 이슈 수
- PR 수
- 리뷰 기록
- PR 승인 여부
- 파일 존재 여부

수동 확인 필요:
- 리뷰 내용
- 커밋 내용
- 회의 참석 여부
- 문서 내용의 충실도
- 기능이 요구사항대로 동작하는지

## 공식 문서
- GitHub CLI: https://cli.github.com/manual/
- gh auth login: https://cli.github.com/manual/gh_auth_login
- gh pr view: https://cli.github.com/manual/gh_pr_view
- gh api: https://cli.github.com/manual/gh_api
GitHub REST API: https://docs.github.com/en/rest