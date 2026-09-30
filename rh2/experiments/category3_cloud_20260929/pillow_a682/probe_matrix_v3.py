"""私有行为矩阵（pillow__a682ceaf）：在候选代码上逐个场景保存 GIF，记录异常、警告、读回结果与副作用。

在容器内 /testbed 下运行：python probe_matrix.py <临时输出目录>
每个场景单独 try，互不影响；每行输出一个 JSON。只记录事实，对错由结论页按公开要求判定，不以 gold 为答案。
"""
import io
import json
import os
import sys
import traceback
import warnings

from PIL import GifImagePlugin, Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/probe"
os.makedirs(OUT, exist_ok=True)


def red_ramp():  # 题面示例的图：256x1，256 种互不相同的红色
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0))
    return im


def teal_256():  # 非示例：16x16，256 种互不相同的颜色 (0, i, 255 - i)
    im = Image.new("RGB", (16, 16))
    for i in range(256):
        im.putpixel((i % 16, i // 16), (0, i, 255 - i))
    return im


def colors_255():  # 255 种颜色，调色板留有空位
    im = Image.new("RGB", (255, 1))
    for x in range(255):
        im.putpixel((x, 0), (x, 0, 0))
    return im


def hopper_rgb():
    with Image.open("Tests/images/hopper.ppm") as im:
        return im.convert("RGB")


def describe_exc(exc):
    fr = traceback.extract_tb(exc.__traceback__)[-1]
    return f"{type(exc).__name__}: {exc} @ {os.path.basename(fr.filename)}:{fr.lineno} {fr.name}"


def save(label, im, extra=None, **kw):
    out = os.path.join(OUT, label + ".gif")
    rec = {"id": label}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            im.save(out, **kw)
            rec["exc"] = None
        except Exception as exc:  # noqa: BLE001
            rec["exc"] = describe_exc(exc)
    rec["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught]
    rec["src_info_transparency_after"] = repr(im.info.get("transparency", "<absent>"))
    if rec["exc"] is None:
        try:
            with Image.open(out) as re:
                re.load()
                rec["reloaded"] = {
                    "mode": re.mode, "size": list(re.size), "n_frames": getattr(re, "n_frames", 1),
                    "transparency": re.info.get("transparency", "<absent>"),
                    "version": re.info.get("version", b"").decode("latin-1"),
                }
                if extra:
                    rec.update(extra(re, im))
        except Exception as exc:  # noqa: BLE001
            rec["reload_exc"] = describe_exc(exc)
    print(json.dumps(rec, ensure_ascii=False), flush=True)
    return rec


def pixels_equal(re, src):
    a = re.convert("RGB")
    b = src.convert("RGB")
    diff = sum(1 for p, q in zip(a.getdata(), b.getdata()) if p != q)
    return {"pixels_differing_from_source": diff}


def trns_on_last_pixel(re, src):
    t = re.info.get("transparency")
    rgba = re.convert("RGBA")
    alphas = [rgba.getpixel((x, 0))[3] for x in range(re.width)]
    return {"trns_equals_index_of_pixel_255": t is not None and t == re.getpixel((255, 0)),
            "alpha_at_255": alphas[255], "min_alpha_others": min(alphas[:255])}


# S01 题面示例
a = red_ramp()
a.info["transparency"] = (255, 255, 255)
save("S01_example", a, pixels_equal)

# S02 题面示例 + save_all=True（只有一帧，回落单帧写入）
a = red_ramp()
a.info["transparency"] = (255, 255, 255)
save("S02_example_save_all", a, save_all=True)

# S03 hopper RGB，透明色取像素 (0, 0)（与公开测试 test_image_convert.py::test_trns_RGB 相同的输入）
b = hopper_rgb()
b.info["transparency"] = b.getpixel((0, 0))
save("S03_hopper_pixel00", b)

# S04 hopper RGB，另一个不在图中的颜色
b = hopper_rgb()
b.info["transparency"] = (1, 2, 3)
save("S04_hopper_123", b)

# S05 256 色的另一张图（形状、颜色都与示例不同），透明色不在图中
c = teal_256()
c.info["transparency"] = (255, 0, 0)
save("S05_teal256_absent", c)

# S06 示例图，但透明色是图中已有的颜色 (255, 0, 0)：调色板已满，颜色本来就在其中
d = red_ramp()
d.info["transparency"] = (255, 0, 0)
save("S06_example_present_color", d, trns_on_last_pixel)

# S07 1x1 图，元组可分配（公开测试 test_rgb_transparency 的单帧用例）
e = Image.new("RGB", (1, 1))
e.info["transparency"] = (255, 0, 0)
save("S07_1x1_allocatable", e)

# S08 255 色的图，透明色不在图中但调色板有空位
f = colors_255()
f.info["transparency"] = (0, 255, 0)
save("S08_255colors_free_slot", f)

# S09 用 save() 关键字传元组（R7，题面未约定）
save("S09_kwarg_tuple", red_ramp(), transparency=(255, 255, 255))

# S10 两帧（多帧路径）
g = red_ramp()
g.info["transparency"] = (255, 255, 255)
save("S10_two_frames", g, save_all=True, append_images=[Image.new("RGB", (256, 1))])

# S11 真实的带 tRNS 的 RGB PNG
with Image.open("Tests/images/rgb_trns.png") as h:
    h.load()
    save("S11_rgb_trns_png", h)

# S12 同一张图连续保存：先存 GIF，再存 GIF，再存 PNG（查副作用与顺序依赖）
k = red_ramp()
k.info["transparency"] = (255, 255, 255)
save("S12a_first_gif", k)
save("S12b_second_gif", k)
png = os.path.join(OUT, "S12c.png")
try:
    k.save(png)
    with Image.open(png) as p:
        print(json.dumps({"id": "S12c_then_png", "png_transparency": repr(p.info.get("transparency", "<absent>"))}),
              flush=True)
except Exception as exc:  # noqa: BLE001
    print(json.dumps({"id": "S12c_then_png", "exc": describe_exc(exc)}), flush=True)

# S13 旧接口 getdata：P 图 info 里有整数透明度，是否写出透明标志（G1 旁支）
try:
    im = Image.new("P", (4, 4), 1)
    im.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    im.info["transparency"] = 1
    data = b"".join(GifImagePlugin.getdata(im))
    gce = data.find(b"!\xf9\x04")
    flag = data[gce + 3] & 1 if gce >= 0 else None
    print(json.dumps({"id": "S13_getdata_info_int", "gce_present": gce >= 0, "transparent_flag": flag,
                      "transparent_index": data[gce + 6] if gce >= 0 else None}), flush=True)
except Exception as exc:  # noqa: BLE001
    print(json.dumps({"id": "S13_getdata_info_int", "exc": describe_exc(exc)}), flush=True)

# S14 非标准输入：RGB 图 info 里放整数透明度，且对应颜色 (0, 0, 0) 无法分配
m = teal_256()
m.info["transparency"] = 0
save("S14_rgb_int_transparency", m)

# S15 P 图带整数透明度的单帧保存（公开行为，对照）
n = Image.new("P", (4, 4), 1)
n.putpalette([0, 0, 0, 255, 0, 0, 0, 255, 0] + [0] * 759)
n.info["transparency"] = 1
save("S15_p_int_transparency", n)

# S16 写入 BytesIO（不经文件名；确认没有依赖文件路径的写法）
buf = io.BytesIO()
q = red_ramp()
q.info["transparency"] = (255, 255, 255)
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        q.save(buf, format="GIF")
    buf.seek(0)
    with Image.open(buf) as re:
        print(json.dumps({"id": "S16_bytesio", "transparency": re.info.get("transparency", "<absent>")}), flush=True)
except Exception as exc:  # noqa: BLE001
    print(json.dumps({"id": "S16_bytesio", "exc": describe_exc(exc)}), flush=True)

# ---- v2 新增 ----
# S17 多于 256 色的照片，加一块纯色 (0, 255, 0) 背景条，并以该颜色作透明色：颜色本来就能精确落进调色板
def hopper_band():
    im = hopper_rgb()
    im.paste((0, 255, 0), (0, 0, 128, 32))
    return im


def trns_on_band(re, src):
    t = re.info.get("transparency")
    rgba = re.convert("RGBA")
    n_transparent = sum(1 for px in rgba.getdata() if px[3] == 0)
    return {"trns_equals_index_of_pixel_00": t is not None and t == re.getpixel((0, 0)),
            "alpha_at_00": rgba.getpixel((0, 0))[3], "alpha_at_64_100": rgba.getpixel((64, 100))[3],
            "n_transparent_pixels": n_transparent,
            "src_colors": len(src.getcolors(1 << 24))}


s = hopper_band()
s.info["transparency"] = (0, 255, 0)
save("S17_hopper_band_present", s, trns_on_band)

# S18 同一张图，透明色取不在调色板里的颜色 (1, 2, 3)
s = hopper_band()
s.info["transparency"] = (1, 2, 3)
save("S18_hopper_band_absent", s)

# ---- v3 新增 ----
# S19 RGBA 图带元组 info["transparency"]（非标准表示：RGBA 用 alpha 通道表示透明），没有全透明像素
r = Image.new("RGBA", (256, 1))
for x in range(256):
    r.putpixel((x, 0), (x, 0, 0, 255))
r.info["transparency"] = (255, 255, 255)
save("S19_rgba_tuple_opaque", r)

# S20 同上，但有一个全透明像素（_normalize_mode 会用它的调色板索引覆盖元组）
r = Image.new("RGBA", (256, 1))
for x in range(256):
    r.putpixel((x, 0), (x, 0, 0, 0 if x == 0 else 255))
r.info["transparency"] = (255, 255, 255)
save("S20_rgba_tuple_with_alpha0", r)
