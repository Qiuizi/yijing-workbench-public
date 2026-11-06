# evidence — 冻结审计原始数据

本目录保存 2026-11-06 冻结审计的**原始元数据与观测**，供未来复核。所有内容均为只读采集，未在此目录存放私钥、口令或真实用户数据库。

| 文件 | 内容 |
| --- | --- |
| `audit-time.json` | 审计开始时间与范围声明 |
| `git-audit.json` | 主工作区与全部 worktree 的 HEAD、status、diff、Cargo.toml 快照与 blob 对比 |
| `worktree-*-Cargo.toml.snapshot` | 被 `git status` 标记的 Cargo.toml 实际字节快照 |
| `untracked-files.json` | 未跟踪文件清单（仅路径） |
| `releases.json` / `latest-release.json` | 全部公开 Release 与最新 Release（含资产 digest） |
| `pull-requests.json` | 全部 PR 状态（含 #51/#56/#60/#61/#62） |
| `open-issues.json` | 打开的 Issue |
| `artifacts.json` | 全部 Actions Artifact 元数据（166 个） |
| `recent-runs.json` / `workflows.json` | 工作流与最近运行 |
| `cancelled-production-run.json` | 被冻结取消的生产签名演练 Run `42033806115` |
| `production-run-jobs.json` / `dry-run-jobs.json` | 两个发布运行的 job 级状态 |
| `release-environment.json` / `environment-secret-names.json` / `repository-secret-names.json` / `release-branch-policy.json` / `actions-permissions.json` | GitHub 环境、密钥名称与权限配置（只有名称，无值） |
| `security-file-metadata.json` | 密钥文件的路径/大小/哈希（口令文件哈希刻意不记录） |
| `public-identities.json` | 各公钥的 Key ID、公钥文本 SHA-256 与仓库指纹 |
| `qa-inventory.json` / `qa-critical-hashes.json` | `.qa-work` 文件清点与关键证据哈希 |
| `remote-preservation.json` | 191 个远端产物本地归档的逐项校验记录 |
| `website-observation.json` / `website-index.html` / `website-live.js` | 官网当前页面与线上脚本快照（版本仍为 3.3.2） |
| `processes.json` / `listeners.json` | 冻结时进程与监听端口观测 |
| `collect-freeze.ps1` / `preserve-remote.mjs` / `public-identities.mjs` / `build-manifest.mjs` | 本轮采集与清单生成脚本（可重跑复核） |

重跑顺序：`collect-freeze.ps1` → `preserve-remote.mjs` → `public-identities.mjs` → `build-manifest.mjs`。
