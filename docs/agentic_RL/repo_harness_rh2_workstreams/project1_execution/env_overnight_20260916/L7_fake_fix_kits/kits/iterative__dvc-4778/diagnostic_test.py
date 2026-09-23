"""L7 判别用例 · iterative__dvc-4778

断言的是 base 的既有公开行为：对**普通**路径 `dvc add` 必须成功。
当前判分面（4 条 `pytest.raises(DvcException)` + P2P=0）里没有任何一条这样的用例，
所以 `resolve_paths` 开头无条件 `raise DvcException` 的假修复能拿满分。

三态预期：base 通过、gold 通过、fake 失败。
"""
import os


def test_l7_plain_add_still_works(tmp_dir, dvc):
    tmp_dir.gen({"foo": "foo"})
    dvc.add("foo")
    assert (tmp_dir / "foo.dvc").exists()


def test_l7_add_in_plain_subdir_still_works(tmp_dir, dvc):
    tmp_dir.gen({"sub": {"bar": "bar"}})
    dvc.add(os.path.join("sub", "bar"))
    assert (tmp_dir / "sub" / "bar.dvc").exists()
