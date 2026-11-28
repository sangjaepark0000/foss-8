"""Check persisted calendar state and reconciliation with the current handbook."""
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from foss8.cli import main
from foss8.guide import Catalog
from foss8.week_progress import load_progress
from foss8.weeks import get_weekly_item, result_line


class WeekProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "foss8" / "week_progress.json"
        path_patch = patch("foss8.week_progress.progress_path", return_value=self.path)
        path_patch.start()
        self.addCleanup(path_patch.stop)

    def cli(self, *args):
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            status = main(list(args))
        return status, output.getvalue(), error.getvalue()

    def test_cli_persists_completion_and_memo_then_toggles_and_deletes(self):
        status, output, error = self.cli("week", "2", "--done", "1", "--memo", "다음", "회의")
        self.assertEqual((status, error), (0, ""))
        self.assertIn("1. [완료]", output)
        self.assertIn("메모: 다음 회의", output)
        self.assertEqual(self.cli("week", "2"), (0, output, ""))
        self.assertIn("다음 회의", self.path.read_text(encoding="utf-8"))

        status, output, error = self.cli("week", "2", "--done", "1", "--memo")
        self.assertEqual((status, error), (0, ""))
        self.assertIn("1. [--]", output)
        self.assertNotIn("메모:", output)
        self.assertEqual(self.cli("week", "2"), (0, output, ""))

    def test_invalid_task_number_does_not_change_saved_progress(self):
        self.cli("week", "2", "--done", "1", "--memo", "유지할 메모")
        before = self.path.read_bytes()
        for number in ("0", "999", "문자"):
            with self.subTest(number=number):
                status, _, error = self.cli("week", "2", "--done", number)
                self.assertEqual(status, 2)
                self.assertIn("오류:", error)
                self.assertNotIn("Traceback", error)
                self.assertEqual(self.path.read_bytes(), before)

    def test_updated_handbook_replaces_stale_tasks_and_keeps_matching_state(self):
        catalog = Catalog()
        old_tasks = get_weekly_item(catalog, "2")["tasks"]
        self.path.parent.mkdir(parents=True)
        # This is the original PR's JSON format, including a removed task/week.
        saved = {
            "week-2": {
                "tasks": [{**task, "completed": True} for task in reversed(old_tasks)]
                         + [{"role": "팀", "text": "삭제된 할 일", "completed": True}],
                "memo": "기존 메모",
            },
            "week-99": {"tasks": [], "memo": "삭제된 주차"},
        }
        self.path.write_text(json.dumps(saved, ensure_ascii=False), encoding="utf-8")
        doc = catalog.documents["03-roadmap"]
        catalog.documents[doc.id] = replace(
            doc,
            markdown=doc.markdown.replace("팀 구성·역할·팀장", "수정된 할 일")
                     .replace("• 각자: GitHub 계정", "• 팀: 새 할 일<br>• 각자: GitHub 계정"),
        )

        progress = load_progress(catalog)
        week = progress["week-2"]
        current = get_weekly_item(catalog, "2")
        self.assertEqual([{k: task[k] for k in ("role", "text")} for task in week["tasks"]],
                         current["tasks"])
        self.assertEqual([task["completed"] for task in week["tasks"]], [False, True, False, True])
        self.assertEqual(week["memo"], "기존 메모")
        self.assertIn("새 할 일", result_line(current, week))
        self.assertNotIn("삭제된 할 일", result_line(current, week))
        self.assertNotIn("week-99", progress)
        # Weeks absent from an older save must also be available immediately.
        self.assertEqual(progress["week-3"]["memo"], "")
        self.assertTrue(progress["week-3"]["tasks"])
        self.assertTrue(all(not task["completed"] for task in progress["week-3"]["tasks"]))


if __name__ == "__main__":
    unittest.main()
