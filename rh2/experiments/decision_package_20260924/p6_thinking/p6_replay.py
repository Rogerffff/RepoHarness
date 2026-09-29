#!/usr/bin/env python3
"""#6 决策包事实采集：CC 中列 role:system 提醒 → Qwen3.6 thinking 周期性清空，逐轮回放。

只读输入：
  runs/base_probe_20260922/remote/gateway/q36/<attempt>/requests.jsonl   （CC 发出的请求体，网关留证）
  runs/base_probe_20260922/remote/gateway/q36_adapter/<attempt>.turns.jsonl（探针 adapter 的逐轮记录：
      prompt_tokens = len(turn.prompt_ids)、raw_output、parsed = manager_message）
  runs/decision_package_20260924/p6_thinking/hf_tokenizer/                （Qwen/Qwen3.6-35B-A3B 固定 revision
      的 tokenizer 文件，不含权重）

渲染路径：
  current   —— 与生产同一组函数：AnthropicAdapter._preprocess_body（= _fold_mid_list_system_into_user）
               → AnthropicAdapter._translate（= _translate_messages + _tools_to_chat_tools）
               → common._render_token_ids（apply_chat_template, tokenize=True, add_generation_prompt=True）。
  a_smoosh  —— 候选 (a)：fold 之后、translate 之前，把同条 user 消息里以 <system-reminder> 开头的 text 块
               并入最后一个 tool_result（照 CC utils/messages.ts smooshSystemReminderSiblings /
               smooshIntoToolResult 的规则：字符串内容 trim 后以 "\\n\\n" 连接）。
  a2_smoosh_all_text —— (a) 的放宽变体：tool_result 所在消息里的**全部** text 块都并入（覆盖 Skill 正文）。
  b_preserve —— 候选 (b)：渲染时向模板传 preserve_thinking=True（Qwen3.6 模板的开关名）。
  c_no_task_reminder —— 候选 (c) 的可回放部分：从请求体删掉 Task 提醒这类 role:system 消息后照 current 渲染
               （工具清单不变；去掉 Task* 工具对工具段 token 的影响另行单独计量）。

对每个变体：逐轮渲染 token、相邻请求前缀比较（prompt 级与“持有 token = prompt_n + output_n”级，后者即
TrajectoryManager 的 CLEAN 判据）、按 <|im_start|> 分块定位差异并判定是否“只差 thinking”、再把整条会话喂给
vendored TrajectoryManager（fork_threshold=0，与 bringup.FORK_THRESHOLD_TOKENS 一致）并用生产的
turn_identity.export_leaf_identity_spans_with_coverage 取 turn_coverage（training_rows / fork_events）。

注意（口径）：output_ids 没有留证，这里用 tokenizer 对 raw_output 重编码代替（逐轮核对长度 = 记录的
output_tokens）；回放是“同一段已记录会话的重渲染”，不是在候选修法下重跑模型或 CC。

不修改生产代码与 vendored 目录；只写 runs/decision_package_20260924/p6_thinking/。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[4]
RH2 = REPO / "rh2"
sys.path.insert(0, str(RH2 / "src"))

GW = REPO / "runs/base_probe_20260922/remote/gateway"
OUT = REPO / "runs/decision_package_20260924/p6_thinking"
TOK_DIR = OUT / "hf_tokenizer"
HF_REPO = "Qwen/Qwen3.6-35B-A3B"
HF_REVISION = "995ad96eacd98c81ed38be0c5b274b04031597b0"

VARIANTS = ["current", "a_smoosh", "a2_smoosh_all_text", "b_preserve", "c_no_task_reminder"]

TASK_REMINDER_PREFIX = "The task tools haven't been used recently"
FILE_MODIFIED_RE = re.compile(r"^Note: .* was modified, either by the user or by a linter", re.S)
SKILL_LISTING_PREFIX = "The following skills are available for use with the Skill tool"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def sha256_ids(ids: list[int]) -> str:
    return sha256_bytes(json.dumps(ids, separators=(",", ":")).encode())


def strip_cache_control(o: Any) -> Any:
    if isinstance(o, dict):
        return {k: strip_cache_control(v) for k, v in o.items() if k != "cache_control"}
    if isinstance(o, list):
        return [strip_cache_control(x) for x in o]
    return o


def common_prefix_len(a: list[int], b: list[int]) -> int:
    n = min(len(a), len(b))
    i = 0
    # chunked fast path
    step = 4096
    while i < n:
        j = min(i + step, n)
        if a[i:j] == b[i:j]:
            i = j
            continue
        while i < j and a[i] == b[i]:
            i += 1
        return i
    return i


def classify_system_text(text: str) -> str:
    if text.startswith(TASK_REMINDER_PREFIX):
        return "task_reminder"
    if FILE_MODIFIED_RE.match(text):
        return "file_modified"
    if text.startswith(SKILL_LISTING_PREFIX):
        return "skill_listing"
    return "other_system"


def flat_text(c: Any) -> str:
    if isinstance(c, str):
        return c
    return json.dumps(c, ensure_ascii=False)


# ---------------------------------------------------------------------------
# candidate (a): CC-style smoosh of <system-reminder> siblings into the last tool_result
# ---------------------------------------------------------------------------


def smoosh_into_last_tool_result(body: dict, *, only_system_reminder: bool) -> int:
    """Mutates body['messages'] in place (run AFTER _fold_mid_list_system_into_user).

    Mirrors CC utils/messages.ts smooshSystemReminderSiblings + smooshIntoToolResult (snapshot ~2026-05):
    for a user message that has a tool_result, move text siblings whose text startswith '<system-reminder>'
    (or all text siblings when only_system_reminder=False) into the LAST tool_result. String/absent content:
    [existing.trim(), *blocks.map(trim)].filter(Boolean).join('\\n\\n'); list content: trim each text and merge
    adjacent texts with '\\n\\n'. Returns the number of moved blocks.
    """
    moved_total = 0
    for msg in body.get("messages") or []:
        if not isinstance(msg, dict) or msg.get("role") != "user" or not isinstance(msg.get("content"), list):
            continue
        content = msg["content"]
        if not any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            continue
        moved, kept = [], []
        for b in content:
            is_text = isinstance(b, dict) and b.get("type") == "text"
            if is_text and (not only_system_reminder or str(b.get("text", "")).startswith("<system-reminder>")):
                moved.append(b)
            else:
                kept.append(b)
        if not moved:
            continue
        last_tr = max(i for i, b in enumerate(kept) if isinstance(b, dict) and b.get("type") == "tool_result")
        tr = dict(kept[last_tr])
        existing = tr.get("content")
        if existing is None or isinstance(existing, str):
            parts = [(existing or "").strip(), *[str(m.get("text", "")).strip() for m in moved]]
            tr["content"] = "\n\n".join(p for p in parts if p)
        else:
            merged: list[dict] = []
            for b in [*existing, *moved]:
                if isinstance(b, dict) and b.get("type") == "text":
                    t = str(b.get("text", "")).strip()
                    if not t:
                        continue
                    if merged and merged[-1].get("type") == "text":
                        merged[-1] = {**merged[-1], "text": merged[-1]["text"] + "\n\n" + t}
                    else:
                        merged.append({"type": "text", "text": t})
                else:
                    merged.append(b)
            tr["content"] = merged
        kept[last_tr] = tr
        msg["content"] = kept
        moved_total += len(moved)
    return moved_total


def drop_task_reminders(body: dict) -> int:
    msgs = body.get("messages") or []
    keep = [
        m
        for m in msgs
        if not (isinstance(m, dict) and m.get("role") == "system" and flat_text(m.get("content")).startswith(TASK_REMINDER_PREFIX))
    ]
    n = len(msgs) - len(keep)
    body["messages"] = keep
    return n


# ---------------------------------------------------------------------------
# template-rule mirror (for reporting only; the token ids always come from the real template)
# ---------------------------------------------------------------------------


def last_query_index(translated: list[dict]) -> int:
    """Qwen3.6 chat_template: scan backwards; the first role=='user' message whose trimmed rendered content
    does not (startwith '<tool_response>' and endwith '</tool_response>') is the last query. role=='tool'
    messages are never considered."""
    for i in range(len(translated) - 1, -1, -1):
        m = translated[i]
        if m.get("role") != "user":
            continue
        c = m.get("content")
        c = c if isinstance(c, str) else "".join(x.get("text", "") for x in (c or []) if isinstance(x, dict))
        c = c.strip()
        if not (c.startswith("<tool_response>") and c.endswith("</tool_response>")):
            return i
    return -1


# ---------------------------------------------------------------------------
# main replay
# ---------------------------------------------------------------------------


class Replayer:
    def __init__(self) -> None:
        from transformers import AutoTokenizer

        from slime.agent.adapters.anthropic import AnthropicAdapter
        from slime.agent.adapters import common as slime_common

        self.tok = AutoTokenizer.from_pretrained(str(TOK_DIR), trust_remote_code=True)
        self.slime_common = slime_common
        # the production adapter class; only its pure hooks are used (no server, no sglang)
        self.adapter = AnthropicAdapter(tokenizer=self.tok, sglang_url="http://127.0.0.1:9", fork_threshold_tokens=0)
        self.IM_START = self.tok.convert_tokens_to_ids("<|im_start|>")
        self.IM_END = self.tok.convert_tokens_to_ids("<|im_end|>")
        self.THINK = self.tok.convert_tokens_to_ids("<think>")
        self.END_THINK = self.tok.convert_tokens_to_ids("</think>")

    # -- per-variant request -> (translated, tools, ids) -------------------------------------------------

    def render_request(self, raw_body: dict, variant: str) -> tuple[list[dict], list[dict] | None, list[int], dict]:
        body = copy.deepcopy(raw_body)
        info: dict[str, Any] = {}
        if variant == "c_no_task_reminder":
            info["task_reminders_removed"] = drop_task_reminders(body)
        self.adapter._preprocess_body(body)  # production: _fold_mid_list_system_into_user
        if variant == "a_smoosh":
            info["smooshed_blocks"] = smoosh_into_last_tool_result(body, only_system_reminder=True)
        elif variant == "a2_smoosh_all_text":
            info["smooshed_blocks"] = smoosh_into_last_tool_result(body, only_system_reminder=False)
        translated, tools = self.adapter._translate(body)  # production: _translate_messages + _tools_to_chat_tools
        if variant == "b_preserve":
            enc = self.tok.apply_chat_template(
                translated, tools=tools, tokenize=True, add_generation_prompt=True, preserve_thinking=True
            )
            ids = list(enc["input_ids"] if hasattr(enc, "__getitem__") and "input_ids" in enc else enc)
        else:
            ids = self.slime_common._render_token_ids(translated, self.tok, tools=tools, add_generation_prompt=True)
        return translated, tools, ids, info

    # -- block level diff ---------------------------------------------------------------------------------

    def split_blocks(self, ids: list[int]) -> list[tuple[int, int]]:
        starts = [i for i, t in enumerate(ids) if t == self.IM_START]
        if not starts or starts[0] != 0:
            starts = [0] + starts
        ends = starts[1:] + [len(ids)]
        return list(zip(starts, ends))

    def block_diff(self, held: list[int], new: list[int], prompt_n_len: int) -> dict:
        """Compare held (= prompt_n + output_n) with prompt_{n+1} block by block (blocks split at <|im_start|>).

        For every differing block, decide whether the difference is exactly 'old block minus its
        <think>\\n...\\n</think>\\n\\n span' (thinking_only) or something else (other)."""
        ob = self.split_blocks(held)
        nb = self.split_blocks(new)
        res: dict[str, Any] = {
            "n_blocks_held": len(ob),
            "n_blocks_new": len(nb),
            "thinking_only_blocks": 0,
            "other_diff_blocks": 0,
            "thinking_net_tokens_dropped": 0,
            "thinking_inner_tokens_dropped": 0,
            "dropped_think_segments": [],
            "other_diff_examples": [],
        }
        for bi, (s, e) in enumerate(ob):
            if bi >= len(nb):
                res["other_diff_blocks"] += 1
                res["other_diff_examples"].append({"block": bi, "why": "held has more blocks than new prompt"})
                continue
            ns, ne = nb[bi]
            old_ids, new_ids = held[s:e], new[ns:ne]
            is_last = bi == len(ob) - 1
            if old_ids == new_ids or (is_last and new_ids[: len(old_ids)] == old_ids):
                continue
            old_txt = self.tok.decode(old_ids, skip_special_tokens=False)
            new_txt = self.tok.decode(new_ids, skip_special_tokens=False)
            ok = False
            if "<think>" in old_txt and "<think>" not in new_txt:
                i0 = old_txt.find("<think>")
                i1 = old_txt.find("</think>")
                if i1 > i0 and old_txt[i1 + len("</think>") : i1 + len("</think>") + 2] == "\n\n":
                    removed = old_txt[i0 : i1 + len("</think>") + 2]
                    rest = old_txt[:i0] + old_txt[i1 + len("</think>") + 2 :]
                    if rest == new_txt or (is_last and new_txt.startswith(rest)):
                        ok = True
                        # token accounting
                        try:
                            ti0 = old_ids.index(self.THINK)
                            ti1 = old_ids.index(self.END_THINK)
                            inner = ti1 - ti0 + 1
                        except ValueError:
                            # held last block: <think> sits in prompt_n, output starts inside the think block
                            inner = -1
                        new_len_cmp = len(new_ids)
                        if is_last and new_txt != rest:
                            # new block carries the trailing '\n' after <|im_end|> that held does not have
                            new_len_cmp = len(self.tok.encode(rest, add_special_tokens=False))
                        res["thinking_only_blocks"] += 1
                        res["thinking_net_tokens_dropped"] += len(old_ids) - new_len_cmp
                        if inner > 0:
                            res["thinking_inner_tokens_dropped"] += inner
                        res["dropped_think_segments"].append(
                            {
                                "block": bi,
                                "is_last_response_block": is_last,
                                "held_token_start": s,
                                "net_tokens": len(old_ids) - new_len_cmp,
                                "think_span_tokens": inner,
                                "removed_text_head": removed[:160],
                                "removed_text_tail": removed[-80:],
                                "removed_chars": len(removed),
                                "starts_with_think_tag": removed.startswith("<think>"),
                                "ends_with_think_close": removed.endswith("</think>\n\n"),
                            }
                        )
            if not ok:
                res["other_diff_blocks"] += 1
                cp = 0
                m = min(len(old_txt), len(new_txt))
                while cp < m and old_txt[cp] == new_txt[cp]:
                    cp += 1
                res["other_diff_examples"].append(
                    {
                        "block": bi,
                        "is_last_response_block": is_last,
                        "held_token_start": s,
                        "text_common_prefix_chars": cp,
                        "old_around": old_txt[max(0, cp - 60) : cp + 100],
                        "new_around": new_txt[max(0, cp - 60) : cp + 100],
                    }
                )
        return res

    # -- trajectory manager simulation ---------------------------------------------------------------------

    def coverage(self, turns_seq: list[dict]) -> dict:
        from slime.agent.trajectory import TrajectoryManager, TurnRecord
        from repoharness2.adapters.slime.turn_identity import export_leaf_identity_spans_with_coverage

        mgr = TrajectoryManager(fork_threshold_tokens=0)
        sid = "replay"
        for t in turns_seq:
            mgr.record_turn(
                sid,
                turn=TurnRecord(
                    prompt_ids=t["prompt_ids"],
                    output_ids=t["output_ids"],
                    finish_reason=t["finish_reason"],
                    output_log_probs=[0.0] * len(t["output_ids"]),
                ),
                prompt_messages=t["translated"],
                response_message=t["response_message"],
                metadata={"sid": sid},
            )
        root = mgr._trees[sid]
        _, summary = export_leaf_identity_spans_with_coverage(root, fork_threshold=0, max_sample_tokens=0)
        n_leaves = sum(1 for leaf in root.leaves() if not leaf.is_root)
        d = summary.to_dict()
        d["routing_leaves"] = n_leaves
        return d


def load_attempt(att_dir: Path) -> tuple[list[dict], list[dict]]:
    rows = [json.loads(l) for l in att_dir.joinpath("requests.jsonl").read_text().splitlines() if l.strip()]
    reqs = [r for r in rows if r.get("seq") is not None and isinstance(r.get("body"), dict) and "rejected" not in r]
    reqs.sort(key=lambda r: r["seq"])
    tf = GW / "q36_adapter" / f"{att_dir.name}.turns.jsonl"
    turns = [json.loads(l) for l in tf.read_text().splitlines() if l.strip()]
    return reqs, turns


def insertions_between(prev_msgs: list[dict] | None, msgs: list[dict]) -> list[dict]:
    """New role:system messages and new user text blocks (non tool_result) that appear in `msgs` beyond the
    (cache_control-stripped) prefix `prev_msgs`."""
    start = 0 if prev_msgs is None else len(prev_msgs)
    out = []
    for i in range(start, len(msgs)):
        m = msgs[i]
        if m.get("role") == "system":
            out.append({"msg_index": i, "source": "role_system", "kind": classify_system_text(flat_text(m.get("content"))),
                        "chars": len(flat_text(m.get("content")))})
        elif m.get("role") == "user" and isinstance(m.get("content"), list) and i > 0:
            has_tr = any(b.get("type") == "tool_result" for b in m["content"] if isinstance(b, dict))
            for b in m["content"]:
                if isinstance(b, dict) and b.get("type") == "text":
                    prev = msgs[i - 1] if i > 0 else {}
                    prev_tools = [x.get("name") for x in (prev.get("content") or []) if isinstance(x, dict) and x.get("type") == "tool_use"]
                    kind = "skill_body" if "Skill" in prev_tools else "user_text"
                    out.append({"msg_index": i, "source": "user_text_block", "kind": kind, "with_tool_result": has_tr,
                                "prev_tool_uses": prev_tools, "chars": len(b.get("text", "")),
                                "head": b.get("text", "")[:80]})
    return out


def run(args: argparse.Namespace) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rp = Replayer()
    tok = rp.tok
    import transformers

    att_dirs = sorted(p for p in (GW / "q36").iterdir() if p.is_dir() and p.name.startswith("bp22-"))
    if args.only:
        att_dirs = [p for p in att_dirs if any(s in p.name for s in args.only.split(","))]

    turns_out = open(OUT / "replay_turns.jsonl", "w", encoding="utf-8")
    pairs_out = open(OUT / "replay_pairs.jsonl", "w", encoding="utf-8")
    cov_out = open(OUT / "replay_coverage.jsonl", "w", encoding="utf-8")
    examples: dict[str, Any] = {}
    t_start = time.time()

    for att_dir in att_dirs:
        att = att_dir.name
        reqs, turns = load_attempt(att_dir)
        assert len(reqs) == len(turns), (att, len(reqs), len(turns))
        raw_msgs = [strip_cache_control(r["body"]["messages"]) for r in reqs]
        # message-level prefix facts + insertion catalogue (variant independent)
        ins_per_req: list[list[dict]] = []
        for i, msgs in enumerate(raw_msgs):
            prev = raw_msgs[i - 1] if i > 0 else None
            if prev is not None:
                assert msgs[: len(prev)] == prev, f"{att}: request {i} not a message-level prefix extension"
            ins_per_req.append(insertions_between(prev, msgs))
        # outputs: canonical re-encoding of the recorded raw output
        outs = []
        for t in turns:
            o = tok.encode(t["raw_output"], add_special_tokens=False)
            outs.append(o)

        for variant in VARIANTS:
            seq_rows = []
            for i, (r, t) in enumerate(zip(reqs, turns)):
                translated, tools, ids, info = rp.render_request(r["body"], variant)
                lq = last_query_index(translated)
                asst_idx = [k for k, m in enumerate(translated) if m.get("role") == "assistant"]
                n_asst_think = sum(
                    1 for k in asst_idx if (variant == "b_preserve" or k > lq) and (translated[k].get("reasoning_content") or "").strip()
                )
                row = {
                    "variant": variant,
                    "attempt": att,
                    "seq": r["seq"],
                    "prompt_len": len(ids),
                    "prompt_sha256": sha256_ids(ids),
                    "recorded_prompt_tokens": t["prompt_tokens"],
                    "matches_recorded": len(ids) == t["prompt_tokens"],
                    "recorded_n_messages": t.get("n_messages"),
                    "n_translated": len(translated),
                    "n_tools": len(tools or []),
                    "last_query_index": lq,
                    "n_assistant": len(asst_idx),
                    "n_assistant_rendered_with_thinking": n_asst_think,
                    "output_tokens_recorded": t["output_tokens"],
                    "output_tokens_reencoded": len(outs[i]),
                    "output_reencode_len_match": len(outs[i]) == t["output_tokens"],
                    "finish_reason": t.get("finish_reason"),
                    "insertions_in_this_request": ins_per_req[i],
                    **info,
                }
                turns_out.write(json.dumps(row, ensure_ascii=False) + "\n")
                seq_rows.append(
                    {
                        "seq": r["seq"],
                        "prompt_ids": ids,
                        "output_ids": outs[i],
                        "translated": translated,
                        "finish_reason": t.get("finish_reason") or "stop",
                        "response_message": t["parsed"],
                        "row": row,
                    }
                )
            # adjacent pairs
            for i in range(len(seq_rows) - 1):
                a, b = seq_rows[i], seq_rows[i + 1]
                pa, pb = a["prompt_ids"], b["prompt_ids"]
                held = pa + a["output_ids"]
                cp_prompt = common_prefix_len(pa, pb)
                cp_held = common_prefix_len(held, pb)
                clean = cp_held == len(held)
                bd = rp.block_diff(held, pb, len(pa)) if not clean else None
                ins = ins_per_req[i + 1]
                ins_kinds = Counter(x["kind"] for x in ins)
                pair = {
                    "variant": variant,
                    "attempt": att,
                    "seq_from": a["seq"],
                    "seq_to": b["seq"],
                    "L_from": len(pa),
                    "L_to": len(pb),
                    "delta": len(pb) - len(pa),
                    "strict_decrease": len(pb) < len(pa),
                    "cp_prompt": cp_prompt,
                    "prompt_prefix_ok": cp_prompt == len(pa),
                    "held_len": len(held),
                    "cp_held": cp_held,
                    "held_prefix_ok_CLEAN": clean,
                    "divergence_offset_vs_last_response_start": (cp_held - len(pa)) if not clean else None,
                    "divergence_position": (None if clean else ("in_response" if cp_held >= len(pa) else "before_response")),
                    "insertions": ins,
                    "insertion_kinds": dict(ins_kinds),
                    "n_insertions_role_system_after_tool_result": sum(
                        1 for x in ins if x["source"] == "role_system" and x["kind"] in ("task_reminder", "file_modified", "other_system")
                    ),
                    "n_insertions_user_text": sum(1 for x in ins if x["source"] == "user_text_block"),
                    "lqi_from": a["row"]["last_query_index"],
                    "lqi_to": b["row"]["last_query_index"],
                    "thinking_asst_from": a["row"]["n_assistant_rendered_with_thinking"],
                    "thinking_asst_to": b["row"]["n_assistant_rendered_with_thinking"],
                }
                if bd is not None:
                    pair.update(
                        {
                            "thinking_only_blocks": bd["thinking_only_blocks"],
                            "other_diff_blocks": bd["other_diff_blocks"],
                            "thinking_net_tokens_dropped": bd["thinking_net_tokens_dropped"],
                            "thinking_inner_tokens_dropped": bd["thinking_inner_tokens_dropped"],
                            "dropped_think_segments": bd["dropped_think_segments"],
                            "other_diff_examples": bd["other_diff_examples"][:3],
                            "cause": (
                                "thinking_only"
                                if bd["thinking_only_blocks"] > 0 and bd["other_diff_blocks"] == 0
                                else ("thinking_and_other" if bd["thinking_only_blocks"] > 0 else "other_only")
                            ),
                        }
                    )
                else:
                    pair.update({"thinking_only_blocks": 0, "other_diff_blocks": 0, "thinking_net_tokens_dropped": 0,
                                 "thinking_inner_tokens_dropped": 0, "cause": "clean"})
                pairs_out.write(json.dumps(pair, ensure_ascii=False) + "\n")
            # coverage via production TrajectoryManager + turn_identity
            cov = rp.coverage(seq_rows)
            cov_row = {"variant": variant, "attempt": att, **cov}
            cov_out.write(json.dumps(cov_row, ensure_ascii=False) + "\n")
            # keep a few rendered tails for the examples file
            if att in args.example_attempts.split(","):
                for i, sr in enumerate(seq_rows):
                    if ins_per_req[i] and i > 0:
                        key = f"{att}#seq{sr['seq']}"
                        ids = sr["prompt_ids"]
                        # tail: from the last assistant block start to the end
                        blocks = rp.split_blocks(ids)
                        tail_start = blocks[-4][0] if len(blocks) >= 4 else 0
                        examples.setdefault(key, {})[variant] = {
                            "prompt_len": len(ids),
                            "tail_text": tok.decode(ids[tail_start:], skip_special_tokens=False)[-3000:],
                            "tail_token_count": len(ids) - tail_start,
                        }
        turns_out.flush()
        pairs_out.flush()
        cov_out.flush()
        print(f"[{time.time() - t_start:7.1f}s] {att}: {len(reqs)} requests x {len(VARIANTS)} variants", flush=True)

    turns_out.close()
    pairs_out.close()
    cov_out.close()
    (OUT / "examples_rendered_tails.json").write_text(json.dumps(examples, ensure_ascii=False, indent=1))

    # Task* tool schema cost (candidate c): system+tools block with vs without Task* tools, on the last request
    tool_cost = {}
    for att_dir in att_dirs:
        reqs, _ = load_attempt(att_dir)
        body = copy.deepcopy(reqs[-1]["body"])
        names = [t.get("name") for t in body.get("tools") or []]
        rp.adapter._preprocess_body(body)
        translated, tools = rp.adapter._translate(body)
        base_msgs = [translated[0], {"role": "user", "content": "x"}]
        with_all = rp.slime_common._render_token_ids(base_msgs, tok, tools=tools, add_generation_prompt=False)
        tools_wo = [t for t in tools if not t["function"]["name"].startswith("Task")]
        without = rp.slime_common._render_token_ids(base_msgs, tok, tools=tools_wo, add_generation_prompt=False)
        todo_v2 = {"TaskCreate", "TaskGet", "TaskList", "TaskUpdate"}
        tools_wo_todo = [t for t in tools if t["function"]["name"] not in todo_v2]
        without_todo = rp.slime_common._render_token_ids(base_msgs, tok, tools=tools_wo_todo, add_generation_prompt=False)
        per_tool = {}
        for t in tools:
            nm = t["function"]["name"]
            if nm.startswith("Task"):
                wo1 = [x for x in tools if x["function"]["name"] != nm]
                per_tool[nm] = len(with_all) - len(
                    rp.slime_common._render_token_ids(base_msgs, tok, tools=wo1, add_generation_prompt=False)
                )
        tool_cost[att_dir.name] = {
            "tool_names": names,
            "task_tools": [n for n in names if n and n.startswith("Task")],
            "system_plus_tools_tokens_all": len(with_all),
            "system_plus_tools_tokens_without_task": len(without),
            "task_tool_schema_tokens": len(with_all) - len(without),
            "todo_v2_tools_schema_tokens": len(with_all) - len(without_todo),
            "per_task_tool_schema_tokens": per_tool,
        }
    (OUT / "task_tool_schema_cost.json").write_text(json.dumps(tool_cost, ensure_ascii=False, indent=1))

    prov = {
        "generated_at_unix": time.time(),
        "python": sys.version,
        "platform": platform.platform(),
        "transformers": transformers.__version__,
        "hf_repo": HF_REPO,
        "hf_revision": HF_REVISION,
        "tokenizer_files_sha256": {p.name: sha256_file(p) for p in sorted(TOK_DIR.iterdir()) if p.is_file()},
        "chat_template_sha256_loaded": sha256_bytes(tok.chat_template.encode()),
        "git_head": subprocess.run(["git", "-C", str(REPO), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip(),
        "production_files_sha256": {
            str(p.relative_to(REPO)): sha256_file(p)
            for p in [
                RH2 / "src/slime/agent/adapters/anthropic.py",
                RH2 / "src/slime/agent/adapters/common.py",
                RH2 / "src/slime/agent/trajectory.py",
                RH2 / "src/repoharness2/adapters/slime/turn_identity.py",
            ]
        },
        "script_sha256": sha256_file(Path(__file__)),
        "variants": VARIANTS,
        "attempts": [p.name for p in att_dirs],
        "output_ids_note": "sampled output ids were not logged; output_ids = tok.encode(raw_output) (length checked per turn)",
    }
    (OUT / "provenance.json").write_text(json.dumps(prov, ensure_ascii=False, indent=1))
    print("done", time.time() - t_start)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated attempt-name substrings (debug)")
    ap.add_argument(
        "--example-attempts",
        default="bp22-qwen3-6-35b-a3b-moto-5134-a1,bp22-qwen3-6-35b-a3b-dask-8597-a2,bp22-qwen3-6-35b-a3b-conan-15422-a1",
    )
    run(ap.parse_args())
