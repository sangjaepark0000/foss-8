from datetime import date
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from foss8 import assessments, github_activity, team, weeks


class GitHubActivityTests(unittest.TestCase):
    def setUp(self):
        self.config = team.validate({"name": "team", "repository": "owner/repo",
                                     "members": [{"name": "나", "github": "me"}], "me": "me"})
        self.period = weeks.select(weeks.load(), "9")
        self.calls = []
        self.fail_commits = False
        self.incomplete = False

    def runner(self, args, **kwargs):
        self.calls.append(args)
        self.assertEqual(args[:2], ["gh", "api"])
        self.assertEqual(kwargs["env"]["GH_PROMPT_DISABLED"], "1")
        endpoint = args[2]
        if endpoint.endswith("/branches"):
            data = [[{"name": "main"}], [{"name": "feature/test"}]]
        elif endpoint.endswith("/commits"):
            if self.fail_commits:
                return subprocess.CompletedProcess(args, 1, "", "secret internal error")
            def commit(sha, stamp):
                return {"sha": sha, "html_url": f"https://github.com/owner/repo/commit/{sha}",
                        "commit": {"committer": {"date": stamp}}}
            data = [[commit("one", "2026-10-26T15:00:00Z"),
                     commit("outside", "2026-10-26T14:59:59Z")],
                    [commit("two", "2026-11-02T14:59:59Z"),
                     commit("next", "2026-11-02T15:00:00Z")]]
        else:
            query = next(a for a in args if a.startswith("q="))
            self.assertIn("repo:owner/repo author:me", query)
            if "is:pr" in query:
                self.assertIn("created:2026-10-29T15:00:00Z..2026-11-02T14:59:59Z", query)
                self.assertIn("is:merged merged:2026-10-29T15:00:00Z..2026-11-02T14:59:59Z", query)
            else:
                self.assertIn("created:2026-10-26T15:00:00Z..2026-11-02T14:59:59Z", query)
            data = [{"total_count": 2, "incomplete_results": self.incomplete,
                     "items": [{"number": 1, "html_url": "https://github.com/owner/repo/issues/1"}]},
                    {"total_count": 2, "incomplete_results": False,
                     "items": [{"number": 2, "html_url": "https://github.com/owner/repo/issues/2"}]}]
        return subprocess.CompletedProcess(args, 0, json.dumps(data), "")

    def test_week_kst_boundaries_pagination_and_cross_branch_deduplication(self):
        result = github_activity.collect(self.config, self.period, runner=self.runner)
        self.assertEqual(result.counts, {"commits": 2, "issues": 2, "prs": 2})
        self.assertFalse(result.errors)
        self.assertEqual(len(result.evidence["commits"]), 2)
        self.assertEqual(len(self.calls), 5)
        self.assertTrue(all("--paginate" in args and "--slurp" in args for args in self.calls))

    def test_failures_stay_unknown_instead_of_zero_and_keep_successes(self):
        self.fail_commits = True
        result = github_activity.collect(self.config, self.period, runner=self.runner)
        self.assertNotIn("commits", result.counts)
        self.assertEqual(result.counts["issues"], 2)
        self.assertIn("gh auth login", result.errors[0])
        self.assertNotIn("secret", str(result))

    def test_incomplete_search_is_not_a_count(self):
        self.incomplete = True
        result = github_activity.collect(self.config, self.period, runner=self.runner)
        self.assertEqual(result.counts, {"commits": 2})
        self.assertEqual(len(result.errors), 2)

    def test_requirements_are_explicit_and_do_not_run_gh(self):
        self.assertEqual([key for key, _ in github_activity.requirements(None)], ["repository", "me"])
        with self.assertRaisesRegex(ValueError, "설정"):
            github_activity.collect({}, self.period, runner=lambda *a, **kw: self.fail("unexpected gh call"))

    def test_post_exam_counts_use_only_non_exempt_dates(self):
        calls = []
        def runner(args, **kwargs):
            calls.append(args)
            if args[2].endswith("/branches"):
                data = [[{"name": "main"}]]
            elif args[2].endswith("/commits"):
                self.assertIn("since=2026-10-25T15:00:00Z", args)
                self.assertIn("until=2026-10-26T14:59:59Z", args)
                data = [[{"sha": "resumed", "html_url": "https://github.com/o/r/commit/a",
                          "commit": {"committer": {"date": "2026-10-26T00:00:00Z"}}},
                         {"sha": "exam", "html_url": "https://github.com/o/r/commit/b",
                          "commit": {"committer": {"date": "2026-10-25T00:00:00Z"}}}]]
            else:
                query = next(a for a in args if a.startswith("q="))
                self.assertIn("is:issue created:2026-10-25T15:00:00Z..2026-10-26T14:59:59Z", query)
                data = [{"total_count": 0, "incomplete_results": False, "items": []}]
            return subprocess.CompletedProcess(args, 0, json.dumps(data), "")
        period = weeks.select(weeks.load(), "8")
        result = github_activity.collect(self.config, period, runner=runner, on=date(2026, 10, 26))
        self.assertEqual(result.counts, {"commits": 1, "issues": 0})
        self.assertFalse(result.errors)
        calls.clear()
        result = github_activity.collect(self.config, period, runner=runner, on=date(2026, 10, 24))
        self.assertEqual(result.counts, {})
        self.assertEqual(calls, [])

    def test_prs_stay_unknown_until_their_start_date(self):
        result = github_activity.collect(self.config, self.period, runner=self.runner, on=date(2026, 10, 28))
        self.assertEqual(result.counts, {"commits": 2, "issues": 2})

    def test_save_preserves_individual_provenance_and_failed_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = assessments.Store(Path(tmp) / "assessments.json")
            start = date(2026, 10, 30)
            store.save("me", start, {"commits": 2, "issues": 1})
            store.save("me", start, {"issues": 3}, source="github", evidence={"issues": ["https://github.com/x/y/issues/1"]})
            record = store.record("me", start)
            self.assertEqual(record["counts"], {"commits": 2, "issues": 3})
            self.assertEqual(record["sources"], {"commits": "manual", "issues": "github"})
            self.assertIn("synced_at", record)
