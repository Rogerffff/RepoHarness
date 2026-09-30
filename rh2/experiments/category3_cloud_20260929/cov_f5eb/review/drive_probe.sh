#!/bin/bash
# 行为探针驱动：逐个候选开一次性断网容器，输出 logs/probe__<候选>.log
R=$(cd "$(dirname "$0")" && pwd)
AU=$(cd "$R/.." && pwd)   # 作者实验目录（cov_f5eb），只读挂载为 /au
for c in "$@"; do
  while [ $(docker ps -q | wc -l) -ge 3 ]; do sleep 20; done
  docker run --rm --network none -v $R:/rv:ro -v $AU:/au:ro c3keep/coveragepy_f5eb:src bash /rv/run_probe.sh "$c" > $R/logs/probe__${c}.log 2>&1
  echo "probe $c rc=$?"
done
