"""Prepare meeting drafts using the main branch's handbook and local team information."""
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import urlparse

from . import templates
from .guide import Catalog, plain


def today():
    return datetime.now(timezone(timedelta(hours=9))).date()


@dataclass(frozen=True)
class Cycle:
    period_id: str
    week: str
    recording_start: str
    recording_end: str
    due_at: str


def cycles(catalog=None):
    catalog = catalog or Catalog()
    doc, _ = catalog.resolve('minutes')
    result = []
    for line in doc.markdown.splitlines():
        if not line.startswith('|'):
            continue
        cells = [plain(cell.strip()) for cell in line.strip().strip('|').split('|')]
        if len(cells) < 4 or not cells[0].isdigit():
            continue
        week = re.search(r'WEEK(\d+)', cells[1])
        due = re.fullmatch(r'(\d+)/(\d+)', cells[2])
        recording = re.fullmatch(r'(\d+)/(\d+)~(\d+)/(\d+)', cells[3].replace(' ', ''))
        if not week or not due or not recording:
            raise ValueError('안내서의 회의록 제출 날짜표를 확인하세요.')
        start_month, start_day, end_month, end_day = map(int, recording.groups())
        due_month, due_day = map(int, due.groups())
        result.append(Cycle('makeup' if week[1] == '4' else week[1], week[1],
                            date(2026, start_month, start_day).isoformat(),
                            date(2026, end_month, end_day).isoformat(),
                            f'{date(2026, due_month, due_day).isoformat()}T18:00:00+09:00'))
    if len(result) != 10:
        raise ValueError('안내서의 회의록 제출 회차 10개를 읽지 못했습니다.')
    return sorted(result, key=lambda item: item.due_at)


def select_cycle(on, week=None, catalog=None):
    if isinstance(on, str):
        on = date.fromisoformat(on)
    available = cycles(catalog)
    if week is not None:
        key = 'makeup' if str(week) in ('makeup', '보강') else str(week)
        chosen = next((c for c in available if c.period_id == key), None)
        if chosen is None:
            raise ValueError('해당 주차에는 회의록 제출이 없습니다. 제출 회차를 선택하세요. 보강은 --week makeup입니다.')
        return chosen
    chosen = next((c for c in available if date.fromisoformat(c.due_at[:10]) >= on), None)
    if chosen is None:
        raise ValueError('남은 회의록 제출 회차가 없습니다. --week로 제출 회차를 지정하세요.')
    return chosen


def filename_part(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or c in '/\\:*?"<>|' for c in value):
        raise ValueError('파일명에 사용할 팀 이름을 확인하세요.')
    return value.strip()


def save_file(path, content, force=False):
    """Publish a complete file atomically, refusing to overwrite by default."""
    path = Path(path).expanduser().absolute()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(content.encode('utf-8') if isinstance(content, str) else content)
        if force:
            temporary.replace(path)
        else:
            os.link(temporary, path)
        return path
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def project_root(start=None):
    start = Path(start or Path.cwd()).resolve()
    return next((p for p in (start, *start.parents) if (p / '.git').exists()), start)


def normalize_config(raw):
    if not isinstance(raw, dict) or not isinstance(raw.get('members', []), list):
        raise ValueError('팀 기본정보는 name·repository·members를 가진 JSON 객체로 입력하세요.')
    name = filename_part(raw.get('name') or '팀명')
    repository = raw.get('repository', '')
    if not isinstance(repository, str) or any(ord(c) < 32 for c in repository):
        raise ValueError('저장소 주소는 한 줄 문자열로 입력하세요.')
    members = []
    for person in raw.get('members', []):
        if not isinstance(person, dict):
            raise ValueError('각 팀원은 name·github 객체로 입력하세요.')
        member_name, login = person.get('name'), person.get('github', '')
        if not isinstance(member_name, str) or not member_name.strip() or any(ord(c) < 32 for c in member_name):
            raise ValueError('팀원 이름은 한 줄 문자열로 입력하세요.')
        if not isinstance(login, str) or login and not re.fullmatch(r'@?[A-Za-z0-9-]+', login):
            raise ValueError('팀원의 GitHub ID 형식을 확인하세요.')
        members.append({'name': member_name.strip(), 'github': login.lstrip('@')})
    return {'name': name, 'repository': repository, 'members': members}


def load_config(path=None, team_name=None, start=None):
    root = project_root(start)
    selected = Path(path).expanduser() if path else root / '.foss8/team.json'
    if selected.is_file() or path:
        raw = json.loads(selected.read_text(encoding='utf-8'))
    else:
        raw = {'name': root.name, 'repository': '', 'members': []}
        try:
            remote = subprocess.run(['git', 'remote', 'get-url', 'origin'], cwd=root,
                                    capture_output=True, text=True, timeout=5, check=False)
            value = remote.stdout.strip() if remote.returncode == 0 else ''
            if value.startswith(('https://', 'http://')):
                parsed = urlparse(value)
                if parsed.hostname:
                    raw['repository'] = 'https://' + parsed.hostname + parsed.path.removesuffix('.git')
            elif match := re.fullmatch(r'[^@]+@([^:]+):(.+)', value):
                raw['repository'] = 'https://' + match[1] + '/' + match[2].removesuffix('.git')
            if raw['repository']:
                raw['name'] = raw['repository'].rstrip('/').rsplit('/', 1)[-1]
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        readme = root / 'README.md'
        if readme.is_file():
            for line in readme.read_text(encoding='utf-8').splitlines():
                if not line.startswith('|'):
                    continue
                values = [plain(v.strip()) for v in line.strip().strip('|').split('|')]
                if len(values) >= 3 and re.fullmatch(r'@[A-Za-z0-9-]+', values[2]):
                    raw['members'].append({'name': values[0], 'github': values[2].lstrip('@')})
    if team_name is not None:
        if not isinstance(raw, dict):
            raise ValueError('팀 기본정보는 JSON 객체로 입력하세요.')
        raw = {**raw, 'name': team_name}
    return normalize_config(raw)


def calendar_period(on, catalog):
    doc, _ = catalog.resolve('calendar')
    for line in doc.markdown.splitlines():
        if not line.startswith('|'):
            continue
        values = [value.strip() for value in line.strip().strip('|').split('|')]
        if len(values) < 4:
            continue
        label = plain(values[0])
        week = re.match(r'(\d+)\s*주', label)
        day = re.search(r'(\d+)/(\d+)', values[1])
        if not week or not day:
            continue
        class_day = date(2026, int(day[1]), int(day[2]))
        start = class_day - timedelta(days=(class_day.weekday() - 1) % 7)
        if start <= on < start + timedelta(days=7):
            key = 'makeup' if '보강' in label else week[1]
            actions = [plain(templates.cell(value)).strip() for value in values[3].split('•') if plain(templates.cell(value)).strip()]
            return {'id': key, 'label': '보강 주' if key == 'makeup' else week[1] + '주차', 'actions': actions}
    raise ValueError('안내서 주차 범위에 없는 회의 날짜입니다. --date를 확인하세요.')


def checklist(catalog, week):
    doc, _ = catalog.resolve('appendix-a-checklist')
    for line in doc.markdown.splitlines():
        if not line.startswith('|'):
            continue
        cells = [cell.strip() for cell in line.strip().strip('|').split('|')]
        if len(cells) < 2:
            continue
        label = templates.cell(cells[0])
        match = re.match(r'(\d+)주', label)
        if not match:
            continue
        if (week == 'makeup' and '보강' in label) or (match[1] == str(week) and '보강' not in label):
            values = [plain(templates.cell(v)).strip() for v in cells[1].split(' / ')]
            if str(week) == '8':
                values[0] = '10/19~10/25 활동 최소 기준 면제 · 10/29 회의록 #4는 제출'
            return values
    return []


def draft(on=None, week=None, config=None, catalog=None):
    on = on or today()
    if isinstance(on, str):
        on = date.fromisoformat(on)
    catalog = catalog or Catalog()
    cycle = select_cycle(on, week, catalog)
    config = normalize_config(config or {})
    team_name, members = config['name'], config['members']
    period = calendar_period(on, catalog)
    metadata = {'schema_version': 1, 'meeting_date': on.isoformat(), 'period_id': cycle.period_id,
                'submission_week': cycle.week, 'team': team_name, 'recording_start': cycle.recording_start,
                'recording_end': cycle.recording_end, 'due_at': cycle.due_at}
    content = templates.minutes(catalog)['content']
    content = content.replace('# [WEEK#] 회의록 — 팀명', f'# [WEEK{cycle.week}] 회의록 — {team_name}', 1)
    content = content.replace('- 일시: ', f'- 일시: {on.isoformat()} ({"월화수목금토일"[on.weekday()]}) ', 1)
    due = datetime.fromisoformat(cycle.due_at)
    context = [f'- 기록기간: {cycle.recording_start} ~ {cycle.recording_end}',
               f'- 제출 마감: {due:%Y-%m-%d %H:%M} (한국 시간)', f'- 저장소: {config["repository"]}',
               '- 팀원: ' + ', '.join(p['name'] + (f' (@{p["github"]})' if p['github'] else '') for p in members)]
    content = content.replace('\n## 1.', '\n' + '\n'.join(context) + '\n\n## 1.', 1)
    result, section = [], 0
    for line in content.splitlines():
        if match := re.match(r'## (\d+)\.', line):
            section = int(match[1])
        if section in (2, 5) and line.startswith('|') and all(not c.strip() for c in line.strip('|').split('|')):
            columns = len(line.strip('|').split('|'))
            for person in members or [{'name': ''}]:
                result.append('| ' + ' | '.join([person['name'].replace('|', '\\|')] + [''] * (columns - 1)) + ' |')
        else:
            result.append(line)
    content = '\n'.join(result) + '\n'
    agenda = ['### 안내서에서 확인할 일 (' + period['label'] + ')', '']
    agenda += ['- [ ] ' + action for action in period['actions']]
    agenda += ['', '### 회의 결정', '']
    content = content.replace('- 결정: / 이유:', '\n'.join(agenda) + '- 결정: / 이유:', 1)
    items = checklist(catalog, period['id'])
    content = re.sub(r'## 6\. 이번 주 점검표 \(부록 A 해당 주차\)\n.*?(?=\n\[원문 양식\])',
                     lambda _: '## 6. 이번 주 점검표 (부록 A ' + period['label'] + ')\n' +
                     '\n'.join('- [ ] ' + value for value in items) + '\n', content, flags=re.S)
    return '<!-- foss8-minutes: ' + json.dumps(metadata, ensure_ascii=False) + ' -->\n' + content


def create(on=None, week=None, config=None, output=None, force=False):
    content = draft(on, week, config)
    meta = json.loads(content.split('<!-- foss8-minutes: ', 1)[1].split(' -->', 1)[0])
    path = Path(output) if output else Path('docs/meetings') / (meta['meeting_date'] + '.md')
    if path.suffix.lower() not in ('.md', '.markdown'):
        raise ValueError('초안 저장 경로는 .md 또는 .markdown 파일로 지정하세요.')
    return save_file(path, content, force)
