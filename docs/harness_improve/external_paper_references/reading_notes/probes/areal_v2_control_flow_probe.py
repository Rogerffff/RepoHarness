#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""CPU-only characterization of four pinned AReaL method bodies.

Upstream: https://github.com/areal-project/AReaL
Revision: f289b989bc5d1930d5c6d592d335e2ffaf8c2f01
The verbatim method fragments below retain the upstream Apache-2.0 license.
The harness, stubs, assertions, and report generation are this reading's additions.

No AReaL installation, network, model, GPU, NCCL or sandbox is exercised.
A PASS characterizes the observed control flow; it does NOT certify correctness.
With --source-root /path/to/pinned/AReaL, also verify fragment ASTs and queue size
against a real checkout, and require that checkout's HEAD to match the revision.
Without it, fragments are manually transcribed from connector-returned source;
AST/checkout verification is explicitly reported as NOT RUN.
"""
from __future__ import annotations
import argparse
import ast
import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import textwrap
import threading
from types import SimpleNamespace
from typing import Any

PIN = "f289b989bc5d1930d5c6d592d335e2ffaf8c2f01"
FRAGMENTS = {
    "transport": {
        "path": "areal/v2/weight_update/controller/controller.py",
        "class": "WeightUpdateController",
        "method": "update_weights",
        "source": '''
    def update_weights(self, version: int) -> WeightUpdateResult:
        if self._pair_name is None:
            raise RuntimeError("Not connected. Call connect() first.")
        resp = self._http.post(
            f"{self._gateway_url}/update_weights",
            json={"pair_name": self._pair_name, "version": version},
            timeout=self.config.request_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return WeightUpdateResult(
            status=data["status"],
            version=data["version"],
            duration_ms=data["duration_ms"],
            error=data.get("error"),
        )
''',
    },
    "actor": {
        "path": "areal/v2/training_service/controller/controller.py",
        "class": "GatewayTrainController",
        "method": "update_weights",
        "source": '''
    def update_weights(self, meta: Any) -> None:
        if self._weight_update_ctrl is None or self.rollout is None:
            raise RuntimeError(
                "connect_engine() must be called before update_weights()"
            )
        self.rollout.pause_generation()
        assert meta.version is not None and meta.version > 0, (
            f"meta.version must be a positive integer, got {meta.version}"
        )
        result = self._weight_update_ctrl.update_weights(version=meta.version)
        self.rollout.continue_generation()
        logger.info(
            "Weight update v%d completed (%s, %.0fms)",
            meta.version,
            result.status,
            result.duration_ms,
        )
''',
    },
    "publish": {
        "path": "areal/trainer/rl_trainer.py",
        "class": "PPOTrainer",
        "method": "_update_weights_and_publish_version",
        "source": '''
    def _update_weights_and_publish_version(
        self, meta: WeightUpdateMeta, new_version: int
    ) -> None:
        """Update weights, publish their version, then restore AWEX rollout."""
        self.actor.update_weights(meta)

        self.actor.set_version(new_version)
        if self.critic is not None:
            self.critic.set_version(new_version)
        self.rollout.set_version(new_version)
        if self.eval_rollout is not None:
            self.eval_rollout.set_version(new_version)

        if not self._is_v1_awex_colocate(self.config):
            return

        # The AWEX reader flushes all old cache entries while installing the
        # new weights. Reallocate an empty KV pool only after every actor worker
        # has returned, then let SGLang serve requests again. This must remain a
        # controller-side call: invoking rollout RPCs from an actor worker creates
        # a nested controller call while its update_weights collective is active.
        self.rollout.abort_all_requests()
        self.rollout.onload(tags=["cuda_graph"])
        self.rollout.onload(tags=["kv_cache"])
        call_maybe_async(self.rollout.continue_generation)
''',
    },
    "callback": {
        "path": "areal/v2/inference_service/controller/controller.py",
        "class": "RolloutControllerV2",
        "method": "_handle_online_ready_callback",
        "source": '''
    async def _handle_online_ready_callback(
        self, payload: dict[str, Any]
    ) -> dict[str, Any]:
        session_id = payload.get("session_id")
        trajectory_id = payload.get("trajectory_id")
        if not session_id or trajectory_id is None:
            raise RuntimeError("Missing session_id or trajectory_id")

        export_request = {
            "session_id": session_id,
            "trajectory_id": int(trajectory_id),
        }

        waiter = self._pop_online_waiter()
        if waiter is None:
            with self._online_waiters_lock:
                self._completed_online_results.append(export_request)
        elif waiter.future.cancelled() or waiter.future.done():
            with self._online_waiters_lock:
                self._completed_online_results.append(export_request)
        else:
            waiter.future.get_loop().call_soon_threadsafe(
                waiter.future.set_result, export_request
            )
        return {
            "status": "ok",
            "session_id": session_id,
            "trajectory_id": int(trajectory_id),
        }
''',
    },
}

@dataclass
class WeightUpdateResult:
    status: str
    version: int
    duration_ms: float
    error: str | None = None

class FakeHTTPError(RuntimeError):
    pass

class FakeResponse:
    def __init__(self, http_status: int, body: dict[str, Any]):
        self.http_status, self.body = http_status, body
    def raise_for_status(self):
        if self.http_status >= 400:
            raise FakeHTTPError(str(self.http_status))
    def json(self):
        return self.body

FUNCTIONS = {}
for name, fragment in FRAGMENTS.items():
    fragment["source"] = textwrap.dedent(fragment["source"]).strip() + "\n"
    namespace = {
        "Any": Any,
        "WeightUpdateResult": WeightUpdateResult,
        "WeightUpdateMeta": Any,
        "logger": SimpleNamespace(info=lambda *args: None),
        "call_maybe_async": lambda fn: fn(),
    }
    exec("from __future__ import annotations\n" + fragment["source"], namespace)
    FUNCTIONS[name] = namespace[fragment["method"]]

def characterize_update(http_status=200, body_status="ok"):
    events: list[str] = []
    state = {"actor_version": 0, "rollout_version": 0, "paused": False}
    def pause():
        events.append("pause_generation")
        state["paused"] = True
    def resume():
        events.append("continue_generation")
        state["paused"] = False
    def set_version(role, version):
        events.append(f"{role}.set_version({version})")
        state[f"{role}_version"] = version
    def post(url, json, timeout):
        events.append(f"gateway_response({http_status},{body_status})")
        return FakeResponse(http_status, {
            "status": body_status, "version": json["version"],
            "duration_ms": 1.0,
            "error": "injected transfer failure" if body_status == "error" else None,
        })
    transport = SimpleNamespace(
        _pair_name="actor-rollout", _gateway_url="http://mock",
        _http=SimpleNamespace(post=post), config=SimpleNamespace(request_timeout=1),
    )
    transport.update_weights = lambda version: FUNCTIONS["transport"](transport, version)
    rollout = SimpleNamespace(
        pause_generation=pause, continue_generation=resume,
        set_version=lambda v: set_version("rollout", v),
    )
    actor = SimpleNamespace(_weight_update_ctrl=transport, rollout=rollout,
                            set_version=lambda v: set_version("actor", v))
    actor.update_weights = lambda meta: FUNCTIONS["actor"](actor, meta)
    trainer = SimpleNamespace(actor=actor, rollout=rollout, critic=None,
                              eval_rollout=None, config=SimpleNamespace(),
                              _is_v1_awex_colocate=lambda cfg: False)
    error = None
    try:
        FUNCTIONS["publish"](trainer, SimpleNamespace(version=1), 1)
    except FakeHTTPError as exc:
        error = type(exc).__name__
    return {"events": events, "state": state, "exception": error}

async def characterize_callbacks():
    def make_controller():
        return SimpleNamespace(_pop_online_waiter=lambda: None,
            _online_waiters_lock=threading.Lock(),
            _completed_online_results=deque(maxlen=1024))
    controller = make_controller()
    ack = []
    for i in range(1025):
        ack.append(await FUNCTIONS["callback"](controller,
                   {"session_id": "s", "trajectory_id": i}))
    q = controller._completed_online_results
    assert len(q) == 1024 and q[0]["trajectory_id"] == 1
    assert all(x["status"] == "ok" for x in ack)
    duplicated = make_controller()
    payload = {"session_id": "same", "trajectory_id": 7}
    await FUNCTIONS["callback"](duplicated, payload)
    await FUNCTIONS["callback"](duplicated, payload)
    assert list(duplicated._completed_online_results) == [payload, payload]
    invalid_raised = False
    try:
        await FUNCTIONS["callback"](duplicated, {"session_id": "same"})
    except RuntimeError:
        invalid_raised = True
    assert invalid_raised
    return {
        "overflow": {"callbacks": len(ack), "all_ack_ok": True,
                     "retained": len(q), "oldest_retained_id": q[0]["trajectory_id"]},
        "duplicate": {"queued_descriptors": len(duplicated._completed_online_results)},
        "invalid_payload": {"raises": invalid_raised},
    }

def normalized_ast(node):
    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) and isinstance(node.body[0].value.value, str):
        node.body = node.body[1:]
    return ast.dump(node, include_attributes=False)

def verify_checkout(root: Path):
    head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if head != PIN:
        raise ValueError(f"Expected {PIN}, checkout HEAD is {head}")
    for fragment in FRAGMENTS.values():
        tree = ast.parse((root / fragment["path"]).read_text())
        klass = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == fragment["class"])
        actual = next(x for x in klass.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name == fragment["method"])
        expected = ast.parse(fragment["source"]).body[0]
        if normalized_ast(actual) != normalized_ast(expected):
            raise AssertionError(f"Fragment AST differs: {fragment['class']}.{fragment['method']}")
    tree = ast.parse((root / FRAGMENTS["callback"]["path"]).read_text())
    queue_verified = False
    for node in ast.walk(tree):
        targets = [node.target] if isinstance(node, ast.AnnAssign) else (node.targets if isinstance(node, ast.Assign) else [])
        value = getattr(node, "value", None)
        if any(isinstance(t, ast.Attribute) and t.attr == "_completed_online_results" for t in targets) and isinstance(value, ast.Call):
            queue_verified = any(k.arg == "maxlen" and isinstance(k.value, ast.Constant) and k.value.value == 1024 for k in value.keywords)
    if not queue_verified:
        raise AssertionError("Could not confirm _completed_online_results maxlen=1024")
    return {"status": "passed", "head": head, "fragment_asts": 4, "queue_maxlen": 1024}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    source_verification = verify_checkout(args.source_root) if args.source_root else {
        "status": "not_run", "reason": "No local upstream checkout; connector source was manually transcribed."}
    success = characterize_update()
    failure = characterize_update(body_status="error")
    http_failure = characterize_update(500, "error")
    assert success["state"]["rollout_version"] == 1 and success["exception"] is None
    assert failure["state"]["rollout_version"] == 1 and failure["exception"] is None
    assert not failure["state"]["paused"]
    assert http_failure["state"]["rollout_version"] == 0 and http_failure["exception"] == "FakeHTTPError"
    assert http_failure["state"]["paused"]
    assert success["events"].index("continue_generation") < success["events"].index("rollout.set_version(1)")
    callbacks = asyncio.run(characterize_callbacks())
    report = {
        "source_commit": PIN, "runtime": f"Python {platform.python_version()}",
        "scope": "Isolated method bodies with HTTP/worker stubs; not a deployed AReaL test or training reproduction.",
        "source_verification": source_verification,
        "characterization_cases_passed": 7,
        "pass_meaning": "Assertions match current control flow, including undesirable outcomes; NOT a health certification.",
        "cases": {"positive_update": success, "http_200_logical_error": failure,
                  "http_500_control": http_failure,
                  "success_resumes_before_version_publication": True, **callbacks},
        "fragment_sha256": {name: hashlib.sha256(x["source"].encode()).hexdigest() for name,x in FRAGMENTS.items()},
        "not_tested": ["Actual transfer or mixed weights", "HTTP service deployment", "NCCL/GPU", "Concurrent waiter race", "Remote export/storage recovery", "Model learning"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
