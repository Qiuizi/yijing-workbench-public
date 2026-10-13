# 易经起卦工作台

正式版本准备基于已完成 RC 3.2.2 用户报告 6/6 手工 GUI 验收的源码。应用包括 Vue 3 / TypeScript 前端、FastAPI 本地后端、Tauri Windows 桌面配置、PyInstaller sidecar 构建脚本、锁定依赖及核心自动化测试。

功能包括铜钱起卦、手动起卦、卦辞爻辞阅读、六爻纳甲排盘、SQLite 历史记录、备份和可选 DeepSeek 辅助解读。AI 是可选联网功能；起卦、阅读、排盘和本地历史可独立使用。

## 许可与数据来源

- `LICENSE` 中的 MIT 许可仅适用于 Qiuizi 有权授权的项目自有应用源码、自动化测试和构建配置，版权声明为 `Copyright (c) 2026 Qiuizi`。该许可不覆盖古籍数据、第三方组件或下述图标素材。
- RC 快照中的历史 Tauri 图标位于 `frontend/src-tauri/icons/`。Git 提交身份不能证明素材权利；该快照没有对应的原始图形源文件，因此这些图标不纳入 MIT 授权，公开分发前仍须确认权利或经授权替换。
- 古籍文本数据的来源、修订链接与适用许可见 [`backend/data/README.md`](backend/data/README.md)。该说明针对所引用的维基文库文本，不为未确认的纸本底本作许可声明。
- 第三方软件和测试参考数据分别见 [`THIRD_PARTY_NOTICES.txt`](THIRD_PARTY_NOTICES.txt) 与 [`backend/tests/data/NOTICE.md`](backend/tests/data/NOTICE.md)，各自保留适用许可。

## 发布准备状态

源码版本为 3.2.2，正式应用标识沿用 Stable v3.2.0 的 `cn.yijing.workbench`，产品名为 `易经起卦工作台`。SQLite 数据继续使用同一应用数据目录；3.2.2 与 v3.2.0 基线的数据库迁移模块一致。公开前仍须解决历史图标素材权利，并在隔离 Windows 环境实装最终包，验证安装、启动和数据兼容。尚未创建公开仓库或 GitHub Release。

RC 3.2.2 GUI 6/6 为用户报告结果；构建时 manifest 记录的 GUI 与安装/启动状态仍为 NOT_TESTED。时间顺序和记录范围见 [docs/rc-3.2.2-acceptance.md](docs/rc-3.2.2-acceptance.md)。

## 普通用户安装

正式安装包尚未发布。发布后，从 GitHub Releases 下载 Windows x64 安装程序并核对发布页 SHA-256。NSIS 安装程序未签名，Windows 可能显示未知发布者或 SmartScreen 警告。安装模式为当前用户；已有 v3.2.0 安装记录使用 `%LOCALAPPDATA%\Programs\YijingWorkbench-V3.1`，正式包覆盖该目录的行为仍须用最终包验证。若设备缺少 WebView2 Evergreen Runtime，安装需联网下载 Microsoft 官方 bootstrapper。

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

`LICENSE` 仅授权项目自有应用源码、自动化测试和构建配置。古籍数据与第三方依赖分别适用 `backend/data/README.md` 和 `THIRD_PARTY_NOTICES.txt` 中列明的条款；历史图标 `frontend/src-tauri/icons/` 不在 MIT 授权范围内，来源与分发权待确认。
