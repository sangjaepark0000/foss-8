import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from foss8.check import ACTIVITY_RULES, check_required_files, collect_activity, format_activity_results, format_file_results
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class CheckTests(unittest.TestCase):
    def run_check(self, *args):
        # UTF-8로 CLI 실행 결과를 수집
        return subprocess.run(
            [sys.executable, "main.py", "check", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        )

    def test_default_path(self):
        result = self.run_check()

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f"검사 대상: {ROOT}", result.stdout)
        self.assertIn("총 배점: 30점", result.stdout)
        self.assertIn("존재 6개 · 누락 0개", result.stdout)
        self.assertEqual(result.stdout.count("상태: 미확인"), 4)

    def test_selected_path_and_missing_files(self):
        # 임시 폴더에 일부 파일만 만들어 검사
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / "README.md").write_text(
                "# 테스트", encoding="utf-8"
            )

            result = self.run_check("--path", directory)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn(
                f"검사 대상: {folder.resolve()}", result.stdout
            )
            self.assertIn("[존재] README.md", result.stdout)
            self.assertIn("[누락] LICENSE", result.stdout)
            self.assertIn("존재 1개 · 누락 5개", result.stdout)
            self.assertEqual(result.stdout.count("상태: 미확인"), 4)

    def test_status_summary_counts_missing_and_non_file(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            for name in ("README.md", "LICENSE", "CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "requirements.txt"):
                (folder / name).write_text("ok", encoding="utf-8")
            output = format_file_results(check_required_files(folder))
            self.assertIn("존재 5개 · 누락 1개", output)
            self.assertIn("문서 내용은 직접 확인해주세요.", output)

            (folder / "main.py").mkdir()
            output_with_dir = format_file_results(check_required_files(folder))
            self.assertIn("존재 5개 · 누락 0개 · 파일 아님 1개", output_with_dir)

    def test_collect_activity_respects_path_and_short_repo(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            (folder / ".git").mkdir()
            (folder / ".foss8").mkdir()
            (folder / ".foss8" / "team.json").write_text(
                '{"name": "팀", "repository": "owner/repo", "members": [{"name": "가람", "github": "garam"}]}',
                encoding="utf-8",
            )
            with patch("foss8.activity.collect", return_value={"ok": True}) as mock_collect:
                result = collect_activity(path=folder)
            self.assertEqual(result, {"ok": True})
            self.assertEqual(mock_collect.call_args[0][0], "owner/repo")

            with self.assertRaisesRegex(ValueError, "존재하는 폴더가 아닙니다"):
                collect_activity(path=folder / "missing")
                
    def test_activity_errors_are_shown_once(self):
        error = "To get started with GitHub CLI, please run:  gh auth login"
        categories = {rule[0]: {"error": error, "links": []} for rule in ACTIVITY_RULES}
        data = {
            "repository": "owner/repo",
            "start": "2026-11-23",
            "end": "2026-11-26",
            "members": [{"name": name, "categories": categories} for name in ("가람", "나래")],
        }

        output = format_activity_results(data)

        self.assertEqual(output.count(error), 1)
        self.assertIn("· 가람: 커밋, PR 생성, PR 병합, 이슈 작성", output)
        self.assertIn("· 나래: 커밋, PR 생성, PR 병합, 이슈 작성", output)
        self.assertIn("gh auth status", output)


    def test_directory_is_not_a_file(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "README.md").mkdir()

            results = check_required_files(directory)
            statuses = {
                item["name"]: item["status"] for item in results
            }

            self.assertEqual(statuses["README.md"], "파일 아님")

    def test_invalid_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            file_path = folder / "sample.txt"
            file_path.write_text("테스트", encoding="utf-8")

            # 존재하지 않는 경로와 파일 경로를 각각 확인
            for target in (folder / "missing", file_path):
                with self.subTest(path=str(target)):
                    result = self.run_check("--path", str(target))

                    self.assertEqual(result.returncode, 2)
                    self.assertIn(
                        "검사 경로가 존재하는 폴더가 아닙니다",
                        result.stderr,
                    )


if __name__ == "__main__":
    unittest.main()