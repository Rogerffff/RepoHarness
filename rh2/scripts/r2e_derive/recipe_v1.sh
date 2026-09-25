#!/bin/bash
# rh2 R2E 派生镜像配方 r2e_derive_v1（R2E 接线 DR3=A，2026-09-23）。
# 在 `docker build` 的 RUN 里以 root 执行，网络关闭；arg1 = 来源修复提交（40 位）。只做三件事，其余一律不动：
#   1. 解释器搬迁：/root/.local/share/uv/python/<cpython-…> 复制到 /opt/py/<同名>，改写 .venv/pyvenv.cfg 的 home、
#      重指 .venv/bin/python* 符号链接、修 .venv/bin 里指向 /root 的 shebang。/root 保持 700（M3 §8 的布置 b）。
#   2. 隐藏测试：/r2e_tests 搬到 /rh2_private/r2e_tests（root:root，/rh2_private 700）；工作区里不得已有 r2e_tests。
#   3. git 清理：分离 HEAD、删全部 ref / remote、过期 reflog、删 packed-refs、gc --prune=now（M3 §pass5）。
#      工作树与索引不动：HEAD、`git status` 与 `git ls-files -s` 的摘要前后必须相同（初态脏树按原样保留）。
# 不做的事：不 chown /testbed（rollout / grader 两侧在运行期各自改属主）、不改 run_tests.sh、不装任何包。
# 任何一步失败 → 非零退出 → docker build 失败，不产出半成品镜像。`RH2_DERIVE_*` 行进 build.log，宿主侧复核用。
set -euo pipefail
FIX="${1:?fix commit required}"
UVROOT=/root/.local/share/uv/python
TB=/testbed
PRIVATE=/rh2_private
say() { echo "RH2_DERIVE_$1"; }
die() { say "ERROR=$1"; exit 3; }

# ---- 0. 前置事实（与 M3 事实表一致才继续）
[ -d "$TB" ] || die "no_testbed"
[ -d /r2e_tests ] && [ ! -L /r2e_tests ] || die "no_hidden_tests_source"
[ ! -e "$TB/r2e_tests" ] || die "workdir_r2e_tests_present"
[ -f "$TB/run_tests.sh" ] || die "no_run_tests_sh"
[ ! -e "$PRIVATE" ] || die "private_dir_already_present"
[ ! -e /opt/py ] || die "opt_py_already_present"
PYREAL=$(readlink -f "$TB/.venv/bin/python")
case "$PYREAL" in "$UVROOT"/*) ;; *) die "interpreter_not_under_uv_root:$PYREAL" ;; esac
PYDIR=$(basename "$(dirname "$(dirname "$PYREAL")")")
say "INTERP_BEFORE=$PYREAL"
cd "$TB"
git cat-file -e "$FIX^{commit}" 2>/dev/null || die "fix_commit_not_present_before_scrub:$FIX"
HEAD_BEFORE=$(git rev-parse HEAD)
STATUS_BEFORE=$(git status --porcelain=v1 -uall | sha256sum | cut -d' ' -f1)
INDEX_BEFORE=$(git ls-files -s | sha256sum | cut -d' ' -f1)
say "HEAD_BEFORE=$HEAD_BEFORE"
say "STATUS_LINES_BEFORE=$(git status --porcelain=v1 -uall | wc -l | tr -d ' ')"
say "RUN_TESTS_SH_SHA256_BEFORE=$(sha256sum "$TB/run_tests.sh" | cut -d' ' -f1)"

# ---- 1. 解释器搬迁
mkdir -p /opt/py
cp -a "$UVROOT/$PYDIR" "/opt/py/$PYDIR"
chmod -R a+rX /opt/py
sed -i "s#$UVROOT/$PYDIR#/opt/py/$PYDIR#g" "$TB/.venv/pyvenv.cfg"
grep -q "^home = /opt/py/$PYDIR" "$TB/.venv/pyvenv.cfg" || die "pyvenv_cfg_not_rewritten"
RELINKED=0
for l in "$TB"/.venv/bin/python "$TB"/.venv/bin/python3 "$TB"/.venv/bin/python3.*; do
  [ -L "$l" ] || continue
  TGT=$(readlink -f "$l")
  case "$TGT" in
    "$UVROOT"/*) ln -sfn "/opt/py/$PYDIR/bin/$(basename "$TGT")" "$l"; RELINKED=$((RELINKED + 1)) ;;
  esac
done
say "RELINKED=$RELINKED"
# grep 无命中返回 1，set -e + pipefail 下要显式放行（coveragepy 这类镜像的 .venv/bin 脚本 shebang 本就指向 .venv）
SHEBANGS=$( { grep -rlI "^#!$UVROOT" "$TB/.venv/bin" 2>/dev/null || true; } | wc -l | tr -d ' ')
{ grep -rlI "^#!$UVROOT" "$TB/.venv/bin" 2>/dev/null || true; } | xargs -r sed -i "s#^\#!$UVROOT#\#!/opt/py#"
say "SHEBANGS_FIXED=$SHEBANGS"
INTERP_AFTER=$(readlink -f "$TB/.venv/bin/python")
case "$INTERP_AFTER" in /opt/py/*) ;; *) die "interpreter_not_relocated:$INTERP_AFTER" ;; esac
say "INTERP_AFTER=$INTERP_AFTER"
# 两种启动方式下 sys.path 都不再指向 /root（run_tests.sh 用普通模式；观测 / 复证用 -I -S）
"$TB/.venv/bin/python" -I -S -c 'import sys; bad=[p for p in sys.path if p.startswith("/root")]; sys.exit(1 if bad else 0)' \
  || die "sys_path_under_root_isolated_mode"
"$TB/.venv/bin/python" -c 'import sys; bad=[p for p in sys.path if p.startswith("/root")]; sys.exit(1 if bad else 0)' \
  || die "sys_path_under_root_normal_mode"
say "SYS_PATH_ROOT_ENTRIES=0"

# ---- 2. 隐藏测试搬到 root 私有位置
mkdir -p "$PRIVATE"
mv /r2e_tests "$PRIVATE/r2e_tests"
chown -R root:root "$PRIVATE"
chmod 700 "$PRIVATE"
find "$PRIVATE/r2e_tests" -type d -name __pycache__ -prune -exec rm -rf {} +
[ ! -e /r2e_tests ] || die "hidden_tests_source_still_present"
say "HIDDEN_TESTS_TREE=$(cd "$PRIVATE/r2e_tests" && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"

# ---- 3. git 清理（工作树 / 索引不动）
cd "$TB"
git update-ref --no-deref HEAD "$HEAD_BEFORE"
git symbolic-ref -d refs/remotes/origin/HEAD 2>/dev/null || true
n=0
for r in $(git for-each-ref --format='%(refname)'); do git update-ref -d "$r" && n=$((n + 1)); done
say "REFS_DELETED=$n"
for m in $(git remote); do git remote remove "$m"; done
git reflog expire --expire=now --all
rm -f .git/packed-refs
git gc --prune=now -q
[ "$(git rev-parse HEAD)" = "$HEAD_BEFORE" ] || die "head_changed_by_scrub"
[ "$(git status --porcelain=v1 -uall | sha256sum | cut -d' ' -f1)" = "$STATUS_BEFORE" ] || die "worktree_status_changed_by_scrub"
[ "$(git ls-files -s | sha256sum | cut -d' ' -f1)" = "$INDEX_BEFORE" ] || die "index_changed_by_scrub"
if git cat-file -e "$FIX^{commit}" 2>/dev/null; then die "fix_commit_still_present_after_scrub"; fi
[ "$(git rev-list --children --all | grep "^$HEAD_BEFORE" | wc -w | tr -d ' ')" = "1" ] || die "head_still_has_children"
say "REFS_AFTER=$(git for-each-ref | wc -l | tr -d ' ')"
say "REMOTES_AFTER=$(git remote | wc -l | tr -d ' ')"
say "REFLOG_AFTER=$( { git reflog 2>/dev/null || true; } | wc -l | tr -d ' ')"
say "GIT_DIR_KB_AFTER=$(du -sk .git | cut -f1)"
# 沙箱身份在改属主之前也能读 git（宿主侧复核用；运行期 rollout / grader 脚本各自再加 --global）
git config --system --add safe.directory '*'
say "RUN_TESTS_SH_SHA256_AFTER=$(sha256sum "$TB/run_tests.sh" | cut -d' ' -f1)"
say "OK=1"
