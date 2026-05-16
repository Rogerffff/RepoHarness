from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import sglang as sgl
from transformers import AutoTokenizer

from repo_harness_verl.tool_parser import parse_hermes_tool_calls

MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
BACKEND = "sglang"
IMAGE = "verlai/verl:sgl056.latest"
RUN_DIR = Path("/workspace/RepoHarness/runs") / ("stage12b-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
PROBE_DIR = RUN_DIR / "tool_format_probe"
TOOL_PROTOCOL = """You are RepoHarness software engineering agent.

You must obey this exact output grammar.

When using a tool, your entire assistant message must be exactly:
<tool_call>
{"name": "read_file", "arguments": {"path": "calculator.py"}}
</tool_call>

The literal line <tool_call> is mandatory.
The literal line </tool_call> is mandatory.
Do not output bare JSON.
Do not output Markdown code fences.
Do not add explanation before or after the block.

Allowed tools: read_file, grep, edit_file, git_diff.
Arguments must be a JSON object.

Allowed examples:
<tool_call>
{"name": "grep", "arguments": {"query": "divide", "root": "."}}
</tool_call>
<tool_call>
{"name": "edit_file", "arguments": {"path": "calculator.py", "old_text": "return left / right", "new_text": "return 1"}}
</tool_call>

For final answer tasks only, do not use a tool_call block. Write a short plain English final answer.
Do not use absolute paths. Do not mention hidden verifier, gold patch, reward metadata, or evaluator-only information.
""".strip()
PROMPTS = [
    {"id": "read_file_1", "category": "read_file", "user": "Read calculator.py before editing. Output only the tool call."},
    {"id": "read_file_2", "category": "read_file", "user": "Inspect tests/test_calculator.py. Output only the tool call."},
    {"id": "read_file_3", "category": "read_file", "user": "Open README.md to understand the task. Output only the tool call."},
    {"id": "grep_1", "category": "grep", "user": "Search for the symbol divide in the repository. Output only the tool call."},
    {"id": "grep_2", "category": "grep", "user": "Search for the text division by zero. Output only the tool call."},
    {"id": "edit_file_1", "category": "edit_file", "user": "Patch calculator.py by replacing return left / right with return 1. Output only the tool call."},
    {"id": "edit_file_2", "category": "edit_file", "user": "Patch notes.py by replacing return False with return True. Output only the tool call."},
    {"id": "edit_file_3", "category": "edit_file", "user": "Patch helper.py by replacing pass with return None. Output only the tool call."},
    {"id": "final_1", "category": "final", "user": "The patch is complete and tests passed. Give final answer only."},
    {"id": "final_2", "category": "final", "user": "No more tools are needed. Summarize completion in one sentence."},
]


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def logprobs_from_output(output: dict) -> list[float]:
    values = ((output.get("meta_info") or {}).get("output_token_logprobs") or [])
    result = []
    for item in values:
        if isinstance(item, (list, tuple)) and item:
            result.append(0.0 if item[0] is None else float(item[0]))
    return result


def main() -> None:
    os.environ.setdefault("HF_HOME", "/workspace/hf_cache")
    PROBE_DIR.mkdir(parents=True, exist_ok=True)
    (PROBE_DIR / "tool_protocol_prompt_v0.txt").write_text(TOOL_PROTOCOL + "\n", encoding="utf-8")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    engine = sgl.Engine(
        model_path=MODEL_ID,
        tp_size=1,
        context_length=4096,
        mem_fraction_static=0.55,
        attention_backend="flashinfer",
        disable_cuda_graph=True,
    )
    prompts = []
    raw_generations = []
    parsed_rows = []
    diagnostics_rows = []
    try:
        for index, item in enumerate(PROMPTS):
            messages = [
                {"role": "system", "content": TOOL_PROTOCOL},
                {"role": "user", "content": item["user"]},
            ]
            prompt_ids = tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True)
            prompts.append({**item, "prompt_ids_length": len(prompt_ids)})
            output = engine.generate(
                input_ids=prompt_ids,
                sampling_params={"max_new_tokens": 192, "temperature": 0.0, "top_p": 1.0},
                return_logprob=True,
                logprob_start_len=0,
            )
            text = str(output.get("text") or "")
            output_ids = [int(token_id) for token_id in output.get("output_ids") or []]
            output_logprobs = logprobs_from_output(output)
            parsed = parse_hermes_tool_calls(text, turn=index)
            parse_success = parsed.success and (bool(parsed.tool_calls) if item["category"] != "final" else not parsed.tool_calls)
            raw_generations.append(
                {
                    **item,
                    "text": text,
                    "output_ids": output_ids,
                    "output_logprobs": output_logprobs,
                    "finish_reason": (output.get("meta_info") or {}).get("finish_reason"),
                }
            )
            parsed_rows.append(
                {
                    **item,
                    "parse_success": parse_success,
                    "parsed_content": parsed.content,
                    "tool_calls": parsed.tool_calls,
                }
            )
            diagnostics_rows.append({**item, "diagnostics": parsed.diagnostics})
            print(item["id"], "success" if parse_success else "failed", text[:160].replace("\n", " "), flush=True)
    finally:
        engine.shutdown()

    write_jsonl(PROBE_DIR / "prompts.jsonl", prompts)
    write_jsonl(PROBE_DIR / "raw_generations.jsonl", raw_generations)
    write_jsonl(PROBE_DIR / "parsed_tool_calls.jsonl", parsed_rows)
    write_jsonl(PROBE_DIR / "parser_diagnostics.jsonl", diagnostics_rows)
    success_rows = [row for row in parsed_rows if row["parse_success"]]
    covered = {row["category"] for row in success_rows}
    required_covered = {"read_file", "edit_file", "final"}.issubset(covered)
    summary = {
        "schema_version": "repo_harness_stage12b_tool_format_probe_summary_v0",
        "model_id": MODEL_ID,
        "backend": BACKEND,
        "image": IMAGE,
        "run_dir": str(RUN_DIR),
        "prompt_count": len(PROMPTS),
        "parse_success_count": len(success_rows),
        "required_categories_covered": required_covered,
        "can_continue_to_real_episode_smoke": len(success_rows) >= 6 and required_covered,
        "covered_categories": sorted(covered),
        "failure_examples": [row for row in parsed_rows if not row["parse_success"]][:5],
    }
    (PROBE_DIR / "tool_format_probe_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), flush=True)


if __name__ == "__main__":
    main()
