# 易经 UI 2.0：最后一轮视觉收尾

状态：本轮定点修改、自动化、浏览器回归和截图已完成，停止追加视觉迭代，等待最终验收。分支为 `feat/learning-ui-redesign`，未合并、未发布、未更新版本。

## 本轮修改

生产代码只修改 `frontend/src/components/LearningPage.css`：

- 常规桌面继续使用 8 列完整文王序，卦名从 14px/21px 提高至 16px/24px，点击区最小高度从 92px 提高到 100px，序号从 10px 提高至 11px。既有 1000–1210px 的 6 列适配保留，1211px 起为 8 列；全部 64 卦均可滚动到达。
- 收紧预览内边距、卦名与卦象间距、图形内部间距、卦辞行距、按钮及来源间距。保留原有构图、184px 卦象宽度和深墨绿辨识度。
- 深墨绿背景微调为 `#242d26`，正文为 `#f7f7ef`，辅助文字为 `#cfd7c8`；普通索引保持中性颜色，选中项继续使用朱砂。
- 右侧预览在桌面使用 sticky 定位；左侧独立滚动。移除主页 630px 最小高度，较矮窗口避免整页溢出，过长的预览可在自身区域滚动。
- `dvh` 之前补充 `vh` 后备声明；索引预留稳定滚动条槽，补充旧 Chromium 可识别的 WebKit 滚动条。生产 CSS 中后备声明仍被保留。
- 悬停抬升仅对精细鼠标指针生效；键盘焦点有可见轮廓与表面背景。手机继续使用轻量预览、双列目录及直接点按阅读，避免触屏出现悬停抬升。

字体资源、字体家族与字重体系、Vue 组件及业务代码均未修改。起卦、古籍来源、映射、SQLite、AI 协议、Markdown 导出和测试文件保留。桌面与手机详情的本轮前后截图 SHA-256 分别完全一致，未改变已审核的 A 阅读排版。

文档修改为项目根目录 `design-qa.md`（更新本轮自查）和本文件（新增）。工作区原有未提交改动保持原状；上述清单仅指本轮。

## 最终真实截图

均为 Linux Chromium 原生截屏，CSS 视口与图片像素一致，deviceScaleFactor=1，无浏览器边框。

| 页面 | 尺寸 | 截图 |
| --- | --- | --- |
| 桌面主页 | 1366 × 900 | [打开](review/learning-ui-2/learning-desktop.png) |
| 手机主页 | 390 × 844 | [打开](review/learning-ui-2/learning-mobile.png) |
| 桌面详情 | 1366 × 900 | [打开](review/learning-ui-2/learning-detail.png) |
| 手机详情 | 390 × 844 | [打开](review/learning-ui-2/learning-detail-mobile.png) |

补充证据：[桌面前后对比](review/learning-ui-2/comparison-desktop.png)、[索引局部 1:1 对比](review/learning-ui-2/comparison-focus-index.png)、[预览局部 1:1 对比](review/learning-ui-2/comparison-focus-preview.png)、[滚动至第 64 卦时的预览](review/learning-ui-2/desktop-scrolled.png)。

## 自动化与浏览器结果

| 检查 | 结果与证据 |
| --- | --- |
| 前端 `npm test` | **PASS**：17 个文件，76 项通过。[日志](review/learning-ui-2/frontend-tests.txt) |
| 后端 `.venv/bin/python -m pytest -q` | **PASS**：186 通过、1 跳过；跳过项为 Windows DPAPI，另有 1 条既有 Starlette 废弃警告。[日志](review/learning-ui-2/backend-tests.txt) |
| `npm run build` | **PASS**：TypeScript 与 Vite 生产构建。[日志](review/learning-ui-2/build.txt) |
| 64 卦及常规响应式 | **PASS**：完整文王序、六爻编码与顺序、全部详情原文/特殊爻/固定来源；搜索、分组、前进/返回、桌面索引滚动 273px 和手机窗口滚动 3609px 恢复。320、390、768、844、1024、1366、1536px 无横向溢出；学习只发送 GET 请求。[日志](review/learning-ui-2/browser-verification.txt) |
| 原有功能与异常恢复 | **PASS**：目录/预览/详情 503 重试、空搜索恢复；手动乾变姤、传统取辞、纳甲、AI 入口、Markdown 下载、历史重新打开和偏好保存。[日志](review/learning-ui-2/edge-verification.txt) |
| 独立索引滚动与交互 | **PASS**：鼠标滚轮滚动左索引后，右预览 y 坐标保持一致；hover、键盘 Home/End 与当前项同步，静止鼠标不抢占键盘选择；触屏模拟直接进入详情，返回保留选中项，无 hover 抬升。[结果](review/learning-ui-2/polish-verification.json) |
| 短窗口与传统滚动条 | **PASS（Linux Chromium）**：补查 1000×600、1024×768、1210×768、1211×768、1280×720、1366×480/600/768/900、1536×864、1920×1080。无整页横向或额外纵向溢出、卦名未被挤出按钮；较矮窗口中的阅读入口可以在预览内部滚动到达。 |
| 实际字体 | **PASS（Linux Chromium）**：CDP CSS.getPlatformFontsForNode 检查 80 个节点，界面/目录/正文实际使用 `yijing-sans-regular`，大卦名使用 `yijing-serif-regular`，均为自带 Noto CJK 字体，无受检节点 fallback。[证据](review/learning-ui-2/font-evidence.json) |
| 兼容后备模拟 | **PASS（当前 Chromium 中模拟）**：去除 dvh 与标准滚动条声明后，vh 高度及 WebKit 8px 滚动条分支正常。此项只验证后备规则，不等于旧版本引擎或 Windows 实机验证。 |
| DPR 与逻辑视口模拟 | **PASS（Linux Chromium）**：1.25×/1366×900、1.25×/1093×720、1.5×/911×600、2×/390×844，目录与详情无横向溢出，键盘进入详情正常。[结果](review/learning-ui-2/dpi-simulation.json) |
| 浏览器脚本错误 | 所有本轮核查页面均为 0。 |

以上自动化与浏览器结果为已完成的本分支验证记录，不是 Windows 验收。本轮按用户要求停止 Windows 原生验收，仅整理提交与待审阅 PR。

浏览器回归使用既有独立临时数据库 `/tmp/yijing-integrated-review.sqlite3`，没有使用真实用户历史库。脚本及日志保存在 `review/learning-ui-2/`。

## NOT_TESTED

| 项目 | 状态 | 原因 |
| --- | --- | --- |
| Windows Tauri / WebView2 原生运行与布局、滚动 | **NOT_TESTED** | 当前环境为 Linux，无 Windows WebView2。Chromium 检查不能替代此项。 |
| Windows DirectWrite 字体光栅化、125%/150% 系统缩放、原生滚动条 | **NOT_TESTED** | 已做本地字体、逻辑视口及 DPR 模拟；未运行 Windows 实机。 |
| Windows DPAPI | **NOT_TESTED** | 对应自动化测试在 Linux 跳过。 |
| 实体手机与 Safari / Firefox | **NOT_TESTED** | 本轮仅 Chromium，触屏为浏览器模拟。 |
| 真实外部 AI 请求 | **NOT_TESTED** | 保留已有协议与测试，仅验证 AI 入口，没有发起外部请求。 |
| 屏幕阅读器与完整无障碍认证 | **NOT_TESTED** | 已核查键盘焦点和减少动效，未执行完整认证。 |

本轮到此停止，等待用户最终验收。
