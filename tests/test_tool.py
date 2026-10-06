import ast
import json
from pathlib import Path

import pytest
from textual.widgets import Input, Markdown, OptionList, Select, Static

from foss8.cli import main
from foss8.guide import Catalog, display_markdown
from foss8.templates import get, save
from foss8.tui import GuideApp


def test_catalog_covers_source_pages_and_search_has_reproducible_location():
    catalog = Catalog()
    pages = [page for doc in catalog.documents.values() for page in doc.pages]
    assert sorted(pages) == list(range(1, 49))
    hits, count = catalog.search("회의록 제출")
    assert count >= len(hits) > 0
    assert any(hit["source"]["scope"] == "team-decision" for hit in hits)
    for hit in hits:
        doc, anchor = catalog.resolve(hit["selector"])
        assert doc.id == hit["id"]
        assert hit["source"]["sha256"] == catalog.manifest["sha256"]
    assert "10/8" in catalog.show("minutes#section-12-1")["markdown"]


def test_display_preserves_code_and_makes_source_tables_readable():
    catalog = Catalog()
    source = catalog.show("minutes")["markdown"]
    rendered = display_markdown(source)
    assert "<table>" not in rendered and "<td>" not in rendered
    assert "| 마감 |" in rendered and "LMS" in rendered
    readme = get(catalog, "readme")["content"]
    assert display_markdown("````markdown\n" + readme + "````") == "\n````markdown\n" + readme.rstrip("\n") + "\n````\n"


def test_template_extraction_preserves_multiblock_form_and_nested_fences():
    catalog = Catalog()
    readme = get(catalog, "readme")["content"]
    assert "```" in readme and "git clone" in readme and "## 라이선스" in readme
    conduct = get(catalog, "code-of-conduct")["content"]
    assert "# 행동 수칙" in conduct and "## 신고와 처리" in conduct
    ast.parse(get(catalog, "main")["content"])
    blank = get(catalog, "minutes")["content"]
    assert "홍길동" not in blank and "[x]" not in blank and "2026-10-13" not in blank
    assert "해당 주차" in blank and "활동 로그" in blank
    assert get(catalog, "minutes-example")["derived"] is False


def test_cli_json_success_error_and_explicit_overwrite(tmp_path, capsys):
    assert main(["guide", "show", "minutes", "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["schema_version"] == 1 and result["ok"]
    assert main(["guide", "show", "../secret", "--json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"] and result["error"]["code"] == "invalid_request"
    assert main(["guide", "search", "--limit", "wrong", "--json"]) == 2
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"] and result["error"]["code"] == "invalid_request"
    target = tmp_path / "회의록.md"
    target.write_text("preserve me", encoding="utf-8")
    assert main(["format", "minutes", "--output", str(target), "--json"]) == 2
    assert target.read_text() == "preserve me"
    result = json.loads(capsys.readouterr().out)
    assert not result["ok"]
    assert main(["format", "minutes", "--output", str(target), "--force", "--json"]) == 0
    assert "활동 로그" in target.read_text()
    assert json.loads(capsys.readouterr().out)["ok"]


@pytest.mark.asyncio
async def test_tui_search_navigation_link_back_and_template_save(tmp_path):
    app = GuideApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.current == "home"
        await pilot.press("/")
        app.query_one("#search", Input).value = "회의록 제출"
        await pilot.pause()
        assert app.entries
        await pilot.press("enter", "enter")
        await pilot.pause()
        assert app.current != "home"
        await pilot.press("escape")
        await pilot.pause()
        assert app.current == "home"
        await app.follow_link(Markdown.LinkClicked(app.query_one(Markdown), "12-minutes.md#section-12-1"))
        assert app.current == "12-minutes.md#section-12-1"
        app.query_one("#category", Select).value = "양식 저장"
        await pilot.pause()
        await pilot.click("#results")
        app.query_one("#results", OptionList).highlighted = 0
        await pilot.press("enter")
        await pilot.pause()
        assert app.current == "template:minutes"
        await pilot.press("ctrl+s")
        await pilot.pause()
        target = tmp_path / "회의록.md"
        app.screen.query_one("#destination", Input).value = str(target)
        await pilot.press("enter")
        await pilot.pause()
        assert "활동 로그" in target.read_text()
        await pilot.press("ctrl+s")
        await pilot.pause()
        app.screen.query_one("#destination", Input).value = str(target)
        await pilot.press("enter")
        await pilot.pause()
        assert "이미 있습니다" in str(app.screen.query_one("#save-error", Static).render())
        await pilot.press("escape")
