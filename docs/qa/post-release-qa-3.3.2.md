# 易经起卦工作台 v3.3.2 发布后 QA 报告

- 日期：2026-11-04
- 仓库：`Qiuizi/yijing-workbench-public`
- 验收基线：`main` @ `2bdc19afbe68703b439ddfee28520b1606652900`；Release/Tag `v3.3.2`；发布构建 `a4982e0b17a13258488d1f9be472b729ffb7302e`
- 修复分支：`fix/v3.3.2-installer-main-binary` @ `084cbc5`
- 最终状态：**POST_RELEASE_QA_FAILED**

## 1. 结论

正式发布的 v3.3.2 Windows 安装包无法使用：签名与 SHA-256 均正确，但 NSIS 安装包内没有主程序 `yijing-workbench.exe`，只有发布门禁工具 `verify-updater-signature.exe`。全新安装和 v3.3.1 → v3.3.2 覆盖升级后都没有可启动的应用。

这是发布构建的 P0 缺陷，因此本次发布验收判定为 **FAILED**。修复已提交到独立分支并推送，但未发布新 Release、未覆盖 v3.3.2 资产、未修改正式签名密钥。

除该 P0 外，修复构建上的核心业务、数据安全、自动更新流程和故障恢复均通过；另有 2 项 P2 使用体验问题，见第 6 节。

## 2. 测试环境与资产

| 项目 | 值 |
| --- | --- |
| 操作系统 | Windows 11 Pro 10.0.26100（真机，非虚拟机） |
| 显示 | 1560×1040 逻辑分辨率，200% 缩放；窗口截图被裁剪，UIA 驱动不受影响 |
| 运行时 | WebView2、Tauri 2.11.6、Python Sidecar（PyInstaller） |
| 官方 v3.3.2 安装包 | `yijing-workbench-3.3.2-x64-setup.exe`，13,469,345 字节，SHA-256 `bda356afe6ff63086df1608110389067a70a051cdfa187f5ce23e655f273d999`（与 Release 的 `SHA256SUMS.txt` 一致） |
| 官方 v3.3.1 安装包 | `yijing-workbench-3.3.1-x64-setup.exe`，16,097,113 字节，SHA-256 `3caecbe2ce7684805ba5fbe2d8f60767101ccd71565a4ec37bacb2181b086b74`（与 `SHA256SUMS.txt` 一致） |
| 修复构建（fixqa） | `fixqa-installer.exe`，16,996,022 字节，SHA-256 `fca5fccd193cb8324c510670d48a36666a52354c7f89c4f6d428a23a92b6db16`，包名 `YijingWorkbenchFixQA`，应用标识 `cn.yijing.workbench.fixqa` |
| 更新 QA 基线 | `YijingWorkbenchUpdaterQA` 3.3.1，应用标识 `cn.yijing.workbench.updaterqa`，安装目录 `.qa-work/v3.3.2/updater-qa/install-3.3.1` |
| 更新 QA 目标 | `YijingWorkbenchUpdaterQA` 3.3.3，16,995,587 字节，SHA-256 `aab99010335cd8053c24f33f7fb2ae3e7641c3626f82417ffb3eb4917b2ce3ff`，使用临时 QA 密钥签名 |
| 更新服务 | 本地 `http://127.0.0.1:8788`，限速 480 KiB/s，支持 500/断连故障注入 |

## 3. 方法与隔离声明

- 所有安装都使用 `/D=` 指向 `.qa-work/v3.3.2/` 下的隔离目录；应用数据分别落在 `%LOCALAPPDATA%\cn.yijing.workbench.fixqa` 和 `%LOCALAPPDATA%\cn.yijing.workbench.updaterqa`。
- **未启动官方应用，未打开、复制或修改真实数据库 `%LOCALAPPDATA%\cn.yijing.workbench\history.sqlite3`**；官方安装包的安装/升级测试只操作安装目录与隔离注册表项。测试前只列出该目录以确认隔离边界，未读取任何数据内容。
- 后端 API 测试使用安装包内真实 sidecar、隔离数据库副本和独立测试令牌；测试 API Key 为运行时拼接的无效 Key，未使用任何真实密钥。
- UI 测试使用 Windows UI Automation 驱动真实 WebView2 窗口；未使用静态代码检查代替安装/运行测试。
- 模拟更新使用临时 QA 密钥对、独立应用标识和本地 HTTP 服务；正式签名密钥与 v3.3.2 资产未被修改。3.3.3 不是正式发布版本。
- 未宣称自动回滚：代码与 `docs/updater/README.md` §10.4 均明确「无自动回滚」，本报告的故障恢复结论以此为准。

## 4. 结果总览

手工/实机验收用例共 **54** 项：**47 通过 / 3 失败 / 4 未执行**。

| 阶段 | 用例 | 通过 | 失败 | 未执行 |
| --- | ---: | ---: | ---: | ---: |
| 阶段 1 安装包验收 | 10 | 7 | 3 | 0 |
| 阶段 2 核心业务回归 | 14 | 12 | 0 | 2 |
| 阶段 3 数据安全 | 7 | 6 | 0 | 1 |
| 阶段 4 自动更新 | 15 | 15 | 0 | 0 |
| 阶段 5 升级路径 | 5 | 4 | 0 | 1 |
| 阶段 6 故障恢复（新增项） | 3 | 3 | 0 | 0 |
| **合计** | **54** | **47** | **3** | **4** |

自动化测试（单独统计，不并入上表）：

| 套件 | 结果 |
| --- | --- |
| 后端 `pytest` | 371 passed，1 skipped（Windows 符号链接权限不足），0 failed，91.21s |
| 前端 `vitest run` | 25 个文件 / 123 tests passed |
| 前端 `vue-tsc --noEmit` | 通过 |
| 安装包内 sidecar API 回归 | 37/37 通过 |
| 隔离数据库恢复测试 | 6/6 通过 |
| 安装包内容门禁（对官方包） | 正确报出「缺少主程序」与「包含门禁工具」 |
| 安装包内容门禁（对修复包） | 0 问题 |

### 阶段 1：安装包验收

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S1-01 | 官方资产下载与 SHA-256 匹配 | PASS | `downloads/SHA256SUMS.txt` 与实际哈希一致 |
| S1-02 | 官方 updater 签名与公钥验证 | PASS | 校验器输出 `OK signature verified`；`latest.json` 与资产一致 |
| S1-03 | 官方安装包包含主程序 | **FAIL** | `7z l` 只有 `verify-updater-signature.exe`，无 `yijing-workbench.exe` |
| S1-04 | 官方全新安装后启动 | **FAIL** | `install-qa.log`：`mainExeExists=False`，`launchPathExists=False` |
| S1-05 | 官方 v3.3.1 基线安装 | PASS | v3.3.1 安装后 `yijing-workbench.exe` 存在，FileVersion 3.3.1 |
| S1-06 | 官方 v3.3.1 → v3.3.2 覆盖升级后启动 | **FAIL** | 升级后主程序消失，只剩 `verify-updater-signature.exe` |
| S1-07 | 修复构建内容符合契约 | PASS | 含主程序与 sidecar，不含校验器 |
| S1-08 | 修复构建安装、启动、sidecar 运行 | PASS | `fixqa-install-launch.log`：`mainExeExists=True`、`sidecarExists=True` |
| S1-09 | 修复构建显示版本 v3.3.2 | PASS | 设置页「当前版本 V3.3.2」 |
| S1-10 | 安装包内 sidecar 可健康启动 | PASS | sidecar API 37 项均通过 |

### 阶段 2：核心业务回归

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S2-01 | 铜钱起卦（UI） | PASS | 雷火丰 → 震为雷，三爻动，爻辞与保存提示正常 |
| S2-02 | 手动起卦全动爻（UI） | PASS | 六爻全 9 → 乾为天 → 坤为地，动爻 1–6 |
| S2-03 | 卦象、动爻、爻辞展示 | PASS | 本卦/之卦、卦辞、动爻爻辞均显示 |
| S2-04 | 64 卦与乾卦原文（API） | PASS | 64 条；乾为天 6 条爻辞 |
| S2-05 | 学习页筛选与阅读 | PASS | 64 卦列表、乾卦阅读页、筛选切换 |
| S2-06 | 历史保存、打开、检索 | PASS | 保存后可从列表打开；检索命中 |
| S2-07 | 重启后历史保留 | PASS | 「本页 4 条 / 共 4 条」 |
| S2-08 | 纳甲手动排盘（UI） | PASS | 乾宫·金，世应、旬空戌亥、六亲/六神/伏神表 |
| S2-09 | 纳甲自动排盘（API） | PASS | `Asia/Shanghai` 时区、日干支、月建、旬空 |
| S2-10 | 纳甲自动排盘（UI） | 未执行 | 原生 datetime-local 由 Spinner 组成，UIA 无法可靠写入；同一逻辑已由打包 sidecar API 覆盖 |
| S2-11 | API Key 保存、隐私确认、无效 Key 拒绝 | PASS | 「密钥已配置」；DeepSeek 返回「API Key 无效或已失效」 |
| S2-12 | AI 会话、SSE 错误、失败重试持久化 | PASS | `event: error`；`failed_requests` 持久化；新 request_id 重试 |
| S2-13 | AI 成功调用与流式停止 | 未执行 | 无有效测试 Key；仅验证错误与重试路径 |
| S2-14 | 历史列表与详情一致 | PASS | 计数、详情 id/问题一致 |

### 阶段 3：数据安全

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S3-01 | 使用隔离数据库与测试令牌 | PASS | `YIJING_DB_PATH` 指向副本；独立 Bearer 令牌 |
| S3-02 | SQLite 读写与历史计数 | PASS | 备份前后计数一致 |
| S3-03 | WAL 未 checkpoint 行进入备份 | PASS | 在线备份捕获仅存在于 WAL 的行 |
| S3-04 | 安装前一致性备份 | PASS | `integrity_check=ok`；逐表计数、设置、DPAPI Key 均保留 |
| S3-05 | 安装失败旧库保留 | PASS | 注入失败后 DB 哈希不变；安装器不写用户数据目录 |
| S3-06 | 升级/恢复后 DPAPI Key 可用 | PASS | 当前用户可解密，非明文存储 |
| S3-07 | 跨 Windows 用户数据隔离 | 未执行 | 测试机无第二个 Windows 账户；DPAPI 仅验证当前用户 |

### 阶段 4：自动更新

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S4-01 | 真实 GitHub 端点手动检查 | PASS | 首次约 2 分钟，之后 1.2 秒；显示「已是最新」 |
| S4-02 | 最多每 24 小时自动检查一次 | PASS | 24 小时内重启未自动请求，上次检查时间不变 |
| S4-03 | 展示版本号、日期、更新说明 | PASS | `v3.3.3`、`2026-11-04`、模拟更新说明 |
| S4-04 | 用户确认前不下载；「稍后」不下载 | PASS | 服务端日志只有 `latest.json`；「已推迟」状态 |
| S4-05 | 下载进度、速度、ETA | PASS | 0 → 99.1%，16.2 MiB，476 KiB/s，ETA 32 → 0 秒 |
| S4-06 | 下载失败（HTTP 500）可重试 | PASS | `Download request failed with status: 500`；重试成功 |
| S4-07 | 下载中断（40% 断连）可重试 | PASS | `error decoding response body`；重试成功 |
| S4-08 | 签名错误/篡改包被拒绝 | PASS | `The signature verification failed`；应用仍可用，未生成备份 |
| S4-09 | 安装前自动备份 | PASS | 下载完成后生成 `history.pre-update-*.sqlite3` |
| S4-10 | 安装前停止本地服务 | PASS | 安装器启动前 sidecar 进程为空 |
| S4-11 | 安装后重启并运行新版本 | PASS | 应用以 3.3.3 重启，sidecar 重新启动 |
| S4-12 | 更新后再次检查显示已是最新 | PASS | 运行时版本变为 3.3.3 |
| S4-13 | 更新后历史、偏好、Key 保留 | PASS | 记录、`default_method=manual`、DPAPI Key 均保留 |
| S4-14 | 网络不可用提示与恢复 | PASS（附 P2） | 服务停止时显示错误并可重试；恢复服务后「已是最新」 |
| S4-15 | 安装失败时不自动重启/不回滚，旧版本保留 | PASS | 模拟「安装器不落盘」后无新进程，3.3.3 文件与数据仍在 |

### 阶段 5：升级路径

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S5-01 | 官方 v3.3.1 → v3.3.2 数据保留 | 未执行 | 升级后主程序缺失，应用无法启动，无法观察数据；P0 阻断 |
| S5-02 | QA 身份 3.3.1 → 3.3.3 数据保留 | PASS | 历史、偏好、DPAPI Key 全部保留 |
| S5-03 | currentUser 安装模式 | PASS | HKCU 卸载项、用户目录安装，无需管理员 |
| S5-04 | 应用身份与安装目录一致 | PASS | 产品名、标识、安装目录在多次覆盖升级后不变 |
| S5-05 | 全新安装与覆盖安装 | PASS | 全新 fixqa 安装与 4 次覆盖安装均符合预期 |

### 阶段 6：故障恢复（新增项）

| ID | 用例 | 结果 | 证据 |
| --- | --- | --- | --- |
| S6-01 | sidecar 启动失败 | PASS（附 P2） | 应用可打开；首次起卦提示「桌面本地服务连接失败，请查看 yijing-backend.log。」；恢复文件后重启正常 |
| S6-02 | 数据库损坏 | PASS | sidecar 以 `sqlite3.DatabaseError: file is not a database` 退出，未静默覆盖 |
| S6-03 | 备份恢复 | PASS | 备份通过 `integrity_check`，sidecar 健康，历史与 DPAPI Key 可读 |

更新中断、安装失败、签名不匹配、网络不可用已在阶段 4 覆盖，不重复计数。

## 5. P0 缺陷详情

**标题**：正式 v3.3.2 安装包缺少主程序，安装/升级后无应用

**复现步骤**

1. 从 `v3.3.2` Release 下载 `yijing-workbench-3.3.2-x64-setup.exe`，核对 SHA-256 与 `SHA256SUMS.txt`；
2. 用 `7z l -slt` 查看安装包：只有 `verify-updater-signature.exe`、`binaries/yijing-backend/yijing-backend.exe`，没有根目录 `yijing-workbench.exe`；
3. 静默安装到隔离目录：安装进程 exit 0，但目录内不存在主程序；
4. 先安装官方 v3.3.1（主程序存在），再覆盖安装官方 v3.3.2：升级后主程序被移除，仍只剩校验器；
5. 启动路径不存在，应用无法打开。

**根因**

`frontend/src-tauri/Cargo.toml` 中存在第二个 bin target `src/bin/verify-updater-signature.rs`。Cargo 包未声明 `default-run`，Tauri CLI 选择打包主二进制时选中了校验器；发布工作流又把校验器编译到 `target/release`，于是 NSIS 只打进了 `verify-updater-signature.exe`。哈希与 updater 签名只证明「文件未被篡改」，不能证明「安装包里有应用」，所以原发布门禁全部通过。

**修复（分支 `fix/v3.3.2-installer-main-binary`，commit `084cbc5`）**

- `Cargo.toml`：设置 `default-run = "yijing-workbench"`；显式声明两个 bin；校验器加 `required-features = ["verify"]`，普通打包不再包含。
- `release.yml` / `windows-rc.yml`：校验器改用 `cargo build --release --features verify --bin verify-updater-signature`。
- `scripts/updater/verify_release.py`：新增安装包内容门禁，用 7z 读取 NSIS 容器，要求根目录有主程序、存在 sidecar、不得包含校验器；7z 缺失时直接失败（fail closed）。
- 新增 `backend/tests/test_installer_contents.py`、`test_tauri_binary_config.py`，并更新相关测试。

**修复验证**

- 对官方安装包运行新门禁：报出「缺少主程序」与「不应包含门禁工具」；
- 对修复构建运行新门禁：0 问题；
- 修复构建安装后主程序存在、校验器不存在、sidecar 正常；3.3.1 → 3.3.3 QA 更新数据完整。

**PR 状态**

修复分支已推送到 `origin/fix/v3.3.2-installer-main-binary`。由于当前会话的权限分类器拒绝创建公开 PR，未能自动创建；可用以下链接创建（标题与正文已准备）：

`https://github.com/Qiuizi/yijing-workbench-public/compare/main...fix/v3.3.2-installer-main-binary?expand=1`

## 6. 其他发现

| 级别 | 问题 | 复现与影响 | 建议 |
| --- | --- | --- | --- |
| P2 | sidecar 启动失败时应用无启动提示 | 移走 sidecar 后应用正常打开，无横幅；用户起卦时才看到「桌面本地服务连接失败，请查看 yijing-backend.log。」，无应用内重试，日志路径不完整 | 启动时做健康检查；提供「重试/查看日志」入口；显示完整日志路径 |
| P2 | 更新检查连接被拒绝时显示原始英文错误 | 停止本地更新服务后点击检查，状态为「更新失败」，正文 `error sending request for url (...)`；未归入「离线」友好提示 | 扩展 `classifyUpdateError` 匹配连接拒绝/发送失败，或展示统一中文提示 |
| P2（已知） | 未启用 `requireSignedVersion` | `docs/updater/README.md` §10.2 已记录：端点被劫持时可能回放旧的合法签名包 | 待 Tauri CLI 支持后开启；当前依赖 GitHub HTTPS 与发布记录审计 |
| P3（已知） | 安装包无 Authenticode 代码签名 | 首次运行可能触发 SmartScreen，与 updater 签名无关 | 申请代码签名证书；文档已说明 |

## 7. 数据安全结果

- 所有数据库操作都在隔离副本上完成；真实数据库 `%LOCALAPPDATA%\cn.yijing.workbench\history.sqlite3` 未读写。
- 安装前备份通过 SQLite 在线备份 API 生成，`PRAGMA integrity_check=ok`；逐表计数与源库一致；包含未 checkpoint 的 WAL 行。
- 备份包含偏好 `default_method=manual`、时区、AI 默认体系，以及 DPAPI 保护的 Key；备份与升级后实库的 Key 均可由当前用户解密，存储值为 base64 的 DPAPI blob，非明文。
- 模拟安装失败后，数据库文件哈希不变；安装器只写安装目录，不写用户数据目录。
- 损坏数据库不会被静默重建：sidecar 明确报 `file is not a database` 并退出。
- 使用升级前备份启动 sidecar，可正常读取历史记录与 Key，说明人工恢复路径可用。
- 跨 Windows 用户隔离未测试（见第 10 节）。

## 8. 自动更新结果：真实与模拟的边界

| 测试项 | 方式 | 结果 |
| --- | --- | --- |
| 官方 Release 资产、哈希、签名 | 真实 | PASS（内容缺失，见 P0） |
| 对 GitHub 真实端点的检查与 24h 节流 | 真实 | PASS |
| 3.3.1 → 3.3.3 检查、下载、备份、停服务、安装、重启 | 模拟（独立标识 + 临时 QA 密钥 + 本地 HTTP） | PASS |
| 下载进度/速度/ETA | 模拟 | PASS（真实 UI 状态机与真实下载字节） |
| HTTP 500、40% 断连 | 模拟故障注入 | PASS（可重试） |
| 篡改安装包 / 签名错误 | 模拟故障注入 | PASS（拒绝安装） |
| 安装器失败（签名有效但不安装） | 模拟故障注入 | PASS（无自动重启/回滚，旧版本与数据保留） |
| 网络不可用 | 模拟（停止本地服务） | PASS（错误提示可恢复，附 P2） |
| 正式密钥、v3.3.2 资产 | 未修改 | — |

3.3.3 是为验证更新链路构建的 QA 版本，不是正式发布；上述模拟结果不能替代「正式 v3.3.2 → 下一个正式版本」的升级验证，后者需要等新版本发布后补测。

## 9. 测试门禁

| 命令/检查 | 结果 |
| --- | --- |
| `python -m pytest -q` | 371 passed，1 skipped，0 failed |
| `npm test`（vitest run） | 25 files / 123 tests passed |
| `npm run typecheck`（vue-tsc） | 通过 |
| 安装包内容门禁（官方 v3.3.2） | 正确阻断 |
| 安装包内容门禁（修复构建） | 通过 |

1 个跳过项为 `test_provenance.py` 的符号链接测试，原因是 Windows 当前账户缺少创建符号链接权限，与本次修复无关。

## 10. 未执行与受限项

1. **官方 v3.3.1 → v3.3.2 数据保留**：P0 导致升级后无应用，无法观察数据。安装器本身不写用户数据目录，但该路径的端到端结论不可得。
2. **AI 成功调用、流式输出与停止**：没有有效的 DeepSeek 测试 Key；只验证了无效 Key、SSE 错误、失败持久化与重试。
3. **纳甲自动排盘 UI**：原生 `datetime-local` 在 WebView2 中暴露为多个 Spinner，UIA 无法可靠写入；同一后端逻辑已由打包 sidecar 的 API 用例覆盖。
4. **跨 Windows 用户数据隔离**：测试机只有一个账户，未创建第二个用户；DPAPI 仅验证当前用户可解密。
5. **Authenticode/SmartScreen 行为**：无代码签名证书，未测试。
6. **正式 v3.3.2 → 下一正式版本自动升级**：没有更新的正式版本；用 3.3.3 QA 版本模拟。

## 11. 剩余问题与建议

- **P0（未关闭）**：正式 v3.3.2 安装包与升级路径不可用。修复代码已推送，但在发布新版本前，现有 v3.3.2 用户需要按 `docs/updater/README.md` §9 人工恢复（关闭应用、恢复备份、重装上一个可用版本）。不要删除 `%LOCALAPPDATA%\cn.yijing.workbench`。
- **P1**：无额外 P1。
- **P2**：sidecar 启动失败无启动提示与重试；更新检查连接拒绝时显示原始英文错误；`requireSignedVersion` 未启用（已知）。
- **P3**：无 Authenticode 代码签名（已知）。
- 建议发布新版本时：先跑安装包内容门禁，再执行一次真实 v3.3.2 → 新版本升级，并补测 AI 成功流与跨用户隔离。

## 12. 最终状态

**POST_RELEASE_QA_FAILED**

判定依据：正式发布资产在「安装/启动」这一发布底线失败（P0），修复分支的验证通过不代表原发布通过。其余阶段的结果仅对修复构建和模拟更新环境成立，正式升级路径需在新版本发布后重新验收。

## 13. 证据索引

证据目录：`.qa-work/v3.3.2/evidence/`（`.qa-work/` 已被 `.git/info/exclude` 忽略，不进入仓库）。

- 安装与内容：`install-qa.log`、`install-qa-decoded.txt`、`fixqa-install-launch.log`、`fixqa-build.log`、`official-signature-verification.txt`
- 核心业务：`probe-cast-result.txt`、`probe-manual-result2.txt`、`probe-learning-reader.txt`、`probe-history*.txt`、`probe-najia-result.txt`、`probe-ai-*.txt`、`probe-after-restart-*.txt`
- API：`api-sidecar-results.json`
- 更新：`updater-run-timeline.txt`、`updater-retry-timeline.txt`、`updater-check-available.txt`、`updater-downloading.txt`、`updater-fail500.txt`、`updater-failpartial-final.txt`、`updater-signature-fail.txt`、`updater-offline.txt`、`updater-server.log`、`updater-after-*.txt`
- 恢复：`recovery-results.json`、`recovery-test/corrupt-sidecar.log`、`recovery-test/restored-sidecar.log`、`sidecar-fail-*.txt`
- 测试门禁：`pytest.log`（另有终端输出：371 passed / 1 skipped）
