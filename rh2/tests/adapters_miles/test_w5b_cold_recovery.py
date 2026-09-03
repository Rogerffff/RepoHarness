"""W5b（决策包 D2+B v2 B-3；06 计划 §1.5，owner 2026-09-04 细化"不建设联合 checkpoint、事务恢复或复合
版本体系"）：最小冷恢复合同的三个正确性点。

被测对象是 miles 集成分支的真实对象（RH2_MILES_PATH=reference/miles-rh2-integration）：
  - `miles.utils.rh2_recovery`：状态文件读写、恢复语境判定、updater 计数器恢复值、首次 publish 核对、
    `run_restarted` 事件；
  - 真实 `RolloutDataSource.save/load`（绕过 __init__ 的 tokenizer/Dataset 加载——那是 hf_checkpoint
    依赖，不是被测语义——只装配 save/load 用到的状态字段）；
  - 真实 `RolloutManager.save / load / set_weight_version / _verify_engine_weight_versions` 方法体：
    RolloutManager 本体是 Ray actor（sglang/ray import 链在 rh2 venv 不可导），这里用 ast 从生产源码抽出
    这四个方法编译后绑定到最小替身上执行（与 test_zero_signal_semantics 抽 `_any_weights_dirty` 同一手法：
    测的是生产源码，不是复刻）；engine 用 W10 同款 fake actor handle；
  - 真实 `DefaultDataBuffer`（重启后为空）与真实 `verify_engine_weight_versions`（W10 逐 engine 收敛核对）；
  - weight updater：六个真实 updater 都要 torch.distributed 进程组，用"构造 0、publish 前 +1、把
    str(version) 发给每台 engine"的最小替身；这两条事实由 `test_updater_and_wiring_source_facts` 钉死在
    六个真实构造函数与增量点上——它们正是"恢复值 = p-1"的依据。

完整冷恢复场景按生产时序驱动：
    原 run：bootstrap + 真实更新 publish 到 p → train_async 在 rollout_id=r 处 save_model(r) →
            RolloutManager.save(r)（游标 + 已发布版本 p 同目录同时机落盘）→ 继续 publish 到 p+2 → 崩溃
    重启（新 run_id）：trainer init 构造 updater → 计数器恢复为 p-1 → placement_group:
            RolloutManager.load(start_rollout_id-1 = r)（游标恢复 + 版本文件 + run_restarted）→
            train_async bootstrap publish → 标 p，set_weight_version(p) 通过恢复核对、W10 单调断言与
            逐 engine 收敛核对 → 首次真实更新 p+1。
"""

from __future__ import annotations

import ast
import json
import logging
import sys
import types
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

pytestmark = pytest.mark.integration_base

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from w4_helpers import read_events  # noqa: E402


# ---------------------------------------------------------------------------
# 装配
# ---------------------------------------------------------------------------


@pytest.fixture()
def events_dir(tmp_path, monkeypatch):
    from miles.utils import rh2_event_log

    d = tmp_path / "events"
    monkeypatch.setenv(rh2_event_log.EVENT_DIR_ENV, str(d))
    monkeypatch.setenv(rh2_event_log.RUN_ID_ENV, "w5b-run-1")
    return d


def _real_data_source(world, **args_over):
    """真实 RolloutDataSource，只装配 save/load 用到的状态字段（rollout_shuffle=False → load 不触碰 dataset）。"""

    world.install_sglang_stub()
    from miles.rollout.data_source import RolloutDataSource

    args = Namespace(rollout_global_dataset=True, rollout_shuffle=False, save=None, load=None, start_rollout_id=None)
    for key, value in args_over.items():
        setattr(args, key, value)
    ds = RolloutDataSource.__new__(RolloutDataSource)
    ds.args = args
    ds.epoch_id = ds.sample_group_index = ds.sample_index = ds.sample_offset = 0
    ds.metadata = {}
    ds.dataset = None
    return ds


def _cursor(ds) -> dict:
    return {k: getattr(ds, k) for k in ("sample_offset", "epoch_id", "sample_group_index", "sample_index")}


class _FakeActorHandle:
    """SGLangEngine actor handle 的最小替身（W10 同款）：`get_weight_version.remote()` 返回 awaitable。
    `version` 可变：updater 替身"发布"时改写它（= engine.update_weight_version）。"""

    def __init__(self, version="default") -> None:
        self.version = version
        self.calls = 0
        self.get_weight_version = SimpleNamespace(remote=self._remote)

    async def _remote(self):
        self.calls += 1
        return self.version


class _UpdaterStandIn:
    """六个真实 updater 的最小替身：构造 weight_version=0；update_weights 先 +1，再把 str(version) 发给
    self.rollout_engines 的每一台（mixin.py `_finalize_and_resume_engines` /
    update_weight_from_tensor.py 的 engine.update_weight_version）。"""

    def __init__(self, engines) -> None:
        self.weight_version = 0
        self.rollout_engines = list(engines)
        self.sent: list[str] = []

    def update_weights(self) -> None:
        self.weight_version += 1
        for engine in self.rollout_engines:
            engine.version = str(self.weight_version)
        self.sent.append(str(self.weight_version))


def _bind_real_rollout_manager_methods(world, target, names: tuple[str, ...], namespace: dict) -> None:
    """从生产 rollout_manager.py 用 ast 抽出 RolloutManager 的指定方法，在给定命名空间编译并绑定到 target。"""

    path = world.miles_root / "miles" / "ray" / "rollout" / "rollout_manager.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "RolloutManager")
    for name in names:
        fn = next(
            n for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name
        )
        assert not fn.decorator_list, f"{name} 带装饰器，ast 抽取假设不成立"
        ns = dict(namespace)
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), "exec"), ns)  # noqa: S102 - 生产源码的单个方法
        setattr(target, name, types.MethodType(ns[name], target))


def _rollout_manager_stand_in(world, *, data_source, engines):
    """RolloutManager 的最小替身：__init__ 的两个版本字段 + `_get_updatable_server` 返回带 fake engine 的
    server；save / load / set_weight_version / _verify_engine_weight_versions 是**真实方法体**。"""

    from miles.utils import rh2_recovery
    from miles.utils.rh2_engine_versions import verify_engine_weight_versions

    rm = SimpleNamespace()
    rm.args = data_source.args
    rm.args.indep_dp = False
    rm.data_source = data_source
    rm.weight_version = None  # RolloutManager.__init__
    rm._rh2_restored_published_weight_version = None  # RolloutManager.__init__（W5b）
    srv = SimpleNamespace(engines=[SimpleNamespace(actor_handle=h, is_allocated=True) for h in engines])
    rm._get_updatable_server = lambda: srv
    namespace = dict(
        rh2_recovery=rh2_recovery,
        verify_engine_weight_versions=verify_engine_weight_versions,
        logger=logging.getLogger("test_w5b.rollout_manager"),
        event_logger_checkpoint=SimpleNamespace(snapshot=lambda *a, **k: None),
    )
    _bind_real_rollout_manager_methods(
        world, rm, ("save", "load", "set_weight_version", "_verify_engine_weight_versions"), namespace
    )
    return rm


def _fresh_buffer(world):
    from miles.rollout.fully_async_data_buffer import DataBufferConstructorInput, DefaultDataBuffer

    return DefaultDataBuffer(DataBufferConstructorInput(args=world.mk_miles_args(), unused_handler_fn=lambda g: None))


# ===========================================================================
# 1. 完整冷恢复：版本从 p 继续、bootstrap 标 p、首次真实更新 p+1、buffer 空、游标恢复、run_restarted 字段齐全
# ===========================================================================


async def test_full_cold_recovery_continues_version_from_saved_point(world, tmp_path, events_dir, monkeypatch):
    from miles.utils import rh2_event_log, rh2_recovery
    from miles.utils.rh2_engine_versions import ENGINE_VERSIONS_EVENT

    ckpt = tmp_path / "ckpt"
    P, R = 7, 3  # 原 run：在 rollout_id=R 保存 checkpoint 时已发布版本 p=P

    # ---- 原 run（run_id = w5b-run-1）----------------------------------------------------------
    engines1 = [_FakeActorHandle(), _FakeActorHandle()]
    ds1 = _real_data_source(world, save=str(ckpt), load=str(ckpt), start_rollout_id=0)
    rm1 = _rollout_manager_stand_in(world, data_source=ds1, engines=engines1)
    updater1 = _UpdaterStandIn(engines1)
    for _ in range(P):  # bootstrap(1) + 6 次真实更新 → p=7
        updater1.update_weights()
        await rm1.set_weight_version(updater1.weight_version)
    assert rm1.weight_version == P
    ds1.sample_offset, ds1.epoch_id, ds1.sample_group_index, ds1.sample_index = 6, 1, 3, 12
    saved_cursor = _cursor(ds1)

    # train_async 顺序：save_model(R) → rollout_manager.save(R) → update_weights（见源码事实测试）
    rm1.save(R)
    rollout_dir = ckpt / "rollout"
    assert sorted(p.name for p in rollout_dir.iterdir()) == [
        f"global_dataset_state_dict_{R}.pt",
        f"rh2_published_weight_version_{R}.json",
    ]  # 两个文件、同目录、同 rollout_id；没有 .tmp 残留，也没有任何 buffer 内容落盘
    record = json.loads((rollout_dir / f"rh2_published_weight_version_{R}.json").read_text(encoding="utf-8"))
    assert record["schema_id"] == rh2_recovery.PUBLISHED_VERSION_STATE_SCHEMA_ID
    assert record["rollout_id"] == R and record["published_weight_version"] == P and record["run_id"] == "w5b-run-1"

    for _ in range(2):  # 原 run 继续到 p+2 后崩溃：这两代与 buffer/在飞组一起丢弃
        updater1.update_weights()
        await rm1.set_weight_version(updater1.weight_version)
    assert updater1.weight_version == P + 2
    assert read_events(events_dir, (rh2_event_log.RUN_RESTARTED_EVENT,)) == []  # 原 run 不是重启

    # ---- 重启（新 run_id = w5b-run-2）---------------------------------------------------------
    monkeypatch.setenv(rh2_event_log.RUN_ID_ENV, "w5b-run-2")
    loaded_rollout_id = R  # Megatron load_checkpoint 返回的 iteration（miles: iteration == rollout_id）
    # trainer 每个 rank：arguments.py 因 --load 下有 tracker 而保留 start_rollout_id=None；构造 updater 后恢复计数器
    trainer_args = Namespace(load=str(ckpt), start_rollout_id=None)
    engines2 = [_FakeActorHandle(), _FakeActorHandle()]  # 新起的 engine：还没收到任何 publish
    updater2 = _UpdaterStandIn(engines2)
    assert updater2.weight_version == 0
    updater2.weight_version = rh2_recovery.restore_updater_weight_version(trainer_args, loaded_rollout_id)
    assert updater2.weight_version == P - 1

    # placement_group：start_rollout_id = loaded + 1；RolloutManager.load(start_rollout_id - 1)
    start_rollout_id = loaded_rollout_id + 1
    ds2 = _real_data_source(world, save=str(ckpt), load=str(ckpt), start_rollout_id=None)
    rm2 = _rollout_manager_stand_in(world, data_source=ds2, engines=engines2)
    assert _cursor(ds2) == {"sample_offset": 0, "epoch_id": 0, "sample_group_index": 0, "sample_index": 0}
    rm2.load(start_rollout_id - 1)
    assert _cursor(ds2) == saved_cursor  # data_source cursor 恢复
    assert rm2._rh2_restored_published_weight_version == P
    assert rm2.weight_version is None  # 本 run 尚未 publish

    # buffer：新进程新建，空（没有任何持久化面可以把 pre-crash 组带回来）
    buf = _fresh_buffer(world)
    assert buf.get_metrics()["rollout/fully_async/queue_size"] == 0 and buf._buffer == []

    # train_async bootstrap publish：标 p；RolloutManager 首次 set_weight_version = p，通过恢复核对 + W10 收敛核对
    updater2.update_weights()
    assert updater2.weight_version == P and updater2.sent == [str(P)]
    assert [e.version for e in engines2] == [str(P), str(P)]
    await rm2.set_weight_version(updater2.weight_version)
    assert rm2.weight_version == P
    assert [e.calls for e in engines2] == [1, 1]  # W10：逐 engine 核对，不经 router

    # 首次真实更新：p+1（单调核对不红，收敛核对通过）
    updater2.update_weights()
    await rm2.set_weight_version(updater2.weight_version)
    assert rm2.weight_version == P + 1 and [e.version for e in engines2] == [str(P + 1)] * 2

    # run_restarted：恰一条、字段齐全、新 run_id 与旧 run_id
    rows = read_events(events_dir, (rh2_event_log.RUN_RESTARTED_EVENT,))
    assert len(rows) == 1
    ev = rows[0]
    assert ev["run_id"] == "w5b-run-2" and ev["previous_run_id"] == "w5b-run-1"
    assert ev["rollout_id"] == R and ev["start_rollout_id"] == R + 1 and ev["load_dir"] == str(ckpt)
    assert ev["published_weight_version"] == P and ev["bootstrap_weight_version"] == P
    assert ev["published_version_state_path"] == str(rollout_dir / f"rh2_published_weight_version_{R}.json")
    assert ev["data_source_state_path"] == str(rollout_dir / f"global_dataset_state_dict_{R}.pt")
    assert ev["data_source_state_present"] is True and ev["data_source_state"] == saved_cursor
    assert {"ts_unix", "host", "pid"} <= set(ev)

    # 新 run 的 W10 事件：bootstrap 标 p、首次真实更新 p+1，都收敛
    conv = [e for e in read_events(events_dir, (ENGINE_VERSIONS_EVENT,)) if e["run_id"] == "w5b-run-2"]
    assert [(e["expected"], e["converged"]) for e in conv] == [(str(P), True), (str(P + 1), True)]


async def test_recovery_with_no_publish_before_checkpoint_keeps_stock_start(world, tmp_path, events_dir):
    """恢复点之前从未 publish（RolloutManager.weight_version 仍 None，如 debug_train_only）：文件记 null，
    updater 保持 0，首次 publish 不做恢复核对（None → 任何版本都可）。"""

    from miles.utils import rh2_recovery

    ckpt = tmp_path / "ckpt"
    ds1 = _real_data_source(world, save=str(ckpt), load=str(ckpt))
    rm1 = _rollout_manager_stand_in(world, data_source=ds1, engines=[_FakeActorHandle()])
    rm1.save(0)
    assert json.loads((ckpt / "rollout" / "rh2_published_weight_version_0.json").read_text())["published_weight_version"] is None

    assert rh2_recovery.restore_updater_weight_version(Namespace(load=str(ckpt), start_rollout_id=None), 0) == 0
    ds2 = _real_data_source(world, load=str(ckpt))
    engines = [_FakeActorHandle()]
    rm2 = _rollout_manager_stand_in(world, data_source=ds2, engines=engines)
    rm2.load(0)
    assert rm2._rh2_restored_published_weight_version is None
    updater = _UpdaterStandIn(engines)
    updater.update_weights()
    await rm2.set_weight_version(updater.weight_version)
    assert rm2.weight_version == 1
    [ev] = read_events(events_dir, ("run_restarted",))
    assert ev["published_weight_version"] is None and ev["bootstrap_weight_version"] is None


# ===========================================================================
# 2. 状态文件缺失（恢复语境）→ typed 报错；全新 run 无状态文件 → 正常
# ===========================================================================


def test_missing_state_file_in_recovery_context_is_a_typed_error(world, tmp_path, events_dir):
    from miles.utils import rh2_recovery

    ckpt = tmp_path / "ckpt"
    ckpt.mkdir()  # checkpoint 目录在（Megatron 权重已加载），但 rollout/ 状态文件不在
    ds = _real_data_source(world, load=str(ckpt))
    with pytest.raises(rh2_recovery.RecoveryStateMissing) as ei:
        ds.load(3)  # placement_group: start_rollout_id(4) - 1
    err = ei.value
    assert isinstance(err, RuntimeError)
    assert err.kind == rh2_recovery.STATE_KIND_DATA_SOURCE and err.rollout_id == 3 and err.load_dir == str(ckpt)
    assert err.path == str(ckpt / "rollout" / "global_dataset_state_dict_3.pt")
    assert "rollout_id=3" in str(err) and "--ref-load" in str(err)
    assert _cursor(ds) == {"sample_offset": 0, "epoch_id": 0, "sample_group_index": 0, "sample_index": 0}

    # data_source 状态在、版本文件不在（两次写之间崩溃）：RolloutManager.load 与 trainer 侧都是 typed 报错
    ds.args.save = str(ckpt)
    ds.sample_offset = 5
    ds.save(3)
    ds2 = _real_data_source(world, load=str(ckpt))
    with pytest.raises(rh2_recovery.RecoveryStateMissing) as ei2:
        rh2_recovery.restore_rollout_state(ds2.args, 3, ds2)
    assert ei2.value.kind == rh2_recovery.STATE_KIND_PUBLISHED_VERSION
    assert ei2.value.path == str(ckpt / "rollout" / "rh2_published_weight_version_3.json")
    with pytest.raises(rh2_recovery.RecoveryStateMissing) as ei3:
        rh2_recovery.restore_updater_weight_version(Namespace(load=str(ckpt), start_rollout_id=None), 3)
    assert ei3.value.kind == rh2_recovery.STATE_KIND_PUBLISHED_VERSION
    # 失败路径不发 run_restarted
    assert read_events(events_dir, ("run_restarted",)) == []

    # 真实 RolloutManager.load 方法体走同一条路
    rm = _rollout_manager_stand_in(world, data_source=_real_data_source(world, load=str(ckpt)), engines=[])
    with pytest.raises(rh2_recovery.RecoveryStateMissing):
        rm.load(3)


def test_fresh_run_without_state_files_is_normal(world, tmp_path, events_dir):
    from miles.utils import rh2_recovery

    ckpt = tmp_path / "ckpt"  # launch.sh: --load $CKPT --save $CKPT，全新 run 时目录尚不存在
    ds = _real_data_source(world, load=str(ckpt), start_rollout_id=0)
    ds.load(-1)  # placement_group: start_rollout_id(0) - 1
    ds.load(None)
    assert _cursor(ds) == {"sample_offset": 0, "epoch_id": 0, "sample_group_index": 0, "sample_index": 0}
    # trainer 侧：全新 run 的 Megatron finetune 加载返回 iteration 0，但 arguments.py 已把 start_rollout_id 置 0
    assert rh2_recovery.restore_updater_weight_version(Namespace(load=str(ckpt), start_rollout_id=0), 0) == 0
    assert rh2_recovery.restore_rollout_state(ds.args, -1, ds) is None
    rm = _rollout_manager_stand_in(world, data_source=ds, engines=[])
    rm.load(-1)
    assert rm._rh2_restored_published_weight_version is None
    assert read_events(events_dir, ("run_restarted",)) == []

    # stock 静默路径原样：无 --load；非 global dataset
    ds_noload = _real_data_source(world, load=None)
    ds_noload.load(3)
    ds_local = _real_data_source(world, load=str(ckpt), rollout_global_dataset=False)
    ds_local.load(3)


@pytest.mark.parametrize(
    ("load", "rollout_id", "expected"),
    [
        (None, 3, False),  # 无 --load：stock 静默
        ("/ckpt", -1, False),  # 全新 run：start_rollout_id(0) - 1
        ("/ckpt", None, False),
        ("/ckpt", 0, True),  # 恢复自 iter_0000000（start_rollout_id = 1）
        ("/ckpt", 5, True),
    ],
)
def test_recovery_context_predicate(world, load, rollout_id, expected):
    from miles.utils import rh2_recovery

    assert rh2_recovery.is_recovery_context(Namespace(load=load), rollout_id) is expected


@pytest.mark.parametrize(
    ("start_rollout_id", "loaded_rollout_id", "expected"),
    [
        (None, 3, 3),  # 恢复：start_rollout_id = loaded + 1 → load(loaded)
        (None, 0, 0),
        (None, None, -1),
        (0, 0, -1),  # 全新 run（arguments.py 置 0）：Megatron 返回什么迭代都不算恢复
        (0, 9, -1),
        (5, 2, 4),  # 用户显式 --start-rollout-id 5：与 RolloutManager.load(5 - 1) 同键
    ],
)
def test_restore_rollout_id_mirrors_placement_group_formula(world, start_rollout_id, loaded_rollout_id, expected):
    from miles.utils import rh2_recovery

    args = Namespace(load="/ckpt", start_rollout_id=start_rollout_id)
    assert rh2_recovery.resolve_restore_rollout_id(args, loaded_rollout_id) == expected


# ===========================================================================
# 3. 首次 publish 核对与 W10 单调/收敛核对的关系
# ===========================================================================


async def test_first_publish_after_restore_must_carry_restored_version(world, tmp_path, events_dir):
    """恢复点记录 p=7；trainer 没恢复计数器（bootstrap 标 1）→ RecoveryVersionMismatch，在任何 engine 被
    查询之前、在 weight_version 被记录之前抛；恢复核对通过后 W10 的逐 engine 收敛核对照常生效。"""

    from miles.utils import rh2_recovery
    from miles.utils.rh2_engine_versions import EngineWeightVersionMismatch

    ckpt = tmp_path / "ckpt"
    ds1 = _real_data_source(world, save=str(ckpt))
    rh2_recovery.save_rollout_state(ds1.args, 3, ds1, published_weight_version=7)

    engines = [_FakeActorHandle(), _FakeActorHandle()]
    ds2 = _real_data_source(world, load=str(ckpt))
    rm = _rollout_manager_stand_in(world, data_source=ds2, engines=engines)
    rm.load(3)
    assert rm._rh2_restored_published_weight_version == 7

    unrestored = _UpdaterStandIn(engines)  # 计数器仍是 0：bootstrap 会标 1
    unrestored.update_weights()
    with pytest.raises(rh2_recovery.RecoveryVersionMismatch) as ei:
        await rm.set_weight_version(unrestored.weight_version)
    assert ei.value.restored == 7 and ei.value.published == 1
    assert rm.weight_version is None and [e.calls for e in engines] == [0, 0]  # 恢复核对先于一切

    # 恢复核对只针对本 run 的首次 publish；通过后 W10 收敛核对照常：一台 engine 漏掉 publish 即停
    restored = _UpdaterStandIn(engines)
    restored.weight_version = rh2_recovery.initial_updater_weight_version(7)
    restored.update_weights()
    engines[1].version = "default"  # 第二台没收到 bootstrap publish
    with pytest.raises(EngineWeightVersionMismatch):
        await rm.set_weight_version(restored.weight_version)
    assert [e.calls for e in engines] == [1, 1]
    engines[1].version = "7"
    rm.weight_version = None  # 重放"首次 publish"（生产里 mismatch 即停 run，这里只为覆盖通过分支）
    await rm.set_weight_version(7)
    assert rm.weight_version == 7
    # 第二次 publish 不再做恢复核对，只受 W10 单调断言约束（回退即 AssertionError，indep_dp=False）
    with pytest.raises(AssertionError):
        await rm.set_weight_version(6)


@pytest.mark.parametrize(
    ("restored", "published", "ok"),
    [(None, 1, True), (None, 9, True), (7, 7, True), (7, 8, False), (7, 6, False), (7, 1, False)],
)
def test_check_first_publish_after_restore_table(world, restored, published, ok):
    from miles.utils import rh2_recovery

    if ok:
        rh2_recovery.check_first_publish_after_restore(restored, published)
    else:
        with pytest.raises(rh2_recovery.RecoveryVersionMismatch):
            rh2_recovery.check_first_publish_after_restore(restored, published)


# ===========================================================================
# 4. 状态文件与恢复值
# ===========================================================================


@pytest.mark.parametrize(("published", "expected"), [(None, 0), (1, 0), (7, 6), (100, 99)])
def test_initial_updater_weight_version(world, published, expected):
    from miles.utils import rh2_recovery

    assert rh2_recovery.initial_updater_weight_version(published) == expected


@pytest.mark.parametrize("bad", [0, -1, True, "7"])
def test_initial_updater_weight_version_rejects_impossible_values(world, bad):
    """发布过的版本号不可能是 0 或负数（updater 先 +1 再 publish）；bool/str 不是版本。"""

    from miles.utils import rh2_recovery

    with pytest.raises(ValueError):
        rh2_recovery.initial_updater_weight_version(bad)


def test_published_version_state_file_roundtrip_and_validation(world, tmp_path, monkeypatch):
    from miles.utils import rh2_event_log, rh2_recovery

    root = tmp_path / "ckpt"
    monkeypatch.setenv(rh2_event_log.RUN_ID_ENV, "writer-run")
    path = rh2_recovery.save_published_weight_version(str(root), 5, 9)
    assert path == str(root / "rollout" / "rh2_published_weight_version_5.json")
    assert not (root / "rollout" / "rh2_published_weight_version_5.json.tmp").exists()  # tmp + replace 原子写
    record = rh2_recovery.load_published_weight_version(str(root), 5, required=True)
    assert record["published_weight_version"] == 9 and record["rollout_id"] == 5 and record["run_id"] == "writer-run"
    assert record["path"] == path and record["schema_id"] == rh2_recovery.PUBLISHED_VERSION_STATE_SCHEMA_ID

    # 非 required 且缺失 → None；required 缺失 → typed
    assert rh2_recovery.load_published_weight_version(str(root), 6, required=False) is None
    with pytest.raises(rh2_recovery.RecoveryStateMissing):
        rh2_recovery.load_published_weight_version(str(root), 6, required=True)

    # 版本 0 / 负数不可写
    with pytest.raises(ValueError):
        rh2_recovery.save_published_weight_version(str(root), 7, 0)

    # 损坏 / schema 漂移 / rollout_id 不匹配 → typed（detail 非空）
    broken = root / "rollout" / "rh2_published_weight_version_8.json"
    broken.write_text("{not json", encoding="utf-8")
    with pytest.raises(rh2_recovery.RecoveryStateMissing) as ei:
        rh2_recovery.load_published_weight_version(str(root), 8, required=True)
    assert ei.value.detail and "unusable" in str(ei.value)
    mismatched = json.loads(Path(path).read_text(encoding="utf-8"))
    mismatched["rollout_id"] = 4
    (root / "rollout" / "rh2_published_weight_version_9.json").write_text(json.dumps(mismatched), encoding="utf-8")
    with pytest.raises(rh2_recovery.RecoveryStateMissing):
        rh2_recovery.load_published_weight_version(str(root), 9, required=True)
    drifted = dict(mismatched, rollout_id=10, schema_id="rh2.something_else.v9")
    (root / "rollout" / "rh2_published_weight_version_10.json").write_text(json.dumps(drifted), encoding="utf-8")
    with pytest.raises(rh2_recovery.RecoveryStateMissing):
        rh2_recovery.load_published_weight_version(str(root), 10, required=True)


def test_save_rollout_state_without_save_dir_writes_nothing(world, tmp_path):
    """无 --save：data_source.save 本就不写（它自己拼 args.save 路径），版本文件也不写，返回 None。"""

    from miles.utils import rh2_recovery

    ds = _real_data_source(world, save=None, rollout_global_dataset=False)
    assert rh2_recovery.save_rollout_state(ds.args, 1, ds, published_weight_version=3) is None
    assert list(tmp_path.iterdir()) == []


# ===========================================================================
# 5. 源码事实：六个 updater 的"构造 0 / publish 前 +1"、trainer 构造点接线、RolloutManager 接线、时序
# ===========================================================================


def test_updater_and_wiring_source_facts(world):
    """(a) 六个 updater 构造时 weight_version = 0 且 update_weights 先 +1 再把 str(version) 发给 engine——
    这是恢复值 = p-1 的依据；(b) 两个 backend 的 actor 在 updater 唯一构造点之后恢复计数器；
    (c) placement_group 的顺序（actor init → start_rollout_id → RolloutManager.load(start-1)）与
    train_async 的顺序（bootstrap publish 在循环前；save_model → rollout_manager.save → update_weights）；
    (d) RolloutManager / data_source 接线与路径字面量镜像；(e) arguments.py 的全新 run 分类。"""

    from miles.utils import rh2_recovery

    root = world.miles_root / "miles"
    upd = root / "backends" / "megatron_utils" / "update_weight"
    dist = upd / "update_weight_from_distributed"
    constructors = [
        upd / "update_weight_from_tensor.py",
        upd / "update_weight_from_rdt.py",
        dist / "p2p.py",
        dist / "broadcast.py",
        dist / "delta.py",
        root / "backends" / "fsdp_utils" / "update_weight_utils.py",
    ]
    for path in constructors:
        assert "self.weight_version = 0" in path.read_text(encoding="utf-8"), path
    tensor = (upd / "update_weight_from_tensor.py").read_text(encoding="utf-8")
    assert tensor.index("self.weight_version += 1") < tensor.index("weight_version=self.weight_version,")
    mixin = (dist / "mixin.py").read_text(encoding="utf-8")
    body = mixin[mixin.index("    def update_weights(self) -> None:") :]
    assert body.index("self.weight_version += 1") < body.index("self._pause_and_prepare_engines()")
    assert "engine.update_weight_version.remote(weight_version=str(self.weight_version))" in mixin
    delta = (dist / "delta.py").read_text(encoding="utf-8")
    assert delta.index("self.weight_version += 1") < delta.index("weight_version=str(self.weight_version)")
    fsdp_upd = (root / "backends" / "fsdp_utils" / "update_weight_utils.py").read_text(encoding="utf-8")
    assert fsdp_upd.index("self.weight_version += 1") < fsdp_upd.index("weight_version=self.weight_version)")

    # (b) 唯一构造点之后恢复
    actor = (root / "backends" / "megatron_utils" / "actor.py").read_text(encoding="utf-8")
    i_ctor = actor.index("self.weight_updater = update_weight_cls(")
    i_restore = actor.index(
        "self.weight_updater.weight_version = rh2_recovery.restore_updater_weight_version(self.args, loaded_rollout_id)"
    )
    i_return = actor.index("        return start_rollout_id\n", i_ctor)
    assert i_ctor < i_restore < i_return
    assert actor.index("start_rollout_id = loaded_rollout_id + 1") < i_ctor  # loaded_rollout_id 就是 Megatron 加载的迭代
    assert "from miles.utils import rh2_event_log, rh2_recovery" in actor
    fsdp_actor = (root / "backends" / "fsdp_utils" / "actor.py").read_text(encoding="utf-8")
    i_fin = fsdp_actor.index("checkpoint.finalize_load(self, checkpoint_payload)")
    i_frestore = fsdp_actor.index(
        "self.weight_updater.weight_version = rh2_recovery.restore_updater_weight_version(self.args, loaded_rollout_id=None)"
    )
    assert fsdp_actor.index("self.weight_updater = (") < i_fin < i_frestore
    fsdp_ckpt = (root / "backends" / "fsdp_utils" / "checkpoint.py").read_text(encoding="utf-8")
    assert "actor.args.start_rollout_id = next_rollout" in fsdp_ckpt  # finalize_load 之后 start_rollout_id 才定

    # (c) 时序
    pg = (root / "ray" / "placement_group.py").read_text(encoding="utf-8")
    i_init = pg.index("actor_start_rollout_ids = await actor_model.init()")
    i_set = pg.index("args.start_rollout_id = start_rollout_ids[0]")
    i_load = pg.index("await rollout_manager.load.remote(args.start_rollout_id - 1)")
    assert i_init < i_set < i_load
    ta = (world.miles_root / "train_async.py").read_text(encoding="utf-8")
    assert ta.index("await actor_model.update_weights()") < ta.index(
        "for rollout_id in range(args.start_rollout_id, args.num_rollout):"
    )
    i_save_model = ta.index("await save_training_model(actor_model, rollout_id, force_sync)")
    i_rm_save = ta.index("await rollout_manager.save.remote(rollout_id)")
    i_update = ta.index("await actor_model.update_weights(rollout_id=rollout_id)")
    assert i_save_model < i_rm_save < i_update  # 所以保存的是 rollout_id 之前那次 publish 的版本 p

    # (d) RolloutManager / data_source 接线
    rm = (root / "ray" / "rollout" / "rollout_manager.py").read_text(encoding="utf-8")
    assert "self._rh2_restored_published_weight_version: int | None = None" in rm
    assert "rh2_recovery.save_rollout_state(self.args, rollout_id, self.data_source, self.weight_version)" in rm
    assert "state = rh2_recovery.restore_rollout_state(self.args, rollout_id, self.data_source)" in rm
    swv = rm[rm.index("    async def set_weight_version(self, weight_version: int):") :]
    swv = swv[: swv.index("    async def _verify_engine_weight_versions")]
    i_check = swv.index("rh2_recovery.check_first_publish_after_restore(self._rh2_restored_published_weight_version, weight_version)")
    i_back = swv.index("Engine weight version went backwards")
    i_record = swv.index("self.weight_version = weight_version")
    i_verify = swv.index("await self._verify_engine_weight_versions(weight_version)")
    assert swv.index("if self.weight_version is None:") < i_check < i_back < i_record < i_verify
    ds = (root / "rollout" / "data_source.py").read_text(encoding="utf-8")
    assert ds.index("if rh2_recovery.is_recovery_context(self.args, rollout_id):") < ds.index(
        'logger.info(f"Checkpoint {path} does not exist.")'
    )
    assert 'f"rollout/global_dataset_state_dict_{rollout_id}.pt"' in ds  # stock 路径字面量未动
    assert rh2_recovery.data_source_state_path("/x", 3) == "/x/rollout/global_dataset_state_dict_3.pt"
    assert rh2_recovery.published_version_state_path("/x", 3) == "/x/rollout/rh2_published_weight_version_3.json"
    # 没有任何 buffer 持久化面（"buffer 与在飞组全部丢弃"是结构事实，不是清理动作）
    for rel in ("rollout/fully_async_data_buffer.py", "rollout/fully_async_rollout.py"):
        src = (root / rel).read_text(encoding="utf-8")
        assert "torch.save(" not in src and "torch.load(" not in src, rel

    # (e) arguments.py：--load 下无 tracker → start_rollout_id = 0（全新 run），否则保留 None 交给 trainer
    args_src = (root / "utils" / "arguments.py").read_text(encoding="utf-8")
    assert 'os.path.join(args.load, "latest_checkpointed_iteration.txt")' in args_src
    assert args_src.count("args.start_rollout_id = 0") >= 2
    assert '"--start-rollout-id"' in args_src and "default=None" in args_src[args_src.index('"--start-rollout-id"') :][:200]
