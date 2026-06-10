"""Парсинг потока `-progress pipe:1` от ffmpeg в долю выполнения 0.0..1.0."""

from __future__ import annotations


class ProgressParser:
    """Состояние для построчного разбора вывода ffmpeg `-progress pipe:1`.

    ffmpeg печатает блоки строк key=value, заканчивающиеся `progress=continue`
    или `progress=end`. Нас интересует out_time_us / out_time_ms (микросекунды).
    """

    def __init__(self, total_duration_s: float):
        self.total = max(0.001, total_duration_s)
        self.fraction = 0.0
        self.done = False

    def feed(self, line: str) -> float:
        """Скормить одну строку. Вернуть текущую долю выполнения 0.0..1.0."""
        line = line.strip()
        if not line or "=" not in line:
            return self.fraction
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()

        if key in ("out_time_us", "out_time_ms"):
            try:
                us = float(value)  # обе единицы фактически в микросекундах
            except ValueError:
                return self.fraction
            self.fraction = max(0.0, min(1.0, us / 1_000_000.0 / self.total))
        elif key == "progress" and value == "end":
            self.done = True
            self.fraction = 1.0
        return self.fraction
