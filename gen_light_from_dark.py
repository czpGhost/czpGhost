# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24.0", "opencv-python-headless<5.0.0", "pillow>=10.0.0"]
# ///
"""从 dark_mode.svg 生成 light_mode.svg (v4: 以 dark 卡为唯一参照).

dark 卡语义 = 银色底板(墙/西装/五官亮面) + 暗缝(眼窝/嘴缝/五官细节).
light 卡语义 = 白纸 + 墨素描:
  - dark 暗缝 (op0.25 疏符)      -> 浓墨密符 0.85 (符号镜像, 五官细节成墨笔)
  - dark 实体块 (op1, 中短游程)  -> 浓墨 0.90 (西装/鼻梁/嘴唇: 白纸上最重的实体)
  - dark 背景墙 (op1, 长纯密游程) -> 近白 0.15 (洗成纸面)
  - 中间档保持中间 (0.45<->0.55, 0.7->0.45)
dark_mode.svg 永不修改.
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
dens = {c: i / (n - 1) for i, c in enumerate(ramp)}

src = Path("dark_mode.svg").read_text(encoding="utf-8")

BG_OP = "0.15"     # 背景墙洗白
SOLID_OP = "0.90"  # 实体块浓墨
MIN_RUN = 10       # 连续纯密字符 >= 10 判为背景墙


def flip(m):
    attrs, body = m.group(1), html.unescape(m.group(2))
    om = re.search(r'fill-opacity="([\d.]+)"', attrs)
    op0 = om.group(1) if om else "1"
    flipped = "".join(mirror.get(c, c) for c in body)
    if op0 == "1":
        # 实体块判据: 原始 body 中密度>0.8 的字符占比 >= 70% 且长度>=6
        # 背景墙 = 长纯密游程(无疏符掺杂) -> 洗白; 西装/五官亮面有过渡字符掺杂 -> 保留浓墨
        solid = sum(1 for c in body if dens.get(c, 0) > 0.80)
        is_bg = len(body) >= 6 and solid / len(body) >= 0.70
        new_op = BG_OP if is_bg else SOLID_OP
    else:
        swap = {"0.25": "0.85", "0.45": "0.55", "0.7": "0.45"}
        new_op = swap.get(op0, op0)
    return '<tspan fill-opacity="{}">{}</tspan>'.format(
        new_op, html.escape(flipped, quote=False)
    )


out_lines = []
for line in src.split("\n"):
    if 'font-size="12"' in line and "<tspan" in line:
        line = re.sub(r"<tspan([^>]*)>(.*?)</tspan>", flip, line)
    out_lines.append(line)
out = "\n".join(out_lines)
out = out.replace('fill="#C0C0C0"', 'fill="#24292f"')
Path("light_mode.svg").write_text(out, encoding="utf-8")
print("wrote light_mode.svg")
