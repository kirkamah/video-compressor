"""Пресеты размеров, отображение ползунка качества в CRF, варианты разрешения."""

from __future__ import annotations

from dataclasses import dataclass

MIB = 1024 * 1024


@dataclass(frozen=True)
class SizePreset:
    label: str
    size_mb: float  # целевой максимум в МиБ


# Популярные лимиты для шаринга. Custom — пользователь вводит сам.
SIZE_PRESETS: list[SizePreset] = [
    SizePreset("Discord — 10 МБ", 10),
    SizePreset("Discord Nitro — 25 МБ", 25),
    SizePreset("Email — 20 МБ", 20),
    SizePreset("WhatsApp — 16 МБ", 16),
    SizePreset("Telegram — 2 ГБ", 2048),
]

# Варианты понижения разрешения: подпись -> максимальная высота (None = как в оригинале).
RESOLUTION_CAPS: dict[str, int | None] = {
    "Как в оригинале": None,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
    "360p": 360,
}

# Диапазон CRF для libx264: 18 (почти без потерь) .. 30 (сильно сжато).
CRF_MIN = 18
CRF_MAX = 30


def slider_to_crf(percent: float) -> int:
    """Ползунок 0..100 (0 = макс. качество) -> CRF CRF_MIN..CRF_MAX."""
    percent = max(0.0, min(100.0, percent))
    return round(CRF_MIN + (percent / 100.0) * (CRF_MAX - CRF_MIN))


def quality_label(percent: float) -> str:
    """Человекочитаемая подпись для положения ползунка."""
    if percent <= 20:
        return "Высокое качество"
    if percent <= 45:
        return "Хорошее"
    if percent <= 70:
        return "Среднее"
    if percent <= 88:
        return "Сильное сжатие"
    return "Максимальное сжатие"
