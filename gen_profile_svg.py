# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "opencv-python-headless<5.0.0",
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""Generate dark_mode.svg / light_mode.svg ASCII profile card.
Usage: uv run gen_profile_svg.py [photo.jpg]
Locks the approved look: crisp ramp + brow_soft=1.5, 80 cols.
"""
import html
import sys
from pathlib import Path
import numpy as np
from PIL import Image
import ascii_face as af

WIDTH = 80
FONT = "Consolas, Menlo, 'Courier New', monospace"
FS = 12          # font-size px
ADV = FS * 0.55  # 等宽字符前进宽
ROW = 15         # 行高
CW = WIDTH * ADV
CANVAS_W = 620
ART_Y0 = 76

PAL = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "art": "#C0C0C0",
             "title": "#58a6ff", "sub": "#8b949e", "mail": "#ffa657"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "art": "#24292f",
              "title": "#0969da", "sub": "#57606a", "mail": "#953800"},
}


def main():
    photo = sys.argv[1] if len(sys.argv) > 1 else "微信图片_20260605222854_71960_665.jpg"
    img = np.array(Image.open(photo).convert("RGB"))
    crop, fb, eyes = af.detect_and_crop_face(img)
    enhanced = af.enhance_facial_details(crop, face_bbox=fb, eye_bboxes=eyes, brow_soft=1.5)
    rows = af.render_ascii(enhanced, crop, width=WIDTH, ramp_name="crisp",
                           invert=False, color=False).split("\n")
    n = len(rows)
    H = ART_Y0 + n * ROW + 36
    art_x = (CANVAS_W - CW) / 2

    for mode, p in PAL.items():
        art_mid = CANVAS_W / 2
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{H}" '
            f'viewBox="0 0 {CANVAS_W} {H}" font-family="{FONT}">',
            f'<rect x="0.5" y="0.5" width="{CANVAS_W - 1}" height="{H - 1}" rx="14" '
            f'fill="{p["bg"]}" stroke="{p["border"]}"/>',
            f'<text x="{art_mid}" y="30" fill="{p["title"]}" font-size="15" '
            f'font-weight="bold" text-anchor="middle">czpGhost@github</text>',
            f'<text x="{art_mid}" y="52" fill="{p["sub"]}" font-size="12" '
            f'text-anchor="middle">人文精神是 AI 的灵魂 · The human spirit is the soul of AI.</text>',
        ]
        for i, row in enumerate(rows):
            parts.append(
                f'<text x="{art_x:.1f}" y="{ART_Y0 + i * ROW}" fill="{p["art"]}" '
                f'font-size="{FS}" xml:space="preserve">{html.escape(row)}</text>'
            )
        parts.append(
            f'<text x="{art_mid}" y="{ART_Y0 + n * ROW + 22}" fill="{p["mail"]}" font-size="12" '
            f'font-weight="bold" text-anchor="middle">✉ ghost.czp@gmail.com</text>'
        )
        parts.append("</svg>")
        out = "\n".join(parts)
        Path(f"{mode}_mode.svg").write_text(out, encoding="utf-8")
        print(f"wrote {mode}_mode.svg ({n} rows, {WIDTH}x{n})")


if __name__ == "__main__":
    main()