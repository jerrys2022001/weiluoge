from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ColorClip, CompositeVideoClip, ImageClip, concatenate_videoclips


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "assets" / "videos"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = OUT_DIR / "bluetooth-explorer-ad-15s-9x16.mp4"

W, H = 720, 1280
SEG_DUR = 3.0
TOTAL_DUR = 15.0


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates: Iterable[str]
    if bold:
        candidates = (
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
        )
    else:
        candidates = (
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/verdana.ttf",
        )
    for c in candidates:
        p = Path(c)
        if p.exists():
            return ImageFont.truetype(str(p), size=size)
    return ImageFont.load_default()


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    buf: list[str] = []
    for word in words:
        candidate = " ".join(buf + [word])
        bbox = draw.textbbox((0, 0), candidate, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width or not buf:
            buf.append(word)
        else:
            lines.append(" ".join(buf))
            buf = [word]
    if buf:
        lines.append(" ".join(buf))
    return lines


def make_caption_card(title: str, body: str, width: int = W - 72) -> np.ndarray:
    pad_x = 28
    pad_y = 22
    title_font = load_font(46, bold=True)
    body_font = load_font(31, bold=False)

    temp = Image.new("RGBA", (width, 500), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp)

    title_lines = wrap_text(draw, title, title_font, width - pad_x * 2)
    body_lines = wrap_text(draw, body, body_font, width - pad_x * 2)

    y = pad_y
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 6
    y += 8
    for line in body_lines:
        bbox = draw.textbbox((0, 0), line, font=body_font)
        y += (bbox[3] - bbox[1]) + 4

    height = y + pad_y
    card = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rounded_rectangle(
        (0, 0, width - 1, height - 1),
        radius=26,
        fill=(8, 14, 30, 190),
        outline=(100, 170, 255, 140),
        width=2,
    )

    y = pad_y
    for line in title_lines:
        draw.text((pad_x, y), line, font=title_font, fill=(236, 245, 255, 255))
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 6
    y += 8
    for line in body_lines:
        draw.text((pad_x, y), line, font=body_font, fill=(181, 204, 240, 255))
        bbox = draw.textbbox((0, 0), line, font=body_font)
        y += (bbox[3] - bbox[1]) + 4

    return np.array(card)


def make_badge(text: str) -> np.ndarray:
    font = load_font(28, bold=True)
    pad_x = 20
    pad_y = 10
    temp = Image.new("RGBA", (800, 120), (0, 0, 0, 0))
    draw = ImageDraw.Draw(temp)
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w = tw + pad_x * 2
    h = th + pad_y * 2

    badge = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(badge)
    draw.rounded_rectangle(
        (0, 0, w - 1, h - 1),
        radius=18,
        fill=(4, 12, 26, 210),
        outline=(91, 166, 255, 170),
        width=2,
    )
    draw.text((pad_x, pad_y - 1), text, font=font, fill=(217, 235, 255, 255))
    return np.array(badge)


def make_bg(path: Path, duration: float, z0: float = 1.02, z1: float = 1.1) -> CompositeVideoClip:
    base = ImageClip(str(path))
    scale = max(W / base.w, H / base.h)
    bg = base.resized(lambda t: scale * (z0 + (z1 - z0) * (t / duration)))
    bg = bg.with_duration(duration).with_position(("center", "center"))

    tint = ColorClip((W, H), color=(8, 12, 22), duration=duration).with_opacity(0.25)
    return CompositeVideoClip([bg, tint], size=(W, H)).with_duration(duration)


def build_segment(
    image_path: Path,
    title: str,
    body: str,
    icon_path: Path,
    duration: float = SEG_DUR,
    is_end: bool = False,
) -> CompositeVideoClip:
    bg = make_bg(image_path, duration)
    caption = ImageClip(make_caption_card(title, body)).with_duration(duration).with_position(("center", H - 420))
    badge = ImageClip(make_badge("Bluetooth Explorer")).with_duration(duration).with_position((34, 34))
    icon = (
        ImageClip(str(icon_path))
        .resized(height=92)
        .with_duration(duration)
        .with_position((W - 126, 34))
        .with_opacity(0.95)
    )

    layers = [bg, caption, badge, icon]

    if is_end:
        cta = ImageClip(make_badge("Scan smarter. Debug faster.")).with_duration(duration).with_position(("center", H - 120))
        layers.append(cta)

    return CompositeVideoClip(layers, size=(W, H)).with_duration(duration)


def main() -> None:
    icon = ROOT / "bluetoothexplorer" / "icon-bluetooth.png"
    segments = [
        (
            ROOT / "assets" / "images" / "stock-2026-03-extra20" / "stock-extra-02.jpg",
            "Bluetooth panic again?",
            "Everything nearby appears first. Your target device? Missing in action.",
            False,
        ),
        (
            ROOT / "bluetoothexplorer" / "guid" / "3.jpg",
            "Open Bluetooth Explorer",
            "Scan nearby devices instantly and stop guessing what is actually broadcasting.",
            False,
        ),
        (
            ROOT / "bluetoothexplorer" / "guid" / "5.jpg",
            "Inspect real structure",
            "Drill into GATT services and characteristic values in a clean, readable flow.",
            False,
        ),
        (
            ROOT / "bluetoothexplorer" / "guid" / "8.jpg",
            "Debug, but stay calm",
            "Run packet tests, watch logs, and fix flaky connections before they waste your day.",
            False,
        ),
        (
            ROOT / "bluetoothexplorer" / "og-cover.jpg",
            "Connection fixed. Mood restored.",
            "You look like a Bluetooth wizard now. That is the whole point.",
            True,
        ),
    ]

    for p, _, _, _ in segments:
        if not p.exists():
            raise FileNotFoundError(f"Missing source image: {p}")
    if not icon.exists():
        raise FileNotFoundError(f"Missing icon image: {icon}")

    clips = [build_segment(path, title, body, icon, SEG_DUR, is_end=end) for path, title, body, end in segments]
    final = concatenate_videoclips(clips, method="compose")
    final = final.with_duration(TOTAL_DUR)

    final.write_videofile(
        str(OUT_FILE),
        fps=30,
        codec="libx264",
        audio=False,
        logger=None,
        threads=4,
    )
    final.close()
    print(str(OUT_FILE))


if __name__ == "__main__":
    main()
