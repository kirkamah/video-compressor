# Video Compressor - a no harm org project
# Author: Kirkamah  |  (c) 2026 Kirkamah / no harm org - All rights reserved.
"""Точка входа. Запускается из окна или из контекстного меню (с путём к файлу)."""

from __future__ import annotations

import sys


def _selftest() -> None:
    """Диагностика: записать в %TEMP%\\vcompress_selftest.txt пути к движкам.

    Нужно для проверки собранного (оконного) exe, у которого нет консоли.
    """
    import os
    import tempfile
    from . import paths
    ff, fp = paths.ffmpeg_path(), paths.ffprobe_path()
    report = (
        f"frozen={getattr(sys, 'frozen', False)}\n"
        f"base_dir={paths.base_dir()}\n"
        f"ffmpeg={ff} exists={ff.exists()}\n"
        f"ffprobe={fp} exists={fp.exists()}\n"
    )
    out = os.path.join(tempfile.gettempdir(), "vcompress_selftest.txt")
    with open(out, "w", encoding="utf-8") as f:
        f.write(report)


def main() -> None:
    args = sys.argv[1:]
    if "--selftest" in args:
        _selftest()
        return
    if "--install-menu" in args:
        from . import context_menu
        context_menu.install()
        if "--refresh" in args:
            context_menu.restart_explorer()
        return
    if "--uninstall-menu" in args:
        from . import context_menu
        context_menu.uninstall()
        return
    initial_file = None
    for arg in args:
        if not arg.startswith("-"):
            initial_file = arg
            break
    from .gui.app import run
    run(initial_file)


if __name__ == "__main__":
    main()
