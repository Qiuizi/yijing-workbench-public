# RECOVERY-GUIDE — 项目恢复操作指南

> 目标：即使间隔数月重新打开项目，也能确定停在哪里、如何安全恢复开发、测试与发布。
> 恢复前先读 [KNOWN-ISSUES.md](KNOWN-ISSUES.md) 的 P0/P1 与 [SECURITY-INVENTORY.md](SECURITY-INVENTORY.md)。
> 冻结基线 SHA：`932f0390bdee79068b955f16b0f82cebc56b1ce5`。

---

## 1. 获取仓库

```powershell
git clone https://github.com/Qiuizi/yijing-workbench-public.git
cd yijing-workbench-public
git fetch --all --tags
git checkout 932f0390bdee79068b955f16b0f82cebc56b1ce5
git log -1 --format='%H %cI %s'
```

预期 `%H` = `932f0390bdee79068b955f16b0f82cebc56b1ce5`，提交信息 `release: prepare v3.3.3 installer packaging fix (#62)`。

- 若需要继续开发，建议从 `main` 新建分支；**不要**直接改 main。
- 冻结时的历史分支/worktree 未清理；克隆新仓库不会带过来，它们仍保留在原机器上。

## 2. 恢复开发环境（Windows x64）

| 组件 | 版本 | 用途 |
| --- | --- | --- |
| Python | 3.12（发布流水线用 3.12） | 后端与打包脚本 |
| Node.js | 24 | 前端与 Tauri CLI |
| Rust | 1.98.1（`x86_64-pc-windows-msvc`） | Tauri 桌面壳 |
| MSVC | Visual Studio 2022 Build Tools（VC143 x64） | Rust 链接与运行库 |
| NSIS | Tauri 自带 | 安装包 |
| WebView2 | Evergreen Runtime | 运行桌面应用 |

核对：

```powershell
python --version          # 3.12.x
node --version            # v24.x
rustc --version           # rustc 1.98.1
```

> 发布流水线通过 `.github/actions/setup-windows-toolchain` 固定上述版本；本地可用相同版本，减少「本地能构建、CI 构建不同」的差异。

## 3. 安装依赖

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-win.lock.txt
# 打包 sidecar 另需：
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt

cd frontend
npm ci
cd ..

cd website
npm ci
cd ..
```

Linux 开发用 `requirements.txt` + `python3.12 -m venv .venv`。

## 4. 检查密钥与签名配置

### 4.1 本机密钥文件（**只看元数据，不要打印内容**）

```powershell
Get-ChildItem 'C:\Users\123\.tauri\yijing-release' -File |
  Select-Object Name,Length,LastWriteTime
```

应有：`yijing-release.key`、`yijing-release.key.pub`、`updater-pubkey.b64`、`key-password.txt`、`backup-passphrase.txt`、`README.txt`。

- 若恢复机器不是原机器：从**离线加密归档**取回私钥，按 `README.txt` 用归档口令解密；**不要**重新生成密钥（重新生成会让旧客户端收不到更新）。
- 若私钥丢失：只能发新公钥的过渡版本并让用户手动重装，详见 `docs/updater/PRODUCTION-SIGNING.md` §6。

### 4.2 核对公钥 Key ID 与指纹

```powershell
$pub = (Get-Content -Raw 'C:\Users\123\.tauri\yijing-release\yijing-release.key.pub').Trim()
.\.venv\Scripts\python.exe -c "from scripts.updater.manifest import public_key_key_id, public_key_fingerprint; import sys; k=sys.argv[1]; print('key_id=', public_key_key_id(k)); print('fingerprint=', public_key_fingerprint(k))" $pub
```

期望 `key_id= 5D79EDB98FE951FF`（minisign 显示序为 `FF51E98FB9ED795D`），`fingerprint` 与 [SECURITY-INVENTORY.md](SECURITY-INVENTORY.md) §3 一致。并与 `tauri.conf.json` 的 `plugins.updater.pubkey` 逐字比对。

### 4.3 离线备份核验（**恢复发布前必须完成**）

1. 接入外置磁盘，确认存在加密归档（冻结时状态 `SIGNING_BACKUP_UNVERIFIED`）。
2. 用 `backup-passphrase.txt` / Windows 凭据管理器 `yijing-release/backup-passphrase` 中的口令解密测试。
3. 确认归档**不是**与口令放在同一介质；口令应另存于密码管理器。
4. 解密出的私钥 Key ID 必须为 `5D79EDB98FE951FF`；否则说明归档错误，禁止发布。

### 4.4 GitHub 配置

- Environment `release`：Required reviewers = 维护者；部署分支仅 `main`；`can_admins_bypass=false`。
- 3 个 Environment Secrets：`TAURI_SIGNING_PRIVATE_KEY`、`TAURI_SIGNING_PRIVATE_KEY_PASSWORD`、`TAURI_UPDATER_PUBKEY`（冻结时均存在，2026-10-29 写入）。
- 仓库级 Secrets 应为 0。
- 复核：

```powershell
gh api repos/Qiuizi/yijing-workbench-public/environments/release --jq '{name,can_admins_bypass,protection_rules}'
gh api repos/Qiuizi/yijing-workbench-public/environments/release/secrets --jq '.secrets[].name'
```

> **不要**在终端 echo 私钥/口令；不要把私钥贴进 Issue/PR/聊天。

## 5. 恢复 QA 环境

- `.qa-work/` **完整保留**在原机器（约 2,043 个非依赖文件；依赖/构建缓存/已安装 sidecar 子树未清点）。关键证据路径见 [QA-ACCEPTANCE.md](QA-ACCEPTANCE.md) §5。
- 重建的 QA worktree：`.qa-work/v3.3.3/inapp-332/reconstruct-332/worktree`（detached `8e42390`），其 `.venv`、`node_modules`、`target` 可能已失效，重新克隆后按第 3 节重装即可。
- QA 数据库、备份、临时密钥、安装目录**全部保留**；不要删除 `%LOCALAPPDATA%\cn.yijing.workbench*` 与 `.qa-work/**/backups/`。
- 恢复测试前确认没有遗留测试进程（冻结时仅有 OpenCLI/REA 的 Node 进程，无 Yijing 进程）：

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'yijing|python|tauri' } | Select-Object ProcessId,Name,ExecutablePath
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 8788,52954
```

## 6. 运行测试

```powershell
# 后端
.\.venv\Scripts\python.exe -X utf8 -m pytest

# 前端
cd frontend
npm test
npm run typecheck
npm run build
cd ..

# 打包 sidecar 冒烟（合成数据）
pwsh -NoProfile -ExecutionPolicy Bypass -File .\scripts\smoke_packaged_sidecar.ps1 `
  -SidecarPath 'frontend\src-tauri\binaries\yijing-backend\yijing-backend.exe' `
  -ReportPath "$env:TEMP\sidecar-smoke.json"

# 安装包内容门禁（必须含主程序，见 P0 回归）
.\.venv\Scripts\python.exe -c "from scripts.updater import installer_contents as i; print(i.__name__)"
```

> 所有 QA 与测试使用**合成数据**，不要读取真实用户数据库或真实 API Key。

## 7. 恢复发布流程

1. 确认第 4 节密钥与离线备份全部通过。
2. 确认 `version` 在所有来源一致（`package.json`、`package-lock.json`、`tauri.conf.json`、`Cargo.toml`、`Cargo.lock`、`backend/main.py`）：

```powershell
.\.venv\Scripts\python.exe -c "from scripts.updater.manifest import assert_versions_consistent; print(assert_versions_consistent('.'))"
.\.venv\Scripts\python.exe scripts/updater/release_gate.py --expect-version 3.3.3
```

3. 先跑**未签名 Dry Run**：GitHub Actions → `Publish stable release (updater-enabled)` → `workflow_dispatch`，`version=3.3.3`、`confirm=3.3.3`、`notes_file=docs/release-notes-v3.3.3.md`、`dry_run=true`、`exercise_production_sign=false`。确认全部 success 且 `dry-run-check` 报告无副作用。
4. 再跑**正式签名演练**：同样参数但 `exercise_production_sign=true`，在 `release` Environment 由维护者本人审批。核对签名 Key ID = `5D79EDB98FE951FF`。
5. 演练通过后，才可 `dry_run=false` 正式发布（需再次确认 `version=confirm`）。
6. 发布后官网入口由工作流开 PR（不直接推 main），合并前核对下载链接与 SHA-256 指向新版本。

## 8. 发布前检查清单

- [ ] 冻结基线/新分支已评审，`git status` 无真实未提交改动
- [ ] 版本号在所有来源一致，`release_gate.py` 通过
- [ ] 该 SHA 的必需 CI 检查全绿（`ci_gate.py`）
- [ ] **安装包含主程序** `yijing-workbench.exe` 且 **不含** `verify-updater-signature.exe`（v3.3.2 P0 回归项）
- [ ] 安装包含 sidecar，SHA 与 manifest 一致
- [ ] 未签名构建**没有** `.sig`（私钥未泄漏进 build job）
- [ ] Staging Artifact digest 与上传一致，provenance 的 source SHA / run / attempt 正确
- [ ] 正式签名 `.sig` Key ID = `5D79EDB98FE951FF`（正式），不是 QA/候选密钥
- [ ] Attestation 验证通过（9 个 subject、OIDC issuer 正确）
- [ ] `latest.json` 指向正确版本与资产，SHA-256 与安装包一致
- [ ] 官网下载入口更新到新版本且提供 SHA-256
- [ ] 离线备份与口令分离已核验（`SIGNING_BACKUP_UNVERIFIED` 已解除）
- [ ] 先用隔离账户 + 合成数据做一次真实安装/覆盖升级验证
