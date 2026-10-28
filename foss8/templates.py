"""Generate blank minutes and report forms from the bundled handbook."""
import re

from .guide import display_markdown


TITLES = {
    "minutes": "회의록",
    "proposal": "제안서",
    "midterm": "중간보고서",
    "final": "최종보고서",
}
REPORTS = {
    "proposal": ("section-5-1", 7),
    "midterm": ("section-13-1", 6),
    "final": ("section-14-3", 8),
}


def cell(value):
    """Join print line breaks within words, keep space after filenames/punctuation."""
    value = re.sub(r"([),]|\.md|\.py)<br>", r"\1 ", value)
    return value.replace("<br>", "").strip()


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
    if fence is not None:
        raise ValueError("회의록 원문 양식의 코드 블록이 닫히지 않았습니다.")
    return blocks


def blank_minutes(example):
    """Keep headings and table columns, remove the example's facts and statuses."""
    lines, previous_table = [], False
    for line in example.splitlines():
        line = line.replace("부록 A 6주차", "부록 A 해당 주차")
        if line.startswith("- "):
            label = line.split(":", 1)[0]
            if label == "- 참석":
                line = "- 참석: / 불참: "
            elif label in ("- 일시", "- 방식", "- 서기"):
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
                columns = len(line.split("|")) - 2
                lines.append("| " + " | ".join([""] * columns) + " |")
            previous_table = True
            continue
        previous_table = False
        lines.append(line)
    return "\n".join(lines) + "\n"


def minutes(catalog):
    doc, anchor = catalog.resolve("appendix-b-minutes-template#page-40")
    blocks = code_blocks(doc.markdown)
    if len(blocks) != 1:
        raise ValueError("회의록 원문 양식 1개를 읽지 못했습니다. 원문 형식을 확인하세요.")
    source = catalog.reference(doc, anchor)
    content = blank_minutes(blocks[0])
    content += f"\n[원문 양식]({source['url']})\n"
    return {"title": "회의록 — 빈 양식", "content": content,
            "derived": True, "source": source}


def report(catalog, name):
    anchor, count = REPORTS[name]
    title = TITLES[name]
    doc, _ = catalog.resolve(f"{name}#{anchor}")
    section = doc.markdown.split(f'<a id="{anchor}"></a>', 1)[1]
    section = re.split(r'<a id="section-[^"]+"></a>', section, maxsplit=1)[0]
    source = catalog.reference(doc, anchor)
    base_url = source["url"].split("#", 1)[0].rsplit("/", 1)[0] + "/"

    def portable_links(value):
        return re.sub(r"\]\(([^)]+)\)",
                      lambda match: "](" + (base_url + match[1] if "://" not in match[1] else match[1]) + ")",
                      value)

    rows = []
    for line in section.splitlines():
        if not line.startswith("|"):
            continue
        columns = [cell(value) for value in line.strip().strip("|").split("|")]
        if len(columns) >= 3 and (columns[0].isdigit() or columns[0] == "+"):
            rows.append([portable_links(value) for value in columns])
    if sum(row[0].isdigit() for row in rows) != count:
        raise ValueError(f"{title}의 필수 항목 {count}개를 읽지 못했습니다. 원문 형식을 확인하세요.")
    lines = [f"# {title}", "",
             "> 안내서 요구사항에서 만든 작업용 Markdown 양식입니다. 내용을 작성한 후 제출용 PDF로 변환하세요.",
             "> 원문의 기능 4개 기준은 보존했습니다. 팀별 조정은 승인 근거를 별도로 기록하세요.",
             "", "## 표지", "", "- 팀명: ", "- 프로젝트 이름: ",
             "- 팀원·GitHub 아이디: ", "- 저장소 주소: ", "- 작성일: ", "", "## 목차", ""]
    lines += [f"- {row[0] + '. ' if row[0].isdigit() else ''}{row[1]}" for row in rows]
    for number, heading, requirement, *length in rows:
        lines += ["", f"## {number + '. ' if number.isdigit() else ''}{heading}", "",
                  f"> 필수 내용: {requirement}"]
        if length and length[0] != "—":
            lines += [f"> 권장 분량: {length[0]}"]
        lines += ["", "[작성]", ""]
    rules = catalog.show("proposal#section-5-2")["markdown"] if name == "proposal" else section
    table = re.search(r"<table>.*?</table>", rules, flags=re.S)
    if table is None:
        raise ValueError(f"{title} 제출 기준을 읽지 못했습니다.")
    lines += ["## 제출 기준", "", portable_links(display_markdown(cell(table[0])).strip()),
              "", f"[원문 요구사항]({source['url']})", ""]
    return {"title": title + " — 빈 양식", "content": "\n".join(lines),
            "derived": True, "source": source}


def get(catalog, name, team_config=None):
    if name not in TITLES:
        raise ValueError(f"알 수 없는 양식: {name}. 지원 양식: {', '.join(TITLES)}")
    item = minutes(catalog) if name == "minutes" else report(catalog, name)
    item = {"id": name, **item}
    if team_config is not None:
        content = item["content"]
        if name == "minutes":
            # Attendance and actual progress stay blank; membership does not prove attendance.
            content = content.replace("회의록 — 팀명", "회의록 — " + team_config["name"], 1)
        else:
            content = content.replace("- 팀명: \n", "- 팀명: " + team_config["name"] + "\n", 1)
            content = content.replace("- 저장소 주소: \n", "- 저장소 주소: " + team_config["repository"] + "\n", 1)
            people = ", ".join(f'{p["name"]} (@{p["github"]})' for p in team_config["members"])
            content = content.replace("- 팀원·GitHub 아이디: \n", "- 팀원·GitHub 아이디: " + people + "\n", 1)
            content = content.replace(f"[{TITLES[name]}] 팀명.pdf",
                                      f"[{TITLES[name]}] {team_config['name']}.pdf")
        item["content"] = content
    return item
