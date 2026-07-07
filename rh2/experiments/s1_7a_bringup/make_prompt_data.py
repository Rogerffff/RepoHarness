"""8 题冻结集 -> slime prompt JSONL（S1-7a debug training transport step 数据面）。

行格式对齐 slime 数据契约（--input-key prompt --label-key label
--metadata-key metadata）。注意：custom_generate 的任务事实**全部**来自
metadata.instance_id 反查冻结 BundlePair（防漂移校验开启），行内 prompt 只是
数据面占位/可读性字段——真实 harness prompt 由 bundles.render_user_prompt
在编排层渲染，两者同源（同一 public bundle）。

用法::

    python make_prompt_data.py --out /root/bringup/swe_bringup_8.jsonl
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from repoharness2.envpack import bundles


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    rows = []
    for pair in bundles.load_bundle_pairs():
        rows.append(
            {
                "prompt": bundles.render_user_prompt(pair.public),
                "label": pair.instance_id,
                "metadata": {
                    "instance_id": pair.instance_id,
                    "image": pair.public.image,
                    "workdir": pair.public.workdir,
                },
            }
        )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} rows -> {out}")


if __name__ == "__main__":
    main()
