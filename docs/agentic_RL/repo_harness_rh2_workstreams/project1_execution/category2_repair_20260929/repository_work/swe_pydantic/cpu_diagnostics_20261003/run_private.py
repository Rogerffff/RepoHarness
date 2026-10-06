"""通过冻结入口执行本包私有安装／行为诊断；不产生正式 reward。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

RELEASE_ID = 'cat2-cpu-r2e078079-swe7-git-20261003-v1'
RELEASE_SHA = '80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--task', choices=('8511', '8567'), required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    here = Path(__file__).resolve().parent
    root = Path('/work/rh2-category2-20261003')
    release = root / 'releases' / RELEASE_ID
    repo = release / 'repo'
    code = repo / 'rh2'
    out = Path(a.out).resolve()
    assert out.is_relative_to(root / 'packages/swe_pydantic/private_v1/outputs')
    out.mkdir(parents=True, exist_ok=False)
    c = json.loads((here / 'private_inputs.json').read_text())['tasks'][a.task]
    state = dict(task='pydantic__pydantic-' + a.task,
                 scope='private_root_install_and_selected_behavior_diagnostic',
                 status='running', source_release=RELEASE_ID, manifest_sha256=sha(release / 'manifest.json'),
                 wrapper_sha256=sha(Path(__file__)), input_sha256=sha(here / 'private_inputs.json'),
                 runtime=sys.executable, steps=[], started_at=time.time(),
                 formal_grading_verified=False, model_probe=False, frozen_patch_exported=False)

    def save():
        (out / 'diagnostic_result.json').write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')

    def stop(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(code / 'src'))

    def run(name, argv, timeout):
        step = dict(name=name, argv=[str(x) for x in argv], started_at=time.time())
        state['steps'].append(step)
        save()
        with (out / (name + '.log')).open('wb') as log:
            proc = subprocess.Popen(step['argv'], env=env, cwd=code, stdout=log,
                                    stderr=subprocess.STDOUT, start_new_session=True)
            try:
                rc = proc.wait(timeout=timeout)
            except BaseException:
                if proc.poll() is None:
                    os.killpg(proc.pid, signal.SIGTERM)
                    try:
                        proc.wait(timeout=150)
                    except subprocess.TimeoutExpired:
                        os.killpg(proc.pid, signal.SIGKILL)
                        proc.wait(timeout=30)
                        state['cleanup_unconfirmed'] = True
                step.update(rc=proc.returncode, interrupted=True, finished_at=time.time())
                save()
                raise
        step.update(rc=rc, finished_at=time.time())
        save()
        if rc:
            raise RuntimeError(name + ': rc=' + str(rc))

    try:
        assert state['manifest_sha256'] == RELEASE_SHA
        run('verify_release', [sys.executable, '-B', release / 'verify_release.py'], 180)
        runner = code / 'experiments/swegym_cpu_preprobe_20260929/private_behavior.py'
        assert sha(runner) == c['private_runner_sha256']
        for entry in c['files_checked']:
            assert sha(Path(entry['path'])) == entry['sha256'], entry['path']
        spec = here / c['spec']
        assert sha(spec) == c['spec_sha256']
        run('image_cached', ['docker', 'image', 'inspect', c['image']], 45)
        run('trusted_prepare', [sys.executable, '-B', code / 'scripts/replay_grade.py', 'prepare',
                               '--repo-root', repo, '--out-dir', out / 'prepared', '--private-dir', out / 'private',
                               '--task-ids', 'swe_gym_lite::' + state['task'], '--sources', 'swe_gym_lite'], 180)
        summary = json.loads((out / 'prepared/replay_summary.json').read_text())
        sys.path.insert(0, str(code / 'src'))
        from repoharness2.envpack.prepared_tasks import load_prepared_manifest, load_prepared_rollout_views
        manifest = load_prepared_manifest(out / 'prepared', expected_sha256=summary['prepared_manifest_sha256'])
        view = load_prepared_rollout_views(out / 'prepared', manifest)['swe_gym_lite::' + state['task']]
        assert view.public.base_commit == c['base_commit']
        assert view.public_bundle_digest == c['public_bundle_digest']
        state['prepared_summary'] = summary
        state['prepared_scope'] = 'original_published_material_identity_only'
        run('private_behavior', [sys.executable, '-B', runner, spec, '--out', out / 'behavior'], 5400)
        raw = json.loads((out / 'behavior/summary.json').read_text())
        assert raw['image_id_actual'] == c['image']
        assert set(raw['variants']) == set(c['candidates'])
        state['variants'] = {}
        for candidate, row in raw['variants'].items():
            assert row['status'] == 'executed_interpret_separately', candidate
            assert len(row['preparation']) == c['preparation_step_counts'][candidate]
            assert all(x['rc'] == 0 for x in row['preparation'])
            assert row['cleanup']['rm_rc'] == 0 and row['cleanup']['query_rc'] == 0
            assert row['cleanup']['remaining'] == []
            assert len(row['commands']) == 1 and row['commands'][0]['rc'] in (0, 1)
            output = (out / 'behavior' / candidate / 'selected_nodes.out').read_text()
            statuses = dict(re.findall(r'^(tests/\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)(?:\s|$)',
                                       output, flags=re.MULTILINE))
            assert set(statuses) == set(c['nodes']), (candidate, statuses)
            assert all(x in ('PASSED', 'FAILED') for x in statuses.values()), candidate
            assert 'ERROR collecting' not in output and 'no tests ran' not in output
            assert row['commands'][0]['rc'] == (0 if all(x == 'PASSED' for x in statuses.values()) else 1)
            state['variants'][candidate] = dict(statuses=statuses, preparation=row['preparation'],
                                                execution=row['commands'], cleanup=row['cleanup'])
        state['status'] = 'private_install_and_selected_nodes_executed'
    except BaseException as exc:
        state.update(status='private_diagnostic_stopped_needs_analysis', error=repr(exc))
        raise
    finally:
        state['finished_at'] = time.time()
        save()
        print(json.dumps({k: state[k] for k in ('task', 'status')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
