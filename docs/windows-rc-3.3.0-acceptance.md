# v3.3.0 Windows x64 候选包验收记录

**状态：等待候选包 CI 及 Windows 实机检查，未通过正式发布门槛。**

候选构建由 [Windows CI](../.github/workflows/windows-rc.yml) 以 Python 3.12、Node 24、Rust 1.98.1、固定 Python Windows 快照、签名的 Microsoft VC143 运行库生成。工作流**只上传有时效的 GitHub Actions Artifact**，不自动打 Tag、签名或创建 Release。

## A. 自动候选检查（填写本次实际输出）

| 字段 | 结果 |
| --- | --- |
| 源码提交 SHA | NOT_TESTED |
| Actions Run URL | NOT_TESTED |
| Windows 后端 pytest | NOT_TESTED |
| Windows 前端测试/类型检查 | NOT_TESTED |
| PyInstaller sidecar / Tauri / NSIS | NOT_TESTED |
| 安装包文件名、字节数 | NOT_TESTED |
| 安装包 SHA-256 | NOT_TESTED |
| Microsoft VC143 DLL 签名/哈希 | NOT_TESTED |
| Artifact manifest | NOT_TESTED |

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
