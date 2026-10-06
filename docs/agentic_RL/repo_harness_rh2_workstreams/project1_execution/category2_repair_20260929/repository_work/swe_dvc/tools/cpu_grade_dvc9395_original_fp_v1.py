"""DVC9395原FP补评分。构造复用原code8，观测取自已验Dask CPU runner；不求解、不改原工件。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def need(condition, message):
    if not condition:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, default=str)
        handle.write("\n")


def command(args, timeout=25):
    result = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    need(result.returncode == 0, "readback command failed: " + repr(args[:3]) + ":" + result.stderr[-400:])
    return result.stdout


def verify_snapshot(ns):
    root = ns.snapshot_root.resolve()
    manifest = json.loads((root.parent / "snapshot_manifest.json").read_text())
    need(sha(root.parent / "snapshot_manifest.json") == ns.snapshot_manifest_sha256, "CPU snapshot manifest changed")
    for item in manifest["files"]:
        path = root.parent / item["path"]
        need(path.is_file() and not path.is_symlink() and sha(path) == item["sha256"]
             and path.stat().st_size == item["bytes"], "CPU fixed input changed: " + item["path"])
    return root


def construct(ns):
    need(ns.job_id == "dvc9395-original-fp-cpu-grade-20261003-v1", "unexpected grading job")
    root = verify_snapshot(ns)
    inputs = json.loads((root / "inputs.json").read_text())
    sys.path.insert(0, str(root / "frozen_code_v8/rh2/src"))
    ep = root / "frozen_code_v8/rh2/experiments/ordinary_gpu_probe_20261002/entry.py"
    ms = importlib.util.spec_from_file_location("dvc9395_original_fp_entry", ep)
    entry = importlib.util.module_from_spec(ms)
    ms.loader.exec_module(entry)
    from types import SimpleNamespace
    import copy
    oldroot = inputs["original_host_root"]
    def physical(value):
        need(value.startswith(oldroot + "/"), "unexpected source relocation")
        return str(root / "remote" / value[len(oldroot) + 1:])
    cfg = json.loads((root / "remote/config_v27/tasks.json").read_text())
    changed = copy.deepcopy(cfg)
    task = changed[inputs["task_id"]]
    summary = json.loads(Path(physical(task["prepared_summary"])).read_text())
    relocated = copy.deepcopy(summary)
    relocated["prepared_dir"] = physical(summary["prepared_dir"])
    relocated["private_dir"] = physical(summary["private_dir"])
    save(ns.out / "summary.json", relocated)
    task["prepared_summary"] = str(ns.out / "summary.json")
    task["public_notes"] = physical(task["public_notes"])
    save(ns.out / "tasks.json", changed)
    reverted = copy.deepcopy(changed)
    for k in ["prepared_summary", "public_notes"]:
        reverted[inputs["task_id"]][k] = cfg[inputs["task_id"]][k]
    need(reverted == cfg and all(relocated[k] == summary[k] for k in summary if k not in {"prepared_dir", "private_dir"}),
         "relocation changed semantic fields")
    need(not any(k.startswith("RH2_") for k in os.environ), "unexpected inherited RH2 profile env override")
    n = SimpleNamespace(tasks_config=ns.out / "tasks.json", task=inputs["task_id"], prepared_summary=None,
        gateway_config=root / "remote/config_v27/gateway_coder.json",
        adapter_config=root / "remote/services_v14/coder/adapter/adapter_config.json",
        adapter_idle_drop_seconds=14400, gateway_host="172.17.0.1", gateway_port=18081,
        attempt_id=inputs["original_attempt_id"], solver="coder", out_dir=ns.out)
    _, _, rollout, spec, profile, prompt, record = entry.load_inputs(n)
    old = json.loads((root / "remote/queue_v27/results" / inputs["original_attempt_id"] / "input_check.json").read_text())
    fields = ["task_id", "source", "solver", "budget", "public_delivery", "assignment", "baseline_policy",
        "prepared_manifest_sha256", "host_grading_artifact_sha256", "grading_materials_identity",
        "grading_revision", "preparation_budget_policy", "grading_budgets", "runner_sha256", "spec_overrides_sha256"]
    need(all(record[k] == old[k] for k in fields), "original consumed material/spec/policy/budget drift")
    need(spec.image == inputs["expected_actual_image_id"] and spec.image_local_build_id == spec.image
         and spec.image_manifest_digest is None and spec.image_local_build is True, "immutable image drift")
    source = entry.source_from_original(root / "remote/queue_v27/results" / inputs["original_attempt_id"] / "attempt",
        spec, rollout.public_bundle_digest, expected_attempt_id=inputs["original_attempt_id"])
    need(source.frozen_patch_digest == inputs["old_FP_digest"]
         and source.frozen_patch.baseline_manifest_digest == inputs["old_baseline_digest"], "original FP/baseline drift")
    from repoharness2.grading.manager import SWEGradingManager, grading_scripts_digest
    SWEGradingManager._verify_frozen_delta_binding(None, spec, source)
    need(profile.cpus == 2 and profile.memory_bytes == 4294967296 and profile.pids_limit == 512
         and profile.candidate_exec_uid == 54322, "original grader profile differs")
    scripts = {k: getattr(spec, k) for k in ["trusted_setup_script", "candidate_test_script",
        "candidate_install_script", "candidate_test_after_install_script", "eval_script"]}
    single, two = grading_scripts_digest(spec, two_stage=False), grading_scripts_digest(spec, two_stage=True)
    save(ns.out / "complete_scripts.json", scripts)
    save(ns.out / "input_check.json", record)
    save(ns.out / "projection.json", source.projection.model_dump(mode="json"))
    loaded = []
    for name, module in tuple(sys.modules.items()):
        if name.split(".", 1)[0] in {"repoharness2", "slime"} and getattr(module, "__file__", None):
            path = Path(module.__file__).resolve()
            need(path.is_relative_to(root / "frozen_code_v8/rh2/src"), "runtime outside frozen code8: " + name)
            loaded.append({"module": name, "path": str(path), "sha256": sha(path)})
    save(ns.out / "runtime_code_binding.json", {"python": sys.executable, "prefix": sys.prefix,
        "actual_modules": loaded, "worker_path": str(Path(__file__).resolve()), "worker_sha256": sha(Path(__file__)),
        "actual_entry_path": str(ep), "entry_sha256": sha(ep)})
    binding = {"job_id": ns.job_id, "original_attempt_id": inputs["original_attempt_id"],
        "original_FP_digest": source.frozen_patch_digest, "original_baseline_digest": inputs["old_baseline_digest"],
        "original_materials_identity": spec.grading_materials_identity, "budgets": record["grading_budgets"],
        "full_grader_profile": profile.to_parameters(), "reference_total": inputs["reference_total"],
        "script_sha256": {k: hashlib.sha256(v.encode()).hexdigest() if v is not None else None for k, v in scripts.items()},
        "single_shell_scripts_digest": single, "two_stage_scripts_digest": two,
        "expected_actual_scripts_digest": single, "expected_actual_mode": "single_shell_deny_all_no_supply",
        "snapshot_manifest_sha256": ns.snapshot_manifest_sha256, "baseline_binding_verified_without_rewriting_original": True,
        "baseline_environment_package_digest": source.baseline_manifest.environment_package_digest,
        "new_model_calls": 0, "relocation_only": True, "original_failure_preserved": True}
    save(ns.out / "binding.json", binding)
    inputs["new_grading_revision"] = old["grading_revision"]
    return inputs, spec, profile, source, binding

async def execute(ns, inputs, spec, profile, source, binding):
    from repoharness2.grading.manager import GradingManagerConfig, SWEGradingManager
    slot_root = Path("/work/rh2-category2-20261003")
    need(sha(slot_root / "control" / "cpu_slot.py") == "a77d0665ec15e919a341c0d7dbd18fdc6091663e372dfb1002c57d17e5753972",
         "fixed CPU slot wrapper differs")
    admissions = []
    for path in (slot_root / "jobs" / "swe_dvc").glob(ns.job_id + "-q*/status.json"):
        row = json.loads(path.read_text())
        if row.get("status") == "running" and row.get("child_pid") == os.getpid():
            need(row["mode"] == "run" and row["supervisor_pid"] == os.getppid()
                 and row["package"] == "swe_dvc" and "--execute" in row["command"], "actual CPU admission differs")
            admissions.append({"path": str(path), "record": row})
    need(len(admissions) == 1, "no unique foreground CPU slot admission for this worker")
    save(ns.out / "actual_cpu_slot_admission.json", admissions[0])
    prefix = "rh2.dvc9395.cpu.samefp.v1"
    state = {"job_id": ns.job_id, "actual_host_role": "cpu-a", "model_started": False,
             "original_FP_digest": inputs["old_FP_digest"], "original_old_infra_preserved": True,
             "baseline_rebuild_passed": False, "full_reference_complete": False, "cleanup_ok": False}
    manager = SWEGradingManager(GradingManagerConfig(
        label_prefix=prefix, name_prefix="rh2-dvc9395-cpu-samefp-v1", eval_log_dir=ns.out / "eval_logs",
        sandbox_profile=profile))
    need(manager.config.supply is None and not manager._supply_applies(spec), "unexpected supply/two-stage mode")
    owned = command(["docker", "ps", "-a", "--filter", f"label={prefix}.trajectory={ns.job_id}", "--format", "{{.Names}}"])
    need(not owned.strip(), "same job already has a container; no repeat dispatch")
    actual_image = json.loads(command(["docker", "image", "inspect", inputs["expected_actual_image_id"]]))
    save(ns.out / "actual_image.json", actual_image)
    need(len(actual_image) == 1 and all(actual_image[0][key] == value
         for key, value in inputs["expected_cpu_image"].items()), "exact CPU source image API representation differs")
    original_start, original_close = manager._start_container, manager._close_container_scope
    original_exec, original_verify = manager._exec_bash_checked, manager._verify_baseline_rebuild
    sequence, context, monitor_task = 0, {}, None

    def resource_snapshot(stage):
        if not context:
            return None
        cg = Path(context["host_cgroup"])
        facts = {"at": time.time(), "stage": stage, "container": context["container"], "host_pid": context["pid"]}
        for name in ["cpu.max", "memory.current", "memory.peak", "memory.events", "pids.current", "pids.peak", "pids.max", "pids.events"]:
            path = cg / name
            facts[name] = path.read_text().strip() if path.is_file() else None
        procs = cg / "cgroup.procs"
        processes = []
        for pid in procs.read_text().splitlines() if procs.is_file() else []:
            try:
                status = Path(f"/proc/{pid}/status").read_text().splitlines()
                selected = {line.split(":", 1)[0]: line.split(":", 1)[1].strip()
                            for line in status if line.startswith(("Name:", "Threads:"))}
                processes.append({"host_pid": int(pid), **selected})
            except FileNotFoundError:
                pass  # 已结束的自有进程不补猜测。
        facts["own_processes"] = processes
        with (ns.out / "resource_samples.jsonl").open("a") as handle:
            handle.write(json.dumps(facts, sort_keys=True) + "\n")
        return facts

    async def monitor():
        while True:
            try:
                resource_snapshot("during")
            except Exception as exc:
                state.setdefault("resource_monitor_errors", []).append(repr(exc))
            await asyncio.sleep(5)

    async def start(*args, **kwargs):
        nonlocal monitor_task
        record = await original_start(*args, **kwargs)
        raw = json.loads(command(["docker", "inspect", record.name]))[0]
        labels = raw["Config"]["Labels"]
        need(labels.get(prefix + ".owner") == manager.run_id
             and labels.get(prefix + ".trajectory") == ns.job_id, "actual container ownership differs")
        need(raw["Image"] == inputs["expected_actual_image_id"], "actual container source differs")
        hc = raw["HostConfig"]
        need(hc["NanoCpus"] == 2000000000 and hc["Memory"] == 4294967296
             and hc["PidsLimit"] == 512 and hc["NetworkMode"] == "none", "actual resource/network profile differs")
        pid = raw["State"]["Pid"]
        lines = Path(f"/proc/{pid}/cgroup").read_text().splitlines()
        cg_rel = next(line.split(":", 2)[2] for line in lines if line.startswith("0::"))
        context.update(container=record.name, pid=pid, host_cgroup="/sys/fs/cgroup" + cg_rel)
        save(ns.out / "actual_container_start.json", {"container": record.name, "id": raw["Id"],
            "image": raw["Image"], "host_pid": pid, "host_cgroup": context["host_cgroup"],
            "HostConfig": hc, "labels": labels, "candidate_policy_uid": profile.candidate_exec_uid})
        first = resource_snapshot("fresh_before_baseline")
        need(first["pids.events"] == "max 0", "fresh cgroup already has PID quota event")
        monitor_task = asyncio.create_task(monitor())
        return record

    async def close(record, *args, **kwargs):
        try:
            if context and record.name == context["container"]:
                snap = resource_snapshot("before_cleanup")
                if snap["pids.events"] is not None and not (ns.out / "resource_before_cleanup.json").exists():
                    raw = json.loads(command(["docker", "inspect", record.name], timeout=5))[0]
                    save(ns.out / "resource_before_cleanup.json", {"cgroup": snap, "OOMKilled": raw["State"]["OOMKilled"]})
        except Exception as exc:
            state.setdefault("resource_cleanup_readback_errors", []).append(repr(exc))
        # 观测失败也必须进入manager原有的有界清理，不让日志钩子阻止收口。
        return await original_close(record, *args, **kwargs)

    async def verify(*args, **kwargs):
        result = await original_verify(*args, **kwargs)
        state["baseline_rebuild_passed"] = True
        return result

    async def logged(*args, **kwargs):
        nonlocal sequence
        if kwargs.get("phase") == "test" and not state.get("actual_candidate_uid_verified"):
            need(kwargs.get("user") == "54322", "actual candidate command UID differs")
            uid = await original_exec(args[0], "id -u", phase="owner_candidate_uid_readback",
                                      timeout=30, user="54322", home=f"/home/{profile.candidate_exec_user}")
            save(ns.out / "actual_candidate_uid.json", {"exit_code": uid.exit_code,
                 "stdout": uid.stdout, "stderr": uid.stderr, "user_argument": "54322"})
            need(uid.exit_code == 0 and uid.stdout.strip() == "54322", "actual candidate UID readback differs")
            state["actual_candidate_uid_verified"] = True
        sequence += 1
        index, phase, callback = sequence, kwargs.get("phase"), kwargs.get("on_delivered")
        def delivered(result):
            save(ns.out / "exec_logs" / f"{index:03d}.json", {"phase": phase, "exit_code": result.exit_code,
                 "user_argument": kwargs.get("user"), "stdout": result.stdout, "stderr": result.stderr})
            if callback:
                callback(result)
        kwargs["on_delivered"] = delivered
        return await original_exec(*args, **kwargs)

    manager._start_container, manager._close_container_scope = start, close
    manager._verify_baseline_rebuild, manager._exec_bash_checked = verify, logged
    try:
        report = await asyncio.wait_for(manager.grade(
            trajectory_id=ns.job_id, workspace=None, spec=spec, frozen_delta=source,
            deadline_monotonic=time.monotonic() + inputs["grading_budgets"]["whole_seconds"]), timeout=inputs["grading_budgets"]["whole_seconds"] + 300)
        state["report"] = report.model_dump(mode="json")
        save(ns.out / "report.json", state["report"])
        ds = list((ns.out / "eval_logs").glob("*.diagnostics.json"))
        need(len(ds) == 1, "unique diagnostics absent")
        diagnostic = json.loads(ds[0].read_text())
        need(diagnostic["supply"] is None and diagnostic["scripts_digest"] == binding["expected_actual_scripts_digest"], "actual single-shell digest/mode differs")
        candidate = diagnostic.get("candidate") or {}
        state["actual_candidate"] = candidate
        need(report.outcome != "failed_to_grade" and report.failure_category not in {"infra_failure", "test_log_parse_failed"}, "actual grading infra/parse failure")
        need(candidate.get("candidate_segment_completed") is True and candidate.get("log_partial") is False
             and candidate.get("install_rc_last_command") == 0 and not candidate.get("install_failed_commands")
             and type(candidate.get("test_rc")) is int, "install/test incomplete")
        parts = diagnostic["grading_revision"]["partitions"]
        need({k: v["references"] for k, v in parts.items()} == {k: v["references"] for k, v in inputs["new_grading_revision"]["partitions"].items()}, "reference lists changed")
        count = 0
        for part in parts.values():
            result = part.get("result")
            need(isinstance(result, dict), "reference result absent")
            items = [item for group in result.values() for item in group]
            need(len(items) == len(set(items)) and set(items) == set(part["references"])
                 and not any(result.get(k) for k in ["missing", "skipped", "unaccounted"]), "incomplete reference accounting")
            count += len(items)
        need(count == inputs["reference_total"], "reference count changed")
        state["full_reference_complete"] = True
        save(ns.out / "full_reference_readback.json", {"total": count, "partitions": parts,
             "candidate": candidate, "actual_single_shell_digest": diagnostic["scripts_digest"], "same_original_FP": True})
        logs = list((ns.out / "eval_logs").glob("*.eval.log"))
        need(len(logs) == 1, "unique eval log absent")
        text = logs[0].read_text()
        resource = json.loads((ns.out / "resource_before_cleanup.json").read_text())
        memory_events = dict(line.split() for line in resource["cgroup"]["memory.events"].splitlines())
        need(resource["cgroup"]["pids.events"] == "max 0" and resource["OOMKilled"] is False
             and memory_events.get("oom") == memory_events.get("oom_kill") == "0", "PID/OOM resource failure")
    except BaseException as exc:
        state["exception"] = repr(exc)
    finally:
        state["received_signals"] = list(getattr(ns, "received_signals", []))
        if monitor_task:
            monitor_task.cancel()
            await asyncio.gather(monitor_task, return_exceptions=True)
        try:
            closing = await asyncio.wait_for(manager.close(), timeout=300)
            state["manager_close"] = closing
            left = command(["docker", "ps", "-a", "--filter", f"label={prefix}.trajectory={ns.job_id}", "--format", "{{.Names}}"])
            state["owned_containers_remaining"] = left.strip()
            state["cleanup_ok"] = not left.strip() and closing.get("containers_open") == closing.get("supply_open") == closing.get("cleanup_failures") == [] and closing.get("containers_created_total") == closing.get("containers_removed_total") == 1
        except BaseException as exc:
            state["cleanup_exception"] = repr(exc)
        try:
            verify_snapshot(ns)
            state["fixed_sources_unchanged_after_run"] = True
        except Exception as exc:
            state["source_readback_exception"] = repr(exc)
        save(ns.out / "status.json", state)
    need("exception" not in state and state["baseline_rebuild_passed"] and state["full_reference_complete"]
         and state.get("actual_candidate_uid_verified") and state.get("fixed_sources_unchanged_after_run")
         and not state.get("resource_monitor_errors") and not state.get("resource_cleanup_readback_errors")
         and state["cleanup_ok"], "CPU same-FP recovery incomplete; retain evidence, no automatic retry")
    save(ns.out / "done.json", {"same_FP_CPU_environment_acceptance_complete": True,
         "new_model_samples": 0, "original_infra_preserved": True, "training_qualification": None})


async def execute_with_signals(ns, inputs, spec, profile, source, binding):
    loop = asyncio.get_running_loop()
    task = asyncio.current_task()
    ns.received_signals = []

    def stop(signum):
        ns.received_signals.append(signum)
        if len(ns.received_signals) == 1:
            task.cancel()  # 首次取消走grade/finally清理；再次信号不截断有界收口。

    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stop, signum)
    try:
        await execute(ns, inputs, spec, profile, source, binding)
    finally:
        for signum in (signal.SIGTERM, signal.SIGINT):
            loop.remove_signal_handler(signum)


def main():
    parser = argparse.ArgumentParser(allow_abbrev=False)
    parser.add_argument("--snapshot-root", type=Path, required=True)
    parser.add_argument("--snapshot-manifest-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    ns = parser.parse_args()
    need(not ns.out.exists(), "output exists; do not overwrite or auto-retry")
    ns.out.mkdir(parents=True, mode=0o700)
    inputs, spec, profile, source, binding = construct(ns)
    if ns.execute:
        need(os.geteuid() == 0 and str(ns.out).startswith("/work/rh2-category2-20261003/packages/swe_dvc/"), "CPU package execution boundary differs")
        asyncio.run(execute_with_signals(ns, inputs, spec, profile, source, binding))
    else:
        save(ns.out / "pure_check_done.json", {"identity_constructed_only": True, "candidate_executed": False})
    print(json.dumps({"output": str(ns.out), "job_id": ns.job_id, "executed": ns.execute}, ensure_ascii=False))


if __name__ == "__main__":
    main()
