"""P4 public repro: pillow 2b061b68 (base 608ccd059438). Written from the public prompt only (E06).

Prompt claims: Image.open(..., formats=[...]) is used, then save()/show() raise
"TypeError: exceptions must be derived from Warning, not <class 'NoneType'>".
Inference: hopper.png is replaced by an in-memory PNG; show() is only called when no
external viewer is registered (so nothing is launched). Only observes; temp files in /tmp.
"""
import inspect, io, os, sys, tempfile, warnings
import PIL
from PIL import Image, ImageShow

WARN_TYPEERR = "exceptions must be derived from Warning"


def attempt(label, fn):
    with warnings.catch_warnings(record=True) as rec:
        warnings.simplefilter("always")
        try:
            out = fn()
            print(f"{label}=ok {out!r} warnings={[w.category.__name__ for w in rec]}")
            return ""
        except Exception as e:  # observe only
            print(f"{label}=raised {type(e).__name__}: {e}")
            return str(e)


def main():
    print("PIL_FILE", PIL.__file__, getattr(PIL, "__version__", "?"))
    print("OPEN_SIGNATURE_HAS_FORMATS", "formats" in inspect.signature(Image.open).parameters)
    buf = io.BytesIO()
    Image.new("RGB", (8, 8), (10, 20, 30)).save(buf, "PNG")
    png = buf.getvalue()
    msgs = [attempt("OPEN_FORMATS_JPEG", lambda: Image.open(io.BytesIO(png), formats=["JPEG"]).format),
            attempt("OPEN_FORMATS_PNG", lambda: Image.open(io.BytesIO(png), formats=["PNG"]).format)]
    im = Image.open(io.BytesIO(png))
    with tempfile.TemporaryDirectory() as d:
        msgs.append(attempt("SAVE_JPEG", lambda: im.save(os.path.join(d, "output.jpg"))))
    if ImageShow._viewers:
        print("SHOW=skipped registered viewers:", [type(v).__name__ for v in ImageShow._viewers])
    else:
        msgs.append(attempt("SHOW_NOARGS", lambda: im.show()))
        msgs.append(attempt("SHOW_COMMAND", lambda: im.show(command="true")))
    observed = any(WARN_TYPEERR in m for m in msgs)
    print(f"REPRO_OBSERVED={int(observed)}")
    if not observed:
        print("REPRO_REASON=no library call raised the Warning/NoneType TypeError; see OPEN_* lines for formats support")
    return 0


if __name__ == "__main__":
    sys.exit(main())
