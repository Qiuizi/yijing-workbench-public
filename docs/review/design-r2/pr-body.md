## 概要

第二轮视觉语言与交互精修，只做设计系统层面的统一，不修 bug、不加功能。官网与桌面端共用一套角色 token（两套色值），把「硬分隔 + 各自为政的浅色值 + 级差过猛」三件事一起收掉，并补上双端夜间模式、品牌标记、图标基线、等宽数字与克制的微交互。

- 未改动算法、经典原文、学习审批门控、数据库语义。
- 未触碰 v3.3.1 Release 资产、历史安装包、Manifest、SHA256SUMS。
- 未合并 main、未触发发布工作流。

详细交付说明（含 10 项要求逐条对应）：[`docs/review/design-r2/README.md`](docs/review/design-r2/README.md)

## 主要改动

### 设计 token
- 新增 `website/src/styles/tokens.css`（重写）与 `frontend/src/theme.css`：调色板（米白 / 温灰 / 墨绿 / 黛青 / 柔和棕红）、语义角色、字号、间距、圆角、动效；旧变量名保留为别名。
- 新增 `frontend/src/dark.css`：把遗留浅色值（卡片、爻线、表格、标签、EP 浮层）与学习页调色板迁到夜间色。
- 新增 `scripts/check_contrast.py`：解析两端 token，逐对算 WCAG，66 组全过（`checks/contrast.txt`）。据此修掉两处真实缺陷：浅色 `text-3` 在二级表面上 4.37→4.63；夜间主按钮白字压浅赭 2.6:1 → 改深墨字 5.22:1。

### 分隔与过渡
- 官网删除 5 条整幅硬边，改 `.section--blend`：上一区块色调以 64–92px 渐变溶解，相邻 surface 保持 ±3% 色阶差。
- 页脚由整幅暗底改为墨玉封底卡（与下载区同一语言），避免「贴在纸面上」的硬边与渐变雾带。
- 桌面端顶栏分隔改两端渐隐发丝；底部导航改不透明，消除内容透出的重影。

### 品牌区
- 新标记：六爻既济 + 朱色变爻，双线边栏。官网 header/封底、桌面端侧栏、学习页 header、起卦页顶部统一使用；旧「易」字方块与 5 线稀疏标记删除。

### 夜间模式
- 官网：跟随系统 + header 手动切换 + localStorage，内联脚本先定主题不闪白。
- 桌面端：`appearance.ts`（跟随系统 / 浅色 / 夜间）+ 顶栏快捷按钮 + 设置页「外观」分组；Element Plus 暗色变量按同一套 token 桥接（`data-theme` + `.dark` 双写）。
- 夜间字号整体降一档：官网走 token 覆盖，桌面端对阅读面逐条 −1px；实测 −0.5 ~ −2px（`checks/type-scale.txt`）。
- 不用纯黑、不靠阴影分层、亮底截图夜间压暗。

### 细节
- 图标与文字：行内 `vertical-align:-0.125em`，flex 行内下沉 1px；图标线重统一 1.3。
- 数字：SHA、版本、卦序、时间、分页、干支全部 `tabular-nums`。
- 微交互：hover/press ≤1px、120ms；复制 SHA 有 340ms `seal-pop`；成功 toast 200ms；输入框聚焦墨晕用径向渐变 + opacity 过渡，**无 `filter: blur`**。

## 截图

| 场景 | 前 | 后 |
| --- | --- | --- |
| 官网首屏 | [before](docs/review/design-r2/before/site-hero-1440.png) | [after](docs/review/design-r2/after/site-hero-1440.png) / [夜间](docs/review/design-r2/after/site-hero-1440-dark.png) |
| 官网图鉴 | [before](docs/review/design-r2/before/site-atlas-1440.png) | [after](docs/review/design-r2/after/site-atlas-1440.png) |
| 官网下载 | [before](docs/review/design-r2/before/site-download-1440.png) | [after](docs/review/design-r2/after/site-download-1440.png) |
| 桌面端起卦 | [before](docs/review/design-r2/before/app-home-1280.png) | [after](docs/review/design-r2/after/app-home-1280.png) / [夜间](docs/review/design-r2/after/app-home-1280-dark.png) |
| 桌面端结果 | [before](docs/review/design-r2/before/app-result-1280.png) | [after](docs/review/design-r2/after/app-result-1280.png) / [夜间](docs/review/design-r2/after/app-result-1280-dark.png) |
| 桌面端学习 | [before](docs/review/design-r2/before/app-learning-1440.png) | [after](docs/review/design-r2/after/app-learning-1440.png) / [夜间](docs/review/design-r2/after/app-learning-1440-dark.png) |

before 由 `git archive HEAD` 快照 + 复用依赖启动，同视口、同合成数据库、同操作序列。

## 验证

| 项目 | 结果 | 记录 |
| --- | --- | --- |
| 官网 typecheck / build | 通过，CSS 41.75→39.63 kB | `checks/typecheck-website.txt`、`checks/build-website.txt` |
| 官网链接检查 | 6 内部链接 0 缺失 | `checks/check-links.txt` |
| 桌面端 typecheck / build | 通过（既有 chunk 警告未变） | `checks/typecheck-frontend.txt`、`checks/build-frontend.txt` |
| 桌面端单测 | 24 文件 / 108 用例全通过 | `checks/test-frontend.txt` |
| 对比度 | 66 组全过 | `checks/contrast.txt` |
| 交互回归 | 15/15，控制台 0 错误 | `checks/interaction-regression.txt` |
| 夜间字号 | 18 个元素均下降 | `checks/type-scale.txt` |

三个零依赖脚本（`scripts/shoot.mjs`、`ui-regression.mjs`、`measure-type.mjs`）用 Node 22 自带 WebSocket 直连 CDP，不新增 npm 依赖、不改锁文件。

## 未完成与风险

1. 真实 Tauri / WebView2 未截图验证（同内核 Chromium 逐视口取证，WebView2 仍 `NOT_TESTED`）。
2. 深色下 `el-dialog` / `el-message-box` / 下拉只做变量桥接，未逐组件截图。
3. 桌面端仍有写死 px 字号（`style.css` 273 条、`LearningPage.css` 88 条），夜间降档只覆盖阅读面；全量迁 token 属下一轮。
4. 学习页 9–12px 小字夜间未调字号，只调色。
5. 官网 `og-cover.svg` 仍是旧标记（不属于本轮 UI 面）。
6. GitHub Pages 线上是否已更新需合并后由 `pages.yml` 确认。
