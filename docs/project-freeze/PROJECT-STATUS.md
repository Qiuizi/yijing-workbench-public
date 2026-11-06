# PROJECT-STATUS — 项目整体状态

> 观测时间：2026-11-06（详见 [evidence/audit-time.json](evidence/audit-time.json)）
> 所有结论以 GitHub 实时状态与本地实际状态为准；原始数据见 [evidence/](evidence/)。

## 1. 仓库与 Git

| 项目 | 值 |
| --- | --- |
| 仓库 | `Qiuizi/yijing-workbench-public`（公开） |
| 默认分支 | `main` |
| 冻结时 main SHA | `932f0390bdee79068b955f16b0f82cebc56b1ce5` |
| main 提交信息 | `release: prepare v3.3.3 installer packaging fix (#62)` |
| main 提交时间 | 2026-11-05T02:31:43Z |
| 本地 main 与 origin/main | 一致（`+0 -0`） |
| 本地分支数 | 26 |
| 远程跟踪引用数 | 52（`origin/*`） |
| 远端分支数（`git ls-remote --heads`） | 51 |
| Tag | 4 个：`v3.2.2`、`v3.3.0`、`v3.3.1`、`v3.3.2`（无 `v3.3.3`） |
| Worktree | 11 个（主工作区 1 + 附加 10） |
| 打开的 PR | 0 |
| 打开的 Issue | #27（Windows 隔离账户安装升级与 GUI/DPAPI 最终验收）、#28（64 卦逐卦审批） |

### 1.1 Worktree 清单

主工作区：`D:\Qiuizi\project\yijing`（main）。

附加 worktree：

| 路径 | HEAD | 说明 |
| --- | --- | --- |
| `.qa-work/v3.3.3/inapp-332/reconstruct-332/worktree` | `8e42390`（detached） | 重建 v3.3.2 QA 基线用的构建树 |
| `.qa-work/v3.3.3/runner-wt` | `8153f2c`（`qa/v3.3.3-candidate-acceptance`） | QA 验收分支 |
| `.workbuddy/post-release-qa/worktree-v3.3.2` | `a4982e0`（detached） | v3.3.2 发布后 QA 树 |
| `D:\Qiuizi\project\yijing-cicd-v2-phase1` | `f776c91`（`refactor/cicd-v2-shared-build-actions`） | CI 重构 |
| `D:\Qiuizi\project\yijing-cicd-v2-phase2` | `9fa1a6b`（`feat/cicd-v2-artifact-provenance`） | Artifact 来源 |
| `D:\Qiuizi\project\yijing-cicd-v2-phase3` | `05485d0`（`fix/release-sign-provenance`） | 签名来源 |
| `D:\Qiuizi\project\yijing-disable-legacy-331` | `9ea6da7`（`chore/disable-legacy-v3.3.1-publish`） | 禁用旧发布流 |
| `D:\Qiuizi\project\yijing-publish-gate` | `6b8a267`（`docs/release-notes-v3.3.2`） | 发布门禁 |
| `D:\Qiuizi\project\yijing-release-publish` | `371a26a`（`fix/release-draft-lookup`） | 发布草稿查询 |
| `D:\Qiuizi\project\yijing-site` | `61f0a7e`（`release/site-v3.3.2`） | 官网 v3.3.2 下载入口 |

### 1.2 未提交修改与未跟踪文件

**结论：没有需要抢救的未提交代码改动。**

- `git status` 唯一报告的已修改文件是 `frontend/src-tauri/Cargo.toml`（`.M`）。但工作区字节内容与 `HEAD` 完全一致（`git hash-object --no-filters` = `366906a0…103c` = HEAD blob），属于文件系统时间戳引起的 **stat-dirty 假阳性**，不是真实改动。快照仍已保存：`evidence/worktree-1-Cargo.toml.snapshot`。
- 其余 worktree 的 `Cargo.toml` 出现「worktree blob ≠ HEAD blob」的，均为 **CRLF/LF 归一化差异**，`git status` 干净，无内容改动。
- 未跟踪目录（清理后仍保留、未删除）：
  - `.workbuddy/`（发布后 QA 记录与 memory）
  - `docs/review/ui-audit/`（UI 审计证据截图与报告）
  - `docs/project-freeze/`（本结项目录，属本轮新增）
- 2026-11-06 晚经授权删除了 `docs/review/ui-audit-node-modules-backup/`、`docs/review/ui-audit-vite-cache-backup/` 两个纯缓存备份目录，以及可重建的 `node_modules`/`.venv`/`target`/临时安装目录；详见 [CLEANUP-REPORT.md](CLEANUP-REPORT.md)。
- 完整清单：[evidence/untracked-files.json](evidence/untracked-files.json)、[evidence/git-audit.json](evidence/git-audit.json)。

## 2. 技术栈

| 层 | 技术 | 位置 |
| --- | --- | --- |
| 前端 | Vue 3.5 + TypeScript + Element Plus | `frontend/` |
| 桌面壳 | Tauri 2（crate 2.11.6 / CLI 2.11.5） | `frontend/src-tauri/` |
| 后端 | FastAPI（PyInstaller 打包为 sidecar） | `backend/` |
| 数据库 | SQLite（历史、AI 会话、设置、备份） | 应用数据目录 |
| 打包 | PyInstaller + NSIS（currentUser 安装） | `scripts/`、`frontend/src-tauri` |
| 官网 | Vite 6 + Vue 3.5，GitHub Pages | `website/` |
| 发布 CI | GitHub Actions（build → verify → sign → attest → publish） | `.github/workflows/release.yml` |

工具链（发布流水线固定）：Python 3.12、Node.js 24、Rust 1.98.1（`.github/actions/setup-windows-toolchain`）。

## 3. 已实现功能

- 铜钱起卦、手动起卦、传统取辞（按动爻取卦辞/爻辞）
- 六爻纳甲排盘（干支、旬空、六神、伏神、六亲、世应、变爻）
- 64 卦图鉴与原文阅读（文王序、检索、乾坤用九用六）
- 历史记录：关键词搜索、AI/无 AI 筛选、每页 20 条分页、单条 Markdown 导出
- 可选 DeepSeek 解读（自备 Key、DPAPI 保护、可完全关闭）
- 应用内自动更新（v3.3.2 起）：24 小时节流检查、手动检查、下载进度、minisign 签名校验、安装前 SQLite 一致性备份、安装后重启
- 发布工程化：候选构建与正式发布分离、不可变 Artifact 来源证明、SHA 固定、Attestation 门禁、官网仅开 PR

## 4. 版本状态

| 项 | 状态 |
| --- | --- |
| 当前正式版本 | **v3.3.2**（最新公开 Release；安装包 P0 缺陷不可用，见下） |
| 前一个可用正式版本 | v3.3.1（安装包完整，但无更新器） |
| 仓库版本号（main） | `3.3.3`（`package.json`、`tauri.conf.json`、`Cargo.toml` 一致） |
| 当前 Candidate | v3.3.3，Artifact `13383072964`，Build Run `41955823250`，临时 Candidate 签名 |
| v3.3.3 发布状态 | **未发布**：无 Tag、无 Release、无正式签名产物 |

## 5. 尚未完成的功能与工作

1. **v3.3.3 正式发布**：安装包打包缺陷已修（PR #61/#62），但生产签名演练在冻结时被取消，正式发布从未执行。
2. **v3.3.2 用户补救**：现有 v3.3.2 用户（含从 v3.3.1 升级后主程序丢失者）需要人工恢复，见 [KNOWN-ISSUES.md](KNOWN-ISSUES.md) P0 与 `docs/updater/README.md` §9。
3. **完整数据库迁移矩阵**：只有「跨升级数据保留」的证据，缺少逐 schema 版本的迁移成功/失败回退测试。
4. **DPAPI 跨 Windows 用户隔离**：未测试。
5. **干净系统缺少 WebView2 时的安装/失败矩阵**：未测试（仅验证已有 runtime 的情况）。
6. **AI 成功联网流**：只用无效 Key 测试了失败路径，真实 Key 成功调用未测试。
7. **`requireSignedVersion`**：未启用（P2）。
8. **正式生产签名链路下的 3.3.2 → 3.3.3 应用内升级**：NOT_RUN。

## 6. 仓库健康度观察

- main 与 origin 同步，无中断的进行中发布（唯一等待审批的 Run 已按冻结授权取消）。
- 长期存在的功能分支与 worktree 较多（26 个本地分支、10 个附加 worktree），冻结时**全部保留**，未来清理需单独评审后再做。
- 最近一次 main 上的 UI 审计临时目录（`docs/review/*`）未纳入版本控制，属历史遗留，未清理。

