#!/bin/bash
# 公开命令 repro_cli_json 原样（commands.json）
cd /testbed && rm -rf /tmp/rh2_cov_cli && mkdir -p /tmp/rh2_cov_cli && printf "a = {'b': 1}\nif a.get('a'):\n    b = 1\n" > /tmp/rh2_cov_cli/rh2_cli_probe.py && export COVERAGE_FILE=/tmp/rh2_cov_cli/.coverage PYTHONDONTWRITEBYTECODE=1 && python -m coverage run --branch /tmp/rh2_cov_cli/rh2_cli_probe.py && python -m coverage json -o /tmp/rh2_cov_cli/coverage.json --include='/tmp/rh2_cov_cli/*' && python -c "import json; r = json.load(open('/tmp/rh2_cov_cli/coverage.json')); print('totals:', json.dumps(r['totals'], sort_keys=True)); print('file summaries:', json.dumps(dict((k, v['summary']) for k, v in r['files'].items()), sort_keys=True))"
echo RH2_CMD_RC=$?
