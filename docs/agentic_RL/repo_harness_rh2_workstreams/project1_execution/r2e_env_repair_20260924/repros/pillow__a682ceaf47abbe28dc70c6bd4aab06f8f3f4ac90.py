"""P4 public repro: pillow a682ceaf (base 7a1e28404d69). Written from the public prompt only (E06).

Prompt: saving an RGB image as GIF with info["transparency"] = (255, 255, 255) raises
"TypeError: int() argument must be ... not 'tuple'". Saved to BytesIO instead of temp.gif.
"""
import io, sys
import PIL
from PIL import Image


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0))
    im.info["transparency"] = (255, 255, 255)
    buf = io.BytesIO()
    try:
        im.save(buf, format="GIF")
    except Exception as e:  # observe only
        print(f"SAVE_GIF=raised {type(e).__name__}: {e}")
        observed = isinstance(e, TypeError)
        print(f"REPRO_OBSERVED={int(observed)}")
        if not observed:
            print("REPRO_REASON=save failed, but not with TypeError")
        return 0
    buf.seek(0)
    with Image.open(buf) as reloaded:
        print("SAVE_GIF=ok reloaded transparency:", reloaded.info.get("transparency"))
    print("REPRO_OBSERVED=0")
    print("REPRO_REASON=GIF saved without exception")
    return 0


if __name__ == "__main__":
    sys.exit(main())
