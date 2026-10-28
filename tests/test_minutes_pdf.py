from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from foss8 import minutes, minutes_pdf


class MinutesPdfTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / '작성한 회의록.md'
        self.content = minutes.draft('2026-10-28', config={'name': '예시 팀'})
        self.source.write_text(self.content, encoding='utf-8')
        found = patch('foss8.minutes_pdf.shutil.which', return_value='/browser/chromium')
        found.start(); self.addCleanup(found.stop)

    def runner(self, args, **kwargs):
        self.assertIn('--headless', args)
        self.assertIn('--no-pdf-header-footer', args)
        self.assertFalse(kwargs.get('shell', False))
        pdf = Path(next(a.split('=', 1)[1] for a in args if a.startswith('--print-to-pdf=')))
        html = Path(args[-1].removeprefix('file://')).read_text()
        self.assertIn('lang="ko"', html)
        self.assertIn('Noto Sans CJK KR', html)
        pdf.write_bytes(b'%PDF-1.7\n' + b'example' * 30)
        return subprocess.CompletedProcess(args, 0, b'', b'')

    def test_default_submission_filename_and_source_preservation(self):
        output = minutes_pdf.export(self.source, runner=self.runner)
        self.assertEqual(output.name, '[WEEK9] 회의록_예시 팀.pdf')
        self.assertTrue(output.read_bytes().startswith(b'%PDF-'))
        self.assertEqual(self.source.read_text(), self.content)
        with self.assertRaises(FileExistsError):
            minutes_pdf.export(self.source, runner=lambda *a, **kw: self.fail('must reject before rendering'))

    def test_failed_conversion_preserves_existing_pdf_even_with_force(self):
        target = self.root / '기존 제출본.pdf'
        target.write_bytes(b'existing submission')
        def fail(args, **kwargs):
            return subprocess.CompletedProcess(args, 1, b'', b'failure')
        with self.assertRaisesRegex(ValueError, '변환에 실패'):
            minutes_pdf.export(self.source, output=target, force=True, runner=fail)
        self.assertEqual(target.read_bytes(), b'existing submission')
        self.assertEqual(self.source.read_text(), self.content)

    def test_timeout_and_missing_browser_are_actionable(self):
        def timeout(args, **kwargs):
            raise subprocess.TimeoutExpired(args, 45)
        with self.assertRaisesRegex(ValueError, '시간이 초과'):
            minutes_pdf.export(self.source, runner=timeout)
        with patch('foss8.minutes_pdf.shutil.which', return_value=None):
            with self.assertRaisesRegex(ValueError, '--browser'):
                minutes_pdf.export(self.source, runner=self.runner)

    def test_legacy_minutes_and_makeup_title_determine_submission_name(self):
        cycle, name = minutes_pdf.submission_info('# [WEEK7] 회의록 — foss-8\n기존 작성 내용')
        self.assertEqual((cycle.week, name), ('7', 'foss-8'))
        cycle, _ = minutes_pdf.submission_info('# [WEEK4] 회의록 — 팀')
        self.assertEqual(cycle.period_id, 'makeup')
        with self.assertRaisesRegex(ValueError, '회차가 다릅니다'):
            minutes_pdf.export(self.source, week='10', runner=self.runner)
        with self.assertRaisesRegex(ValueError, '팀 이름이 다릅니다'):
            minutes_pdf.export(self.source, team_name='다른 팀', runner=self.runner)

    def test_markdown_tables_links_and_checkboxes_preserve_content(self):
        content = '# 회의록\n\n| 항목 | 내용 |\n|---|---|\n| 한글 | 가람 \\| 나래 |\n\n- [x] 완료\n- [ ] 다음 작업\n\n[이슈](https://github.com/a/b/issues/1)\n'
        html = minutes_pdf.to_html(content)
        for expected in ['<table', '<th>항목', '가람 | 나래', '☑', '☐', '<a href="https://github.com/a/b/issues/1">이슈</a>']:
            self.assertIn(expected, html)
        with self.assertRaisesRegex(ValueError, '표 열 수'):
            minutes_pdf.to_html('| a | b |\n|---|---|\n| a | b | c |')

    def test_raw_html_and_metadata_are_not_active_page_content(self):
        html = minutes_pdf.to_html('<!-- foss8-minutes: {"team":"secret metadata"} -->\n<script>alert(1)</script>\n<img src="https://example.com/pixel">\n[bad](javascript:alert)')
        self.assertNotIn('secret metadata', html)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertNotIn('href="javascript:', html)
        self.assertIn('&lt;script&gt;', html)

    def test_empty_user_list_items_and_headings_do_not_interrupt_conversion(self):
        html = minutes_pdf.to_html('# \n\n- \n- 다음 항목\n\n1. \n2. 완료\n')
        self.assertIn('다음 항목', html)
        self.assertIn('<li>완료</li>', html)
