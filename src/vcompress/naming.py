"""Формирование имени выходного файла рядом с оригиналом, без перезаписи."""

from __future__ import annotations

from pathlib import Path

SUFFIX = "_small"


def unique_output_path(src: str | Path, ext: str = ".mp4") -> Path:
    """Вернуть путь вида `имя_small.mp4` рядом с оригиналом.

    Если такой файл уже есть — добавляет ` (1)`, ` (2)` и т.д.
    Не перезаписывает существующие файлы.
    """
    src = Path(src)
    stem = src.stem + SUFFIX
    parent = src.parent

    candidate = parent / f"{stem}{ext}"
    n = 1
    while candidate.exists():
        candidate = parent / f"{stem} ({n}){ext}"
        n += 1
    return candidate
