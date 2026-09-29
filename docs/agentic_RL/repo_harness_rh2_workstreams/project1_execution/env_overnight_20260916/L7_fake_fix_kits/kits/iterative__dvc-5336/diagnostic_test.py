"""L7 判别用例 · iterative__dvc-5336

F2P 的唯一断言是 `assert mock_chmod.called`，对"哪些异常应当继续上抛"没有任何约束。
gold 的语义是"只吞 OSError 并记 logger.trace"；假修复吞掉 BaseException。
`LocalTree.protect` 只是转调 `self.chmod`（`dvc/tree/local.py:300-301`），中间没有别的 try。

三态预期：base 通过、gold 通过、fake 失败（ValueError 被吞掉）。
"""
import pytest

from dvc.path_info import PathInfo
from dvc.tree.local import LocalTree


def test_l7_non_oserror_still_propagates(tmp_dir, mocker):
    tmp_dir.gen("foo", "foo")
    mocker.patch("os.chmod", side_effect=ValueError("not an OSError"))
    with pytest.raises(ValueError):
        LocalTree(None, {}).protect(PathInfo("foo"))
