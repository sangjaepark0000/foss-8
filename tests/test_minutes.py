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

    def test_shared_report_cover_uses_team_file_without_claiming_attendance(self):
        from foss8 import templates
        from foss8.guide import Catalog
        self.config['project'] = '도구'
        for name in ('proposal', 'midterm', 'final'):
            content = templates.fill_report(templates.get(Catalog(), name)['content'], self.config)
            self.assertIn('- 팀명: 테스트 팀', content)
            self.assertIn('- 프로젝트 이름: 도구', content)
            self.assertIn('가람 (@garam)', content)
            self.assertIn('[작성]', content)

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

    def test_fetch_activity_uses_recording_period_and_fills_member_rows(self):
        self.config['repository'] = 'https://github.com/owner/project.git'
        def category(*links, error=None):
            return {'links': list(links), 'error': error}
        categories = {
            'commits': category('https://example/commit'),
            'prs_created': category('https://example/pr1', 'https://example/pr2'),
            'prs_merged': category('https://example/pr1'),
            'reviews': category(error='권한 없음'),
            'issues': category(),
        }
        empty = {key: category() for key in categories}
        data = {'repository': 'owner/project', 'start': '2026-10-15', 'end': '2026-10-28',
                'members': [{'name': '가람', 'github': 'garam', 'categories': categories},
                            {'name': '나래', 'github': 'narae', 'categories': empty}]}
        with patch('foss8.activity.collect', return_value=data) as collect:
            content = minutes.draft('2026-10-28', config=self.config, fetch_activity=True)
        collect.assert_called_once_with('owner/project', '2026-10-15', '2026-10-28', self.config['members'])
        self.assertIn('| 가람 | 1 | 2/1 | 확인 불가 | 0 |  |  |', content)
        self.assertIn('| 나래 | 0 | 0/0 | 0 | 0 |  |  |', content)
        self.assertIn('조회 실패: 권한 없음', content)
        self.assertIn('[근거 1](https://example/commit)', content)

    def test_fetch_activity_is_opt_in(self):
        with patch('foss8.activity.collect') as collect:
            content = minutes.draft('2026-10-14', config=self.config)
        collect.assert_not_called()
        self.assertIn('| 가람 |  |  |  |  |  |  |', content)
        self.assertNotIn('GitHub 활동 근거 초안', content)

    def test_fetch_activity_cli_rejects_incompatible_options(self):
        base = [sys.executable, str(ROOT / 'main.py'), 'format']
        for args, message in [
            (['minutes', '--fetch-activity', '--activity', 'activity.json'], 'not allowed'),
            (['proposal', '--fetch-activity'], '회의록 초안 생성'),
            (['minutes', '--fetch-activity', '--pdf', 'minutes.md'], '회의록 초안 생성'),
        ]:
            with self.subTest(args=args):
                result = subprocess.run(base + args, cwd=self.root, capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertIn(message, result.stderr)

    def test_exam_week_discloses_distinct_submission_cycle_and_sources(self):
        content = minutes.draft('2026-10-21', config=self.config)
        self.assertIn('수업 주차: 8주차', content)
        self.assertIn('해당 수업 주차에 해당하는 회의록 제출 회차는 없습니다', content)
        self.assertIn('회의록 제출 일정', content)
        self.assertIn('개인 점검표', content)

    def test_carry_previous_actions_preserves_source_without_inference(self):
        source = ROOT / 'docs/meetings/2026-10-07.md'
        before = source.read_text(encoding='utf-8')
        content = minutes.carry_previous(minutes.draft('2026-10-14', config=self.config), source)
        self.assertIn('| 현재 수업 주차 계산 구현 | 양하윤 | 10.14 | #11 | 확인 필요 |', content)
        self.assertIn(source.as_uri(), content)
        self.assertEqual(minutes.carry_previous(content, source), content)
        self.assertEqual(source.read_text(encoding='utf-8'), before)
        missing = minutes.carry_previous(minutes.draft('2026-10-14', config=self.config), self.root / 'missing.md')
        self.assertIn('이전 회의록을 읽지 못했습니다', missing)

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
        self.assertEqual(path.read_text(encoding="utf-8"), '직접 작성한 내용')
        minutes.create('2026-10-28', config=self.config, output=path, force=True)
        self.assertIn('[WEEK9]', path.read_text(encoding="utf-8"))
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

    def test_invalid_date_and_malformed_activity_json_show_friendly_errors(self):
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            minutes.draft('2026/10/28', config=self.config)
        bad_team = self.root / 'bad.json'
        bad_team.write_text('{broken', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, '팀 기본정보 JSON 형식'):
            minutes.load_config(bad_team)
        bad_activity = self.root / 'wrong_activity.json'
        bad_activity.write_text('{"name": "not-activity"}', encoding='utf-8')
        result = subprocess.run(
            [sys.executable, str(ROOT / 'main.py'), 'format', 'minutes', '--date', '2026-10-28', '--activity', str(bad_activity)],
            cwd=self.root, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn('활동 JSON 형식', result.stderr)
        self.assertNotIn('Traceback', result.stderr)

    def test_activity_cli_supports_force_overwrite(self):
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO
        from foss8 import cli
        profile = self.root / '팀정보.json'
        profile.write_text(json.dumps(self.config, ensure_ascii=False), encoding='utf-8')
        out_path = self.root / 'act.json'
        sample = {'repository': 'owner/project', 'start': '2026-10-08', 'end': '2026-10-08', 'members': []}
        with patch('foss8.activity.collect', return_value=sample), redirect_stdout(StringIO()), redirect_stderr(StringIO()):
            self.assertEqual(cli.main(['activity', '--repo', 'owner/project', '--start', '2026-10-08', '--end', '2026-10-08', '--team-file', str(profile), '-o', str(out_path)]), 0)
            self.assertEqual(cli.main(['activity', '--repo', 'owner/project', '--start', '2026-10-08', '--end', '2026-10-08', '--team-file', str(profile), '-o', str(out_path)]), 2)
            self.assertEqual(cli.main(['activity', '--repo', 'owner/project', '--start', '2026-10-08', '--end', '2026-10-08', '--team-file', str(profile), '-o', str(out_path), '--force']), 0)
