"""S0-7 题单冻结脚本：从 SWE-bench Verified 选定 8 题并生成 SweSmokeTaskset 的冻结数据文件。

职责（只在本机跑一次，产物随代码同步到远程）：
    1. 按 C6 标准选题（题单直接硬编码在 PICKED 里——这就是"冻结"动作本身，
       重跑脚本只会重新生成同一份数据，不会改题单）。
    2. 用 pinned swebench（4.1.0）的 make_test_spec 生成每题的官方 eval 脚本
       （含 golden test_patch、官方测试命令与 '>>>>> Start/End Test Output' 标记）。
    3. 向 Docker Hub registry API 核对每题官方 x86_64 镜像存在，并记录 manifest digest。
    4. 写出 rh2/src/repoharness2/envpack/data/swe_smoke_tasks.json（S1-2 起题目数据归
       envpack 库层所有；重新生成后必须同步重跑 `python -m repoharness2.envpack.freeze`
       再生成 frozen_v1.json，否则加载时防漂移校验会 fail-closed 拒绝）。

C6 选题标准与本次落点：
    - 官方预构建 x86_64 镜像存在：docker.io/swebench/sweb.eval.x86_64.<instance_id 中
      `__` 替换为 `_1776_`>:latest（swebench 4.1.0 make_test_spec(namespace="swebench")
      的 instance_image_key），本脚本逐题核对 manifest。
    - Python 主流仓库：django×3、sympy×2、requests×2、astropy×1。
    - 单题测试 < 5 分钟：静态代理指标是 F2P+P2P 测试数量与测试命令范围
      （django 按模块跑 runtests、sympy bin/test 单文件、requests/astropy pytest 单文件），
      真实耗时在 S0-7 远程执行时逐题记录。

用法（在仓库根目录）：
    rh2/.venv/bin/python rh2/experiments/s0_swe_smoke_prep.py
依赖：rh2/.venv 内额外 `uv pip install swebench==4.1.0`（未写入 pyproject，
    属 S0 实验期临时依赖，见 implementation-notes S0-7 条目）。
"""

import json
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = (
    REPO_ROOT / "rh2" / "src" / "repoharness2" / "envpack" / "data" / "swe_smoke_tasks.json"
)

DATASET = "princeton-nlp/SWE-bench_Verified"
SPLIT = "test"
NAMESPACE = "swebench"
ARCH = "x86_64"

# ---------------------------------------------------------------------------
# 冻结题单（初选 8 题，待用户过目后长期冻结；顺序即 task.idx 0..7）
# 括号内是选题时的静态画像：repo / version / F2P+P2P 数量。
# ---------------------------------------------------------------------------
PICKED: list[str] = [
    "django__django-11099",  # django 3.0, f2p=3 p2p=19, auth username validator 正则
    "django__django-11133",  # django 3.0, f2p=1 p2p=64, HttpResponse memoryview
    "django__django-16139",  # django 4.2, f2p=1 p2p=86, admin 改密链接 404
    "sympy__sympy-14711",    # sympy 1.1, f2p=1 p2p=2,  vector add 0 报错
    "sympy__sympy-15349",    # sympy 1.4, f2p=1 p2p=3,  Quaternion.to_rotation_matrix 符号
    "psf__requests-1142",    # requests 1.1, f2p=1 p2p=5,   GET 不应总带 Content-Length
    "psf__requests-2931",    # requests 2.9, f2p=1 p2p=84,  binary payload to_native_string
    "astropy__astropy-14995",  # astropy 5.2, f2p=1 p2p=179, NDDataRef mask 传播
]


def hub_manifest_digest(image_ref: str) -> str:
    """向 Docker Hub registry 匿名要 token 后 HEAD/GET manifest，返回 digest。
    镜像不存在会抛 HTTPError 404——把"镜像存在"作为冻结前的硬校验。"""
    repo, tag = image_ref.rsplit(":", 1)
    token = json.load(
        urllib.request.urlopen(
            "https://auth.docker.io/token?service=registry.docker.io"
            f"&scope=repository:{repo}:pull"
        )
    )["token"]
    req = urllib.request.Request(
        f"https://registry-1.docker.io/v2/{repo}/manifests/{tag}",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": (
                "application/vnd.docker.distribution.manifest.list.v2+json, "
                "application/vnd.oci.image.index.v1+json, "
                "application/vnd.docker.distribution.manifest.v2+json"
            ),
        },
    )
    with urllib.request.urlopen(req) as resp:
        json.load(resp)  # 校验响应体可解析
        return resp.headers["Docker-Content-Digest"]


def main() -> None:
    import swebench
    from swebench.harness.constants import MAP_REPO_VERSION_TO_SPECS
    from swebench.harness.test_spec.test_spec import make_test_spec
    from swebench.harness.utils import load_swebench_dataset

    rows = {r["instance_id"]: r for r in load_swebench_dataset(DATASET, SPLIT)}
    missing = [iid for iid in PICKED if iid not in rows]
    if missing:
        raise SystemExit(f"instance 不在 {DATASET} 中: {missing}")

    tasks = []
    for idx, iid in enumerate(PICKED):
        row = dict(rows[iid])
        spec = make_test_spec(row, namespace=NAMESPACE, arch=ARCH)
        image = spec.instance_image_key
        digest = hub_manifest_digest(image)
        test_cmd = MAP_REPO_VERSION_TO_SPECS[row["repo"]][row["version"]]["test_cmd"]
        if isinstance(test_cmd, list):
            test_cmd = test_cmd[-1]
        f2p = json.loads(row["FAIL_TO_PASS"])
        p2p = json.loads(row["PASS_TO_PASS"])
        print(
            f"[{idx}] {iid}: image={image} f2p={len(f2p)} p2p={len(p2p)}\n"
            f"     digest={digest}"
        )
        tasks.append(
            {
                "idx": idx,
                # instance 原始行整体保留（含 golden patch/test_patch），供远程评分侧
                # make_test_spec 重建 TestSpec 用官方 parser。注意：golden patch 只进
                # 这份数据文件与 TestSpec，绝不进 Task 字段/prompt/trace dump。
                "instance": row,
                "image": image,
                "image_manifest_digest": digest,
                "eval_script": spec.eval_script,
                "test_cmd": test_cmd,
                "fail_to_pass": f2p,
                "pass_to_pass": p2p,
            }
        )

    payload = {
        "meta": {
            "stage": "rh2-s0-7-swe-smoke",
            "status": "初选题单，冻结待用户过目",
            "dataset": DATASET,
            "split": SPLIT,
            "namespace": NAMESPACE,
            "arch": ARCH,
            "swebench_version": swebench.__version__,
            "selection_criteria": (
                "C6：官方预构建 x86_64 镜像存在（逐题核对 Docker Hub manifest）；"
                "Python 主流仓库（django/sympy/requests/astropy）；"
                "单题测试<5 分钟（静态代理：F2P+P2P 数量与按模块/单文件的测试命令，"
                "真实耗时在 S0-7 运行时逐题记录）"
            ),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        },
        "tasks": tasks,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"\n冻结数据 -> {OUT_PATH.relative_to(REPO_ROOT)} ({OUT_PATH.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
