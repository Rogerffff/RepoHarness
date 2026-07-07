"""frozen_v1 冻结记录：8 题的 digest 账本（生成 + 防漂移校验）。

`data/frozen_v1.json` 是 S1-2 的冻结固化产物，逐题记录：

    instance_id                     题目主键
    image                          官方镜像引用
    image_manifest_digest          镜像 manifest digest（题单冻结时核对 Docker Hub）
    problem_statement_sha256       题面原文 sha256（模型可见面的锚点）
    public_bundle_digest           PublicTaskBundle 规范化内容 digest
    private_grading_bundle_digest  PrivateGradingBundle 规范化内容 digest

它回答的问题是：**后续任何时刻加载出来的题目，还是不是 2026-07-09 用户确认冻结的
那 8 题**。`bundles.load_bundle_pairs` 默认对照本记录逐题重算比对（fail-closed），
任何对题面、评分材料、镜像 pin 的改动都会当场炸出来，而不是悄悄改变训练分布。

生成方式（确定性：同一份 swe_smoke_tasks.json 永远生成同一份记录，无运行期时间戳）：

    cd rh2 && uv run python -m repoharness2.envpack.freeze

注意生成动作本身不做"防漂移校验"（自举时记录还不存在/即将被覆盖），
但 public bundle 的泄漏扫描在 split_frozen_entry 里无条件执行。
"""

from __future__ import annotations

import json
from pathlib import Path

from repoharness2.contracts._base import canonical_json_digest
from repoharness2.envpack.bundles import (
    FROZEN_V1_FILE,
    TASKS_FILE,
    BundlePair,
    load_bundle_pairs,
)

FROZEN_SCHEMA_ID = "rh2.envpack.frozen_v1"


class FrozenRecordMismatch(ValueError):
    """加载出的题目与 frozen_v1 记录不符（题面/评分材料/镜像 pin 漂移），fail-closed。"""


def build_freeze_record(pair: BundlePair) -> dict:
    """单题冻结记录（纯函数：只依赖 bundle 内容，重算即比对）。"""

    return {
        "instance_id": pair.instance_id,
        "image": pair.public.image,
        "image_manifest_digest": pair.public.image_manifest_digest,
        "problem_statement_sha256": pair.public.problem_statement_sha256,
        "public_bundle_digest": pair.public.digest(),
        "private_grading_bundle_digest": pair.private.digest(),
    }


def build_frozen_v1(tasks_file: Path | str = TASKS_FILE) -> dict:
    """从冻结题目数据生成完整 frozen_v1 记录（含 meta 与全文件 digest 锚点）。"""

    source_path = Path(tasks_file)
    payload_meta = json.loads(source_path.read_text()).get("meta", {})
    pairs = load_bundle_pairs(tasks_file, frozen_file=None)  # 自举：不对照自身
    records = [build_freeze_record(pair) for pair in pairs]
    return {
        "schema_id": FROZEN_SCHEMA_ID,
        "meta": {
            # 冻结事实（来自 s0/swe_smoke_report.md §1 与 C2 状态同步，非运行期时间）。
            "frozen_at": "2026-07-09",
            "frozen_by": "user-confirmed (C6 选题 + C2 状态同步)",
            "task_count": len(records),
            "dataset": payload_meta.get("dataset", ""),
            "swebench_version": payload_meta.get("swebench_version", ""),
            "source_tasks_file": source_path.name,
            # 源数据文件字节流 sha256：把 140KB 原始冻结数据也锚进账本。
            "source_tasks_file_sha256": sha256_of_file(source_path),
            # 记录本体的规范化 digest（不含本字段自身），inspector 四步范式第一步用。
            "records_digest": canonical_json_digest(records),
        },
        "tasks": records,
    }


def sha256_of_file(path: Path | str) -> str:
    import hashlib

    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_frozen_v1(frozen_file: Path | str = FROZEN_V1_FILE) -> dict:
    frozen = json.loads(Path(frozen_file).read_text())
    if frozen.get("schema_id") != FROZEN_SCHEMA_ID:
        raise FrozenRecordMismatch(
            f"{frozen_file}: schema_id={frozen.get('schema_id')!r} 不是 {FROZEN_SCHEMA_ID}"
        )
    return frozen


def verify_pairs_against_frozen(
    pairs: list[BundlePair], frozen_file: Path | str = FROZEN_V1_FILE
) -> None:
    """逐题重算 digest 与 frozen_v1 记录比对，任一字段不符即抛 FrozenRecordMismatch。

    只校验 pairs 覆盖的题（subset 加载时不要求全量在场），但 subset 里的每一题
    必须出现在冻结记录里。
    """

    frozen = load_frozen_v1(frozen_file)
    by_id = {rec["instance_id"]: rec for rec in frozen["tasks"]}
    problems: list[str] = []
    for pair in pairs:
        expected = by_id.get(pair.instance_id)
        if expected is None:
            problems.append(f"{pair.instance_id}: 不在 frozen_v1 记录里")
            continue
        actual = build_freeze_record(pair)
        for key, expected_value in expected.items():
            if actual.get(key) != expected_value:
                problems.append(
                    f"{pair.instance_id}.{key}: 冻结记录 {expected_value!r} != 重算 {actual.get(key)!r}"
                )
    if problems:
        raise FrozenRecordMismatch(
            "frozen_v1 防漂移校验失败（题目数据被改动或记录未再生成）：\n  - "
            + "\n  - ".join(problems)
        )


def write_frozen_v1(
    tasks_file: Path | str = TASKS_FILE, frozen_file: Path | str = FROZEN_V1_FILE
) -> Path:
    frozen_path = Path(frozen_file)
    frozen_path.write_text(
        json.dumps(build_frozen_v1(tasks_file), ensure_ascii=False, indent=1) + "\n"
    )
    return frozen_path


if __name__ == "__main__":
    path = write_frozen_v1()
    frozen = load_frozen_v1(path)
    print(f"frozen_v1 written -> {path}")
    print(f"tasks={frozen['meta']['task_count']} records_digest={frozen['meta']['records_digest']}")
    for record in frozen["tasks"]:
        print(
            f"  {record['instance_id']}: public={record['public_bundle_digest'][:19]}… "
            f"private={record['private_grading_bundle_digest'][:19]}…"
        )
