"""MONAI3715 五行 CPU 对照；仅编排已冻结 runner，须在 cpu_slot run 内执行。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'release', 'inputs', 'prepared-job', 'image-job', 'job', 'out'):
        ap.add_argument('--' + name, required=True)
    a = ap.parse_args()
    for value in (a.prepared_job, a.image_job, a.job):
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,100}', value):
            ap.error('invalid job id')
    root, release, inp, out = map(Path, (a.root, a.release, a.inputs, a.out))
    package = root / 'packages/swe_monai'
    manifest_sha = '80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9'
    assert sha(release / 'manifest.json') == manifest_sha
    manifest = json.loads((release / 'manifest.json').read_text())
    for rel, entry in manifest['files'].items():
        f = release / 'repo' / rel
        assert f.stat().st_size == entry['size'] and sha(f) == entry['sha256'], rel
    inputs = json.loads((inp / 'input_manifest.json').read_text())
    for rel, entry in inputs['files'].items():
        f = inp / rel
        assert f.stat().st_size == entry['bytes'] and sha(f) == entry['sha256'], rel
    prepared_launch = json.loads((package / 'launchers' / (a.prepared_job + '.json')).read_text())
    assert prepared_launch['release_sha256'] == manifest_sha
    for job in (a.prepared_job, a.image_job):
        assert json.loads((package / 'launchers' / (job + '.exit.json')).read_text())['rc'] == 0
    image = json.loads((package / 'outputs' / a.image_job / 'preparation.json').read_text())
    assert image['task'] == '3715' and image['status'] == 'image_prepared_not_task_accepted'
    assert image['cleanup']['remaining'] == [] and image['cleanup']['rm_rc'] == image['cleanup']['query_rc'] == 0
    public = json.loads((inp / 'source_bundles/3715_public.json').read_text())
    actual = json.loads(subprocess.check_output(['docker', 'image', 'inspect', public['image']], timeout=60))[0]
    assert actual['Id'] == image['actual_image_id']
    assert image['source_image'] in actual['RepoDigests']
    proposal = json.loads((inp / 'materials/3715/revision_request.json').read_text())
    prepared = package / 'outputs' / a.prepared_job / 'prepared/replay_summary.json'
    out.mkdir(parents=True, exist_ok=False)
    state = {'schema': 'monai.formal_cpu_campaign.v1', 'task_id': 'Project-MONAI__MONAI-3715',
             'job': a.job, 'status': 'running', 'started_at': time.time(),
             'release_manifest_sha256': manifest_sha, 'prepared_job': a.prepared_job,
             'prepared_summary_sha256': sha(prepared), 'image_id_actual': actual['Id'],
             'source_image': image['source_image'], 'script_sha256': sha(__file__), 'rows': []}
    child = None

    def save():
        temp = out / 'campaign.json.tmp'
        temp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        temp.replace(out / 'campaign.json')

    def stop_child():
        nonlocal child
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=180)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                state['cleanup_unconfirmed_after_forced_kill'] = True
        child = None

    def interrupted(signum, _frame):
        stop_child()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(release / 'repo/rh2/src'),
               RH2_SANDBOX_CPUS='2', RH2_SANDBOX_MEMORY_BYTES='4294967296',
               RH2_GRADER_CPUS='2', RH2_GRADER_MEMORY_BYTES='4294967296')
    code = release / 'repo/rh2'
    python = root / 'runtime_cpu_v2/rh2/.venv/bin/python'
    try:
        save()
        for name, expected in [('noop', 0), ('gold', 1), ('eval_only', 0), ('always_eval', 0), ('alternative_local_mode', 1)]:
            dest = out / name
            dest.mkdir()
            patch = inp / 'materials/3715/controls' / (name + '.patch')
            assert sha(patch) == proposal['controls'][name]['sha256'].removeprefix('sha256:')
            candidate = 'noop' if name == 'noop' else 'patch:' + str(patch)
            run_id = a.job + '-' + name.replace('_', '-')
            command = [str(python), str(code / 'experiments/swegym_cpu_preprobe_20260929/replay_with_cpu_budget_v2.py'),
                       '--mode', 'direct', '--code-root', str(code), '--setup-seconds', '900',
                       '--budget-audit-dir', str(dest / 'budget'), '--', 'run',
                       '--prepared-summary', str(prepared), '--task-ids', 'Project-MONAI__MONAI-3715',
                       '--candidate', candidate, '--candidate-stage-seconds', '900',
                       '--grading-deadline-seconds', '3600', '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
                       '--eval-log-dir', str(dest / 'eval_logs'), '--artifacts-dir', str(dest / 'artifacts'),
                       '--ledger', str(dest / 'ledger.jsonl')]
            if name != 'noop':
                command += ['--qualification-ledger', str(out / 'noop/ledger.jsonl')]
            row = {'control': name, 'run_id': run_id, 'expected_reward': expected,
                   'candidate_patch_sha256': sha(patch), 'command': command, 'started_at': time.time()}
            state['rows'].append(row)
            save()
            log = dest / 'runner.log'
            with log.open('xb') as f:
                child = subprocess.Popen(command, cwd=code, env={**env, 'MILES_RH2_RUN_ID': run_id},
                                         stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    row['runner_rc'] = child.wait(timeout=6600)
                except subprocess.TimeoutExpired:
                    stop_child()
                    row['runner_rc'] = 124
                    raise RuntimeError(name + ' outer deadline; cleanup must be audited')
                finally:
                    stop_child()
            row.update(finished_at=time.time(), runner_log_sha256=sha(log))
            rows = [json.loads(line) for line in (dest / 'ledger.jsonl').read_text().splitlines() if line.strip()]
            assert len(rows) == 1, name + ' expected exactly one grading row'
            result = rows[0]
            report = result.get('report') or {}
            row.update(reward=report.get('reward'), outcome=report.get('outcome'),
                       stage_error=result.get('stage_error'), reference_missing_count=result.get('reference_missing_count'),
                       candidate_cleanup=result.get('cleanup'), matches_expected=report.get('reward') == expected)
            finals = []
            for line in log.read_text(errors='replace').splitlines():
                try:
                    data = json.loads(line)
                except ValueError:
                    continue
                if isinstance(data, dict) and 'final_status' in data:
                    finals.append(data)
            row['runner_final'] = finals[-1] if finals else None
            residual = subprocess.run(['docker', 'ps', '-a', '--filter', 'label=rh2.run_id=' + run_id,
                                       '--format', '{{.Names}}'], text=True, capture_output=True, timeout=60)
            row['own_residual'] = {'query_rc': residual.returncode, 'containers': residual.stdout.split(),
                                   'stderr': residual.stderr}
            save()
            if (row['runner_rc'] != 0 or row['stage_error'] or report.get('reward') is None
                    or not (row['candidate_cleanup'] or {}).get('removed')
                    or row['reference_missing_count'] != 0 or not finals
                    or finals[-1]['final_status'].get('exit_code') != 0
                    or residual.returncode != 0 or residual.stdout.strip()):
                raise RuntimeError(name + ' infra, incomplete references, or cleanup requires diagnosis')
        state['status'] = ('executed_pending_non_author_review' if all(x['matches_expected'] for x in state['rows'])
                           else 'executed_expectation_mismatch')
        return 0 if state['status'] == 'executed_pending_non_author_review' else 2
    except BaseException as exc:
        state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        stop_child()
        state['finished_at'] = time.time()
        save()


if __name__ == '__main__':
    raise SystemExit(main())
