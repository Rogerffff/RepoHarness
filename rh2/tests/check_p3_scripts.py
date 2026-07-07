"""P3 预实验脚本包的静态验证（无 GPU，本地跑）。

覆盖任务书要求的四类断言：
1. bash -n 全部通过 + 每个可执行脚本 --dry-run 退出码 0；
2. 所有 slime flag（*_ARGS 数组内的 --xxx token，见 p3_preflight/common.sh
   头注的约定）都能在 reference/slime 的 arguments.py / backends 参数文件 /
   官方 scripts、tests、examples 里 grep 到——不许发明参数
   （协议 "--enable-ep-moe" 笔误教训）；
3. A1~A5 的 TP×CP×PP×DP 乘积 == 卡数、EP×ETP 整除卡数、128 % EP == 0；
4. E2 flags 与实验设计定案一致（grpo / n=4 / clip 0.2/0.28 /
   disable-grpo-std-normalization / top_p 0.95 / --use-rollout-routing-replay
   必开）+ J4c 防误用断言在场 + update-weights-interval=1。

运行：cd rh2 && uv run pytest tests/check_p3_scripts.py -q
"""

from __future__ import annotations

import os
import py_compile
import re
import subprocess
from pathlib import Path

import pytest

RH2_DIR = Path(__file__).resolve().parents[1]
P3_DIR = RH2_DIR / "experiments" / "p3_preflight"
SLIME_DIR = RH2_DIR.parent / "reference" / "slime"

SHELL_SCRIPTS = sorted(
    [p for p in P3_DIR.rglob("*.sh")],
    key=lambda p: str(p),
)
# 可独立执行（支持 --dry-run）的入口脚本；common.sh / j3_matrix/a*.sh 是被 source 的库
DRY_RUN_SCRIPTS = [
    P3_DIR / "j0_env_check.sh",
    P3_DIR / "j0_convert_weights.sh",
    P3_DIR / "j05_kernel_smoke.sh",
    P3_DIR / "j1_nccl.sh",
    P3_DIR / "j2_sglang_30b.sh",
    P3_DIR / "j3_matrix" / "run_j3.sh",
    P3_DIR / "j4_full_step.sh",
    P3_DIR / "j4b_topo_compare.sh",
    P3_DIR / "j4c_fully_async_smoke.sh",
    P3_DIR / "j5_weight_sync.sh",
]
PY_LIBS = sorted((P3_DIR / "lib").glob("*.py"))

# --sglang-<x> 是 slime 对 SGLang ServerArgs 的自动前缀透传
# （reference/slime/slime/backends/sglang_utils/arguments.py:34
# add_sglang_arguments 的 new_add_argument_wrapper），部分字段没在 slime
# 仓库任何脚本里出现过但真实存在于 SGLang ServerArgs——白名单显式列出，
# 并附验证依据（S1-0/S1-7a 在 pin 镜像上实跑通过的 sm_120 规避组合）。
EXPLICIT_ALLOWED = {
    "--sglang-sampling-backend",  # SGLang ServerArgs.sampling_backend；7a container_train.sh 实跑验证
    "--sglang-disable-cuda-graph",  # SGLang ServerArgs.disable_cuda_graph；同上
}


# ---------------------------------------------------------------- 工具

def _extract_args_block_flags(script: Path) -> set[str]:
    """抽取 *_ARGS=( ... ) 数组块内的 --flag token（slime flag 约定区）。"""
    text = script.read_text()
    flags: set[str] = set()
    in_block = False
    for line in text.splitlines():
        stripped = line.strip()
        if re.match(r"^[A-Z0-9_]*_ARGS=\(", stripped) or re.match(r"^[A-Z0-9_]*_ARGS\+?=\(", stripped):
            in_block = True
        if in_block:
            for token in re.findall(r"(?<![\w\"'-])--[a-z][a-z0-9-]*", stripped):
                flags.add(token)
            if stripped.endswith(")") and not stripped.endswith("=("):
                in_block = False
        # 形如 ROLLOUT_ARGS=("${ROLLOUT_ARGS[@]}" --foo bar) 的追加行
        if re.match(r'^[A-Z0-9_]*_ARGS=\("\$\{', stripped):
            for token in re.findall(r"(?<![\w\"'-])--[a-z][a-z0-9-]*", stripped):
                flags.add(token)
    return flags


_CORPUS_CACHE: str | None = None


def _slime_corpus() -> str:
    """slime flag 白名单语料：参数定义文件 + 官方 scripts/tests/examples。"""
    global _CORPUS_CACHE
    if _CORPUS_CACHE is not None:
        return _CORPUS_CACHE
    parts: list[str] = []
    files = [
        SLIME_DIR / "slime" / "utils" / "arguments.py",
        SLIME_DIR / "slime" / "backends" / "sglang_utils" / "arguments.py",
        SLIME_DIR / "slime" / "backends" / "megatron_utils" / "arguments.py",
    ]
    for pattern in ("scripts/**/*.sh", "tests/**/*.py", "examples/**/*.sh", "examples/**/*.py", "examples/**/*.md"):
        files.extend(SLIME_DIR.glob(pattern))
    for f in files:
        if f.is_file():
            parts.append(f.read_text(errors="replace"))
    _CORPUS_CACHE = "\n".join(parts)
    return _CORPUS_CACHE


def _read_a_config(path: Path) -> dict[str, int]:
    conf: dict[str, int] = {}
    for line in path.read_text().splitlines():
        m = re.match(r"^(J3_[A-Z_]+)=(\d+)$", line.strip())
        if m:
            conf[m.group(1)] = int(m.group(2))
    return conf


# ---------------------------------------------------------------- 1. bash -n + dry-run

@pytest.mark.parametrize("script", SHELL_SCRIPTS, ids=lambda p: p.name)
def test_bash_syntax(script: Path) -> None:
    proc = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
    assert proc.returncode == 0, f"bash -n {script.name}: {proc.stderr}"


@pytest.mark.parametrize("script", DRY_RUN_SCRIPTS, ids=lambda p: p.name)
def test_dry_run(script: Path, tmp_path: Path) -> None:
    env = dict(os.environ)
    env["P3_EV"] = str(tmp_path / "evidence")
    proc = subprocess.run(
        ["bash", str(script), "--dry-run"],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(P3_DIR),
        timeout=120,
    )
    assert proc.returncode == 0, f"{script.name} --dry-run rc={proc.returncode}\nstdout:\n{proc.stdout[-2000:]}\nstderr:\n{proc.stderr[-2000:]}"
    assert proc.stdout.strip(), f"{script.name} --dry-run 应打印解析后的命令"


def test_python_libs_compile() -> None:
    assert PY_LIBS, "lib/*.py 不应为空"
    for f in PY_LIBS:
        py_compile.compile(str(f), doraise=True)


# ---------------------------------------------------------------- 2. slime flag 逐个核对

def test_all_slime_flags_exist_in_reference() -> None:
    assert SLIME_DIR.exists(), f"reference/slime 不在 {SLIME_DIR}"
    corpus = _slime_corpus()
    unknown: dict[str, list[str]] = {}
    checked = 0
    for script in SHELL_SCRIPTS:
        for flag in sorted(_extract_args_block_flags(script)):
            checked += 1
            if flag in EXPLICIT_ALLOWED:
                continue
            if flag not in corpus:
                unknown.setdefault(script.name, []).append(flag)
    assert checked > 100, f"抽取到的 slime flag 太少（{checked}），*_ARGS 解析可能失效"
    assert not unknown, (
        "以下 flag 在 reference/slime 的 arguments.py/官方脚本里 grep 不到"
        f"（不许发明参数，'--enable-ep-moe' 教训）：{unknown}"
    )


# ---------------------------------------------------------------- 3. A1~A5 并行算术

A_EXPECTED = {
    "a1": dict(J3_TRAIN_GPUS=2, J3_TP=2, J3_CP=1, J3_DP=1, J3_EP=2, J3_ETP=1),
    "a2": dict(J3_TRAIN_GPUS=4, J3_TP=2, J3_CP=1, J3_DP=2, J3_EP=4, J3_ETP=1),
    "a3": dict(J3_TRAIN_GPUS=6, J3_TP=2, J3_CP=1, J3_DP=3, J3_EP=2, J3_ETP=1),
    "a4": dict(J3_TRAIN_GPUS=8, J3_TP=4, J3_CP=2, J3_DP=1, J3_EP=8, J3_ETP=1),
    "a5": dict(J3_TRAIN_GPUS=4, J3_TP=2, J3_CP=2, J3_DP=1, J3_EP=4, J3_ETP=1),
}


@pytest.mark.parametrize("name", sorted(A_EXPECTED), ids=str)
def test_j3_matrix_parallel_arithmetic(name: str) -> None:
    conf = _read_a_config(P3_DIR / "j3_matrix" / f"{name}.sh")
    exp = A_EXPECTED[name]
    for key, val in exp.items():
        assert conf.get(key) == val, f"{name}.sh {key}={conf.get(key)}，协议要求 {val}"
    gpus = conf["J3_TRAIN_GPUS"]
    product = conf["J3_TP"] * conf["J3_CP"] * conf["J3_PP"] * conf["J3_DP"]
    assert product == gpus, f"{name}: TP×CP×PP×DP={product} != 卡数 {gpus}"
    assert gpus % (conf["J3_EP"] * conf["J3_ETP"]) == 0, f"{name}: EP×ETP 不整除卡数"
    assert 128 % conf["J3_EP"] == 0, f"{name}: 128 experts 不被 EP={conf['J3_EP']} 整除"
    # 协议对照锚：A4 = slime 官方 30B 测试同款（tests/test_qwen3_30B_A3B.py TP4/CP2/EP8）
    if name == "a4":
        assert (conf["J3_TP"], conf["J3_CP"], conf["J3_EP"]) == (4, 2, 8)


# ---------------------------------------------------------------- 4. E2 flags 定案一致

E2_REQUIRED_IN_J4 = [
    "--advantage-estimator grpo",
    "--n-samples-per-prompt 4",
    "--eps-clip 0.2",
    "--eps-clip-high 0.28",
    "--disable-grpo-std-normalization",
    "--rollout-top-p 0.95",
    "--use-rollout-routing-replay",
]


def test_j4_e2_flags_match_experiment_design() -> None:
    text = (P3_DIR / "j4_full_step.sh").read_text()
    missing = [f for f in E2_REQUIRED_IN_J4 if f not in text]
    assert not missing, f"j4_full_step.sh 缺 E2 定案 flags: {missing}"
    # 动态采样 filter（E2 定案默认开，标准路径有效）
    assert "--dynamic-sampling-filter-path" in text
    assert "check_reward_nonzero_std" in text
    # J4 在 T3 分离拓扑（train_async，非 colocate）
    assert "train_async.py" in text
    assert "--colocate" not in text


def test_j3_e2_flags_and_fixed_terms() -> None:
    text = (P3_DIR / "j3_matrix" / "run_j3.sh").read_text()
    for f in [
        "--advantage-estimator grpo",
        "--eps-clip 0.2",
        "--eps-clip-high 0.28",
        "--disable-grpo-std-normalization",
        "--use-rollout-routing-replay",
        "--optimizer-cpu-offload",  # 协议 J3 固定项
        "--sequence-parallel",  # 协议 J3 固定项
        "--log-probs-chunk-size 1024",  # J3 附②长上下文三件套
        "--rollout-top-p 0.95",
    ]:
        assert f in text, f"run_j3.sh 缺协议固定项: {f}"
    # 长上下文三件套之 max-tokens-per-gpu = CTX/CP
    assert re.search(r"--max-tokens-per-gpu \$\(\(_ctx / J3_CP\)\)", text)
    # 合成 batch = 64 条（协议 J3 固定项）
    assert "J3_NUM_SAMPLES:-64" in text


def test_j4c_misuse_guard_and_interval() -> None:
    text = (P3_DIR / "j4c_fully_async_smoke.sh").read_text()
    # §1.6 防误用断言：fully_async 配动态采样参数即 fail
    assert "RH2_DYNAMIC_SAMPLING_FILTER_PATH" in text and "exit 3" in text
    # 强制 abort 三要素：fully_async 入口 + interval=1 + debug dump
    assert "slime.rollout.fully_async_rollout.generate_rollout_fully_async" in text
    assert "--update-weights-interval 1" in text
    assert "--save-debug-rollout-data" in text
    # 三元组打点入口
    assert "p3_preflight.lib.j4c_probe.generate" in text


def test_weight_sync_baseline_full_nccl() -> None:
    """J3 附④：分离基线 = full + nccl；interval=1。J4/J4b/J4c/J5 一致。"""
    for name in ("j4_full_step.sh", "j4b_topo_compare.sh", "j4c_fully_async_smoke.sh", "j5_weight_sync.sh"):
        text = (P3_DIR / name).read_text()
        assert "--update-weight-mode full" in text, name
        assert "--update-weight-transport nccl" in text, name
        assert "--update-weights-interval 1" in text, name


def test_model_args_sourced_and_dumped_for_30b() -> None:
    """J3 附①：30B 脚本必须 source qwen3-30B-A3B.sh 且 dump 展开后的 MODEL_ARGS。"""
    for name in ("j0_convert_weights.sh", "j4_full_step.sh", "j4b_topo_compare.sh", "j5_weight_sync.sh"):
        text = (P3_DIR / name).read_text()
        assert "P3_MODEL_SCRIPT" in text, name
        assert "MODEL_ARGS" in text, name
    common = (P3_DIR / "common.sh").read_text()
    assert "qwen3-30B-A3B.sh" in common  # P3_MODEL_SCRIPT 默认值
    run_j3 = (P3_DIR / "j3_matrix" / "run_j3.sh").read_text()
    assert "p3_dump_args" in run_j3 and 'MODEL_ARGS[@]' in run_j3


def test_image_pin_matches_s1() -> None:
    """P-1/P-9：镜像 pin 与 S1-0 一致（a7317182…）。"""
    common = (P3_DIR / "common.sh").read_text()
    assert "a7317182c71d35712ee4edc86a5d1c313dc969efdf0026d339673299c186ea75" in common
