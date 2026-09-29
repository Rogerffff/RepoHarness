#!/usr/bin/env bash
# pydantic-8316：第二组候选的正式评分（原材料 + 修订版 v1），在 run_all.sh 之后顺序执行。
set -uo pipefail
E=/home/user/RepoHarness/rh2/experiments/category3_cloud_20260929/pydantic8316
CANDS="normalize lower_or_start no_lower_upper"
bash $E/run_formal.sh orig $CANDS
bash $E/run_formal.sh rev1 $CANDS
