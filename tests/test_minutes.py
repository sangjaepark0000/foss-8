from datetime import date
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from foss8 import minutes

ROOT = Path(__file__).resolve().parents[1]


class MinutesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / '.git').mkdir()
        self.config = minutes.normalize_config({'name': '테스트 팀', 'repository': 'owner/project',
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
        self.assertIn('첫 풀 리퀘스트', content)
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
        profile = self.root / '.foss8/team.json'
        profile.parent.mkdir()
        profile.write_text(json.dumps(self.config, ensure_ascii=False), encoding='utf-8')
        args = [sys.executable, str(ROOT / 'main.py'), 'format', 'minutes', '--date', '2026-10-28', '-o', 'docs/meetings/2026-10-28.md']
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.root / 'docs/meetings/2026-10-28.md'
        self.assertIn('테스트 팀', path.read_text(encoding='utf-8'))
        repeated = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        self.assertEqual(repeated.returncode, 2)
        self.assertIn('파일이 이미', repeated.stderr)

    def test_readme_and_remote_supply_defaults_without_copying_credentials(self):
        (self.root / 'README.md').write_text('| 이름 | 역할 | GitHub |\n|---|---|---|\n| 가람 | 팀장 | @garam |\n', encoding='utf-8')
        response = subprocess.CompletedProcess([], 0, 'https://token:secret@github.com/owner/project.git\n', '')
        with patch('foss8.minutes.subprocess.run', return_value=response):
            config = minutes.load_config(start=self.root)
        self.assertEqual(config['repository'], 'https://github.com/owner/project')
        self.assertEqual(config['name'], 'project')
        self.assertEqual(config['members'], [{'name': '가람', 'github': 'garam'}])
        self.assertNotIn('secret', str(config))
        self.assertFalse((self.root / '.foss8').exists())

    def test_explicit_team_file_overrides_inferred_project_information(self):
        profile = self.root / '팀정보.json'
        profile.write_text(json.dumps(self.config, ensure_ascii=False), encoding='utf-8')
        with patch('foss8.minutes.subprocess.run') as git:
            config = minutes.load_config(profile, team_name='다른 팀', start=self.root)
            git.assert_not_called()
        self.assertEqual(config['name'], '다른 팀')
        self.assertEqual(config['members'], self.config['members'])
