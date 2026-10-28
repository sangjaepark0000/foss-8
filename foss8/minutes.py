"""Prepare editable meeting minutes without inventing attendance or decisions."""
from dataclasses import dataclass
from datetime import date, datetime
import json
import os
from pathlib import Path
import re
import tempfile

from . import team, templates, weeks
from .guide import Catalog


@dataclass(frozen=True)
class Cycle:
    period_id: str
    week: str
    recording_start: str
    recording_end: str
    due_at: str


def cycles():
    result = []
    for period in weeks.load():
        for task in period['tasks']:
            if task.get('recording_start') and task.get('due_at'):
                result.append(Cycle(period['id'], '4' if period['id'] == 'makeup' else period['id'],
                                    task['recording_start'], task['recording_end'], task['due_at']))
    return sorted(result, key=lambda item: item.due_at)


def select_cycle(on, week=None):
    if isinstance(on, str):
        on = date.fromisoformat(on)
    if week is not None:
        key = 'makeup' if str(week) in ('makeup', '보강') else str(week)
        chosen = next((c for c in cycles() if c.period_id == key), None)
        if chosen is None:
            raise ValueError('해당 주차에는 회의록 제출이 없습니다. 제출 회차를 선택하세요. 보강은 --week makeup입니다.')
        return chosen
    chosen = next((c for c in cycles() if date.fromisoformat(c.due_at[:10]) >= on), None)
    if chosen is None:
        raise ValueError('남은 회의록 제출 회차가 없습니다. --week로 제출 회차를 지정하세요.')
    return chosen


def filename_part(value):
    if not isinstance(value, str) or not value.strip() or any(ord(c) < 32 or c in '/\\:*?"<>|' for c in value):
        raise ValueError('파일명에 사용할 팀 이름을 확인하세요.')
    return value.strip()


def save_file(path, content, force=False):
    """Publish a complete file atomically; an existing destination wins by default."""
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
        if match and match[1] == str(week) and '보강' not in label:
            return [re.sub(r'\[([^]]+)\]\([^)]+\)', r'\1', templates.cell(v).strip())
                    for v in cells[1].split(' / ')]
    return []


def draft(on=None, week=None, config=None, catalog=None):
    on = on or weeks.today()
    if isinstance(on, str):
        on = date.fromisoformat(on)
    cycle = select_cycle(on, week)
    catalog = catalog or Catalog()
    config = team.validate(config) if config else {}
    team_name = filename_part(config.get('name') or '팀명')
    members = config.get('members', [])
    period = weeks.select(weeks.load(config or None), on=on)
    metadata = {'schema_version': 1, 'meeting_date': on.isoformat(), 'period_id': cycle.period_id,
                'submission_week': cycle.week, 'team': team_name,
                'recording_start': cycle.recording_start, 'recording_end': cycle.recording_end,
                'due_at': cycle.due_at}
    content = templates.minutes(catalog)['content']
    content = content.replace('# [WEEK#] 회의록 — 팀명', f'# [WEEK{cycle.week}] 회의록 — {team_name}', 1)
    content = content.replace('- 일시: ', f'- 일시: {on.isoformat()} ({"월화수목금토일"[on.weekday()]}) ', 1)
    due = datetime.fromisoformat(cycle.due_at)
    context = [f'- 기록기간: {cycle.recording_start} ~ {cycle.recording_end}',
               f'- 제출 마감: {due:%Y-%m-%d %H:%M} (한국 시간)',
               f'- 저장소: {config.get("repository", "")}',
               '- 팀원: ' + ', '.join(f'{p["name"]} (@{p["github"]})' for p in members)]
    content = content.replace('\n## 1.', '\n' + '\n'.join(context) + '\n\n## 1.', 1)
    # Only name the rows. Membership proves neither presence nor completed work.
    lines, section, result = content.splitlines(), 0, []
    for line in lines:
        match = re.match(r'## (\d+)\.', line)
        if match:
            section = int(match[1])
        if section in (2, 5) and line.startswith('|') and all(not c.strip() for c in line.strip('|').split('|')):
            columns = len(line.strip('|').split('|'))
            for person in members or [{'name': ''}]:
                name = person['name'].replace('|', '\\|')
                result.append('| ' + ' | '.join([name] + [''] * (columns - 1)) + ' |')
        else:
            result.append(line)
    content = '\n'.join(result) + '\n'
    agenda = ['### 안내서에서 확인할 일 (' + period['label'] + ')', '']
    agenda += ['- [ ] ' + weeks.plain(t['title']) +
               (' (' + weeks.timing_notes(t)[0].removeprefix('시작: ') + ')' if t.get('after_class') else '') +
               (' [이어서]' if t.get('carryover_from') else '')
               for t in weeks.view_tasks(period) if not t.get('recording_start')]
    agenda += ['', '### 회의 결정', '']
    content = content.replace('- 결정: / 이유:', '\n'.join(agenda) + '- 결정: / 이유:', 1)
    items = checklist(catalog, period['weeks'][0])
    if period['id'] == '9':
        items = [value + (' (10/30 수업 후)' if i < 5 else ' [다음 제출]') for i, value in enumerate(items)]
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


def run(args):
    from . import team
    if args.minutes_command == 'pdf':
        from .minutes_pdf import export
        path = export(args.source, args.output, args.week, args.team, args.force, args.browser)
        print('제출용 PDF 저장: ' + str(path))
        return 0
    path = create(args.date, args.week, team.load(), args.output, args.force)
    print('회의록 초안 저장: ' + str(path))
    return 0
