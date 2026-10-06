"""重建带此前 B 改动、去掉本轮 I21 的临时树，辨别 6 个导入失败；不修改共享工作树。"""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "rh2/src/repoharness2").is_dir())
OUT = Path(__file__).resolve().parent
I21_OWNED = {
    "rh2/src/repoharness2/adapters/miles/attempt_assignment.py",
    "rh2/src/repoharness2/adapters/miles/drop_events.py",
    "rh2/src/repoharness2/adapters/miles/generate_fn.py",
    "rh2/src/repoharness2/adapters/miles/identity.py",
    "rh2/src/repoharness2/adapters/miles/run_report.py",
    "rh2/tests/adapters_miles/test_w1b_prepared_chain.py",
}
NEW_I21 = {
    "rh2/src/repoharness2/adapters/miles/eval_report.py",
    "rh2/src/repoharness2/adapters/slime/eval_result.py",
    "rh2/src/repoharness2/adapters/slime/eval_wiring.py",
}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    head = git("rev-parse", "HEAD").decode().strip()
    copied, reversed_hunks = [], {}
    with tempfile.TemporaryDirectory(prefix="rh2-pre-i21-with-b-") as directory:
        tree = Path(directory)
        with tarfile.open(fileobj=io.BytesIO(git("archive", head, "rh2"))) as archive:
            archive.extractall(tree, filter="data")
        for folder in ("reference", "docs"):
            (tree / folder).symlink_to(ROOT / folder, target_is_directory=True)
        paths = set(git("diff", "--name-only", "HEAD", "--", "rh2/src", "rh2/tests", "rh2/scripts").decode().splitlines())
        paths.update(git("ls-files", "--others", "--exclude-standard", "rh2/src", "rh2/tests", "rh2/scripts").decode().splitlines())
        for path in sorted(paths):
            if path in I21_OWNED or path in NEW_I21 or Path(path).name.startswith("test_i21_"):
                continue
            source, dest = ROOT / path, tree / path
            if not source.is_file():
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest)
            copied.append(path)
        for name in ("bringup.py", "generate.py"):
            path = "rh2/src/repoharness2/adapters/slime/" + name
            diff = git("diff", "HEAD", "--", path).decode()
            parts = re.split(r"(?m)(?=^@@ )", diff)
            # 已逐 hunk 对照 Claude §11.1：bringup 只有缓存计数 hunk 属 B；generate 的四个 I21
            # 接线位置均带 I21 注释，其余 exporter / cache 等改动全部保留。
            chosen = [h for h in parts[1:] if ("omitted_cache_counts" not in h if name == "bringup.py" else "I21" in h)]
            reversed_hunks[path] = [h.splitlines()[0] for h in chosen]
            subprocess.run(["git", "apply", "--reverse", "--check"], input=(parts[0] + "".join(chosen)).encode(), cwd=tree, check=True)
            subprocess.run(["git", "apply", "--reverse"], input=(parts[0] + "".join(chosen)).encode(), cwd=tree, check=True)
        env = dict(os.environ, PYTHONPATH=str(tree / "rh2/src"))
        env.pop("RH2_MILES_PATH", None)
        cmd = [str(ROOT / "rh2/.venv/bin/python"), "-m", "pytest", "tests/", "-m", "not docker", "-k", "dp_schedule_differential", "-q", "--tb=short"]
        done = subprocess.run(cmd, cwd=tree / "rh2", env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log = done.stdout.replace(str(tree), "<pre-i21-with-b>").replace(str(ROOT), "<repo>")
        (OUT / "pre_i21_dp.log").write_text(log)
        result = {"baseline_head": head, "preserved_worktree_files": copied, "restored_head_files": sorted(I21_OWNED),
                  "removed_i21_new_files": sorted(NEW_I21), "removed_test_pattern": "test_i21_*",
                  "reversed_shared_hunks": reversed_hunks, "exit_code": done.returncode, "tail": log.splitlines()[-10:]}
        (OUT / "pre_i21_dp.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
