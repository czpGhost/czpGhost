# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24.0", "opencv-python-headless<5.0.0", "pillow>=10.0.0"]
# ///
"""从 dark_mode.svg 反转生成 light_mode.svg.

方案: 符号镜像 + 轮廓增强档位映射.
- 符号按 crisp 密度轴镜像 (疏<->密), 使五官暗部在白底上由浓密笔画勾出.
- 透明度向两端推: 背景纹理近白 (0.18/0.25), 五官浓墨但保留笔画感 (0.85, 非实心).
- dark_mode.svg 是唯一事实源, 永不修改.
"""
from pathlib import Path
import re
import html
import sys

sys.path.insert(0, ".")
from ascii_face import RAMPS

ramp = RAMPS["crisp"]
n = len(ramp)
mirror = {c: ramp[n - 1 - i] for i, c in enumerate(ramp)}

src = Path("dark_mode.svg").read_text(encoding="utf-8")
# 轮廓增强: 五官密符 0.85(浓而有笔画感), 中间档大间隔, 背景近白
OP_SWAP = {"1": "0.18", "0.7": "0.25", "0.45": "0.55", "0.25": "0.85"}


def flip(m):
    attrs, body = m.group(1), html.unescape(m.group(2))
    flipped = "".join(mirror.get(c, c) for c in body)
    om = re.search(r'fill-opacity="([\d.]+)"', attrs)
    if om:
        attrs = attrs.replace(om.group(0), f'fill-opacity="{OP_SWAP[om.group(1)]}"')
    else:
        attrs += ' fill-opacity="0.18"'
    return "<tspan" + attrs + ">" + html.escape(flipped, quote=False) + "</tspan>"


out_lines = []
for line in src.split("\n"):
    if 'font-size="12"' in line and "<tspan" in line:
        line = re.sub(r"<tspan([^>]*)>(.*?)</tspan>", flip, line)
    out_lines.append(line)
out = "\n".join(out_lines)
out = out.replace('fill="#C0C0C0"', 'fill="#24292f"')
Path("light_mode.svg").write_text(out, encoding="utf-8")
print("wrote light_mode.svg")
