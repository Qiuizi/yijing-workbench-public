from playwright.sync_api import sync_playwright,expect
import json
BASE='http://127.0.0.1:5173'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--no-sandbox'])
 page=b.new_page(viewport={'width':390,'height':844});page.set_default_timeout(10000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route('**/api/hexagrams',lambda r:r.fulfill(status=503,json={'error':{'message':'测试目录失败'}}))
 page.goto(BASE+'/#/learning');page.get_by_role('heading',name='暂时无法读取典籍').wait_for()
 page.unroute('**/api/hexagrams');page.get_by_role('button',name='重新读取',exact=True).click();expect(page.locator('.learning-card')).to_have_count(64)
 page.get_by_role('textbox',name='搜索卦名或卦序').fill('不存在');page.get_by_role('heading',name='没有找到相符的卦').wait_for()
 page.get_by_role('button',name='查看全部六十四卦').click();expect(page.locator('.learning-card')).to_have_count(64)
 # Fresh page makes preview failure deterministic, without previously cached text.
 page.route('**/api/hexagrams/3',lambda r:r.fulfill(status=503,json={'error':{'message':'测试预览失败'}}))
 page.reload();page.locator('.learning-preview__error').wait_for();assert not page.locator('.learning-preview__original blockquote').count()
 page.unroute('**/api/hexagrams/3');page.get_by_role('button',name='重新读取',exact=True).click();expect(page.locator('.learning-preview__original blockquote')).to_contain_text('屯：')
 page.route('**/api/hexagrams/2',lambda r:r.fulfill(status=503,json={'error':{'message':'测试详情失败'}}))
 page.goto(BASE+'/#/learning/2');page.get_by_role('heading',name='暂时无法读取典籍').wait_for();assert not page.locator('.learning-reader').count()
 page.unroute('**/api/hexagrams/2');page.get_by_role('button',name='重新读取',exact=True).click();expect(page.locator('.learning-reader h1')).to_have_text('坤为地')
 # Existing business flows on isolated temporary DB, without contacting an AI provider.
 page.goto(BASE+'/#/learning');page.locator('.learning-top-nav').get_by_role('button',name='起卦',exact=True).click()
 page.locator('#question').fill('UI 2.0 自动化回归 · 手动爻序')
 page.locator('.el-radio-button').filter(has_text='手动输入').click();assert page.locator('.manual-row').count()==6
 page.locator('.manual-row').last.locator('.el-select').click();page.get_by_role('option',name='9 · 老阳（动）').click()
 page.get_by_role('button',name='开始起卦',exact=False).click();page.locator('.result-overview').wait_for()
 assert page.locator('.hexagram-card__title').all_text_contents()==['乾为天','天风姤']
 assert page.locator('.result-tabs button').count()==4
 for name,selector in [('经典与取辞','.reading-page'),('六爻排盘','.najia-panel'),('AI 辅助 · 可选联网','.ai-page')]:
  page.get_by_role('button',name=name,exact=True).click();page.locator(selector).wait_for()
 with page.expect_download() as download:page.get_by_role('button',name='导出 Markdown').click()
 assert download.value.suggested_filename.endswith('.md')
 page.locator('.bottom-nav button').filter(has_text='历史').click();page.locator('.history-page__open').first.wait_for();page.locator('.history-page__open').first.click();page.locator('.result-overview').wait_for()
 assert 'UI 2.0 自动化回归' in page.locator('.result-heading').inner_text()
 page.locator('.bottom-nav button').filter(has_text='设置').click();page.locator('.settings-category').first.wait_for();assert page.locator('.settings-category').count()==4
 page.get_by_role('button',name='保存默认偏好',exact=True).click();page.get_by_text('应用偏好已保存。').wait_for()
 # Touch API sends a touch event; card opens immediately with no hover prerequisite.
 touch=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True)
 tp=touch.new_page();tp.goto(BASE+'/#/learning',wait_until='networkidle');tp.locator('[data-hexagram="2"]').tap();expect(tp.locator('.learning-reader h1')).to_have_text('坤为地')
 assert not errors,errors
 result={'status':'PASS','errorRetry':['catalog','preview','detail'],'searchEmpty':True,'manualCast':['乾为天','天风姤'],'traditionalReading':True,'najia':True,'aiEntryOnly':True,'markdownDownload':True,'historyReopen':True,'preferencesSave':True,'emulatedTouchDirectOpen':True,'consoleErrors':errors}
 print(json.dumps(result,ensure_ascii=False));b.close()
