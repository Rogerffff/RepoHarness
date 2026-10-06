"""离线重建 Dask 五题草案；只写本包，不发布正式材料，不运行项目代码。"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent.parent
ROOT = next(p for p in HERE.parents if (p / "rh2").is_dir() and (p / "AGENTS.md").is_file())
CLOUD = ROOT / "rh2/experiments/category3_cloud_20260929"
OWNER = "01a0fd62-996e-7953-8af9-856540ff3015"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def rel(p: Path) -> str:
    return p.relative_to(ROOT).as_posix()


def read(p: Path) -> str:
    return p.read_bytes().decode("utf-8")


def save_json(p: Path, value: object) -> None:
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"需要恰好命中一次，实际 {text.count(old)}: {old[:100]!r}")
    return text.replace(old, new, 1)


def apply_to_file(base: bytes, path: str, patch: bytes) -> bytes:
    # 在独立临时树里让 git 核对上下文；不碰导出的原件和当前仓库。
    with tempfile.TemporaryDirectory(prefix="rh2-dask-material-") as td:
        target = Path(td) / path
        target.parent.mkdir(parents=True)
        target.write_bytes(base)
        subprocess.run(["git", "apply", "--check", "-"], input=patch, cwd=td, check=True, capture_output=True)
        subprocess.run(["git", "apply", "-"], input=patch, cwd=td, check=True, capture_output=True)
        return target.read_bytes()


def make_patch(path: str, old: str, new: str) -> bytes:
    patch = "diff --git a/" + path + " b/" + path + "\n"
    patch += "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True), fromfile="a/" + path, tofile="b/" + path))
    return patch.encode("utf-8")


def source(task: int) -> tuple[Path, Path, dict, dict]:
    root = ROOT / "runs" / ("swegym_quality_batch01_20260921" if task == 8801 else "swegym_quality_expansion_20260925")
    public = root / "public" / f"dask__dask-{task}"
    private = root / "private" / f"dask__dask-{task}"
    pub = json.loads(read(public / "public_bundle.json"))
    grade = json.loads(read(private / "grading.json"))
    assert pub["base_commit"] == grade["base_commit"]
    assert pub["problem_statement_sha256"].removeprefix("sha256:") == sha(pub["problem_statement"].encode("utf-8"))
    assert grade["test_patch"].encode("utf-8") == (private / "test.patch").read_bytes()
    return public, private, pub, grade


def save_task(task: int, test_path: str, effective: str, *, version: str, requested: str,
              reason: str, added_p2p: list[str] | None = None, statement: str | None = None,
              candidate_patches: dict[str, bytes] | None = None) -> Path:
    public, private, pub, grade = source(task)
    out = HERE / "tasks" / f"dask__dask-{task}"
    out.mkdir(parents=True, exist_ok=True)
    result_path = out / "results.json"
    if result_path.exists():
        previous = json.loads(read(result_path))
        if (previous.get("new_reward_rows") or previous.get("cpu_formal_acceptance") != "pending"
                or previous.get("isolated_config_api_check") or previous.get("image_preparation")):
            raise ValueError("已有行为/准备/评分证据，不允许重建脚本覆盖；先保存原件并另登记新的材料版本")
    base = (public / "base" / test_path).read_bytes()
    patch = make_patch(test_path, base.decode("utf-8"), effective)
    rebuilt = apply_to_file(base, test_path, patch)
    assert rebuilt.decode("utf-8") == effective
    ast.parse(effective, filename=test_path)
    (out / "effective_test.patch").write_bytes(patch)
    # 把可审阅的有效文件留在题主私有材料区；它不是 actor 的公开源码。
    (out / "effective_test.py").write_bytes(rebuilt)
    artifacts = {}
    for name, p in {"public_bundle": public / "public_bundle.json", "grading_bundle": private / "grading.json",
                    "original_test_patch": private / "test.patch", "gold": private / "gold.patch",
                    "exported_base_identity": public / "base_identity.json",
                    "base_test_file": public / "base" / test_path}.items():
        artifacts[name] = {"path": rel(p), "sha256": sha(p.read_bytes())}
    added_p2p = added_p2p or []
    assert not set(added_p2p).intersection(grade["pass_to_pass"])
    assert len(set(grade["fail_to_pass"] + grade["pass_to_pass"] + added_p2p)) == len(grade["fail_to_pass"] + grade["pass_to_pass"] + added_p2p)
    save_json(out / "revision.json", {
        "schema": "dask_task_revision_preparation.v1", "as_of": "2026-10-03", "instance_id": pub["instance_id"],
        "owner_thread_id": OWNER, "state": "draft_not_published_not_cpu_accepted", "revision_id": version,
        "repo": pub["repo"], "base_commit": pub["base_commit"], "source_artifacts": artifacts,
        "image": pub["image"], "image_manifest_digest": pub["image_manifest_digest"],
        "requested_operation": requested, "reason": reason,
        "effective_test_patch": {"path": rel(out / "effective_test.patch"), "sha256": sha(patch)},
        "effective_test_file": {"repository_path": test_path, "base_sha256": sha(base), "effective_sha256": sha(rebuilt)},
        "original_fail_to_pass": grade["fail_to_pass"], "original_pass_to_pass": grade["pass_to_pass"],
        "added_pass_to_pass": added_p2p, "effective_fail_to_pass": grade["fail_to_pass"],
        "effective_pass_to_pass": grade["pass_to_pass"] + added_p2p, "test_command": grade["eval_cmd"],
        "statement_change": statement is not None, "formal_ingest_version": None,
        "formal_material_digest": None, "independent_review": "pending", "solver_materials": "公开题面及中性环境说明；本目录的测试、gold、候选、分析均为私有"
    })
    if statement is not None:
        (out / "effective_statement.txt").write_bytes(statement.encode("utf-8"))
        save_json(out / "statement_revision.json", {
            "parent_problem_statement_sha256": pub["problem_statement_sha256"],
            "effective_problem_statement_sha256": sha(statement.encode("utf-8")),
            "change": "保留原题面字节，在末尾补最低诊断行为；不写隐藏实例或异常措辞",
            "fresh_public_reader": "pending", "actual_prompt_delivery": "pending"
        })
    for name, candidate in (candidate_patches or {}).items():
        (out / (name + ".patch")).write_bytes(candidate)
    save_json(result_path, {
        "schema": "dask_task_result_preparation.v1", "instance_id": pub["instance_id"], "revision_id": version,
        "current_checks": {"source_public_hash": "pass", "original_test_matches_grading": "pass",
                           "patch_apply_against_exported_base": "pass", "effective_python_ast": "pass"},
        "verification_scope": "本机离线字节、补丁上下文和语法检查；没有导入 Dask、运行 pytest 或使用远端机器",
        "cpu_formal_acceptance": "pending", "actor_development": "pending_or_inherited_only",
        "independent_acceptance": "pending", "model_probe": "not_submitted", "new_reward_rows": []
    })
    return out


def prepare_7138() -> None:
    public, private, _, _ = source(7138)
    path = "dask/array/tests/test_routines.py"
    base = read(public / "base" / path)
    effective = apply_to_file(base.encode(), path, (private / "test.patch").read_bytes()).decode()
    effective = replace_once(effective,
        '    assert isinstance(da.ravel([(0,), (0,)]), da.core.Array)\n',
        '    assert isinstance(da.ravel([(0,), (0,)]), da.core.Array)\n'
        '\n    values = [[1, -2], [3, 4]]\n'
        '    result = da.ravel(values)\n'
        '    assert isinstance(result, da.core.Array)\n'
        '    assert_eq(result, np.ravel(values))\n')
    marker = '\n\n@pytest.mark.parametrize("is_func", [True, False])\n@pytest.mark.parametrize("axis", [None, 0, -1, (0, -1)])\ndef test_squeeze'
    keyword_test = '\n\ndef test_ravel_keyword_array():\n    # 既有公开签名为 ravel(array)，增加转换时仍须兼容关键字调用。\n    values = np.arange(6).reshape((2, 3))\n    array = da.from_array(values, chunks=(1, 3))\n    result = da.ravel(array=array)\n    assert isinstance(result, da.core.Array)\n    assert_eq(result, np.ravel(values))\n'
    effective = replace_once(effective, marker, keyword_test + marker)
    code_path = "dask/array/routines.py"
    old_code = read(public / "base" / code_path)
    code = replace_once(old_code, 'def ravel(array):\n    return array.reshape((-1,))',
                        'def ravel(array):\n    return asanyarray(array).reshape((-1,))')
    save_task(7138, path, effective, version="dask7138-array-keyword-v1", requested="replace_test_patch_append_p2p",
              reason="保留 array-like F2P，增加非零展开控制；旧 array= 调用作为 P2P；gold 按实际兼容性失败留档。",
              added_p2p=[path + "::test_ravel_keyword_array"],
              candidate_patches={"compatible_ravel": make_patch(code_path, old_code, code)})


def prepare_7656() -> None:
    public, private, _, _ = source(7656)
    path = "dask/tests/test_delayed.py"
    base = read(public / "base" / path)
    effective = apply_to_file(base.encode(), path, (private / "test.patch").read_bytes()).decode()
    effective = replace_once(effective,
        '"ADataClass", [("a", int), ("b", int, dataclasses.field(init=False))]',
        '"ADataClass",\n        [("a", int, dataclasses.field(default=3)),\n         ("b", int, dataclasses.field(init=False))]')
    effective = replace_once(effective, '    def return_nested(obj):\n        return obj["a"].a',
        '    def return_nested(obj):\n        # 检查 delayed 函数实际收到的参数类型和值。\n'
        '        assert isinstance(obj["a"], ADataClass)\n        assert obj["a"].a == 3\n        return obj["a"].a')
    effective = replace_once(effective, '    assert final.compute() == 3\n',
        '    assert final.compute(scheduler="sync") == 3\n'
        '\n    with_default = dask.delayed({"a": ADataClass()})\n'
        '    assert delayed(return_nested)(with_default).compute(scheduler="sync") == 3\n')
    save_task(7656, path, effective, version="dask7656-dataclass-argument-v1", requested="replace_test_patch",
              reason="在既有 F2P 检查被调用函数实际收到的 dataclass 类型、默认字段与嵌套 Delayed 求值；不扩大 init=False 已存在字段的状态恢复目标。")


def prepare_9378() -> None:
    public, private, _, _ = source(9378)
    path = "dask/array/tests/test_masked.py"
    base = read(public / "base" / path)
    effective = apply_to_file(base.encode(), path, (CLOUD / "dask9378/revised_test_v1.patch").read_bytes()).decode()
    effective = replace_once(effective, '    da_func = getattr(da.ma, funcname)\n',
        '    # 用户已选择 B：已有 ma 入口必须正确，缺失时接受顶层入口。\n'
        '    # 不要求实现新的 API。\n'
        '    da_func = getattr(da.ma, funcname) if hasattr(da.ma, funcname) else getattr(da, funcname)\n')
    code_path = "dask/array/ma.py"
    old_code = read(public / "base" / code_path)
    code = apply_to_file(old_code.encode(), code_path, (private / "gold.patch").read_bytes()).decode()
    code += ('\n\ndef _like_values_seven(block):\n'
             '    return np.ma.array(np.full(block.shape, 7, dtype=block.dtype),\n'
             '                       mask=np.ma.getmaskarray(block))\n'
             '\n\ndef ones_like(a, **kwargs):\n'
             '    return asanyarray(a).map_blocks(_like_values_seven, **kwargs)\n'
             '\n\ndef zeros_like(a, **kwargs):\n'
             '    return asanyarray(a).map_blocks(_like_values_seven, **kwargs)\n')
    ast.parse(code, filename=code_path)
    save_task(9378, path, effective, version="dask9378-mask-route-b-v1", requested="replace_test_patch",
              reason="执行用户 09-30 选 B；三种 like 都逐元素比较 mask，ones/zeros 保留值比较；不改题面，不沿用旧强制 ma API 的 R-f。",
              candidate_patches={"wrong_values_seven": make_patch(code_path, old_code, code)})


def prepare_7305() -> None:
    public, _, _, _ = source(7305)
    path = "dask/dataframe/tests/test_shuffle.py"
    base = read(public / "base" / path)
    effective = apply_to_file(base.encode(), path, (CLOUD / "dask7305/revised_test_v2.patch").read_bytes()).decode()
    old = ('    qs = partition_quantiles(ddf.x, npartitions=npartitions_out).compute()\n'
           '    assert qs.dtype == np.dtype(dtype)\n    got = [int(v) for v in qs]\n'
           '    assert got[0] == lo\n    assert got[-1] == hi\n    assert got == sorted(got)\n')
    effective = replace_once(effective, old,
        '    # "auto" 属于 set_index；partition_quantiles 的分区数须为整数。\n'
        '    if npartitions_out != "auto":\n' + ''.join('    ' + line for line in old.splitlines(keepends=True)))
    effective = replace_once(effective,
        '    _assert_exact_int_divisions([-big - 997 * k for k in order], "int64", 4, 4)\n',
        '    _assert_exact_int_divisions([-big - 997 * k for k in order], "int64", 4, 4)\n'
        '\n    # 复用独立观察到的 auto 失败实例，最小值置于末尾输入分区。\n'
        '    # 不锁定近似的内部分界。\n'
        '    auto_values = [big + int(k) * 997 for k in np.random.RandomState(0).permutation(1000)]\n'
        '    i = auto_values.index(min(auto_values))\n'
        '    auto_values[i], auto_values[-1] = auto_values[-1], auto_values[i]\n'
        '    _assert_exact_int_divisions(auto_values, "uint64", 4, "auto")\n')
    code_path = "dask/dataframe/shuffle.py"
    old_code = read(public / "base" / code_path)
    code = replace_once(old_code, '            try:\n                divisions = np.interp(\n',
        '            try:\n                if pd.api.types.is_integer_dtype(index2.dtype):\n'
        '                    # 内部分界允许近似；从精确整数摘要中取值，\n'
        '                    # 避免先转换为浮点数而损失端点精度。\n'
        '                    indexes = np.linspace(0, n - 1, npartitions + 1).astype(int)\n'
        '                    divisions = [divisions[i] for i in indexes]\n'
        '                else:\n                    divisions = np.interp(\n')
    # 仅把原 np.interp 的参数和函数体缩进到新 else 分支。
    interp_tail = ('                    x=np.linspace(0, n - 1, npartitions + 1),\n'
                   '                    xp=np.linspace(0, n - 1, n),\n'
                   '                    fp=divisions,\n                ).tolist()\n')
    code = replace_once(code, interp_tail, ''.join('    ' + line for line in interp_tail.splitlines(keepends=True)))
    ast.parse(code, filename=code_path)
    candidate = (CLOUD / "dask7305/candidates/gold_full.patch").read_bytes() + make_patch(code_path, old_code, code)
    save_task(7305, path, effective, version="dask7305-exact-ends-auto-v3", requested="replace_test_patch",
              reason="保留 v2 的七个大整数控制，补已证同一 set_index 行归属要求的 auto 路径；旧三份正对照的核实范围不能覆盖新路径。",
              candidate_patches={"gold_full_auto": candidate})


def prepare_8801() -> None:
    public, private, pub, _ = source(8801)
    path = "dask/tests/test_config.py"
    base = read(public / "base" / path)
    effective = read(CLOUD / "dask8801/test_config_revised_v5.py")
    effective = replace_once(effective, '    for content in [b"", b"# x: 1\\n"]:',
                              '    for content in [b"", b"# x: 1\\n", b"null\\n", b"---\\n"]:')
    effective = replace_once(effective,
        '    for content, type_name in [(b"[1234]", "list"), (b"hello", "str"), (b"1234", "int")]:',
        '    # 同一文件和加载器产生语法错误诊断作为对照。\n'
        '    # 非映射错误须有不同诊断，或展示额外且不同的原因；\n'
        '    # 不依赖英文同义词表。这仍需独立接受性核查。\n'
        '    with open(fil_path, mode="wb") as f:\n        f.write(b"{")\n'
        '    syntax_header = str(_collect_yaml_error([fil_path]))\n'
        '\n    for content in [b"[1234]", b"hello", b"1234", b"1.5"]:')
    effective = replace_once(effective,
        '            msg = str(_collect_yaml_error(paths))\n            assert fil_path in msg\n'
        '            assert other_path not in msg\n            rest = msg.replace(fil_path, "").lower()\n'
        '            assert any(w in rest for w in ("dict", "map", "key", "object", type_name))\n',
        '            err = _collect_yaml_error(paths)\n            msg = str(err)\n'
        '            assert fil_path in msg\n            assert other_path not in msg\n'
        '            cause = err.__cause__\n'
        '            if cause is None and not err.__suppress_context__:\n                cause = err.__context__\n'
        '            has_distinct_cause = cause is not None and bool(str(cause)) and str(cause) != msg\n'
        '            assert msg != syntax_header or has_distinct_cause\n')
    # 追加原参考名单遗漏的既有权限测试，把内容错误与权限回归分开记录。
    # 正式执行必须使用非 root 身份。
    extra = [path + "::test_collect_yaml_permission_errors[directory]", path + "::test_collect_yaml_permission_errors[file]"]
    statement = pub["problem_statement"] + (
        '\n\nExpected behavior: when the contents of a Dask configuration file cannot be used as configuration '
        '(for example, they are not valid YAML, or their top level is not a mapping of keys to values), '
        'loading the configuration, including `import dask`, should fail with an error that names the '
        'offending file and explains the problem. Files that cannot be read are still ignored, and '
        'empty configurations remain valid.\n')
    code_path = "dask/config.py"
    old_code = read(public / "base" / code_path)
    words = apply_to_file(old_code.encode(), code_path, (private / "gold.patch").read_bytes()).decode()
    words = replace_once(words,
        '            f"A dask config file at {path!r} is malformed - config files must have "\n'
        '            f"a dict as the top level object, got a {type(config).__name__} instead"',
        '            f"The contents of {path!r} cannot be used: expected a collection of named values."')
    wrong_reason = replace_once(words,
        '            f"The contents of {path!r} cannot be used: expected a collection of named values."',
        '            f"Cannot load {path!r}: the configuration file does not exist."')
    save_task(8801, path, effective, version="dask8801-diagnostics-v6-draft", requested="replace_test_patch_append_p2p_statement_replace",
              reason="v5 上补 float/null/文档分隔符，复用公开权限 P2P；撤原因词表，使用语法/非映射诊断区分草案。诊断区别不是自然语言语义判定，必须核接受性及错因反例后才能采用。",
              added_p2p=extra, statement=statement,
              candidate_patches={"reasonable_named_values": make_patch(code_path, old_code, words),
                                 "wrong_missing_file_reason": make_patch(code_path, old_code, wrong_reason)})


def main() -> None:
    # 先检查全部题，避免中途发现证据后留下部分已重写的材料。
    for task in (7138, 7656, 9378, 7305, 8801):
        p = HERE / "tasks" / f"dask__dask-{task}" / "results.json"
        if p.exists():
            value = json.loads(read(p))
            if (value.get("new_reward_rows") or value.get("cpu_formal_acceptance") != "pending"
                    or value.get("isolated_config_api_check") or value.get("image_preparation")):
                raise ValueError(f"{task} 已有行为/准备/评分证据；本脚本只初始化草案，不能覆盖已有证据")
    for fn in [prepare_7138, prepare_7656, prepare_9378, prepare_7305, prepare_8801]:
        fn()
    print("prepared 5 drafts; patch context and Python AST checked; no Dask imports or CPU acceptance")


if __name__ == "__main__":
    main()
