"""用两份现存真实覆盖条目，模拟摘要读取之后生产者完整替换覆盖表的交错。"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch


OUT = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--binding-run-dir", type=Path, default=OUT, help="probe_actor_binding.py 已输出的 run_dir；默认复用首次审查证据")
args = parser.parse_args()
ROOT = next(p for p in OUT.parents if (p / "rh2/src/repoharness2").is_dir())
sys.path.insert(0, str(ROOT / "rh2/src"))
from repoharness2.adapters.slime.prepared_task_face import PreparedTaskFace
from repoharness2.envpack.environment_overlay import load_environment_overlays


TID = "r2e_gym_subset::orange3__9b5494e26f407b75e79699c9d40be6df1d80a040"
source_a = "runs/r2e_t0_batch3_20260924/derived6/overlays.jsonl"
source_b = "runs/r2e_t0_batch3_20260924/derived7/overlays.jsonl"
a = load_environment_overlays(ROOT / source_a)[TID]
b = load_environment_overlays(ROOT / source_b)[TID]
assert a.derived_image_id != b.derived_image_id
data_a = (a.model_dump_json() + "\n").encode()
data_b = (b.model_dump_json() + "\n").encode()
path = OUT / "swappable_overlay.jsonl"
path.write_bytes(data_a)
sha_a = hashlib.sha256(data_a).hexdigest()
prep = args.binding_run_dir / "prepared_probe"
summary = json.loads((prep / "public/replay_summary.json").read_text())
real_read = Path.read_bytes
interleaving = []


def replace_after_read(self):
    data = real_read(self)
    if self == path:
        interleaving.append("read A bytes for supplied SHA-256")
        # 与一个构建/同步进程在两次 open 之间完整替换该文件等价。只改审查目录的副本。
        self.write_bytes(data_b)
        interleaving.append("replace file with unchanged real B overlay before loader reopens it")
    return data


with patch.object(Path, "read_bytes", replace_after_read):
    face = PreparedTaskFace.load(
        prepared_dir=prep / "public", manifest_sha256=summary["prepared_manifest_sha256"],
        host_grading_path=prep / "private/host_grading_views.jsonl", host_grading_sha256=summary["host_grading_artifact_sha256"],
        time_budget_seconds=600, image_overlays_path=path, image_overlays_sha256=sha_a,
    )
selected = face.rollout_spec(TID).image
assert selected == b.derived_image_id
assert selected != a.derived_image_id
result = {
    "scope": "CPU only, deterministic interleaving at real PreparedTaskFace.load; both overlay records come unchanged from saved evidence. No Docker or concurrent-process timing claim.",
    "source_a": source_a, "source_b": source_b, "task_id": TID,
    "expected_overlay_sha256": sha_a, "consumed_file_sha256": hashlib.sha256(data_b).hexdigest(),
    "authorized_by_expected_sha_image": a.derived_image_id, "selected_image": selected,
    "interleaving": interleaving, "unexpected_second_snapshot_accepted": selected != a.derived_image_id,
}
(OUT / "probe_overlay_read_race.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"unexpected_second_snapshot_accepted": True, "selected_image": selected}, ensure_ascii=False))
