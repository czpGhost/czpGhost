# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Slow down GIFs by patching frame delays in raw bytes.

Frames stay byte-identical (true "looks same but slower"): only the 2-byte
delay field inside each Graphic Control Extension is scaled.

Usage: uv run slow_gif.py [factor]   (default factor = 2.0)
Writes ghost-*-slow.gif next to the originals.
"""
import re
import struct
import sys
from pathlib import Path

FACTOR = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
# GCE block: 21 F9 04 <flags> <delay:2> <transparent-idx> 00  (8 bytes total)
GCE = re.compile(rb"\x21\xf9\x04.(..).\x00", re.DOTALL)

for name in ("ghost-banner.gif", "ghost-footer.gif"):
    src = Path(name)
    data = src.read_bytes()
    out = bytearray()
    pos = 0
    for m in GCE.finditer(data):
        out += data[pos:m.start()]
        cur = struct.unpack("<H", data[m.start() + 4:m.start() + 6])[0]
        new = min(65535, round(cur * FACTOR))
        out += data[m.start():m.start() + 4] + struct.pack("<H", new) + data[m.start() + 6:m.end()]
        pos = m.end()
    out += data[pos:]
    dst = src.with_name(src.stem + "-slow.gif")
    dst.write_bytes(bytes(out))
    print(f"{name} -> {dst.name}: delays x{FACTOR:g} (e.g. 170ms -> {round(170 * FACTOR)}ms)")
