"""复核 145cb5fd 的 Read 配置接缝；不启动服务、Docker 或模型。

执行实际 Bringup 中的 SlimeBindingConfig 构造表达式，构造前的资源型初始化
不执行。再走实际窗口映射和 CC 环境合并函数，核对现有 extra env 通道。
输出只创建新文件，不覆盖已有证据。
"""

from __future__ import annotations

import argparse
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
    namespace = dict(vars(bringup))
    namespace.update({
        "self": SimpleNamespace(
            renderer=object(), harness_adapter_url="http://review.invalid",
            policy_version="0", max_context_len=32768, staleness_threshold_mirror=None,
        ),
        "template_hash": "sha256:" + "0" * 64,
        "moe_num_layers": None,
        "moe_router_topk": None,
        # 这不是已注册的 CLI 参数，只证明构造点不读取这个字段。
        "args": SimpleNamespace(cc_file_read_max_output_tokens=8000),
    })
    with patch.dict(os.environ, {"RH2_REQUIRE_REAL_WEIGHT_VERSIONS": "0", "RH2_REJECT_NONZERO_HARNESS_EXIT": "0"}):
        config = eval(compile(ast.Expression(call), str(source_path), "eval"), namespace)
    injected = cc_context_env(
        max_context_len=config.max_context_len, max_new_tokens=4096,
        file_read_max_output_tokens=config.cc_file_read_max_output_tokens,
    )

    def launch_env(extra: dict[str, str]) -> dict[str, str]:
        with patch.dict(os.environ, {"SLIME_AGENT_CC_EXTRA_ENVS": json.dumps(extra)}):
            env = bringup.claude_code_launch_env(
                adapter_url="http://review.invalid", session_id="review", model_label="qwen",
                env_injections=injected,
            )
        return {k: v for k, v in env.items() if k in injected or k == CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV}

    plain = launch_env({})
    via_extra_env = launch_env({CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV: "8000"})
    assert config.cc_file_read_max_output_tokens is None
    assert CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV not in plain
    assert via_extra_env[CC_FILE_READ_MAX_OUTPUT_TOKENS_ENV] == "8000"
    return {
        "scope": "actual constructor expression and environment functions; resource initialization not executed",
        "constructor_line": call.lineno,
        "constructor_keyword_present": "cc_file_read_max_output_tokens" in [kw.arg for kw in call.keywords],
        "args_field_is_not_registered_cli": True,
        "config_read_cap": config.cc_file_read_max_output_tokens,
        "production_default_environment": plain,
        "existing_extra_env_channel": via_extra_env,
        "conclusion": "New config field is not wired by Bringup; existing job-wide extra environment can still set the cap.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = json.dumps(run(), ensure_ascii=False, indent=2) + "\n"
    if args.out:
        with args.out.open("x") as handle:
            handle.write(result)
    else:
        print(result, end="")
