# 主审自写的第三个替代实现（按上游 3.51 的语义“只拉取缺失的数据”，代码独立于复核者的 mine_*）：
# - 顶层 run-cache 拉取：遵守 dry 与 run_cache 参数，remote 不支持 run-cache 或未配置 remote 时只警告；
# - 数据源 stage：只拉取工作区里缺失的输出，已存在（包括被用户修改）的数据不动；
# - 有命令的 stage 仍按原逻辑经 run-cache 恢复（restore 在 pull=True 时会拉取输出对象）。
from pathlib import Path

p = Path("dvc/repo/reproduce.py")
s = p.read_text()
old_ret = "    return _reproduce_stages(self.index.graph, list(stages), **kwargs)\n"
assert s.count(old_ret) == 1
s = s.replace(old_ret, '''    if (
        kwargs.get("pull", False)
        and kwargs.get("run_cache", True)
        and not kwargs.get("dry", False)
    ):
        _pull_run_cache(self)

    return _reproduce_stages(self.index.graph, list(stages), **kwargs)


def _pull_run_cache(repo: "Repo") -> None:
    from dvc.config import NoRemoteError
    from dvc.stage.cache import RunCacheNotSupported

    logger.debug("Pulling run cache")
    try:
        repo.stage_cache.pull(None)
    except (NoRemoteError, RunCacheNotSupported) as exc:
        logger.warning("Failed to pull run cache: %s", exc)


def _pull_missing_data(stage: "Stage", jobs=None) -> None:
    """Pull the outputs of a data source that are missing from the workspace."""
    if stage.cmd:
        return
    missing = [out.fs_path for out in stage.outs if out.use_cache and not out.exists]
    if missing:
        logger.debug("Pulling missing data of %s", stage.addressing)
        stage.repo.pull(missing, jobs=jobs, allow_missing=True)
''')
old_try = "        try:\n            ret = _reproduce_stage(stage, **kwargs)\n"
assert s.count(old_try) == 1, s.count(old_try)
s = s.replace(old_try, '''        try:
            if kwargs.get("pull") and not kwargs.get("dry"):
                _pull_missing_data(stage, jobs=kwargs.get("jobs"))
            ret = _reproduce_stage(stage, **kwargs)
''')
p.write_text(s)
