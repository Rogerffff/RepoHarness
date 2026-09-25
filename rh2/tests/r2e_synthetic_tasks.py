"""R2E 合成来源夹具（不是测试模块，无 test_ 前缀）。

- R-a 构造器（原在 tests/envpack/test_ingest_r2e_subset.py，移到这里共用）：一行来源 + 一条镜像事实，
  经真实 `ingest_r2e_subset` 得到四面产物；
- R-e 组级运输（tests/adapters_miles/test_r2e_group_transport.py）用的混来源 trusted-prep：一题 SWE
  （getmoto__moto-1）+ 一题 R2E（demo__fff…），形状同 r2e_local_review_20260922 评审探针的 `mixed_fixture`。
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from repoharness2.envpack import ingest_r2e_subset as r2e
from repoharness2.envpack.prepared_tasks import prepare_tasks
from repoharness2.envpack.r2e_parsers import R2E_DATASET_REVISION
from repoharness2.envpack.training_view import TrustedTaskController
from w1b_synthetic_tasks import BASE_COMMIT, IMG_DIG, TID1, PreparedFixture, make_result

R2E_FIX_COMMIT = "a" * 40  # 合成来源行的 commit_hash（R-a 构造器默认值）
R2E_IMAGE_HEAD = "b" * 40  # 镜像事实里的 git HEAD：base_commit 取它，不取来源行的符号形式
_R2E_MIXED_COMMIT = "f" * 40  # 混来源夹具里 R2E 题的来源 commit
R2E_TID = "r2e_gym_subset::demo__" + _R2E_MIXED_COMMIT
# 混来源夹具的 R2E 期望映射：三种期望状态各一键
R2E_MIXED_EXPECTED = {"TestCore.test_x": "PASSED", "TestCore.test_legacy": "FAILED", "TestCore.test_env": "ERROR"}


# ---------------------------------------------------------------------------
# R-a 构造器（小而完整：一行来源 + 一条镜像事实）
# ---------------------------------------------------------------------------


def make_commit_doc(commit: str = R2E_FIX_COMMIT) -> dict:
    hunk = {
        "descriptor": {"old_range": {"start": 1, "length": 1}, "new_range": {"start": 1, "length": 1}, "section": ""},
        "line_group": {"all_lines": [{"content": "x = 1", "type": "deleted"}, {"content": "x = 2", "type": "added"}]},
    }

    def _fd(path: str) -> dict:
        return {
            "header": {"file": {"path": path}, "misc_line": None},
            "index_line": {"old_commit_hash": "1111111", "new_commit_hash": "2222222", "mode": "100644"},
            "minus_file": {"path": f"a/{path}"}, "plus_file": {"path": f"b/{path}"},
            "hunks": [hunk], "old_file_content": "x = 1\n", "new_file_content": "x = 2\n",
        }

    return {
        "old_commit_hash": commit + "^", "new_commit_hash": commit, "commit_message": "fix", "commit_date": "2020",
        "metadata": {}, "file_diffs": [_fd("pkg/core.py"), _fd("tests/test_core.py"), _fd("docs/notes.rst")],
    }


def make_r2e_row(repo: str = "demo", commit: str = R2E_FIX_COMMIT) -> dict:
    return {
        "repo_name": repo,
        "docker_image": f"namanjain12/{repo}_final:{commit}",
        "commit_hash": commit,
        "parsed_commit_content": json.dumps(make_commit_doc(commit)),
        "execution_result_content": "{}",
        "modified_files": ["pkg/core.py"],
        "modified_entity_summaries": [],
        "relevant_files": ["pkg/core.py"],
        "num_non_test_files": 1,
        "num_non_test_func_methods": 1,
        "num_non_test_lines": 2,
        "prompt": "You are an expert software engineer tasked with creating informative GitHub issues ...",
        "problem_statement": "[ISSUE]\n\n**Title:** x should be 2\n\n**Description:** it is 1.\n[/ISSUE]",
        "expected_output_json": json.dumps({"TestCore.test_x": "PASSED", "TestCore.test_legacy": "FAILED"}),
    }


def make_r2e_facts_doc(repo: str = "demo", commit: str = R2E_FIX_COMMIT, *, expected_n: int = 2) -> dict:
    entry = ".venv/bin/python -W ignore -m pytest -rA r2e_tests"
    return {
        "schema": r2e.IMAGE_FACTS_SCHEMA, "generated_by": "test", "machine": "test", "n": 1,
        "tasks": [{
            "commit_hash": commit, "commit12": commit[:12], "repo": repo, "collect_status": "OK",
            "source": "R2E-Gym/R2E-Gym-Subset", "source_revision": R2E_DATASET_REVISION,
            "image_ref": f"namanjain12/{repo}_final:{commit}",
            "image": {"repo_digest": f"namanjain12/{repo}_final@sha256:" + "c" * 64, "workdir": "/testbed"},
            "git": {"head": R2E_IMAGE_HEAD, "head_is_ancestor_of_fix": "yes"},
            "run_tests_sh": {"text": entry, "sha256": hashlib.sha256(entry.encode()).hexdigest()},
            "r2e_tests": {"n_files": 2, "files": [
                {"path": "/r2e_tests/test_1.py", "sha256": hashlib.sha256(b"t").hexdigest()},
                {"path": "/r2e_tests/__init__.py", "sha256": hashlib.sha256(b"").hexdigest()},
            ]},
            "expected_n": expected_n,
        }],
    }


def ingest_r2e_synthetic(rows=None, facts_doc=None, **kw) -> r2e.R2EIngestResult:
    rows = [make_r2e_row()] if rows is None else rows
    facts = r2e.parse_r2e_image_facts(make_r2e_facts_doc() if facts_doc is None else facts_doc)
    return r2e.ingest_r2e_subset(
        rows=rows, image_facts=facts, raw_archive_sha256="sha256:" + "1" * 64,
        image_facts_sha256="sha256:" + "2" * 64, source_revision=R2E_DATASET_REVISION,
        expected_task_count=kw.pop("expected_task_count", len(rows)), **kw,
    )


# ---------------------------------------------------------------------------
# R-e 组级运输：一题 SWE + 一题 R2E 的 trusted-prep
# ---------------------------------------------------------------------------


def prepare_mixed_swe_and_r2e(root: Path) -> PreparedFixture:
    """在 root 下跑一次 trusted-prep（TID1 + R2E_TID，按此顺序派发）：root/prepared 公开、root/private 私有。

    R2E 题的镜像事实对齐 miles 链上的 rollout 替身：HEAD = BASE_COMMIT（fake docker 血缘探针应答），
    repo_digest 的 sha256 = IMG_DIG（`_PreparedDocker` 的 RepoDigests 应答）。
    """

    row = make_r2e_row(commit=_R2E_MIXED_COMMIT)
    row["expected_output_json"] = json.dumps(R2E_MIXED_EXPECTED)
    facts = make_r2e_facts_doc(commit=_R2E_MIXED_COMMIT, expected_n=len(R2E_MIXED_EXPECTED))
    facts["tasks"][0]["git"]["head"] = BASE_COMMIT
    facts["tasks"][0]["image"]["repo_digest"] = "namanjain12/demo_final@" + IMG_DIG
    r2e_result = ingest_r2e_synthetic([row], facts)
    controller = TrustedTaskController.build_for_tests_from_ingest_result(make_result(("getmoto__moto-1",)), r2e_result)
    prepared_dir = root / "prepared"
    private_dir = root / "private"
    manifest = prepare_tasks(controller, out_dir=prepared_dir, private_dir=private_dir, task_ids=[TID1, R2E_TID])
    return PreparedFixture(controller=controller, prepared_dir=prepared_dir, private_dir=private_dir, manifest=manifest)
