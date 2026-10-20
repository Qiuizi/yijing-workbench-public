# v3.3.0 Windows x64 候选包验收记录

**状态：GitHub Windows 候选包 CI 已通过；隔离 Windows 实机安装/升级与 GUI/DPAPI 人工验收尚未完成，未通过正式发布门槛。**

候选构建由 [Windows CI](../.github/workflows/windows-rc.yml) 以 Python 3.12、Node 24、Rust 1.98.1、固定 Python Windows 快照、签名的 Microsoft VC143 运行库生成。工作流**只上传有时效的 GitHub Actions Artifact**，不自动打 Tag、签名或创建 Release。

## A. 自动候选检查（填写本次实际输出）

| 字段 | 结果 |
| --- | --- |
| 源码提交 SHA | 以 Actions Run 39292710601 的 `head_sha` 及随包 `manifest-rc.json` 为准；本记录不猜测具体哈希 |
| Actions Run URL | [39292710601](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39292710601) · completed/success |
| Windows 后端 pytest | PASS（GitHub job 的 Windows backend regression tests 步骤） |
| Windows 前端测试/类型检查 | PASS（Frontend regression tests / Typecheck） |
| PyInstaller sidecar / Tauri / NSIS | PASS（Build PyInstaller sidecar and Tauri NSIS candidate） |
| 安装包文件名、字节数 | 工作流已生成并上传未签名安装包；包内实际文件名与字节数须从 manifest 核对。Artifact 压缩包大小为 16,074,400 bytes，不等于安装包大小 |
| 安装包 SHA-256 | 已由 workflow 生成 manifest-rc.json，但尚未从 Artifact 独立读取具体哈希，待核对 |
| Microsoft VC143 DLL 签名/哈希 | PASS（workflow 的官方 VC143 CRT 签名校验；实际哈希尚未单独登记） |
| Artifact manifest | PASS（生成并上传步骤成功）；Artifact ID `12205683488`，大小 16,074,400 bytes，有效期至 2026-11-02 UTC。具体 manifest 内容待独立检查 |

自动构建的 PASS 只来自 GitHub Actions 作业状态和步骤结果，不能冒充在实体 Windows 账户执行了安装或升级。候选产物是有时效的 Artifact，尚未成为公开 Release。

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
