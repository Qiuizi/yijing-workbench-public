# 第二轮视觉语言与交互精修 · 交付说明

PR：[#40](https://github.com/Qiuizi/yijing-workbench-public/pull/40) · 分支 `design/visual-language-r2`

范围：`website/`（GitHub Pages 官网）+ `frontend/`（Tauri 桌面端）。
未改动算法、经典原文、学习审批门控与数据库语义；未触碰 v3.3.1 Release 资产、历史安装包、Manifest、SHA256SUMS；未合并 main、未触发发布工作流。

---

## 0. 结论摘要

| 项目 | 结果 |
| --- | --- |
| 双端色板 | 一套角色、两套色值（浅色纸面 / 夜间深墨绿），全部收敛到 `tokens.css` / `theme.css` |
| 硬分隔 | 官网去掉 5 条整幅 border，改「上一区块色调溶解 + ±3% 色阶差」；页脚由整块暗底改为墨玉封底卡 |
| 品牌区 | 官网 / 桌面端 / 学习页统一为「六爻既济 + 朱色变爻」标记，双线边栏取篆刻意 |
| 夜间模式 | 官网 + 桌面端均可切换、持久化、跟随系统、首屏不闪；夜间字号整体降一档（实测 −0.5 ~ −2px） |
| 对比度 | token 66 组 + DOM 实测 1118 个文字节点，全部达 WCAG AA（严格 4.5 亦全过） |
| 浮层 | Element Plus 五类浮层在深浅两套主题下实开验收 64/64 |
| 实机 | 真实 Tauri/WebView2（Edg/155，dpr=2）通过 9+2 项检查 |
| 线上 | PR #40 合并（`0bcfabe`）+ Pages 部署成功，线上 13/13 |
| 回归 | typecheck / build / 单测 108 项 / 链接检查 / 交互回归 15 项 全部通过；控制台 0 错误 |
| 改动规模 | 90 个文件，+4242 / −697 行（含 37 张截图与校验记录） |

---

## 1. 判断：这轮真正要修的是什么

不是「不够好看」，而是三处不一致叠加出了「拼装感」：

1. **边界不一致**：官网 5 个区块各画一条 1px 深色硬边，块与块像木板拼接；桌面端卡片用 `#e8e4da`、表格用 `#efede7`、侧栏用 `#f1f0ea`，同一个"分隔"有 4 种表达。
2. **色阶不咬合**：深墨绿 hero 直接切到米白纸面，中间没有过渡；桌面端浅色卡片叠在浅色底上，靠边框硬撑层次。
3. **级差不统一**：官网标题 `clamp(38,5.2vw,64)`，桌面端标题 34/30/25 混用，同一层级在不同页面不是同一字号。

因此本轮的顺序是：**先统一角色（token）→ 再削弱边界（去硬线、给色阶）→ 最后才动细节（品牌、字体节奏、微交互）**。没有新增装饰性元素，删掉的规则和新增的一样多。

---

## 2. 改造清单 · 官网

| # | 模块 | 改动前 | 改动后 |
| --- | --- | --- | --- |
| 1 | 分隔与过渡 | hero 底部、features、download 各有整幅 `border: 1px` 深色硬边；深墨绿与纸面直接相接 | 删除全部整幅硬边；新增 `.section--blend`：把上一区块色调以 64–92px 渐变溶解进本区块顶部，相邻 surface 保持 ±3% 色阶差 |
| 2 | 页脚 | 整幅深色直接压在纸面上（试过渐隐，产生奶白雾带） | 改为**墨玉封底卡**：圆角、留白、内高光、铜金发丝边，与下载区同一语言，彻底不需要硬边 |
| 3 | Hero | 深色营销式首屏：64px 标题、金色主按钮、满幅暗底 | 纸面编辑式首屏：52px 上限标题、朱砂主按钮、暖纸底 + 极淡墨晕；截图 600px 宽，铜金卡纸边 10px，右上印章微旋转 |
| 4 | 导航 | 半透明暗底 + 金色硬边线 | 半透明纸底 + `backdrop-filter`，底部分隔改为两端渐隐发丝；新增主题切换按钮；品牌改为「标记 + 名称 + 拉丁 + 版本」四段式 |
| 5 | 功能区 | 7 张卡片统一 3px 圆角、金色描边，hover 上浮 2px 并发光 | 12 栏栅格（4+3）不变，卡片改 `surface-1` + 微对比边 + 内高光；hover 只做 `−1px` 位移 + 边色转向强调色；图标统一 32 视框 / 1.3 线重 / 34px 底座 |
| 6 | 图鉴 | 单元格 3px 圆角 + 深色边；搜索框、分组按钮各自一套边框 | 8×8 保留（文王序语义），单元格改半透明纸面 + 微对比边；分组按钮改分段控件；搜索框聚焦时墨晕 + 朱色边 |
| 7 | 图库 | 缩略图写死 `repeat(9,1fr)`，窄屏强行压扁 | 改 `repeat(auto-fill, minmax(98px,1fr))`，1440 下仍是 9 列，768/375 自动落列；夜间对截图整体压暗 12% |
| 8 | 下载区 | 深色面板 + 金色实边 + 大段留白；SHA 用衬线数字 | 全站唯一墨玉 slab：内部重挂语义 token（组件无需知道自己在暗底）；SHA 改等宽、点按复制带 Q 弹反馈与 `aria` 状态 |
| 9 | 开源区 | 整块卡片包裹 + 每项独立边框 | 去掉外框，改发丝线分区 + 行 hover 微亮；序号等宽、链接箭头微位移 |
| 10 | 字体节奏 | 标题 64 / 40 / 20 三级跳，overline 字距 .3em | 收敛为 52 / 33 / 22 / 17 / 16 / 14 / 12.5 七档，overline 字距 .16em，标题行高 1.18–1.36，正文 1.78 |
| 11 | 双语 | 英文页沿用同一套样式 | 英文页同步，拉丁标题用衬线 display，`letter-spacing` 单独收敛 |

---

## 3. 改造清单 · 桌面端

| # | 模块 | 改动前 | 改动后 |
| --- | --- | --- | --- |
| 1 | 品牌区 | 左上角是「易」字方块（`border:1px` + 20px 楷体），与右侧文字没有形成单元 | 换 `BrandMark`（六爻既济 + 朱色变爻，双线边栏），34px；字标「易经 / 起卦工作台」两级；折叠态只留标记；学习页 header 同步 |
| 2 | 顶栏 | 整条 `1px #dedbd1` 硬线；无主题入口 | 分隔改两端渐隐发丝；右侧新增主题按钮；窄屏（≤760）补品牌标记 |
| 3 | 主题 | 无 | `appearance.ts`：跟随系统 / 浅色 / 夜间，localStorage 持久化；顶栏快捷切换 + 设置页「外观」分组；Element Plus 暗色变量按同一套 token 桥接 |
| 4 | 表面层级 | 侧栏 `#f1f0ea`、卡片 `#fffefa`、表格 `#f2f1eb`、输入 `#fdfcf9` 各自为政 | 统一 `--bg / --surface / --surface-muted / --surface-raised / --surface-sunken` 五级，圆角收为 6/10/14，阴影改 1px+柔光双层 |
| 5 | 侧边导航 | 选中态是白底 + 粉边 | 选中态 = 表面抬升 + 朱色 2px 竖线咬住左边；hover 120ms；图标下沉 1px 与文字对齐 |
| 6 | 起卦页 | 顶部是 `☰` 字符方块；输入框聚焦只有 1px 变红 | 顶部改卦象标记（无底色版）；输入框聚焦出现径向墨晕（`--dur-3` 420ms，无滤镜）；主按钮按压缩进 1px |
| 7 | 结果页 | 卦象线固定深色，夜间不可读；序号混排 | 爻线用 `--ink-mark`（浅色深墨 / 夜间暖白），动爻保持朱色；序号、时间、版本全部等宽 |
| 8 | 学习页 | 阅读面板 `#242d26` / `#f7f7ef` 冷灰绿，与主界面不是一套色 | 改暖墨 `#17211c` / `#e9e4d6`；暗色下阅读面板抬一档为 `--surface-muted`；64 格图鉴爻线改 `--ink-mark` |
| 9 | 排盘 / 历史 / 设置 | 表格底、标签、筛选、设置分组各用一套浅色值 | 全部走语义 token；标签按 status 归类（角色/动爻/旬空/节气/冲克）各自取对应 soft 色 |
| 10 | 窄屏 | 底部导航 96% 半透明，下方按钮透出「重影」 | 改不透明 + 顶部柔影；`--shell-pad` 统一留白 |

---

## 4. 色彩与样式 token

### 4.1 角色表（官网 `website/src/styles/tokens.css`）

| 角色 | 浅色 | 夜间 | 用途 |
| --- | --- | --- | --- |
| `--bg` | `#f8f4ea` | `#131c17` | 页面底（米白 / 深墨绿） |
| `--surface-1` | `#fdfbf6` | `#17211c` | 一级表面：卡片、详情、封底内块 |
| `--surface-2` | `#f2ecdd` | `#1c2721` | 二级表面：交替区块（图库、图鉴） |
| `--surface-3` | `#eae3d1` | `#212d27` | 三级表面：输入槽、缩略图槽 |
| `--line` | `#e5ddcb` | `#2a362e` | 微对比边界（默认描边） |
| `--line-strong` | `#d3c8b2` | `#35423a` | 需要一点存在感的边界 |
| `--text-1` | `#222a26` | `#e5e0d2` | 正文主色 |
| `--text-2` | `#4d564e` | `#b3bab0` | 正文次色 |
| `--text-3` | `#626c63` | `#8b948a` | 弱化文字 |
| `--accent` | `#a04a38` | `#c4785f` | 强调（朱砂 / 陶红）：主按钮、当前项、变爻 |
| `--accent-strong` | `#83382a` | `#d18d75` | 强调按下态 / 深色文字 |
| `--accent-soft` | `#f4e5df` | `#2b211d` | 强调底色 |
| `--bronze` | `#81641f` | `#d3b57c` | 铜金：眉标、序号、细线 |
| `--success` | `#3f6449` | `#7fa48b` | 成功 / 已批准 |
| `--warning` | `#7f5c1d` | `#c3a05f` | 警示 / 待校对 |
| `--danger` | `#83382a` | `#d08a7a` | 危险 / 删除 |
| `--shell-bg` | `#17211c` | `#0f1713` | 墨玉块（下载区 / 封底） |

桌面端 `frontend/src/theme.css` 同角色命名（`--surface` / `--surface-muted` / `--text-primary` / `--text-secondary` / `--text-muted` / `--border` / `--border-strong`），色值与官网同源，仅按 UI 密度微调（纸底 `#f7f5ef`、夜底 `#121a16`）。

**兼容**：旧的 `--paper / --ink-text / --gold-300/400/500/600 / --shell-text / --cinnabar` 全部保留为别名指向新角色，历史组件的 `var()` 引用不需要一次性改写；新代码只允许使用语义名。

### 4.2 尺度 token

| 类别 | token | 值 |
| --- | --- | --- |
| 字号（官网） | `--t-display / h2 / h3 / lead / body / sm / xs / micro` | 52 / 33 / 17 / 22 / 16 / 14 / 12.5 / 11.5（夜间各降 1–2px） |
| 字号（桌面端） | `--text-display … --text-xs` | 30 / 24 / 19 / 16 / 14 / 13 / 12（夜间 28 / 22 / 18 / 15 / 13.5 / 12.5 / 11.5） |
| 间距 | `--s-1 … --s-11`（官网）/ `--space-1 … --space-7`（桌面端） | 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 / 80 / 104 / 128 |
| 圆角 | `--radius-xs/sm/md/lg` | 2 / 4 / 8 / 14（桌面端 6 / 10 / 14） |
| 动效 | `--dur-1/2/3` × `--ease-out/soft` | 120ms / 200ms / 420ms，`cubic-bezier(.22,.68,.28,1)` 为主 |

### 4.3 对比度校验

`scripts/check_contrast.py` 从两个 token 文件里解析变量、递归解析 `var()`、逐对计算 WCAG 比值，共 66 组（无法解析或低于阈值即退出码 1，可直接进门禁）：

- 官网浅色：正文/页面底 **13.40**、次文 6.94、弱化 4.97、强调 5.41、铜金 5.06、墨玉区正文 13.01
- 官网夜间：13.20 / 8.76 / 5.56 / 5.14 / 8.85 / 14.35
- 桌面端浅色：13.50 / 7.23 / 5.31 / 强调 5.75 / 按钮文字对强调填充 5.75
- 桌面端夜间：13.44 / 7.69 / 5.16 / 强调 4.88 / 按钮文字对强调填充 5.22

结果：`checks/contrast.txt`，`PASS`。

> 本轮据此修掉两个真实缺陷：浅色 `text-3` 在二级表面上只有 4.37（调到 `#626c63` → 4.63）；桌面端夜间主按钮原本是白字压浅赭（约 2.6:1），改为深墨字后 5.22。

---

## 5. 品牌区方案

- **形**：六爻「既济」排列，第二爻为朱色断线，表示「变爻」——这是产品语义（起卦 / 动爻），不是装饰。外框双线（0.9px + 34% 不透明度）取篆刻边栏意，无文字，40×40 网格内 6 条 2.8px 横线，最粗也最简。
- **色**：纸面用 `currentColor` + 朱线；墨玉面用铜金 `#d3b57c` + 提亮朱 `#c4785f`。
- **单元**：标记 34–38px + 两行字标（名称 / 副题），间距 9–11px，整体左对齐；版本号等宽放在副题末尾。桌面端折叠后只留标记，不留下「半截文字」。
- **落点**：官网 header、官网封底、桌面端侧栏、学习页 header、起卦页顶部（无底色版）。
- **弃用**：原「易」字方块（`18px` 楷体 + 1px 边框，视觉上是占位符）与旧 5 线标记（40px 下过于稀疏）已删除，旧 SVG 资源同步替换为同形。

---

## 6. 夜间模式方案

**不反色**，而是同一角色换一套色值，且遵守三条规则：

1. **不用纯黑**：夜间底 `#121a16`（桌面端）/ `#131c17`（官网），墨玉块压到 `#0f1713`，都是深墨绿；
2. **靠边界与色阶分层，不靠阴影**：夜间阴影几乎不可见，改用 `--border` 微亮线 + 内高光 `--sheen`（`rgba(233,228,214,.06)`）；
3. **亮底素材压暗**：官网 hero / 图库截图在夜间 `filter: brightness(.88~.90)`，避免整屏最亮的是一张界面图。

**字号降一档**：官网直接改 token（`--t-display 52→50`、`--t-body 16→15` 等）；桌面端大部分规则仍是写死 px，故在 `dark.css` 里对**阅读面**逐条收 1px（起卦标题 −2、正文 −1、表格 −0.5、标签 −0.5）。实测见 `checks/type-scale.txt`：

```
site: hero h1 52→50 (−2) · slogan 22→21 (−1) · body 14→13.5 (−0.5) · card title 17→16 (−1)
app : page title 32→30 (−2) · field label 16→15 (−1) · textarea 15→14 (−1) · nav item 14→13 (−1)
学习页: index h1 30→28 (−2) · matrix name 16→15 (−1) · preview title 44→42 (−2)
```

**入口与落地**：官网 header 主题按钮 + `prefers-color-scheme` 兜底 + `localStorage`；`index.html` / `en/index.html` 内联脚本在首屏绘制前定主题，避免闪白。桌面端顶栏按钮 + 设置页「外观」三选（跟随系统 / 浅色 / 夜间），同一套 `data-theme` + `.dark` 双写（后者供 Element Plus 暗色变量）。

**已核对项**：正文字号与对比度、输入框（`--surface` 底 + `--border-strong` 边 + 聚焦光环）、卡片边界（微亮线）、状态标签（role / moving / void / calendar / clash 各自 soft 底）、焦点态（2px 强调色描边 + 2px offset）、数字与时间（等宽 + 弱化色）。

---

## 7. 图标与文字对齐

- 根因：图标放在 flex 行里由 `align-items:center` 居中，字形却有下伸部（如「学」「史」），视觉重心偏上；行内图标则完全按基线对齐，在 14–16px 字号下会「浮」起来。
- 处理：行内 SVG 统一 `vertical-align: -0.125em`；flex 行内图标（侧栏、底部导航、按钮、学习页导航）统一下沉 `1px`（≈1/8em）；`BrandMark` 在字标旁 `margin-top:-1px` 做光学对齐。
- 线重统一：官网功能图标 32 视框 / `stroke-width:1.3` / `round` 末端；桌面端 Element Plus 图标 18px，与大写汉字视觉重量匹配。

---

## 8. 数字系统

`font-variant-numeric: tabular-nums` + `font-feature-settings:'tnum' 1` 覆盖：

- 官网：SHA 摘要、文件大小、版本号、发布日期、卦序、图库页码、功能编号、封底版本与年份；
- 桌面端：结果时间、卦序、爻位、干支与旬空、历史时间与分页、排盘表、设置里的版本号、学习页 64 卦序号。

效果：时间与序号切换时不再左右跳动（`checks/type-scale.txt` 同页可复核字号）。

---

## 9. 微交互与墨晕

| 场景 | 处理 | 参数 |
| --- | --- | --- |
| Hover | 只改边色 / 底色的明度，位移 ≤1px | 120ms `--ease-out` |
| Press | 下沉 0.5–1px，无回弹 | 120ms |
| Focus | 2px 强调色描边 + 2px offset；输入框追加 3px 12% 光环 | 200ms |
| 复制 SHA | 文案切「已复制」+ 勾选图标 + 一次 340ms `seal-pop`（1→1.06→1） | 340ms |
| 起卦成功 | toast 一次 200ms `toast-pop`（−6px→+1px→0） | 200ms |
| 展开/切页 | 内容 `rise-in` 位移 10px + 淡入 | 520ms |
| 拖拽 / 吸附 | 本产品无拖拽交互（无排序、无分栏拖拽），本轮不引入 | — |

**输入墨晕**：只落在起卦问题输入与 AI 输入两处。实现是 `.el-textarea::after` 上的一层径向渐变（`color-mix(accent 14%)`）+ `opacity` 过渡，**不使用 `filter: blur`**，不参与布局，不拦截指针；`prefers-reduced-motion` 下自动降为瞬时。输入框本体只加 3px 12% 光环，文字与光标不动。

---

## 10. 修改前后截图

同一 Chrome 版本、同一视口、同一合成数据库、同一操作序列（before 由 `git archive HEAD` 快照 + 复用依赖启动，after 由当前工作区启动）。

| 场景 | 修改前 | 修改后 |
| --- | --- | --- |
| 官网首屏 1440 | [before](before/site-hero-1440.png) | [after](after/site-hero-1440.png) · [夜间](after/site-hero-1440-dark.png) |
| 官网功能/图库 | [before](before/site-features-1440.png) | [after](after/site-features-1440.png) |
| 官网图鉴 | [before](before/site-atlas-1440.png) | [after](after/site-atlas-1440.png) |
| 官网下载 | [before](before/site-download-1440.png) | [after](after/site-download-1440.png) |
| 官网页脚 | [before](before/site-footer-1440.png) | [after](after/site-footer-1440.png) |
| 官网 375 | [before](before/site-375.png) | [after](after/site-375.png) |
| 桌面端起卦 | [before](before/app-home-1280.png) | [after](after/app-home-1280.png) · [夜间](after/app-home-1280-dark.png) |
| 桌面端结果 | [before](before/app-result-1280.png) | [after](after/app-result-1280.png) · [夜间](after/app-result-1280-dark.png) |
| 桌面端学习 | [before](before/app-learning-1440.png) | [after](after/app-learning-1440.png) · [夜间](after/app-learning-1440-dark.png) |
| 桌面端设置 | [before](before/app-settings-1280.png) | [after](after/app-settings-1280.png) |
| 桌面端 683（≈200%） | [before](before/app-683.png) | [after](after/app-683.png) |

补充细节：品牌区 2x [桌面](after/app-sidebar-2x.png) / [官网](after/site-header-2x.png)；宽屏 1920 [桌面](after/app-1920.png)；官网整页 [浅色](after/site-full-1440.png) / [夜间](after/site-full-1440-dark.png)；官网 768 [平板](after/site-768.png)。

---

## 11. 验证

| 项目 | 命令 | 结果 | 记录 |
| --- | --- | --- | --- |
| 官网类型 | `npm --prefix website run typecheck` | 通过 | `checks/typecheck-website.txt` |
| 官网构建 | `npm --prefix website run build` | 通过，CSS 41.75→39.63 kB | `checks/build-website.txt` |
| 官网链接 | `node website/scripts/check-links.mjs --base /yijing-workbench-public/` | 6 内部链接 0 缺失 | `checks/check-links.txt` |
| 桌面类型 | `npm --prefix frontend run typecheck` | 通过 | `checks/typecheck-frontend.txt` |
| 桌面构建 | `npm --prefix frontend run build` | 通过（既有 chunk >500kB 警告未变） | `checks/build-frontend.txt` |
| 桌面单测 | `npm --prefix frontend run test` | 24 文件 / 108 用例全通过（新增设置页外观分组断言） | `checks/test-frontend.txt` |
| 对比度（token） | `python scripts/check_contrast.py` | 66 组全过 | `checks/contrast.txt` |
| 对比度（DOM 实测） | `node scripts/audit-contrast.mjs` | 10 个页面/主题组合 **0 处**低于 AA（修复前 38 处） | `checks/dom-contrast.txt` |
| 交互回归 | `node scripts/ui-regression.mjs` | 15/15 通过，控制台 0 错误 | `checks/interaction-regression.txt` |
| 字号降档 | `node scripts/measure-type.mjs` | 两端 16 个元素均下降 | `checks/type-scale.txt` |
| 字号可读性（本轮） | `node scripts/type-readability.mjs` | 5 页逐元素比对，0 处不合规 | `checks/type-readability.txt` |

> DOM 审计的做法：遍历所有文字节点，向上逐层合成有效背景（含半透明与 `background-color`），按字号/字重选 4.5 或 3.0 阈值。它抓到了 token 校验抓不到的三类问题：官网墨玉块用纯渐变当底色（有效背景不可测，已改 `background-color`）、夜间历史列表问句仍是 `#44453e`（1.7:1）、Element Plus 的 `--el-radio-button-*` 定义在组件自身导致白色文字压浅赭（3.39:1）。修复记录见 `checks/dom-contrast-before.txt`（旧版脚本、38 处，含误报）与 `checks/dom-contrast.txt`（本轮修复后 0 处）。

> 版本说明：`dom-contrast-before.txt` 由**上一版**审计脚本生成（该版本无论结果如何都返回 0，且不区分「未评估」），只作历史对照；当前门禁语义见 12.1。

交互回归覆盖：主题按钮切换并持久化、`color-scheme` 同步、图鉴 64 格选中与搜索收敛、图库 9 张点击与方向键、SHA 复制反馈、英文页文案与导航、桌面端起卦链路（问句/4 标签/双卦卡）、排盘页与 6 爻表格生成、设置页外观分组与切回浅色、两端控制台无错误。

> 说明：`scripts/shoot.mjs`、`ui-regression.mjs`、`measure-type.mjs`、`audit-contrast.mjs`、`audit-contrast.selftest.mjs`、`ep-overlay-check.mjs`、`type-readability.mjs`、`webview2-check.mjs` 都是零依赖脚本（Node 22 自带 WebSocket + CDP），不新增 npm 依赖、不改锁文件。

---

## 12. 验收收尾（PR #40 最终质量验收）

本轮不新增视觉设计，只做质量闭环：修审计工具、补真实缺陷、补实机验证。

### 12.1 审计脚本：从「永远通过」改成真门禁

原 `scripts/audit-contrast.mjs` 无论检测到什么，最后都 `process.exit(0)`，等于没有门禁。现在：

| 退出码 | 含义 | 触发条件 |
| --- | --- | --- |
| 0 | 通过 | 全部页面完成审计，0 违规，0 未评估 |
| 1 | 违规 | 存在低于阈值的文字节点 |
| 2 | 执行失败 | Chrome 启动/CDP/页面加载/脚本异常，或页面没完成扫描（body 为空、0 个文字节点、主题未生效） |
| 3 | 未评估 | 无违规，但有无法准确计算背景的文字（渐变态/图片底/找不到不透明背景）——不算通过 |

其他修正：`--min` 明确为「统一阈值，覆盖 AA 的分级规则」（默认仍按 AA：正文 4.5、大字 3.0）；每页导航前先回 `about:blank`，避免 SPA 的 hash 跳转不触发 load 事件；Chrome 与 CDP 在成功/失败路径都清理，`kill` 的 ESRCH 竞态不再覆盖退出码；`--url name=url@theme` 支持任意页面审计。

**反向测试**（`scripts/audit-contrast.selftest.mjs`，本地起静态服务造 5 种页面）：

```
PASS  合规页面 → 0            exit=0
PASS  低对比度文字 → 1        exit=1
PASS  渐变背景文字 → 3        exit=3（未评估不算通过）
PASS  页面不可达 → 2          exit=2
PASS  页面无内容 → 2          exit=2（不得报 0 违规）
5/5 反向用例符合预期
```

本轮审计用它跑出 8 处真违规并修掉：`.feature__num` 11px + `opacity .7` 只有 3.29；下载区/封底用纯渐变当底色导致「有效背景」不可测（改 `background-color` + `::before` 装饰层，墨玉块回归可计算）；三处装饰性「·」「/」分隔符分别只有 2.0–2.5:1（删掉「·」，页码斜杠改 `--text-3`，品牌副题改用 1px 竖线）。修完 10 页 1118 节点 0 违规 0 未评估，`--min 4.5` 严格模式同样 0 违规。

### 12.2 Element Plus 浮层：实开验收 64/64

新增开发期自检页 `frontend/dev/overlay-inspect.html`（`?theme=dark`，不进生产构建）+ 自动化 `scripts/ep-overlay-check.mjs`：真实点开 dialog / drawer / message-box / select 下拉 / message，量计算样式并在两套主题下各截一张图。

| 检查面 | 结果 |
| --- | --- |
| 表面色 | 夜间 lum 0.014 / 0.022（dialog、drawer、message-box、select popper、message 全为深墨，无白底） |
| 文字对比 | 弹层标题 12.53、正文 7.69、主按钮 5.22、选项 4.61 — 全部 ≥ 4.5 |
| Teleport | message-box overlay 直挂 body；select 下拉挂在 `#el-popper-container-*`（已脱离组件子树） |
| 遮罩 | dialog `rgba(0,0,0,.5)` / 夜间 `rgba(9,15,12,.62)`，覆盖满视口 |
| 主题切换 | 已打开的 message-box 从 `rgb(23,33,28)` → `rgb(253,251,246)`，实时跟随 |
| 滚动锁 | drawer 关闭后 `el-popup-parent--hidden` 已移除 |
| 状态 | 单选选中 5.75/5.22；禁用按钮 5.72/5.1；禁用选择器 5.11/5.95；复选框勾选态可见 |

**发现并修掉两个真实缺陷**：
1. **夜间焦点环几乎不可见**：EP 用 `--el-button-outline-color: primary-light-5`，夜间混成 `rgb(103,73,59)`，对深底约 **2.2:1**（低于 1.4.11 的 3:1）。改为 `--el-button-outline-color: var(--accent)` 后浅色 3.53、夜间 6.20。
2. 单选选中项仍是 EP 的 `#fff`（上一轮只改了 `:root` 级变量，被组件自身的 `--el-radio-button-*` 覆盖），3.39:1；改为在 `.el-radio-button` 同层级改写后 5.75/5.22。

真实应用内的删除确认（`ElMessageBox.confirm`）另存截图：`after/app-delete-confirm-dark.png`。

### 12.3 夜间字号：按可读性重做，54 处不合规 → 0

新增 `scripts/type-readability.mjs`：同一元素浅/夜两套主题逐个比对计算字号，规则是「≤12px 的微字不得再缩」「夜间阅读文字不低于 12px」「字差不超过 2px」。首跑 54 处不合规，全部是上一轮「整体降一档」的副作用：

- 官网 `--t-micro` 11.5→11px（缩略图标签、眉标、下载区标签等 50 处）→ 微字保持原尺寸，只缩标题与正文；
- 桌面端 `.field-hint` 13→11.5px（掉到 12px 以下）→ 改 12.5px；
- 设置页辅助说明 12→11.5px、以及 `em` 相对缩放的 11.67→11.25px → 统一保住 12px 下限。

结论：夜间仍是「标题 −2px、正文 −1px」，但 9–12px 的微标签、输入提示、错误与状态文字不再缩小；字差 ≤2px，无布局跳动（`checks/type-readability.txt`）。

### 12.4 真实 Windows / WebView2（不再是 NOT_TESTED）

用隔离 identifier（`cn.yijing.workbench.qaverify`）重建 `yijing-workbench.exe`，以 `WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS=--remote-debugging-port=9223` 启动真实 WebView2，再用 CDP 附着取证（不依赖 PrintWindow，直接拿渲染器像素）：

| 检查 | 结果 |
| --- | --- |
| 运行时 | UA 含 `Edg/155.0.4283.62`，真实 WebView2 而非浏览器模拟 |
| 缩放 | `devicePixelRatio = 2`，CSS 视口 1320×880，截图 2640×1760 物理像素 |
| 首启主题 | 浅色、无存储偏好 → 点顶栏按钮切夜间，`data-theme=dark` 且写入 localStorage |
| 起卦与结果 | 实机输入问句 → 4 标签 + 双卦卡；夜间爻线与卡片层级正常 |
| 排盘 | 实机生成 6 爻表格，表头底色 `rgb(27,38,32)` |
| 弹窗 | 实机 message-box：表面 `rgb(23,33,28)`，标题对比 12.53，Teleport 到 body |
| 重启持久化 | 关闭进程后重启，仍为夜间（`theme=dark stored=dark`） |

数据隔离：全程只写 `%LOCALAPPDATA%\cn.yijing.workbench.qaverify`，测试后删除；真实库 `%LOCALAPPDATA%\cn.yijing.workbench\history.sqlite3` 未改动（sha256 `B0A8D304…343452`，282624 bytes）。`tauri.conf.json` 的 identifier 已还原。

### 12.5 本轮回归全量结果

| 项目 | 结果 | 记录 |
| --- | --- | --- |
| 前端 typecheck / test / build | 通过 / 108 用例 / 通过 | `checks/typecheck-frontend.txt`、`test-frontend.txt`、`build-frontend.txt` |
| 官网 typecheck / build / 链接 | 通过 / 通过 / 6 内部链接 0 缺失 | `checks/typecheck-website.txt`、`build-website.txt`、`check-links.txt` |
| token 对比度 | 66 组全过 | `checks/contrast.txt` |
| DOM 对比度 | 10 页 1118 节点，0 违规 0 未评估（严格 4.5 亦 0） | `checks/dom-contrast.txt`、`dom-contrast-strict.txt` |
| 审计反向测试 | 5/5 | `checks/audit-selftest.txt` |
| 浮层验收 | 64/64 | `checks/ep-overlay.txt` |
| 夜间字号 | 0 处不合规 | `checks/type-readability.txt` |
| 交互回归 | 15/15 | `checks/interaction-regression.txt` |
| 实机 WebView2 | 9/9 + 2/2 | `checks/webview2.txt` |

### 12.6 合并与线上部署验证

| 项目 | 结果 |
| --- | --- |
| PR #40 | 已合并（squash），merge commit `0bcfabe`，2026-10-26T13:30:31Z |
| 合并前 CI（e3adf51） | Backend / Frontend / website-validation / Windows x64 + NSIS 四项全 pass |
| Pages 部署 | `Deploy website to Pages` run 40331182930，commit `0bcfabe`，**success** |
| 线上验收 | `node scripts/pages-live-check.mjs` → **13/13**，连续两次运行结果一致（`checks/pages-live.txt`） |

线上逐项：中文首页标题/语言正确；新版品牌标记与主题按钮在线；5 个色阶咬合区块；图鉴 64 格、图库 9 张；首屏浅色 → 点按钮转夜间 → 刷新仍为夜间；移动端 390px 抽屉可展开且 4 个入口、无横向溢出；英文页正常；控制台 0 错误。

**下载区与真实 Release 的逐项核对**（`checks/release-crosscheck.txt`）：

| 项 | GitHub Release v3.3.1 | 线上页面 |
| --- | --- | --- |
| tag | `v3.3.1` | `v3.3.1` |
| 文件名 | `yijing-workbench-3.3.1-x64-setup.exe` | 同 |
| 字节数 | 16,097,113 | `15.4 MiB · 16,097,113 bytes` |
| SHA-256 | `3CAECBE2…B086B74`（与 SHA256SUMS.txt 逐字一致） | `3CAECBE2…B086B74` |
| 发布日期 | 2026-10-24 | `2026-10-24` |

线上截图：`after/pages-home-light.png`、`pages-home-dark.png`、`pages-mobile-drawer.png`、`pages-en.png`。

> 测试隔离：`pages-live-check.mjs` 在每次运行前用 CDP `Storage.clearDataForOrigin` 清掉线上 origin 的 localStorage —— 否则上一次运行的 `yijing-theme=dark` 会让「首屏浅色」断言误报（首次复跑就是这样失败的，已修）。

## 13. 未完成项与风险

1. ~~真实 Tauri 窗口 / WebView2 未在真机截图验证~~ —— 已在 12.4 补齐（Edg/155，dpr=2，9+2 项通过）。仍未覆盖：多显示器拖拽、系统缩放中途切换、WebView2 缺失时的 Bootstrapper 路径。
2. **深色下 Element Plus 浮层只做变量桥接**（`--el-bg-color` 等），未逐组件截图核对 `el-dialog` / `el-message-box` / `el-select` 下拉；DOM 审计也只覆盖了当前渲染出的节点（抽屉与下拉未展开取样）。
3. **桌面端仍有大量写死 px 字号**（`style.css` 273 条、`LearningPage.css` 88 条）。夜间降档只覆盖了阅读面 30 余条规则与全部 token 化文本；微标签（9–11px）有意不降。彻底方案是把组件字号全部迁到 `--text-*`，属于下一轮的结构性工作。
4. **学习页仍有一批 9–12px 小字**（文王序、页码、脚注）。夜间未调整，仅调色；更细的可读性优化需要与 Qiuizi 确认是否允许放大版面。
5. **官网 `og-cover.svg` 仍是旧标记**（5 线母题）。分享封面不在本轮 UI 面内，未改动；如需统一，是一张图的独立改动。
6. ~~GitHub Pages 线上未验证~~ —— 已在 12.6 完成（run 40331182930，13/13）。仍未覆盖：GitHub Pages 的 CDN 缓存刷新时间窗、部署回滚演练、自定义域名/HTTPS 证书。
7. **`prefers-reduced-motion` 覆盖**：两端均已把动画降到 0.01ms，但没有做「关闭墨晕」的独立开关——墨晕本身是纯渐变透明度，降级后即静态。
8. **未做 A/B 或可用性测试**：字号、间距的取舍来自对比度与版式规则，不是用户实测数据。

---

## 14. v3.3.2 发布前门禁（本轮不执行）

本轮不建 Tag、不覆盖 v3.3.1 安装包、不发布新安装程序。合并后的正式发布是独立操作，前置条件：

1. 从**最终 main SHA** 重新构建 Windows 安装包（不得复用本轮 QA 用的 exe：它带临时 identifier `…qaverify`）。
2. 用独立脚本核验 EXE 的 SHA-256，并与 Manifest / SHA256SUMS.txt 逐字一致。
3. Windows 安装与升级实测：干净安装、覆盖升级（保留历史记录与设置）、卸载残留检查。
4. 主题切换与数据保全：升级后 localStorage 外观偏好、`history.sqlite3`、DPAPI 保护的 API Key 均不受影响。
5. 新 Release 的 EXE、校验和、PROVENANCE 三者同源且版本号一致（`tauri.conf.json` / `package.json` / `Cargo.toml` / `Cargo.lock`）。
6. 官网 `RELEASE_STATIC` 与 GitHub Release 的 tag、文件名、字节数、SHA-256 四项对齐后再部署 Pages。
7. 若本次合并不改版本号，则不应产生新 Release —— 发布与前一轮的 v3.3.1 资产保持互不影响。
