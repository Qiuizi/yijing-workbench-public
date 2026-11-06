# KNOWN-ISSUES — 未修复问题清单

> 冻结期间**不修复**任何问题。本清单用于恢复后按优先级处理。
> 严重度：**P0** 阻断/数据不可用；**P1** 高，影响发布或正式链路；**P2** 中，可用性/体验/测试缺口；**P3** 低，清理与文档。

## P0 — 阻断

### P0-1 v3.3.2 正式安装包缺失主程序

- **现象**：公开的 `yijing-workbench-3.3.2-x64-setup.exe`（13,469,345 B，`bda356af…d999`）只含 `verify-updater-signature.exe` 与 sidecar，**没有 `yijing-workbench.exe`**。全新安装退出码 0 但无法启动；v3.3.1 覆盖升级到 v3.3.2 后主程序消失。
- **影响**：最新正式版本实际不可用；所有从 v3.3.1 升级到 v3.3.2 的用户受影响。
- **根因**：新增第二个 `[[bin]]` 后未设置 `default-run`，Tauri 打包选错 bin。
- **现状**：修复已合入 main（PR #61 `c851e50`、PR #62 `b9e2fad`），**但未发布**。
- **证据**：`docs/qa/post-release-qa-3.3.2.md`。
- **恢复后动作**：不要继续分发 v3.3.2；先发布含修复的版本，并更新官网入口。受影响用户按 `docs/updater/README.md` §9 人工恢复（关闭应用、恢复备份、重装可用版本；**不要删除** `%LOCALAPPDATA%\cn.yijing.workbench`）。

## P1 — 高

### P1-1 v3.3.3 已构建并通过 Candidate 验收，但从未正式发布

- **现象**：无 `v3.3.3` Tag / Release；生产签名演练 Run `42033806115` 在冻结时被取消；无正式签名产物。
- **影响**：修复未到达用户；正式发布链路未端到端验证。
- **证据**：[RELEASE-HISTORY.md](RELEASE-HISTORY.md) §5；[evidence/cancelled-production-run.json](evidence/cancelled-production-run.json)。
- **恢复后动作**：先完成生产签名 dry-run 演练并核对签名 Key ID = `5D79EDB98FE951FF`，再按 [RECOVERY-GUIDE.md](RECOVERY-GUIDE.md) 发布。

### P1-2 正式生产签名链路下的 3.3.2 → 3.3.3 应用内升级未验证

- **现象**：应用内升级只在「重建 QA 基线 + 临时 QA 密钥 + 本地 HTTP」下 PASS；正式链路 NOT_RUN。
- **证据**：[QA-ACCEPTANCE.md](QA-ACCEPTANCE.md) §4。
- **恢复后动作**：发布后用真实正式签名包做一次真实用户路径升级验证（隔离账户、合成数据）。

### P1-3 正式签名材料的离线备份无法核实

- **现象**：`SIGNING_BACKUP_UNVERIFIED`；外置磁盘未连接，无法确认加密归档存在且与口令分离。
- **证据**：[SECURITY-INVENTORY.md](SECURITY-INVENTORY.md) R-1。
- **恢复后动作**：接入外置磁盘核验归档与口令分离；在此之前不要触发任何正式发布。

## P2 — 中

| ID | 问题 | 证据 | 备注 |
| --- | --- | --- | --- |
| P2-1 | 升级后「关于」页显示 `V3.3.2`，实际运行时为 3.3.3 | reconstruct `evidence/upgrade-timeline.txt` 第 14 行 | 目标包沿用旧前端硬编码；需修版本来源 |
| P2-2 | 更新网络错误直接显示英文原文（`error sending request for url (...)`） | `ACCEPTANCE-REPORT.md` §G | 本地化缺失 |
| P2-3 | Sidecar 启动失败时无全局提示/重试，首次起卦才暴露 | `ACCEPTANCE-REPORT.md` §G P2-1 | v3.3.3 未重测，沿用 v3.3.2 证据 |
| P2-4 | `requireSignedVersion` 未启用 | `ACCEPTANCE-REPORT.md` §G P2-3 | 更新器安全加固项 |
| P2-5 | 缺少逐 schema 版本的数据库迁移矩阵 | `QA-ACCEPTANCE.md` #7 | 仅有跨升级数据保留证据 |
| P2-6 | DPAPI 跨 Windows 用户隔离未测试 | `QA-ACCEPTANCE.md` #9b | 历史文档明确未测 |
| P2-7 | 干净系统缺少 WebView2 的安装/失败矩阵未测试 | `QA-ACCEPTANCE.md` #6b | 仅验证已有 runtime |
| P2-8 | AI 真实 Key 成功联网流未测试（只测了无效 Key 失败路径） | `QA-ACCEPTANCE.md` #5、`docs/qa/post-release-qa-3.3.2.md` | — |
| P2-9 | 历史 v3.3.2 UpdaterQA 基线从未寻获，本次升级测试依赖**重建**基线 | `.qa-work/v3.3.3/inapp-332/BLOCKED-report.md` | 流程缺口：正式基线应随发布归档 |
| P2-10 | 私钥口令文件与私钥同目录 | `SECURITY-INVENTORY.md` R-2 | 口令应移入密码管理器 |

## P3 — 低

| ID | 问题 | 证据 |
| --- | --- | --- |
| P3-1 | `README.md` 顶部徽章仍写 `version-v3.3.1`、下载链接指向 v3.3.1（正文状态段也停在 v3.3.1） | `README.md` 第 8–20、51–84 行 |
| P3-2 | 官网下载入口仍指向 v3.3.2（有 P0 缺陷包） | [evidence/website-observation.json](evidence/website-observation.json) |
| P3-3 | `docs/review/ui-audit*` 三个未跟踪目录遗留（含 node_modules 备份） | [PROJECT-STATUS.md](PROJECT-STATUS.md) §1.2 |
| P3-4 | 26 个本地分支 + 10 个附加 worktree 长期未清理 | [PROJECT-STATUS.md](PROJECT-STATUS.md) §1.1 |
| P3-5 | GitHub Actions Artifacts 普遍 14 天到期（2026-11-13 至 11-19），过期后仅能依赖本地归档 | [evidence/artifacts.json](evidence/artifacts.json) |
| P3-6 | `frontend/src-tauri/Cargo.toml` 的 stat-dirty 假阳性会干扰 `git status` 阅读 | [PROJECT-STATUS.md](PROJECT-STATUS.md) §1.2 |
| P3-7 | Actions 未启用 SHA pinning | `SECURITY-INVENTORY.md` R-5 |

## 测试证据的「不可混用」提醒

- `docs/updater/qa-upgrade-report.md`（2026-10-27，3.3.2-qa.1→qa.2，22/22 PASS）对当前 3.3.2→3.3.3 属于 **STALE**，不得引用为当前结论。
- v3.3.2 发布后 QA 的 PASS 项不能覆盖其 P0 FAIL。
- Candidate 的 PASS 均为**临时 Candidate 签名**，不能当作正式签名验证。
