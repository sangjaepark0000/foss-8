# [부록 D](appendix-d-git-drill.md). 소스트리·명령어 대응표와 충돌 실습

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 45~46쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-45"></a>

## 원문 45쪽

<!-- source-page: 45 -->
## [부록 D](appendix-d-git-drill.md). 소스트리·명령어 대응표와 충돌 실습

<a id="appendix-d-1"></a>

### D-1. 소스트리 조작 ↔ Git Bash 명령 (수업 3·12·14주차)

같은 일을 두 가지 방법으로 할 수 있습니다. 활동 집계에는 차이가 없습니다.

| 하려는 일 | 소스트리 | Git Bash 명령 |
| --- | --- | --- |
| 저장소 받기 | Clone → 주소 → 폴더 → 클론 | git clone &lt;주소&gt; |
| 상태 보기 | 파일 상태, History | git status, git log --oneline --graph --all |
| 최신화 | main 체크아웃 → Pull | git switch main → git pull |
| 브랜치 만들기·이동 | 브랜치 → 이름 → 새 브랜치 체크아웃 / 사이드바<br>더블클릭 | git branch feature/x → git switch feature/x (또는<br>git switch -c feature/x) |
| 커밋 | 커밋 → +로 스테이지 → 메시지 → 커밋 | git add &lt;파일&gt; (전체는 git add .) → git commit -m "<br>메시지" |
| 마지막 커밋 정정 | 커밋 옵션 → 마지막 커밋 정정 | git commit --amend (Push 전에만) |
| 푸시 | Push → 브랜치 체크 → Push | 첫 푸시 git push -u origin feature/x, 이후 git push |
| 원격 변화 확인 | 패치 | git fetch |
| 병합 | 체크아웃 → 대상 커밋 우클릭 → 병합 | git switch main → git merge feature/x |
| 충돌 해결 후 | 파일 스테이지 → 커밋 → Push | git add &lt;파일&gt; → git commit → git push |
| 되돌리기(내 브랜치) | 커밋 우클릭 → 이 커밋까지 현재 브랜치 초기화 | git reset --hard HEAD~1 (Push 전에만) |
| 되돌리기(공용 브랜<br>치) | 커밋 우클릭 → 커밋 되돌리기 | git revert &lt;커밋ID&gt; |
| 잠시 치우기 | 스태시 → 설명 입력 / 스태시 적용 | git stash / git stash pop |
| 태그 | 태그 → 이름 → 태그 추가 → Push(모든 태그 푸<br>시) | git tag v1.0.0 → git push origin v1.0.0 |
| 브랜치 삭제 | 브랜치 우클릭 → 삭제 | git branch -d feature/x |



> \[참고\] 수업 14주차에서 배우는 rebase와 reset --hard, 12주차의 강제 푸시는 이력을 바꾸는 기능이라 여럿이 쓰는 브랜치에서는 위험합니다. 이 프로젝트에서는 병합(merge)과 풀 리퀘스트, 되돌릴 때는 리버트만 사용하세 요.

<a id="appendix-d-2"></a>

### D-2. 충돌 해결 실습 (9주차, 수업 9주차 직후, 2인 1조 20분)

수업 9주차 실습(학생A·학생B가 같은 파일을 고쳐 충돌)과 같은 상황을 팀 저장소에서 일부러 만듭니다. A·B가 끝나 면 C·D가 반복합니다.

1\. 준비(팀장): docs/drill.md에 현재 당번: (이름) 한 줄을 넣어 풀 리퀘스트로 병합

2\. A와 B 모두: 소스트리 main 체크아웃 → Pull
<!-- /source-page: 45 -->

<a id="page-46"></a>

## 원문 46쪽

<!-- source-page: 46 -->
3\. A: feature/drill-a 브랜치 → 그 줄을 현재 당번: A이름으로 수정 → 커밋 → Push → 풀 리퀘스트 → B가 Approve → A가 병합

4\. B: (A가 병합한 뒤, main을 Pull하지 말고) feature/drill-b 브랜치 → 같은 줄을 현재 당번: B이름으로 수정 → 커밋 → Push → 풀 리퀘스트 → 'This branch has conflicts' 확인

5\. B: [8.7절](08-collaboration.md#section-8-7) 순서대로 해결(main Pull → 내 브랜치에 main 병합 → VS Code에서 정리 → 커밋 → Push) → 충돌 표시가 사라지면 A가 Approve → 병합

6\. 회의록 활동 로그의 '충돌 해결' 칸에 B 1회 기록. 이어서 C·D 반복(역할을 바꾸면 4명 모두 1회)
<!-- /source-page: 46 -->

[이전: 부록 C. 템플릿 파일](appendix-c-templates.md) · [전체 목차](README.md) · [다음: 부록 E. 문제 해결 FAQ](appendix-e-faq.md)
