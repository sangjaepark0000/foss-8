import unittest
from unittest.mock import patch
from foss8 import activity


class ActivityTests(unittest.TestCase):
    def test_collect_respects_korean_dates_and_distinguishes_prs_and_failures(self):
        commit = {'sha': 'one', 'author': {'login': 'alice'}, 'parents': [{}], 'commit': {'author': {'date': '2026-10-07T15:00:00Z'}}, 'html_url': 'https://example/commit'}
        merge = {**commit, 'sha': 'merge', 'parents': [{}, {}], 'html_url': 'https://example/merge'}
        pr = {'number': 1, 'user': {'login': 'alice'}, 'created_at': '2026-10-08T01:00:00Z', 'merged_at': None, 'html_url': 'https://example/pr'}
        issue = {'user': {'login': 'alice'}, 'created_at': '2026-10-08T00:00:00Z', 'html_url': 'https://example/issue'}
        def fake(endpoint):
            if '/branches?' in endpoint: return [{'name': 'main'}, {'name': 'feature/test'}]
            if '/commits?' in endpoint: return [commit, merge]
            if '/pulls?' in endpoint: return [pr]
            if '/reviews?' in endpoint: raise RuntimeError('권한 없음')
            return [issue]
        with patch('foss8.activity.api', side_effect=fake):
            data = activity.collect('team/project', '2026-10-08', '2026-10-08', [{'name': 'A', 'github': 'alice'}])
        categories = data['members'][0]['categories']
        self.assertEqual(categories['commits']['links'], ['https://example/commit'])
        self.assertEqual(categories['prs_merged']['links'], [])
        self.assertEqual(categories['reviews']['error'], '권한 없음')
        self.assertEqual(categories['issues']['links'], ['https://example/issue'])
        self.assertIn('조회 실패: 권한 없음', activity.markdown(data))
        self.assertIn('- [ ] https://example/pr', activity.report_markdown(data))

    def test_invalid_range_rejected(self):
        with self.assertRaises(ValueError):
            activity.bounds('2026-10-09', '2026-10-08')
