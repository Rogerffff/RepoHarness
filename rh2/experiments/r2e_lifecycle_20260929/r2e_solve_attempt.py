#!/usr/bin/env python3
"""R2E 基座探针的求解入口（原型，2026-09-29，B 线 R2E 生命周期批）。

叠在共用探针入口 `experiments/base_probe_20260922/solve_attempt.py` 上：继承 `Attempt`，沿用它的 CC 启动与预算注入
（`solve()`：`ClaudeCodeDriver.run`、`--max-turns`、`cc_context_env`、宿主收集轨迹、CC 会话目录、pip freeze）、清理
（`cleanup()`：容器 → attempt 网络 → relay → 按 `rh2.run_id` 标签复查残留）与记录工具。只换 R2E 必需的层，其余调用
同一组正式函数：

1. **任务面**：正式 `PreparedTaskFace.load(..., image_overlays_path/sha256)`——派生镜像 image ID、`.venv` 激活脚本与
   解释器前缀、覆盖条目与评分面互检（隐藏测试位置 / 树摘要、配方自报、修订所需环境步骤）。不接受 `--image-override`：
   镜像只来自覆盖表；镜像身份按 image ID 核对（`image_local_build` 豁免 registry digest，与 generate.py 相同）。
2. **物化顺序按 generate.py**：relay → attempt 网络 → 容器 → 血缘探针 → git sanitize → 可信初始化 → 基线未跟踪清单
   → public bundle / 激活文件 → 启动前核对 → **基线 census**（`generate_baseline_manifest`，R2E 政策 r2e_v1）→
   **R2E rollout 预检**（agent 身份；解释器可执行、隐藏测试不可读、HEAD 无子提交；失败不启动）→ 激活核对 → CC。
3. **root 命令一律走 `TRUSTED_ROOT_EXEC_PREFIX`**（E2b：R2E 派生镜像 PATH 首项是 agent 可写的 /testbed/.venv/bin，
   继承镜像 ENV 的 root `pkill` / `ps` / `git` / `tar` 可能执行候选放进去的同名程序）。共用入口 `solve()` 里唯一一处
   root `docker exec … bash -c`（打包 CC 会话目录）在本进程内改走可信前缀，记录在 `trusted_root_exec_rewrites`。
4. **候选**：正式静止屏障 `DockerQuiescenceBarrier`（杀 agent 进程并有界核零、双读指纹）→ 正式 `export_frozen_patch`
   （census 冻结补丁，不经 git，`.gitignore` 不影响交付）→ `classify_frozen_patch`。冻结补丁与基线清单原样落盘
   （`frozen/`），是候选的权威形态。为让 `scripts/replay_grade.py run --candidate patch-dir:<out>/candidate` 能消费，
   再把冻结补丁渲染成 git 补丁 `<iid>.diff`：修改 / 删除路径的基线字节取自同一派生镜像的一次性容器（root、不联网），
   逐个按基线清单摘要核对；渲染只用宿主临时裸仓库的 git 管道命令（不读任何工作区、仓库配置、属性或钩子），并在
   该仓库里自检"补丁把基线树变成冻结后的树"。回放后由调用方比对回放容器重新导出的冻结补丁与本次是否逐条一致
   （见 r2e_probe_e2e.py）。候选记录保留 `export_ok` / `empty` 两键，run_matrix 的评分分支（空补丁送 noop、导出失败
   不评分）可以直接沿用。
5. 可选 `--legacy-gitdiff-compare`：另按旧探针口径（`git add -N .` + `git diff --binary <stash-create 基线>`，排除
   基线未跟踪清单）导出一份到 `legacy_gitdiff/`，只作对照证据，不交评分。

用法（需要 Docker、本机派生镜像、CC 平台包、已在 --gateway-host:port 监听的宿主网关）：

  SLIME_AGENT_CC_PLATFORM_TARBALL=<claude-code-linux-x64-2.1.205.tgz> \\
  <rh2>/.venv/bin/python experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py --mode solve \\
      --prepared-summary <prepared>/replay_summary.json --overlays <overlays.jsonl> --task <iid> \\
      --out-dir <dir> --attempt-id <id> --gateway-port 18190 --max-context-len 32768 [--max-new-tokens 4096] \\
      [--extra-label rh2.r2e_lifecycle=probe_proto]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import types
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RH2_ROOT = HERE.parents[1]
sys.path.insert(0, str(RH2_ROOT / "src"))
sys.path.insert(0, str(RH2_ROOT / "experiments" / "base_probe_20260922"))
import solve_attempt as sa  # noqa: E402  共用探针入口（本文件不改它）

from repoharness2.grading.manager import TRUSTED_ROOT_EXEC_PREFIX  # noqa: E402

R2E_SOURCE = "r2e_gym_subset"
TEST_PATH_RE = re.compile(r"(^|/)tests?(/|_)|(^|/)test_[^/]*\.py$|_test\.py$")  # 与 solve_attempt 同一口径
_TRUSTED_REWRITES: list[str] = []
_ORIG_DOCKER_BYTES = sa._docker_bytes


def _docker_bytes_trusted(*args: str, timeout: float, input_bytes: bytes | None = None):
    """共用入口 `solve()` 里 root 的 `docker exec <c> bash -c <script>`（打包 CC 会话目录）改走可信前缀；其余原样。"""

    a = list(args)
    if len(a) == 5 and a[0] == "exec" and a[2:4] == ["bash", "-c"]:
        _TRUSTED_REWRITES.append(a[4][:80])
        a = ["exec", a[1], *TRUSTED_ROOT_EXEC_PREFIX, a[4]]
    return _ORIG_DOCKER_BYTES(*a, timeout=timeout, input_bytes=input_bytes)


sa._docker_bytes = _docker_bytes_trusted  # 只影响本进程


def _read_snapshot_id() -> str | None:
    p = RH2_ROOT / "SNAPSHOT_ID"
    try:
        return p.read_text(encoding="utf-8").strip() or None
    except OSError:
        return None


# ---------------------------------------------------------------------------------------------------------------------
# 冻结补丁 → git 补丁（纯宿主侧，可单测）
# ---------------------------------------------------------------------------------------------------------------------

_ATTR_SPECIAL = re.compile(r"[*?\[\\]")


def _attr_pattern(path: str) -> str | None:
    """gitattributes 里按字面匹配一个路径的模式；含空白 / 引号 / 控制字符的路径返回 None（调用方改用全局 binary）。"""

    if any(ch.isspace() or ch in "\"'" or ord(ch) < 0x20 for ch in path):
        return None
    return "/" + _ATTR_SPECIAL.sub(lambda m: "\\" + m.group(0), path)


def _utf8_ok(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def render_git_patch(changes: list[dict[str, Any]], base_blobs: dict[str, tuple[str, bytes]], *, git: str = "git",
                     timeout: float = 600.0) -> tuple[bytes, dict[str, Any]]:
    """把冻结补丁条目渲染成 `git apply` 能在基线工作树上应用的补丁（`--binary --full-index`）。

    changes：冻结补丁条目解码后的列表 `{path, operation, object_type, mode, content(bytes|None)}`；
    base_blobs：修改 / 删除路径的基线 `(mode, bytes)`（调用方已按基线清单摘要核过）。
    做法：宿主临时**裸**仓库里用 `hash-object --no-filters` / `update-index --index-info` / `write-tree` 建两棵只含变更
    路径的树（基线侧、冻结后侧），`diff-tree -p --binary --full-index --no-renames` 出补丁；全局 / 系统配置与系统属性
    关闭，裸仓库没有工作区属性。非 UTF-8 或含回车的内容经 info/attributes 标 binary（replay_grade 以 UTF-8、通用换行读补丁文件）。
    自检：`read-tree 基线树` + `apply --cached` 后 `write-tree` 必须等于冻结后侧的树。"""

    tmp = tempfile.mkdtemp(prefix="rh2r2e_render_")
    env0 = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": tmp, "XDG_CONFIG_HOME": tmp, "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_ATTR_NOSYSTEM": "1", "LC_ALL": "C", "GIT_TERMINAL_PROMPT": "0"}
    repo = os.path.join(tmp, "r.git")

    def g(*args: str, input_bytes: bytes | None = None, index: str | None = None) -> bytes:
        env = dict(env0, GIT_DIR=repo)
        if index is not None:
            env["GIT_INDEX_FILE"] = index
        p = subprocess.run([git, *args], input=input_bytes, capture_output=True, env=env, timeout=timeout)
        if p.returncode != 0:
            raise RuntimeError(f"git {' '.join(args[:3])} 失败（rc={p.returncode}）：{p.stderr.decode(errors='replace')[-400:]}")
        return p.stdout

    try:
        init = subprocess.run([git, "init", "-q", "--bare", "--template=", repo], capture_output=True, env=env0, timeout=60)
        if init.returncode != 0:
            raise RuntimeError(f"git init 失败：{init.stderr.decode(errors='replace')[-300:]}")
        base_entries: dict[str, tuple[str, bytes]] = {}
        post_entries: dict[str, tuple[str, bytes]] = {}
        for c in changes:
            if c["operation"] in ("modify", "delete"):
                base_entries[c["path"]] = base_blobs[c["path"]]
            if c["operation"] in ("add", "modify"):
                post_entries[c["path"]] = (c["mode"], c["content"])
        # 强制按二进制出补丁的路径：非 UTF-8 内容（replay_grade 以 UTF-8 读补丁文件），或含回车（`Path.read_text` 的
        # 通用换行会把补丁里的 \r\n / \r 改成 \n，文本 hunk 就对不上了）；二进制 hunk 是 base85，不含这两类字节
        non_utf8 = sorted({p for p, (_m, raw) in [*base_entries.items(), *post_entries.items()]
                           if not _utf8_ok(raw) or b"\r" in raw})
        attr_mode = "none"
        if non_utf8:
            pats = [_attr_pattern(p) for p in non_utf8]
            if all(pats):
                lines, attr_mode = [f"{p} binary" for p in pats], "per_path"
            else:
                lines, attr_mode = ["* binary"], "global_fallback"
            os.makedirs(os.path.join(repo, "info"), exist_ok=True)
            Path(repo, "info", "attributes").write_text("\n".join(lines) + "\n", encoding="utf-8")

        def tree(entries: dict[str, tuple[str, bytes]], tag: str) -> str:
            if not entries:
                return g("mktree", input_bytes=b"").decode().strip()
            idx = os.path.join(tmp, f"index.{tag}")
            data = b""
            for path, (mode, raw) in sorted(entries.items()):
                sha = g("hash-object", "-w", "--no-filters", "--stdin", input_bytes=raw).decode().strip()
                data += f"{mode} {sha}\t".encode() + path.encode("utf-8", "surrogateescape") + b"\0"
            g("update-index", "-z", "--index-info", input_bytes=data, index=idx)
            return g("write-tree", index=idx).decode().strip()

        base_tree, post_tree = tree(base_entries, "base"), tree(post_entries, "post")
        patch = g("-c", "core.quotePath=true", "diff-tree", "-r", "-p", "--binary", "--full-index", "--no-renames",
                  "--no-ext-diff", "--no-textconv", base_tree, post_tree)
        patch.decode("utf-8")  # 解不了就抛：replay_grade 以 UTF-8 读补丁文件
        if b"\r" in patch:
            raise RuntimeError("补丁含回车字节：replay_grade 的 read_text 会改写它")
        check_idx = os.path.join(tmp, "index.check")
        g("read-tree", base_tree, index=check_idx)
        pf = os.path.join(tmp, "candidate.patch")
        Path(pf).write_bytes(patch)
        g("apply", "--cached", pf, index=check_idx)
        after = g("write-tree", index=check_idx).decode().strip()
        files = [ln[len("diff --git a/"):].split(" b/", 1)[0] for ln in patch.decode("utf-8").splitlines()
                 if ln.startswith("diff --git a/")]
        info = {"base_tree": base_tree, "post_tree": post_tree, "selfcheck_apply_cached_tree": after,
                "selfcheck_ok": after == post_tree, "forced_binary_paths": non_utf8, "attributes_mode": attr_mode,
                "diff_headers": len(files), "files_in_patch": files,
                "binary_hunks": patch.count(b"\nGIT binary patch\n"), "git_version": subprocess.run(
                    [git, "--version"], capture_output=True, text=True, env=env0).stdout.strip()}
        if not info["selfcheck_ok"]:
            raise RuntimeError(f"补丁自检不通过：apply --cached 得到 {after}，应为 {post_tree}")
        return patch, info
    finally:
        subprocess.run(["rm", "-rf", tmp], check=False)


# ---------------------------------------------------------------------------------------------------------------------
# R2E attempt
# ---------------------------------------------------------------------------------------------------------------------


class R2EAttempt(sa.Attempt):
    def __init__(self, ns: argparse.Namespace) -> None:
        super().__init__(ns)
        self.rec.update({
            "schema": "rh2.r2e_probe.attempt.v1",
            "entry": "rh2/experiments/r2e_lifecycle_20260929/r2e_solve_attempt.py",
            "entry_sha256": sa._sha256_file(Path(__file__).resolve()),
            "shared_entry": "rh2/experiments/base_probe_20260922/solve_attempt.py",
            "shared_entry_sha256": sa._sha256_file(Path(sa.__file__).resolve()),
            "code_snapshot_id": _read_snapshot_id(),
            "trusted_root_exec_rewrites": _TRUSTED_REWRITES,
            "deviations": [
                "薄诊断入口：没有 miles / 训练捕获 / receipt；模型端点是宿主侧探针网关（上游为自部署 adapter、供应商或 CPU 验证用的桩），"
                "不是 slime 训练 adapter",
                "每个 attempt 自带一份 egress relay（正式链一 run 一份）",
                "回合上限用 CC 的 --max-turns 与网关的 session 请求上限，不是正式链 adapter 的 turn 预算闸门",
                "静止屏障的'会话面已排空'前提由本入口在 CC 进程退出后置真（没有 adapter 会话撤销 / drain）；其余屏障步骤是正式实现",
                "候选在求解容器里按正式 census 冻结导出（与正式链同）；为交 replay_grade run，另渲染成 git 补丁，回放容器会重新"
                " apply + census 导出，调用方核对两次导出逐条一致",
                "R2E rollout 预检由本入口在启动前以 agent 身份执行（正式 generate.py 目前不跑，回放候选阶段跑）",
            ],
        })
        self.labels: tuple[str, ...] = ()
        self.baseline = None
        self.legacy_baseline_commit: str | None = None

    # ------------------------------------------------------------------ root 一律走可信前缀
    async def sh(self, script: str, *, user: str = "root", timeout: float = 120.0, env: dict[str, str] | None = None,
                 input_bytes: bytes | None = None):
        if user != "root":
            return await super().sh(script, user=user, timeout=timeout, env=env, input_bytes=input_bytes)
        if env:
            raise ValueError("root 命令走可信前缀（env -i），不接受额外环境变量")
        args = ["exec"] + (["-i"] if input_bytes is not None else []) + [self.container, *TRUSTED_ROOT_EXEC_PREFIX, script]
        return await self.dk(*args, timeout=timeout, input_bytes=input_bytes)

    # ------------------------------------------------------------------ 主流程
    async def run(self) -> int:  # noqa: C901 - 与 generate.py 的物化顺序逐段对应，保持线性
        ns = self.ns
        os.environ.setdefault("RH2_BRINGUP_ARTIFACT_DIR", str(self.out / "bringup_artifacts"))
        Path(os.environ["RH2_BRINGUP_ARTIFACT_DIR"]).mkdir(parents=True, exist_ok=True)

        from repoharness2.adapters.slime import prepared_task_face as ptf
        from repoharness2.adapters.slime.baseline_census import (
            BaselineCensusError, baseline_policy_for_task_id, generate_baseline_manifest,
        )
        from repoharness2.adapters.slime.cc_launch_conditions import cc_context_env
        from repoharness2.adapters.slime.docker_sandbox import DockerSandbox
        from repoharness2.adapters.slime.generate import PUBLIC_BUNDLE_CONTAINER_PATH, RolloutContainerWorkspace
        from repoharness2.adapters.slime.r2e_grading_scripts import (
            evaluate_r2e_rollout_preflight, render_r2e_rollout_preflight_script,
        )
        from repoharness2.adapters.slime.sandbox_profile import (
            EgressSubnetPool, agent_shell_env, connect_relay_to_network, create_attempt_network, default_docker_runner,
            rollout_profile_from_env, rollout_trusted_init_script, run_git_sanitize, run_rollout_activation_check,
            run_rollout_prelaunch_check, run_trusted_init, start_egress_relay,
        )
        from repoharness2.contracts.baseline_manifest import compute_baseline_manifest_digest
        from repoharness2.envpack import materialize
        from repoharness2.envpack.prepared_tasks import load_prepared_rollout_views
        from repoharness2.grading.manager import BASE_UNTRACKED_MANIFEST, BASE_UNTRACKED_SNAPSHOT_SCRIPT
        from slime.agent.sandbox import exec_and_wait

        self.docker = default_docker_runner
        summary = json.loads(Path(ns.prepared_summary).read_text(encoding="utf-8"))
        profile = rollout_profile_from_env(
            os.environ, model_proxy_upstream_host=ns.gateway_host, model_proxy_upstream_port=int(ns.gateway_port),
        )
        self.profile = profile

        # 0. 正式 R2E 任务面（覆盖表路径与摘要成对；缺条目 / 互检不过 = 构造即拒，不回退来源镜像）
        overlays_sha = hashlib.sha256(Path(ns.overlays).read_bytes()).hexdigest()
        if ns.overlays_sha256 and ns.overlays_sha256.removeprefix("sha256:") != overlays_sha:
            return self.fail("overlays_sha256_mismatch", f"actual={overlays_sha[:16]} expected={ns.overlays_sha256[:23]}")
        task_id = f"{R2E_SOURCE}::{ns.task.split('::')[-1]}"
        face = ptf.PreparedTaskFace.load(
            prepared_dir=summary["prepared_dir"], manifest_sha256=summary["prepared_manifest_sha256"],
            host_grading_path=Path(summary["private_dir"]) / "host_grading_views.jsonl",
            host_grading_sha256=summary["host_grading_artifact_sha256"], time_budget_seconds=int(ns.wall_seconds),
            image_overlays_path=ns.overlays, image_overlays_sha256=overlays_sha,
        )
        spec = face.rollout_spec(task_id)
        overlay = ptf.load_overlays_input(ns.overlays, overlays_sha)[task_id]
        public = load_prepared_rollout_views(summary["prepared_dir"], face.manifest)[task_id].public
        self.rec.update({
            "task_id": task_id, "instance_id": public.instance_id, "repo": public.repo, "source": R2E_SOURCE,
            "base_commit": spec.base_commit, "workdir": spec.workdir,
            "image_source_public": public.image, "image_used": spec.image, "image_local_build": spec.image_local_build,
            "overlay": {"derived_image_ref": overlay.derived_image_ref, "derived_image_id": overlay.derived_image_id,
                        "recipe_id": overlay.recipe_id, "recipe_sha256": overlay.recipe_sha256,
                        "base_image_ref": overlay.base_image_ref, "built_at_utc": getattr(overlay, "built_at_utc", None)},
            "overlays_path": str(ns.overlays), "overlays_sha256": "sha256:" + overlays_sha,
            "prepared_summary": str(ns.prepared_summary), "prepared_manifest_sha256": summary["prepared_manifest_sha256"],
            "host_grading_artifact_sha256": summary["host_grading_artifact_sha256"],
            "public_bundle_digest": spec.public_bundle_digest,
            "prompt_sha256": "sha256:" + hashlib.sha256(spec.prompt.encode("utf-8")).hexdigest(),
            "env_activation_script_sha256": "sha256:" + hashlib.sha256(spec.env_activation_script.encode()).hexdigest(),
            "expected_interpreter_prefix": spec.expected_interpreter_prefix,
            "profile_parameters": profile.to_parameters(), "profile_digest": profile.digest(),
            "actor_env": "formal_activation(r2e_venv)", "wall_seconds": ns.wall_seconds, "max_turns": ns.max_turns,
            "max_context_len": ns.max_context_len, "max_new_tokens": ns.max_new_tokens,
            "file_read_max_output_tokens": ns.file_read_max_output_tokens, "cc_extra_args": None,
            "gateway": f"{ns.gateway_host}:{ns.gateway_port}", "solver_note": ns.solver_note,
            "extra_labels": list(ns.extra_label or []),
        })
        self.write_text("prompt.txt", spec.prompt)
        self.save()

        # 1. 派生镜像在场（本地构建：rollout 不拉；tag 可重指，按 image ID 启动）
        t = time.monotonic()
        insp = await self.dk("image", "inspect", "-f", "{{.Id}}", spec.image, timeout=60)
        if insp.exit_code != 0 or insp.stdout.strip() != spec.image:
            return self.fail("r2e_derived_image_missing", (insp.stderr or insp.stdout)[-300:])
        self.rec["image_id"] = insp.stdout.strip()
        self.rec["timings"]["image_ready"] = round(time.monotonic() - t, 3)

        extra: list[str] = []
        for kv in ns.extra_label or []:
            extra += ["--label", kv]
        labels = ("--label", f"rh2.run_id={ns.attempt_id}", "--label", "rh2.base_probe=1", "--label", "rh2.r2e_probe=1",
                  *extra)
        self.labels = labels
        name = f"rh2r2e-{sa._slug(public.instance_id, 26)}-{uuid.uuid4().hex[:8]}"

        # 2. relay + attempt 网络 + 容器（参数只由正式 profile 组装）
        t = time.monotonic()
        self.relay = await start_egress_relay(self.docker, profile, run_id=ns.attempt_id, labels=labels)
        self.pool = EgressSubnetPool(profile.egress_subnet_pool, profile.egress_subnet_prefix)
        for _ in range(int(ns.subnet_skip)):
            self.pool.mark_foreign(self.pool.allocate())
        self.network = await create_attempt_network(
            self.docker, profile=profile, pool=self.pool, name=f"{name}-net", labels=labels, max_slots=512,
        )
        await connect_relay_to_network(self.docker, relay=self.relay, network=self.network)
        run = await self.dk(*profile.docker_run_args(name=name, network=self.network.name, image=spec.image, labels=labels),
                            timeout=300)
        if run.exit_code != 0:
            return self.fail("container_start_failed", (run.stderr or run.stdout)[-400:])
        self.container = name
        self.rec["container"] = name
        self.rec["timings"]["network_and_container"] = round(time.monotonic() - t, 3)
        self.stage("container_started", network=self.network.name, subnet=self.network.subnet,
                   relay=self.relay.container_name, relay_image_id=self.relay.image_id)

        # 3. 镜像身份：容器实际 image ID == 任务面 image == 覆盖表 derived_image_id
        ref = await self.dk("inspect", "-f", "{{.Image}}", name, timeout=60)
        actual = ref.stdout.strip()
        ok = ref.exit_code == 0 and actual == spec.image == overlay.derived_image_id
        self.rec["container_image_id"] = actual
        self.stage("image_identity", mode="r2e_overlay_image_id", ok=ok, container_image_id=actual,
                   overlay_derived_image_id=overlay.derived_image_id)
        if not ok:
            return self.fail("r2e_image_identity_mismatch", f"container={actual[:19]} overlay={overlay.derived_image_id[:19]}")

        # 4. /testbed 血缘探针（输出含初态 `git status --porcelain`：R2E 部分题初态带已跟踪改动与未跟踪文件）
        probe = await self.sh(materialize.build_probe_script(spec.base_commit), timeout=300)
        check = materialize.evaluate_probe(spec.base_commit, probe.exit_code, probe.stdout, probe.stderr)
        self.write_text("facts/materialize_probe.txt", probe.stdout + "\n--- stderr ---\n" + probe.stderr)
        if probe.exit_code != 0 or not check.ok:
            return self.fail("testbed_lineage_failed", check.failure_message()[:400])
        head = check.head
        self.rec["materialized_head"] = head
        porcelain = [ln for ln in probe.stdout.splitlines() if re.match(r"^(.[MADRCU?!]|[MADRCU?!].) ", ln)]
        self.stage("materialize_probe", head=head, head_equals_base=(head == spec.base_commit),
                   initial_porcelain=porcelain[:50])

        # 5. git sanitize → root 可信初始化（顺序与正式链一致）
        t = time.monotonic()
        try:
            san = await run_git_sanitize(self.docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
            self.rec["timings"]["git_sanitize"] = round(time.monotonic() - t, 3)
            t = time.monotonic()
            init = await run_trusted_init(self.docker, name=name, script=rollout_trusted_init_script(profile),
                                          timeout=profile.init_timeout_seconds)
        except RuntimeError as exc:
            return self.fail("sanitize_or_init_failed", str(exc)[:400])
        self.rec["timings"]["trusted_init"] = round(time.monotonic() - t, 3)
        self.stage("sanitize_and_init", git_sanitize=san, trusted_init=init)

        # 6. 基线未跟踪清单（generate.py 同样写；census 导出不用它，旧 git diff 口径用）+ public bundle + 激活文件
        snap = await self.sh(f"cd {shlex.quote(spec.workdir)} && "
                             + BASE_UNTRACKED_SNAPSHOT_SCRIPT.format(manifest=BASE_UNTRACKED_MANIFEST), timeout=300)
        if snap.exit_code != 0:
            return self.fail("base_untracked_snapshot_failed", snap.stderr[-300:])
        for path, payload in ((PUBLIC_BUNDLE_CONTAINER_PATH, spec.public_bundle_payload),
                              (materialize.BASH_ENV_PATH, spec.env_activation_script.encode())):
            w = await self.sh(f"mkdir -p $(dirname {shlex.quote(path)}) && cat > {shlex.quote(path)} && chmod 0644 {shlex.quote(path)}",
                              input_bytes=payload, timeout=120)
            if w.exit_code != 0:
                return self.fail("workspace_write_failed", f"{path}: {w.stderr[-300:]}")
        self.stage("bundle_and_activation_written", base_untracked_manifest=BASE_UNTRACKED_MANIFEST)

        # 7. 启动前核对（一次 inspect + 一次 agent 身份探针）：不通过就不启动
        pre = await run_rollout_prelaunch_check(self.docker, name=name, profile=profile, network=self.network.name,
                                                expected_head=head, activation_file=materialize.BASH_ENV_PATH)
        self.write_text("facts/prelaunch.json", json.dumps(pre.to_dict(), ensure_ascii=False, indent=1, default=str))
        self.stage("prelaunch_check", ok=pre.ok, violations=list(pre.violations), seconds=round(pre.seconds, 3))
        if not pre.ok:
            return self.fail("prelaunch_check_failed", "; ".join(pre.violations)[:600])

        # 8. 基线 census（harness 获写权前；与 generate._prepare_workspace 同一函数、同一 R2E 政策、同一可信 root 通道）
        ws = RolloutContainerWorkspace(docker=self.docker, container_name=name, testbed_path=spec.workdir)
        hd = await ws.run_bash(f"git -C {shlex.quote(spec.workdir)} rev-parse HEAD")
        if hd.exit_code != 0:
            return self.fail("baseline_head_unreadable", hd.stderr[-200:])
        t = time.monotonic()
        omitted: dict[str, int] = {}
        try:
            baseline = await generate_baseline_manifest(
                ws, task_id=task_id, workdir=spec.workdir, public_bundle_digest=spec.public_bundle_digest,
                runtime_image_digest=self.rec["image_id"], materialized_head=hd.stdout.strip(),
                task_base_commit=spec.base_commit, policy=baseline_policy_for_task_id(task_id), omitted_sink=omitted,
            )
        except BaselineCensusError as exc:
            return self.fail("baseline_census_failed", str(exc)[:400])
        self.rec["timings"]["baseline_census"] = round(time.monotonic() - t, 3)
        self.baseline = baseline
        (self.out / "frozen").mkdir(exist_ok=True)
        (self.out / "frozen" / "baseline_manifest.json").write_text(baseline.model_dump_json(indent=1), encoding="utf-8")
        self.rec["baseline_manifest_digest"] = compute_baseline_manifest_digest(baseline)
        self.stage("baseline_census", digest=self.rec["baseline_manifest_digest"], entries=len(baseline.entries),
                   policy=baseline.policy.policy_version, excluded_namespaces=list(baseline.policy.excluded_namespaces),
                   omitted_cache=omitted, seconds=self.rec["timings"]["baseline_census"])

        # 9. R2E rollout 预检（agent 身份；census 之后——B 线 B1；失败 = 派生环境没接好，不启动）
        pf = await self.sh(render_r2e_rollout_preflight_script(), user=str(profile.agent_uid),
                           timeout=profile.probe_timeout_seconds)
        failures = evaluate_r2e_rollout_preflight(pf.stdout)
        self.write_text("facts/r2e_preflight.txt", pf.stdout + "\n--- stderr ---\n" + pf.stderr)
        self.stage("r2e_preflight", ok=not failures, failures=failures, identity=f"uid {profile.agent_uid}",
                   lines=[ln for ln in pf.stdout.splitlines() if ln.startswith("RH2_PREFLIGHT_")])
        if failures:
            return self.fail("r2e_preflight_failed", ";".join(failures)[:400])

        if ns.legacy_gitdiff_compare:
            # 旧探针的 F4 基线（stash create 只写悬空提交对象，不改工作区 / 索引 / refs；.git 在 census 排除区）
            st = await self.sh(f"cd {shlex.quote(spec.workdir)} && git -c user.name=rh2 -c user.email=rh2@local "
                               "-c core.fsmonitor=false stash create 'rh2 materialized baseline'", timeout=300)
            self.legacy_baseline_commit = st.stdout.strip() or head

        # 10. 激活核对 + 逐 execution 注入（与 solve_attempt / generate.py 同形）
        shell_env = agent_shell_env(profile, activation_file=materialize.BASH_ENV_PATH)
        act = await run_rollout_activation_check(self.docker, name=name, profile=profile, env=shell_env,
                                                 expected_interpreter_prefix=spec.expected_interpreter_prefix)
        self.write_text("facts/activation_check.json", json.dumps(act.to_dict(), ensure_ascii=False, indent=1, default=str))
        self.stage("activation_check", ok=act.ok, violations=list(act.violations), facts=dict(act.probe_facts))
        if not act.ok:
            return self.fail("activation_check_failed", "; ".join(act.violations)[:600])
        env_injections = {**shell_env, **cc_context_env(max_context_len=int(ns.max_context_len), max_new_tokens=ns.max_new_tokens,
                                                         file_read_max_output_tokens=ns.file_read_max_output_tokens)}
        self.rec["env_injections"] = env_injections
        agent_env = {
            "ANTHROPIC_BASE_URL": profile.harness_adapter_url(), "ANTHROPIC_AUTH_TOKEN": ns.attempt_id,
            "ANTHROPIC_MODEL": "slime-actor", "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
            "CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS": "1", "CLAUDE_CODE_ATTRIBUTION_HEADER": "0", **shell_env,
        }

        # 11. agent 身份的环境事实（slime exec_and_wait，输出在 /tmp，不进 /testbed）
        sb = DockerSandbox(name)
        rc, out = await exec_and_wait(sb, cmd=sa.AGENT_ENV_FACTS_SCRIPT, user="agent", env=agent_env, workdir=spec.workdir,
                                      time_budget_sec=120, tag="rh2facts", want_output=True)
        self.write_text("facts/agent_env_facts.txt", out)
        facts = {ln.split("=", 1)[0]: ln.split("=", 1)[1] for ln in out.splitlines() if ln.startswith("RH2F_") and "=" in ln}
        self.stage("agent_env_facts", exit_code=rc, facts=facts)

        exit_code = 0
        if ns.mode == "dev-check":
            script = Path(ns.dev_script).read_text(encoding="utf-8")
            t = time.monotonic()
            rc, out = await exec_and_wait(sb, cmd=script, user="agent", env=agent_env, workdir=spec.workdir,
                                          time_budget_sec=int(ns.wall_seconds), tag="rh2dev", want_output=True)
            self.write_text("dev_check_output.txt", out)
            self.rec["timings"]["dev_check"] = round(time.monotonic() - t, 3)
            self.stage("dev_check", script=str(ns.dev_script), script_sha256=sa._sha256_file(Path(ns.dev_script)), exit_code=rc)
            self.rec["result"] = "dev_check_done"
            self.rec["dev_check_exit_code"] = rc
        else:
            exit_code = await self.solve(sb, spec, agent_env, env_injections)  # 共用入口的正式 CC 启动（预算、轨迹、会话目录）

        # 12. 候选：正式静止屏障 → census 冻结导出 → 分类 → 渲染 git 补丁（两种模式都做：dev-check 下是开发命令的产物）
        await self.export_candidate(spec, head, public.instance_id)
        return exit_code

    # ------------------------------------------------------------------ 候选导出（覆盖共用入口的 git diff 口径）
    async def export_candidate(self, spec, head: str, instance_id: str) -> None:  # noqa: C901
        from repoharness2.adapters.slime.generate import QuiescenceConfirmed, RolloutContainerWorkspace
        from repoharness2.adapters.slime.patch_exporter import PatchExportError, export_frozen_patch
        from repoharness2.adapters.slime.quiescence_barrier import DockerQuiescenceBarrier
        from repoharness2.contracts.frozen_patch import compute_frozen_patch_digest
        from repoharness2.contracts.scoring_projection import ProjectionContractError, classify_frozen_patch

        cand: dict[str, Any] = {"form": "frozen_patch_v1 (+ git patch rendered for replay_grade patch-dir)",
                                "export_ok": False, "empty": None}
        self.rec["candidate"] = cand
        ws = RolloutContainerWorkspace(docker=self.docker, container_name=self.container, testbed_path=spec.workdir)
        audit = types.SimpleNamespace(session_plane_drained=True, termination={})
        t = time.monotonic()
        q = await DockerQuiescenceBarrier(spec.workdir).establish(workspace=ws, audit=audit)
        self.rec["timings"]["quiescence"] = round(time.monotonic() - t, 3)
        if not isinstance(q, QuiescenceConfirmed):
            self.stage("quiescence", ok=False, reason=q.reason_code, evidence=list(q.evidence_refs),
                       barrier_stop=audit.termination.get("barrier_stop"))
            self.rec["result"] = "infra_failed:quiescence_rejected"
            self.rec["failure_detail"] = q.reason_code
            self.save()
            return
        self.stage("quiescence", ok=True, snapshot_ref=q.snapshot_ref, evidence=list(q.evidence_refs),
                   barrier_stop=audit.termination.get("barrier_stop"))

        segs: dict[str, float] = {}
        post_omitted: dict[str, int] = {}
        try:
            art = await export_frozen_patch(q.frozen_grading_workspace, self.baseline,
                                            rollout_execution_id=self.ns.attempt_id,
                                            physical_attempt_id=f"{self.ns.attempt_id}#p1",
                                            segment_sink=segs, omitted_sink=post_omitted)
        except PatchExportError as exc:
            unsafe = exc.reason_code in ("unsupported_object_in_patch", "unsupported_delta_shape")
            cand.update(frozen_export_ok=False, unsafe=unsafe, export_error=f"{exc.reason_code}: {exc}"[:400],
                        object_path=exc.object_path, object_type=exc.object_type, export_segments=segs)
            # 正式链：unsafe = 模型产物 present + 永久拒绝、不评分（result 保持 ran，export_ok=False → 调度器不评分）；
            # 其它导出失败 = 执行基础设施失败（不是空补丁）
            if not unsafe:
                self.rec["result"] = "infra_failed:frozen_export_failed"
                self.rec["failure_detail"] = cand["export_error"]
            self.save()
            return
        (self.out / "frozen").mkdir(exist_ok=True)
        (self.out / "frozen" / "frozen_patch.json").write_text(art.model_dump_json(indent=1), encoding="utf-8")
        try:
            cls, _ = classify_frozen_patch(art, self.baseline)
            verdict, reasons = cls.verdict, list(cls.reason_codes)
            (self.out / "frozen" / "classification.json").write_text(cls.model_dump_json(indent=1), encoding="utf-8")
        except ProjectionContractError as exc:
            verdict, reasons = "contract_error", [str(exc)[:300]]
        base_by_path = {e.path: e for e in self.baseline.entries}
        entries = []
        for e in art.entries:
            b = base_by_path.get(e.path)
            entries.append({
                "path": e.path, "operation": e.operation, "object_type": e.object_type, "mode": e.mode,
                "bytes": len(base64.b64decode(e.content_b64)) if e.content_b64 else None, "digest": e.content_digest,
                "baseline_digest": (b.content_digest or b.symlink_target_digest) if b is not None else None,
                "baseline_mode": b.mode if b is not None else None,
            })
        files = [e.path for e in art.entries]
        cand.update({
            "frozen_export_ok": True, "frozen_patch_digest": compute_frozen_patch_digest(art),
            "baseline_manifest_digest": art.baseline_manifest_digest, "entry_count": len(art.entries), "entries": entries,
            "files": files, "touches_tests": [p for p in files if TEST_PATH_RE.search(p)],
            "excluded_pathset_changed": art.excluded_pathset_changed, "classification": {"verdict": verdict, "reasons": reasons},
            "unsafe": verdict != "projectable", "export_segments": {k: round(v, 3) for k, v in segs.items()},
            "post_omitted_cache": post_omitted, "empty": not art.entries,
        })
        self.save()
        if cand["unsafe"]:
            if verdict != "unsafe_artifact":  # 契约矛盾 = 基础设施问题；unsafe_artifact = 模型产物永久拒绝（不评分）
                self.rec["result"] = "infra_failed:classify_contract_error"
                self.rec["failure_detail"] = ";".join(reasons)[:300]
            self.save()
            return
        if not art.entries:
            cand["export_ok"] = True  # 合法空补丁：调用方送 noop
            self.save()
        else:
            t = time.monotonic()
            try:
                info = await self.render_candidate(art, spec, instance_id)
                cand.update(render=info, export_ok=True, bytes=info["bytes"], sha256=info["sha256"])
            except Exception as exc:  # noqa: BLE001 - 冻结补丁已落盘；渲染失败 = 不交评分（不是空补丁）
                cand.update(render_ok=False, render_error=f"{type(exc).__name__}: {exc}"[:600])
                self.rec["result"] = "infra_failed:candidate_render_failed"
                self.rec["failure_detail"] = cand["render_error"]
            self.rec["timings"]["candidate_render"] = round(time.monotonic() - t, 3)
            self.save()
        if self.ns.legacy_gitdiff_compare:
            await self.legacy_gitdiff_compare(spec, head, instance_id)

    async def fetch_baseline_bytes(self, image: str, workdir: str, paths: list[str]) -> dict[str, tuple[str, bytes]]:
        """修改 / 删除路径的基线字节：同一派生镜像的一次性容器（root、不联网、可信前缀），逐个按基线清单摘要核对。"""

        base_by_path = {e.path: e for e in self.baseline.entries}
        lines = ["set -e", f"cd {shlex.quote(workdir)}"]
        for i, p in enumerate(paths):
            e = base_by_path.get(p)
            if e is None:
                raise RuntimeError(f"基线清单里没有 {p!r}")
            q = shlex.quote(p)
            if e.object_type == "symlink":
                lines.append(f"printf 'F{i}\\t'; readlink -- {q} | tr -d '\\n' | base64 | tr -d '\\n'; printf '\\n'")
            else:
                lines.append(f"printf 'F{i}\\t'; base64 < {q} | tr -d '\\n'; printf '\\n'")
        name = f"rh2r2e-basefetch-{uuid.uuid4().hex[:10]}"
        rec: dict[str, Any] = {"name": name, "paths": len(paths)}
        self.rec.setdefault("baseline_fetch", []).append(rec)
        run = await self.dk("run", "-d", "--network", "none", *self.labels, "--name", name, "--entrypoint", "/bin/sleep",
                            image, "infinity", timeout=180)
        try:
            if run.exit_code != 0:
                raise RuntimeError(f"基线取数容器启动失败：{(run.stderr or run.stdout)[-300:]}")
            res = await self.dk("exec", name, *TRUSTED_ROOT_EXEC_PREFIX, "\n".join(lines) + "\n", timeout=600)
        finally:
            rm = await self.dk("rm", "-f", name, timeout=120)
            rec["rm_exit"] = rm.exit_code
        if res.exit_code != 0:
            raise RuntimeError(f"基线取数失败（exit={res.exit_code}）：{res.stderr[-300:]}")
        got: dict[str, tuple[str, bytes]] = {}
        for line in res.stdout.splitlines():
            if not line.startswith("F") or "\t" not in line:
                continue
            idx, _, b64 = line.partition("\t")
            p = paths[int(idx[1:])]
            raw = base64.b64decode(b64, validate=True)
            e = base_by_path[p]
            want = e.content_digest if e.object_type == "regular" else e.symlink_target_digest
            if "sha256:" + hashlib.sha256(raw).hexdigest() != want:
                raise RuntimeError(f"基线字节与基线清单摘要不符：{p!r}（一次性容器的树不是求解容器的基线）")
            got[p] = (e.mode, raw)
        missing = sorted(set(paths) - set(got))
        if missing:
            raise RuntimeError(f"基线取数缺路径：{missing[:5]}")
        rec["verified"] = len(got)
        return got

    async def render_candidate(self, art, spec, instance_id: str) -> dict[str, Any]:
        need = sorted({e.path for e in art.entries if e.operation in ("modify", "delete")})
        base_blobs = await self.fetch_baseline_bytes(spec.image, spec.workdir, need) if need else {}
        changes = [{"path": e.path, "operation": e.operation, "object_type": e.object_type, "mode": e.mode,
                    "content": base64.b64decode(e.content_b64) if e.content_b64 is not None else None}
                   for e in art.entries]
        patch, info = await asyncio.to_thread(render_git_patch, changes, base_blobs)
        cdir = self.out / "candidate"
        cdir.mkdir(exist_ok=True)
        (cdir / f"{instance_id}.diff").write_bytes(patch)
        info.update(bytes=len(patch), sha256="sha256:" + hashlib.sha256(patch).hexdigest(),
                    path=f"candidate/{instance_id}.diff", baseline_paths_fetched=len(need))
        missing = sorted(set(e.path for e in art.entries) - set(info["files_in_patch"]))
        info["frozen_paths_missing_from_patch_headers"] = missing  # 带引号的路径不在简单解析里（记录，不判错）
        return info

    async def legacy_gitdiff_compare(self, spec, head: str, instance_id: str) -> None:
        """对照证据：旧探针口径（solve_attempt.export_candidate 的同一脚本形态，基线 = stash create）。不交评分。"""

        from repoharness2.grading.manager import BASE_UNTRACKED_MANIFEST

        base = self.legacy_baseline_commit or head
        wd = shlex.quote(spec.workdir)
        script = (
            f"cd {wd} && git -c core.fsmonitor=false add -N . 1>&2 && excl=() && "
            f"if [ -f {BASE_UNTRACKED_MANIFEST} ]; then while IFS= read -r p; do "
            '[ -n "$p" ] && excl+=(":(exclude,literal)$p"); '
            f"done < {BASE_UNTRACKED_MANIFEST}; fi && "
            f'git -c core.fileMode=false -c core.fsmonitor=false diff --no-ext-diff --no-textconv --binary {base} -- . "${{excl[@]}}"'
        )
        rc, data, err = await asyncio.to_thread(
            _ORIG_DOCKER_BYTES, "exec", self.container, *TRUSTED_ROOT_EXEC_PREFIX, script, timeout=600)
        d = self.out / "legacy_gitdiff"
        d.mkdir(exist_ok=True)
        if rc == 0:
            (d / f"{instance_id}.diff").write_bytes(data)
        files = sorted({ln.split(" b/", 1)[1] for ln in data.decode("utf-8", "replace").splitlines()
                        if ln.startswith("diff --git ") and " b/" in ln}) if rc == 0 else []
        frozen = set((self.rec.get("candidate") or {}).get("files") or [])
        self.rec["legacy_gitdiff_compare"] = {
            "exit_code": rc, "stderr_tail": err.decode("utf-8", "replace")[-300:], "bytes": len(data) if rc == 0 else 0,
            "baseline": base, "baseline_is_head": base == head, "files": files,
            "only_in_frozen_census": sorted(frozen - set(files)), "only_in_legacy_gitdiff": sorted(set(files) - frozen),
        }
        self.save()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="R2E 基座探针：一次真实解题身份的尝试（dev-check | solve）")
    ap.add_argument("--mode", choices=("dev-check", "solve"), required=True)
    ap.add_argument("--prepared-summary", required=True, help="replay_grade.py prepare 写出的 replay_summary.json（含 R2E 来源）")
    ap.add_argument("--overlays", required=True, help="派生镜像覆盖表 overlays.jsonl（与 prepared 同批）")
    ap.add_argument("--overlays-sha256", default=None, help="可选：钉住覆盖表文件摘要（不给则按文件现算并记录）")
    ap.add_argument("--task", required=True, help="裸 instance_id 或 r2e_gym_subset::<iid>")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--attempt-id", required=True, help="也是网关的 session token：[A-Za-z0-9_.-]{6,96}")
    ap.add_argument("--solver", default="none")
    ap.add_argument("--solver-note", default=None)
    ap.add_argument("--gateway-host", default="172.17.0.1", help="relay 的上游 = 宿主侧网关地址")
    ap.add_argument("--gateway-port", type=int, default=18190)
    ap.add_argument("--wall-seconds", type=int, default=1800)
    ap.add_argument("--max-turns", type=int, default=60)
    ap.add_argument("--max-context-len", type=int, required=True, help="CC 窗口；必须与 adapter 的 --max-context-tokens 同一个数")
    ap.add_argument("--max-new-tokens", type=int, default=None)
    ap.add_argument("--file-read-max-output-tokens", type=int, default=None)
    ap.add_argument("--cc-extra-args", default=None)
    ap.add_argument("--dev-script", default=None, help="dev-check 模式的确定性命令脚本（host 文件，只含公开内容）")
    ap.add_argument("--subnet-skip", type=int, default=0)
    ap.add_argument("--extra-label", action="append", default=[], help="额外容器 / 网络标签 k=v（可重复）")
    ap.add_argument("--legacy-gitdiff-compare", action="store_true", help="另按旧 git diff 口径导出一份对照（不交评分）")
    ns = ap.parse_args(argv)
    if not re.match(r"^[A-Za-z0-9_.-]{6,96}$", ns.attempt_id):
        ap.error("--attempt-id 形态不合法")
    for kv in ns.extra_label:
        if not re.match(r"^[A-Za-z0-9_.-]+=[A-Za-z0-9_.:-]*$", kv):
            ap.error(f"--extra-label 形态不合法：{kv!r}")
    if ns.mode == "dev-check" and not ns.dev_script:
        ap.error("dev-check 需要 --dev-script")
    if ns.mode == "solve" and not os.environ.get("SLIME_AGENT_CC_PLATFORM_TARBALL"):
        ap.error("solve 需要环境变量 SLIME_AGENT_CC_PLATFORM_TARBALL（claude-code-linux-x64 平台包）")
    return ns


async def _amain(ns: argparse.Namespace) -> int:
    attempt = R2EAttempt(ns)
    code = 4
    loop = asyncio.get_running_loop()
    inner = asyncio.ensure_future(attempt.run())
    for sig in (signal.SIGTERM, signal.SIGINT):  # 与 task2 devcheck 同：取消主任务后仍走清理
        loop.add_signal_handler(sig, inner.cancel)
    try:
        code = await inner
    except BaseException as exc:  # noqa: BLE001 - 记录后原样处理；清理一定执行
        attempt.rec["result"] = attempt.rec.get("result") or f"infra_failed:exception:{type(exc).__name__}"
        attempt.rec["exception"] = f"{type(exc).__name__}: {exc}"[:800]
        attempt.save()
        code = 130 if isinstance(exc, asyncio.CancelledError) else 3
    finally:
        try:
            await attempt.cleanup()
        except Exception as exc:  # noqa: BLE001
            attempt.rec["cleanup_exception"] = f"{type(exc).__name__}: {exc}"[:400]
            attempt.rec.setdefault("cleanup", {})["cleanup_ok"] = False
            attempt.save()
    if not (attempt.rec.get("cleanup") or {}).get("cleanup_ok"):
        code = 4  # 清理失败或无法确认：候选与现场保留，调用方必须停止派发
    print(json.dumps({"attempt_id": ns.attempt_id, "result": attempt.rec.get("result"),
                      "termination": attempt.rec.get("termination"),
                      "candidate": {k: v for k, v in (attempt.rec.get("candidate") or {}).items() if k != "entries"},
                      "cleanup": attempt.rec.get("cleanup")}, ensure_ascii=False, default=str), flush=True)
    return code


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_amain(parse_args(argv)))


if __name__ == "__main__":
    raise SystemExit(main())
