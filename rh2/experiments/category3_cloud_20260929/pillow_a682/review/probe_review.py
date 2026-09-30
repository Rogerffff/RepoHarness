"""复核者行为探针（pillow__a682ceaf 独立复核）。在容器内 /testbed 下运行：python probe_review.py <输出目录>

每个场景单独 try，互不影响；每行输出一个 JSON，只记事实，对错由 review.md 按公开要求判定。
场景编号 P01–P16，含义见 review.md §3。探针在同一进程里按固定顺序执行（P09、P13 专门查顺序与全局副作用）。
"""
import io
import json
import os
import sys
import traceback
import warnings

from PIL import GifImagePlugin, Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/probe_review"
os.makedirs(OUT, exist_ok=True)
warnings.simplefilter("always")  # 基线：每条警告都显示；若候选装了全局过滤器，会排在它前面


def red_ramp(t=None):
    im = Image.new("RGB", (256, 1))
    for x in range(256):
        im.putpixel((x, 0), (x, 0, 0))
    if t is not None:
        im.info["transparency"] = t
    return im


def hopper_rgb():
    with Image.open("Tests/images/hopper.ppm") as im:
        return im.convert("RGB")


def hopper_band():
    im = hopper_rgb()
    im.paste((0, 255, 0), (0, 0, 128, 32))
    return im


def exc_str(exc):
    fr = traceback.extract_tb(exc.__traceback__)[-1]
    return f"{type(exc).__name__}: {exc} @ {os.path.basename(fr.filename)}:{fr.lineno}"


def emit(rec):
    print(json.dumps(rec, ensure_ascii=False, default=repr), flush=True)


def save(label, im, check=None, **kw):
    out = os.path.join(OUT, label + ".gif")
    rec = {"id": label}
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            im.save(out, **kw)
            rec["exc"] = None
        except Exception as exc:  # noqa: BLE001
            rec["exc"] = exc_str(exc)
    rec["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught
                       if not issubclass(w.category, (DeprecationWarning, ResourceWarning))]
    rec["caller_info_trns_after"] = im.info.get("transparency", "<absent>")
    if rec["exc"] is None:
        try:
            with Image.open(out) as re:
                re.load()
                rec["reloaded_trns"] = re.info.get("transparency", "<absent>")
                rec["version"] = re.info.get("version", b"").decode("latin-1")
                rec["n_frames"] = getattr(re, "n_frames", 1)
                if check:
                    rec.update(check(re))
        except Exception as exc:  # noqa: BLE001
            rec["reload_exc"] = exc_str(exc)
    emit(rec)
    return rec


def trns_is_pixel(xy):
    def check(re):
        t = re.info.get("transparency")
        return {"trns_equals_index_of_pixel": t is not None and t == re.getpixel(xy)}
    return check


# P01 题面示例
im = red_ramp((255, 255, 255))
save("P01_example", im)

# P02 (a)：hopper＋像素 (0,0) 的颜色
im = hopper_rgb()
im.info["transparency"] = im.getpixel((0, 0))
save("P02_hopper_px00", im)

# P03 (b)：示例图，透明色 (255,0,0) 已在满调色板里；看调用者 info 是否被改
im = red_ramp((255, 0, 0))
save("P03_ramp_present", im, trns_is_pixel((255, 0)))

# P04 (b′)：hopper＋纯色条，透明色为纯色
im = hopper_band()
im.info["transparency"] = (0, 255, 0)
save("P04_band_present", im, trns_is_pixel((0, 0)))

# P05 示例 save_all=True，只有一帧
save("P05_example_save_all_single", red_ramp((255, 255, 255)), save_all=True)

# P06 示例两帧完全相同（合并为一帧后回落单帧写入）
save("P06_example_two_identical_frames", red_ramp((255, 255, 255)), save_all=True,
     append_images=[red_ramp((255, 255, 255))])

# P07 两帧不同（base 本来就能保存；看警告是否保留）
save("P07_two_distinct_frames", red_ramp((255, 255, 255)), save_all=True,
     append_images=[Image.new("RGB", (256, 1), (0, 0, 255))])

# P08 透明色能用的图先存 GIF 再存 PNG：PNG 里的透明色是否仍是原来的颜色
im = red_ramp((255, 0, 0))
rec = {"id": "P08_kept_then_png"}
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        im.save(os.path.join(OUT, "P08.gif"))
    rec["caller_info_trns_after_gif"] = im.info.get("transparency", "<absent>")
    im.save(os.path.join(OUT, "P08.png"))
    with Image.open(os.path.join(OUT, "P08.png")) as p:
        rec["png_trns"] = p.info.get("transparency", "<absent>")
except Exception as exc:  # noqa: BLE001
    rec["exc"] = exc_str(exc)
emit(rec)

# P09 顺序：P01 之后，另一张调色板有空位的 1x1 图用同一颜色 (255,255,255)，透明度应保留
im = Image.new("RGB", (1, 1))
im.info["transparency"] = (255, 255, 255)
save("P09_same_colour_small_image_after_P01", im)

# P10 同一张示例图连续保存两次：第二次是否仍有警告、仍不抛异常
im = red_ramp((255, 255, 255))
save("P10a_example_first", im)
save("P10b_example_second", im)

# P11 关键字传元组（题面未要求，只登记）
save("P11_kwarg_tuple_full", red_ramp(), transparency=(255, 255, 255))
save("P11b_kwarg_tuple_present", red_ramp(), transparency=(255, 0, 0), check=trns_is_pixel((255, 0)))

# P12 旧接口 getdata：P 图 info 里有整数透明度（题面未要求，只登记）
rec = {"id": "P12_getdata_info_int"}
try:
    g = Image.new("P", (4, 4), 1)
    g.putpalette([0, 0, 0, 255, 0, 0] + [0] * 762)
    g.info["transparency"] = 1
    data = b"".join(GifImagePlugin.getdata(g))
    pos = data.find(b"!\xf9\x04")
    rec["gce_transparent_flag"] = (data[pos + 3] & 1) if pos >= 0 else None
except Exception as exc:  # noqa: BLE001
    rec["exc"] = exc_str(exc)
emit(rec)

# P13 全局副作用：先在任何 catch_warnings 之外正常保存一次示例（像普通用户代码那样），
# 再看 Image.convert 的公开警告（test_trns_RGB 的同一输入）还在不在
rec = {"id": "P13_convert_warning_after_plain_gif_save"}
try:
    try:
        red_ramp((255, 255, 255)).save(os.path.join(OUT, "P13.gif"))
        rec["plain_save_exc"] = None
    except Exception as exc:  # noqa: BLE001
        rec["plain_save_exc"] = exc_str(exc)
    h = hopper_rgb()
    h.info["transparency"] = h.getpixel((0, 0))
    with warnings.catch_warnings(record=True) as caught:  # 不重设过滤器：要看保存代码有没有留下全局过滤器
        p = h.convert("P", palette=Image.Palette.ADAPTIVE)
    rec["warnings"] = [f"{w.category.__name__}: {w.message}" for w in caught]
    rec["p_has_trns"] = "transparency" in p.info
    rec["n_filters_ignore_allocate"] = sum(
        1 for f in warnings.filters if f[0] == "ignore" and f[1] is not None and "allocate" in f[1].pattern)
except Exception as exc:  # noqa: BLE001
    rec["exc"] = exc_str(exc)
emit(rec)

# P14 RGBA 图带元组、256 色全不透明（非标准表示，只登记 gold 的边界）
r = Image.new("RGBA", (256, 1))
for x in range(256):
    r.putpixel((x, 0), (x, 0, 0, 255))
r.info["transparency"] = (255, 255, 255)
save("P14_rgba_tuple_opaque256", r)

# P15 PNG 读回的 RGB 图（tRNS 为元组，透明色分配不到）
rec_src = hopper_rgb()
buf = io.BytesIO()
rec_src.save(buf, "PNG", transparency=rec_src.getpixel((0, 0)))
buf.seek(0)
with Image.open(buf) as png_im:
    png_im.load()
    save("P15_png_roundtrip_hopper", png_im)

# P16 灰阶 256 色、另一个颜色（非示例的“正好 256 色”实例）
g = Image.new("RGB", (16, 16))
for i in range(256):
    g.putpixel((i % 16, i // 16), (i, i, i))
g.info["transparency"] = (1, 2, 3)
save("P16_gray256_absent", g)
