# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# pyttsx3/SAPI imports are partly dynamic on Windows.
hiddenimports = collect_submodules("pyttsx3") + [
    "pyttsx3.drivers.sapi5",
    "pythoncom",
    "pywintypes",
    "win32com.client",
]

# Piper 1.5 contains a native eSpeak bridge plus eSpeak language data, while
# ONNX Runtime supplies native inference DLLs. Keep both packages complete.
piper_datas, piper_binaries, piper_hidden = collect_all("piper")
onnx_datas, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
hiddenimports += piper_hidden + onnx_hidden

datas = piper_datas + onnx_datas
binaries = piper_binaries + onnx_binaries

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

# IMPORTANT: DictaType now uses PyInstaller's one-folder layout internally.
# This keeps Piper/eSpeak/ONNX native files in a stable on-disk layout instead
# of unpacking them into a temporary _MEI directory on every launch. The user
# still launches a normal DictaType.exe, and the installer hides the internals.
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DictaType",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="dictatype.ico",
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DictaType",
)
