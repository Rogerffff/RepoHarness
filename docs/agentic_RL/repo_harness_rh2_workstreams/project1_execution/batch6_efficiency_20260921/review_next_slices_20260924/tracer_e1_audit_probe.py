"""E1 只读 CPU 运输探针：生产编排/audit writer，沿用本地假 Docker/driver。

不启动容器，不修改维护测试。输出只在本脚本同目录的 tracer_* 文件。
"""
import asyncio
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "rh2/src/repoharness2").is_dir())
sys.path[:0] = [str(ROOT / "rh2/src"), str(ROOT / "rh2/tests"), str(ROOT / "rh2/tests/adapters")]

from repoharness2.adapters.slime.bringup import write_execution_audit_record
from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS
from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain


async def main():
    audit_path = HERE / "tracer_e1_execution_audit.jsonl"
    if audit_path.exists():
        raise FileExistsError(audit_path)
    emitted = {}
    chain = build_dense_chain(audit_sink=lambda audit: write_execution_audit_record(None, audit, audit_path))
    original = chain.orchestrator._harness_driver

    class EmitE1Driver:
        async def run(self, *args, **kwargs):
            facts = HARNESS_LAUNCH_FACTS.get()
            assert facts is not None
            facts.update({
                "agent_user_init_bootstrap": {"mode": "reused", "recheck": "ok", "seconds": 0.1234},
                "agent_user_init_launch": {"mode": "reused", "recheck": "ok", "seconds": 0.0123},
                "harness_log": {"exec_state": "exited", "exit_code": 0, "log_complete": True},
            })
            emitted.update(facts)
            return await original.run(*args, **kwargs)

    chain.orchestrator._harness_driver = EmitE1Driver()
    delivered = await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    persisted = json.loads(audit_path.read_text().splitlines()[-1])
    audit = chain.orchestrator.audits[-1]
    result = {
        "scope": "real RolloutOrchestrator and write_execution_audit_record; fake Docker/driver/model/grading",
        "emitted": emitted,
        "audit_has_e1_fields": {k: hasattr(audit, k) for k in emitted if k.startswith("agent_user_init_")},
        "persisted_has_e1_fields": {k: k in persisted for k in emitted if k.startswith("agent_user_init_")},
        "persisted_harness_log_control": persisted.get("harness_log"),
        "delivered_count": len(delivered) if isinstance(delivered, list) else 1,
        "audit_path": str(audit_path.relative_to(ROOT)),
    }
    target = HERE / "tracer_e1_audit_probe.json"
    with target.open("x") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
