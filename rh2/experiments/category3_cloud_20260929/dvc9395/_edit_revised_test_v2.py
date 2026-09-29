# 修订测试 v2（在已应用原 test_patch 的工作树上编辑）：
# R-b：删除 checkout 计数断言；restore 的调用断言放宽为 assert_called_with（复核 N5）
# R-c：数据源测试断言 foo、bar 的内容（复核 N1）；已存在但被修改的数据源在 --pull 下保留（复核 N2，主审判 S1）
from pathlib import Path

p = Path("tests/func/test_repro_multistage.py")
s = p.read_text()
old = '''    dvc.stage.add(name="copy-foo", cmd="cp foo bar", deps=["foo"], outs=["bar"])
    remove("foo")
    remove(foo.outs[0].cache_path)

    assert dvc.reproduce(pull=True)


def test_repro_pulls_mising_import('''
assert s.count(old) == 1
s = s.replace(old, '''    dvc.stage.add(name="copy-foo", cmd="cp foo bar", deps=["foo"], outs=["bar"])
    remove("foo")
    remove(foo.outs[0].cache_path)

    assert dvc.reproduce(pull=True)
    assert (tmp_dir / "foo").read_text() == "foo"
    assert (tmp_dir / "bar").read_text() == "foo"

    # Data that is present but was modified is not missing: it is kept and used
    (tmp_dir / "foo").write_text("modified")
    assert dvc.reproduce(pull=True)
    assert (tmp_dir / "foo").read_text() == "modified"
    assert (tmp_dir / "bar").read_text() == "modified"


def test_repro_pulls_mising_import(''')
p.write_text(s)

p = Path("tests/func/test_run_cache.py")
s = p.read_text()
old = '''    mock_restore.assert_called_once_with(stage, pull=True, dry=False)
    mock_run.assert_not_called()
    assert mock_checkout.call_count == 3
    assert (tmp_dir / "bar").exists()
'''
assert s.count(old) == 1
s = s.replace(old, '''    mock_restore.assert_called_with(stage, pull=True, dry=False)
    mock_run.assert_not_called()
    assert (tmp_dir / "bar").read_text() == "foo"
''')
p.write_text(s)
