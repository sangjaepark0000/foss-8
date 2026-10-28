"""Convert completed minutes to a submission PDF using Chrome's local print engine."""
from html import escape
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from . import minutes


CSS = '''
@page { size: A4; margin: 17mm 16mm 18mm; }
* { box-sizing: border-box; }
body { font-family: "Noto Sans CJK KR", "Noto Sans KR", "Malgun Gothic", "Apple SD Gothic Neo", sans-serif;
       font-size: 10pt; line-height: 1.65; color: #20252b; overflow-wrap: anywhere; }
h1 { font-size: 20pt; line-height: 1.45; margin: 0 0 8mm; padding-bottom: 4mm; border-bottom: 2px solid #253448; }
h2 { font-size: 13pt; margin: 7mm 0 3mm; color: #253448; }
h3 { font-size: 10.5pt; margin: 4mm 0 2mm; }
h1, h2, h3, h4 { break-after: avoid; }
p, li { orphans: 3; widows: 3; }
p { margin: 2mm 0; }
ul, ol { padding-left: 5mm; margin: 2mm 0; }
li { margin-bottom: 1mm; }
table { border-collapse: collapse; width: 100%; table-layout: fixed; font-size: 9pt; margin: 3mm 0 4mm; }
th, td { border: 0.25mm solid #c1c9d2; padding: 2mm; vertical-align: top; overflow-wrap: anywhere; }
th { background: #eef1f5; color: #253448; font-weight: 600; text-align: left; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
table.activity { font-size: 8pt; }
.activity th:nth-child(1) { width: 14%; } .activity th:nth-child(2) { width: 8%; }
.activity th:nth-child(3) { width: 18%; } .activity th:nth-child(4) { width: 8%; }
.activity th:nth-child(5) { width: 8%; } .activity th:nth-child(6) { width: 14%; }
.activity th:nth-child(7) { width: 30%; }
a { color: #294f76; text-decoration: underline; }
code, pre { font-family: "Noto Sans Mono CJK KR", monospace; font-size: 8.5pt; }
code { background: #f1f3f5; padding: 0 1mm; }
pre { white-space: pre-wrap; overflow-wrap: anywhere; background: #f5f6f8; padding: 3mm; }
blockquote { border-left: 1mm solid #c1c9d2; padding-left: 3mm; margin: 3mm 0; color: #4d5864; }
.checkbox { font-family: "Noto Sans CJK KR", sans-serif; }
'''


def inline(text):
    # Escape HTML first; user content cannot load scripts, images or remote styles.
    tokens = []
    def stash(html):
        tokens.append(html)
        return f'\x00{len(tokens)-1}\x00'
    text = escape(text)
    text = re.sub(r'`([^`]+)`', lambda m: stash('<code>' + m[1] + '</code>'), text)
    def link(match):
        label, url = match.groups()
        if not re.match(r'https?://', url, re.I):
            return label + ' (' + url + ')'
        return stash('<a href="' + url.replace('"', '&quot;') + '">' + label + '</a>')
    text = re.sub(r'\[([^]]+)\]\(([^\s)]+)\)', link, text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    text = re.sub(r'^\[([ xX])\]\s*', lambda m: '<span class="checkbox">' + ('☐' if m[1] == ' ' else '☑') + '</span> ', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: tokens[int(m[1])], text)


def cells(line):
    return [part.strip().replace('\\|', '|') for part in re.split(r'(?<!\\)\|', line.strip().strip('|'))]


def to_html(content):
    content = re.sub(r'<!--.*?-->', '', content, flags=re.S)
    lines, out, index = content.splitlines(), [], 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            index += 1
            continue
        if line.startswith('```'):
            block = []
            index += 1
            while index < len(lines) and not lines[index].startswith('```'):
                block.append(lines[index]); index += 1
            out.append('<pre>' + escape('\n'.join(block)) + '</pre>')
        elif line.startswith('|') and index + 1 < len(lines) and re.fullmatch(r'[\s|:\-]+', lines[index + 1]):
            headers = cells(line)
            activity = len(headers) == 7 and '커밋' in headers
            out.append('<table' + (' class="activity"' if activity else '') + '><thead><tr>')
            out.append(''.join('<th>' + inline(v) + '</th>' for v in headers) + '</tr></thead><tbody>')
            index += 2
            while index < len(lines) and lines[index].startswith('|'):
                row = cells(lines[index])
                if len(row) != len(headers):
                    raise ValueError(f'표 열 수가 맞지 않습니다: {index + 1}번째 줄')
                out.append('<tr>' + ''.join('<td>' + (inline(v) or '&nbsp;') + '</td>' for v in row) + '</tr>')
                index += 1
            out.append('</tbody></table>')
            continue
        elif match := re.match(r'(#{1,6})\s+(.+)', line):
            level = len(match[1]); out.append(f'<h{level}>' + inline(match[2]) + f'</h{level}>')
        elif re.match(r'\s*(?:[-*]|\d+[.)])\s+', line):
            ordered = bool(re.match(r'\s*\d+[.)]', line))
            tag = 'ol' if ordered else 'ul'
            pattern = r'\s*\d+[.)]\s+(.*)' if ordered else r'\s*[-*]\s+(.*)'
            out.append(f'<{tag}>')
            while index < len(lines) and (match := re.match(pattern, lines[index])):
                out.append('<li>' + inline(match[1]) + '</li>'); index += 1
            out.append(f'</{tag}>')
            continue
        elif line.startswith('>'):
            out.append('<blockquote>' + inline(line.lstrip('> ')) + '</blockquote>')
        else:
            out.append('<p>' + inline(line) + '</p>')
        index += 1
    return '<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>회의록</title><style>' + CSS + '</style></head><body>' + '\n'.join(out) + '</body></html>'


def submission_info(content, week=None, team_name=None):
    header = re.search(r'^#\s+\[WEEK(\d+)\]\s*회의록\s*[—–-]\s*(.+?)\s*$', content, re.M)
    if header:
        header_week, header_team = header.groups()
        key = 'makeup' if header_week == '4' else header_week
        if week is not None and minutes.select_cycle(minutes.today(), week).week != header_week:
            raise ValueError('문서 제목과 선택한 제출 회차가 다릅니다. 회의록 제목·회차를 확인하세요.')
        if team_name is not None and team_name != header_team:
            raise ValueError('문서 제목과 지정한 팀 이름이 다릅니다. 회의록 제목을 확인하세요.')
        cycle = minutes.select_cycle(minutes.today(), key)
        return cycle, minutes.filename_part(header_team)
    if week is None or team_name is None:
        raise ValueError('제출 회차·팀명을 읽을 수 없습니다. 제목을 "# [WEEK9] 회의록 — 팀명"으로 작성하거나 --week와 --team을 지정하세요.')
    return minutes.select_cycle(minutes.today(), week), minutes.filename_part(team_name)


def browser_path(browser=None):
    candidates = [browser] if browser else ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable', 'chrome', 'msedge',
                                            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    for candidate in candidates:
        found = shutil.which(candidate)
        if found:
            return found
    raise ValueError('PDF 변환에 Chrome 또는 Chromium이 필요합니다. 설치 후 다시 실행하거나 --browser로 실행 파일을 지정하세요.')


def export(source, output=None, week=None, team_name=None, force=False, browser=None, runner=subprocess.run):
    source = Path(source).expanduser().absolute()
    if source.suffix.lower() not in ('.md', '.markdown'):
        raise ValueError('작성한 회의록 Markdown(.md) 파일을 선택하세요.')
    content = source.read_text(encoding='utf-8')
    cycle, name = submission_info(content, week, team_name)
    target = Path(output).expanduser().absolute() if output else source.parent / f'[WEEK{cycle.week}] 회의록_{name}.pdf'
    if target.suffix.lower() != '.pdf':
        raise ValueError('제출본 저장 경로는 .pdf 파일로 지정하세요.')
    if target.exists() and not force:
        raise FileExistsError(target)
    html = to_html(content)
    binary = browser_path(browser)
    with tempfile.TemporaryDirectory(prefix='foss8-minutes-pdf-') as temporary:
        root = Path(temporary)
        page, pdf = root / 'minutes.html', root / 'minutes.pdf'
        page.write_text(html, encoding='utf-8')
        args = [binary, '--headless', '--disable-gpu', '--no-first-run', '--disable-extensions',
                '--disable-background-networking', '--disable-default-apps', '--disable-sync',
                '--no-pdf-header-footer', '--user-data-dir=' + str(root / 'profile'),
                '--print-to-pdf=' + str(pdf), page.as_uri()]
        try:
            result = runner(args, capture_output=True, timeout=45, check=False)
        except subprocess.TimeoutExpired as error:
            raise ValueError('PDF 변환 시간이 초과됐습니다. Chrome 실행 환경을 확인한 뒤 다시 시도하세요.') from error
        if result.returncode or not pdf.is_file():
            raise ValueError('PDF 변환에 실패했습니다. --browser로 Chrome/Chromium 실행 파일을 확인하세요. 원본과 기존 PDF는 유지됩니다.')
        data = pdf.read_bytes()
        if not data.startswith(b'%PDF-') or len(data) < 100:
            raise ValueError('정상적인 PDF가 생성되지 않았습니다. 원본과 기존 PDF는 유지됩니다.')
        return minutes.save_file(target, data, force)
