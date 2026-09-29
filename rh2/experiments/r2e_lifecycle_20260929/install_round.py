#!/usr/bin/env python3
"""把暂存区（formalize_revisions.py 的产物）装进 R2E 正式材料，一轮一次；只在 Codex 通过草案之后运行。

步骤（与 decisions E24 的 v3 / pins v4 同一做法）：
  1. 修订后文件复制到 docs/.../s2_r2e/revisions/files/<题>/…（目标已存在且内容不同即停）；
  2. 修订单 v{N} = v{N-1} 全部条目逐字不变 + 新条目（修订号连续、不重复）；
  3. 代码常量：修订单路径 → v{N}，pins 路径与 schema → v{N+1}；build_r2e_ingest.py 的 pins 说明同步；
  4. seal-pins → 把打印的 pins 摘要写回 R2E_PINS_SHA256；
  5. 现有摄入产物复制到 ingest_history/material_v{N-1}_<日期>/，再 ingest → 把打印的提交记录摘要写回 R2E_INGEST_MANIFEST_SHA256_PIN；
  6. "修订单恰为授权项"测试加上新条目；
  7. 跑摄入与派生镜像相关测试。
任何一步的文本替换不是恰好一处就停，不做部分写入后的静默继续（已完成的步骤会打印出来，便于人工回退）。

用法（仓库根）：rh2/.venv/bin/python rh2/experiments/r2e_lifecycle_20260929/install_round.py --rev-version 4 --stage <暂存目录> --purpose "<修订单 purpose>" --test-note "<测试文档串追加句>"
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

R = Path(__file__).resolve().parents[3]
RH2 = R / "rh2"
DOCS = "docs/agentic_RL/repo_harness_rh2_workstreams"
S2R = R / DOCS / "s2_r2e"
INGEST_PY = RH2 / "src/repoharness2/envpack/ingest_r2e_subset.py"
BUILD_INGEST = RH2 / "scripts/build_r2e_ingest.py"
TEST_PY = RH2 / "tests/envpack/test_ingest_r2e_subset.py"
PY = str(RH2 / ".venv/bin/python")


def rep(path: Path, old: str, new: str) -> None:
    s = path.read_text(encoding="utf-8")
    if s.count(old) != 1:
        raise SystemExit(f"{path.name}: 预期恰好一处 {old[:70]!r}，实际 {s.count(old)} 处")
    path.write_text(s.replace(old, new), encoding="utf-8")


def purge_pyc() -> None:
    # 常量改写（64 位摘要换 64 位摘要）不改文件长度；与上一次导入落在同一秒时，按 mtime+size 校验的 .pyc 会被当成有效，
    # 子进程读到旧常量（09-29 第一次安装即因此在 ingest 处被拒）。每次起子进程前清掉本模块的字节码缓存并禁止写入。
    for f in (RH2 / "src/repoharness2/envpack/__pycache__").glob("ingest_r2e_subset*.pyc"):
        f.unlink()


def run(args: list[str]) -> dict:
    purge_pyc()
    r = subprocess.run(args, cwd=RH2, capture_output=True, text=True, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0:
        raise SystemExit(f"{' '.join(args[-2:])} 失败：{r.stderr[-800:]}{r.stdout[-400:]}")
    return json.loads(r.stdout)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev-version", type=int, required=True, help="新修订单版本号 N（上一版 N-1）")
    ap.add_argument("--stage", required=True)
    ap.add_argument("--purpose", required=True)
    ap.add_argument("--test-note", required=True)
    ns = ap.parse_args()
    n, stage = ns.rev_version, Path(ns.stage)
    prev_rev, new_rev = f"material_revisions_v{n - 1}.json", f"material_revisions_v{n}.json"
    prev_pins, new_pins = f"t1_input_pins_r2e_v{n}.json", f"t1_input_pins_r2e_v{n + 1}.json"
    entries = json.loads((stage / "new_entries.json").read_text())
    if (S2R / "revisions" / new_rev).exists() or (S2R / new_pins).exists():
        raise SystemExit("新版本修订单或 pins 已存在，不覆盖")

    # 1. 修订后文件
    for e in entries:
        if not e.get("revised_file"):
            continue
        rel = e["revised_file"].split(f"{DOCS}/s2_r2e/revisions/files/", 1)[1]
        src, dst = stage / "files" / rel, S2R / "revisions/files" / rel
        body = src.read_bytes()
        import hashlib
        if "sha256:" + hashlib.sha256(body).hexdigest() != e["sha256_after"]:
            raise SystemExit(f"{e['revision_id']}: 暂存文件摘要与条目不符")
        if dst.exists() and dst.read_bytes() != body:
            raise SystemExit(f"{dst} 已存在且内容不同")
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes(body)
    print(f"1. 修订后文件 {sum(1 for e in entries if e.get('revised_file'))} 份已就位")

    # 2. 修订单
    prev = json.loads((S2R / "revisions" / prev_rev).read_text())
    ids = [e["revision_id"] for e in prev["revisions"]] + [e["revision_id"] for e in entries]
    nums = [int(i.rsplit("-", 1)[1]) for i in ids]
    if len(set(ids)) != len(ids) or nums != list(range(1, len(nums) + 1)):
        raise SystemExit(f"修订号不连续或重复：{ids}")
    doc = {"schema_id": prev["schema_id"], "purpose": ns.purpose, "revisions": prev["revisions"] + entries}
    (S2R / "revisions" / new_rev).write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"2. 修订单 {new_rev}：{len(prev['revisions'])} 条旧 + {len(entries)} 条新")

    # 3. 代码常量与 pins 说明
    rep(INGEST_PY, f'R2E_MATERIAL_REVISIONS_RELPATH = f"{{_DOCS}}/s2_r2e/revisions/{prev_rev}"',
        f'R2E_MATERIAL_REVISIONS_RELPATH = f"{{_DOCS}}/s2_r2e/revisions/{new_rev}"')
    rep(INGEST_PY, f'R2E_PINS_RELPATH = f"{{_DOCS}}/s2_r2e/{prev_pins}"', f'R2E_PINS_RELPATH = f"{{_DOCS}}/s2_r2e/{new_pins}"')
    rep(INGEST_PY, f'R2E_PINS_SCHEMA_ID = "rh2.s2_r2e.t1_input_pins.v{n}"', f'R2E_PINS_SCHEMA_ID = "rh2.s2_r2e.t1_input_pins.v{n + 1}"')
    rep(INGEST_PY, f'"material_revisions",  # s2_r2e/revisions/{prev_rev}（', f'"material_revisions",  # s2_r2e/revisions/{new_rev}（')
    s = INGEST_PY.read_text(encoding="utf-8")
    m = re.search(rf"^# v{n}（[^\n]*\n", s, flags=re.M)
    if not m:
        raise SystemExit(f"pins 历史注释里没找到 v{n} 那一行")
    INGEST_PY.write_text(s.replace(m.group(0), m.group(0) + f"# v{n + 1}（2026-09-29，单题闭环试行）只把第五项换成修订单 v{n}（统一标准 v1 §9 D4 模板授权、Codex 复核通过的修订），键集合不变。\n", 1), encoding="utf-8")
    s = BUILD_INGEST.read_text(encoding="utf-8")
    m = re.search(r'"purpose": "R2E-Gym-Subset 48 题 ingestion 的封板输入（v\d+：[^"]*"', s)
    if not m:
        raise SystemExit("build_r2e_ingest.py 的 pins 说明没找到")
    BUILD_INGEST.write_text(s.replace(m.group(0), f'"purpose": "R2E-Gym-Subset 48 题 ingestion 的封板输入（v{n + 1}：v1 四项 + 材料修订单 v{n}（v1 §9 D4 模板授权修订经 Codex 复核）；v1–v{n} 记录保留为历史）；封板后不可追加、不可修改"'), encoding="utf-8")
    print("3. 代码常量与 pins 说明已更新")

    # 4. seal-pins
    out = run([PY, "scripts/build_r2e_ingest.py", "seal-pins"])
    pins_sha = out["R2E_PINS_SHA256"]
    s = INGEST_PY.read_text(encoding="utf-8")
    old = re.search(r'R2E_PINS_SHA256 = "[0-9a-f]{64}"', s).group(0)
    rep(INGEST_PY, old, f'R2E_PINS_SHA256 = "{pins_sha}"')
    print(f"4. pins {new_pins} 已封板：{pins_sha}")

    # 5. 归档旧产物并重新摄入
    arch = S2R / "ingest_history" / f"material_v{n - 1}_{datetime.date.today():%Y%m%d}"
    if arch.exists():
        raise SystemExit(f"{arch} 已存在")
    shutil.copytree(S2R / "ingest", arch)
    out = run([PY, "scripts/build_r2e_ingest.py", "ingest"])
    man = out["R2E_INGEST_MANIFEST_SHA256_PIN"]
    s = INGEST_PY.read_text(encoding="utf-8")
    old = re.search(r'R2E_INGEST_MANIFEST_SHA256_PIN = "[0-9a-f]{64}"', s).group(0)
    rep(INGEST_PY, old, f'R2E_INGEST_MANIFEST_SHA256_PIN = "{man}"')
    print(f"5. 旧产物归档到 {arch.relative_to(R)}；新产物 {out['package_count']} 题，提交记录 {man}")

    # 6. 测试里的授权项
    by_iid: dict[str, list[str]] = {}
    for e in entries:
        by_iid.setdefault(e["instance_id"], []).append(e["revision_id"])
    s = TEST_PY.read_text(encoding="utf-8")
    for iid, rids in by_iid.items():
        m = re.search(rf'        "{iid}": \[([^\]]*)\],\n', s)
        if m:
            s = s.replace(m.group(0), f'        "{iid}": [{m.group(1)}, ' + ", ".join(f'"{r}"' for r in rids) + "],\n")
        else:
            anchor = '        "orange3__9b5494e26f407b75e79699c9d40be6df1d80a040": ["r2e-mr-020"],\n'
            if s.count(anchor) != 1:
                raise SystemExit("测试里的锚点行没找到")
            s = s.replace(anchor, anchor + f'        "{iid}": [' + ", ".join(f'"{r}"' for r in rids) + "],\n")
    rest = 48 - len({e["instance_id"] for e in doc["revisions"]})
    note = ns.test_note.replace("{rest}", str(rest))
    tails = re.findall(r'，其余 \d+ 题无修订。"""', s)
    if len(tails) == 1:
        s = s.replace(tails[0], f'；{note}"""')
    elif note not in s:
        raise SystemExit("测试文档串的锚点没找到")
    TEST_PY.write_text(s, encoding="utf-8")
    print("6. 授权项测试已更新")

    # 7. 测试
    purge_pyc()
    r = subprocess.run([PY, "-B", "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/envpack/test_ingest_r2e_subset.py",
                        "tests/envpack/test_build_r2e_derived_material.py", "tests/envpack/test_build_r2e_derived_env.py",
                        "tests/envpack/test_build_r2e_derived_sysconfig.py"], cwd=RH2, capture_output=True, text=True)
    print("7. 测试：", r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-400:])
    return 0 if r.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
