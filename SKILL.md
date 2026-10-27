---
name: workbuddy-dual-edition
description: 处理腾讯 WorkBuddy 国内版(workbuddy.cn)与国际版(workbuddy.ai)在同一台电脑上的共存问题。触发词：双开、同时开两个、开第二个没反应、装国内版却变国际版、只能登录国际版、重启后被覆盖、卸载重装还复发、两版互相覆盖、国际版登不上、国内版登不上、WorkBuddy 两版冲突、WorkBuddyAI.exe 突然出现、安装文件损坏或缺失、每次启动要重新登录、套餐一直转圈获取中、积分额度刷不出来、个人管理网页打不开、桌面图标空白、快捷方式图标丢失。
---

# WorkBuddy 国内版 / 国际版 同机共存

## 0. 何时用 / 何时不用

**用**：用户在同一台机想同时用国内版和国际版，或遇到「只能开一个 / 被覆盖 / 登不上」。

**不用**（直接回答，别执行）：
- 用户只想问「两版区别」「怎么下载」→ 普通问答即可
- 用户的问题与网络/账号权限无关但**发生在 macOS/Linux** → 见 `references/platform-notes.md`：这些平台**未实测**，必须先向用户声明这一点再继续
- 用户机器上**没有** `resources/app.asar.unpacked/cli/product.json`（旧版本/绿色版）→ 只做「层 2 封锁」，见 playbook §5.8

**核心前提（先确认，不满足就别动手）**：
1. 两版**必须装在不同安装目录**
2. 两版**各登各的账号**（国内=微信/手机号，国际=Google/GitHub/X/OneID/邮箱；**国际版无法登录国内账号**——这是产品设计，不要试图绕过）
3. 用户**接受放弃自动更新**（本方案核心是关掉它；升级改为手动装包）

## 1. 三问快速定位（按顺序问/查，别跳）

**Q1：现在跑的是哪一版？**

对安装目录里的 exe 看「产品名称」（Windows）或读 `product.json`（最权威）：

| 判定 | 国内版 | 国际版 |
|---|---|---|
| 产品名称 | `WorkBuddy` | `WorkBuddy AI` |
| `applicationName` | `workbuddy` | `workbuddy-ai` |
| `dataFolderName` | `.workbuddy` | `.workbuddy-ai` |
| `isOversea` | 缺省/false | `true` |
| `win32MutexName` | `workbuddy` | `workbuddy-ai` |

> ⚠️ **文件名带 `AI` 不代表是国际版**（社区有假包）。只认产品名称与 `product.json`。

**Q2：故障属于哪一类？**

| 用户症状 | 根因 | 去处 |
|---|---|---|
| 一启动就自动装、目录冒出 `WorkBuddyAI.exe` | 自动更新「启动期强装」 | §3 层 1+2 |
| 重启后恢复故障 / 卸载重装仍复发 | 同上 + 卸载器不清 staging | §3 层 1+2 + §5.4 |
| 起第二个没反应 / 第一个被顶掉 | 装到同一目录 或 托盘残留 或 假包 | §5.1 |
| 国际版登录页打不开 | 可能只是**网络** | §5.7 先分流 |
| A 版显示 B 版账号/历史 | 两版指向同一数据目录 | §5.3 |
| 改完开关日志仍 `enabled=true` | 被 `source` 指向的更高优先级覆盖 | §3.2 速查表 |

**Q3：日志怎么说？**

日志位置：`<数据目录>/logs/update/update-YYYYMMDD.log`（取最新的）
关键行：`enabled=`、`source=`、`Restored downloaded update from cache`、`quitAndInstall`、`Launching installer:`
速查表见 `references/log-cheatsheet.md`。

## 2. 处理流程（四步）

按 `references/full-playbook.md` §3 执行，四步缺一不可：

1. **§3.1 目录隔离**：两版装到不同目录；装过同目录的先各卸一次再依次装
2. **§3.2 关「启动期强装」**：改 `<安装目录>/resources/app.asar.unpacked/cli/product.json` 的 `updates.startupForceAutoUpdate=false`（**两版都改，必须带 `apiVersion:"v2"`**）
3. **§3.3 阻断下载**：staging 目录加 ACL 拒写（日志会打印路径；Windows 已实测两个：`%LOCALAPPDATA%\@genieworkbuddy-desktop-updater`、`%TEMP%\workbuddy-update-x64`）
4. **§3.4 加固缓存**：若日志仍 `source=product-base` 且值 true，同改 `<数据目录>/cache/acc-product-config-v3.json`

完成后**必须按 playbook §4 逐项验证**，尤其「重启电脑后再验一次」。

**第 5 步（混合构建症状专用）**：若做完四步仍出现套餐面板转圈（零网络请求）、积分刷不出、个人页跳错域名且补丁无效——这是混合构建结构性问题，走 playbook §9「重装整包治本路线」：官网整包覆盖安装 → 用 `scripts/verify_install.py` 跑装后验证 → 干净整包原生自带正确配置，**不要再画蛇添足打补丁**。衍生故障（桌面图标空白、旧路径残留）见 playbook §10，脚本在 `scripts/`。

## 3. 确认闸（破坏性操作，先问人再做）

| 操作 | 级别 |
|---|---|
| 读文件、读日志、跑探测命令 | 直接做 |
| 改 `product.json` / `acc-product-config-v3.json` | 先说明改什么+已备份，可继续 |
| `icacls /deny`（目录拒写） | 同上，须说明「升级改手动」 |
| 注册/删除计划任务 | 同上，注明任务名 |
| **卸载任一版 / 删安装目录 / `Remove-AppxPackage`** | **必须先问人**（可能丢数据；卸载器会删目录） |
| macOS 上改 `.app` 内文件 | **必须先问人**（破坏签名，可能无法启动；未实测） |

## 4. 交付给用户的固定收尾

做完后给用户三样，缺一不可：
1. **判据**：让他自己怎么确认成功（日志 `enabled=false`、正向写测试被拒、两个进程并存）
2. **回滚**：每一步怎么退（playbook §7）
3. **边界**：自动更新已关、以后手动升级；macOS/Linux 未实测
