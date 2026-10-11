# 9. Python 프로젝트 기본

[전체 목차](README.md) · [출처·검증](sources.md)

원문: v1.3 · 2026년 9월 · 26~27쪽. 아래 내용은 원문 전체 전사입니다. [팀 적용 사항](team-context.md)은 별도로 확인합니다.

<a id="page-26"></a>

## 원문 26쪽

<!-- source-page: 26 -->
<a id="chapter-9"></a>

## 9. Python 프로젝트 기본

<a id="section-9-1"></a>

### 9.1 Python 버전

- 3.12 이상 아무 버전. 팀원끼리 같은 버전(예: 3.13)이면 더 좋음. README에 '테스트한 버전'을 적어 둠

- 학기 중에는 설치한 버전을 바꾸지 않기 (10월 1일 출시 예정인 3.15로 갈아타지 않기)

<a id="section-9-2"></a>

### 9.2 폴더 구조

```text
moneylog/
├── main.py # 시작 파일: 메뉴를 보여 주고 각 기능을 호출
├── add.py # 기능 1 (팀원 A) ← 기능마다 파일 1개, 담당자 1명
├── summary.py # 기능 2 (팀원 B)
├── budget.py # 기능 3 (팀원 C)
├── chart.py # 기능 4 (팀원 D)
├── storage.py # 공통: 파일 읽기·쓰기 (개발 리드)
├── requirements.txt # 사용하는 라이브러리 목록
├── data/ # 샘플 데이터 (작은 파일만)
├── docs/ # 회의록, 팀 약속, 스크린샷
├── README.md LICENSE CONTRIBUTING.md CODE_OF_CONDUCT.md
└── .gitignore
```



> \[왜?\] 기능마다 파일을 나누고 담당자를 정하면 4명이 같은 파일을 고칠 일이 줄어 충돌이 거의 나지 않습니다. main.py와 공통 파일(storage.py)만 여럿이 손대므로, 이 파일을 고칠 때는 이슈 댓글로 먼저 알립니다.

<a id="section-9-3"></a>

### 9.3 설치와 실행 (README에 그대로 적을 내용)

```bash
# 1) 저장소 받기 (소스트리 Clone 또는 아래 명령)
git clone https://github.com/<팀장아이디>/moneylog.git
cd moneylog

# 2) 라이브러리 설치 (requirements.txt에 적힌 것을 한 번에)
pip install -r requirements.txt

# 3) 실행
python main.py
```

- 새 라이브러리를 쓰면 requirements.txt에 한 줄 추가(예: pandas)하고 같은 풀 리퀘스트에 포함. 팀원은 Pull 뒤 pip install -r requirements.txt를 다시 실행

- 웹(Streamlit)이나 봇은 실행 명령이 다르므로 README '실행' 절에 정확한 명령을 적음 (예: streamlit run main.py)
<!-- /source-page: 26 -->

<a id="page-27"></a>

## 원문 27쪽

<!-- source-page: 27 -->
<a id="section-9-4"></a>

### 9.4 코드 습관 (수업 3주차 '스타일 가이드')

- Python 표준 스타일 PEP 8을 따릅니다. VS Code Python 확장이 밑줄로 알려 주는 것만 고쳐도 충분

- 함수는 한 가지 일만, 30줄 안팎. 파일 하나가 300줄을 넘으면 나눔

- 이름은 영문으로 뜻이 보이게(monthly\_total), 주석과 문자열은 한글 가능

- 파일을 읽고 쓸 때는 open(path, encoding="utf-8") — Windows에서 한글 깨짐 방지

- 화면 출력(print, 입력)과 계산(함수)을 나누면 다른 팀원이 읽고 고치기 쉬움

<a id="section-9-5"></a>

### 9.5 저장소에 올리면 안 되는 것

| 올리지 말 것 | 대신 |
| --- | --- |
| API 키, 봇 토큰, 비밀번호, 개인정보 | config\_example.py에 키 이름만 적어 올리고, 실제 값은 각자 PC의 config.py에<br>(.gitignore에 config.py 추가). 올라갔으면 즉시 재발급 |
| 큰 데이터 파일(수십 MB) | data/에는 5MB 이하 샘플만. 원본은 다운로드 링크를 README에 |
| \_\_pycache\_\_/, 가상환경 폴더, 편집기 설정 | 저장소 생성 시 고른 Python .gitignore가 자동으로 제외함 |
<!-- /source-page: 27 -->

[이전: 8. 협업 루틴](08-collaboration.md) · [전체 목차](README.md) · [다음: 10. 활동 규칙](10-activity.md)
