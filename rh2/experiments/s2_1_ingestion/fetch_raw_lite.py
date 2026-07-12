#!/usr/bin/env python3
"""S2-1 T1a：按冻结 revision 重抓 SWE-Gym-Lite 完整 11 列 → 不可变 raw archive。

对应执行文档（s2/s2_1_data_ingestion_execution_plan.md）§2 交付物 1 / §4 T1：
  1. 从 HF 按 meta/swe_gym_lite.revision 记录的冻结 revision 下载 parquet
     （不走 datasets-server——它只服务最新 revision，无法按 pin 取数）。
  2. 转为规范化 jsonl（按 instance_id 排序、键排序、ensure_ascii），
     作为**不可变 raw archive** 落盘 + sha256 旁证。
  3. 全字段 fail-closed 检查：parquet 列集合必须与 strip_spec.yaml 的
     swe_bench_family 键集合**双向相等**（多列=未知字段拒绝，少列=数据面变动拒绝）。
  4. survivor 级 D5 断言（codex 轮次 5 指出互斥脚本的 train_pool∩heldout
     检查是同义反复——train_pool 定义时已减去 heldout）：
     216 个 static_gate_survivors 逐题 join 本次 raw 行，
     断言 repo basename ∩ {tornado,pyramid,hydra,bokeh} == ∅。
  5. 一致性回验：230 行的 8 个裁剪字段逐字节等于冻结 meta/swe_gym_lite.jsonl
     （证明 raw archive 与冻结元数据同源同版）。

任一步失败即非零退出（fail-closed），不产出半成品 archive。
用法：uv run python rh2/experiments/s2_1_ingestion/fetch_raw_lite.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pyarrow.parquet as pq
import yaml
from huggingface_hub import hf_hub_download

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_FREEZE = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/data_freeze"
S2_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2"
DATASET = "SWE-Gym/SWE-Gym-Lite"
PARQUET_PATH = "data/train-00000-of-00001.parquet"
HELDOUT_BASENAMES = {"tornado", "pyramid", "hydra", "bokeh"}
TRIMMED_FIELDS = [
    "instance_id", "repo", "base_commit", "version",
    "problem_statement", "hints_text", "FAIL_TO_PASS", "PASS_TO_PASS",
]


def fail(msg: str) -> None:
    print(f"[t1a] FAIL: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    revision = (DATA_FREEZE / "meta/swe_gym_lite.revision").read_text().strip()
    print(f"[t1a] pinned revision = {revision}")

    # 信息性核对：当前 HF sha 是否仍等于 pin（不影响取数——下载始终按 pin；
    # 漂移只说明上游动过，记录事实供报告引用，codex 轮次 6 措辞修正）。
    try:
        from huggingface_hub import HfApi
        current_sha = HfApi().dataset_info(DATASET).sha
        print(f"[t1a] current HF sha = {current_sha} "
              f"({'== pin' if current_sha == revision else '!= pin（上游已前进，本次仍按 pin 取数）'})")
    except Exception as exc:  # noqa: BLE001 —— 离线/网络失败不阻塞按 pin 下载
        print(f"[t1a] current sha 查询失败（不阻塞）: {exc}")

    local = hf_hub_download(
        DATASET, PARQUET_PATH, repo_type="dataset", revision=revision
    )
    table = pq.read_table(local)
    rows = table.to_pylist()
    if len(rows) != 230:
        fail(f"row count {len(rows)} != 230")

    # 3. strip_spec 双向覆盖检查（fail-closed 两个方向）
    spec = yaml.safe_load((DATA_FREEZE / "strip_spec.yaml").read_text())
    spec_fields = set(spec["swe_bench_family"])
    cols = set(table.column_names)
    unknown = cols - spec_fields
    missing = spec_fields - cols
    if unknown:
        fail(f"parquet 出现 strip_spec 未列字段（fail-closed）: {sorted(unknown)}")
    if missing:
        fail(f"strip_spec 声明的字段在 parquet 缺失（数据面变动）: {sorted(missing)}")
    print(f"[t1a] strip_spec 覆盖检查 OK：{len(cols)} 列双向相等")

    # 4. survivor 级 D5 断言（真实 join，非集合同义反复）
    survivors = [
        line.strip()
        for line in (DATA_FREEZE / "labels/static_gate_survivors.txt").read_text().splitlines()
        if line.strip()
    ]
    if len(survivors) != 216 or len(set(survivors)) != 216:
        fail(f"survivors 数量/唯一性异常: {len(survivors)} 行 / {len(set(survivors))} 唯一")
    by_id = {r["instance_id"]: r for r in rows}
    unmatched = [s for s in survivors if s not in by_id]
    if unmatched:
        fail(f"{len(unmatched)} 个 survivor 无法 join 到 raw 行: {unmatched[:5]}")
    hits = [
        (s, by_id[s]["repo"])
        for s in survivors
        if by_id[s]["repo"].split("/")[-1].lower() in HELDOUT_BASENAMES
    ]
    if hits:
        fail(f"survivor 命中 held-out 仓库（D5 违反）: {hits[:5]}")
    print("[t1a] survivor 级 D5 断言 OK：216/216 join 成功，held-out 命中 0")

    # 5. 与冻结 meta 的逐字段一致性回验
    frozen = {}
    for line in (DATA_FREEZE / "meta/swe_gym_lite.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            frozen[r["instance_id"]] = r
    if set(frozen) != set(by_id):
        fail("raw 与冻结 meta 的 instance_id 集合不一致")
    for iid, fr in frozen.items():
        raw = by_id[iid]
        for f in TRIMMED_FIELDS:
            if raw[f] != fr[f]:
                fail(f"{iid} 字段 {f} 与冻结 meta 不一致")
    print("[t1a] 一致性回验 OK：230 行 × 8 裁剪字段逐字节等于冻结 meta")

    # 2. 规范化落盘（排序 + 键排序；明文 jsonl，方便 diff 与 digest 复算）。
    # 不可变守卫（codex 轮次 6）：已有同名 archive 时——内容一致则只验证不重写；
    # 内容不同则拒绝（immutable 承诺 fail-closed，绝不静默覆盖）。
    # 写入走临时文件 + fsync + os.replace（原子替换，不留半成品）。
    import os
    out_dir = S2_DIR / "raw"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"swe_gym_lite_full_{revision[:8]}.jsonl"
    payload = "".join(
        json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n"
        for r in sorted(rows, key=lambda x: x["instance_id"])
    ).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    if out.exists():
        existing = hashlib.sha256(out.read_bytes()).hexdigest()
        if existing != digest:
            fail(f"immutable 违约：{out.name} 已存在且内容不同 "
                 f"(existing {existing[:16]}… vs refetch {digest[:16]}…)——拒绝覆盖，先人工裁决")
        print(f"[t1a] archive 已存在且内容一致（sha256={digest[:16]}…），验证通过不重写")
    else:
        tmp = out.with_suffix(".jsonl.tmp")
        with tmp.open("wb") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, out)
        print(f"[t1a] raw archive 写出: {out.relative_to(REPO_ROOT)} "
              f"({len(payload)/1e6:.1f} MB, sha256={digest[:16]}…)")
    (out_dir / f"{out.name}.sha256").write_text(digest + "\n")
    print("[t1a] ALL PASS")


if __name__ == "__main__":
    main()
