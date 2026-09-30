"""把 runs/ 下某题的云端证据复制到提交目录，并为 runs/ 下该题的全部文件（含未复制的）写 SHA256 清单。

云端容器是临时的，runs/ 被 git 忽略；因此账本、评分日志、私有对照输出等小文件随提交保存。
prepared/private 任务面可从已提交的 ingest 重建，只登记摘要。
评分导出的 artifacts/ 里，实际被评分的候选补丁（candidate.patch）、frozen_patch/classification/stage/projection
等小文件是唯一的必要输入，照常归档（09-30 按 Codex 复核意见修正：不再因目录名统一排除）；
超过 64 KB 的 artifacts 文件（每次重复的 baseline_manifest.json 等，可由镜像重建）只登记摘要。
用法：python archive_evidence.py <runs 下的题目录> <docs 证据目录>
"""
import hashlib
import json
import shutil
import sys
from pathlib import Path

SKIP_DIRS = {"prepared", "private"}
MAX_BYTES = 2_000_000
ARTIFACT_MAX_BYTES = 64_000

src, dst = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
dst.mkdir(parents=True, exist_ok=True)
manifest = []
for f in sorted(p for p in src.rglob("*") if p.is_file()):
    rel = f.relative_to(src)
    data = f.read_bytes()
    entry = {"path": str(rel), "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
    skipped = next((part for part in rel.parts[:-1] if part in SKIP_DIRS), None)
    if skipped:
        entry["archived"] = f"no ({skipped}: reproducible from committed ingest)"
    elif "artifacts" in rel.parts[:-1] and len(data) > ARTIFACT_MAX_BYTES:
        entry["archived"] = "no (artifacts: over 64 KB, repeated or reproducible from the image)"
    elif len(data) > MAX_BYTES:
        entry["archived"] = "no (over 2 MB)"
    else:
        out = dst / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, out)
        entry["archived"] = "yes"
    manifest.append(entry)
(dst / "evidence_manifest.json").write_text(json.dumps(
    {"source_dir": str(src.relative_to(Path.cwd())) if src.is_relative_to(Path.cwd()) else str(src),
     "files": manifest}, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"files": len(manifest), "archived": sum(e["archived"] == "yes" for e in manifest),
                  "archived_bytes": sum(e["bytes"] for e in manifest if e["archived"] == "yes")}))
