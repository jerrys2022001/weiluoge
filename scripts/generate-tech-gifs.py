from __future__ import annotations

import math
import random
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter


WIDTH = 512
HEIGHT = 288
FRAME_COUNT = 36
BACKGROUND = (6, 10, 20)


@dataclass
class GifSpec:
    name: str
    duration_ms: int
    frames: list[Image.Image]


def blank_frame() -> Image.Image:
    return Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)


def quantize_frames(frames: list[Image.Image], colors: int = 72) -> list[Image.Image]:
    return [f.convert("P", palette=Image.ADAPTIVE, colors=colors) for f in frames]


def save_gif(spec: GifSpec, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / spec.name
    q = quantize_frames(spec.frames)
    q[0].save(
        path,
        save_all=True,
        append_images=q[1:],
        duration=spec.duration_ms,
        loop=0,
        optimize=True,
        disposal=2,
    )


def make_holo_grid_scan() -> GifSpec:
    frames: list[Image.Image] = []
    spacing = 24
    for i in range(FRAME_COUNT):
        frame = blank_frame()
        draw = ImageDraw.Draw(frame)

        for x in range(0, WIDTH, spacing):
            draw.line((x, 0, x, HEIGHT), fill=(18, 42, 70), width=1)
        for y in range(0, HEIGHT, spacing):
            draw.line((0, y, WIDTH, y), fill=(16, 38, 64), width=1)

        scan_y = int((i / FRAME_COUNT) * HEIGHT)
        draw.rectangle((0, max(0, scan_y - 3), WIDTH, min(HEIGHT, scan_y + 3)), fill=(45, 210, 255))

        for cx in range(0, WIDTH, spacing * 2):
            r = 3 + ((i + cx // spacing) % 6)
            draw.ellipse((cx - r, scan_y - r, cx + r, scan_y + r), outline=(120, 240, 255), width=1)

        frames.append(frame.filter(ImageFilter.GaussianBlur(radius=0.2)))
    return GifSpec("tech-holo-grid-scan.gif", 60, frames)


def make_data_rain() -> GifSpec:
    rng = random.Random(20260305)
    streams = []
    for x in range(10, WIDTH, 22):
        streams.append(
            {
                "x": x,
                "y": rng.randint(-HEIGHT, HEIGHT),
                "speed": rng.randint(4, 10),
                "length": rng.randint(5, 14),
            }
        )

    frames: list[Image.Image] = []
    for _ in range(FRAME_COUNT):
        frame = blank_frame()
        draw = ImageDraw.Draw(frame)

        for s in streams:
            for k in range(s["length"]):
                y = s["y"] - k * 14
                if 0 <= y <= HEIGHT:
                    alpha = max(20, 255 - k * 22)
                    color = (40, min(255, 160 + k * 4), min(255, 220 + k * 2))
                    draw.text((s["x"], y), "1" if (k + s["y"]) % 3 else "0", fill=color)
                    if alpha < 255:
                        draw.point((s["x"] + 4, y + 6), fill=(15, 55, 85))
            s["y"] += s["speed"]
            if s["y"] - s["length"] * 14 > HEIGHT + 20:
                s["y"] = rng.randint(-160, -10)

        frame = frame.filter(ImageFilter.GaussianBlur(radius=0.4))
        frames.append(frame)
    return GifSpec("tech-data-rain.gif", 55, frames)


def make_orbital_network() -> GifSpec:
    center = (WIDTH // 2, HEIGHT // 2)
    nodes = [
        (center[0] + 130, center[1]),
        (center[0] - 130, center[1]),
        (center[0], center[1] + 90),
        (center[0], center[1] - 90),
        (center[0] + 95, center[1] + 68),
        (center[0] - 95, center[1] - 68),
    ]

    frames: list[Image.Image] = []
    for i in range(FRAME_COUNT):
        frame = blank_frame()
        draw = ImageDraw.Draw(frame)

        phase = (i / FRAME_COUNT) * math.tau
        r1 = 82 + int(8 * math.sin(phase * 2))
        r2 = 128 + int(10 * math.cos(phase * 1.4))
        draw.ellipse((center[0] - r1, center[1] - r1, center[0] + r1, center[1] + r1), outline=(32, 100, 180), width=2)
        draw.ellipse((center[0] - r2, center[1] - r2, center[0] + r2, center[1] + r2), outline=(22, 66, 130), width=2)

        for a in range(len(nodes)):
            for b in range(a + 1, len(nodes)):
                if (a + b) % 2 == 0:
                    draw.line((nodes[a], nodes[b]), fill=(18, 80, 145), width=1)

        for idx, (x, y) in enumerate(nodes):
            pulse = 4 + int(3 * (1 + math.sin(phase * 2.2 + idx)))
            draw.ellipse((x - pulse, y - pulse, x + pulse, y + pulse), fill=(70, 220, 255), outline=(180, 255, 255))

        sx = int(center[0] + math.cos(phase * 1.8) * r2)
        sy = int(center[1] + math.sin(phase * 1.8) * r2)
        draw.ellipse((sx - 5, sy - 5, sx + 5, sy + 5), fill=(255, 215, 120))

        frames.append(frame.filter(ImageFilter.GaussianBlur(radius=0.25)))
    return GifSpec("tech-orbital-network.gif", 65, frames)


def make_circuit_pulse() -> GifSpec:
    lines = [
        ((30, 80), (180, 80), (180, 40), (320, 40), (320, 120), (470, 120)),
        ((40, 220), (140, 220), (140, 170), (260, 170), (260, 250), (470, 250)),
        ((80, 140), (200, 140), (200, 210), (340, 210), (340, 90), (470, 90)),
    ]

    frames: list[Image.Image] = []
    for i in range(FRAME_COUNT):
        frame = blank_frame()
        draw = ImageDraw.Draw(frame)

        for path in lines:
            draw.line(path, fill=(24, 90, 150), width=3, joint="curve")
            for x, y in path:
                draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(55, 165, 220))

        pulse = (i / FRAME_COUNT) * 1.0
        for idx, path in enumerate(lines):
            seg_points = list(path)
            total = len(seg_points) - 1
            t = (pulse + idx * 0.22) % 1.0
            seg = min(total - 1, int(t * total))
            local = t * total - seg
            x1, y1 = seg_points[seg]
            x2, y2 = seg_points[seg + 1]
            px = int(x1 + (x2 - x1) * local)
            py = int(y1 + (y2 - y1) * local)
            glow = Image.new("RGB", (WIDTH, HEIGHT), (0, 0, 0))
            gdraw = ImageDraw.Draw(glow)
            gdraw.ellipse((px - 9, py - 9, px + 9, py + 9), fill=(120, 245, 255))
            frame = ImageChops.add(frame, glow)

        frames.append(frame.filter(ImageFilter.GaussianBlur(radius=0.3)))
    return GifSpec("tech-circuit-pulse.gif", 55, frames)


def make_radar_sweep() -> GifSpec:
    center = (WIDTH // 2, HEIGHT // 2)
    radius = 120
    points = [(130, 85), (388, 140), (322, 222), (250, 95), (162, 206)]

    frames: list[Image.Image] = []
    for i in range(FRAME_COUNT):
        frame = blank_frame()
        draw = ImageDraw.Draw(frame)

        for r in (30, 60, 90, 120):
            draw.ellipse((center[0] - r, center[1] - r, center[0] + r, center[1] + r), outline=(18, 80, 130), width=1)
        draw.line((center[0] - radius, center[1], center[0] + radius, center[1]), fill=(18, 80, 130), width=1)
        draw.line((center[0], center[1] - radius, center[0], center[1] + radius), fill=(18, 80, 130), width=1)

        angle = (i / FRAME_COUNT) * math.tau
        x2 = int(center[0] + math.cos(angle) * radius)
        y2 = int(center[1] + math.sin(angle) * radius)
        draw.line((center[0], center[1], x2, y2), fill=(95, 250, 200), width=2)

        for px, py in points:
            pangle = math.atan2(py - center[1], px - center[0]) % math.tau
            diff = min((angle - pangle) % math.tau, (pangle - angle) % math.tau)
            if diff < 0.25:
                draw.ellipse((px - 5, py - 5, px + 5, py + 5), fill=(180, 255, 170))
            else:
                draw.ellipse((px - 3, py - 3, px + 3, py + 3), fill=(42, 120, 90))

        frames.append(frame.filter(ImageFilter.GaussianBlur(radius=0.2)))
    return GifSpec("tech-radar-sweep.gif", 60, frames)


def main() -> None:
    out_dir = Path("assets/images/gif-tech-2026-03")
    specs = [
        make_holo_grid_scan(),
        make_data_rain(),
        make_orbital_network(),
        make_circuit_pulse(),
        make_radar_sweep(),
    ]
    for spec in specs:
        save_gif(spec, out_dir)

    readme = out_dir / "README.md"
    readme.write_text(
        "\n".join(
            [
                "# Tech GIF Pack (2026-03)",
                "",
                "Generated for web usage from `scripts/generate-tech-gifs.py`.",
                "",
                "Folder: `assets/images/gif-tech-2026-03`",
                "",
                "| File | Size | Frames | Notes |",
                "|---|---:|---:|---|",
                "| tech-holo-grid-scan.gif | 512x288 | 36 | Futuristic grid scanline |",
                "| tech-data-rain.gif | 512x288 | 36 | Data stream rain effect |",
                "| tech-orbital-network.gif | 512x288 | 36 | Orbiting node network |",
                "| tech-circuit-pulse.gif | 512x288 | 36 | Circuit pulse flow |",
                "| tech-radar-sweep.gif | 512x288 | 36 | Radar sweep and blips |",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
