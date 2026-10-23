# Windows v3.3.1 构建计划与身份校验（2026-10-24）

**状态：待 GitHub Actions 真正运行与记录产物后填写。此文件不表示构建、Windows GUI 或升级已经验收通过。**

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
- 本 PR **不**创建 v3.3.1 Tag/正式 Release，**不**修改旧 v3.3.0 Release 资产；只有真正检查完候选文件哈希、manifest 和来源后才考虑正式发布。
- 若 GitHub Actions 尚在运行，需明确报告状态，不能虚构成功或安装包地址。
