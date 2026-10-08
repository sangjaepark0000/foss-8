"""Check handbook coverage, source identity, links and copied Python syntax.

Uses only the Python standard library. The baseline in source-map.json comes
from the source PDF's character objects, not from the generated Markdown.
"""
from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import ast
import json
import re


ROOT = Path(__file__).resolve().parents[1]
GUIDE = ROOT / "docs/guide"
BLOCK = re.compile(r"<!-- source-page: (\d+) -->\n(.*?)<!-- /source-page: \1 -->", re.S)


class Text(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def split_code(markdown):
    """Yield code and narrative separately so example links stay literal."""
    buffer, fence, kind = [], None, None
    for line in markdown.splitlines():
        match = re.match(r"^(`{3,})(\w*)\s*$", line)
        if match and not fence:
            if buffer:
                yield None, "\n".join(buffer)
            buffer, fence, kind = [], match[1], match[2]
        elif match and fence and len(match[1]) >= len(fence):
            yield kind or "text", "\n".join(buffer)
            buffer, fence, kind = [], None, None
        else:
            buffer.append(line)
    if fence:
        raise ValueError("Unclosed code fence")
    if buffer:
        yield None, "\n".join(buffer)


def visible(markdown):
    parts = []
    for language, value in split_code(markdown):
        if language:
            parts.append(value)
            continue
        value = re.sub(r"(?<!\\)\[([^\]\n]+)\]\([^\n)]+\)", r"\1", value)
        parser = Text()
        parser.feed(value)
        parts.extend(parser.parts)
    return "\n".join(parts)


def main():
    manifest = json.loads((GUIDE / "source-map.json").read_text())
    source = GUIDE / manifest["source_path"]
    assert sha256(source.read_bytes()).hexdigest() == manifest["sha256"], "Source PDF changed"
    files = {path: path.read_text() for path in GUIDE.glob("*.md")}
    pages = {}
    for path, markdown in files.items():
        for number, content in BLOCK.findall(markdown):
            number = int(number)
            assert number not in pages, f"Duplicate source page {number}"
            pages[number] = (path.name, content)
    assert sorted(pages) == list(range(1, manifest["pages"] + 1)), "Missing source page"
    total = 0
    for entry in manifest["page_map"]:
        filename, content = pages[entry["page"]]
        assert filename == entry["file"], f"Page {entry['page']} moved without updating map"
        counts = Counter(c for c in visible(content) if c.isalnum())
        checksum = sha256(json.dumps(sorted(counts.items()), ensure_ascii=False).encode()).hexdigest()
        assert checksum == entry["character_multiset_sha256"], f"Page {entry['page']} source text changed"
        assert sum(counts.values()) == entry["alphanumeric_characters"]
        total += sum(counts.values())
    links, python_examples = 0, 0
    for path, markdown in files.items():
        anchors = set(re.findall(r'<a id="([^"]+)"', markdown))
        assert len(anchors) == len(re.findall(r'<a id="([^"]+)"', markdown)), f"Duplicate anchor in {path.name}"
        for language, value in split_code(markdown):
            if language == "python":
                ast.parse(value)
                python_examples += 1
            if language:
                continue
            targets = re.findall(r"(?<!\\)\[[^\]\n]+\]\(([^\n)]+)\)", value)
            targets += re.findall(r'<a\s+href="([^"]+)"', value)
            for target in targets:
                parsed = urlsplit(target)
                if parsed.scheme:
                    continue
                dest = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                assert dest.exists(), f"Broken file link: {path.name} -> {target}"
                if parsed.fragment and dest.suffix == ".md":
                    other = dest.read_text()
                    assert f'id="{unquote(parsed.fragment)}"' in other, f"Broken anchor: {path.name} -> {target}"
                links += 1
    print(f"PASS: {manifest['pages']}/{manifest['pages']} source pages, {total:,} source letters/digits,")
    print(f"      unchanged PDF, {links} local links, closed fences, {python_examples} valid Python example.")


if __name__ == "__main__":
    main()
