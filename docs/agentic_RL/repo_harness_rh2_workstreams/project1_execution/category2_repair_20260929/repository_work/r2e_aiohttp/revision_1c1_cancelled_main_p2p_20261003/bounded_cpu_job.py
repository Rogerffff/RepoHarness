"""仅给本批固定准备/五行验证设总时限，独立记录超时及清理宽限。"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import time

ap = argparse.ArgumentParser()
ap.add_argument('--mode', required=True, choices=['prepare', 'matrix'])
ap.add_argument('--inputs', required=True, type=Path)
ap.add_argument('--expected-input-manifest-sha256', required=True)
ap.add_argument('--out', required=True, type=Path)
ap.add_argument('--run-id', required=True)
ap.add_argument('--prepared-base', type=Path)
ap.add_argument('--expected-prepare-summary-sha256')
ap.add_argument('--expected-overlay-sha256')
ns = ap.parse_args()
manifest_path = ns.inputs / 'input_manifest.json'
assert 'sha256:' + hashlib.sha256(manifest_path.read_bytes()).hexdigest() == ns.expected_input_manifest_sha256
m = json.loads(manifest_path.read_text())
controller = next(r for r in m['files'] if r['name'] == 'bounded_cpu_job.py')
assert Path(__file__).resolve() == (ns.inputs / controller['name']).resolve()
assert 'sha256:' + hashlib.sha256(Path(__file__).read_bytes()).hexdigest() == controller['sha256']
argv = ['/work/rh2-category2-20261003/runtime_cpu_v2/rh2/.venv/bin/python', '-B',
    str(ns.inputs / 'run_p2p_cpu_validation.py'), '--mode', ns.mode,
    '--inputs', str(ns.inputs), '--expected-input-manifest-sha256', ns.expected_input_manifest_sha256,
    '--out', str(ns.out), '--run-id', ns.run_id]
if ns.mode == 'matrix':
    assert ns.prepared_base is not None and ns.expected_prepare_summary_sha256 and ns.expected_overlay_sha256
    argv += ['--prepared-base', str(ns.prepared_base),
        '--expected-prepare-summary-sha256', ns.expected_prepare_summary_sha256,
        '--expected-overlay-sha256', ns.expected_overlay_sha256]
budget = 10800 if ns.mode == 'prepare' else 24000
grace = 120
start = datetime.datetime.now(datetime.timezone.utc).isoformat()
child = subprocess.Popen(argv, start_new_session=True)
timed_out = False
try:
    rc = child.wait(timeout=budget)
except subprocess.TimeoutExpired:
    timed_out = True
    try:
        os.killpg(child.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline:
        child.poll()
        try:
            os.killpg(child.pid, 0)
        except ProcessLookupError:
            break
        time.sleep(1)
    try:
        os.killpg(child.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    child.wait()
    rc = 124
record = {'started_at': start, 'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'mode': ns.mode, 'argv': argv, 'returncode': rc, 'whole_run_seconds': budget,
    'cleanup_grace_seconds': grace, 'timeout_occurred': timed_out,
    'docker_cleanup_confirmed_by_this_controller': False,
    'on_timeout': '停止本批，保留真实infra/null与ledger并另核daemon残留；信号不证明manager finally完成。',
    'original_grades_changed': False, 'new_model_sampling': False}
with ns.out.with_name(ns.out.name + '_bounded_controller_receipt.json').open('x') as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
    f.write('\n')
print(json.dumps(record), flush=True)
raise SystemExit(rc)
