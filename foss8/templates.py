"""Extract reusable source templates; writing requires an explicit destination."""
from pathlib import Path
import re


def code_blocks(markdown):
    blocks, lines, fence = [], [], None
    for line in markdown.splitlines():
        match = re.match(r"^(`{3,})\w*\s*$", line)
        if match and fence is None:
            lines, fence = [], len(match[1])
        elif match and fence is not None and len(match[1]) >= fence:
            blocks.append("\n".join(lines) + "\n")
            fence = None
        elif fence is not None:
            lines.append(line)
    return blocks


def blank_minutes(example):
    """Keep the source form's headings and columns, remove fictional sample facts."""
    lines, previous_table = [], False
    for line in example.splitlines():
        line = line.replace("부록 A 6주차", "부록 A 해당 주차")
        if line.startswith("- "):
            label = line.split(":", 1)[0]
            if label in ("- 일시", "- 방식", "- 참석", "- 서기"):
                line = label + ": "
            elif "예산 저장" in line:
                line = "- 결정: / 이유: "
            elif "[x]" in line:
                line = "- [ ] 해당 주차의 부록 A 점검 항목 확인"
        if line.startswith("|"):
            if not previous_table:
                lines.append(line)
            elif re.fullmatch(r"\|[\s|:\-]+\|", line):
                lines.append(line)
                cells = len(line.split("|")) - 2
                lines.append("| " + " | ".join([""] * cells) + " |")
            previous_table = True
            continue
        previous_table = False
        lines.append(line)
    return "\n".join(lines) + "\n"


def listing(catalog):
    doc, _ = catalog.resolve("appendix-b-minutes-template")
    example = code_blocks(doc.markdown)[0]
    result = {
        "minutes": {"title": "회의록 — 빈 양식", "content": blank_minutes(example), "derived": True,
                    "source": catalog.reference(doc, "page-40")},
        "minutes-example": {"title": "회의록 — 원문 작성 예시", "content": example, "derived": False,
                            "source": catalog.reference(doc, "page-40")},
    }
    doc, _ = catalog.resolve("templates")
    names = ["readme", "contributing", "code-of-conduct", "requirements", "main", "gitignore", "pull-request"]
    for number, name in enumerate(names, 1):
        anchor = f"appendix-c-{number}"
        section = doc.markdown.split(f'<a id="{anchor}"></a>', 1)[1]
        section = re.split(r'<a id="appendix-c-\d+"></a>', section, maxsplit=1)[0]
        blocks = code_blocks(section)
        title = next(plain_heading(line) for line in section.splitlines() if line.startswith("### "))
        result[name] = {"title": title, "content": "\n".join(blocks), "derived": False,
                        "source": catalog.reference(doc, anchor)}
    doc, _ = catalog.resolve("appendix-f-team-template")
    result["team-agreement"] = {"title": "팀 약속 — 원문 양식", "content": "\n".join(code_blocks(doc.markdown)),
                                "derived": False, "source": catalog.reference(doc, "page-48")}
    return result


def plain_heading(value):
    return value.lstrip("# ").replace("\\_", "_")


def get(catalog, name):
    items = listing(catalog)
    if name not in items:
        raise ValueError(f"알 수 없는 양식: {name}. oss format --list로 확인하세요.")
    return {"id": name, **items[name]}


def save(content, destination, force=False):
    path = Path(destination).expanduser()
    with path.open("w" if force else "x", encoding="utf-8") as stream:
        stream.write(content)
    return str(path.resolve())
