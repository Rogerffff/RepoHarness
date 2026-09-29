"""Apply constructed candidate edits on top of an already-applied gold/U11 tree (run in /testbed)."""
import sys
name = sys.argv[1]
p = "src/PIL/Image.py"
s = open(p).read()

def rep(old, new, count=1):
    global s
    assert s.count(old) == count, (name, old[:60], s.count(old))
    s = s.replace(old, new)

CONV = '        m_im = m_im.convert("L")\n'
TRNS = '        if "transparency" in self.info:\n            try:\n                m_im.info["transparency"] = dest_map.index(self.info["transparency"])\n'
RET_BLOCK = '                if "transparency" in m_im.info:\n                    del m_im.info["transparency"]\n\n        return m_im\n'

if name == "G_del":      # natural minimal fix: drop the transparency key only for the internal mapping convert
    rep(CONV, '        m_im.info.pop("transparency", None)\n' + CONV)
elif name == "G_cim":    # natural fix: convert the mapping image at C level, bypassing Python-level transparency handling
    rep(CONV, '        m_im = m_im._new(m_im.im.convert("L"))\n')
elif name == "HYB":      # coordinator's example: C1 path only when a transparency index is present, gold path otherwise
    rep('        m_im.palette = ImagePalette.ImagePalette(\n            palette_mode, palette=mapping_palette * bands\n        )\n',
        '        use_c1 = bands == 4 and "transparency" in self.info\n'
        '        map_mode, map_bands = ("RGB", 3) if use_c1 else (palette_mode, bands)\n'
        '        m_im.palette = ImagePalette.ImagePalette(\n            map_mode, palette=mapping_palette * map_bands\n        )\n')
    rep('        m_im.im.putpalette(palette_mode + ";L", m_im.palette.tobytes())\n',
        '        m_im.im.putpalette(map_mode + ";L", m_im.palette.tobytes())\n')
    rep('        m_im.putpalette(new_palette_bytes, palette_mode)\n',
        '        if use_c1:\n'
        '            rgb = b"".join(palette_bytes[i : i + 3] for i in range(0, len(palette_bytes), 4))\n'
        '            m_im.putpalette(rgb + (768 - len(rgb)) * b"\\x00")\n'
        '            m_im.im.putpalettealphas(bytes(palette_bytes[3::4]))\n'
        '        else:\n'
        '            m_im.putpalette(new_palette_bytes, palette_mode)\n')
elif name in ("A0K", "A0D"):  # coordinator's example: write alpha 0 into the transparency entry (K keeps / D drops the info key)
    rep(CONV, '        m_im.info.pop("transparency", None)\n' + CONV)
    extra = ('        if bands == 4 and "transparency" in m_im.info:\n'
             '            t = m_im.info["transparency"]\n'
             '            pb = bytearray(palette_bytes)\n'
             '            if t * 4 + 3 < len(pb):\n'
             '                pb[t * 4 + 3] = 0\n'
             '            m_im.putpalette(bytes(pb) + ((256 * 4) - len(pb)) * b"\\x00", "RGBA")\n'
             '            m_im.palette = ImagePalette.ImagePalette("RGBA", palette=bytes(pb))\n')
    if name == "A0D":
        extra += '            del m_im.info["transparency"]\n'
    rep(RET_BLOCK, '                if "transparency" in m_im.info:\n                    del m_im.info["transparency"]\n\n' + extra + '        return m_im\n')
elif name == "FB":       # defensive fallback: on ValueError redo with an explicit RGB source palette (base-like result)
    rep(CONV, '        try:\n            m_im = m_im.convert("L")\n        except ValueError:\n'
              '            return self.remap_palette(dest_map, self.im.getpalette("RGB")[:768])\n')
elif name == "DROP":     # avoid the crash by dropping transparency for RGBA palettes
    rep(CONV, '        m_im.info.pop("transparency", None)\n' + CONV)
    rep(TRNS, TRNS.replace('if "transparency" in self.info:', 'if "transparency" in self.info and bands == 3:'))
elif name == "G_gif":    # (on top of U11) also make GifImagePlugin keep an RGB-mode palette for the RGB bytes it writes
    g = "src/PIL/GifImagePlugin.py"
    t = open(g).read()
    old = "    im.palette.palette = source_palette\n    return im\n"
    assert t.count(old) == 1
    t = t.replace(old, "    if palette:\n        im.palette = ImagePalette.ImagePalette(\"RGB\", palette=source_palette)\n"
                       "    else:\n        im.palette.palette = source_palette\n    return im\n")
    open(g, "w").write(t)
elif name == "G_small":  # size-dependent partial fix: mapping palette only as long as the source palette
    rep('        m_im.palette = ImagePalette.ImagePalette(\n            palette_mode, palette=mapping_palette * bands\n        )\n',
        '        n_src = max(1, min(256, len(source_palette) // bands))\n'
        '        m_im.palette = ImagePalette.ImagePalette(\n            palette_mode, palette=mapping_palette[:n_src] * bands\n        )\n')
else:
    raise SystemExit("unknown " + name)
open(p, "w").write(s)
print("edited", name)
