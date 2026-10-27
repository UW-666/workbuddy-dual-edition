# workbuddy-dual-edition

Tencent **WorkBuddy 国内版与国际版同机共存**的完整处置方案，同时是一个可直接加载的 Agent Skill。

> **来源与致谢**：本仓库 fork 自 [ZenHG/workbuddy-dual-edition](https://github.com/ZenHG/workbuddy-dual-edition)。
> 原方案（v1.0：根因分析、四步处置、playbook、日志速查）全部出自原作者 **ZenHG**，见 init commit `2dcd841`。
> 本 fork 增量（v1.1，2026-10-27）：playbook §9 重装整包治本路线、§10 衍生故障排查、`scripts/` 验证与图标修复脚本，来自一次真实修复实战。

## 它解决什么

- 装国内版，一启动却变成国际版
- 电脑重启后故障复发、卸载重装无数次无效
- 只能开一个客户端，起第二个没反应
- 国际版/国内版互相顶号、账号串台

## 结论先行

两版是**两个独立产品**（不同 exe、不同互斥锁名、不同数据目录 `.workbuddy` / `.workbuddy-ai`），**本就支持同机共存**。
绝大多数「只能开一个 / 被覆盖」是**自动更新**覆盖安装目录造成的假象。

处置 = **关掉启动期强装** + **阻断其下载落盘** + **两版装不同目录**。

## 目录

```
SKILL.md                          # Agent 用：触发词 → 三问定位 → 分支路由 → 确认闸
references/
  full-playbook.md                # 完整方案：探测/根因/四步处置/验证/FAQ/回滚
  log-cheatsheet.md               # 日志关键字速查 + source 五源对照表
  platform-notes.md               # 各平台实测状态与边界（谁实测过、谁没有）
scripts/
  verify_install.py               # 重装/升级后一键验证（asar版本/manifest/product.json/配置/vbs/auth）
  fix_lnk_icon.py                 # 桌面快捷方式图标空白修复（comtypes 改 IconLocation）
```

## 2026-10-27 更新（v1.1）

- **新增 playbook §9「重装整包治本路线」**：四步方案治不了的混合构建症状（套餐面板转圈且零请求、积分刷不出、改 links 仍跳错域名）→ 官网整包覆盖安装 + 装后验证清单
- **新增 playbook §10「衍生故障排查」**：桌面图标空白（IconLocation 失效）、旧安装位置空壳 + defaultWorkspacePath 残留、vbs/lnk 的 UTF-16LE 编码坑
- **新增 `scripts/verify_install.py`**：重装后逐项验证（11 项检查，两版实测 11/11、7/7 通过）
- **新增 `scripts/fix_lnk_icon.py`**：不改目标只改图标，自动备份，兼容受限环境（无 PowerShell COM / reg.exe）
- 关键结论：**干净整包原生自带正确配置**（isOversea:false、startupForceAutoUpdate:false），混合目录上的手工补丁在重装后不再需要

## 快速开始

**只想读文档**：从 [references/full-playbook.md](references/full-playbook.md) §1 探测开始，按 §3 四步执行，最后按 §4 验证。

**给 AI Agent 用**：把 `SKILL.md` 放进你的 skills 目录，它会自动带上前三个 references。

**最小修复（只想不被覆盖，不双开）**：做 playbook §3.2 + §3.3 两件事即可。

## 实测状态（如实声明）

| 项目 | 状态 |
|---|---|
| Windows + WorkBuddy 5.8.x（国内 5.8.2 / 国际 5.8.4）两版并存 + 重启不复发 | ✅ 实测通过 |
| `updates.startupForceAutoUpdate` 开关位置与效果（Win） | ✅ 实测 |
| staging 目录路径与封锁（Win） | ✅ 实测 |
| 本仓所有命令/脚本 | ✅ 均真实执行验证过 |
| macOS / Linux 全链路 | ⚠️ **未实测**，按 Electron 通用规律给出，路径需以本地日志为准 |

## 边界

- 官方**从未承诺**同机双开；本方案是把两版本已独立的身份用起来，并堵住破坏它的自动更新。
- 采用本方案 = **放弃自动更新**，升级改为手动运行安装包。
- 若某版本把自动更新改为「整包替换且不走 staging」，目录封锁会失效，需重估。

## 贡献

提 Issue / PR 时请附：**版本号 + 平台 + `<数据目录>/logs/update/` 最新日志片段**。
特别欢迎补充 **macOS / Linux 的实测结果**（这是当前最大空白）。
