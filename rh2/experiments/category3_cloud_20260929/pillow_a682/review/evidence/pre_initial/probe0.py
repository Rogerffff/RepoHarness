# Pre-judgment behavior probe (reviewer, before reading author materials)
import io, json, sys, warnings, traceback
sys.path.insert(0, "/testbed/Tests")
from PIL import Image, GifImagePlugin

def mk_example(t=(255, 255, 255)):
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0))
    im.info["transparency"] = t
    return im

def hopper_rgb():
    with Image.open("/testbed/Tests/images/hopper.ppm") as im:
        im.load()
        return im.copy()

def run(name, fn):
    rec = {"case": name}
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        try:
            out = fn()
            rec["ok"] = True
            if out is not None:
                rec.update(out)
        except Exception as e:
            rec["ok"] = False
            rec["exc"] = f"{type(e).__name__}: {e}"
    rec["warnings"] = [f"{x.category.__name__}: {x.message}" for x in w if not issubclass(x.category, (DeprecationWarning, ResourceWarning))]
    print(json.dumps(rec, ensure_ascii=False))

def save_reload(im, **kw):
    b = io.BytesIO()
    info_before = dict(im.info)
    im.save(b, "GIF", **kw)
    after = dict(im.info)
    b.seek(0)
    with Image.open(b) as r:
        r.load()
        res = {"reloaded_trns": r.info.get("transparency"), "n_frames": getattr(r, "n_frames", 1)}
        if "transparency" in r.info:
            res["trns_color"] = r.convert("RGB").getpixel((0, 0)) if False else r.getpalette()[3*r.info["transparency"]:3*r.info["transparency"]+3]
    res["info_changed"] = info_before != after
    return res

run("S0_example", lambda: save_reload(mk_example()))
run("S1_other_tuple_0_255_0", lambda: save_reload(mk_example((0, 255, 0))))
run("S1b_other_tuple_1_2_3", lambda: save_reload(mk_example((1, 2, 3))))
def gray256(t):
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, x, x))
    im.info["transparency"] = t
    return im
run("S2_gray256_1_2_3", lambda: save_reload(gray256((1, 2, 3))))
def hop():
    im = hopper_rgb()
    im.info["transparency"] = im.getpixel((0, 0))
    return im
run("S3_hopper_px00", lambda: save_reload(hop()))
run("S4_example_trns_in_palette_255_0_0", lambda: save_reload(mk_example((255, 0, 0))))
run("S4b_example_trns_in_palette_7_0_0", lambda: save_reload(mk_example((7, 0, 0))))
def small():
    im = Image.new("RGB", (1, 1)); im.info["transparency"] = (255, 0, 0); return im
run("S5_small_room", lambda: save_reload(small()))
run("S6_example_save_all_single", lambda: save_reload(mk_example(), save_all=True))
run("S7_example_save_all_2frames", lambda: save_reload(mk_example(), save_all=True, append_images=[mk_example()]))
run("S7b_example_2frames_disposal2", lambda: save_reload(mk_example(), save_all=True, append_images=[Image.new("RGB", (256, 1), (9, 9, 9))], disposal=2))
run("S8a_example_optimize_false", lambda: save_reload(mk_example(), optimize=False))
run("S8b_example_palette_kw", lambda: save_reload(mk_example(), palette=bytes(range(256)) + bytes(512)))
def pngrt():
    im = hopper_rgb()
    b = io.BytesIO(); im.save(b, "PNG", transparency=im.getpixel((0, 0))); b.seek(0)
    r = Image.open(b); r.load()
    return r
run("S9_png_roundtrip_hopper", lambda: dict(save_reload(pngrt()), png_info_trns=str(pngrt().info.get("transparency"))))
run("S11_kw_tuple_full", lambda: save_reload(mk_example(None) if False else Image.new("RGB", (4, 1)), transparency=(255, 255, 255)))
def ex_noinfo():
    im = mk_example(); del im.info["transparency"]; return im
run("S11b_kw_tuple_example_full", lambda: save_reload(ex_noinfo(), transparency=(255, 255, 255)))
run("S12_rgb_int_trns_5", lambda: save_reload(mk_example(5)))
def gd():
    im = Image.new("P", (4, 4)); im.putpixel((0, 0), 3); im.info["transparency"] = 3
    d = GifImagePlugin.getdata(im)
    gce = [x for x in d if isinstance(x, bytes) and x.startswith(b"!\xf9")]
    return {"gce": [x.hex() for x in gce]}
run("S13_legacy_getdata_info_trns", gd)
def c300():
    im = Image.new("RGB", (300, 1))
    for x in range(300):
        im.putpixel((x, 0), (x % 256, x // 256 * 100, 0))
    im.info["transparency"] = (255, 255, 255)
    return im
run("S14_300colors", lambda: save_reload(c300()))
def twice():
    im = mk_example()
    r1 = save_reload(im)
    r2 = save_reload(im)
    return {"first": r1, "second": r2, "info_after": str(im.info.get("transparency"))}
run("S15_save_twice", twice)
def rgba_tuple():
    im = Image.new("RGBA", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0, 255))
    im.info["transparency"] = (255, 255, 255)
    return im
run("S16_rgba_tuple", lambda: save_reload(rgba_tuple()))
def p_tuple():
    im = Image.new("P", (4, 1)); im.info["transparency"] = (255, 255, 255); return im
run("S17_P_tuple", lambda: save_reload(p_tuple()))
