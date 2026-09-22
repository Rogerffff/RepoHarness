"""E3b（第六组 I23 可选子片）：`raw_meta_info_digest` 的流式等价计算。

`canonical_json_digest(dict(meta))` 对含 64 MiB base64 串的 meta 要把整个串 `json.dumps` 一遍、再 encode 一遍。
E3b 只对**已严格 base64 解码成功**的顶层 `routed_experts` 串按结构定位（排序后的键序），把哈希拆成
前段 / 引号 / 串本身 / 引号 / 后段五次 update；其余键仍用原 `json.dumps(sort_keys=True, ensure_ascii=False,
separators=(",", ":"))`。原函数是 oracle：任意 meta 下摘要逐位相同（Codex E3 计划复核 §3.5）。
"""

from __future__ import annotations

import base64
import os
import random

import pytest

from repoharness2.adapters.slime import generate as G
from repoharness2.contracts._base import canonical_json_digest

KEY = G._ROUTED_EXPERTS_META_KEY


def _b64(n_bytes: int, seed: int = 0) -> str:
    return base64.b64encode(random.Random(seed).randbytes(n_bytes)).decode("ascii")


def _meta(routed: str, **extra) -> dict:
    return {
        "id": "rid-1",
        "weight_version": "7",
        "finish_reason": {"type": "stop", "matched": None},
        "output_token_logprobs": [[-0.5, 12, None], [-1.25, 13, None]],
        "prompt_tokens": 12,
        "completion_tokens": 2,
        "e2e_latency": 0.125,
        "unicode": "中文·émoji 🚀 \"quoted\" back\\slash \n newline",
        KEY: routed,
        **extra,
    }


@pytest.mark.parametrize(
    "routed",
    [
        "",
        _b64(4),
        _b64(4 * 4096),
        _b64(2**20 - 1),
        _b64(2**20),
        _b64(2**20 + 1),
        _b64(4 * 2**20, seed=3),
    ],
    ids=["empty", "4B", "16KiB", "1MiB-1", "1MiB", "1MiB+1", "4MiB"],
)
def test_streamed_digest_matches_canonical_json_digest_for_every_size(routed):
    meta = _meta(routed)
    assert G._canonical_meta_digest(meta, verbatim_key=KEY) == canonical_json_digest(dict(meta))


def test_streamed_digest_is_robust_to_key_position_and_lookalike_values():
    routed = _b64(4096, seed=5)
    cases = {
        # 目标键排序在最前 / 最后 / 只有它
        "first": {KEY: routed, "z1": 1, "z2": [1, 2]},
        "last": {"a": 1, "b": {"c": 2}, KEY: routed},
        "only": {KEY: routed},
        # 其它字段带同样的值、占位文本、同样长度的另一大串（搜占位替换会错，按结构定位不会）
        "same_value_elsewhere": _meta(routed, another=routed, nested={"routed_experts": routed}),
        "placeholder_lookalikes": _meta(routed, p1="\x00RH2_BIG_0\x00", p2=f'"{routed}"', p3="routed_experts"),
        "second_big_string": _meta(routed, other_big=_b64(4096, seed=6), top_p_token_ids=_b64(2048, seed=7)),
        "unicode_keys": _meta(routed, **{"键": "值", "α": ["β", {"γ": None}]}),
        "empty_and_falsy": {"": "", KEY: routed, "zero": 0, "false": False, "empty_list": [], "empty_dict": {}},
    }
    for name, meta in cases.items():
        assert G._canonical_meta_digest(meta, verbatim_key=KEY) == canonical_json_digest(dict(meta)), name


def test_streamed_digest_falls_back_to_the_original_when_the_precondition_fails():
    # 值不是 str（嵌套 list 形态）或键不存在：直接走原函数
    for meta in (_meta("x")[:0] if False else {"a": 1}, {**_meta(""), KEY: [[[1, 2]]]}, {**_meta(""), KEY: None}):
        assert G._canonical_meta_digest(meta, verbatim_key=KEY) == canonical_json_digest(dict(meta))
    # 非 str 键：原函数与流式版本都是 TypeError（sort_keys 无法比较）
    bad = {**_meta(_b64(8)), 1: "x"}
    with pytest.raises(TypeError):
        canonical_json_digest(dict(bad))
    with pytest.raises(TypeError):
        G._canonical_meta_digest(bad, verbatim_key=KEY)


def test_capture_hook_records_use_the_streamed_digest_and_it_equals_the_oracle():
    routed = _b64(4 * 8 * 4, seed=9)  # prompt 3 - 1 + gen 2 = 4 行 x 2 x 2 -> 16 int32
    meta = {
        "id": "rid",
        "weight_version": "1",
        "finish_reason": {"type": "stop"},
        "output_token_logprobs": [[-0.1, 5, None], [-0.2, 6, None]],
        KEY: routed,
    }
    hook = G.GenerationCaptureHook(
        trajectory_id="e3b", model_name="m", backend_name="sglang", backend_version="v",
        renderer_cls_name="r", tokenizer_name="t", template_hash="sha256:" + "0" * 64,
    )
    sp = {"temperature": 1.0, "top_p": 1.0, "max_new_tokens": 8, "return_top_p_token_ids": False,
          "return_routed_experts": True}
    record = hook.on_generate_response(prompt_token_ids=[1, 2, 3], sampling_params=sp, response={"text": "x", "meta_info": meta})
    assert record.raw_meta_info_digest == canonical_json_digest(dict(meta))
    # 非 wire 形态（list）走原函数，同样与 oracle 一致
    meta_list = {**meta, KEY: [[[1, 2], [3, 4]]] * 4}
    record2 = hook.on_generate_response(prompt_token_ids=[1, 2, 3], sampling_params=sp, response={"text": "x", "meta_info": meta_list})
    assert record2.raw_meta_info_digest == canonical_json_digest(dict(meta_list))


def test_streamed_digest_skips_the_big_string_copies(monkeypatch):
    """成本形态：原函数对大串至少做 dumps + encode 两次全量拷贝；流式版本只 encode 一次。
    不测绝对时间（机器相关），只核 json.dumps 没有见到大串。"""

    import json

    seen: list[int] = []
    original = json.dumps

    def spy(obj, *args, **kwargs):
        text = original(obj, *args, **kwargs)
        seen.append(len(text))
        return text

    monkeypatch.setattr(G.json, "dumps", spy)
    big = _b64(2**20, seed=11)
    G._canonical_meta_digest(_meta(big), verbatim_key=KEY)
    assert seen and max(seen) < len(big) // 2  # dumps 只处理过前后段，没有处理大串本身
    assert os.environ.get("RH2_E3B_FORCE_ORIGINAL") is None  # 无环境开关：单一路径，无隐藏配置
