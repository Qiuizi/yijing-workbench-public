# SECURITY-INVENTORY — 密钥、签名、权限与安全风险

> **本文件绝不包含任何私钥内容、口令、Token 或密钥明文。** 仅记录路径、存在性、大小、哈希、Key ID、公钥指纹与用途。
> 本轮未修改任何 Environment Secret，未生成或轮换密钥，未读取 `.key` 或 `password/passphrase` 文件内容。

## 1. 总状态

| 项 | 状态 |
| --- | --- |
| 正式私钥文件 | ✅ 存在（本机，口令加密） |
| 正式公钥（仓库内置） | ✅ 存在，与 `tauri.conf.json` 一致 |
| GitHub `release` Environment Secrets | ✅ 3 个名称均存在（GitHub 不回读值） |
| 离线加密归档 | ⚠️ **无法核实** → `SIGNING_BACKUP_UNVERIFIED` |
| 归档口令与归档分离保管 | ⚠️ **无法核实** → `UNVERIFIED` |
| 正式签名演练 | ⛔ 冻结时取消，未生成正式签名产物 |

**结论：正式密钥材料本身在位，但「离线备份已完成且与口令分离」无法确认，因此不得声称安全归档完成。**

## 2. 正式签名材料（本机）

目录：`C:\Users\123\.tauri\yijing-release\`（仅当前用户可访问）

| 文件 | 存在 | 大小 (B) | SHA-256 | 用途 |
| --- | --- | --- | --- | --- |
| `yijing-release.key` | 是 | 348 | `00370433a15fab5d3eb8d3d2f6e02a4664952f0b7d86db83a75bdb05590c5354` | 正式 Tauri updater 私钥（口令加密）；内容未读取 |
| `yijing-release.key.pub` | 是 | 152 | `31b9fa380600af3cabfbdb47051346a9120f9879557310004acee0a838ed757c` | 正式公钥原文（写入配置的那一行） |
| `updater-pubkey.b64` | 是 | 152 | `31b9fa380600af3cabfbdb47051346a9120f9879557310004acee0a838ed757c` | 写入 `tauri.conf.json` / `TAURI_UPDATER_PUBKEY` 的值（与 `.key.pub` 同内容） |
| `key-password.txt` | 是 | 64 | 刻意不记录 | 私钥口令（**与私钥同目录存放，见 §6 风险 R-2**） |
| `backup-passphrase.txt` | 是 | 64 | 刻意不记录 | 外置磁盘加密归档的口令 |
| `README.txt` | 是 | 684 | `cd773779862e6f99498d6b5f63e9b37e330b9055f4d1ca211550d617ec6b26bb` | 本目录说明 |
| `reveal-backup-passphrase.ps1` | 是 | 1,567 | `6635a5822cb4a669455cf72fcc7a55431213908238a506e6b9837a672f262232` | 从 Windows 凭据管理器复制归档口令到剪贴板（不打印） |
| `_provision.ps1` | 是 | 21,266 | `83f15321703168808417dc3362f41ea678c2a48bd8f83ca49ed4a2a8bc4cef0a` | 配置脚本 |

`README.txt` 声明的备份设计：**外置磁盘只放加密归档、不放口令；归档口令另存于 Windows 凭据管理器（目标名 `yijing-release/backup-passphrase`）**。

## 3. 公钥身份与指纹

指纹定义：解码后的 minisign 公钥前两行文本（LF 结尾）的 SHA-256；`repository_fingerprint` 取其前 16 位大写十六进制。Key ID 同时给出原始字节序与 minisign 显示序（两者字节反序）。原始数据：[evidence/public-identities.json](evidence/public-identities.json)。

| 用途 | Key ID（字节序） | Key ID（minisign 显示） | 公钥文本 SHA-256 | repository fingerprint |
| --- | --- | --- | --- | --- |
| 正式生产（仓库内置 = 本机 `.pub`） | `5D79EDB98FE951FF` | `FF51E98FB9ED795D` | `05974a347e99a1d9893e94131c8baa954ae3c3b88dd1a78372231a08e4c81c36` | `05974A347E99A1D9` |
| v3.3.3 Candidate（临时） | `36F737BF65941C82` | `821C9465BF37F736` | `8d11a233dbf9751ec813ffda3f590498341454ce8486181c306265da5dd0c385` | `8D11A233DBF9751E` |
| QA 固定（隔离实验） | `7B072FC9CF8B402F` | `2F408BCFC92F077B` | `093e59e9b93fe19e456b0f7680fc45404732ed7da513f7da0b029b0b9450cbe9` | `093E59E9B93FE19E` |
| 重建基线用临时 QA 密钥 | `4002C7DE3340768D` | `8D764033DEC70240` | `11aa54fc738f5f485d514173ef9e2470f48272b113ce802d7b7e5583357b1a74` | `11AA54FC738F5F48` |
| 发布后 QA 密钥 | `E96A04C0FFC5456B` | `6B45C5FFC0046AE9` | `d5eda17ad6c664e23f20deaaf875172d19304d7cfceb78a9e6dab8c51b77ba0d` | `D5EDA17AD6C664E2` |

**核对结论**：仓库内置正式公钥与维护者本机 `yijing-release.key.pub` **逐字一致**（`production_public_file_matches_embedded: true`）。v3.3.3 Candidate 公钥**既不是**正式公钥，**也不是**仓库 QA 公钥，符合 `signing_mode=ephemeral_candidate`。

## 4. QA 与 Candidate 密钥（隔离，非生产）

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `frontend/src-tauri/.updater-qa/qa.key.pub`（及同目录私钥，已被 `.gitignore`） | QA 公钥 | 固定 QA 对照密钥，Key ID `7B072FC9CF8B402F` |
| `.qa-work/v3.3.2/updater-qa/ephemeral.key.pub` | 临时 QA 公钥 | 重建基线/目标包签名，Key ID `4002C7DE3340768D` |
| `.workbuddy/post-release-qa/keys/postqa.key.pub` | QA 公钥 | 发布后 QA，Key ID `E96A04C0FFC5456B` |

这些密钥**只用于隔离实验**：`release_gate.py` 与 `verify_release.py --production` 都会拒绝它们。候选包 `.sig` 的 Key ID `36F737BF65941C82` 属于每次运行生成的临时候选密钥。

## 5. GitHub 配置状态（只读）

| 项 | 观测值 |
| --- | --- |
| `release` Environment | 存在；Required reviewers = `Qiuizi`；`can_admins_bypass=false`；部署分支策略仅 `main` |
| `release` Environment Secrets | 3 个名称存在：`TAURI_SIGNING_PRIVATE_KEY`、`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`、`TAURI_UPDATER_PUBKEY`（均创建/更新于 2026-10-29；值不可读） |
| 仓库级 Secrets | 0 个（正式私钥只在 Environment 中） |
| Actions 默认工作流权限 | `read`；`can_approve_pull_request_reviews=false` |
| Actions 允许范围 | `allowed_actions=all`；`sha_pinning_required=false`（见 R-5） |
| `github-pages` Environment | 存在，自定义分支策略 |

原始：[evidence/release-environment.json](evidence/release-environment.json)、[evidence/environment-secret-names.json](evidence/environment-secret-names.json)、[evidence/repository-secret-names.json](evidence/repository-secret-names.json)。

## 6. 安全风险

| ID | 级别 | 风险 | 依据 / 建议 |
| --- | --- | --- | --- |
| R-1 | **高** | **离线备份无法核实**：外置磁盘当前未连接，`D:\Qiuizi\backups` 只有 10-13/10-16 的旧项目归档，未见 2026-10-28 前后的签名加密归档 | 状态 `SIGNING_BACKUP_UNVERIFIED`。恢复项目前必须插上外置磁盘，校验归档存在、可解密、且与口令分离保管 |
| R-2 | **高** | 私钥口令文件 `key-password.txt` 与私钥放在同一目录，未与私钥分离 | 违背「口令与私钥分开保管」原则；建议把口令移入密码管理器，删除同目录明文口令文件（需维护者执行，本轮未动） |
| R-3 | 中 | 私钥本体在本机用户目录（DPAPI/ACL 保护，但非硬件隔离） | 保持机器访问控制；确认 BitLocker/磁盘加密状态 |
| R-4 | 中 | 正式签名演练在冻结时被取消，正式签名产物与正式发布链路**从未端到端验证成功** | 恢复发布前必须完成一次 `dry_run=true, exercise_production_sign=true` 演练并核对签名 Key ID = `5D79EDB98FE951FF` |
| R-5 | 中 | Actions 未强制 SHA pinning（`sha_pinning_required=false`），第三方 action 以 tag 引用 | 提高供应链安全：启用 SHA pinning，或固定关键 action 到 commit |
| R-6 | 低 | QA 密钥私钥存于工作区（已 gitignore） | 不得提交、不得上传；确认 `.gitignore` 规则持续生效 |
| R-7 | 低 | 官网下载入口仍指向有 P0 缺陷的 v3.3.2 | 完整性而非机密性风险；恢复发布前应更新入口或明确告警 |

## 7. 明确未做的事（合规声明）

- 未输出任何私钥内容、口令或 GitHub Token。
- 未把私钥复制到任何报告。
- 未将密钥上传到 GitHub。
- 未删除原始密钥。
- 未重新生成或轮换密钥。
- 未修改 Environment Secrets。
- 仅读取了密钥文件的**元数据**（名称、大小、哈希），未读取 `.key` 与口令文件正文；口令文件的哈希也刻意不记录。
