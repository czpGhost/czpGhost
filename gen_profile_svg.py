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
import cv2
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
    # 只生成 light 卡; dark_mode.svg 为用户定稿版本, 本脚本不再触碰
    "light": {"bg": "#fdfdfd", "border": "#e4e8ec", "art": "#3a4149",
              "ops": ("1", "0.72", "0.45", "0.22")},
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
    # invert 按底色定: light 白底用 True (暗->密), dark 深底用 False (亮->密)
    rows_by_mode = {
        m: af.render_ascii(enhanced, crop, width=WIDTH, ramp_name="crisp",
                           invert=(m == "light"), color=False).split("\n")
        for m in PAL
    }
    N_ROWS = len(next(iter(rows_by_mode.values())))
    # 与渲染同网格的每格亮度, 供分级不透明度使用
    vals = cv2.resize(enhanced, (WIDTH, N_ROWS), interpolation=cv2.INTER_AREA).astype(np.float32)
    n = N_ROWS
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
        OPS = p["ops"]
        for i in range(n):
            # 四档不透明度: 暗(五官/发丝)最实 -> 亮(背景)几乎隐形, 灰阶过渡更平滑
            t4 = np.clip(np.floor((3 - vals[i] / 255.0 * 4)), 0, 3).astype(int)
            segs, run_t, run_c = [], None, []
            row = rows_by_mode[mode][i]
            for c in range(WIDTH):
                t = None if row[c] == " " else int(t4[c])
                if t != run_t:
                    if run_c:
                        body = html.escape("".join(run_c))
                        segs.append(f'<tspan fill-opacity="{OPS[run_t]}">{body}</tspan>'
                                    if run_t is not None else f"<tspan>{body}</tspan>")
                    run_c, run_t = [], t
                run_c.append(row[c])
            if run_c:
                body = html.escape("".join(run_c))
                segs.append(f'<tspan fill-opacity="{OPS[run_t]}">{body}</tspan>'
                            if run_t is not None else f"<tspan>{body}</tspan>")
            parts.append(
                f'<text x="{art_x:.1f}" y="{ART_Y0 + i * ROW}" fill="{p["art"]}" '
                f'font-size="{FS}" xml:space="preserve">{"".join(segs)}</text>'
            )
        parts.append("</svg>")
        out = "\n".join(parts)
        Path(f"{mode}_mode.svg").write_text(out, encoding="utf-8")
        print(f"wrote {mode}_mode.svg ({n} rows, {WIDTH}x{n})")


if __name__ == "__main__":
    main()