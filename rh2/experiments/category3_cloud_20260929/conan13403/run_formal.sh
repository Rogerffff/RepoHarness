#!/usr/bin/env bash
# 第3类 conan-13403 正式评分驱动（主审）。逐个候选串行执行；每次开始前等机器上容器少于 3 个。
# 用法：run_formal.sh original <候选...>    原材料正式评分
#       run_formal.sh revised_v2 <候选...>  修订版 v2 诊断评分（--materials）
# 候选：noop | gold | 其它名字对应本目录下 <名字>.patch
set -u
MODE=$1; shift
REPO=/home/user/RepoHarness
E=$REPO/rh2/experiments/category3_cloud_20260929/conan13403
W=$REPO/runs/category3_cloud_20260929/conan13403
IID=conan-io__conan-13403
cd $REPO/rh2
for C in "$@"; do
  case $C in
    noop) CAND=noop ;;
    gold) CAND=gold-dir:$W/gold ;;
    *) CAND=patch:$E/$C.patch ;;
  esac
  while [ "$(docker ps -q | wc -l)" -ge 3 ]; do sleep 20; done
  START=$(date +%s)
  if [ "$MODE" = original ]; then
    D=$W/formal
    mkdir -p $D
    MILES_RH2_RUN_ID=c3b2-conan13403-$C .venv/bin/python scripts/replay_grade.py run \
      --prepared-summary $W/prepared/replay_summary.json --task-ids $IID --candidate $CAND \
      --eval-log-dir $D/eval_logs --artifacts-dir $D/artifacts --ledger $D/ledger_$C.jsonl \
      > $D/run_$C.out 2>&1
    RC=$?
  else
    D=$W/formal_$MODE
    mkdir -p $D
    MILES_RH2_RUN_ID=c3b2-conan13403-$MODE-$C .venv/bin/python \
      experiments/env_recipe_repair_20260919/replay_with_install_recipe.py --code-root $(pwd) \
      --materials $E/materials_$MODE.json --audit-dir $D/audit_$C -- run \
      --prepared-summary $W/prepared/replay_summary.json --task-ids $IID --candidate $CAND \
      --eval-log-dir $D/eval_logs --artifacts-dir $D/artifacts --ledger $D/ledger_$C.jsonl \
      > $D/run_$C.out 2>&1
    RC=$?
  fi
  echo "rc=$RC" >> $D/run_$C.out
  END=$(date +%s)
  python3 - "$D/ledger_$C.jsonl" "$C" "$RC" "$((END-START))" <<'PY'
import json, sys
path, cand, rc, secs = sys.argv[1:]
try:
    row = json.loads(open(path).read().strip().splitlines()[-1])
    rep = row.get("report", {}); diag = row.get("verdict_diagnostics", {}); ins = row.get("install", {})
    print(json.dumps({"cand": cand, "rc": int(rc), "secs": int(secs), "reward": rep.get("reward"),
        "f2p": "{}/{}".format(rep.get("f2p_pass"), rep.get("f2p_total")),
        "p2p_fail": "{}/{}".format(rep.get("p2p_fail"), rep.get("p2p_total")),
        "missing": diag.get("reference_missing"), "apply_ok": diag.get("apply_ok"),
        "install_rc": ins.get("install_rc_last_command"), "test_rc": ins.get("test_rc"),
        "grader": rep.get("grader_version"), "cleanup": row.get("cleanup", {}).get("removed")}))
except Exception as e:
    print(json.dumps({"cand": cand, "rc": int(rc), "secs": int(secs), "error": repr(e)}))
PY
done
