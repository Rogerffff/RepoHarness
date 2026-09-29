"""私有对照：GIF 保存的 palette= 分支（_normalize_palette 调 remap_palette 不传 source）。
比较 base / gold / 替代解：规范化后的 Python 调色板 mode 与字节长度、C 层调色板、保存读回的逐像素颜色、元组背景色。"""
import io
import json

from PIL import GifImagePlugin, Image

COLORS = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (10, 20, 30)]
ALPHAS = [255, 128, 255, 0]
NEW_ORDER = [(0, 0, 255), (255, 0, 0), (10, 20, 30), (0, 255, 0)]  # 调用者给的 palette= 是同一组颜色换序


def make(kind):
    im = Image.new("P", (4, 1))
    for x in range(4):
        im.putpixel((x, 0), x)
    if kind == "rgba":
        flat = [v for c, a in zip(COLORS, ALPHAS) for v in (*c, a)]
        im.putpalette(flat + [0] * (1024 - len(flat)), "RGBA")
    else:
        flat = [v for c in COLORS for v in c]
        im.putpalette(flat + [0] * (768 - len(flat)))
    return im


def rgb_pixels(im):
    return [im.convert("RGB").getpixel((x, 0)) for x in range(im.size[0])]


def attempt(fn):
    try:
        return fn()
    except Exception as e:  # noqa: BLE001
        return {"exception": f"{type(e).__name__}: {str(e)[:160]}"}


out = {}
new_pal = [v for c in NEW_ORDER for v in c]
for kind in ("rgba", "rgb"):
    im = make(kind)
    expect = [c for c in COLORS]

    def norm():
        n = GifImagePlugin._normalize_palette(im.copy(), new_pal, {})
        pb = bytes(n.palette.palette)
        return {"py_palette_mode": n.palette.mode, "py_palette_len": len(pb), "py_palette_head": list(pb[:12]),
                "c_palette_mode": n.im.getpalettemode(), "indices": [n.getpixel((x, 0)) for x in range(4)],
                "rgb_render_ok": rgb_pixels(n) == expect}

    def save_reload(**kw):
        buf = io.BytesIO()
        im.save(buf, "GIF", palette=new_pal, **kw)
        buf.seek(0)
        r = Image.open(buf)
        r.load()
        res = {"reloaded_rgb_ok": rgb_pixels(r) == expect, "reloaded_rgb": rgb_pixels(r)}
        if "background" in kw:
            bi = r.info.get("background")
            pal = r.getpalette()
            res["background_index"] = bi
            res["background_color"] = tuple(pal[bi * 3: bi * 3 + 3]) if bi is not None else None
            res["background_ok"] = res["background_color"] == kw["background"]
        return res

    def plain_save():
        buf = io.BytesIO()
        im.save(buf, "GIF")
        buf.seek(0)
        r = Image.open(buf)
        r.load()
        return {"reloaded_rgb_ok": rgb_pixels(r) == expect}

    out[kind] = {"normalize": attempt(norm), "save_palette": attempt(save_reload),
                 "save_palette_bg_tuple": attempt(lambda: save_reload(background=(0, 255, 0))),
                 "save_plain": attempt(plain_save)}
print(json.dumps(out, ensure_ascii=False, indent=1))
