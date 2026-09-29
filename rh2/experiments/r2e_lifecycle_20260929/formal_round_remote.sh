#!/bin/bash
# 一轮正式修订落地后的远端验收（2026-09-29，R2E 单题闭环试行）。在 systemd 单元里跑：
#   构建本轮题的派生镜像 → 以上一轮合并覆盖表为底、换入本轮题 → 准备本轮任务面 → 导出 gold → 建候选槽位
#   → 等上一轮评分单元全部结束（避免并发 IO 拖垮控制面保护的 300 s 时限）→ 按 lanes 起评分单元。
# 用法：formal_round_remote.sh <轮次 vN> <上一轮合并覆盖表目录> <上一轮评分单元前缀> <lanes，如 "noop+s7 gold+s6 s1+s5 s2 s3 s4"> [放宽预算的题前缀，逗号分隔]
# 第 5 个参数里的题（如 datalad__）在本机并发评分时，控制面保护基本都会超过缺省 300 s（与宿主存储和并发有关；09-25 另一台机器上只要 35–54 s），改用 replay_grade_budget.py 把 env_reset_timeout 放宽到 1200 s；
# 只放宽时限、评分语义不变，账本单独成文件（ledger_<槽位>_budget1200.jsonl），不与缺省预算的结果混记。
set -euo pipefail
ROUND=$1; PREV_ALL=$2; PREV_UNITS=$3; LANES=$4; WRAP=${5:-}
CODE=/work/code_$ROUND/rh2; PY=$CODE/.venv/bin/python
F=/work/r2e/formal_$ROUND; NEW=/work/r2e/derived/$ROUND; ALL=/work/r2e/derived/all_$ROUND
PREP=/work/r2e/prepared_$ROUND; PRIV=/work/r2e/private_$ROUND; GOLD=/work/r2e/gold_$ROUND
ENV_PINS=/work/code_$ROUND/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924/recipes/env_pins_v2.json
cd $CODE
IDS=$(python3 -c "import json;print(','.join(sorted({r['instance_id'] for r in json.load(open('$F/plan.json'))['rows']})))")
echo "[$(date -u +%T)] build $IDS"
for p in $NEW $ALL $PREP $PRIV $GOLD $F/slots; do [ -e $p ] && { echo "exists: $p"; exit 1; }; done
mkdir -p $NEW $ALL
$PY scripts/build_r2e_derived.py --repo-root .. --out-dir $NEW --sysconfig-fix --env-pins $ENV_PINS --task-ids $IDS > $F/build.log 2> $F/build.err
python3 - "$NEW" "$PREV_ALL" "$ALL" "$IDS" <<'PY'
import json, shutil, sys
from pathlib import Path
new, prev, out, ids = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4].split(",")
for iid in ids:
    f = json.load(open(new / iid / "facts.json"))
    if not f.get("ok"):
        raise SystemExit(f"build failed: {iid} {f.get('failures')}")
n = 0
for d in sorted(prev.iterdir()):
    if (d / "facts.json").is_file():
        (out / d.name).mkdir()
        shutil.copy2((new if d.name in ids else prev) / d.name / "facts.json", out / d.name / "facts.json"); n += 1
print(json.dumps({"merged": n, "replaced": len(ids)}))
PY
$PY scripts/build_r2e_derived.py --repo-root .. --out-dir $ALL --regenerate-overlays > $F/regenerate_overlays.json
echo "[$(date -u +%T)] overlays_rows=$(wc -l < $ALL/overlays.jsonl)"
$PY scripts/replay_grade.py prepare --repo-root .. --out-dir $PREP --private-dir $PRIV --sources r2e_gym_subset > $F/prepare.json 2> $F/prepare.err
$PY scripts/replay_grade.py export-gold --ingest-dir ../docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest --instance-ids "$IDS" --out-dir $GOLD > $F/export_gold.json 2>&1
for i in ${IDS//,/ }; do cmp -s $GOLD/$i.gold.patch /work/r2e/gold/$i.gold.patch && echo "gold_same $i" || echo "gold_DIFF $i"; done
python3 - "$F" <<'PY'
import json, hashlib, shutil, sys
from pathlib import Path
F = Path(sys.argv[1]); plan = json.load(open(F / "plan.json")); man = []
for r in plan["rows"]:
    if r["spec"] != "patch-dir":
        continue
    src = Path(r["remote_patch"]); sha = hashlib.sha256(src.read_bytes()).hexdigest()
    if r.get("expect_remote_sha256") and r["expect_remote_sha256"] != sha:
        raise SystemExit(f"{r['instance_id']} {r['candidate']}: 远端试跑补丁摘要与记录不符")
    if r["local_sha256"] and r["local_sha256"] != sha:
        raise SystemExit(f"{r['instance_id']} {r['candidate']}: 远端试跑补丁与本地来源摘要不同")
    dst = F / "slots" / r["slot"] / f"{r['instance_id']}.diff"; dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    man.append({**{k: r[k] for k in ("instance_id", "candidate", "slot", "expected_score")}, "sha256": sha, "from": str(src)})
(F / "slots_manifest.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n")
print(json.dumps({"slot_patches": len(man)}))
PY
echo "[$(date -u +%T)] waiting for ${PREV_UNITS}*"
while systemctl list-units --no-legend --state=active "${PREV_UNITS}*" | grep -q .; do sleep 30; done
echo "[$(date -u +%T)] launching lanes: $LANES"
k=0
for lane in $LANES; do
  k=$((k + 1)); cmds=""
  for s in ${lane//+/ }; do
    case $s in noop) cand=noop;; gold) cand=gold-dir:$GOLD;; *) cand=patch-dir:$F/slots/$s;; esac
    for part in plain wrap; do
      ids=$(python3 -c "
import json
p = json.load(open('$F/plan.json')); wrap = [x for x in '$WRAP'.split(',') if x]
ids = [r['instance_id'] for r in p['rows'] if r['slot'] == '$s']
sel = [i for i in ids if any(i.startswith(w) for w in wrap)]
print(','.join(sel if '$part' == 'wrap' else [i for i in ids if i not in sel]))")
      [ -z "$ids" ] && continue
      if [ $part = wrap ]; then
        cmds+="MILES_RH2_RUN_ID=r2e-$ROUND-$s-b-$(date +%m%d%H%M) $PY experiments/r2e_lifecycle_20260929/replay_grade_budget.py --env-reset-timeout 1200 -- run --prepared-summary $PREP/replay_summary.json --task-ids $ids --candidate $cand --image-overlays $ALL/overlays.jsonl --eval-log-dir $F/${s}_logs --artifacts-dir $F/${s}_art --ledger $F/ledger_${s}_budget1200.jsonl; echo \"slot $s budget rc=\$?\"; "
      else
        cmds+="MILES_RH2_RUN_ID=r2e-$ROUND-$s-$(date +%m%d%H%M) $PY scripts/replay_grade.py run --prepared-summary $PREP/replay_summary.json --task-ids $ids --candidate $cand --image-overlays $ALL/overlays.jsonl --eval-log-dir $F/${s}_logs --artifacts-dir $F/${s}_art --ledger $F/ledger_$s.jsonl; echo \"slot $s rc=\$?\"; "
      fi
    done
  done
  systemd-run --unit=r2e-$ROUND-u$k --collect --working-directory=$CODE -p LimitNOFILE=65536 \
    -p StandardOutput=append:$F/r2e-$ROUND-u$k.log -p StandardError=append:$F/r2e-$ROUND-u$k.log /bin/bash -c "$cmds"
done
echo "[$(date -u +%T)] launched $k lanes"
