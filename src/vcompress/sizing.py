"""Расчёт битрейта под целевой размер и грубая оценка размера для режима CRF.

Все функции чистые (без I/O) — удобно тестировать.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import presets

# Запас на накладные расходы контейнера и неточность rate-control.
# Намеренно консервативный, чтобы результат гарантированно укладывался под лимит.
SAFETY = 0.92
# Ниже этого видеобитрейт (kbps) считаем нереалистичным для нормальной картинки.
MIN_VIDEO_KBPS = 120
# Возможные значения аудио при автоподборе (kbps), от лучшего к худшему.
AUDIO_LADDER = [128, 96, 64, 48]


@dataclass(frozen=True)
class TargetPlan:
    video_kbps: int
    audio_kbps: int
    feasible: bool          # удалось ли уложиться без ухудшения сверх запрошенного
    note: str = ""          # пояснение для пользователя (например, про авто-снижение)


def target_plan(
    target_size_mb: float,
    duration_s: float,
    preferred_audio_kbps: int = 128,
    safety: float = SAFETY,
) -> TargetPlan:
    """Подобрать видео/аудио битрейт, чтобы файл уложился в target_size_mb (МиБ).

    Если при выбранном аудио видеобитрейт получается слишком низким, пробуем
    последовательно снижать аудио. Если и это не помогает — возвращаем минимально
    допустимый видеобитрейт с feasible=False (вызывающий код может предложить
    понижение разрешения).
    """
    if duration_s <= 0:
        raise ValueError("Длительность должна быть положительной")

    target_bits = target_size_mb * presets.MIB * 8 * safety
    total_kbps = target_bits / duration_s / 1000.0

    ladder = [a for a in AUDIO_LADDER if a <= preferred_audio_kbps] or [AUDIO_LADDER[-1]]
    if preferred_audio_kbps not in ladder:
        ladder = [preferred_audio_kbps] + ladder

    for audio_kbps in ladder:
        video_kbps = total_kbps - audio_kbps
        if video_kbps >= MIN_VIDEO_KBPS:
            note = ""
            if audio_kbps < preferred_audio_kbps:
                note = f"Звук снижен до {audio_kbps} кбит/с, чтобы уложиться в размер."
            return TargetPlan(round(video_kbps), audio_kbps, True, note)

    # Не уложиться даже с самым низким аудио — отдаём минимум и просим понизить разрешение.
    audio_kbps = ladder[-1]
    return TargetPlan(
        MIN_VIDEO_KBPS,
        audio_kbps,
        False,
        "Целевой размер очень мал для такой длительности — "
        "рекомендуется понизить разрешение (720p/480p).",
    )


def predicted_size_mb(video_kbps: int, audio_kbps: int, duration_s: float) -> float:
    """Размер (МиБ) при заданных битрейтах — для отображения «получится ~N МБ»."""
    bits = (video_kbps + audio_kbps) * 1000.0 * duration_s
    return bits / 8 / presets.MIB


# --- Режим качества (CRF): размер контентозависим, считаем эвристикой -------

# Доля от исходного видеобитрейта при разных CRF (грубая эвристика для libx264).
_CRF_RATIO = {
    18: 0.90,
    20: 0.72,
    22: 0.58,
    23: 0.50,
    24: 0.44,
    26: 0.34,
    28: 0.26,
    30: 0.20,
}


def _crf_ratio(crf: int) -> float:
    if crf in _CRF_RATIO:
        return _CRF_RATIO[crf]
    keys = sorted(_CRF_RATIO)
    crf = max(keys[0], min(keys[-1], crf))
    lo = max(k for k in keys if k <= crf)
    hi = min(k for k in keys if k >= crf)
    if lo == hi:
        return _CRF_RATIO[lo]
    t = (crf - lo) / (hi - lo)
    return _CRF_RATIO[lo] + t * (_CRF_RATIO[hi] - _CRF_RATIO[lo])


def estimate_crf_size_mb(
    crf: int,
    source_video_kbps: float,
    duration_s: float,
    audio_kbps: int = 128,
    scale_factor: float = 1.0,
) -> float:
    """Грубая оценка размера (МиБ) для режима CRF.

    scale_factor — отношение площади кадра после понижения разрешения к исходной
    (например, 720p из 1080p ≈ (1280*720)/(1920*1080) ≈ 0.44). Меньше площадь — меньше файл.
    """
    est_video_kbps = max(MIN_VIDEO_KBPS * 0.5, source_video_kbps * _crf_ratio(crf) * scale_factor)
    bits = (est_video_kbps + audio_kbps) * 1000.0 * duration_s
    return bits / 8 / presets.MIB
