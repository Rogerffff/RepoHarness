"""轻量隔离核查：新断言能接受抛出/报告，拒绝既有 C3 吞错路线。

只执行各候选实际 web.py 中的 run_app/_cancel_tasks；用 async generator
替代网络与 AppRunner。它不是 aiohttp 集成测试，也不是正式评分。
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import logging
import subprocess
import tempfile
from pathlib import Path
from types import SimpleNamespace

from prepare_materials import HERE, ROOT, dump, sha

IID = "aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52"
PUBLIC = ROOT / "runs/r2e_static_prep_20260924/v3/public" / IID / "worktree"
PRIVATE = ROOT / "runs/r2e_static_prep_20260924/v3/private" / IID
CANDIDATES = {
    "base": None,
    "gold": PRIVATE / "gold.patch",
    "C1": ROOT / "runs/r2e_actor_20260925/grader_cands/aiohttp_1c1c_C1_skip_done_main_task.patch",
    "C3": ROOT / "runs/r2e_actor_20260925/grader_cands/aiohttp_1c1c_C3_gather_swallow.patch",
}


def compile_functions(text: str, names: set[str], namespace: dict) -> None:
    tree = ast.parse(text)
    nodes = [x for x in tree.body if isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef)) and x.name in names]
    assert {x.name for x in nodes} == names
    future = ast.parse("from __future__ import annotations").body[0]
    # 此私有诊断刻意执行指定的候选函数；不执行模块其它顶层代码。
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[])),  # noqa: S102
                 "<isolated-aiohttp-control-flow>", "exec"), namespace)


def main() -> None:
    original = (PUBLIC / "aiohttp/web.py").read_text()
    results = []
    for name, patch in CANDIDATES.items():
        with tempfile.TemporaryDirectory(prefix="rh2-aiohttp-cleanup-") as temp:
            directory = Path(temp)
            target = directory / "aiohttp/web.py"
            target.parent.mkdir()
            target.write_text(original)
            if patch is not None:
                subprocess.run(["git", "apply", str(patch)], cwd=directory,
                               check=True, capture_output=True, timeout=10)

            class Application:
                def __init__(self):
                    self.cleanup_ctx = []

            async def run_context(app, **kwargs):
                generators = [fn(app) for fn in app.cleanup_ctx]
                for generator in generators:
                    await anext(generator)
                try:
                    kwargs["print"]("isolated startup")
                    await asyncio.sleep(3600)
                finally:
                    for generator in reversed(generators):
                        with contextlib.suppress(StopAsyncIteration):
                            await anext(generator)

            namespace = {
                "asyncio": asyncio, "logging": logging, "suppress": contextlib.suppress,
                "AccessLogger": SimpleNamespace(LOG_FORMAT=""),
                "access_logger": logging.getLogger("aiohttp.access"),
                "GracefulExit": type("GracefulExit", (SystemExit,), {}),
                "_run_app": run_context,
            }
            compile_functions(target.read_text(), {"run_app", "_cancel_tasks"}, namespace)
            namespace["web"] = SimpleNamespace(Application=Application, run_app=namespace["run_app"])
            compile_functions((PUBLIC / "tests/test_run_app.py").read_text(), {"stopper"}, namespace)
            compile_functions((HERE / "materials/1c1c0ea3/test_1.py").read_text(),
                              {"test_run_app_cleanup_error_is_observable_after_interrupt"}, namespace)
            loop = asyncio.new_event_loop()
            try:
                namespace["test_run_app_cleanup_error_is_observable_after_interrupt"](loop)
                outcome = "assertion_passed"
            except AssertionError as exc:
                outcome = "assertion_failed"
                assert str(exc) == "cleanup exception was silently lost"
            finally:
                if not loop.is_closed():
                    loop.run_until_complete(loop.shutdown_asyncgens())
                    loop.close()
                asyncio.set_event_loop(None)
            assert (outcome == "assertion_failed") == (name == "C3"), (name, outcome)
            results.append({"candidate": name, "new_assertion_only": outcome,
                            "patch_sha256": None if patch is None else sha(patch.read_bytes())})

    dump(HERE / "cleanup_control_flow_check.json", {
        "as_of": "2026-10-03", "kind": "isolated_stdlib_control_flow_not_grading",
        "source_web_sha256": sha(original), "results": results,
        "limitations": ["本地Python3.12，不是正式Linux镜像Python3.9",
                        "以async generator替代真实Application/AppRunner/网络",
                        "仅核新增断言，base通过此断言不等于题目得1",
                        "仍需正式58键收集、六方评分和非作者核查"],
    })
    print("cleanup assertion: base/gold/C1 accepted; C3 rejected (isolated check only)")


if __name__ == "__main__":
    main()
