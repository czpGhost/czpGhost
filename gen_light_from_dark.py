# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""从 dark_mode.svg 生成 light_mode.svg (v11: 字符原样, 仅反转浓淡档位).

dark 卡 (银字深底) 档位 -> light 卡 (墨字白底) 两极反转:
  op 1    (背景墙, 最浓) -> 0.04 (几乎纯白)
  op 0.7  (眼睑/唇纹亮线) -> 0.30 (可见线条)
  op 0.45 (过渡)          -> 0.65
  op 0.25 (眼窝/脸颊阴影暗缝, 最淡) -> 1.0 纯墨 (突出五官纹理)
字符本体与 dark 卡逐字节一致, 仅 fill 换墨色.
dark_mode.svg 永不修改.
"""
from pathlib import Path
import re
import html

OP_INVERT = {"1": "0.04", "0.7": "0.3", "0.45": "0.65", "0.25": "1"}

src = Path("dark_mode.svg").read_text(encoding="utf-8")




def flip(m):
    om = re.search(r'fill-opacity="([\d.]+)"', m.group(1))
    new_op = OP_INVERT[om.group(1) if om else "1"]
    body = html.unescape(m.group(2))
    return '<tspan fill-opacity="{}">{}</tspan>'.format(
        new_op, html.escape(body, quote=False)
    )


out_lines = []
for line in src.split("\n"):
    if 'font-size="12"' in line and "<tspan" in line:
        line = re.sub(r"<tspan([^>]*)>(.*?)</tspan>", flip, line)
    out_lines.append(line)
out = "\n".join(out_lines)
out = out.replace('fill="#C0C0C0"', 'fill="#24292f"')
Path("light_mode.svg").write_text(out, encoding="utf-8")
print("wrote light_mode.svg (v11 inverted tiers)")
