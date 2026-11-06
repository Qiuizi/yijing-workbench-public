# RELEASE-HISTORY — 真实发布历史

> 数据来源：GitHub Releases / Tags / Actions 实时查询（[evidence/releases.json](evidence/releases.json)、[evidence/latest-release.json](evidence/latest-release.json)、[evidence/recent-runs.json](evidence/recent-runs.json)、[evidence/artifacts.json](evidence/artifacts.json)）。
> 资产摘要均为 GitHub API 记录的 `sha256`。

## 0. 总览

| 版本 | 类型 | Tag | 公开 Release | 安装包 | 状态 |
| --- | --- | --- | --- | --- | --- |
| v3.2.2 | 正式发布 | `v3.2.2` | ✅ 2026-10-13 | 15,428,837 B | 可用（旧版，无更新器） |
| v3.3.0 | 正式发布（风险自担） | `v3.3.0` | ✅ 2026-10-23 | 16,096,623 B | 可用（无更新器） |
| v3.3.1 | 正式发布 | `v3.3.1` | ✅ 2026-10-24 | 16,097,113 B | 可用（无更新器） |
| v3.3.2 | 正式发布 | `v3.3.2` | ✅ 2026-11-02 | 13,469,345 B | **P0：缺失主程序，不可用** |
| v3.3.3 | Candidate / QA | 无 | ❌ 无 | 16,994,357 B（Artifact 内） | 未发布；正式签名未生成 |

**最新公开 Release = v3.3.2**（`releases/latest`，id `431706476`，published 2026-11-02T16:39:53Z）。`v3.3.3` 不存在任何公开 Release，也不存在 `v3.3.3` Tag（远端标签仅 4 个：v3.2.2 / v3.3.0 / v3.3.1 / v3.3.2）。

---

## 1. v3.2.2（历史基线）

- Release id `411641657`，published 2026-10-13T12:18:18Z。
- 安装包 `yijing-workbench-3.2.2-x64-setup.exe`：15,428,837 B，SHA-256 `b594507662d2b0263d1909972211f26b088b26ea182065c96b54b53889ab9f8f`。
- 附带 LICENSE、PRIVACY、DATA_SOURCES、ICON_PROVENANCE、THIRD_PARTY_NOTICES、manifest、SHA256SUMS、ReleaseNotes。无更新器签名。

## 2. v3.3.0（正式发布，明确接受未完成实机验收）

- Release id `422014163`，published 2026-10-23T15:36:52Z，对应 PR #30。
- 安装包：16,096,623 B，SHA-256 `0620a0497c76b25524275f21516f7d69a5ac2291bd362f8094f99e267693ebc8`。
- 资产含 `manifest-rc.json`、`PROVENANCE.md`、`SHA256SUMS.txt`、`sidecar-smoke.json`（`4573383306045334598586f669e4947fca4859cdcb1b33c52de2ecf06a061cc9`）。
- 发布说明明确「接受未完成的 Windows 实机验收」；无更新器、无 `.sig`。

## 3. v3.3.1（正式发布，64 卦导读获批）

- Release id `422493471`，published 2026-10-24T03:35:24Z，对应 PR #37（Tag 提交 `dc21dab`）。
- 安装包：16,097,113 B，SHA-256 `3caecbe2ce7684805ba5fbe2d8f60767101ccd71565a4ec37bacb2181b086b74`。
- 构建来源：main push 构建 Run `39995846568`，二进制源码 `f6f102f1f87bcc6aebba0ad7eac822ad9b25e882`；发布 Tag 是之后仅增补文档/工作流的提交，差异已写入发布说明。
- 无更新器（v3.3.1 用户升级到 v3.3.2 需手动安装一次）。
- 附 `sidecar-smoke.json`；无 `.sig`。

## 4. v3.3.2（最新正式发布 —— 但安装包 P0 缺陷）

### 4.1 发布事实

- Release id `431706476`，published 2026-11-02T16:39:53Z，Tag `v3.3.2` → `a4982e0b17a13258488d1f9be472b729ffb7302e`。
- 构建：`Publish stable release` Run `41479457847`（success）。staging Artifact `13158704072`（digest `sha256:18e0dc211867e7d2dd594a42b4b0dd4f1c17ddf5d048c840e44859452592a9ae`），production-signed Artifact `13160435971`（digest `sha256:36284ecd725dae6737748786a75b1c1514355804af165096dcaaf487afc7da46`）。
- 公开资产：

| 资产 | 大小 | SHA-256 |
| --- | --- | --- |
| `yijing-workbench-3.3.2-x64-setup.exe` | 13,469,345 | `bda356afe6ff63086df1608110389067a70a051cdfa187f5ce23e655f273d999` |
| `.exe.sig`（正式 Tauri 更新签名） | 448 | `ddf528d56e2fab949103021d59170ed16acf116f82618567ecc09657791c4f7f` |
| `latest.json` | 2,357 | `af9ca00b502bf3beff50666b4a65a802467683621a6f8636b1c71624745a7b2e` |
| `manifest.json` | 1,073 | `c64d932cc60d47ad0a2b135fadc591dba7ab8175287dbb84e22f64eaaa90e644` |
| `PROVENANCE.md` | 327 | `9fd025a27d4ef91876bf18bb8b0605efd8887f1b2d3316ec62f8b3a5f896b8ae` |
| `SHA256SUMS.txt` | 104 | `eeb452eca2e2f1cd8703dd65f8630235569ad99f749c3c25b520d3f68f961493` |

### 4.2 P0 缺陷（已确认）

公开的 v3.3.2 安装包**只包含 `verify-updater-signature.exe` 与 sidecar，没有主程序 `yijing-workbench.exe`**：

- 全新安装退出码 0，但启动路径不存在；v3.3.1 覆盖升级到 v3.3.2 后主程序消失。
- 根因：`Cargo.toml` 新增第二个 `[[bin]]`（签名校验器）后未显式设置 `default-run`，Tauri 打包选了错误的 bin。
- 修复：PR #61（`fix(ci): ship the desktop binary in NSIS installers`，2026-11-04 合并，`c851e50`）+ PR #62（`release: prepare v3.3.3 installer packaging fix`，2026-11-05 合并，`b9e2fad`），已合入 main `932f039`。**修复未发布。**
- 完整调查与证据：`docs/qa/post-release-qa-3.3.2.md`（47 PASS / 3 FAIL / 4 未执行）。

### 4.3 发布过程中的失败尝试（未产生对外 Release）

`Publish stable release` 工作流在 v3.3.2 定稿前后有多次失败运行，属于发布链路的调试，均未覆盖已发布的 v3.3.2 资产：

- `41223140848` failure（2026-10-31）
- `41276444581` failure（2026-11-01，签名 provenance）
- `41324078512` failure（2026-11-01，publish 门禁）
- `41312532445` failure（2026-11-01，V1 learning CI）
- `41469631244` failure（2026-11-02，draft 查询）

同期的成功 dry-run/签名运行（如 `41319836661`、`41290566377`、`41292953564`）只为演练，不改变公开资产。

## 5. v3.3.3（Candidate / QA，未发布）

### 5.1 构建与 Candidate

| 项 | 值 |
| --- | --- |
| 版本来源 | main `932f0390…b1ce5` |
| Candidate Build Run | `41955823250`（`Windows x64 candidate build`，success，attempt 1） |
| Candidate Artifact | `13383072964`，16,984,522 B，digest `sha256:f5481c1cfc2f6a4e9d51713df6000ac9c20d77455f06ae5cebc420fdd553fc00`，到期 **2026-11-19T02:43:13Z** |
| 安装包（Artifact 内） | `yijing-workbench-3.3.3-x64-setup.exe`，16,994,357 B，SHA-256 `0bedceaa5eec581e92897e9a4856eb55017609168a5ab42aa33110d745312a38` |
| 主程序 | `yijing-workbench.exe`，SHA-256 `6f61808d0503364b7edc5ea6fed679c334ef579271ca57bd2d0c00df4796bfff`，FileVersion `3.3.3` |
| Sidecar | `yijing-backend.exe`，SHA-256 `cc88f977238b61fe8fd51d27c13cd2f994939164f9abbb19ad59234a81475948` |
| NSIS 内容 | 747 项；有主程序与 sidecar；**无** `verify-updater-signature.exe` |
| 签名 | `signing_mode=ephemeral_candidate`，临时 Candidate 密钥（Key ID `36F737BF65941C82`），**不是正式生产签名** |

另有 release 分支 `release/v3.3.3`（`b9e2fad`）的 Candidate 构建 Run `41867079418`，Artifact `13344156064`（digest `sha256:959e3ecb4f06db1eeb22b5cc97d3c225db0e38db8484c07494b5400441ee51d9`），仅作对比。

### 5.2 QA / 验收运行

- QA Candidate 验收（`QA candidate acceptance (temporary)`）：`42031937030`、`42032346331`、`42032895209`、`42033479080`、`42042680743`、`42042741115` 均 success；`42032732349` failure（中间调试运行，已被后续成功运行取代）。
- 详见 [QA-ACCEPTANCE.md](QA-ACCEPTANCE.md)。

### 5.3 发布演练

| 运行 | 内容 | 结果 |
| --- | --- | --- |
| `42032014347` | 未签名 Dry Run（`dry_run=true`，`exercise_production_sign=false`） | **success**；Build/Verify/Attest staging 通过；Production-sign/Verify signed/Attest signed/Publish 按预期 skipped；无副作用 |
| `42033806115` | 正式签名演练（`dry_run=true`，`exercise_production_sign=true`） | 构建与 staging 成功（Artifact `13418007574`，digest `sha256:8af63639b49ebbf7570c5ce2195f7d893aaae10fb114805691187b2b385995ea`，到期 2026-11-19T13:23:20Z）；`production-sign` 停在 `release` Environment 等待审批；**2026-11-06T10:05:08Z 由本轮冻结取消，conclusion=cancelled** |

### 5.4 未发布结论

- v3.3.3 **没有** Tag、**没有** Release、**没有**正式签名产物、**没有**官网入口更新。
- 官网下载入口仍指向 v3.3.2（见 [evidence/website-observation.json](evidence/website-observation.json)，站点脚本中版本字符串为 `3.3.2`）。

## 6. QA / 临时版本（不构成发布）

- `YijingWorkbenchUpdaterQA` 3.3.1 / 3.3.2 / 3.3.3、`cn.yijing.workbench.v333qa`、`cn.yijing.workbench.updaterqa` 等均为隔离 QA 应用标识与临时 QA 密钥的测试构建，**从未公开发布**，也**不得**当作正式版本。
- 重建的 3.3.2 QA 基线包：16,995,165 B，SHA-256 `f6009a211577d159904de6cd303bf0a361f4e4a7cd0187d33dfe521ac457d896`（`YijingWorkbenchUpdaterQA_3.3.2_x64-setup.exe`）。
