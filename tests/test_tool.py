import ast
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from datetime import date

import pytest
from textual.widgets import Input, Markdown, OptionList, Select, Static

from foss8.cli import main
from foss8.guide import Catalog, display_markdown
from foss8.templates import get, save
from foss8.tui import GuideApp, HelpHint, HelpScreen, StartScreen, WeekScreen
from foss8 import weeks, focus
from foss8 import completion
from foss8.completion import install as install_completion


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


@pytest.mark.parametrize("name,count,pages,deadline,last", [
    ("proposal", 7, [15], "10/1(목) 18:00", "기대 효과 및 목표"),
    ("midterm", 6, [33], "11/5(목) 18:00", "남은 계획"),
    ("final", 8, [34, 35], "12/17(목) 18:00", "회고와 향후 계획"),
])
def test_report_forms_keep_required_sections_submission_and_portable_sources(name, count, pages, deadline, last, tmp_path, capsys):
    template = get(Catalog(), name)
    content = template["content"]
    assert len(re.findall(r"^## \d+\. ", content, re.M)) == count
    assert f"## {count}. {last}" in content
    assert "## 표지" in content and "## 목차" in content and deadline in content
    assert template["derived"] is True and template["source"]["pages"] == pages
    assert "기능 4개" in content and "팀명: \n" in content and "[작성]" in content
    assert not re.search(r"\]\((?!https://)[^)]+\)", content)
    if name == "final":
        assert "## 부록" in content and "회의록 10회 링크" in content and "대표 풀 리퀘스트 2개 링크" in content
    if name == "midterm":
        assert "동작하는 기능 2개" in content and "충돌 해결 사례 1개" in content
    target = tmp_path / f"{name}.md"
    assert main(["format", name, "-o", str(target), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["ok"] and target.read_text(encoding="utf-8") == content
    assert name in completion.forms()
    assert name in GuideApp().forms


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


def test_week_selection_handles_break_makeup_exam_and_next_deadlines(capsys):
    catalog = Catalog()
    items = weeks.listing(catalog)
    assert len(items) == 15 and len({item['id'] for item in items}) == 15
    assert weeks.default(catalog, date(2026, 10, 6)) == "week-06"
    assert weeks.get(catalog, "4")["date"] == "2026-09-25"
    assert weeks.get(catalog, "4", makeup=True)["date"] == "2026-12-11"
    assert "없음" in weeks.get(catalog, "8")["submission"]
    assert "목요일 18:00" not in weeks.markdown(weeks.get(catalog, "8"))
    assert len(weeks.get(catalog, "6")["checklist"]) == 5
    assert "10/15" in weeks.get(catalog, "6")["checklist"][-1]
    for day, expected in [(date(2026,10,6), {'[WEEK6] 회의록'}),
                          (date(2026,10,16), {'[WEEK9] 회의록'}),
                          (date(2026,11,5), {'[WEEK10] 회의록','중간보고서'}),
                          (date(2026,12,11), {'최종보고서'})]:
        assert {item['title'] for item in focus.next_submissions(catalog, day)['next_submissions']} == expected
    assert main(["week", "4", "--makeup", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["data"]["id"] == "week-04-makeup"
    assert main(["week", "1", "--json"]) == 2
    assert not json.loads(capsys.readouterr().out)["ok"]


@pytest.mark.asyncio
async def test_simple_start_week_selection_and_direct_minutes_save(tmp_path):
    app = GuideApp()
    async with app.run_test(size=(80, 28)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, StartScreen)

        assert app.screen.query_one(OptionList).option_count == 4
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, WeekScreen)
        app.screen.query_one("#week-choice", Select).value = "week-06"
        await pilot.pause()
        app.screen.query_one("#week-choice", Select).focus()
        await pilot.press("enter", "down", "enter")
        await pilot.pause()
        assert app.screen.selected["id"] == "week-07"
        for key in ["week-06", "week-08", "week-04-makeup"]:
            app.screen.query_one("#week-choice", Select).value = key
            await pilot.pause()
            assert app.screen.selected["id"] == key
        await pilot.click("#week-checklist")
        await pilot.pause()
        assert app.screen.checklist
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, StartScreen)
        await pilot.press("down", "enter")
        await pilot.pause()
        target = tmp_path / "간단회의록.md"
        app.screen.query_one("#destination", Input).value = str(target)
        await pilot.press("enter")
        await pilot.pause()
        assert target.exists() and "활동 로그" in target.read_text()
        assert isinstance(app.screen, StartScreen)


@pytest.mark.asyncio
async def test_focus_hints_dropdown_help_and_input_restore():
    app = GuideApp()
    async with app.run_test(size=(80, 28)) as pilot:
        await pilot.pause()
        assert "주차별 할 일" in str(app.screen.query_one(HelpHint).render())
        await pilot.press("down")
        await pilot.pause()
        assert "빈 양식" in str(app.screen.query_one(HelpHint).render())
        await pilot.press("up", "enter")
        await pilot.pause()
        assert "목록 펼치기" in str(app.screen.query_one(HelpHint).render())
        await pilot.press("enter")
        await pilot.pause()
        assert app.screen.query_one(Select).expanded
        assert "Esc 목록 닫기" in str(app.screen.query_one(HelpHint).render())
        await pilot.press("escape")
        await pilot.pause()
        assert isinstance(app.screen, WeekScreen)
        assert not app.screen.query_one(Select).expanded
        await pilot.press("tab")
        await pilot.pause()
        assert app.screen.focused.id == "week-reader"
        assert "스크롤" in str(app.screen.query_one(HelpHint).render())
        previous = app.screen.focused
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, WeekScreen)
        assert app.screen.focused is previous
        await pilot.press("/")
        await pilot.pause()
        assert "검색어 입력" in str(app.screen.query_one(HelpHint).render())
        query = app.screen.query_one("#search", Input)
        query.value = "회의록 제출"
        await pilot.pause()
        await pilot.press("f1", "escape")
        await pilot.pause()
        assert app.screen.focused is query and query.value == "회의록 제출"
        await pilot.press("enter")
        await pilot.pause()
        assert "검색" in str(app.screen.query_one(HelpHint).render())
        assert "Enter 본문 열기" in str(app.screen.query_one(HelpHint).render())
        await pilot.press("ctrl+s")
        await pilot.pause()
        destination = app.screen.query_one("#destination", Input)
        destination.value = "내 회의록.md"
        await pilot.press("f1")
        await pilot.pause()
        assert isinstance(app.screen, HelpScreen)
        await pilot.press("escape")
        await pilot.pause()
        assert app.screen.focused is destination and destination.value == "내 회의록.md"
        assert "저장 경로" in str(app.screen.query_one(HelpHint).render())


def test_cli_incomplete_commands_show_choices_and_keep_json_contract(capsys):
    for arguments, expected in [(["help"], "oss completion bash --install"),
                                (["guide"], "oss guide search"),
                                (["guide", "show"], "calendar"),
                                (["guide", "search"], "검색어"),
                                (["format"], "minutes-example")]:
        assert main(arguments) == 0
        output = capsys.readouterr()
        assert expected in output.out and not output.err
    assert main(["format", "unknown"]) == 2
    assert "지원 양식: minutes, minutes-example" in capsys.readouterr().err
    assert main(["guide", "wrong"]) == 2
    assert "oss guide search" in capsys.readouterr().err
    assert main(["guide", "show", "--json"]) == 2
    output = capsys.readouterr()
    assert not output.err and not json.loads(output.out)["ok"]
    assert main(["format", "--json"]) == 0
    output = capsys.readouterr()
    assert not output.err and json.loads(output.out)["data"][0]["id"] == "minutes"


def test_shell_completion_offers_context_values_and_output_paths(tmp_path):
    def complete(line):
        destination = tmp_path / "completion-output"
        env = dict(os.environ, _ARGCOMPLETE="1", COMP_LINE=line, COMP_POINT=str(len(line)),
                   _ARGCOMPLETE_STDOUT_FILENAME=str(destination), _ARGCOMPLETE_IFS="\v")
        result = subprocess.run([sys.executable, "-m", "foss8"], env=env, capture_output=True, text=True)
        assert result.returncode == 0 and not result.stdout and not result.stderr
        return {item.strip() for item in destination.read_text().split("\v")}
    assert {"week", "guide", "format", "completion"} <= complete("oss ")
    assert complete("oss guide ") == {"list", "show", "search"}
    assert complete("oss format min") == {"minutes", "minutes-example"}
    assert {"6", "week-04-makeup"} <= complete("oss week ")
    assert "minutes" in complete("oss guide show min")
    assert "--output" in complete("oss format minutes --")
    target = tmp_path / "my-minutes.md"
    target.write_text("preserve")
    assert str(target) in complete("oss format minutes --output " + str(tmp_path) + "/my-")
    assert target.read_text() == "preserve"


def test_completion_install_is_repeatable_and_protects_existing_customization(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    path, activate = install_completion("bash")
    assert Path(path).read_text().startswith("# foss-8 shell completion\n")
    assert "source " in activate and install_completion("bash")[0] == path
    Path(path).write_text("my custom completion")
    with pytest.raises(ValueError, match="보호"):
        install_completion("bash")
    assert Path(path).read_text() == "my custom completion"
