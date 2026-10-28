"""Check team isolation, role binding, safe settings, and the real offline CLI."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from foss8 import team, weeks, templates
from foss8.guide import Catalog


ROOT = Path(__file__).resolve().parents[1]


def example():
    return json.loads((ROOT / "docs/team.example.json").read_text(encoding="utf-8"))


class TeamTests(unittest.TestCase):
    def cli(self, cwd, *args):
        (Path(cwd) / ".git").mkdir(exist_ok=True)
        return subprocess.run([sys.executable, str(ROOT / "main.py"), *args],
                              cwd=cwd, capture_output=True, text=True,
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_unconfigured_week_has_roles_and_placeholder_filename(self):
        period = weeks.select(weeks.load(), "9")
        self.assertIn("main 보호 설정 (팀장)", weeks.render(period))
        output = weeks.render(period, (4, 6))
        self.assertIn("회의록_팀명.pdf", output)
        for old in ("박상재", "백지훈", "양하윤", "foss-8.pdf", "{{"):
            self.assertNotIn(old, output)

    def test_roles_multiple_roles_and_explicit_task_owner_are_bound(self):
        config = team.validate(example())
        periods = weeks.load(config)
        period = weeks.select(periods, "9")
        self.assertIn("main 보호 설정 (가람)", weeks.render(period))
        self.assertIn("회의록 작성 (나래)", weeks.render(period, (4,)))
        self.assertIn("LMS에 PDF 제출 (나래)", weeks.render(period, (4, 6)))
        self.assertIn("회의록_team-example.pdf", weeks.render(period, (4, 6)))
        self.assertEqual(config["members"][0]["roles"], ["team_lead", "development_lead"])
        self.assertEqual(config["repository"], "https://github.com/owner/project")

    def test_unassigned_and_shared_roles_do_not_guess_a_person(self):
        raw = example()
        raw["members"][1]["roles"] = []
        raw["task_owners"] = {"minutes_submitter": None}
        values = team.bindings(team.validate(raw))
        self.assertEqual(values["task.minutes_writer"], "문서 담당 미정")
        self.assertEqual(values["task.minutes_submitter"], "회의록 제출 담당 미정")
        raw["members"][1]["roles"] = ["팀장"]
        self.assertEqual(team.bindings(team.validate(raw))["role.team_lead"], "가람·나래")

    def test_all_task_overrides_are_used_in_the_weekly_guide(self):
        raw = example()
        raw["task_owners"].update(repository_admin="narae", development_lead="narae", cross_team_contact="garam")
        periods = weeks.load(team.validate(raw))
        self.assertIn("main 보호 설정 (나래)", weeks.render(weeks.select(periods, "9")))
        self.assertIn("공통 코드 준비 (나래)", weeks.render(weeks.select(periods, "6")))
        self.assertIn("타 팀이 맡을 이슈 준비 (가람)", weeks.render(weeks.select(periods, "10")))

    def test_two_projects_keep_different_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            one = team.save(example(), first / ".foss8/team.json")
            raw = example()
            raw["name"] = "second-team"
            two = team.save(raw, second / ".foss8/team.json")
            self.assertNotEqual(one["name"], two["name"])
            self.assertEqual(team.load(team.config_path(first))["name"], "team-example")
            self.assertEqual(team.load(team.config_path(second))["name"], "second-team")

    def test_nested_working_directory_finds_project_settings_but_stops_at_git_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            outer = Path(tmp)
            config = outer / ".foss8/team.json"
            team.save(example(), config)
            nested = outer / "project/src"
            nested.mkdir(parents=True)
            self.assertEqual(team.config_path(nested), config)
            (outer / "project/.git").mkdir()
            self.assertEqual(team.config_path(nested), outer / "project/.foss8/team.json")

    def test_invalid_settings_leave_existing_file_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "team.json"
            team.save(example(), path)
            original = path.read_bytes()
            invalid = []
            raw = example(); raw["members"].append(copy.deepcopy(raw["members"][0])); invalid.append(raw)
            raw = example(); raw["me"] = "stranger"; invalid.append(raw)
            raw = example(); raw["task_owners"]["minutes_writer"] = "stranger"; invalid.append(raw)
            raw = example(); raw["approved_changes"] = [{"description": "2인 팀"}]; invalid.append(raw)
            raw = example(); raw["name"] = "../outside"; invalid.append(raw)
            for raw in invalid:
                with self.subTest(raw=raw):
                    with self.assertRaises(ValueError):
                        team.save(raw, path)
                    self.assertEqual(path.read_bytes(), original)

    def test_approved_team_changes_do_not_rewrite_handbook_scores(self):
        raw = example()
        raw["approved_changes"] = [{"description": "2인·2기능 승인", "source": "교수 확인 기록", "date": "2026-10-28"}]
        config = team.validate(raw)
        generic = weeks.select(weeks.load(), "13")["references"]
        configured = weeks.select(weeks.load(config), "13")["references"]
        self.assertEqual(generic[-1]["children"][:4], configured[-1]["children"][:4])
        self.assertIn("기능 동작: 12점", json.dumps(configured, ensure_ascii=False))

    def test_cli_import_show_week_and_forms_use_the_same_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = self.cli(tmp, "team", "setup", "--from", str(ROOT / "docs/team.example.json"), "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["data"]["team"]["name"], "team-example")
            show = self.cli(tmp, "team", "show", "--json")
            self.assertEqual(json.loads(show.stdout)["data"]["team"]["me"], "garam")
            output = self.cli(tmp, "week", "9", "--task", "4.6")
            self.assertIn("LMS에 PDF 제출 (나래)", output.stdout)
            self.assertIn("회의록_team-example.pdf", output.stdout)
            form = self.cli(tmp, "format", "midterm")
            self.assertIn("- 팀명: team-example", form.stdout)
            self.assertIn("가람 (@garam)", form.stdout)
            self.assertIn("https://github.com/owner/project", form.stdout)
            self.assertIn("[중간보고서] team-example.pdf", form.stdout)
            self.assertIn("기능 4개", form.stdout)

    def test_configured_minutes_do_not_invent_attendance_or_completion(self):
        item = templates.get(Catalog(), "minutes", team_config=team.validate(example()))
        self.assertIn("회의록 — team-example", item["content"])
        self.assertIn("- 참석: / 불참:", item["content"])
        self.assertNotIn("[x]", item["content"])

    def test_detect_cli_reads_local_roster_without_saving_unless_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "README.md").write_text(
                "| 이름 | 역할 | GitHub | 담당 기능 |\n|---|---|---|---|\n| 가람 | 팀장 | @garam | 입력 |\n", encoding="utf-8")
            result = self.cli(tmp, "team", "detect", "--no-gh", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            data = json.loads(result.stdout)["data"]
            self.assertEqual(data["team"]["members"][0]["github"], "garam")
            self.assertFalse(data["saved"])
            self.assertFalse((Path(tmp) / ".foss8/team.json").exists())
            result = self.cli(tmp, "team", "detect", "--no-gh", "--apply", "--json")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(json.loads(result.stdout)["data"]["saved"])

    def test_setup_can_clear_optional_values(self):
        existing = team.validate(example())
        # name, repository, member count, member fields, me, meeting
        answers = iter(["", "-", "1", "", "", "-", "-", "-", "-"])
        updated = team.validate(team.setup(existing, input_fn=lambda _: next(answers)))
        self.assertEqual(updated["repository"], "")
        self.assertEqual(updated["members"][0]["roles"], [])
        self.assertEqual(updated["members"][0]["features"], [])
        self.assertIsNone(updated["me"])
        self.assertIsNone(updated["task_owners"]["minutes_submitter"])


if __name__ == "__main__":
    unittest.main()
