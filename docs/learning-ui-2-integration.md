# 易经 UI 2.0：B 主页与 A 详情整合交付

已在 `feat/learning-ui-redesign` 工作区完成实现。B 提供图鉴主页的交互索引及聚焦预览，A 提供单卦的编辑式阅读排版；复用既有本地 Noto CJK 字体、六爻组件、接口与卦库。

本轮未自动创建提交、合并、发布或更改版本。工作区开始时已有上一轮未提交文件；下面的清单按本轮开始时的文件快照比较，不把既有后端和其他页面的修改归入本轮。

## 使用行为

桌面顶部为起卦、学习、历史、设置。左侧目录按文王序展示，上经/下经及名称、序号、上下卦搜索保留。鼠标移动和键盘焦点更新右侧当前卦，单次点击/Enter 直接阅读。方向键按实际列数移动，Home/End 到首尾。

390px 为简洁顶栏、轻量当前卦预览、双列目录；触屏直接进入全屏阅读，不依赖 hover。返回目录恢复搜索、分组、窗口/索引滚动和卡片焦点。

详情正文最大宽度 720px，原文、固定修订来源和六爻始终可读；逐爻展开补充来源及已审核导读。乾坤用九/用六保留，首末卦边界禁用前后导航。未审核导读不作为正式解读显示。

预览先退后进总计 220ms，进入详情总计 290ms，仅使用 Vue Transition、transform 和 opacity；prefers-reduced-motion 时取消。预览与详情共用只读缓存，同一待完成请求合并，失败可重试，旧响应无法覆盖当前选择。

## 实际修改文件

| 文件 | 本轮改动 |
| --- | --- |
| `frontend/src/App.vue` | 学习态启用顶部导航，隐藏原侧栏、旧顶栏、底栏；其他业务入口沿用原实现。 |
| `frontend/src/components/LearningPage.vue` | 图鉴与阅读协调，搜索/分组、键盘、预览、路由转场、滚动和焦点恢复。 |
| `frontend/src/components/LearningHeader.vue` | 新增顶部四项导航。 |
| `frontend/src/components/LearningPreview.vue` | 新增当前卦预览、真实卦辞、来源和直接阅读。 |
| `frontend/src/components/LearningReader.vue` | 新增 A 风格阅读组件，六爻/特殊爻、审核导读保护及上下卦导航。 |
| `frontend/src/components/LearningPage.css` | 新增统一学习态样式、桌面/平板/手机构图及动效。 |
| `frontend/src/components/LearningGallery.css` | 删除旧横卡主页样式。 |
| `frontend/src/redesign.css` | 移除旧学习页/详情规则，保留全局与其他业务页面规则。 |
| `frontend/src/learningResource.ts` | 新增共享只读缓存、竞态隔离及错误重试。 |
| `frontend/src/learningResource.test.ts` | 新增缓存、竞态、失败和离开页面的测试。 |
| `frontend/src/components/LearningReader.test.ts` | 新增 64 卦正文/来源/特殊爻、导读审核及四项导航测试。 |
| `design-qa.md`、本文件 | 视觉自查、交付与验证记录。 |

本轮没有修改后端、古籍正文、映射、数据库结构、计算、AI 协议、Markdown 导出代码、Tauri 配置、版本号或字体资源。上述范围通过本轮开始时的 SHA-256 文件清单比较确认。[本轮初始文件快照](/workspace/scratch/yijing-integrated/baseline-files.json)。

## 验证结果

- 前端 `npm test`：17 个文件、76 项通过。含原有起卦、纳甲呈现、Markdown、AI 状态等测试，以及本轮新增 7 项。
- 后端 `.venv/bin/python -m pytest -q`：186 通过、1 跳过（Windows 专用 DPAPI）；1 条既有 Starlette 废弃警告。[日志](/workspace/scratch/yijing-integrated/backend-tests.log)。
- `npm run build`：TypeScript 与 Vite 生产构建通过。[日志](/workspace/scratch/yijing-integrated/build.log)。
- 浏览器验证 64 卦目录爻序/阴阳编码、全部详情的准确卦辞/六爻/特殊爻与固定来源；学习浏览没有非 GET API 请求，也未新增历史。
- 320、390、768、844、1024、1366、1536px：图鉴和乾/坤/未济详情无横向溢出，目录名称未被挤出点击区。验证搜索、分组、浏览器前进/返回、桌面内部滚动 209px 与手机窗口滚动 3609px 恢复，以及减少动效。
- 目录、预览、详情各自模拟 503 后可重试；空搜索可恢复。Chromium 无页面脚本错误。
- 实际浏览器走通手动初爻老阳（乾变姤）、经典取辞、纳甲、AI 入口、Markdown 下载、历史重新打开、偏好保存；390px 触摸事件模拟单次点按直接进入详情。
- 首页 71 个、详情 9 个文字节点的 CDP 实际字体检查均符合预期：界面与原文 `yijing-sans-regular`，大卦名 `yijing-serif-regular`，均为自带字体，没有受检节点回退。

浏览器脚本及日志位于 `/workspace/scratch/yijing-integrated/`：`verify_browser.py`、`verify_edges.py`、`capture_final.py`、`final_check.py`。开发核查使用临时库 `/tmp/yijing-integrated-review.sqlite3`，未使用真实用户数据库。既有自动化测试使用其自身测试隔离环境。

## 截图与待验收内容

全部为 Chromium 原生截图，1366 × 900 桌面、390 × 844 手机。完整对比和字体说明见 [设计自查](/workspace/yijing-workbench-public/design-qa.md)。

- [学习主页桌面](/workspace/scratch/yijing-integrated/learning-desktop.png)
- [学习主页手机](/workspace/scratch/yijing-integrated/learning-mobile.png)
- [详情桌面](/workspace/scratch/yijing-integrated/learning-detail.png) / [完整长页](/workspace/scratch/yijing-integrated/learning-detail-full.png)
- [详情手机](/workspace/scratch/yijing-integrated/learning-detail-mobile.png) / [完整长页](/workspace/scratch/yijing-integrated/learning-detail-mobile-full.png)
- [关键交互连续截图](/workspace/scratch/yijing-integrated/motion-sequence.png)
- [原型 B / 实现并排](/workspace/scratch/yijing-integrated/comparison-index.png)
- [原型 A / 实现并排](/workspace/scratch/yijing-integrated/comparison-reader.png)

未验证事项：Tauri 原生运行、安装与 Windows DPAPI；实体触屏设备、Safari 和 Firefox；真实联网 AI 响应；屏幕阅读器与完整无障碍认证。未进行真实用户历史库迁移，因为本轮未修改数据库。

视觉实现已自查，最终视觉验收仍等待用户反馈。后续根据反馈微调，不自动扩展重写其他业务页面。
