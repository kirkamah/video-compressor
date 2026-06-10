# Video Compressor - a no harm org project
# Author: Kirkamah  |  (c) 2026 Kirkamah / no harm org - All rights reserved.
"""Сборка ПРОБНОЙ (trial) версии «Видео-компрессор».

Запуск:  .venv\\Scripts\\python scripts\\build_trial.py

Что делает:
1. Временно ставит TRIAL = True в src/vcompress/trial.py.
2. Собирает PyInstaller-сборку в dist-trial\\ (обычная dist\\ не трогается).
3. Возвращает TRIAL = False (try/finally — репозиторий не остаётся в trial-состоянии).
4. Если найден Inno Setup — собирает installer\\VideoCompressor-Trial-Setup.exe
   по временной trial-копии installer.iss; иначе делает
   installer\\VideoCompressor-Trial-portable.zip.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRIAL_PY = ROOT / "src" / "vcompress" / "trial.py"
DIST_TRIAL = ROOT / "dist-trial"
WORK_TRIAL = ROOT / "build-trial"
OUT_DIR = ROOT / "installer"

OFF = "TRIAL = False"
ON = "TRIAL = True"


def find_iscc() -> str | None:
    found = shutil.which("iscc")
    if found:
        return found
    candidates = [
        Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return None


def set_trial(enabled: bool) -> None:
    """Переключить строку флага. Сравнение целыми строками, чтобы не задеть
    случайные упоминания в комментариях/докстрингах."""
    src, dst = (OFF, ON) if enabled else (ON, OFF)
    lines = TRIAL_PY.read_text(encoding="utf-8").splitlines(keepends=True)
    for n, line in enumerate(lines):
        if line.rstrip("\r\n") == src:
            lines[n] = line.replace(src, dst)
            TRIAL_PY.write_text("".join(lines), encoding="utf-8")
            print(f"[trial] {TRIAL_PY.name}: {dst}")
            return
    if any(line.rstrip("\r\n") == dst for line in lines):
        return  # уже в нужном состоянии
    raise RuntimeError(f"В {TRIAL_PY} не найдена строка '{src}'")


def build_pyinstaller() -> None:
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm",
        "--distpath", str(DIST_TRIAL),
        "--workpath", str(WORK_TRIAL),
        str(ROOT / "build.spec"),
    ]
    print("[trial] PyInstaller:", " ".join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def make_trial_iss() -> Path:
    """Trial-копия installer.iss: своё имя, свой AppId, своя папка установки."""
    text = (ROOT / "installer.iss").read_text(encoding="utf-8-sig")
    replacements = [
        ('#define AppName "Видео-компрессор"',
         '#define AppName "Видео-компрессор (Пробная версия)"'),
        ('AppId={{8B2E6C41-9F3A-4D7E-B1C2-7A5E0D9F4C10}',
         'AppId={{8B2E6C41-9F3A-4D7E-B1C2-7A5E0D9F4C11}'),
        ('DefaultDirName={autopf}\\VideoCompressor',
         'DefaultDirName={autopf}\\VideoCompressorTrial'),
        ('OutputBaseFilename=VideoCompressor-Setup',
         'OutputBaseFilename=VideoCompressor-Trial-Setup'),
        ('Source: "dist\\VideoCompressor\\*"',
         'Source: "dist-trial\\VideoCompressor\\*"'),
    ]
    for old, new in replacements:
        if old not in text:
            raise RuntimeError(f"В installer.iss не найдено: {old}")
        text = text.replace(old, new, 1)
    out = ROOT / "installer-trial.iss"
    out.write_text(text, encoding="utf-8-sig")
    return out


def build_installer() -> Path:
    iscc = find_iscc()
    if iscc:
        iss = make_trial_iss()
        try:
            print(f"[trial] Inno Setup: {iscc}")
            subprocess.run([iscc, str(iss)], cwd=ROOT, check=True)
        finally:
            iss.unlink(missing_ok=True)
        return OUT_DIR / "VideoCompressor-Trial-Setup.exe"

    print("[trial] Inno Setup не найден — делаю портативный zip.")
    OUT_DIR.mkdir(exist_ok=True)
    zip_path = OUT_DIR / "VideoCompressor-Trial-portable.zip"
    src_dir = DIST_TRIAL / "VideoCompressor"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src_dir.rglob("*"):
            zf.write(f, Path("VideoCompressor-Trial") / f.relative_to(src_dir))
    return zip_path


def main() -> None:
    set_trial(True)
    try:
        build_pyinstaller()
    finally:
        set_trial(False)
    artifact = build_installer()
    print(f"[trial] Готово: {artifact} ({artifact.stat().st_size / (1024 * 1024):.1f} МБ)")


if __name__ == "__main__":
    main()
