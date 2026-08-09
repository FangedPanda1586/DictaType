# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

# pyttsx3/SAPI imports are partly dynamic on Windows.
hiddenimports = collect_submodules("pyttsx3") + [
    "pyttsx3.drivers.sapi5",
    "pythoncom",
    "pywintypes",
    "win32com.client",
]

# Piper includes an embedded eSpeak-NG phonemizer and ONNX Runtime. The data
# and native libraries must be copied explicitly into a one-file build.
piper_datas = collect_data_files("piper")
piper_binaries = collect_dynamic_libs("piper")
onnx_binaries = collect_dynamic_libs("onnxruntime")
hiddenimports += [
    "piper",
    "piper.voice",
    "piper.config",
    "piper.espeakbridge",
] + collect_submodules("onnxruntime.capi")

datas = piper_datas + [
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
