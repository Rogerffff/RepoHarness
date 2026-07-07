#!/usr/bin/env bash
# DF-1: 从 HF datasets-server 拉取四个数据集的行级元数据（只保留需要的字段）。
# 产物: meta/<name>.jsonl + meta/<name>.revision
set -euo pipefail
cd "$(dirname "$0")"
API="https://datasets-server.huggingface.co"

fetch() { # $1=dataset $2=config $3=split $4=total $5=outname $6=jq_filter
  local ds="$1" cfg="$2" split="$3" total="$4" out="$5" filt="$6"
  : > "$out.jsonl"
  local off=0
  while [ "$off" -lt "$total" ]; do
    for attempt in 1 2 3; do
      if curl -sf --max-time 60 "$API/rows?dataset=$ds&config=$cfg&split=$split&offset=$off&length=100" \
        | jq -c ".rows[].row | $filt" >> "$out.jsonl"; then
        break
      fi
      echo "retry $ds off=$off attempt=$attempt" >&2; sleep $((attempt*5))
      [ "$attempt" = 3 ] && exit 1
    done
    off=$((off+100)); sleep 1
  done
  curl -sf "https://huggingface.co/api/datasets/$ds" | jq -r ".sha" > "$out.revision" || true  # 真实 HF revision（修复：原表达式抓到的是配置键）
  echo "$out: $(wc -l < "$out.jsonl") rows"
}

# SWE-bench Verified（500）：评测面，元数据即可
fetch "SWE-bench/SWE-bench_Verified" default test 500 verified \
  '{instance_id, repo, base_commit, version}'

# SWE-Gym Lite（230）：bring-up 候选，打标需要题面全文
fetch "SWE-Gym/SWE-Gym-Lite" default train 230 swe_gym_lite \
  '{instance_id, repo, base_commit, version, problem_statement, hints_text, FAIL_TO_PASS, PASS_TO_PASS}'

# SWE-Gym 全量（2438）：扩容候选，轻元数据
fetch "SWE-Gym/SWE-Gym" default train 2438 swe_gym_full \
  '{instance_id, repo, base_commit, version}'

# R2E-Gym-Subset（4578）：success run 主力 + held-out 候选，轻元数据 + 题面（不拉答案字段）
fetch "R2E-Gym/R2E-Gym-Subset" default train 4578 r2e_subset \
  '{repo_name, docker_image, commit_hash, problem_statement: (.problem_statement // .prompt // "" | .[0:20000])}'

echo "ALL DONE"
