# 易经 UI 2.0：学习主页视觉审核

状态：**实现及技术核查完成，等待用户视觉反馈；未标记视觉验收通过。**

本轮仅精修六十四卦学习主页及该主页可见的导航外壳。保留原有详情、搜索/分组、接口、卦库、六爻绘图语义及测试。没有修改起卦、历史、纳甲、AI、Markdown 业务逻辑，没有升级版本、发布或合并分支。

## 1. 当前页诊断：已完成

本轮修改前重新打开 Linux Chromium，并保存原始截图。以 CDP `CSS.getPlatformFontsForNode` 检查实际排版字体，结合 `getComputedStyle`、匹配规则、`fc-list` 和 `fc-match` 交叉核对；未以字体声明或 `document.fonts.check()` 代替实际字体证据。

发现：

- 原 CSS 声明微软雅黑、楷体、宋体，但当前 Linux 未安装这些字体。标题、卦名实际使用 Noto Serif CJK SC Regular，界面文字使用 Noto Sans CJK SC Regular。标题/卦名声明 500 字重，实际匹配 Regular；未观察到字形重叠。
- 主标题额外字距为 2.16px，普通说明和侧栏多处行高是 `normal`，跨平台排版缺少明确约定。
- 旧页面的顶部栏分割线、标题区、工具栏、数量说明累积，桌面首卡约从 368px 才开始。
- 方卡将图形、卦名和重复的「原文阅读」居中堆叠，缺少左右阅读顺序，也没有在卡片上呈现上下卦名称。
- 品牌副标题为 11px；侧栏底部说明宽度不足，最后一个「备」字单独换行。修改前截图可直接看到这一问题。
- 主外壳在 `style.css` 与 `redesign.css` 均有规则；首页卡片、宫格和响应式规则散落于 `redesign.css` 多处。继续在文件尾堆叠覆盖会让视觉调整越来越难判断。

证据：

- [修改前桌面截图](/workspace/scratch/yijing-ui-v2/before-desktop.png)
- [修改前窄屏截图](/workspace/scratch/yijing-ui-v2/before-mobile.png)
- [修改前实际字体、计算样式及匹配规则](/workspace/scratch/yijing-ui-v2/before-fonts-and-css.json)

## 2. 新学习主页：已实现，待视觉审核

- 暖白底、深墨文本、少量朱砂，取消顶部栏分割线，搜索和分组共用一条对齐基线。
- 1366px 下三列横卡，单卡约 343 × 184px；390px 下单列横卡，单卡 350 × 140px。卦序/经篇、卦名、上下卦左对齐，六爻在右侧。
- 保留全部 64 卦及文王序，卡片名称和上下卦直接来自现有接口。页尾说明经典原文来源，详情继续保留固定修订出处。
- 首卡桌面位置为 y=315px，窄屏为约 y=337px。删除 64 次重复的「原文阅读」占位文字。
- 主标题使用 40px / 52px 无衬线 Bold；卡片卦名使用 27px / 40.5px 衬线 Regular；上下卦为 12px / 20px 无衬线。正文和卦名不设置额外字距。
- 学习主页品牌使用明确的无衬线字重；底部短说明保持单行。收起导航和底部四项导航继续可用。
- 卡片仅有 2px 上移、轻微按下缩放和轮廓/箭头淡入；减少动效时取消这些变化。未添加渐变、玻璃、重阴影或装饰插画。

### 实际字体

随包提供 OFL 授权 Noto CJK 字体子集，重新命名为 Yijing UI Sans / Yijing Reading Serif。字体从应用本地资源加载，不依赖字体 CDN 或操作系统安装。Regular 无衬线覆盖现有界面和经典字符；Bold 仅收录主页粗体所需字符；衬线收录 64 卦名。

| 用途 | 实际 PostScript 字体 | 实际字重 |
|---|---|---|
| 主标题、品牌、选中分组 | `yijing-sans-bold` | 700 |
| 描述、卦序、上下卦、导航说明 | `yijing-sans-regular` | 400 |
| 64 张卡片卦名 | `yijing-serif-regular` | 400 |

共核对 198 个文字节点，CDP 均返回预期字体且 `isCustomFont: true`。没有发现受检文字的字体回退、合成字重或标题/卦图相互侵入。三个 WOFF2 资源合计约 539 KiB。许可证附于 `frontend/src/assets/fonts/OFL-Noto-CJK.txt`，可用 `scripts/build_learning_fonts.py` 重建。

### CSS 收敛

- 主页样式集中于 `frontend/src/components/LearningGallery.css`。
- 删除 `redesign.css` 原有的首页宫格、卡片、工具栏和相关媒体查询规则，避免新旧两套首页样式同时生效。
- 主页使用 `learning-page--gallery` 标识；外壳调整只在 `app-shell--learning-gallery` 下生效，离开主页恢复原有业务页面样式。
- 卡片文字、图形采用统一内部间距；修正悬停轮廓向外 1px 导致按钮自身滚动宽度增加的问题。
- 生产预览与开发页的卡片坐标、尺寸及实际加载的卦名字体一致。

## 3. 技术核查：通过；视觉结论留待用户审核

- 前端原有 15 个测试文件、69 项测试全部通过；TypeScript 和 Vite 生产构建通过。
- Chromium 检查 320、390、768、1024、1366、1536px：页面和卡片无横向溢出。
- 64 张卡片逐项对照接口编码：六爻为上爻到初爻的显示顺序，阴阳线型一致。
- 搜索、上经/下经筛选、无结果状态、打开详情、浏览器返回、搜索状态、滚动位置和卡片焦点恢复正常。
- 侧栏收起/展开、窄屏导航和减少动效正常，未发生浏览器脚本错误。
- 卡片主文字与背景对比度约 14.81:1，次级文字 5.82:1，辅助文字 4.54:1。这些是指定纯色组合的计算值，不等于完整无障碍认证。

证据：

- [198 个节点的实际字体](/workspace/scratch/yijing-ui-v2/font-verification.json)
- [最终计算样式](/workspace/scratch/yijing-ui-v2/computed-styles.json)
- [浏览器核查结果](/workspace/scratch/yijing-ui-v2/verification.json)

## 审核截图

均为本轮真实浏览器截图。对比图只是将两张原始截图并排排版，没有重绘界面。

- [1366 × 900 桌面](/workspace/scratch/yijing-ui-v2/desktop-1366x900.png)
- [水雷屯卡片 3× 高分辨率细节](/workspace/scratch/yijing-ui-v2/card-detail-3x.png)
- [390 × 844 窄屏](/workspace/scratch/yijing-ui-v2/mobile-390.png)
- [调整前 / 本轮方案并排对比](/workspace/scratch/yijing-ui-v2/before-after.png)

到此停止，等待学习主页的视觉反馈，再决定是否将语言延伸到其他页面。
