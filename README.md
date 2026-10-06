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

[설치·명령·TUI 조작 방법](docs/tool.md)을 확인하세요.

```bash
pip install -r requirements.txt
python main.py
```

uv가 있다면 다음 명령으로 실행합니다.

```bash
uv run oss
uv run oss week 6
uv run oss guide search 회의록
uv run oss format minutes --output 회의록.md
```

첫 화면에서 주차별 할 일·회의록 양식 저장·검색·전체 안내서를 선택합니다. 주차별 할 일에서는 원하는 주차를 골라 할 일·제출물·개인 점검표를 확인합니다. 안내서 전체와 양식은 설치에 포함되어 오프라인으로 사용할 수 있습니다. 완료 상태 저장과 평가 자동화는 후속 작업입니다.
