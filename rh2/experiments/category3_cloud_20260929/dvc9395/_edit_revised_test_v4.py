# 修订测试 v4（在已应用原 test_patch 并执行 _edit_revised_test_v2.py 的工作树上编辑）：
# - 复核 v2 聚焦复核的 v3 三处（原样采纳）：模拟对提示一律回答“是”时修改仍保留；repro 后 status 为空；
#   从未 push 的数据源缺失时必须报 ReproductionError
# - 主审补一个非示例实例（§4 第 2 步严格版）：dvc import 也是数据源（base 的 is_data_source：
#   "created with `dvc add` or `dvc import`"），缺失时同样要被拉回；测试体取自 test_patch 自带的 import 测试
from pathlib import Path

p = Path("tests/func/test_repro_multistage.py")
s = p.read_text()
old_sig = "def test_repro_pulls_mising_data_source(tmp_dir, dvc, mocker, local_remote):\n"
assert s.count(old_sig) == 1
s = s.replace(old_sig, "def test_repro_pulls_mising_data_source(\n    tmp_dir, dvc, mocker, local_remote, erepo_dir\n):\n")
old = '''    # Data that is present but was modified is not missing: it is kept and used
    (tmp_dir / "foo").write_text("modified")
    assert dvc.reproduce(pull=True)
    assert (tmp_dir / "foo").read_text() == "modified"
    assert (tmp_dir / "bar").read_text() == "modified"
'''
assert s.count(old) == 1
s = s.replace(old, '''    # Data that is present but was modified is not missing: it is kept and used,
    # even by a user who answers yes to every prompt
    (tmp_dir / "foo").write_text("modified")
    mocker.patch("dvc.prompt.confirm", return_value=True)
    assert dvc.reproduce(pull=True)
    assert (tmp_dir / "foo").read_text() == "modified"
    assert (tmp_dir / "bar").read_text() == "modified"
    assert not dvc.status()

    # Imports are data sources too: their missing data is pulled as well
    with erepo_dir.chdir():
        erepo_dir.dvc_gen("imported", "imported", commit="add imported")
    imported = dvc.imp(os.fspath(erepo_dir), "imported")
    dvc.push()
    remove("imported")
    remove(imported.outs[0].cache_path)
    dvc.reproduce("imported.dvc", pull=True)
    assert (tmp_dir / "imported").read_text() == "imported"

    # Missing data that cannot be pulled is still an error
    (baz,) = tmp_dir.dvc_gen("baz", "baz")
    remove("baz")
    remove(baz.outs[0].cache_path)
    with pytest.raises(ReproductionError):
        dvc.reproduce("baz.dvc", pull=True)
''')
p.write_text(s)
