# 소개

부경대학교 오픈소스소프트웨어 수업의 팀 프로젝트 진행을 돕는 CLI 도구입니다.

프로젝트 안내서에 흩어져 있는 서식, 평가 기준, 주차별 일정을 터미널에서 쉽게 확인할 수 있도록 하는 것을 목표로 합니다.

## 팀원

| 이름 | 역할 | GitHub | 담당 기능 |
|---|---|---|---|
| 박상재 | 팀장 | @sangjaepark0000 | 서식 불러오기 |
| 양하윤 | 개발 리드 | @sheep-ship-it | 현재 주차와 해야 할 일 확인 |
| 백지훈 | 문서 담당 | @jihun31 | 평가 기준과 완료 여부 확인 |


## 팀프로젝트 안내서

[안내서 전체 목차](docs/guide/README.md)에서 일정·제출물·평가 기준·협업 규칙·양식·FAQ를 확인할 수 있습니다. 원문 전체와 [팀 적용 사항](docs/guide/team-context.md)을 함께 제공합니다.


## 실행 방법

### 1. 저장소 클론

```bash
git clone https://github.com/sangjaepark0000/foss-8.git
cd foss-8
```

### 2. 서식 조회

Python 3.12 이상에서 실행합니다. 서식 조회에는 외부 라이브러리가 필요하지 않습니다.

```bash
python main.py format             # 지원 양식 목록
python main.py format minutes     # 빈 회의록
python main.py format proposal    # 제안서
python main.py format midterm     # 중간보고서
python main.py format final       # 최종보고서
python main.py format --help
```

회의록은 안내서 부록 B의 제목·표 열을 유지하고 예시 이름·날짜·진행 상황·완료 표시를 비운 양식입니다.
보고서는 안내서의 제안서 7항목·중간보고서 6항목·최종보고서 8항목과 부록을 읽어
표지·목차·작성란·필수 내용·분량·제출 기준·원문 링크를 제공합니다.

출력된 Markdown에 내용을 작성한 후 PDF로 변환해 제출합니다.
팀명·팀원·주차·활동 로그 자동 채움과 파일 저장은 후속 작업입니다.

### 검증

```bash
python -m unittest discover -s tests -v
python scripts/check_guide.py
```
