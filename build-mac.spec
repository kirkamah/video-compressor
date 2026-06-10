# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the macOS .app bundle of Video Compressor.
# Build (on macOS): pyinstaller --noconfirm build-mac.spec
# Expects mac static engines at bin/ffmpeg and bin/ffprobe, and an
# assets/app.icns icon — the CI workflow puts both in place before building.
from PyInstaller.utils.hooks import collect_all

datas = [
    ("bin/ffmpeg", "bin"),
    ("bin/ffprobe", "bin"),
    ("assets/app.png", "assets"),
]
binaries = []
hiddenimports = []

# customtkinter themes + tkinterdnd2 (tkdnd) native bits.
for pkg in ("customtkinter", "tkinterdnd2"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

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
)
coll = COLLECT(exe, a.binaries, a.datas, name="VideoCompressor")

app = BUNDLE(
    coll,
    name="Video Compressor.app",
    icon="assets/app.icns",
    bundle_identifier="org.noharm.videocompressor",
    info_plist={
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
        "CFBundleShortVersionString": "1.0.0",
    },
)
