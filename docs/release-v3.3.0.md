# 易经起卦工作台 v3.3.0 — Windows x64 正式发布

**⚠️ 维护者明确接受尚未完成的安装包实机验收后发布（2026-10-23）。这是一项风险接受决定，绝不表示未执行的测试已经通过。**

**下载：**[Windows x64 安装包（未签名）](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/yijing-workbench-3.3.0-x64-setup.exe) · [SHA256SUMS.txt](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/SHA256SUMS.txt) · [原始候选构建 Manifest](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.0/manifest-rc.json)

## 新功能

- **六十四卦图鉴**：按文王序浏览全部 64 卦、原始卦辞与爻辞、乾用九与坤用六；可检索，目录分上经 30 和下经 34。
- **有审核门控的现代导读**：已获批准、可公开显示的仅 01–04 卦；05–64 卦为 `draft`，仅显示古籍原文与“导读整理中”，**不公开未批准的现代解释**。
- **Markdown 导出**：单条起卦结果及已有排盘可导出本地 UTF-8 Markdown，不包含密钥与 AI 会话。
- **历史记录改进**：服务端关键字搜索、按有无 AI 会话筛选、20 条分页、详情返回状态恢复与删除后翻页。
- **关于页与许可说明**：嵌入 MIT LICENSE 内容，区分自有代码、古籍与第三方许可。
- 保留铜钱/手动起卦、传统取辞、六爻纳甲、SQLite 历史和可选 DeepSeek 解读。无需 AI 密钥也能使用本地功能。

## 已通过的检查

- [Windows CI run 39373256162](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39373256162)：真实 `push(main)`，源码 `e5f613c5456cbd1dbb428c73bfb5234747133fb9`；Windows 后端、前端、类型检查、VC143 运行库签名校验、PyInstaller sidecar、Tauri NSIS 打包均 PASS。
- **打包后的** Python sidecar 使用一次性测试数据启动，健康检查、无令牌/错误令牌拒绝、64 卦目录及空白历史 PASS。
- 2026-10-23 轻量验收：与该源码一致的后端合成数据 **21/21 PASS**、DPAPI 合成密钥 **5/5 PASS**、源码 Vite GUI 功能测试 PASS，原有用户数据归位后逐文件哈希 0 差异。
- 本地源码回归：pytest **188 passed**、Vitest **107 passed**、TypeScript 与 Vite build 通过。这些不替代安装包本体的测试。

## 未测试、已明确接受的发布风险

**以下均为 NOT_TESTED，而非 PASS：**

- 此发布的 **v3.3.0 安装程序本体**在真实 Windows 上的完整 GUI 启动、关于页与许可证显示、原生文件保存对话框和 Markdown 实际落盘、打包版多次重启
- Windows 全新安装、v3.2.2 → v3.3.0 覆盖升级、卸载、回滚与数据恢复演练
- 跨 Windows 用户账户的 DPAPI 凭据隔离；实际密钥联网 DeepSeek 调用

**安装前务必备份应用数据和重要历史记录，关闭旧版本再安装。** 当前沿用应用标识 `cn.yijing.workbench` 和当前用户安装方式；虽然代码未修改数据库迁移模块，但没有实际验证 v3.2.2→v3.3.0 覆盖安装或数据保留。需要更保守的版本可继续使用 [v3.2.2](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.2.2)。

安装程序**未做代码签名**，Windows 可能提示未知发布者/SmartScreen；缺少 WebView2 Evergreen Runtime 的机器可能需要联网安装官方运行库。DeepSeek 需用户自行提供密钥，只有主动调用时联网。

## 可复核构建来源

| 字段 | 值 |
| --- | --- |
| Windows 安装包 | `yijing-workbench-3.3.0-x64-setup.exe`（只将原中文安装包改为英文文件名，字节内容不变） |
| 大小 | **16,096,623 bytes** |
| SHA-256 | `0620A0497C76B25524275F21516F7D69A5AC2291BD362F8094F99E267693EBC8` |
| 打包源码提交 | `e5f613c5456cbd1dbb428c73bfb5234747133fb9` |
| 发布 Tag | `v3.3.0`，额外只纳入发布文档和发布工作流；**与二进制源码 SHA 不相同** |
| 构建链接 | https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39373256162 |
| 资产 | 安装包、`SHA256SUMS.txt`、未改写的 `manifest-rc.json`、`sidecar-smoke.json`、`PROVENANCE.md` |

原始 `manifest-rc.json` 中 `status=unsigned-rc-not-manually-accepted` 和 `gui_upgrade_tested=false` 保持不变。这反映**构建时真实测试范围**；正式发布是维护者随后明确接受未验证风险的决定，不会篡改旧证据。

验收和发布后仍待改进的内容见 [Issue #27](https://github.com/Qiuizi/yijing-workbench-public/issues/27)；其他 60 卦导读仍须逐卦审核，见 [Issue #28](https://github.com/Qiuizi/yijing-workbench-public/issues/28)。源码、第三方许可及隐私说明见仓库 [README](https://github.com/Qiuizi/yijing-workbench-public)。
