# 简洁化 UI 与六十四卦学习模块

本次实现文档中的首期「经典原文版」。使用现有 Vue 3、Element Plus、FastAPI 和 Tauri，不修改起卦、取辞、纳甲或 AI 协议，不升级正式版本。

## 已实现

- 四项主导航：起卦、学习、历史记录、设置。桌面侧栏可折叠，窄屏使用底部导航。
- 居中起卦表单，铜钱与手动 6/7/8/9 输入。结果通过四个二级入口访问概览、经典与取辞、六爻排盘和可选联网 AI；起爻过程默认折叠。
- 设置分成基础偏好、AI 辅助、数据与隐私、关于应用；保留密钥操作、偏好保存、桌面旧库导入限制、隐私确认及许可证。
- `GET /api/hexagrams`：从唯一 `HexagramCatalog` 返回文王序的 64 条轻量摘要。详情继续使用原有 `/api/hexagrams/{id}`；桌面鉴权照常执行。
- 2–5 列图鉴，支持名称、序号（包括 01）、上下卦名称搜索和上经/下经筛选。64 个详情展示原卦辞、初爻到上爻的爻辞、乾坤特殊爻辞及固定修订来源。
- 结果与学习共用 `HexagramGlyph`，初爻始终在下。学习数据不包含占问、历史或 AI 会话。
- Hash 路由支持直接访问、浏览器前进/后退；返回图鉴恢复搜索、筛选、滚动与卡片焦点。读不到资料时可重试；请求序号防止旧响应覆盖新详情。
- 卡片悬停、按下反馈、详情淡入及减少动效支持。键盘可打开卡片、逐爻展开和操作导航。

## 编辑导读

`frontend/src/data/learning_guides.json` 是独立只读编辑内容层，当前为空。`LearningGuide` 类型约定 `hexagram_id`、`one_liner`、`overview`、`line_guides`、`editorial_version`、`references` 和 `review_status`。只有 `review_status: "reviewed"` 才在界面展示；爻说明以 1–6 为键。经典原文仍由后端卦库提供。

当前没有可证明经过人工校审的八篇导读，因而界面诚实显示「原文阅读 / 导读整理中」。后续人工核对出处和校审后再添加内容；未补造白话课程、《彖传》或《象传》。未加入收藏、学习进度或数据库迁移。

## 验证方法与边界

```sh
.venv/bin/python -m pytest -q
cd frontend
npm test
npm run build
```

浏览器使用 Chromium + Playwright，在临时 SQLite 数据库下验证。服务启动示例（请使用新的临时数据库路径）：

```sh
YIJING_DB_PATH=/tmp/yijing-ui-review.sqlite3 .venv/bin/python -m uvicorn backend.main:app --port 8000
# 另一个终端
cd frontend && npm run dev
```

浏览器验收覆盖：64 个详情、来源与六爻、返回/前进、返回定位与焦点、搜索及分组、减少动效、390/768/1024/1536px 无横向溢出；起卦、手动爻序、结果入口、历史恢复、Markdown 下载、设置保存；学习错误/重试及空态。学习前后临时历史总量不变。

Windows DPAPI 测试在 Linux 跳过。未执行 Windows Tauri 安装包构建、真实密钥联网 AI 请求或真实旧库导入；既有相关单元测试继续覆盖业务逻辑。没有使用真实用户数据库。

## 本次验证结果

- 后端：186 passed，1 skipped（Windows DPAPI）。
- 前端：15 个测试文件、69 项测试通过；TypeScript 与 Vite 生产构建通过。
- 浏览器：64/64 详情、四种窗口宽度、返回定位与焦点、搜索/分组、错误重试、手动起卦、历史恢复及 Markdown 下载通过，未发生浏览器脚本错误。
- 测试数据仅写入 `/tmp/yijing-redesign-review.sqlite3`，截图保存在 `/workspace/scratch/yijing-ui/`。
