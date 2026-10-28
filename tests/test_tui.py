"""Exercise actual key-driven transitions and rendering without a terminal emulator."""
import copy
import curses
from datetime import date
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from foss8 import discovery, github_activity, team, tui, weeks


class Screen:
    def __init__(self, keys=(), width=110, height=30):
        self.keys = iter(keys)
        self.width, self.height = width, height
        self.lines = []

    def erase(self):
        self.lines = []

    def getmaxyx(self):
        return self.height, self.width

    def addstr(self, y, x, value, attr=0):
        assert 0 <= y < self.height
        assert x + weeks._width(value) < self.width
        self.lines.append((y, x, value))

    def refresh(self):
        pass

    def move(self, y, x):
        assert 0 <= y < self.height and 0 <= x < self.width

    def get_wch(self):
        return next(self.keys)

    @property
    def text(self):
        return "\n".join(value for _, _, value in self.lines)


class TuiTests(unittest.TestCase):
    def setUp(self):
        clock = patch("foss8.weeks.today", return_value=date(2026, 10, 31))
        clock.start()
        self.addCleanup(clock.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / ".foss8/team.json"
        self.periods = weeks.load()
        self.app = tui.App(self.periods, weeks.select(self.periods, "9"), config_path=self.path)

    def test_arrows_change_selection_and_preview_without_enter(self):
        screen = Screen()
        self.app.draw(screen)
        before = screen.text
        target = next(i for i, row in enumerate(self.app.items()) if row["title"] == "충돌 해결 실습")
        for _ in range(target):
            self.app.handle(curses.KEY_DOWN)
        self.app.draw(screen)
        self.assertEqual(self.app.index(), target)
        self.assertIn("2인 1조 정하기", screen.text)
        self.assertNotIn("2인 1조 정하기", before)
        self.app.handle(curses.KEY_RIGHT)
        self.assertEqual(self.app.focus, "detail")
        self.assertEqual(self.app.period["weeks"], [9])
        self.app.draw(screen)
        self.assertIn("▶ 상세", screen.text)
        self.assertNotIn("▶ 할 일", screen.text)
        self.app.handle(curses.KEY_LEFT)
        self.assertEqual(self.app.focus, "list")
        self.app.focus = "period"
        self.app.handle(curses.KEY_RIGHT)
        self.assertEqual(self.app.period["weeks"], [10])
        self.app.handle(curses.KEY_LEFT)
        self.assertEqual(self.app.index(), target)

    def test_tabs_show_relevant_evaluation_and_settings(self):
        self.app.focus = "tabs"
        self.app.handle(curses.KEY_RIGHT)
        self.assertEqual(self.app.tab, 1)
        items = self.app.items()
        self.assertTrue(any(item.get("kind") == "assessment_criterion" for item in items))
        screen = Screen()
        self.app.draw(screen)
        self.assertIn("미집계", screen.text)
        self.app.handle(curses.KEY_RIGHT)
        self.app.handle(curses.KEY_DOWN)
        self.app.draw(screen)
        self.assertEqual(self.app.tab, 2)
        self.assertIn("팀 이름", screen.text)
        self.assertIn("Enter 수정", screen.text)

    def test_tab_moves_focus_without_switching_views(self):
        self.app.handle("\t")
        self.assertEqual(self.app.focus, "detail")
        self.assertEqual(self.app.tab, 0)
        self.app.handle("\t")
        self.assertEqual(self.app.focus, "period")

    def test_up_from_first_item_moves_up_and_down_returns_without_tab(self):
        for tab in range(3):
            with self.subTest(tab=tab):
                self.app.tab, self.app.focus = tab, "list"
                self.app.handle(curses.KEY_UP)
                self.assertEqual(self.app.focus, "tabs")
                self.app.handle(curses.KEY_UP)
                self.assertEqual(self.app.focus, "period")
                self.app.handle(curses.KEY_UP)
                self.assertEqual(self.app.focus, "period")
                self.app.handle(curses.KEY_DOWN)
                self.assertEqual(self.app.focus, "tabs")
                self.app.handle(curses.KEY_DOWN)
                self.assertEqual(self.app.focus, "list")
                self.assertEqual(self.app.index(), 0)
                self.assertEqual(self.app.period["weeks"], [9])

    def test_up_inside_list_selects_previous_item_before_leaving_list(self):
        self.app.move(2)
        self.app.handle(curses.KEY_UP)
        self.assertEqual((self.app.focus, self.app.index()), ("list", 1))
        self.app.handle(curses.KEY_UP)
        self.assertEqual((self.app.focus, self.app.index()), ("list", 0))
        self.app.handle(curses.KEY_UP)
        self.assertEqual(self.app.focus, "tabs")

    def test_visible_period_picker_changes_period_and_returns_to_list(self):
        self.app.focus = "period"
        with patch("foss8.tui.choose", return_value=self.app.periods.index(weeks.select(self.app.periods, "10"))):
            self.app.handle("\n", Screen())
        self.assertEqual(self.app.period["weeks"], [10])
        self.assertEqual(self.app.focus, "list")

    def test_space_persists_completion_and_undoes_it(self):
        self.app.move(next(i for i, row in enumerate(self.app.items()) if row.get("id")))
        item = self.app.items()[self.app.index()]
        self.app.handle(" ")
        self.assertTrue(self.app.done(item))
        screen = Screen()
        self.app.draw(screen)
        self.assertIn("[x]", screen.text)
        reopened = tui.App(self.periods, weeks.select(self.periods, "9"), config_path=self.path)
        reopened.move(next(i for i, row in enumerate(reopened.items()) if row.get("id")))
        self.assertTrue(reopened.done(reopened.items()[reopened.index()]))
        reopened.tab = 1
        assessed = next(x for x in reopened.items() if x.get("id") == item["id"])
        self.assertTrue(reopened.done(assessed))
        reopened.handle(" ")
        self.assertTrue(reopened.done(assessed))
        reopened.tab = 0
        reopened.handle(" ")
        self.assertFalse(reopened.done(reopened.items()[reopened.index()]))
        self.assertEqual(reopened.period["status"], "unknown")

    def test_team_name_and_assignee_changes_keep_completion(self):
        index = next(i for i, row in enumerate(self.app.items()) if row.get("id"))
        self.app.move(index)
        self.app.handle(" ")
        old_id = self.app.items()[index]["id"]
        self.app.save({"name": "changed-team"})
        self.assertEqual(self.app.items()[index]["id"], old_id)
        self.assertTrue(self.app.done(self.app.items()[index]))

    def test_space_in_settings_does_not_mark_work_done(self):
        self.app.tab = 2
        self.app.handle(" ")
        self.assertFalse(self.path.with_name("progress.json").exists())

    def test_checkbox_precedes_title_and_evaluation_marker_follows_it(self):
        screen = Screen()
        self.app.draw(screen)
        self.assertIn("[ ] [수업 후] 첫 PR 병합 [평가]", screen.text)
        self.assertNotIn("[평가] [ ]", screen.text)

    def test_reference_rules_are_not_checkable_tasks(self):
        self.assertTrue(self.app.period["references"])
        refs = [i for i, t in enumerate(self.app.items()) if t.get("kind") == "reference"]
        self.assertTrue(refs)
        self.app.selected[self.app.selection_key] = refs[0]
        self.app.handle(" ")
        self.assertFalse(self.path.with_name("progress.json").exists())
        self.app.tab = 1
        self.app.handle(" ")
        self.assertFalse(self.path.with_name("progress.json").exists())

    def test_semester_rules_are_listed_once_in_both_views(self):
        self.app.period_index = self.app.periods.index(weeks.select(self.app.periods, "10"))
        for tab in (0, 1):
            self.app.tab = tab
            rules = [r for r in self.app.items() if r["title"] == "학기 활동 기준"]
            self.assertEqual(len(rules), 1)

    def test_weekly_assessment_stays_visible_and_editable_in_tasks(self):
        self.assertEqual(self.app.items()[0]["kind"], "assessment_criterion")
        screen = Screen(width=80, height=24)
        self.app.draw(screen)
        self.assertIn("커밋", screen.text)
        self.assertNotIn("10/30 ~ 11/5", screen.text)
        self.assertIn("미집계", screen.text)
        self.assertNotIn("주간 활동 ·", screen.text)
        self.assertNotIn("주간 활동", screen.text)
        with patch("foss8.tui.edit_form", side_effect=lambda s, t, f, submit: submit({"commits": "2", "issues": "1", "prs": "0"})):
            self.app.handle("\n", screen)
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 2)

    def test_weekly_assessment_input_updates_remaining_counts_not_task_checks(self):
        self.app.tab = 1
        def edit(screen, title, fields, submit):
            submit({"commits": "1", "issues": "1", "prs": "0"})
        with patch("foss8.tui.edit_form", side_effect=edit):
            self.app.handle("\n", Screen())
        item = self.app.items()[self.app.index()]
        lines = "\n".join(self.app.assessment_detail(item, 80))
        self.assertIn("커밋  1/2회 · 1회 남음", lines)
        self.app.move(1)
        self.assertIn("이슈 작성  1/1회 · 충족", "\n".join(self.app.assessment_detail(self.app.items()[self.app.index()], 80)))
        self.app.move(1)
        self.assertIn("PR 생성·병합  0/1회 · 1회 남음", "\n".join(self.app.assessment_detail(self.app.items()[self.app.index()], 80)))
        self.assertFalse(self.path.with_name("progress.json").exists())
        self.assertTrue(self.path.with_name("assessments.json").exists())
        screen = Screen(width=80, height=24)
        self.app.draw(screen)
        self.assertIn("PR 생성·병합  0/1회", screen.text)

    def test_repeated_criteria_use_one_selected_course_week(self):
        rows = [r for r in self.app.items() if r.get("kind") == "assessment_criterion"]
        self.assertEqual([r["criterion"].id for r in rows], ["commits", "issues", "prs"])
        self.assertTrue(all(r["bundle"].start == date(2026, 10, 27) for r in rows))
        self.app.assessments.save(tui.progress.context(self.app.config), date(2026, 10, 27), {"commits": 2})
        with patch("foss8.weeks.today", return_value=date(2026, 11, 3)):
            self.assertFalse(any(r.get("kind") == "assessment_criterion" for r in self.app.items()))
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 2)

    def test_space_counts_repeated_work_and_backspace_corrects_it(self):
        self.app.handle(" ")
        self.assertEqual(self.app.items()[0]["bundle"].counts, {"commits": 1})
        self.app.handle(" ")
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 2)
        self.app.handle(" ")
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 3)
        self.app.tab = 1
        self.app.handle(curses.KEY_BACKSPACE)
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 2)
        reopened = tui.App(self.periods, weeks.select(self.periods, "9"), config_path=self.path)
        self.assertEqual(reopened.items()[0]["bundle"].counts["commits"], 2)
        for _ in range(4):
            reopened.handle("\x7f")
        self.assertEqual(reopened.items()[0]["bundle"].counts["commits"], 0)
        self.assertFalse(self.path.with_name("progress.json").exists())

    def test_space_does_not_count_exempt_or_future_weeks(self):
        self.app.change_period(1)
        future = 0
        self.app.selected[self.app.selection_key] = future
        self.app.handle(" ")
        self.assertIn("아직 시작하지 않은", self.app.message)
        clock = patch("foss8.weeks.today", return_value=date(2026, 10, 24))
        clock.start()
        self.addCleanup(clock.stop)
        self.app.period_index = self.app.periods.index(weeks.select(self.app.periods, "8"))
        exempt = next(i for i, r in enumerate(self.app.items()) if r.get("bundle") and r["bundle"].exam_overlap)
        self.app.selected[self.app.selection_key] = exempt
        self.app.handle(" ")
        self.assertIn("면제", self.app.message)
        self.assertFalse(self.path.with_name("assessments.json").exists())

    def test_edit_one_repeated_criterion_preserves_other_counts(self):
        self.app.assessments.save(tui.progress.context(self.app.config), date(2026, 10, 27),
                                  {"commits": 2, "issues": 1})
        def edit(screen, title, fields, submit):
            self.assertEqual([f.key for f in fields], ["commits"])
            submit({"commits": "3"})
        with patch("foss8.tui.edit_form", side_effect=edit):
            self.app.handle("\n", Screen())
        self.assertEqual(self.app.items()[0]["bundle"].counts, {"commits": 3, "issues": 1})

    def test_exam_exception_is_scoped_to_repeated_minimum(self):
        clock = patch("foss8.weeks.today", return_value=date(2026, 10, 24))
        clock.start()
        self.addCleanup(clock.stop)
        self.app.period_index = self.app.periods.index(weeks.select(self.app.periods, "8"))
        i = next(i for i, r in enumerate(self.app.items()) if r.get("bundle") and r["bundle"].exam_overlap)
        self.app.selected[self.app.selection_key] = i
        item = self.app.items()[i]
        self.assertFalse(item["bundle"].exempt)
        with patch("foss8.tui.edit_form") as edit:
            self.app.handle("\n", Screen())
            edit.assert_not_called()
        self.assertIn("10/19~10/25만 제외", "\n".join(self.app.assessment_detail(item, 80)))

    def test_wide_narrow_and_resized_layouts_stay_inside_terminal(self):
        for width, height in [(120, 30), (90, 24), (80, 24), (40, 20), (32, 13), (20, 8)]:
            with self.subTest(width=width, height=height):
                screen = Screen(width=width, height=height)
                self.app.draw(screen)
                self.assertTrue(screen.text)

    def test_editing_team_name_inside_app_updates_guide_immediately(self):
        self.app.tab = 2
        with patch("foss8.tui.edit_text", return_value="new-team"):
            self.app.handle("\n", Screen())
        self.assertEqual(team.load(self.path)["name"], "new-team")
        self.assertIn("회의록_new-team.pdf", weeks.render(self.app.period, (4, 6)))
        self.assertEqual(self.app.period["weeks"], [9])

    def test_cancelled_edit_does_not_create_settings(self):
        self.app.tab = 2
        with patch("foss8.tui.edit_text", return_value=None):
            self.app.handle("\n", Screen())
        self.assertFalse(self.path.exists())

    def test_detected_settings_fill_preview_without_saving(self):
        config = team.validate(json.loads((Path(__file__).resolve().parents[1] / "docs/team.example.json").read_text()))
        result = discovery.Result(config, ["Git origin", "README.md"], [])
        self.app.discovery_queue.put((0, True, result, None))
        self.app.poll_discovery()
        self.assertEqual(self.app.config["me"], "garam")
        self.assertTrue(self.app.detected_draft)
        self.assertFalse(self.path.exists())
        self.assertIn("회의록_team-example.pdf", weeks.render(self.app.period, (4, 6)))

    def test_late_discovery_does_not_overwrite_manual_settings(self):
        config = team.validate({"name": "detected"})
        self.app.save({"name": "manual"})
        self.app.discovery_queue.put((0, True, discovery.Result(config, [], []), None))
        self.app.poll_discovery()
        self.assertEqual(self.app.config["name"], "manual")

    def test_existing_local_records_prevent_automatic_identity_switch(self):
        self.app.move(next(i for i, row in enumerate(self.app.items()) if row.get("id")))
        self.app.handle(" ")
        config = team.validate({"name": "detected", "repository": "owner/repo"})
        self.app.discovery_queue.put((self.app.config_revision, True, discovery.Result(config, [], []), None))
        self.app.poll_discovery()
        self.assertIsNone(self.app.config)
        self.assertIsNotNone(self.app.pending_discovery)

    def test_discovered_values_can_be_applied_inside_settings(self):
        config = team.validate({"name": "detected"})
        self.app.pending_discovery = discovery.Result(config, ["Git origin"], [])
        self.app.tab = 2
        row = next(i for i, r in enumerate(self.app.settings()) if r.kind == "discover")
        self.app.selected[self.app.selection_key] = row
        with patch("foss8.tui.choose", return_value=True):
            self.app.handle("\n", Screen())
        self.assertEqual(team.load(self.path)["name"], "detected")

    def test_member_form_saves_roles_and_renames_person_references(self):
        raw = json.loads((Path(__file__).resolve().parents[1] / "docs/team.example.json").read_text())
        self.app.save(raw)
        self.app.tab = 2
        self.app.selected[self.app.selection_key] = 6
        edited = {"name": "새이름", "github": "changed-id", "roles": ["team_lead", "quality"], "features": "입력, 검증"}
        def edit(screen, title, fields, submit):
            submit(copy.deepcopy(edited))
        with patch("foss8.tui.edit_form", side_effect=edit):
            self.app.edit_setting(Screen())
        saved = team.load(self.path)
        self.assertEqual(saved["me"], "changed-id")
        self.assertEqual(saved["members"][0]["features"], ["입력", "검증"])
        self.assertIn("main 보호 설정 (새이름)", weeks.render(self.app.period))

    def test_picker_uses_arrows_and_multi_select_without_text_input(self):
        options = [("a", "첫 항목"), ("b", "둘째 항목")]
        self.assertEqual(tui.choose(Screen([curses.KEY_DOWN, "\n"]), "선택", options), "b")
        self.assertEqual(tui.choose(Screen([" ", curses.KEY_DOWN, " ", "\n"]), "역할", options, [], True), ["a", "b"])
        self.assertIs(tui.choose(Screen(["\x1b"]), "선택", options), tui.CANCEL)

    def activity_config(self):
        self.app.save({"name": "sample", "repository": "owner/repo",
                       "members": [{"name": "나", "github": "me"}], "me": "me"})

    def test_missing_activity_settings_are_visible_and_open_the_required_field(self):
        self.app.save({"name": "sample"})
        screen = Screen()
        self.app.draw(screen)
        self.assertIn("집계 설정 필요", screen.text)
        self.assertIn("GitHub 저장소 설정", screen.text)
        self.app.handle("s")
        self.assertEqual(self.app.tab, 2)
        self.assertEqual(self.app.settings()[self.app.index()].key, "repository")
        with patch("foss8.tui.threading.Thread") as thread:
            self.app.start_activity()
            thread.assert_not_called()

    def test_discovery_action_moves_up_only_when_settings_differ(self):
        self.activity_config()
        config = copy.deepcopy(self.app.config)
        self.app.pending_discovery = discovery.Result(config, ["Git origin"], [])
        self.assertEqual(self.app.settings()[-1].kind, "discover")
        config["name"] = "renamed"
        self.assertEqual(self.app.settings()[0].kind, "discover")
        self.assertIn("1건", self.app.settings()[0].label)
        self.app.handle("s")
        self.assertEqual(self.app.index(), 0)
        details = "\n".join(self.app.setting_detail(self.app.settings()[0], 90))
        self.assertIn("현재: sample", details)
        self.assertIn("변경: renamed", details)
        with patch("foss8.tui.choose", return_value=False):
            self.app.handle("\n", Screen())
        self.assertEqual(self.app.config["name"], "sample")
        with patch("foss8.tui.choose", return_value="changes"):
            self.app.handle("\n", Screen())
        self.assertEqual(self.app.config["name"], "renamed")
        self.assertIsNone(self.app.pending_discovery)
        self.assertEqual(self.app.settings()[-1].kind, "discover")

    def test_background_github_result_saves_evidence_and_preserves_failed_counts(self):
        self.activity_config()
        start = date(2026, 10, 27)
        self.app.assessments.save(tui.progress.context(self.app.config), start, {"commits": 1, "issues": 2})
        result = github_activity.Result({"commits": 3, "prs": 1}, {"commits": ["https://github.com/owner/repo/commit/abc"]}, ["이슈 조회 실패"])
        self.app.activity_queue.put((self.app.activity_key(), self.app.config_revision, copy.deepcopy(self.app.period), result))
        self.app.poll_activity()
        record = self.app.assessments.record(tui.progress.context(self.app.config), start)
        self.assertEqual(record["counts"], {"commits": 3, "issues": 2, "prs": 1})
        self.assertEqual(record["sources"]["commits"], "github")
        screen = Screen()
        self.app.draw(screen)
        self.assertIn("GitHub 집계 실패", screen.text)
        self.assertIn("https://github.com/owner/repo/commit/abc", "\n".join(self.app.assessment_detail(self.app.items()[0], 90)))

    def test_github_result_does_not_overwrite_a_manual_edit_during_fetch(self):
        self.activity_config()
        key, revision, period = self.app.activity_key(), self.app.config_revision, copy.deepcopy(self.app.period)
        self.app.handle(" ")
        self.app.activity_queue.put((key, revision, period, github_activity.Result({"commits": 7})))
        self.app.poll_activity()
        self.assertEqual(self.app.items()[0]["bundle"].counts["commits"], 1)
        self.assertIn("변경됨", self.app.message)

    def test_github_refresh_key_and_nonblocking_auto_fetch(self):
        self.activity_config()
        with patch.object(self.app, "start_activity") as start:
            self.app.handle("r")
            start.assert_called_once_with(force=True)
        with patch("foss8.tui.threading.Thread") as thread:
            self.app.start_activity()
            self.assertTrue(thread.call_args.kwargs["daemon"])
            thread.return_value.start.assert_called_once()
            self.app.start_activity()
            self.assertEqual(thread.call_count, 1)

    def test_evaluation_screen_does_not_invent_progress_or_scores(self):
        lines = tui.task_detail(next(t for t in self.app.period["tasks"] if t["title"].startswith("회의록")), 70, evaluation=True)
        text = "\n".join(lines)
        self.assertIn("총 10회", text)
        self.assertIn("회차별 3점 아님", text)
        self.assertNotIn("완료됨", text)

    def test_minutes_task_creates_an_editable_draft_without_marking_submission(self):
        index = next(i for i, row in enumerate(self.app.items()) if row.get("recording_start"))
        self.app.selected[self.app.selection_key] = index
        with patch("foss8.tui.choose", return_value="draft"), patch("foss8.tui.edit_form", side_effect=lambda s, title, fields, submit: submit({"date": "2026-10-28"})):
            self.app.handle("\n", Screen())
        path = self.path.parent.parent / "docs/meetings/2026-10-28.md"
        self.assertIn("[WEEK9]", path.read_text())
        self.assertFalse(self.app.done(self.app.items()[index]))
        self.assertFalse(self.path.with_name("progress.json").exists())

    def test_minutes_task_exports_the_selected_file_without_marking_submission(self):
        index = next(i for i, row in enumerate(self.app.items()) if row.get("recording_start"))
        self.app.selected[self.app.selection_key] = index
        source = self.path.parent.parent / "docs/meetings/2026-10-28.md"
        target = source.with_suffix(".pdf")
        with patch("foss8.tui.choose", return_value="pdf"), patch("foss8.tui.edit_text", return_value=str(source)), patch("foss8.minutes_pdf.export", return_value=target) as export:
            self.app.handle("\n", Screen())
        export.assert_called_once_with(str(source), week="9")
        self.assertIn("제출용 PDF 저장", self.app.message)
        self.assertFalse(self.app.done(self.app.items()[index]))

    def test_before_class_list_prioritizes_current_deadline_and_marks_later_work(self):
        with patch("foss8.weeks.today", return_value=date(2026, 10, 28)):
            rows = self.app.items()
            pr = next(i for i, row in enumerate(rows) if row.get("id") == "task-1425f70aabc1")
            minutes = next(i for i, row in enumerate(rows) if row.get("recording_start"))
            self.assertLess(minutes, pr)
            criterion = next(row for row in rows if row.get("criterion") and row["criterion"].id == "prs")
            self.assertEqual(criterion["after_class"], "2026-10-30")
            self.assertIn("10/30 수업 후", "\n".join(self.app.assessment_detail(criterion, 80)))
            screen = Screen()
            self.app.draw(screen)
            self.assertIn("[수업 후]", screen.text)

    def test_same_post_class_task_shares_completion_across_weeks(self):
        task_id = "task-1425f70aabc1"
        def select():
            index = next(i for i, row in enumerate(self.app.items()) if row.get("id") == task_id)
            self.app.selected[self.app.selection_key] = index
            return self.app.items()[index]
        original = select()
        self.app.handle(" ")
        self.app.change_period(1)
        carried = select()
        self.assertEqual(carried["carryover_from"], "9주차")
        self.assertTrue(self.app.done(carried))
        self.assertIn("10/30 수업 후", "\n".join(tui.task_detail(carried, 80)))
        self.app.handle(" ")
        self.app.change_period(-1)
        self.assertFalse(self.app.done(select()))
        records = self.app.progress.data["contexts"][tui.progress.context(self.app.config)]
        self.assertEqual(list(records), [original["progress_period"] + "/" + task_id])


if __name__ == "__main__":
    unittest.main()
