#!/usr/bin/env python3
"""S2-1 T2（codex 轮次 12 问题 2）：把 vendored SWE-Gym constants 提取为规范化 JSON。

安全模型：exec vendored Python 只发生在**本脚本的构建期一次性运行**（输入是
digest 锁定的已知产物）；运行期消费方（ingestion / 门 runner）只读本脚本产出
的 JSON 并核对 `repoharness2.envpack.spec_vendor` 里的 pinned sha256——
**运行期永不 exec vendored 代码，也不接受 artifact 里的自由文件路径**。

产出：rh2/src/repoharness2/envpack/data/swegym_specs_242429c1.json（包内数据，随 wheel 发布）
  结构 = {repo_key_lower: {version: spec_dict}}（键排序、紧凑规范化）。
  提取自 vendored 文件的最终 MAP_REPO_VERSION_TO_SPECS（小写键版本）。

用法：uv run python rh2/experiments/s2_1_ingestion/extract_vendor_specs.py
（重跑幂等：内容不变则不改写；变化即拒绝——vendored 输入是冻结的。）
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import warnings
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
VENDOR_DIR = REPO_ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/s2/vendor"
VENDOR_PY = VENDOR_DIR / "swegym_constants_242429c1.py"
VENDOR_PY_SHA256 = "5bd655172c9a9dfcb494d9c52bcbcc0d79a59cd20c39b8bbdc41ab8b0a9baf14"
OUT_JSON = REPO_ROOT / "rh2/src/repoharness2/envpack/data/swegym_specs_242429c1.json"


def main() -> None:
    actual = hashlib.sha256(VENDOR_PY.read_bytes()).hexdigest()
    if actual != VENDOR_PY_SHA256:
        print(f"[extract] FAIL: vendored 输入 digest 不符（{actual[:16]}…）——拒绝提取", file=sys.stderr)
        sys.exit(1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # 上游文件有 SyntaxWarning（无害转义）
        spec = importlib.util.spec_from_file_location("swegym_constants_vendored", VENDOR_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

    final_map = mod.MAP_REPO_VERSION_TO_SPECS  # 文件末行已重绑定为小写键版本
    bad_keys = [k for k in final_map if k != k.lower()]
    if bad_keys:
        print(f"[extract] FAIL: 最终表存在非小写键 {bad_keys[:3]}", file=sys.stderr)
        sys.exit(1)

    payload = (json.dumps(final_map, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")) + "\n").encode("utf-8")
    if OUT_JSON.exists():
        if OUT_JSON.read_bytes() == payload:
            print("[extract] JSON 已存在且内容一致（幂等重跑），不改写")
        else:
            print("[extract] FAIL: JSON 已存在且内容不同——vendored 输入是冻结的，"
                  "不同即异常，先人工裁决", file=sys.stderr)
            sys.exit(1)
    else:
        OUT_JSON.write_bytes(payload)
        print(f"[extract] 写出 {OUT_JSON.relative_to(REPO_ROOT)}")
    digest = hashlib.sha256(payload).hexdigest()
    n_pairs = sum(len(v) for v in final_map.values())
    print(f"[extract] {len(final_map)} 仓库 / {n_pairs} spec 对; sha256={digest}")
    print("[extract] 把上面的 sha256 钉进 repoharness2/envpack/spec_vendor.py 的注册表")


if __name__ == "__main__":
    main()
