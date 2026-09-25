#!/bin/bash
# rh2 r2e_env 开发条件探针（agent 阶段，v1）。以 agent/54321 身份、cwd=/testbed、HOME=/home/agent 运行；
# 环境变量由宿主 runner 传入：MODULE（包导入名）、MODULE_DIR（包目录，可空）、PREFIX（入口脚本里解释器之前的
# 环境前缀，如 `QT_QPA_PLATFORM=minimal xvfb-run -a`，可空）、REPRO（公开复现脚本路径，可空）。
# 输出 KEY=VALUE 行与 `@@BEGIN name` … `@@END name` 多行块；宿主解析成 JSON。只观测，不改题目材料；
# 会产生 __pycache__（与真实 rollout 相同）；pytest 缓存目录指到 /tmp（cache_dir），不在工作区留 .pytest_cache。
set -u
say() { printf '%s=%s\n' "$1" "$2"; }
blk() { printf '@@BEGIN %s\n' "$1"; cat; printf '\n@@END %s\n' "$1"; }
T=""; command -v timeout >/dev/null 2>&1 && T="timeout"
tmo() { local s="$1"; shift; if [ -n "$T" ]; then "$T" "$s" "$@"; else "$@"; fi; }
MODULE="${MODULE:-}"; MODULE_DIR="${MODULE_DIR:-}"; PREFIX="${PREFIX:-}"; REPRO="${REPRO:-}"

say PROBE_VERSION 1
say ID "$(id 2>&1)"
say PWD "$(pwd)"
say HOME_VAR "${HOME-}"
say PATH_VAR "$PATH"
say VIRTUAL_ENV_VAR "${VIRTUAL_ENV-}"
say BASH_ENV_VAR "${BASH_ENV-}"
say CONDA_DEFAULT_ENV_VAR "${CONDA_DEFAULT_ENV-}"
for c in python python3 pip pip3 uv pytest git gcc make xvfb-run; do
  say "WHICH_$c" "$(command -v "$c" 2>/dev/null || echo MISSING)"
done
say PY_INFO "$(python -c 'import sys; print(sys.executable, sys.version.split()[0], sys.prefix, sys.base_prefix)' 2>&1 | tail -1)"
say PY_INFO_RC "$(python -c 'import sys' >/dev/null 2>&1; echo $?)"
say PY_ISOLATED_RC "$(/testbed/.venv/bin/python -B -I -S -c pass >/dev/null 2>&1; echo $?)"
say PYTEST_VERSION "$(tmo 60 python -m pytest --version 2>&1 | grep -m1 -E '^pytest [0-9]' || tmo 60 python -m pytest --version 2>&1 | head -1)"
say PYTEST_RC "$(tmo 60 python -m pytest --version >/dev/null 2>&1; echo $?)"
if [ -n "$MODULE" ]; then
  say IMPORT_FROM_TESTBED "$(cd /testbed && tmo 120 python -c "import $MODULE as m; print(m.__file__, getattr(m,'__version__','?'))" 2>&1 | tail -1)"
  say IMPORT_FROM_TESTBED_RC "$(cd /testbed && tmo 120 python -c "import $MODULE" >/dev/null 2>&1; echo $?)"
  say IMPORT_FROM_TMP "$(cd /tmp && tmo 120 python -c "import $MODULE as m; print(m.__file__, getattr(m,'__version__','?'))" 2>&1 | tail -1)"
  say IMPORT_FROM_TMP_RC "$(cd /tmp && tmo 120 python -c "import $MODULE" >/dev/null 2>&1; echo $?)"
fi
say PIP_VERSION "$(tmo 60 python -m pip --version 2>&1 | tail -1)"
say PIP_CHECK "$(tmo 180 python -m pip check 2>&1 | tail -6 | tr '\n' '|')"
say PIP_CHECK_RC "$(tmo 180 python -m pip check >/dev/null 2>&1; echo $?)"
say PIP_LIST_COUNT "$(tmo 180 python -m pip list --format=freeze 2>/dev/null | wc -l | tr -d ' ')"
SITE="$(python -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null || echo "")"
say SITE_PACKAGES "$SITE"
wtest() { local p="$1"; if ( : > "$p/.rh2_wtest" ) 2>/dev/null; then rm -f "$p/.rh2_wtest"; echo ok; else echo denied; fi; }
say WRITE_TESTBED "$(wtest /testbed)"
say WRITE_SITE "$( [ -n "$SITE" ] && [ -d "$SITE" ] && wtest "$SITE" || echo n/a)"
say WRITE_VENV_BIN "$(wtest /testbed/.venv/bin)"
say WRITE_HOME "$(wtest "${HOME:-/home/agent}")"
say WRITE_TMP "$(wtest /tmp)"
say WRITE_ROOT_FS "$(wtest /usr/local)"
say DF_TMP_KB "$(df -k /tmp 2>/dev/null | tail -1 | awk '{print $2" "$4}')"
say DF_TESTBED_KB "$(df -k /testbed 2>/dev/null | tail -1 | awk '{print $2" "$4}')"
say CG_MEM_MAX "$(cat /sys/fs/cgroup/memory.max 2>/dev/null || echo unknown)"
say CG_CPU_MAX "$(cat /sys/fs/cgroup/cpu.max 2>/dev/null || echo unknown)"
say CG_PIDS_MAX "$(cat /sys/fs/cgroup/pids.max 2>/dev/null || echo unknown)"
say NPROC "$(nproc 2>/dev/null || echo unknown)"
say GIT_HEAD "$(git rev-parse HEAD 2>&1 | tail -1)"
say GIT_STATUS_COUNT "$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
git status --short 2>&1 | head -60 | blk GIT_STATUS
HEADC="$(git rev-parse HEAD 2>/dev/null || echo none)"
say GIT_HEAD_CHILDREN_WORDS "$(git rev-list --children --all 2>/dev/null | grep "^$HEADC" | wc -w | tr -d ' ')"
say GIT_REFS_COUNT "$(git for-each-ref 2>/dev/null | wc -l | tr -d ' ')"
say GIT_REFLOG_COUNT "$(git reflog 2>/dev/null | wc -l | tr -d ' ')"
say GIT_STASH_COUNT "$(git stash list 2>/dev/null | wc -l | tr -d ' ')"
say GIT_REMOTES "$(git remote 2>/dev/null | tr '\n' ',')"
say GIT_PACKED_REFS "$( [ -e /testbed/.git/packed-refs ] && echo present || echo absent)"
git log --oneline -3 2>&1 | blk GIT_LOG
say PRIVATE_LS "$(ls /rh2_private 2>&1 | head -1)"
say PRIVATE_TESTS_LS "$(ls /rh2_private/r2e_tests 2>&1 | head -1)"
say R2E_TESTS_ROOT "$( [ -e /r2e_tests ] && echo present || echo absent)"
say R2E_TESTS_WORKDIR "$( [ -e /testbed/r2e_tests ] && echo present || echo absent)"
say RUN_TESTS_SH_READABLE "$( [ -r /testbed/run_tests.sh ] && echo yes || echo no)"
head -c 400 /testbed/run_tests.sh 2>&1 | blk RUN_TESTS_SH_HEAD
find /testbed \( -path /testbed/.venv -o -path /testbed/.git \) -prune -o \( -name '*.orig' -o -name '*.rej' -o -name '*.patch' -o -name '*.diff' \) -print 2>/dev/null | head -20 | blk STRAY_PATCH_FILES
ls -la /testbed 2>&1 | head -60 | blk TESTBED_LS
# 公开测试（仓库自带的测试目录，不是隐藏的 r2e_tests）：找第一个 test_*.py，收集 + 限量运行
TESTFILE=""
for d in tests test Tests testing "$MODULE_DIR/tests" "src/$MODULE/tests" "$MODULE/tests" "Tests/PIL" "$MODULE/tests/unit"; do
  [ -n "$d" ] && [ -d "/testbed/$d" ] || continue
  f="$(find "/testbed/$d" -maxdepth 1 -name 'test_*.py' 2>/dev/null | LC_ALL=C sort | head -1)"
  [ -n "$f" ] || f="$(find "/testbed/$d" -maxdepth 2 -name 'test_*.py' -not -path '*/r2e_tests/*' 2>/dev/null | LC_ALL=C sort | head -1)"
  if [ -n "$f" ]; then TESTFILE="${f#/testbed/}"; break; fi
done
say PUBLIC_TEST_FILE "$TESTFILE"
if [ -n "$TESTFILE" ]; then
  out="$(cd /testbed && eval "tmo 300 env $PREFIX python -m pytest --collect-only -q -o cache_dir=/tmp/rh2_pytest_cache '$TESTFILE'" 2>&1)"; rc=$?
  say PUBLIC_COLLECT_RC "$rc"; say PUBLIC_COLLECT_TAIL "$(printf '%s\n' "$out" | tail -3 | tr '\n' '|')"
  out="$(cd /testbed && eval "tmo 600 env $PREFIX python -m pytest -q -o cache_dir=/tmp/rh2_pytest_cache --maxfail=5 -x '$TESTFILE'" 2>&1)"; rc=$?
  say PUBLIC_RUN_RC "$rc"; say PUBLIC_RUN_TAIL "$(printf '%s\n' "$out" | tail -3 | tr '\n' '|')"
fi
if [ -n "$REPRO" ] && [ -r "$REPRO" ]; then
  out="$(cd /testbed && eval "tmo 300 env $PREFIX python '$REPRO'" 2>&1)"; rc=$?
  say REPRO_RC "$rc"; printf '%s\n' "$out" | tail -40 | blk REPRO_OUTPUT
else
  say REPRO_RC n/a
fi
say NET_CONNECT_RC "$(tmo 8 python -c "import socket; socket.create_connection(('1.1.1.1',443),timeout=3)" >/dev/null 2>&1; echo $?)"
say NET_DNS_RC "$(tmo 8 getent hosts pypi.org >/dev/null 2>&1; echo $?)"
say GIT_STATUS_COUNT_AFTER "$(git status --short 2>/dev/null | wc -l | tr -d ' ')"
say PROBE_DONE 1
