#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""WorkBuddy 重装/升级后一键验证脚本（仅标准库，Windows）

用法:
  python verify_install.py --install-dir "E:\\Workbuddy"            # 国内版
  python verify_install.py --install-dir "E:\\WorkBuddy国外版"      # 国际版
  python verify_install.py --install-dir "E:\\Workbuddy" --auth-dir "C:\\Users\\UW\\AppData\\Local\\CodeBuddyExtension\\Data\\Public\\auth"

逐项检查并输出 PASS/FAIL：
  1. asar 内 package.json version
  2. resources/install-manifest.json（appVersion / fileCount）
  3. product.json 关键字段（authentication.id / links 域名 / isOversea）
  4. cn-product-config.json（isOversea / updates.startupForceAutoUpdate）
  5. 启动 vbs 是否存在（launch-cn.vbs / launch-oversea.vbs，按版别）
  6. auth 会话文件（--auth-dir 给定时检查）
"""
import argparse
import json
import os
import re
import struct
import sys

OK, BAD, WARN = "[PASS]", "[FAIL]", "[WARN] "
results = []


def check(name, ok, detail="", warn=False):
    tag = WARN if warn else (OK if ok else BAD)
    results.append((name, ok or warn))
    print(f"{tag} {name}" + (f"  ->  {detail}" if detail else ""))


def parse_asar_version(asar_path):
    """从 asar 读取 package.json 的 version/name。宽松解析，不依赖严格 JSON。"""
    with open(asar_path, "rb") as f:
        f.read(8)  # pickle 头
        header_size = struct.unpack("<I", f.read(4))[0]
        header_raw = f.read(header_size)
    s = header_raw.decode("utf-8", "ignore")
    start = s.find("{")
    header = json.loads(s[start: s.rfind("}") + 1])
    pkg = header["files"]["package.json"]
    offset, size = int(pkg["offset"]), int(pkg["size"])
    with open(asar_path, "rb") as f:
        f.seek(8 + header_size + offset)
        # 前 4 字节是 pickle 前缀，向后搜到 '{' 再解析
        raw = f.read(size + 16)
    i = raw.find(b"{")
    if i < 0:
        return None, None
    txt = raw[i:].decode("utf-8", "ignore")
    ver = re.search(r'"version"\s*:\s*"([^"]+)"', txt)
    name = re.search(r'"name"\s*:\s*"([^"]+)"', txt)
    return (ver.group(1) if ver else None), (name.group(1) if name else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--install-dir", required=True)
    ap.add_argument("--expect-version", default=None, help="期望版本号，缺省只报告不比对")
    ap.add_argument("--auth-dir", default=None, help="共享 auth 目录路径")
    ap.add_argument("--edition", choices=["cn", "intl", "auto"], default="auto",
                    help="版别：cn=国内 intl=国际 auto=按 links 域名自动判定")
    args = ap.parse_args()

    d = args.install_dir
    if not os.path.isdir(d):
        print(f"{BAD} 安装目录不存在: {d}")
        sys.exit(2)

    # 1. asar version
    asar = os.path.join(d, "resources", "app.asar")
    if os.path.isfile(asar):
        try:
            ver, name = parse_asar_version(asar)
            check("asar package.json 可解析", ver is not None, f"name={name} version={ver}")
            if args.expect_version:
                check(f"asar 版本 == {args.expect_version}", ver == args.expect_version, f"实际 {ver}")
        except Exception as e:
            check("asar package.json 可解析", False, f"解析失败: {e}")
    else:
        check("app.asar 存在", False, asar)

    # 2. install-manifest
    mf = os.path.join(d, "resources", "install-manifest.json")
    if os.path.isfile(mf):
        try:
            m = json.load(open(mf, encoding="utf-8"))
            mv, fc = m.get("appVersion"), m.get("fileCount")
            check("install-manifest.json 有效", bool(mv), f"appVersion={mv} fileCount={fc} generatedAt={m.get('generatedAt')}")
            if ver:
                check("manifest.appVersion 与 asar 版本一致", mv == ver, f"{mv} vs {ver}")
        except Exception as e:
            check("install-manifest.json 有效", False, f"解析失败: {e}")
    else:
        check("install-manifest.json 存在", False, "缺失会触发启动期「安装文件损坏」弹窗")

    # 3. product.json
    pj = os.path.join(d, "resources", "app.asar.unpacked", "cli", "product.json")
    if os.path.isfile(pj):
        try:
            p = json.load(open(pj, encoding="utf-8"))
            auth = p.get("authentication") or {}
            aid = auth.get("id") if isinstance(auth, dict) else None
            help_url = (p.get("links") or {}).get("helpDocument", "")
            is_cn_link = "workbuddy.cn" in help_url or "codebuddy.cn" in help_url
            is_intl_link = ".ai/" in help_url or "workbuddy.ai" in help_url
            check("product.json authentication.id 非空", bool(aid), f"id={aid}")
            if args.edition == "cn":
                check("product.json links 指向 .cn", is_cn_link, help_url)
            elif args.edition == "intl":
                check("product.json links 指向海外域名", is_intl_link, help_url)
            else:
                print(f"{WARN} 未指定 --edition，域名仅报告: helpDocument={help_url}")
            if "isOversea" in p:
                print(f"{WARN} product.json 含 isOversea 字段（值为 {p['isOversea']}）。"
                      f"官方整包通常无此字段；若出现，说明可能叠加了另一版残留，需排查")
        except Exception as e:
            check("product.json 可解析", False, f"解析失败: {e}")
    else:
        check("product.json 存在", False, pj)

    # 4. cn-product-config.json
    cc = os.path.join(d, "cn-product-config.json")
    if os.path.isfile(cc):
        try:
            c = json.load(open(cc, encoding="utf-8"))
            up = c.get("updates") or {}
            if args.edition == "intl":
                print(f"{WARN} 国际版 cn-product-config 仅报告: isOversea={c.get('isOversea')} "
                      f"startupForceAutoUpdate={up.get('startupForceAutoUpdate')}")
            else:
                check("cn-product-config isOversea 为 False", c.get("isOversea") is False, f"实际 {c.get('isOversea')}")
                check("updates.startupForceAutoUpdate 为 False", up.get("startupForceAutoUpdate") is False,
                      f"实际 {up.get('startupForceAutoUpdate')}（True 会在启动期强装更新）")
        except Exception as e:
            check("cn-product-config.json 可解析", False, f"解析失败: {e}")
    else:
        print(f"{WARN} 未找到 cn-product-config.json（部分打包形态可能没有）")

    # 5. 启动 vbs（双版共存方案的自定义启动脚本；注意部分脚本为 UTF-16LE 编码）
    for vbs in ("launch-cn.vbs", "launch-oversea.vbs"):
        p = os.path.join(d, vbs)
        if os.path.isfile(p):
            raw = open(p, "rb").read()
            if raw[:2] in (b"\xff\xfe", b"\xfe\xff") or b"\x00" in raw[:200]:
                content = raw.decode("utf-16-le", "ignore")
            else:
                content = raw.decode("utf-8", "ignore")
            ok = ("WORKBUDDY_CONFIG_DIR" in content) and ("WorkBuddy" in content)
            check(f"{vbs} 存在且指向有效配置目录", ok)
        else:
            print(f"{WARN} 未找到 {vbs}（若未部署双版启动脚本可忽略）")

    # 6. auth 会话
    if args.auth_dir and os.path.isdir(args.auth_dir):
        for f in ("workbuddy-desktop.info", "workbuddy-desktop-ai.info"):
            check(f"auth 会话文件存在: {f}", os.path.isfile(os.path.join(args.auth_dir, f)))
    elif args.auth_dir:
        check("auth 目录存在", False, args.auth_dir)

    failed = [n for n, ok in results if not ok]
    print("\n==== 汇总 ====")
    print(f"通过 {len(results) - len(failed)}/{len(results)} 项")
    if failed:
        print("未通过：")
        for n in failed:
            print("  -", n)
        sys.exit(1)
    print("全部通过。")


if __name__ == "__main__":
    main()
