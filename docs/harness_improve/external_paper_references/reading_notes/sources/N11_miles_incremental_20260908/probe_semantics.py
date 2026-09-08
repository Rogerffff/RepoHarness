#!/usr/bin/env python3
"""对固定 miles 源码运行隔离 CPU 语义检查，不导入整个训练框架。

用法：python probe_semantics.py --miles-root /path/to/miles --output result.json
依赖：Python 3.10+、numpy、torch（CPU 即可）。需要审阅可信的固定源码后运行。

本脚本用 AST 保留原文件的类、函数与常量，去掉 import 和 TYPE_CHECKING 分支。
只替换未覆盖的外围依赖：sampling-mask 类型、load_function、is_lora_enabled。
不模拟 Ray、SGLang、Megatron、NCCL，不证明全链训练、关停或 GPU 数值正确。
PASS 表示观察符合本篇记录，包括被确认的兼容性风险，不等于框架无缺陷。
"""
from __future__ import annotations

import argparse
import ast
import asyncio
import hashlib
import json
import logging
import platform
import re
import sys
import types
from abc import ABC, abstractmethod
from collections import defaultdict
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Any

import numpy
import torch

UPSTREAM_COMMIT = "3de96596f16b9e6d23ba550c4c47de3479c9f14c"
SOURCE_BLOBS = {
    "miles/utils/types.py": "a4d6de01d3d500faae0039c462a2199a46e5958a",
    "miles/rollout/filter_hub/base_types.py": "96e887c66887cb677badcf1e3f3da5f9a2bf1357",
    "miles/rollout/filter_hub/common_filters.py": "498c63c01022ef7f0a80a649034c4873b777f9d8",
    "miles/rollout/fully_async_data_buffer.py": "58fd5cd83669d0f5cc2366eca453b40144e2c294",
    "miles/utils/weight_version.py": "480689607cbf67e6cb155d97e6d76ca409378200",
}
OLD_INTEGRATION_FIELDS = set("""
group_index index rollout_id prompt tokens multimodal_inputs multimodal_train_inputs
response response_length label reward loss_mask weight_versions rollout_log_probs
rollout_routed_experts rollout_indexer_topk remove_sample teacher_log_probs opd_reverse_kl
status metadata generate_function_path train_metadata adapter reward_spec routing_key
non_generation_time spec_info prefix_cache_info rollout_sampling_mask
""".split())


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def expect_error(kind: type[Exception], action: Callable[[], Any]) -> str:
    try:
        action()
    except kind as exc:
        return type(exc).__name__
    raise AssertionError(f"预期 {kind.__name__}，但没有抛出")


def load_sources(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    if sys.flags.optimize:
        raise RuntimeError("请不要用 python -O/-OO；本轮检查包含上游 assert 的正常执行语义")
    env: dict[str, Any] = {
        "Any": Any, "ABC": ABC, "abstractmethod": abstractmethod,
        "Namespace": argparse.Namespace, "Iterator": Iterator, "Callable": Callable,
        "asdict": asdict, "dataclass": dataclass, "field": field, "replace": replace,
        "Enum": Enum, "numpy": numpy, "torch": torch, "asyncio": asyncio,
        "logging": logging, "defaultdict": defaultdict, "re": re,
        # 未覆盖外围依赖：不做动态路径导入；所有被测样本均无 LoRA 和 sampling mask。
        "RolloutSamplingMask": type("UnusedSamplingMask", (), {}),
        "load_function": lambda value: value,
        "is_lora_enabled": lambda _args: False,
    }
    verified: dict[str, str] = {}
    for i, (relative, expected) in enumerate(SOURCE_BLOBS.items()):
        path = root / relative
        data = path.read_bytes()
        actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual != expected:
            raise ValueError(f"本篇源文件不匹配：{relative}: {actual} != {expected}")
        verified[relative] = actual
        tree = ast.parse(data.decode("utf-8"), filename=str(path))
        tree.body = [node for node in tree.body if not isinstance(node, (ast.Import, ast.ImportFrom))
                     and not (isinstance(node, ast.If) and isinstance(node.test, ast.Name)
                              and node.test.id == "TYPE_CHECKING")]
        name = f"miles_delta_probe_{i}"
        module = types.ModuleType(name)
        module.__dict__.update(env)
        module.__dict__["__name__"] = name
        # dataclass 解析字段时需要能找到所属模块。
        sys.modules[name] = module
        exec(compile(tree, str(path), "exec"), module.__dict__)
        env.update({k: v for k, v in module.__dict__.items() if not k.startswith("__")})
    return env, verified


async def run_checks(ns: dict[str, Any]) -> list[dict[str, Any]]:
    Sample, Call, Span = ns["Sample"], ns["WeightVersionsPerCall"], ns["WeightVersionSpan"]
    Buffer, Constructor, Entry = ns["DefaultDataBuffer"], ns["DataBufferConstructorInput"], ns["DataBufferInput"]
    staleness = ns["group_staleness"]
    checks: list[dict[str, Any]] = []

    def done(identifier: str, title: str, observed: Any) -> None:
        checks.append({"id": identifier, "status": "PASS", "title": title, "observed": observed})

    def sample(version: str | None = "9", reward: float | None = 1.0):
        return Sample(index=0, tokens=[10, 20], response_length=1, loss_mask=[1],
                      reward=reward, status=Sample.Status.COMPLETED,
                      weight_versions=[] if version is None else [Call([Span(version, 1, 2)])])

    def make_buffer(*, dynamic_filter=None, maximum=2, capacity=2, unused=None):
        args = argparse.Namespace(async_data_buffer_capacity_factor=1,
                                  rollout_batch_size=capacity, dynamic_sampling_filter_path=dynamic_filter,
                                  max_weight_staleness=maximum, reward_key=None)
        return Buffer(Constructor(args=args, unused_handler_fn=unused or (lambda _: None)))

    def entry(s):
        return Entry(prompt_group=[s], group=[s])

    require(set(Sample.__dataclass_fields__) == OLD_INTEGRATION_FIELDS, "字段集合不再相同")
    old = Sample(weight_versions=["3", "4"])
    err = expect_error(AttributeError, lambda: old.oldest_weight_version)
    done("P01", "字段名未变，但旧字符串版本列表不能被新消费者读取", {"fields": len(OLD_INTEGRATION_FIELDS), "error": err})

    mixed = Sample(tokens=[10, 20, 30, 40], response_length=3, loss_mask=[1, 1, 1],
                   weight_versions=[Call([Span("3", 1, 2), Span("4", 2, 4)])])
    mixed.validate()
    restored = Sample.from_dict(mixed.to_dict())
    require(restored.oldest_weight_version == 3 and len(restored.all_weight_version_spans) == 2, "区间往返失败")
    done("P02", "原生逐调用版本区间可以正确序列化往返", {"oldest": restored.oldest_weight_version})

    restored.strip_last_output_tokens(1, argparse.Namespace(decode=lambda ids: str(ids)))
    restored.validate()
    require(restored.all_weight_version_spans[-1].abs_end == 3, "尾部裁剪未更新区间")
    done("P03", "裁剪输出同步裁剪版本区间", {"spans": [asdict(x) for x in restored.all_weight_version_spans]})

    meta = {"output_token_logprobs": [[-1.0, 7, None]], "completion_tokens": 1,
            "weight_version": "9", "weight_versions": None}
    parsed_null = Call.from_meta_info(meta, output_end=2)
    parsed_empty = Call.from_meta_info({**meta, "weight_versions": []}, output_end=2)
    require(len(parsed_null.spans) == 1 and not parsed_empty.spans, "null/空列表处理发生变化")
    done("P04", "null 回退单数版本，而空列表产生空区间", {"null_spans": len(parsed_null.spans), "empty_spans": len(parsed_empty.spans)})

    custom_calls, unused_calls = [], []
    def fatal_filter(*_args, **_kwargs):
        custom_calls.append("called")
        raise RuntimeError("probe formal integrity failure")
    missing_buffer = make_buffer(dynamic_filter=fatal_filter, unused=unused_calls.append)
    await missing_buffer.put(entry(sample(reward=None)))
    require(not custom_calls and not unused_calls and not missing_buffer._buffer, "缺 reward 路径未按预期截断")
    done("P05", "缺 reward 的默认过滤抢先于自定义 fatal 检查", {"custom_calls": 0, "unused_calls": 0, "stored": 0})

    zero_buffer = make_buffer(dynamic_filter=fatal_filter)
    try:
        await zero_buffer.put(entry(sample(reward=0.0)))
    except RuntimeError as exc:
        require(str(exc) == "probe formal integrity failure", "抛出的不是探针异常")
    else:
        raise AssertionError("正常零分没有进入自定义检查")
    require(len(custom_calls) == 1, "自定义检查调用次数错误")
    done("P06", "合法零 reward 不会被误认为缺失", {"custom_calls": 1, "fatal_propagated": True})

    require(ns["DynamicFilterOutput"] is ns["FilterOutput"], "兼容别名失效")
    done("P07", "DynamicFilterOutput 仍是同一类型的兼容别名", True)

    partial = [sample("4"), sample(None)]
    require(staleness(partial, 10) == 6 and staleness([sample(None)], 10) is None, "缺版本处理变化")
    done("P08", "staleness 忽略缺版本成员，全部缺失则返回 None", {"partial": 6, "all_missing": None})

    negative_buffer = make_buffer(maximum=0)
    future = sample("12")
    await negative_buffer.put(entry(future))
    got = await asyncio.wait_for(negative_buffer.get(current_version=10), timeout=1)
    require(got.group[0] is future and staleness(got.group, 10) == -2, "负 lag 不再被放行")
    done("P09", "默认 buffer 的阈值不会拒绝负 lag", {"lag": -2, "returned": True})

    stale_drops = []
    metrics_buffer = make_buffer(maximum=2, unused=stale_drops.append)
    await metrics_buffer.put(entry(sample("5")))
    await metrics_buffer.put(entry(sample("9")))
    got = await asyncio.wait_for(metrics_buffer.get(current_version=10), timeout=1)
    metrics = metrics_buffer.get_metrics()
    require(staleness(got.group, 10) == 1 and metrics["rollout/fully_async/avg_staleness"] == 3, "指标口径变化")
    require(len(stale_drops) == 1, "stale 丢弃次数错误")
    done("P10", "avg_staleness 包含被扫描后拒绝的组", {"accepted_lag": 1, "reported_average": 3.0, "stale_drops": 1})

    bounded = make_buffer(capacity=1)
    await bounded.put(entry(sample("9")))
    waiter = asyncio.create_task(bounded.put(entry(sample("9"))))
    try:
        await asyncio.sleep(0)
        require(not waiter.done(), "buffer 满时生产者未阻塞")
        await asyncio.wait_for(bounded.get(current_version=10), timeout=1)
        await asyncio.wait_for(waiter, timeout=1)
        require(len(bounded._buffer) == 1, "消费后生产者未被唤醒")
    finally:
        if not waiter.done():
            waiter.cancel()
            await asyncio.gather(waiter, return_exceptions=True)
    done("P11", "正向对照：有界 buffer 的背压与唤醒", {"capacity": 1, "blocked_then_released": True})

    guard_args = argparse.Namespace(debug_rollout_only=False, debug_train_only=False,
                                    debug_skip_weight_update=False, update_weights_interval=1)
    ns["assert_samples_weight_version_sane"](guard_args, [sample(None)])
    default_error = expect_error(AssertionError, lambda: ns["assert_samples_weight_version_sane"](guard_args, [sample("default")]))
    done("P12", "版本合法性守卫检查已有区间，但空区间不触发", {"empty_passed": True, "default": default_error})

    guard = ns["assert_weight_version_is_published"]
    guard(guard_args, rollouts_since_publish=3)
    no_publish = expect_error(AssertionError, lambda: guard(guard_args, rollouts_since_publish=4))
    guard(guard_args, rollouts_since_publish=0)
    done("P13", "零更新跳发布的未来组合风险：第4次 get 触发通知守卫", {"allowed_without_notification": 3, "fourth": no_publish, "scope": "guard only; not integrated driver"})

    legacy = Sample.from_dict({"status": "completed", "weight_versions": ["3", "4"]})
    require(legacy.weight_versions == [] and legacy.oldest_weight_version is None, "旧 dump 已被推断为原生区间")
    require(legacy.legacy_weight_versions == ["3", "4"], "旧版本信息未保留")
    done("P14", "旧 dump 兼容保留旁路字段，但没有恢复可消费区间", {"legacy": legacy.legacy_weight_versions, "active_spans": 0})

    require(not hasattr(Buffer, "aclose") and not hasattr(ns["DataBuffer"], "aclose"), "当前 buffer 已有关闭 API")
    done("P15", "当前 DataBuffer 合同没有 aclose", True)
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--miles-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report: dict[str, Any] = {"upstream_commit": UPSTREAM_COMMIT, "python": platform.python_version(),
                              "torch": torch.__version__, "numpy": numpy.__version__,
                              "scope": "isolated CPU source execution; not Ray/SGLang/Megatron integration",
                              "substitutions": ["load_function: identity for callable/None", "is_lora_enabled: False", "RolloutSamplingMask: unused placeholder"]}
    try:
        ns, verified = load_sources(args.miles_root.resolve())
        report["verified_source_blobs"] = verified
        report["checks"] = asyncio.run(run_checks(ns))
        report["passed"] = len(report["checks"])
        report["failed"] = 0
        code = 0
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        report["failed"] = 1
        code = 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
