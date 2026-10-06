"""P4 public repro: pillow 2d01f7d0 (base 5db0969f6f98). Written from the public prompt only (E06).

Prompt: saving a '1' or 'L' TIFF with tiffinfo={262: 0} (PhotometricInterpretation=0)
reloads with tag 262 == 1 instead of 0. In-memory images; temp files in /tmp; observe only.
"""
import os, sys, tempfile
import PIL
from PIL import Image


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    got = {}
    with tempfile.TemporaryDirectory() as d:
        for mode in ("1", "L"):
            path = os.path.join(d, f"temp_{mode}.tif")
            try:
                Image.new(mode, (100, 100)).save(path, tiffinfo={262: 0})
                with Image.open(path) as reloaded:
                    got[mode] = reloaded.tag_v2.get(262)
            except Exception as e:  # observe only
                got[mode] = f"raised {type(e).__name__}: {e}"
            print(f"MODE_{mode}_TAG262={got[mode]!r} (expected 0)")
    observed = any(v != 0 for v in got.values())
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=tag 262 round-trips as 0 for both modes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
