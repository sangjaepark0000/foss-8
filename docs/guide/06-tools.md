# 6. 준비하기: 계정과 도구

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 16~18쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-16"></a>

## 원문 16쪽

<!-- source-page: 16 -->
<a id="chapter-6"></a>

## 6. 준비하기: 계정과 도구 (3~6 주차, 각자)

필요한 것은 수업 3주차(GitHub·Git)와 6주차(소스트리·VS Code, 10/9 온라인)에서 설치하는 것과 같습니다. 수업 시간에 따라 했다면 [6.6절](06-tools.md#section-6-6) 체크리스트만 확인하세요. 아래는 수업 자료를 요약한 것이며, 자세한 화면은 해당 주차 강 의자료를 보면 됩니다.

<a id="section-6-1"></a>

### 6.1 필요한 것

| 항목 | 용도 | 수업 | 비고 |
| --- | --- | --- | --- |
| GitHub 계정 | 저장소·이슈·풀 리퀘스트·리뷰 | 3주차 | 학교 이메일(@pukyong.ac.kr 또는 @pknu.ac.kr)을 계<br>정에 추가해 두면 GitHub Student Developer Pack 신<br>청 가능(선택) |
| 개인 액세스 토큰 | Git Bash에서 push할 때 비밀번호<br>대신 사용 | 3주차 | 생성 직후 복사해 메모장에 보관 (다시 볼 수 없음) |
| Git (Git Bash) | 버전 관리 도구 | 3주차 | git-scm.com 설치 파일 |
| 소스트리 | Git을 버튼으로 다루는 GUI | 6주차 | sourcetreeapp.com. 이 안내서의 기본 도구 |
| VS Code | 코드·문서 편집 | 6주차 | code.visualstudio.com + Korean Language Pack,<br>Python 확장 |
| Python | 프로그램 실행 | 2주차 예시 | python.org |

<a id="section-6-2"></a>

### 6.2 GitHub 계정과 토큰 (수업 3주차)

1\. github.com → Sign up → 이메일·비밀번호·아이디 입력 → 이메일로 온 코드 입력 → 가입 완료. 아이디는 포트폴리오에 남으므로 알아보기 쉬운 영문으로

2\. 프로필 → Settings → Emails 에서 학교 이메일 추가(선택). 같은 화면의 'Keep my email addresses private'가 켜져 있으면 숫자+아이디@users.noreply.github.com 주소가 보이는데, Git·소스트리에 이메일을 넣을 때 이 주소를 써도 됨

3\. 토큰: Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic) → Note에 OSS 프로젝트, Expiration은 12월 이후, 권한(scope)에서 repo 체크 → Generate token → 복사해 보관

> \[왜?\] 커밋이 내 GitHub Contribution 그래프에 집계되려면 Git과 소스트리에 입력한 이메일이 GitHub 계정의 이메일(또는 noreply 주소)과 같아야 합니다. [6.3절](06-tools.md#section-6-3)과 [6.4절](06-tools.md#section-6-4)에서 같은 이메일을 넣으세요.

<a id="section-6-3"></a>

### 6.3 Git 설치와 첫 설정 (수업 3주차)

- Windows: git-scm.com/downloads → Download for Windows → 설치 파일 실행 → 계속 Next → Finish. 시작 메뉴에서 Git Bash 실행
<!-- /source-page: 16 -->

<a id="page-17"></a>

## 원문 17쪽

<!-- source-page: 17 -->
- macOS: 터미널(Spotlight에서 'terminal')에서 git --version 입력 → 설치 안내 창이 뜨면 설치 (Xcode Command Line Tools) Git Bash(또는 macOS 터미널)에서 내 정보를 등록합니다. 수업 3주차 '첫 번째 커밋 만들기'와 같은 명령입니다.

```bash
git config --global user.name "홍길동"
git config --global user.email "GitHub에 등록한 이메일"
git config --global core.editor "code --wait" # 커밋·병합 메시지 편집기를 VS Code로 (수업 14주차 권장)
git --version # git version 2.4x 가 나오면 성공
```



> \[TIP\] Git Bash에서 처음 git push를 하면 GitHub 로그인 창이 뜹니다. 브라우저로 로그인하거나, 비밀번호 칸 에 [6.2절](06-tools.md#section-6-2)의 토큰을 붙여 넣으면 됩니다. 한 번 로그인하면 Windows가 기억합니다.

<a id="section-6-4"></a>

### 6.4 소스트리와 VS Code (수업 6주차)

1\. sourcetreeapp.com → 운영체제에 맞는 파일 다운로드 → 설치. Bitbucket 로그인 화면은 건너뛰기, Mercurial 체크 해제, 이름·이메일은 GitHub과 같게 입력, SSH 키는 아니오

2\. 소스트리 → Remote → 계정 추가 → 호스팅 서비스 GitHub → OAuth 토큰 새로고침 → 브라우저에서 GitHub 로그인 → 확인. 원격 저장소 목록에 내 저장소가 보이면 성공

3\. code.visualstudio.com → 다운로드·설치. 왼쪽 확장에서 Korean Language Pack과 Python(Microsoft) 설치

4\. 소스트리 상단의 터미널 버튼을 누르면 저장소 폴더에서 Git Bash가 열립니다. pip·python 명령은 여기서 실행하면 됩니다

<a id="section-6-5"></a>

### 6.5 Python 설치

1\. python.org/downloads → 최신 안정 버전(3.12~3.14) 설치. Windows는 설치 첫 화면의 \`Add python.exe to PATH\` 체크가 중요

2\. 확인: Git Bash 또는 CMD에서 python --version, pip --version

3\. 라이브러리 설치는 수업 2주차 예시처럼 pip install 이름. 팀 프로젝트에서는 requirements.txt에 적어 두고 pip install -r requirements.txt로 한 번에 설치(9.3)

> \[참고\] Python 3.15가 출시될 예정이지만, 라이브러리 호환 문제를 피하기 위해 학기 중에는 설치한 버전을 바꾸 지 마세요.
<!-- /source-page: 17 -->

<a id="page-18"></a>

## 원문 18쪽

<!-- source-page: 18 -->
<a id="section-6-6"></a>

### 6.6 준비 완료 체크리스트 (6주차까지)

| 확인 항목 | 완료 |
| --- | --- |
| GitHub 계정, 토큰 보관, (선택) 학교 이메일 등록 | ☐ |
| git --version 정상, user.name·user.email 등록(이메일은 GitHub과 동일) | ☐ |
| 수업 3주차 실습 저장소(OSS)에 커밋 2개 이상 push 완료 | ☐ |
| 소스트리 설치 + GitHub 계정 연결(Remote에 내 저장소가 보임) | ☐ |
| VS Code + Korean Language Pack + Python 확장 | ☐ |
| python --version 정상(3.12 이상) | ☐ |
| 팀 저장소 초대 수락 → 소스트리로 클론 완료(7.4) | ☐ |
<!-- /source-page: 18 -->

[이전: 5. 프로젝트 제안서](05-proposal.md) · [전체 목차](README.md) · [다음: 7. 팀 저장소 만들기](07-repository.md)
