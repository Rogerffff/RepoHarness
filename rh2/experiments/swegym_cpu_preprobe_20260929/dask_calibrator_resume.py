"""Dask7656原控制面超时后的独立评分复验；复用已完成actor/私有对照。"""
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path('/work/swegym_cpu_preprobe_20260929')
CODE = ROOT / 'code_v1/rh2'
IID = 'dask__dask-7656'


def main():
    inp = ROOT / 'inputs_v1' / IID
    old = ROOT / 'results' / IID / 'calibration_v1'
    state0 = json.loads((old / 'status.json').read_text())
    if state0['status'] != 'stopped_needs_diagnosis':
        raise RuntimeError('original run still active or not the diagnosed stop')
    row0 = json.loads((old / 'noop/ledger.jsonl').read_text().splitlines()[0])
    if row0['report']['infra_failure_detail'] != 'grading_control_surface_protect_timeout_after_300s':
        raise RuntimeError('original failure differs; do not apply this diagnosis')
    if not row0['cleanup']['removed']:
        raise RuntimeError('original cleanup not confirmed')
    image = json.loads((old / 'grader_build' / IID / 'image.json').read_text())['image_id']
    out = ROOT / 'results' / IID / 'grading_setup900_v1'
    out.mkdir(exist_ok=False)
    state = {'task': IID, 'started_at': time.time(), 'status': 'running', 'steps': [],
             'reuse': {'actor': str(old / 'actor_revised'), 'private_behavior': str(old / 'private_behavior')},
             'change': 'same image/code/recipe/candidates; env_reset_timeout 300 to 900 seconds only'}

    def save():
        (out / 'status.json').write_text(json.dumps(state, indent=2) + '\n')

    try:
        for name, candidate in [('noop', 'noop'), ('gold', 'gold-dir:' + str(ROOT / 'gold/v1')),
                                ('opaque', 'patch:' + str(inp / 'opaque_dataclass.patch')),
                                ('wrong_result_type', 'patch:' + str(inp / 'wrong_result_type.patch'))]:
            dest = out / name
            dest.mkdir()
            cmd = [CODE / '.venv/bin/python', ROOT / 'tools_v1/replay_with_cpu_budget.py', '--setup-seconds', '900',
                   '--budget-audit-dir', dest / 'budget', '--code-root', CODE,
                   '--recipe', inp / 'grader_install_recipe.json', '--audit-dir', dest / 'recipe', '--', 'run',
                   '--prepared-summary', ROOT / 'prepared/v1/replay_summary.json', '--task-ids', IID,
                   '--candidate', candidate, '--derived-image', image, '--derived-image-recipe', 'cpu29-calibration-v1:' + IID,
                   '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
                   '--eval-log-dir', dest / 'eval_logs', '--artifacts-dir', dest / 'artifacts', '--ledger', dest / 'ledger.jsonl']
            step = {'name': name, 'started_at': time.time(), 'command': list(map(str, cmd))}
            state['steps'].append(step)
            save()
            with (out / (name + '.log')).open('w') as log:
                p = subprocess.run(list(map(str, cmd)), cwd=CODE, stdout=log, stderr=subprocess.STDOUT,
                                   env={**os.environ, 'MILES_RH2_RUN_ID': 'cpu29-dask7656-setup900-' + name})
            step.update(rc=p.returncode, finished_at=time.time())
            save()
            if p.returncode:
                raise RuntimeError('driver failed; stop and inspect cleanup')
            rows = [json.loads(x) for x in (dest / 'ledger.jsonl').read_text().splitlines() if x.strip()]
            if len(rows) != 1:
                raise RuntimeError('grading row missing/ambiguous')
            row = rows[0]
            test = row.get('test') or {}
            install = row.get('install') or {}
            if (row.get('stage_error') or not (row.get('cleanup') or {}).get('removed') or
                (row.get('report') or {}).get('reward') is None or not test.get('segment_completed') or
                test.get('rc') not in (0, 1) or install.get('install_rc_last_command') != 0 or
                row.get('reference_missing_count') != 0):
                raise RuntimeError('incomplete installation/tests/reference/cleanup; no further candidates')
            if name in ('noop', 'gold') and row['report']['reward'] != (1 if name == 'gold' else 0):
                raise RuntimeError('control unexpected; inspect before next candidate')
        state['status'] = 'executed_pending_review'
    except BaseException as exc:
        state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        state['finished_at'] = time.time()
        save()


if __name__ == '__main__':
    main()
