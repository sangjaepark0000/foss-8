"""Collect auditable GitHub activity without deciding whether work is complete."""
from datetime import date, datetime, time, timedelta, timezone
import json
import re
import subprocess
from urllib.parse import quote

KST = timezone(timedelta(hours=9))


def bounds(start, end):
    first, last = date.fromisoformat(start), date.fromisoformat(end)
    if first > last:
        raise ValueError('시작 날짜는 종료 날짜보다 늦을 수 없습니다.')
    return (datetime.combine(first, time.min, KST).astimezone(timezone.utc),
            datetime.combine(last + timedelta(days=1), time.min, KST).astimezone(timezone.utc))


def api(endpoint):
    response = subprocess.run(['gh', 'api', '--paginate', '--slurp', endpoint],
                              capture_output=True, text=True, timeout=120, check=False)
    if response.returncode:
        raise RuntimeError(response.stderr.strip() or 'GitHub 조회 실패')
    pages = json.loads(response.stdout)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise RuntimeError('GitHub 응답 형식을 확인하세요.')
    return [item for page in pages for item in page]


def collect(repo, start, end, members):
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repo):
        raise ValueError('저장소는 owner/repository 형식으로 입력하세요.')
    first, limit = bounds(start, end)
    def inside(value):
        return bool(value) and first <= datetime.fromisoformat(value.replace('Z', '+00:00')) < limit
    def fetch(endpoint):
        try:
            return api(endpoint), None
        except (OSError, subprocess.TimeoutExpired, RuntimeError, ValueError) as exc:
            return [], str(exc)
    base = 'repos/' + repo
    stamps = f'since={first.isoformat().replace("+00:00", "Z")}&until={(limit - timedelta(seconds=1)).isoformat().replace("+00:00", "Z")}'
    branches, commit_error = fetch(base + '/branches?per_page=100')
    commits = []
    if not commit_error:
        seen = set()
        for branch in branches:
            batch, error = fetch(base + '/commits?per_page=100&sha=' + quote(branch['name'], safe='') + '&' + stamps)
            if error:
                commit_error = error
                break
            for commit in batch:
                sha = commit.get('sha')
                if sha and sha not in seen:
                    seen.add(sha)
                    commits.append(commit)
    pulls, pull_error = fetch(base + '/pulls?state=all&per_page=100')
    issues, issue_error = fetch(base + '/issues?state=all&per_page=100')
    reviews, review_error = [], pull_error
    if not pull_error:
        for pr in pulls:
            batch, error = fetch(base + f'/pulls/{pr["number"]}/reviews?per_page=100')
            if error:
                review_error = error
                break
            reviews.extend(batch)
    releases, release_error = fetch(base + '/releases?per_page=100')
    meeting_files, meeting_error = fetch(base + '/contents/docs/meetings?per_page=100')
    meeting_links = []
    for item in meeting_files:
        match = re.match(r'(\d{4}-\d{2}-\d{2})\.md$', item.get('name', ''))
        if match and start <= match[1] <= end and item.get('html_url'):
            meeting_links.append(item['html_url'])
    result = {'repository': repo, 'start': start, 'end': end, 'members': [],
              'releases': {'error': release_error, 'links': [r['html_url'] for r in releases if inside(r.get('published_at'))]},
              'meetings': {'error': meeting_error, 'links': meeting_links}}
    for member in members:
        login = member.get('github', '').lower()
        def authored(item):
            return login and (item.get('user') or {}).get('login', '').lower() == login
        commit_items = [c for c in commits if login and (c.get('author') or {}).get('login', '').lower() == login and len(c.get('parents', [])) < 2 and inside(c['commit']['author']['date'])]
        categories = {
            'commits': (commit_items, commit_error),
            'prs_created': ([p for p in pulls if authored(p) and inside(p.get('created_at'))], pull_error),
            'prs_merged': ([p for p in pulls if authored(p) and inside(p.get('merged_at'))], pull_error),
            'reviews': ([r for r in reviews if authored(r) and r.get('state') != 'PENDING' and inside(r.get('submitted_at'))], review_error),
            'issues': ([i for i in issues if 'pull_request' not in i and authored(i) and inside(i.get('created_at'))], issue_error),
        }
        entry = {'name': member.get('name', ''), 'github': member.get('github', ''), 'categories': {}}
        for name, (items, error) in categories.items():
            if not login:
                error = '팀원의 GitHub ID가 없습니다.'
            entry['categories'][name] = {'error': error, 'links': [] if error else list(dict.fromkeys(item['html_url'] for item in items))}
        result['members'].append(entry)
    return result


def markdown(data):
    labels = {'commits': '커밋', 'prs_created': 'PR 생성', 'prs_merged': 'PR 병합', 'reviews': '제출 리뷰', 'issues': '이슈 생성'}
    lines = [f"조회: {data['repository']} · {data['start']}~{data['end']} (한국 시간)",
             '접근 가능한 브랜치의 커밋을 SHA로 중복 제거하고 병합 커밋은 제외합니다. PR 병합은 작성자 기준, 리뷰는 제출 시각 기준입니다. 일반 댓글은 제외합니다.',
             '각 링크와 숫자를 확인·수정하세요. 활동의 실질성, 충돌 해결, 참석은 직접 작성합니다.', '']
    for member in data['members']:
        lines += [f"### {member['name']} (@{member['github']})"]
        for key, label in labels.items():
            item = member['categories'][key]
            lines.append(f"- {label}: " + (f"조회 실패: {item['error']}" if item['error'] else f"{len(item['links'])}건" + (' — ' + ', '.join(f'[근거 {n}]({url})' for n, url in enumerate(item['links'], 1)) if item['links'] else ' (자료 없음)')))
        lines.append('')
    return '\n'.join(lines)


def report_markdown(data):
    lines = [markdown(data), '### 릴리스와 회의록']
    for key, label in [('releases', '릴리스'), ('meetings', '회의록')]:
        entry = data.get(key, {'error': '수집된 자료가 없습니다. 다시 조회하세요.', 'links': []})
        lines.append('- ' + label + ': ' + (('조회 실패: ' + entry['error']) if entry['error'] else (', '.join(f'[근거 {i}]({url})' for i, url in enumerate(entry['links'], 1)) or '자료 없음')))
    lines += ['', '### 대표 PR 후보 (직접 선택)', '']
    candidates = list(dict.fromkeys(url for m in data['members'] for key in ('prs_created', 'prs_merged') for url in m['categories'][key]['links']))
    lines += [f'- [ ] {url}' for url in candidates] if candidates else ['- 후보 없음 또는 조회 실패: 위 결과를 확인하세요.']
    lines += ['', '스크린샷, 시연, 기능 완성도, 문제 해결과 회고는 직접 작성합니다.']
    return '\n'.join(lines)
