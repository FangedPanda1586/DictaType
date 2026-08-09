# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_submodules

# pyttsx3/SAPI imports are partly dynamic on Windows.
hiddenimports = collect_submodules("pyttsx3") + [
    "pyttsx3.drivers.sapi5",
    "pythoncom",
    "pywintypes",
    "win32com.client",
]

# Piper bundles Python modules, an embedded eSpeak bridge, eSpeak language
# data and native libraries. collect_all is deliberately used here because a
# partial bundle can import in the build environment but fail inside the frozen
# Windows executable. The release workflow performs a real synthesis test on
# the finished EXE before publishing it.
piper_datas, piper_binaries, piper_hidden = collect_all("piper")
onnx_datas, onnx_binaries, onnx_hidden = collect_all("onnxruntime")
hiddenimports += piper_hidden + onnx_hidden

datas = piper_datas + onnx_datas + [
    ("assets/voices", "assets/voices"),
]
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="DictaType",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Your working repository currently keeps the icon at the project root.
    icon="dictatype.ico",
)
