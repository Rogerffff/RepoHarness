"""RGBA 图带元组 info["transparency"]（S19）：convert 之后与 _normalize_mode 之后 transparency 的值，以及被选中的调色板项。"""
from PIL import GifImagePlugin, Image

r = Image.new("RGBA", (256, 1))
for x in range(256):
    r.putpixel((x, 0), (x, 0, 0, 255))
r.info["transparency"] = (255, 255, 255)
q = r.convert("P", palette=Image.Palette.ADAPTIVE)
print("after convert:", q.palette.mode, repr(q.info.get("transparency")))
n = GifImagePlugin._normalize_mode(r)
t = n.info.get("transparency")
print("after _normalize_mode:", repr(t), "palette entry:", n.palette.palette[4 * t:4 * t + 4], "pixels using it:", n.histogram()[t])
