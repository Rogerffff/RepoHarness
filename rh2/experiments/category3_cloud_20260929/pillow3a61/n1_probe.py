import io, json, traceback
from PIL import Image
res = {}
def run(name, fn):
    try:
        res[name] = fn()
    except Exception as e:
        res[name] = "EXC %s: %s" % (type(e).__name__, e)

def stmt_example(trns):
    im = Image.new("P", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), x)
    im.putpalette(list(range(256)) * 4, "RGBA")
    if trns is not None:
        im.info["transparency"] = trns
    before = bytes(im.palette.palette)
    rgba_before = im.convert("RGBA").tobytes() if trns is None else None
    r = im.remap_palette(list(range(256)))
    return {"same_palette": bytes(r.palette.palette) == before,
            "py_mode": r.palette.mode, "c_mode": r.im.getpalettemode(),
            "trns": r.info.get("transparency"),
            "rgba_equal": (r.convert("RGBA").tobytes() == rgba_before) if rgba_before else None}

def small(trns, dest=(0, 1, 2, 3)):
    im = Image.new("P", (4, 1)); im.putdata([0, 1, 2, 3])
    im.putpalette(bytes([255,0,0,255, 0,255,0,128, 0,0,255,255, 10,20,30,0]), "RGBA")
    if trns is not None:
        im.info["transparency"] = trns
    r = im.remap_palette(list(dest))
    return {"data": list(r.getdata()), "pal16": list(r.getpalette("RGBA")[:16]), "trns": r.info.get("transparency")}

def gif_rgba_mode(palette_kind):
    im = Image.new("RGBA", (4, 1))
    im.putdata([(255,0,0,255), (0,255,0,255), (0,0,255,255), (10,20,30,255)])
    pal = [255,0,0, 0,255,0, 0,0,255, 10,20,30]
    out = io.BytesIO()
    if palette_kind == "none":
        im.save(out, "GIF")
    else:
        im.save(out, "GIF", palette=bytes(pal))
    out.seek(0)
    with Image.open(out) as re_:
        return {"rgb": list(re_.convert("RGB").getdata())}

def gif_hopper_rgba(palette_kind):
    with Image.open("Tests/images/hopper.png") as h:
        im = h.convert("RGBA")
    out = io.BytesIO()
    if palette_kind == "none":
        im.save(out, "GIF")
    else:
        pal = im.convert("P", palette=Image.Palette.ADAPTIVE).convert("RGB").getpalette() if False else None
        q = im.convert("RGB").quantize(256)
        im.save(out, "GIF", palette=q.getpalette())
    out.seek(0)
    with Image.open(out) as re_:
        return {"size": re_.size, "mode": re_.mode}

def quantize_then_trns():
    with Image.open("Tests/images/hopper.png") as h:
        im = h.convert("RGBA")
    q = im.quantize(16)
    q.info["transparency"] = 0
    r = q.remap_palette(list(range(16)))
    return {"c_mode": r.im.getpalettemode(), "trns": r.info.get("transparency")}

for t in (None, 0, 3):
    run("stmt_trns=%s" % t, lambda t=t: stmt_example(t))
    run("small_trns=%s" % t, lambda t=t: small(t))
run("small_trns=3_swap", lambda: small(3, (1, 0, 2, 3)))
run("gif_rgba_mode_none", lambda: gif_rgba_mode("none"))
run("gif_rgba_mode_pal", lambda: gif_rgba_mode("pal"))
run("gif_hopper_rgba_none", lambda: gif_hopper_rgba("none"))
run("gif_hopper_rgba_pal", lambda: gif_hopper_rgba("pal"))
run("quantize_then_trns", quantize_then_trns)
print(json.dumps(res, indent=1))
