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
        with self.assertRaisesRegex(ValueError, 'YYYY-MM-DD'):
            activity.bounds('2026/10/08', '2026-10-09')

    def test_missing_gh_gives_actionable_korean_error(self):
        with patch('foss8.activity.subprocess.run', side_effect=FileNotFoundError('gh')):
            with self.assertRaisesRegex(RuntimeError, 'GitHub CLI'):
                activity.api('repos/a/b/branches')

    def test_collect_skips_stale_pr_reviews(self):
        stale_pr = {'number': 1, 'user': {'login': 'alice'}, 'created_at': '2026-09-01T00:00:00Z',
                    'updated_at': '2026-09-02T00:00:00Z', 'merged_at': None, 'html_url': 'https://example/pr1'}
        active_pr = {'number': 2, 'user': {'login': 'alice'}, 'created_at': '2026-10-08T01:00:00Z',
                     'updated_at': '2026-10-08T02:00:00Z', 'merged_at': None, 'html_url': 'https://example/pr2'}
        called = []
        def fake(endpoint):
            called.append(endpoint)
            if '/branches?' in endpoint: return []
            if '/pulls?' in endpoint: return [stale_pr, active_pr]
            return []
        with patch('foss8.activity.api', side_effect=fake):
            activity.collect('team/project', '2026-10-08', '2026-10-08', [{'name': 'A', 'github': 'alice'}])
        self.assertNotIn('repos/team/project/pulls/1/reviews?per_page=100', called)
        self.assertIn('repos/team/project/pulls/2/reviews?per_page=100', called)

    def test_validate_data_rejects_malformed_activity_json(self):
        with self.assertRaisesRegex(ValueError, '활동 JSON 형식'):
            activity.validate_data({'name': 'team'})

        valid_categories = {
            key: {'links': [], 'error': None}
            for key in ('commits', 'prs_created', 'prs_merged', 'reviews', 'issues')
        }
        base = {'repository': 'team/project', 'start': '2026-10-08', 'end': '2026-10-08'}

        # 팀원 항목에 name 또는 github가 없거나 문자열이 아닌 경우
        for bad_member in (
            {'github': 'alice', 'categories': valid_categories},
            {'name': 'A', 'categories': valid_categories},
            {'name': 123, 'github': 'alice', 'categories': valid_categories},
            {'name': 'A', 'github': None, 'categories': valid_categories},
        ):
            with self.assertRaisesRegex(ValueError, '팀원 활동 항목'):
                activity.validate_data({**base, 'members': [bad_member]})

        # 카테고리의 links가 리스트가 아니거나 문자열 목록이 아닌 경우
        for bad_links in ('https://example/commit', 123, None, [123]):
            bad_categories = {**valid_categories, 'commits': {'links': bad_links, 'error': None}}
            with self.assertRaisesRegex(ValueError, '필수 활동 항목'):
                activity.validate_data({**base, 'members': [{'name': 'A', 'github': 'alice', 'categories': bad_categories}]})

        # 카테고리의 error가 None 또는 문자열이 아닌 경우
        bad_error_categories = {**valid_categories, 'commits': {'links': [], 'error': 500}}
        with self.assertRaisesRegex(ValueError, '필수 활동 항목'):
            activity.validate_data({**base, 'members': [{'name': 'A', 'github': 'alice', 'categories': bad_error_categories}]})
