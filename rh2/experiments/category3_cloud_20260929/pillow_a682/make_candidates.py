"""按精确文本替换，从 base 的 src/PIL/GifImagePlugin.py 生成本题的私有候选补丁（pillow__a682ceaf）。

每个候选是一组 (旧文本, 新文本) 替换，旧文本必须在 base 文件里恰好出现一次；
补丁写成 git apply 可用的 unified diff（a/ b/ 前缀）。gold 不在这里生成，直接取自 validation bundle。

用法：python make_candidates.py <base 的 GifImagePlugin.py> <输出目录> [base 的 Image.py]
候选的含义、预期与违反的公开要求见结论页 result.md §3。
"""
import difflib
import hashlib
import sys
from pathlib import Path

REL = "src/PIL/GifImagePlugin.py"

# --- 常用锚点（均取自 base 7a1e28404） ---
LH_LOOKUP = """        if "transparency" in im.encoderinfo:
            transparency = im.encoderinfo["transparency"]
        else:
            transparency = im.info["transparency"]
        transparency = int(transparency)
    except (KeyError, ValueError):
        pass
"""
GOLD_LOOKUP = """        transparency = int(im.encoderinfo["transparency"])
    except (KeyError, ValueError):
        pass
"""
SF_HEAD = """    im_out = _normalize_mode(im)
    for k, v in im_out.info.items():
        im.encoderinfo.setdefault(k, v)
"""
SF_LOCAL_HEADER = """    _write_local_header(fp, im, (0, 0), flags)
"""
NM_CONVERT = """        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
"""
IMPORTS = """import itertools
import math
import os
import subprocess
"""
SAVE_SINGLE = """        _write_single_frame(im, fp, palette)
"""

CANDIDATES = {
    # ---------- 合理实现（与 gold 不同的写法） ----------
    # 局部图像头对“不能换算成调色板索引的值”宽容：多捕获 TypeError，保留 info 回退
    "alt_typeerror": [(LH_LOOKUP, LH_LOOKUP.replace(
        "    except (KeyError, ValueError):\n",
        "    except (KeyError, TypeError, ValueError):\n"
        "        # e.g. an RGB tuple that could not be turned into a palette index\n"))],
    # 单帧写入以“归一化后仍存在的透明度”为准：归一化丢掉透明度时，用去掉该键的副本写局部图像头（不改调用者的图）
    "alt_frame": [(SF_LOCAL_HEADER,
        "    header_im = im\n"
        "    if (\n"
        "        \"transparency\" not in im.encoderinfo\n"
        "        and \"transparency\" in im.info\n"
        "        and \"transparency\" not in im_out.info\n"
        "    ):\n"
        "        # the transparency could not be kept when normalizing the mode\n"
        "        header_im = im.copy()\n"
        "        del header_im.info[\"transparency\"]\n"
        "        header_im.encoderinfo = im.encoderinfo\n"
        "    _write_local_header(fp, header_im, (0, 0), flags)\n")],
    # 只接受整数类索引（numbers.Integral），其它类型（元组等）视为无透明度；保留 info 回退
    "alt_integral": [
        (IMPORTS, IMPORTS + "import numbers\n"),
        (LH_LOOKUP, LH_LOOKUP.replace(
            "        transparency = int(transparency)\n",
            "        if not isinstance(transparency, numbers.Integral):\n"
            "            # only a palette index can be written to the GIF\n"
            "            raise ValueError(\"transparency is not a palette index\")\n"
            "        transparency = int(transparency)\n"))],

    # 静默版（查误拒用）：在 GIF 插件里先拿掉元组、转换后自己按 getcolor 分配，分配不到就不用透明度；
    # 与 gold 的唯一可见差别是不再发出 convert 的 UserWarning
    "q_prestrip": [
        (NM_CONVERT, """        trns = im.info.get("transparency")
        if isinstance(trns, tuple):
            im = im.copy()
            del im.info["transparency"]
        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
        if isinstance(trns, tuple):
            try:
                im.info["transparency"] = im.palette.getcolor(trns, im)
            except ValueError:
                pass  # no palette entry for the transparent colour: save without it
"""),
        (LH_LOOKUP, GOLD_LOOKUP)],
    # 静默分配、但自己发一条措辞不同的 UserWarning（查 pytest.warns 是否绑定 convert 的具体文案）
    "alt_prestrip_warn": [
        (IMPORTS, IMPORTS + "import warnings\n"),
        (NM_CONVERT, """        trns = im.info.get("transparency")
        if isinstance(trns, tuple):
            im = im.copy()
            del im.info["transparency"]
        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
        if isinstance(trns, tuple):
            try:
                im.info["transparency"] = im.palette.getcolor(trns, im)
            except ValueError:
                warnings.warn("The transparent colour could not be kept, saving without transparency")
"""),
        (LH_LOOKUP, GOLD_LOOKUP)],
    # ---------- 退化与错误候选 ----------
    # 关掉检查：局部图像头永远不写透明度（退化方向：关掉检查、提前返回）
    "deg_off": [(LH_LOOKUP, """        raise KeyError("transparency")  # never write a transparent colour
    except (KeyError, ValueError):
        pass
""")],
    # 示例字面值：只把 (255, 255, 255) 当作不可用的透明色（与输入无关的硬编码）
    "w_literal": [(LH_LOOKUP, LH_LOOKUP.replace(
        "        transparency = int(transparency)\n",
        "        if transparency == (255, 255, 255):\n"
        "            # white cannot be used as the transparent colour here\n"
        "            raise KeyError(\"transparency\")\n"
        "        transparency = int(transparency)\n"))],
    # 阈值：只在原图恰好用满 256 色时丢弃元组（getcolors(256) 对多于 256 色的图返回 None，于是照旧抛 TypeError）
    "w_count256": [(LH_LOOKUP, LH_LOOKUP.replace(
        "            transparency = im.info[\"transparency\"]\n",
        "            transparency = im.info[\"transparency\"]\n"
        "            colors = im.getcolors(256)\n"
        "            if isinstance(transparency, tuple) and colors and len(colors) == 256:\n"
        "                # the image already uses all 256 palette entries,\n"
        "                # so there is no room for the transparent colour\n"
        "                raise KeyError(\"transparency\")\n"))],
    # 过度丢弃：调色板 256 项都被用到就丢弃元组透明度，即使该颜色本来就在调色板里（配合 gold 的局部头改动）
    "w_drop_full": [
        (SF_HEAD, """    im_out = _normalize_mode(im)
    if isinstance(im.info.get("transparency"), tuple) and len(im_out.getcolors(256) or ()) == 256:
        # every palette entry is in use, so there is no entry left for the transparent colour
        im_out.info.pop("transparency", None)
    for k, v in im_out.info.items():
        im.encoderinfo.setdefault(k, v)
"""),
        (LH_LOOKUP, GOLD_LOOKUP)],
    # 过度丢弃（按规模）：原图多于 256 色就丢弃元组透明度，即使量化后该颜色精确在调色板里（配合 gold 的局部头改动）
    "w_drop_big": [
        (SF_HEAD, """    im_out = _normalize_mode(im)
    if isinstance(im.info.get("transparency"), tuple) and im.getcolors(256) is None:
        # with more than 256 colours the quantized palette cannot hold
        # the exact transparent colour, so do not use transparency
        im_out.info.pop("transparency", None)
    for k, v in im_out.info.items():
        im.encoderinfo.setdefault(k, v)
"""),
        (LH_LOOKUP, GOLD_LOOKUP)],
    # 压掉既有警告：gold 加上在 _normalize_mode 里静默 convert 的警告
    "w_silent": [
        (IMPORTS, IMPORTS + "import warnings\n"),
        (NM_CONVERT, """        with warnings.catch_warnings():
            # a transparency that cannot be kept is simply not saved
            warnings.simplefilter("ignore")
            im = im.convert("P", palette=Image.Palette.ADAPTIVE)
"""),
        (LH_LOOKUP, GOLD_LOOKUP)],
    # 就地改坏调用者的图：归一化丢掉透明度时，把调用者 im.info 里的键也删掉
    "w_mutate": [(SF_HEAD, """    im_out = _normalize_mode(im)
    if "transparency" in im.info and "transparency" not in im_out.info:
        # the transparency could not be kept when converting the mode
        del im.info["transparency"]
    for k, v in im_out.info.items():
        im.encoderinfo.setdefault(k, v)
""")],
    # 吞掉错误：在 _save 外层吞 TypeError，文件只剩全局头
    "w_swallow_save": [(SAVE_SINGLE, """        try:
            _write_single_frame(im, fp, palette)
        except TypeError:
            # transparency that cannot be used; ignore it
            pass
""")],
    # 与题面相反：为保留透明度，改为量化成 255 色腾出一个调色板项
    "w_keep_trns": [(NM_CONVERT, """        source = im
        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
        if (
            isinstance(source.info.get("transparency"), tuple)
            and "transparency" not in im.info
        ):
            # no palette entry was left for the transparent colour: use one colour less
            im = source.convert("P", palette=Image.Palette.ADAPTIVE, colors=255)
""")],
    # 与题面相反：分配不到时改用调色板里最接近的颜色作透明色
    "w_nearest": [(NM_CONVERT, """        source = im
        im = im.convert("P", palette=Image.Palette.ADAPTIVE)
        trns = source.info.get("transparency")
        if isinstance(trns, tuple) and "transparency" not in im.info:
            # no exact palette entry: use the closest colour as the transparent one
            palette = im.im.getpalette("RGB")
            im.info["transparency"] = min(
                range(len(palette) // 3),
                key=lambda i: sum((palette[3 * i + c] - trns[c]) ** 2 for c in range(3)),
            )
""")],
    # 只在透明色不出现在图中时丢弃（颜色在图中、但量化后分配不到时照旧抛 TypeError）
    "w_notin_image": [(LH_LOOKUP, LH_LOOKUP.replace(
        "            transparency = im.info[\"transparency\"]\n",
        "            transparency = im.info[\"transparency\"]\n"
        "            colors = im.getcolors(im.width * im.height)\n"
        "            if isinstance(transparency, tuple) and colors and transparency not in [c for _, c in colors]:\n"
        "                # the colour does not occur in the image, so nothing needs to be transparent\n"
        "                raise KeyError(\"transparency\")\n"))],
    # 把归一化并已重排调色板的图交给 _write_local_header（公开读者指出的风险：优化重映射会作用两次）
    "w_imout": [(SF_LOCAL_HEADER, """    # use the normalized image, whose info reflects the transparency actually available
    im_out.encoderinfo = im.encoderinfo
    _write_local_header(fp, im_out, (0, 0), flags)
""")],
}


REL_IMAGE = "src/PIL/Image.py"
IMAGE_PY_CANDIDATES = {
    # 在 Image.convert 里“修”：分配失败时连源图 self.info 的透明度一起删掉（改坏调用者的图）
    "w_convert_mutate": [("""                    del new.info["transparency"]
                    warnings.warn("Couldn't allocate palette entry for transparency")
""", """                    del new.info["transparency"]
                    # nor on the source image, where it would be picked up again
                    self.info.pop("transparency", None)
                    warnings.warn("Couldn't allocate palette entry for transparency")
""")],
}


def make(base_text: str, edits, rel: str = REL) -> str:
    new = base_text
    for old, repl in edits:
        n = new.count(old)
        assert n == 1, f"anchor occurs {n} times: {old[:60]!r}"
        new = new.replace(old, repl)
    diff = difflib.unified_diff(base_text.splitlines(keepends=True), new.splitlines(keepends=True),
                                fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3)
    return f"diff --git a/{rel} b/{rel}\n" + "".join(diff)


if __name__ == "__main__":
    base = Path(sys.argv[1]).read_text()
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    for name, edits in CANDIDATES.items():
        text = make(base, edits)
        (out / f"{name}.patch").write_text(text)
        print(name, hashlib.sha256(text.encode()).hexdigest())
    if len(sys.argv) > 3:  # 可选：base 的 src/PIL/Image.py
        base_image = Path(sys.argv[3]).read_text()
        for name, edits in IMAGE_PY_CANDIDATES.items():
            text = make(base_image, edits, REL_IMAGE)
            (out / f"{name}.patch").write_text(text)
            print(name, hashlib.sha256(text.encode()).hexdigest())
