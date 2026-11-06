# QA-ACCEPTANCE — 完整 QA 验收矩阵

> 证据来源均为**本地已存在的历史真实运行记录**，本轮**未重跑、未重建、未安装**。
> 状态严格区分：**PASS**（有实际执行证据）/ **FAIL**（有实际失败证据）/ **BLOCKED**（明确阻断）/ **NOT_RUN**（没有执行）/ **STALE**（证据过期或对应旧 SHA）。

## 0. 结论摘要

- v3.3.3 Candidate 的**来源、NSIS 内容、官方安装/启动/GUI/卸载、Sidecar API、数据保留**：**PASS**（签名性质为临时 Candidate）。
- **v3.3.2 → v3.3.3 应用内升级**：**PASS**，但证据来自**重建的 QA 基线 + 临时 QA 密钥 + 本地 HTTP**；历史正式 v3.3.2 UpdaterQA 基线**确实不存在**（已确认事实）。
- **正式生产签名链路下的 3.3.2 → 3.3.3 应用内升级**：**NOT_RUN**。
- v3.3.2 正式安装包：**FAIL（P0）**。

> 因此本轮**不**使用 `IN_APP_UPDATER_QA_NOT_COMPLETED` 标记：重建基线及升级测试已经真实完成并通过（见 §4）。该代码保留给「未完成」的情况，本次不适用。但必须同时记录其**范围限制**：它不是生产签名链路的验证。

## 1. 主验收矩阵

| # | 测试项 | 状态 | 证据（相对仓库根） | Run / 产物 | 对应 SHA |
| --- | --- | --- | --- | --- | --- |
| 1 | v3.3.2 安装包缺失调查（正式 Release） | **FAIL（P0）** | `docs/qa/post-release-qa-3.3.2.md` | 正式资产 `bda356af…d999`（13,469,345 B） | Tag `a4982e0`；构建 Run `41479457847` |
| 2 | v3.3.3 Candidate 独立核验（按 Artifact ID 下载、来源与签名） | **PASS** | `.qa-work/v3.3.3/ACCEPTANCE-REPORT.md`；`.qa-work/v3.3.3/reverify-live/reverify-summary.json`；`reverify-result.json`；`sidecar-smoke-candidate-attestation.json` | Artifact `13383072964`；Run `41955823250` attempt 1 | `932f039…b1ce5`；ZIP `f5481c1c…3fc00` |
| 3 | NSIS 安装包内容检查 | **PASS** | `.qa-work/v3.3.3/evidence/candidate-nsis-contents.json` | 747 项；主程序 + sidecar；无校验器 | 安装包 `0bedceaa…12a38` |
| 4 | 官方 Candidate 真实 Windows 安装 / 启动 / GUI / 退出 / 卸载 | **PASS** | `.qa-work/v3.3.3/runner-evidence2/extracted/result.json` | Run `42032346331`；证据 Artifact `13415419891` | 主程序 `6f61808d…6bfff`，FileVersion 3.3.3 |
| 5 | Sidecar 测试（API/鉴权/备份/WAL/DPAPI 当前用户） | **PASS** | `.qa-work/v3.3.3/evidence/api-sidecar-results.json`（37/37 ok=true） | 官方 Candidate 包内 Sidecar | sidecar `cc88f977…75948` |
| 6 | WebView2 测试（已有运行时下载入） | **PASS**（范围受限） | 同 #4（`Edg/131.0.2903.86`，CDP 页面就绪） | Run `42032346331` | 同上 |
| 6b | 干净系统缺少 WebView2 的安装/失败矩阵 | **NOT_RUN** | 未见证据 | — | — |
| 7 | 数据库迁移（逐 schema 版本矩阵） | **NOT_RUN** | 仅有 `schema_migrations` 4/4 计数一致（见 #5），不足以构成迁移矩阵 | — | — |
| 8 | SQLite 备份与恢复 | **PASS** | `.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/failures-timeline.txt`（backup-restore 10/10、integrity ok）；`.qa-work/v3.3.2/evidence/recovery-results.json`（6/6） | 重建 QA 会话 2026-11-05T17:56Z | 备份 `2afd8820…fb460`（147,456 B） |
| 9 | DPAPI 测试（同一 Windows 用户加解密） | **PASS** | `.qa-work/v3.3.3/evidence/api-sidecar-results.json`；reconstruct `upgrade-after-db.json`（keyMatches=true） | 同上 | 存储为 base64 DPAPI blob，无明文 |
| 9b | DPAPI 跨 Windows 用户隔离 | **NOT_RUN** | 历史文档明确未测（`docs/release-v3.3.1.md` 等） | — | — |
| 10 | 自动更新测试（检查/下载/校验/失败注入） | **PASS** | `ACCEPTANCE-REPORT.md` §G；reconstruct `evidence/failures-timeline.txt` | 本地 mock `127.0.0.1:8788` | 临时 QA 密钥 |
| 11 | **v3.3.2 → v3.3.3 应用内升级（重建基线）** | **PASS**（QA 身份，非生产链） | `.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/{baseline-install,upgrade-timeline,final-timeline,upgrade-after-db}.json/txt` | 重建 QA 基线 `f6009a21…d896` → 目标 `aab99010…ce3ff` | 见 §4 |
| 12 | 官方 v3.3.1 → v3.3.3 覆盖升级（同目录、非应用内） | **PASS** | `.qa-work/v3.3.3/upgrade-evidence3/upgrade-result.json` | Run `42033479080`；Artifact `qa-upgrade-evidence-13383072964` | 基线 `3caecbe2…6b74` |
| 13 | 未签名 Dry Run | **PASS** | `ACCEPTANCE-REPORT.md` §I-1 | Run `42032014347`；staging `13417456279` | `932f039…b1ce5` |
| 14 | 正式签名演练（production-sign） | **BLOCKED → 本轮取消** | Run `42033806115`（[evidence/cancelled-production-run.json](evidence/cancelled-production-run.json)） | 构建成功；签名作业等待 Environment 审批 | `932f039…b1ce5` |
| 15 | 正式生产签名链路的 3.3.2 → 3.3.3 应用内升级 | **NOT_RUN** | 无（正式 v3.3.2 无主程序；v3.3.3 未正式发布） | — | — |
| 16 | 历史 v3.3.2 UpdaterQA 基线寻获 | **BLOCKED**（历史事实，已由重建替代） | `.qa-work/v3.3.3/inapp-332/BLOCKED-report.md` | 338 runs / 167 artifacts / 25 release assets 搜索无果 | — |
| 17 | 旧 3.3.2-qa.1 → qa.2 升级实验（2026-10-27） | **STALE** | `docs/updater/qa-upgrade-report.md` | 22/22 PASS，但**目标不是** 3.3.2→3.3.3 | 旧 QA 构建 |
| 18 | v3.3.2 发布后 QA 中的 sidecar 故障 P2 | **STALE（沿用未重测）** | `docs/qa/post-release-qa-3.3.2.md`；`ACCEPTANCE-REPORT.md` §G P2-1 | v3.3.3 未改相关代码，未重测 | — |

## 2. v3.3.2 发布后 QA（历史）

- 报告：`docs/qa/post-release-qa-3.3.2.md`；结论 **FAILED**（P0）。
- 统计：54 项 = 47 PASS / 3 FAIL / 4 未执行；后端 pytest 371 passed + 1 skip、前端 123 tests 为**历史记录**，本轮未重跑。
- 该报告中的 PASS 项（如合成数据后端、DPAPI 合成、备份一致性）**不能**抵消「正式安装包缺失主程序」这一 P0。

## 3. v3.3.3 Candidate 特别说明（证据纠正链）

- `reverify-result.json` 的**原始**记录出现 `passed=false` 与 `key_ids_match=false` 等字段，但实际签名校验结果为 `exit 0` / `OK signature verified`；后续 `reverify-summary.json` 已解释并修正：Key ID 同一、签名有效。
- Attestation：默认 `gh attestation verify` 会先命中**较晚**的 `release.yml` Run `42033806115`（因为 `sidecar-smoke.json` 字节同时出现在未签名 staging 中）；用 `--signer-workflow windows-rc.yml` 限定后，Candidate Run `41955823250` attempt 1 的 **9 个 subject 全部匹配**，证据保留在 `sidecar-smoke-candidate-attestation.json`。
- 结论：候选来源与签名**有效但为临时 Candidate 密钥**，不是生产签名。引用时必须连同该纠正链一起披露。

## 4. 重建 v3.3.2 QA 基线 → v3.3.3 应用内升级（详细）

**背景事实**：历史 v3.3.2 UpdaterQA 基线包从未获得（`BLOCKED-report.md` 明确）。为完成升级测试，使用 `8e42390`（含 #61 修复、版本仍为 3.3.2）重建了一个**标记为 RECONSTRUCTED QA BASELINE** 的独立 QA 安装包，并复用既有临时 QA 签名密钥对目标包签名。

| 项 | 值 |
| --- | --- |
| 重建基线包 | `YijingWorkbenchUpdaterQA_3.3.2_x64-setup.exe`，16,995,165 B，SHA-256 `f6009a211577d159904de6cd303bf0a361f4e4a7cd0187d33dfe521ac457d896` |
| 基线主程序 | `8a7886c0850074d0c64170c59dd908b388a1da729fb8903bf23419fa614d8fe7`，FileVersion 3.3.2 |
| 基线内容 | 747 文件；有 sidecar，无校验器；identifier / pubkey 已嵌入 |
| 目标包 | `YijingWorkbenchUpdaterQA_3.3.3_x64-setup.exe`，16,995,587 B，SHA-256 `aab99010335cd8053c24f33f7fb2ae3e7641c3626f82417ffb3eb4917b2ce3ff` |
| 目标签名 | 临时 QA 密钥 Key ID `4002C7DE3340768D`；校验器 `exit 0` |
| 升级时间线 | 2026-11-05T17:50:58Z → 17:52:10Z（`evidence/upgrade-timeline.txt`） |

升级过程与结果：

1. 首次下载被截断 → `error decoding response body`，备份数 0→0（**未进入安装**，数据无损）。
2. 正常重试 → 出现安装前备份 `history.pre-update-20261105T175142Z.sqlite3`（10 条记录，integrity ok）。
3. 旧应用退出 → 安装器运行 → 新应用启动（`yijing-workbench.exe`，`214c3be8…13460`），health=200。
4. 升级后：运行时版本 `V3.3.3`；10 条历史全部保留 + 新增 1 条 = 11 条；`integrity_check=ok`；`keyMatches=true`；备份 1 份。
5. 最终复核（`final-timeline.txt`，17:57Z）：仍为 3.3.3 / 11 条 / integrity ok / keyMatches true / health 200。
6. **已知显示缺陷**：升级后「关于」页显示 `aboutVersion=V3.3.2`，而 runtime/版本资源为 3.3.3（目标包沿用旧前端硬编码）。**按原样记录，不抹去**，见 [KNOWN-ISSUES.md](KNOWN-ISSUES.md) P2。
7. 故障与恢复（`failures-timeline.txt`）：异钥签名拒绝、单字节篡改拒绝、HTTP 500、离线、安装器中断（exit 4294967295）、安装失败注入、sidecar 失效、备份恢复 —— 均保持旧版本可运行、数据库哈希不变；备份恢复 10/10 条、integrity ok、Key 可解密。

**边界**：以上为 QA 隔离身份（`cn.yijing.workbench.updaterqa`）、临时 QA 密钥、本地 HTTP 更新源；**不代表**正式生产签名链路。正式 3.3.2 → 3.3.3 升级为 **NOT_RUN**。

## 5. 证据文件位置

- v3.3.3 验收总报告：`.qa-work/v3.3.3/ACCEPTANCE-REPORT.md`
- 重建基线与升级：`.qa-work/v3.3.3/inapp-332/reconstruct-332/evidence/`
- 官方 Candidate 运行证据：`.qa-work/v3.3.3/runner-evidence2/`、`.qa-work/v3.3.3/upgrade-evidence3/`
- 独立复核：`.qa-work/v3.3.3/reverify-live/`
- v3.3.2 发布后 QA：`docs/qa/post-release-qa-3.3.2.md`
- 本轮 QA 文件清点与关键哈希：[evidence/qa-inventory.json](evidence/qa-inventory.json)、[evidence/qa-critical-hashes.json](evidence/qa-critical-hashes.json)
