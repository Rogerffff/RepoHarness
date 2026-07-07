"""verifiers 薄壳（swebench_smoke.py）的本机可测部分：任务构造面与 A6 纪律。

本文件**允许** import verifiers（它测的就是绑定层）；库层纯度由
test_no_verifiers_import.py 的子进程检查保证。docker rollout 本机不可跑
（U-D：官方镜像是 x86_64，本机 arm64），整链回归见 s1/envpack_freeze_v1.md
的远程回归记录。
"""

import pytest

from repoharness2.contracts import scan_for_forbidden_markers
from repoharness2.envpack.bundles import (
    PUBLIC_SYSTEM_HINTS,
    load_bundle_pairs,
    render_user_prompt,
)
from repoharness2.taskset.swebench_smoke import (
    SweSmokeConfig,
    SweSmokeTask,
    SweSmokeTaskset,
)


@pytest.fixture(scope="module")
def taskset() -> SweSmokeTaskset:
    return SweSmokeTaskset(SweSmokeConfig(id="swebench_smoke"))


def test_loads_eight_frozen_tasks_in_order(taskset):
    tasks = taskset.load_tasks()
    assert [t.instance_id for t in tasks] == [p.instance_id for p in load_bundle_pairs()]
    assert len(tasks) == 8
    assert all(t.workdir == "/testbed" for t in tasks)
    assert all(t.image.startswith("swebench/sweb.eval.x86_64.") for t in tasks)


def test_prompts_come_verbatim_from_public_bundle(taskset):
    """薄壳不再自渲染 prompt：逐字等于库层 render_user_prompt + 公开提示（S0-7 等价锚点）。"""
    pairs = {p.instance_id: p for p in load_bundle_pairs()}
    for task in taskset.load_tasks():
        public = pairs[task.instance_id].public
        assert task.prompt == render_user_prompt(public)
        assert task.system_prompt == PUBLIC_SYSTEM_HINTS
        assert task.image_manifest_digest == public.image_manifest_digest
        assert task.base_commit == public.base_commit


def test_task_object_carries_no_private_material(taskset):
    """A6 收紧的回归：Task 会随 trace dump 序列化，字段名与全部内容都必须过 marker 扫描。

    （S0-7 版的 fail_to_pass/pass_to_pass/test_cmd 字段已删除——它们属于
    PrivateGradingBundle，评分时按 instance_id 取。）
    """
    private_leftovers = {"fail_to_pass", "pass_to_pass", "test_cmd", "test_patch", "golden_patch"}
    assert not private_leftovers & set(SweSmokeTask.model_fields)
    for task in taskset.load_tasks():
        assert scan_for_forbidden_markers(task.model_dump(mode="json")) == []


def test_subset_single_instance_matches_runner_usage(taskset):
    """runner（s0_swe_smoke.py）的单题一进程形态：subset 恰好命中 1 题 + _rows 兼容入口。"""
    config = SweSmokeConfig(id="swebench_smoke", subset=["psf__requests-2931"])
    shell = SweSmokeTaskset(config)
    tasks = shell.load_tasks()
    assert len(tasks) == 1 and tasks[0].instance_id == "psf__requests-2931"
    row = shell._rows()["psf__requests-2931"]
    assert row["image_manifest_digest"] == tasks[0].image_manifest_digest


def test_needs_container_still_pinned(taskset):
    assert SweSmokeTaskset.NEEDS_CONTAINER is True


def test_grading_material_reachable_only_via_private_bundle(taskset):
    """评分材料的唯一通路是 _pairs() 的 private 半区（@reward 用的正是它）。"""
    pair = taskset._pairs()["django__django-11099"]
    assert pair.private.eval_script.startswith("#!/bin/bash")
    assert pair.private.fail_to_pass
