"""复核者私有对照驱动：逐个变体调用 semantic_control.py（断网、一次性、root 容器，原镜像 c3keep/pydantic8316:src），
每个变体启动前等待机器上的容器数 < 3（复核须知）；同一时间只有本脚本的 1 个容器。
每个变体执行：环境信息、review_behavior.py、私有模拟评分（原 test_patch、作者 v2、复核草案 v3，各跑 tests/test_utils.py），
以及 v3 在 UID 54322 下的一次复跑。不跑正式评分。
用法：python run_review.py <gold.patch> [变体名 ...]（不给变体名时跑全部）
输出：review/out/sem/<变体>/…（被 .gitignore 忽略；负责人定稿后按需 git add -f）
"""
import json
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP = HERE.parent
TOOL = EXP.parents[1] / "task2_swegym_dev_20260925" / "semantic_control.py"
OUT = HERE / "out"
IMAGE = "c3keep/pydantic8316:src"
AUTHOR = ["keep_digit", "lookaround", "scan", "upstream_main", "normalize", "lead_only", "first_only", "acr3",
          "lower_or_start", "lower_or_start_la", "skip_if_underscore", "skip_if_digit", "no_lower_upper",
          "no_trailing_upper", "acr_max5", "acr_max4", "literal", "only_if_no_us", "no_digit_split", "no_digit_upper"]
MINE = sorted(p.stem for p in (HERE / "candidates").glob("*.patch"))
PYTEST = "python -m pytest -p no:cacheprovider -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_utils.py"


def run_with(patch: str, uid: bool = False) -> str:
    prefix = "setpriv --reuid=54322 --regid=54322 --clear-groups env HOME=/tmp " if uid else ""
    return (f"git apply /in/{patch} && {prefix}{PYTEST}; rc=$?; git apply -R /in/{patch}; exit $rc")


COMMANDS = [
    {"id": "b0_env", "cmd": "python -c \"import sys, pydantic, pydantic_core; print(sys.version); print(pydantic.VERSION, "
                            "pydantic_core.__version__)\"; git rev-parse HEAD; git status --short | head; id; which setpriv",
     "timeout_s": 120},
    {"id": "b1_behavior", "cmd": "python /in/review_behavior.py", "timeout_s": 300},
    {"id": "s_orig", "cmd": run_with("original_test.patch"), "timeout_s": 600},
    {"id": "s_v2", "cmd": run_with("revised_test_v2.patch"), "timeout_s": 600},
    {"id": "s_v3", "cmd": run_with("revised_test_v3_draft.patch"), "timeout_s": 600},
    {"id": "s_v3_uid54322", "cmd": run_with("revised_test_v3_draft.patch", uid=True), "timeout_s": 600},
]


def main() -> None:
    gold = Path(sys.argv[1]).resolve()
    wanted = sys.argv[2:]
    variants = {"base": [], "gold": ["git apply /in/gold.patch"]}
    files = {"gold.patch": str(gold), "review_behavior.py": str(HERE / "review_behavior.py"),
             "original_test.patch": str(EXP / "original_test.patch"),
             "revised_test_v2.patch": str(EXP / "revised_test_v2.patch"),
             "revised_test_v3_draft.patch": str(HERE / "revised_test_v3_draft.patch")}
    for name in AUTHOR:
        variants[name] = [f"git apply /in/{name}.patch"]
        files[f"{name}.patch"] = str(EXP / f"{name}.patch")
    for name in MINE:
        variants[name] = [f"git apply /in/{name}.patch"]
        files[f"{name}.patch"] = str(HERE / "candidates" / f"{name}.patch")
    if wanted:
        variants = {k: v for k, v in variants.items() if k in wanted}
    (OUT / "specs").mkdir(parents=True, exist_ok=True)
    for vname, prep in variants.items():
        spec = {"image": IMAGE, "python_prefix": "/opt/miniconda3/envs/testbed", "variants": {vname: prep},
                "files": files, "commands": COMMANDS}
        sp = OUT / "specs" / f"{vname}.json"
        sp.write_text(json.dumps(spec, ensure_ascii=False, indent=1))
        while int(subprocess.run("docker ps -q | wc -l", shell=True, capture_output=True, text=True).stdout.strip()) >= 3:
            time.sleep(20)
        t0 = time.time()
        r = subprocess.run([sys.executable, str(TOOL), str(sp), "--out", str(OUT / "sem")], capture_output=True, text=True)
        print(vname, f"{time.time() - t0:.0f}s", r.stdout.strip()[-300:], r.stderr.strip()[-300:], flush=True)


if __name__ == "__main__":
    main()
