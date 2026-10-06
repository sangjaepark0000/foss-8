"""Extract reusable source templates; writing requires an explicit destination."""
from pathlib import Path
import re

from .guide import display_markdown
from .weeks import cell


def report(catalog, name, title, anchor, count):
    """Derive report sections and submission rules from the checked source."""
    doc, _ = catalog.resolve(name)
    section = doc.markdown.split(f'<a id="{anchor}"></a>', 1)[1]
    section = re.split(r'<a id="section-[^"]+"></a>', section, maxsplit=1)[0]
    source = catalog.reference(doc, anchor)
    base_url = source["url"].split("#", 1)[0].rsplit("/", 1)[0] + "/"

    def portable_links(value):
        return re.sub(r"\]\(([^)]+)\)", lambda match: "](" + (base_url + match[1] if "://" not in match[1] else match[1]) + ")", value)

    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        columns = [cell(value) for value in line.strip().strip("|").split("|")]
        if len(columns) >= 3 and (columns[0].isdigit() or columns[0] == "+"):
            rows.append([portable_links(value) for value in columns])
    if sum(row[0].isdigit() for row in rows) != count:
        raise ValueError(f"{title}의 필수 항목 {count}개를 읽지 못했습니다. 원문 형식을 확인하세요.")
    lines = [f"# {title}", "", "> 안내서 요구사항에서 만든 작업용 Markdown 양식입니다. 제출용 PDF로 변환하기 전에 내용을 작성하세요.",
             "> 원문의 기능 4개 기준은 보존했습니다. 승인된 팀별 적용 사항은 [팀 결정](" + catalog.reference(*catalog.resolve("team"))["url"] + ")을 확인하세요.",
             "", "## 표지", "", "- 팀명: ", "- 프로젝트 이름: ", "- 팀원·GitHub 아이디: ",
             "- 저장소 주소: ", "- 작성일: ", "", "## 목차", ""]
    lines += [f"- {row[0] + '. ' if row[0].isdigit() else ''}{row[1]}" for row in rows]
    for row in rows:
        number, heading, requirement, *length = row
        lines += ["", f"## {number + '. ' if number.isdigit() else ''}{heading}", "", f"> 필수 내용: {requirement}"]
        if length and length[0] != "—":
            lines += [f"> 권장 분량: {length[0]}"]
        lines += ["", "[작성]", ""]
    rules = section if name != "proposal" else doc.markdown.split('<a id="section-5-2"></a>', 1)[1]
    table = re.search(r"<table>.*?</table>", rules, flags=re.S)
    if table is None:
        raise ValueError(f"{title} 제출 기준을 읽지 못했습니다.")
    lines += ["## 제출 기준", "", portable_links(display_markdown(cell(table[0])).strip()), "", f"[원문 요구사항]({source['url']})", ""]
    return {"title": title + " — 빈 양식", "content": "\n".join(lines), "derived": True, "source": source}


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
    for name, title, anchor, count in [("proposal", "제안서", "section-5-1", 7),
                                        ("midterm", "중간보고서", "section-13-1", 6),
                                        ("final", "최종보고서", "section-14-3", 8)]:
        result[name] = report(catalog, name, title, anchor, count)
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
