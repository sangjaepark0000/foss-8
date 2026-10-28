"""Check activity boundaries, local task details, and CLI navigation."""
from datetime import date
from io import StringIO
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from foss8 import weeks


ROOT = Path(__file__).resolve().parents[1]


class WeekTests(unittest.TestCase):
    def setUp(self):
        self.periods = weeks.load()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        (Path(self.tmp.name) / ".git").mkdir()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "main.py"), "week", *args],
                              cwd=self.tmp.name, capture_output=True, text=True,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_pr_work_starts_at_its_activity_period(self):
        before = weeks.select(self.periods, on="2026-10-26")
        after = weeks.select(self.periods, on="2026-10-27")
        self.assertEqual(before["weeks"], [8])
        self.assertEqual(after["weeks"], [9])
        self.assertNotIn("첫 PR 병합", weeks.render(before))
        self.assertIn("첫 PR 병합", weeks.render(after))
        self.assertEqual(weeks.select(self.periods, on=date(2026, 11, 6))["weeks"], [10])

    def test_makeup_and_regular_week_four_are_different(self):
        self.assertEqual(weeks.select(self.periods, "4")["weeks"], [4])
        for key in ["makeup", "보강"]:
            self.assertEqual(weeks.select(self.periods, key)["start"], "2026-12-08")

    def test_previously_merged_weeks_have_separate_tasks_and_contiguous_dates(self):
        for first, second in [("3", "4"), ("7", "8")]:
            a, b = weeks.select(self.periods, first), weeks.select(self.periods, second)
            self.assertEqual(a["weeks"], [int(first)])
            self.assertEqual(b["weeks"], [int(second)])
            self.assertEqual(a["end"], b["start"])
        self.assertIn("개발 준비", weeks.render(weeks.select(self.periods, "3")))
        self.assertNotIn("회의록 #1 제출", weeks.render(weeks.select(self.periods, "3")))
        self.assertIn("제안서 완성", weeks.render(weeks.select(self.periods, "4")))
        self.assertIn("회의록 #1 제출", weeks.render(weeks.select(self.periods, "5")))
        self.assertNotIn("회의록 #4 제출", weeks.render(weeks.select(self.periods, "7")))
        self.assertNotIn("회의록 #4 제출", weeks.render(weeks.select(self.periods, "8")))
        self.assertIn("회의록 #4 제출", weeks.render(weeks.select(self.periods, "9")))

    def test_academic_weeks_and_minutes_recording_window_are_independent(self):
        eight = weeks.select(self.periods, on="2026-10-26")
        nine = weeks.select(self.periods, on="2026-10-27")
        self.assertEqual(eight["weeks"], [8])
        self.assertEqual(nine["weeks"], [9])
        self.assertEqual(weeks.heading(nine)[1], "  10/27 ~ 11/2")
        for p in self.periods:
            self.assertEqual(date.fromisoformat(p["start"]).weekday(), 1)
            self.assertEqual(date.fromisoformat(p["end"]).weekday(), 1)
        minutes = next(t for t in nine["tasks"] if t["title"].startswith("회의록 #4"))
        self.assertEqual(minutes["due_at"], "2026-10-29T18:00:00+09:00")
        self.assertEqual((minutes["recording_start"], minutes["recording_end"]), ("2026-10-15", "2026-10-28"))
        self.assertEqual(minutes["progress_period"], "7")

    def test_post_class_actions_are_shared_in_the_following_week(self):
        nine, ten = weeks.select(self.periods, "9"), weeks.select(self.periods, "10")
        task = next(t for t in nine["tasks"] if t["title"] == "첫 PR 병합")
        carried = next(t for t in weeks.view_tasks(ten) if t["id"] == task["id"])
        self.assertEqual(task["after_class"], "2026-10-30")
        self.assertEqual(carried["progress_period"], task["progress_period"])
        self.assertEqual(carried["carryover_from"], "9주차")
        self.assertIn('첫 PR 병합 [수업 후]', weeks.render(nine))
        self.assertIn('첫 PR 병합 [이어서]', weeks.render(ten))
        deadline = next(t for t in nine["tasks"] if t.get("recording_start"))
        self.assertNotIn("after_class", deadline)

    def test_moved_reference_rules_appear_once_without_losing_content(self):
        nine, ten = weeks.select(self.periods, "9"), weeks.select(self.periods, "10")
        expected = next(r for r in nine["references"] if r["title"] == "학기 활동 기준")
        actual = [r for r in ten["references"] if r["title"] == "학기 활동 기준"]
        self.assertEqual(len(actual), 1)
        for key in ("children", "details", "evaluation", "evaluation_source"):
            self.assertEqual(actual[0][key], expected[key])

    def test_overview_puts_week_and_title_before_dates_and_hides_details(self):
        output = self.cli("9")
        self.assertEqual(output.returncode, 0, output.stderr)
        lines = output.stdout.splitlines()
        self.assertEqual(lines[0], "9주차 · PR 병합과 회의록")
        self.assertEqual(lines[1], "  10/27 ~ 11/2")
        self.assertIn("회의록 #4 제출 · 10/29 18:00 [평가]", output.stdout)
        self.assertNotIn("Ctrl+P", output.stdout)
        self.assertNotIn("안내서 기준 일정", output.stdout)

    def test_minutes_file_rules_and_pdf_method_are_next_to_the_task(self):
        output = self.cli("9", "--task", "4.6")
        self.assertEqual(output.returncode, 0, output.stderr)
        self.assertIn("[WEEK9] 회의록_팀명.pdf", output.stdout)
        self.assertIn("LMS 과제 탭", output.stdout)
        detail = self.cli("9", "--task", "4.6.1")
        self.assertEqual(detail.returncode, 0, detail.stderr)
        self.assertIn("Ctrl+P", detail.stdout)
        self.assertIn("PDF로 저장", detail.stdout)
        self.assertNotIn("1. 방법", detail.stdout)

    def test_team_actions_are_short_and_separate(self):
        output = self.cli("2", "--task", "1")
        for action in ["팀 이름 공유", "GitHub ID 공유", "담당 기능 정하기", "담당 역할 정하기"]:
            self.assertIn(action, output.stdout)
        self.assertNotIn("전원 ·", output.stdout)

    def test_evaluation_and_unobserved_status_remain_distinct(self):
        result = self.cli("9", "--task", "4", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["data"]["period"]["status"], "unknown")
        self.assertIn("회차별 3점 아님", " ".join(payload["data"]["node"]["evaluation"]))

    def test_invalid_paths_and_dates_show_errors_without_tracebacks(self):
        for args in [("9", "--task", "99"), ("9", "--task", "0"),
                     ("9", "--task", "1.x"), ("--date", "2026-02-30"),
                     ("9", "--date", "2026-10-30"), ("--list", "--task", "1")]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertIn("오류:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_interactive_tree_opens_deep_details_without_entering_and_leaving_pages(self):
        output = StringIO()
        answers = iter(["4.6.1", "5", "4", "w 2", "1", "w9", "q"])
        status = weeks.browse(self.periods, weeks.select(self.periods, "9"),
                              input_fn=lambda _: next(answers), output=output)
        self.assertEqual(status, 0)
        text = output.getvalue()
        self.assertIn("Ctrl+P", text)
        self.assertIn("2주차 · 팀 구성", text)
        self.assertIn("GitHub ID 공유", text)

    def test_tree_keeps_sibling_tasks_visible_and_supports_multiple_open_branches(self):
        period = weeks.select(self.periods, "9")
        expanded = set()
        weeks.toggle_paths(period, expanded, ["4.6.1", "3"])
        text = weeks.render_tree(period, expanded)
        self.assertIn("Ctrl+P", text)
        self.assertIn("3 ▾ main 보호 설정", text)
        self.assertIn("5 ▸ 수업", text)
        weeks.toggle_paths(period, expanded, ["4"])
        text = weeks.render_tree(period, expanded)
        self.assertNotIn("Ctrl+P", text)
        self.assertIn("3 ▾ main 보호 설정", text)
        weeks.toggle_paths(period, expanded, ["4.6.1"])
        self.assertIn("Ctrl+P", weeks.render_tree(period, expanded))

    def test_invalid_batch_leaves_open_branches_unchanged(self):
        period = weeks.select(self.periods, "9")
        expanded = {(1,)}
        with self.assertRaises(ValueError):
            weeks.toggle_paths(period, expanded, ["4", "99"])
        self.assertEqual(expanded, {(1,)})

    def test_all_periods_and_every_detail_can_be_opened(self):
        # Ensures generated method/criteria paths do not require the staging files or network.
        def visit(period, path=()):
            node = weeks.resolve(period, path)
            self.assertTrue(weeks.render(period, path))
            for i, child in enumerate(weeks.entries(node), 1):
                visit(period, path + (i,))
        for period in self.periods:
            visit(period)

    def test_json_list_is_structured_and_offline(self):
        result = self.cli("--list", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["data"]["periods"]), 15)


if __name__ == "__main__":
    unittest.main()
