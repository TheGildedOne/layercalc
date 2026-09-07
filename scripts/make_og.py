#!/usr/bin/env python3
"""Generate social-share images (1200x630) for every page, plus the app icon.

Needs Pillow (pip install pillow). Run once locally and commit static/og/ -
the deploy workflow does not regenerate them, so a missing image simply falls
back to default.png. Re-run after adding a calculator:

    python scripts/make_og.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import build  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

OUT = build.STATIC / "og"
W, H = 1200, 630
BG, INK, MUTED, ACCENT = "#f6f6f2", "#1b1d21", "#5d6370", "#e4561a"

FONT_CANDIDATES = ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/Library/Fonts/Arial Bold.ttf"]
FONT_REG = ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/Library/Fonts/Arial.ttf"]


def font(candidates, size):
    for c in candidates:
        if Path(c).exists():
            return ImageFont.truetype(c, size)
    return ImageFont.load_default(size=size)


def mark(draw, x, y, s):
    """The three-bar logo at scale s (1 = 64px)."""
    draw.rounded_rectangle([x, y, x + 64 * s, y + 64 * s], radius=14 * s, fill=ACCENT)
    for (bx, by, bw, alpha) in [(12, 40, 40, 255), (16, 28, 32, 210), (20, 16, 24, 170)]:
        col = (255, 255, 255, alpha)
        draw.rounded_rectangle([x + bx * s, y + by * s, x + (bx + bw) * s, y + (by + 8) * s], radius=4 * s, fill=col)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def render(title, subtitle, out: Path):
    img = Image.new("RGBA", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 18, H], fill=ACCENT)
    mark(d, 80, 70, 1.25)
    brand = font(FONT_CANDIDATES, 40)
    d.text((190, 84), build.SITE["name"], font=brand, fill=INK)
    d.text((190, 132), "Free 3D printing calculators", font=font(FONT_REG, 26), fill=MUTED)

    size = 74
    while True:
        tf = font(FONT_CANDIDATES, size)
        lines = wrap(d, title, tf, W - 160)
        if len(lines) <= 3 or size <= 44:
            break
        size -= 6
    y = 250
    for line in lines:
        d.text((80, y), line, font=tf, fill=INK)
        y += size * 1.15
    d.text((80, H - 90), subtitle, font=font(FONT_REG, 28), fill=MUTED)
    img.convert("RGB").save(out, "PNG", optimize=True)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    domain = build.SITE["url"].replace("https://", "")
    render("Free 3D printing calculators", f"No signup · runs in your browser · {domain}", OUT / "default.png")
    for tool in build.load_calculators():
        render(tool["title"], f"Free · no signup · {domain}", OUT / f"{tool['slug']}.png")
    for cat in build.CATEGORIES.values():
        render(cat["title"], f"Free · no signup · {domain}", OUT / f"{cat['slug']}.png")

    icon = Image.new("RGBA", (180, 180), (0, 0, 0, 0))
    mark(ImageDraw.Draw(icon), 0, 0, 180 / 64)
    icon.save(build.STATIC / "apple-touch-icon.png", "PNG", optimize=True)
    print(f"wrote share images to {OUT.relative_to(build.ROOT)}/ and apple-touch-icon.png")


if __name__ == "__main__":
    main()
