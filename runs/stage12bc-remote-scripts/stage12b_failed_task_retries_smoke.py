from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import ray
from omegaconf import OmegaConf
from transformers import AutoTokenizer


MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
IMAGE = "verlai/verl:sgl056.latest"
REPO_ROOT = Path("/workspace/RepoHarness")
RUN_ROOT = REPO_ROOT / "runs" / ("stage12b-failed-task-retries-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
SOURCE_ROOT = RUN_ROOT / "source_repos"
REAL_RUNS_DIR = RUN_ROOT / "real_episode_runs"
SUMMARY_PATH = RUN_ROOT / "stage12b_failed_task_retries_summary.json"


@dataclass(frozen=True)
class RetryTask:
    task_id: str
    repo_name: str
    prompt: str
    first_read_path: str
    files: dict[str, str]


TASKS = [
    RetryTask(
        task_id="stage12b-retry-calculator",
        repo_name="calculator_retry",
        first_read_path="calculator.py",
        prompt=(
            "Fix calculator.divide so division by zero raises ValueError with message division by zero. "
            "Read calculator.py first. After reading it, call edit_file to change calculator.py. "
            "Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"calculator-retry\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "calculator.py": "def add(left: int, right: int) -> int:\n    return left + right\n\n\ndef divide(left: int, right: int) -> float:\n    return left / right\n",
            "tests/test_calculator.py": (
                "import pytest\n\nfrom calculator import add, divide\n\n\n"
                "def test_add():\n    assert add(2, 3) == 5\n\n"
                "def test_divide_regular_numbers():\n    assert divide(8, 2) == 4\n\n"
                "def test_divide_zero():\n    with pytest.raises(ValueError, match='division by zero'):\n        divide(8, 0)\n"
            ),
        },
    ),
    RetryTask(
        task_id="stage12b-retry-clamp",
        repo_name="clamp_retry",
        first_read_path="math_utils.py",
        prompt=(
            "Fix math_utils.clamp so it returns lower for values below lower, upper for values above upper, "
            "and the original value when it is inside the range. Read math_utils.py first. "
            "After reading it, call edit_file to change math_utils.py. Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"clamp-retry\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "math_utils.py": "def clamp(value: int, lower: int, upper: int) -> int:\n    if value < lower:\n        return lower\n    return value\n",
            "tests/test_math_utils.py": (
                "from math_utils import clamp\n\n\n"
                "def test_clamp_low():\n    assert clamp(-5, 0, 10) == 0\n\n"
                "def test_clamp_inside():\n    assert clamp(5, 0, 10) == 5\n\n"
                "def test_clamp_high():\n    assert clamp(15, 0, 10) == 10\n"
            ),
        },
    ),
    RetryTask(
        task_id="stage12b-retry-config-default",
        repo_name="config_retry",
        first_read_path="config_utils.py",
        prompt=(
            "Fix config_utils.get_timeout so missing service names return 30 instead of raising KeyError. "
            "Known service names must keep their configured value. Read config_utils.py first. "
            "After reading it, call edit_file to change config_utils.py. Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"config-retry\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "config_utils.py": "TIMEOUTS = {\"search\": 5, \"index\": 10}\n\n\ndef get_timeout(service: str) -> int:\n    return TIMEOUTS[service]\n",
            "tests/test_config_utils.py": (
                "from config_utils import get_timeout\n\n\n"
                "def test_known_service():\n    assert get_timeout('search') == 5\n\n"
                "def test_unknown_service_default():\n    assert get_timeout('missing') == 30\n"
            ),
        },
    ),
    RetryTask(
        task_id="stage12b-retry-slugify",
        repo_name="slugify_retry",
        first_read_path="text_utils.py",
        prompt=(
            "Fix text_utils.slugify so it lowercases text, strips leading and trailing spaces, "
            "and collapses one or more whitespace characters between words into a single hyphen. "
            "Use a correct Python implementation, for example split and join or re.sub. "
            "Read text_utils.py first. After reading it, call edit_file to change text_utils.py. "
            "Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"slugify-retry\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "text_utils.py": "def slugify(text: str) -> str:\n    return text.lower()\n",
            "tests/test_text_utils.py": (
                "from text_utils import slugify\n\n\n"
                "def test_slugify_basic():\n    assert slugify('Hello World') == 'hello-world'\n\n"
                "def test_slugify_extra_spaces():\n    assert slugify('  Repo   Harness  ') == 'repo-harness'\n"
            ),
        },
    ),
]


def write_sources() -> dict[str, str]:
    result: dict[str, str] = {}
    for task in TASKS:
        repo_dir = SOURCE_ROOT / task.repo_name
        for rel, content in task.files.items():
            path = repo_dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        result[task.task_id] = str(repo_dir)
    return result


def tool_protocol(first_read_path: str) -> str:
    return f"""You are RepoHarness software engineering agent.

When you need a tool, your whole assistant message must be one JSON tool call, either wrapped in <tool_call> tags or as a bare JSON object.

Preferred exact shape:
<tool_call>
{{"name": "read_file", "arguments": {{"path": "{first_read_path}"}}}}
</tool_call>

Allowed tools: read_file, grep, edit_file, git_diff.
Do not output <tool_response>.
Do not output file contents as your assistant answer.
Do not output a patch in Markdown.
After a read_file result, if code must change, call edit_file.
For edit_file, old_text must exactly match current file text and new_text must be the replacement text.
After editing, give a short final answer without a tool call.
Do not use absolute paths. Do not mention evaluator-only information.
""".strip()


class ConfigWrap:
    def __init__(self, config: Any) -> None:
        self.config = config


def trainer_config() -> ConfigWrap:
    rollout = SimpleNamespace(name="sglang", prompt_length=8192, response_length=768)
    return ConfigWrap(SimpleNamespace(actor_rollout_ref=SimpleNamespace(rollout=rollout)))


def verifier_result_from_pytest(workspace_path: Path):
    from repo_harness.verifier import VerifierResult

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace_path,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=30,
        check=False,
    )
    accepted = completed.returncode == 0
    return VerifierResult(
        verifier_stage="final",
        parser_confidence=1.0,
        command=f"{sys.executable} -m pytest -q",
        accepted=accepted,
        pass_ratio=1.0 if accepted else 0.0,
        fail_to_pass={"passed": 1 if accepted else 0, "total": 1},
        pass_to_pass={"passed": 1 if accepted else 0, "total": 1},
        exit_code=completed.returncode,
        error_type=None if accepted else "test_command_error",
    )


def output_logprobs(output: dict[str, Any]) -> list[float]:
    rows = ((output.get("meta_info") or {}).get("output_token_logprobs") or [])
    result: list[float] = []
    for item in rows:
        if isinstance(item, (list, tuple)) and item:
            result.append(0.0 if item[0] is None else float(item[0]))
    return result


def finish_reason(output: dict[str, Any]) -> str | None:
    reason = (output.get("meta_info") or {}).get("finish_reason")
    if reason is None:
        return None
    if isinstance(reason, dict):
        return str(reason.get("type") or reason.get("reason") or reason)
    return str(reason)


class LocalRemoteGenerate:
    def __init__(self, server: "LocalSGLangServerHandle") -> None:
        self.server = server

    def remote(self, **kwargs: Any):
        return self.server.generate_one(**kwargs)


class LocalSGLangServerHandle:
    def __init__(self, engine: Any) -> None:
        self.engine = engine
        self.calls: list[dict[str, Any]] = []
        self.generate = LocalRemoteGenerate(self)

    async def generate_one(self, request_id: str, *, prompt_ids: list[int], sampling_params: dict[str, Any], **kwargs: Any):
        from verl.workers.rollout.replica import TokenOutput

        clean_sampling = {key: value for key, value in dict(sampling_params or {}).items() if value is not None}
        if "max_new_tokens" not in clean_sampling and "max_output_tokens" in clean_sampling:
            clean_sampling["max_new_tokens"] = clean_sampling["max_output_tokens"]
        for unsupported in ["max_output_tokens", "reasoning_effort", "thinking_mode"]:
            clean_sampling.pop(unsupported, None)
        clean_sampling.setdefault("temperature", 0.0)
        clean_sampling.setdefault("top_p", 1.0)
        clean_sampling.setdefault("max_new_tokens", 96)
        clean_sampling["max_new_tokens"] = min(int(clean_sampling["max_new_tokens"]), 96)
        print("RETRY_GENERATE_START", request_id, len(prompt_ids), clean_sampling, flush=True)
        output = await self.engine.async_generate(
            input_ids=[int(item) for item in prompt_ids],
            sampling_params=clean_sampling,
            return_logprob=True,
            logprob_start_len=0,
        )
        text = str(output.get("text") or "")
        print("RETRY_GENERATE_TEXT", text[:500].replace("\n", " "), flush=True)
        token_ids = [int(item) for item in output.get("output_ids") or []]
        log_probs = output_logprobs(output)
        self.calls.append(
            {
                "request_id": request_id,
                "prompt_len": len(prompt_ids),
                "sampling_params": clean_sampling,
                "text": text,
                "token_count": len(token_ids),
                "finish_reason": finish_reason(output),
            }
        )
        return TokenOutput(
            token_ids=token_ids,
            log_probs=log_probs,
            stop_reason=finish_reason(output),
            extra_fields={"global_steps": 1500, "min_global_steps": 1500, "max_global_steps": 1500},
        )


def runtime_options(tokenizer: Any, task: RetryTask, source_paths: dict[str, str]):
    from repo_harness.rl import RepoHarnessRuntimeOptions

    def verifier_factory(context: Any):
        def verify():
            return verifier_result_from_pytest(context.workspace_path)

        return verify

    return RepoHarnessRuntimeOptions(
        runtime_execution_mode="real_episode",
        output_dir=REAL_RUNS_DIR,
        real_episode_source_resolver=lambda _request: Path(source_paths[task.task_id]),
        real_episode_final_verifier_factory=verifier_factory,
        tool_observation_token_projector=lambda content: tokenizer.encode(str(content), add_special_tokens=False)[:96],
        episode_timeout_seconds=180.0,
    )


def sample_kwargs(task: RetryTask, index: int) -> dict[str, Any]:
    return {
        "raw_prompt": [
            {"role": "system", "content": tool_protocol(task.first_read_path)},
            {"role": "user", "content": task.prompt},
        ],
        "agent_name": "repo_harness",
        "task_id": task.task_id,
        "repo_harness_task_ref": {"task_ref": f"rh://task/{task.task_id}"},
        "repo_harness_run_mode": "training_fast",
        "uid": f"uid-{task.task_id}",
        "index": index,
        "session_id": index + 30,
        "global_steps": 1500 + index,
    }


async def run_one_task(tokenizer: Any, client: Any, server: LocalSGLangServerHandle, task: RetryTask, index: int, source_paths: dict[str, str]) -> dict[str, Any]:
    from repo_harness.rl import RepoHarnessRuntime
    from repo_harness_verl.agent_loop import RepoHarnessVerlAgentLoop
    from repo_harness_verl.visibility import validate_transfer_queue_field_visibility

    start_call_index = len(server.calls)
    runtime = RepoHarnessRuntime(runtime_options(tokenizer, task, source_paths))
    loop = RepoHarnessVerlAgentLoop(
        trainer_config=trainer_config(),
        server_manager=client,
        tokenizer=tokenizer,
        processor=None,
        dataset_cls=object,
        data_config=ConfigWrap({"apply_chat_template_kwargs": {}}),
        runtime=runtime,
        inference_backend="sglang",
    )
    kwargs = sample_kwargs(task, index)
    try:
        output = await loop.run({"max_new_tokens": 256, "temperature": 0.0, "top_p": 1.0}, **kwargs)
        field = output.as_dict()
        field.update({"raw_prompt": kwargs["raw_prompt"]})
        validate_transfer_queue_field_visibility(field)
        extra_fields = dict(output.extra_fields)
        run_id = extra_fields.get("repo_harness_run_id")
        run_dir = REAL_RUNS_DIR / str(run_id) if run_id else None
        return {
            "task_id": task.task_id,
            "source_repo": source_paths[task.task_id],
            "status": "completed",
            "repo_harness_status": extra_fields.get("repo_harness_status"),
            "invalid_for_training": extra_fields.get("repo_harness_invalid_for_training"),
            "invalid_for_online_rl": extra_fields.get("repo_harness_invalid_for_online_rl"),
            "reward_score": output.reward_score,
            "num_turns": output.num_turns,
            "response_token_count": len(output.response_ids),
            "response_mask_count": len(output.response_mask),
            "response_logprob_count": 0 if output.response_logprobs is None else len(output.response_logprobs),
            "server_call_count": len(server.calls) - start_call_index,
            "server_calls": server.calls[start_call_index:],
            "run_dir": str(run_dir) if run_dir else None,
            "transfer_queue_visibility": "passed",
        }
    except Exception as exc:
        return {
            "task_id": task.task_id,
            "source_repo": source_paths[task.task_id],
            "status": "failed",
            "failure_type": exc.__class__.__name__,
            "failure_message": str(exc),
            "server_call_count": len(server.calls) - start_call_index,
            "server_calls": server.calls[start_call_index:],
        }


async def run_pool(tokenizer: Any) -> dict[str, Any]:
    from verl.workers.rollout.llm_server import GlobalRequestLoadBalancer, LLMServerClient
    import sglang as sgl

    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    source_paths = write_sources()
    (RUN_ROOT / "tool_protocol_prompt_retry.txt").write_text(tool_protocol("relative/path.py") + "\n", encoding="utf-8")
    if ray.is_initialized():
        ray.shutdown()
    ray.init(ignore_reinit_error=True, include_dashboard=False, num_gpus=2, logging_level="ERROR")
    engine = sgl.Engine(
        model_path=MODEL_ID,
        tp_size=1,
        context_length=8192,
        mem_fraction_static=0.55,
        attention_backend="flashinfer",
        disable_cuda_graph=True,
    )
    server = LocalSGLangServerHandle(engine)
    servers = {"sglang0": server}
    load_balancer = GlobalRequestLoadBalancer.remote({"sglang0": None})
    client = LLMServerClient(OmegaConf.create({}), servers, load_balancer)
    results = []
    for index, task in enumerate(TASKS):
        print("RETRY_TASK_START", task.task_id, flush=True)
        result = await run_one_task(tokenizer, client, server, task, index, source_paths)
        results.append(result)
        print("RETRY_TASK_DONE", task.task_id, result.get("status"), result.get("repo_harness_status"), flush=True)
    completed = [item for item in results if item.get("status") == "completed"]
    succeeded = [item for item in completed if item.get("repo_harness_status") == "succeeded"]
    return {
        "schema_version": "repo_harness_stage12b_failed_task_retries_summary_v0",
        "status": "completed",
        "model_id": MODEL_ID,
        "image": IMAGE,
        "run_root": str(RUN_ROOT),
        "source_root": str(SOURCE_ROOT),
        "repo_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip(),
        "task_count": len(TASKS),
        "completed_count": len(completed),
        "succeeded_count": len(succeeded),
        "results": results,
        "server_call_count": len(server.calls),
    }


def main() -> None:
    os.environ.setdefault("HF_HOME", "/workspace/hf_cache")
    os.environ.setdefault("TRANSFORMERS_CACHE", "/workspace/hf_cache")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, trust_remote_code=True)
    try:
        summary = asyncio.run(run_pool(tokenizer))
    except Exception as exc:
        summary = {
            "schema_version": "repo_harness_stage12b_failed_task_retries_summary_v0",
            "status": "failed",
            "failure_type": exc.__class__.__name__,
            "failure_message": str(exc),
            "run_root": str(RUN_ROOT),
        }
        raise
    finally:
        if "summary" in locals():
            RUN_ROOT.mkdir(parents=True, exist_ok=True)
            SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True), flush=True)
        if ray.is_initialized():
            ray.shutdown()


if __name__ == "__main__":
    main()
