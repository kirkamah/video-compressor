"""Генерация иконки приложения assets/app.ico (многоразмерный .ico).

Дизайн: скруглённый квадрат с сине-фиолетовым градиентом, белая «кинолента»
сверху и стрелка вниз (символ сжатия/уменьшения).
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "app.ico"
S = 1024  # рисуем крупно, потом уменьшаем


def lerp(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def rounded_mask(size: int, radius: int) -> Image.Image:
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=255)
    return m


def make_base() -> Image.Image:
    # Диагональный градиент.
    top = (79, 70, 229)     # индиго
    bot = (124, 58, 237)    # фиолетовый
    grad = Image.new("RGB", (S, S))
    px = grad.load()
    for y in range(S):
        for x in range(0, S, 4):
            t = (x + y) / (2 * S)
            c = lerp(top, bot, t)
            for dx in range(4):
                if x + dx < S:
                    px[x + dx, y] = c

    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    img.paste(grad, (0, 0), rounded_mask(S, radius=int(S * 0.22)))
    return img


def draw_film_and_arrow(img: Image.Image) -> None:
    d = ImageDraw.Draw(img)
    white = (255, 255, 255, 255)

    # Киноплёнка-полоса сверху по центру: прямоугольник с перфорацией.
    strip_w, strip_h = int(S * 0.56), int(S * 0.20)
    sx = (S - strip_w) // 2
    sy = int(S * 0.20)
    r = int(strip_h * 0.18)
    d.rounded_rectangle([sx, sy, sx + strip_w, sy + strip_h], radius=r, fill=white)
    # перфорация (дырочки) — вырезаем градиентным фоном иллюзорно: рисуем точками цвета фона
    hole = int(strip_h * 0.16)
    gap = strip_w / 6
    hy1 = sy + int(strip_h * 0.16)
    hy2 = sy + strip_h - int(strip_h * 0.16) - hole
    for i in range(6):
        hx = sx + int(gap * i + gap * 0.5 - hole / 2)
        d.rectangle([hx, hy1, hx + hole, hy1 + hole], fill=(99, 64, 233, 255))
        d.rectangle([hx, hy2, hx + hole, hy2 + hole], fill=(99, 64, 233, 255))

    # Большая стрелка вниз — символ «уменьшить/сжать».
    cx = S // 2
    shaft_w = int(S * 0.16)
    top_y = int(S * 0.46)
    head_y = int(S * 0.66)
    bot_y = int(S * 0.80)
    head_w = int(S * 0.30)
    # стержень
    d.rounded_rectangle(
        [cx - shaft_w // 2, top_y, cx + shaft_w // 2, head_y],
        radius=int(shaft_w * 0.25), fill=white,
    )
    # наконечник (треугольник)
    d.polygon(
        [(cx - head_w // 2, head_y), (cx + head_w // 2, head_y), (cx, bot_y)],
        fill=white,
    )


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    img = make_base()
    draw_film_and_arrow(img)
    # Pillow сам сгенерирует все размеры из одного изображения 256x256.
    base = img.resize((256, 256), Image.LANCZOS)
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    base.save(OUT, format="ICO", sizes=sizes)
    # Также сохраним PNG для предпросмотра/установщика.
    base.save(OUT.with_suffix(".png"))
    print("Saved:", OUT, "and", OUT.with_suffix(".png"))


if __name__ == "__main__":
    main()
