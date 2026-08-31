# /// script
# requires-python = ">=3.10"
# dependencies = ["numpy>=1.24.0", "opencv-python-headless<5.0.0", "pillow>=10.0.0"]
# ///
"""从 dark_mode.svg 反转生成 light_mode.svg: 符号镜像 + 透明度档位互换 + 墨色白底."""
from pathlib import Path
import re
import html
import sys

sys.path.insert(0, ".")
from ascii_face import RAMPS

ramp = RAMPS["crisp"]
n = len(ramp)
print("权威 ramp len:", n)
mirror = {c: ramp[n - 1 - i] for i, c in enumerate(ramp)}
print("校验: & ->", repr(mirror["&"]), "W ->", repr(mirror["W"]), "o ->", repr(mirror["o"]), "! ->", repr(mirror["!"]))

src = Path("dark_mode.svg").read_text(encoding="utf-8")
OP_SWAP = {"0.25": "1", "0.45": "0.7", "0.7": "0.45", "1": "0.25"}


def flip(m):
    attrs, body = m.group(1), html.unescape(m.group(2))
    flipped = "".join(mirror.get(c, c) for c in body)
    om = re.search(r'fill-opacity="([\d.]+)"', attrs)
    if om:
        attrs = attrs.replace(om.group(0), f'fill-opacity="{OP_SWAP[om.group(1)]}"')
    else:
        attrs += ' fill-opacity="0.25"'
    return "<tspan" + attrs + ">" + html.escape(flipped, quote=False) + "</tspan>"


out_lines = []
for line in src.split("\n"):
    if 'font-size="12"' in line and "<tspan" in line:
        line = re.sub(r"<tspan([^>]*)>(.*?)</tspan>", flip, line)
    out_lines.append(line)
out = "\n".join(out_lines)
out = out.replace('fill="#C0C0C0"', 'fill="#24292f"')
Path("light_mode.svg").write_text(out, encoding="utf-8")

m = re.search(r'<text x="145.0" y="52".*?</text>', out, re.S)
print("行0:", m.group(0)[60:230])
print("尺寸:", re.search(r'width="(\d+)" height="(\d+)"', out).groups())
