"""Добавление/удаление пункта «Сжать видео» в контекстном меню Проводника (Windows).

Пишем в HKCU\\Software\\Classes\\SystemFileAssociations\\<.ext>\\shell\\CompressVideo.
Не требует прав администратора. Работает на классическом меню Windows 10
(на Windows 11 пункт будет в «Показать дополнительные параметры»).
"""

from __future__ import annotations

import sys
from pathlib import Path

VERB = "CompressVideo"
CAPTION = "Сжать видео"
EXTENSIONS = [
    ".mp4", ".mov", ".mkv", ".avi", ".webm",
    ".m4v", ".wmv", ".flv", ".mpg", ".mpeg", ".ts",
]


def _shell_key(ext: str) -> str:
    return rf"Software\Classes\SystemFileAssociations\{ext}\shell\{VERB}"


def current_app_command() -> str:
    """Команда запуска приложения с подстановкой пути к файлу (%1)."""
    if getattr(sys, "frozen", False):
        # Собранный exe — запускаем напрямую.
        return f'"{Path(sys.executable)}" "%1"'
    # Режим разработки — python -m vcompress <file>.
    main = Path(__file__).resolve().parents[2]  # корень репозитория
    return f'"{Path(sys.executable)}" "{main / "run.py"}" "%1"'


def is_installed() -> bool:
    import winreg
    try:
        winreg.OpenKey(winreg.HKEY_CURRENT_USER, _shell_key(EXTENSIONS[0])).Close()
        return True
    except FileNotFoundError:
        return False


def install(command: str | None = None, icon: str | None = None) -> None:
    """Создать пункты меню для всех видеорасширений."""
    import winreg

    command = command or current_app_command()
    if icon is None and getattr(sys, "frozen", False):
        icon = f"{Path(sys.executable)},0"

    for ext in EXTENSIONS:
        key_path = _shell_key(ext)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as k:
            # И (Default), и MUIVerb — для надёжного отображения подписи.
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, CAPTION)
            winreg.SetValueEx(k, "MUIVerb", 0, winreg.REG_SZ, CAPTION)
            if icon:
                winreg.SetValueEx(k, "Icon", 0, winreg.REG_SZ, icon)
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path + r"\command") as k:
            winreg.SetValueEx(k, None, 0, winreg.REG_SZ, command)

    _notify_shell()


def uninstall() -> None:
    """Удалить пункты меню для всех видеорасширений."""
    import winreg

    for ext in EXTENSIONS:
        key_path = _shell_key(ext)
        for sub in (key_path + r"\command", key_path):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, sub)
            except FileNotFoundError:
                pass
    _notify_shell()


def _notify_shell() -> None:
    """Сообщить Проводнику об изменении ассоциаций, чтобы меню обновилось сразу."""
    try:
        import ctypes
        SHCNE_ASSOCCHANGED = 0x08000000
        SHCNF_IDLIST = 0x0000
        ctypes.windll.shell32.SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, None, None)
    except Exception:
        pass


def restart_explorer() -> None:
    """Перезапустить Проводник, чтобы новый пункт меню точно появился.

    Иногда новые статические команды в контекстном меню кэшируются и
    подхватываются только после перезапуска explorer.exe.
    """
    import subprocess
    no_window = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
    try:
        subprocess.run(["taskkill", "/f", "/im", "explorer.exe"],
                       creationflags=no_window, capture_output=True)
    except Exception:
        pass
    # Windows обычно сам перезапускает Explorer, но подстрахуемся.
    try:
        subprocess.Popen(["explorer.exe"], creationflags=no_window)
    except Exception:
        pass
