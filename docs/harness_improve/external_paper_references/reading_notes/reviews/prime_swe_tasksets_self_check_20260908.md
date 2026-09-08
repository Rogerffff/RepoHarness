# Prime SWE tasksets：作者自查与离线检查记录

日期：2026-09-08。正文：[prime_swe_tasksets_validation.md](../prime_swe_tasksets_validation.md)。

**状态：限定范围精读与作者自查完成，未独立审查。** 本线程没有独立 reviewer／子 agent 工具，不填写虚构的线程 ID、模型 effort 或通过标签。没有运行 GPU、付费 API 或真实 sandbox，没有更改训练代码、数据选择或项目实施方案。

## 1. 实际覆盖

主文章为 Prime Intellect 2026-07-22 的 *Scaling Agentic RL: 365,000+ Environments for SWE, Terminal, and Search*。全部主体（含 terminal/search、Training、What's next）已读；没有将链接到的每篇原论文算作已读。详细覆盖表与永久一手链接在正文 §1 和末尾。

固定代码：

- `prime-envs@c4d04dfe212c153a587ea4ce072ae6753e74d6e9`：SWE family README、三套 taskset 和包 README、Scale score.py、SWE-rebench 可见性测试；parser 只查头部和 pytest 示例，根 LICENSE 已读。
- `verifiers@27bbd216df0af719a43705866b2cf6139bcc95de`：完整 validate CLI／配置、git patch helper；rollout 只检查相关生命周期，不声称整体源码审计。
- `R2E-Gym@0d94c4eb9431cd195c55a7ea3abd54006c9a1735`：运行、parse 分派与 R2E reward 主体，用于区分继承规则与移植改动。
- 三套 HF 数据卡的主体，以及 SWE-rebench/Scale 两份内嵌生成脚本已读。部分附件访问失败；没有取得全量 parquet、所有 sidecar 或三套固定 HF revision。
- 项目基线：`RepoHarness@miles-migration:d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`。只读 B 请求、模板及目标路径，不重审 rh2 实现。

## 2. 关键证据复核

| 项目 | 核对路径 | 结论／修正 |
| --- | --- | --- |
| setup 是否等于 no-op | `validate.py::_run_check/_run_all`，配置 docstring | 否。setup 返回 True 而不调用评分；历史文章和历史数据不能据此被否定 |
| 三套 reward 是否相同 | 三条 solved 与辅助函数、R2E 上游 runtime | R2E 匹配预期状态，另两条检查 expected ID；不能统一成所有日志都通过 |
| 异常是否统一抛出 | rebench parser fallback、Scale `_apply_patch`、R2E host archive | 不统一，部分异常记 0，部分抛错；正文逐类记录 |
| 是否 fresh grading | 三份 solved 与 `Rollout.close()` | 本稿三条仍使用原 runtime；`deep_swe` 的另一条隔离路径不外推 |
| patch 是否完整交付物 | `utils/git.py::capture_patch` 与三个 finalize | 有截断、error和未传ignore等边界；三者并未用它作为实际评分输入 |
| 验证是否统一重复标准 | R2E卡、rebench清洗脚本 | R2E保留重试曾通过的flaky行；rebench第二轮排除规则还按难度分组不同 |
| Scale所有保留行是否有正验证白名单 | H-S `_passes_filter/prepare_data` | 所示脚本采用排除集补集；不能据此否定历史验证，也不能补成完整逐题证据 |
| 数量／语言差异 | README、卡片、viewer | 6,275/6,272和20/17/16的身份分开；未用其中一个覆盖其他来源 |
| 安装／网络的新旧差异 | 固定C树、#798、三包changelog | 老 `_v1` 命令不代表当前目录；prompt不是网络强制隔离 |
| 许可与成本 | 根LICENSE、三卡、全文预算段 | 代码许可不替代数据许可；没有给全流程费用或清洗的模型因果收益 |

## 3. 本地检查及其限制

执行环境：Python 3.13.5、本地 bash；没有 Docker 可执行程序。脚本摘录固定源码中的小函数，必要时重命名避免冲突；Scale main 控制流使用 mock pytest，validate 使用原函数主体配合依赖替身。**这不是安装后的上游模块测试，不是测试集复跑，也不是端到端安全攻击复现。**

26 个断言均通过，且重新核对 JSON 序列化后的 observed == expected。这里的 expected 指预期代码行为，不代表希望生产系统接受该输入。

| 检查 | observed |
| --- | --- |
| `r2e_pass_match` | `1.0` |
| `r2e_expected_failure_matches` | `1.0` |
| `r2e_improved_status_mismatches` | `0.0` |
| `r2e_missing_summary_nonempty_expected` | `0.0` |
| `r2e_empty_expected_empty_parse` | `1.0` |
| `r2e_extra_test_is_rejected` | `0.0` |
| `r2e_file_identity_collision` | `{"test_same":"PASSED"}` |
| `rebench_empty_expected` | `false` |
| `rebench_missing_expected` | `false` |
| `rebench_unlisted_failure_ignored` | `true` |
| `rebench_p2p_only_can_pass` | `true` |
| `rebench_timing_normalization` | `true` |
| `rebench_command_exit7_becomes_exit1` | `1` |
| `rebench_failure_still_has_end_marker` | `true` |
| `scale_pass` | `true` |
| `scale_empty_xml_invalid` | `false` |
| `scale_skipped_expected` | `false` |
| `scale_failed_expected` | `false` |
| `scale_unlisted_failure_ignored` | `true` |
| `scale_duplicate_later_pass_overwrites` | `true` |
| `scale_duplicate_later_failure_overwrites` | `false` |
| `scale_missing_expected` | `false` |
| `scale_stale_xml_after_mock_pytest_exit2` | `1.0` |
| `validate_setup_has_no_scoring` | `["start","setup","stop"]` |
| `validate_setup_marks_valid` | `true` |
| `validate_gold_calls_validate` | `["start","setup","gold_validate","stop"]` |

测试记录器初稿引用了一个随后被修改的可变调用列表；已将记录改为 deep copy，重新运行全部检查并复核持久化结果。没有将这个本轮自查问题当作上游发现。

## 4. 可重跑的完整离线脚本

将下列内容保存成 `semantic_probes.py`，用 Python 3.11+ 和 bash 运行 `python semantic_probes.py`。只使用标准库，写出同目录的 `semantic_probe_results.json`。脚本的代码摘录来自 Apache-2.0 Prime 仓库，完整归属与固定 commit 在脚本头及正文来源表中。它使用合成输入，不会调用网络或云服务；运行者仍应先检查代码。

<details>
<summary>展开脚本（26项断言；非容器实验）</summary>

```python
"""Offline semantic probes; no model, network, Docker, or dataset execution.

Selected function bodies follow Apache-2.0 code from:
  PrimeIntellect-ai/prime-envs@c4d04dfe212c153a587ea4ce072ae6753e74d6e9
  PrimeIntellect-ai/verifiers@27bbd216df0af719a43705866b2cf6139bcc95de
Copyright 2025 Prime Intellect. Source links are in the companion reading note.
This is a standalone extraction with renamed globals / dependency stubs, not
execution of an installed upstream package. Inputs are synthetic.
"""
from __future__ import annotations
import asyncio
import contextlib
import copy
import io
import json
import logging
import re
import subprocess
import tempfile
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path
from uuid import uuid4

RESULTS = []
def check(name, actual, expected, scope):
    assert actual == expected, (name, actual, expected)
    RESULTS.append(dict(name=name, observed=copy.deepcopy(actual), expected=copy.deepcopy(expected), scope=scope))

# r2e_gym/taskset.py: parse_log_pytest, _decolor, calculate_reward
# Body logic is preserved; names are prefixed only to avoid collisions.
def parse_log_pytest(log: str | None) -> dict[str, str]:
    if log is None or "short test summary info" not in log:
        return {}
    out: dict[str, str] = {}
    for line in log.split("short test summary info")[1].strip().split("\n"):
        if "PASSED" in line:
            out[".".join(line.split("::")[1:])] = "PASSED"
        elif "FAILED" in line:
            out[".".join(line.split("::")[1:]).split(" - ")[0]] = "FAILED"
        elif "ERROR" in line:
            parts = line.split("::")
            name = ".".join(parts[1:]) if len(parts) > 1 else line
            out[name.split(" - ")[0]] = "ERROR"
    return out

def _decolor(d: dict) -> dict:
    return {re.sub(r"\x1b\[\d+m", "", k): v for k, v in d.items()}

def r2e_reward(test_output: str, expected_output_json: str) -> float:
    parse = _decolor(parse_log_pytest(test_output))
    expected = _decolor(json.loads(expected_output_json))
    parse = {k.split(" - ")[0]: parse[k] for k in sorted(parse)}
    expected = {k.split(" - ")[0]: expected[k] for k in sorted(expected)}
    if len(parse) != len(expected):
        return 0.0
    for k in parse:
        if k and (k not in expected or parse[k] != expected[k]):
            return 0.0
    return 1.0

S = "================ short test summary info ================\n"
r2e_scope = "Extracted R2E reward, synthetic logs; no dataset-frequency claim"
check("r2e_pass_match", r2e_reward(S + "PASSED a.py::test_a", '{"test_a":"PASSED"}'), 1., r2e_scope)
check("r2e_expected_failure_matches", r2e_reward(S + "FAILED a.py::test_a - msg", '{"test_a":"FAILED"}'), 1., r2e_scope)
check("r2e_improved_status_mismatches", r2e_reward(S + "PASSED a.py::test_a", '{"test_a":"FAILED"}'), 0., r2e_scope)
check("r2e_missing_summary_nonempty_expected", r2e_reward("collection failed", '{"test_a":"PASSED"}'), 0., r2e_scope)
check("r2e_empty_expected_empty_parse", r2e_reward("collection failed", '{}'), 1., r2e_scope)
check("r2e_extra_test_is_rejected", r2e_reward(S + "PASSED a.py::test_a\nPASSED a.py::test_b", '{"test_a":"PASSED"}'), 0., r2e_scope)
check("r2e_file_identity_collision", parse_log_pytest(S + "FAILED a.py::test_same - err\nPASSED b.py::test_same"), {"test_same":"PASSED"}, r2e_scope)

# swerebench_v2/taskset.py: normalization / resolution / shell builder.
TIMING_NORMALIZE_RES = [
    re.compile(r"\s*\[\s*\d+(?:\.\d+)?\s*(?:ms|s)\s*\]\s*$", re.IGNORECASE),
    re.compile(r"\s+in\s+\d+(?:\.\d+)?\s+(?:msec|sec)\b", re.IGNORECASE),
    re.compile(r"\s*\(\s*\d+(?:\.\d+)?\s*(?:ms|s)\s*\)\s*$", re.IGNORECASE),
]
def normalize_test_name(name):
    for pattern in TIMING_NORMALIZE_RES:
        name = pattern.sub("", name)
    return name.strip()
def rebench_resolved(status_map, fail_to_pass, pass_to_pass):
    normalized = {normalize_test_name(k): v for k, v in status_map.items()}
    expected = [normalize_test_name(t) for t in fail_to_pass + pass_to_pass]
    if not expected:
        return False
    return all(normalized.get(t) == "PASSED" for t in expected)
def build_eval_script(test_cmds):
    lines = ["#!/bin/bash", "set -uo pipefail", "", 'echo "SWEREBENCH_V2_TEST_OUTPUT_START"', "FAIL=0"]
    for command in test_cmds:
        lines.append(f"{command} || FAIL=1")
    lines += ['echo "SWEREBENCH_V2_TEST_OUTPUT_END"', "", 'exit "$FAIL"', ""]
    return "\n".join(lines)
rebench_scope = "Extracted expected-ID check; all arbitrary parsers NOT audited"
check("rebench_empty_expected", rebench_resolved({"a":"PASSED"}, [], []), False, rebench_scope)
check("rebench_missing_expected", rebench_resolved({"a":"PASSED"}, ["a"], ["b"]), False, rebench_scope)
check("rebench_unlisted_failure_ignored", rebench_resolved({"a":"PASSED","other":"FAILED"}, ["a"], []), True, rebench_scope)
check("rebench_p2p_only_can_pass", rebench_resolved({"a":"PASSED"}, [], ["a"]), True, rebench_scope)
check("rebench_timing_normalization", rebench_resolved({"a [10 ms]":"PASSED"}, ["a"], []), True, rebench_scope)
p = subprocess.run(["bash"], input=build_eval_script(["(exit 7)"]), text=True, capture_output=True, timeout=5)
check("rebench_command_exit7_becomes_exit1", p.returncode, 1, "Actual local bash, no sandbox")
check("rebench_failure_still_has_end_marker", "SWEREBENCH_V2_TEST_OUTPUT_END" in p.stdout, True, "Actual local bash, no sandbox")

# scaleswe/score.py: all_passed and main behavior.
def scale_normalize(value):
    parts = value.strip().split("::")
    if parts and parts[0].endswith(".py"):
        parts[0] = parts[0][:-3]
    return ".".join(parts).replace("/", ".").strip(".")
def scale_all_passed(xml_content, expected):
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return False
    exact = set(expected)
    norm = {scale_normalize(t): t for t in expected}
    fp = {re.sub(r"\s+", "", scale_normalize(t)): t for t in expected}
    matched = {}
    found = set()
    for tc in root.iter("testcase"):
        if tc.find("skipped") is not None:
            continue
        name, classname = tc.get("name", ""), tc.get("classname", "")
        file_attr = tc.get("file", "")
        status = "failed" if tc.find("failure") is not None or tc.find("error") is not None else "passed"
        for candidate in (
            f"{file_attr}::{name}" if file_attr else "",
            scale_normalize(f"{classname}.{name}"),
            re.sub(r"\s+", "", scale_normalize(f"{classname}.{name}")),
            f"{classname.replace('.', '/')}.py::{name}",
        ):
            original = candidate if candidate in exact else norm.get(candidate) or fp.get(candidate)
            if original:
                matched[original] = status
                found.add(original)
                break
    return bool(found) and all(status == "passed" for status in matched.values()) and not [t for t in expected if t not in found]

def xml(*cases): return "<testsuite>" + "".join(cases) + "</testsuite>"
a = '<testcase classname="tests.test_demo" name="test_a"/>'
af = '<testcase classname="tests.test_demo" name="test_a"><failure/></testcase>'
as_ = '<testcase classname="tests.test_demo" name="test_a"><skipped/></testcase>'
bf = '<testcase classname="tests.test_demo" name="test_b"><failure/></testcase>'
expected = ["tests/test_demo.py::test_a"]
scale_scope = "Extracted JUnit ID matcher; synthetic XML, not exploit prevalence"
check("scale_pass", scale_all_passed(xml(a), expected), True, scale_scope)
check("scale_empty_xml_invalid", scale_all_passed("", expected), False, scale_scope)
check("scale_skipped_expected", scale_all_passed(xml(as_), expected), False, scale_scope)
check("scale_failed_expected", scale_all_passed(xml(af), expected), False, scale_scope)
check("scale_unlisted_failure_ignored", scale_all_passed(xml(a,bf), expected), True, scale_scope)
check("scale_duplicate_later_pass_overwrites", scale_all_passed(xml(af,a), expected), True, scale_scope)
check("scale_duplicate_later_failure_overwrites", scale_all_passed(xml(a,af), expected), False, scale_scope)
check("scale_missing_expected", scale_all_passed(xml(a), expected+["tests/test_demo.py::test_b"]), False, scale_scope)

# Copy of main control flow with dependency substitutes; local temp path replaces XML.
def scale_main(argv, pytest_stub, xml_path):
    ids = json.loads(Path(argv[1]).read_text())
    if not ids:
        return 0.0
    pytest_stub.main(["-vv", f"--junitxml={xml_path}", "-o", "addopts=", "--rootdir=.", *ids])
    try:
        content = Path(xml_path).read_text()
    except OSError:
        return 0.0
    return 1.0 if scale_all_passed(content, ids) else 0.0
with tempfile.TemporaryDirectory() as td:
    td=Path(td); (td/'ids.json').write_text(json.dumps(expected)); (td/'results.xml').write_text(xml(a))
    stub=types.SimpleNamespace(main=lambda args:2)
    check("scale_stale_xml_after_mock_pytest_exit2",scale_main(["score.py",str(td/'ids.json')],stub,str(td/'results.xml')),1.,"Control-flow replay with mocked pytest; no real pytest/environment failure reproduced")

# Validate _run_check core branches, preserving upstream body and stubbing imports.
VALIDATE_SOURCE = '''
async def _run_check(task: Task, config: ValidateConfig, mode: str) -> ResultRow:
    start = time.time()
    runtime = make_runtime(
        resolve_runtime_config(config.runtime, task),
        name=f"validate-{mode}-{task.data.idx}-{uuid4().hex[:8]}",
    )
    setup_timeout = (
        config.timeout.setup
        if config.timeout.setup is not None
        else task.data.timeout.setup
    )
    valid: bool | None = False
    exc = None
    try:
        runtime.env = dict(task.runtime_env())
        trace = Trace(
            task=TraceTask(
                type=type(task).__name__, data=task.data, key=task.key, hash=task.hash
            ),
            state=state_cls(type(task))(),
            agent=vf.AgentInfo(
                config=vf.AgentConfig(runtime=config.runtime),
                name="validate",
                trainable=False,
            ),
        )
        await runtime.start()
        await asyncio.wait_for(
            invoke(task.setup, {"trace": trace, "runtime": runtime}),
            setup_timeout,
        )
        valid = (
            await asyncio.wait_for(task.validate(runtime), config.timeout.total)
            if mode == "gold"
            else True
        )
    except Exception as e:
        exc = e
    finally:
        try:
            await runtime.stop()
        except Exception:
            logger.warning(
                "runtime teardown failed (task %s)", task.data.idx, exc_info=True
            )
    return _row(task, mode, valid, exc, start)
'''
class FakeRuntime:
    def __init__(self): self.calls=[]
    async def start(self): self.calls.append("start")
    async def stop(self): self.calls.append("stop")
class FakeTask:
    data=types.SimpleNamespace(idx=0,timeout=types.SimpleNamespace(setup=None));key='key';hash='hash'
    def runtime_env(self): return {}
    async def setup(self,trace,runtime): runtime.calls.append("setup")
    async def validate(self,runtime): runtime.calls.append("gold_validate");return True
async def invoke(fn, deps): return await fn(**deps)
box=FakeRuntime()
ns=dict(asyncio=asyncio,time=time,uuid4=uuid4,Task=FakeTask,ValidateConfig=object,ResultRow=dict,
        make_runtime=lambda cfg,**kw:box,resolve_runtime_config=lambda cfg,task:cfg,
        Trace=types.SimpleNamespace,TraceTask=types.SimpleNamespace,state_cls=lambda _:lambda:None,
        vf=types.SimpleNamespace(AgentInfo=types.SimpleNamespace,AgentConfig=types.SimpleNamespace),
        invoke=invoke,logger=logging.getLogger("probe"),
        _row=lambda task,mode,valid,exc,start:{"mode":mode,"valid":valid,"error":None if exc is None else str(exc)})
exec(VALIDATE_SOURCE,ns)
cfg=types.SimpleNamespace(runtime=object(),timeout=types.SimpleNamespace(setup=None,total=None))
result=asyncio.run(ns['_run_check'](FakeTask(),cfg,'setup'))
check("validate_setup_has_no_scoring",box.calls,["start","setup","stop"],"Unchanged upstream _run_check body with mocked dependencies")
check("validate_setup_marks_valid",result['valid'],True,"Mocked runtime")
box.calls.clear()
result=asyncio.run(ns['_run_check'](FakeTask(),cfg,'gold'))
check("validate_gold_calls_validate",box.calls,["start","setup","gold_validate","stop"],"Unchanged upstream _run_check body with mocked dependencies")

if __name__=='__main__':
    payload={"date":"2026-09-08","mode":"offline extracted-function and control-flow probes","live_sandbox_runs":0,"dataset_rows_executed":0,"passed":len(RESULTS),"results":RESULTS}
    out=Path(__file__).with_name('semantic_probe_results.json')
    out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(payload,ensure_ascii=False,indent=2))
```

</details>

## 5. 尚需外部独立复核的重点

首先检查当前 validate 与历史数据生成方法是否确实被分开；其次核对三条评分路径的成功／失败定义、异常和测试可见性；最后核实 HF 全量 revision、sidecar 与过滤结果。关于旧 XML、重复测试 ID、缺失预期和 host 归档生命周期，先检查真实数据或最小容器复现，再决定是否值得报告上游问题。

本文未完成项目评分器与 Prime 原生路径的差分重放，未测试目标底座、registry账号权限或镜像冷启动。所有模型收益、全量误判率和上游 bug 定案均不在交付范围。当前结果足以提供实现定位与待验证条件，不足以自动批准数据集。

## 6. 文档交付边界

本任务只新增自己的正文和本检查记录；不编辑共享 README/catalog，不修改一次性交接包，也不提交任何外部 issue／PR。最终远程 commit 和回读结果以交付消息中的实际工具返回为准，不在提交前预填。
