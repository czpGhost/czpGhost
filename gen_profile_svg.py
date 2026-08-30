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
TITLE_FS = 26    # 标题字号
ADV = FS * 0.55  # 等宽字符前进宽
ROW = 15         # 行高
CW = WIDTH * ADV
CANVAS_W = 620
ART_Y0 = 64

PAL = {
    "dark": {"bg": "#0d1117", "border": "#30363d", "art": "#C0C0C0"},
    "light": {"bg": "#ffffff", "border": "#d0d7de", "art": "#24292f"},
}

# 银色流光:高光矩形裁剪到文字形状 + CSS transform 扫描(GitHub img 内可播放)
TITLE_Y = TITLE_FS + 8
SILVER_DEFS = f"""
<style>
@keyframes silverflow {{
  0%   {{ transform: translateX(-250px); }}
  50%  {{ transform: translateX(250px); }}
  100% {{ transform: translateX(-250px); }}
}}
.beam {{ animation: silverflow 3.5s ease-in-out infinite; }}
</style>
<defs>
  <linearGradient id="silver" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#9aa0a6"/>
    <stop offset="0.45" stop-color="#f5f7f9"/>
    <stop offset="0.5" stop-color="#ffffff"/>
    <stop offset="0.55" stop-color="#f5f7f9"/>
    <stop offset="1" stop-color="#9aa0a6"/>
  </linearGradient>
  <clipPath id="titleclip">
    <text x="{CANVAS_W / 2}" y="{TITLE_Y}" font-size="{TITLE_FS}" font-weight="bold" text-anchor="middle">czpGhost@github</text>
  </clipPath>
</defs>
"""


def main():
    photo = sys.argv[1] if len(sys.argv) > 1 else "微信图片_20260605222854_71960_665.jpg"
    img = np.array(Image.open(photo).convert("RGB"))
    crop, fb, eyes = af.detect_and_crop_face(img)
    enhanced = af.enhance_facial_details(crop, face_bbox=fb, eye_bboxes=eyes, brow_soft=1.5)
    rows = af.render_ascii(enhanced, crop, width=WIDTH, ramp_name="crisp",
                           invert=False, color=False).split("\n")
    n = len(rows)
    H = ART_Y0 + n * ROW + 24
    art_x = (CANVAS_W - CW) / 2

    for mode, p in PAL.items():
        art_mid = CANVAS_W / 2
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{H}" '
            f'viewBox="0 0 {CANVAS_W} {H}" font-family="{FONT}">',
            SILVER_DEFS,
            f'<rect x="0.5" y="0.5" width="{CANVAS_W - 1}" height="{H - 1}" rx="14" '
            f'fill="{p["bg"]}" stroke="{p["border"]}"/>',
            f'<text x="{art_mid}" y="{TITLE_Y}" fill="#9aa0a6" font-size="{TITLE_FS}" '
            f'font-weight="bold" text-anchor="middle">czpGhost@github</text>',
            f'<g clip-path="url(#titleclip)">'
            f'<rect class="beam" x="{art_mid - 120}" y="0" width="240" height="40" fill="url(#silver)"/>'
            f'</g>',
        ]
        for i, row in enumerate(rows):
            parts.append(
                f'<text x="{art_x:.1f}" y="{ART_Y0 + i * ROW}" fill="{p["art"]}" '
                f'font-size="{FS}" xml:space="preserve">{html.escape(row)}</text>'
            )
        parts.append("</svg>")
        out = "\n".join(parts)
        Path(f"{mode}_mode.svg").write_text(out, encoding="utf-8")
        print(f"wrote {mode}_mode.svg ({n} rows, {WIDTH}x{n})")


if __name__ == "__main__":
    main()