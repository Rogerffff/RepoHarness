"""I21（第五组）：评测派发身份——独立命名空间、只由宿主事实推导、与训练身份互不可达。

规则来源：`adapters/miles/identity.py::mint_eval_attempt_identity`。eval 样本没有 `group_index`
（miles `inference_rollout_eval` 只给扁平 `index`），训练铸造的组算术不适用；rollout_id 也不是唯一调用
标识（训练前与第 0 步之后两次 eval 都是 rollout 0），所以评测点用宿主每次调用生成的 `eval_point_id`。
"""

from __future__ import annotations

import pytest


def _facts(**over):
    base = {
        "eval_point_id": "0123abcd4567", "eval_rollout_id": 0, "target_weight_version": "1", "hf_dir": None,
        "dataset": "swe dev/中文 name", "dataset_index": 0, "prompt_index": 3, "sample_slot": 1,
        "n_samples_per_eval_prompt": 2, "num_prompts": 5,
    }
    base.update(over)
    return base


def _eval_sample(world, **facts_over):
    sample = world.mk_miles_input(index=7, group_index=None)
    sample.metadata = {"task_id": "t", "rh2_eval_dispatch": _facts(**facts_over)}
    return sample


def test_eval_identity_is_derived_from_host_facts_in_its_own_namespace(world):
    from repoharness2.adapters.miles import identity as idm

    sample = _eval_sample(world)
    minted = idm.mint_eval_attempt_identity(sample)
    assert minted[idm.GROUP_ID_KEY] == "eval-0123abcd4567-d0-p3"
    assert minted[idm.GROUP_INDEX_KEY] == 3 and minted[idm.MEMBER_SLOT_KEY] == 1
    assert minted[idm.EXECUTION_ID_KEY] == "eval-0123abcd4567-d0-p3_m1"
    assert minted[idm.ATTEMPT_SEQ_KEY] == 1
    assert minted[idm.ATTEMPT_ID_KEY].startswith("eval-0123abcd4567-d0-p3_m1#p1-") and len(minted[idm.ATTEMPT_ID_KEY].rsplit("-", 1)[1]) == 8
    assert all(sample.metadata[k] == minted[k] for k in idm.IDENTITY_KEYS)  # 写回样本 metadata
    # 数据集名不进身份（任意字符都行）；训练命名空间以 miles_g 开头，两者不相交
    assert "中文" not in minted[idm.GROUP_ID_KEY] and not minted[idm.GROUP_ID_KEY].startswith(idm.TRAIN_GROUP_ID_PREFIX)


def test_two_eval_calls_at_the_same_rollout_id_never_share_identity(world):
    """Codex R2：训练前 r0 与第 0 步之后 r0 是两个评测点——身份由 eval_point_id 区分，不是 rollout_id。"""

    from repoharness2.adapters.miles import identity as idm

    before = idm.mint_eval_attempt_identity(_eval_sample(world, eval_point_id="aaaaaaaa0001", eval_rollout_id=0))
    after = idm.mint_eval_attempt_identity(_eval_sample(world, eval_point_id="aaaaaaaa0002", eval_rollout_id=0))
    assert before[idm.EXECUTION_ID_KEY] != after[idm.EXECUTION_ID_KEY]
    assert before[idm.GROUP_ID_KEY] != after[idm.GROUP_ID_KEY]
    # 同一评测点、同一 prompt 的不同样本槽 → 同组、不同成员
    a = idm.mint_eval_attempt_identity(_eval_sample(world, sample_slot=0))
    b = idm.mint_eval_attempt_identity(_eval_sample(world, sample_slot=1))
    assert a[idm.GROUP_ID_KEY] == b[idm.GROUP_ID_KEY] and a[idm.EXECUTION_ID_KEY] != b[idm.EXECUTION_ID_KEY]


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (lambda s: s.metadata.pop("rh2_eval_dispatch"), "eval_host_facts_missing"),
        (lambda s: s.metadata.update(rh2_eval_dispatch="swe_dev"), "eval_host_facts_missing"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(eval_point_id="r0"), "eval_host_facts_malformed"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(eval_point_id="ABCDEF0123"), "eval_host_facts_malformed"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(prompt_index=True), "eval_host_facts_malformed"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(sample_slot=2), "eval_host_facts_malformed"),  # >= n
        (lambda s: s.metadata["rh2_eval_dispatch"].update(prompt_index=5), "eval_host_facts_malformed"),  # >= prompts
        (lambda s: s.metadata["rh2_eval_dispatch"].update(dataset=""), "eval_host_facts_malformed"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(eval_rollout_id="0"), "eval_host_facts_malformed"),
        (lambda s: s.metadata["rh2_eval_dispatch"].update(target_weight_version=1), "eval_host_facts_malformed"),
    ],
)
def test_missing_or_malformed_host_facts_fail_closed(world, mutate, code):
    from repoharness2.adapters.miles import identity as idm

    sample = _eval_sample(world)
    mutate(sample)
    with pytest.raises(idm.MilesIdentityError) as err:
        idm.mint_eval_attempt_identity(sample)
    assert err.value.reason_code == code
    assert not any(k in sample.metadata for k in idm.IDENTITY_KEYS)  # 拒绝时不留半截身份


def test_eval_input_carrying_reserved_identity_or_non_fresh_status_is_rejected(world):
    from repoharness2.adapters.miles import identity as idm

    polluted = _eval_sample(world)
    polluted.metadata[idm.GROUP_ID_KEY] = "miles_g3"  # 训练身份键混进评测输入
    with pytest.raises(idm.MilesIdentityError) as err:
        idm.mint_eval_attempt_identity(polluted)
    assert err.value.reason_code == "reserved_identity_keys_polluted"

    retried = _eval_sample(world)
    retried.status = world.MS.Status.ABORTED  # miles eval 不重派发：非 fresh 形态不认
    with pytest.raises(idm.MilesIdentityError) as err:
        idm.mint_eval_attempt_identity(retried)
    assert err.value.reason_code == "dispatch_status_unexpected"

    twice = _eval_sample(world)
    idm.mint_eval_attempt_identity(twice)
    with pytest.raises(idm.MilesIdentityError):  # 同一样本二次派发 = 已带身份键
        idm.mint_eval_attempt_identity(twice)


def test_training_minting_is_unchanged_and_still_requires_group_facts(world):
    from repoharness2.adapters.miles import identity as idm

    train = world.mk_miles_input(index=5, group_index=2)
    minted = idm.mint_attempt_identity(train, n_samples_per_prompt=2)
    assert minted[idm.GROUP_ID_KEY] == "miles_g2" and minted[idm.MEMBER_SLOT_KEY] == 1
    # eval 形状（group_index=None）走训练铸造仍然 fail-closed——这正是评测需要独立铸造的原因
    with pytest.raises(idm.MilesIdentityError) as err:
        idm.mint_attempt_identity(_eval_sample(world), n_samples_per_prompt=2)
    assert err.value.reason_code == "identity_facts_missing"


def test_assignment_carries_the_dispatch_plane(world):
    from repoharness2.adapters.miles import identity as idm
    from repoharness2.adapters.miles.attempt_assignment import AttemptAssignmentRegistry, assignment_from_dispatch

    dispatch = {"task_id": "t1", "environment_package_digest": "sha256:" + "a" * 64, "public_bundle_digest": "sha256:" + "b" * 64}
    sample = _eval_sample(world)
    sample.metadata.update(dispatch)
    minted = idm.mint_eval_attempt_identity(sample)
    eval_assignment = assignment_from_dispatch(sample.metadata, minted, evaluation=True)
    assert eval_assignment.evaluation is True and eval_assignment.group_index == 3
    train = world.mk_miles_input(index=0, group_index=0)
    train.metadata.update(dispatch)
    train_assignment = assignment_from_dispatch(train.metadata, idm.mint_attempt_identity(train, n_samples_per_prompt=2))
    assert train_assignment.evaluation is False  # 缺省 = 训练平面

    seen: list[tuple[str, bool]] = []
    registry = AttemptAssignmentRegistry(verify_dispatch=lambda a: seen.append((a.task_id, a.evaluation)))
    registry.bind(eval_assignment)
    registry.bind(train_assignment)
    assert seen == [("t1", True), ("t1", False)]  # 同一道题可以同时出现在两个平面，核对各按各的平面
    assert registry.resolve_for_sample(sample.metadata).evaluation is True
