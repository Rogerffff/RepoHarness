#!/usr/bin/env bash
# 复核者：对若干版本跑 probe_extra.py（私有对照）。用法：bash run_extra.sh <输出文件> 变体...
# 变体：base、gold、作者候选名（../<名>.patch）、复核者候选名（candidates/<名>.patch）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP="$(dirname "$HERE")"
OUT="$1"; shift
: > "$OUT"
GOLD_TMP="$(mktemp)"
python3 - "$GOLD_TMP" <<'PY'
import json, sys
for line in open("/home/user/RepoHarness/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/validation_bundles_v0.jsonl"):
    d = json.loads(line)
    if d["instance_id"] == "getmoto__moto-6185":
        open(sys.argv[1], "w").write(d["golden_patch"])
PY
for v in "$@"; do
  case $v in
    base) P="";;
    gold) P="$GOLD_TMP";;
    *) if [ -f "$HERE/candidates/$v.patch" ]; then P="$HERE/candidates/$v.patch"; else P="$EXP/$v.patch"; fi;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  C="rv6185-x-$v-$RANDOM"
  docker run -d --rm --network none --name "$C" --entrypoint sleep c3keep/moto6185:src 1800 >/dev/null
  docker cp "$HERE/probe_extra.py" "$C:/tmp/probe_extra.py"
  if [ -n "$P" ]; then docker cp "$P" "$C:/tmp/cand.patch"; docker exec -w /testbed "$C" git apply /tmp/cand.patch; fi
  docker exec -w /testbed "$C" /opt/miniconda3/envs/testbed/bin/python /tmp/probe_extra.py 2>/dev/null | sed "s/^/$v\t/" | tee -a "$OUT"
  docker rm -f "$C" >/dev/null
done
rm -f "$GOLD_TMP"
