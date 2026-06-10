# Video Compressor - a no harm org project
# Author: Kirkamah  |  (c) 2026 Kirkamah / no harm org - All rights reserved.
"""Запуск приложения в режиме разработки: py run.py [путь_к_видео]."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from vcompress.__main__ import main  # noqa: E402

if __name__ == "__main__":
    main()
