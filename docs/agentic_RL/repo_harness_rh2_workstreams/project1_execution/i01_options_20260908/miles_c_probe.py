"""I01 有界 CPU 探针：真实缓存 tokenizer；合成消息，不是 CLI / 推理服务端到端。

运行：rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/i01_options_20260908/miles_c_probe.py
只读 miles 源码；AST 原样提取 Qwen 路径，避免导入本机未安装的 SGLang。
仅隔离非 Qwen 分支及 tools=None 时未执行的 schema 校验；不模拟 tokenizer。
"""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import os
import platform
import subprocess
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"

import transformers
from jinja2 import TemplateError
from transformers import AutoTokenizer

OUT = Path(__file__).resolve().parent
ROOT = next(p for p in OUT.parents if (p / "rh2/pyproject.toml").is_file())
MILES = ROOT / "reference/miles-rh2-integration"
CHAT = MILES / "miles/utils/chat_template_utils"
PIN = "98a0272e4158b2c20e3a34d210c79b50159af0f6"
MODEL = "Qwen/Qwen3-30B-A3B"
REVISION = "ad44e777bcd18fa416d9da3bd8f70d33ebb85d39"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_matchers():
    # 跳过包 __init__ 的无关依赖；以下两个源码模块完整执行。
    for name, path in (
        ("miles", MILES / "miles"),
        ("miles.utils", MILES / "miles/utils"),
        ("miles.utils.chat_template_utils", CHAT),
        ("miles.utils.chat_template_utils.message_matcher_hub", CHAT / "message_matcher_hub"),
    ):
        module = types.ModuleType(name)
        module.__path__ = [str(path)]
        sys.modules[name] = module
    for short in ("utils", "funcs"):
        name = "miles.utils.chat_template_utils.message_matcher_hub." + short
        spec = importlib.util.spec_from_file_location(name, CHAT / "message_matcher_hub" / (short + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def load_ast(path, names, namespace):
    tree = ast.parse(path.read_text())
    selected, found = [], set()
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            selected.append(node)
        elif isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in names:
            selected.append(node)
            found.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            matched = {t.id for t in targets if isinstance(t, ast.Name)} & names
            if matched:
                selected.append(node)
                found.update(matched)
    assert found == names, (found, names)
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)


def no_tools(tools):
    assert tools is None, "此探针只覆盖 tools=None 的渲染分支"
    return None


def assistant(arguments, reasoning="TRACE_THINK", name="Edit"):
    message = {"role": "assistant", "content": "", "tool_calls": [
        {"type": "function", "function": {"name": name, "arguments": arguments}}
    ]}
    if reasoning is not None:
        message["reasoning_content"] = reasoning
    return message


def outcome(fn):
    try:
        value = fn()
        return {"accepted": True, "value": value}
    except ValueError as exc:
        # args[0] 保留上游错误原文，不打印无关 traceback / 本机路径。
        return {"accepted": False, "error": str(exc.args[0])}


def main():
    commit = subprocess.check_output(["git", "-C", str(MILES), "rev-parse", "HEAD"], text=True).strip()
    assert commit == PIN, commit
    matchers = load_matchers()
    template_namespace = dict(
        copy=copy, json=json, TemplateError=TemplateError,
        deepseek=types.SimpleNamespace(model_type=lambda _: None),
        inkling=types.SimpleNamespace(is_inkling=lambda _: False),
        extract_tool_dicts=no_tools,
    )
    load_ast(CHAT / "template.py", {"normalize_tool_arguments", "apply_chat_template"}, template_namespace)
    module = types.ModuleType("i01_qwen_ast")
    sys.modules[module.__name__] = module
    module.__dict__.update(
        Any=Any, Path=Path, dataclass=dataclass, field=field,
        template=types.SimpleNamespace(apply_chat_template=template_namespace["apply_chat_template"]),
        assert_messages_append_only_with_allowed_role=matchers.assert_messages_append_only_with_allowed_role,
    )
    load_ast(CHAT / "tito_tokenizer.py", {
        "VALID_APPEND_ROLES", "ALL_APPEND_ROLES", "_DUMMY_SYSTEM", "FixedTemplate",
        "_build_dummy_assistant", "TITOTokenizer", "Qwen3TITOTokenizer",
    }, module.__dict__)
    qwen_class = module.Qwen3TITOTokenizer
    native = AutoTokenizer.from_pretrained(MODEL, revision=REVISION, local_files_only=True, trust_remote_code=False)
    fixed = copy.deepcopy(native)
    fixed.chat_template = (CHAT / "templates/qwen3_fixed.jinja").read_text()
    native_tito, fixed_tito = qwen_class(native), qwen_class(fixed)
    assert "clear_thinking" not in native.chat_template
    assert native_tito.tokenizer.chat_template == native.chat_template

    a_dict = {"file_path": "a.py", "old_string": "a", "new_string": "b", "replace_all": False}
    b_dict = {"replace_all": False, "new_string": "b", "old_string": "a", "file_path": "a.py"}
    a_string = json.dumps(a_dict)
    b_string = json.dumps(b_dict)
    pairs = {
        "dict_key_order": (assistant(a_dict), assistant(b_dict)),
        "json_string_key_order": (assistant(a_string), assistant(b_string)),
        "json_string_vs_dict": (assistant(a_string), assistant(b_dict)),
        "missing_nonempty_thinking": (assistant(a_dict), assistant(a_dict, reasoning=None)),
        "changed_tool_name": (assistant(a_dict), assistant(a_dict, name="Delete")),
        "changed_tool_arguments": (assistant(a_dict), assistant({**a_dict, "new_string": "c"})),
        "dict_boolean_vs_integer": (assistant({"value": True}), assistant({"value": 1})),
        "json_boolean_vs_integer": (assistant('{"value": true}'), assistant('{"value": 1}')),
        "duplicate_json_key": (assistant('{"value": 1, "value": 2}'), assistant('{"value": 2}')),
        "array_order": (assistant({"value": [1, 2]}), assistant({"value": [2, 1]})),
    }
    matrix = {name: {
        "strict": matchers.strict_message_matches(left, right),
        "loose_tool_call": matchers.loose_tool_call_message_matches(left, right),
        "role_content_only": matchers.role_content_only_message_matches(left, right),
    } for name, (left, right) in pairs.items()}
    assert matrix["dict_key_order"] == dict(strict=True, loose_tool_call=True, role_content_only=True)
    assert matrix["json_string_key_order"] == dict(strict=False, loose_tool_call=True, role_content_only=True)
    assert matrix["missing_nonempty_thinking"] == dict(strict=False, loose_tool_call=False, role_content_only=True)
    assert matrix["dict_boolean_vs_integer"] == dict(strict=True, loose_tool_call=True, role_content_only=True)
    assert matrix["json_boolean_vs_integer"]["loose_tool_call"] is False
    assert matrix["duplicate_json_key"]["loose_tool_call"] is False
    assert matrix["array_order"]["loose_tool_call"] is False

    opening = [{"role": "system", "content": "You fix code."}, {"role": "user", "content": "Replace a with b in a.py."}]
    stored = opening + [assistant(a_dict)]
    tail_tool = [{"role": "tool", "content": "File updated."}]
    tail_reminder = tail_tool + [{"role": "user", "content": "<system-reminder>Continue.</system-reminder>"}]
    prompt_ids = native_tito.apply_chat_template(opening, add_generation_prompt=True, tokenize=True)
    # 特意使用紧凑 JSON；这是合成输出，保留真实 tokenizer 编码结果，未调用任何模型。
    action_text = '<think>\nTRACE_THINK\n</think>\n\n<tool_call>\n' + json.dumps(
        {"name": "Edit", "arguments": a_dict}, separators=(",", ":")
    ) + '\n</tool_call><|im_end|>'
    action_ids = native.encode(action_text, add_special_tokens=False)
    prefix = prompt_ids + action_ids

    def merge_result(tito, old, new):
        result = outcome(lambda: tito.merge_tokens(old, new, prefix))
        if result["accepted"]:
            token_ids = result.pop("value")
            result.update(
                prefix_preserved=token_ids[:len(prefix)] == prefix,
                prefix_tokens=len(prefix), total_tokens=len(token_ids),
                inserted_boundary_token=token_ids[len(prefix)],
                suffix_text=native.decode(token_ids[len(prefix):], skip_special_tokens=False),
            )
        return result

    native_reminder_text = native_tito.apply_chat_template(stored + tail_reminder, add_generation_prompt=True)
    native_default_text = template_namespace["apply_chat_template"](
        stored + tail_reminder, tokenizer=native, add_generation_prompt=True
    )
    fixed_reminder_text = fixed_tito.apply_chat_template(stored + tail_reminder, add_generation_prompt=True)
    omitted = opening + [assistant(a_dict, reasoning=None)] + tail_tool
    compacted = [opening[0], {"role": "user", "content": "Summary: a.py was updated. Continue."}]
    stored_string = opening + [assistant(a_string)]
    replay_string = opening + [assistant(b_string)] + tail_tool
    canonical_replay = stored_string + replay_string[len(stored_string):]
    merges = {
        "native_tool_only": merge_result(native_tito, stored, stored + tail_tool),
        "native_user_reminder": merge_result(native_tito, stored, stored + tail_reminder),
        "fixed_user_reminder": merge_result(fixed_tito, stored, stored + tail_reminder),
        "fixed_reordered_dict": merge_result(fixed_tito, stored, opening + [assistant(b_dict)] + tail_tool),
        "loose_match_then_raw_merge": merge_result(fixed_tito, stored_string, replay_string),
        "loose_match_then_stored_prefix_merge": merge_result(fixed_tito, stored_string, canonical_replay),
        "missing_cli_thinking": merge_result(fixed_tito, stored, omitted),
        "synthetic_compaction": merge_result(fixed_tito, stored, compacted),
    }
    assert merges["native_tool_only"]["prefix_preserved"]
    assert merges["native_user_reminder"]["prefix_preserved"]
    assert merges["fixed_user_reminder"]["prefix_preserved"]
    assert merges["fixed_reordered_dict"]["prefix_preserved"]
    assert not merges["loose_match_then_raw_merge"]["accepted"]
    assert merges["loose_match_then_stored_prefix_merge"]["prefix_preserved"]
    assert not merges["missing_cli_thinking"]["accepted"]
    assert not merges["synthetic_compaction"]["accepted"]
    assert native_default_text == native_reminder_text
    assert "TRACE_THINK" not in native_reminder_text
    assert "TRACE_THINK" in fixed_reminder_text
    assert "TRACE_THINK" not in fixed_tito.apply_chat_template(omitted, add_generation_prompt=True)
    native_a = native_tito.apply_chat_template(stored + tail_tool, add_generation_prompt=True, tokenize=True)
    native_b = native_tito.apply_chat_template(opening + [assistant(b_dict)] + tail_tool, add_generation_prompt=True, tokenize=True)
    assert native_a != native_b
    dummy_base = [module._DUMMY_SYSTEM, module._build_dummy_assistant(stored[-1])]
    dummy_renders = {}
    for label, tito in (("native", native_tito), ("fixed", fixed_tito)):
        before = tito.apply_chat_template(dummy_base, add_generation_prompt=False)
        after = tito.apply_chat_template(dummy_base + tail_reminder, add_generation_prompt=True)
        assert after.startswith(before)
        dummy_renders[label] = {"before": before, "after": after, "prefix_stable": after.startswith(before)}
    assert "<think>" not in dummy_renders["native"]["before"]
    assert "<think>" in dummy_renders["fixed"]["before"]
    sources = [CHAT / "tito_tokenizer.py", CHAT / "template.py", CHAT / "templates/qwen3_fixed.jinja",
               CHAT / "message_matcher_hub/funcs.py", CHAT / "message_matcher_hub/utils.py"]
    output = {
        "scope": "缓存真实 tokenizer；合成消息与输出 token；未执行 CLI、SGLang、模型采样、训练或 tools schema 校验",
        "miles_integration_commit": commit, "model": MODEL, "model_revision": REVISION,
        "python": platform.python_version(), "transformers": transformers.__version__,
        "source_sha256": {str(p.relative_to(ROOT)): digest(p) for p in sources},
        "probe_sha256": digest(Path(__file__)),
        "native_chat_template_sha256": hashlib.sha256(native.chat_template.encode()).hexdigest(),
        "matcher_inputs": pairs, "matcher_results": matrix,
        "messages": {"stored": stored, "tool_tail": tail_tool, "reminder_tail": tail_reminder,
                     "missing_thinking": omitted, "compaction": compacted},
        "synthetic_prompt_ids": prompt_ids, "synthetic_output_text": action_text, "synthetic_output_ids": action_ids,
        "template_results": {
            "constructor_installs_fixed_template": False,
            "native_clear_thinking_false_ignored": native_default_text == native_reminder_text,
            "native_reminder_retains_thinking": "TRACE_THINK" in native_reminder_text,
            "fixed_reminder_retains_thinking": "TRACE_THINK" in fixed_reminder_text,
            "native_full_render_dict_key_order_changes_tokens": native_a != native_b,
            "native_reminder_text": native_reminder_text, "fixed_reminder_text": fixed_reminder_text,
        },
        "dummy_prefix_renders": dummy_renders,
        "falsified_probe_hypothesis": "首跑预期 native + reminder 会 suffix-diff 失败；实测成功。源码与实际 dummy 渲染显示 native 的 dummy assistant 从开始就不含 thinking，因此追加 reminder 没有删除 dummy 文本。此处已纠正探针预期，产品源码未变。",
        "merge_results": merges, "assertions": "passed",
    }
    result_path = OUT / "miles_c_probe_result.json"
    result_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"assertions": "passed", "result": str(result_path.relative_to(ROOT)),
                      "matcher_results": matrix, "merge_results": merges}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
