"""Получение сведений о видео через ffprobe."""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .paths import ffprobe_path

# Не показывать окно консоли при запуске из GUI на Windows.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


@dataclass
class MediaInfo:
    path: Path
    duration_s: float
    size_bytes: int
    width: int
    height: int
    video_codec: str
    audio_codec: str | None
    video_kbps: float
    audio_kbps: int

    @property
    def has_audio(self) -> bool:
        return self.audio_codec is not None


def _to_float(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def probe(path: str | Path) -> MediaInfo:
    """Считать длительность, размер, разрешение и битрейты файла."""
    path = Path(path)
    cmd = [
        str(ffprobe_path()),
        "-v", "error",
        "-hide_banner",
        "-show_entries", "format=duration,size,bit_rate",
        "-show_entries", "stream=index,codec_type,codec_name,width,height,bit_rate,duration,nb_frames,avg_frame_rate",
        "-of", "json",
        str(path),
    ]
    out = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=_NO_WINDOW
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe не смог прочитать файл:\n{out.stderr.strip()}")

    data = json.loads(out.stdout)
    fmt = data.get("format", {})
    streams = data.get("streams", [])

    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if video is None:
        raise RuntimeError("В файле не найдена видеодорожка.")

    # Длительность: из format, иначе из видеопотока, иначе из кадров/fps.
    duration = _to_float(fmt.get("duration"))
    if duration <= 0:
        duration = _to_float(video.get("duration"))
    if duration <= 0:
        nb = _to_float(video.get("nb_frames"))
        fr = video.get("avg_frame_rate", "0/0")
        try:
            num, den = (float(x) for x in fr.split("/"))
            fps = num / den if den else 0
        except (ValueError, ZeroDivisionError):
            fps = 0
        if nb > 0 and fps > 0:
            duration = nb / fps
    if duration <= 0:
        raise RuntimeError("Не удалось определить длительность видео.")

    size_bytes = int(_to_float(fmt.get("size"))) or (path.stat().st_size if path.exists() else 0)

    # Аудио битрейт.
    audio_kbps = 0
    audio_codec = None
    if audio is not None:
        audio_codec = audio.get("codec_name")
        audio_kbps = int(_to_float(audio.get("bit_rate")) / 1000) or 128

    # Видео битрейт: из потока, иначе (общий - аудио), иначе из размера.
    video_kbps = _to_float(video.get("bit_rate")) / 1000
    if video_kbps <= 0:
        total_kbps = _to_float(fmt.get("bit_rate")) / 1000
        if total_kbps <= 0 and size_bytes > 0:
            total_kbps = size_bytes * 8 / duration / 1000
        video_kbps = max(0.0, total_kbps - audio_kbps)

    return MediaInfo(
        path=path,
        duration_s=duration,
        size_bytes=size_bytes,
        width=int(video.get("width") or 0),
        height=int(video.get("height") or 0),
        video_codec=video.get("codec_name", "?"),
        audio_codec=audio_codec,
        video_kbps=video_kbps,
        audio_kbps=audio_kbps or 128,
    )
