# 隔离 Windows NSIS 升级实验报告

- 运行时间：2026-10-27T06:45:04.706Z
- 隔离标识：`cn.yijing.workbench.updaterqa`（正式版为 `cn.yijing.workbench`，两者互不影响）
- 安装目录：`C:\Users\123\AppData\Local\YijingWorkbenchQA`
- 数据目录：`C:\Users\123\AppData\Local\cn.yijing.workbench.updaterqa`
- 旧版安装包：`YijingWorkbenchQA_3.3.2-qa.1_x64-setup.exe`
- 更新源：本地 HTTP `C:\Users\123\AppData\Local\Temp\updater-e2e\update`（QA 构建显式开启 `dangerousInsecureTransportProtocol`，正式构建不允许）

## 结论

**22/22 项通过**（全部通过）

| # | 检查项 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | 旧版 NSIS 静默安装返回 0 | ✅ 通过 | `exit=0` |
| 2 | 安装目录存在 | ✅ 通过 | `C:\Users\123\AppData\Local\YijingWorkbenchQA\yijing-workbench.exe` |
| 3 | 旧版起卦成功并渲染结果 | ✅ 通过 | `隔离升级实验：更新后这条记录必须还在。` |
| 4 | 设置页可写入 API Key 输入框 | ✅ 通过 | `` |
| 5 | 旧版数据：新增 1 条记录 | ✅ 通过 | `2 → 3` |
| 6 | 旧版数据：DPAPI 密钥已保存 | ✅ 通过 | `` |
| 7 | 旧版数据：偏好已写入 | ✅ 通过 | `{"default_method": "coins", "timezone": "Asia/Shanghai", "ai` |
| 8 | 检查更新得到「发现新版本」 | ✅ 通过 | `发现新版本 / v3.3.2-qa.22026-10-27` |
| 9 | 显示可用版本号 | ✅ 通过 | `v3.3.2-qa.22026-10-27` |
| 10 | 下载并安装按钮可点击 | ✅ 通过 | `` |
| 11 | 应用在安装前退出 | ✅ 通过 | `lastState=正在下载 error=-` |
| 12 | 界面读取到运行时版本 3.3.2-qa.2 | ✅ 通过 | `{"aboutVersion":"V3.3.2","runtimeVersion":"V3.3.2-qa.2","state":"未检查"}` |
| 13 | 升级后历史记录条数未变 | ✅ 通过 | `3 → 3` |
| 14 | 升级后问句内容未变 | ✅ 通过 | `隔离升级实验：更新后这条记录必须还在。` |
| 15 | 升级后偏好保留 | ✅ 通过 | `{"default_method": "coins", "timezone": "Asia/Shanghai", "ai` |
| 16 | 升级后 DPAPI 密钥仍存在 | ✅ 通过 | `` |
| 17 | 升级后至少一份升级前备份 | ✅ 通过 | `history.pre-update-20261027T064435Z.sqlite3` |
| 18 | DPAPI 密钥可被当前用户解密 | ✅ 通过 | `decrypted` |
| 19 | 篡改场景先被识别为新版本（qa.3） | ✅ 通过 | `发现新版本` |
| 20 | 篡改包被拒绝（状态为更新失败） | ✅ 通过 | `更新失败 / The signature verification failed` |
| 21 | 错误提示说明校验失败 | ✅ 通过 | `The signature verification failed` |
| 22 | 应用仍可继续使用且版本未变 | ✅ 通过 | `{"version":"V3.3.2-qa.2","rows":4}` |

## 数据快照

| 阶段 | 历史条数 | 问句 | 偏好 | DPAPI 密钥 | 升级前备份 |
| --- | --- | --- | --- | --- | --- |
| 升级前 | 3 | 隔离升级实验：更新后这条记录必须还在… | `Asia/Shanghai` | 存在 | — |
| 升级后 | 3 | 隔离升级实验：更新后这条记录必须还在… | `Asia/Shanghai` | 存在且可解密 | history.pre-update-20261027T064435Z.sqlite3 |

## 观察到的两次「正确失败」

1. **sidecar 未更新导致备份 404**：第一次实验时打包的 Python sidecar 还是旧版本，没有 `/api/desktop/update/backup`，应用在下载完成后直接报「安装前备份失败，已取消安装」，没有进入安装、没有停机、数据无损 —— 说明「备份失败即中止」生效。
2. **篡改安装包**：把 qa.2 安装包的字节改动 1 位后由 `latest.json` 宣布为 qa.3，应用完成下载后在安装阶段报 `The signature verification failed`，状态转为「更新失败」，仍停留在 qa.2 并可继续使用。

## 复现方式

```bash
# 1) 用 QA 配置分别构建两个版本（identifier/productName 均为隔离值）
npx tauri build --bundles nsis --config qa-config.json   # version=3.3.2-qa.1 / 3.3.2-qa.2
# 2) 准备本地更新源：安装包 + .sig + latest.json（url 指向本地 HTTP）
# 3) 执行
node scripts/updater/qa-upgrade-e2e.mjs \
  --old-setup <qa.1-setup.exe> --update-dir <update-dir>
# 4) 仅采集界面截图
node scripts/updater/qa-upgrade-e2e.mjs --capture-only
```

> QA 私钥位于 `frontend/src-tauri/.updater-qa/`（已 gitignore），密码为实验用固定值；**它不是、也不能用作正式发布密钥**。
