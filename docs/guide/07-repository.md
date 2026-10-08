# 7. 팀 저장소 만들기

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 19~21쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-19"></a>

## 원문 19쪽

<!-- source-page: 19 -->
<a id="chapter-7"></a>

## 7. 팀 저장소 만들기 (2~6 주차)

저장소 생성과 협력자 등록은 GitHub 웹에서 하므로 2주차에 바로 할 수 있습니다. 클론은 6주차(10/9 온라인 수업) 에 소스트리를 배운 뒤, 브랜치 보호는 9주차에 풀 리퀘스트를 시작하면서 켭니다.

<a id="section-7-1"></a>

### 7.1 저장소 생성 (팀장, 2주차)

1\. GitHub → 오른쪽 위 + → New repository

2\. Owner: 팀장 계정 / Repository name: 프로젝트 이름 (영문 소문자·숫자, 예: moneylog, busanair)

3\. Description: 한 줄 소개 (한글 가능)

4\. Public 선택

5\. Add a README file 체크 / .gitignore template → Python / Choose a license → MIT License

6\. Create repository

> \[왜?\] Public이어야 하는 이유: 타 팀이 Fork해서 기여하려면 볼 수 있어야 하고, 공개 저장소의 활동만 프로필의 Contribution 그래프에 표시되며, 브랜치 보호 규칙도 무료 계정에서는 공개 저장소에만 제공됩니다. 비공개 저장 소는 인정되지 않습니다.



> \[참고\] 라이선스는 수업 2주차에서 배운 방임형 라이선스 MIT를 기본으로 합니다. 다른 OSI 승인 라이선스를 고 르면 제안서에 이유를 한 줄 적으세요. 라이선스 파일이 없으면 오픈소스가 아닙니다(수업 3주차).

<a id="section-7-2"></a>

### 7.2 팀원 협력자(Collaborator) 등록 (수업 11 주차 '협력자 등록'과 같은 화면)

1\. 저장소 → Settings → Collaborators → Add people → 팀원 GitHub 아이디 입력 → Add

2\. 팀원은 GitHub 알림 또는 이메일에서 Accept invitation. 초대는 7일 뒤 만료되므로 당일 수락

3\. 확인: Collaborators 목록에 팀원 3명이 표시되면 완료

<a id="section-7-3"></a>

### 7.3 기본 파일 넣기 (팀장, 5주차 이후, GitHub 웹에서)

소스트리를 배우기 전이므로 GitHub 웹에서 만듭니다. 저장소 → Add file → Create new file → 파일 이름 입력(폴 더는 docs/meetings/README.md처럼 /로) → [부록 C](appendix-c-templates.md) 내용 붙여넣기 → Commit changes. 파일 이름의 moneylog는 여러분의 프로젝트 이름으로 바꿉니다.
<!-- /source-page: 19 -->

<a id="page-20"></a>

## 원문 20쪽

<!-- source-page: 20 -->
```text
moneylog/
├── README.md # 소개·설치·실행·팀원 (부록 C-1) — 생성 시 자동 생성된 파일을 고쳐 씀
├── LICENSE # MIT (생성 시 자동)
├── .gitignore # Python 템플릿 (생성 시 자동)
├── CONTRIBUTING.md # 기여 방법 (부록 C-2)
├── CODE_OF_CONDUCT.md # 행동 수칙 (부록 C-3, 수업 3·13주차 '필수 파일')
├── requirements.txt # 사용하는 라이브러리 목록 (부록 C-4)
├── main.py # 프로그램 시작 파일 (부록 C-5)
└── docs/
    ├── meetings/README.md # 회의록 폴더 (내용: '회의록 저장 폴더')
    ├── members/ # 6주차에 각자 자기소개 파일 추가
    └── team-agreement.md # 팀 약속 (부록 F)
```

<a id="section-7-4"></a>

### 7.4 소스트리로 클론 (전원, 6주차)

1\. GitHub 팀 저장소 → 초록색 Code 버튼 → HTTPS 주소 오른쪽의 복사 버튼

2\. 소스트리 → Clone → 첫 칸에 주소 붙여넣기 → 둘째 칸 탐색으로 내 PC 의 폴더 선택(예: 바탕 화면/Programming/moneylog) → 클론

3\. 새 탭에 저장소가 열리고 History에 커밋이 보이면 성공. VS Code → 파일 → 폴더 열기로 같은 폴더를 엽니다

4\. 첫 커밋: VS Code에서 docs/members/&lt;내이름&gt;.md 파일을 만들어 자기소개 3줄 저장 → 소스트리 커밋 → 파일 옆 +로 스테이지 → 메시지 홍길동 자기소개 추가 → -에 바뀐 내용 즉시 푸시 체크 → 커밋 (수업 6주차 실습과 동일)

> \[주의\] Push가 거부되면(다른 팀원이 먼저 올림) 소스트리 상단 Pull → Pull 버튼 → 다시 Push. 여러 명이 main 에 직접 올리는 것은 6주차까지만이며, 7주차부터는 각자 브랜치에서 작업합니다.

<a id="section-7-5"></a>

### 7.5 main 브랜치 보호 (팀장, 9주차) — 수업 13주차 '브랜치 보호하기'와 동일

풀 리퀘스트를 시작하는 9주차에 켭니다. 켜고 나면 누구도(팀장 포함) main에 직접 커밋할 수 없고, 리뷰 승인 1개 없 이는 병합할 수 없습니다. 실수로 main을 망가뜨리는 사고를 막아 주는 안전장치입니다.

1\. 저장소 → Settings → 왼쪽 Branches → Add classic branch protection rule

2\. Branch name pattern에 main 입력

3\. Require a pull request before merging 체크 → 그 아래 Require approvals 체크(숫자 1)

4\. 맨 아래 Do not allow bypassing the above settings 체크 → Create 확인: 소스트리에서 main에 직접 커밋해 Push하면 오류가 나고, 풀 리퀘스트는 승인 1개가 있어야 Merge pull request 버튼이 켜집니다. 본인 풀 리퀘스트는 본인이 승인할 수 없습니다.
<!-- /source-page: 20 -->

<a id="page-21"></a>

## 원문 21쪽

<!-- source-page: 21 -->
<a id="section-7-6"></a>

### 7.6 선택: 라벨과 Project 보드

- 라벨은 GitHub 기본 라벨을 사용: enhancement(기능), bug, documentation, question, good first issue(타 팀 기여용)

- Project 보드(Projects 탭 → New project → Board)는 할 일을 Todo / In Progress / Done으로 보고 싶을 때 씁니다. 필수는 아니며, 이슈 목록만으로도 충분합니다

| 저장소 준비 체크 | 담당 | 주차 | 완료 |
| --- | --- | --- | --- |
| 공개 저장소 + README + LICENSE(MIT) + .gitignore(Python) | 팀장 | 2주 | ☐ |
| 팀원 3명 협력자 등록·수락 | 팀장·팀원 | 2주 | ☐ |
| 기본 파일 6종(CONTRIBUTING, 행동 수칙, requirements.txt, main.py,<br>docs/meetings, 팀 약속) | 팀장 | 5주 | ☐ |
| 담당 기능 이슈 각자 3개 이상 | 전원 | 5~6주 | ☐ |
| 전원 소스트리 클론 + 자기소개 파일 커밋·Push | 전원 | 6주 | ☐ |
| main 브랜치 보호 규칙 | 팀장 | 9주 | ☐ |
<!-- /source-page: 21 -->

[이전: 6. 준비하기: 계정과 도구](06-tools.md) · [전체 목차](README.md) · [다음: 8. 협업 루틴](08-collaboration.md)
