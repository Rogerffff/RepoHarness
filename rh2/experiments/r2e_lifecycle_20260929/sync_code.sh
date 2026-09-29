#!/usr/bin/env bash
# 组一份确定的代码快照并同步到 R2E 机：HEAD 的 rh2 + 明列未跟踪目录 + 本线程（R2E）改过的工作树文件。
# 其它线程正在编辑的工作树改动不进快照。快照清单与 tar 存 runs/r2e_lifecycle_20260929/code_snapshots/。
# 用法：sync_code.sh <host> <port> [远端根，缺省 /work/code；09-29 修订单 v4 起另用 /work/code_v4，避免改动正在跑的复验]
set -euo pipefail
HOST=${1:?host}; PORT=${2:?port}; DEST=${3:-/work/code}
R=$(cd "$(dirname "$0")/../../.." && pwd)
KEY=$HOME/.ssh/vastai_ed25519
SSH=(ssh -p "$PORT" -o BatchMode=yes -o IdentitiesOnly=yes -i "$KEY" "root@$HOST")
RSYNC_E="ssh -p $PORT -o BatchMode=yes -o IdentitiesOnly=yes -i $KEY"
SNAPDIR=$R/runs/r2e_lifecycle_20260929/code_snapshots
EXTRA=(rh2/experiments/r2e_actor_20260925 rh2/experiments/task2_swegym_dev_20260925 rh2/experiments/base_probe_20260922
       rh2/experiments/base_probe_fixes_20260923 rh2/experiments/r2e_lifecycle_20260929 rh2/scripts/screening_facts.py)
OWNED=(rh2/src/repoharness2/envpack/ingest_r2e_subset.py rh2/tests/envpack/test_ingest_r2e_subset.py
       rh2/scripts/build_r2e_derived.py rh2/scripts/r2e_derive/sysconfig_v1.sh rh2/tests/envpack/test_build_r2e_derived_sysconfig.py
       rh2/scripts/build_r2e_ingest.py)
HEAD_SHA=$(git -C "$R" rev-parse HEAD)
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git -C "$R" archive HEAD rh2 | tar -x -C "$TMP"
for p in "${EXTRA[@]}" "${OWNED[@]}"; do mkdir -p "$TMP/$(dirname "$p")"; rsync -a --exclude '__pycache__' "$R/$p" "$TMP/$(dirname "$p")/"; done
MAN=$TMP/SNAPSHOT_MANIFEST.txt
{ echo "head=$HEAD_SHA"; echo "untracked_added:"; printf '  %s\n' "${EXTRA[@]}"; echo "r2e_owned_worktree_files:"; printf '  %s\n' "${OWNED[@]}"
  echo "file_sha256:"; (cd "$TMP" && find rh2 -type f ! -path '*/__pycache__/*' | LC_ALL=C sort | xargs sha256sum); } > "$MAN"
SNAP_ID=$(sha256sum "$MAN" | cut -c1-12)
tar -czf "$SNAPDIR/rh2_snapshot_$SNAP_ID.tgz" -C "$TMP" rh2 SNAPSHOT_MANIFEST.txt
cp "$MAN" "$SNAPDIR/SNAPSHOT_MANIFEST_$SNAP_ID.txt"
echo "$SNAP_ID" > "$TMP/rh2/SNAPSHOT_ID"; cp "$MAN" "$TMP/rh2/SNAPSHOT_MANIFEST.txt"
"${SSH[@]}" "mkdir -p $DEST/rh2"
rsync -azc --delete -e "$RSYNC_E" --exclude '.venv' "$TMP/rh2/" "root@$HOST:$DEST/rh2/"
"${SSH[@]}" "cat $DEST/rh2/SNAPSHOT_ID"
echo "snapshot_id=$SNAP_ID head=$HEAD_SHA"
