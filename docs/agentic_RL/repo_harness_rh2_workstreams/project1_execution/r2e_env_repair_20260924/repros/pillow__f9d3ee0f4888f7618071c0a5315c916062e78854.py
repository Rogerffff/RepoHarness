"""P4 public repro: pillow f9d3ee0f (base df4bb3460000). Written from the public prompt only (E06).

Prompt: ImageOps.pad truncates the paste offset with int(); for a 1x1 white "1" image,
pad to (4, 1) should set pixel (2, 0) and pad to (1, 4) should set pixel (0, 2).
The prompt example is used verbatim (in-memory); observe only.
"""
import sys
import PIL
from PIL import Image, ImageOps


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    im = Image.new("1", (1, 1), 1)
    wide = ImageOps.pad(im, (4, 1))
    tall = ImageOps.pad(im, (1, 4))
    row = [wide.getpixel((x, 0)) for x in range(4)]
    col = [tall.getpixel((0, y)) for y in range(4)]
    print("PAD_4x1_ROW", row, "(prompt expects index 2 == 1)")
    print("PAD_1x4_COL", col, "(prompt expects index 2 == 1)")
    observed = not (row[2] and col[2])
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=pixels already placed at the rounded (centered) offset")
    return 0


if __name__ == "__main__":
    sys.exit(main())
