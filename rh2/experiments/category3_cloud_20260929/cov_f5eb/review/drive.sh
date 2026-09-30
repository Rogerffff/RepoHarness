#!/bin/bash
# 主机侧驱动：逐个候选开一次性断网容器（最多 1 个同时运行），日志写 logs/
# 用法：drive.sh <标签> <候选...> -- <测试版本...>
R=$(cd "$(dirname "$0")" && pwd)
AU=$(cd "$R/.." && pwd)   # 作者实验目录（cov_f5eb），只读挂载为 /au
tag=$1; shift
cands=(); while [ "$1" != "--" ]; do cands+=("$1"); shift; done; shift
tvs=("$@")
for c in "${cands[@]}"; do
  while [ $(docker ps -q | wc -l) -ge 3 ]; do sleep 20; done
  docker run --rm --network none -v $R:/rv:ro -v $AU:/au:ro c3keep/coveragepy_f5eb:src bash /rv/run_cand.sh "$c" "${tvs[@]}" > $R/logs/${tag}__${c}.log 2>&1
  echo "$c done rc=$?"
done
