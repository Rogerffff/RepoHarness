"""MONAI2446/6975 R15 正式对照；仅在共享 cpu_slot 内编排冻结评分入口。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time


MANIFEST_SHA = '2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917'
S2 = 'docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/monai2446_6975_fixed_v1'
MATRICES = {
    '2446': [('noop', 0), ('gold', 1), ('array_no_shuffle', 0), ('alternative_list_copy', 1)],
    '6975': [('noop', 0), ('gold', 1), ('degenerate_discard_dict_output', 0)],
}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'release', 'inputs', 'prepared-job', 'task', 'job', 'out'):
        ap.add_argument('--' + name, required=True)
    a = ap.parse_args()
    for value in (a.prepared_job, a.job):
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,100}', value):
            ap.error('invalid job id')
    if a.task not in MATRICES:
        ap.error('task outside fixed R15 MONAI scope')
    root, release, inp, out = map(Path, (a.root, a.release, a.inputs, a.out))
    package = root / 'packages/swe_monai'
    assert sha(release / 'manifest.json') == MANIFEST_SHA
    manifest = json.loads((release / 'manifest.json').read_text())
    for rel, entry in manifest['files'].items():
        f = release / 'repo' / rel
        assert f.stat().st_size == entry['size'] and sha(f) == entry['sha256'], rel
    inputs = json.loads((inp / 'input_manifest.json').read_text())
    for rel, entry in inputs['files'].items():
        f = inp / rel
        assert f.stat().st_size == entry['bytes'] and sha(f) == entry['sha256'], rel
    prepared_launch = json.loads((package / 'launchers' / (a.prepared_job + '.json')).read_text())
    assert prepared_launch['release_sha256'] == MANIFEST_SHA
    assert json.loads((package / 'launchers' / (a.prepared_job + '.exit.json')).read_text())['rc'] == 0
    iid = 'Project-MONAI__MONAI-' + a.task
    registry = json.loads((release / 'repo' / S2 / 'material_revisions.json').read_text())
    revision = next(x for x in registry['revisions'] if x['instance_id'] == iid)
    binding = revision['environment_binding']
    actual = json.loads(subprocess.check_output(
        ['docker', 'image', 'inspect', binding['prepared_image_id']], timeout=60))[0]
    assert actual['Id'] == binding['prepared_image_id']
    prepared = package / 'outputs' / a.prepared_job / 'prepared/replay_summary.json'
    out.mkdir(parents=True, exist_ok=False)
    (out / 'image_inspect.json').write_text(json.dumps(actual, indent=2) + '\n')
    state = {'schema': 'monai.formal_cpu_campaign.r15.v1', 'task_id': iid,
             'job': a.job, 'status': 'running', 'started_at': time.time(),
             'release_manifest_sha256': MANIFEST_SHA, 'prepared_job': a.prepared_job,
             'prepared_summary_sha256': sha(prepared), 'image_id_actual': actual['Id'],
             'source_image': binding['source_image'], 'script_sha256': sha(__file__),
             'effective_test_patch_sha256': revision['effective_test_patch_sha256'],
             'environment_binding_asset_sha256': revision['environment_binding_asset_sha256'],
             'expected_references': len(revision['effective_fail_to_pass']) + len(revision['effective_pass_to_pass']),
             'rows': []}
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

    def observe(row, dest):
        """只读本行标签容器；不改 manager，不读取其它包容器。"""
        query = subprocess.run(['docker', 'ps', '-a', '--filter', 'label=rh2.run_id=' + row['run_id'],
                                '--format', '{{.ID}}'], text=True, capture_output=True, timeout=20)
        if query.returncode:
            row.setdefault('observation_errors', []).append(query.stderr)
            return
        for cid in query.stdout.split():
            if cid in row['container_observations']:
                continue
            ins = subprocess.run(['docker', 'inspect', cid], text=True, capture_output=True, timeout=20)
            if ins.returncode:
                row.setdefault('observation_errors', []).append(ins.stderr)
                continue
            facts = json.loads(ins.stdout)[0]
            assert facts['Config']['Labels']['rh2.run_id'] == row['run_id']
            f = dest / ('container_' + cid + '.json')
            f.write_text(json.dumps(facts, indent=2) + '\n')
            h = facts['HostConfig']
            row['container_observations'][cid] = {
                'name': facts['Name'], 'image_id_actual': facts['Image'], 'config_user': facts['Config']['User'],
                'NanoCpus': h['NanoCpus'], 'Memory': h['Memory'], 'PidsLimit': h['PidsLimit'],
                'inspect_sha256': sha(f), 'observed_at': time.time(), 'file': f.name}

    try:
        save()
        for name, expected in MATRICES[a.task]:
            dest = out / name
            dest.mkdir()
            patch = (inp / 'materials/2446/controls' if a.task == '2446' else inp / 'inherited6975/controls') / (name + '.patch')
            entry = inputs['files'][str(patch.relative_to(inp))]
            assert sha(patch) == entry['sha256']
            candidate = 'noop' if name == 'noop' else 'patch:' + str(patch)
            run_id = a.job + '-' + name.replace('_', '-')
            command = [str(python), str(code / 'experiments/swegym_cpu_preprobe_20260929/replay_with_cpu_budget_v2.py'),
                       '--mode', 'direct', '--code-root', str(code),
                       '--setup-seconds', '1800' if a.task == '6975' else '900',
                       '--budget-audit-dir', str(dest / 'budget'), '--', 'run',
                       '--prepared-summary', str(prepared), '--task-ids', iid,
                       '--candidate', candidate, '--candidate-stage-seconds', '900',
                       '--grading-deadline-seconds', '3600', '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
                       '--eval-log-dir', str(dest / 'eval_logs'), '--artifacts-dir', str(dest / 'artifacts'),
                       '--ledger', str(dest / 'ledger.jsonl')]
            if name != 'noop':
                command += ['--qualification-ledger', str(out / 'noop/ledger.jsonl')]
            row = {'control': name, 'run_id': run_id, 'expected_reward': expected,
                   'candidate_patch_sha256': sha(patch), 'command': command, 'started_at': time.time(),
                   'container_observations': {}}
            state['rows'].append(row)
            save()
            log = dest / 'runner.log'
            with log.open('xb') as f:
                child = subprocess.Popen(command, cwd=code, env={**env, 'MILES_RH2_RUN_ID': run_id},
                                         stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
                deadline = time.monotonic() + 6600
                while child.poll() is None:
                    if time.monotonic() > deadline:
                        stop_child()
                        row['runner_rc'] = 124
                        raise RuntimeError(name + ' outer deadline; cleanup must be audited')
                    observe(row, dest)
                    save()
                    try:
                        child.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        pass
                row['runner_rc'] = child.returncode
                stop_child()
            row.update(finished_at=time.time(), runner_log_sha256=sha(log))
            rows = [json.loads(line) for line in (dest / 'ledger.jsonl').read_text().splitlines() if line.strip()]
            assert len(rows) == 1, name + ' expected exactly one grading row'
            result = rows[0]
            report = result.get('report') or {}
            row.update(reward=report.get('reward'), outcome=report.get('outcome'),
                       stage_error=result.get('stage_error'), reference_missing_count=result.get('reference_missing_count'),
                       candidate_cleanup=result.get('cleanup'), matches_expected=report.get('reward') == expected,
                       ledger_image_id_actual=result.get('image_id_actual'),
                       f2p_total=report.get('f2p_total'), p2p_total=report.get('p2p_total'))
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
                    or residual.returncode != 0 or residual.stdout.strip()
                    or row['ledger_image_id_actual'] != actual['Id']
                    or row['f2p_total'] != len(revision['effective_fail_to_pass'])
                    or row['p2p_total'] != len(revision['effective_pass_to_pass'])):
                raise RuntimeError(name + ' infra, material identity, incomplete references, or cleanup requires diagnosis')
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
