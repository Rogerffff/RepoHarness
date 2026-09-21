"""L7 判别用例 · iterative__dvc-4719

上游 test_patch 里的 `assert get_stage_hash.not_called` 是笔误（Mock 属性访问恒真）。
把它写成真断言之后，"`save` 开头无条件 return" 这种破坏性假修复就暴露了：
普通 stage（既不是 callback 也不是 always_changed）必须真的去算 stage hash。

三态预期：base 通过、gold 通过、fake 失败（`_get_stage_hash` 根本没被调用）。
"""


def test_l7_normal_stage_still_computes_hash(mocker):
    from dvc.repo import Repo
    from dvc.stage import Stage
    from dvc.stage.cache import StageCache

    repo = mocker.Mock(spec=Repo)
    cache = StageCache(repo)
    stage = Stage(repo)  # is_callback=False, always_changed=False
    # 返回 None 让 save() 在算完 hash 后立刻返回，避免产生任何落盘副作用
    get_stage_hash = mocker.patch("dvc.stage.cache._get_stage_hash", return_value=None)

    assert cache.save(stage) is None
    get_stage_hash.assert_called_once_with(stage)


def test_l7_always_changed_stage_is_skipped(mocker):
    """gold 的正向语义：always_changed 的 stage 不算 hash（这条 base 会失败）。"""
    from dvc.repo import Repo
    from dvc.stage import Stage
    from dvc.stage.cache import StageCache

    repo = mocker.Mock(spec=Repo)
    cache = StageCache(repo)
    stage = Stage(repo, always_changed=True)
    get_stage_hash = mocker.patch("dvc.stage.cache._get_stage_hash", return_value=None)

    assert cache.save(stage) is None
    get_stage_hash.assert_not_called()
