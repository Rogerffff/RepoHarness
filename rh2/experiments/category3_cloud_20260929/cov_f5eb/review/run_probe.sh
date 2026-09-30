#!/bin/bash
# 行为探针：应用候选后运行 probe.py（一次性断网容器内）
set -u
cand=$1
cd /testbed
if [ "$cand" = "gold_official" ]; then git apply /rv/materials/gold_official.patch || exit 3
elif [ "$cand" != "noop" ]; then cp -r /rv/cands/$cand/files/. /testbed/ || exit 3; fi
/testbed/.venv/bin/python /rv/probe.py 2>&1 | tail -n 5
