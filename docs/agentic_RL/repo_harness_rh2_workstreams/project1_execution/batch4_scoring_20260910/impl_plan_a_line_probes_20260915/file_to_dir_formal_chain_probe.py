"""A 线补充探针（CPU，正式链 fa_formal）：候选把普通文件 `config` 变成目录（post 只有 `config/default.json`），
以及反向（基线 `config/default.json`，post 只有普通文件 `config`）时，正式 rollout 链的收口是什么。

从仓库根运行：
  PYTHONDONTWRITEBYTECODE=1 rh2/.venv/bin/python -m pytest -q -s -p no:cacheprovider \
    docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_a_line_probes_20260915/file_to_dir_formal_chain_probe.py

复用 rh2/tests/adapters 的替身：rollout 基线 census 由 FakeRolloutDocker 的 exec 罐头给出（此处子类改成含指定文件），
post census / 内容抓取由 W3a 屏障替身给出；评分侧是真实 SWEGradingManager + FakeDocker。不运行 Docker、模型或 GPU。
三个用例都只打印观察结果并断言"当前行为"（run-fatal / completed），用于钉住修复前的事实；修复后应改成断言新通道。"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest

REPO_ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "rh2/src").is_dir())
sys.path.insert(0, str(REPO_ROOT / "rh2/src"))
sys.path.insert(0, str(REPO_ROOT / "rh2/tests/adapters"))
sys.path.insert(0, str(REPO_ROOT / "rh2/tests/grading"))

from test_w3a_formal_grading_freeze import _formal_chain, _steps, make_barrier  # noqa: E402
from test_slime_generate import _Args, SAMPLING_PARAMS, FakeRolloutDocker  # noqa: E402
from repoharness2.adapters.slime.generate import FatalExecutionInfrastructureError  # noqa: E402
from repoharness2.grading.manager import ExecResult  # noqa: E402


def _census_line(path: str, content: bytes) -> str:
    return f"regular\t100644\t{hashlib.sha256(content).hexdigest()}\t{path}\n"


class _DockerWithBaseline(FakeRolloutDocker):
    """rollout 基线 census 罐头：按 baseline_regular 给出 regular 行（原替身是空树）。"""

    baseline_regular: dict[str, bytes] = {}

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        if args and args[0] == "exec" and "find ." in args[-1] and "sha256sum" in args[-1]:
            return ExecResult(0, "".join(_census_line(p, c) for p, c in sorted(self.baseline_regular.items())), "")
        return await super().__call__(*args, input_bytes=input_bytes)


async def _run(baseline: dict[str, bytes], post: dict[str, bytes], label: str) -> str:
    docker = _DockerWithBaseline(exec_after_rm_raises=True)
    docker.baseline_regular = baseline
    chain = _formal_chain(barrier=make_barrier(regular=post), docker=docker)
    try:
        delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    except FatalExecutionInfrastructureError as exc:
        audit = chain.orchestrator.audits[0]
        print(f"[{label}] RUN-FATAL reason_code={getattr(exc, 'reason_code', None)!r}")
        print(f"[{label}] failure_records={[(r.stage, r.error_type, r.detail[:90]) for r in audit.failure_records][-2:]}")
        print(f"[{label}] steps tail={_steps(audit)[-5:]}")
        print(f"[{label}] outcome_v2={'absent' if audit.outcome_v2 is None else audit.outcome_v2.get('reason_code')}")
        print(f"[{label}] grading calls={len(chain.grading.calls)}")
        return "run_fatal"
    audit = chain.orchestrator.audits[0]
    print(f"[{label}] delivered remove_sample={[getattr(l, 'remove_sample', None) for l in delivered]}")
    print(f"[{label}] outcome_v2={ {k: audit.outcome_v2.get(k) for k in ('termination_kind', 'reason_code')} if audit.outcome_v2 else None}")
    print(f"[{label}] steps tail={_steps(audit)[-5:]}")
    return "completed"


@pytest.mark.asyncio
async def test_file_to_dir_shape_is_run_fatal_today():
    result = await _run(
        baseline={"config": b"a=1\n", "src/x.py": b"x\n"},
        post={"config/default.json": b"{}\n", "src/x.py": b"x\n"},
        label="file->dir",
    )
    assert result == "run_fatal"  # 修复前事实：候选可控的 run-halt（rh2_contract_validation_failed）


@pytest.mark.asyncio
async def test_dir_to_file_shape_is_run_fatal_today():
    result = await _run(
        baseline={"config/default.json": b"{}\n", "src/x.py": b"x\n"},
        post={"config": b"a=1\n", "src/x.py": b"x\n"},
        label="dir->file",
    )
    assert result == "run_fatal"


@pytest.mark.asyncio
async def test_control_plain_modify_is_completed():
    result = await _run(
        baseline={"config": b"a=1\n", "src/x.py": b"x\n"},
        post={"config": b"a=2\n", "src/x.py": b"x\n"},
        label="control modify",
    )
    assert result == "completed"
