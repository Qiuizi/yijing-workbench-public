# Yijing Workbench — 项目冻结说明（Project Freeze）

- 项目：易经起卦工作台（Yijing Workbench）
- 仓库：`Qiuizi/yijing-workbench-public`
- 冻结时间：2026-11-06（北京时间，审计快照见 [evidence/audit-time.json](evidence/audit-time.json)）
- 冻结时 Git SHA：`932f0390bdee79068b955f16b0f82cebc56b1ce5`（`main`，提交时间 2026-11-05T02:31:43Z）
- 当前正式发布版本：**v3.3.2**（公开 Release，2026-11-02 发布；但该版本安装包存在 P0 缺陷，见下）
- 当前 Candidate：v3.3.3（Artifact `13383072964`，临时 Candidate 签名，**未发布**）
- 冻结结论：**PROJECT_FROZEN_WITH_WARNINGS**

## 这是什么

项目暂时停止开发，进入冻结状态。这不是删除或放弃项目，而是一次正式的阶段性结项：代码、分支、PR、Release、构建产物、QA 证据和签名材料全部**原地保留**，并在此目录留下可长期复查的状态记录。

本轮**没有**开发新功能、修复缺陷、构建、安装、重跑测试、创建 Tag/Release 或提交推送。唯一的远端写操作是：按冻结授权**取消**了一个仍在等待人工审批的生产签名演练工作流（Run `42033806115`，结果 `cancelled`），因为它属于「尚未完成的发布任务」，冻结期间不得批准或继续。

## 为什么状态是 `PROJECT_FROZEN_WITH_WARNINGS`

冻结本身已完成，但存在**四项必须让未来维护者先看到**的警告：

1. **v3.3.2 正式安装包不可用（P0）**：公开 Release 的 `yijing-workbench-3.3.2-x64-setup.exe` 缺失主程序，只打包了签名校验器和 sidecar。安装后无法启动，v3.3.1 覆盖升级到 v3.3.2 还会导致主程序消失。修复已在 PR #61、#62 合入 main，但**没有发布新版本**。官网下载入口仍指向这个有缺陷的 v3.3.2。
2. **v3.3.3 已构建、已通过 Candidate 验收，但没有正式发布**：没有 v3.3.3 Tag、没有公开 Release；正式签名演练在冻结时被取消，因此**正式签名产物从未生成**。
3. **正式签名材料的离线备份无法核实**：`SIGNING_BACKUP_UNVERIFIED`。本机存在正式私钥与口令文件，但外置磁盘当前未连接，无法确认加密归档存在、且归档与口令分离保管。
4. **应用内更新测试的结论有边界**：v3.3.2 → v3.3.3 的应用内升级已在**重建的 QA 身份 + 临时 QA 密钥 + 本地 HTTP** 下真实跑通（PASS），但**正式生产签名链路下的 3.3.2 → 3.3.3 升级为 NOT_RUN**，不能把 QA 结论当作正式发布验证。

## 文档目录（恢复入口）

| 文件 | 内容 |
| --- | --- |
| [PROJECT-STATUS.md](PROJECT-STATUS.md) | 项目整体状态、技术栈、已实现/未完成功能 |
| [RELEASE-HISTORY.md](RELEASE-HISTORY.md) | v3.2.2 / v3.3.0 / v3.3.1 / v3.3.2 / v3.3.3 的真实发布情况 |
| [QA-ACCEPTANCE.md](QA-ACCEPTANCE.md) | 完整 QA 验收矩阵、证据路径、Run ID、对应 SHA |
| [SECURITY-INVENTORY.md](SECURITY-INVENTORY.md) | 密钥、签名、权限、备份与安全风险（不含任何私钥或口令） |
| [KNOWN-ISSUES.md](KNOWN-ISSUES.md) | 未修复问题，按 P0–P3 分类 |
| [RECOVERY-GUIDE.md](RECOVERY-GUIDE.md) | 未来恢复项目的完整操作步骤与发布前检查清单 |
| [FREEZE-MANIFEST.json](FREEZE-MANIFEST.json) | 机器可读冻结清单（SHA、Release、PR、Artifact、Run、QA、密钥指纹、未完成项） |
| [evidence/](evidence/) | 本轮审计的原始元数据、哈希清单、Git 快照、流程与站点观测 |

## 恢复入口（最短路径）

```powershell
git clone https://github.com/Qiuizi/yijing-workbench-public.git
cd yijing-workbench-public
git checkout 932f0390bdee79068b955f16b0f82cebc56b1ce5   # 冻结 SHA
```

然后按 [RECOVERY-GUIDE.md](RECOVERY-GUIDE.md) 操作。**恢复后的第一件事不是继续开发，而是先阅读 [KNOWN-ISSUES.md](KNOWN-ISSUES.md) 的 P0/P1，并确认签名材料与产物备份。**

## 构建产物与本地归档

- 所有 4 个公开 Release 的全部资产（25 个文件）已下载并按 GitHub 记录的 `sha256` 逐一校验，**25/25 通过**。
- 全部 166 个未过期 Actions Artifact 已下载并校验，**166/166 通过**；合计 **191/191** 个远端产物在本地归档。
- 归档位置：`.qa-work/project-freeze-20261106/remote-archives/`（约 1.2 GB，保留在 `.qa-work/` 内，未纳入 Git）。
- 校验记录：[evidence/remote-preservation.json](evidence/remote-preservation.json)（每项的 `sha256`、`size`、`status`）。
- 关键产物：v3.3.3 Candidate `13383072964`（`f5481c1c…3fc00`）、生产签名演练 staging `13418007574`（`8af63639…995ea`）、v3.3.2 signed `13160435971`（`36284ecd…da46`）。
- 注意：这些 GitHub Artifact 会在 2026-11-13 至 11-19 之间陆续到期，本地归档是主要可恢复副本。

## 本目录文件校验

各文档与清单的 SHA-256 见 [SHA256SUMS.txt](SHA256SUMS.txt)；冻结清单同时内嵌文档哈希。

## 冻结状态

- 开发：已停止
- 构建：已停止
- Candidate：不再触发
- Release：不再触发
- 正式签名配置：未修改
- 官网：未修改
- 提交 / 推送：冻结时未执行；2026-11-06 晚经维护者授权，结项文档推送至分支 `docs/project-freeze-20261106` 并开 PR（见 [CLEANUP-REPORT.md](CLEANUP-REPORT.md)）
- `.qa-work/`：证据、报告、安装包、数据库与 1.2 GB 产物归档全部保留；可重建缓存与临时安装/解包副本已按授权清理（详见 [CLEANUP-REPORT.md](CLEANUP-REPORT.md)）
- 已有分支、Artifact、Release、Tag、密钥：全部保留

> 除非维护者未来明确要求恢复，否则不要继续推进任何 Phase。
