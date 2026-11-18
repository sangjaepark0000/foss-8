"""Render every architecture diagram with an externally installed Mermaid CLI."""
import argparse
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'docs/architecture'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cli', default='mmdc')
    parser.add_argument('--puppeteer-config')
    args = parser.parse_args()
    manifest = json.loads((BASE / 'manifest.json').read_text())
    report = []
    for diagram in manifest['diagrams']:
        slug = diagram['slug']
        command = [args.cli, '-i', str(BASE / 'diagrams' / (slug + '.mmd')),
                   '-o', str(BASE / 'rendered' / (slug + '.svg')),
                   '-c', str(BASE / 'mermaid-config.json'), '--no-font-embed', '-q']
        if args.puppeteer_config:
            command.extend(['-p', args.puppeteer_config])
        start = time.monotonic()
        result = subprocess.run(command, capture_output=True, text=True)
        entry = {'id': slug, 'exit_code': result.returncode,
                 'seconds': round(time.monotonic() - start, 2),
                 'error': result.stderr if result.returncode else ''}
        report.append(entry)
        (BASE / 'render-report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print(slug, 'OK' if result.returncode == 0 else entry['error'][:1500], flush=True)
        if result.returncode:
            raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
