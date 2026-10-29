# 应用内自动更新（v3.3.2 起）

本目录说明「易经起卦工作台」的更新机制、签名边界、发布流水线与数据保全策略。
实现基于 Tauri 2 官方 updater，不自行实现下载执行器。

## 1. 版本策略

| 版本 | 能力 |
| --- | --- |
| ≤ v3.3.1 | 没有 updater，只能手动安装 |
| v3.3.2 | 首次集成 updater：**只能从 v3.3.2 升级到更高版本**；从 v3.3.1 升到 v3.3.2 仍需手动安装一次 |
| ≥ v3.3.3 | 由已安装的 v3.3.2（或更高）自动检测、下载、校验、安装 |

## 2. 数据流

```
启动（Tauri 桌面端）
  └─ updater.init()
       ├─ 距上次检查 < 24h 或自动检查已关闭 → 什么都不做
       └─ check()  ── Rust: GET <endpoint>/latest.json（HTTPS，20s 超时）
              ├─ 无更新         → phase=up_to_date
              ├─ 有更新         → phase=available（只报告，不下载）
              └─ 网络/结构错误   → phase=offline / error（本地功能不受影响）

用户点击「下载并安装」
  ├─ update.download()          → 进度事件（Started/Progress/Finished）
  ├─ POST /api/desktop/update/backup   → SQLite 在线备份 + 计数校验（失败即中止）
  ├─ invoke('prepare_for_update')      → 停 sidecar 并等待退出
  ├─ update.install()                  → Tauri 校验签名 → 运行 NSIS 安装包
  └─ relaunch()                        → 新版本启动
```

关键点：

- **检查是后台任务**，不 await 阻塞起卦、阅读、历史；失败只更新状态标签。
- **不静默安装**：`check()` 只产出「可更新」，下载与安装必须由用户点击。
- **禁止任意 URL**：端点来自 `tauri.conf.json`，前端 JS 不能传自定义 URL；Rust 侧只允许 HTTPS（QA 构建显式打开 `dangerousInsecureTransportProtocol` 以便本地回环测试）。
- **并发守卫**：`busy` 期间拒绝重复的 check/download，避免两个安装任务并行。

## 3. 三类完整性凭据（不能互相替代）

| 凭据 | 作用 | 谁来验 | 现状 |
| --- | --- | --- | --- |
| Tauri Updater 签名（`.sig`，minisign/ed25519） | 证明更新包出自持有私钥的一方 | 应用安装前，Rust 内置公钥 | 已实现 |
| SHA-256（`SHA256SUMS.txt`） | 证明字节未被改动/下载完整 | 发布脚本、人工核对 | 已实现 |
| Windows Authenticode | 操作系统层面的发布者身份 | Windows / SmartScreen | **未提供**（安装包无代码签名证书） |

> 哈希可以重新计算，签名不能伪造；因此发布门禁以签名为准，哈希只作完整性交叉校验。

## 4. 密钥管理

| 项 | 位置 | 说明 |
| --- | --- | --- |
| 公钥（正式） | `frontend/src-tauri/tauri.conf.json` → `plugins.updater.pubkey` | 当前仓库内置的是正式公钥，可公开 |
| 公钥（QA） | `scripts/updater/keys.py` 的 `QA_PUBLIC_KEY` | 只给测试对照，正式发布会拒绝 |
| 私钥（QA） | 本地 `frontend/src-tauri/.updater-qa/`（已 gitignore） | 不提交、不上传 |
| 私钥（正式） | GitHub Environment `release` 的 `TAURI_SIGNING_PRIVATE_KEY` | 只有审批通过的 build job 能读取 |
| 私钥口令 | 同环境 `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | 与私钥分开配置 |
| 公钥（正式，环境侧） | 同环境 `TAURI_UPDATER_PUBKEY` | 必须与仓库内置公钥逐字一致，否则 `release_gate.py` 拒绝 |

正式密钥的生成、备份、写入配置与轮换步骤见 [`PRODUCTION-SIGNING.md`](PRODUCTION-SIGNING.md)。

规则：

1. 私钥、口令、完整环境变量**不得**出现在日志、Artifact、安装包或仓库中（流水线只打印布尔值与 key id）。
2. 候选构建（PR / main push）**拿不到**正式私钥：优先用仓库级候选密钥，缺失时为本次运行生成临时密钥。
3. 正式发布若检测到仓库仍在用 QA 公钥，`release_gate.py` / `verify_release.py --production` 直接失败。
4. 私钥丢失 = 无法再发布可被现有用户自动升级的版本（只能让用户手动重装），请离线备份。

当前状态：**仓库只有 QA 公钥**。正式发布前必须由维护者生成正式密钥对并替换公钥 —— 这是本轮的阻断项之一。

## 5. 更新协议（latest.json）

`latest.json` 随 Release 一起上传，`releases/latest/download/latest.json` 是应用默认端点：

```json
{
  "version": "3.3.2",
  "notes": "更新说明",
  "pub_date": "2026-10-27T00:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "<.sig 文件内容：base64 编码的 minisign 文本，不是链接>",
      "url": "https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.2/yijing-workbench-3.3.2-x64-setup.exe"
    }
  }
}
```

强制约束（`scripts/updater/manifest.py` 校验，任一不满足即拒绝发布）：

- `version` 是合法 SemVer，且与仓库所有版本来源一致；
- 正式渠道拒绝预发布版本（含 `-`）；
- `signature` 是 `.sig` 文件的内容本身（Tauri 写成单行 base64，解码后是 minisign 文本），不能是 URL；与 `.sig` 逐字相同；
- `url` 必须 HTTPS、指向本仓库、与 tag 和文件名一致；
- 所有字段来自同一次构建（`SHA256SUMS.txt` / `manifest.json` / `PROVENANCE.md` 交叉核对）。

## 6. 流水线

### A. 候选构建（`.github/workflows/windows-rc.yml`）

- 触发：PR（按路径过滤）/ **main push（不过滤）** / 手动 dispatch。
  main push 不过滤是为了保证「最终 main SHA 上一定存在这四条检查」——正式发布门禁依赖它。
- 步骤：版本一致性 → 后端测试 → 前端测试 + typecheck → 构建 sidecar + NSIS →
  sidecar 冒烟 → `build_release_dir.py` 生成 latest.json/SHA256SUMS/manifest/PROVENANCE →
  `verify_release.py`（非生产模式）→ 上传 Artifact。
- 边界：不创建 Release、不写更新渠道、不接触正式私钥；产物 14 天过期。
- 实跑记录：run 40466608307（commit `ff87bbe`）——签名构建、sidecar 冒烟、契约校验、Artifact 上传全部通过。

### B. 正式发布（`.github/workflows/release.yml`）

- 触发：`workflow_dispatch`，必须填 `version` + `confirm`，默认 `dry_run=true`。
- 三个 job，权限与风险分离：
  - `build`（`contents: read` + `actions: read`，持有签名私钥）：预检输入/ref/SHA/Tag →
    版本 + 公钥门禁（`release_gate.py --expect-pubkey`）→ **该 SHA 的四条检查全绿**
    （`ci_gate.py`，按工作流文件判定 + check run 交叉核对）→ 用**注入的正式公钥**构建 →
    组装 → 真实验签（`verify_release.py --signature-verifier`）→ 上传 Artifact。
  - `publish`（`contents: write`，拿不到私钥）：仅在 `dry_run=false` 时运行；draft 上传 →
    回读 API 核对字节/摘要 → publish `--latest` → 核对 `releases/latest` 与公开 `latest.json`
    → 更新官网静态事实并推送。
  - `dry-run-check`：仅在 `dry_run=true` 时运行，断言没有创建 tag/release、官网未被改动。
- 任何一步失败都不会让半成品进入更新渠道：draft Release 不是 `releases/latest`。
- 已存在的 tag/release 在构建**之前**就会被拒绝（重试不会覆盖历史版本）。
- 源码只认 `github.sha`；main 已前进时预检直接失败，要求重新触发。

## 7. 数据保全

| 阶段 | 做法 |
| --- | --- |
| 备份 | `POST /api/desktop/update/backup` 用 SQLite **在线备份 API**（`Connection.backup`）生成一致性快照，`PRAGMA integrity_check` + 逐表计数与源库对比，不一致即失败 |
| 位置 | `%LOCALAPPDATA%\cn.yijing.workbench\backups\history.pre-update-<UTC>.sqlite3`，只保留最近 5 份 |
| 停服务 | `prepare_for_update` 停 sidecar 并等待退出（NSIS 要覆盖 `yijing-backend.exe`，进程活着就装不上） |
| 安装 | NSIS `currentUser`，identifier 不变（`cn.yijing.workbench`），不删除数据库与设置 |
| 失败恢复 | 备份失败 → 不停止服务、不安装；停服务失败 → 不安装；安装失败 → 旧版本仍在，下次请求会自动重启 sidecar |
| 不承诺自动回滚 | 未实现回滚安装包；人工恢复方法见 §9 |

备份为什么不直接 copy：SQLite 可能处于 WAL 未 checkpoint 状态，直接复制主文件会漏事务甚至得到损坏文件（`backend/tests/test_desktop_backup.py` 里有专门用例证明 WAL 中的写入会被在线备份捕获）。

## 8. 测试矩阵与实测记录

实测结果见 [`qa-upgrade-report.md`](qa-upgrade-report.md)（隔离 Windows NSIS 升级实验，**22/22 通过**）。

| 场景 | 预期 | 覆盖方式 | 结果 |
| --- | --- | --- | --- |
| 已是最新 | 显示无需更新 | 单测 | 通过 |
| 存在合法新版本 | 显示版本/日期/说明 | 单测 + 实机 | 通过（实机显示 v3.3.2-qa.2） |
| 用户选择稍后 | 不下载不安装 | 单测 | 通过 |
| 网络断开 | 本地功能可用 | 单测（offline 分支） | 通过 |
| 更新服务超时 | 可重试 | 单测 | 通过 |
| latest.json 损坏 | 拒绝更新 | 契约校验 + 单测 | 通过 |
| 缺失 `.sig` | 拒绝更新 | `verify_release.py` + 单测 | 通过 |
| 签名错误/包被篡改 | 拒绝安装 | 实机故障注入 | 通过（`The signature verification failed`） |
| 版本相同或更旧 | 拒绝更新 | updater 内置版本比较 | 通过 |
| 重复点击 | 不并发安装 | 单测 | 通过 |
| 备份失败 | 取消安装、不停服务 | 实机（sidecar 缺接口导致 404） | 通过 |
| 下载中断 | 不损坏已装应用 | 下载失败仅改状态 | 通过 |
| 安装后重启 | 新版本启动 | 实机 NSIS 覆盖安装 | 通过（运行时版本变为 qa.2） |
| 历史与 DPAPI | 完整 | 实机 + 独立解密脚本 | 通过（3→3 条、密钥可解密） |

单元/契约测试位置：

- `frontend/src/updater.test.ts`：状态机、24h 节流、并发守卫、离线归类、进度统计、格式化；
- `backend/tests/test_desktop_backup.py`：一致性备份、WAL、清理、缺库拒绝；
- `backend/tests/test_updater_manifest.py`：latest.json 构造/校验、篡改检测、QA 公钥门禁、官网同步幂等。

## 9. 升级与恢复

**v3.3.1 → v3.3.2（手动一次）**

1. 从官网或 Release 下载 `yijing-workbench-3.3.2-x64-setup.exe`；
2. 关闭应用，双击安装（currentUser，无需管理员）；
3. 历史数据库、设置、DPAPI 保护的 API Key 原位保留；
4. 打开后「设置 → 关于应用 → 应用更新」应显示当前版本 V3.3.2。

**v3.3.2 → 后续版本（自动）**

- 默认每 24 小时检查一次；也可手动「检查更新」；
- 确认后下载并安装，安装前自动备份数据库；
- 若安装后未自动启动，手动打开即可（数据在安装前已备份）。

**人工恢复（安装失败/新版本异常时）**

1. 关闭应用；
2. 把 `backups\history.pre-update-*.sqlite3` 覆盖回 `history.sqlite3`（应用关闭状态下）；
3. 重新安装上一个可用版本的安装包（Release 页面保留历史版本）；
4. 不要删除 `%LOCALAPPDATA%\cn.yijing.workbench` 目录，否则 API Key 与历史会一起丢失。

## 10. 已知限制与剩余风险

1. **正式签名密钥尚未配置**：当前仓库内置 QA 公钥，正式流水线会被门禁拦下（设计如此）。
2. **未启用 `requireSignedVersion`**：Tauri CLI 2.11 的签名 trusted comment 只记录 `timestamp` 与 `file`，没有版本号；开启会拒绝所有现存更新包。风险是「端点被劫持时可能回放旧的合法签名包」，缓解手段是端点固定在 GitHub HTTPS + 仓库发布记录可审计。待 CLI 支持后应开启。
3. **没有代码签名证书**：安装包会触发 SmartScreen 提示；Authenticode 与 updater 签名是两件事，不能互相替代。
4. **无自动回滚**：失败时保留旧版本与数据库，但需要人工重装（见 §9）。
5. **更新检查默认开启**：这是产品决策（可关闭）；离线用户不会因此失去任何本地功能。
6. **QA 隔离构建**使用临时 identifier `cn.yijing.workbench.updaterqa` 与 `YijingWorkbenchQA` 产品名，与正式版互不影响。

## 11. 正式发布 v3.3.2 还需要什么（独立授权）

按 [`PRODUCTION-SIGNING.md`](PRODUCTION-SIGNING.md) 完成：

1. 维护者本机生成正式密钥对并离线备份，私钥与口令放进 GitHub Environment `release`；
2. 把正式公钥写进 `tauri.conf.json`（走 PR）并配置环境 Secret `TAURI_UPDATER_PUBKEY`；
3. 配置 `release` 环境的必需审批人、只允许 `main` 部署；
4. 授权执行 `release.yml`：先 `dry_run=true`，确认无副作用后再 `dry_run=false`；
5. 发布后人工验证：官网下载区指向 v3.3.2、`latest.json` 可访问、已安装的 v3.3.2 能发现 v3.3.3（需要下一个版本配合）。

当前状态：**BLOCKED**（缺正式密钥与环境配置）。审查细节见 [`release-gate-review.md`](release-gate-review.md)。
