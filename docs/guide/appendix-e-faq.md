# [부록 E](appendix-e-faq.md). 문제 해결 FAQ

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 47~47쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-47"></a>

## 원문 47쪽

<!-- source-page: 47 -->
## [부록 E](appendix-e-faq.md). 문제 해결 FAQ

오류 메시지의 핵심 단어로 이 표를 검색하세요(Ctrl+F). 해결되지 않으면 [16.2절](16-help.md#section-16-2) 양식으로 질문합니다.

| 증상 | 원인 | 해결 |
| --- | --- | --- |
| 소스트리 Push가 거부됨 (rejected) | 다른 팀원이 먼저 올림 | Pull → (충돌 있으면 [8.7절](08-collaboration.md#section-8-7)) → 다시 Push. 강제 푸시 금지 |
| Push할 때 'Permission denied' / 인증 오류 | 로그인 계정이 다르거나 토큰<br>만료·협력자 미등록 | 소스트리 도구 → 옵션 → 인증에서 GitHub 계정 확인·재<br>로그인(수업 6·11주차). 협력자 초대를 수락했는지 확인 |
| main에 직접 커밋해서 Push가 막힘 | 보호 규칙이 켜져 있음(9주차<br>이후) | 정상 동작. [8.8절](08-collaboration.md#section-8-8) 둘째 줄 방법으로 커밋을 새 브랜치로 옮<br>긴 뒤 풀 리퀘스트 |
| 풀 리퀘스트에 'This branch has conflicts<br>that must be resolved' | 같은 부분을 두 사람이 수정 | [8.7절](08-collaboration.md#section-8-7) |
| 병합 버튼이 회색 — 'Review required' | 승인 1개가 없음 | 리뷰어에게 Approve 요청. 본인은 본인 풀 리퀘스트를 승<br>인할 수 없음 |
| 소스트리 그래프에 GitHub에서 병합한 결과가<br>안 보임 | 그래프 미갱신 | 패치 → main 체크아웃 → Pull (수업 9주차 실습 8~12단<br>계) |
| ModuleNotFoundError: No module<br>named 'pandas' | 라이브러리 미설치 | pip install -r requirements.txt. 여전히 안 되면 VS<br>Code 오른쪽 아래 Python 버전이 설치한 것과 같은지 확<br>인 |
| python을 입력하면 Microsoft Store가 열림<br>/ 'python은 내부 또는 외부 명령이 아닙니다' | 설치 시 PATH 체크 누락 | Python 재설치하며 Add python.exe to PATH 체크, 또<br>는 py main.py로 실행 |
| 터미널에서 한글이 ?로 깨짐 | 인코딩 | CMD/PowerShell에서 chcp 65001 후 재시도. 파일 입<br>출력에는 encoding="utf-8" |
| Windows에서 warning: LF will be<br>replaced by CRLF | 줄바꿈 안내 | 경고일 뿐 오류 아님. 무시해도 됨 |
| Git Bash에서 git merge 뒤 검은 화면(vim)<br>에 갇힘 | 병합 메시지 편집기 | Esc → :wq → Enter. [6.3절](06-tools.md#section-6-3) core.editor 설정으로 예방 |
| 병합했는데 이슈가 안 닫힘 | Closes #n이 설명이 아닌 댓<br>글에 있거나 오타 | 풀 리퀘스트 설명(첫 글)에 Closes #12. 이미 병합됐으면<br>이슈에서 수동 Close |
| Fork한 저장소가 원본보다 뒤처짐 | 원본에 새 커밋 | fork 페이지의 Sync fork 버튼 |
| 협력자 초대를 받았는데 Push가 안 됨 | 초대 미수락(7일 만료) | GitHub 알림·이메일에서 Accept. 만료됐으면 팀장이 재<br>초대 |
| 내 커밋이 GitHub 프로필 잔디(Contribution)<br>에 안 뜸 | 이메일 불일치 또는 main에<br>아직 병합 안 됨 | Git·소스트리의 이메일이 GitHub 계정 이메일과 같은지 확<br>인(6.2). main에 병합된 커밋만 집계 (fork의 커밋은 원본<br>에 병합되면 집계) |
| 실수로 토큰·비밀번호를 커밋함 | 비밀 정보 유출 | 파일을 지워도 이력에 남음 → 해당 토큰 즉시 재발급<br>(GitHub Settings → Developer settings에서 삭제).<br>[9.5절](09-python.md#section-9-5) |
| 작업 중인 파일이 있는데 급히 다른 브랜치로<br>가야 함 | 커밋하기엔 미완성 | 소스트리 스태시 → 브랜치 이동 → 돌아와서 스태시 적용<br>(수업 12주차) |
| 팀원이 갑자기 연락 두절 | 개인 사정 | [2.4절](02-team.md#section-2-4): 팀장 연락 → 회의록 기록 → 2주 시 교수 이메일.<br>담당 기능은 팀이 임시 인수 |
<!-- /source-page: 47 -->

[이전: 부록 D. 소스트리·명령어 대응표와 충돌 실습](appendix-d-git-drill.md) · [전체 목차](README.md) · [다음: 부록 F. 팀 약속 양식](appendix-f-team-template.md)
