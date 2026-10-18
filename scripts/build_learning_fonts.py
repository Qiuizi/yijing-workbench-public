"""Optional asset build: pip install fonttools brotli; sources from Debian fonts-noto-cjk.

The app consumes the checked-in WOFF2 files, so font tools are not runtime dependencies.
Run from any directory; pass the upstream TTC directory as the first argument if needed.
"""
from pathlib import Path
import sys
from fontTools import subset
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/usr/share/fonts/opentype/noto')
OUTPUT = ROOT / 'frontend/src/assets/fonts'
OUTPUT.mkdir(parents=True, exist_ok=True)
catalog_text = (ROOT / 'backend/data/hexagrams.json').read_text(encoding='utf-8')
import json
catalog = json.loads(catalog_text)
ui_text = ''.join(path.read_text(encoding='utf-8') for path in (ROOT / 'frontend/src').rglob('*')
                  if path.suffix in ('.vue', '.ts', '.json'))
latin = ''.join(chr(i) for i in range(32, 127))
serif_text = ''.join(entry['title'] for entry in catalog) + '易' + latin
bold_text = '六十四卦易经起卦学习历史记录设置全部64上经30下经34' + latin
for source, label, family, weight, text in [
    ('NotoSansCJK-Regular.ttc', 'yijing-sans-regular', 'Yijing UI Sans', 400, ui_text + catalog_text + latin),
    ('NotoSansCJK-Bold.ttc', 'yijing-sans-bold', 'Yijing UI Sans', 700, bold_text),
    ('NotoSerifCJK-Regular.ttc', 'yijing-serif-regular', 'Yijing Reading Serif', 400, serif_text),
]:
    font = TTFont(SOURCE / source, fontNumber=2)  # Simplified Chinese face.
    options = subset.Options()
    options.flavor = 'woff2'
    options.name_IDs = ['*']
    options.name_legacy = True
    options.name_languages = ['*']
    builder = subset.Subsetter(options=options)
    builder.populate(text=text)
    builder.subset(font)
    # Distinct names for subset derivatives; retain original copyright/OFL metadata.
    for name_id, value in [(1, family), (2, 'Bold' if weight == 700 else 'Regular'),
                           (3, label), (4, family + (' Bold' if weight == 700 else ' Regular')), (6, label)]:
        font['name'].setName(value, name_id, 3, 1, 0x409)
    font.flavor = 'woff2'
    target = OUTPUT / f'{label}.woff2'
    font.save(target)
    print(f'{target.name}: {target.stat().st_size:,} bytes')
