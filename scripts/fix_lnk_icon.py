#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修复 Windows 快捷方式图标空白（IconLocation 指向不存在的文件）

依赖: pip install comtypes（写入隔离 venv 亦可）
用法:
  python fix_lnk_icon.py <lnk路径> <新的图标exe路径> [图标索引]

原理: 用 IShellLinkW + IPersistFile 只改 IconLocation 字段，
      目标路径/参数/工作目录/描述等其余字段保持原样。
      修改前自动备份原 .lnk 到同目录（.bak-<时间戳>）。
"""
import ctypes
import os
import shutil
import sys
import time
from ctypes import c_int, c_uint, c_wchar, create_unicode_buffer
from ctypes.wintypes import FILETIME

from comtypes import COMMETHOD, GUID, IUnknown
from comtypes.client import CreateObject

MAX_PATH = 260


class WIN32_FIND_DATAW(ctypes.Structure):
    _fields_ = [
        ("dwFileAttributes", c_uint),
        ("ftCreationTime", FILETIME), ("ftLastAccessTime", FILETIME),
        ("ftLastWriteTime", FILETIME),
        ("nFileSizeHigh", c_uint), ("nFileSizeLow", c_uint),
        ("dwReserved0", c_uint), ("dwReserved1", c_uint),
        ("cFileName", c_wchar * MAX_PATH), ("cAlternateFileName", c_wchar * 14),
    ]


class IPersistFile(IUnknown):
    _iid_ = GUID("{0000010B-0000-0000-C000-000000000046}")
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], ctypes.HRESULT, "GetClassID", (["out"], ctypes.POINTER(GUID), "pClassID")),
        COMMETHOD([], ctypes.HRESULT, "IsDirty", (["out"], ctypes.POINTER(ctypes.c_long), "pfDirty")),
        COMMETHOD([], ctypes.HRESULT, "Load",
                  (["in"], ctypes.c_wchar_p, "pszFileName"), (["in"], c_uint, "dwMode")),
        COMMETHOD([], ctypes.HRESULT, "Save",
                  (["in"], ctypes.c_wchar_p, "pszFileName"), (["in"], ctypes.c_long, "fRemember")),
        COMMETHOD([], ctypes.HRESULT, "SaveCompleted", (["in"], ctypes.c_wchar_p, "pszFileName")),
        COMMETHOD([], ctypes.HRESULT, "GetCurFile", (["out"], ctypes.POINTER(ctypes.c_wchar_p), "ppszFileName")),
    ]


class IShellLinkW(IUnknown):
    _iid_ = GUID("{000214F9-0000-0000-C000-000000000046}")
    _idlflags_ = []
    _methods_ = [
        # 注意：vtable 顺序不可改动
        COMMETHOD([], ctypes.HRESULT, "GetPath",
                  (["in"], ctypes.c_wchar_p, "pszFile"), (["in"], c_int, "cch"),
                  (["in"], ctypes.c_void_p, "pfd"), (["in"], c_uint, "fFlags")),
        COMMETHOD([], ctypes.HRESULT, "GetIDList", (["out"], ctypes.c_void_p, "ppidl")),
        COMMETHOD([], ctypes.HRESULT, "SetIDList", (["in"], ctypes.c_void_p, "pidl")),
        COMMETHOD([], ctypes.HRESULT, "GetDescription",
                  (["in"], ctypes.c_wchar_p, "pszName"), (["in"], c_int, "cch")),
        COMMETHOD([], ctypes.HRESULT, "SetDescription", (["in"], ctypes.c_wchar_p, "pszName")),
        COMMETHOD([], ctypes.HRESULT, "GetWorkingDirectory",
                  (["in"], ctypes.c_wchar_p, "pszDir"), (["in"], c_int, "cch")),
        COMMETHOD([], ctypes.HRESULT, "SetWorkingDirectory", (["in"], ctypes.c_wchar_p, "pszDir")),
        COMMETHOD([], ctypes.HRESULT, "GetArguments",
                  (["in"], ctypes.c_wchar_p, "pszArgs"), (["in"], c_int, "cch")),
        COMMETHOD([], ctypes.HRESULT, "SetArguments", (["in"], ctypes.c_wchar_p, "pszArgs")),
        COMMETHOD([], ctypes.HRESULT, "GetHotkey", (["out"], ctypes.POINTER(ctypes.c_short), "pwHotkey")),
        COMMETHOD([], ctypes.HRESULT, "SetHotkey", (["in"], ctypes.c_short, "wHotkey")),
        COMMETHOD([], ctypes.HRESULT, "GetShowCmd", (["out"], ctypes.POINTER(c_int), "piShowCmd")),
        COMMETHOD([], ctypes.HRESULT, "SetShowCmd", (["in"], c_int, "iShowCmd")),
        COMMETHOD([], ctypes.HRESULT, "GetIconLocation",
                  (["in"], ctypes.c_wchar_p, "pszIconPath"), (["in"], c_int, "cch"),
                  (["in"], ctypes.POINTER(c_int), "piIcon")),
        COMMETHOD([], ctypes.HRESULT, "SetIconLocation",
                  (["in"], ctypes.c_wchar_p, "pszIconPath"), (["in"], c_int, "iIcon")),
        COMMETHOD([], ctypes.HRESULT, "SetRelativePath", (["in"], ctypes.c_wchar_p, "pszPathRel")),
        COMMETHOD([], ctypes.HRESULT, "Resolve", (["in"], c_uint, "hwnd"), (["in"], c_uint, "fFlags")),
        COMMETHOD([], ctypes.HRESULT, "SetPath", (["in"], ctypes.c_wchar_p, "pszFile")),
    ]


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(2)
    lnk = os.path.abspath(sys.argv[1])
    new_icon = os.path.abspath(sys.argv[2])
    icon_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0

    if not os.path.isfile(lnk):
        print(f"[FAIL] 快捷方式不存在: {lnk}"); sys.exit(2)
    if not os.path.isfile(new_icon):
        print(f"[FAIL] 图标目标文件不存在: {new_icon}"); sys.exit(2)

    # 备份
    bak = f"{lnk}.bak-{time.strftime('%Y%m%d-%H%M%S')}"
    shutil.copy2(lnk, bak)
    print(f"backup -> {bak}")

    # 打印旧字符串段（UTF-16LE），便于确认旧 IconLocation
    data = open(lnk, "rb").read()
    import re
    for s in re.findall(rb"(?:[\x20-\x7e]\x00){4,}", data):
        t = s.decode("utf-16-le")
        if "exe" in t.lower() or ":\\" in t:
            print("  old string:", t)

    # 修改
    import comtypes
    comtypes.CoInitialize()
    shell_link = CreateObject("{00021401-0000-0000-C000-000000000046}", interface=IShellLinkW)
    pf = shell_link.QueryInterface(IPersistFile)
    pf.Load(lnk, 0)
    shell_link.SetIconLocation(new_icon, icon_index)
    pf.Save(lnk, True)
    print("saved:", lnk)
    print(f"new IconLocation: {new_icon},{icon_index}")

    # 回读验证
    idx = c_int()
    buf = create_unicode_buffer(1024)
    shell_link.GetIconLocation(buf, 1024, ctypes.byref(idx))
    ok = os.path.isfile(buf.value)
    print(f"verify: {buf.value},{idx.value}  exists={ok}")
    print("\n若桌面图标未立即刷新：F5 刷新桌面，或 ie4uinit.exe -show，或重启 explorer。")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
