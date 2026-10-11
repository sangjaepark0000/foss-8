"""Read the same checked-in handbook from a checkout or an installed wheel."""
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from importlib.resources import files
from pathlib import Path
import json
import re
import unicodedata


ALIASES = {
    "home": "README", "minutes": "12-minutes", "calendar": "03-roadmap",
    "evaluation": "15-evaluation", "activity": "10-activity",
    "templates": "appendix-c-templates", "checklist": "appendix-a-checklist",
    "team": "team-context", "proposal": "05-proposal", "midterm": "13-midterm",
    "final": "14-release-final", "faq": "appendix-e-faq",
}

CATEGORIES = {
    "하려는 일": ["minutes", "proposal", "midterm", "final", "08-collaboration", "11-contributions"],
    "주차·활동·평가": ["calendar", "checklist", "activity", "evaluation", "01-overview"],
    "양식·템플릿": ["appendix-b-minutes-template", "templates", "appendix-f-team-template"],
    "팀 결정·출처": ["team", "sources"],
}


def plain(value):
    value = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", value)
    return unescape(re.sub(r"<[^>]+>", "", value)).replace("\\_", "_").replace("\\[", "[").replace("\\]", "]")


def folded(value):
    return unicodedata.normalize("NFKC", plain(value)).casefold()


class Table(HTMLParser):
    """Display the source's headerless HTML tables in a terminal Markdown viewer."""
    def __init__(self):
        super().__init__()
        self.rows, self.row, self.cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag in ("td", "th"):
            self.cell = []
        elif tag == "br" and self.cell is not None:
            self.cell.append(" / ")
        elif tag == "a" and self.cell is not None and dict(attrs).get("href"):
            self.cell.append("[")
            self.href = dict(attrs)["href"]

    def handle_endtag(self, tag):
        if tag == "a" and self.cell is not None and getattr(self, "href", None):
            self.cell.append(f"]({self.href})")
            self.href = None
        elif tag in ("td", "th") and self.cell is not None:
            self.row.append("".join(self.cell).replace("|", "\\|"))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None

    def handle_data(self, value):
        if self.cell is not None:
            self.cell.append(value)

    def markdown(self):
        width = max(map(len, self.rows), default=0)
        if not width:
            return ""
        headings = ["항목", "내용"] if width == 2 else [""] * width
        lines = ["| " + " | ".join(headings) + " |", "| " + " | ".join(["---"] * width) + " |"]
        lines += ["| " + " | ".join(row + [""] * (width - len(row))) + " |" for row in self.rows]
        return "\n\n" + "\n".join(lines) + "\n\n"


def display_markdown(markdown):
    """Normalize print markup for display only; never change the source files."""
    # Split code first: literal HTML and links in copied examples must stay literal.
    def narrative(value):
        def table(match):
            parser = Table()
            parser.feed(match[0])
            return parser.markdown()
        value = re.sub(r"<table>.*?</table>", table, value, flags=re.S)
        value = re.sub(r"<a\s+href=\"([^\"]+)\">(.*?)</a>", r"[\2](\1)", value)
        value = re.sub(r"<a id=\"[^\"]+\"></a>|<!--.*?-->", "", value, flags=re.S)
        return unescape(value.replace("<br>", " / "))
    pieces, buffer, fence = [], [], None
    for line in markdown.splitlines():
        match = re.match(r"^(`{3,})", line)
        if match and fence is None:
            pieces.append(narrative("\n".join(buffer)))
            buffer, fence = [line], len(match[1])
        elif match and fence is not None and len(match[1]) >= fence:
            buffer.append(line)
            pieces.append("\n".join(buffer))
            buffer, fence = [], None
        else:
            buffer.append(line)
    pieces.append("\n".join(buffer) if fence else narrative("\n".join(buffer)))
    return "\n".join(pieces)


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    markdown: str
    pages: tuple[int, ...]


class Catalog:
    def __init__(self):
        local = Path(__file__).resolve().parents[1] / "docs/guide"
        self.root = local if (local / "source-map.json").exists() else files("foss8").joinpath("data/guide")
        self.manifest = json.loads(self.root.joinpath("source-map.json").read_text(encoding="utf-8"))
        documents = []
        for path in sorted(self.root.iterdir(), key=lambda item: item.name):
            if not path.name.endswith(".md"):
                continue
            markdown = path.read_text(encoding="utf-8")
            title = plain(markdown.splitlines()[0].lstrip("# "))
            pages = tuple(int(n) for n in re.findall(r"<!-- source-page: (\d+) -->", markdown))
            documents.append(Document(path.name[:-3], title, markdown, pages))
        self.documents = {doc.id: doc for doc in documents}

    def resolve(self, selector):
        name, _, anchor = selector.partition("#")
        if name.endswith(".md"):
            name = name[:-3]
        name = ALIASES.get(name, name)
        if name not in self.documents:
            raise ValueError(f"알 수 없는 문서: {selector}. oss guide list로 ID를 확인하세요.")
        doc = self.documents[name]
        if anchor and f'<a id="{anchor}"></a>' not in doc.markdown:
            raise ValueError(f"알 수 없는 원문 위치: {selector}")
        return doc, anchor

    def reference(self, doc, anchor=""):
        return {
            "document": doc.id + ".md", "anchor": anchor or None, "pages": list(doc.pages),
            "handbook": "OSS_팀프로젝트_안내서_2026-2_공개용.pdf",
            "sha256": self.manifest["sha256"],
            "url": f"https://github.com/sangjaepark0000/foss-8/blob/78a5fda3ebc25f1bf74f809d0b40a2b6397acbf9/docs/guide/{doc.id}.md" + (f"#{anchor}" if anchor else ""),
            "scope": "team-decision" if doc.id == "team-context" else "handbook" if doc.pages else "navigation",
        }

    def show(self, selector):
        doc, anchor = self.resolve(selector)
        markdown = doc.markdown
        if anchor:
            markdown = markdown.split(f'<a id="{anchor}"></a>', 1)[1]
        return {"id": doc.id, "title": doc.title, "markdown": markdown,
                "source": self.reference(doc, anchor)}

    def listing(self):
        return [{"id": doc.id, "title": doc.title, "source": self.reference(doc)} for doc in self.documents.values()]

    def search(self, query, limit=30):
        terms = folded(query).split()
        if not terms:
            raise ValueError("검색어를 입력하세요.")
        hits = []
        for doc in self.documents.values():
            anchor, page, heading, fence = "", None, doc.title, None
            for number, line in enumerate(doc.markdown.splitlines(), 1):
                found = re.search(r'<a id="([^\"]+)"', line)
                if found:
                    anchor = found[1]
                found = re.search(r"<!-- source-page: (\d+) -->", line)
                if found:
                    page = int(found[1])
                match = re.match(r"^(`{3,})", line)
                if match:
                    fence = len(match[1]) if fence is None else None if len(match[1]) >= fence else fence
                    continue
                if not fence and line.startswith("#"):
                    heading = plain(line.lstrip("# "))
                if not line.strip() or line.startswith(("<!--", "<a id=")):
                    continue
                text = folded(line)
                if all(term in text for term in terms):
                    source = self.reference(doc, anchor)
                    if page:
                        source["pages"] = [page]
                    snippet = plain(line).strip()
                    index = text.find(terms[0])
                    start = max(0, index - 60)
                    snippet = ("…" if start else "") + snippet[start:start + 240]
                    hits.append({"id": doc.id, "title": doc.title, "heading": heading,
                                 "line": number, "excerpt": snippet, "source": source,
                                 "selector": doc.id + (f"#{anchor}" if anchor else "")})
        def rank(hit):
            title = folded(hit["title"])
            heading = folded(hit["heading"])
            return sum(4 * (term in title) + 2 * (term in heading) for term in terms) - (3 if hit["id"] == "00-introduction" else 0)
        hits.sort(key=rank, reverse=True)
        return hits[:limit], len(hits)
