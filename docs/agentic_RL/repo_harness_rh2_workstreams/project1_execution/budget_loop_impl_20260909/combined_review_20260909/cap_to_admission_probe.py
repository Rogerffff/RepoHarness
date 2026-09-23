"""批 C 同一竞态的消息→capture→formal 编排→miles buffer 验证。

仅 CPU、本机 aiohttp 与已存在的 prepared/grading/Docker IO 测试替身。
真实调用 capture wire、proxy、vendored app/轨迹、per-rollout adapter、编排、canonicalize 和 buffer。
"""

from __future__ import annotations

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path

import cap_body_race_probe as base

sys.path.insert(1, str(base.fixtures.MILES_ROOT))
sys.path.insert(2, str(base.ROOT / "rh2/tests/adapters_miles"))
sys.path.insert(3, str(base.ROOT / "rh2/tests/adapters"))
from test_w1b_group_admission import (
    BOTH_OK, _buffer, _build_chain, _convert, _dispatch_group, _entry, _miles_args,
)

from repoharness2.adapters.slime.bringup import (
    bringup_leaf_facts, build_production_model_call_proxy, inject_disposition_policy, make_per_rollout_adapter,
)


class HttpDriver:
    name = "claude_code"

    def __init__(self, client, registry, engine, holder, *, race_first):
        self.client, self.registry, self.engine, self.holder = client, registry, engine, holder
        self.race_first = race_first
        self.rows = []

    async def run(self, sandbox, *, workdir, session_id, adapter_url, time_budget_sec, prompt):
        self.engine.reset()
        sid = self.registry.resolve_capability(session_id)
        hook = self.holder["hook"]
        row = {"race": self.race_first and not self.rows}
        self.rows.append(row)
        body = {"model": "probe", "max_tokens": 16, "stream": True,
                "messages": [{"role": "user", "content": "probe"}]}
        encoded = json.dumps(body).encode()
        headers = {"Authorization": f"Bearer {session_id}", "Content-Type": "application/json"}
        gates = [asyncio.Event(), asyncio.Event()]

        async def partial(gate):
            yield encoded[:-1]
            await gate.wait()
            yield encoded[-1:]

        async def request(n):
            if row["race"]:
                return await self.client.post("/v1/messages", data=partial(gates[n]), headers=headers)
            return await self.client.post("/v1/messages", json=body, headers=headers)

        tasks = []
        try:
            tasks.append(asyncio.create_task(request(0)))
            if row["race"]:
                tasks.append(asyncio.create_task(request(1)))
                await base.until(lambda: self.registry._inflight.get(sid, 0) == 2)
                gates[0].set()
                await self.engine.entered.wait()
                gates[1].set()
                refused = await asyncio.wait_for(tasks[1], timeout=1)
                row.update(refusal_status=refused.status, captures_at_refusal=len(hook.records))
                assert refused.status == 403 and len(hook.records) == 0
                tasks[0].cancel()  # 可达客户端行为：收到非重试拒绝后关闭同一运行的在飞连接
                await asyncio.gather(tasks[0], return_exceptions=True)
                await base.until(lambda: self.registry.poison.is_poisoned(sid))
            else:
                await self.engine.entered.wait()
                tasks.append(asyncio.create_task(request(1)))
                await asyncio.sleep(0.03)
                assert not tasks[1].done()
                self.engine.release.set()
                responses = await asyncio.gather(*tasks)
                for response in responses:
                    await response.read()
                row.update(statuses=[r.status for r in responses], captures_at_refusal=len(hook.records))
            return 1
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            row.update(captures=len(hook.records), poison=self.registry.poison.reason(sid),
                       abort_requests=self.engine.aborts)
            self.engine.release.set()


async def group_case(world, root, registry, shared_adapter, client, engine, *, race_first):
    chain = _build_chain(world, root, grading_kinds=BOTH_OK)
    holder = {}
    orch = chain.orchestrator

    def factory(hook, defaults):
        holder["hook"] = hook
        return make_per_rollout_adapter(registry, shared_adapter, hook)

    orch._adapter_factory = factory
    orch._leaf_facts_fn = bringup_leaf_facts
    orch._session_drain_owner = registry.drain_session_plane
    orch._session_poison_check = registry.poison.is_poisoned
    orch._session_poison_subscribe = registry.poison.subscribe
    orch._session_poison_unsubscribe = registry.poison.unsubscribe
    orch._session_poison_reason = registry.poison.reason
    orch._capture_boundary_check = registry.assert_session_clean
    orch._turn_budget_subscribe = registry.subscribe_turn_budget
    orch._turn_budget_unsubscribe = registry.unsubscribe_turn_budget
    orch._turn_budget_snapshot = registry.turn_budget_snapshot
    driver = HttpDriver(client, registry, engine, holder, race_first=race_first)
    orch._harness_driver = driver
    prompt_group, group = await _dispatch_group(world, chain)
    args = _miles_args(world, chain)
    inject_disposition_policy(args)
    buf, recycled = _buffer(world, args)
    await buf.put(_entry(world, prompt_group, group))
    output = {
        "case": "body_race_group" if race_first else "sequential_cap_group",
        "requests": driver.rows, "graded": list(chain.grading_calls),
        "outcomes": [audit.outcome_v2 for audit in orch.audits],
        "remove_sample": [[s.remove_sample for s in member] for member in group],
        "buffered_groups": len(buf._buffer), "recycled_groups": len(recycled),
    }
    if buf._buffer:
        got = await buf.get(current_version=5)
        td = _convert(world, args, got.group)
        output["raw_reward"] = td["raw_reward"]
        output["trained_token_counts"] = [sum(mask) for mask in td["loss_masks"]]
    if race_first:
        assert output["buffered_groups"] == 0 and output["remove_sample"][0] == [True]
    else:
        assert output["buffered_groups"] == 1 and output["raw_reward"] == [1.0, 0.0]
        assert output["trained_token_counts"] == [2, 2]
    return output


async def main():
    world = base.fixtures._World()
    registry = base.cw.CaptureRegistry()
    base.cw.install_capture_wire(registry)
    build_production_model_call_proxy(registry, lambda: "5", require_real=False, artifact_sink=None)
    engine = base.Engine()
    engine.version = "5"
    base.cw.aiohttp = base.EngineAiohttp(engine)
    adapter = base.AnthropicAdapter(tokenizer=base.Tokenizer(), sglang_url="http://fake-engine", max_turns_per_sid=1)
    adapter.app.middlewares.append(base.cw.build_session_guard_middleware(registry))
    client = base.TestClient(base.TestServer(adapter.app, handler_cancellation=True))
    await client.start_server()
    try:
        with tempfile.TemporaryDirectory(prefix="rh2-cap-admission-") as temp:
            for raced in (False, True):
                result = await group_case(world, Path(temp) / str(raced), registry, adapter, client, engine,
                                          race_first=raced)
                print(json.dumps(result, ensure_ascii=False))
    finally:
        await client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.ERROR)
    asyncio.run(main())
