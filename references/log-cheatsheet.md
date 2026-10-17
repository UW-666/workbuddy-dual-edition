# 日志速查表

诊断全靠这一份。日志位置：`<数据目录>/logs/update/update-YYYYMMDD.log`（按天轮转，取最新）。

## 取最新日志
```
# Windows
Get-ChildItem "$HOME\.workbuddy*\logs\update\update-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
# macOS / Linux
ls -lt ~/.workbuddy*/logs/update/update-*.log | head -3
```

## 关键字 → 含义 → 你要做什么

| 日志行 | 含义 | 动作 |
|---|---|---|
| `Startup force auto-update: enabled=true source=product-base` | 启动期强装**开着** | 改 `product.json` 的 `updates.startupForceAutoUpdate=false`（见 playbook §3.2） |
| `... enabled=false source=product-base` | 已关掉 ✅ | 无需动作 |
| `... enabled=true source=remote-feature` | **服务端/企业策略**在推，优先级高于本地文件 | 本地改不掉；用 §3.3 目录封锁兜住实际安装动作 |
| `... enabled=true source=cached-system-default` | 本地缓存的系统默认值 | 改 `<数据目录>/cache/acc-product-config-v3.json`（§3.4） |
| `... enabled=true source=user-setting` | UI 里的用户开关 | 去 UI 关掉（注：多数版本 `hasShowSetting=false`，UI 未暴露） |
| `... enabled=true source=hardcoded-fallback` | **没读到配置**，落兜底=true | 文件路径改错了 / 改了 asar 内那份（不生效） |
| `Restored downloaded update from cache: version=X` | 从缓存恢复安装器，即将套用 | **这就是覆盖的发动机**；先清 staging 再上封锁 |
| `[early-silent-startup-update] ready update restored before window, quitting to install` | 启动期强装确认执行 | 同上；改完应不再出现此行 |
| `quitAndInstall ENTRY` | 真的要装了 | 同上 |
| `Launching installer: <路径>` | 安装器落点 | **上一行路径即 staging 目录**，§3.3 封它 |
| `Update downloaded: <路径>` | 下载落地路径 | 同上 |
| `Downloading update from: https://...` | 正在下载 | 封锁后应变 `downloadUpdate error: EPERM` |
| `downloadUpdate error: EPERM` / `EACCES` | 写入被拒 = 封锁生效 | ✅ 层 2 达成（旁证） |
| `No update available (HTTP 204)` | 当前已是最新 | 正常，不代表没在强装 |

## 找「谁改了 product.json」
若重启后发现 `product.json` 被改回 `true`：
```
# Windows：看该文件最后写入时间，与 logs 里各事件时间对照
Get-Item "<安装目录>\resources\app.asar.unpacked\cli\product.json" | Select-Object LastWriteTime
```

## 其他日志
| 文件 | 内容 |
|---|---|
| `installer.log` / `register.log` | 安装器落点、文件关联/ShareTarget 注册 |
| `main.log` / `daemon.log` / `renderer.log` | 登录、产品判定、网络请求 |
| `storage/skeleton/account-snapshot.json` | 当前登录账号 `primary.uid` |
| `cache/acc-product-config-v3.json` | 产品配置快照（含 `updates`） |
