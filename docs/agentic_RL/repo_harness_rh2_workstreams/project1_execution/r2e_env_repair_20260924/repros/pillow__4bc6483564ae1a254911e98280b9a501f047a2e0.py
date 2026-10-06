"""P4 public repro: pillow 4bc64835 (base a6efaa1ae1d0). Written from the public prompt only (E06).

Prompt: ImageOps.invert on a mode "1" image raises "OSError: not supported for this image mode".
The prompt example is used verbatim (in-memory); observe only.
"""
import sys
import PIL
from PIL import Image, ImageOps


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    binary_image = Image.new("1", (128, 128), color=1)
    try:
        inverted = ImageOps.invert(binary_image)
    except Exception as e:  # observe only
        print(f"INVERT=raised {type(e).__name__}: {e}")
        observed = isinstance(e, OSError)
        print(f"REPRO_OBSERVED={int(observed)}")
        if not observed:
            print("REPRO_REASON=invert failed, but not with OSError")
        return 0
    print("INVERT=ok", inverted.mode, inverted.getpixel((0, 0)))
    print("REPRO_OBSERVED=0")
    print("REPRO_REASON=invert of mode 1 succeeded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
