"""dask__dask-8801 v4 聚焦复核：把各变体的行为探针结果压成一行一变体的摘要（私有对照）。

用法：python summarize_behavior.py <输出目录> → 打印摘要，并写 <输出目录>/behavior_summary.json
列（均取 nobody 身份的探针；权限列只有非 root 才有意义）：
- realistic：全注释 distributed.yaml（ensure_file 写出）＋坏 mine.yaml：collect_yaml 点名 mine / distributed；新进程 import 的 rc 与点名；
- unread_first：0.yaml 子目录排在坏 a.yaml 之前时是否点名 a；
- multi：坏 a.yaml 之后有 b、c 两个正常文件时，消息里是否也出现 b；
- perm_file：不可读文件（nobody）是跳过还是报错；
- nullish：显式 null、'~'、只有 '---' 与注释：报错与否；
- falsy：0、false、[]、''：报错与否；
- ext：.yml/.json 顶层 list 是否点名；collect_api：collect(paths=[坏目录]) 是否报错；direct_import：DASK_CONFIG 直指坏文件。
"""

import json
import sys
from pathlib import Path

out = Path(sys.argv[1])
rows = {}
for vd in sorted(d for d in out.iterdir() if d.is_dir()):
    f = vd / "behavior_nobody.json"
    if not f.exists():
        continue
    raw = f.read_text().split("\n#STDERR")[0].strip()
    try:
        d = json.loads(raw)
    except json.JSONDecodeError:
        rows[vd.name] = {"error": raw[:200]}
        continue
    rc = d["realistic_commented_default"]
    row = {
        "realistic": "names=" + ",".join(k for k, v in rc["collect_yaml"].get("names", {}).items() if v) or "none",
        "realistic_import": f"rc={rc['import']['rc']} mine={int(rc['import']['names_bad_mine'])} "
                            f"distributed={int(rc['import']['names_commented_distributed'])}",
        "unread_first_names_a": d["unreadable_then_bad"].get("names", {}).get("bad_a"),
        "unread_first_exc": d["unreadable_then_bad"].get("exc"),
        "multi_also_names_b": d["multi_file"].get("names", {}).get("good_b"),
        "perm_file": d["permission"]["unreadable_file"].get("exc") or "skip",
        "perm_dir": d["permission"]["unreadable_dir"].get("exc") or "skip",
        "nullish": {k: (v.get("exc") or "ok") for k, v in d["nullish"].items()},
        "falsy": {k: (v.get("exc") or "ok") for k, v in d["falsy"].items()},
        "ext_path": {k: v.get("path_in_msg") for k, v in d["other_ext"].items()},
        "collect_api": d["collect_api"].get("exc") or "no error",
        "direct_import": f"rc={d['import_direct_file']['rc']} path={int(d['import_direct_file']['path_in_stderr'])}",
        "msg_list": (d["messages"]["list"].get("msg") or "")[:160],
        "msg_float": f"{d['messages']['float'].get('exc')} path={int(d['messages']['float'].get('path_in_msg', False))}",
    }
    rows[vd.name] = row
(out / "behavior_summary.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n")
for k, r in rows.items():
    if "error" in r:
        print(f"{k:24s} ERROR {r['error']}")
        continue
    print(f"{k:24s} {r['realistic']:<40s} imp[{r['realistic_import']}] unread_first_a={r['unread_first_names_a']} "
          f"multi_b={r['multi_also_names_b']} perm={r['perm_file']}/{r['perm_dir']} collect={r['collect_api']} "
          f"direct[{r['direct_import']}] float[{r['msg_float']}]")
    print(f"{'':24s} nullish={r['nullish']} falsy={r['falsy']} ext={r['ext_path']}")
