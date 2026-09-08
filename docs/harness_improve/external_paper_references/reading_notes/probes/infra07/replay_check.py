#!/usr/bin/env python3
"""固定 token 的离线比较器，以及只读 SGLang prefill / 本地 HF 打分入口。

只作诊断，不接训练、不更新权重、不自动清缓存；成功不代表 GPU 或模型已被认证。
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import math
import os
from pathlib import Path
import statistics
import sys
import time
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SCHEMA = "infra07.fixed-token-logprobs.v1"
RAW = {"kind": "full_vocab", "temperature": 1.0, "processors": []}
EXIT = {"PASS": 0, "FAIL": 1, "INCOMPARABLE": 2, "INSUFFICIENT": 3}


class ContractError(ValueError):
    """输入材料不足以形成声明的配对比较。"""


def read_json(path: str | Path) -> dict[str, Any]:
    def reject(value: str) -> None:
        raise ContractError(f"JSON 含非有限常量：{value}")
    with open(path, encoding="utf-8") as stream:
        return json.load(stream, parse_constant=reject)


def write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def integer(x: Any) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not isinstance(doc, dict):
        raise ContractError("输入根必须是 JSON object")
    if doc.get("schema") != SCHEMA:
        raise ContractError("未知 schema")
    contract = doc.get("contract", {})
    if not isinstance(contract, dict):
        raise ContractError("contract 必须是 object")
    for name in ("weights", "tokenizer", "context"):
        if not isinstance(contract.get(name), str) or not contract[name]:
            raise ContractError(f"缺少 contract.{name}；这些是操作者声明，不是权重证明")
    prob = contract.get("probability", {})
    if not isinstance(prob, dict):
        raise ContractError("probability 必须是 object")
    if prob.get("kind") not in {"full_vocab", "fixed_retained_support"}:
        raise ContractError("概率种类必须明确为 full_vocab 或 fixed_retained_support")
    temp = prob.get("temperature")
    if isinstance(temp, bool) or not isinstance(temp, (int, float)) or not math.isfinite(temp) or temp <= 0:
        raise ContractError("本比较协议要求正温度；贪心 delta 分布须另作实验")
    if not isinstance(prob.get("processors"), list):
        raise ContractError("必须显式记录 processors 列表")
    rows = doc.get("records")
    if not isinstance(rows, list):
        raise ContractError("records 不是列表")
    found: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ContractError("record 必须是 object")
        key = row.get("id")
        if not isinstance(key, str) or not key or key in found:
            raise ContractError("记录身份缺失或重复")
        ids, pos, mask, lp = (row.get(k) for k in ("input_ids", "positions", "mask", "logprobs"))
        if not isinstance(ids, list) or len(ids) < 2 or any(not integer(t) or t < 0 for t in ids):
            raise ContractError(f"{key}: token IDs 无效")
        if not all(isinstance(x, list) for x in (pos, mask, lp)) or not (len(pos) == len(mask) == len(lp)):
            raise ContractError(f"{key}: positions/mask/logprobs 长度不齐")
        if any(not integer(p) or not 1 <= p < len(ids) for p in pos) or pos != sorted(set(pos)):
            raise ContractError(f"{key}: positions 必须递增且唯一；位置 0 没有本协议定义的条件概率")
        if any(type(m) not in (int, bool) or m not in (0, 1) for m in mask):
            raise ContractError(f"{key}: mask 不是 0/1")
        for m, value in zip(mask, lp, strict=True):
            if value is None and not m:
                continue
            if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ContractError(f"{key}: 非有限或缺失 logprob；不静默填零")
            if value > 1e-6:
                raise ContractError(f"{key}: logprob 显著大于零")
        labels = row.get("weight_labels")
        if not isinstance(labels, list) or len(labels) != len(pos) or any(not isinstance(v, str) or not v for v in labels):
            raise ContractError(f"{key}: 逐打分位置 weight_labels 缺失")
        if prob["kind"] == "fixed_retained_support":
            supports = row.get("support_ids")
            if not isinstance(supports, list) or len(supports) != len(pos):
                raise ContractError(f"{key}: 缺真实采样保留集；top_logprobs 列表不能代替")
            for p, support in zip(pos, supports, strict=True):
                if not isinstance(support, list) or not support or any(not integer(t) or t < 0 for t in support):
                    raise ContractError(f"{key}: 支持集无效")
                if len(set(support)) != len(support) or ids[p] not in support:
                    raise ContractError(f"{key}: 支持集重复或目标不在支持集")
        found[key] = row
    return found


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    where = (len(ordered) - 1) * q
    left = int(where)
    right = min(left + 1, len(ordered) - 1)
    return ordered[left] + (ordered[right] - ordered[left]) * (where - left)


def compare(reference: dict[str, Any], candidate: dict[str, Any], *, atol: float, ratio_low: float = 0.8, ratio_high: float = 1.2) -> dict[str, Any]:
    if not math.isfinite(atol) or atol < 0 or not 0 < ratio_low < ratio_high or not math.isfinite(ratio_high):
        raise ValueError("容差或 ratio 诊断区间无效")
    report: dict[str, Any] = {
        "schema": "infra07.comparison.v1", "atol": atol,
        "meaning": "只检查给定数据在声明合同下的配对一致性；不验证权重标签真实、全部词表、路由或训练正确性",
        "reference_execution": reference.get("execution", {}) if isinstance(reference, dict) else {},
        "candidate_execution": candidate.get("execution", {}) if isinstance(candidate, dict) else {},
    }
    try:
        left, right = validate(reference), validate(candidate)
        if reference["contract"] != candidate["contract"]:
            raise ContractError("contract 不同：先解决权重/上下文/概率语义，不能当作数值误差")
        if set(left) != set(right):
            raise ContractError("两侧记录集合不同；禁止静默取交集")
        deltas: list[float] = []
        cases: list[dict[str, Any]] = []
        for key in sorted(left):
            a, b = left[key], right[key]
            for field in ("input_ids", "positions", "mask", "weight_labels", "support_ids", "routing_ids", "position_ids", "attention_mask", "segment_ids"):
                if a.get(field) != b.get(field):
                    raise ContractError(f"{key}: {field} 不同；不能按数组下标猜测对应")
            ds = [y - x for x, y, m in zip(a["logprobs"], b["logprobs"], a["mask"], strict=True) if m]
            deltas.extend(ds)
            cases.append({"id": key, "active_tokens": len(ds), "max_abs": max(map(abs, ds), default=None),
                          "selected_token_log_ratio_sum": math.fsum(ds) if ds else None})
        report["cases"] = cases
        if not deltas:
            return {**report, "status": "INSUFFICIENT", "active_tokens": 0, "reason": "没有可比较的有效 token"}
        absolute = list(map(abs, deltas))
        peak = max(deltas)
        stable_weights = [math.exp(d - peak) for d in deltas]
        ess = math.fsum(stable_weights) ** 2 / (len(deltas) * math.fsum(w * w for w in stable_weights))
        report.update({"active_tokens": len(deltas), "mean_signed": statistics.fmean(deltas),
                       "mean_abs": statistics.fmean(absolute), "p99_abs": quantile(absolute, .99),
                       "max_abs": max(absolute), "normalized_ratio_ess": ess,
                       "ratio_interval": [ratio_low, ratio_high],
                       "ratio_outside_fraction": sum(d < math.log(ratio_low) or d > math.log(ratio_high) for d in deltas) / len(deltas),
                       "status": "PASS" if max(absolute) <= atol else "FAIL"})
        return report
    except (ContractError, TypeError, KeyError) as exc:
        return {**report, "status": "INCOMPARABLE", "reason": str(exc)}


def contract(weights: str, tokenizer: str) -> dict[str, Any]:
    return {"weights": weights, "tokenizer": tokenizer, "context": "causal-text-no-padding-position0-v1", "probability": copy.deepcopy(RAW)}


def cases_from(path: str | Path) -> list[dict[str, Any]]:
    cases = read_json(path).get("cases")
    if not isinstance(cases, list) or not cases:
        raise ContractError("需要非空 cases 列表")
    rows = []
    for case in cases:
        if not isinstance(case, dict) or set(case) - {"id", "input_ids", "positions", "mask"}:
            raise ContractError("capture cases 只支持 id/input_ids/positions/mask；复杂注意力或多模态必须另写适配器")
        ids = case.get("input_ids", [])
        pos = case.get("positions", list(range(1, len(ids))))
        rows.append({"id": case.get("id"), "input_ids": ids, "positions": pos,
                     "mask": case.get("mask", [1] * len(pos)), "logprobs": [-1.0] * len(pos),
                     "weight_labels": ["validation-only"] * len(pos)})
    validate({"schema": SCHEMA, "contract": contract("validation-only", "validation-only"), "records": rows})
    return rows


def score_sglang_case(endpoint: str, case: dict[str, Any], *, weights: str, timeout: float, api_key: str | None = None) -> dict[str, Any]:
    """请求已启动、已冻结的服务。无重试、无 flush、无训练写操作。"""
    payload = {"input_ids": case["input_ids"], "return_logprob": True, "logprob_start_len": 0,
               "sampling_params": {"max_new_tokens": 0, "temperature": 1.0, "top_p": 1.0, "top_k": -1, "min_p": 0.0}}
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = "Bearer " + api_key
    request = Request(endpoint.rstrip("/") + "/generate", json.dumps(payload).encode(), headers, method="POST")
    start = time.perf_counter()
    with urlopen(request, timeout=timeout) as reply:
        result = json.loads(reply.read())
    if not isinstance(result, dict) or not isinstance(result.get("meta_info"), dict):
        raise ContractError("服务响应不是单个标准 meta_info object")
    meta = result["meta_info"]
    pairs = meta.get("input_token_logprobs")
    if not isinstance(pairs, list) or len(pairs) != len(case["input_ids"]):
        raise ContractError("服务未返回从位置0开始、与输入等长的 input_token_logprobs；不猜测 shift")
    if any(not isinstance(p, list) or len(p) < 2 for p in pairs):
        raise ContractError("input_token_logprobs 单项形状不符")
    if [p[1] for p in pairs] != case["input_ids"]:
        raise ContractError("服务打分 token IDs 与请求不一致")
    row = {**case, "logprobs": [pairs[p][0] for p in case["positions"]],
           "weight_labels": [weights] * len(case["positions"]),
           "observed_server_weight_version": meta.get("weight_version"),
           "elapsed_seconds": time.perf_counter() - start}
    validate({"schema": SCHEMA, "contract": contract(weights, "capture-validation"), "records": [row]})
    return row


def capture(args: argparse.Namespace) -> None:
    parsed = urlparse(args.endpoint)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username:
        raise ContractError("endpoint 必须为无内嵌凭据的 http(s) 服务根路径")
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"} and not args.allow_remote:
        raise ContractError("非本地服务需要 --allow-remote；必须是你有权调用的冻结服务")
    if args.repeats < 1 or args.concurrency < 1 or args.timeout <= 0:
        raise ContractError("repeats/concurrency/timeout 必须为正")
    rows = []
    for repeat in range(args.repeats):
        for case in cases_from(args.cases):
            rows.append({**case, "id": f"{case['id']}::r{repeat}"})
    key = os.environ.get("INFRA07_API_KEY")
    def work(row: dict[str, Any]) -> dict[str, Any]:
        return score_sglang_case(args.endpoint, row, weights=args.weights, timeout=args.timeout, api_key=key)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        records = list(pool.map(work, rows))
    write_json(args.output, {"schema": SCHEMA, "contract": contract(args.weights, args.tokenizer),
        "execution": {"backend": "sglang-prefill-http", "concurrency": args.concurrency, "repeats": args.repeats,
                      "weights_identity_basis": "operator_declared_not_tensor_verified", "quiescent_server_required": True,
                      "warning": "客户端并发不等于实际 GPU batch；本入口不是 decode replay，也不是 Megatron trainer"},
        "records": records})


def score_hf(args: argparse.Namespace) -> None:
    """可选的单进程 HF 对照；只从本地读模型，不执行 remote code。"""
    import torch
    from transformers import AutoModelForCausalLM
    model = AutoModelForCausalLM.from_pretrained(args.model_dir, local_files_only=True, trust_remote_code=False,
                                               torch_dtype=getattr(torch, args.dtype), attn_implementation="eager").to(args.device).eval()
    records = []
    for case in cases_from(args.cases):
        tokens = torch.tensor([case["input_ids"]], dtype=torch.long, device=args.device)
        with torch.no_grad():
            logits = model(input_ids=tokens, attention_mask=torch.ones_like(tokens), use_cache=False).logits
            pos = torch.tensor(case["positions"], dtype=torch.long, device=args.device)
            selected = logits[0, pos - 1].float().log_softmax(-1).gather(1, tokens[0, pos, None]).squeeze(-1)
        records.append({**case, "id": case["id"] + "::r0", "logprobs": selected.double().cpu().tolist(),
                        "weight_labels": [args.weights] * len(case["positions"])})
    doc = {"schema": SCHEMA, "contract": contract(args.weights, args.tokenizer),
           "execution": {"backend": "hf-eager-local", "dtype": args.dtype, "device": args.device,
                         "warning": "不是项目 Megatron、FSDP、TP/CP 或 MoE routing replay 实现；没有证明与其等价"}, "records": records}
    validate(doc)
    write_json(args.output, doc)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("compare")
    p.add_argument("reference"); p.add_argument("candidate"); p.add_argument("--atol", type=float, required=True)
    p.add_argument("--output", required=True)
    p = sub.add_parser("capture-sglang")
    p.add_argument("--endpoint", default="http://127.0.0.1:30000")
    p.add_argument("--allow-remote", action="store_true")
    p.add_argument("--concurrency", type=int, default=1); p.add_argument("--repeats", type=int, default=1)
    p.add_argument("--timeout", type=float, default=120)
    for command in (p,):
        for name in ("cases", "weights", "tokenizer", "output"):
            command.add_argument("--" + name, required=True)
    p = sub.add_parser("score-hf")
    for name in ("cases", "weights", "tokenizer", "output", "model-dir"):
        p.add_argument("--" + name, required=True)
    p.add_argument("--device", default="cpu")
    p.add_argument("--dtype", choices=["float32", "bfloat16", "float16"], default="float32")
    args = parser.parse_args()
    try:
        if args.command == "compare":
            result = compare(read_json(args.reference), read_json(args.candidate), atol=args.atol)
            write_json(args.output, result)
            print(result["status"])
            return EXIT[result["status"]]
        if args.command == "capture-sglang":
            capture(args)
        else:
            score_hf(args)
        return 0
    except (ValueError, OSError, ImportError, KeyError, TypeError) as exc:
        print(f"未完成：{type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
