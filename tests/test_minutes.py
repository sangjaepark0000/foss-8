from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from foss8 import minutes, team

ROOT = Path(__file__).resolve().parents[1]


class MinutesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.git').mkdir()
        self.config = team.validate({'name': '테스트 팀', 'repository': 'owner/project',
                                    'members': [{'name': '가람', 'github': 'garam'},
                                                {'name': '나래', 'github': 'narae'}]})

    def test_post_exam_meeting_uses_actual_submission_cycle_and_blank_facts(self):
        content = minutes.draft('2026-10-28', config=self.config)
        self.assertIn('# [WEEK9] 회의록 — 테스트 팀', content)
        self.assertIn('기록기간: 2026-10-15 ~ 2026-10-28', content)
        self.assertIn('제출 마감: 2026-10-29 18:00', content)
        self.assertIn('- 일시: 2026-10-28 (수)', content)
        self.assertIn('- 참석: / 불참:', content)
        self.assertIn('| 가람 |  |  |', content)
        self.assertIn('| 나래 |  |  |', content)
        self.assertIn('| 가람 |  |  |  |  |  |  |', content)
        self.assertIn('- [ ] 첫 PR 병합', content)
        self.assertNotIn('[x]', content)
        self.assertNotIn('홍길동', content)
        self.assertEqual(sum(line.startswith('## ') for line in content.splitlines()), 6)

    def test_meeting_date_and_submission_week_are_separate(self):
        content = minutes.draft('2026-10-30', week='9', config=self.config)
        self.assertIn('WEEK9', content)
        self.assertIn('제출 마감: 2026-10-29 18:00', content)
        automatic = minutes.draft('2026-10-30', config=self.config)
        self.assertIn('[WEEK10]', automatic)
        self.assertIn('제출 마감: 2026-11-05 18:00', automatic)

    def test_draft_distinguishes_post_class_actions_and_later_submissions(self):
        content = minutes.draft('2026-10-28', config=self.config)
        self.assertIn('첫 PR 병합 (10/30 수업 후)', content)
        self.assertIn('충돌 해결 실습 (10/30 수업 후)', content)
        self.assertIn('회의록 #5(11/5) [다음 제출]', content)
        following = minutes.draft('2026-11-04', config=self.config)
        self.assertIn('첫 PR 병합 (10/30 수업 후) [이어서]', following)

    def test_makeup_and_non_submission_weeks(self):
        content = minutes.draft('2026-12-09', week='makeup', config=self.config)
        self.assertIn('[WEEK4]', content)
        self.assertIn('2026-12-10 18:00', content)
        for week in ['4', '8', '15']:
            with self.assertRaisesRegex(ValueError, '회의록 제출이 없습니다'):
                minutes.draft('2026-10-28', week=week)
        with self.assertRaisesRegex(ValueError, '남은 회의록'):
            minutes.draft('2026-12-18')

    def test_atomic_save_protects_written_minutes_and_allows_explicit_force(self):
        path = self.root / 'meetings/회의록.md'
        minutes.create('2026-10-28', config=self.config, output=path)
        path.write_text('직접 작성한 내용', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            minutes.create('2026-10-28', config=self.config, output=path)
        self.assertEqual(path.read_text(), '직접 작성한 내용')
        minutes.create('2026-10-28', config=self.config, output=path, force=True)
        self.assertIn('[WEEK9]', path.read_text())
        with self.assertRaises(ValueError):
            minutes.create('2026-10-28', output=self.root / 'wrong.pdf')
        self.assertEqual(list(path.parent.iterdir()), [path])

    def test_cli_reads_project_config_and_creates_utf8_file(self):
        team.save(self.config, self.root / '.foss8/team.json')
        args = [sys.executable, str(ROOT / 'main.py'), 'minutes', 'draft', '--date', '2026-10-28']
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / 'docs/meetings/2026-10-28.md'
        self.assertIn('테스트 팀', path.read_text(encoding='utf-8'))
        repeated = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn('파일이 이미', repeated.stderr)
