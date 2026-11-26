"""Tests for weekly roadmap parsing and week CLI lookups."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest

from foss8 import cli, weeks
from foss8.guide import Catalog


class WeeksTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()

    def test_cell_preserves_spacing_and_strips_markdown_links(self):
        item9 = weeks.get_weekly_item(self.catalog, "9")
        output9 = weeks.result_line(item9)
        self.assertNotIn("appendix-d-git-drill.md", output9)
        self.assertIn("부록 D-2", output9)
        self.assertIn("→ Merge", output9)
        self.assertIn("리퀘스트, 태그", output9)

        item13 = weeks.get_weekly_item(self.catalog, "13")
        output13 = weeks.result_line(item13)
        self.assertIn("파일, 더 좋은", output13)
        self.assertIn("문서만. README", output13)

    def test_makeup_accepts_english_and_korean_selectors(self):
        en = weeks.get_weekly_item(self.catalog, "makeup")
        ko = weeks.get_weekly_item(self.catalog, "보강")
        self.assertEqual(en["id"], "week-4-makeup")
        self.assertEqual(en, ko)

    def test_invalid_week_raises_clear_error(self):
        with self.assertRaisesRegex(ValueError, "안내서에 없는 주차"):
            weeks.get_weekly_item(self.catalog, "99")
        with self.assertRaisesRegex(ValueError, "잘못된 입력"):
            weeks.get_weekly_item(self.catalog, "invalid")

    def test_week_list_cli(self):
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = cli.main(["week", "--list"])
        self.assertEqual((status, err.getvalue()), (0, ""))
        self.assertIn("week-4-makeup", out.getvalue())
        self.assertIn("week-15", out.getvalue())


if __name__ == "__main__":
    unittest.main()
