"""Coordinator-only, stdlib artifact adjudication; never executes task code."""
import hashlib
import json
import runpy
from pathlib import Path

B = Path(__file__).resolve().parent
H = runpy.run_path(str(B / "coordination_metadata.py"))
ROOT = H["ROOT"]
PACKAGE = "pack01_monai"
IDS = ["Project-MONAI__MONAI-" + n for n in ("2446", "3715", "5686")]
ARCHIVE = B / "coordinator_revisions" / PACKAGE
assert not ARCHIVE.exists(), "Do not overwrite pre-adjudication originals"
ARCHIVE.mkdir(parents=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rel(path):
    return str(path.relative_to(ROOT))


actions = {
    "actual_actor_evidence_gap": (
        "actual actor delivery and public development evidence only; historical grader evidence remains valid within its recorded condition",
        "由任务二取得正式actor消息、初态与开发条件，并沿公开入口验证；本审查不执行或派发运行。",
    ),
    "historical_family_lead_unverified": (
        "unverified historical family/split lead; not a certified duplicate finding",
        "保留为未核实线索；正式用途涉及划分时再独立核原版本关系，本轮不沿旧链接扩读。",
    ),
    "train_coverage_gap": (
        "public train string behavior and current F2P/P2P acceptance",
        "形成公开SupervisedEvaluator行为验收提案，观测forward时training/梯度和退出恢复；不用函数身份限制等效实现。",
    ),
    "gradient_connectivity_gap": (
        "SSIMLoss input derivatives under the public API; flags and constant forward values are insufficient",
        "参考/验收修订时采用非恒等输入检查真实输入导数；梯度存在不等于正确，不能要求所有图像每像素梯度非零。",
    ),
    "gold_multichannel_incomplete": (
        "public B1C5 SSIMLoss use with non-differentiable data_range; residual base defect, not a new gold regression",
        "由任务二择机做私有gold B1C1/B1C5 CPU对照，确认递归detach残留；结果只用于参考与验收范围，不赋予actor资格。",
    ),
    "device_parameter_scope": (
        "selected historical CPU parameter identities; no claim about CUDA execution",
        "保留CPU条件与稳定旧ID说明；无需仅为追加CUDA项而重跑收集或改参考。",
    ),
}
findings = {
    "2446": "主审与reviewer一致支持受限静态候选；协调者采纳reviewer具体补充：数组列表F2P与字典列表shuffle P2P缺少同输入类型的联合约束，25记静态覆盖issue，未运行错修。",
    "3715": "主审与reviewer一致：train核心诉求漏测归25，eval有公开依据，未证gold新增回归；先形成行为验收提案。",
    "5686": "主审与reviewer一致：flag不足以验梯度，公开C5递归detach为gold残留归27；私有gold定向CPU只确认参考范围，不证明actor资格。",
}
changes = []
for tid in IDS:
    out = B / "results" / tid
    short = tid.rsplit("-", 1)[1]
    entry = {"instance_id": tid, "before": {}, "after": {}, "changes": []}
    dst = ARCHIVE / tid
    dst.mkdir()
    for filename in ("card.md", "screening_record.json"):
        original = out / filename
        archived = dst / filename
        archived.write_bytes(original.read_bytes())
        entry["before"][filename] = {"file": rel(archived), "sha256": sha(archived)}
    r = json.loads((out / "screening_record.json").read_text())
    for number, check in r["checks"].items():
        assert "by" not in check, "Unexpected original author field"
        check["by"] = "/root/e25_main_monai"
        if number in {"3", "7", "8", "10", "13", "29", "30", "33", "34", "35", "36", "38"}:
            check["evidence_level"] = "explicit_missing_evidence"
    r["checks"]["40"].update(
        status="unknown", by="/root",
        note="已核三角色阶段封存和release，且完成独立复核；这些过程事实不能证明无漏检、误杀或选样偏差。本批按公开类型和材料可定位性选样，协调者已见私有历史，不是独立审查者。",
        evidence_level="process_audit_with_unmeasured_error_and_sampling_bias",
        evidence_refs=["review.md", "../../assignments.json", "../../manifest.json"],
    )
    for issue in r["issues"]:
        scope, action = actions[issue["id"]]
        issue.update(scope=scope, proposed_action=action)
    if short == "2446":
        claim = "数组列表F2P只验外部顺序；shuffle P2P用字典列表，update_cache显式关闭shuffle。只对数组列表禁shuffle而保留字典分支的错修没有同类型内部打乱断言约束；静态定位，未运行。"
        refs = ["reviewer_initial.md", "review.md", str(ROOT / "runs/swegym_quality_expansion_20260925/private" / tid / "test.patch") + ":8", str(ROOT / "runs/swegym_quality_expansion_20260925/public" / tid / "base/tests/test_smartcachedataset.py") + ":103"]
        r["checks"]["25"].update(status="issue", note=claim, evidence_level="static_inference", evidence_refs=refs, by="/root")
        r["issues"].append({"id": "array_shuffle_joint_coverage_gap", "checks": ["25"], "status": "open", "severity": "P3", "category": "acceptance_coverage", "scope": "joint input ownership and internal shuffle behavior for the public array-list example", "claim": claim, "evidence_level": "static_inference", "evidence_refs": refs, "proposed_action": "保留受限静态候选；未来完善窄验收时在同一数组输入上同时检查外部不变与内部seed打乱，不为此重复安排本轮CPU。", "not_claimed": "未执行错修或认证实际满分；不是gold新增回归。", "by": "/root", "finding_origin": "/root/e25_review_monai"})
        r["disposition"]["reason"] = "静态候选待actor验证；compat-v1已覆盖旧nibabel问题，存在非阻断的数组列表联合shuffle覆盖缺口，无已证gold新增回归。"
    else:
        r["checks"]["25"]["evidence_level"] = "static_inference"
    if short == "5686":
        r["checks"]["27"]["evidence_level"] = "static_call_chain"
    review = {"file": rel(out / "review.md"), "sha256": sha(out / "review.md"), "agent_id": "/root/e25_review_monai"}
    r["disposition"].update(independent_review="completed", reviewer_findings={"summary": findings[short], "evidence_ref": review, "coordinator_adjudicated": True}, ready_for_probe=False, parent_acceptance="pending")
    r["disposition"]["unique_priority_next_step"]["execution_owner"] = "task2 / Claude B; proposal only, not dispatched"
    r["disposition"]["unique_priority_next_step"]["actor_qualification_limit"] = "实际actor资格须在正式actor入口保存身份、初态、开发条件及公开功能执行证据；metadata/import或私有gold诊断均不能单独证明。"
    r["usage"]["exposure_scope"] = "exposure fields above preserve the investigator's reported reading scope"
    r["usage"]["coordinator_closeout"] = {"by": "/root", "independent_of_prior_conclusions": False, "read_independent_review": review, "coordinator_saw_other_package_materials": True, "actual_actor_exposure": "unknown", "initials_unchanged": True}
    r["coordinator_revision"] = {"by": "/root", "at": H["now"](), "original_record": entry["before"]["screening_record.json"], "original_card": entry["before"]["card.md"], "revision_log": rel(ARCHIVE / "revision_log.json"), "note": "协调者在交叉复核后修订可变后稿；三种封存初判、历史delta及review未改。"}
    (out / "screening_record.json").write_text(json.dumps(r, ensure_ascii=False, indent=2) + "\n")
    card = (out / "card.md").read_text().replace("独立review待完成", "独立review已完成，待根任务验收")
    if short == "2446":
        card = card.replace("双方通过；可阻止简单取消shuffle", "双方通过；可阻止全局取消shuffle，未联合覆盖数组列表内部打乱")
    card += "\n协调收口：" + findings[short] + " checks署名和问题处置字段已补齐；40改unknown，流程合规不证明无筛查偏差。review及原版归档见review.md、../../coordinator_revisions/pack01_monai/。实际actor资格仍未知，未执行项目或测试。\n"
    (out / "card.md").write_text(card)
    entry["changes"] = ["39 checks.by credited to actual investigator; coordinator changes explicitly credited", "issue scope/proposed_action added", "check40 pass -> unknown", "review completion and actor qualification limits added", "evidence levels separated from historical execution", findings[short]]
    for filename in ("card.md", "screening_record.json"):
        entry["after"][filename] = {"file": rel(out / filename), "sha256": sha(out / filename)}
    changes.append(entry)

(ARCHIVE / "revision_log.json").write_text(json.dumps({"package": PACKAGE, "by": "/root", "at": H["now"](), "scope": "mutable final card/record only", "sealed_initials_changed": False, "tasks": changes}, ensure_ascii=False, indent=2) + "\n")
a = H["load"]()
for task in a["tasks"]:
    matches = [x for x in a["assignments"] if task["instance_id"] in x["instance_ids"]]
    task["role_states"] = {x["role"]: {"agent_id": x["agent_id"], "status": x["status"], "phase": x["phase"]} for x in matches}
    if task["instance_id"] in IDS:
        task["status"] = "static_review_complete_pending_parent_acceptance"
for package in a["packages"]:
    if package["package_id"] == PACKAGE:
        package.update(status="static_review_complete_pending_parent_acceptance", report="pack01_report.md", coordinator_revision_log=rel(ARCHIVE / "revision_log.json"))
    elif package["package_id"] == "pack02_conan":
        package["status"] = "cross_review"
    elif package["package_id"] == "pack03_dask":
        package["status"] = "independent_original_analysis"
    elif package["package_id"] == "pack04_pydantic":
        package["status"] = "public_reading"
a["status"] = "first_package_static_review_complete_first12_in_progress"
a["events"].append({"at": H["now"](), "type": "coordinator_package_closeout", "package": PACKAGE, "revision_log": rel(ARCHIVE / "revision_log.json"), "parent_acceptance": "pending"})
H["save"](a)
print(json.dumps({"package": PACKAGE, "archived_originals": 6, "mutable_finals_updated": 6, "revision_log_sha256": sha(ARCHIVE / "revision_log.json")}, ensure_ascii=False))
