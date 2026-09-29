# 按旧卡 card.md 第 44-51 行描述重建 C1（RGB 写回 C 层 + putpalettealphas；Python 层保留原 mode）
from pathlib import Path
p = Path("src/PIL/Image.py")
s = p.read_text()
old1 = '''        if source_palette is None:
            if self.mode == "P":
                self.load()
                source_palette = self.im.getpalette("RGB")[:768]
'''
new1 = '''        palette_mode = "RGB"
        bands = 3
        if source_palette is None:
            if self.mode == "P":
                self.load()
                palette_mode = self.im.getpalettemode()
                bands = len(palette_mode)
                source_palette = bytes(self.getpalette(None))
'''
assert s.count(old1) == 1
s = s.replace(old1, new1)
old2 = "            palette_bytes += source_palette[oldPosition * 3 : oldPosition * 3 + 3]\n"
assert s.count(old2) == 1
s = s.replace(old2, "            palette_bytes += source_palette[oldPosition * bands : oldPosition * bands + bands]\n")
old3 = '''        # Internally, we require 768 bytes for a palette.
        new_palette_bytes = palette_bytes + (768 - len(palette_bytes)) * b"\\x00"
        m_im.putpalette(new_palette_bytes)
        m_im.palette = ImagePalette.ImagePalette("RGB", palette=palette_bytes)
'''
assert s.count(old3) == 1, "old3"
s = s.replace(old3, '''        # Internally, we require 768 bytes for a palette.
        rgb = b"".join(palette_bytes[i : i + 3] for i in range(0, len(palette_bytes), bands))
        m_im.putpalette(rgb + (768 - len(rgb)) * b"\\x00")
        if bands == 4:
            m_im.im.putpalettealphas(bytes(palette_bytes[3::4]))
        m_im.palette = ImagePalette.ImagePalette(palette_mode, palette=palette_bytes)
''')
p.write_text(s)
