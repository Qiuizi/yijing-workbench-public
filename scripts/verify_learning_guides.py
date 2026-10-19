"""Check published guides and the draft safety gate against the real Vue reader.

Run the existing API with an isolated temporary database and the Vite dev server,
then run this script with Python Playwright installed. It never rewrites the JSON or adds an approval route to the app. Status changes
only affect an in-memory test-only component mount in the browser.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import platform

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='http://127.0.0.1:5173')
    parser.add_argument('--chromium', default=shutil.which('chromium'))
    parser.add_argument('--output-dir', type=Path, default=Path(tempfile.gettempdir()) / 'yijing-guide-verification')
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    guide_file = ROOT / 'frontend/src/data/learning_guides.json'
    original_bytes = guide_file.read_bytes()
    guides = json.loads(original_bytes)
    catalog = json.loads((ROOT / 'backend/data/hexagrams.json').read_text())
    errors: list[str] = []
    results = []
    with sync_playwright() as playwright:
        launch_options = {'args': ['--no-sandbox']}
        if args.chromium:
            launch_options['executable_path'] = args.chromium
        browser = playwright.chromium.launch(**launch_options)
        page = browser.new_page(viewport={'width': 1366, 'height': 900})
        page.on('pageerror', lambda error: errors.append(str(error)))
        for guide in guides:
            entry = catalog[guide['hexagram_id'] - 1]
            page.goto('about:blank')
            page.goto(f"{args.base_url}/#/learning/{guide['hexagram_id']}", wait_until='networkidle')
            expect(page.locator('.learning-reader h1')).to_have_text(entry['title'])
            reader = page.locator('.learning-reader')
            expect(reader.locator('.learning-reader__guide')).to_contain_text(guide['overview'])
            expect(reader.locator('.learning-reader__one-liner')).to_have_text(guide['one_liner'])
            assert guide['overview'] in reader.inner_text()
            reader.get_by_role('button', name='全部展开', exact=True).click()
            assert reader.locator('.learning-reader__line-note p').count() == 6
            assert reader.locator('.learning-reader__line-text').all_text_contents() == (
                entry['line_texts'] + ([entry['special_line']['text']] if entry.get('special_line') else [])
            )
            # Reuse the real reader on an isolated mount. The regular app and its
            # production selection path are hidden, not reconfigured or approved.
            page.evaluate('''async ({draft, entry}) => {
              const {createApp, h, reactive, nextTick} = await import('/node_modules/.vite/deps/vue.js');
              const {default: Reader} = await import('/src/components/LearningReader.vue');
              document.querySelector('#app').style.display = 'none';
              const banner = document.createElement('p');
              banner.textContent = '测试副本：模拟 reviewed → draft，不更改正式内容';
              banner.style.cssText = 'margin:0;padding:14px 24px;background:#f5ece5;color:#783b2e';
              document.body.append(banner);
              const host = document.createElement('div');
              host.id = 'guide-test-harness'; host.className = 'app-shell app-shell--learning';
              document.body.append(host);
              const state = reactive({guide: {...draft, review_status: 'reviewed'}, hexagram: entry});
              createApp({render: () => h(Reader, {guide: state.guide, hexagram: state.hexagram})}).mount(host);
              window.__guideTestState = state;
              await nextTick();
            }''', {'draft': guide, 'entry': entry})
            harness = page.locator('#guide-test-harness')
            expect(harness.locator('.learning-reader__guide')).to_contain_text(guide['overview'])
            expect(harness.locator('.learning-reader__one-liner')).to_have_text(guide['one_liner'])
            for reference in guide['references']:
                expect(harness.locator('.learning-reader__guide').get_by_role('link', name=reference['title'] + ' ↗', exact=True)).to_have_attribute('href', reference['url'])
            harness.get_by_role('button', name='全部展开', exact=True).click()
            notes = harness.locator('.learning-reader__line-note p')
            expect(notes).to_have_count(6)
            for index, explanation in enumerate(guide['line_guides'].values()):
                expect(notes.nth(index)).to_contain_text(explanation)
            assert harness.locator('.learning-reader__line-text').all_text_contents() == (
                entry['line_texts'] + ([entry['special_line']['text']] if entry.get('special_line') else [])
            )
            if guide['hexagram_id'] == 1:
                page.evaluate('document.fonts.ready')
                page.screenshot(path=str(args.output_dir / 'reviewed-test-copy-qian.png'), full_page=True)
            # Downgrading this prop must immediately remove all editorial content,
            # including notes that are already expanded.
            page.evaluate("window.__guideTestState.guide.review_status = 'draft'")
            expect(harness.locator('.learning-reader__guide')).to_contain_text('导读整理中')
            expect(harness.locator('.learning-reader__one-liner')).to_have_count(0)
            expect(harness.locator('.learning-reader__line-note p')).to_have_count(0)
            assert guide['overview'] not in harness.inner_text()
            for explanation in guide['line_guides'].values():
                assert explanation not in harness.inner_text()
            results.append({'id': guide['hexagram_id'], 'publishedGuideVisible': True, 'draftHidden': True,
                            'reviewedCopyNotes': 6, 'revertedDraftNotes': 0,
                            'classicalAndSpecialLinesIntact': True})
        browser.close()
    assert guide_file.read_bytes() == original_bytes
    assert all(guide['review_status'] == 'reviewed' for guide in json.loads(original_bytes))
    assert not errors, errors
    report = {'status': 'PASS', 'scope': f'{platform.system()} Chromium + published Vue reader; draft safety gate',
              'sourceFileUnchanged': True, 'sourceSha256': hashlib.sha256(original_bytes).hexdigest(),
              'guides': results, 'reviewedCopyTotalNotes': 24, 'consoleErrors': errors}
    (args.output_dir / 'browser-verification.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(report, ensure_ascii=False))


if __name__ == '__main__':
    main()
