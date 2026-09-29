"""只读 CPU 探针：官方空日志语义、归因歧义与 manager 超时分类。"""
import asyncio
import json
from importlib.metadata import version
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from swebench.harness.constants import (
    END_TEST_OUTPUT, START_TEST_OUTPUT, FAIL_TO_PASS, PASS_TO_PASS,
    MAP_REPO_VERSION_TO_SPECS, EvalType,
)
from swebench.harness.grading import (
    get_logs_eval, get_eval_tests_report, get_resolution_status,
    compute_fail_to_pass, compute_pass_to_pass,
)
from repoharness2.envpack.scoring import EvalVerdict
from repoharness2.grading.manager import SWEGradingManager, GradingInfraError


def emit(kind, **facts):
    print(json.dumps(dict(kind=kind, **facts), ensure_ascii=False, sort_keys=True))


def parser_probe():
    repo = "django/django"
    spec = SimpleNamespace(repo=repo, version=next(iter(MAP_REPO_VERSION_TO_SPECS[repo])))
    gold = {FAIL_TO_PASS: ["test_fixed (app.tests.Case)"], PASS_TO_PASS: ["test_stable (app.tests.Case)"]}
    logs = {
        "候选源码导入报错（合成日志）": 'Traceback (most recent call last):\n  File "/testbed/module.py", line 1\nSyntaxError: invalid syntax\n',
        "环境命令缺失（合成日志）": 'bash: python: command not found\n',
    }
    with TemporaryDirectory(prefix="rh2-grading-crosscheck-") as tmp:
        for i, (cause, body) in enumerate(logs.items()):
            path = Path(tmp) / f"{i}.log"
            path.write_text(f"{START_TEST_OUTPUT}\n{body}{END_TEST_OUTPUT}\n")
            status_map, apply_ok = get_logs_eval(spec, str(path))
            report = get_eval_tests_report(status_map, gold)
            resolution = get_resolution_status(report)
            verdict = EvalVerdict(
                instance_id="synthetic-parser-probe", apply_ok=apply_ok,
                resolution=resolution, resolved=resolution == "RESOLVED_FULL",
                f2p_rate=compute_fail_to_pass(report), p2p_rate=compute_pass_to_pass(report),
                f2p_success=report[FAIL_TO_PASS]["success"], f2p_failure=report[FAIL_TO_PASS]["failure"],
                p2p_success=report[PASS_TO_PASS]["success"], p2p_failure=report[PASS_TO_PASS]["failure"],
                num_parsed_tests=len(status_map),
            )
            manager_spec = SimpleNamespace(parse_log=lambda _: verdict)
            try:
                SWEGradingManager._parse_eval_log(None, manager_spec, path.read_text())
            except GradingInfraError as exc:
                manager_result = {"category": exc.category, "detail": exc.detail}
            else:
                manager_result = {"reward": verdict.reward}
            emit("parser", cause=cause, swebench_version=version("swebench"), repo=repo,
                 status_map=status_map, apply_ok=apply_ok, default_resolution=resolution,
                 default_reward=verdict.reward, manager_result=manager_result)
    fail_only = get_eval_tests_report({}, gold, eval_type=EvalType.FAIL_ONLY)
    emit("official_mode_caveat", fail_only_empty_resolution=get_resolution_status(fail_only),
         rh2_current_call_uses="PASS_AND_FAIL default")


async def timeout_probe():
    async def timeout_exec(*args, **kwargs):
        raise TimeoutError("模拟超时，不运行 Docker")
    manager = SimpleNamespace(_exec_bash=timeout_exec)
    for phase in ("test", "setup"):
        try:
            await SWEGradingManager._exec_bash_checked(manager, None, "", phase=phase, timeout=1800)
        except GradingInfraError as exc:
            emit("timeout", phase=phase, category=exc.category, detail=exc.detail,
                 evidence="合成异常，只验证真实分类函数，无 GPU/Docker/生产频率主张")


parser_probe()
asyncio.run(timeout_probe())
