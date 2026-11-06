import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from foss8.check import check_required_files


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
            self.assertEqual(result.stdout.count("상태: 미확인"), 4)

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