import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from foss8 import discovery, team


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "docs/members").mkdir(parents=True)
        (self.root / "README.md").write_text(
            "| 이름 | 역할 | GitHub | 담당 기능 |\n|---|---|---|---|\n"
            "| 가람 | 팀장 | [garam](https://github.com/garam) | 입력 |\n"
            "| 나래 | 문서 담당 | @narae | 출력 |\n", encoding="utf-8")
        (self.root / "docs/team-agreement.md").write_text(
            "# 팀 약속 — alpha\n| 이름 | 역할 | GitHub | 담당 기능 |\n|---|---|---|---|\n"
            "| 가람 | 팀장 | @garam-old | 미정 |\n| 공동 책임 | 리뷰·품질 담당 | | |\n"
            "- 정기 회의: 금요일 09:00~10:00, 오프라인. 불참 시 알림\n"
            "- 응답: 채팅 24시간, PR 리뷰 48시간\n", encoding="utf-8")
        (self.root / "docs/members/가람.md").write_text("이름: 가람\n담당: 개발리드, 입력 기능\n", encoding="utf-8")
        self.calls = []
        self.remote = "git@github.com:owner/project.git"
        self.fail_gh = False
        self.collaborators = [[{"login": "garam", "type": "User", "permissions": {"admin": True}},
                               {"login": "narae", "type": "User", "permissions": {"admin": False}}]]

    def runner(self, args, **kwargs):
        self.calls.append(args)
        if args[:3] == ["git", "rev-parse", "--show-toplevel"]:
            value = str(self.root)
        elif args[:4] == ["git", "remote", "get-url", "origin"]:
            value = self.remote
        elif args[:2] == ["gh", "api"]:
            if self.fail_gh:
                return subprocess.CompletedProcess(args, 1, "", "private failure details not for display")
            if args[2] == "user":
                value = json.dumps({"login": "garam", "name": "Garam"})
            elif args[2].endswith("/collaborators"):
                value = json.dumps(self.collaborators)
            else:
                value = json.dumps({"name": "project", "html_url": "https://github.com/owner/project"})
        else:
            raise AssertionError(args)
        return subprocess.CompletedProcess(args, 0, value, "")

    def test_reads_repository_identity_roster_roles_and_agreements(self):
        result = discovery.detect(self.root, runner=self.runner)
        config = result.config
        self.assertEqual(config["name"], "alpha")
        self.assertEqual(config["repository"], "https://github.com/owner/project")
        self.assertEqual(config["me"], "garam")
        garam = next(p for p in config["members"] if p["github"] == "garam")
        self.assertIn("development_lead", garam["roles"])
        self.assertIn("quality", garam["roles"])
        self.assertEqual(garam["features"], ["입력"])
        self.assertNotIn("garam-old", [p["github"] for p in config["members"]])
        self.assertTrue(result.warnings)
        self.assertEqual(config["agreements"]["review_hours"], 48)
        self.assertEqual(config["task_owners"]["repository_admin"], "garam")
        self.assertFalse((self.root / ".foss8").exists())

    def test_missing_github_access_keeps_local_information(self):
        self.fail_gh = True
        result = discovery.detect(self.root, runner=self.runner)
        self.assertEqual(len(result.config["members"]), 2)
        self.assertIsNone(result.config["me"])
        self.assertNotIn("private failure", " ".join(result.warnings))

    def test_offline_detection_does_not_call_gh(self):
        result = discovery.detect(self.root, use_github=False, runner=self.runner)
        self.assertFalse(any(args[0] == "gh" for args in self.calls))
        self.assertEqual(result.config["name"], "alpha")

    def test_credentials_in_remote_are_not_retained(self):
        url, slug = discovery.repository_url("https://token:secret@github.com/owner/project.git")
        self.assertEqual(url, "https://github.com/owner/project")
        self.assertEqual(slug, "owner/project")
        self.assertEqual(discovery.repository_url("ssh://git@github.com/owner/project.git"), (url, slug))

    def test_collaborators_do_not_invent_course_roles_or_bot_members(self):
        (self.root / "README.md").unlink()
        (self.root / "docs/team-agreement.md").unlink()
        self.collaborators[0].append({"login": "robot", "type": "Bot"})
        result = discovery.detect(self.root, runner=self.runner)
        self.assertEqual([p["roles"] for p in result.config["members"]], [[], []])
        self.assertNotIn("robot", [p["github"] for p in result.config["members"]])

    def test_existing_settings_and_explicit_unassigned_values_win(self):
        found = discovery.detect(self.root, runner=self.runner).config
        existing = team.validate({"name": "my-team", "repository": found["repository"],
                                  "members": [{"name": "수동 이름", "github": "garam", "roles": [], "features": []}],
                                  "task_owners": {"repository_admin": None}})
        merged = discovery.merge(existing, found)
        self.assertEqual(merged["name"], "my-team")
        self.assertEqual(merged["members"][0]["roles"], [])
        self.assertIsNone(merged["task_owners"]["repository_admin"])

    def test_different_repository_does_not_mix_teams(self):
        found = discovery.detect(self.root, runner=self.runner).config
        existing = team.validate({"name": "other-team", "repository": "other/repo"})
        self.assertEqual(discovery.merge(existing, found), existing)

    def test_new_named_profile_can_fill_empty_roster(self):
        found = discovery.detect(self.root, runner=self.runner).config
        merged = discovery.merge(team.validate({"name": "custom"}), found)
        self.assertEqual(merged["name"], "custom")
        self.assertEqual(merged["me"], "garam")
        self.assertEqual(len(merged["members"]), 2)


if __name__ == "__main__":
    unittest.main()
