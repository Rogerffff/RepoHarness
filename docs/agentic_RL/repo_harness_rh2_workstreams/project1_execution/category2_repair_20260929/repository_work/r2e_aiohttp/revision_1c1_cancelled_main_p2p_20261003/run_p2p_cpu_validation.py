"""固定发布版下的新P2P准备/五行重放；不生成模型或改变评分实现。"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess

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
root = Path('/work/rh2-category2-20261003')

def sha(p):
    return 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()

manifest_path = ns.inputs / 'input_manifest.json'
assert sha(manifest_path) == ns.expected_input_manifest_sha256
m = json.loads(manifest_path.read_text())
file_names = [r['name'] for r in m['files']]
assert len(file_names) == len(set(file_names))
assert all(not Path(name).is_absolute() and '..' not in Path(name).parts for name in file_names)
assert Path(__file__).resolve() == (ns.inputs / 'run_p2p_cpu_validation.py').resolve()
case_identity = [(x['case'], x['patch_file'], x.get('original_frozen_file'), x['anticipated_reward']) for x in m['cases']]
assert case_identity == [
    ('baseline', None, None, 0),
    ('gold', 'gold.patch', None, 1),
    ('C1', 'C1.patch', None, 1),
    ('coder_full_frozen', 'coder_complete_original_frozen_binary.patch', 'coder_frozen_patch.json', 0),
    ('qwen_full_frozen', 'qwen_complete_original_frozen_binary.patch', 'qwen_frozen_patch.json', 1),
]
assert {'baseline_manifest.json', 'expected_output.json', 'test_1.py',
        'run_p2p_cpu_validation.py', 'bounded_cpu_job.py'} <= set(file_names)
for case in m['cases']:
    for field in ['patch_file', 'original_frozen_file']:
        if case.get(field):
            assert case[field] in file_names
for r in m['files']:
    p = ns.inputs / r['name']
    assert sha(p) == r['sha256'] and p.stat().st_size == r['bytes'], r['name']
release = root / 'releases' / m['release_id']
repo = release / 'repo'
assert sha(release / 'manifest.json') == m['release_manifest_sha256']
py = root / 'runtime_cpu_v2/rh2/.venv/bin/python'
env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=str(repo / 'rh2/src'))
assert not ns.out.exists(), 'new output required'
ns.out.mkdir()

def save(p, value):
    with p.open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def invoke(label, argv, extra=None):
    start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (ns.out / (label + '.stdout.log')).open('xb') as stdout, (ns.out / (label + '.stderr.log')).open('xb') as stderr:
        rc = subprocess.run(argv, cwd=repo / 'rh2', env=dict(env, **(extra or {})), stdout=stdout, stderr=stderr).returncode
    record = {'stage': label, 'argv': argv, 'returncode': rc, 'started_at': start,
              'finished_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    save(ns.out / (label + '_process.json'), record)
    print(json.dumps(record), flush=True)
    return rc

iid = m['instance_id']
task_id = 'r2e_gym_subset::' + iid
rc = invoke('verify_release', [str(py), '-B', str(release / 'verify_release.py')])
if rc:
    raise SystemExit(rc)

if ns.mode == 'prepare':
    rc = invoke('prepare', [str(py), '-B', str(repo / 'rh2/scripts/replay_grade.py'), 'prepare',
        '--repo-root', str(repo), '--out-dir', str(ns.out / 'prepared'),
        '--private-dir', str(ns.out / 'private'), '--sources', 'r2e_gym_subset', '--task-ids', task_id])
    if rc:
        raise SystemExit(rc)
    views = [json.loads(x) for x in (ns.out / 'prepared/rollout_task_views.jsonl').read_text().splitlines()]
    privates = [json.loads(x) for x in (ns.out / 'private/host_grading_views.jsonl').read_text().splitlines()]
    assert len(views) == len(privates) == 1
    public, grading = views[0]['public'], privates[0]['grading']
    assert views[0]['public_bundle_digest'] == m['public_bundle_digest']
    assert public['problem_statement_sha256'] == m['statement_sha256']
    assert grading['expected_output_json_sha256'] == m['expected_sha256']
    assert grading['run_tests_sh_sha256'] == m['runner_sha256']
    assert grading['hidden_tests_tree_sha256'] == m['hidden_tree_sha256']
    assert json.loads(grading['expected_output_json']) == json.loads((ns.inputs / 'expected_output.json').read_text())
    assert len(json.loads(grading['expected_output_json'])) == 59
    rc = invoke('build', [str(py), '-B', str(repo / 'rh2/scripts/build_r2e_derived.py'),
        '--repo-root', str(repo), '--out-dir', str(ns.out / 'derived'), '--task-ids', iid,
        '--tag-prefix', ns.run_id, '--job-prefix', ns.run_id, '--container-cpus', '2',
        '--container-memory', '4g', '--container-pids-limit', '512', '--cleanup-timeout', '60',
        '--sysconfig-fix', '--env-pins', str(repo / m['env_pins_relative_path'])])
    if rc:
        raise SystemExit(rc)
    assert sha(ns.out / 'derived' / iid / 'context/material/files/test_1.py') == m['hidden_file_sha256']
    overlays = [json.loads(x) for x in (ns.out / 'derived/overlays.jsonl').read_text().splitlines()]
    assert len(overlays) == 1 and overlays[0]['task_id'] == task_id
    save(ns.out / 'prepare_identity.json', {'release_id': m['release_id'],
        'release_manifest_sha256': m['release_manifest_sha256'],
        'summary_sha256': sha(ns.out / 'prepared/replay_summary.json'),
        'overlay_sha256': sha(ns.out / 'derived/overlays.jsonl'), 'public_bundle_digest': views[0]['public_bundle_digest'],
        'grading': {k: grading[k] for k in ['hidden_tests_tree_sha256', 'expected_output_json_sha256', 'run_tests_sh_sha256', 'material_revisions']},
        'overlay': overlays[0], 'expected_count': 59, 'actual_collection_or_grade_run': False})
else:
    assert ns.prepared_base is not None
    summary = ns.prepared_base / 'prepared/replay_summary.json'
    overlays = ns.prepared_base / 'derived/overlays.jsonl'
    assert sha(summary) == ns.expected_prepare_summary_sha256
    assert sha(overlays) == ns.expected_overlay_sha256
    original_base = json.loads((ns.inputs / 'baseline_manifest.json').read_text())
    rows = []
    for index, case in enumerate(m['cases'], 1):
        label = case['case']
        folder = ns.out / 'matrices' / label
        folder.mkdir(parents=True)
        candidate = 'noop' if case['patch_file'] is None else 'patch:' + str(ns.inputs / case['patch_file'])
        rc = invoke(label, [str(py), '-B', str(repo / 'rh2/scripts/replay_grade.py'), 'run',
            '--prepared-summary', str(summary), '--task-ids', task_id, '--candidate', candidate, '--repeat', '1',
            '--candidate-stage-seconds', '900', '--grading-deadline-seconds', '3600',
            '--cleanup-seconds', '120', '--image-pull-seconds', '1800',
            '--eval-log-dir', str(folder / 'eval_logs'), '--artifacts-dir', str(folder / 'artifacts'),
            '--ledger', str(folder / 'ledger.jsonl'), '--image-overlays', str(overlays)],
            {'MILES_RH2_RUN_ID': ns.run_id + '-' + str(index)})
        ledgers = [json.loads(x) for x in (folder / 'ledger.jsonl').read_text().splitlines()] if (folder / 'ledger.jsonl').exists() else []
        row = ledgers[0] if len(ledgers) == 1 else {}
        report = row.get('report') or {}
        record = {'case': label, 'runner_returncode': rc, 'ledger_rows': len(ledgers),
            'reward': report.get('reward'), 'expected_match': report.get('expected_match'),
            'expected_total': report.get('expected_total'), 'outcome': report.get('outcome'),
            'stage_error': row.get('stage_error'), 'ledger': str(folder / 'ledger.jsonl'),
            'expected_reward_for_diagnosis_only': case['anticipated_reward']}
        rows.append(record)
        (ns.out / 'progress.json').write_text(json.dumps({'rows': rows}, ensure_ascii=False, indent=2) + '\n')
        print(json.dumps(record), flush=True)
        if rc or len(ledgers) != 1 or row.get('stage_error') or row.get('runner_integrity_changed') or report.get('reward') is None:
            save(ns.out / 'halt.json', {'reason': 'execution_or_grading_incomplete', 'rows': rows})
            raise SystemExit(rc or 6)
        baselines = list((folder / 'artifacts').rglob('baseline_manifest.json'))
        patches = list((folder / 'artifacts').rglob('frozen_patch.json'))
        assert len(baselines) == len(patches) == 1
        baseline = json.loads(baselines[0].read_text())
        frozen = json.loads(patches[0].read_text())
        assert baseline['entries'] == original_base['entries'], 'actual full baseline differs'
        if case.get('original_frozen_file'):
            original = json.loads((ns.inputs / case['original_frozen_file']).read_text())
            assert frozen['entries'] == original['entries'], 'complete original Frozen entries differ'
        assert report['expected_total'] == 59, 'actual key count must be verified, not forced'
    assert len(rows) == 5 and [r['case'] for r in rows] == [x['case'] for x in m['cases']]
    save(ns.out / 'matrix_summary.json', {'rows': rows, 'all_five_formal_rows_completed': len(rows) == 5,
        'expected_rewards_match': all(x['reward'] == x['expected_reward_for_diagnosis_only'] for x in rows),
        'full_parser_and_semantic_readback_pending': True, 'non_author_result_review_pending': True,
        'old_raw_grade_modified': False, 'new_model_sampling': False})
