"""Check form completeness and the real CLI using only the standard library."""
import os
import re
import subprocess
import sys
import unittest
from dataclasses import replace
from pathlib import Path

from foss8.guide import Catalog
from foss8.templates import get


ROOT = Path(__file__).resolve().parents[1]


class FormsTests(unittest.TestCase):
    def setUp(self):
        self.catalog = Catalog()

    def cli(self, *args):
        return subprocess.run([sys.executable, "main.py", *args], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8",
                              env={**os.environ, "PYTHONIOENCODING": "utf-8"})

    def test_minutes_has_sections_and_blank_rows_without_example_facts(self):
        item = get(self.catalog, "minutes")
        content = item["content"]
        self.assertEqual(len(re.findall(r"^## \d+\. ", content, re.M)), 6)
        for heading in ["지난주 결정 사항 점검", "팀원별 진행 상황", "논의 내용과 결정 사항",
                        "다음 주 할 일", "활동 로그", "이번 주 점검표"]:
            self.assertIn(heading, content)
        for fact in ["홍길동", "김철수", "이영희", "박민수", "2026-10-13", "budget.json", "storage.py", "[x]"]:
            self.assertNotIn(fact, content)
        self.assertIn("- 참석: / 불참:", content)
        self.assertIn("- [ ] 해당 주차", content)
        table_groups = re.findall(r"(?:^\|.*\n)+", content, re.M)
        self.assertEqual(len(table_groups), 4)
        for table in table_groups:
            rows = table.splitlines()
            self.assertEqual(len(rows), 3)
            self.assertTrue(all(not value.strip() for value in rows[2].strip("|").split("|")))
            self.assertEqual(len(rows[0].split("|")), len(rows[2].split("|")))
        self.assertEqual(item["source"]["pages"], [40])
        self.assertIn(item["source"]["url"], content)

    def test_report_forms_keep_sections_rules_and_portable_sources(self):
        cases = [("proposal", 7, "기대 효과 및 목표", "10/1(목) 18:00", [15]),
                 ("midterm", 6, "남은 계획", "11/5(목) 18:00", [33]),
                 ("final", 8, "회고와 향후 계획", "12/17(목) 18:00", [34, 35])]
        for name, count, last, deadline, pages in cases:
            with self.subTest(name=name):
                item = get(self.catalog, name)
                content = item["content"]
                self.assertEqual(len(re.findall(r"^## \d+\. ", content, re.M)), count)
                self.assertIn(f"## {count}. {last}", content)
                for required in ["## 표지", "## 목차", "## 제출 기준", "[작성]", "기능 4개", deadline]:
                    self.assertIn(required, content)
                self.assertEqual(item["source"]["pages"], pages)
                self.assertIn(item["source"]["url"], content)
                self.assertNotRegex(content, r"\]\((?!https://)[^)]+\)")
                self.assertNotIn("<br>", content)
        final = get(self.catalog, "final")["content"]
        self.assertIn("## 부록", final)
        self.assertIn("회의록 10회 링크", final)
        self.assertIn("대표 풀 리퀘스트 2개 링크", final)
        midterm = get(self.catalog, "midterm")["content"]
        self.assertIn("충돌 해결 사례 1개", midterm)
        self.assertIn("동작하는 기능 2개", midterm)

    def test_each_form_is_printed_by_the_existing_entrypoint(self):
        for name in ["minutes", "proposal", "midterm", "final"]:
            with self.subTest(name=name):
                result = self.cli("format", name)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout, get(self.catalog, name)["content"])
                self.assertEqual(result.stderr, "")

    def test_incomplete_and_invalid_requests_show_supported_forms(self):
        for args, status in [(('format',), 0), (('format', '--help'), 0),
                             (('format', 'unknown'), 2)]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, status)
                for name in ["minutes", "proposal", "midterm", "final"]:
                    self.assertIn(name, result.stdout + result.stderr)
                self.assertNotIn("Traceback", result.stderr)
        with self.assertRaises(ValueError):
            get(self.catalog, "../secret")

    def test_missing_source_fields_fail_instead_of_producing_incomplete_forms(self):
        original = self.catalog.documents["05-proposal"]
        changed = original.markdown.replace("| 7 | 기대 효과 및 목표", "| ? | 기대 효과 및 목표")
        self.catalog.documents[original.id] = replace(original, markdown=changed)
        with self.assertRaisesRegex(ValueError, "필수 항목 7개"):
            get(self.catalog, "proposal")
        changed = original.markdown.replace("<table>", "<broken-table>")
        self.catalog.documents[original.id] = replace(original, markdown=changed)
        with self.assertRaisesRegex(ValueError, "제출 기준"):
            get(self.catalog, "proposal")

    def test_other_cli_commands_still_run(self):
        for args in [(), ('help',), ('check',), ('week',)]:
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stderr, "")


if __name__ == "__main__":
    unittest.main()
