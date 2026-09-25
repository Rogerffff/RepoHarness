"""第六组 E2a（E2/E4 Brief §1.5）：批量哈希的 census 与现行逐文件 census 在真实 Linux 上逐字节同输出。

对照物是 E2a 之前的 `build_census_script` 原文（下面 `_frozen_census_script`，逐字冻结）。语料树覆盖空树、空格 / 反斜线
/ TAB / LF / CR / 控制字符 / 非 ASCII 文件名、各种权限位（含 0000 与 setuid）、相对 / 绝对 / 悬空 / 目标含换行的软链、
指向目录的软链、同名缓存文件与软链、排除区边界（`.gitx` / `.harnessy` 不排除）、空目录、FIFO 与 socket；三种基线政策
（v1 / v2 / r2e_v1）× root / 非 root（单个文件读不了 → 批量失败整批回退）/ 强制回退。

唯一允许的差别（同批修复）：旧脚本对含反斜线或回车的文件名把 sha256sum 的转义前缀带进摘要（`\\<hash>`）；新脚本给出
正确摘要。差分只对旧输出做这一处规范化并计数。另核：root 时确实走批量路径（sha256sum 调用次数从"每个文件一次"降到
"每个软链一次 + 批次数"）；导出器端到端——反斜线文件名照常导出、含回车的文件名走既有不支持路径名处置（不再 run-fatal）。
"""

from __future__ import annotations

import asyncio
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from re import escape as re_escape
from shlex import quote as shlex_quote

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_patch_export_path_names import _baseline  # noqa: E402

from repoharness2.adapters.slime import sandbox_profile as sp  # noqa: E402
from repoharness2.adapters.slime.baseline_census import build_census_script  # noqa: E402
from repoharness2.adapters.slime.generate import RolloutContainerWorkspace  # noqa: E402
from repoharness2.adapters.slime.patch_exporter import PatchExportError, export_frozen_patch  # noqa: E402
from repoharness2.contracts.baseline_manifest import (  # noqa: E402
    BASELINE_MANIFEST_POLICY_R2E_V1,
    BASELINE_MANIFEST_POLICY_V1,
    BASELINE_MANIFEST_POLICY_V2,
)

def _frozen_census_script(workdir: str, policy) -> str:
    """枚举脚本：每行 `<kind>\\t<perm>\\t<sha256>\\t<path>`；排除区行首用
    EXCL 标记（独立 census）。遇到不支持对象类型输出 UNSUPPORTED 行。"""

    prunes = " ".join(
        f"-path './{ns.rstrip('/')}' -prune -o" for ns in policy.excluded_namespaces
    )
    # 第四组 P-C（R4）：只剪**目录**（-type d），同名普通文件/软链照常列出；被剪目录下的文件只计数，不进 digest。
    cache_dirs = tuple(policy.regenerable_cache_dirs)
    if cache_dirs:
        names = " -o ".join(f"-name {shlex_quote(d)}" for d in cache_dirs)
        ns_prunes = prunes
        prunes = prunes + f" \\( -type d \\( {names} \\) -prune \\) -o"
        alt = "|".join(re_escape(d) for d in cache_dirs)
        cache_count = (
            f"echo \"CACHE_OMITTED_DIRS\t$(find . {ns_prunes} -type d \\( {names} \\) -prune -print | wc -l | tr -d ' ')\"\n"
            f"echo \"CACHE_OMITTED_FILES\t$(find . {ns_prunes} -type f -print | grep -c -E '/({alt})/' || true)\"\n"
        )
    else:
        cache_count = ""
    excl_finds = " ; ".join(
        f"find './{ns.rstrip('/')}' -type f -print 2>/dev/null | LC_ALL=C sort | "
        f"while IFS= read -r p; do printf 'EXCL\\t%s\\n' \"${{p#./}}\"; done"
        for ns in policy.excluded_namespaces
    )
    return f"""set -e
cd {workdir}
find . {prunes} \\( -type f -o -type l -o \\( ! -type d ! -type f ! -type l \\) \\) -print | LC_ALL=C sort | while IFS= read -r p; do
  rel="${{p#./}}"
  if [ -L "$p" ]; then
    tgt=$(readlink "$p" | tr -d '\\n' | sha256sum | cut -d' ' -f1)
    printf 'symlink\\t120000\\t%s\\t%s\\n' "$tgt" "$rel"
  elif [ -f "$p" ]; then
    if [ -x "$p" ]; then perm=100755; else perm=100644; fi
    sha=$(sha256sum "$p" | cut -d' ' -f1)
    printf 'regular\\t%s\\t%s\\t%s\\n' "$perm" "$sha" "$rel"
  else
    if [ -p "$p" ]; then t=fifo; elif [ -S "$p" ]; then t=socket; elif [ -b "$p" ]; then t=block_device; elif [ -c "$p" ]; then t=char_device; else t=unknown; fi
    printf 'UNSUPPORTED\\t%s\\t%s\\n' "$t" "$rel"
  fi
done
{excl_finds}
{cache_count}"""



CORPUS = r"""# 语料树（root 在容器里建）：特殊文件名、权限位、软链、同名缓存文件 / 软链、排除区边界、空目录、特殊文件类型
set -e
W="${1:-/work/tree}"
rm -rf "$W"; mkdir -p "$W"; cd "$W"
mkdir -p src/pkg sub/deep/er empty_dir .git/objects .harness .venv/bin src/__pycache__ src/pkg/.pytest_cache
printf 'a\n' > src/a.py
printf 'with space\n' > "src/with space.py"
printf 'bs\n' > 'src/back\slash.py'
printf 'tab\n' > "$(printf 'src/ta\tb.py')"
printf 'lf\n' > "$(printf 'src/l\nf.py')"
printf 'cr\n' > "$(printf 'src/c\rr.py')"
printf 'ctl\n' > "$(printf 'src/ctl\001.py')"
printf 'utf8\n' > "src/中文名.py"
printf '' > src/empty.py
head -c 300000 /dev/urandom > src/big.bin
printf 'x\n' > src/exec_owner.sh; chmod 0744 src/exec_owner.sh
printf 'x\n' > src/exec_other.sh; chmod 0601 src/exec_other.sh
printf 'x\n' > src/exec_group.sh; chmod 0610 src/exec_group.sh
printf 'x\n' > src/noperm.txt; chmod 0000 src/noperm.txt
printf 'x\n' > src/ro.txt; chmod 0444 src/ro.txt
printf 'x\n' > src/setuid.sh; chmod 4755 src/setuid.sh
ln -s a.py src/link_rel
ln -s /etc/hostname src/link_abs
ln -s nowhere src/link_dangling
ln -s "$(printf 'odd\ntarget')" src/link_lf_target
ln -s sub sublink_dir
ln -s ../src sub/deep/up
printf 'c\n' > src/pkg/mod.py
printf 'pyc\n' > src/__pycache__/a.cpython-312.pyc
printf 'cache\n' > src/pkg/.pytest_cache/v
printf 'file named like a cache dir\n' > src/pkg/__pycache__
ln -s a.py sub/__pycache__
printf 'g\n' > .git/objects/x
printf 'h\n' > .harness/y
printf 'v\n' > .venv/bin/python
printf 'not excluded\n' > .gitx
printf 'not excluded\n' > .harnessy
mkfifo src/fifo
python3 -c "import socket,os; s=socket.socket(socket.AF_UNIX); s.bind('src/sock')"
printf 'deep\n' > sub/deep/er/leaf.txt
"""

IMAGE = sp.RELAY_IMAGE_DEFAULT  # 钉死 digest 的 python:3.12-slim（Debian coreutils；本机已在场，测试不拉镜像）
ESCAPED = re.compile(rb"(?m)^(regular\t[0-9]{6}\t)\\")  # 行首摘要位前的一个转义反斜线
POLICIES = (("v1", BASELINE_MANIFEST_POLICY_V1), ("v2", BASELINE_MANIFEST_POLICY_V2), ("r2e_v1", BASELINE_MANIFEST_POLICY_R2E_V1))
TRUSTED_ENV = ["/usr/bin/env", "-i", "PATH=/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/root"]
SHELL = ["/bin/bash", "--noprofile", "--norc", "-c"]


def _docker_with_image(image: str) -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        return subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=30).returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False


needs_docker = pytest.mark.skipif(not _docker_with_image(IMAGE), reason="本机 docker 不可用或没有钉死的 python 镜像（测试不拉镜像）")


@pytest.fixture(scope="module")
def box():
    if not _docker_with_image(IMAGE):
        pytest.skip("docker 不可用")
    name = f"rh2-e2a-{uuid.uuid4().hex[:8]}"
    run = subprocess.run(["docker", "run", "-d", "--init", "--name", name, IMAGE, "sleep", "900"], capture_output=True, text=True)
    assert run.returncode == 0, run.stderr

    def dexec(*args, user=None, stdin=None):
        cmd = ["docker", "exec", "-i"] + (["-u", user] if user else []) + [name, *args]
        return subprocess.run(cmd, input=stdin, capture_output=True, timeout=600)

    try:
        for tree in ("/work/tree", "/testbed"):
            made = dexec("/bin/bash", "-s", tree, stdin=CORPUS.encode())
            assert made.returncode == 0, made.stderr.decode()
        prep = dexec("/bin/bash", "-c", "mkdir -p /work/emptytree && chmod -R a+rX /work && chmod 0000 /work/tree/src/noperm.txt")
        assert prep.returncode == 0
        yield name, dexec
    finally:
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)


def test_the_script_keeps_the_keywords_existing_fakes_dispatch_on():
    script = build_census_script("/testbed", BASELINE_MANIFEST_POLICY_V2)
    assert all(k in script for k in ("find .", "-prune", "readlink", "sha256sum"))
    assert "xargs -0 -r sha256sum" in script and "rh2_census_per_file" in script


@pytest.mark.docker
@needs_docker
@pytest.mark.parametrize("tree", ["/work/tree", "/work/emptytree"])
@pytest.mark.parametrize(("policy_name", "policy"), POLICIES)
@pytest.mark.parametrize(("mode", "user", "extra_env"), [
    ("root", None, []),
    ("nonroot_digest_failure", "65534", []),
    ("forced_fallback", None, ["RH2_CENSUS_FORCE_FALLBACK=1"]),
])
def test_new_census_matches_the_frozen_one_byte_for_byte(box, tree, policy_name, policy, mode, user, extra_env):
    _name, dexec = box
    old = dexec(*TRUSTED_ENV, *SHELL, _frozen_census_script(tree, policy), user=user)
    new = dexec(*TRUSTED_ENV, *extra_env, *SHELL, build_census_script(tree, policy), user=user)
    assert (old.returncode, new.returncode) == (0, 0)
    assert ESCAPED.sub(rb"\1", old.stdout) == new.stdout
    # 旧输出里只有反斜线与回车两个文件名带了转义前缀（语料树），空树没有
    assert len(ESCAPED.findall(old.stdout)) == (2 if tree == "/work/tree" else 0)
    assert not ESCAPED.findall(new.stdout)


@pytest.mark.docker
@needs_docker
def test_root_takes_the_batched_path_with_far_fewer_hash_processes(box):
    _name, dexec = box
    shim = (
        "mkdir -p /shim && printf '#!/bin/sh\\necho x >> /shim/calls\\nexec /usr/bin/sha256sum \"$@\"\\n' > /shim/sha256sum"
        " && chmod 0755 /shim/sha256sum"
    )
    assert dexec("/bin/bash", "-c", shim).returncode == 0

    def calls(script: str) -> int:
        dexec("/bin/bash", "-c", "rm -f /shim/calls")
        run = dexec("/usr/bin/env", "-i", "PATH=/shim:/usr/sbin:/usr/bin:/sbin:/bin", "HOME=/root", *SHELL, script)
        assert run.returncode == 0
        return int(dexec("/bin/bash", "-c", "wc -l < /shim/calls").stdout.strip() or 0)

    policy = BASELINE_MANIFEST_POLICY_V1
    old_calls = calls(_frozen_census_script("/work/tree", policy))
    new_calls = calls(build_census_script("/work/tree", policy))
    listing = dexec(*TRUSTED_ENV, *SHELL, build_census_script("/work/tree", policy)).stdout
    symlinks = listing.count(b"\nsymlink\t") + listing.startswith(b"symlink\t")
    regular = listing.count(b"\nregular\t") + listing.startswith(b"regular\t")
    assert old_calls == regular + symlinks  # 旧：每个普通文件与软链各一次
    assert new_calls <= symlinks + 2 and new_calls < old_calls  # 新：软链各一次 + 一次（或少数几次）批量


class _BoxWorkspace:
    """在测试容器里以 root 可信通道执行（与 rollout 工作区通道同一前缀）。"""

    def __init__(self, name: str) -> None:
        self._inner = RolloutContainerWorkspace(docker=sp.default_docker_runner, container_name=name)

    async def run_bash(self, script):
        return await self._inner.run_bash(script)


@pytest.mark.docker
@needs_docker
def test_exporter_end_to_end_backslash_and_carriage_return_names_no_longer_halt_the_run(box, monkeypatch):
    """导出器端到端（真实容器里跑 census）：修复前两种文件名都让解析抛字段级 ValidationError（run-fatal）；修复后反斜线
    文件名照常导出，含回车的文件名被 `splitlines()` 切成两行，按既有规则是单题的 `post_census_parse_failed`。"""
    import hashlib

    from repoharness2.adapters.slime import patch_exporter
    from pydantic import ValidationError

    name, dexec = box

    def export():
        return asyncio.run(export_frozen_patch(_BoxWorkspace(name), _baseline(), rollout_execution_id="e",
                                               physical_attempt_id="e#p1-aaaa"))

    only_backslash = "rm -rf /testbed && mkdir -p /testbed/src && printf 'bs\\n' > '/testbed/src/back\\slash.py'"
    assert dexec("/bin/bash", "-c", only_backslash).returncode == 0
    [entry] = export().entries
    assert entry.path == "src/back\\slash.py" and entry.content_digest == "sha256:" + hashlib.sha256(b"bs\n").hexdigest()
    with monkeypatch.context() as m:  # 反证：冻结的旧脚本 → 字段级 ValidationError（修复前的 run-fatal）
        m.setattr(patch_exporter, "build_census_script", _frozen_census_script)
        with pytest.raises(ValidationError):
            export()

    assert dexec("/bin/bash", "-c", "printf 'cr\\n' > \"$(printf '/testbed/src/c\\rr.py')\"").returncode == 0
    with pytest.raises(PatchExportError) as err:
        export()
    assert err.value.reason_code == "post_census_parse_failed"  # typed 单题失败，不是 run-fatal
    with monkeypatch.context() as m:
        m.setattr(patch_exporter, "build_census_script", _frozen_census_script)
        with pytest.raises(ValidationError):
            export()
