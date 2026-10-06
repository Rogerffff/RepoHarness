"""独立核对 #6 回放分母与 a2 对真实 CC 压缩指令的角色改写。

只读既有输入，使用本地 tokenizer；默认输出 stdout。--out 只创建新工件，
拒绝覆盖已有文件。不启动模型、CC、Docker 或网络请求。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import sys
from collections import Counter
from pathlib import Path

REPO = next(
    p for p in Path(__file__).resolve().parents
    if (p / "rh2/src/slime/agent/trajectory.py").is_file()
)
P6 = REPO / "runs/decision_package_20260924/p6_thinking"
GW = REPO / "runs/base_probe_20260922/remote/gateway"
COMPACTION = Path(
    "runs/decision_package_20260924/p8_9_10/remote/"
    "dp_c8_reactive/stub/requests/messages_003.json"
)


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    sys.path.insert(0, str(REPO / "rh2/src"))

    from slime.agent.adapters.anthropic import (
        _fold_mid_list_system_into_user,
        _tools_to_chat_tools,
        _translate_messages,
    )
    from transformers import AutoTokenizer

    script = REPO / "rh2/experiments/decision_package_20260924/p6_thinking/p6_replay.py"
    spec = importlib.util.spec_from_file_location("reviewed_p6_replay", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prov = json.loads((P6 / "provenance.json").read_text())
    pairs = read_jsonl(P6 / "replay_pairs.jsonl")
    coverage = read_jsonl(P6 / "replay_coverage.jsonl")
    turns = read_jsonl(P6 / "replay_turns.jsonl")
    raw_turns, exclusions = [], []
    for attempt in prov["attempts"]:
        raw_turns.extend(read_jsonl(GW / "q36_adapter" / f"{attempt}.turns.jsonl"))
        for row in read_jsonl(GW / "q36" / attempt / "requests.jsonl"):
            if row.get("seq") is None or not isinstance(row.get("body"), dict) or "rejected" in row:
                exclusions.append({"attempt": attempt, "path": row.get("path")})
    current = {(p["attempt"], p["seq_to"]): p for p in pairs if p["variant"] == "current"}
    drops = {key for key, p in current.items() if p["thinking_only_blocks"]}
    forks = {
        variant: {
            (c["attempt"], f["turn_index"])
            for c in coverage if c["variant"] == variant for f in c["fork_events"]
        }
        for variant in ("current", "b_preserve")
    }
    variants = {}
    for variant in module.VARIANTS:
        vs = [x for x in coverage if x["variant"] == variant]
        vt = [x for x in turns if x["variant"] == variant]
        vp = [x for x in pairs if x["variant"] == variant]
        variants[variant] = {
            "turns": len(vt),
            "pairs": len(vp),
            "unique_pairs": len({(p["attempt"], p["seq_from"], p["seq_to"]) for p in vp}),
            "thinking_drop_pairs": sum(p["thinking_only_blocks"] > 0 for p in vp),
            "training_rows": sum(c["training_rows"] for c in vs),
            "turns_generated": sum(c["turns_generated"] for c in vs),
            "turns_trained": sum(c["turns_trained"] for c in vs),
            "trainable_tokens_total": sum(c["trainable_tokens_total"] for c in vs),
            "input_tokens_total": sum(c["input_tokens_total"] for c in vs),
        }
    extra_removed = []
    for attempt, seq in sorted((forks["current"] - forks["b_preserve"]) - drops):
        p = current[(attempt, seq)]
        prev = current[(attempt, seq - 1)]
        extra_removed.append({
            "attempt": attempt,
            "seq_to": seq,
            "cause": p["cause"],
            "insertion_kinds": p["insertion_kinds"],
            "previous_pair_thinking_drop": prev["thinking_only_blocks"] > 0,
            "previous_pair_insertion_kinds": prev["insertion_kinds"],
            "first_diff": p["other_diff_examples"][0],
        })

    tok = AutoTokenizer.from_pretrained(
        str(P6 / "hf_tokenizer"), local_files_only=True, trust_remote_code=False
    )
    raw_body = json.loads((REPO / COMPACTION).read_text())
    instruction = raw_body["messages"][-1]["content"][-1]["text"]
    assert instruction.startswith("CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.")
    rendered = {}
    for variant, only_reminder in (("current", None), ("a_smoosh", True), ("a2_smoosh_all_text", False)):
        body = copy.deepcopy(raw_body)
        _fold_mid_list_system_into_user(body)
        moved = 0 if only_reminder is None else module.smoosh_into_last_tool_result(
            body, only_system_reminder=only_reminder
        )
        translated = _translate_messages(body["messages"], body.get("system"))
        text = tok.apply_chat_template(
            translated, tools=_tools_to_chat_tools(body.get("tools")),
            tokenize=False, add_generation_prompt=True,
        )
        pos = text.index(instruction.strip())
        rendered[variant] = {
            "moved_blocks": moved,
            "instruction_roles": [
                m["role"] for m in translated if instruction.strip() in (m.get("content") or "")
            ],
            "last_query_index": module.last_query_index(translated),
            "roles_tail": [m["role"] for m in translated[-4:]],
            "instruction_inside_tool_response": text.rfind("<tool_response>", 0, pos)
            > text.rfind("</tool_response>", 0, pos),
            "instruction_text_present": instruction.strip() in text,
            "rendered_before_instruction": text[max(0, pos - 100):pos],
            "instruction_head": instruction[:110],
            "rendered_after_instruction": text[pos + len(instruction.strip()):][:100],
        }
    assert rendered["current"]["instruction_roles"] == ["user"]
    assert rendered["a_smoosh"]["instruction_roles"] == ["user"]
    assert rendered["a2_smoosh_all_text"]["instruction_roles"] == ["tool"]
    assert not rendered["a_smoosh"]["instruction_inside_tool_response"]
    assert rendered["a2_smoosh_all_text"]["instruction_inside_tool_response"]

    out = {
        "scope": "CPU read-only source/evidence audit; real local template; no model behavior claim",
        "source_hash_matches_recorded_replay": {
            p: sha(REPO / p) == recorded for p, recorded in prov["production_files_sha256"].items()
        },
        "denominators": {
            "attempts": len(prov["attempts"]), "raw_generation_turns": len(raw_turns),
            "raw_output_tokens_sum": sum(t["output_tokens"] for t in raw_turns),
            "finish_reasons": dict(Counter(t.get("finish_reason") for t in raw_turns)),
            "excluded_gateway_rows": exclusions,
        },
        "variants": variants,
        "replay_limitations": {
            "output_ids": prov["output_ids_note"],
            "coverage_max_sample_tokens": 0,
            "scope_note": "Amounts are replay outputs, not proof of original sampled token identity or all production training stages.",
        },
        "fork_attribution": {
            "current_forks": len(forks["current"]),
            "thinking_drop_pairs": len(drops),
            "drop_pairs_also_current_fork": len(drops & forks["current"]),
            "preserve_forks": len(forks["b_preserve"]),
            "extra_removed_forks_not_at_drop_pair": extra_removed,
        },
        "real_compaction_scope": {
            "source": str(COMPACTION), "source_sha256": sha(REPO / COMPACTION),
            "instruction_chars": len(instruction),
            "instruction_sha256": hashlib.sha256(instruction.encode()).hexdigest(),
            "variants": rendered,
        },
    }
    serialized = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x") as handle:
            handle.write(serialized)
    else:
        print(serialized, end="")


if __name__ == "__main__":
    main()
