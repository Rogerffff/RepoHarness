#!/usr/bin/env bash
# pydantic-8316：顺序执行全部正式评分（原材料 + 修订版 v1），同一时间只跑一个。
set -uo pipefail
E=/home/user/RepoHarness/rh2/experiments/category3_cloud_20260929/pydantic8316
CANDS="noop gold keep_digit lookaround scan upstream_main lead_only first_only acr3 literal"
bash $E/run_formal.sh orig $CANDS
bash $E/run_formal.sh rev1 $CANDS
