# 在 gold 之上移植上游 Pillow 11.0.0 对 N1 的两处改动（convert 的透明度分支、putpalette 接受无 rawmode 的 ImagePalette）
p = "src/PIL/Image.py"
s = open(p).read()
old1 = "                        trns_im.putpalette(self.palette)\n"
new1 = "                        trns_im.putpalette(self.palette, self.palette.mode)\n"
assert s.count(old1) == 1
s = s.replace(old1, new1)
old2 = """        if isinstance(data, ImagePalette.ImagePalette):
            palette = ImagePalette.raw(data.rawmode, data.palette)
        else:
            if not isinstance(data, bytes):
                data = bytes(data)
            palette = ImagePalette.raw(rawmode, data)
        self.mode = "PA" if "A" in self.mode else "P"
        self.palette = palette
        self.palette.mode = "RGB"
"""
new2 = """        if isinstance(data, ImagePalette.ImagePalette):
            if data.rawmode is not None:
                palette = ImagePalette.raw(data.rawmode, data.palette)
            else:
                palette = ImagePalette.ImagePalette(palette=data.palette)
                palette.dirty = 1
        else:
            if not isinstance(data, bytes):
                data = bytes(data)
            palette = ImagePalette.raw(rawmode, data)
        self.mode = "PA" if "A" in self.mode else "P"
        self.palette = palette
        self.palette.mode = "RGBA" if "A" in rawmode else "RGB"
"""
assert s.count(old2) == 1
s = s.replace(old2, new2)
open(p, "w").write(s)
