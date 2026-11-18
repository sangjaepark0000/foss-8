"""Check diagram sources, SVGs, local documentation links, and code citations."""
import ast
import json
from pathlib import Path
import re
import subprocess
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/architecture'


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    source_index = json.loads((BASE / 'source-index.json').read_text())
    render_report = json.loads((BASE / 'render-report.json').read_text())
    issues = []
    diagrams = manifest['diagrams']
    assert len(diagrams) == 19
    ids = [d['slug'] for d in diagrams]
    if len(set(ids)) != len(ids):
        issues.append('duplicate diagram IDs')
    if [r['id'] for r in render_report] != ids or any(r['exit_code'] for r in render_report):
        issues.append('missing or failed SVG render')

    source_cache = {}
    for d in diagrams:
        source = BASE / 'diagrams' / (d['slug'] + '.mmd')
        svg = BASE / 'rendered' / (d['slug'] + '.svg')
        if source.read_text() != d['syntax']:
            issues.append(f'stale source: {source.name}')
        root = ElementTree.parse(svg).getroot()
        if not root.tag.endswith('svg') or not root.get('viewBox'):
            issues.append(f'invalid SVG: {svg.name}')
        if 'Syntax error in text' in svg.read_text():
            issues.append(f'error diagram: {svg.name}')
        for branch, path, symbol in d['sources']:
            key = (branch, path)
            if key not in source_cache:
                result = subprocess.run(['git', 'show', manifest['commits'][branch] + ':' + path],
                                        cwd=ROOT, capture_output=True, text=True, check=True)
                source_cache[key] = ast.parse(result.stdout)
            expected = next(x for x in source_index[branch][path]['definitions'] if x['name'] == symbol)
            found = any(isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                        and node.name == symbol and node.lineno == expected['line']
                        for node in ast.walk(source_cache[key]))
            if not found:
                issues.append(f'bad code citation: {branch}:{path}:{symbol}')

    link_count = 0
    documents = list(BASE.glob('*.md')) + [BASE / 'index.html']
    for doc in documents:
        text = doc.read_text()
        links = re.findall(r'\]\(([^)]+)\)', text) if doc.suffix == '.md' else re.findall(r'(?:href|src)="([^"]+)"', text)
        for link in links:
            if link.startswith(('https:', 'http:', '#', 'mailto:')):
                continue
            path = (doc.parent / link.split('#', 1)[0]).resolve()
            if not path.exists():
                issues.append(f'broken link: {doc.name} -> {link}')
            link_count += 1
    subprocess.run(['git', 'diff', '--check'], cwd=ROOT, check=True)
    report = {
        'date': manifest['date'], 'diagram_count': len(diagrams),
        'rendered_svgs': len(render_report),
        'checked_code_files': len(source_cache), 'checked_local_links': link_count,
        'issues': issues,
    }
    browser_report = Path('/tmp/foss8-browser-inspection.json')
    if browser_report.exists():
        browser = json.loads(browser_report.read_text())
        report['browser_inspection'] = {
            'all_19_images_loaded': len(browser['images']) == 19 and all(i['loaded'] for i in browser['images']),
            'page_errors': browser['errors'],
            'target_filter_count': browser['targetCount'],
            'current_filter_count': browser['currentCount'],
            'comparison_filter_count': browser['comparisonCount'],
            'mobile_overflow': browser['mobileOverflow'],
            'inspected_widths': [1440, 390],
        }
        if browser['errors'] or browser['mobileOverflow'] or not report['browser_inspection']['all_19_images_loaded']:
            issues.append('browser inspection failed')
    (BASE / 'validation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if issues:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
