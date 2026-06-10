"""Разрешение путей к bundled ffmpeg/ffprobe — работает и в dev, и в собранном exe."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def base_dir() -> Path:
    """Каталог, в котором лежит папка bin\\ с ffmpeg/ffprobe.

    - В собранном PyInstaller данные кладутся в sys._MEIPASS
      (для --onedir это подпапка _internal, для --onefile — временный каталог).
    - В режиме разработки — корень репозитория (на два уровня выше этого файла:
      src/vcompress/paths.py -> корень).
    """
    if getattr(sys, "frozen", False):
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def _exe(name: str) -> Path:
    """Путь к исполняемому файлу в bin\\; на не-Windows без расширения."""
    if os.name == "nt" and not name.lower().endswith(".exe"):
        name += ".exe"
    return base_dir() / "bin" / name


def asset_path(name: str) -> Path:
    """Путь к файлу в папке assets\\ (иконка и т.п.)."""
    return base_dir() / "assets" / name


def ffmpeg_path() -> Path:
    return _exe("ffmpeg")


def ffprobe_path() -> Path:
    return _exe("ffprobe")


def ensure_engines() -> None:
    """Бросает понятную ошибку, если движки не найдены."""
    for p in (ffmpeg_path(), ffprobe_path()):
        if not p.exists():
            raise FileNotFoundError(
                f"Не найден {p.name}. Ожидается в папке: {p.parent}\n"
                "Скачайте FFmpeg (essentials build) и положите ffmpeg.exe и ffprobe.exe в bin\\."
            )
