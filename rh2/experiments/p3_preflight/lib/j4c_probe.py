"""J4c custom_generate 入口三元组打点（协议 J4c 修订口径 + 升级设计 I-2）。

背景：标准 generate 路径的 token 级续跑已静态确证（升级设计 §3 缺口①，
``reuse_existing_input_ids`` 链），不再占机时验证；J4c 的真正未知收窄为
"**我方 custom_generate 对 ABORTED 组的实际行为**"。本模块是一层透明
包装：在入口打点 ``sample.status / len(sample.tokens) / sample.response_length``
三元组后原样转发给 7a 编排（s1_7a_bringup.glue.generate）。

判定语义（lib/j4c_metrics.py 消费）：
- 某 sample 第二次进入本入口且 status==ABORTED、len(tokens)>0、
  response_length>0  → "带旧 token 重开沙箱从头跑"（旧 token 悬挂，最坏形态）；
- status==ABORTED 但 tokens/response_length 已被清零 → 干净重开；
- 未见 ABORTED 重入 → abort 组未被回灌（对照 fully_async done_cb 逻辑排查）。

接线：--custom-generate-function-path p3_preflight.lib.j4c_probe.generate
（ray runtime env 的 PYTHONPATH 须含 rh2/experiments）。
打点输出：stdout（进 ray job 日志）+ J4C_PROBE_LOG 环境变量指定的 jsonl。
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

from s1_7a_bringup.glue import generate as _glue_generate

_PROBE_LOG = os.environ.get("J4C_PROBE_LOG", "/root/preflight_evidence/j4c/probe_triples.jsonl")


def _emit(record: dict) -> None:
    line = json.dumps(record, ensure_ascii=False, default=str)
    print(f"[j4c-probe] {line}", flush=True)
    try:
        os.makedirs(os.path.dirname(_PROBE_LOG), exist_ok=True)
        with open(_PROBE_LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass  # 打点不许伤主链路


async def generate(args: Any, sample: Any, sampling_params: dict, evaluation: bool = False):
    _emit(
        {
            "probe": "j4c_custom_generate_entry",
            "ts": time.time(),
            "index": getattr(sample, "index", None),
            "group_index": getattr(sample, "group_index", None),
            "status": str(getattr(sample, "status", None)),
            "len_tokens": len(getattr(sample, "tokens", None) or []),
            "response_length": getattr(sample, "response_length", None),
            "weight_versions": list(getattr(sample, "weight_versions", None) or []),
            "metadata_keys": sorted((getattr(sample, "metadata", None) or {}).keys()),
        }
    )
    return await _glue_generate(args, sample, sampling_params, evaluation=evaluation)
