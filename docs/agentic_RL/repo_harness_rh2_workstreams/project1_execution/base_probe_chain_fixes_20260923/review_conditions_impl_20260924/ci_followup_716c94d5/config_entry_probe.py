"""CI1 复核：执行当前 Bringup 的真实构造表达式，再走窗口映射与 CC 环境合并。

不执行资源初始化，不启动 Docker/CC；collector 运输由维护测试覆盖。
运行结果另存，不改上轮反例。
"""

from __future__ import annotations

import ast
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

REPO = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").is_file())
sys.path.insert(0, str(REPO / "rh2/src"))


def run() -> dict:
    from repoharness2.adapters.slime import bringup
    from repoharness2.adapters.slime.cc_launch_conditions import (
        CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV,
        cc_context_env,
    )

    source_path = Path(bringup.__file__)
    tree = ast.parse(source_path.read_text())
    service = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "BringupService")
    start = next(n for n in service.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "_async_start_body")
    calls = [
        n for n in ast.walk(start)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "SlimeBindingConfig"
    ]
    assert len(calls) == 1
    call = calls[0]
    assert "cc_file_read_max_output_tokens" in [kw.arg for kw in call.keywords]
    namespace = dict(vars(bringup))
    namespace.update({
        "self": SimpleNamespace(
            renderer=object(), harness_adapter_url="http://review.invalid",
            policy_version="0", max_context_len=32768, staleness_threshold_mirror=None,
        ),
        "template_hash": "sha256:" + "0" * 64,
        "moe_num_layers": None,
        "moe_router_topk": None,
    })
    expression = compile(ast.Expression(call), str(source_path), "eval")
    cases = []
    for name, raw, extra, expected in (
        ("configured", "8000", None, "8000"),
        ("unset", None, None, None),
        ("empty", "", None, None),
        ("spaces", " 8000 ", None, "8000"),
        ("explicit_beats_extra_env", "8000", "7000", "8000"),
        ("extra_env_when_unset", None, "7000", "7000"),
        ("zero", "0", None, "ValueError"),
        ("negative", "-1", None, "ValueError"),
        ("nonnumeric", "8k", None, "ValueError"),
    ):
        with patch.dict(os.environ, {
            "RH2_REQUIRE_REAL_WEIGHT_VERSIONS": "0", "RH2_REJECT_NONZERO_HARNESS_EXIT": "0",
            "SLIME_AGENT_CC_EXTRA_ENVS": json.dumps({CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV: extra} if extra else {}),
        }):
            if raw is None:
                os.environ.pop(bringup.CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV, None)
            else:
                os.environ[bringup.CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV] = raw
            try:
                config = eval(expression, namespace)
            except ValueError:
                assert expected == "ValueError", name
                cases.append({"name": name, "result": "ValueError"})
                continue
            injected = cc_context_env(
                max_context_len=config.max_context_len, max_new_tokens=4096,
                file_read_max_output_tokens=config.cc_file_read_max_output_tokens,
            )
            env = bringup.claude_code_launch_env(
                adapter_url="http://review.invalid", session_id="review", model_label="qwen",
                env_injections=injected,
            )
            actual = env.get(CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV)
            assert actual == expected, (name, actual, expected)
            cases.append({"name": name, "config": config.cc_file_read_max_output_tokens, "cc_environment": actual})
    return {
        "scope": "actual constructor expression, mapping and environment merge; no resource initialization",
        "constructor_line": call.lineno,
        "cases": cases,
    }


if __name__ == "__main__":
    result = json.dumps(run(), ensure_ascii=False, indent=2) + "\n"
    with Path(__file__).with_suffix(".json").open("x") as handle:
        handle.write(result)
    print(result, end="")
