# 易经起卦工作台 v3.3.3

## 修复：安装包缺少桌面主程序

- 修复 v3.3.2 安装包只包含发布校验器、没有 `yijing-workbench.exe` 的问题。全新安装和从 v3.3.1 覆盖升级后都能正常启动桌面应用。
- 根因是新增签名校验器后 Cargo 出现两个可执行目标，Tauri 打包时误选了校验器作为主程序。现在显式声明 `default-run` 与两个 bin，并把校验器隔离在 `verify` feature 之后，不再参与正常打包。
- 发布门禁新增安装包内容检查：直接读取 NSIS 容器，确认包含 `yijing-workbench.exe` 与 Python sidecar，且不夹带仅用于发布校验的 `verify-updater-signature.exe`。7-Zip 不可用或读取失败时拒绝发布，不会静默跳过。

## 数据安全与升级路径

- 覆盖安装保留历史记录、偏好设置与 DPAPI 保护的 API Key；安装前仍会自动创建 SQLite 一致性备份，备份失败即取消安装。
- 安装模式仍为 currentUser（无需管理员），应用标识 `cn.yijing.workbench` 不变。
- v3.3.1 及更早版本没有更新器，升级到 v3.3.3 需要手动安装一次；从 v3.3.3 起可自动升级。
- v3.3.2 发布包无法启动，如曾下载请直接使用 v3.3.3 覆盖安装，数据不受影响。

## 隐私说明

应用有两类联网行为：主动调用 AI 时的 DeepSeek 请求，以及更新检查时的 GitHub 请求。更新检查只发送版本信息，不包含卦象、历史、设置或 API Key。详见 `PRIVACY.md`。

## 已知限制

- 安装包未做 Windows Authenticode 代码签名，首次运行仍可能出现 SmartScreen 提示。
- 未实现自动回滚；安装失败时旧版本与数据库均保留，可按 `docs/updater/README.md` §9 人工恢复。
