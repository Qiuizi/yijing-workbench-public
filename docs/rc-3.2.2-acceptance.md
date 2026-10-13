# RC 3.2.2 构建与验收记录

## 源码与安装包

- RC worktree 基于 v3.2.0 / 0542aa5cf95f3936fd9e399d2a8f0618a4fa1671；RC 3.2.2 候选源码含 15 个未提交文件变更。
- 原始 RC manifest 的 15 个变更文件哈希均与实际源码匹配。
- 构建时间：2026-10-13T01:57:11Z。
- 安装包版本：3.2.2，文件版本 3.2.2，未签名。
- 安装包大小：15,456,941 bytes。
- 安装包 SHA-256：F43D52AFF7B25CA9847CAC6E84D04B80C01060294BBFAE0B1DF5110B88FC8A73。
- 随包 hexagrams.json SHA-256：FD64BEF37318451ED75346F6AD7AE28B18103A85623426997CB3E17902460F9D。
- 随包 LICENSE 与 THIRD_PARTY_NOTICES 哈希分别为 A45F093B58D0E34E745A65FE170D10C1B6DE18D284DD30837A8B5C88F5D5A721、20647C04F9C9FAD59C730EB513AF38E6ED2231BB20F49FF1FD9BE855EA943148。
- 原始 manifest 记录安装包内无历史 SQLite 数据库，且源码、dist、主程序与 sidecar 的凭据模式扫描无命中；未读取真实 API Key。

## 自动化验证

本任务对与 RC 源码逐文件哈希匹配的 worktree 重新执行：

- 后端 pytest：165 passed。
- 前端 Vitest：44 passed。
- Vue TypeScript 类型检查：通过。

RC 原始 manifest 还记录 Vite 生产构建和 Tauri NSIS Release 构建通过。该构建复用了既有 Cargo Release target 和未变化的 sidecar，不能视作从干净公开快照进行的正式构建。

## GUI 与安装状态

用户在本任务中确认 RC 3.2.2 已完成 6/6 项手工 GUI 验收，按用户报告记录为 PASS。未在本快照定位逐项清单或截图，因此不补写项目名称或时间。

原始构建 manifest 在构建时记录 guiRc322=NOT_TESTED、actualInstallOrLaunch=NOT_TESTED；它还明确说明 RC 3.2.1 的 GUI 验收不适用于 RC 3.2.2。上述状态是原始清单的历史记录，本文件保留并注明用户后续确认，不改写原始 manifest。

本次未对正式标识构建进行安装或启动验证。Windows Sandbox 不可用；Hyper-V 虚拟机枚举因本机授权策略拒绝而未能读取。正式包必须在隔离 Windows 用户或虚拟机中实装并检查关键启动路径。
