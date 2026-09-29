"""补充：palette= 与原调色板同序；以及 RGBA 调色板图 → palette= 的 C 层调色板与读回调色板前 4 项。"""
import io
import json

from PIL import Image

COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)]
ALPHAS = [255, 128, 255, 0]
im = Image.new("P", (4, 1))
for x in range(4):
    im.putpixel((x, 0), x)
flat = [v for c, a in zip(COLORS, ALPHAS) for v in (*c, a)]
im.putpalette(flat + [0] * (1024 - len(flat)), "RGBA")
out = {}
for name, order in (("same_order", COLORS), ("reordered", [COLORS[2], COLORS[0], COLORS[3], COLORS[1]])):
    buf = io.BytesIO()
    im.save(buf, "GIF", palette=[v for c in order for v in c])
    buf.seek(0)
    r = Image.open(buf)
    r.load()
    out[name] = {"reloaded_rgb": [r.convert("RGB").getpixel((x, 0)) for x in range(4)],
                 "reloaded_palette_head": r.getpalette()[:12], "indices": [r.getpixel((x, 0)) for x in range(4)]}
out["expected_rgb"] = COLORS
print(json.dumps(out))
