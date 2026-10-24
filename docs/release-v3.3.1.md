# 易经起卦工作台 v3.3.1 — Windows x64 正式发布

**此版本在维护者允许保留未实机验收项目的前提下发布，且已分别公开列出风险。正式发布不等于所有安装、升级及 GUI 项目都已通过。**

**下载：**[Windows x64 安装包（未签名）](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.1/yijing-workbench-3.3.1-x64-setup.exe) · [SHA256SUMS.txt](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.1/SHA256SUMS.txt) · [构建溯源 PROVENANCE.md](https://github.com/Qiuizi/yijing-workbench-public/releases/download/v3.3.1/PROVENANCE.md)。

## 主要变化：64 卦现代导读全部开放

- 依 [维护者明确批准 PR #35](https://github.com/Qiuizi/yijing-workbench-public/pull/35) 和 [批准决议记录](https://github.com/Qiuizi/yijing-workbench-public/blob/main/docs/learning-guides-review-05-64.md)，**第 01–64 卦共 64 篇现代导读和 384 条逐爻说明均获编辑发布批准**。此前 v3.3.0 的 05–64 卦显示“导读整理中”；v3.3.1 重新构建后可通过原有审批双门槛展示全部 64 卦。
- **注意证据边界**：`reviewed` 在项目中表示维护者批准内容公开，不意味着王弼、孔颖达、朱熹两种传统注释中全部 420 个待核对位置的底本、影印版本和异文已经完整校勘。已知文献证据缺口仍在 [Issue #28](https://github.com/Qiuizi/yijing-workbench-public/issues/28)。
- 复核并修订《小畜》九五“富以其邻”、《泰》九二“用冯河”、《大过》九二“稊/梯”字形与注释归属；另替换 33–44 卦 25 条重复模板化收尾，全部已经在 [PR #33](https://github.com/Qiuizi/yijing-workbench-public/pull/33)、[PR #34](https://github.com/Qiuizi/yijing-workbench-public/pull/34) 合入。
- **未更改** 64 卦古籍经典经文、历史 SQLite 数据模型、DPAPI 密钥保存机制、原有用户数据及 DeepSeek 联网策略。
- 版本从 3.3.0 同步更新到 **3.3.1**（Node/Tauri/Cargo/FastAPI、Windows 打包 manifest），保留同一应用 identifier `cn.yijing.workbench`，采用 NSIS 当前用户安装。

## 验证范围：已通过

- [Windows main CI run 39995846568](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39995846568) 为正式主分支 `push`，构建源码为 `f6f102f1f87bcc6aebba0ad7eac822ad9b25e882`；completed/success。
- Windows 2022 runner 上的 Python 后端 pytest、前端 Vitest、TypeScript 类型检查、PyInstaller sidecar、Tauri NSIS 打包和微软 VC143 运行库签名验证均成功。
- **打包后的** Windows Python sidecar 在隔离**合成数据**配置下测试健康鉴权、缺失/错误 API Token 返回 401、64 卦目录、空白历史：PASS；未读取真实用户数据。
- 代码与台账的门控测试：**64/64 `reviewed`、64/64 独立批准台账记录**，缺少某一门槛仍须隐藏。
- 从 run 39995846568 下载的原始安装包经**独立字节级 SHA-256 复算**，与 Manifest 完全一致。正式 Release 仅将原文件中文文件名更换为 ASCII 名称，安装程序内容字节不变。

## 已知风险 / NOT_TESTED

以下内容**未完成实机验收，不可视为通过**：

- 此 v3.3.1 NSIS 安装包在真实 Windows 环境中的安装与完整应用 GUI、关于页显示、原生 Markdown 保存框与文件实际落盘、打包版应用重复启动。
- 从 v3.2.2 或 v3.3.0 **覆盖升级**、卸载、回滚、旧数据恢复和跨用户 DPAPI 凭据隔离。
- 用户真实 DeepSeek 密钥联网调用与系统级行为。

**升级前请先备份应用的 SQLite 历史、配置与重要导出文件，并在关闭旧程序后再运行安装程序。** 已发布的 [v3.3.0](https://github.com/Qiuizi/yijing-workbench-public/releases/tag/v3.3.0) 继续保留供希望暂不升级的用户使用；此版本的旧安装程序原样不改。安装包未做代码签名，Windows 可能提示未知发布者或 SmartScreen；运行需要 Microsoft Edge WebView2 Evergreen Runtime。

## 安装包真实身份

| 项目 | v3.3.1 |
| --- | --- |
| Release EXE | `yijing-workbench-3.3.1-x64-setup.exe` |
| 原始 CI EXE | `易经起卦工作台_3.3.1_x64-setup.exe` |
| 文件大小 | **16,097,113 bytes** |
| SHA-256 | `3CAECBE2CE7684805BA5FBE2D8F60767101CCD71565A4EC37BACB2181B086B74` |
| 二进制构建源码 | `f6f102f1f87bcc6aebba0ad7eac822ad9b25e882` |
| Windows CI | [run 39995846568](https://github.com/Qiuizi/yijing-workbench-public/actions/runs/39995846568) |
| GitHub Release Tag | `v3.3.1`（Tag 指向后续只加入发布说明和流程的提交，**不是**二进制构建 SHA） |
| 归档资产 | NSIS EXE、SHA256SUMS、原始 manifest-rc.json、sidecar-smoke.json、PROVENANCE.md |

原始 CI manifest 的 `status=unsigned-rc-not-manually-accepted` 及 `gui_upgrade_tested=false` **按当时真实测试范围保留**，不因正式发布而事后篡改历史。发布同意是编辑/版本交付决定，不是将未做的安装与古籍校勘工作认作已完成。

跟进问题：[Windows 验收 Issue #27](https://github.com/Qiuizi/yijing-workbench-public/issues/27)；[现代导读古注补校 Issue #28](https://github.com/Qiuizi/yijing-workbench-public/issues/28)。
