# 원문과 검증

[전체 목차](README.md)

## 확정 원문

| 항목 | 값 |
| --- | --- |
| 파일 | [OSS_팀프로젝트_안내서_2026-2_공개용.pdf](source/OSS_팀프로젝트_안내서_2026-2_공개용.pdf) |
| 문서 제목 | 오픈소스소프트웨어 팀 프로젝트 안내서 (2026-2) |
| 저자 | 오상호 교수 · 국립부경대학교 컴퓨터·인공지능공학부 |
| 표지 버전 | v1.3 · 2026년 9월 |
| 분량 | PDF 실제 페이지 48쪽 |
| 원문 확정 | 2026-10-06 사용자 첨부 파일 |
| SHA-256 | `41cd32bf33db1af53a2ba07b699dd8cff166f66241987d037f5b2bc40d435fa5` |

이 전사는 첨부 파일을 기준으로 합니다. 앞서 대화에서 언급된 71쪽은 이 파일의 실제 페이지 수와 다르며, 23쪽 발표 자료를 덧붙여 구성하지 않았습니다. 기존 Basecamp 파일(파일명 끝에 `_변경` 포함)은 이 첨부 파일과 SHA-256이 동일합니다.

## 포함 범위와 편집 원칙

- 표지·원문 목차·사용법, 1~16장, 부록 A~F: **48/48쪽 포함**.
- 설명·일정·완성 기준·배점·활동 규칙·필수/주의/TIP·예시·명령·코드·양식·FAQ를 보존했습니다.
- 제외한 인쇄 요소는 반복되는 머리말, 쪽수 꼬리말, 대각선 이메일 워터마크입니다. 저자·연락처·버전은 표지 전사와 원문 PDF에 남아 있습니다.
- PDF 표는 Markdown 표 또는 제목 없는 HTML 표로 옮겼습니다. 원문에 없는 표 제목은 추가하지 않았습니다. 병합 셀 값은 첫 행에만 표시합니다.
- 코드·템플릿은 코드 블록으로 옮겼습니다. Python 예시의 최상위 `def main()`에 있던 한 글자 폭의 인쇄상 오프셋은 제거해 정상 들여쓰기로 맞췄습니다. 원문의 코드 내용은 유지했습니다.
- 공식 안내 내용과 팀 결정은 각각 원문 전사와 [팀 적용 사항](team-context.md)에 기록합니다.

## 검증 결과

- 페이지별 원문 PDF의 가로쓰기 문자와 Markdown 렌더링 결과의 한글·영문·숫자 개수 및 문자별 개수를 비교: **48/48쪽 일치, 총 33,355자**.
- 표 50개와 코드/템플릿 블록 15개를 문자 비교에 포함했습니다.
- 원문 페이지 전체의 레이아웃, 주요 표와 양식, Python 들여쓰기를 이미지와 대조했습니다.
- 원문 PDF 체크섬, 페이지 대응, 내부 파일·앵커 링크, 코드 블록 닫힘을 검사합니다.

문자 개수 비교는 글자 누락을 찾는 검사입니다. 읽는 순서·문장 의미·공백·구두점까지 자동으로 증명하지는 않으므로 원문 PDF와 표·코드의 시각 대조를 함께 했습니다. 검사 기준과 결과는 [source-map.json](source-map.json)에 있습니다.

저장소 루트에서 다음 명령으로 검증을 다시 실행할 수 있습니다. Python 표준 라이브러리만 사용합니다.

```bash
python3 scripts/check_guide.py
```

## 전체 페이지 대응표

쪽수는 PDF 페이지 번호와 원문에 인쇄된 쪽수가 같습니다.

| 원문 쪽 | 대응 Markdown | 비교한 한글·영문·숫자 |
| --- | --- | --- |
| 1 | [00-introduction.md](00-introduction.md#page-1) | 79 |
| 2 | [00-introduction.md](00-introduction.md#page-2) | 520 |
| 3 | [00-introduction.md](00-introduction.md#page-3) | 672 |
| 4 | [00-introduction.md](00-introduction.md#page-4) | 431 |
| 5 | [00-introduction.md](00-introduction.md#page-5) | 786 |
| 6 | [00-introduction.md](00-introduction.md#page-6) | 514 |
| 7 | [01-overview.md](01-overview.md#page-7) | 765 |
| 8 | [01-overview.md](01-overview.md#page-8) | 447 |
| 9 | [02-team.md](02-team.md#page-9) | 786 |
| 10 | [03-roadmap.md](03-roadmap.md#page-10) | 988 |
| 11 | [03-roadmap.md](03-roadmap.md#page-11) | 940 |
| 12 | [03-roadmap.md](03-roadmap.md#page-12) | 1097 |
| 13 | [04-topic.md](04-topic.md#page-13) | 769 |
| 14 | [04-topic.md](04-topic.md#page-14) | 404 |
| 15 | [05-proposal.md](05-proposal.md#page-15) | 521 |
| 16 | [06-tools.md](06-tools.md#page-16) | 984 |
| 17 | [06-tools.md](06-tools.md#page-17) | 932 |
| 18 | [06-tools.md](06-tools.md#page-18) | 214 |
| 19 | [07-repository.md](07-repository.md#page-19) | 814 |
| 20 | [07-repository.md](07-repository.md#page-20) | 977 |
| 21 | [07-repository.md](07-repository.md#page-21) | 360 |
| 22 | [08-collaboration.md](08-collaboration.md#page-22) | 1058 |
| 23 | [08-collaboration.md](08-collaboration.md#page-23) | 845 |
| 24 | [08-collaboration.md](08-collaboration.md#page-24) | 945 |
| 25 | [08-collaboration.md](08-collaboration.md#page-25) | 828 |
| 26 | [09-python.md](09-python.md#page-26) | 732 |
| 27 | [09-python.md](09-python.md#page-27) | 402 |
| 28 | [10-activity.md](10-activity.md#page-28) | 918 |
| 29 | [10-activity.md](10-activity.md#page-29) | 776 |
| 30 | [11-contributions.md](11-contributions.md#page-30) | 1036 |
| 31 | [11-contributions.md](11-contributions.md#page-31) | 596 |
| 32 | [12-minutes.md](12-minutes.md#page-32) | 807 |
| 33 | [13-midterm.md](13-midterm.md#page-33) | 724 |
| 34 | [14-release-final.md](14-release-final.md#page-34) | 901 |
| 35 | [14-release-final.md](14-release-final.md#page-35) | 584 |
| 36 | [15-evaluation.md](15-evaluation.md#page-36) | 591 |
| 37 | [15-evaluation.md](15-evaluation.md#page-37) | 583 |
| 38 | [16-help.md](16-help.md#page-38) | 943 |
| 39 | [appendix-a-checklist.md](appendix-a-checklist.md#page-39) | 740 |
| 40 | [appendix-b-minutes-template.md](appendix-b-minutes-template.md#page-40) | 432 |
| 41 | [appendix-c-templates.md](appendix-c-templates.md#page-41) | 536 |
| 42 | [appendix-c-templates.md](appendix-c-templates.md#page-42) | 716 |
| 43 | [appendix-c-templates.md](appendix-c-templates.md#page-43) | 595 |
| 44 | [appendix-c-templates.md](appendix-c-templates.md#page-44) | 226 |
| 45 | [appendix-d-git-drill.md](appendix-d-git-drill.md#page-45) | 949 |
| 46 | [appendix-d-git-drill.md](appendix-d-git-drill.md#page-46) | 248 |
| 47 | [appendix-e-faq.md](appendix-e-faq.md#page-47) | 1288 |
| 48 | [appendix-f-team-template.md](appendix-f-team-template.md#page-48) | 356 |
