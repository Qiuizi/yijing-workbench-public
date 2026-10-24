# Windows v3.3.1 构建计划与身份校验（2026-10-24）

**当前状态（2026-10-24）：Windows main push 构建、独立 SHA-256 校验及 v3.3.1 正式 Release 已完成。实际 Windows 安装、覆盖升级、原生文件保存与打包 GUI 仍是 NOT_TESTED。**

## 为什么需要新版本

- 2026-10-24 [PR #35](https://github.com/Qiuizi/yijing-workbench-public/pull/35) 已将 05–64 卦 `review_status` 切换为 `reviewed` 并在 `learning_approvals.json` 登记批准，连同此前 01–04 卦：**64/64 编辑发布批准**，零 `draft`。
- 2026-10-23 发布的 [v3.3.0](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.3.0) 仍使用 `e5f613c` 旧构建，只有 01–04 卦现代导读可见；不可重用原 v3.3.0 安装包或为其改名。
- 本次只同步 7 个必需版本字段与 Windows 候选 CI，构建 **v3.3.1**（包含 64 卦导读）。v3.3.0 正式 Release、网站下载链接、其原校验值全部保持不变。未完成古籍版本学全量核读的风险见 [批准说明](learning-guides-review-05-64.md)。

## 更新范围和校验

| 配置 | 新版本 |
| --- | --- |
| frontend/package.json | 3.3.1 |
| frontend/package-lock.json（root、packages[""]） | 3.3.1 |
| frontend/src-tauri/tauri.conf.json | 3.3.1 |
| frontend/src-tauri/Cargo.toml | 3.3.1 |
| frontend/src-tauri/Cargo.lock（package=yijing-workbench） | 3.3.1 |
| backend/main.py（FastAPI） | 3.3.1 |
| .github/workflows/windows-rc.yml（名称、NSIS 版本门槛、Manifest、Artifact） | 3.3.1 |

从 **合并到 main 的真实 push** 触发 Windows runner，且仅在以下全部通过时可称候选完成：

- pytest、Vitest、typecheck、前端生产构建 PASS；
- Windows x64 Tauri NSIS 打包与 PyInstaller sidecar 完成，打包 sidecar 使用合成数据做启动/鉴权冒烟；
- manifest 的 source_sha 精确指向 `main` push 合并提交，`source_trigger=push`、`source_ref=refs/heads/main`、`version=3.3.1`；
- Manifest 记录真实安装包 filename、bytes、SHA256，与 Artifact 中实际文件一致；
- 前端 `reviewedGuide(5)`、`reviewedGuide(64)` 与 64 条台账的双重门控回归通过。

## 阻碍和后续

- CI 不替代实机 GUI、覆盖升级、卸载、原生 Markdown 文件保存或 DPAPI 跨账户验收；未做的要标 NOT_TESTED。
- 原构建 PR **并未**创建 Tag/Release；之后独立核验候选字节、Manifest 和来源后，才由 [PR #37](https://github.com/Qiuizi/yijing-workbench-public/pull/37) 的受控工作流正式发布 v3.3.1。旧 v3.3.0 Release 资产未修改。
- 若 GitHub Actions 尚在运行，需明确报告状态，不能虚构成功或安装包地址。

## 2026-10-24 独立验收和 Release 结果

| 项目 | 核实结果 |
| --- | --- |
| main push 源码 SHA | `f6f102f1f87bcc6aebba0ad7eac822ad9b25e882` |
| Windows runner | [Run 39995846568](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39995846568)，completed/success |
| Artifact | `yijing-workbench-3.3.1-windows-x64-unsigned-rc`，ID `12520670700` |
| 原始 NSIS EXE | `易经起卦工作台_3.3.1_x64-setup.exe`，**16,097,113 bytes** |
| 安装包 SHA-256 | `3CAECBE2CE7684805BA5FBE2D8F60767101CCD71565A4EC37BACB2181B086B74` |
| 独立复核 | 下载原始 GitHub Actions ZIP 后重新提取 EXE 计算，与 `manifest-rc.json` 内 SHA-256 完全相同 |
| 原始 Manifest 来源 | version=3.3.1，source_trigger=push，refs/heads/main，sidecar_smoke=PASS，gui_upgrade_tested=false |
| 正式发布工作流 | [Run 40058914967](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/40058914967)，completed/success |
| 最新 Release | [v3.3.1](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.3.1)，正式、非预发布 |
| 发布资产 | 5 个文件，安装程序资产 digest 与原 EXE SHA-256 一致 |
| 尚未完成 | 实机安装/升级/卸载、打包版 GUI/重启、原生 Markdown 保存、DPAPI 跨账户 |

正式 Release 的 EXE 仅将原 CI 中文文件名更改为 ASCII 的 `yijing-workbench-3.3.1-x64-setup.exe`，文件内容不变。最初的 `manifest-rc.json` 中状态 `unsigned-rc-not-manually-accepted` 按实际自动化验收范围保留，**不意味着后来补做了实机验收**。
