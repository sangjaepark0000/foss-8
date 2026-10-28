from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from foss8 import assessments, weeks


class AssessmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "assessments.json"
        self.store = assessments.Store(self.path)
        self.start = date(2026, 10, 26)

    def test_week_lifecycle_is_separate_from_attainment(self):
        b = self.store.bundle("me", self.start)
        self.assertEqual(b.end, date(2026, 11, 1))
        self.assertEqual(b.lifecycle(date(2026, 10, 25)), "예정")
        self.assertEqual(b.lifecycle(self.start), "진행 중")
        self.assertEqual(b.lifecycle(date(2026, 11, 2)), "종료")
        self.assertEqual(b.status(date(2026, 11, 2)), "미집계")

    def test_unknown_and_zero_are_different(self):
        b = self.store.bundle("me", self.start)
        self.assertIn("미집계", b.line(assessments.CRITERIA[0]))
        b = self.store.save("me", self.start, {"commits": 0, "issues": None, "prs": None})
        self.assertIn("0/2회 · 2회 남음", b.line(assessments.CRITERIA[0]))
        self.assertEqual(b.status(self.start), "일부 미집계")

    def test_counts_determine_remaining_work_and_closed_result(self):
        b = self.store.save("me", self.start, {"commits": 1, "issues": 1, "prs": 0})
        self.assertEqual(b.status(self.start), "진행 중")
        self.assertEqual(b.status(date(2026, 11, 2)), "미충족")
        self.assertIn("1회 남음", b.line(assessments.CRITERIA[0]))
        b = self.store.save("me", self.start, {"commits": 3, "issues": 1, "prs": 1})
        self.assertEqual(b.status(self.start), "기준 충족")

    def test_exam_exemption_and_learning_start_dates(self):
        exam = self.store.bundle("me", date(2026, 10, 19))
        self.assertEqual(exam.criteria, ())
        self.assertEqual(exam.status(date(2026, 10, 28)), "주간 최소 횟수 면제")
        early = self.store.bundle("me", date(2026, 10, 12))
        self.assertEqual([c.id for c in early.criteria], ["commits", "issues"])
        self.assertEqual(self.store.bundle("me", date(2026, 12, 14)).criteria, ())

    def test_course_week_counts_are_separate_and_keep_legacy_records(self):
        self.store.save("me", self.start, {"commits": 2})
        periods = weeks.load()
        p9 = weeks.select(periods, "9")
        p10 = weeks.select(periods, "10")
        nine = self.store.for_period("me", p9)[0]
        self.assertEqual(nine.start, date(2026, 10, 27))
        self.assertEqual(nine.end, date(2026, 11, 2))
        self.assertEqual(nine.counts, {})
        self.store.save("me", nine.start, {"commits": 1})
        self.assertEqual(self.store.for_period("me", p9)[0].counts, {"commits": 1})
        self.assertEqual(self.store.for_period("me", p10)[0].counts, {})
        self.assertEqual(self.store.bundle("me", self.start).counts, {"commits": 2})
        self.assertFalse(self.store.for_period("me", weeks.select(periods, "8"))[0].exempt)
        self.assertFalse(self.store.for_period("me", weeks.select(periods, "7"))[0].exempt)

    def test_no_weekly_requirements_before_their_first_activity_period(self):
        earlier = weeks.select(weeks.load(), "5")
        self.assertEqual(self.store.for_period("me", earlier), [])

    def test_exam_dates_are_excluded_without_exempting_post_exam_days(self):
        periods = weeks.load()
        c = assessments.CRITERIA[0]
        eight = self.store.for_period("me", weeks.select(periods, "8"))[0]
        nine = self.store.for_period("me", weeks.select(periods, "9"))[0]
        self.assertTrue(eight.exam_overlap)
        self.assertFalse(eight.exempt)
        self.assertEqual(eight.active_ranges(c), [(date(2026, 10, 26), date(2026, 10, 27))])
        self.assertFalse(nine.exam_overlap)
        self.assertEqual(nine.active_ranges(c), [(date(2026, 10, 27), date(2026, 11, 3))])
        self.assertTrue(nine.criteria)

    def test_invalid_counts_preserve_previous_values(self):
        self.store.save("me", self.start, {"commits": 1})
        original = self.path.read_bytes()
        for counts in [{"commits": -1}, {"commits": True}, {"commits": 1.2}, {"unknown": 3}]:
            with self.subTest(counts=counts):
                with self.assertRaises(ValueError):
                    self.store.save("me", self.start, counts)
                self.assertEqual(self.path.read_bytes(), original)

    def test_invalid_state_is_not_overwritten(self):
        self.path.write_text("broken")
        store = assessments.Store(self.path)
        with self.assertRaises(ValueError):
            store.save("me", self.start, {"commits": 1})
        self.assertEqual(self.path.read_text(), "broken")

    def test_saved_counts_are_marked_as_manual_not_github_evidence(self):
        self.store.save("me", self.start, {"commits": 1, "issues": None})
        record = json.loads(self.path.read_text())["contexts"]["me"][self.start.isoformat()]
        self.assertEqual(record["source"], "manual")
        self.assertIsNone(record["counts"]["issues"])
        self.assertNotIn("score", record)


if __name__ == "__main__":
    unittest.main()
