# -*- mode: python ; coding: utf-8 -*-
# Сборка: py -m PyInstaller --noconfirm build.spec
# Результат: dist\VideoCompressor\VideoCompressor.exe (рядом лежит bin\ с ffmpeg).

from PyInstaller.utils.hooks import collect_all

datas = [
    ("bin/ffmpeg.exe", "bin"),
    ("bin/ffprobe.exe", "bin"),
    ("assets/app.ico", "assets"),
]
binaries = []
hiddenimports = []

# Собираем ресурсы customtkinter (темы) и tkinterdnd2 (бинарники tkdnd).
for pkg in ("customtkinter", "tkinterdnd2"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

icon = "assets/app.ico"

a = Analysis(
    ["run.py"],
    pathex=["src"],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="VideoCompressor",
    console=False,
    icon=icon if __import__("os").path.exists(icon) else None,
)
coll = COLLECT(
    exe, a.binaries, a.datas,
    name="VideoCompressor",
)
