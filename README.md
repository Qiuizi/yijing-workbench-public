# 易经起卦工作台

<p align="center">
  <img src="docs/images/readme-banner.png" alt="易经起卦工作台" width="1280">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-v3.3.0-c9a227" alt="version v3.3.0">
  <img src="https://img.shields.io/badge/license-MIT-a94736" alt="license MIT">
  <img src="https://img.shields.io/badge/platform-Windows%20x64-14201d" alt="platform Windows x64">
  <img src="https://img.shields.io/badge/website-live-0d1614" alt="website live">
  <img src="https://img.shields.io/badge/release-2026--10--23-1d2b27" alt="release 2026-10-23">
</p>

<p align="center">
  <a href="https://qiuizi.github.io/yijing-workbench-public/">官网</a> ·
  <a href="https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/yijing-workbench-3.3.0-x64-setup.exe">下载</a> ·
  <a href="https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/SHA256SUMS.txt">校验值</a> ·
  <a href="docs/release-notes-v3.3.0.md">文档</a>
</p>

本地优先的周易起卦工具：铜钱或手动起卦、卦辞爻辞原文阅读、六爻纳甲排盘与 64 卦图鉴全部本地完成，历史保存在本机 SQLite；可选 DeepSeek 解读，自备 Key、主动调用、可完全关闭，原文出处可溯。

项目官网：[中文](https://qiuizi.github.io/yijing-workbench-public/) · [English](https://qiuizi.github.io/yijing-workbench-public/en/)。

## 界面截图 (Screenshots)

<table>
  <tr>
    <td align="center"><img src="website/public/shots/workbench-result.png" alt="起卦结果" width="480"><br>起卦结果：本卦、动爻、之卦与传统取辞（v3.3.0 真实界面截图）</td>
    <td align="center"><img src="website/public/shots/learning-atlas.png" alt="64 卦图鉴" width="480"><br>64 卦图鉴：文王序浏览与检索（v3.3.0 真实界面截图）</td>
  </tr>
  <tr>
    <td align="center"><img src="website/public/shots/workbench-najia.png" alt="六爻纳甲排盘" width="480"><br>六爻纳甲排盘：干支、六亲、六神、世应与旬空（v3.3.0 真实界面截图）</td>
    <td align="center"><img src="website/public/shots/history.png" alt="历史记录" width="480"><br>历史记录：搜索、AI 筛选与分页（v3.3.0 真实界面截图）</td>
  </tr>
</table>

## 功能 (Features)

- 铜钱起卦：模拟三枚铜钱摇卦，记录每爻阴阳与动爻。
- 手动起卦：手动输入六爻并标注动爻。
- 传统取辞：按启蒙占法依据动爻取卦辞或爻辞，附原文与来源链接。
- 六爻纳甲：干支、旬空、六神、伏神、六亲、世应与变爻排盘。
- 64 卦图鉴与原文阅读：按文王序浏览、检索，逐卦阅读卦辞、爻辞及乾坤特殊爻（用九、用六）。
- 历史记录：占问关键词搜索、有 AI/无 AI 筛选、每页 20 条分页、单条 Markdown 导出。
- 可选 DeepSeek 解读：用户自备 API Key、主动调用，可完全关闭；离线不影响本地功能。

## 安装 (Install)

最新版本 v3.3.0（2026-10-23）。Windows x64 NSIS 安装包，当前用户安装，应用标识 `cn.yijing.workbench`：

- 安装包：[yijing-workbench-3.3.0-x64-setup.exe](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/yijing-workbench-3.3.0-x64-setup.exe)（16,096,623 bytes，15.4 MiB）
- 校验文件：[SHA256SUMS.txt](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/SHA256SUMS.txt)

下载后校验 SHA-256：

```powershell
Get-FileHash .\yijing-workbench-3.3.0-x64-setup.exe -Algorithm SHA256
```

期望值：

```text
0620A0497C76B25524275F21516F7D69A5AC2291BD362F8094F99E267693EBC8
```

前置条件：

- Windows x64。
- Microsoft Edge WebView2 Evergreen Runtime；缺失时安装程序需联网下载并运行官方 bootstrapper。

首次启动即可使用铜钱起卦、原文阅读、六爻纳甲与本地历史；AI 解读需在设置中填写自备的 DeepSeek API Key。升级前请先关闭应用并备份本机数据。

## 当前版本状态与风险 (Status & Risks)

**v3.3.0 已发布。** 打包源码提交为 `e5f613c5456cbd1dbb428c73bfb5234747133fb9`；Release Tag v3.3.0 仅额外包含发布文档与发布工作流，与二进制源码 SHA 不同。

已验证：

- Windows CI（[Run 39373256162](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39373256162)，push(main) 构建）：Windows 后端、前端、类型检查、VC143 运行库签名校验、PyInstaller sidecar、Tauri NSIS 打包均 PASS；打包后 sidecar 令牌鉴权/健康检查/64 卦目录/空白历史 smoke PASS。
- 本地源码回归：pytest 188 passed、Vitest 107 passed、TypeScript 与 Vite build 通过。
- 2026-10-23 轻量验收：与该源码一致的后端合成数据 21/21 PASS、DPAPI 合成密钥 5/5 PASS、源码 Vite GUI 功能测试 PASS；用户原有数据归位后逐文件哈希 0 差异。

未测试（未测试不等于通过）：

- 安装包本体的真实 Windows GUI 启动。
- 全新安装、从 v3.2.2 覆盖升级、卸载回滚的实机验收。
- 打包版的关于页、原生 Markdown 保存与重启持久化。

`manifest-rc.json` 中 `status=unsigned-rc-not-manually-accepted`、`gui_upgrade_tested=false` 原样保留；维护者是在上述安装包本体实机验收未完成的情况下明确接受风险后发布。安装包未签名，Windows 可能提示未知发布者或 SmartScreen；缺少 WebView2 Evergreen Runtime 的机器可能需要联网安装官方运行库。

需要更保守的选择时，可继续使用 [v3.2.2](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.2.2)。

完整验收与 NOT_TESTED 明细见 [docs/windows-rc-3.3.0-acceptance.md](docs/windows-rc-3.3.0-acceptance.md)。

## 技术架构 (Architecture)

| 层 | 技术 | 说明 |
| --- | --- | --- |
| 前端 | Vue 3.5 + TypeScript | 界面逻辑，位于 `frontend/` |
| 桌面壳 | Tauri | Windows 桌面窗口与原生能力，位于 `frontend/src-tauri/` |
| 后端 | FastAPI | 本地 HTTP 服务，以 sidecar 方式运行 |
| 数据库 | SQLite | 历史、AI 会话、设置与备份 |
| 打包 | PyInstaller + NSIS | 后端 sidecar 打包与 Windows 安装程序 |
| 官网 | Vite 6 + Vue 3.5 + TypeScript | 独立静态站点，位于 `website/`，由 GitHub Pages 自动部署 |

`website/` 与 `frontend/` 是两套独立的前端工程，互不影响。

## 仓库结构 (Repository Layout)

```text
.
├── frontend/             # Vue 3.5 + TypeScript 前端与 Tauri 桌面壳
├── backend/              # FastAPI 后端、64 卦数据与测试
├── website/              # 官网（Vite 6 静态站点，GitHub Pages）
├── scripts/              # 构建、打包与内容审核脚本
├── docs/                 # 文档与验收记录
├── .github/workflows/    # windows-rc.yml（桌面构建）、pages.yml（官网部署）、v1-learning-ci.yml（学习导读 CI）
├── LICENSE               # MIT（仅覆盖项目自有代码/测试/构建配置/原创图标）
├── PRIVACY.md            # 隐私与数据处理说明
└── THIRD_PARTY_NOTICES.txt
```

## 开发与测试 (Development & Tests)

Linux（Python 3.12、Node.js 24）：

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cd frontend && npm ci && cd ..

.venv/bin/python -m pytest
cd frontend
npm test
npm run typecheck
npm run build
```

Windows（Python 3.12、Node.js 24、Rust MSVC 工具链）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win.lock.txt
cd frontend
npm ci
cd ..

.\.venv\Scripts\python.exe -X utf8 -m pytest
cd frontend
npm test
npm run typecheck
```

官网：

```bash
cd website
npm ci
npm run dev     # 本地预览
npm run build   # 产出 dist/，由 .github/workflows/pages.yml 部署
```

测试数字出处：pytest 188 passed、Vitest 107 passed、TypeScript 与 Vite build 通过，来自与 v3.3.0 打包源码一致的本地源码回归；Windows 打包与 sidecar smoke 来自 [Run 39373256162](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39373256162)。

## 隐私与数据处理 (Privacy)

本地优先：起卦、原文、排盘与历史完全本地处理，不启用 AI 时不联网；AI Key 由当前 Windows 用户 DPAPI 保护，不回显给前端。DeepSeek 仅在用户主动调用时以 HTTPS Bearer 发送请求。详细范围见 [PRIVACY.md](PRIVACY.md)。

## 许可与数据来源 (License & Data Sources)

- [LICENSE](LICENSE) 为 MIT 许可，版权 `Copyright (c) 2026 Qiuizi`，只覆盖项目自有代码、测试、构建配置与原创图标，不覆盖古籍文本与第三方组件。
- 应用图标为原创几何图形，来源与生成方法见 [docs/icon-provenance.md](docs/icon-provenance.md)；官网品牌资产与视觉语言见 [website/public/brand/PROVENANCE.md](website/public/brand/PROVENANCE.md)。
- 卦爻辞转录自维基文库《周易》固定修订版，来源与核对记录见 [backend/data/README.md](backend/data/README.md)。
- 第三方组件许可见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。

## 更新记录 (Changelog)

v3.3.0（2026-10-23）：

- 新增 64 卦图鉴与原文阅读。
- 新增审核门控导读：64 卦现代导读均为 draft，仅 01–04 卦通过审核并在应用内可见，05–64 卦只显示经典原文与「导读整理中」，见 [docs/learning-approval-policy.md](docs/learning-approval-policy.md)。
- 新增单条 Markdown 导出。
- 历史记录新增搜索、AI 筛选与每页 20 条分页。
- 关于页正确显示版本、MIT 许可范围与 LICENSE 正文。
- 新增官网（GitHub Pages）。

详见 [Release](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.3.0) 与 [docs/release-notes-v3.3.0.md](docs/release-notes-v3.3.0.md)。

v3.2.2：上一稳定版本，见 [v3.2.2 Release](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.2.2)。

## 贡献与反馈 (Contributing)

问题与建议请在 [Issues](https://github.com/Qiuizi/yijing-workbench-public/issues) 提交。64 卦现代导读的审核进度见 [Issue #27](https://github.com/Qiuizi/yijing-workbench-public/issues/27) 与 [Issue #28](https://github.com/Qiuizi/yijing-workbench-public/issues/28)。改动请从 main 创建独立分支，提交 Pull Request 并等待人工审阅后合并。

---

v3.3.0 · 作者 Qiuizi · 版权 © 2026 Qiuizi · [MIT License](LICENSE)
