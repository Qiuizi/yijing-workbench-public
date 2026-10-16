# 易经起卦工作台

**v3.2.2 已正式发布**：[公开源码仓库](https://github.com/Qiuizi/yijing-workbench-public) · [正式 Release](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.2.2) · [Windows x64 安装包下载](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.2.2/yijing-workbench-3.2.2-x64-setup.exe)。应用包括 Vue 3 / TypeScript 前端、FastAPI 本地后端、SQLite 历史记录、Tauri Windows 桌面应用及 PyInstaller sidecar。

功能包括铜钱起卦、手动起卦、卦辞爻辞阅读、六爻纳甲排盘、SQLite 历史记录、备份和可选 DeepSeek 辅助解读。DeepSeek AI 是可选联网功能，需用户自行配置并主动调用；起卦、阅读、排盘和本地历史可独立使用。数据处理范围见 [PRIVACY.md](PRIVACY.md)。

当前源码正在准备 **v3.3.0 发布候选**，包含单条 Markdown 导出、历史记录服务端搜索/AI 筛选/分页，以及“关于”页许可和版本信息修复。更新说明与最终验收范围见 [v3.3.0 发布说明草稿](docs/release-notes-v3.3.0.md)。v3.3.0 尚未发布安装包；上方下载链接仍指向已发布的稳定版 v3.2.2，其手工安装/升级验收不代表 v3.3.0 最终验收。

## 许可与数据来源

- `LICENSE` 中的 MIT 许可适用于 Qiuizi 有权授权的项目自有应用源码、自动化测试、构建配置及原创图标源文件与其生成的 Tauri 图标，版权声明为 `Copyright (c) 2026 Qiuizi`。该许可不覆盖古籍数据或第三方组件。
- 图标源文件 `frontend/src-tauri/icons-source/yijing-workbench.svg` 为项目原创几何图形，不使用第三方素材、图标库、模板或字体；来源与生成方法见 [`docs/icon-provenance.md`](docs/icon-provenance.md)。旧图标已从公开快照移除。
- 古籍文本数据的来源、修订链接与适用许可见 [`backend/data/README.md`](backend/data/README.md)。该说明针对所引用的维基文库文本，不为未确认的纸本底本作许可声明。
- 第三方软件和测试参考数据分别见 [`THIRD_PARTY_NOTICES.txt`](THIRD_PARTY_NOTICES.txt) 与 [`backend/tests/data/NOTICE.md`](backend/tests/data/NOTICE.md)，各自保留适用许可。

## v3.2.2 发布与验收状态

正式安装包基于公开源码提交 `e67770cc9a0e6b338aa1eed4f76174f6f41c32a5` 构建。应用标识沿用 Stable v3.2.0 的 `cn.yijing.workbench`，产品名为 `易经起卦工作台`，SQLite 数据继续使用同一应用数据目录。

正式 Release 记录后端 165/165、前端 44/44、TypeScript 类型检查及 x64 安装包构建通过。用户在隔离 Windows 测试账户完成最终 **6/6 手工验收**：安装 v3.2.0 并创建合成历史、升级到 v3.2.2、启动/起卦/排盘、历史保留及重启持久化、正常卸载，以及确认主账户 Stable v3.2.0 和真实数据不受影响。这是用户报告的手工 GUI、安装与升级验收，**不是自动化 GUI 测试**。

正式结果以 [Release 发布说明](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.2.2) 和随附 [manifest.json](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.2.2/manifest.json) 为准。[RC 构建与验收记录](docs/rc-3.2.2-acceptance.md) 保留早期构建时的 NOT_TESTED 等历史状态，不代表最终正式包的验收状态。

## 普通用户安装

下载 [v3.2.2 Windows x64 NSIS 安装程序](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.2.2/yijing-workbench-3.2.2-x64-setup.exe)，并核对 [SHA256SUMS.txt](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.2.2/SHA256SUMS.txt)。文件大小为 15,428,837 bytes，SHA-256 为：

    B594507662D2B0263D1909972211F26B088B26EA182065C96B54B53889AB9F8F

安装模式为当前用户；v3.2.0 → v3.2.2 升级及合成历史保留已由用户手工验收。NSIS 安装程序未签名，Windows 可能显示未知发布者或 SmartScreen 警告。若设备缺少 WebView2 Evergreen Runtime，安装需联网下载 Microsoft 官方 bootstrapper。

## Linux Cloud 开发与测试

日常开发以本公开仓库为源，从 `main` 创建独立分支，经过测试和 Pull Request 人工审阅后合并；不直接修改 `main` 或已发布 Tag/Release。

使用 Python 3.12、Node.js 24 和 npm 11。已配置的 Cloud 环境优先复用根目录 `.venv` 与 `frontend/node_modules`，不要重复安装。仅首次准备或依赖缺失时，在仓库根目录执行：

    python3.12 -m venv .venv
    .venv/bin/python -m pip install -r requirements.txt
    cd frontend
    npm ci
    cd ..

若虚拟环境由 uv 创建且不带 pip，可用 `uv pip install --python .venv/bin/python -r requirements.txt` 安装 Python 依赖。Linux 使用 `requirements.txt`；`requirements-win.lock.txt` 留给 Windows 构建。

从仓库根目录复核自动化测试：

    .venv/bin/python -m pytest
    cd frontend
    npm test
    npm run typecheck
    cd ..

v3.3.0 发布准备的 Linux 验证为后端 184 PASS、1 项 Windows DPAPI 测试 SKIP，前端 66 PASS，类型检查和前端生产构建 PASS。测试使用临时数据库和模拟 AI 服务，不需个人数据库或真实 API Key；不替代 Windows 构建、安装和升级验收。

开发时，在仓库根目录启动后端，使用独立的临时数据库：

    YIJING_DB_PATH="$(mktemp -d)/history.sqlite3" .venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

另一个终端在 `frontend` 目录执行 `npm run dev`；Vite 将 `/api` 代理到本地后端。健康检查为 `curl --fail http://127.0.0.1:8000/api/health`，预期返回 `{"status":"ok"}`。Cloud 中仅使用合成数据，不接入私人历史归档或真实 API Key。

Linux 无需 Windows SDK、MSVC 或 NSIS；Windows DPAPI、Tauri 桌面 GUI、安装、升级和卸载仍需 Windows 本地验收，不能由上述 Linux 测试代替。

## Windows 开发与构建

构建准备采用 Windows x64、Python 3.12.10、Node.js 24.14.0 / npm 11.9.0、Rust/Cargo 1.98.1。Node、Python、Rust 版本分别记录在 `frontend/.nvmrc`、`.python-version` 和 `frontend/src-tauri/rust-toolchain.toml`。npm、Cargo 与 Python 依赖分别由 `package-lock.json`、`Cargo.lock` 和 `requirements-win.lock.txt` 锁定。

需要 PowerShell 7、Visual Studio 2022 C++ Build Tools、NSIS、Rust MSVC 工具链，以及 Microsoft VC143 x64 CRT 可再发行文件。sidecar 构建会验证 VC runtime 的 Authenticode 签名及打包哈希。首次准备环境：

    py -3.12 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install -r requirements-win.lock.txt
    cd frontend
    npm ci
    cd ..

设置 `YIJING_VC_REDIST_DIR` 指向已安装的 Microsoft.VC143.CRT x64 目录，再从 `frontend` 目录执行：

    npm run desktop:build

NSIS 安装包生成于 `frontend/src-tauri/target/release/bundle/nsis/`。Tauri 默认使用 `downloadBootstrapper`：若设备缺少 WebView2 Evergreen Runtime，安装程序需要联网下载并运行 Microsoft 官方 bootstrapper。最终正式构建还应记录 Windows SDK、MSVC/VC143 CRT 文件哈希、NSIS 与构建工具版本，并生成与源码提交对应的 SHA-256 manifest。

## 测试

    .\.venv\Scripts\python.exe -X utf8 -m pytest
    cd frontend
    npm test
    npm run typecheck

数据来源、许可与第三方组件见 `backend/data/README.md`、`LICENSE` 和 `THIRD_PARTY_NOTICES.txt`。本地与联网数据处理见 `PRIVACY.md`。

## 许可

`LICENSE` 授权项目自有应用源码、自动化测试、构建配置及来源记录中的原创 SVG 和其生成图标。古籍数据与第三方依赖分别适用 `backend/data/README.md` 和 `THIRD_PARTY_NOTICES.txt` 中列明的条款。
