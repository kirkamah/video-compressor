"""Сборка и запуск команд ffmpeg для сжатия видео с обратной связью по прогрессу."""

from __future__ import annotations

import os
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .paths import ffmpeg_path
from .progress import ProgressParser

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

ProgressCallback = Callable[[float], None]


@dataclass
class EncodeSettings:
    """Параметры одного задания на сжатие."""
    src: Path
    dst: Path
    duration_s: float
    mode: str                       # "size" | "quality"
    # режим size:
    video_kbps: int = 0
    # режим quality:
    crf: int = 23
    # общее:
    audio_kbps: int = 128
    height_cap: int | None = None   # максимальная высота (None = без изменения)
    preset: str = "medium"          # пресет скорости x264


class CancelledError(Exception):
    """Кодирование отменено пользователем."""


class Encoder:
    """Запускает ffmpeg, отдаёт прогресс через колбэк, поддерживает отмену."""

    def __init__(self, settings: EncodeSettings):
        self.s = settings
        self._proc: subprocess.Popen | None = None
        self._cancel = threading.Event()

    # -- публичный API -------------------------------------------------------

    def cancel(self) -> None:
        self._cancel.set()
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self, on_progress: ProgressCallback | None = None) -> Path:
        """Выполнить кодирование. Вернуть путь к готовому файлу.

        Бросает CancelledError при отмене и RuntimeError при ошибке ffmpeg.
        """
        try:
            if self.s.mode == "size":
                self._run_two_pass(on_progress)
            elif self.s.mode == "quality":
                self._run_single_pass(on_progress)
            else:
                raise ValueError(f"Неизвестный режим: {self.s.mode}")
        except CancelledError:
            self._cleanup_partial()
            raise
        return self.s.dst

    # -- внутреннее ----------------------------------------------------------

    def _scale_filter(self) -> list[str]:
        """-vf для понижения разрешения (только вниз, чётные размеры, сохранение пропорций)."""
        if not self.s.height_cap:
            return []
        return ["-vf", f"scale=-2:'min({self.s.height_cap},ih)'"]

    def _common_progress_args(self) -> list[str]:
        return ["-progress", "pipe:1", "-nostats"]

    def _run_single_pass(self, on_progress: ProgressCallback | None) -> None:
        cmd = [
            str(ffmpeg_path()), "-y", "-hide_banner", "-loglevel", "error",
            "-i", str(self.s.src),
            "-c:v", "libx264", "-crf", str(self.s.crf), "-preset", self.s.preset,
            *self._scale_filter(),
            "-c:a", "aac", "-b:a", f"{self.s.audio_kbps}k",
            "-movflags", "+faststart",
            *self._common_progress_args(),
            str(self.s.dst),
        ]
        self._spawn_and_track(cmd, on_progress, base=0.0, span=1.0)

    def _run_two_pass(self, on_progress: ProgressCallback | None) -> None:
        log_dir = Path(tempfile.mkdtemp(prefix="vcompress_"))
        log_prefix = str(log_dir / "passlog")
        null_out = "NUL" if os.name == "nt" else "/dev/null"
        try:
            # Pass 1 — без звука, вывод в никуда.
            cmd1 = [
                str(ffmpeg_path()), "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(self.s.src),
                "-c:v", "libx264", "-b:v", f"{self.s.video_kbps}k",
                "-pass", "1", "-passlogfile", log_prefix,
                "-preset", self.s.preset, "-an",
                *self._scale_filter(),
                "-f", "mp4",
                *self._common_progress_args(),
                null_out,
            ]
            self._spawn_and_track(cmd1, on_progress, base=0.0, span=0.5)

            if self._cancel.is_set():
                raise CancelledError()

            # Pass 2 — со звуком, реальный вывод.
            cmd2 = [
                str(ffmpeg_path()), "-y", "-hide_banner", "-loglevel", "error",
                "-i", str(self.s.src),
                "-c:v", "libx264", "-b:v", f"{self.s.video_kbps}k",
                "-pass", "2", "-passlogfile", log_prefix,
                "-preset", self.s.preset,
                *self._scale_filter(),
                "-c:a", "aac", "-b:a", f"{self.s.audio_kbps}k",
                "-movflags", "+faststart",
                *self._common_progress_args(),
                str(self.s.dst),
            ]
            self._spawn_and_track(cmd2, on_progress, base=0.5, span=0.5)
        finally:
            self._rmtree(log_dir)

    def _spawn_and_track(
        self, cmd: list[str], on_progress: ProgressCallback | None,
        base: float, span: float,
    ) -> None:
        """Запустить ffmpeg, читать прогресс из stdout, ошибки — из stderr."""
        parser = ProgressParser(self.s.duration_s)
        self._proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            creationflags=_NO_WINDOW,
        )
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            if self._cancel.is_set():
                self._proc.terminate()
                raise CancelledError()
            frac = parser.feed(line)
            if on_progress:
                on_progress(base + frac * span)

        stderr = self._proc.stderr.read() if self._proc.stderr else ""
        code = self._proc.wait()
        if self._cancel.is_set():
            raise CancelledError()
        if code != 0:
            raise RuntimeError(f"ffmpeg завершился с ошибкой:\n{stderr.strip()}")
        if on_progress:
            on_progress(base + span)

    def _cleanup_partial(self) -> None:
        try:
            if self.s.dst.exists():
                self.s.dst.unlink()
        except OSError:
            pass

    @staticmethod
    def _rmtree(path: Path) -> None:
        import shutil
        try:
            shutil.rmtree(path, ignore_errors=True)
        except Exception:
            pass


def quick_sample_estimate_mb(
    src: Path, crf: int, duration_s: float, audio_kbps: int,
    height_cap: int | None = None, sample_s: int = 8,
) -> float:
    """Точнее оценить размер CRF-режима: кодируем короткий фрагмент и экстраполируем.

    Берём фрагмент с 25% длительности (мимо заставок), без звука, и масштабируем
    по длительности. Возвращает оценку в МиБ (видео+звук).
    """
    offset = max(0.0, duration_s * 0.25)
    sample_s = min(sample_s, max(2, int(duration_s)))
    tmp = Path(tempfile.gettempdir()) / f"vcompress_sample_{os.getpid()}.mp4"
    scale = ["-vf", f"scale=-2:'min({height_cap},ih)'"] if height_cap else []
    cmd = [
        str(ffmpeg_path()), "-y", "-hide_banner", "-loglevel", "error",
        "-ss", f"{offset:.2f}", "-i", str(src), "-t", str(sample_s),
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-an",
        *scale, "-f", "mp4", str(tmp),
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, creationflags=_NO_WINDOW)
        if r.returncode != 0 or not tmp.exists():
            raise RuntimeError(r.stderr.strip() or "sample encode failed")
        sample_bytes = tmp.stat().st_size
        video_bytes = sample_bytes * (duration_s / sample_s)
        audio_bytes = audio_kbps * 1000 / 8 * duration_s
        from . import presets
        return (video_bytes + audio_bytes) / presets.MIB
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
