"""离线：把桩落盘的首请求体按 vendored adapter 的同一条渲染路径算成 prompt token 数。

路径与生产 `BaseAdapter._run_turn` 相同：`_fold_mid_list_system_into_user` → `_translate_messages` +
`_tools_to_chat_tools` → `_render_token_ids(apply_chat_template, add_generation_prompt=True)`。
tokenizer / chat template 用本机 HF 缓存里的 Qwen/Qwen3-30B-A3B（**代理**：探针实际基座是 Qwen3-Coder-30B-A3B /
Qwen3.6-35B-A3B，正式训练基座未定；不同模板对工具的渲染不同，数字只作量级与相对比较）。

    HF_HUB_OFFLINE=1 python tokens_p8910.py <remote_dir> <out_json> [--model Qwen/Qwen3-30B-A3B]
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path


def render_counts(body: dict, tok) -> dict:
    from slime.agent.adapters.anthropic import _fold_mid_list_system_into_user, _tools_to_chat_tools, _translate_messages
    from slime.agent.adapters.common import _render_token_ids

    b = copy.deepcopy(body)
    _fold_mid_list_system_into_user(b)
    translated = _translate_messages(b.get("messages") or [], b.get("system"))
    tools_schema = _tools_to_chat_tools(b.get("tools"))
    full = len(_render_token_ids(translated, tok, tools=tools_schema, add_generation_prompt=True))
    no_tools = len(_render_token_ids(translated, tok, tools=None, add_generation_prompt=True))
    return {"prompt_tokens": full, "prompt_tokens_without_tools": no_tools, "tools_tokens": full - no_tools,
            "n_tools": len(b.get("tools") or [])}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("remote_dir")
    ap.add_argument("out_json")
    ap.add_argument("--model", default="Qwen/Qwen3-30B-A3B")
    ap.add_argument("--extra-files", nargs="*", default=[], help="另外要渲染的请求体（相对 remote_dir），如 dp_r8_zero/stub/requests/messages_002.json")
    ns = ap.parse_args()
    from transformers import AutoTokenizer

    tok = AutoTokenizer.from_pretrained(ns.model)
    out: dict = {"tokenizer": ns.model, "note": "proxy tokenizer/template; same render path as vendored adapter", "runs": {}}
    for run in sorted(Path(ns.remote_dir).glob("dp_*")):
        p = run / "stub" / "requests" / "messages_000.json"
        if not p.exists():
            continue
        body = json.loads(p.read_bytes())
        rec = render_counts(body, tok)
        # 分项：只去掉非核心工具（保持其余不变）的渲染，用来把"工具"与"清单/system"拆开
        core = {"Bash", "Read", "Edit", "Write", "NotebookEdit"}
        b2 = copy.deepcopy(body)
        b2["tools"] = [t for t in (b2.get("tools") or []) if t.get("name") in core]
        rec["prompt_tokens_core_tools_only_same_messages"] = render_counts(b2, tok)["prompt_tokens"]
        out["runs"][run.name] = rec
    out["extra_files"] = {}
    for rel in ns.extra_files:
        body = json.loads((Path(ns.remote_dir) / rel).read_bytes())
        out["extra_files"][rel] = render_counts(body, tok)
    Path(ns.out_json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for k, v in out["extra_files"].items():
        print(f"{k:50s} {v}")
    for k, v in out["runs"].items():
        print(f"{k:18s} {v}")


if __name__ == "__main__":
    main()
