"""#6(a) 回放验收（Brief 切片 4；Codex 复核 R2 的口径）：用 B 线 22 条 Qwen3.6 尝试的真实 CC 请求，比较
"现状（vendored fold → translate）" 与 "RH2（fold → 只并约定提醒 → translate）" 在真实 Qwen3.6 模板下：
  1) 目标提醒（fold 出的 <system-reminder> text 块）不再清空历史 thinking；
  2) 真实压缩摘要指令（Codex 反例 dp_c8_reactive/.../messages_003.json）仍位于工具结果之外（独立 role:user）；
  3) 相邻请求前缀一致对数（训练行归属的代理指标）。
不跑模型，不改生产代码。用法（仓库根）：rh2/.venv/bin/python rh2/experiments/decision_package_20260924/p6_thinking/p6_smoosh_acceptance.py
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "rh2" / "src"))

from slime.agent.adapters.anthropic import _fold_mid_list_system_into_user, _translate_messages, _tools_to_chat_tools  # noqa: E402

from repoharness2.adapters.slime.rh2_anthropic_adapter import smoosh_system_reminders_into_last_tool_result  # noqa: E402

TOK_DIR = REPO / "runs" / "decision_package_20260924" / "p6_thinking" / "hf_tokenizer"
GW = REPO / "runs" / "base_probe_20260922" / "remote" / "gateway" / "q36"
CODEX_COMPACTION = REPO / "runs" / "decision_package_20260924" / "p8_9_10" / "remote" / "dp_c8_reactive" / "stub" / "requests" / "messages_003.json"
# v2（Codex 实施复核 CI2）：只取 22 条基座尝试（bp22-*，排除启动探针 wire-test-*）、只取生成请求（path=/v1/messages，
# 排除夹在账本里的 count_tokens 记录）；写新文件，不覆盖 v1。
OUT = REPO / "runs" / "decision_package_20260924" / "p6_thinking" / "smoosh_acceptance_v2.json"


def preprocess(body: dict, *, rh2: bool) -> dict:
    b = copy.deepcopy(body)
    _fold_mid_list_system_into_user(b)
    if rh2:
        smoosh_system_reminders_into_last_tool_result(b)
    return b


def render(tok, body: dict) -> list[int]:
    translated = _translate_messages(body.get("messages") or [], body.get("system"))
    tools = _tools_to_chat_tools(body.get("tools"))
    enc = tok.apply_chat_template(translated, tools=tools, tokenize=True, add_generation_prompt=True)
    return list(enc["input_ids"] if hasattr(enc, "__getitem__") and "input_ids" in enc else enc)


def think_blocks(tok, ids: list[int]) -> int:
    return tok.decode(ids).count("<think>")


def mid_system_count(body: dict) -> int:
    """会话中 role:system 条数（排除每个请求都有的 messages[1] Skill 清单）。插入 = 比上一请求多出来。"""
    msgs = body.get("messages") or []
    n = 0
    for i, m in enumerate(msgs):
        if i == 0 or not isinstance(m, dict) or m.get("role") != "system":
            continue
        if i == 1 and "skill" in json.dumps(m.get("content", ""), ensure_ascii=False).lower():
            continue
        n += 1
    return n


def common_prefix(a: list[int], b: list[int]) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def main() -> int:
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(str(TOK_DIR))
    attempts = sorted(p for p in GW.glob("bp22-*/requests.jsonl"))
    summary = {"scope": "22 bp22-* attempts, /v1/messages generation requests only (count_tokens + wire-test excluded)",
               "attempts": len(attempts), "requests": 0, "pairs": 0, "insertion_pairs": 0, "cleared_current": 0, "cleared_rh2": 0,
               "prompt_prefix_pairs_current": 0, "prompt_prefix_pairs_rh2": 0, "prompt_total_current": 0, "prompt_total_rh2": 0, "per_attempt": []}
    for path in attempts:
        reqs = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        reqs = [r for r in reqs if str(r.get("path", "/v1/messages")).split("?")[0] == "/v1/messages"]  # 只取生成请求
        bodies = [r.get("body", r) for r in reqs]
        prev = {"current": None, "rh2": None}
        summary["requests"] += len(bodies)
        rec = {"attempt": path.parent.name, "requests": len(bodies), "insertions": 0, "cleared_current": 0, "cleared_rh2": 0}
        for i, body in enumerate(bodies):
            ids = {v: render(tok, preprocess(body, rh2=(v == "rh2"))) for v in ("current", "rh2")}
            summary["prompt_total_current"] += len(ids["current"])
            summary["prompt_total_rh2"] += len(ids["rh2"])
            if i > 0:
                summary["pairs"] += 1
                for v in ("current", "rh2"):
                    if common_prefix(prev[v], ids[v]) == len(prev[v]):
                        summary[f"prompt_prefix_pairs_{v}"] += 1  # 上次 prompt 是本次 prompt 的前缀（不含 output，不是训练行归属）
                ins = mid_system_count(body) > mid_system_count(bodies[i - 1])
                if ins:
                    summary["insertion_pairs"] += 1
                    rec["insertions"] += 1
                # 清空 = 上一请求渲染里的 <think> 块在本请求渲染里少了（历史 thinking 被丢）；分插入对 / 全部对两口径
                for v in ("current", "rh2"):
                    if think_blocks(tok, ids[v]) < think_blocks(tok, prev[v]):
                        summary[f"cleared_{v}_any_pair"] = summary.get(f"cleared_{v}_any_pair", 0) + 1
                        if ins:
                            summary[f"cleared_{v}"] += 1
                            rec[f"cleared_{v}"] += 1
            prev = ids
        summary["per_attempt"].append(rec)
    # Codex R2 反例：真实压缩指令仍在工具结果之外
    cbody = json.loads(CODEX_COMPACTION.read_text(encoding="utf-8"))
    rh2_body = preprocess(cbody, rh2=True)
    translated = _translate_messages(rh2_body.get("messages") or [], rh2_body.get("system"))
    last_user = [m for m in translated if m.get("role") == "user"][-1]
    tool_msgs = [m for m in translated if m.get("role") == "tool"]
    summary["codex_compaction_request"] = {
        "summary_instruction_is_separate_user": "Respond with TEXT ONLY" in str(last_user.get("content", "")),
        "instruction_inside_any_tool_content": any("Respond with TEXT ONLY" in str(m.get("content", "")) for m in tool_msgs),
        "roles_rh2": [m.get("role") for m in translated], "n_messages_raw": len(cbody.get("messages") or []),
    }
    OUT.write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_attempt"}, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
