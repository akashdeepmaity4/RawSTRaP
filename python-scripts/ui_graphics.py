"""Supersampled Pillow artwork for smooth Tkinter screens."""

# I made this to render the UI without aliasing.

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageTk


SCALE = 4
GOLD = "#e3a004"
HOVER_GOLD = "#f6b500"
INK = "#111111"
PANEL = "#b0b0b0"
BACKGROUND = "#121212"


def _font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    """Load a Windows UI font, falling back cleanly if it is unavailable."""
    fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
    names = {
        "display": ("segoeprb.ttf", "segoepr.ttf", "segoeui.ttf"),
        "body": ("georgia.ttf", "segoeui.ttf"),
        "button": ("segoeui.ttf", "arial.ttf"),
    }
    for filename in names.get(name, ("segoeui.ttf",)):
        font_path = fonts_dir / filename
        if font_path.is_file():
            try:
                return ImageFont.truetype(str(font_path), size * SCALE)
            except OSError:
                continue
    return ImageFont.load_default(size=size * SCALE)


def render_artwork(
    width: int,
    height: int,
    *,
    title: str,
    subtitle: str = "",
    buttons: tuple[dict[str, Any], ...] = (),
    title_y: int | None = None,
    subtitle_y: int | None = None,
    title_size: int = 39,
    title_font: str = "display",
    footer: str = "",
) -> Image.Image:
    '''
    
    Render screen artwork above target resolution and downsample smoothly.
    

    '''
    image = Image.new("RGB", (width * SCALE, height * SCALE), BACKGROUND)
    draw = ImageDraw.Draw(image)

    def px(value: int) -> int:
        return value * SCALE

    draw.rounded_rectangle(
        (px(round(width * 0.086)), px(17), px(round(width * 0.935)), px(height - 7)),
        radius=px(39), fill=PANEL, outline="#151515", width=px(5),
    )
    draw.rounded_rectangle(
        (px(round(width * 0.111)), px(33), px(round(width * 0.91)), px(height - 23)),
        radius=px(35), fill=INK, outline="#252525", width=px(2),
    )

    title_position = title_y if title_y is not None else int(height * 0.21)
    subtitle_position = subtitle_y if subtitle_y is not None else int(height * 0.34)
    draw.text(
        (px(width // 2), px(title_position)), title,
        font=_font(title_font, title_size), fill=GOLD, anchor="mm",
        stroke_width=0,
    )
    if subtitle:
        draw.text(
            (px(width // 2), px(subtitle_position)), subtitle,
            font=_font("body", 12), fill=GOLD, anchor="mm",
        )

    for button in buttons:
        x1, y1, x2, y2 = button["bounds"]
        box = (px(x1), px(y1), px(x2), px(y2))
        draw.rounded_rectangle(box, radius=px(15), fill=button.get("fill", GOLD))
        label = button.get("label", "")
        if label:
            draw.text(
                (px(button.get("label_x", (x1 + x2) // 2)), px((y1 + y2) // 2)),
                label,
                font=_font("button", button.get("font_size", 15)),
                fill=INK,
                anchor="mm",
            )
        icon = button.get("icon")
        if icon == "chat":
            draw.rounded_rectangle(
                (px(x2 - 46), px((y1 + y2) // 2 - 12), px(x2 - 22), px((y1 + y2) // 2 + 9)),
                radius=px(9), outline=INK, width=px(2),
            )
            cy = (y1 + y2) // 2
            draw.line(
                [(px(x2 - 40), px(cy + 7)), (px(x2 - 44), px(cy + 14)), (px(x2 - 34), px(cy + 9))],
                fill=INK, width=px(2),
            )
            for dx in (39, 33, 27):
                draw.ellipse((px(x2 - dx), px(cy - 2), px(x2 - dx + 2), px(cy)), fill=INK)
        elif icon == "file":
            left, top = x2 - 43, (y1 + y2) // 2 - 14
            right, bottom = x2 - 24, (y1 + y2) // 2 + 14
            draw.rectangle((px(left), px(top), px(right), px(bottom)), outline=INK, width=px(2))
            draw.line(
                [(px(right - 6), px(top)), (px(right - 6), px(top + 6)), (px(right), px(top + 6))],
                fill=INK, width=px(2),
            )
            for row in (top + 11, top + 16, top + 21):
                draw.line((px(left + 4), px(row), px(right - 4), px(row)), fill=INK, width=px(1))

    if footer:
        draw.text(
            (px(width // 2), px(height - 44)), footer,
            font=_font("body", 10), fill=GOLD, anchor="mm",
        )

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    return image


def render_screen(
    width: int,
    height: int,
    **options: Any,
) -> ImageTk.PhotoImage:
    return ImageTk.PhotoImage(render_artwork(width, height, **options))
