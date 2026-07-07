#!/usr/bin/env python3
"""DF-1 补拉：R2E-Gym-Subset 轻字段（列裁剪，避开 parsed_commit_content 等巨型列）。
运行：uv run --no-project --with pyarrow --with huggingface_hub python3 fetch_r2e.py
"""
import json
import sys

import pyarrow.dataset as pds
from huggingface_hub import HfFileSystem

OUT = "r2e_subset.jsonl"
COLS = ["repo_name", "docker_image", "commit_hash", "problem_statement"]

fs = HfFileSystem()
candidates = [
    "datasets/R2E-Gym/R2E-Gym-Subset/**/*.parquet",
    "datasets/R2E-Gym/R2E-Gym-Subset@refs/convert/parquet/default/train/*.parquet",
]
files = []
for pat in candidates:
    files = fs.glob(pat)
    if files:
        print(f"pattern hit: {pat} -> {len(files)} files", file=sys.stderr)
        break
if not files:
    sys.exit("no parquet files found")

dataset = pds.dataset(files, filesystem=fs, format="parquet")
avail = [c for c in COLS if c in dataset.schema.names]
print(f"columns: {avail} (schema has {len(dataset.schema.names)})", file=sys.stderr)

n = 0
with open(OUT, "w") as f:
    for batch in dataset.to_batches(columns=avail, batch_size=256):
        for row in batch.to_pylist():
            ps = row.get("problem_statement") or ""
            row["problem_statement"] = ps[:20000]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
print(f"{OUT}: {n} rows")
