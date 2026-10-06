"""P4 public repro: pillow 3a61c9e9 (base 355820742bc2). Written from the public prompt only (E06).

Prompt: for a 'P' image with an RGBA palette, remap_palette(identity) yields a palette
different from the original. The prompt example is used verbatim (in-memory); observe only.
"""
import sys
import PIL
from PIL import Image


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    im = Image.new("P", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), x)
    im.putpalette(list(range(256)) * 4, "RGBA")
    try:
        remapped = im.remap_palette(list(range(256)))
    except Exception as e:  # observe only
        print(f"REMAP=raised {type(e).__name__}: {e}")
        print("REPRO_OBSERVED=1")
        return 0
    a, b = im.palette.palette, remapped.palette.palette
    print("PALETTE_MODES", im.palette.mode, remapped.palette.mode)
    print("PALETTE_LENGTHS", len(a), len(b))
    print("PALETTES_EQUAL", a == b)
    print("FIRST_8_BYTES", bytes(a[:8]), bytes(b[:8]))
    observed = a != b
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=identity remap kept the RGBA palette")
    return 0


if __name__ == "__main__":
    sys.exit(main())
