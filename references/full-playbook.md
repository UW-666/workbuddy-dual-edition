# WorkBuddy 国内版 / 国际版「同机共存」完全方案

> 适用：Tencent WorkBuddy（国内版 `workbuddy.cn` / 国际版 `workbuddy.ai`）在同一台电脑上**同时使用**。
> 平台：Windows / macOS / Linux。**路径一律用探测命令获取，不要照抄示例值。**
> 面向「人或 AI 照做即可解决」。文中 `<...>` 需按 §1 探测结果替换。

---

## 0. 一句话结论

**两版是两个独立产品，本就支持同机共存。** 若你「只能开一个 / 一开就变国际版 / 重启后被覆盖」，根因是**自动更新覆盖了安装目录**。关掉更新的「启动期强装」并阻断其下载落盘，即可稳定双开。

另有两项**前提**（见 §3.1 / §5.1）：**两版必须装在不同目录**；**两版各登各的账号**。缺任一项都双开不成，所以别只做更新封锁就收工。

---

## 0.1 适用范围与前置条件
- **验证版本**：Windows + WorkBuddy 5.8.x（国内版 5.8.2 / 国际版 5.8.4）。
- **必要条件**：安装目录内存在
  `<安装目录>/resources/app.asar.unpacked/cli/product.json`
  （这是关闭「启动期强装」的落点；不存在则只能做 §3.3，效果打折 —— 见 §8）。
- **两个独立账号**：国内版一个（微信/手机号），国际版一个（Google/GitHub 等）。
- **放弃自动更新**：本方案的核心是**让自动更新不再覆盖目录** —— 代价是以后**手动升级**（见 §5.5）。
- **两个账号**：为彻底避免互相顶号，建议两版各登各的账号；**若你就是要两版登同一账号，也能跑**（数据按 `user_id` 隔离，不会串数据），但据社区反馈远程控制通道可能互相接管，详见 §5.1。
- **先备份**：改动前会生成 `.bak`；建议先确认已记住 `pid/uid` 等现状（§1）。

---

## 1. 环境探测（先做，所有平台通用）

### 1.1 判定装的是哪一版
- Windows：右键 `WorkBuddy*.exe` → 属性 → 详细信息 → **产品名称**
- macOS：先列 app，再读 Info.plist
  ```
  ls /Applications | grep -i workbuddy
  defaults read "/Applications/<列出的App名>.app/Contents/Info.plist" CFBundleName
  ```
- Linux：读 `product.json`（见 1.2），或 `strings <exe> | grep -i workbuddy`

| 产品名称 | 版本 |
|---|---|
| `WorkBuddy` | 国内版 |
| `WorkBuddy AI` | 国际版 |

> ⚠️ **文件名带 `AI` 不等于国际版**：据社区反馈与本次实测，确有名为 `...4AI.exe` 的包装出来是**国内版载荷**。**只认「产品名称」与 `product.json`，不认文件名。**

### 1.2 读主程序的 `product.json`（最权威）
```
<安装目录>/resources/app.asar.unpacked/cli/product.json
```
关键字段与取值：
```json
{
  "applicationName": "workbuddy" | "workbuddy-ai",
  "dataFolderName":  ".workbuddy" | ".workbuddy-ai",
  "isOversea":       false | true,
  "win32MutexName":  "workbuddy" | "workbuddy-ai",
  "updates": { "startupForceAutoUpdate": true }
}
```
- 国内版：`applicationName=workbuddy`、`dataFolderName=.workbuddy`、`isOversea` 缺省、`win32MutexName=workbuddy`
- 国际版：`applicationName=workbuddy-ai`、`dataFolderName=.workbuddy-ai`、`isOversea=true`、`win32MutexName=workbuddy-ai`

> 文件不存在 = 版本较老或打包不同，改用 1.1 的产品名称判定。

### 1.3 探测数据目录
数据/登录态放在**用户主目录**下的隐藏目录，名字来自 `dataFolderName`：
- 国内版 → `.workbuddy`
- 国际版 → `.workbuddy-ai`

探测（**以实际存在者为准**；Windows 实测为 `$HOME\.workbuddy*`）：
```
# Windows PowerShell
Get-ChildItem $HOME -Force -Directory | Where-Object Name -like '.workbuddy*'
# macOS / Linux
ls -d ~/.workbuddy* 2>/dev/null
# macOS 补充（部分打包把数据放在 Application Support 下）
ls -d ~/Library/Application\ Support/*orkBuddy* 2>/dev/null
```
登录态文件：`<数据目录>/storage/skeleton/account-snapshot.json` → `primary.uid`
（实测该值即客户端会话面板所过滤的账号；另一个来源 `storage.json` 可能与其不一致 —— **判登录态以 `account-snapshot.json` 为准**，此为单版本实测观察，跨版本如失效以面板实际显示为准。）

> 最可靠的定位法：启动一次客户端，然后在 `$HOME` 附近找**最近被写入**的 `*workbuddy*` 目录。

### 1.4 探测安装目录
| 平台 | 默认安装目录 |
|---|---|
| Windows | `%LOCALAPPDATA%\Programs\WorkBuddy` / `...\WorkBuddyAI` |
| macOS | `/Applications/WorkBuddy.app` / `/Applications/WorkBuddy AI.app` |
| Linux | `/opt/WorkBuddy` / `/opt/WorkBuddyAI`（或 AUR/自解压目录） |

探测：
```
# Windows
Get-ChildItem "$env:LOCALAPPDATA\Programs" -Directory | Where-Object Name -like 'WorkBuddy*'
# macOS
ls -d /Applications/WorkBuddy*.app
# Linux
ls -d /opt/*orkBuddy* ~/.local/share/*orkBuddy* 2>/dev/null
```
权威判定仍是各安装目录里的 `resources/app.asar.unpacked/cli/product.json`。

---

## 2. 根因（三条，互不替代）

### 根因 A：安装器**复用已登记的安装目录** → 两版被装进同一处，互相覆盖
两版**默认目录本就不同**（§1.4）。但安装器启动时会**复用系统里已登记的安装目录**（Windows 注册表 `Uninstall\...` 项），因此：
- 若另一版已被登记，新装的这版会被**塞进同一目录**
- 安装时该目录**会清空重写**，连 `resources/app.asar`（内含 `product.json`）一起覆盖
- 自定义目录参数（`/DIR=`、`/D=`）**本文实测不生效**

⇒ 结果：两版被装到同一处，后装者毁前者。

> 📌 官方 FAQ 旁证：「WorkBuddy 更新或重装时，安装目录会清空并重新写入文件」（出处见 §5.6）—— 这正是「同目录会被覆盖」的官方说明。

### 根因 B：自动更新的「启动期强装」会在重启后覆盖安装目录
更新器会把下载的安装器**暂存**在 staging 目录，并在下次启动时**先于窗口**套用它：
```
State changed: ready | version=<ver>
[win32] Restored downloaded update from cache: version=<ver>
[early-silent-startup-update] ready update restored before window, quitting to install
[win32] quitAndInstall ENTRY
```
关键：实测观察到它反复套用**与当前版本号相同**的安装器、且在更新通道当日返回 `204` 后仍照装 —— 据此推断 `state=ready` + 落盘安装器**不会自清**，形成永动机（逐请求未核对）。
**卸载重装无效**，因为卸载器**不清** staging 目录（见 §3 层 2）。

### 根因 C：两版登录体系不互通 → 必须两套客户端
| | 国内版 | 国际版 |
|---|---|---|
| host | `workbuddy.cn` | `workbuddy.ai` |
| 登录方式 | 微信 / 手机号 | Google / GitHub / X / OneID / 邮箱 |

**国际版无法登录国内账号。** 所以「一个客户端靠登录切换」**不成立**，两套客户端是刚需。

### 为什么「以前能双开、更新后就不行」
两版身份（exe 名 / `win32MutexName` / `dataFolderName`）**一直不同**，本就可并存。「以前能、现在不能」的转变，**推断**与某次更新后安装器/自动更新策略变化导致的**覆盖**频发有关（未做版本比对）；**双开能力本身没被移除**这一判断是实测支撑的（两版在干净目录下可并存）。

---

## 3. 解决方案（四步，配合根因 A/B/C，缺一不可）

> 目标状态：两版各在自己目录、各用自己数据目录、更新不会互相覆盖。
> 步骤与根因对应：3.1↔A、3.2↔B、3.3↔B、3.4↔B（加固）、两版各登各的账号↔C（见 §5.1）。

### 3.1 装到两个不同目录（治根因 A）
1. 装**国内版** → 记下目录 `<DIR_CN>`（默认见 §1.4）
2. 装**国际版** → 记下目录 `<DIR_INTL>`
3. **必须满足** `DIR_CN != DIR_INTL`；且 `DIR_CN/product.json` 为国内版、`DIR_INTL/product.json` 为国际版（§1.2）

**若安装器硬要装进同一个目录**（实测存在此行为），按下面两条处理：

#### 先试：清掉另一版的安装登记，让它各归各位
安装器会**复用系统里已登记的安装目录**（Windows 注册表 `Uninstall\...` 项）。所以顺序很重要：
1. 先在系统「应用/程序」里**卸载另一个版本**（不是删目录）
2. 再装当前版 → 它会回到自己的默认目录（`WorkBuddy` / `WorkBuddyAI` 是两个不同默认目录）
3. 然后装另一个版本 → 同样回它自己的默认目录
4. 校验两边 `product.json` 判定正确（§1.2）

> 实测：把两版都卸载干净后重新依次安装，各自落在自己的目录，**互不覆盖**。

#### 再试：复制冻结（安装器仍不听话时）
1. 装 A → 把整个 A 目录**复制**到独立位置 `<DIR_A_FROZEN>`
2. 再装 B（任它覆盖默认目录）
3. 校验 `<DIR_A_FROZEN>/resources/app.asar.unpacked/cli/product.json` 仍是 A 版
4. 以后启动用冻结副本的 exe

> 复制出来的目录不受安装器覆盖影响（Electron 应用的数据目录由 `dataFolderName` 决定，**与安装位置无关**），可放任意盘符。

### 3.2 关掉「启动期强装」（治根因 B，**最关键**）
**先退出客户端。** 然后编辑**安装目录内、asar 之外**的这个文件：
```
<安装目录>/resources/app.asar.unpacked/cli/product.json
```
> 运行期实际读取的是**这一份**（asar 内的同名文件不生效）。它直接可编辑，无需解包。
> 备份：
> ```
> Copy-Item "<该文件路径>" "<该文件路径>.bak"        # PowerShell
> cp "<该文件路径>" "<该文件路径>.bak"                # macOS / Linux
> ```
> ⚠️ 若该文件是 **JSONC**（含 `//` 注释或尾逗号），**请用文本编辑器手工改**，不要用 JSON 解析/重写（会丢注释甚至报错）。

改法（**统一规则**）：
- `updates` **已存在** → 只把 `startupForceAutoUpdate` 设为 `false`；**若缺 `apiVersion` 一并补上 `"apiVersion": "v2"`**
- `updates` **不存在** → 整块新建：
```json
"updates": { "apiVersion": "v2", "startupForceAutoUpdate": false }
```
> 为什么必须带 `apiVersion`：只写 `startupForceAutoUpdate` 时，部分版本会回落到 `hardcoded-fallback`（= true），开关不生效。

> 🍎 **macOS 特别注意（未实测）**：改 `/Applications/*.app` 内的文件会**破坏代码签名**，新版 macOS 可能拒绝启动（报「已损坏」）。若被拒，可试：
> ```
> xattr -dr com.apple.quarantine "/Applications/<App>.app"
> # 或本地重签（需已装 Xcode 命令行工具）
> codesign --force --deep --sign - "/Applications/<App>.app"
> ```
> 若仍无法启动，**放弃层 1、只做 §3.3 的封锁**（Windows 实测层 1 最有效，macOS 上以封锁为主）。

**两版都要各改一次。**

#### 原理（源码依据）
`app.asar` 内函数 `resolveStartupForceAutoPreference(inputs)` 的优先级链（高 → 低）：
```
userSetting  →  remoteFeature  →  cachedSystemDefault  →  productBase  →  hardcoded-fallback(true)
```
- `productBase` 取自「当前产品配置」的 `updates.startupForceAutoUpdate`
- 上述 `product.json` 就是该值的来源之一（另一来源是数据目录下 `cache/acc-product-config-v3.json`，见 3.4）
- 原生用户开关 key 名为 `startupForceAutoUpdate`，但该版本 `hasShowSetting=false`（**UI 未暴露**），因此只能改文件
- 上述优先级链为**直读 asar 内 JS** 所得（非反编译猜测）

#### 若改完仍是 `enabled=true`：按 `source=` 字段定位
日志里的 `source` 会告诉你**是谁在说话**：
| `source` | 含义 | 处置 |
|---|---|---|
| `product-base` | 就是我们改的这层 | 检查两处文件都改了（安装目录 + `cache/acc-product-config-v3.json`）、是否带 `apiVersion`、改前是否退出了客户端 |
| `remote-feature` | **服务端/企业策略在推**，优先级高于本文件 | 企业/租户策略无法本地绕过；只能加 §3.3 的目录封锁兜住实际安装动作 |
| `cached-system-default` | 本地缓存的系统默认值 | 数据目录 `cache/acc-product-config-v3.json`（§3.4） |
| `user-setting` | 客户端 UI 里的用户开关 | 去 UI 里关掉它（**注：本版本 `hasShowSetting=false`，UI 未暴露，正常不会出现此 source**；若出现说明该版本已开放该开关） |
| `hardcoded-fallback` | 上面的都没读到，落到兜底（=true） | 说明 `product.json` 没被读到 → 检查路径是否对、是否改错文件（asar 内那份不生效） |

### 3.3 阻断自动更新的下载落盘（治根因 B 的另一半）

⚠️ **3.2 只管住「启动期强装」，管不住常规自动下载。** 改完 3.2 后日志**仍会出现**：
```
State changed: available | version=<ver>
[win32] Downloading update from: https://...
```
所以要再让 staging 目录**写不进去**。

#### 第一步：找出 staging 目录（跨平台通用）
更新日志会**直接打印它**。日志位置：`<数据目录>/logs/update/update-YYYYMMDD.log`
搜关键字：
```
Launching installer:              → 该行路径即 staging 目录内的安装器
Update downloaded:                → 下载落地路径
Restored downloaded update from cache:
```
（日志若已轮转，再搜数据目录与系统临时目录下名字含 `workbuddy` / `genieworkbuddy` 的目录。）

**Windows 已实测的两个**：
```
%LOCALAPPDATA%\@genieworkbuddy-desktop-updater
%TEMP%\workbuddy-update-x64        # 常见即 %TEMP%\workbuddy-update-x64
```
> 两者都可能存在（一个是长期缓存目录，一个是下载暂存目录）；**都封**。用 `$env:TEMP` 确认后者。

**macOS / Linux**：目录名含 `genieworkbuddy-desktop-updater` / `workbuddy-update`，一般在 `~/Library/Caches`、`~/.cache`、`$TMPDIR` 或 `/tmp` 下 —— **以你日志打印的路径为准**。

#### 第二步：让该目录拒绝写入
```
# Windows PowerShell
$u = "$env:USERDOMAIN\$env:USERNAME"
# 目录必须先存在：icacls 不会替你创建
New-Item -ItemType Directory -Force -Path "<STAGING_DIR>" | Out-Null
icacls "<STAGING_DIR>" /deny "${u}:(W,DC)"     # 必须写 ${u}；写成 "$u:(W,DC)" 会解析失败
# 解除：
icacls "<STAGING_DIR>" /remove:d "$u"

# Linux（强封锁必须 root；普通用户做不到，见 §6.3）
sudo chattr +i "<STAGING_DIR>"     # 不可变，连 root 写也挡
# 解除：sudo chattr -i "<STAGING_DIR>"

# macOS（无 chattr；用户级即可）
chmod 500 "<STAGING_DIR>"          # 5=r-x，去掉写位 → 目录内建不了条目
# 解除：chmod 700 "<STAGING_DIR>"
```
**正向验证（首选，随时可做，不依赖当期是否有可下载更新）**：
```
# Windows：应报 “拒绝访问 / Access denied”
New-Item -ItemType File -Path "<STAGING_DIR>\t" -ErrorAction Stop
Remove-Item "<STAGING_DIR>\t" -ErrorAction SilentlyContinue
# macOS / Linux：应报 Permission denied
touch "<STAGING_DIR>/t"
```
**旁证**（仅当当期确实触发过下载时才有）：日志出现 `downloadUpdate error: EPERM`（Win）/ `EACCES`（macOS/Linux）。
> ⚠️ 若当期没有可下载的新版本，staging 本来是空的、日志也不会出现 `EPERM` —— **这不等于封锁失效**，请以上面的正向验证为准。

#### 第三步：防「临时目录被系统清理后封锁失效」
`Temp` / `/tmp` 类目录可能被清理，ACL/权限会随之丢失。加一个**登录时触发**的守卫（开机执行一次即可，**不必常驻轮询**）：
- 对每个 staging 目录：不存在则创建 → 重加封锁 → 清掉里面已落盘的安装器
- 注册为登录触发任务（Windows 计划任务 / launchd / systemd user unit）

> Windows 参考脚本见 §6.2。

### 3.4 加固：同时改数据目录里的产品配置缓存
若 3.2 后日志仍显示 `productBase=true`，说明该值来自缓存，一并改：
```
<数据目录>/cache/acc-product-config-v3.json  →  updates.startupForceAutoUpdate = false
```
**两版的数据目录各改一次。** 改前备份该缓存文件（`cp "<文件>" "<文件>.bak"`）。此步与 §3.2 的备份分开，回滚见 §7。

---

## 4. 验证（逐步做，全部通过才算成）

### 4.1 层 1 生效
启动主程序，看 `<数据目录>/logs/update/update-YYYYMMDD.log`：
```
改前： Startup force auto-update: enabled=true  source=product-base
改后： Startup force auto-update: enabled=false source=product-base   ← 期望
```
并且**不再出现**下面任意一行：
```
State changed: ready
Restored downloaded update from cache
[early-silent-startup-update] ready update restored before window, quitting to install
quitAndInstall
```
最后**重启电脑再验一次**（根因 B 的复发点就在这里）。

### 4.2 层 2 生效
**以 §3.3 第二步的「正向验证」为主判据**（向 staging 目录写一个文件应报拒绝）。日志侧的 `downloadUpdate error: EPERM`（Win）/ `EACCES`（macOS/Linux）仅作旁证——当期无新版本可下时不出现，**不代表失效**。

### 4.3 隔离生效
- `<DIR_CN>/…/product.json` 与 `<DIR_INTL>/…/product.json` 分别对应国内版/国际版
- **两数据目录是不同源**（路径不同）+ 各自启动后只写自己的目录 —— 这才是隔离的判据
- ⚠️ **`uid` 相同不等于串号**：若你**故意两版登同一个账号**，`uid` 本来就相同，这是允许的。
  **串号的判据 = 「两版指向同一数据目录」**（见 §5.3），不是 uid 相等。
- 各自启动后，只写自己的数据目录：
```
Get-ChildItem $HOME -Force -Directory | Where-Object Name -like '.workbuddy*' |
  ForEach-Object { "$($_.Name)  $((Get-ChildItem $_.FullName -Force | Sort-Object LastWriteTime -Descending | Select-Object -First 1).LastWriteTime)" }
```

### 4.4 双开最终验证
先起 A，等界面出来，再起 B，然后看进程**是否两个都在**：
```
# Windows
Get-Process | Where-Object { $_.ProcessName -match 'WorkBuddy' } |
  Group-Object ProcessName | Select-Object Count,Name
# macOS / Linux
ps aux | grep -i workbuddy | grep -v grep
```
期望：出现**两个不同的进程名/路径**（如 `WorkBuddy` 与 `WorkBuddyAI`）。
若只有一个 → 见 §5.1 / §5.2。

---

## 5. 常见问题与坑

### 5.1 起第二个没反应 / 第一个被顶掉
- 检查两版是否**真的装在不同目录**（§3.1）。装到同一目录 = 只有一版存在。
- 检查每个安装目录的 `product.json` 的 `win32MutexName` 是否**不同**（`workbuddy` vs `workbuddy-ai`）。相同则说明两个安装包其实是同一版。
- 先完全退出（含托盘）再起第二个，避免旧实例残留。
- **两版建议各登各的账号**。据社区反馈，该产品的**远程控制/助理通道**采用「最后登录有效」（后登设备接管指令下发）；若两版同账号可能互相顶掉。此点非官方文档明示，仅作规避建议。**两版会话数据本身按 `user_id` 隔离，同账号不会合并数据。**

### 5.2 装了「国际版」却是国内版
**假包陷阱**：只认 §1.1 的「产品名称」与 §1.2 的 `applicationName`/`dataFolderName`，**不认文件名里的 `AI` 字样**。请从官方国际站下载。

### 5.3 两版账号串了（A 版显示 B 版账号）
- **判据不是「uid 相同」**：若你**故意两版登同一个账号**，`uid` 本来就相同，这是允许的。
  真判据 = **两版指向同一个数据目录**（例如装在同一目录 / 数据目录被指到同一处），或只登了一套账号却看到另一套的历史数据。
- 原因：两版**共用同一份登录态来源**。
- 处理（按顺序）：
  1. 确认两版**安装目录**与**数据目录**都分开（§3.1、§1.3）—— 串号只会在「两版指向同一数据目录」时发生
  2. 两版分别「退出登录」，再各自重新登录对应账号（§5.1 已提示两版建议各登各的账号）
  3. 仅在需要合并**历史数据归属**时，才考虑社区第三方工具（**未核实、自负风险**）：
     `github.com/xiaoliuzhuan666/workbuddy-account-migrate`
     ⚠️ 据其自述：同机装两版时**必须按「数据目录」区分登录态**，不要按 `storage.json`，否则会判错方向。

### 5.4 卸载重装后依旧复发
因为**卸载器不清 staging 目录**。必须做 §3.3；只重装不做封锁，重启后仍会被缓存的安装器覆盖。

### 5.5 想恢复自动更新
- 把 §3.2 的 `updates.startupForceAutoUpdate` 改回 `true`
- 按 §3.3 第二步的「解除」命令去掉封锁
- 手动升级**不受封锁影响**：直接跑新版安装包即可（实测封锁状态下静默安装 `exit=0`）；装完记得**重新打一遍 §3.2**。

### 5.6 安全软件拦截
官方 FAQ 指出登录失败常见原因含**安全软件拦截**（如火绒 / 360 / 电脑管家 / Windows 安全中心），可先临时退出重试。
出处见 `www.workbuddy.ai/docs/zh/workbuddy/From-Beginner-to-Expert-Guide/FAQ`（登录失败三条原因：默认浏览器 / 账号目录权限 / 安全软件拦截）。

### 5.7 国际版登录不上：先分清「网络」还是「本方案」
国际站 `workbuddy.ai` 与国内站域名不同，**部分地区直连可能不通**。30 秒判定：
1. 浏览器直接开 `https://www.workbuddy.ai/` —— 打不开 ⇒ **网络/ DNS 问题**，与本方案无关，别继续改文件。
2. 浏览器能开、客户端登录页打不开/转圈 ⇒ 多半是 §5.6 安全软件或默认浏览器未设置（把 Chrome 设为默认浏览器后重试）。
3. 客户端提示登录成功但界面报错/无会话 ⇒ 看 §4.3，多半是数据目录/账号隔离问题。

### 5.8 特殊安装形态

#### 绿色版 / 解压版（无安装器、不在系统卸载登记里）
特征：解压即用，`应用和功能` 列表里**没有**对应条目。
- **根因 A 不适用**（没有安装器会覆盖你），可直接跳到 §3.2 + §3.3
- 更新行为可能不同（内置更新器、或压根不自更新），**以日志为准**：有 `Restored downloaded update from cache` 才需要层 1，否则只需 §3.3
- 数据目录判定方式与安装版一致（§1.3）

#### 只想保留一个版本（不双开）
不用看 §3.1，**做 §3.2 + §3.3 后重装一次你要的那版**即可，不会再被覆盖。都不想留时按 §5.5 恢复 + §7 回滚，再正常卸载。

#### 没有日志可看时怎么判
- **层 1 是否生效**：重启后直接看安装目录那个 `product.json` 的 `updates.startupForceAutoUpdate` 是否仍为 `false`（被改回 `true` = 仍有路径在写它）
- **层 2 是否生效**：直接做 §3.3 第二步的**正向验证**（尝试写 staging 目录，应被拒）
- **是否需要层 1**：看 staging 目录里是否出现过 `*.exe`

---

## 6. 附录

### 6.1 关闭「启动期强装」的一键脚本（跨平台，Python 3，仅标准库）
把 `TARGETS` 换成**你实际安装目录的绝对路径**（§1.4 探测结果）。**执行前先退出客户端。**
```python
import json, os, shutil
TARGETS = [
    # 换成绝对路径；Windows 例：r"C:\Users\me\AppData\Local\Programs\WorkBuddy\resources\app.asar.unpacked\cli\product.json"
    "/absolute/path/to/<DIR_CN>/resources/app.asar.unpacked/cli/product.json",
    "/absolute/path/to/<DIR_INTL>/resources/app.asar.unpacked/cli/product.json",
    # 可选：数据目录缓存（仅当 §3.2 无效时启用）
    # os.path.expanduser("~/.workbuddy/cache/acc-product-config-v3.json"),
    # os.path.expanduser("~/.workbuddy-ai/cache/acc-product-config-v3.json"),
]
for f in TARGETS:
    f = os.path.expanduser(f)
    if not os.path.exists(f):
        print("skip (missing):", f); continue
    if not os.path.exists(f + ".bak"):
        shutil.copy2(f, f + ".bak")     # 仅首次创建，避免二次运行把原始备份覆盖成已改版
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception as e:
        print("解析失败（可能是 JSONC，请改用手工文本编辑）:", f, e); continue
    u = d.get("updates")
    if not isinstance(u, dict):
        d["updates"] = {"apiVersion": "v2", "startupForceAutoUpdate": False}
    else:
        u["startupForceAutoUpdate"] = False
        if "apiVersion" not in u:
            u["apiVersion"] = "v2"      # 与 §3.2 规则一致：缺则补，避免回落 hardcoded-fallback
    json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("patched:", f)
```
> 生成 `.bak` 备份，可回滚。若 `product.json` 不存在，说明该版本打包方式不同 —— 退化为「只做 §3.3 的封锁」，并考虑升级到含该文件的版本。

### 6.2 Windows 守卫脚本（防 Temp 清理后封锁失效）
存为 `block-update-staging.ps1`：
```powershell
$ErrorActionPreference = 'SilentlyContinue'
$user  = "$env:USERDOMAIN\$env:USERNAME"
$paths = @(
  "$env:LOCALAPPDATA\@genieworkbuddy-desktop-updater",
  "$env:TEMP\workbuddy-update-x64"          # 用 $env:TEMP，勿硬编码 $env:LOCALAPPDATA\Temp（用户可能把 TEMP 改到别盘）
)
foreach ($p in $paths) {
  if (-not (Test-Path -LiteralPath $p)) { New-Item -ItemType Directory -Force -Path $p | Out-Null }
  # 1) 先把已落盘的安装器删掉（趁还没上 DENY，否则 deny 会传播到子文件导致删不动）
  Get-ChildItem -LiteralPath $p -Recurse -Force -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  # 2) 再上 deny
  $acl  = Get-Acl -LiteralPath $p
  $deny = New-Object System.Security.AccessControl.FileSystemAccessRule(
            $user, "Write,DeleteSubdirectoriesAndFiles", "Deny")
  $acl.AddAccessRule($deny); Set-Acl -LiteralPath $p -AclObject $acl
  # 3) 自检：确认已拒写
  $probe = Join-Path $p "__wb_probe.tmp"
  try {
    "x" | Set-Content -LiteralPath $probe -ErrorAction Stop
    Remove-Item -LiteralPath $probe -Force -ErrorAction SilentlyContinue
    Write-Host "WARN 仍可写入: $p"
  } catch {
    Write-Host "OK   已拒写: $p"
  }
}
```
注册为**登录触发**任务（**执行一次即可，不要轮询**）——**需以管理员身份运行 PowerShell**：
```powershell
$act = New-ScheduledTaskAction -Execute "powershell.exe" `
       -Argument '-NoProfile -WindowStyle Hidden -File "<脚本绝对路径>"'
$trg = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "WorkBuddy-Staging-Guard" -Action $act -Trigger $trg -Force
```

### 6.3 macOS / Linux 对应做法
- **launchd（macOS）**：写 `~/Library/LaunchAgents/<label>.plist`，`RunAtLoad=true`，`ProgramArguments` 调一个 shell 脚本做 `mkdir -p` + `chmod 500` + 清目录。（macOS 是用户级 `chmod`，无需 root。）
- **systemd（Linux）**：
  - `chattr +i`（强封锁）需 root → 必须用 **system 级**：`sudo systemctl` 或 `/etc/rc.local`
  - 仅用 `chmod` 则可用 **user unit**：`~/.config/systemd/user/<name>.service`，`WantedBy=default.target`
  - **两者二选一，别混用**；user unit 拿不到 root，做不了 `chattr +i`
- 脚本内容与 §6.2 等价，顺序必须一致：**创建 → 清空 → 封锁**。
  （先删已有安装器再收紧权限 —— 反过来会因没有写权限而删不动，`chattr +i` 下更是自相矛盾。）

### 6.4 日志速查（诊断全靠它）
| 位置 | 内容 |
|---|---|
| `<数据目录>/logs/update/update-YYYYMMDD.log` | 更新检查 / 下载 / 启动期强装 / staging 路径 |
| `<数据目录>/logs/installer.log`、`register.log` | 安装器落点、文件关联/ShareTarget 注册 |
| `<数据目录>/logs/main.log`、`daemon.log`、`renderer.log` | 登录、产品判定、网络请求 |
| `<数据目录>/storage/skeleton/account-snapshot.json` | 当前登录账号 `primary.uid` |

关键串（grep 这些即可定位阶段）：
`enabled=` / `source=product-base` / `Restored downloaded update from cache` / `quitAndInstall` / `Launching installer:` / `downloadUpdate error` / `Update downloaded:`

> 日志按天轮转，`update-YYYYMMDD.log` 的日期为**本机当天**。取最新日志：
> ```
> # Windows
> Get-ChildItem "$HOME\.workbuddy*\logs\update\update-*.log" | Sort-Object LastWriteTime -Descending | Select-Object -First 3
> # macOS / Linux
> ls -lt ~/.workbuddy*/logs/update/update-*.log | head -3
> ```

---

## 7. 回滚清单
| 动作 | 回滚 |
|---|---|
| 改 `product.json` | 用同目录 `.bak` 覆盖回去；若无 `.bak`：原值 `true` 的改回 `true`；**原文件本无 `updates` 字段的，删除新增的 `updates` 整块** |
| 改数据目录缓存（§3.4） | 用该缓存文件的 `.bak` 覆盖回去；若无备份，把 `updates.startupForceAutoUpdate` 改回 `true`（若原无该字段则删掉它） |
| Windows ACL 封锁 | `icacls "<DIR>" /remove:d "<user>"` |
| Linux 不可变 | `chattr -i "<DIR>"` |
| macOS 只读 | `chmod 700 "<DIR>"` |
| 守卫任务 | `Unregister-ScheduledTask -TaskName "WorkBuddy-Staging-Guard"`（或删 launchd/systemd unit）。**⚠️ 解 ACL 封锁前必须先注销守卫任务**，否则下次登录守卫会重建 deny，你会以为"恢复更新失败" |
| 复制冻结的安装 | 直接删除该目录 |

---

## 8. 方案边界（如实声明）
- 本文的 **Windows 路径、ACL 封锁、`updates.startupForceAutoUpdate` 开关**均已**实测生效**。
- **macOS / Linux 的路径与权限手段未实测**，按 Electron 通用规律给出；请以本地日志打印的路径为准（§3.3 第一步）。
- 若某版本把自动更新改成「整包替换」且不走 staging，封锁会失效；此时以「关开关 + 不同目录」为主，必要时降级为 VMware/Hyper-V/独立用户账户隔离。
- 官方**从未承诺**同机双开；本文是把两版**本已独立的身份**用起来，并堵住会破坏它的自动更新。产品若变更行为，请以本文 §1 探测 + §4 验证重新判定。
