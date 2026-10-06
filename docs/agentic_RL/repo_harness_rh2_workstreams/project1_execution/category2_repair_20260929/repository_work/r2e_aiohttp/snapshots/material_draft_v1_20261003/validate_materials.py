"""用现有生产摄入纯函数检查本包草案；不写共享产物、不启动运行时。"""

from __future__ import annotations

import ast
import json
import sys
from dataclasses import replace
from pathlib import Path

from prepare_materials import HERE, ROOT, S2, dump, sha

sys.path.insert(0, str(ROOT / "rh2/src"))
from repoharness2.envpack.ingest_r2e_subset import (
    build_r2e_task,
    parse_r2e_image_facts,
    parse_r2e_material_revisions,
)


def main() -> None:
    manifest = json.loads((HERE / "material_manifest.json").read_text())
    for rel, digest in manifest["sources"].items():
        assert sha((ROOT / rel).read_bytes()) == digest, f"父材料已变化：{rel}"
    raw_file = S2 / "raw/r2e_gym_subset_48_e8b9fcbc.jsonl"
    raw = {x["commit_hash"]: x for x in map(json.loads, raw_file.read_text().splitlines())}
    facts_file = S2 / "raw/r2e_image_facts_m3_48.json"
    facts = parse_r2e_image_facts(json.loads(facts_file.read_text()))
    official = parse_r2e_material_revisions(json.loads((S2 / "revisions/material_revisions_v11.json").read_text()))
    proposed = parse_r2e_material_revisions(json.loads((HERE / "revision_draft.json").read_text()))
    source_revision = (S2 / "raw/r2e_subset.revision").read_text().strip()
    results = []

    def hydrate(rev, directory: Path | None):
        if rev.revised_file is None:
            return rev
        path = ROOT / rev.revised_file if directory is None else directory / Path(rev.revised_file).name
        content = path.read_bytes()
        assert sha(content) == rev.sha256_after, f"修订全文摘要不符：{path}"
        return replace(rev, revised_content=content)

    for task in manifest["tasks"]:
        iid = task["instance_id"]
        directory = HERE / "materials" / iid.split("__", 1)[1][:8]
        for filename, digest in task["local_files"].items():
            path = directory / filename
            assert sha(path.read_bytes()) == digest, f"本地材料已变化：{path}"
            if path.suffix == ".py":
                ast.parse(path.read_text())
        new = proposed[iid]
        replaced_targets = {rev.target for rev in new}
        existing = [hydrate(rev, None) for rev in official[iid] if rev.target not in replaced_targets]
        selected = tuple(sorted(existing + [hydrate(rev, directory) for rev in new], key=lambda rev: rev.revision_id))
        row = raw[iid.split("__", 1)[1]]
        fact = next(v for v in facts.values() if v.repo == row["repo_name"] and v.commit_hash == row["commit_hash"])
        public, grading, _, _ = build_r2e_task(
            row, fact, raw_archive_sha256=sha(raw_file.read_bytes()),
            image_facts_sha256=sha(facts_file.read_bytes()), source_revision=source_revision,
            revisions=selected,
        )
        statement = directory / "problem_statement.txt"
        if statement.exists():
            assert public.problem_statement == statement.read_text()
        for block in public.problem_statement.split("```python\n")[1:]:
            ast.parse(block.split("```", 1)[0])
        if "expected_count_after" in task:
            assert len(grading.expected_map()) == task["expected_count_after"]
        else:
            assert grading.hidden_tests_tree_sha256 == task["parent_grading"]["hidden_tests_tree_sha256"]
            assert grading.expected_output_json_sha256 == task["parent_grading"]["expected_output_json_sha256"]
        # 只供干净公开读者：不带 gold、期望映射、私有测试、候选及内部结论。
        dump(directory / "public_reader_bundle.json", public.model_dump(mode="json"))
        results.append({"instance_id": iid, "production_ingest_pure_functions": "passed",
                        "public_statement_sha256": public.problem_statement_sha256,
                        "hidden_tests_tree_sha256": grading.hidden_tests_tree_sha256,
                        "expected_output_json_sha256": grading.expected_output_json_sha256,
                        "expected_count": len(grading.expected_map()),
                        "material_revisions_for_local_check_only": grading.material_revisions})

    # 确认 4075 窄替换修的是线上字节，不是只改文字。
    old = "\xffoo: bar".encode()
    old_request = f"POST / HTTP/1.1\r\n{old}\r\n\r\n".encode()
    new = "\xffoo: bar"
    new_request = f"POST / HTTP/1.1\r\n{new}\r\n\r\n".encode()
    assert b"b'" in old_request and b"b'" not in new_request
    assert new.encode() in new_request and new.encode() not in old_request
    dump(HERE / "local_validation.json", {
        "as_of": "2026-10-03", "kind": "offline_production_ingest_functions_not_publication",
        "tasks": results, "header_bytes_check": "passed", "source_hashes_unchanged": True,
        "cpu_acceptance": "not_run", "independent_review": "pending",
        "formal_pins_or_ingest_written": False,
        "limitations": ["未执行正式评分或 actor 开发命令", "未捕获实际 solver 消息",
                        "未检验目标 Linux 镜像内的兼容性与收集键", "本地编号仅为草案解析检查"],
    })
    print(json.dumps({"offline_ingest_checks": len(results), "header_bytes_check": "passed",
                      "cpu_acceptance": "not_run"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
