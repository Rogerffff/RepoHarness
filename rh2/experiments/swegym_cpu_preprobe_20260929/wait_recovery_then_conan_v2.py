"""已诊断准备失败后的新队列；旧停止记录不恢复、不覆盖。"""
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path

R = Path('/work/swegym_cpu_preprobe_20260929')
OUT = R / 'reserve_conan_wait_v2.json'
DEPENDENCY = R / 'results/Project-MONAI__MONAI-6975/grading-setup1800-v1/status.json'
state = {'started_at': time.time(), 'status': 'waiting_setup1800_recovery', 'dependency': str(DEPENDENCY)}


def save():
    OUT.write_text(json.dumps(state, indent=2) + '\n')


def require(value, message):
    if not value:
        raise RuntimeError(message)


def interrupted(sig, _frame):
    state.update(status='interrupted_before_dispatch', signal=sig, finished_at=time.time())
    save()
    raise SystemExit(128 + sig)


for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, interrupted)
require(not OUT.exists(), 'new waiting record already exists')
save()
try:
    while True:
        d = json.loads(DEPENDENCY.read_text())
        state.update(dependency_status=d['status'], checked_at=time.time())
        save()
        if d['status'] == 'executed_pending_review':
            break
        require(d['status'] == 'running', 'recovery stopped or state unknown: ' + str(d.get('error')))
        require(time.time() - state['started_at'] < 25200, 'wait exceeded 7 hours')
        unit = subprocess.run(['systemctl', 'is-active', 'rh2-cpu29-monai6975-setup1800-v1'],
                              text=True, capture_output=True, timeout=15)
        require(unit.returncode == 0 and unit.stdout.strip() == 'active', 'recovery unit inactive while state running')
        time.sleep(15)
    require(set(d.get('formal_results', {})) == {'noop', 'gold', 'degenerate'}, 'recovery groups incomplete')
    require(not d.get('error'), 'recovery retained an error')
    sibling = json.loads((R / 'results/Project-MONAI__MONAI-4583/reserve6-v1/status.json').read_text())
    require(sibling.get('status') == 'executed_pending_review', 'sibling task not closed normally')
    require(subprocess.check_output(['docker', 'ps', '-aq'], text=True, timeout=30).strip() == '',
            'containers remain before Conan dispatch')
    networks = subprocess.check_output(['docker', 'network', 'ls', '--format', '{{.Name}}'],
                                       text=True, timeout=30).splitlines()
    require(all(n in ('bridge', 'host', 'none') for n in networks), 'task networks remain')
    manifest = json.loads((R / 'queue_reserve_conan_v2.json').read_text())
    require([j['task'] for j in manifest['jobs']] == ['conan-io__conan-13230', 'conan-io__conan-13721'],
            'unexpected continuation tasks')
    for name, expected in manifest['script_sha256'].items():
        require(hashlib.sha256((R / 'tools_v1' / name).read_bytes()).hexdigest() == expected,
                'reviewed continuation script changed: ' + name)
    require(not (R / 'dispatch_reserve_conan_v2').exists(), 'continuation already dispatched')
    state.update(status='recovery_execution_and_cleanup_checked_dispatching', checked_at=time.time())
    save()
    py = str(R / 'code_v1/rh2/.venv/bin/python')
    os.execv(py, [py, str(R / 'tools_v1/dispatch_followups.py'), '--manifest',
                 str(R / 'queue_reserve_conan_v2.json'), '--out', str(R / 'dispatch_reserve_conan_v2')])
except BaseException as exc:
    state.update(status='stopped_needs_diagnosis', error=repr(exc), finished_at=time.time())
    save()
    raise
