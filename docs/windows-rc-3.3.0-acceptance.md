# v3.3.0 Windows x64 候选包验收记录

**状态：GitHub Windows 候选包 CI 已通过；隔离 Windows 实机安装/升级与 GUI/DPAPI 人工验收尚未完成，未通过正式发布门槛。**

候选构建由 [Windows CI](../.github/workflows/windows-rc.yml) 以 Python 3.12、Node 24、Rust 1.98.1、固定 Python Windows 快照、签名的 Microsoft VC143 运行库生成。工作流**只上传有时效的 GitHub Actions Artifact**，不自动打 Tag、签名或创建 Release。

## A. 自动候选检查（填写本次实际输出）

| 字段 | 结果 |
| --- | --- |
| 源码提交 SHA | Artifact manifest 的 `source_sha=83028f50f0d75879b7294d6b7943dcf3d8fcff2c`（PR 触发时的 `GITHUB_SHA` 合并测试提交）；运行详情的分支 `head_sha=7be8f2464eb8b3505c5c4e0a2f1d0bd9e0b73080`。两者不是同一个 SHA；本候选不等于当前 main 构建 |
| Actions Run URL | [39292710601](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39292710601) · completed/success |
| Windows 后端 pytest | PASS：187 passed、1 warning（Actions job 原始日志） |
| Windows 前端测试/类型检查 | PASS：107/107 Vitest；Typecheck success（Actions job 日志） |
| PyInstaller sidecar / Tauri / NSIS | PASS（Build PyInstaller sidecar and Tauri NSIS candidate） |
| 安装包文件名、字节数 | `易经起卦工作台_3.3.0_x64-setup.exe`，EXE **16,089,518 bytes**；Artifact ZIP 16,074,400 bytes，分别独立计数 |
| 安装包 SHA-256 | **`6EBA34016332FAA0B761038929BFFF715D1CCBECDBA410348D1E096F6DC70EC8`**；已下载 Artifact ZIP 并对其中 EXE **独立计算 SHA-256，结果与 manifest 及 CI 日志三方一致** |
| Microsoft VC143 DLL 签名/哈希 | PASS（workflow 的官方 VC143 CRT 签名校验；实际哈希尚未单独登记） |
| Artifact manifest | **已下载核验**：Artifact ID `12205683488`，ZIP 大小 16,074,400 bytes，保留至 2026-11-02 UTC；manifest `version=3.3.0`、`install_mode=currentUser`、`status=unsigned-rc-not-manually-accepted`；sidecar SHA-256 为 `83AB9E7E5FE4AE88304B8C82EE6F3B19B7ABF7C1903ECEF06EC847375116CCF6`（sidecar 未单独提取复算） |

本记录中的运行状态、测试数量来自 [GitHub Windows Run 39292710601](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39292710601)。2026-10-20 下载 Artifact ZIP 后，已实际读取包内 manifest 并独立对 EXE 重新计算 SHA-256：**结果与 manifest、CI 日志一致**。特别注意 PR 合并测试提交的 `source_sha` 与 PR `head_sha` 的差异，发布不得偷换为当前 main 已复验。自动构建的 PASS 只来自 GitHub Actions 作业状态和步骤结果，不能冒充在实体 Windows 账户执行了安装或升级。候选产物是有时效的 Artifact，尚未成为公开 Release。

## A2. 更新内容后的最新候选核验（2026-10-20）

上文 A 表格记录的是 PR #14 的候选产物，不能与后续构建混为一谈。PR #15、PR #16 内容修订已合并到主分支（主分支源码合并 SHA 分别为 `8d2603cb3185326174b2a711e86cb7db069c285f`、`85ee5da906c7ab18e9766e4680587b89b144b681`）。

对 PR #16 的 Windows 工作流 [Run 39348813774](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39348813774) 已核实：

| 字段 | 结果 |
| --- | --- |
| CI / 测试 / 构建 | `completed/success`：Windows Python 回归、前端测试、类型检查、VC143 验证、PyInstaller/Tauri/NSIS、Artifact 上传均成功 |
| 下载的 Artifact | `yijing-workbench-3.3.0-windows-x64-unsigned-rc`，Artifact ID `12232527619`，ZIP 16,079,482 bytes，保留至 2026-11-03 UTC |
| 安装包文件 | `易经起卦工作台_3.3.0_x64-setup.exe`，16,094,605 bytes |
| EXE SHA-256 | `A1C566C4D602CE6F7BD46F8F6AD9192406C4C35BCBDE1F78F9F306B56B0052F1` |
| 二次核验 | 下载 GitHub Artifact ZIP，读取 `manifest-rc.json` 并独立对 ZIP 内 EXE 计算 SHA-256，文件大小和哈希与 manifest 完全一致 |
| manifest `source_sha` | `32c8d07db0a4193f9cf2dd30877855558fe9413c`，这是 **pull_request 触发的测试合并提交**，不是 PR 分支 head 或最终 main 合并提交 |
| sidecar SHA-256 | `7DE9A5F56C9E101E19E9F74A0657A38EE0D2F02C0394C078FF46DB20B661C0AA`（只记录 manifest 数值，未独立提取 sidecar 二进制复算） |
| 发布状态 | `unsigned-rc-not-manually-accepted`：未签名、尚无实体 Windows 新装/升级、GUI、DPAPI 人工验收；**不得作为正式 Release** |

**注意：**此候选证明 PR #16 的临时测试合并树可以在托管 Windows 环境构建。正式 Release 必须从指定的正式源码提交重新构建，或有明确的同一源码/二进制验证及人工安装升级验收；不能把此 Artifact 自动标记成已经验收的 v3.3.0。

## A3. 自动验收覆盖扩充：主分支可追溯候选与 sidecar 启动

2026-10-20 起，Windows RC 工作流新增 **`push` 到 `main`** 的自动构建路径。先前仅有 `pull_request` 构建的 `GITHUB_SHA` 为合并测试提交，不能直接说成最终 main 构建。新增的 `manifest-rc.json` 会记录 `source_trigger`、`source_ref`、`source_sha`、PR head 及 `sidecar_smoke` 状态。仅当 `source_trigger=push`、`source_ref=refs/heads/main` 且 SHA 与 GitHub main 指定提交一致时，才可称为基于正式主分支的候选构建。

还将启动**打包后的** `yijing-backend.exe` 并使用一次性合成数据库执行 loopback API 冒烟验收：带令牌健康接口 200、无令牌/错误令牌 401、64 卦目录完整、私有历史为空。导出的 `sidecar-smoke.json` 随 Artifact 保存；不写个人 SQLite 或 API Key。

**当前状态：新流程的主分支运行尚待 GitHub Actions 实际 completed/success；不得提前填写通过。** 即使以上成功，也不会自动做安装器 GUI、WebView2、DPAPI、历史升级或卸载检查。它们仍属下方 B 的人工验收。

## B. 隔离 Windows 账户的人工验收（不可由 Linux/CI 自动推断）

使用测试账户及**合成**占卜历史，先备份，绝不上传私人的 SQLite、API Key 或 DPAPI 密文；不替换主账户正在使用的稳定版。

- [ ] 全新安装：验证 NSIS 仅当前用户安装、WebView2 依赖处理、开始菜单与实际启动
- [ ] 从 3.2.2 升级到候选 3.3.0：对比合成历史数量、占问/排盘/AI 会话、设置，重启后复核
- [ ] 核实关于页版本、许可证、第三方声明、隐私说明
- [ ] 铜钱和手动起卦、变爻、传统取辞、六爻纳甲、乾用九/坤用六均正确
- [ ] 图鉴目录全部 64 卦可查、原文六爻可见；仅批准导读可见、未批准 60 卦不显示草稿
- [ ] 关键词搜索、AI 条件筛选、分页、删除后翻页、详情返回状态正常
- [ ] Markdown 导出：保存/取消/覆盖/中文路径/不可写路径/真实落盘，检查内容没有密钥
- [ ] 断网时仍可起卦、读原文和访问本地历史；联网 AI 仅在主动调用时访问网络
- [ ] 正常退出、再次启动、卸载；源稳定版与测试用备份可恢复

## C. 最终发布判定

只有 A 真实通过、B 有独立记录，且候选安装包与计划 Release 使用**同一 SHA-256**，才可更新发布说明并创建正式 v3.3.0 Tag/Release。未完成前必须继续使用“候选包 / 未验收”措辞。

学习导读中除已批准的前四卦以外，其余 60 卦能否上线是**独立于桌面软件构建**的学术内容审定任务，参见 [批准门槛](learning-approval-policy.md)。
