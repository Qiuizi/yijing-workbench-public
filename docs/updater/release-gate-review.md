# 发布门禁审查与修复记录（2026-10-27）

审查对象：`main@edb8507`（PR #43 合并后）。目标不是加功能，而是让发布系统「只在真正该放行的时候放行」。

## 一、实际发现的问题

| # | 问题 | 证据 | 影响 |
| --- | --- | --- | --- |
| P1 | 正式发布门禁在真实 main SHA 上**必然失败** | `edb8507` 的 workflow runs 只有 `pages.yml` 与 `windows-rc.yml`；`v1-learning-ci.yml` / `website-ci.yml` 根本没有 main 触发 | `release.yml` 第一步就 throw；发布永远走不下去 |
| P2 | 正式构建**没有注入正式公钥** | 旧 `release.yml` 只传 `createUpdaterArtifacts:true`，公钥仍取 `tauri.conf.json` 的 QA 公钥 | 用正式私钥签名、应用内置 QA 公钥 → 用户永远装不上更新；而 `verify_release --production` 只查仓库配置，会**假通过** |
| P3 | `workflow_dispatch` 输入直接拼进 PowerShell | `'${{ inputs.version }}'`、`--notes-file '${{ inputs.notes_file }}'` | 注入面；`notes_file` 还能指向仓库外任意文件 |
| P4 | 源码 SHA 未真正钉死 | `ref: main` 事后才 `git rev-parse HEAD` | dispatch 到 checkout 之间 main 前进 → 构建的提交与维护者看到的不一致 |
| P5 | 缺少 Tag/Release 存在的**早期**拦截 | 旧流程只有 `gh release create` 会失败 | 浪费一次完整构建；失败点靠后，容易留下半成品 |
| P6 | 整个 job 持有 `contents: write` | workflow 级权限 | 跑 `npm ci` / 项目脚本的步骤也能写仓库 |
| P7 | Dry Run 没有「零副作用」断言 | 只打印一行日志 | 无法证明 dry run 真的没建 tag/release |
| P8 | 签名只做「格式检查」，没有密码学验证 | 旧 `read_signature` 只看行数 | 公钥与私钥不匹配也能过门禁 |
| P9 | 同名 check 的来源未区分 | Pages 工作流产出通用名 `build` / `deploy` | 名字匹配可能采信无关结果 |
| P10 | QA 升级实验的结论无法自动化复用到正式构建 | 只有人工记录 | 「QA 通过」不等于「正式密钥构建通过」 |

## 二、修复内容

### 1) CI 门禁覆盖（P1、P4、P9）

- `windows-rc.yml` / `v1-learning-ci.yml` / `website-ci.yml`：**main push 一律不加路径过滤**（PR 侧仍按路径过滤控成本），保证任意一次合并后，最终 SHA 上都能拿到四条检查；`workflow_dispatch` 保留作为补跑机制。
- 新增 `scripts/updater/ci_gate.py`：按**工作流文件路径**判定，而不是只看名字。
  - run 必须 `head_sha == 发布 SHA`；
  - 事件只接受 `push` / `workflow_dispatch`（PR 的合并测试提交不算）；
  - 取该工作流最新一次 run，必须 `completed + success`；
  - 再交叉核对 job 的 check run：`app.slug == github-actions`、`head_sha` 一致、`completed + success`——防止「workflow success 但 job 被跳过」。
- `release.yml` 用 `github.sha`（dispatch 时刻的 main 顶端）作为唯一源码，checkout 该 SHA，并在预检里断言 `git HEAD == pinned SHA == 当前 main 顶端`；main 已前进则直接失败，提示重新触发。

### 2) 正式公钥注入（P2、P8、P10）

- `release.yml` 从 `release` 环境取 `TAURI_UPDATER_PUBKEY`，写进构建用的 `--config` 覆盖文件：`plugins.updater.pubkey` = 正式公钥，`bundle.createUpdaterArtifacts` = true。
- `release_gate.py --expect-pubkey`：要求**仓库内置公钥与环境公钥完全一致**且都不是 QA 公钥。
- `build_release_dir.py --updater-pubkey`：把「本次实际注入的公钥」的 key id、指纹、来源写进 `manifest.json`，并当场核对**公钥 key id == 签名 key id**。
- 新增 Rust 校验器 `frontend/src-tauri/src/bin/verify-updater-signature.rs`（复用 Tauri 同款 `minisign-verify`），`verify_release.py --signature-verifier` 调用它做真正的 ed25519 验证。

### 3) 输入与权限（P3、P6）

- 新增 `scripts/updater/release_preflight.py`：版本/确认号/SemVer、`notes_file` 只允许 `docs/release-notes-v<版本>.md`（规范化 + 仓库边界 + 存在性 + 大小）、ref 必须是 `refs/heads/main`、SHA 三元一致、Tag/Release 不存在。
- 所有 `${{ inputs.* }}` 改为经 `env:` 传入，PowerShell 只读 `$env:`，不再拼接。
- 拆成两个 job：`build`（`contents: read` + `actions: read`，持有签名私钥）与 `publish`（`contents: write`，拿不到私钥）。`dry-run-check` 单独 job 只读。

### 4) Dry Run 与重复发布（P5、P7）

- 构建前即拒绝已存在的 tag / release；`publish` job 再检查一次。
- `dry-run-check` job 显式断言：无 tag、无 release、`website/src/links.ts` 未被改成新版本。
- 发布后 `gh api releases/latest --jq .tag_name` 必须等于本次 tag。

## 三、验证证据

### CI 门禁（离线回放真实状态）

```
$ python scripts/updater/ci_gate.py --repo Qiuizi/yijing-workbench-public \
      --sha edb85075a0fded200bcab9ba146fd16910b6f13d
source sha: edb85075a0fded200bcab9ba146fd16910b6f13d
  OK   .github/workflows/windows-rc.yml           success · run 64 · push
  FAIL .github/workflows/v1-learning-ci.yml       该 SHA 上没有这次工作流的运行记录；缺少 check run：Frontend tests and build（可能该 job 被条件跳过）；缺少 check run：Backend regression tests（可能该 job 被条件跳过）
  FAIL .github/workflows/website-ci.yml           该 SHA 上没有这次工作流的运行记录；缺少 check run：website-validation（可能该 job 被条件跳过）
exit=1
```

反向测试 21 项（`backend/tests/test_ci_gate.py`）：缺工作流、failure/cancelled/timed_out/skipped、in_progress、跨 SHA、PR 事件、同名异 App、缺 check run、check run 失败、非法 SHA —— 全部拒绝；「旧失败 + 新成功」「手动补跑」正确放行。

### 签名验证（真实 QA 产物，QA 公钥 key id `7B072FC9CF8B402F`）

```
OK    signature verified for ...qa.2-x64-setup.exe            exit=0
FAIL  signature is invalid: 安装包被改动…                       exit=1   # 篡改 1 字节
FAIL  signature is invalid: …                                 exit=1   # 用 qa.1 的签名验 qa.2
FAIL  key id mismatch: 公钥与签名不是同一把钥匙（…）              exit=1   # 换一把公钥
```

`verify_release.py --production` 另有两道：缺 `--expect-pubkey` 直接拒绝；`manifest` 记录的指纹与期望不一致时拒绝。

### 端到端（QA 产物，非正式）

```
build_release_dir --updater-pubkey <QA> --allow-prerelease   → 写入 key id/指纹/来源
verify_release --expect-pubkey <QA> --signature-verifier …   → OK（含密码学验签）
```

## 四、没有做的事

- 没有创建/修改任何 Tag、Release；v3.3.1 资产未动；官网仍指向 v3.3.1。
- 没有生成任何正式密钥（按任务要求由维护者本机生成）。
- 没有执行真正的正式 Dry Run：`release` 环境与正式密钥尚不存在，状态见 `PRODUCTION-SIGNING.md` §5。
