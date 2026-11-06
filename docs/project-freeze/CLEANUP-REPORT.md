# CLEANUP-REPORT — 冻结后工作区清理记录

- 执行时间：2026-11-06 19:0x（Asia/Shanghai），**经维护者明确授权**
- 授权范围：清理可重建缓存/构建产物，并额外删除 `.qa-work` 中的大型临时安装/解包目录
- 结果：工作区从 **12,988 MB** 降至 **1,991 MB**，释放 **10,997 MB（约 10.7 GB）**

## 1. 清理内容（40 项，按类别）

| 类别 | 内容 | 说明 |
| --- | --- | --- |
| 构建缓存 | `frontend/src-tauri/target`（7.77 GB）、`scripts/updater/verifier-proof/target`、`.qa-work/v3.3.3/shim/target`、各 `dist` | 可由 `cargo`/`tauri build` 重建 |
| 依赖 | 根 `.venv`、`frontend/node_modules`、`website/node_modules`、重建 worktree 的 `.venv`/`node_modules` | 可由 `pip install`/`npm ci` 重建 |
| Python 缓存 | 各 `__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache` | 可重建 |
| 浏览器缓存 | 4 个 QA 运行数据目录的 `EBWebView`（约 76 MB） | WebView2 运行缓存 |
| 临时安装副本 | `install-official`、`install-fresh`、`install-upgrade`、`updater-run/install-331`、`v3.3.2/install-fixqa`、`updater-qa/install-3.3.1`、两个 `install-baseline-pristine-*` | 已安装应用副本，各约 45 MB |
| 解包副本 | `extract-331`、`v3.3.2/extract-3.3.1`；以及 `candidate/extracted`、`reverify-live/extracted`、`github-audit/*/extracted`、`baseline-check/extracted`、`keycheck/extract-candidate` 下的 `binaries` | 安装包解包产物；**保留同目录的 `provenance.json`、`verification.json` 等证据** |
| 历史审计备份 | `docs/review/ui-audit-node-modules-backup`（117.8 MB）、`docs/review/ui-audit-vite-cache-backup`（9 MB） | 纯 node_modules / vite 缓存备份 |

逐项明细（路径、类别、大小）：[evidence/cleanup-deleted.json](evidence/cleanup-deleted.json)。

## 2. 明确保留（未删除）

- **全部 QA 证据与报告**：`.qa-work/**/evidence/`、`ACCEPTANCE-REPORT.md`、`reverify-live/*.json`、`runner-evidence*/`、`upgrade-evidence*/`、`BLOCKED-report.md`、`docs/qa/`、`docs/updater/`。
- **全部 QA 安装包**：`YijingWorkbenchV333QA_3.3.3_x64-setup.exe`、`YijingWorkbenchUpdaterQA_3.3.3_x64-setup.exe`、重建基线 `YijingWorkbenchUpdaterQA_3.3.2_x64-setup.exe`、`fixqa-installer.exe` 等。
- **数据库、备份与恢复快照**：`*.sqlite3`、`backups/`、`db-*-restore-*.sqlite3`。
- **密钥材料**：`C:\Users\123\.tauri\yijing-release\`、`.updater-qa/`、`.qa-work/v3.3.2/updater-qa/ephemeral.key*`、`.workbuddy/post-release-qa/keys/`（本轮未触碰）。
- **产物本地归档**：`.qa-work/project-freeze-20261106/remote-archives/`（191 个文件，1,217.6 MB，校验记录不变）。
- **文档与源码**：`docs/review/ui-audit/`、`docs/project-freeze/`、`website/`、`backend/`、`frontend/` 源码与配置。
- **Git 元数据**：分支、worktree 注册、Tag、历史。

## 3. 清理后的影响

- `node_modules`、`.venv`、`target` 被删除，重新开发/测试前需按 [RECOVERY-GUIDE.md](RECOVERY-GUIDE.md) 第 3 节重装依赖；这是可重建成本，不影响任何证据。
- QA 的「已安装应用副本」与解包目录被删除，但**原始安装包、数据库、时间线、JSON 证据、截图和报告都在**，验收结论仍可复核；如需重跑某个用例，用保留的安装包重新安装即可。
- `frontend/dist`、`website/dist` 被删除，官网页面可重新 `npm run build` 生成。
- 本次清理**不在**冻结时的审计快照内；[FREEZE-MANIFEST.json](FREEZE-MANIFEST.json) 记录的是 2026-11-06 18:08 的冻结状态，本报告记录其后的授权变更。

## 4. 未做

- 未删除任何 Release、Tag、Artifact、分支或 worktree。
- 未删除任何密钥、备份、数据库或产物归档。
- 未修改任何被删除目录之外的业务代码。
