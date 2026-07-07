#!/usr/bin/env bash
# rh2 S0-7：顺序驱动冻结题单 8 题 SWE smoke（每题单进程，见 s0_swe_smoke.py docstring）。
# 用法（远程机，rh2/ 为工作根）：
#   read -r DEEPSEEK_API_KEY; export DEEPSEEK_API_KEY   # key 经 ssh stdin 注入，不落盘
#   nohup bash experiments/s0_swe_smoke_run_all.sh > swe_smoke_out/run_all.log 2>&1 &
# 特性：已有 <instance>.json dump 的题自动跳过，中断后可安全重跑续传；
#       本脚本不含任何凭据；单题硬超时 5400s（rollout/评分内部超时之和 + 余量）。
set -u
cd "$(dirname "$0")/.."

OUT="${OUT_DIR:-swe_smoke_out}"
mkdir -p "$OUT"

INSTANCES=(
  django__django-11099
  django__django-11133
  django__django-16139
  sympy__sympy-14711
  sympy__sympy-15349
  psf__requests-1142
  psf__requests-2931
  astropy__astropy-14995
)

for iid in "${INSTANCES[@]}"; do
  if [ -s "$OUT/$iid.json" ]; then
    echo "[skip] $iid 已有 dump，跳过"
    continue
  fi
  echo "=== [$(date -u '+%F %T')] start $iid ==="
  timeout -k 60 5400 .venv/bin/python experiments/s0_swe_smoke.py \
    --instance "$iid" --out-dir "$OUT" > "$OUT/$iid.run.log" 2>&1
  rc=$?
  echo "=== [$(date -u '+%F %T')] end $iid exit=$rc ==="
  tail -n 4 "$OUT/$iid.run.log" | sed 's/^/    | /'
done

echo "ALL_DONE $(date -u '+%F %T')"
