"""S1-4 评分测试的共享 fixture 素材（U-D：本机轻量镜像，不拉 x86 SWE 镜像）。

三块内容：

1. **手工小 git repo**（源文件 + 官方测试文件）：官方测试以
   `python tests/test_thing.py` 运行，按官方 pytest -rA 摘要行格式
   （`PASSED path::name` / `FAILED path::name`）输出真实执行结果——
   官方 parser（psf/requests 的 pytest parser）能原样解析，评分结论由
   patch 重放后的真实代码行为决定，不是写死的假日志。
2. **假 private bundle**：repo/version 借用官方 MAP_REPO_TO_PARSER 里的
   psf/requests 配置键（本机无该 repo，仅让官方 parser 选中 pytest 解析器），
   F2P/P2P 清单指向 fixture 测试名。这样本机行为验证跑的是**真官方 parser
   链路**（make_test_spec -> get_logs_eval -> get_eval_tests_report）。
3. **FakeDocker**：可注入 manager 的 docker 替身（P7 backend-neutral 的直接
   受益者），无 docker 环境也能测 P2/P5/P8/P10/P11 与归因决策树。
"""

from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from repoharness2.envpack import scoring
from repoharness2.envpack.bundles import PrivateGradingBundle
from repoharness2.grading.manager import ExecResult, GradingEnvSpec, HygieneRules

FIXTURE_INSTANCE_ID = "rh2-fixture.tiny-0001"

# ---------------------------------------------------------------------------
# fixture repo 文件内容
# ---------------------------------------------------------------------------

SRC_BROKEN = 'def feature():\n    return "broken"\n'
SRC_FIXED = 'def feature():\n    return "fixed"\n'
SRC_STILL_BROKEN = 'def feature():\n    return "still broken"\n'

F2P_TEST = "tests/test_thing.py::test_feature"
P2P_TEST = "tests/test_thing.py::test_stable"

# 官方测试文件：真实 import 源码、真实断言，仅输出格式对齐官方 pytest -rA 摘要行。
TEST_FILE_CONTENT = '''"""fixture 官方测试：输出官方 pytest -rA 摘要行格式，可被官方 parser 解析。"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from src.thing import feature


def check_feature():
    return feature() == "fixed"


def check_stable():
    return 1 + 1 == 2


CASES = [
    ("tests/test_thing.py::test_feature", check_feature),
    ("tests/test_thing.py::test_stable", check_stable),
]

if __name__ == "__main__":
    for name, check in CASES:
        try:
            ok = check()
        except Exception:
            ok = False
        print(("PASSED " if ok else "FAILED ") + name)
'''

# 假想的官方 golden test patch（只用于：派生 test_files 名单 + 填充 private bundle）。
FIXTURE_TEST_PATCH = (
    "diff --git a/tests/test_thing.py b/tests/test_thing.py\n"
    "--- a/tests/test_thing.py\n"
    "+++ b/tests/test_thing.py\n"
    "@@ -1 +1 @@\n"
    "-# placeholder\n"
    "+# golden placeholder\n"
)

FIXTURE_GOLDEN_PATCH = (
    "diff --git a/src/thing.py b/src/thing.py\n"
    "--- a/src/thing.py\n"
    "+++ b/src/thing.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def feature():\n"
    '-    return "broken"\n'
    '+    return "fixed"\n'
)

FIXTURE_HYGIENE = HygieneRules(
    test_files=("tests/test_thing.py",),
    test_globs=("tests/*",),
    forbidden_globs=("grader/*", ".rh2*"),
)


def make_eval_script(base_commit: str, *, extra_prelude: str = "") -> str:
    """fixture 官方 eval 脚本（形态对齐官方：set -x、评分前 reset 测试文件、双标记）。"""

    return (
        "#!/bin/bash\n"
        "set -xo pipefail\n"
        "cd /testbed\n"
        f"{extra_prelude}"
        f"git checkout {base_commit} -- tests/\n"
        "echo '>>>>> Start Test Output'\n"
        "python tests/test_thing.py\n"
        "echo '>>>>> End Test Output'\n"
    )


# 故障注入用 eval 脚本变体 -----------------------------------------------------

# 标记齐全但中间是垃圾（官方 parser 解析出 0 条测试 -> test_log_parse_failed）。
GARBAGE_EVAL_SCRIPT = (
    "#!/bin/bash\n"
    "cd /testbed\n"
    "echo '>>>>> Start Test Output'\n"
    "echo 'kernel panic: log corrupted, nothing test-like here'\n"
    "echo '>>>>> End Test Output'\n"
)

# 先打点再长睡（杀容器注入：/rh2/eval_started 出现后即可下手）。
SLOW_EVAL_SCRIPT = (
    "#!/bin/bash\n"
    "mkdir -p /rh2 && touch /rh2/eval_started\n"
    "sleep 300\n"
)


def make_fixture_private_bundle(base_commit: str) -> PrivateGradingBundle:
    """假 private bundle：官方 parser 配置键借用 psf/requests（pytest 解析器）。"""

    return PrivateGradingBundle(
        instance_id=FIXTURE_INSTANCE_ID,
        repo="psf/requests",  # MAP_REPO_TO_PARSER 的 pytest parser 键（仅选 parser 用）
        version="2.3",  # MAP_REPO_VERSION_TO_SPECS["psf/requests"] 的合法键
        base_commit=base_commit,
        golden_patch=FIXTURE_GOLDEN_PATCH,
        test_patch=FIXTURE_TEST_PATCH,
        fail_to_pass=[F2P_TEST],
        pass_to_pass=[P2P_TEST],
        eval_script=make_eval_script(base_commit),
        test_cmd="python tests/test_thing.py",
    )


def make_fixture_spec(
    base_commit: str,
    image: str,
    *,
    snapshot_host_path: str | None = None,
    eval_script: str | None = None,
    checkout_mode: str = "clone_from_readonly_snapshot",
    **overrides,
) -> GradingEnvSpec:
    """fixture 评分 spec。docker e2e 用 clone 模式（P6 只读快照）；
    FakeDocker 单测用 image_embedded 模式（少一次 clone exec，桩更简单）。"""

    private = make_fixture_private_bundle(base_commit)

    def _parse(log_text: str) -> scoring.EvalVerdict:
        return scoring.parse_eval_log(private, log_text)

    kwargs = dict(
        task_id=FIXTURE_INSTANCE_ID,
        image=image,
        base_commit=base_commit,
        eval_script=eval_script if eval_script is not None else private.eval_script,
        parse_log=_parse,
        grader_version=f"swebench-{scoring.swebench_version()}",
        hygiene=FIXTURE_HYGIENE,
        checkout_mode=checkout_mode,
        snapshot_host_path=snapshot_host_path,
        eval_script_path="/rh2/eval.sh",
        # fixture 镜像是本地 docker build 产物，没有 RepoDigests——按 codex#1 的
        # 纪律显式声明豁免；测试若传入 image_manifest_digest 则改走比对路径。
        image_local_build="image_manifest_digest" not in overrides,
    )
    kwargs.update(overrides)
    return GradingEnvSpec(**kwargs)


# ---------------------------------------------------------------------------
# 本机 git 仓库操作（fixture repo 构建 + agent workspace 克隆）
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FixtureRepo:
    path: Path
    base_commit: str


_GIT_ID = ("-c", "user.email=rh2-fixture@test", "-c", "user.name=rh2-fixture")


def git_in(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *_GIT_ID, "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip()


def build_fixture_repo(root: Path) -> FixtureRepo:
    """手工造小 git repo：含官方测试文件，HEAD 即 base_commit。"""

    root.mkdir(parents=True, exist_ok=True)
    (root / "src").mkdir()
    (root / "tests").mkdir()
    (root / "src" / "thing.py").write_text(SRC_BROKEN)
    (root / "tests" / "test_thing.py").write_text(TEST_FILE_CONTENT)
    (root / "README.md").write_text("rh2 S1-4 grading fixture repo\n")
    subprocess.run(
        ["git", "init", "-q", "-b", "main", str(root)], check=True, capture_output=True
    )
    git_in(root, "add", "-A")
    git_in(root, "commit", "-q", "-m", "fixture base")
    return FixtureRepo(path=root, base_commit=git_in(root, "rev-parse", "HEAD"))


def clone_workspace(repo: FixtureRepo, dest: Path) -> Path:
    """克隆出一个 agent workspace（模拟 rollout 后的 /testbed，HEAD==base）。"""

    subprocess.run(
        ["git", "clone", "-q", str(repo.path), str(dest)], check=True, capture_output=True
    )
    return dest


# ---------------------------------------------------------------------------
# FakeDocker / FakeWorkspace（无 docker 的单测桩）
# ---------------------------------------------------------------------------

GOOD_FAKE_LOG = (
    ">>>>> Start Test Output\n"
    f"PASSED {P2P_TEST}\n"
    f"PASSED {F2P_TEST}\n"
    ">>>>> End Test Output\n"
)

FAILING_FAKE_LOG = (
    ">>>>> Start Test Output\n"
    f"PASSED {P2P_TEST}\n"
    f"FAILED {F2P_TEST}\n"
    ">>>>> End Test Output\n"
)

GARBAGE_FAKE_LOG = (
    ">>>>> Start Test Output\nnothing parseable here\n>>>>> End Test Output\n"
)

NO_MARKER_FAKE_LOG = "eval crashed before emitting markers\n"


@dataclass
class FakeDocker:
    """docker CLI 替身：按命令首词 + 脚本内容启发式返回罐头结果，并记账所有调用。"""

    base_commit: str
    image_present: bool = True
    pull_delay: float = 0.0
    pull_fail: bool = False
    eval_log: str = GOOD_FAKE_LOG
    eval_delay: float = 0.0
    eval_exit_code: int = 0
    apply_exit_code: int = 0
    container_running: bool = True
    # B4 exact-baseline 重建：census 脚本的罐头输出（默认空树 census）。
    census_output: str = ""
    census_exit_code: int = 0
    ps_stdout: str = ""
    rm_fail_names: tuple[str, ...] = ()
    # 镜像 RepoDigests 罐头值（codex#1 运行期比对用；json 序列化后返回）。
    repo_digests: tuple[str, ...] = ()
    calls: list[tuple[str, ...]] = field(default_factory=list)
    # 每次带 stdin 的调用记账（(args, payload)）：golden 隔离 negative test 会
    # 扫描这里，证明评分容器的全部写入面都不含 golden_patch 内容。
    input_payloads: list[tuple[tuple[str, ...], bytes]] = field(default_factory=list)
    pull_count: int = 0
    pulls_in_flight: int = 0
    max_concurrent_pulls: int = 0
    removed: list[str] = field(default_factory=list)
    pulled_images: set[str] = field(default_factory=set)

    def _probe_stdout(self) -> str:
        return (
            f"HEAD={self.base_commit}\n"
            "BASE_OBJECT_OK\n"
            "PARENT=none\n"
            "DIFFSTAT=\n"
        )

    async def __call__(self, *args: str, input_bytes: bytes | None = None) -> ExecResult:
        self.calls.append(args)
        if input_bytes is not None:
            self.input_payloads.append((args, input_bytes))
        cmd = args[0]
        if cmd == "image":  # image inspect [-f fmt] <image>
            image = args[-1]
            if "RepoDigests" in " ".join(args):  # codex#1：RepoDigests 查询
                import json as _json

                return ExecResult(0, _json.dumps(list(self.repo_digests)) + "\n", "")
            if "-f" in args:
                return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
            if self.image_present or image in self.pulled_images:
                return ExecResult(0, "[]", "")
            return ExecResult(1, "", f"Error: No such image: {image}")
        if cmd == "pull":
            self.pull_count += 1
            self.pulls_in_flight += 1
            self.max_concurrent_pulls = max(self.max_concurrent_pulls, self.pulls_in_flight)
            try:
                if self.pull_delay:
                    await asyncio.sleep(self.pull_delay)
            finally:
                self.pulls_in_flight -= 1
            if self.pull_fail:
                return ExecResult(1, "", "pull access denied")
            self.pulled_images.add(args[-1])
            return ExecResult(0, "", "")
        if cmd == "run":
            return ExecResult(0, "f00dfeedcafe\n", "")
        if cmd == "inspect":
            if "{{.Image}}" in args:  # 容器实际镜像 ID（codex#1 比对入口）
                return ExecResult(0, "sha256:" + "ab" * 32 + "\n", "")
            return ExecResult(0, "true\n" if self.container_running else "false\n", "")
        if cmd == "ps":
            return ExecResult(0, self.ps_stdout, "")
        if cmd == "rm":
            name = args[-1]
            if name in self.rm_fail_names:
                return ExecResult(1, "", f"cannot remove {name}: fake failure")
            self.removed.append(name)
            return ExecResult(0, "", "")
        if cmd == "exec":
            script = args[-1]
            if "-prune" in script and "readlink" in script:
                # B4 exact-baseline 重建旋钮：census 脚本 → census_output
                # 罐头（默认空树；census_exit_code 可模拟脚本失败）。
                return ExecResult(self.census_exit_code, self.census_output, "")
            if "rev-parse HEAD" in script:
                return ExecResult(0, self._probe_stdout(), "")
            if "cat > " in script:
                return ExecResult(0, "", "")
            if "git apply" in script:
                stderr = "" if self.apply_exit_code == 0 else "error: patch failed (fake)"
                return ExecResult(self.apply_exit_code, "", stderr)
            if "memory.peak" in script:
                return ExecResult(0, str(1024 * 1024) + "\n", "")
            if script.startswith("bash ") and "2>&1" in script:
                if self.eval_delay:
                    await asyncio.sleep(self.eval_delay)
                return ExecResult(self.eval_exit_code, self.eval_log, "")
            return ExecResult(0, "", "")
        raise AssertionError(f"FakeDocker 不认识的命令: {args}")


@dataclass
class FakeWorkspace:
    """agent workspace 替身：run_bash 一律返回配置好的 patch 文本（stdout）。"""

    patch_text: str = ""
    exit_code: int = 0

    async def run_bash(self, script: str) -> ExecResult:
        if self.exit_code != 0:
            return ExecResult(self.exit_code, "", "fake workspace is dead")
        return ExecResult(0, self.patch_text, "")


@dataclass
class SlowFakeManager:
    """GradingQueue 单测用的 manager 替身：grade 睡 grade_delay 秒后回显参数。"""

    grade_delay: float = 0.05
    active: int = 0
    max_active_seen: int = 0
    grade_calls: list[dict] = field(default_factory=list)

    async def grade(self, **kwargs) -> dict:
        self.active += 1
        self.max_active_seen = max(self.max_active_seen, self.active)
        try:
            await asyncio.sleep(self.grade_delay)
            self.grade_calls.append(kwargs)
            return kwargs
        finally:
            self.active -= 1


# 常用 patch 文本（unit 与 hygiene 测试共用） ---------------------------------

GOOD_PATCH = (
    "diff --git a/src/thing.py b/src/thing.py\n"
    "index 1111111..2222222 100644\n"
    "--- a/src/thing.py\n"
    "+++ b/src/thing.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def feature():\n"
    '-    return "broken"\n'
    '+    return "fixed"\n'
)

TAMPER_SEGMENT = (
    "diff --git a/tests/test_thing.py b/tests/test_thing.py\n"
    "index 3333333..4444444 100644\n"
    "--- a/tests/test_thing.py\n"
    "+++ b/tests/test_thing.py\n"
    "@@ -10,2 +10,2 @@\n"
    "-    ok = check()\n"
    "+    ok = True\n"
)

POLLUTION_SEGMENT = (
    "diff --git a/grader/secret.txt b/grader/secret.txt\n"
    "new file mode 100644\n"
    "index 0000000..5555555\n"
    "--- /dev/null\n"
    "+++ b/grader/secret.txt\n"
    "@@ -0,0 +1 @@\n"
    "+stolen grading assets\n"
)
