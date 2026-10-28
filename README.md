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
빈 서식 출력은 유지하며, 아래 명령으로 기본정보를 채운 회의록을 파일로 저장할 수 있습니다.

### 3. 회의록 초안 생성

```bash
python main.py format minutes --date 2026-10-28 -o docs/meetings/2026-10-28.md
python main.py format minutes --date 2026-10-28 --week 9 --team foss-8 -o 회의록.md
```

회의 날짜 이후 가장 가까운 제출분을 골라 WEEK 번호·기록기간·제출 마감을 채웁니다.
10/28 회의는 WEEK9, 기록기간 10/15~10/28, 제출 마감 10/29 18:00입니다.
학사 주차는 화~월이며 회의 날짜·제출 회차·기록기간을 구분합니다. 8주차는 제출 회차가 없고,
시험 이후 10/29 제출분은 필요합니다. 12/11 보강 제출분을 지정하려면 `--week makeup`을 사용합니다.

팀 기본정보는 현재 프로젝트의 `.foss8/team.json`이 있으면 읽고, 없으면 Git 원격 저장소와 README 팀원 표에서 읽습니다.
파일을 직접 지정하려면 `--team-file 팀정보.json`을 사용합니다. 설정을 자동 생성하거나 변경하지 않습니다.

```json
{
  "name": "우리팀",
  "repository": "https://github.com/owner/repository",
  "members": [
    {"name": "가람", "github": "garam"},
    {"name": "나래", "github": "narae"}
  ]
}
```

팀원별 빈 행과 안내서의 해당 주차 할 일·점검표를 넣습니다. 실제 참석·서기·진행 상황·결정·활동 횟수·완료 체크는 비워 둡니다.
`-o`를 생략하면 화면에 출력합니다. 기존 파일은 보호하고 `--force`를 함께 지정했을 때만 교체합니다.
다른 보고서도 `python main.py format midterm -o 중간보고서.md`처럼 빈 양식을 저장할 수 있습니다.
활동 로그 수집과 지난 회의록 이어받기는 후속 작업입니다.

### 검증

```bash
python -m unittest discover -s tests -v
python scripts/check_guide.py
```
