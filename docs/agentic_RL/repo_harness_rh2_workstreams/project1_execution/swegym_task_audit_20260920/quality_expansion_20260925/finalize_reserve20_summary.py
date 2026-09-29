"""Build the final static audit summary from completed reserve metadata; stdlib only.

Reads reserve outputs and verification metadata. Does not scan first12 source/output
files, execute a project, alter a task, or dispatch runtime work.
"""
import hashlib
import json
import runpy
from pathlib import Path

B = Path(__file__).resolve().parent
H = runpy.run_path(str(B / "coordination_metadata.py"))
ROOT = H["ROOT"]


def read(name):
    return json.loads((B / name).read_text())


def digest(name):
    return hashlib.sha256((B / name).read_bytes()).hexdigest()


def finalize():
    a = H["load"]()
    tasks = [t for t in a["tasks"] if t["stage"] == "reserve20"]
    ids = {t["instance_id"] for t in tasks}
    assert len(ids) == len(tasks) == 20
    assert all(t["status"] in ("static_review_completed", "static_review_accepted_by_parent") for t in tasks)
    outputs = read("reserve20_final_output_verification.json")
    revisions = read("reserve20_final_revision_provenance_verification.json")
    assert outputs["passed"] and not outputs["errors"] and outputs["task_count"] == 20
    assert {t["instance_id"] for t in outputs["tasks"]} == ids
    assert revisions["passed"] and not revisions["errors"] and revisions["artifact_count"] == 40
    assert {t["instance_id"] for t in revisions["artifacts"]} == ids
    assert digest("manifest.json") == a["manifest_sha256"]

    candidates = read("probe_candidates.json")
    queue = read("cpu_queue.json")
    cids = {x["instance_id"] for x in candidates["candidates"]}
    qids = {x["instance_id"] for x in candidates["not_prioritized"]}
    assert not cids & qids and cids | qids == {t["instance_id"] for t in a["tasks"]}
    assert len(cids) == len(candidates["candidates"]) and len(qids) == len(candidates["not_prioritized"])
    assert candidates["ready_for_probe"] is False
    categories = ["actor_workflow_requests", "items", "acceptance_design_requests", "reference_review_requests"]
    primary = [item["instance_id"] for category in categories for item in queue[category]]
    assert len(primary) == len(set(primary)) == 32 and set(primary) == cids | qids
    assert all(item.get("dispatched", False) is False for category in categories for item in queue[category])
    assert all(item["execution_status"] == "not_executed" for category in ["items", "actor_workflow_requests", "reference_review_requests"] for item in queue[category])

    roles = [r for r in a["assignments"] if r["role"] in ("public_reader", "investigator", "reviewer") and set(r["instance_ids"]) & ids]
    assert len(roles) == 36 and all(r["status"] == "completed" for r in roles)
    assert all(r["model"] == "gpt-6-astra" and r["reasoning_effort"] == "high" and r["fork_turns"] == "none" for r in roles)
    assert sum(len(r["sealed_outputs"]) for r in roles) == 60
    assert sum(len(t["artifact_sha256"]) for t in outputs["tasks"]) == 140
    reserve_c, reserve_q = len(cids & ids), len(qids & ids)
    assert reserve_c + reserve_q == 20
    for tid in ids:
        r = read(f"results/{tid}/screening_record.json")
        assert r["disposition"]["ready_for_probe"] is False
        assert r["disposition"]["static_classification"] == ("conditional_static_development_candidate" if tid in cids else "quality_first")
    first = a["first12_summary"]
    assert first["static_review_completed"] == 12
    assert first["conditional_development_candidates"] + reserve_c == len(cids)
    assert first["quality_first"] + reserve_q == len(qids)

    at = H["now"]()
    a["status"] = "frozen32_static_review_complete_reserve20_final_ready_for_parent_review"
    a["reserve20_summary"].update(completed_tasks=20, conditional_candidates=reserve_c,
        quality_first=reserve_q, remaining_tasks=0, total_batch_completed=32,
        final_report="reserve20_final_report.md", final_inventory="reserve20_final_inventory.json",
        parent_pending_tasks=32-a["reserve20_summary"]["total_batch_parent_accepted"], updated_at=at)
    a["events"].append({"at": at, "type": "reserve20_final_static_summary_completed",
        "report_ref": "reserve20_final_report.md", "inventory_ref": "reserve20_final_inventory.json",
        "first12_rescanned": False, "project_runtime_executed": False, "task2_dispatched": False})
    H["save"](a)

    decisions = [
        ("Project-MONAI__MONAI-1121", "pack05", "测试路径网络隔离与预定public_hints边界待明确；实际消息unknown", "验收契约"),
        ("Project-MONAI__MONAI-3566", "pack05", "题面默认DICOM读取与gold新增series_meta opt-in不一致", "验收契约"),
        ("Project-MONAI__MONAI-4583", "pack05", "2D/3D foreground坐标修复有正证据；dtype/稀疏3D范围有限", "实际actor公开流程"),
        ("conan-io__conan-11560", "pack06", "字面注释断言不能证明Bazel实际链接行为；alwayslink建议非绑定规格", "验收契约"),
        ("conan-io__conan-12397", "pack06", "cpp_link_args子串可命中objcpp_link_args，实际key可能错误", "私有CPU：生成键"),
        ("conan-io__conan-13403", "pack06", "autoreconf新增首参数影响旧非空位置args；mock未验证真实cwd", "私有CPU：旧位置参数/cwd"),
        ("dask__dask-6801", "pack07", "infer在PyArrow/schema_field_supported/object采样条件仍可能提前compute", "私有CPU：阶段调用次数"),
        ("dask__dask-7138", "pack07", "array改名array_like静态破坏旧array=关键字；无需CPU重证参数绑定", "参考兼容审查"),
        ("dask__dask-7305", "pack07", "quantiles调用已执行但精确端点未单独验收；大uint多分区残留待验", "私有CPU：精确端点/dtype"),
        ("pydantic__pydantic-5662", "pack08", "ANY反射比较修复有正证据；需保留一般matcher真假返回行为", "实际actor公开流程"),
        ("pydantic__pydantic-6043", "pack08", "递归排序与properties声明顺序的公开契约优先级待明确", "验收契约"),
        ("pydantic__pydantic-8316", "pack08", "A1从a_1变a1会传播到alias；实际旧键兼容性及契约未验", "私有CPU：alias输入/输出"),
        ("Project-MONAI__MONAI-5932", "pack09", "最长ID优先修复有正证据；长短引用顺序仍需公开流程核验", "实际actor公开流程"),
        ("Project-MONAI__MONAI-6975", "pack09", "None透传恢复Compose lazy配置；日志断言缺返回图像验收", "实际actor公开流程"),
        ("conan-io__conan-13610", "pack10", "裸-v新语义未公开明确；gold新增帮助说明不一致静态已证", "验收契约"),
        ("conan-io__conan-13788", "pack10", "普通build依赖的build_require_context=None被gold默认解释为host", "私有CPU：双profile锁重放"),
        ("dask__dask-7894", "pack11", "drop0/new0具体轴映射可能被gold破坏；none边界漏测另保留", "私有CPU：drop/new轴"),
        ("dask__dask-9212", "pack11", "跨module同名Enum表示固定碰撞，pure delayed用户结果未运行", "私有CPU：同函数联合compute"),
        ("pydantic__pydantic-8793", "pack12", "Annotated必填核心修复成立；缺值验证和default边界覆盖有限", "实际actor公开流程"),
        ("pydantic__pydantic-9066", "pack12", "普通dataclass默认实例可能触发未捕获TypeAdapter配置异常", "私有CPU：dataclass默认实例"),
    ]
    assert {row[0] for row in decisions} == ids
    lines = ["# 09-25 冻结储备20题：最终静态审查", "",
        f"新增20题全部完成：{reserve_c}项有条件静态开发候选、{reserve_q}项quality_first。连同已验首12题，冻结32题共{len(cids)}项候选、{len(qids)}项质量优先处理，全部ready_for_probe=false、needs_review/static_review、development_diagnostic。没有新项目执行或任务二派发，也没有训练/正式评测准入。", "",
        "首12和新增9题中期已获根任务验收；本最终交付覆盖新增全部20题，其中后11题提交根任务复核。当前32题静态产物完成与根任务已验21题是不同状态，不将提交等同验收。", "",
        "quality_first表示优先消解表中具体不确定性，不是通用CPU/模型门。候选也保留覆盖和actor限制；gold不是规格，缺覆盖不等于已证gold回归，历史grader可运行不等于实际actor可开发。", "",
        "| 新增题目 | 分类 | 核心证据与限制 | 唯一优先下一步 |",
        "| --- | --- | --- | --- |"]
    for tid, pack, finding, next_step in decisions:
        label = "候选" if tid in cids else "quality_first"
        lines.append(f"| [{tid}]({pack}_report.md) | {label} | {finding} | {next_step} |")
    lines += ["", "新增5项候选为MONAI4583/5932/6975、Pydantic5662/8793。它们有公开核心要求和局部修复正证据，但不是评分完备或模型成功保证。6975应在公开actor流程一起检查返回图像与lazy模式，applied_operations长度不等于resample调用次数；8793应包括缺值验证，Python3.8使用已有公开测试的typing_extensions.Annotated。", "",
        f"全32题后续清单共{len(queue['actor_workflow_requests'])}项实际actor公开开发需求、{len(queue['items'])}项私有CPU建议、{len(queue['acceptance_design_requests'])}项验收设计/契约建议、{len(queue['reference_review_requests'])}项参考兼容审查。每题仅一个当前优先类别，均未执行、未派发；任务二由Claude B负责，后续选择与环境执行不由本静态任务启动。详见[cpu_queue](cpu_queue.json)及各包followups。", "",
        "几处重要裁定：7894采用独立review具体drop+new_axis风险优先于主审depth-only漏接收实验，后者保留但不重复排程；9212的review改采同一pure delayed函数对照。13788严格区分Requirement.build_require_context与Node.context，并避免已含prev完整锁的强制重建混淆。9066保留dataclass配置异常疑点，同时否定旧‘warning普遍升级异常’及‘IP类别局部修复必属错误硬编码’推论。", "",
        "历史材料与环境：20题均核对授权noop/gold运行、目标失败、返回码、expected映射及恢复/投影。大P2P集合只做风险语义抽查，逐ID状态核对不冒充全文语义审计。1121的materials-v1确实修改了测试收集helper的__test__标记，不能称为仅改环境；Dask9212和Pydantic的历史安装修订则核过before/after配方，测试补丁/选择保持。raw source digest、派生actual image ID与当前actor身份分别记录；本地缺repair inventory不证明镜像缺资产。", "",
        "冻结与抽样：216减五批已审task_ids并集40，剩176，按公开类型和材料定位定向冻结32；这32不在该40内，不表示从未有L1记录。Modin5940/6937维持隔离。manifest SHA256为52649a38cadccdeacc2317f8d4fb7beee798247e2c9adbc00a198dea88261c7e，未改选样；不得把本批计数估作全池缺陷率。未扩读未授权跨题材料或据旧关系强制划分。", "",
        "来源与验证：新增20题有140份逐题产物、60份不可变初稿、40份原main短卡/record档案，36名审查角色（20公开、8主审、8复核）另加1名材料角色。所有审查角色显式请求gpt-6-astra/high/fork_turns=none；初稿封存后才释放历史/交叉资料。工具接受配置不等于后端认证或OS隔离，意见一致不提高证据等级。结构/时间/SHA及修订来源检查通过，不证明语义无遗漏或actor资格。", "",
        "中期反馈只改1121/6801/7305的可变短卡，并另存3份此前协调版本；原中期报告/清单及封存稿未改。首12报告、84份输出与24份修订档案沿用已验快照，本轮没有重新扫描。全冻结32据两阶段合计224份逐题输出、96份封存初稿、64份main档案；56名审查角色另加3名材料角色。", "",
        "交付：[最终清单](reserve20_final_inventory.json) · [140份输出校验](reserve20_final_output_verification.json) · [40份修订来源校验](reserve20_final_revision_provenance_verification.json) · [实际角色/release台账](assignments.json) · [协调阅读边界](reserve20_coordinator_read_notes.md) · [已验首12](first12_report.md) · [中期9题](reserve20_midpoint9_report.md)。原题、gold、评分、生产代码、父任务root_dispatch及环境交接未修改。", ""]
    # The concrete candidate sentence is checked against the final classification, not inferred from counts.
    assert cids & ids == {"Project-MONAI__MONAI-4583", "Project-MONAI__MONAI-5932", "Project-MONAI__MONAI-6975", "pydantic__pydantic-5662", "pydantic__pydantic-8793"}
    (B / "reserve20_final_report.md").write_text("\n".join(lines))

    amendments = []
    for package in read("reserve20_packages.json")["packages"]:
        revision_log = read(f"coordinator_revisions/{package['package_id']}/revision_log.json")
        for entry in revision_log["tasks"]:
            for amendment in entry.get("amendments", []):
                amendments.append({"instance_id": entry["instance_id"], **amendment})
        # Older coordinator logs may place the amendment array at package level.
        for amendment in revision_log.get("amendments", []):
            amendments.append(amendment)
    assert len(amendments) == 3
    verification_refs = [{"file": fn, "sha256": digest(fn)} for fn in [
        "reserve20_final_output_verification.json", "reserve20_final_revision_provenance_verification.json",
        "reserve20_material_check.json", "reserve20_coordinator_material_review.json",
        "pack05_monai1121_material_override_review.json"]]
    inventory = {"schema": "quality_expansion.reserve20_final_snapshot.v1", "as_of": at,
        "manifest_sha256": a["manifest_sha256"], "report": {"file": "reserve20_final_report.md", "sha256": digest("reserve20_final_report.md")},
        "counts": {"reserve_complete": 20, "overall_complete": 32, "reserve_candidates": reserve_c,
            "reserve_quality_first": reserve_q, "overall_candidates": len(cids), "overall_quality_first": len(qids),
            "task_artifacts": 140, "immutable_initials": 60, "archived_main_final_artifacts": 40,
            "reserve_review_roles": 36, "reserve_material_roles": 1,
            "overall_task_artifacts_from_stage_snapshots": 224, "overall_immutable_initials_from_stage_snapshots": 96,
            "overall_main_archives_from_stage_snapshots": 64, "overall_review_roles": 56, "overall_material_roles": 3},
        "parent_acceptance_as_of": {"first12": 12, "reserve_midpoint": 9, "final_reserve_remaining_pending": 11},
        "requested_role_configuration": "gpt-6-astra/high/fork_turns=none; tool accepted, not backend-attested",
        "roles": roles, "outputs": outputs["tasks"], "main_revision_provenance": revisions["artifacts"],
        "coordinator_wording_amendments": amendments, "verification_reports": verification_refs,
        "frozen_prior_snapshots_not_rescanned": [
            {"file": "first12_report.md", "sha256": "2e4686d1393826ec3dc2d7e69c8384d1412fdf14b77c956b80bcbb57090e8da9"},
            {"file": "first12_handoff_inventory.json", "sha256": "4a02fc81f53318e344f715117ae8806750c41c91b5b5cf2abd29a7d3a6c0e0b5"},
            {"file": "reserve20_midpoint9_report.md", "sha256": "9b8e2252cd92685b216b42b5981de67e3e3e4634909b2f3e66267687cd68bf70"},
            {"file": "reserve20_midpoint9_inventory.json", "sha256": "2109aa95b0960cca6b0d8ca699ae26a8f73616926716258be58e84d8bf41b449"}],
        "primary_followup_counts": {category: len(queue[category]) for category in categories},
        "ready_for_probe": False, "new_project_runtime_experiments": 0, "task2_dispatched": False,
        "limits": "Reserve metadata/hash snapshot only. Prior first12 artifacts are referenced from accepted snapshots, not rescanned. No semantic completeness, actual actor qualification, runtime result, or backend model attestation is inferred."}
    (B / "reserve20_final_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"report_sha256": digest("reserve20_final_report.md"), "inventory_sha256": digest("reserve20_final_inventory.json"), "counts": inventory["counts"], "amendments": len(amendments)}, ensure_ascii=False))


if __name__ == "__main__":
    finalize()
