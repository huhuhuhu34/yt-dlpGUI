# -*- mode: python ; coding: utf-8 -*-
# yt-dlpGUI Windows 单文件打包配置
# 用法：python -m PyInstaller --noconfirm --clean yt-dlpGUI.spec
# （必须在本机是 Windows 时执行；仓库已提供 GitHub Actions 自动构建）

a = Analysis(
    ['ytdlpGUI.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['ytdlp_gui', 'ytdlp_gui.ui'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter.test'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='yt-dlpGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # 窗口程序（不带黑框）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/yt-dlpGUI.ico',
)
