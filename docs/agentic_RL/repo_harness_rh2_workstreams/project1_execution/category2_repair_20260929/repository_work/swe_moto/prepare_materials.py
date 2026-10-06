"""仅生成 Moto 私有修订草案并做离线检查；不导入 Moto 或执行评分。"""

from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


ROOT = next(p for p in Path(__file__).resolve().parents if (p / "AGENTS.md").is_file())
OUT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
SOURCES = {
    "5960": ("batch03", "tests/test_dynamodb/test_dynamodb.py"),
    "6114": ("batch04", "tests/test_rds/test_rds_clusters.py"),
    "6408": ("batch03", "tests/test_ecr/test_ecr_boto3.py"),
    "6185": ("batch03", "tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py"),
    "7584": ("batch02", "tests/test_sns/test_application_boto3.py"),
}


def asset(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise ValueError(f"替换锚点应恰好出现一次，实际 {text.count(old)} 次：{old[:80]!r}")
    return text.replace(old, new, 1)


def patch_text(old: str, new: str, file: str) -> str:
    return f"diff --git a/{file} b/{file}\n" + "".join(difflib.unified_diff(
        old.splitlines(keepends=True), new.splitlines(keepends=True),
        fromfile=f"a/{file}", tofile=f"b/{file}", n=3,
    ))


def apply_and_parse(base: Path, patch: Path) -> tuple[str, list[str]]:
    headers = [s[6:] for s in patch.read_text().splitlines() if s.startswith("+++ b/")]
    if not headers or len(headers) != len(set(headers)):
        raise ValueError(f"补丁文件列表无效：{patch}")
    with tempfile.TemporaryDirectory(prefix="moto-offline-") as scratch:
        scratch_path = Path(scratch)
        for file in headers:
            if file.startswith("/") or ".." in Path(file).parts:
                raise ValueError(f"越界文件：{file}")
            target = scratch_path / file
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((base / file).read_bytes())
        command = ["git", "-C", scratch, "apply"]
        subprocess.run(command + ["--check", str(patch)], check=True, capture_output=True, text=True)
        subprocess.run(command + [str(patch)], check=True, capture_output=True, text=True)
        for file in headers:
            ast.parse((scratch_path / file).read_text(), filename=file)
        return (scratch_path / headers[0]).read_text(), headers


def functions(text: str) -> dict[str, str]:
    return {n.name: ast.dump(n, include_attributes=False) for n in ast.parse(text).body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def make_5960(original: str) -> str:
    anchor = '    # Same when scanning the table\n    items = table.scan(IndexName="GSI-INC")["Items"]\n'
    original = replace_once(original, anchor, '    # Same when scanning the table\n    response = table.scan(IndexName="GSI-INC")\n    items = response["Items"]\n    assert response["Count"] == len(items) == 1\n')
    anchor = '\n\n@mock_dynamodb\ndef test_lsi_projection_type_keys_only():'
    addition = '''
    # 索引扫描只能投影返回值，不能损坏原表存储。
    assert table.get_item(Key={"partitionKey": "pk-1"})["Item"] == item


@mock_dynamodb
def test_gsi_scan_projection_keys_only_all_items():
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.create_table(
        TableName="scan-gsi-keys-only",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[
            {"AttributeName": "id", "AttributeType": "S"},
            {"AttributeName": "gsi_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[{
            "IndexName": "keys-only",
            "KeySchema": [{"AttributeName": "gsi_id", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "KEYS_ONLY"},
        }],
        BillingMode="PAY_PER_REQUEST",
    )
    originals = [
        {"id": "row-a", "gsi_id": "index-a", "payload": "alpha"},
        {"id": "row-b", "gsi_id": "index-b", "payload": "beta"},
    ]
    for item in originals:
        table.put_item(Item=item)

    response = table.scan(IndexName="keys-only")
    assert response["Count"] == len(response["Items"]) == 2
    assert sorted(response["Items"], key=lambda item: item["id"]) == [
        {"id": "row-a", "gsi_id": "index-a"},
        {"id": "row-b", "gsi_id": "index-b"},
    ]
    for item in originals:
        assert table.get_item(Key={"id": item["id"]})["Item"] == item
'''
    return replace_once(original, anchor, addition + anchor)


def make_6114(original: str) -> str:
    anchor = '''    client.describe_db_clusters(DBClusterIdentifier=cluster_arn)[
        "DBClusters"
    ].should.have.length_of(1)
'''
    return replace_once(original, anchor, '''    clusters = client.describe_db_clusters(DBClusterIdentifier=cluster_arn)["DBClusters"]
    assert len(clusters) == 1
    assert clusters[0]["DBClusterIdentifier"] == "cluster-id2"
    assert clusters[0]["DBClusterArn"] == cluster_arn

    # 名称与 ARN 必须定位到同一对象，不比较会随状态变化的整份响应。
    clusters_by_name = client.describe_db_clusters(DBClusterIdentifier="cluster-id2")["DBClusters"]
    assert len(clusters_by_name) == 1
    assert clusters_by_name[0]["DBClusterIdentifier"] == "cluster-id2"
    assert clusters_by_name[0]["DBClusterArn"] == cluster_arn
''')


def make_6408(original: str) -> str:
    anchor = '    assert new_image["imageManifest"] == image_manifests["image_002"]\n'
    return replace_once(original, anchor, anchor + '''
    # 查询迁移标签只能返回目标镜像，不能靠第一项顺序掩盖重复归属。
    moved = client.batch_get_image(repositoryName=repo_name, imageIds=[{"imageTag": tag_to_move}])
    assert moved["failures"] == []
    assert len(moved["images"]) == 1
    assert moved["images"][0]["imageManifest"] == image_manifests["image_002"]

    # 两侧原有标签与镜像均保留，迁移标签只属于目标。
    details = client.describe_images(repositoryName=repo_name)["imageDetails"]
    assert len(details) == 2
    by_digest = {image["imageDigest"]: image for image in details}
    assert len(by_digest) == 2
    expected = {
        initial_image["imageId"]["imageDigest"]: {"image_001"},
        new_image["imageId"]["imageDigest"]: {"image_002", tag_to_move},
    }
    assert set(by_digest) == set(expected)
    for digest, tags in expected.items():
        actual = by_digest[digest]["imageTags"]
        assert len(actual) == len(tags)
        assert set(actual) == tags
''')


def main() -> None:
    checks = []
    for tid, (batch, file) in SOURCES.items():
        package = RUNS / f"swegym_quality_{batch}_20260921_v1"
        task = f"getmoto__moto-{tid}"
        public = package / "public" / task
        private = package / "private" / task
        base = public / "base"
        original_patch = private / "test.patch"
        original, original_headers = apply_and_parse(base, original_patch)
        grading = json.loads((private / "grading.json").read_text())
        if grading["test_patch"].encode() != original_patch.read_bytes():
            raise ValueError(f"{tid} grading/test.patch 字节不一致")
        task_out = OUT / "tasks" / task
        task_out.mkdir(parents=True, exist_ok=True)
        if tid in {"6185", "7584"}:
            revised = ROOT / "rh2/experiments/category3_cloud_20260929" / f"moto{tid}" / "revised_test_v3.patch"
            material = json.loads((revised.parent / "materials_revised_v3.json").read_text())["tasks"][task]
            if material["test_patch"].encode() != revised.read_bytes() or material["revised_patch_sha256"] != asset(revised)["sha256"]:
                raise ValueError(f"{tid} cloud v3 内嵌字节/SHA 不一致")
            if material["original_patch_sha256"] != asset(original_patch)["sha256"]:
                raise ValueError(f"{tid} cloud v3 的原补丁身份与本地来源不一致")
        else:
            revised_text = {"5960": make_5960, "6114": make_6114, "6408": make_6408}[tid](original)
            revised = task_out / "revised_test_draft_v1.patch"
            revised.write_text(patch_text((base / file).read_text(), revised_text, file))
        effective, headers = apply_and_parse(base, revised)
        if headers != original_headers or headers != [file]:
            raise ValueError(f"{tid} 补丁触及文件变化")
        before, after = functions(original), functions(effective)
        changed = [name for name in before if before[name] != after.get(name)]
        added = [name for name in after if name not in before]
        allowed = {
            "5960": (["test_gsi_projection_type_include"], ["test_gsi_scan_projection_keys_only_all_items"]),
            "6114": (["test_describe_db_cluster_after_creation"], []),
            "6408": (["test_multiple_tags__ensure_tags_exist_only_on_one_image"], []),
            "6185": (["test_put_item__string_as_integer_value"], []),
            "7584": (["test_publish_to_deleted_platform_endpoint"], ["_assert_endpoint_does_not_exist"]),
        }[tid]
        if changed != allowed[0] or added != allowed[1]:
            raise ValueError(f"{tid} AST 修改范围不符：{changed}, {added}")
        checks.append({"instance_id": task, "status": "offline_checks_passed", "base_commit": grading["base_commit"],
                       "public_bundle": asset(public / "public_bundle.json"), "base_identity": asset(public / "base_identity.json"),
                       "grading": asset(private / "grading.json"), "base_test_file": asset(base / file),
                       "original_test_patch": asset(original_patch), "revised_test_patch": asset(revised),
                       "changed_functions": changed, "added_functions": added,
                       "original_reference_count": len(grading["fail_to_pass"]) + len(grading["pass_to_pass"]),
                       "patch_apply_check": True, "ast_parse": True, "cloud_embedded_identity_check": tid in {"6185", "7584"},
                       "runtime_validation": "not_run", "independent_review_of_new_draft": "pending" if tid in {"5960", "6114", "6408"} else "reuse_existing_review"})

        if tid == "5960":
            file = "moto/dynamodb/models/table.py"
            gold, _ = apply_and_parse(base, private / "gold.patch")
            start = gold.index("    def scan(\n")
            body = replace_once(gold[start:], "                index.project(result)\n",
                                "                if not (isinstance(index, GlobalSecondaryIndex) and index.projection.get(\"ProjectionType\") == \"KEYS_ONLY\"):\n                    index.project(result)\n")
            bad = gold[:start] + body
            control = task_out / "omit_keys_only.patch"
            control.write_text(patch_text((base / file).read_text(), bad, file))
            apply_and_parse(base, control)
        elif tid == "6408":
            file = "moto/ecr/models.py"
            s = (base / file).read_text()
            start = s.index("    def batch_get_image(")
            end = s.index("    def batch_delete_image(", start)
            body = replace_once(s[start:end], "        return response\n", '        if len(image_ids) == 1:\n            response["images"].reverse()\n        return response\n')
            control = task_out / "reorder_only.patch"
            control.write_text(patch_text(s, s[:start] + body + s[end:], file))
            apply_and_parse(base, control)
        elif tid == "6114":
            control = RUNS / "swegym_cpu_preprobe_20260929/task_inputs" / task / "private/degenerate_first_object.patch"
            apply_and_parse(base, control)
        else:
            control = None
        if control:
            checks[-1]["negative_control"] = asset(control)
            checks[-1]["negative_control_runtime"] = "not_run"
        candidate_files = [private / "gold.patch"]
        if tid in {"6185", "7584"}:
            candidate_files.extend(p for p in sorted(revised.parent.glob("*.patch")) if not p.name.startswith("revised_"))
            candidate_files.extend(sorted((revised.parent / "review/candidates").glob("*.patch")))
        elif control:
            candidate_files.append(control)
        for candidate in candidate_files:
            apply_and_parse(base, candidate)
        checks[-1]["candidate_assets"] = [asset(p) for p in candidate_files]
        checks[-1]["candidate_patch_apply_and_ast"] = True

    manifest_path = ROOT / "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/swe_materials/moto5406_next/materials_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    checked = 0
    for section in ["frozen_source_assets", "generated_assets"]:
        for value in manifest[section].values():
            actual = asset(ROOT / value["path"])
            if actual["sha256"] != value["sha256"] or actual["bytes"] != value["bytes"]:
                raise ValueError(f"Moto5406 冻结资产不符：{value['path']}")
            checked += 1
    checks.append({"instance_id": "getmoto__moto-5406", "status": "existing_asset_hashes_verified",
                   "manifest": asset(manifest_path), "checked_assets": checked,
                   "existing_isolated_code_path": "runs/category2_repair_20260929/d6_moto5406_implementation_v1/code_v1",
                   "runtime_validation": "not_run", "shared_publication": "pending"})

    report = {"schema": "moto.offline_material_checks.v1", "as_of": "2026-10-03", "scope": "private_draft_only",
              "no_moto_import_or_runtime": True, "no_shared_code_changes": True, "checks": checks}
    write_json(OUT / "offline_checks.json", report)
    print(json.dumps({"checked_tasks": len(checks), "report": str((OUT / "offline_checks.json").relative_to(ROOT)),
                      "runtime": "not_run"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
