# 正式签名密钥与 release 环境配置（维护者操作手册）

> 本轮**没有**生成任何正式密钥。仓库当前内置的仍是 QA 公钥（key id `7B072FC9CF8B402F`，指纹 `093E59E9B93FE19E`），
> 因此正式发布门禁 `release_gate.py` 会明确拒绝，`release.yml` 无法进入构建阶段。

下面每一步都在**维护者自己的 Windows 机器**上执行；私钥与口令不要出现在聊天、Issue、PR、终端日志或 Actions 日志里。

## 1. 生成正式密钥对（本机，一次性）

```powershell
# 放在仓库之外，别放进项目目录
$dir = Join-Path $env:USERPROFILE '.tauri\yijing-release'
New-Item -ItemType Directory -Force -Path $dir | Out-Null

cd D:\Qiuizi\project\yijing\frontend
npx tauri signer generate -w "$dir\yijing-release.key"
# 会交互式要求输入口令两次。口令请单独存进密码管理器。
```

产物：

- `$dir\yijing-release.key`：私钥（含口令加密）
- `$dir\yijing-release.key.pub`：公钥（两行文本：untrusted comment + base64）

**立即做离线备份**（U 盘 / 加密归档），并把口令单独保存。丢失私钥 = 已安装的用户再也收不到自动更新，只能手动重装。

## 2. 得到要提交进仓库的公钥

Tauri 配置里存的是「整份 .pub 文件的 base64」，不是其中那行 key：

```powershell
$pubB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("$dir\yijing-release.key.pub"))
$pubB64 | Set-Clipboard
```

核对 key id（应与你之后在发布日志里看到的一致）：

```powershell
cd D:\Qiuizi\project\yijing
.\.venv\Scripts\python.exe -c "from scripts.updater.manifest import public_key_key_id, public_key_fingerprint; import sys; k=sys.argv[1]; print('key_id=', public_key_key_id(k)); print('fingerprint=', public_key_fingerprint(k))" $pubB64
```

## 3. 把公钥写进 `tauri.conf.json` 并提 PR

把 `frontend/src-tauri/tauri.conf.json` → `plugins.updater.pubkey` 的值替换为上一步的 `$pubB64`。

```powershell
cd D:\Qiuizi\project\yijing
python scripts/updater/release_gate.py --expect-version 3.3.2 --expect-pubkey $pubB64
# 期望输出：OK  version=3.3.2 pubkey_key_id=<你的 key id>
```

改动走正常 PR 流程合并到 main；**在此之前不要触发 `release.yml`**。

## 4. 配置 GitHub `release` 环境

在 GitHub 网页完成（本仓库无法用脚本安全地配置审批人）：

1. Settings → Environments → New environment → 名称 **`release`**。
2. **Required reviewers**：加入维护者本人（可再加一位）。
3. **Deployment branches and tags** → 选 `Selected branches` → 只允许 `main`。
4. 在该环境里添加三个 Secret：

| Secret | 内容 | 说明 |
| --- | --- | --- |
| `TAURI_SIGNING_PRIVATE_KEY` | `$dir\yijing-release.key` 的**文件内容**（整段文本） | 私钥本体，含口令加密 |
| `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` | 生成时输入的口令 | 与私钥分开保存 |
| `TAURI_UPDATER_PUBKEY` | 第 2 步的 `$pubB64` | 必须与仓库内置公钥逐字一致，否则门禁拒绝 |

可用 PowerShell 把私钥内容读出来粘到网页（不要 echo 到日志）：

```powershell
Get-Content -Raw "$dir\yijing-release.key" | Set-Clipboard
```

5. 建议同时确认：Settings → Actions → General 里 Workflow permissions 为 **Read repository contents**（发布 job 自己声明 `contents: write`，不需要全局写权限）。

> 注意：环境审批 + `workflow_dispatch` 不是绝对安全边界。能改 workflow 文件的人仍可改流程，
> 因此发布前必须确认「该 SHA 的 workflow 文件本身」也是经过评审的（`release.yml` 已固定 SHA 并核对来源）。

## 5. 当前状态（本轮结束时）

| 项 | 状态 |
| --- | --- |
| 正式密钥对 | ❌ 未生成（需维护者本机执行 §1） |
| 仓库内置公钥 | ⚠️ 仍是 QA 公钥 |
| `release` 环境 | ❌ 未配置（需 §4） |
| 三个 Secret | ❌ 未配置 |
| 正式 Dry Run | ⛔ BLOCKED（缺上述三项） |
| Tag / Release | ✅ 未创建，仍停在 v3.3.1 |

## 6. 密钥轮换与丢失

- **轮换**：Tauri 一个构建只内置一个公钥，换钥匙会让旧客户端验不过新签名。做法是发一个「过渡版本」：用**旧私钥**签名，但内置**新公钥**；之后所有版本用新私钥签名。
- **丢失私钥**：无法再对现有用户推送自动更新。只能让用户手动下载安装新版本（新版本可以内置一把新公钥），并在 Release 说明里写清楚。
- **QA 私钥**（`frontend/src-tauri/.updater-qa/`）只用于隔离实验，**永远不能**当作正式密钥；`release_gate.py` 与 `verify_release.py --production` 都会拒绝它。
