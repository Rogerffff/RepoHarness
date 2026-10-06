"""09-25 reserve20-only static exporter; first12 is outside all read/write targets. Stdlib and read-only Git; no project import."""
from __future__ import annotations
import argparse, ast, hashlib, json, os, stat, subprocess, tarfile, sys
from types import SimpleNamespace
from pathlib import Path
ROOT=Path("/Users/roger/Desktop/claude-code-verl-stage0h")
HERE=Path(__file__).resolve().parent
def validate_public(row: dict) -> SimpleNamespace:
    fields = {"allowed_tools", "base_commit", "image", "image_manifest_digest", "instance_id",
              "problem_statement", "problem_statement_sha256", "public_hints", "repo", "schema_id", "workdir"}
    if set(row) != fields or row["schema_id"] != "rh2.public_task_bundle.v1":
        raise ValueError("public字段或schema不符")
    if row["problem_statement_sha256"] != "sha256:" + sha(row["problem_statement"].encode()):
        raise ValueError("题面hash不符")
    return SimpleNamespace(**row)

def render_user_prompt(public: SimpleNamespace) -> str:
    return (
        f"Fix the following issue from the `{public.repo}` repository "
        f"(checked out at {public.workdir}, commit {public.base_commit[:12]}):\n\n"
        f"{public.problem_statement}"
    )

def verify_prompt_template() -> None:
    """只解析AST，不导入/执行项目函数；对拍返回表达式。"""
    current = ast.parse((ROOT / "rh2/src/repoharness2/envpack/bundles.py").read_text())
    local = ast.parse(Path(__file__).read_text())
    returns = []
    for module in (current, local):
        func = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == "render_user_prompt")
        returns.append(ast.dump(next(n for n in func.body if isinstance(n, ast.Return)), include_attributes=False))
    if returns[0] != returns[1]:
        raise ValueError("当前prompt模板已变化；保留缺口，不导入项目或静默改写")

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        handle.write(json.dumps(value, ensure_ascii=False, indent=2) + "\n")

def task_id(row: dict) -> str:
    return row["instance_id"].split("::")[-1]

def git(clone: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(clone), *args])

def verify_base(clone: Path, commit: str, destination: Path, exported: dict) -> dict:
    """从磁盘重读全部文件，逐个对拍精确Git blob OID、执行位和路径集合。"""
    entries = git(clone, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    inventory, expected_paths, executable = [], set(), 0
    expected_gitlinks, expected_symlinks, expected_lfs = [], [], []
    for entry in entries:
        if not entry:
            continue
        metadata, raw_name = entry.split(b"\t", 1)
        mode, kind, oid = metadata.split()
        name = raw_name.decode("utf-8")
        path = destination / name
        if mode == b"160000" and kind == b"commit":
            expected_gitlinks.append({"path": name, "commit": oid.decode(),
                                      "status": "contents_not_materialized"})
            if path.exists() or path.is_symlink():
                raise ValueError(f"gitlink 不应伪造内容: {name}")
            continue
        if kind != b"blob":
            raise ValueError(f"未支持对象: {name}")
        if mode == b"120000":
            if not path.is_symlink():
                raise ValueError(f"符号链接未保留: {name}")
            data = os.readlink(path).encode()
            expected_symlinks.append(name)
        else:
            if not path.is_file() or path.is_symlink():
                raise ValueError(f"文件类型不符: {name}")
            data = path.read_bytes()
            actual_mode = stat.S_IMODE(path.stat().st_mode)
            expected_mode = 0o755 if mode == b"100755" else 0o644
            if actual_mode != expected_mode:
                raise ValueError(f"执行位/权限不符: {name} {actual_mode:o}")
            executable += int(mode == b"100755")
        actual_oid = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if actual_oid != oid.decode():
            raise ValueError(f"磁盘字节与base Git blob不符: {name}")
        if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
            expected_lfs.append(name)
        expected_paths.add(name)
        inventory.append({"path": name, "mode": mode.decode(), "oid": oid.decode(),
                          "bytes": len(data), "sha256": sha(data)})
    actual_paths = set()
    for parent, dirs, files in os.walk(destination, followlinks=False):
        for name in files + [name for name in dirs if (Path(parent) / name).is_symlink()]:
            actual_paths.add(str((Path(parent) / name).relative_to(destination)))
        if ".git" in dirs:
            raise ValueError("base包含Git元数据")
    if actual_paths != expected_paths:
        raise ValueError("磁盘文件集合与base树不符")
    if (expected_gitlinks != exported["gitlinks"] or expected_symlinks != exported["symlinks"]
            or expected_lfs != exported["lfs_pointers_not_materialized"]):
        raise ValueError("gitlink/symlink/LFS记录不一致")
    if sum(i["bytes"] for i in inventory) != exported["blob_bytes"]:
        raise ValueError("base字节总数不一致")
    canonical = json.dumps(inventory, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return {"disk_blob_oid_verified": True, "disk_modes_verified": True,
            "disk_path_set_verified": True, "executable_blob_entries": executable,
            "blob_inventory_sha256": sha(canonical)}

def export_base(clone: Path, commit: str, destination: Path) -> dict:
    """直接读 blob，避免 archive 属性遗漏测试或替换源文件字节。"""
    tree = git(clone, "rev-parse", commit + "^{tree}").decode().strip()
    entries = git(clone, "ls-tree", "-rz", "--full-tree", commit).split(b"\0")
    destination.mkdir(parents=True)
    count, total_bytes, links, lfs = 0, 0, [], []
    submodules = []
    proc = subprocess.Popen(
        ["git", "-C", str(clone), "cat-file", "--batch"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    )
    try:
        for entry in entries:
            if not entry:
                continue
            metadata, raw_name = entry.split(b"\t", 1)
            mode, kind, oid = metadata.split()
            name = raw_name.decode("utf-8")
            if kind == b"commit" and mode == b"160000":
                submodules.append({"path": name, "commit": oid.decode(),
                                   "status": "contents_not_materialized"})
                continue
            if kind != b"blob":
                raise ValueError(f"材料需要单独补齐的非 blob 对象: {name} {kind!r}")
            target = destination / name
            if not target.resolve().is_relative_to(destination.resolve()):
                raise ValueError(f"base 路径越出导出目录: {name}")
            proc.stdin.write(oid + b"\n")
            proc.stdin.flush()
            header = proc.stdout.readline().split()
            if len(header) != 3 or header[1] != b"blob":
                raise ValueError(f"Git 对象读取失败: {name} {header!r}")
            data = proc.stdout.read(int(header[2]))
            if len(data) != int(header[2]) or proc.stdout.read(1) != b"\n":
                raise ValueError(f"Git 对象不完整: {name}")
            if hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() != oid.decode():
                raise ValueError(f"Git blob 字节不符: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if mode == b"120000":
                link = data.decode("utf-8")
                if not (target.parent / link).resolve().is_relative_to(destination.resolve()):
                    raise ValueError(f"需要人工处理的外部符号链接: {name} -> {link}")
                target.symlink_to(link)
                links.append(name)
            elif mode in (b"100644", b"100755"):
                target.write_bytes(data)
                target.chmod(0o755 if mode == b"100755" else 0o644)
            else:
                raise ValueError(f"未支持的 Git mode: {name} {mode!r}")
            if data.startswith(b"version https://git-lfs.github.com/spec/v1"):
                lfs.append(name)
            count += 1
            total_bytes += len(data)
    finally:
        proc.stdin.close()
        proc.stdout.close()
        proc.wait()
    if proc.returncode:
        raise RuntimeError(f"cat-file 退出 {proc.returncode}")
    return {"base_tree": tree, "tracked_entries": count + len(submodules), "materialized_blob_entries": count, "blob_bytes": total_bytes,
            "symlinks": links, "lfs_pointers_not_materialized": lfs, "gitlinks": submodules,
            "git_metadata_exported": False, "blob_bytes_verified": True}

def ledger_refs(ledger: Path, instance: str, role: str | None = None) -> list[dict]:
    result = []
    ledger_bytes = ledger.read_bytes()
    for number, line in enumerate(ledger_bytes.splitlines(), 1):
        row = json.loads(line)
        if task_id(row) != instance:
            continue
        kind = row.get("candidate", {}).get("kind")
        if role is not None and kind != role:
            continue
        log = row.get("log") or {}
        path = log.get("path")
        if path and path.startswith("/work/full216_20260919/"):
            path = "runs/full216_rh2_diagnostic_20260919/remote/" + path.removeprefix("/work/full216_20260919/")
        elif path and path.startswith("/work/env_recipe_repair_20260919/"):
            path = "runs/env_recipe_repair_20260919/" + path.removeprefix("/work/env_recipe_repair_20260919/")
        result.append({"ledger": str(ledger.relative_to(ROOT)), "line": number,
                       "candidate": kind, "log": path, "log_sha256": log.get("sha256"),
                       "ledger_sha256": sha(ledger_bytes), "ledger_line_sha256": sha(line)})
    return result

EXPECTED_MANIFEST="52649a38cadccdeacc2317f8d4fb7beee798247e2c9adbc00a198dea88261c7e"
BRIEF="""# 本题公开静态材料
base/ 是本题明确 base_commit 的 Git 跟踪源码、文档和当时已有测试的静态导出；没有 .git 或未来历史。
它不是实际 actor 初始工作树。实际 HEAD、status/diff、来源规定初始改动、忽略资产、准备后状态均未知。
user_prompt.txt 按当前 render_user_prompt 返回表达式经 AST 对拍生成，仅表示计划输入；实际用户消息、
system message、工具调用呈现及 public_hints 是否交付均尚未捕获。public_bundle.json 保留原公开字段。
公开字段中的工作目录、工具、环境激活或操作要求是来源声明，不能作为已验运行事实。
实际 actor 的用户/权限、UID/HOME/cwd/PATH、解释器激活、源码导入、依赖、资产、网络与资源尚未验核。
请据公开问题、源码和旧测试判断必要开发条件，不把未导出材料解释为镜像缺资产或题目不可解。
base_identity.json 的 gitlinks/LFS 指针/软链记录描述静态导出边界，不代表这些资产在原环境存在或缺失。
隐藏测试和 gold 不属于公开包；实际运行条件需另行在 actor 身份核验。本轮没有运行项目测试。
"""
def file_ref(path, expected=None):
    p=Path(path)
    if not p.is_absolute(): p=ROOT/p
    result={"path":str(p.relative_to(ROOT)),"absolute_path":str(p),"exists":p.is_file()}
    if p.is_file():
        data=p.read_bytes()
        result.update(sha256=sha(data),bytes=len(data))
        if expected: assert result["sha256"]==expected.removeprefix("sha256:"), str(p)
    return result

def line_ref(path, number):
    ref=file_ref(path); raw=(ROOT/ref["path"]).read_bytes().splitlines()[number-1]
    return {**ref,"line":number,"line_sha256":sha(raw),"selector":{"line_start":number,"line_end":number}},json.loads(raw)

def local_path(path):
    for remote,local in [("/work/full216_20260919/","runs/full216_rh2_diagnostic_20260919/remote/"),
                         ("/work/env_recipe_repair_20260919/","runs/env_recipe_repair_20260919/")]:
        if path.startswith(remote): return local+path[len(remote):]
    return path

def original_ref(path):
    ref=file_ref(path)
    if ref["exists"]: ref["selector"]={"line_start":1,"line_end":len((ROOT/ref["path"]).read_bytes().splitlines()),"scope":"single-task original"}
    return ref

def source_entry_refs(path, instance):
    """Select only this task from a multi-task JSON input, without copying other entries."""
    p=Path(path); refs=[]
    if not p.is_file(): return refs
    value=json.loads(p.read_text())
    items=value if isinstance(value,list) else value.get("tasks",{})
    if isinstance(items,list):
        for i,x in enumerate(items):
            if isinstance(x,dict) and task_id(x)==instance:
                refs.append({**file_ref(p),"json_pointer":("/tasks" if isinstance(value,dict) else "")+"/"+str(i),
                             "entry_sha256":sha(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()),
                             "entry":x})
    elif isinstance(items,dict) and instance in items:
        x=items[instance]
        refs.append({**file_ref(p),"json_pointer":"/tasks/"+instance,"entry":x,
                     "entry_sha256":sha(json.dumps(x,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode())})
    return refs

def task_candidate_refs(ledger, row, instance, role, task):
    """Resolve only same-task/same-attempt originals and bind noop as well as gold."""
    assert task_id(row) == instance and row["task_id"].split("::")[-1] == instance
    assert row["candidate"]["kind"] == role and role in {"noop", "gold"}
    expected = row["candidate"].get("patch_sha256")
    assert (expected is None) == (role == "noop")
    task_dir = ledger.parent / "artifacts" / row["task_id"].replace("::", "--")
    matches, examined = [], []
    for folder in sorted(task_dir.glob(f"a{row['attempt']}-*")):
        assert folder.parent == task_dir
        patch = folder / "candidate.patch"
        # Hash candidate bytes only inside this task and attempt. No worker-wide glob.
        raw_hash = sha(patch.read_bytes()) if patch.is_file() else None
        projection_path, baseline_path, stage_path = [folder / n for n in
            ["projection.json", "baseline_manifest.json", "stage.json"]]
        missing = [str(p.relative_to(ROOT)) for p in [projection_path, baseline_path, stage_path] if not p.is_file()]
        assert not missing, (instance, role, "binding originals missing", missing)
        projection = json.loads(projection_path.read_text())
        baseline = json.loads(baseline_path.read_text())
        stage = json.loads(stage_path.read_text())
        selected = (raw_hash == (expected.removeprefix("sha256:") if expected else None)
                    and stage["apply_method"] == row["candidate"]["apply_method"]
                    and projection["frozen_patch_digest"] == row["projection"]["frozen_patch_digest"])
        examined.append({"directory": str(folder.relative_to(ROOT)), "raw_patch_sha256": raw_hash,
                         "matches_candidate_binding": selected})
        if not selected:
            continue
        assert baseline["task_id"] == row["task_id"]
        assert baseline["task_base_commit"] == task["base_commit"]
        assert baseline["materialized_head"] == stage["head"] == task["base_commit"]
        rollout = "replay-" + row["run_id"] + "-" + row["task_id"].replace("::", "--")
        assert projection["rollout_execution_id"] == rollout
        assert projection["physical_attempt_id"] == rollout + "-" + folder.name.split("-", 1)[1]
        assert projection["included_entry_paths"] == row["projection"]["included_paths"]
        identity = {"instance_id": instance, "task_id": row["task_id"], "attempt": row["attempt"],
            "candidate_kind": role, "ledger_patch_sha256": expected, "raw_patch_sha256": raw_hash,
            "patch_hash_matches_ledger": True, "no_candidate_patch_for_noop": role == "noop",
            "physical_attempt_id": projection["physical_attempt_id"], "base_commit": task["base_commit"],
            "projection": {**file_ref(projection_path), "json_pointers": ["/frozen_patch_digest", "/physical_attempt_id", "/rollout_execution_id", "/included_entry_paths"]},
            "baseline": {**file_ref(baseline_path), "json_pointers": ["/task_id", "/task_base_commit", "/materialized_head"]},
            "stage": {**file_ref(stage_path), "json_pointers": ["/apply_method", "/head"]}}
        refs = [] if role == "noop" else [{**original_ref(patch), "identity_verification": identity}]
        matches.append((refs, identity))
    assert len(matches) == 1, (instance, role, "candidate identity must resolve uniquely", len(matches), examined)
    refs, identity = matches[0]
    return refs, {**identity, "same_task_attempt_candidates_examined": examined, "unique_match_verified": True}

def environment(task, catalog):
    instance=task["instance_id"]; source=catalog["environment_materials"]; runs=[]
    for loc in source["historical_input_and_log_locators"]:
        role=loc["candidate_kind"]; ledger=ROOT/loc.get("ledger",str(Path(loc["log"]).parent.parent/"ledger.jsonl"))
        refs=ledger_refs(ledger,instance,role)
        refs=[x for x in refs if x["log"]==loc["log"]]
        assert len(refs)==1,(instance,role,refs)
        ref=refs[0]; lr,row=line_ref(ledger,ref["line"])
        assert task_id(row)==instance and row["candidate"]["kind"]==role
        assert lr["line_sha256"]==ref["ledger_line_sha256"]
        if loc.get("line_sha256"): assert lr["line_sha256"]==loc["line_sha256"]
        log=original_ref(ref["log"]); assert log["exists"]
        assert log["sha256"]==ref["log_sha256"].removeprefix("sha256:")
        assert log["sha256"]==loc["expected_log_sha256"].removeprefix("sha256:")
        safe_keys=["run_id","source","schema_id","started_at_utc","image_ref","image_digest_expected","image_id_actual",
                   "image_identity","image_local_build","derived_image_recipe","scripts_digest","baseline_policy_version",
                   "policy","budgets","resource","resource_facts","reference"]
        inputs={k:row.get(k) for k in safe_keys}
        assert all(inputs[k]==v for k,v in loc["input_identity"].items())
        artifacts=[]
        for recipe_dir in [ledger.parent/"recipe",ledger.parent/"bindings"]:
            if recipe_dir.is_dir():
                for p in sorted(recipe_dir.iterdir()):
                    if p.is_file(): artifacts.append(original_ref(p))
        image_originals=[]
        for p in [ledger.parent.parent/"image.json",ledger.parent.parent/"build.log"]:
            if p.is_file(): image_originals.append(original_ref(p))
        candidate_originals, candidate_binding=task_candidate_refs(ledger, row, instance, role, task)

        for expected in loc.get("recipe_audit_files",[]):
            file_ref(expected["path"],expected["sha256"])
        # Original task logs and raw ledger row remain directly accessible, but no verdicts are copied.
        runs.append({"candidate_kind":role,"ledger":lr,"log":log,"input_identity":inputs,
                     "recipe_and_override_originals":artifacts,"derived_image_originals":image_originals,
                     "candidate_input_originals":candidate_originals,"candidate_binding_verification":candidate_binding,
                     "candidate_input_identity":{k:row["candidate"].get(k) for k in ["kind","origin","patch_sha256"]},
                     "diagnostics":file_ref(local_path(row["diagnostics_ref"])) if row.get("diagnostics_ref") else None,
                     "raw_resource_note":"Original field names and values preserved; units have not been inferred.",
                     "ledger_read_scope":"Read only selected row for this task; original runtime evidence is private. No quality summaries copied."})
    assert len(runs)==2 and {x["candidate_kind"] for x in runs}=={"noop","gold"}
    inventory=file_ref(source["image_inventory"]["path"],source["image_inventory"].get("sha256"))
    artifacts=[]; entry_refs=[]
    # Shared source snapshot records code identity, not runtime qualification.
    snap=ROOT/"runs/full216_rh2_diagnostic_20260919/source_snapshot.json"
    snapshot={"source":file_ref(snap),"entries":[],"archive":None}
    if snap.is_file():
        for n,x in enumerate(json.loads(snap.read_text())):
            if x["path"] in ["rh2/scripts/replay_grade.py","rh2/src/repoharness2/adapters/slime/replay_grade.py",
                             "rh2/src/repoharness2/grading/manager.py","rh2/src/repoharness2/envpack/bundles.py"]:
                snapshot["entries"].append({"json_pointer":"/"+str(n),"entry":x})
    archive=ROOT/"runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz"
    if archive.is_file():
        snapshot["archive"]={**file_ref(archive),"inspection":"tar metadata only; contents not extracted/imported",
                             "member_content_hashes_verified":False,"members":[]}
        with tarfile.open(archive) as handle:
            for member in handle.getmembers():
                if member.name in ["scripts/replay_grade.py","src/repoharness2/adapters/slime/replay_grade.py",
                                   "src/repoharness2/grading/manager.py","src/repoharness2/envpack/bundles.py"]:
                    snapshot["archive"]["members"].append({"name":member.name,"bytes":member.size,"mode":oct(member.mode)})
    parent_sets=set()
    for run in runs:
        p=ROOT/run["ledger"]["path"]
        if "env_recipe_repair_20260919" in p.parts:
            rel=p.relative_to(ROOT/"runs/env_recipe_repair_20260919")
            parent_sets.add(ROOT/"runs/env_recipe_repair_20260919"/rel.parts[0])
    for p in sorted(parent_sets):
        for name in ["run_compat_cases.py","run_pydantic_cases.py","run_pydantic.py","replay_with_install_recipe.py","reference_bindings.py","run_reference_cases.py"]:
            if (p/name).is_file():
                lines=(p/name).read_text().splitlines()
                selectors=[i for i,line in enumerate(lines,1) if any(k in line for k in ["--code-root","--recipe","--bindings","--materials","--prepared-summary","--candidate","--derived-image","OLD=","OLD =","frozen_replay_cli"])]
                artifacts.append({**file_ref(p/name),"scope":"shared historical entry source; not executed",
                                  "relevant_line_selectors":selectors,"line_count":len(lines)})
        for name in ["plan.json","reference_bindings_v1.json","materials_v1.json"]:
            entry_refs.extend(source_entry_refs(p/name,instance))
        if (p/"recipes"/(instance+".json")).is_file(): artifacts.append(original_ref(p/"recipes"/(instance+".json")))
        if (p/(instance+".json")).is_file(): artifacts.append(original_ref(p/(instance+".json")))
    prepared=ROOT/"runs/full216_rh2_diagnostic_20260919/preparation/private/host_grading_views.jsonl"
    prep_refs=[]
    if prepared.is_file():
        for n,raw in enumerate(prepared.read_bytes().splitlines(),1):
            row=json.loads(raw)
            if task_id(row)==instance:
                rr,_=line_ref(prepared,n);prep_refs.append(rr)
    gaps=list(source["gaps"])
    gaps.extend(["Current actor user/permissions/PATH/imports, actual delivered messages, worktree status/diff and ignored assets are unverified.",
                 "Historical code archive and source snapshot located; archive member bytes were not independently compared in this metadata-only inspection.",
                 "Baseline generated shell scripts are not separately located for baseline-only runs; host grading view and historical code identity are referenced."] if not parent_sets else
                ["Current actor user/permissions/PATH/imports, actual delivered messages, worktree status/diff and ignored assets are unverified.",
                 "Historical code archive and source snapshot located; archive member bytes were not independently compared in this metadata-only inspection."])
    return {"instance_id":instance,"scope":"private original evidence locators, not a quality assessment or current actor qualification",
            "source_image":source["source_image"],"source_image_manifest_digest":source["source_image_manifest_digest"],
            "image_inventory_original":inventory,"inventory_identity":source.get("inventory_identity"),
            "inventory_identity_scope":"Separate historical source-image inventory; never substituted for actual derived grader image ID.",
            "runs":runs,"historical_entry_sources":artifacts,"task_specific_shared_input_entries":entry_refs,
            "historical_code_snapshot":snapshot,"historical_host_grading_view":prep_refs,
            "material_or_reference_override_status":"See per-run recipe_and_override_originals and task_specific_shared_input_entries; absence means not located, not proof none was used.",
            "actor_initial_worktree":"unknown","actual_actor_messages":"unknown","gaps":gaps}

def install_write_guard(manifest):
    """Fail closed outside reserve20 outputs; do not inspect first12 file contents."""
    out = ROOT / manifest["material_output"]
    allowed = [out / typ / iid for typ in ["public", "private", "history"]
               for iid in manifest["reserve20_task_ids"]]
    allowed_files = {out / "material_checks" / (iid + ".json") for iid in manifest["reserve20_task_ids"]}
    allowed_files.update(HERE / n for n in ["reserve20_material_check.json", "reserve20_environment_replay_inventory.json"])
    parents = {out / "material_checks", out / "public", out / "private", out / "history"}
    forbidden = [out / typ / iid for typ in ["public", "private", "history", "checks", "material_checks"]
                 for iid in manifest["first12_task_ids"]]
    def check(event, args):
        if event == "open" and isinstance(args[0], (str, bytes, os.PathLike)):
            path = Path(os.fsdecode(args[0])).absolute()
            assert not any(path == p or path.is_relative_to(p) for p in forbidden), ("first12 read blocked", str(path))
            assert not path.is_relative_to(HERE / "results"), ("results read blocked", str(path))
            flags = args[2]
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
                assert path in allowed_files or any(path == p or path.is_relative_to(p) for p in allowed), ("write outside reserve20", str(path))
        elif event in {"os.mkdir", "os.chmod", "os.remove", "os.rmdir", "os.symlink"}:
            name = args[1] if event == "os.symlink" else args[0]
            path = Path(os.fsdecode(name)).absolute()
            assert path in parents or path in allowed_files or any(path == p or path.is_relative_to(p) for p in allowed), (event, str(path))
        elif event in {"os.rename", "os.system"}:
            raise AssertionError(("operation forbidden", event))
    sys.addaudithook(check)

def main():
    ap=argparse.ArgumentParser();ap.add_argument("--resume",action="store_true");args=ap.parse_args()
    manifest_bytes=(HERE/"manifest.json").read_bytes();assert sha(manifest_bytes)==EXPECTED_MANIFEST
    m=json.loads(manifest_bytes);assert len(m["reserve20_task_ids"])==20
    assert not set(m["reserve20_task_ids"]) & set(m["first12_task_ids"])
    assert sha((ROOT/m["preparation_catalog"]["path"]).read_bytes())==m["preparation_catalog"]["sha256"]
    install_write_guard(m)
    cat=json.loads((HERE/"preparation_catalog.json").read_text());cats={x["instance_id"]:x for x in cat["focus_tasks"]}
    verify_prompt_template()
    sources={}
    for k,ref in m["source_files"].items():
        data=(ROOT/ref["path"]).read_bytes();assert sha(data)==ref["sha256"];sources[k]=data.splitlines()
    out=ROOT/m["material_output"]; checks=[]; envs=[]
    tasks={x["instance_id"]:x for x in m["tasks"]}
    preflight_envs={}
    for instance in m["reserve20_task_ids"]:
        preflight_envs[instance]=environment(tasks[instance],cats[instance])
        print("IDENTITY_VERIFIED",instance,flush=True)
    for instance in m["reserve20_task_ids"]:
        task=tasks[instance];pub=ROOT/task["public_dir"];priv=ROOT/task["private_dir"]
        assert pub==out/"public"/instance and priv==out/"private"/instance
        assert ROOT/task["history_dir"]==out/"history"/instance
        prior=out/"material_checks"/(instance+".json")
        if prior.is_file():
            assert args.resume, "Existing reserve20 outputs require explicit --resume"
            check=json.loads(prior.read_text())
            base=json.loads((pub/"base_identity.json").read_text())
            verify_base(ROOT/task["repo_mirror"],task["base_commit"],pub/"base",base)
            for ref in check["artifact_hashes"]:
                file_ref(ref["path"],ref["sha256"])
            env=preflight_envs[instance]
            for path,value in [(priv/"environment_record.json",env),(priv/"run_refs.json",env["runs"])]:
                path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
            check["gaps"]=env["gaps"]
            check["artifact_hashes"]=[file_ref(ref["path"]) for ref in check["artifact_hashes"]]
            prior.write_text(json.dumps(check,ensure_ascii=False,indent=2)+"\n")
            checks.append(check);envs.append(env);continue
        pub.mkdir(parents=True,exist_ok=False);priv.mkdir(parents=True,exist_ok=False)
        rows={};source_refs={}
        for k,ref in task["source_refs"].items():
            raw=sources[k][ref["line"]-1];assert sha(raw)==ref["line_sha256"]
            rows[k]=json.loads(raw);assert task_id(rows[k])==instance
            p=pub/"public_bundle.json" if k=="public" else priv/(k+".json")
            p.write_bytes(raw+b"\n");assert p.read_bytes()==raw+b"\n"
            source_refs[k]={**ref,"source_file_sha256":m["source_files"][k]["sha256"],
                            "exported":file_ref(p)}
        public=validate_public(rows["public"])
        assert public.base_commit==task["base_commit"]==rows["grading"]["base_commit"]
        assert public.repo==task["repo"]==rows["grading"]["repo"]
        prompt=render_user_prompt(public)
        (pub/"user_prompt.txt").write_bytes(prompt.encode());(pub/"environment_brief.md").write_text(BRIEF)
        base=export_base(ROOT/task["repo_mirror"],task["base_commit"],pub/"base")
        assert base["base_tree"]==task["base_tree"]
        base.update(verify_base(ROOT/task["repo_mirror"],task["base_commit"],pub/"base",base))
        base["symlink_target_gaps"]=[p for p in base["symlinks"] if not (pub/"base"/p).exists()]
        write_json(pub/"base_identity.json",{"instance_id":instance,"base_commit":task["base_commit"],
                  "actual_actor_worktree":"unknown","scope":"static exact Git blobs, not current actor state",**base})
        for name,value in [("test.patch",rows["grading"]["test_patch"]),("gold.patch",rows["validation"]["golden_patch"])]:
            (priv/name).write_bytes(value.encode());assert (priv/name).read_bytes()==value.encode()
        assert sha((priv/"gold.patch").read_bytes())==rows["validation"]["golden_patch_sha256"].removeprefix("sha256:")
        env=preflight_envs[instance];write_json(priv/"environment_record.json",env)
        write_json(priv/"run_refs.json",env["runs"]);write_json(priv/"source_refs.json",source_refs)
        history=[]
        for p in task["history_sources"]:
            expected=task["history_source_availability"][p];ref=file_ref(p,expected.get("sha256"))
            assert ref["exists"]==expected["exists"];history.append(ref)
        write_json(out/"history"/instance/"refs.json",{"instance_id":instance,"requires_root_release":True,
             "rule":"Do not read content until root releases this task's history after sealed independent analysis.",
             "content_read_or_copied":False,"hash_only":True,"sources":history})
        assert {p.name for p in pub.iterdir()}=={"base","base_identity.json","public_bundle.json","user_prompt.txt","environment_brief.md"}
        hashes=[file_ref(p) for folder in [pub,priv,out/"history"/instance] for p in sorted(folder.iterdir()) if p.is_file()]
        check={"instance_id":instance,"base_commit":task["base_commit"],**base,"source_rows_exact":True,
               "prompt_ast_verified":True,"public_allowlist_verified":True,"patch_bytes_verified":True,
               "history_references_hash_only":True,"candidate_reference_identity_verified":True,"run_ref_count":len(env["runs"]),"artifact_hashes":hashes,
               "gaps":env["gaps"]}
        write_json(prior,check);checks.append(check);envs.append(env)
        print("VERIFIED",instance,base["materialized_blob_entries"],"blobs",len(env["runs"]),"run refs",flush=True)
    summary={"schema":"quality_expansion.material_check.v1","scope":"reserve20 materials only; no project import/test/runtime",
             "manifest_sha256":EXPECTED_MANIFEST,"task_count":len(checks),"task_ids":[x["instance_id"] for x in checks],
             "prompt_template_sha256":sha((ROOT/m["exporter_source"]["current_prompt_source"]["path"]).read_bytes()),
             "exporter_sha256":sha(Path(__file__).read_bytes()),"run_ref_count":sum(x["run_ref_count"] for x in checks),
             "totals":{k:sum(x[k] for x in checks) for k in ["tracked_entries","materialized_blob_entries","blob_bytes","executable_blob_entries"]},
             "gitlinks":sum(len(x["gitlinks"]) for x in checks),"symlinks":sum(len(x["symlinks"]) for x in checks),
             "lfs_pointers":sum(len(x["lfs_pointers_not_materialized"]) for x in checks),"tasks":checks,
             "reserve20_exported":True,"first12_read_or_modified":False,
             "candidate_reference_identity_verified":True}
    for name,value in [("reserve20_material_check.json",summary),("reserve20_environment_replay_inventory.json",{"scope":"private task-specific original locators","tasks":envs})]:
        (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n")
    assert sha((HERE/"manifest.json").read_bytes())==EXPECTED_MANIFEST
    for typ in ["public","private","history"]:
        assert {x.name for x in (out/typ).iterdir()} <= set(m["first12_task_ids"] + m["reserve20_task_ids"])
    print("COMPLETE",20,summary["totals"],flush=True)

if __name__ == "__main__":
    main()
