"""只重建 8801 v7；显式保留 v6 原件与已完成证据，不调用总初始化脚本。"""
import ast
import json
from pathlib import Path

from prepare_materials import HERE, ROOT, apply_to_file, make_patch, rel, sha, save_json


def main():
    out = HERE / "tasks/dask__dask-8801"
    if (out / "revision.json").exists():
        current = json.loads((out / "revision.json").read_text())
        if current.get("revision_id") == "dask8801-behavior-semantic-v7-compat1":
            raise ValueError("当前已采用假值双分支材料；本历史v7生成器不得覆盖新版，使用固定有效补丁及当前revision")
    historical = out / "history/dask8801-diagnostics-v6-draft_20261003"
    manifest = json.loads((historical / "manifest.json").read_text())
    # 历史正文只读。当前结果/计划可保留续作记录。
    old_test = (historical / "effective_test.py").read_text()
    assert sha(old_test.encode()) == "cd8d5ed48d7e45579acd58f5266b3a26e5d329615e45730f86c85d9c73abac45"
    protocol = (HERE / "tools/config_diagnostic_protocol.py").read_text()
    tree = ast.parse(protocol)
    names = {"visible_exception", "encode_marker", "decode_markers", "file_fact", "alias_diagnostic", "emit_diagnostic"}
    definitions = "\n\n".join(ast.get_source_segment(protocol, n) for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in names)
    imports = "import base64\nimport builtins\nimport hashlib\nimport json\nimport re\n"
    declarations = '\nDIAGNOSTIC_PREFIX = "RH2_DASK8801_DIAGNOSTIC_V1:"\nIMPORT_PREFIX = "RH2_DASK8801_IMPORT_EXCEPTION_V1:"\n'
    start = old_test.index("def _displayed_error(")
    end = old_test.index("\ndef test_env():", start)
    # 子进程使用同一可见消息采集实现；原始 traceback 仍由 sys.__excepthook__ 保留。
    collector = ast.get_source_segment(protocol, next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "visible_exception"))
    encoder = ast.get_source_segment(protocol, next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "encode_marker"))
    import_program = "import sys, base64, builtins, json\n" + collector + "\n\n" + encoder + '''
def trusted_exception_hook(kind, exc, tb):
    sys.__excepthook__(kind, exc, tb)
    print(encode_marker("RH2_DASK8801_IMPORT_EXCEPTION_V1:", visible_exception(exc)), file=sys.stderr)
sys.excepthook = trusted_exception_hook
import dask
'''
    targets = '''
def _collect_yaml_error(paths):
    with pytest.raises(Exception) as rec:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            collect_yaml(paths=paths)
    return rec.value


def test_collect_yaml_malformed_file(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")
    other_path = os.path.join(dir_path, "b.yaml")
    os.mkdir(os.path.join(dir_path, "0.yaml"))
    with open(other_path, "wb") as f:
        f.write(b"x: 1\\n")
    for fixture, content in [("syntax_brace", b"{"), ("syntax_tab", b"a: 1\\n\\tb: 2\\n")]:
        with open(fil_path, "wb") as f:
            f.write(content)
        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(content.decode())
        for entry, paths in [("directory", [dir_path]), ("file", [fil_path])]:
            before = file_fact(fil_path)
            err = _collect_yaml_error(paths)
            emit_diagnostic(fixture, entry, fil_path, other_path, before, visible_exception(err))


def test_collect_yaml_no_top_level_dict(tmpdir):
    dir_path = str(tmpdir)
    fil_path = os.path.join(dir_path, "a.yaml")
    other_path = os.path.join(dir_path, "b.yaml")
    os.mkdir(os.path.join(dir_path, "0.yaml"))
    with open(other_path, "wb") as f:
        f.write(b"x: 1\\n")
    for content in [b"", b"# x: 1\\n", b"null\\n", b"---\\n"]:
        with open(fil_path, "wb") as f:
            f.write(content)
        assert merge(*collect_yaml(paths=[dir_path])) == {"x": 1}
    for fixture, content in [("nonmapping_list", b"[1234]"), ("nonmapping_str", b"hello"),
                             ("nonmapping_int", b"1234"), ("nonmapping_float", b"1.5")]:
        with open(fil_path, "wb") as f:
            f.write(content)
        for entry, paths in [("directory", [dir_path]), ("file", [fil_path])]:
            before = file_fact(fil_path)
            err = _collect_yaml_error(paths)
            emit_diagnostic(fixture, entry, fil_path, other_path, before, visible_exception(err))

    with open(fil_path, "wb") as f:
        f.write(b"hello")
    before = file_fact(fil_path)
    env = dict(os.environ, DASK_CONFIG=dir_path,
               DASK_ROOT_CONFIG=os.path.join(dir_path, "no-such-dir"),
               HOME=os.path.join(dir_path, "no-such-home"))
    proc = subprocess.run([sys.executable, "-c", IMPORT_CAPTURE_PROGRAM], env=env,
                          capture_output=True, text=True, timeout=120)
    assert proc.returncode != 0
    # 打印原始 stderr 以供运行审计，宿主仅将封包的可见消息送语义裁决。
    print("RH2_DASK8801_RAW_IMPORT_STDERR_BEGIN")
    for line in proc.stderr.splitlines():
        print("RAW_IMPORT | " + line)
    print("RH2_DASK8801_RAW_IMPORT_STDERR_END")
    diagnostics, issues = decode_markers(proc.stderr, IMPORT_PREFIX)
    diagnostic = diagnostics[0] if len(diagnostics) == 1 and not issues else {
        "visible_exception": None, "capture_issues": issues + ["import_exception_packet_missing_or_duplicated"]}
    emit_diagnostic("nonmapping_str", "import", fil_path, other_path, before, diagnostic)

'''
    # 原有 P2P、两项权限检查不改。行为断言与诊断侧裁决分别记录。
    new_test = imports + old_test[:start].replace("import traceback\n", "") + declarations + "\n" + definitions + "\n\nIMPORT_CAPTURE_PROGRAM = " + repr(import_program) + "\n" + targets + old_test[end:]
    ast.parse(new_test)
    old_revision = json.loads((historical / "revision.json").read_text())
    base_path = ROOT / old_revision["source_artifacts"]["base_test_file"]["path"]
    base = base_path.read_bytes()
    patch = make_patch("dask/tests/test_config.py", base.decode(), new_test)
    assert apply_to_file(base, "dask/tests/test_config.py", patch) == new_test.encode()
    (out / "effective_test.py").write_text(new_test)
    (out / "effective_test.patch").write_bytes(patch)
    revision = dict(old_revision)
    revision.update(state="draft_behavior_capture_semantic_validation_pending", revision_id="dask8801-behavior-semantic-v7",
                    reason="保留公开目标和原行为回归；确定性行为验收与受信可见诊断独立语义裁决分别记录。仅题级诊断，未授权自动训练 reward。",
                    independent_review="pending_v7_collector_and_material_review", diagnostic_rule_acceptance="pending_fixed_judge_controls_and_holdout",
                    effective_test_patch={"path": rel(out / "effective_test.patch"), "sha256": sha(patch)},
                    effective_test_file={**old_revision["effective_test_file"], "effective_sha256": sha(new_test.encode())})
    revision["diagnostic_side_policy"] = {
        "authorization": "overnight_watch_20261003.md#dask-8801-的题级裁定",
        "automatic_training_reward_authorized": False, "raw_behavior_score_separate": True,
        "semantic_judge_prompt": {"path": rel(out / "semantic_judge_prompt_v2.txt"), "sha256": sha((out / "semantic_judge_prompt_v2.txt").read_bytes())},
        "collector_protocol": {"path": rel(HERE / "tools/config_diagnostic_protocol.py"), "sha256": sha(protocol.encode())},
        "required_full_cases": 13, "missing_capture": "needs_evidence", "uncertain_or_service_failure": "needs_review",
        "no_new_solver_output_fields": True, "v6_known_false_accept_not_adopted": True,
    }
    save_json(out / "revision.json", revision)
    matrix = json.loads((historical / "acceptance_matrix.json").read_text())
    matrix.update(schema="dask_behavior_semantic_acceptance_plan.v2", revision_id=revision["revision_id"],
                  effective_test_patch=revision["effective_test_patch"], automatic_training_reward_authorized=False,
                  prior_material_version="dask8801-diagnostics-v6-draft")
    behavior_bad = {"noop", "rv_enum_types", "wr_null_raises", "wr_perm_fatal", "oserr_fatal", "import_swallow", "rv_import_warn", "wr_import_only"}
    for row in matrix["rows"]:
        old_expected = row.pop("expected_reward")
        row["historical_v6_expected_reward"] = old_expected
        row["expected_raw_behavior_score"] = 0 if row["name"] in behavior_bad else 1
        row["expected_diagnostic_outcome"] = "pending_actual_parser_equivalence" if old_expected is None else ("pass_diagnostic_goal" if old_expected == 1 else "fail")
        row["observed_raw_behavior_score"] = None
        row["observed_semantic_verdict"] = None
        row["observed_diagnostic_outcome"] = None
        row.pop("observed_reward_on_this_revision", None)
        row["expectations_scope"] = "hypotheses_not_observed_scores_not_automatic_training_reward"
        if row["name"] == "parsererror_only":
            row["reason"] = "ScannerError 仍抛出，所以预计原始行为分1；其可见消息未指名坏文件，应由语义裁决拒绝，不混作未抛错"
    matrix["success_conditions"] = [
        "冻结正式 consumer、材料、镜像、配方及真正非 root 身份；F2P/P2P 逐项在场且执行完整",
        "确定性行为与语义裁决分别留证；行为分1不代表公开错误解释目标通过",
        "固定 prompt/config 的新鲜非作者判定通过已知正负和未调试留出控制；每份实际模型候选独立裁决",
        "已知 wrong_missing_file_reason 即使行为分1也必须语义拒绝；合理改写/异常链/类不误拒",
        "封包缺失 needs_evidence；uncertain 或服务失败 needs_review，不默认0/1，不丢样本",
        "题级诊断通过不授予自动训练 reward；保留原始诊断、裁决引用、SHA、清理与非作者验收",
    ]
    save_json(out / "acceptance_matrix.json", matrix)
    print(json.dumps({"revision": revision["revision_id"], "test_sha256": sha(new_test.encode()), "patch_sha256": sha(patch), "matrix_rows": len(matrix["rows"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
