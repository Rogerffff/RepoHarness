#!/usr/bin/env python
"""S0-4 附加证据：tokenizer 快照信息 + U-E 分歧点解码。"""
import glob
import os
import sys

sys.path.insert(0, "/Users/roger/Desktop/claude-code-verl-stage0h/reference/renderers")
from renderers.base import create_renderer, load_tokenizer

for repo in ["models--Qwen--Qwen3-30B-A3B", "models--Qwen--Qwen3-8B"]:
    base = os.path.expanduser(f"~/.cache/huggingface/hub/{repo}")
    for s in glob.glob(f"{base}/snapshots/*"):
        print(repo, "revision:", os.path.basename(s))
        for f in sorted(os.listdir(s)):
            sz = os.path.getsize(os.path.realpath(os.path.join(s, f)))
            print(f"    {f}  {sz/1e6:.2f} MB")

tok = load_tokenizer("Qwen/Qwen3-30B-A3B")
r = create_renderer(tok)

TOOLS = [
    {"type": "function", "function": {
        "name": "bash", "description": "Run a shell command in the workspace",
        "parameters": {"type": "object",
                       "properties": {"command": {"type": "string", "description": "shell command to run"}},
                       "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "read_file", "description": "Read a text file from the workspace",
        "parameters": {"type": "object",
                       "properties": {"path": {"type": "string", "description": "file path"}},
                       "required": ["path"]}}},
]
MSGS = [
    {"role": "system", "content": "You are a coding agent working in /workspace."},
    {"role": "user", "content": "Create hello.txt containing exactly 'hello world', then verify it."},
    {"role": "assistant", "content": "",
     "reasoning_content": "I need to create the file first, then read it back to verify.",
     "tool_calls": [{"id": "call_1", "type": "function",
                     "function": {"name": "bash",
                                  "arguments": {"command": "printf 'hello world' > /workspace/hello.txt"}}}]},
]
P1 = r.render_ids(MSGS[:2], tools=TOOLS, add_generation_prompt=True)
print("len(P1) turn-1 generation prompt =", len(P1))
F3 = r.render_ids(MSGS, tools=TOOLS)
print("tape@244..252 decode:", repr(tok.decode(F3[244:252])))
