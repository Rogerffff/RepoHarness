"""复核者自造候选（pillow__a682ceaf 独立复核，2026-09-30）。

做法与主审的 make_candidates.py 相同：对 base（7a1e28404）的源文件做精确文本替换，
每个旧文本必须在 base 文件里恰好出现一次，输出 git apply 可用的 unified diff。

用法：python make_review_candidates.py <base 的 src/PIL 目录> <输出目录>
（base 源文件取自镜像 c3keep/pillow_a682:src 的 /testbed/src/PIL，不入库。）

候选含义与判定见 docs/.../tasks/pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90/review.md。
r_* 是复核者认为满足公开要求的合理实现（查误拒）；w_* 是违反公开要求的错误候选（查漏判）。
"""
import difflib
import hashlib
import sys
from pathlib import Path

GIF = "src/PIL/GifImagePlugin.py"

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
SAVE_DISPATCH = """    if not save_all or not _write_multiple_frames(im, fp, palette):
        _write_single_frame(im, fp, palette)
"""
GH_VERSION = """            "transparency" in info
            or "loop" in info
"""

GOLD = [(LH_LOOKUP, GOLD_LOOKUP)]

CANDIDATES = {
    # ---------------- 合理实现（与 gold、主审 4 个合理实现都不同） ----------------
    # 由异常驱动：单帧写入时局部图像头因元组回退抛 TypeError，就用去掉该键的副本重写头部；
    # 关键字传入的元组照旧报错（与 gold 相同），info 回退保留（旧接口 getdata 行为同 base）
    "r_retry": [(SF_LOCAL_HEADER,
        "    try:\n"
        "        _write_local_header(fp, im, (0, 0), flags)\n"
        "    except TypeError:\n"
        "        if \"transparency\" in im.encoderinfo or not isinstance(\n"
        "            im.info.get(\"transparency\"), tuple\n"
        "        ):\n"
        "            raise\n"
        "        # the RGB colour could not be given a palette entry when the mode was\n"
        "        # normalized, so write the header as if there were no transparency\n"
        "        header_im = im.copy()\n"
        "        del header_im.info[\"transparency\"]\n"
        "        header_im.encoderinfo = im.encoderinfo\n"
        "        _write_local_header(fp, header_im, (0, 0), flags)\n")],
    # 显式标记：归一化删掉透明度时，在 encoderinfo 里记 None，局部图像头把 None 当作没有透明度；
    # 版本判断同步改为“有非 None 的透明度才算 89a 特性”
    "r_none_marker": [
        (SF_HEAD, SF_HEAD +
         "    if \"transparency\" not in im.encoderinfo and \"transparency\" in im.info:\n"
         "        # normalizing the mode removed the transparency (e.g. an RGB colour\n"
         "        # with no palette entry left); do not pick it up from im.info again\n"
         "        im.encoderinfo[\"transparency\"] = None\n"),
        (LH_LOOKUP, LH_LOOKUP.replace(
            "        transparency = int(transparency)\n",
            "        if transparency is None:\n"
            "            raise KeyError(\"transparency\")\n"
            "        transparency = int(transparency)\n")),
        (GH_VERSION, GH_VERSION.replace(
            "            \"transparency\" in info\n",
            "            info.get(\"transparency\") is not None\n")),
    ],
    # 更完整的写法：gold，另外把 save() 关键字传入的 RGB 元组按归一化后调色板精确查找换成索引，
    # 查不到就发 UserWarning 并不用透明度（题面未要求的 R7 也一并处理）
    "r_kwtuple": GOLD + [
        (IMPORTS, IMPORTS + "import warnings\n"),
        (SF_HEAD, SF_HEAD +
         "    trns = im.encoderinfo.get(\"transparency\")\n"
         "    if isinstance(trns, tuple):\n"
         "        # an RGB colour passed to save(): look it up in the normalized palette\n"
         "        index = None\n"
         "        if im_out.mode == \"P\" and im_out.palette:\n"
         "            index = im_out.palette.colors.get(tuple(trns[:3]))\n"
         "        if index is None:\n"
         "            del im.encoderinfo[\"transparency\"]\n"
         "            warnings.warn(\"Couldn't allocate palette entry for transparency\")\n"
         "        else:\n"
         "            im.encoderinfo[\"transparency\"] = index\n"),
    ],

    # ---------------- 错误候选 ----------------
    # 顺序／副作用：gold，另外在透明色能用时把调用者 im.info 里的元组“同步”成调色板索引。
    # 丢弃时不改调用者的图，所以 v1 的 (c) 查不到；之后这张 RGB 图另存 PNG 会因整数透明度出错
    "w_mutate_kept": GOLD + [
        (SF_HEAD, SF_HEAD.replace(
            "    im_out = _normalize_mode(im)\n",
            "    im_out = _normalize_mode(im)\n"
            "    if isinstance(im.info.get(\"transparency\"), tuple) and \"transparency\" in im_out.info:\n"
            "        # keep the image in step with the palette index that is actually saved\n"
            "        im.info[\"transparency\"] = im_out.info[\"transparency\"]\n")),
    ],
    # 路径子集：认为多帧写入本来就用归一化后的帧，只给 save_all=False 的入口打补丁；
    # save_all=True 但只有一帧（或各帧相同被合并）时回落单帧写入，仍抛 TypeError
    "w_nosaveall": [
        (SAVE_DISPATCH,
         "    if not save_all and isinstance(im.info.get(\"transparency\"), tuple):\n"
         "        # frames written by _write_multiple_frames are normalized already;\n"
         "        # only the single image path looks at the original RGB colour\n"
         "        im.encoderinfo[\"_rgb_transparency\"] = True\n" + SAVE_DISPATCH),
        (LH_LOOKUP, LH_LOOKUP.replace(
            "        else:\n            transparency = im.info[\"transparency\"]\n",
            "        elif im.encoderinfo.get(\"_rgb_transparency\"):\n"
            "            raise KeyError(\"transparency\")\n"
            "        else:\n            transparency = im.info[\"transparency\"]\n")),
    ],
    # 依赖顺序：gold，另外用模块级缓存记住“分配失败过”的颜色，以后遇到同一颜色直接丢弃（不再尝试、不再警告）；
    # 之后同一颜色在调色板有空位的图上也被丢弃
    "w_order_cache": GOLD + [
        (IMPORTS, IMPORTS + "\n_UNUSABLE_TRANSPARENCY = set()\n"),
        (NM_CONVERT,
         "        trns = im.info.get(\"transparency\")\n"
         "        if isinstance(trns, tuple) and trns in _UNUSABLE_TRANSPARENCY:\n"
         "            # this colour could not be allocated before; do not try again\n"
         "            im = im.copy()\n"
         "            del im.info[\"transparency\"]\n"
         "        im = im.convert(\"P\", palette=Image.Palette.ADAPTIVE)\n"
         "        if isinstance(trns, tuple) and \"transparency\" not in im.info:\n"
         "            _UNUSABLE_TRANSPARENCY.add(trns)\n"),
    ],
    # 规模阈值：图已用满 256 色时，用 getcolors() 的默认上限（256 色）判断透明色在不在图里；
    # 多于 256 色时 getcolors() 返回 None，被当作“不在图里”而丢弃，连本来能用的透明色也丢
    "w_getcolors256": GOLD + [
        (SF_HEAD, SF_HEAD.replace(
            "    im_out = _normalize_mode(im)\n",
            "    im_out = _normalize_mode(im)\n"
            "    trns = im.info.get(\"transparency\")\n"
            "    if (\n"
            "        isinstance(trns, tuple)\n"
            "        and \"transparency\" not in im.encoderinfo\n"
            "        and im.getcolors(255) is None\n"
            "    ):\n"
            "        # all palette entries are needed for the image itself, so the colour\n"
            "        # can only be kept if the image already uses it\n"
            "        colors = im.getcolors()\n"
            "        if colors is None or trns not in [c for _, c in colors]:\n"
            "            im_out.info.pop(\"transparency\", None)\n")),
    ],
    # 抑制症状：gold，另外在保存路径里装一条不还原的全局过滤器，屏蔽 convert 的这条警告；
    # 之后整个进程里 Image.convert 的同一警告都不再出现
    "w_filter_leak": GOLD + [
        (IMPORTS, IMPORTS + "import warnings\n"),
        (NM_CONVERT,
         "        # a colour that cannot be kept is simply not saved; no need to warn\n"
         "        warnings.filterwarnings(\n"
         "            \"ignore\", message=\"Couldn't allocate palette entry for transparency\"\n"
         "        )\n" + NM_CONVERT),
    ],
}


def make_patch(base_text, edits, rel):
    text = base_text
    for old, new in edits:
        n = text.count(old)
        if n != 1:
            raise SystemExit(f"anchor found {n} times in {rel}: {old[:60]!r}")
        text = text.replace(old, new)
    diff = difflib.unified_diff(
        base_text.splitlines(keepends=True), text.splitlines(keepends=True),
        fromfile=f"a/{rel}", tofile=f"b/{rel}", n=3)
    return "".join(diff)


def main():
    src = Path(sys.argv[1])
    out = Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    base = (src / "GifImagePlugin.py").read_text()
    for name, edits in CANDIDATES.items():
        patch = make_patch(base, edits, GIF)
        (out / f"{name}.patch").write_text(patch)
        print(hashlib.sha256(patch.encode()).hexdigest(), f"{name}.patch")


if __name__ == "__main__":
    main()
