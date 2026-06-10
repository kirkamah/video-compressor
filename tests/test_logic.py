"""Юнит-тесты чистой логики (без ffmpeg)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcompress import naming, presets, sizing  # noqa: E402
from vcompress.progress import ProgressParser  # noqa: E402


def test_slider_to_crf_endpoints():
    assert presets.slider_to_crf(0) == presets.CRF_MIN
    assert presets.slider_to_crf(100) == presets.CRF_MAX
    assert presets.CRF_MIN < presets.slider_to_crf(50) < presets.CRF_MAX


def test_target_plan_basic():
    # 10 минут, целимся в 25 МБ.
    plan = sizing.target_plan(25, duration_s=600, preferred_audio_kbps=128)
    assert plan.feasible
    assert plan.video_kbps > sizing.MIN_VIDEO_KBPS
    # Размер по плану не превышает целевой.
    got = sizing.predicted_size_mb(plan.video_kbps, plan.audio_kbps, 600)
    assert got <= 25 + 0.5


def test_target_plan_reduces_audio_then_gives_up():
    # 2 часа в 8 МБ — нереально, должно вернуть feasible=False с минимальным видео.
    plan = sizing.target_plan(8, duration_s=7200, preferred_audio_kbps=128)
    assert not plan.feasible
    assert plan.video_kbps == sizing.MIN_VIDEO_KBPS


def test_estimate_crf_size_monotonic():
    big = sizing.estimate_crf_size_mb(18, 5000, 120)
    small = sizing.estimate_crf_size_mb(30, 5000, 120)
    assert big > small


def test_unique_output_path(tmp_path):
    src = tmp_path / "video.mp4"
    src.write_bytes(b"x")
    out1 = naming.unique_output_path(src)
    assert out1.name == "video_small.mp4"
    out1.write_bytes(b"x")
    out2 = naming.unique_output_path(src)
    assert out2.name == "video_small (1).mp4"


def test_progress_parser():
    p = ProgressParser(total_duration_s=10)
    assert p.feed("out_time_us=5000000") == 0.5
    p.feed("progress=end")
    assert p.fraction == 1.0 and p.done
