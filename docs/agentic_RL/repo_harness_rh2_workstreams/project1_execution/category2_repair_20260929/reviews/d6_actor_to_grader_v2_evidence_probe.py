"""只读本地同步原件：独立重建 census、核正式脚本/参考/清理，不读自动 review。"""
from __future__ import annotations

import ast
import dataclasses
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
RUNS = ROOT / "runs/category2_repair_20260929"
CODE = RUNS / "frozen_d6_v2/code_v1"
REMOTE = RUNS / "remote/d6"
sys.path.insert(0, str(CODE / "rh2/src"))
sys.dont_write_bytecode = True

from repoharness2.adapters.slime.baseline_census import build_census_script, parse_census_output
from repoharness2.adapters.slime.prepared_task_face import build_grading_spec_from_host_view
from repoharness2.adapters.slime.sandbox_profile import git_sanitize_script, git_sanitize_violations, parse_key_value_output
from repoharness2.contracts.baseline_manifest import BaselineWorkspaceManifestV1, compute_baseline_manifest_digest
from repoharness2.contracts.frozen_patch import FrozenPatchArtifactV1, compute_frozen_patch_digest
from repoharness2.envpack.prepared_tasks import load_host_grading_views, load_prepared_manifest, load_prepared_rollout_views
from repoharness2.envpack.training_view import TrustedTaskController
from repoharness2.grading.manager import TRUSTED_ROOT_EXEC_PREFIX, grading_scripts_digest


def read(path):
    return json.loads(path.read_text())


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_files(base, manifest):
    for rel, item in manifest['files'].items():
        path = base / rel
        assert path.is_file() and not path.is_symlink()
        assert sha(path) == item['sha256'] and path.stat().st_size == item['bytes'], path
    return len(manifest['files'])


def verify_code():
    manifest = RUNS / 'frozen_d6_v2/code_v1_manifest.json'
    assert sha(manifest) == '4110b196c8df1f0e8d51595b525eed17f6487977d83e59e2fddd68f5f11d965b'
    count = verify_files(CODE, read(manifest))
    rel = 'rh2/src/repoharness2/grading/manager.py'
    trees = [ast.parse((base / rel).read_text()) for base in (RUNS / 'frozen_d6_v1/code_v1', CODE)]
    methods = [next(n for n in ast.walk(t) if isinstance(n, ast.AsyncFunctionDef) and n.name == '_verify_baseline_rebuild') for t in trees]
    assert ast.dump(methods[0]) == ast.dump(methods[1])
    for rel in ('rh2/src/repoharness2/adapters/slime/baseline_census.py', 'rh2/src/repoharness2/contracts/baseline_manifest.py'):
        assert (CODE / rel).read_bytes() == (RUNS / 'frozen_d6_v1/code_v1' / rel).read_bytes()
    return count


def verify_task(iid):
    directory = REMOTE / 'actor_to_grader_v2' / iid
    actor = REMOTE / 'actor_acceptance_v1' / iid
    status = read(directory / 'status.json')
    facts = read(directory / 'input_check.json')
    actor_manifest = read(actor / 'recordmanifest.json')
    assert facts['actor_recordmanifest_sha256'] == sha(actor / 'recordmanifest.json')
    assert facts['actor_files'] == actor_manifest['files']
    files = verify_files(directory, read(directory / 'recordmanifest.json'))
    assert verify_files(actor, actor_manifest) == 28
    assert status['runner_sha256'] == sha(RUNS / 'tools/d6_actor_to_grader_v2/actor_to_grader.py')
    assert status['actor_origin_code_manifest_sha256'] == '43186d0d85f1eb4e7d28e51b92a9a2c82bf1d4ff178d785d8d4846795300460e'
    assert status['execution_code_manifest_sha256'] == sha(RUNS / 'frozen_d6_v2/code_v1_manifest.json')
    baseline = BaselineWorkspaceManifestV1.model_validate_json((actor / 'baseline_manifest.json').read_text())
    frozen = FrozenPatchArtifactV1.model_validate_json((actor / 'frozen_patch.json').read_text())
    assert not frozen.entries and compute_frozen_patch_digest(frozen) == facts['frozen_patch_digest']
    assert compute_baseline_manifest_digest(baseline) == facts['baseline_digest'] == frozen.baseline_manifest_digest
    calls = [(p.parent, read(p)) for p in sorted(directory.glob('docker_calls/*/call.json'))]
    for p, call in calls:
        for stream in ('stdout', 'stderr'):
            assert sha(p / (stream + '.full')) == call[stream + '_sha256']
        assert call['exit_code'] == 0, p
    census_path, census = next((p, c) for p, c in calls if c['phase'] == 'baseline_rebuild')
    assert tuple(census['argv'][2:-1]) == TRUSTED_ROOT_EXEC_PREFIX
    assert census['argv'][-1] == build_census_script(baseline.workdir, baseline.policy)
    raw = (census_path / 'stdout.full').read_text()
    rebuilt = parse_census_output(raw, **{key: getattr(baseline, key) for key in
        ('task_id', 'workdir', 'public_bundle_digest', 'runtime_image_digest', 'materialized_head', 'task_base_commit', 'policy')})
    assert rebuilt == baseline, iid
    sanitize_path, sanitize = next((p, c) for p, c in calls if c['phase'] == 'git_sanitize')
    assert tuple(sanitize['argv'][2:-1]) == TRUSTED_ROOT_EXEC_PREFIX
    assert sanitize['argv'][-1] == git_sanitize_script(baseline.workdir)
    sanity = parse_key_value_output((sanitize_path / 'stdout.full').read_text())
    assert not git_sanitize_violations(sanity, exit_code=0)
    assert sanity['HEAD_BEFORE'] == sanity['HEAD_AFTER'] == baseline.materialized_head
    probe_path, _ = next((p, c) for p, c in calls if c['phase'] == 'env_reset')
    assert 'HEAD=' + baseline.materialized_head + '\n' in (probe_path / 'stdout.full').read_text()
    assert sanitize_path.name < census_path.name
    cpu = REMOTE / 'cpu_acceptance_v1'
    summary = read(cpu / 'prepared/replay_summary.json')
    manifest = load_prepared_manifest(cpu / 'prepared', expected_sha256=summary['prepared_manifest_sha256'])
    views = load_prepared_rollout_views(cpu / 'prepared', manifest)
    hosts = load_host_grading_views(cpu / 'private/host_grading_views.jsonl', expected_sha256=manifest.host_grading_artifact_sha256, manifest=manifest)
    tid = 'swe_gym_lite::' + iid
    view, host = views[tid], hosts[tid]
    assert host == TrustedTaskController.from_repo_root(CODE).grading_view(tid, environment_package_digest=view.environment_package_digest)
    spec = build_grading_spec_from_host_view(host, image=view.public.image, image_manifest_digest=view.public.image_manifest_digest)
    spec = dataclasses.replace(spec, image=facts['image'], image_manifest_digest=None, image_local_build=True, image_local_build_id=facts['image'])
    for p, call in calls:
        if call.get('input_bytes') is not None:
            actual = (p / 'stdin.bin').read_text()
            expected = spec.trusted_setup_script if '.trusted_setup' in call['argv'][-1] else spec.candidate_test_script
            assert actual == expected
    report = read(directory / 'report.json')
    logpath = next(directory.glob('eval_logs/*.eval.log'))
    log = logpath.read_text()
    assert report['eval_log_ref']['sha256'] == 'sha256:' + sha(logpath)
    assert report['eval_log_ref']['byte_size'] == logpath.stat().st_size
    assert report['reward'] == 0 and report['outcome'] == 'unresolved' and report['failure_category'] == 'tests_failed'
    segment = log.split('>>>>> Start Test Output', 1)[1].split('>>>>> End Test Output', 1)[0]
    states = dict((node, state) for state, node in re.findall(r'^(PASSED|FAILED|SKIPPED|XFAIL|XPASS) (\S+)', segment, re.M))
    expected = {node: 'FAILED' if node in host.grading.fail_to_pass else 'PASSED' for node in host.grading.fail_to_pass + host.grading.pass_to_pass}
    assert states == expected
    collection = [l for l in segment.splitlines() if re.search(r'\b\d+ (?:selected|items)\b', l)]
    assert any(re.search(r'\b' + str(len(expected)) + r' (?:selected|items)\b', l) for l in collection)
    assert 'RH2_INSTALL_CMD_FAILED=' not in '\n'.join(l for l in log.splitlines() if not l.startswith('+ trap '))
    assert '\nRH2_INSTALL_RC=0\n' in log and '\nRH2_TEST_RC=1\n' in log
    # 两题原始 recipe 不同：17071 的 pytest/xdist 已在 requirements 内，不额外执行第三条安装。
    install_commands = ['python -m pip install -r test-requirements.txt', 'python -m pip install -e .']
    if iid == 'python__mypy-10424':
        install_commands.append('pip install pytest pytest-xdist')
    assert all(command in log for command in install_commands)
    diag = read(next(directory.glob('eval_logs/*.diagnostics.json')))
    assert diag['scripts_digest'] == grading_scripts_digest(spec)
    assert diag['grading_materials_identity'] == spec.grading_materials_identity == facts['grading_materials_identity']
    assert diag['git_sanitize']['facts'] == sanity and diag['git_sanitize']['state'] == 'verified'
    revision = spec.grading_revision.diagnostics(None)
    for key in ('environment_package_digest', 'public_bundle_digest', 'grading_bundle_digest', 'materials_identity', 'revision_id', 'registry_sha256'):
        assert diag['grading_revision'][key] == revision[key]
    for key, part in revision['partitions'].items():
        got = diag['grading_revision']['partitions'][key]
        assert got['references'] == part['references']
        for name in ('missing', 'skipped', 'unaccounted'):
            assert got['result'][name] == []
        assert set(got['result']['success']) == {n for n in part['references'] if expected[n] == 'PASSED'}
        assert set(got['result']['failure']) == {n for n in part['references'] if expected[n] == 'FAILED'}
    assert diag['control_surface']['RH2_PROTECT_OK'] == '1' and diag['control_surface']['MISSING_FILES_COUNT'] == '0'
    assert diag['candidate']['candidate_segment_completed'] and not diag['candidate']['log_partial']
    assert diag['candidate']['install_failed_commands'] == [] and diag['candidate']['test_rc'] == 1
    assert status['baseline_rebuild_passed'] and status['grade_invocations'] == 1 and status['exit_code'] == 0
    close = status['manager_close']
    assert close['containers_created_total'] == close['containers_removed_total'] == 1
    assert not close['containers_open'] and not close['supply_open'] and not close['cleanup_failures']
    tail = calls[-3:]
    assert tail[0][1]['argv'][0:2] == ['rm', '-f']
    for p, call in tail[1:]:
        assert 'label=rh2.run_id=' + status['run_id'] in call['argv']
        assert (p / 'stdout.full').read_bytes() == (p / 'stderr.full').read_bytes() == b''
    return {'task': iid, 'files_verified': files, 'started_at': status['started_at'], 'finished_at': status['finished_at'],
        'census_call': census_path.name, 'census_bytes': (census_path / 'stdout.full').stat().st_size, 'census_sha256': sha(census_path / 'stdout.full'),
        'baseline_all_fields_equal': True, 'entries': len(rebuilt.entries), 'excluded_paths_count': raw.count('EXCL\t'),
        'baseline_digest': compute_baseline_manifest_digest(rebuilt), 'excluded_digest': rebuilt.excluded_census_digest,
        'materialized_head': rebuilt.materialized_head, 'sanitizer_facts': sanity, 'states': states, 'collection': collection,
        'log_sha256': sha(logpath), 'log_bytes': logpath.stat().st_size, 'cleanup_confirmed': True}


if __name__ == '__main__':
    result = {'code_files_verified': verify_code(), 'rows': [verify_task(iid) for iid in sys.argv[1:]]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
