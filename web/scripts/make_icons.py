"""Draws the app icons into web/public/icons (run: python web/scripts/make_icons.py).
The mark is two stops joined by a route, in the app colors. Needs Pillow (pip install pillow)."""
from pathlib import Path

from PIL import Image, ImageDraw

BG, MINT, WHITE = (16, 20, 19), (165, 242, 215), (224, 227, 225)
OUT = Path(__file__).resolve().parents[1] / "public" / "icons"


def draw(size: int, safe: float = 0.0) -> Image.Image:
    """`safe` shrinks the mark so maskable icons survive circular cropping."""
    scale = 4  # draw big, then shrink for smooth edges
    s = size * scale
    img = Image.new("RGB", (s, s), BG)
    d = ImageDraw.Draw(img)
    inset = s * (0.22 + safe)
    x0, y0, x1, y1 = inset, inset, s - inset, s - inset
    width = max(2, int(s * 0.055))
    path = [(x0, y1), (x0 + (x1 - x0) * 0.55, y1), (x1, y1 - (y1 - y0) * 0.35), (x1, y0)]
    d.line(path, fill=MINT, width=width, joint="curve")
    r = s * 0.075
    d.ellipse([x0 - r, y1 - r, x0 + r, y1 + r], fill=BG, outline=WHITE, width=int(width * 0.7))
    d.ellipse([x1 - r, y0 - r, x1 + r, y0 + r], fill=MINT, outline=BG, width=int(width * 0.5))
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192).save(OUT / "icon-192.png")
    draw(512).save(OUT / "icon-512.png")
    draw(512, safe=0.08).save(OUT / "icon-maskable-512.png")
    draw(180).save(OUT / "apple-touch-icon.png")
    print("wrote icons to", OUT)


if __name__ == "__main__":
    main()
