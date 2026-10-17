# 平台边界与实测状态

**最重要的原则：只声称你验证过的东西。**

## 实测状态

| 项目 | Windows | macOS | Linux |
|---|---|---|---|
| 两版能否同机并存（不同目录） | ✅ 实测通过 | 未实测（依据：锁名/数据目录不同，理论可） | 未实测（同上） |
| `updates.startupForceAutoUpdate` 开关位置与效果 | ✅ 实测生效 | 未实测 | 未实测 |
| staging 目录路径（两个） | ✅ 实测 | **未实测**，需按日志打印路径找 | **未实测**，同上 |
| ACL `icacls /deny` 封锁 | ✅ 实测生效 | 不适用 | 不适用 |
| `chmod 500` 封锁 | — | 未实测 | 未实测 |
| `chattr +i` 封锁 | — | 无此命令 | 未实测（需 root） |
| 守卫脚本（登录触发） | ✅ 实测通过 | 未实测 | 未实测 |

**结论：Windows 之外一律先向用户声明"未实测"，并让其以本地日志实际路径为准。**

## 各平台探测命令

| 用途 | Windows | macOS | Linux |
|---|---|---|---|
| 安装目录 | `Get-ChildItem "$env:LOCALAPPDATA\Programs" -Directory \| Where-Object Name -like 'WorkBuddy*'` | `ls -d /Applications/WorkBuddy*.app` | `ls -d /opt/*orkBuddy* ~/.local/share/*orkBuddy* 2>/dev/null` |
| 数据目录 | `Get-ChildItem $HOME -Force -Directory \| Where-Object Name -like '.workbuddy*'` | `ls -d ~/.workbuddy* ~/Library/Application\ Support/*orkBuddy* 2>/dev/null` | `ls -d ~/.workbuddy*` |
| 产品名 | exe 属性→详细信息→产品名称 | `defaults read "/Applications/<App>.app/Contents/Info.plist" CFBundleName` | `strings <exe> \| grep -i workbuddy` |
| Temp | `$env:TEMP` | `$TMPDIR` | `${TMPDIR:-/tmp}` |

## macOS 特有风险（写在前头）

改 `/Applications/*.app` 内的文件会**破坏代码签名**，新版 macOS 可能直接拒绝启动（报「已损坏」）。
- 若已中招：`xattr -dr com.apple.quarantine "/Applications/<App>.app"`
- 或本地重签：`codesign --force --deep --sign - "/Applications/<App>.app"`（需 Xcode 命令行工具）
- 仍不行 → **放弃层 1（改 product.json），只做层 2（目录封锁）**，并把这一点明确告知用户

## Linux 特有：权限分级

- `chattr +i`（连 root 写都挡）**必须 root** → 只能由 systemd **system 级** unit 或 `/etc/rc.local` 执行
- `chmod 500`（用户级即可挡普通进程）可用 systemd **user** unit
- **二者不要混用**：user unit 拿不到 root，做不了 `chattr +i`

## 临时目录会被清理（所有平台）

`%TEMP%` / `$TMPDIR` / `/tmp` 里的封锁可能被系统清理而失效 → 用「登录时触发一次」的守卫任务重铺（不要常驻轮询）：
- Windows：计划任务 `-AtLogOn`
- macOS：launchd `RunAtLoad=true`
- Linux：systemd（system 或 user，按上面分级）
