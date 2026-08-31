# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "opencv-python-headless<5.0.0",
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""Generate transparent-background, tiered-opacity ASCII portrait SVGs.

- Person-only mask (GrabCut): face + suit kept, sides/background dropped.
- No <rect> background: art floats on the theme (DietrichGebert style).
- Brightness -> 4 opacity tiers on one ink color = shading = 3D look.
Usage: uv run gen_profile_svg.py [photo.jpg]
"""
import html
import sys
from pathlib import Path
import cv2
import numpy as np
from PIL import Image
import ascii_face as af

WIDTH = 80
FONT = "Consolas, Menlo, 'Courier New', monospace"
FS = 12
TITLE_FS = 26
ADV = FS * 0.55
ROW = 15
CW = WIDTH * ADV
CANVAS_W = 620
TITLE_Y = TITLE_FS + 8

INK = {"dark": "#C0C0C0", "light": "#24292f"}
# opacity per density tier (0=faintest .. 3=densest): faint chars recede, dense pop
TIERS = ("0.25", "0.45", "0.7", "1")

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


def person_mask(crop_rgb: np.ndarray, face_bbox) -> np.ndarray:
    """GrabCut person segmentation anchored by the face ellipse + torso bar."""
    h, w = crop_rgb.shape[:2]
    gc = np.zeros(crop_rgb.shape[:2], np.uint8)
    gc[:] = cv2.GC_PR_BGD
    # border = definite background
    gc[:3, :] = gc[-3:, :] = gc[:, :3] = gc[:, -3:] = cv2.GC_BGD
    r_fx, r_fy, fw, fh = face_bbox
    cv2.ellipse(gc, (r_fx + fw // 2, r_fy + fh // 2), (int(fw * 0.62), int(fh * 0.75)),
                0, 0, 360, cv2.GC_PR_FGD, -1)
    cv2.ellipse(gc, (r_fx + fw // 2, r_fy + fh // 2), (int(fw * 0.42), int(fh * 0.55)),
                0, 0, 360, cv2.GC_FGD, -1)
    # torso: bottom-center bar (suit)
    cv2.rectangle(gc, (int(w * 0.22), int(r_fy + fh * 1.5)),
                  (int(w * 0.78), h - 4), cv2.GC_PR_FGD, -1)
    bgd, fgd = np.zeros((1, 65), np.float64), np.zeros((1, 65), np.float64)
    cv2.grabCut(crop_rgb, gc, None, bgd, fgd, 5, cv2.GC_INIT_WITH_MASK)
    mask = np.where((gc == cv2.GC_FGD) | (gc == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE,
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
    return mask


def emit_row(row: str, vals: np.ndarray, keep: np.ndarray) -> str:
    """One <text> per row; consecutive same-tier runs become <tspan> with fill-opacity."""
    parts = []
    run_ch, run_t = [], None
    for c, ch in enumerate(row):
        if keep[c] and ch != " ":
            t = min(3, int(vals[c] / 255.0 * 4))
        else:
            t = None  # masked-out -> blank cell
        if t != run_t:
            if run_ch:
                body = html.escape("".join(run_ch))
                parts.append(f'<tspan fill-opacity="{TIERS[run_t]}">{body}</tspan>'
                             if run_t is not None else f"<tspan>{body}</tspan>")
            run_ch, run_t = [], t
        run_ch.append(ch if ch != " " else " ")
    if run_ch:
        body = html.escape("".join(run_ch))
        parts.append(f'<tspan fill-opacity="{TIERS[run_t]}">{body}</tspan>'
                     if run_t is not None else f"<tspan>{body}</tspan>")
    return "".join(parts)


def main():
    photo = sys.argv[1] if len(sys.argv) > 1 else "微信图片_20260605222854_71960_665.jpg"
    img = np.array(Image.open(photo).convert("RGB"))
    crop, fb, eyes = af.detect_and_crop_face(img)
    enhanced = af.enhance_facial_details(crop, face_bbox=fb, eye_bboxes=eyes, brow_soft=1.5)
    rows = af.render_ascii(enhanced, crop, width=WIDTH, ramp_name="crisp",
                           invert=False, color=False).split("\n")
    n = len(rows)
    out_h = enhanced.shape[0] and n  # rows count
    # per-cell brightness, same grid as render_ascii
    vals = cv2.resize(enhanced, (WIDTH, n), interpolation=cv2.INTER_AREA).astype(np.float32)
    keep2d = person_mask(crop, fb)
    keep = cv2.resize(keep2d, (WIDTH, n), interpolation=cv2.INTER_AREA) > 127

    # trim fully-blank rows and columns
    row_has = keep.any(axis=1)
    r0, r1 = np.argmax(row_has), len(row_has) - np.argmax(row_has[::-1])
    rows = rows[r0:r1]
    vals, keep = vals[r0:r1], keep[r0:r1]
    col_has = keep.any(axis=0)
    c0 = int(np.argmax(col_has))
    c1 = len(col_has) - int(np.argmax(col_has[::-1]))
    art_x = (CANVAS_W - (c1 - c0) * ADV) / 2

    n = len(rows)
    H = TITLE_Y + 18 + n * ROW + 10
    for mode, ink in INK.items():
        parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" height="{H}" '
            f'viewBox="0 0 {CANVAS_W} {H}" font-family="{FONT}">',
            SILVER_DEFS,
            f'<text x="{CANVAS_W / 2}" y="{TITLE_Y}" fill="#9aa0a6" font-size="{TITLE_FS}" '
            f'font-weight="bold" text-anchor="middle">czpGhost@github</text>',
            f'<g clip-path="url(#titleclip)">'
            f'<rect class="beam" x="{CANVAS_W / 2 - 120}" y="0" width="240" height="40" fill="url(#silver)"/>'
            f'</g>',
        ]
        for i, row in enumerate(rows):
            seg = emit_row(row[c0:c1], vals[i][c0:c1], keep[i][c0:c1])
            y = TITLE_Y + 18 + i * ROW
            parts.append(
                f'<text x="{art_x:.1f}" y="{y}" fill="{ink}" font-size="{FS}" '
                f'xml:space="preserve">{seg}</text>'
            )
        parts.append("</svg>")
        Path(f"{mode}_mode.svg").write_text("\n".join(parts), encoding="utf-8")
        print(f"wrote {mode}_mode.svg ({n} rows, cols {c0}-{c1}, {H}px)")


if __name__ == "__main__":
    main()
