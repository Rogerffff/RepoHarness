#!/usr/bin/env bash
# 复核者：v3 草案在评分 UID（54322，非 root）下与 root 下的结果是否一致（私有对照，不是正式评分）。
# 用法：bash uid_check.sh <输出文件>；候选：gold、ctx、parity（与 run_review.py 同一镜像、断网、一次性容器）。
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
EXP="$(dirname "$HERE")"
OUT="$1"
: > "$OUT"
GOLD_TMP="$(mktemp)"
python3 - "$GOLD_TMP" <<'PY'
import json, sys
for line in open("/home/user/RepoHarness/docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/validation_bundles_v0.jsonl"):
    d = json.loads(line)
    if d["instance_id"] == "getmoto__moto-6185":
        open(sys.argv[1], "w").write(d["golden_patch"])
PY
for v in gold ctx parity; do
  case $v in gold) P="$GOLD_TMP";; *) P="$EXP/$v.patch";; esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  C="rv6185-uid-$v-$RANDOM"
  docker run -d --rm --network none --name "$C" --entrypoint sleep c3keep/moto6185:src 1800 >/dev/null
  docker cp "$P" "$C:/tmp/cand.patch"
  docker cp "$HERE/revised_test_v3_draft.patch" "$C:/tmp/v3.patch"
  R=$(docker exec -w /testbed "$C" bash -c '
    export PATH=/opt/miniconda3/envs/testbed/bin:$PATH
    git apply /tmp/cand.patch && git apply /tmp/v3.patch || exit 9
    T=tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py::test_put_item__string_as_integer_value
    a=$(TEST_SERVER_MODE=false pytest -n0 -rA -p no:cacheprovider -q "$T" 2>&1 | tail -1)
    b=$(HOME=/tmp setpriv --reuid=54322 --regid=54322 --clear-groups env TEST_SERVER_MODE=false PATH=$PATH pytest -n0 -rA -p no:cacheprovider -q "$T" 2>&1 | tail -1)
    echo "root: $a | uid54322: $b"')
  echo "$v $R" | tee -a "$OUT"
  docker rm -f "$C" >/dev/null
done
rm -f "$GOLD_TMP"
