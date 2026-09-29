"""把已重放审阅的题级证据汇总成可续查目录；不据此自动改变正式题池。"""

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

REPO = Path(__file__).resolve().parents[3]
EVIDENCE = REPO / "runs/env_recipe_repair_20260919"
DOCS = REPO / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_recipe_repair_20260919"
# 后项覆盖同题较早、较不完整的配方；每个目录只有通过reconcile校验的analysis可入表。
BATCHES = [
    "remote", "round2", "round2b", "install_wave1", "pydantic_v1", "reference_v1",
    "combined_v1", "materials_v1", "materials_v2", "compat_v1", "compat_v2b",
    "compat_v3", "moto_local_v1", "moto_transport_v1", "python311_v1b", "sqs_v1",
    "dvc_install_v1c", "dvc2231_v3", "itk_v2", "resources_v1", "moto_docker_v3", "moto_docker_v4",
    "numeric_v1b", "numeric_v1c", "numeric_v1d", "numeric_v1e", "pandas_meta_v1", "dvc_tail_v1",
    "modin5940_resources_v2", "modin6780_compat_v1", "pandas_meta_v3", "modin_s3_compat_v1",
    "numeric_v1f", "modin_s3_compat_v2", "modin_s3_compat_v3", "modin_s3_compat_v4",
    "modin_s3_compat_v5", "modin_s3_compat_v6",
]


def main():
    issues = json.loads((DOCS / "known_issues.json").read_text())
    families = defaultdict(list)
    for family in issues["families"]:
        for task in family["tasks"]:
            families[task].append(family["family"])
    latest = {}
    history = defaultdict(list)
    for batch in BATCHES:
        folder = EVIDENCE if batch == "remote" else EVIDENCE / batch
        analyses = list(folder.glob("analysis_*.json"))
        if not analyses:
            continue
        analysis = max(analyses, key=lambda p: int(p.stem.rsplit("_", 1)[1]))
        rows = json.loads(analysis.read_text())
        groups = defaultdict(dict)
        for row in rows:
            if "canary" in row["run"] or "probe" in row["run"]:
                continue
            role = row["kind"]
            # 11352的context-only gold由cc_patch_dir输入；不把其它候选当gold。
            if row["instance_id"] == "python__mypy-11352" and batch == "materials_v1" and row["run"].endswith("-gold_context_rebased"):
                role = "gold"
            if role not in {"noop", "gold"}:
                continue
            groups[row["instance_id"]][role] = row
        for task, pair in groups.items():
            if task == "Project-MONAI__MONAI-763" and batch == "numeric_v1f":
                # 只重测被其它manager误删的gold；若原noop正常完成，逐项证明其环境可复用。
                prior = latest[task]
                if prior["batch"] == "numeric_v1e" and "noop" in prior["pair"]:
                    original_noop = prior["pair"]["noop"]
                    a = json.loads((REPO / original_noop["log"]).parent.parent.joinpath("ledger.jsonl").read_text())
                    b = json.loads((folder / pair["gold"]["run"] / "ledger.jsonl").read_text())
                    assert all(a[k] == b[k] for k in ["image_id_actual", "image_identity", "scripts_digest", "policy", "budgets"])
                    pair["noop"] = original_noop
            if task == "python__mypy-11352" and batch == "materials_v1":
                prior = latest[task]
                assert prior["batch"] == "install_wave1" and set(prior["pair"]) == {"noop"}
                a = json.loads((EVIDENCE / "install_wave1" / prior["pair"]["noop"]["run"] / "ledger.jsonl").read_text())
                b = json.loads((folder / pair["gold"]["run"] / "ledger.jsonl").read_text())
                assert all(a[k] == b[k] for k in ["image_id_actual", "scripts_digest", "policy"])
                pair["noop"] = prior["pair"]["noop"]
            entry = {"batch": batch, "analysis": str(analysis.relative_to(REPO)), "pair": pair}
            history[task].append({"batch": batch, "analysis": entry["analysis"], "roles": sorted(pair)})
            latest[task] = entry
    result = []
    for task in sorted(families):
        chosen = latest.get(task)
        if chosen is None:
            result.append({"instance_id": task, "issues": families[task], "status": "no_repair_pair_yet"})
            continue
        pair = chosen["pair"]
        checks = {
            "both_roles": set(pair) == {"noop", "gold"},
            "noop_reward_zero": pair.get("noop", {}).get("report", {}).get("reward") == 0,
            "gold_reward_one": pair.get("gold", {}).get("report", {}).get("reward") == 1,
            "gold_full_test_exit_zero": pair.get("gold", {}).get("install", {}).get("test_rc") == 0,
            "all_installations_complete": bool(pair) and all(
                r["install"].get("install_rc_last_command") == 0
                and not r["install"].get("install_failed_commands")
                and not r["install"].get("install_skipped")
                # 旧扫描保留了git diff中IS_ERROR等字面量；只用真实安装段的错误行。
                and not install_errors(r) for r in pair.values()),
            "all_logs_complete": bool(pair) and all(log_is_complete(r) for r in pair.values()),
            "cleanup_verified": bool(pair) and all(
                r["cleanup"]["removed"] and not r["stage_error"] and driver_close_ok(r)
                for r in pair.values()),
        }
        observations = {}
        for role, r in pair.items():
            run_path = (REPO / r["log"]).parent.parent
            ledger = json.loads((run_path / "ledger.jsonl").read_text())
            observations[role] = {
                "run": r["run"], "log": r["log"],
                "log_sha256": hashlib.sha256((REPO / r["log"]).read_bytes()).hexdigest(),
                "report": r["report"], "install": r["install"], "full_test_summary": r["pytest_summaries"],
                "reference_counts": r["reference_counts"], "resource": r["resource"],
                "resource_facts": r["resource_facts"],
                "driver_close": driver_close_record(r),
                "inputs": {k: ledger[k] for k in ["image_ref", "image_id_actual", "image_identity", "derived_image_recipe", "scripts_digest", "budgets", "policy"]},
                "recipe_audit_files": [{"path": str(p.relative_to(REPO)), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                                       for p in sorted((run_path / "recipe").rglob("*")) if p.is_file()],
            }
        result.append({
            "instance_id": task, "issues": families[task],
            "status": "verified_environment_pair" if all(checks.values()) else "open_or_partial",
            "selected_batch": chosen["batch"], "analysis": chosen["analysis"], "checks": checks,
            "observations": observations, "history": history[task],
        })
    dispositions = json.loads((DOCS / "dispositions.json").read_text())
    for entry in result:
        disposition = dispositions["tasks"].get(entry["instance_id"])
        if disposition:
            entry["environment_pair_status"] = entry["status"]
            entry["status"] = disposition["status"]
            entry["disposition"] = disposition
    output = {
        "scope": "本批已知问题的实验配方目录；不是正式题池、P-A资格或题意质量认证。",
        "selection": "显式批次顺序；保留失败及较早配方。任何open项不得继承较早gold=1冒充完成；材料隔离不能冒充环境修复或免除在跑对照的审阅。",
        "requirements_before_training": ["选定配方重新冻结正式题包并打通actor消费", "公开资产/依赖同步提供rollout", "私有测试材料不得泄漏给agent", "资源档位与隔离服务边界单独验收"],
        "counts": dict(Counter(x["status"] for x in result)), "tasks": result,
    }
    dest = DOCS / "repair_catalog.json"
    dest.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"tasks": len(result), "counts": output["counts"], "output": str(dest)}))


def install_errors(row):
    text = (REPO / row["log"]).read_text()
    start = re.search(r"^RH2_TS_INSTALL_START=[0-9.]+$", text, re.MULTILINE)
    end = re.search(r"^RH2_TS_INSTALL_END=[0-9.]+$", text, re.MULTILINE)
    assert start and end and start.end() < end.start(), row["log"]
    return re.findall(r"^\s*ERROR:.*$", text[start.end():end.start()], re.MULTILINE)


def driver_close_record(row):
    records = []
    for line in (REPO / row["log"]).parent.parent.joinpath("driver.log").read_text().splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and "manager_close" in value:
            records.append(value)
    return records[0] if len(records) == 1 else None


def log_is_complete(row):
    # 早期analysis没有reference_completeness字段；统一以原日志及退出事实核对。
    return (not row["install"].get("log_partial")
            and row["install"].get("test_rc") is not None
            and ">>>>> End Test Output" in (REPO / row["log"]).read_text())


def driver_close_ok(row):
    closed = driver_close_record(row)
    return bool(closed is not None and not closed.get("halted") and not closed.get("cleanup_failures")
                and not closed["manager_close"].get("containers_open")
                and not closed["manager_close"].get("cleanup_failures"))


if __name__ == "__main__":
    main()
