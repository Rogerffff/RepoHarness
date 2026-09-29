"""E1 R3：真实编排 + writer，正常 / 初始化后期限取消；假资源与模型。"""
import asyncio
import json
from pathlib import Path
import sys
import tempfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/pyproject.toml").exists())
sys.path[:0] = [str(ROOT / "rh2/src"), str(ROOT / "rh2/tests"), str(ROOT / "rh2/tests/adapters")]
from repoharness2.adapters.slime.bringup import write_execution_audit_record
from repoharness2.adapters.slime.generate import HARNESS_LAUNCH_FACTS
from test_slime_generate import SAMPLING_PARAMS, _Args, build_dense_chain
from test_startup_fix_2_host_collected import _fa_cfg, _stamp_fa_identity, _ticking_clock, BUDGET


async def run(outcome):
    chain = build_dense_chain(config=_fa_cfg()) if outcome == "deadline" else build_dense_chain()
    if outcome == "deadline":
        _stamp_fa_identity(chain.base_sample)
        chain.orchestrator._clock = _ticking_clock(0.0, 100.0, 100.0, BUDGET - 0.1, 5000.0)
    original = chain.orchestrator._harness_driver
    facts_sent = {"agent_user_init_bootstrap": {"mode": "reused", "recheck": "ok", "seconds": 0.25}}
    if outcome == "normal":
        facts_sent["agent_user_init_launch"] = {"mode": "reused", "recheck": "ok", "seconds": 0.05}

    class Driver:
        async def run(self, *args, **kwargs):
            facts = HARNESS_LAUNCH_FACTS.get()
            facts.update(facts_sent)
            if outcome == "deadline":
                await asyncio.Event().wait()
            return await original.run(*args, **kwargs)

    chain.orchestrator._harness_driver = Driver()
    await chain.orchestrator.generate(_Args(), chain.base_sample, dict(SAMPLING_PARAMS))
    audit = chain.orchestrator.audits[-1]
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        write_execution_audit_record(None, audit, path)
        stored = json.loads(path.read_text().splitlines()[-1])
    expected = {key.removeprefix("agent_user_init_"): value for key, value in facts_sent.items()}
    assert audit.agent_user_init == stored["agent_user_init"] == expected
    return {"agent_user_init": stored["agent_user_init"], "harness_exit_code": audit.harness_exit_code,
            "hit_by": (audit.episode_deadline or {}).get("hit_by"), "transport_equal": True}


async def main():
    result = {"scope": "real RolloutOrchestrator and audit writer; fake driver/resources/model, controlled deadline clock"}
    for outcome in ("normal", "deadline"):
        result[outcome] = await run(outcome)
    Path(__file__).with_suffix(".json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
