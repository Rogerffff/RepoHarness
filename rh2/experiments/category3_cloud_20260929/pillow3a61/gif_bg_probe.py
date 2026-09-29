import io, json
from PIL import Image
res = {}
def mk():
    im = Image.new("P", (4, 1)); im.putdata([0, 1, 2, 3])
    im.putpalette(bytes([255,0,0,255, 0,255,0,128, 0,0,255,255, 10,20,30,0]), "RGBA")
    return im
def gif_struct(b):
    flags = b[10]; gct = 3 * (2 ** ((flags & 7) + 1)) if flags & 0x80 else 0
    return {"len": len(b), "gct_entries": gct // 3, "bg_index": b[11], "next_byte_after_gct": hex(b[13 + gct])}
def case(name, palette, bg):
    im = mk(); out = io.BytesIO()
    try:
        im.save(out, "GIF", palette=bytes(palette), background=bg)
    except Exception as e:
        res[name] = "EXC %s: %s" % (type(e).__name__, e); return
    b = out.getvalue(); s = gif_struct(b)
    with Image.open(io.BytesIO(b)) as r:
        pal = r.getpalette()[:3 * s["gct_entries"]]
        bi = r.info.get("background")
        s["bg_color"] = tuple(pal[3 * bi: 3 * bi + 3]) if bi is not None and 3 * bi + 3 <= len(pal) else None
        s["pixels"] = list(r.convert("RGB").getdata())
    res[name] = s
swap = [0,255,0, 255,0,0, 0,0,255, 10,20,30]      # 作者的换序
rev = [10,20,30, 0,0,255, 0,255,0, 255,0,0]        # 反转
case("R3_swap_bg_tuple", swap, (0, 255, 0))
case("R4_rev_bg_tuple", rev, (0, 255, 0))
case("swap_bg_int", swap, 1)
case("orig_order_bg_tuple", [255,0,0, 0,255,0, 0,0,255, 10,20,30], (0, 255, 0))
# R5：256 项 palette=，像素用到索引 255，元组背景为新颜色
im = Image.new("P", (5, 1)); im.putdata([0, 1, 2, 3, 255])
pal4 = []
for i in range(256): pal4 += [i, 0, 255 - i, 255]
pal4[255*4:255*4+4] = [255, 0, 249, 255]
im.putpalette(bytes(pal4), "RGBA")
p3 = []
for i in range(256): p3 += pal4[i*4:i*4+3]
out = io.BytesIO()
try:
    im.save(out, "GIF", palette=bytes(p3), background=(0, 255, 0))
    with Image.open(io.BytesIO(out.getvalue())) as r:
        res["R5_full256_bg_new"] = {"px4": r.convert("RGB").getpixel((4, 0)), "expected": (255, 0, 249), **{k: v for k, v in gif_struct(out.getvalue()).items() if k != "len"}}
except Exception as e:
    res["R5_full256_bg_new"] = "EXC %s: %s" % (type(e).__name__, e)
print(json.dumps(res))
