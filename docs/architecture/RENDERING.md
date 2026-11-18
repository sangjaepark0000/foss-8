# 다이어그램 재생성

[전체 지도](README.md)

Mermaid 원본은 `diagrams/*.mmd`, 렌더링 결과는 `rendered/*.svg`이다. Markdown 문서는 Mermaid 코드 블록도 포함하므로 GitHub에서 직접 볼 수 있다. `index.html`은 로컬 SVG를 읽으며 네트워크를 사용하지 않는다.

검증에 사용한 도구: Mermaid CLI **12.2.0**, 시스템 Chromium, Noto Sans CJK KR. CLI는 프로젝트 런타임 의존성이 아니며 앱의 requirements.txt는 변경하지 않았다.

설치 예:

```bash
PUPPETEER_SKIP_DOWNLOAD=true npm install --prefix /tmp/foss8-diagram-tools --no-audit --no-fund @mermaid-js/mermaid-cli@12.2.0
```

Chromium 실행 파일을 지정한 Puppeteer 설정을 별도 파일로 만든다. 아래 경로는 Linux 환경의 예이며 자기 환경에 맞게 바꾼다.

```json
{"executablePath":"/usr/bin/chromium","args":["--disable-dev-shm-usage"]}
```

문서·Mermaid 생성:

```bash
python scripts/build_architecture.py
```

도표 하나 렌더링:

```bash
/tmp/foss8-diagram-tools/node_modules/.bin/mmdc \
  -i docs/architecture/diagrams/09-target-domain.mmd \
  -o docs/architecture/rendered/09-target-domain.svg \
  -c docs/architecture/mermaid-config.json \
  -p /경로/puppeteer.json \
  --no-font-embed
```

전체 렌더링:

```bash
python scripts/render_architecture.py \
  --cli /tmp/foss8-diagram-tools/node_modules/.bin/mmdc \
  --puppeteer-config /경로/puppeteer.json
```

`source-index.json`은 기준 커밋에서 추출한 자료이며, 기준 커밋을 바꾸면 코드 근거·문서 설명도 함께 다시 검토해야 한다. 생성 스크립트만 실행했다고 최신 구현과 의미가 일치하는 것은 아니다.

`validation.json`은 이번 생성물에 대한 검사 결과이며 자동으로 갱신되는 CI 배지가 아니다. 도표를 수정했다면 렌더링·문서 링크·도형 배치를 다시 확인한다.
