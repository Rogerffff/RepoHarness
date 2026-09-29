"""P4 public repro: pillow 3ac9396e (base 48e4e0722e6a, Pillow 3.1 dev, package dir /testbed/PIL).

Written from the public prompt only (E06). Prompt: saving a TIFF whose tiffinfo holds
tag 41988 = IFDRational(0, 0) raises "struct.error: required argument is not an integer".
Inference: hopper.png is replaced by an in-memory RGB image; temp file in /tmp; observe only.
"""
import os, struct, sys, tempfile
import PIL
from PIL import Image, TiffImagePlugin


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "PILLOW_VERSION", getattr(PIL, "__version__", "?")))
    im = Image.new("RGB", (16, 16), (200, 100, 50))
    info = TiffImagePlugin.ImageFileDirectory_v2()
    info[41988] = TiffImagePlugin.IFDRational(0, 0)
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "temp.tiff")
        try:
            im.save(path, tiffinfo=info, compression="raw")
        except Exception as e:  # observe only
            print(f"SAVE=raised {type(e).__name__}: {e}")
            observed = isinstance(e, struct.error) or "not an integer" in str(e)
            print(f"REPRO_OBSERVED={int(observed)}")
            if not observed:
                print("REPRO_REASON=save failed, but not with the struct.error from the prompt")
            return 0
        print("SAVE=ok")
        reloaded = Image.open(path)
        value = reloaded.tag_v2[41988]
        r = value[0] if isinstance(value, tuple) else value
        print("RELOADED_41988", repr(value), getattr(r, "numerator", "?"), getattr(r, "denominator", "?"))
    print("REPRO_OBSERVED=0")
    print("REPRO_REASON=save succeeded and the tag reloaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
