import json
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
ROOT=Path(__file__).resolve().parents[3];BASE='http://127.0.0.1:5173'
catalog=json.loads((ROOT/'backend/data/hexagrams.json').read_text())
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1366,'height':900});page.set_default_timeout(12000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 mutations=[];page.on('request',lambda r:mutations.append(r.url) if r.method!='GET' and '/api/' in r.url else None)
 page.goto(BASE+'/#/learning',wait_until='networkidle');page.locator('.learning-preview__original blockquote').wait_for();page.evaluate('document.fonts.ready')
 assert page.locator('.learning-top-nav button').count()==4
 assert not page.locator('.app-sidebar').count()
 assert page.locator('.learning-card').count()==64
 assert page.locator('.learning-card').evaluate_all('els=>els.map(el=>Number(el.dataset.hexagram))')==list(range(1,65))
 history_before=page.request.get(BASE+'/api/history').json()['total']
 for e in catalog:
  item=page.locator(f'[data-hexagram="{e["wenwang_order"]}"]')
  assert item.locator('.gua-line-row').evaluate_all('els=>els.map(el=>Number(el.dataset.position))')==[6,5,4,3,2,1]
  assert ''.join('1' if value=='阳' else '0' for value in item.locator('.gua-line-row').evaluate_all('els=>els.map(el=>el.dataset.polarity)'))==e['binary_code']
 # Mouse, keyboard and direct detail use a single action, with current original text.
 page.locator('[data-hexagram="24"]').hover()
 expect(page.locator('.learning-preview__heading h2')).to_have_text('地雷复')
 expect(page.locator('.learning-preview__original blockquote')).to_have_text(catalog[23]['judgment'])
 page.locator('[data-hexagram="3"]').focus();page.keyboard.press('ArrowRight')
 assert page.locator(':focus').get_attribute('data-hexagram')=='4'
 expect(page.locator('.learning-preview__heading h2')).to_have_text('山水蒙')
 page.keyboard.press('End')
 assert page.locator(':focus').get_attribute('data-hexagram')=='64'
 expect(page.locator('.learning-preview__heading h2')).to_have_text('火水未济')
 position=page.locator('.learning-index__scroll').evaluate('el=>el.scrollTop')
 assert position>0
 page.keyboard.press('Enter');expect(page.locator('.learning-reader h1')).to_have_text('火水未济');page.wait_for_timeout(350)
 assert page.locator(':focus').evaluate('el=>el.tagName')=='H1'
 page.get_by_role('button',name='← 返回六十四卦',exact=True).click();page.locator('.learning-card').last.wait_for();page.wait_for_timeout(350)
 assert abs(page.locator('.learning-index__scroll').evaluate('el=>el.scrollTop')-position)<3
 assert page.locator(':focus').get_attribute('data-hexagram')=='64'
 # Search/filter restoration through browser back and forward.
 page.get_by_role('button',name='下经 34',exact=True).click();assert page.locator('.learning-card').count()==34
 page.get_by_role('textbox',name='搜索卦名或卦序').fill('63');assert page.locator('.learning-card').count()==1
 page.locator('.learning-card').click();expect(page.locator('.learning-reader h1')).to_have_text('水火既济');page.wait_for_timeout(350)
 page.go_back();page.locator('.learning-card').wait_for();page.wait_for_timeout(350)
 assert page.get_by_role('textbox',name='搜索卦名或卦序').input_value()=='63'
 assert page.get_by_role('button',name='下经 34',exact=True).get_attribute('aria-pressed')=='true'
 page.go_forward();expect(page.locator('.learning-reader h1')).to_have_text('水火既济');page.wait_for_timeout(350)
 # All 64 live detail pages, six exact original lines, pinned source, special lines.
 for e in catalog:
  page.goto(BASE+f'/#/learning/{e["wenwang_order"]}',wait_until='networkidle');expect(page.locator('.learning-reader h1')).to_have_text(e['title'])
  expect(page.locator('.learning-reader__judgment blockquote')).to_have_text(e['judgment'])
  assert page.locator('.learning-reader__line-text').all_text_contents()==e['line_texts']+([e['special_line']['text']] if e.get('special_line') else [])
  assert page.locator('.learning-reader__judgment a').get_attribute('href')==e['source_url']
  assert '导读整理中' in page.locator('.learning-reader__guide').inner_text()
 page.goto(BASE+'/#/learning/2',wait_until='networkidle');page.locator('.learning-reader h1').wait_for()
 page.get_by_role('button',name='全部展开',exact=True).click();assert page.locator('.learning-reader__line-note').count()==7
 page.get_by_role('button',name='全部收起',exact=True).click();assert page.locator('.learning-reader__line-note').count()==0
 assert page.request.get(BASE+'/api/history').json()['total']==history_before
 assert not mutations,mutations
 # Layout and pointer-independent mobile activation, plus external scroll restoration.
 page.goto(BASE+'/#/learning',wait_until='networkidle');page.wait_for_timeout(350)
 page.get_by_role('textbox',name='搜索卦名或卦序').fill('');page.get_by_role('button',name='全部 64',exact=True).click()
 expect(page.locator('.learning-card')).to_have_count(64)
 for width in [320,390,768,844,1024,1366,1536]:
  page.set_viewport_size({'width':width,'height':844 if width<1000 else 900})
  for route in ['learning','learning/1','learning/2','learning/64']:
   page.goto(BASE+'/#/'+route,wait_until='networkidle');page.wait_for_timeout(350)
   assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),(width,route)
   if route=='learning':
    assert page.locator('.learning-matrix__entry').evaluate_all('els=>els.every(el=>el.scrollWidth<=el.clientWidth)'),width
 page.set_viewport_size({'width':390,'height':844});page.goto(BASE+'/#/learning',wait_until='networkidle');page.wait_for_timeout(350)
 assert page.locator('.learning-matrix').evaluate('el=>getComputedStyle(el).gridTemplateColumns.split(" ").length')==2
 assert page.locator('.learning-preview-frame').is_visible()
 assert page.locator('.learning-preview-frame').bounding_box()['y']<page.locator('.learning-index').bounding_box()['y']
 page.locator('[data-hexagram="64"]').scroll_into_view_if_needed();mobile_position=page.evaluate('scrollY');page.locator('[data-hexagram="64"]').click()
 expect(page.locator('.learning-reader h1')).to_have_text('火水未济');page.wait_for_timeout(350)
 assert page.evaluate('scrollY')==0
 page.get_by_role('button',name='← 返回六十四卦',exact=True).click();page.locator('.learning-card').last.wait_for();page.wait_for_timeout(350)
 assert abs(page.evaluate('scrollY')-mobile_position)<3,(mobile_position,page.evaluate('scrollY'))
 # Reduced motion applies to both preview and route transitions.
 page.emulate_media(reduced_motion='reduce');page.locator('[data-hexagram="1"]').scroll_into_view_if_needed();page.locator('[data-hexagram="1"]').focus()
 expect(page.locator('.learning-preview__heading h2')).to_have_text('乾为天')
 assert page.locator('.learning-card').first.evaluate('el=>getComputedStyle(el).transitionDuration')=='0s'
 assert not errors,errors
 print(json.dumps({'status':'PASS','details':64,'viewports':[320,390,768,844,1024,1366,1536],'learningMutations':mutations,'consoleErrors':errors,'restoredDesktopScroll':position,'restoredMobileScroll':mobile_position},ensure_ascii=False))
 b.close()
