# 隐私与数据处理说明

## 本地保存

桌面版在当前 Windows 用户的应用数据目录保存 SQLite 历史、AI 会话、设置和备份。正式版沿用 Stable v3.2.0 的应用标识 cn.yijing.workbench，应用数据目录因此与现有 SQLite 历史、AI 会话、设置和备份相同。v3.2.2 的数据库迁移模块与 v3.2.0 基线一致；正式版预期原位使用现有数据库，不复制或删除旧数据。安装包不包含个人 SQLite 数据库、API Key、用户设置或备份。用户可在应用内查看、删除或备份相应记录。

Windows 后端作为 sidecar 在本机回环地址运行。设置中的 API Key 通过本地接口交给后端，并由当前 Windows 用户 DPAPI 保护后保存在 SQLite；密钥不回显给前端。

## DeepSeek 联网功能

AI 为可选功能。读取模型列表、测试连接或校验模型时，应用会将 API Key 作为 HTTPS Bearer 身份验证信息发送至 DeepSeek，这些操作不发送卦象问题或聊天内容。

AI 对话请求会发送本条消息、当前起卦问题和所选模式的卦象/资料上下文，以及当前 AI 会话此前的消息；API Key 同时作为 Bearer 身份验证信息发送，不作为提示词内容。其他历史会话和整个 SQLite 数据库不会自动上传。回答与会话记录保存在本机 SQLite。DeepSeek 对服务端请求数据的处理与留存遵循其适用的开放平台条款；应用不承诺服务方不会保存。

应用在发生 DeepSeek 请求前说明数据范围并请求用户确认。拒绝后不会连接 DeepSeek；铜钱起卦、手动起卦、排盘和本地历史可继续使用。

## Microsoft Edge WebView2

桌面界面使用 Microsoft Edge WebView2，应用未关闭默认启用的 Microsoft Defender SmartScreen。SmartScreen 可能向 Microsoft 发送用户信息用于信誉检查。WebView2 可选诊断数据受 Windows“诊断和反馈”设置控制；必要的可靠性和性能数据仍可能收集。Microsoft 文档还说明 WebView2 进程崩溃时可能向 Microsoft 发送崩溃转储用于诊断。若设备缺少 Evergreen Runtime，NSIS 安装程序会联网下载并运行 Microsoft 官方 bootstrapper。

相关政策与说明：

- [DeepSeek 隐私政策](https://cdn.deepseek.com/policies/en-US/deepseek-privacy-policy.html?locale=en_US)
- [DeepSeek 开放平台服务条款](https://cdn.deepseek.com/policies/en-US/deepseek-open-platform-terms-of-service.html)
- [Microsoft WebView2 数据与隐私](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/data-privacy)
- [Microsoft 隐私声明](https://privacy.microsoft.com/privacystatement)

本文件说明 3.2.2 源码中的数据处理行为。安装路径、安装覆盖和首次启动必须由最终安装包在隔离 Windows 环境中验证；本地准备阶段未打开或修改 Stable 用户数据库。
