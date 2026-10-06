"""仅生成 coveragepy 独占草案，不发布修订单、不运行容器或项目代码。"""

from pathlib import Path
import difflib
import hashlib
import json

from repoharness2.envpack.ingest_r2e_subset import R2E_MATERIAL_REVISIONS_SCHEMA_ID

BASE = Path(__file__).resolve().parent
REPO = next(p for p in BASE.parents if (p / "rh2/src/repoharness2").is_dir())
EXEC = Path("docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution")
REGISTRY = Path("docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/material_revisions_v11.json")
PUB = Path("runs/r2e_static_prep_20260924/v3/public")
PRIV = Path("runs/r2e_static_prep_20260924/v3/private")
CLOUD = Path("rh2/experiments/category3_cloud_20260929")
FUTURE = Path("docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/coveragepy_20261003_draft_v1")
IDS = {s: "coveragepy__" + h for s, h in {
    "016af5f6": "016af5f6352d69206ac8f7537c2b18828767bcae",
    "5dbbe143": "5dbbe1430c16fe15b553e6909be8be5f2b9b71b9",
    "ea6906b0": "ea6906b092d9bb09285094eee94e322d2cb413a5",
    "f5eb5f21": "f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96",
}.items()}


def digest(body):
    return "sha256:" + hashlib.sha256(body).hexdigest()


def read(path):
    return (REPO / path).read_bytes()


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def material(short, name, body):
    path = BASE / "tasks" / IDS[short] / "materials" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return path


def revision(short, number, kind, target, old, new, dest=None, decision=None, reason=""):
    record = {
        "revision_id": f"r2e-mr-{number:03d}", "instance_id": IDS[short],
        "kind": kind, "target": target,
        "edits": [{"old": old.decode(), "new": new.decode()}]
        if kind in ("hidden_test_text_replace", "statement_text_replace") else None,
        "sha256_before": digest(old) if old is not None else None,
        "sha256_after": digest(new),
        "revised_file": str(FUTURE / IDS[short] / dest.name) if dest else None,
        "expected_change": None,
        "decision_ref": decision or "统一处理标准 v1 §5 的既有题级修订授权；本条为未发布草案",
        "reason": reason,
        "evidence": [str(EXEC / "category2_repair_20260929/remaining_workflow_20261002.md")],
    }
    if kind == "expected_file_replace":
        before, after = json.loads(old), json.loads(new)
        record["expected_change"] = {
            "changed": {k: [before[k], after[k]] for k in before if k in after and before[k] != after[k]},
            "added": {k: v for k, v in after.items() if k not in before},
            "removed": [k for k in before if k not in after],
        }
    evidence = EXEC / "category3_diagnosis_20260929/tasks" / IDS[short]
    if (REPO / evidence / "result.md").exists():
        record["evidence"].append(str(evidence / "result.md"))
    if (REPO / evidence / "review.md").exists():
        record["evidence"].append(str(evidence / "review.md"))
    if short == "ea6906b0":
        record["evidence"].append(str(EXEC / "category2_repair_20260929/r2e/r2e_inventory.md"))
    record["evidence"].append(str((BASE / "tasks" / IDS[short] / "card.md").relative_to(REPO)))
    return record


def main():
    parent_bytes = read(REGISTRY)
    parent = json.loads(parent_bytes)
    entries = {s: [] for s in IDS}
    s = "016af5f6"
    body = read(CLOUD / "cov016/hidden_test_1_revised_v2.py")
    path = material(s, "test_1_v2.py", body)
    entries[s].append(revision(s, 901, "hidden_test_text_replace", "test_1.py",
        read(PRIV / IDS[s] / "hidden_tests/test_1.py"), body, path,
        reason="R-c：直接采用独立复核通过的 v2；保留可编码文件数据，允许跳过和转义两类正确路线。"))
    for s, number, filename, output, decision in [
        ("016af5f6", 902, "cov016/revised_statement_v1.txt", "statement_v1.txt", None),
        ("5dbbe143", 903, "cov5dbbe/revised_statement_A.txt", "statement_A.txt",
         "用户 2026-09-29 已选 A：按 slug；见本题云端 result.md §6。"),
    ]:
        body = read(CLOUD / filename)
        material(s, output, body)
        public = json.loads(read(PUB / IDS[s] / "public_bundle.json"))["row"]
        entries[s].append(revision(s, number, "statement_text_replace", "problem_statement",
            public["problem_statement"].encode(), body, decision=decision,
            reason="R-f：直接采用已有窄题面修订；不改变无关要求。"))

    s = "f5eb5f21"
    decision = "用户 2026-09-30 已选 A：每文件 summary 可带成对且正确的分支计数；采用复核 R-b v3。"
    for number, kind, target, source, output, oldpath in [
        (904, "hidden_test_text_replace", "test_1.py", "test_1_rb3h.py", "test_1_rb3h.py", "hidden_tests/test_1.py"),
        (905, "expected_file_replace", "expected_output_json", "expected_rc3.json", "expected_v3.json", "expected_output.json"),
    ]:
        body = read(CLOUD / "cov_f5eb/review/materials" / source)
        path = material(s, output, body)
        entries[s].append(revision(s, number, kind, target, read(PRIV / IDS[s] / oldpath), body,
            path, decision, "R-b/R-c v3：直接采用复核文件；替换 053/054，不叠加同目标修订。"))

    s = "ea6906b0"
    old = read(PRIV / IDS[s] / "hidden_tests/test_1.py")
    oldblock = '''    def open(self, filename, mode="r"):
        """Be just like `open`, but write written file names to `self.written`."""
        if mode.startswith("w"):
            self.written.add(filename.replace('\\\\', '/'))
        return open(filename, mode)
'''.encode()
    newblock = oldblock.replace(b'def open(self, filename, mode="r"):',
        b'def open(self, filename, mode="r", *args, **kwargs):').replace(
        b'return open(filename, mode)', b'return open(filename, mode, *args, **kwargs)')
    assert old.count(oldblock) == 1
    body = old.replace(oldblock, newblock, 1)
    path = material(s, "test_1_open_args_v1.py", body)
    entries[s].append(revision(s, 906, "hidden_test_text_replace", "test_1.py", old, body, path,
        reason="R-b：私有 FileWriteTracker 转交真实 open 的其它参数；保留原写入和 HTML 行为断言。"))
    formal = Path("docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/revisions/files") / IDS[s]
    old = read(formal / "r2e_tests/test_2.py").decode()
    addition = '''
    def test_existing_gitignore_is_preserved_and_report_ignored(self):
        # 接续当前清单：保留用户内容，同时用真实 git 核对新报告。
        init = run_git("init", "-q", ".")
        assert init.returncode == 0, init.stderr
        self.make_file("main_file.py", "a = 1\\n")
        os.makedirs("report_out")
        prior = b"# User-owned rules\\ncustom.tmp\\n"
        path = os.path.join("report_out", ".gitignore")
        with open(path, "wb") as stream:
            stream.write(prior)
        cov = coverage.Coverage()
        self.start_import_stop(cov, "main_file")
        for _ in range(2):
            cov.html_report(directory="report_out")
            with open(path, "rb") as stream:
                assert prior in stream.read(), "Existing user .gitignore content was lost"
            assert os.path.exists(os.path.join("report_out", "index.html"))
            status = run_git("status", "--porcelain", "--untracked-files=all", "--", "report_out")
            assert status.returncode == 0, status.stderr
            not_ignored = sorted(
                line[3:] for line in status.stdout.splitlines()
                if line[3:] != "report_out/.gitignore"
            )
            assert not_ignored == [], status.stdout

'''
    marker = "\n\nclass ReportingTest(CoverageTest):"
    assert old.count(marker) == 1
    body = old.replace(marker, "\n" + addition + marker, 1).encode()
    path = material(s, "test_2_preserve_v1.py", body)
    entries[s].append(revision(s, 907, "hidden_test_file_add", "test_2.py", None, body, path,
        reason="R-c：保留已验两条断言，加已有内容及真实忽略效果；替换 036，待独立核查和正式矩阵。"))
    expected = json.loads(read(formal / "expected_output.json"))
    expected["HtmlGitignoreTest.test_existing_gitignore_is_preserved_and_report_ignored"] = "PASSED"
    body = (json.dumps(expected, ensure_ascii=False, indent=2) + "\n").encode()
    path = material(s, "expected_v1.json", body)
    entries[s].append(revision(s, 908, "expected_file_replace", "expected_output_json",
        read(PRIV / IDS[s] / "expected_output.json"), body, path,
        reason="原始 46 键直接变为 49 键；保留先前两条，增加一条；替换 037。"))
    source = read(PUB / IDS[s] / "worktree/coverage/html.py").decode()
    anchor = "        # The user may have extra CSS they want copied.\n"
    for name, encoding in [("safe_append", False), ("safe_append_encoding", True)]:
        call = 'open(os.path.join(self.directory, ".gitignore"), "a"' + (', encoding="utf-8"' if encoding else '') + ')'
        block = '        # Preserve user rules while ignoring generated report files.\n        with ' + call + ' as fgi:\n            fgi.write("\\n# Created by coverage.py\\n*\\n")\n\n'
        assert source.count(anchor) == 1
        updated = source.replace(anchor, block + anchor, 1)
        path = BASE / "tasks" / IDS[s] / "candidates" / (name + ".patch")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(''.join(difflib.unified_diff(source.splitlines(keepends=True),
            updated.splitlines(keepends=True), fromfile="a/coverage/html.py", tofile="b/coverage/html.py")))

    for s, iid in IDS.items():
        folder = BASE / "tasks" / iid
        replaced = {"f5eb5f21": ["r2e-mr-053", "r2e-mr-054"], "ea6906b0": ["r2e-mr-036", "r2e-mr-037"]}.get(s, [])
        public = json.loads(read(PUB / iid / "public_bundle.json"))["row"]
        dump(folder / "revision_draft.json", {
            "schema_id": R2E_MATERIAL_REVISIONS_SCHEMA_ID,
            "purpose": "未发布草案；901–908 仅供本包静态验证，非正式编号、未预约编号。",
            "revisions": entries[s],
        })
        dump(folder / "results_manifest.json", {
            "schema": "coveragepy.preparation.v1", "as_of": "2026-10-03", "instance_id": iid,
            "owner_thread_id": "01a0fd63-c159-7331-b391-d78dd853ec75",
            "status": "draft_not_published_not_cpu_verified",
            "parent_registry": str(REGISTRY), "parent_registry_sha256": digest(parent_bytes),
            "retained_revision_ids": [r["revision_id"] for r in parent["revisions"] if r["instance_id"] == iid and r["revision_id"] not in replaced],
            "replace_revision_ids": replaced,
            "provisional_revision_ids": [r["revision_id"] for r in entries[s]],
            "publication_files": {r["revised_file"]: str((folder / "materials" / Path(r["revised_file"]).name).relative_to(REPO)) for r in entries[s] if r["revised_file"]},
            "source_image": public["image"], "source_image_manifest_digest": public["image_manifest_digest"],
            "source_base_commit": public["base_commit"],
            "public_bundle": str(PUB / iid / "public_bundle.json"),
            "public_bundle_sha256": digest(read(PUB / iid / "public_bundle.json")),
            "materials": [{"path": str(p.relative_to(REPO)), "sha256": digest(p.read_bytes())} for p in sorted((folder / "materials").glob("*"))],
            "cpu_acceptance": {"status": "not_run_waiting_for_user_machine"},
            "independent_review": {"status": "prior_reviews_reused_new_deltas_not_reviewed"},
            "probe_submission": {"status": "not_submitted"},
        })
        parts = []
        for r in entries[s]:
            for edit in r["edits"] or []:
                parts.extend(difflib.unified_diff(edit["old"].splitlines(keepends=True),
                    edit["new"].splitlines(keepends=True), fromfile="source/" + r["target"], tofile="draft/" + r["target"]))
        (folder / "material_changes.diff").write_text(''.join(parts))
    assert read(REGISTRY) == parent_bytes
    print("Prepared 4 unpublished task drafts, 8 provisional revision entries; shared registry unchanged.")


if __name__ == "__main__":
    main()
