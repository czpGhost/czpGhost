"""生成 ghost-banner.svg / ghost-footer.svg (银灰流光风, CSS 动画, GitHub README 可播放)."""
from pathlib import Path

FONT = "Consolas, Menlo, 'Courier New', monospace"

# 银灰渐变: 与 gen_profile_svg.py 标题流光同源
GRAD = """
  <linearGradient id="silver" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#9aa0a6"/>
    <stop offset="0.45" stop-color="#f5f7f9"/>
    <stop offset="0.5" stop-color="#ffffff"/>
    <stop offset="0.55" stop-color="#f5f7f9"/>
    <stop offset="1" stop-color="#9aa0a6"/>
  </linearGradient>
  <linearGradient id="silversoft" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#6e7278" stop-opacity="0.9"/>
    <stop offset="0.5" stop-color="#e8eaed" stop-opacity="0.9"/>
    <stop offset="1" stop-color="#6e7278" stop-opacity="0.9"/>
  </linearGradient>"""

# 浅色主题: 深墨字 + 深灰波浪, 保证浅底可读
GRAD_LIGHT = """
  <linearGradient id="silver" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#8b949e"/>
    <stop offset="0.45" stop-color="#4b5560"/>
    <stop offset="0.5" stop-color="#24292f"/>
    <stop offset="0.55" stop-color="#4b5560"/>
    <stop offset="1" stop-color="#8b949e"/>
  </linearGradient>
  <linearGradient id="silversoft" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0" stop-color="#9aa0a6" stop-opacity="0.9"/>
    <stop offset="0.5" stop-color="#57606a" stop-opacity="0.9"/>
    <stop offset="1" stop-color="#9aa0a6" stop-opacity="0.9"/>
  </linearGradient>"""

# 波浪 path: 一条完整正弦周期, 拼两倍宽做无缝横移循环
def wave_path(width: int, base_y: float, amp: float, wavelength: float) -> str:
    seg = wavelength / 2
    pts = []
    x = 0.0
    while x <= width + wavelength:
        # 交替上/下半波, 二次贝塞尔近似正弦
        ctrl_y = base_y - amp if (int(x / seg) % 2 == 0) else base_y + amp
        pts.append(f"Q {x + seg / 2:.1f} {ctrl_y:.1f} {x + seg:.1f} {base_y:.1f}")
        x += seg
    return f"M 0 {base_y:.1f} " + " ".join(pts)


def banner(theme: str) -> str:
    W, H = 1200, 220
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    waves = []
    for i, (y, amp, wl, op, dur) in enumerate([
        (150, 16, 260, 0.5, 7), (162, 20, 320, 0.7, 9), (176, 24, 400, 1.0, 11),
    ]):
        d = wave_path(W, y, amp, wl)
        waves.append(
            f'<g class="wave w{i}"><path d="{d}" fill="none" stroke="url(#silversoft)" '
            f'stroke-width="{2 + i}" stroke-opacity="{op}" stroke-linecap="round"/></g>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<style>
@keyframes drift {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-{400}px); }} }}
@keyframes sweep {{ 0% {{ transform: translateX(-320px); }} 50% {{ transform: translateX(320px); }} 100% {{ transform: translateX(-320px); }} }}
@keyframes glow {{ 0%,100% {{ opacity: 0.92; }} 50% {{ opacity: 1; }} }}
.wave {{ animation: drift 11s linear infinite; }}
.w0 {{ animation-duration: 14s; opacity: 0.9; }}
.w1 {{ animation-duration: 11s; }}
.w2 {{ animation-duration: 8s; }}
.beam {{ animation: sweep 6s ease-in-out infinite; }}
.gt {{ animation: glow 6s ease-in-out infinite; }}
</style>
<defs>{GRAD if theme == "dark" else GRAD_LIGHT}
  <clipPath id="all"><rect width="{W}" height="{H}" rx="0"/></clipPath>
  <clipPath id="gt"><text x="{W / 2}" y="96" font-size="72" font-weight="bold" text-anchor="middle">Ghost</text></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="{bg}"/>
<g clip-path="url(#all)">
  {''.join(waves)}
  <g clip-path="url(#gt)"><rect class="beam" x="-320" y="0" width="640" height="140" fill="url(#silver)"/></g>
  <text class="gt" x="{W / 2}" y="96" font-size="72" font-weight="bold" text-anchor="middle" fill="{'#e8eaed' if theme == 'dark' else '#24292f'}" fill-opacity="{'0.35' if theme == 'dark' else '0.5'}">Ghost</text>
</g>
</svg>
"""

def footer(theme: str) -> str:
    W, H = 1200, 120
    bg = "#0d1117" if theme == "dark" else "#ffffff"
    waves = []
    for i, (y, amp, wl, op) in enumerate([
        (52, 12, 280, 0.55), (62, 16, 340, 0.8), (74, 18, 420, 1.0),
    ]):
        d = wave_path(W, y, amp, wl)
        waves.append(
            f'<g class="wave w{i}"><path d="{d}" fill="none" stroke="url(#silversoft)" '
            f'stroke-width="{2 + i}" stroke-opacity="{op}" stroke-linecap="round"/></g>'
        )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="{FONT}">
<style>
@keyframes drift {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-420px); }} }}
@keyframes sweep {{ 0% {{ transform: translateX(-320px); }} 50% {{ transform: translateX(320px); }} 100% {{ transform: translateX(-320px); }} }}
.wave {{ animation: drift 11s linear infinite; }}
.w0 {{ animation-duration: 15s; }}
.w1 {{ animation-duration: 11s; }}
.w2 {{ animation-duration: 8s; }}
.beam {{ animation: sweep 6s ease-in-out infinite; }}
</style>
<defs>{GRAD if theme == "dark" else GRAD_LIGHT}
  <clipPath id="all"><rect width="{W}" height="{H}"/></clipPath>
</defs>
<rect width="{W}" height="{H}" fill="{bg}"/>
<rect width="{W}" height="{H}" fill="url(#fade)"/>
<g clip-path="url(#all)">
  {''.join(waves)}
</g>
</svg>
"""


# footer 底部渐变叠加层
GRAD_FADE = """
  <linearGradient id="fade" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0.45" stop-color="#0d1117" stop-opacity="0"/>
    <stop offset="1" stop-color="#05070a" stop-opacity="0.85"/>
  </linearGradient>"""


def main():
    # footer fade 渐变按主题适配底色
    fade_dark = GRAD_FADE
    fade_light = GRAD_FADE.replace("#0d1117", "#ffffff").replace("#05070a", "#f0f2f4")
    outputs = {}
    for theme in ("dark", "light"):
        outputs[f"ghost-banner-{theme}.svg"] = banner(theme)
        outputs[f"ghost-footer-{theme}.svg"] = footer(theme).replace(
            "<defs>" + GRAD, "<defs>" + GRAD + (fade_dark if theme == "dark" else fade_light)
        )
    for name, content in outputs.items():
        Path(name).write_text(content, encoding="utf-8")
        print("wrote", name)


if __name__ == "__main__":
    main()
