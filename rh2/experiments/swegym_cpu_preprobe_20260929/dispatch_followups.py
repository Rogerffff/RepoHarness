"""本夜固定清单的单机派发；2路含已在跑校准，任一异常暂停新派发。"""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

ROOT = Path('/work/swegym_cpu_preprobe_20260929')
PY = ROOT / 'code_v1/rh2/.venv/bin/python'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--manifest', required=True)
    ap.add_argument('--out', required=True)
    ns = ap.parse_args()
    manifest = json.loads(Path(ns.manifest).read_text())
    out = Path(ns.out)
    out.mkdir(parents=True, exist_ok=False)
    state = {'started_at': time.time(), 'status': 'running', 'jobs': [], 'parallel_limit': 2}
    pending = list(manifest['jobs'])
    running = {}
    stop_reason = None

    def save():
        (out / 'state.json').write_text(json.dumps(state, indent=2) + '\n')

    def on_signal(signum, _frame):
        nonlocal stop_reason
        if stop_reason is None:
            stop_reason = 'dispatcher signal ' + str(signum)
            for p, _log, _record in running.values():
                if p.poll() is None:
                    os.killpg(p.pid, signal.SIGTERM)

    signal.signal(signal.SIGTERM, on_signal)
    signal.signal(signal.SIGINT, on_signal)
    save()
    while pending or running:
        external = 0
        for entry in manifest.get('external_jobs', []):
            p = Path(entry['status'])
            try:
                d = json.loads(p.read_text())
            except (OSError, ValueError) as exc:
                stop_reason = 'external status unreadable: ' + repr(exc)
                break
            if d['status'] == 'running':
                unit = subprocess.run(['systemctl', 'is-active', entry['unit']], capture_output=True, text=True, timeout=10)
                if unit.returncode or unit.stdout.strip() != 'active':
                    stop_reason = 'external run status stale or unit stopped: ' + entry['unit']
                    break
                external += 1
            elif d['status'] != 'executed_pending_review':
                stop_reason = 'external job needs diagnosis: ' + entry['unit']
                break
        for key, (proc, log, record) in list(running.items()):
            rc = proc.poll()
            if rc is None:
                continue
            log.close()
            result_root = ROOT / 'results' / record['task']
            after = set(p.name for p in result_root.iterdir()) if result_root.exists() else set()
            new = sorted(after - set(record['existing_result_dirs']))
            record.update(rc=rc, finished_at=time.time(), result_dirs=new)
            summaries = []
            for name in new:
                try:
                    d = json.loads((result_root / name / 'status.json').read_text())
                    summaries.append({'directory': name, 'status': d['status'], 'error': d.get('error')})
                except (OSError, ValueError) as exc:
                    summaries.append({'directory': name, 'status': 'unknown', 'error': repr(exc)})
            record['result_statuses'] = summaries
            if rc or len(summaries) != 1 or summaries[0]['status'] != 'executed_pending_review':
                stop_reason = 'task requires diagnosis: ' + record['task']
            del running[key]
        while pending and not stop_reason and len(running) + external < 2:
            job = pending.pop(0)
            iid = job['task']
            if iid in running:
                raise ValueError('duplicate task in manifest')
            result_root = ROOT / 'results' / iid
            command = [str(PY), str(ROOT / 'tools_v1' / job['script']), '--task', iid]
            record = {'task': iid, 'command': command, 'started_at': time.time(),
                      'existing_result_dirs': sorted(p.name for p in result_root.iterdir()) if result_root.exists() else []}
            log = (out / (iid + '.log')).open('w')
            proc = subprocess.Popen(command, cwd=ROOT / 'code_v1/rh2', stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            record['pid'] = proc.pid
            state['jobs'].append(record)
            running[iid] = (proc, log, record)
        state.update(pending=[j['task'] for j in pending], external_running=external,
                     active=list(running), stop_reason=stop_reason, updated_at=time.time())
        save()
        if stop_reason and not running:
            break
        time.sleep(10)
    state.update(status='paused_needs_diagnosis' if stop_reason else 'executed_pending_review',
                 stop_reason=stop_reason, finished_at=time.time())
    save()
    return 2 if stop_reason else 0


if __name__ == '__main__':
    raise SystemExit(main())
