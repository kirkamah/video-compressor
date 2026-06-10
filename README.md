<p align="center">
  <img src="brand/logo.svg" alt="no harm org" width="96" height="96">
</p>

<h1 align="center">Video Compressor</h1>

<p align="center">
  <b>a no harm org project</b> · by <b>Kirkamah</b> ☮<br>
  <sub>© 2026 Kirkamah · no harm org — All rights reserved.</sub>
</p>

---

Простое приложение для Windows: уменьшает размер видеофайлов, чтобы их было легче
пересылать через мессенджеры и файлообменники. Движок — FFmpeg.

## Возможности
- **По размеру** — указываешь целевой максимум (или пресет Discord/Telegram/…), приложение
  подбирает битрейт и кодирует в два прохода, чтобы уложиться.
- **По качеству** — ползунок «лучше ↔ меньше», рядом показывается примерный итоговый размер.
- Понижение разрешения (1080p/720p/480p/360p) как дополнительный рычаг.
- Готовый файл `имя_small.mp4` рядом с оригиналом, оригинал не трогается.
- Пункт **«Сжать видео»** в контекстном меню Проводника (правый клик по видео).

## Запуск (разработка)
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
# Положить ffmpeg.exe и ffprobe.exe в .\bin\
py run.py            # окно
py run.py "C:\путь\видео.mp4"   # сразу с файлом
```

## Контекстное меню
В окне есть кнопка «Добавить «Сжать видео» в меню правого клика» (пишет в HKCU, без админ-прав).
Либо вручную:
```powershell
py scripts\install_context_menu.py --install
py scripts\install_context_menu.py --uninstall
```
На Windows 11 пункт появляется в «Показать дополнительные параметры».

## Сборка приложения и установщика

1. Иконка (если меняешь дизайн): `py scripts\make_icon.py` → `assets\app.ico`.
2. Сборка exe (onedir, со встроенным ffmpeg и иконкой):
   ```powershell
   py -m PyInstaller --noconfirm --clean build.spec
   # Результат: dist\VideoCompressor\VideoCompressor.exe
   ```
3. Установщик (нужен Inno Setup 6):
   ```powershell
   & "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer.iss
   # Результат: installer\VideoCompressor-Setup.exe (~65 МБ, один файл для раздачи)
   ```

## Распространение
Отправляй людям один файл — **`installer\VideoCompressor-Setup.exe`**. Установщик:
- ставится **без прав администратора** в профиль пользователя (`%LOCALAPPDATA%\Programs\VideoCompressor`);
- создаёт ярлык в меню «Пуск» (и на рабочем столе — по галочке);
- по галочке добавляет пункт **«Сжать видео»** в контекстное меню Проводника и обновляет Проводник;
- корректно удаляется через «Установка и удаление программ».

> **SmartScreen:** приложение не подписано цифровым сертификатом, поэтому при первом запуске
> Windows может показать синее окно «Защита Windows». Это нормально для нового неподписанного ПО —
> нажми «Подробнее» → «Выполнить в любом случае». Чтобы убрать предупреждение совсем, нужен платный
> сертификат подписи кода (code signing).

## Контекстное меню без установщика (портативный режим)
Запусти `VideoCompressor.exe` и нажми кнопку «Добавить "Сжать видео" в меню правого клика»
(прав администратора не нужно). Приложение предложит перезапустить Проводник, чтобы пункт
появился сразу. В этом режиме **не перемещай папку приложения** после добавления пункта
(иначе путь в меню сломается — просто нажми кнопку ещё раз).

## Тесты
```powershell
py -m pytest
```

## Структура
- `src/vcompress/` — код: `ffprobe`, `sizing`, `encoder`, `naming`, `presets`, `progress`,
  `context_menu`, `paths`, `gui/app.py`.
- `bin/` — `ffmpeg.exe`, `ffprobe.exe` (скачать отдельно).
- `build.spec` — конфигурация PyInstaller.

---

<p align="center">
  ☮ <b>no harm org</b> · made by <b>Kirkamah</b><br>
  <sub>© 2026 Kirkamah · no harm org — All rights reserved. See <a href="LICENSE">LICENSE</a>.</sub>
</p>
