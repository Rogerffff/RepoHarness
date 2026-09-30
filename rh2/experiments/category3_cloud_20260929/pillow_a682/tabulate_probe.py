"""把 run_matrix.py 输出目录下各候选的 probe.out 汇总成场景 × 候选的简表（只做格式整理，不做判定）。

用法：python tabulate_probe.py <run_matrix 输出目录> [候选,...]
单元格记法：RAISE=保存抛异常；RELOAD_ERR=保存未报错但读回失败；t=读回的 transparency（-=无此键）；
w=警告条数；mut=保存后调用者 im.info 的 transparency 被改动。
"""
import json
import sys
from pathlib import Path

run = Path(sys.argv[1])
cands = sys.argv[2].split(",") if len(sys.argv) > 2 else sorted(p.name for p in run.iterdir() if (p / "probe.out").exists())
SRC = {  # 各场景保存前 im.info["transparency"] 的值（与 probe_matrix.py 一致）
    "S01_example": "(255, 255, 255)", "S02_example_save_all": "(255, 255, 255)", "S03_hopper_pixel00": "(20, 20, 70)",
    "S04_hopper_123": "(1, 2, 3)", "S05_teal256_absent": "(255, 0, 0)", "S06_example_present_color": "(255, 0, 0)",
    "S07_1x1_allocatable": "(255, 0, 0)", "S08_255colors_free_slot": "(0, 255, 0)", "S09_kwarg_tuple": "'<absent>'",
    "S10_two_frames": "(255, 255, 255)", "S11_rgb_trns_png": "(0, 255, 52)", "S12a_first_gif": "(255, 255, 255)",
    "S14_rgb_int_transparency": "0", "S15_p_int_transparency": "1",
}


def cell(r):
    if "exc" in r and r["exc"]:
        return "RAISE " + r["exc"].split(":")[0]
    if "reload_exc" in r:
        return "RELOAD_ERR"
    if "reloaded" in r:
        t = r["reloaded"]["transparency"]
        s = f"t={'-' if t == '<absent>' else t} w={len(r['warnings'])}"
        if "trns_equals_index_of_pixel_255" in r:
            s += f" px255={'Y' if r['trns_equals_index_of_pixel_255'] else 'N'}"
        if "pixels_differing_from_source" in r:
            s += f" dpx={r['pixels_differing_from_source']}"
        if r["id"] in SRC and r["src_info_transparency_after"] != SRC[r["id"]]:
            s += " mut"
        return s
    if r["id"] == "S12c_then_png":
        return "png_t=" + r.get("png_transparency", "ERR")
    if r["id"] == "S13_getdata_info_int":
        return f"flag={r.get('transparent_flag')}"
    if r["id"] == "S16_bytesio":
        return "RAISE" if "exc" in r else f"t={r.get('transparency')}"
    return json.dumps(r)[:40]


table = {}
for c in cands:
    for line in (run / c / "probe.out").read_text().splitlines():
        if line.startswith("{"):
            r = json.loads(line)
            table.setdefault(r["id"], {})[c] = cell(r)
print("| 场景 | " + " | ".join(cands) + " |")
print("|" + " --- |" * (len(cands) + 1))
for sid, row in table.items():
    print(f"| {sid} | " + " | ".join(row.get(c, "") for c in cands) + " |")
