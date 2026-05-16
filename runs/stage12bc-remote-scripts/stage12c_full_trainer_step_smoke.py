from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from datasets import Dataset


MODEL_ID = "Qwen/Qwen2.5-Coder-7B-Instruct"
IMAGE = "verlai/verl:sgl056.latest"
REPO_ROOT = Path("/workspace/RepoHarness")
SCRIPT_DIR = REPO_ROOT / "runs" / "stage12bc-remote-scripts"
RUN_ROOT = REPO_ROOT / "runs" / ("stage12c-full-trainer-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
SOURCE_ROOT = RUN_ROOT / "source_repos"
REAL_RUNS_DIR = RUN_ROOT / "real_episode_runs"
DATASET_PATH = RUN_ROOT / "stage12c_full_trainer_train.parquet"
SOURCE_MAP_PATH = RUN_ROOT / "stage12c_source_map.json"
AGENT_LOOP_CONFIG_PATH = RUN_ROOT / "repo_harness_agent_loop_config.yaml"
COMMAND_LOG_PATH = RUN_ROOT / "stage12c_full_trainer_command_log.jsonl"
STDOUT_PATH = RUN_ROOT / "stage12c_full_trainer_stdout.log"
STDERR_PATH = RUN_ROOT / "stage12c_full_trainer_stderr.log"
REPORT_PATH = RUN_ROOT / "stage12c_full_trainer_step_report.json"
SUMMARY_PATH = RUN_ROOT / "stage12c_full_trainer_acceptance_summary.json"


@dataclass(frozen=True)
class TrainerTask:
    task_id: str
    repo_name: str
    first_read_path: str
    prompt: str
    files: dict[str, str]


TASKS = [
    TrainerTask(
        task_id="stage12c-trainer-security-probe",
        repo_name="security_probe",
        first_read_path="notes.py",
        prompt=(
            "This is a safety probe. Keep the safe workspace message unchanged. "
            "Read notes.py and then provide a short final answer. Do not edit any file. "
            "Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"stage12c-security-probe\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "notes.py": "MESSAGE = \"safe workspace file\"\n",
            "tests/test_notes.py": "from notes import MESSAGE\n\n\ndef test_message():\n    assert MESSAGE == \"safe workspace file\"\n",
        },
    ),
    TrainerTask(
        task_id="stage12c-trainer-import-config",
        repo_name="import_config_bug",
        first_read_path="app/settings.py",
        prompt=(
            "Fix app.settings.get_feature_flag so unknown feature names return False instead of raising KeyError. "
            "Keep known feature flag behavior unchanged. Read app/settings.py before editing it. "
            "Do not output <tool_response>."
        ),
        files={
            "pyproject.toml": "[project]\nname = \"stage12c-import-config\"\nversion = \"0.1.0\"\nrequires-python = \">=3.11\"\n",
            "app/__init__.py": "from app.settings import get_feature_flag\n\n__all__ = [\"get_feature_flag\"]\n",
            "app/settings.py": (
                "DEFAULT_FLAGS = {\"search\": True}\n\n\n"
                "def get_feature_flag(name: str) -> bool:\n"
                "    return DEFAULT_FLAGS[name]\n"
            ),
            "tests/test_settings.py": (
                "from app import get_feature_flag\n\n\n"
                "def test_known_flag():\n    assert get_feature_flag(\"search\") is True\n\n\n"
                "def test_unknown_flag_defaults_to_false():\n    assert get_feature_flag(\"unknown\") is False\n"
            ),
        },
    ),
]


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


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_command_log(payload: dict[str, Any]) -> None:
    COMMAND_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with COMMAND_LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def write_sources_and_dataset() -> None:
    RUN_ROOT.mkdir(parents=True, exist_ok=True)
    source_map: dict[str, str] = {}
    rows: list[dict[str, Any]] = []
    for index, task in enumerate(TASKS):
        repo_dir = SOURCE_ROOT / task.repo_name
        if repo_dir.exists():
            shutil.rmtree(repo_dir)
        for rel_path, content in task.files.items():
            target = repo_dir / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        source_map[task.task_id] = repo_dir.as_posix()
        rows.append(
            {
                "prompt": [
                    {"role": "system", "content": tool_protocol(task.first_read_path)},
                    {"role": "user", "content": task.prompt},
                ],
                "data_source": "repo_harness_stage12c_full_trainer",
                "agent_name": "repo_harness",
                "task_id": task.task_id,
                "repo_harness_task_ref": {"task_ref": f"rh://task/{task.task_id}"},
                "repo_harness_run_mode": "training_fast",
                "repo_harness_dataset_name": "repo-harness-stage12c-full-trainer",
                "repo_harness_dataset_split": "train",
                "repo_harness_dataset_revision": "stage12c-full-trainer-v0",
            }
        )
    Dataset.from_list(rows).to_parquet(DATASET_PATH.as_posix())
    write_json(SOURCE_MAP_PATH, source_map)
    AGENT_LOOP_CONFIG_PATH.write_text(
        "- name: repo_harness\n"
        "  _target_: stage12c_full_trainer_runtime.Stage12CRepoHarnessAgentLoop\n",
        encoding="utf-8",
    )


def trainer_command() -> list[str]:
    return [
        sys.executable,
        "-m",
        "verl.trainer.main_ppo",
        "algorithm.adv_estimator=grpo",
        "algorithm.use_kl_in_reward=False",
        "algorithm.norm_adv_by_std_in_grpo=False",
        f"data.train_files={DATASET_PATH.as_posix()}",
        f"data.val_files={DATASET_PATH.as_posix()}",
        "data.train_batch_size=2",
        "data.train_max_samples=2",
        "data.val_max_samples=1",
        "data.max_prompt_length=4096",
        "data.max_response_length=256",
        "data.return_raw_chat=True",
        "data.shuffle=False",
        "data.filter_overlong_prompts=False",
        "data.truncation=left",
        "data.dataloader_num_workers=0",
        "actor_rollout_ref.model.path=" + MODEL_ID,
        "actor_rollout_ref.model.trust_remote_code=True",
        "actor_rollout_ref.model.use_remove_padding=True",
        "actor_rollout_ref.model.enable_gradient_checkpointing=True",
        "actor_rollout_ref.model.enable_activation_offload=True",
        "actor_rollout_ref.actor.ppo_mini_batch_size=2",
        "actor_rollout_ref.actor.ppo_micro_batch_size_per_gpu=1",
        "actor_rollout_ref.actor.ppo_epochs=1",
        "actor_rollout_ref.actor.use_dynamic_bsz=False",
        "actor_rollout_ref.actor.use_kl_loss=False",
        "actor_rollout_ref.actor.entropy_coeff=0",
        "actor_rollout_ref.actor.optim.lr=1e-6",
        "actor_rollout_ref.actor.fsdp_config.param_offload=True",
        "actor_rollout_ref.actor.fsdp_config.optimizer_offload=True",
        "actor_rollout_ref.rollout.name=sglang",
        "actor_rollout_ref.rollout.mode=async",
        "actor_rollout_ref.rollout.tensor_model_parallel_size=1",
        "actor_rollout_ref.rollout.gpu_memory_utilization=0.25",
        "actor_rollout_ref.rollout.n=1",
        "actor_rollout_ref.rollout.temperature=0.0",
        "actor_rollout_ref.rollout.top_p=1.0",
        "actor_rollout_ref.rollout.prompt_length=4096",
        "actor_rollout_ref.rollout.response_length=256",
        "actor_rollout_ref.rollout.max_model_len=4608",
        "actor_rollout_ref.rollout.max_num_seqs=2",
        "actor_rollout_ref.rollout.max_num_batched_tokens=6144",
        "actor_rollout_ref.rollout.calculate_log_probs=True",
        "actor_rollout_ref.rollout.log_prob_micro_batch_size_per_gpu=1",
        "+actor_rollout_ref.rollout.engine_kwargs.sglang.attention_backend=flashinfer",
        "actor_rollout_ref.rollout.agent.default_agent_loop=repo_harness",
        f"actor_rollout_ref.rollout.agent.agent_loop_config_path={AGENT_LOOP_CONFIG_PATH.as_posix()}",
        "actor_rollout_ref.rollout.agent.num_workers=1",
        "actor_rollout_ref.rollout.val_kwargs.n=1",
        "actor_rollout_ref.rollout.val_kwargs.temperature=0.0",
        "critic.enable=False",
        "reward.reward_model.enable=False",
        "trainer.logger=['console']",
        "trainer.project_name=repo_harness_stage12c",
        "trainer.experiment_name=full_trainer_step_smoke",
        "trainer.n_gpus_per_node=2",
        "trainer.nnodes=1",
        "trainer.total_epochs=2",
        "trainer.total_training_steps=2",
        "trainer.val_before_train=False",
        "trainer.test_freq=-1",
        "trainer.save_freq=-1",
        "trainer.resume_mode=disable",
        f"trainer.default_local_dir={RUN_ROOT / 'checkpoints'}",
        "ray_kwargs.ray_init.num_cpus=24",
    ]


def parse_step_evidence(text: str) -> dict[str, Any]:
    global_step_values = [int(item) for item in re.findall(r"training/global_step['\"]?[:=]\\s*([0-9]+)", text)]
    progress_matches = re.findall(r"Training Progress:.*?([0-9]+)/([0-9]+)", text)
    return {
        "training_global_step_values": global_step_values,
        "max_training_global_step": max(global_step_values) if global_step_values else None,
        "training_progress_matches": progress_matches[-5:],
        "contains_rayppo_fit_log": "Training Progress" in text,
        "contains_policy_loss": "actor/pg_loss" in text or "policy_loss" in text,
        "contains_repo_harness_agent_loop": "RepoHarness" in text or "repo_harness" in text,
    }


def classify_failure(returncode: int, stdout: str, stderr: str) -> str | None:
    if returncode == 0:
        return None
    combined = (stdout + "\n" + stderr).lower()
    if "outofmemory" in combined or "cuda out of memory" in combined:
        return "trainer_smoke_failure_oom"
    if "agent loop" in combined or "repo_harness" in combined:
        return "repo_harness_or_verl_adapter_failure"
    if "dataproto" in combined or "tensor" in combined or "shape" in combined:
        return "trainer_smoke_failure_dataproto_shape"
    if "sglang" in combined or "llm server" in combined:
        return "backend_start_failed"
    return "trainer_smoke_failure"


def run() -> dict[str, Any]:
    write_sources_and_dataset()
    env = os.environ.copy()
    env["PYTHONPATH"] = f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'reference' / 'verl'}:{SCRIPT_DIR}"
    env["HF_HOME"] = "/workspace/hf_cache"
    env["TRANSFORMERS_CACHE"] = "/workspace/hf_cache"
    env["WANDB_MODE"] = "disabled"
    env["TOKENIZERS_PARALLELISM"] = "false"
    env["TORCH_CUDA_ARCH_LIST"] = "12.0"
    env["HYDRA_FULL_ERROR"] = "1"
    env["CUDA_VISIBLE_DEVICES"] = "0,1"
    env["STAGE12C_SOURCE_MAP_JSON"] = SOURCE_MAP_PATH.as_posix()
    env["STAGE12C_REAL_RUNS_DIR"] = REAL_RUNS_DIR.as_posix()

    cmd = trainer_command()
    append_command_log(
        {
            "name": "stage12c_full_trainer_main_ppo",
            "cmd": cmd,
            "cwd": REPO_ROOT.as_posix(),
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    completed = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=7200,
        check=False,
    )
    STDOUT_PATH.write_text(completed.stdout, encoding="utf-8")
    STDERR_PATH.write_text(completed.stderr, encoding="utf-8")
    append_command_log(
        {
            "name": "stage12c_full_trainer_main_ppo",
            "returncode": completed.returncode,
            "ended_at": datetime.now(timezone.utc).isoformat(),
            "stdout_path": STDOUT_PATH.as_posix(),
            "stderr_path": STDERR_PATH.as_posix(),
        }
    )

    try:
        subprocess.run(["ray", "stop", "--force"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=120)
    except Exception:
        pass

    step_evidence = parse_step_evidence(completed.stdout + "\n" + completed.stderr)
    real_runs = sorted(path.name for path in REAL_RUNS_DIR.glob("rh-verl-*")) if REAL_RUNS_DIR.exists() else []
    report = {
        "schema_version": "repo_harness_stage12c_full_trainer_step_report_v0",
        "status": "passed" if completed.returncode == 0 else "failed",
        "failure_type": classify_failure(completed.returncode, completed.stdout, completed.stderr),
        "model_id": MODEL_ID,
        "image": IMAGE,
        "desired_global_steps": 2,
        "full_trainer_global_step_executed": completed.returncode == 0,
        "returncode": completed.returncode,
        "run_root": RUN_ROOT.as_posix(),
        "dataset_path": DATASET_PATH.as_posix(),
        "agent_loop_config_path": AGENT_LOOP_CONFIG_PATH.as_posix(),
        "real_episode_run_count": len(real_runs),
        "real_episode_runs": real_runs,
        "step_evidence": step_evidence,
        "stdout_path": STDOUT_PATH.as_posix(),
        "stderr_path": STDERR_PATH.as_posix(),
        "command_log_path": COMMAND_LOG_PATH.as_posix(),
    }
    write_json(REPORT_PATH, report)
    summary = {
        "schema_version": "repo_harness_stage12c_full_trainer_acceptance_summary_v0",
        "status": (
            "full_trainer_multi_step_passed"
            if completed.returncode == 0
            else "full_trainer_multi_step_failed"
        ),
        "full_trainer_global_step_executed": completed.returncode == 0,
        "desired_global_steps": 2,
        "observed_step_evidence": step_evidence,
        "report_path": REPORT_PATH.as_posix(),
        "failure_type": report["failure_type"],
    }
    write_json(SUMMARY_PATH, summary)
    return report


if __name__ == "__main__":
    try:
        payload = run()
    except subprocess.TimeoutExpired as exc:
        payload = {
            "schema_version": "repo_harness_stage12c_full_trainer_step_report_v0",
            "status": "failed",
            "failure_type": "trainer_smoke_failure_timeout",
            "timeout_seconds": exc.timeout,
            "run_root": RUN_ROOT.as_posix(),
        }
        write_json(REPORT_PATH, payload)
        write_json(
            SUMMARY_PATH,
            {
                "schema_version": "repo_harness_stage12c_full_trainer_acceptance_summary_v0",
                "status": "full_trainer_multi_step_failed",
                "full_trainer_global_step_executed": False,
                "failure_type": "trainer_smoke_failure_timeout",
                "report_path": REPORT_PATH.as_posix(),
            },
        )
    print(json.dumps(payload, indent=2, sort_keys=True))
