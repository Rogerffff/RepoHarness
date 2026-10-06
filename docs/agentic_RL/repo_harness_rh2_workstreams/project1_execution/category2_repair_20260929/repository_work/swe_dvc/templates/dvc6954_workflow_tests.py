

def test_negative_python_params_lock_and_repro(tmp_dir, dvc):
    from dvc.utils.serialize import load_yaml

    original = "my_int = -7\nmy_float = -0.25\nnested = {'v': -3.5}\n"
    tmp_dir.gen("params.py", original)
    stage = dvc.run(
        name="negative-params",
        cmd="echo complete > out.txt",
        params=["params.py:my_int,my_float,nested.v"],
        outs=["out.txt"],
    )
    assert stage is not None
    values = load_yaml("dvc.lock")["stages"]["negative-params"]["params"]["params.py"]
    assert values == {"my_int": -7, "my_float": -0.25, "nested.v": -3.5}
    assert (tmp_dir / "out.txt").read_text().strip() == "complete"
    assert not dvc.reproduce("negative-params")

    (tmp_dir / "params.py").write_text(original.replace("-0.25", "-0.375"))
    assert dvc.reproduce("negative-params")
    values = load_yaml("dvc.lock")["stages"]["negative-params"]["params"]["params.py"]
    assert values == {"my_int": -7, "my_float": -0.375, "nested.v": -3.5}
