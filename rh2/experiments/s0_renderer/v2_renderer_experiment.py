#!/usr/bin/env python
"""S0-4 V2 核实实验（验证级脚本，非产品代码）：renderers 库对 Qwen/Qwen3-30B-A3B 的覆盖。

运行方式（rh2 环境）：
    cd rh2 && uv run python <本文件>

实验内容：
  A. 静态核实：MODEL_RENDERER_MAP 注册、renderer 类、thinking retention、stop tokens
  B. 渲染一致性：renderer.render_ids vs tokenizer.apply_chat_template（多组多轮/工具/thinking 用例）
  C. bridge 语义：两轮链式 bridge 的前缀保持、与全量渲染等价、user-query 边界回退、截断合成 close
  D. MoE(30B-A3B) vs dense(Qwen3-8B) 的 tokenizer/chat template 同一性
  E. thinking 剥离对 token tape 的量化影响（U-E）
"""

from __future__ import annotations

import hashlib
import json
import os
import sys

REPO = "/Users/roger/Desktop/claude-code-verl-stage0h"
sys.path.insert(0, f"{REPO}/reference/renderers")

RESULTS: dict = {"parity_cases": [], "bridge_cases": [], "static": {}, "moe_vs_dense": {}, "u_e": {}}
FAILS: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILS.append(f"{name}: {detail}")


def first_diff(a: list[int], b: list[int]) -> int:
    n = min(len(a), len(b))
    for i in range(n):
        if a[i] != b[i]:
            return i
    return -1 if len(a) == len(b) else n


# ── A. 静态核实 ─────────────────────────────────────────────────────────
print("== A. 静态核实 ==")
from renderers.base import MODEL_RENDERER_MAP, create_renderer, load_tokenizer
from renderers.configs import Qwen3RendererConfig

MODEL = "Qwen/Qwen3-30B-A3B"
DENSE = "Qwen/Qwen3-8B"

a3b_entries = {k: v for k, v in MODEL_RENDERER_MAP.items() if "30B-A3B" in k and "VL" not in k}
print(f"  MODEL_RENDERER_MAP 中 30B-A3B 条目: {a3b_entries}")
RESULTS["static"]["map_entries"] = a3b_entries
check("30B-A3B 精确注册到 qwen3", a3b_entries.get(MODEL) == "qwen3")

tok = load_tokenizer(MODEL)
renderer = create_renderer(tok)  # AutoRendererConfig -> qwen3
print(f"  renderer 类: {type(renderer).__name__}")
print(f"  config: {renderer.config!r}")
print(f"  effective_thinking_retention: {renderer.effective_thinking_retention}")
stop_ids = renderer.get_stop_token_ids()
print(f"  stop_token_ids: {stop_ids} = {[tok.convert_ids_to_tokens(i) for i in stop_ids]}")
RESULTS["static"].update(
    renderer_class=type(renderer).__name__,
    thinking_retention=renderer.effective_thinking_retention,
    stop_ids=stop_ids,
    vocab_size=len(tok),
    tokenizer_class=type(tok).__name__,
)
check("auto 解析为 Qwen3Renderer", type(renderer).__name__ == "Qwen3Renderer")

IM_END = stop_ids[0]
NL = tok.encode("\n", add_special_tokens=False)
assert len(NL) == 1
NL = NL[0]

# ── 固定对话素材（SWE agent 风格：单一 user 任务 + 两个工具循环） ────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "Run a shell command in the workspace",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "shell command to run"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the workspace",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "file path"}},
                "required": ["path"],
            },
        },
    },
]

MSGS = [
    {"role": "system", "content": "You are a coding agent working in /workspace."},
    {"role": "user", "content": "Create hello.txt containing exactly 'hello world', then verify it."},
    {
        "role": "assistant",
        "content": "",
        "reasoning_content": "I need to create the file first, then read it back to verify.",
        "tool_calls": [
            {"id": "call_1", "type": "function",
             "function": {"name": "bash", "arguments": {"command": "printf 'hello world' > /workspace/hello.txt"}}}
        ],
    },
    {"role": "tool", "tool_call_id": "call_1", "content": "exit_code=0"},
    {
        "role": "assistant",
        "content": "File written. Now verifying.",
        "reasoning_content": "Write succeeded (exit 0). Read it back.",
        "tool_calls": [
            {"id": "call_2", "type": "function",
             "function": {"name": "read_file", "arguments": {"path": "/workspace/hello.txt"}}}
        ],
    },
    {"role": "tool", "tool_call_id": "call_2", "content": "hello world"},
    {
        "role": "assistant",
        "content": "Done. hello.txt contains exactly 'hello world'.",
        "reasoning_content": "Content matches. Task complete.",
    },
]


def hf_ids(tokenizer, messages, **kw):
    kw.setdefault("add_generation_prompt", False)
    out = tokenizer.apply_chat_template(messages, tokenize=True, return_dict=False, **kw)
    if isinstance(out, dict):
        return list(out["input_ids"])
    if isinstance(out, str):
        return list(tokenizer.encode(out, add_special_tokens=False))
    return list(out)


def parity(name, messages, *, tools=None, add_gen=False, rend=None, hf_kwargs=None):
    r = rend or renderer
    ours = r.render_ids(messages, tools=tools, add_generation_prompt=add_gen)
    theirs = hf_ids(tok, messages, tools=tools, add_generation_prompt=add_gen, **(hf_kwargs or {}))
    ok = ours == theirs
    d = first_diff(ours, theirs)
    detail = f"{len(ours)} tokens"
    if not ok:
        ctx_o = tok.decode(ours[max(0, d - 8): d + 8]) if d >= 0 else ""
        ctx_t = tok.decode(theirs[max(0, d - 8): d + 8]) if d >= 0 else ""
        detail = f"len ours={len(ours)} hf={len(theirs)}, first_diff@{d}: ours=...{ctx_o!r}... hf=...{ctx_t!r}..."
    check(f"parity/{name}", ok, detail)
    RESULTS["parity_cases"].append(
        {"case": name, "ok": ok, "n_tokens_renderer": len(ours), "n_tokens_hf": len(theirs), "first_diff": d}
    )
    return ours


# ── B. 渲染一致性 ───────────────────────────────────────────────────────
print("== B. 渲染一致性 renderer.render_ids vs apply_chat_template ==")

parity("basic_system_user_assistant",
       [{"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi!"}])

full_ids = parity("swe_full_7msgs_reasoning_field", MSGS, tools=TOOLS)

# 同一对话，把 reasoning 内联成 <think>…</think> 写进 content（rollout 解析前的原始形态）
MSGS_INLINE = []
for m in MSGS:
    m = dict(m)
    if m["role"] == "assistant":
        rc = m.pop("reasoning_content")
        m["content"] = f"<think>\n{rc}\n</think>\n\n{m['content']}"
    MSGS_INLINE.append(m)
parity("swe_full_7msgs_inline_think", MSGS_INLINE, tools=TOOLS)

# 生成提示：enable_thinking=True（默认）与 False
parity("gen_prompt_enable_thinking_true", MSGS[:2], tools=TOOLS, add_gen=True)
renderer_nothink = create_renderer(tok, Qwen3RendererConfig(enable_thinking=False))
parity("gen_prompt_enable_thinking_false", MSGS[:2], tools=TOOLS, add_gen=True,
       rend=renderer_nothink, hf_kwargs={"enable_thinking": False})
parity("full_render_enable_thinking_false", MSGS, tools=TOOLS,
       rend=renderer_nothink, hf_kwargs={"enable_thinking": False})

# 中间轮 prompt（工具循环内，历史 assistant 带 reasoning）
parity("mid_rollout_prompt_4msgs", MSGS[:4], tools=TOOLS, add_gen=True)
parity("mid_rollout_prompt_6msgs", MSGS[:6], tools=TOOLS, add_gen=True)

# 第二个 user query 出现后：更早的 assistant thinking 应被两边一致剥离
MSGS_2Q = MSGS + [
    {"role": "user", "content": "Now delete hello.txt."},
    {
        "role": "assistant",
        "content": "",
        "reasoning_content": "Second task: remove the file.",
        "tool_calls": [
            {"id": "call_3", "type": "function",
             "function": {"name": "bash", "arguments": {"command": "rm /workspace/hello.txt"}}}
        ],
    },
]
parity("second_user_query_strips_history_think", MSGS_2Q, tools=TOOLS)
parity("second_user_query_prompt", MSGS_2Q[:8], tools=TOOLS, add_gen=True)

# 并行工具调用 + 连续 tool 消息合并进同一个 user 块
MSGS_PAR = [
    {"role": "user", "content": "Check both files."},
    {
        "role": "assistant",
        "content": "",
        "reasoning_content": "Read both in parallel.",
        "tool_calls": [
            {"id": "p1", "type": "function", "function": {"name": "read_file", "arguments": {"path": "/a.py"}}},
            {"id": "p2", "type": "function", "function": {"name": "read_file", "arguments": {"path": "/b.py"}}},
        ],
    },
    {"role": "tool", "tool_call_id": "p1", "content": "print('a')"},
    {"role": "tool", "tool_call_id": "p2", "content": "print('b')"},
    {"role": "assistant", "content": "Both files are one-line prints."},
]
parity("parallel_tool_calls_consecutive_tool_msgs", MSGS_PAR, tools=TOOLS)

# 工具输出里带类特殊标记文本 / unicode / 代码 diff（SWE 常见形态）
MSGS_ADV = [
    {"role": "user", "content": "Apply the patch."},
    {
        "role": "assistant",
        "content": "",
        "reasoning_content": "Run the patch tool.",
        "tool_calls": [
            {"id": "x1", "type": "function",
             "function": {"name": "bash", "arguments": {"command": "git apply fix.patch && echo done"}}}
        ],
    },
    {"role": "tool", "tool_call_id": "x1",
     "content": "--- a/f.py\n+++ b/f.py\n@@ -1 +1 @@\n-x = '<tool_call>'\n+x = '模型'  # ünïcode\ndone"},
    {"role": "assistant", "content": "Patch applied: the literal '<tool_call>' string was replaced."},
]
parity("tool_output_with_special_lookalikes", MSGS_ADV, tools=TOOLS)


# ── C. bridge 语义 ─────────────────────────────────────────────────────
print("== C. bridge_to_next_turn 语义 ==")


def derive_completion(prompt_msgs, full_msgs, tools):
    """从 canonical 全量渲染推导'模型采样出的 completion token 流'。

    P = 上一轮 prompt（含 generation prompt）；F = 加上 assistant 回复后的全量渲染。
    F 必须以 P 为前缀；completion = F[len(P):] 去掉最后一个模板缝隙 "\\n"
    （vLLM 在 <|im_end|> 停止，completion 以 <|im_end|> 结尾，"\\n" 不会被采样）。
    """
    P = renderer.render_ids(prompt_msgs, tools=tools, add_generation_prompt=True)
    F = renderer.render_ids(full_msgs, tools=tools)
    assert F[: len(P)] == P, "generation prompt 不是全量渲染的前缀"
    C = F[len(P):]
    assert C[-1] == NL and C[-2] == IM_END, "全量渲染末尾应为 <|im_end|> + \\n"
    return P, C[:-1]


def bridge_case(name, ok, detail=""):
    check(f"bridge/{name}", ok, detail)
    RESULTS["bridge_cases"].append({"case": name, "ok": ok, "detail": detail})


# 第 1 轮 → tool 结果 → 第 2 轮 prompt
P1, C1 = derive_completion(MSGS[:2], MSGS[:3], TOOLS)
B1 = renderer.bridge_to_next_turn(P1, C1, [MSGS[3]], tools=TOOLS)
bridge_case("turn1_returns_non_none", B1 is not None)
tape1 = P1 + C1
bridge_case("turn1_prefix_preserved", B1.token_ids[: len(tape1)] == tape1,
            f"prefix {len(tape1)} tokens, bridged total {len(B1.token_ids)}")
canon2 = renderer.render_ids(MSGS[:4], tools=TOOLS, add_generation_prompt=True)
bridge_case("turn1_bridge_equals_full_rerender", B1.token_ids == canon2,
            f"bridge={len(B1.token_ids)} rerender={len(canon2)} first_diff={first_diff(B1.token_ids, canon2)}")

# 第 2 轮 → 第二个 tool 结果 → 第 3 轮 prompt（链式，验证跨两轮前缀保持）
P2 = B1.token_ids
F5 = renderer.render_ids(MSGS[:5], tools=TOOLS)
assert F5[: len(P2)] == P2, "第 2 轮 prompt 不是第 2 轮全量渲染的前缀"
C2 = F5[len(P2):]
assert C2[-1] == NL and C2[-2] == IM_END
C2 = C2[:-1]
B2 = renderer.bridge_to_next_turn(P2, C2, [MSGS[5]], tools=TOOLS)
tape2 = P2 + C2
bridge_case("turn2_chained_prefix_preserved",
            B2 is not None and B2.token_ids[: len(tape2)] == tape2,
            f"prefix {len(tape2)} tokens, bridged total {len(B2.token_ids)}")
bridge_case("turn2_still_prefixed_by_turn1_tape", B2.token_ids[: len(tape1)] == tape1)
canon3 = renderer.render_ids(MSGS[:6], tools=TOOLS, add_generation_prompt=True)
bridge_case("turn2_bridge_equals_full_rerender", B2.token_ids == canon3)

# roundtrip：completion 解析回结构化消息（工具调用格式可解析）
parsed = renderer.parse_response(C1)
tc_ok = (len(parsed.tool_calls) == 1 and parsed.tool_calls[0].status.value == "ok"
         and parsed.tool_calls[0].name == "bash"
         and parsed.reasoning_content == MSGS[2]["reasoning_content"])
bridge_case("completion_parse_roundtrip", tc_ok,
            f"tool={parsed.tool_calls[0].name if parsed.tool_calls else None} reasoning={parsed.reasoning_content!r}")

# user-query 边界：tool_cycle 策略下 bridge 必须回退（返回 None）
B_user = renderer.bridge_to_next_turn(P2, C2, [{"role": "user", "content": "Now delete it."}], tools=TOOLS)
bridge_case("new_user_query_forces_rerender_none", B_user is None)

# assistant 出现在扩展消息里：必须拒绝
B_asst = renderer.bridge_to_next_turn(P1, C1, [{"role": "assistant", "content": "hi"}], tools=TOOLS)
bridge_case("assistant_in_extension_rejected", B_asst is None)

# 截断 completion（max_tokens 截断模拟）：合成 canonical close
C1_trunc = C1[:-3]
B_trunc = renderer.bridge_to_next_turn(P1, C1_trunc, [MSGS[3]], tools=TOOLS)
tape_t = P1 + C1_trunc
bridge_case("truncated_completion_synthesizes_close",
            B_trunc is not None
            and B_trunc.token_ids[: len(tape_t)] == tape_t
            and B_trunc.token_ids[len(tape_t)] == IM_END,
            f"synthesized token id {IM_END} (<|im_end|>) right after truncated tape")

# 并行 tool 结果作为 bridge 扩展（连续 tool 消息合并逻辑在 bridge 路径同样生效）
Pp, Cp = derive_completion(MSGS_PAR[:1], MSGS_PAR[:2], TOOLS)
Bp = renderer.bridge_to_next_turn(Pp, Cp, [MSGS_PAR[2], MSGS_PAR[3]], tools=TOOLS)
canon_p = renderer.render_ids(MSGS_PAR[:4], tools=TOOLS, add_generation_prompt=True)
bridge_case("parallel_tool_msgs_bridge_equals_rerender",
            Bp is not None and Bp.token_ids == canon_p and Bp.token_ids[: len(Pp + Cp)] == Pp + Cp)

# enable_thinking=False 时 retention 派生为 "all"：跨 user query 也允许 bridge
ret_nothink = renderer_nothink.effective_thinking_retention
bridge_case("nothink_config_retention_is_all", ret_nothink == "all", f"retention={ret_nothink}")

# ── E. thinking 剥离的量化影响（U-E） ───────────────────────────────────
print("== E. thinking 剥离对 token tape 的影响（U-E 量化） ==")
# 第 3 轮完成后的真实 tape：P3+C3
P3 = canon3
F7 = renderer.render_ids(MSGS[:7], tools=TOOLS)
assert F7[: len(P3)] == P3
C3 = F7[len(P3):]
assert C3[-1] == NL and C3[-2] == IM_END
C3 = C3[:-1]
tape3 = P3 + C3
# 新 user query 到来，回退全量重渲染 → 历史 thinking 被剥离
R_next = renderer.render_ids(MSGS_2Q[:8], tools=TOOLS, add_generation_prompt=True)
cpl = first_diff(R_next, tape3)
cpl = cpl if cpl >= 0 else min(len(R_next), len(tape3))
R_hist_only = hf_ids(tok, MSGS_2Q[:8], tools=TOOLS, add_generation_prompt=True)
u_e = {
    "tape_after_turn3": len(tape3),
    "rerendered_next_prompt": len(R_next),
    "common_prefix_len": cpl,
    "tape_tokens_discarded_from_prefix": len(tape3) - cpl,
    "hf_parity_on_rerendered_prompt": R_next == R_hist_only,
}
RESULTS["u_e"] = u_e
print(f"  第3轮结束时 tape 长度: {u_e['tape_after_turn3']}")
print(f"  新 user query 全量重渲染 prompt 长度: {u_e['rerendered_next_prompt']}")
print(f"  两者公共前缀: {cpl} → 旧 tape 中 {u_e['tape_tokens_discarded_from_prefix']} 个 token 不再是新 prompt 的前缀")
check("u_e/rerendered_prompt_hf_parity", u_e["hf_parity_on_rerendered_prompt"])

# ── D. MoE vs dense 同一性 ─────────────────────────────────────────────
print("== D. 30B-A3B(MoE) vs Qwen3-8B(dense, CI 代表) tokenizer/模板同一性 ==")
tok8 = load_tokenizer(DENSE)
ct_a3b = tok.chat_template if isinstance(tok.chat_template, str) else str(tok.chat_template)
ct_8b = tok8.chat_template if isinstance(tok8.chat_template, str) else str(tok8.chat_template)
h1, h2 = (hashlib.sha256(x.encode()).hexdigest()[:16] for x in (ct_a3b, ct_8b))
same_vocab = tok.get_vocab() == tok8.get_vocab()
sample = MSGS_INLINE
same_render = hf_ids(tok, sample, tools=TOOLS) == hf_ids(tok8, sample, tools=TOOLS)
RESULTS["moe_vs_dense"] = {
    "chat_template_sha256_16_a3b": h1,
    "chat_template_sha256_16_8b": h2,
    "chat_template_identical": ct_a3b == ct_8b,
    "vocab_identical": same_vocab,
    "same_fixture_renders_identically": same_render,
}
check("chat_template 与 8B 完全一致", ct_a3b == ct_8b, f"a3b={h1} 8b={h2}")
check("vocab 与 8B 完全一致", same_vocab, f"vocab_size a3b={len(tok)} 8b={len(tok8)}")
check("同一 fixture 两个 tokenizer 渲染逐 token 一致", same_render)

# ── 汇总 ────────────────────────────────────────────────────────────────
print("== 汇总 ==")
n_parity = len(RESULTS["parity_cases"])
n_parity_ok = sum(c["ok"] for c in RESULTS["parity_cases"])
n_bridge = len(RESULTS["bridge_cases"])
n_bridge_ok = sum(c["ok"] for c in RESULTS["bridge_cases"])
print(f"  parity: {n_parity_ok}/{n_parity} 通过; bridge: {n_bridge_ok}/{n_bridge} 通过; FAIL 总数: {len(FAILS)}")
for f in FAILS:
    print(f"  FAIL -> {f}")

import transformers, huggingface_hub  # noqa: E402
RESULTS["env"] = {
    "transformers": transformers.__version__,
    "huggingface_hub": huggingface_hub.__version__,
    "python": sys.version.split()[0],
}
out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "v2_results.json")
with open(out_path, "w") as fh:
    json.dump(RESULTS, fh, ensure_ascii=False, indent=2)
print(f"  结果已写入 {out_path}")
sys.exit(1 if FAILS else 0)
