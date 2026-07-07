"""/testbed 物化血缘校验（框架无关层，S1-2 从 S0-7 SweSmokeTaskset.setup 抽出）。

背景（S0-7 两次实证迭代得到的契约，见 s0/swe_smoke_report.md 发现 2）：

官方 SWE-bench 预构建镜像里 /testbed 的 HEAD **不是** base_commit 本身，而是构建时
叠加的一个 "SWE-bench" 提交；且该提交**不保证内容为空**——
astropy__astropy-14995 里它带 pyproject.toml 1 行官方环境修补
（diffstat `1 file changed, 1 insertion(+), 1 deletion(-)`），django/sympy/requests
7 题为空 diff。因此既不能用 "HEAD == base_commit" 也不能用 "树内容等值" 判断，
唯一可靠的判据是**血缘**（fail-closed）：

    base_commit 对象存在 且（HEAD == base_commit 或 HEAD^ == base_commit）

环境修补 diffstat 只作为证据记录，不参与判定。评分不受叠加提交影响：官方 eval
脚本自己会 `git checkout <base_commit> -- <测试文件>` 后再 apply golden test_patch。

本模块刻意**不接触任何 runtime / 容器 API**：它只负责
（1）生成探针 bash 脚本文本、（2）解析探针输出并给出判定。
"运行脚本" 由调用方完成——verifiers 绑定用 `runtime.run(["bash","-c",script])`，
S1-6 的 slime 绑定用它自己的 sandbox 执行通道，两边共享同一套判据。

典型用法（verifiers 绑定侧）：

    script = build_probe_script(task.base_commit)
    result = await runtime.run(["bash", "-c", script], {})
    check = evaluate_probe(task.base_commit, result.exit_code, result.stdout, result.stderr)
    trace.info.update(check.trace_info())
    check.ensure_ok()   # 失败抛 MaterializeError（fail-closed）
"""

from __future__ import annotations

import json
import re

from pydantic import Field

from repoharness2.contracts._base import GitSha, Sha256Digest, StrictModel

# ---------------------------------------------------------------------------
# agent 环境注入（与血缘校验同属"物化"动作，绑定层原样写进容器）
# ---------------------------------------------------------------------------

# 容器内 agent bash 环境激活文件的落点与内容：配合 harness env 的
# BASH_ENV=/root/.rh2_bash_env，让 agent 每次非交互 bash 都先激活 conda testbed
# 环境（否则 `python`/`pip` 落在 miniconda base 环境，测试根本跑不起来）。
BASH_ENV_PATH = "/root/.rh2_bash_env"
BASH_ENV_CONTENT = (
    "# rh2 envpack: 让 agent 的每个非交互 bash 命令都运行在 conda testbed 环境里。\n"
    "source /opt/miniconda3/bin/activate testbed 2>/dev/null || true\n"
)

_GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")

# 探针输出的标记行前缀（build_probe_script 与 evaluate_probe 必须成对演进）。
_TAG_PREFIXES = ("HEAD=", "PARENT=", "DIFFSTAT=")
_BASE_OBJECT_OK_TAG = "BASE_OBJECT_OK"


def build_probe_script(base_commit: str) -> str:
    """生成 /testbed 物化探针脚本（一段 `bash -c` 载荷）。

    输出协议（stdout，逐行）：
      HEAD=<sha>            当前 HEAD
      BASE_OBJECT_OK        base_commit 对象存在时打出（不存在则整段失败，exit!=0）
      PARENT=<sha|none>     HEAD 的第一父提交（孤儿提交时为 none）
      DIFFSTAT=<text>       base..HEAD 的 diffstat 尾行（官方环境修补证据，可为空）
      <其余行>              `git status --porcelain` 前 50 行（工作树污染证据）

    base_commit 必须是 40 位十六进制（GitSha），否则拒绝生成——脚本文本里要内插
    该值，这里的强校验同时挡住形态错误与注入。
    """

    if not _GIT_SHA_RE.match(base_commit):
        raise ValueError(f"base_commit 必须是 40 位十六进制 git sha，得到 {base_commit!r}")
    return (
        # safe.directory：容器内统一 root，通常非必需，但官方 eval 脚本也会设，
        # 提前设好让 agent rollout 期间的 git 命令行为与评分期一致。
        "git config --global --add safe.directory /testbed; "
        "cd /testbed "
        '&& echo "HEAD=$(git rev-parse HEAD)" '
        f"&& (git cat-file -e {base_commit}^{{commit}} && echo {_BASE_OBJECT_OK_TAG}) "
        '&& echo "PARENT=$(git rev-parse HEAD^ 2>/dev/null || echo none)" '
        f'&& echo "DIFFSTAT=$(git diff --stat {base_commit} HEAD | tail -1)" '
        "&& git status --porcelain | head -50"
    )


class MaterializeError(RuntimeError):
    """/testbed 物化校验失败（fail-closed：评分对不在题目基线上的树没有意义）。"""


class MaterializeCheck(StrictModel):
    """一次物化探针的解析结果 + 血缘判定（构造即判定，不可变）。"""

    base_commit: GitSha = Field(description="题目冻结的基线提交（判据锚点）。")
    exit_code: int = Field(description="探针脚本退出码（非 0 = 探针本身失败，直接不通过）。")
    head: str = Field(default="", description="容器内 /testbed 的 HEAD sha（探针失败时为空）。")
    head_parent: str = Field(
        default="", description='HEAD 的第一父提交 sha（孤儿提交时探针给 "none"）。'
    )
    base_object_ok: bool = Field(
        default=False, description="base_commit 对象是否存在于仓库（血缘判据前提）。"
    )
    env_diffstat_vs_base: str = Field(
        default="",
        description="base..HEAD 的 diffstat 尾行——官方构建叠加提交的环境修补证据（可为空，非判定项）。",
    )
    dirty_paths: list[str] = Field(
        default_factory=list,
        description="setup 时工作树非干净的条目（git status --porcelain 前 50 行，证据非判定项）。",
    )
    stderr_tail: str = Field(default="", description="探针 stderr 尾部（失败排障用）。")

    @property
    def lineage_ok(self) -> bool:
        """血缘判据本体：HEAD == base_commit，或 HEAD^ == base_commit（叠加提交形态）。"""

        return self.head == self.base_commit or self.head_parent == self.base_commit

    @property
    def ok(self) -> bool:
        """物化整体判定：探针成功 + base 对象存在 + 血缘正确。"""

        return self.exit_code == 0 and self.base_object_ok and self.lineage_ok

    def failure_message(self) -> str:
        return (
            f"/testbed 物化校验失败: exit={self.exit_code}, HEAD={self.head!r}, "
            f"HEAD^={self.head_parent!r}, base_commit={self.base_commit!r}, "
            f"base_object_ok={self.base_object_ok}; "
            f"stderr tail: {self.stderr_tail[-500:]}"
        )

    def ensure_ok(self) -> None:
        """fail-closed 出口：不通过即抛 MaterializeError（绑定层不得吞掉）。"""

        if not self.ok:
            raise MaterializeError(self.failure_message())

    def trace_info(self) -> dict[str, object]:
        """绑定层写 trace.info 的标准证据字段（键名沿用 S0-7，dump 可对照）。"""

        return {
            "setup_git_head": self.head,
            "setup_git_head_parent": self.head_parent,
            "setup_base_object_ok": self.base_object_ok,
            "setup_env_diffstat_vs_base": self.env_diffstat_vs_base,
            "setup_git_dirty": self.dirty_paths[:20],
        }


def evaluate_probe(
    base_commit: str, exit_code: int, stdout: str, stderr: str = ""
) -> MaterializeCheck:
    """解析探针输出并构造 MaterializeCheck（解析逻辑与 S0-7 setup 完全一致）。

    探针失败（exit_code != 0）时不解析 stdout——那时的输出不可信，
    只保留 stderr 尾部作排障证据。
    """

    lines = stdout.strip().splitlines() if exit_code == 0 else []
    tagged: dict[str, str] = {}
    base_object_ok = False
    dirty: list[str] = []
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text == _BASE_OBJECT_OK_TAG:
            base_object_ok = True
        elif text.startswith(_TAG_PREFIXES):
            key, _, value = text.partition("=")
            tagged[key.lower()] = value.strip()
        else:
            dirty.append(text)
    return MaterializeCheck(
        base_commit=base_commit,
        exit_code=exit_code,
        head=tagged.get("head", ""),
        head_parent=tagged.get("parent", ""),
        base_object_ok=base_object_ok,
        env_diffstat_vs_base=tagged.get("diffstat", ""),
        dirty_paths=dirty,
        stderr_tail=stderr.strip()[-500:] if stderr else "",
    )


# ---------------------------------------------------------------------------
# 运行期镜像 digest 比对（S1-7a 前置修复，codex#1 / F1①）
# ---------------------------------------------------------------------------

# 判据用 RepoDigests 而不是 image ID：envpack 冻结记录的 image_manifest_digest
# 是 registry 侧的 manifest digest（`docker.io/xx/yy@sha256:<manifest>` 的 @ 后半），
# 而 `docker image inspect -f {{.Id}}` 给出的是本地 config digest，两者永不相等。
# S0-7 runner（experiments/s0_swe_smoke.py ensure_image）已实证 RepoDigests 可比对。
IMAGE_REPO_DIGESTS_FORMAT = "{{json .RepoDigests}}"


class ImageDigestError(RuntimeError):
    """运行期镜像 digest 比对失败（fail-closed：漂移镜像上的 rollout/评分都不可信）。"""


class ImageDigestCheck(StrictModel):
    """一次镜像 RepoDigests 比对的解析结果 + 判定（与 MaterializeCheck 同风格）。

    调用方约定：本对象只服务"任务声明了冻结 digest"的路径；本地构建镜像
    （无 RepoDigests）必须在任务面用显式 local_build 标记豁免，**不允许**
    用"RepoDigests 为空就跳过比对"来兜底——空清单在这里就是不通过。
    """

    expected_manifest_digest: Sha256Digest = Field(
        description="envpack 冻结记录的镜像 manifest digest（frozen_v1 的 image_manifest_digest）。"
    )
    inspect_exit_code: int = Field(
        description="`docker image inspect` 的退出码（非 0 = 查询失败，直接不通过）。"
    )
    repo_digests: list[str] = Field(
        default_factory=list,
        description='实际镜像的 RepoDigests 清单（形如 "docker.io/xx/yy@sha256:<hex>"）。',
    )
    stderr_tail: str = Field(default="", description="inspect stderr 尾部（失败排障用）。")

    @property
    def matched_repo_digest(self) -> str | None:
        """命中的 RepoDigests 条目（@ 后半 == 冻结 digest 才算命中；没有则 None）。"""

        for entry in self.repo_digests:
            if entry.rpartition("@")[2] == self.expected_manifest_digest:
                return entry
        return None

    @property
    def ok(self) -> bool:
        return self.inspect_exit_code == 0 and self.matched_repo_digest is not None

    def failure_message(self) -> str:
        if self.inspect_exit_code != 0:
            return (
                f"镜像 RepoDigests 查询失败: exit={self.inspect_exit_code}; "
                f"stderr tail: {self.stderr_tail[-300:]}"
            )
        if not self.repo_digests:
            return (
                "镜像没有任何 RepoDigests（本地构建/未从 registry 拉取的形态），"
                "且任务未显式声明 local_build 豁免——按 fail-closed 拒绝"
            )
        return (
            f"镜像 digest 漂移: 冻结记录 {self.expected_manifest_digest}, "
            f"实际 RepoDigests={self.repo_digests}"
        )

    def ensure_ok(self) -> None:
        if not self.ok:
            raise ImageDigestError(self.failure_message())


def evaluate_image_digest(
    expected_manifest_digest: str, exit_code: int, stdout: str, stderr: str = ""
) -> ImageDigestCheck:
    """解析 `docker image inspect -f '{{json .RepoDigests}}'` 输出并构造比对结果。

    stdout 解析失败（非 JSON / 非字符串数组）按空清单处理——空清单本身就
    判不通过，所以解析失败同样落在 fail-closed 一侧。
    """

    digests: list[str] = []
    if exit_code == 0:
        try:
            parsed = json.loads(stdout.strip() or "null")
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, list):
            digests = [str(item) for item in parsed]
    return ImageDigestCheck(
        expected_manifest_digest=expected_manifest_digest,
        inspect_exit_code=exit_code,
        repo_digests=digests,
        stderr_tail=stderr.strip()[-500:] if stderr else "",
    )
