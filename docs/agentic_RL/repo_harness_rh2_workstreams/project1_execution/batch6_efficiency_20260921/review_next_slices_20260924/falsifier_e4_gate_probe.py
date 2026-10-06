"""有界设计探针：真实 manager 清理方法 + 显式标明的拟议裁剪；本机 Bash 闸门。

从仓库根运行：
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=rh2/src rh2/.venv/bin/python <本文件>
不调用 Docker，不修改生产源码；JSON 写在本文件旁。
"""

from __future__ import annotations

import asyncio
import json
import shlex
import subprocess
from pathlib import Path

from repoharness2.grading.manager import ExecResult, SWEGradingManager, _ContainerRecord

HERE = Path(__file__).resolve().parent
CAP = 256


class ProposedTrimManager(SWEGradingManager):
    """只为解释 Brief 的两种 list 裁剪方式；不是当前生产实现。"""

    def __init__(self, *, replace_list: bool = False, completion_order: bool = False):
        self.rm_calls: list[str] = []
        self.replace_list = replace_list
        self.completion_order = completion_order
        super().__init__(docker=self.fake_docker)

    async def fake_docker(self, *args: str, **_kwargs: object) -> ExecResult:
        assert args[:2] == ("rm", "-f"), args
        self.rm_calls.append(args[2])
        return ExecResult(0, "", "")

    async def _remove_container(self, record: _ContainerRecord, *, timeout: float | None = None) -> None:
        was_removed = record.removed
        await super()._remove_container(record, timeout=timeout)
        if was_removed or not record.removed:
            return
        if self.completion_order:
            self._records.remove(record)
            self._records.append(record)
        excess = max(0, sum(r.removed for r in self._records) - CAP)
        kept: list[_ContainerRecord] = []
        for row in self._records:
            if row.removed and excess:
                excess -= 1
            else:
                kept.append(row)
        if self.replace_list:
            self._records = kept
        else:
            self._records[:] = kept


def record(name: str, *, removed: bool = False) -> _ContainerRecord:
    return _ContainerRecord(name, name, 0.0, 0.0, removed=removed)


async def old_started_finishes_last(*, completion_order: bool) -> dict:
    manager = ProposedTrimManager(completion_order=completion_order)
    long = record("old_started_long_grade")
    manager._records = [long, *(record(f"later_short_{i}", removed=True) for i in range(CAP))]
    await manager._remove_container(long)
    return {
        "is_proposed_policy_model": True,
        "completion_order": completion_order,
        "retained": len(manager.container_records),
        "just_completed_present": long in manager.container_records,
        "rm_calls": manager.rm_calls,
    }


async def close_with_trim(*, replace_list: bool) -> dict:
    manager = ProposedTrimManager(replace_list=replace_list)
    manager._records = [
        *(record(f"old_completed_{i}", removed=True) for i in range(CAP)),
        *(record(f"active_{i}") for i in range(3)),
    ]
    result = await manager.close()  # 当前生产 close() -> gc() -> _remove_container。
    return {
        "is_proposed_policy_model": True,
        "replace_list": replace_list,
        "rm_calls": manager.rm_calls,
        "containers_open": result["containers_open"],
        "manager_closed": manager.closed,
        "retained": len(manager.container_records),
    }


def gate_probe() -> dict:
    missing = HERE / "falsifier_gate_must_not_exist"
    assert not missing.exists()
    # Brief §4.2 的两个 [ 调用保持原样；600 降为 1，避免等待两分钟。
    # 末行只打印示意，不运行测试、不访问网络。没有写 root 文件。
    gate = f"""
n=0; while [ ! -e {shlex.quote(str(missing))} ]; do
  n=$((n+1)); [ "$n" -ge 1 ] && {{ echo RH2_GATE_TIMEOUT=1; exit 97; }}; sleep 0.2; done
echo OFFICIAL_TEST_ENTERED=1
"""
    result = {}
    for name, prefix in {
        "control": "",
        "sourced_shell_function": "function [ { return 1; }\n",
    }.items():
        proc = subprocess.run(["/bin/bash", "-c", prefix + gate], capture_output=True, text=True, timeout=3, check=False)
        result[name] = {"rc": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}
    result["gate_file_exists"] = missing.exists()
    result["scope"] = (
        "local Bash only; same-shell function can bypass proposed check. "
        "Network policy is not implemented; no Docker or current network-enabled grader claim."
    )
    assert result["control"]["rc"] == 97
    assert result["sourced_shell_function"]["rc"] == 0
    assert "OFFICIAL_TEST_ENTERED=1" in result["sourced_shell_function"]["stdout"]
    return result


async def main() -> None:
    result = {
        "scope": "conditional_future design examples; no current B diagnostic-loss claim",
        "record_order": [await old_started_finishes_last(completion_order=flag) for flag in (False, True)],
        "gc_iteration": [await close_with_trim(replace_list=flag) for flag in (False, True)],
        "network_gate": gate_probe(),
    }
    assert result["record_order"][0]["just_completed_present"] is False
    assert result["record_order"][1]["just_completed_present"] is True
    assert result["gc_iteration"][0]["containers_open"] == ["active_1"]
    assert result["gc_iteration"][1]["containers_open"] == []
    output = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    HERE.joinpath("falsifier_e4_gate_probe.json").write_text(output)
    print(output, end="")


if __name__ == "__main__":
    asyncio.run(main())
