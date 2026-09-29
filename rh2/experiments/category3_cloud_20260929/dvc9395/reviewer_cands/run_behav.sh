#!/bin/bash
# usage: run_behav.sh <name> <cand_patch|noop> [scenario names...]
NAME=$1; CAND=$2; shift 2
PY=/opt/miniconda3/envs/testbed/bin/python
cd /testbed
$PY -m pip install -q --no-index --no-deps /wheels/pygit2-1.14.1-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl > /out/$NAME.behav.setup 2>&1
if [ "$CAND" != noop ]; then git apply "$CAND" >> /out/$NAME.behav.setup 2>&1 || { echo CAND_APPLY_FAILED >> /out/$NAME.behav.setup; exit 3; }; fi
git diff --stat >> /out/$NAME.behav.setup
cd /tmp && timeout 280 $PY /in/behav.py "$@" > /out/$NAME.behav.jsonl 2> /out/$NAME.behav.err
echo "rc=$?" >> /out/$NAME.behav.setup
