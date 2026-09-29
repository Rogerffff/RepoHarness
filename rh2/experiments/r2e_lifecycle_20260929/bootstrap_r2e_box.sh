#!/usr/bin/env bash
# R2E 单题闭环试行（2026-09-29）CPU 机一键准备，在本机执行。改自任务二的 bootstrap_box.sh：
# 端口可配；代码用"git archive HEAD 的 rh2 + 明列的未跟踪实验目录"组成确定快照（不带其它线程正在编辑的工作树改动），
# 快照清单与 tar 存本地 runs/r2e_lifecycle_20260929/code_snapshots/；凭据只从 git 忽略的 tmp/API.md 读取，不回显。
# 用法：bootstrap_r2e_box.sh <host> <port> [docker_hub_user]
set -euo pipefail
HOST=${1:?host}; PORT=${2:?port}; DHUB_USER=${3:-fangjianju666}
R=$(cd "$(dirname "$0")/../../.." && pwd)
D=$R/docs/agentic_RL/repo_harness_rh2_workstreams
KEY=$HOME/.ssh/vastai_ed25519
SSH=(ssh -p "$PORT" -o BatchMode=yes -o IdentitiesOnly=yes -o ServerAliveInterval=30 -i "$KEY" "root@$HOST")
RSYNC_E="ssh -p $PORT -o BatchMode=yes -o IdentitiesOnly=yes -i $KEY"
SNAPDIR=$R/runs/r2e_lifecycle_20260929/code_snapshots
DTOKEN=$(python3 -c "import re,sys;m=re.search(r'(dckr_pat_[A-Za-z0-9_\-]+)',open(sys.argv[1]).read());print(m.group(1) if m else '')" "$D/project1_execution/tmp/API.md")
[ -n "$DTOKEN" ] || { echo "API.md 缺 docker token"; exit 1; }

echo "== 1. 工具与目录"
"${SSH[@]}" 'set -e; export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null; apt-get install -y -qq tmux jq git rsync xz-utils python3-venv >/dev/null
mkdir -p /work/code /work/secrets /work/r2e/{cc,logs,runs,prepared,derived,grader,devcheck} && chmod 700 /work/secrets
docker --version; docker info 2>/dev/null | grep -E "Storage Driver|Cgroup Version|Docker Root"'
printf '%s' "$DTOKEN" | "${SSH[@]}" "docker login -u $DHUB_USER --password-stdin >/dev/null && echo docker_login_ok"

echo "== 2. 代码快照（HEAD 的 rh2 + 明列未跟踪目录）"
HEAD_SHA=$(git -C "$R" rev-parse HEAD)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git -C "$R" archive HEAD rh2 | tar -x -C "$TMP"
EXTRA=(rh2/experiments/r2e_actor_20260925 rh2/experiments/task2_swegym_dev_20260925 rh2/experiments/base_probe_20260922
       rh2/experiments/base_probe_fixes_20260923 rh2/experiments/r2e_lifecycle_20260929 rh2/scripts/screening_facts.py)
for p in "${EXTRA[@]}"; do mkdir -p "$TMP/$(dirname "$p")"; rsync -a --exclude '__pycache__' "$R/$p" "$TMP/$(dirname "$p")/"; done
MAN=$TMP/SNAPSHOT_MANIFEST.txt
{ echo "head=$HEAD_SHA"; echo "untracked_added:"; for p in "${EXTRA[@]}"; do echo "  $p"; done
  echo "file_sha256:"; (cd "$TMP" && find rh2 -type f ! -path '*/__pycache__/*' | LC_ALL=C sort | xargs sha256sum); } > "$MAN"
SNAP_ID=$(sha256sum "$MAN" | cut -c1-12)
tar -czf "$SNAPDIR/rh2_snapshot_$SNAP_ID.tgz" -C "$TMP" rh2 SNAPSHOT_MANIFEST.txt
cp "$MAN" "$SNAPDIR/SNAPSHOT_MANIFEST_$SNAP_ID.txt"
echo "snapshot_id=$SNAP_ID head=$HEAD_SHA"
rsync -az --delete -e "$RSYNC_E" --exclude '.venv' "$TMP/rh2/" "root@$HOST:/work/code/rh2/"
printf '%s\n' "$SNAP_ID" | "${SSH[@]}" "cat > /work/code/rh2/SNAPSHOT_ID && cp /dev/stdin /dev/null"
rsync -az -e "$RSYNC_E" "$MAN" "root@$HOST:/work/code/rh2/SNAPSHOT_MANIFEST.txt"

echo "== 3. 文档与材料"
"${SSH[@]}" "mkdir -p /work/code/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924"
for sub in s2 data_freeze s2_r2e; do rsync -az --delete -e "$RSYNC_E" "$D/$sub/" "root@$HOST:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/$sub/"; done
rsync -az -e "$RSYNC_E" "$D/project1_execution/r2e_env_repair_20260924/recipes" "root@$HOST:/work/code/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/"

echo "== 4. rh2 运行环境（锁文件）"
"${SSH[@]}" 'command -v uv >/dev/null || [ -x $HOME/.local/bin/uv ] || (curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1); export PATH=$HOME/.local/bin:$PATH; cd /work/code/rh2 && uv sync --locked --group swe --group dev >/work/r2e/logs/uv_sync.log 2>&1; tail -2 /work/r2e/logs/uv_sync.log; .venv/bin/python -c "import importlib.metadata as m, aiohttp; print(\"swebench\", m.version(\"swebench\"), \"aiohttp\", aiohttp.__version__)"'

echo "== 5. CC 2.1.205 平台包（npm 直取 + integrity）"
"${SSH[@]}" 'set -e; cd /work/r2e/cc; f=claude-code-linux-x64-2.1.205.tgz; [ -s $f ] || curl -fsSL -o $f https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/-/$f; want=$(curl -fsSL https://registry.npmjs.org/@anthropic-ai/claude-code-linux-x64/2.1.205 | python3 -c "import sys,json; print(json.load(sys.stdin)[\"dist\"][\"integrity\"])"); got="sha512-$(openssl dgst -sha512 -binary $f | base64 -w0)"; [ "$want" = "$got" ] && echo "cc_tarball_integrity_ok $(stat -c %s $f)" || { echo "cc integrity mismatch"; exit 1; }'

echo "== 6. relay 镜像"
"${SSH[@]}" 'docker pull -q python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea; ip -4 addr show docker0 | grep -o "inet [0-9.]*"; df -h / | tail -1'
echo "== done"
