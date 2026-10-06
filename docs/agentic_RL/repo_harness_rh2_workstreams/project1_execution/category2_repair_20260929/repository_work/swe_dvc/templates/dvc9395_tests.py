

def _rh2_content_snapshot(dvc):
    # 只核工作区、对象 cache 和 runs 的内容；不把状态数据库/临时锁当输出。
    import hashlib
    from pathlib import Path

    root = Path(dvc.root_dir)

    def collect(directory, exclude_metadata=False):
        result = {}
        if not directory.exists():
            return result
        for path in directory.rglob("*"):
            relative = path.relative_to(directory)
            if exclude_metadata and relative.parts[0] in (".git", ".dvc"):
                continue
            if path.is_symlink():
                result[str(relative)] = ("symlink", os.readlink(path))
            elif path.is_file():
                result[str(relative)] = hashlib.sha256(path.read_bytes()).hexdigest()
        return result

    return {
        "workspace": collect(root, exclude_metadata=True),
        "objects_and_runs": collect(Path(dvc.cache.local.path)),
    }


def _rh2_copy_pipeline(tmp_dir, dvc):
    tmp_dir.dvc_gen("foo", "foo")
    dvc.stage.add(
        name="copy-foo",
        cmd="cp foo bar && printf ran >> executions",
        deps=["foo"],
        outs=["bar"],
    )
    (stage,) = dvc.reproduce("copy-foo")
    assert (tmp_dir / "bar").read_text() == "foo"
    return stage


def test_pull_recovers_frozen_stage_for_downstream(tmp_dir, dvc, local_remote):
    tmp_dir.gen("src", "frozen data")
    dvc.stage.add(
        name="download",
        cmd="cp src raw && printf frozen-ran >> frozen-executions",
        deps=["src"],
        outs=["raw"],
    )
    (stage,) = dvc.reproduce("download")
    dvc.freeze("download")
    dvc.push()
    dvc.stage.add(name="consume", cmd="cp raw model", deps=["raw"], outs=["model"])
    before = (tmp_dir / "frozen-executions").read_bytes()
    remove("raw")
    remove(stage.outs[0].cache_path)

    assert dvc.reproduce("consume", pull=True, run_cache=False)
    assert (tmp_dir / "raw").read_text() == "frozen data"
    assert (tmp_dir / "model").read_text() == "frozen data"
    assert (tmp_dir / "frozen-executions").read_bytes() == before


@pytest.mark.parametrize("missing", ["source", "output"])
def test_pull_dry_preserves_workspace_and_cache(tmp_dir, dvc, local_remote, missing):
    _rh2_copy_pipeline(tmp_dir, dvc)
    dvc.push(run_cache=True)
    remove("foo" if missing == "source" else "bar")
    remove(dvc.cache.local.path)
    before = _rh2_content_snapshot(dvc)
    try:
        dvc.reproduce("copy-foo", pull=True, dry=True)
    except (ReproductionError, FileNotFoundError):
        # base 在 dry 读取缺失源时可报错；此处只保护 dry 的无副作用契约。
        if missing != "source":
            raise
    assert _rh2_content_snapshot(dvc) == before


@pytest.mark.parametrize("dry", [False, True], ids=["normal", "dry"])
def test_pull_without_remote_when_nothing_missing(tmp_dir, dvc, dry):
    _rh2_copy_pipeline(tmp_dir, dvc)
    before = _rh2_content_snapshot(dvc)
    dvc.reproduce("copy-foo", pull=True, dry=dry)
    assert _rh2_content_snapshot(dvc)["workspace"] == before["workspace"]
    assert (tmp_dir / "foo").read_text() == "foo"
    assert (tmp_dir / "bar").read_text() == "foo"


def test_pull_without_remote_preserves_modified_source(tmp_dir, dvc):
    _rh2_copy_pipeline(tmp_dir, dvc)
    (tmp_dir / "foo").write_text("modified")
    assert dvc.reproduce("copy-foo", pull=True)
    assert (tmp_dir / "foo").read_text() == "modified"
    assert (tmp_dir / "bar").read_text() == "modified"


def test_pull_without_remote_still_errors_for_missing_source(tmp_dir, dvc):
    (source,) = tmp_dir.dvc_gen("foo", "foo")
    dvc.stage.add(name="consume", cmd="cp foo bar", deps=["foo"], outs=["bar"])
    remove("foo")
    remove(source.outs[0].cache_path)
    with pytest.raises(ReproductionError):
        dvc.reproduce("consume", pull=True)
    assert not (tmp_dir / "bar").exists()


def test_pull_no_run_cache_does_not_download_runs(tmp_dir, dvc, local_remote):
    _rh2_copy_pipeline(tmp_dir, dvc)
    dvc.push(run_cache=True)
    remove(dvc.stage_cache.cache_dir)
    before = _rh2_content_snapshot(dvc)
    dvc.reproduce("copy-foo", pull=True, run_cache=False)
    assert _rh2_content_snapshot(dvc) == before


def test_pull_existing_output_without_hash_can_run(tmp_dir, dvc, local_remote):
    tmp_dir.dvc_gen("foo", "foo")
    dvc.push()
    tmp_dir.gen("baz", "manual")
    dvc.stage.add(name="make-baz", cmd="cp foo baz", deps=["foo"], outs=["baz"])
    assert dvc.reproduce("make-baz", pull=True)
    assert (tmp_dir / "baz").read_text() == "foo"


def test_pull_changed_dependency_can_recompute(tmp_dir, dvc, local_remote):
    tmp_dir.gen("fixed", "before")
    dvc.stage.add(name="create", cmd="cp fixed result", deps=["fixed"], outs=["result"])
    assert dvc.reproduce("create")
    # remote 保持空；旧输出拿不到并不妨碍按已改变的依赖重新计算。
    remove(dvc.cache.local.path)
    (tmp_dir / "fixed").write_text("after")
    assert dvc.reproduce("create", pull=True)
    assert (tmp_dir / "result").read_text() == "after"


def test_pull_restores_from_http_with_local_run_cache(tmp_dir, dvc, local_remote):
    import functools
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
    from pathlib import Path

    stage = _rh2_copy_pipeline(tmp_dir, dvc)
    dvc.push(run_cache=True)
    remote_name = dvc.config["core"]["remote"]
    remote_path = Path(dvc.config["remote"][remote_name]["url"])
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(remote_path))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with dvc.config.edit() as config:
            config["remote"]["http"] = {
                "url": "http://127.0.0.1:{}/".format(server.server_port)
            }
            config["core"]["remote"] = "http"
        remove("bar")
        remove(LOCK_FILE)
        remove(stage.outs[0].cache_path)
        # 保留本地 runs，只恢复缺失对象；不要求 HTTP 支持列举/下载 runs。
        before = (tmp_dir / "executions").read_bytes()
        dvc.reproduce("copy-foo", pull=True)
        assert (tmp_dir / "bar").read_text() == "foo"
        assert (tmp_dir / "executions").read_bytes() == before
        assert (tmp_dir / LOCK_FILE).exists()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)
        assert not thread.is_alive()
