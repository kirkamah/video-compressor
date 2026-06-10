"""CLI для управления пунктом контекстного меню (dev-режим).

    py scripts\\install_context_menu.py --install
    py scripts\\install_context_menu.py --uninstall
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcompress import context_menu  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description="Пункт «Сжать видео» в контекстном меню")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--install", action="store_true")
    g.add_argument("--uninstall", action="store_true")
    g.add_argument("--status", action="store_true")
    args = ap.parse_args()

    if args.install:
        context_menu.install()
        print("Установлено для:", ", ".join(context_menu.EXTENSIONS))
    elif args.uninstall:
        context_menu.uninstall()
        print("Удалено.")
    else:
        print("Установлено" if context_menu.is_installed() else "Не установлено")


if __name__ == "__main__":
    main()
