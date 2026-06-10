# Video Compressor - a no harm org project
# Author: Kirkamah  |  (c) 2026 Kirkamah / no harm org - All rights reserved.
"""Флаг пробной (trial) сборки.

В обычной сборке флаг выключен и поведение приложения не меняется.
Скрипт scripts/build_trial.py временно включает флаг на время сборки
и возвращает обратно (try/finally).
"""

TRIAL = False

# Ограничение пробной версии: максимальная длительность видео, секунд.
TRIAL_MAX_DURATION_S = 5 * 60

# Где купить полную версию.
BOOSTY_URL = "https://boosty.to/no.harm.org"

TRIAL_LIMIT_MESSAGE = (
    "В пробной версии можно сжимать видео до 5 минут.\n"
    "Полная версия — на Boosty: " + BOOSTY_URL
)
