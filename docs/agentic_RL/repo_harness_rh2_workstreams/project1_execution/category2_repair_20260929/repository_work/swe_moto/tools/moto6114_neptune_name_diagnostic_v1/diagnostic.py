"""复用 R7 production 初始化，两容器两条公开 base/candidate 反例。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import shlex
import sys
from pathlib import Path

ROOT = Path('/work/rh2-category2-20261003')
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


async def run(ns):
    manifest = json.loads((HERE / 'manifest.json').read_text())
    assert {p.name for p in HERE.iterdir()} == set(manifest['files']) | {'manifest.json'}
    for name, pin in manifest['files'].items():
        p = HERE / name
        assert p.is_file() and not p.is_symlink() and sha(p) == pin['sha256'] and p.stat().st_size == pin['bytes']
    cfg = json.loads((HERE / 'config.json').read_text())
    release = ROOT / 'releases' / cfg['release_id']
    assert sha(release / 'manifest.json') == cfg['release_manifest_sha256']
    assert Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python'
    summary_path = Path(cfg['prepared_binding']['prepared_summary'])
    assert summary_path.is_relative_to(ROOT / 'packages/swe_moto/moto6114_r7')
    assert sha(summary_path) == cfg['prepared_binding']['prepared_summary_sha256']
    summary = json.loads(summary_path.read_text())
    assert summary['task_ids'] == [cfg['task_id']]
    sys.path.insert(0, str(release / 'repo/rh2/src'))
    from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.sandbox_profile import (
        agent_shell_env,
        default_docker_runner,
        grader_profile_from_env,
        rollout_profile_from_env,
        rollout_trusted_init_script,
        run_git_sanitize,
        run_rollout_activation_check,
        run_trusted_init,
    )
    from repoharness2.envpack.materialize import BASH_ENV_PATH
    out = ROOT / 'packages/swe_moto/moto6114_neptune_name_diagnostic_v1' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    assert profile.cpus == 2 and profile.memory_bytes == 4 * 1024**3 and profile.pids_limit == 512
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=profile,
        grader_profile=grader_profile_from_env(os.environ), artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[cfg['task_id']]
    spec = rollout_spec_from_view(view, time_budget_seconds=300)
    assert spec.grading_spec is None and spec.base_commit == cfg['base_commit']
    assert view.public_bundle_digest == cfg['public_bundle_digest']
    calls, rows = [], []

    async def docker(*args, input_bytes=None):
        result = await asyncio.wait_for(default_docker_runner(*args, input_bytes=input_bytes), timeout=300)
        calls.append({'argv': args, 'exit_code': result.exit_code, 'stdout': result.stdout, 'stderr': result.stderr})
        save(out / 'docker_calls.json', calls)
        return result

    inspected = await docker('image', 'inspect', cfg['source_manifest_ref'], cfg['runtime_image_id'])
    assert inspected.exit_code == 0
    source, actual = json.loads(inspected.stdout)
    assert source['Id'] == cfg['source_actual_id'] and cfg['source_manifest_ref'] in source['RepoDigests']
    assert actual['Id'] == cfg['runtime_image_id'] and actual['RootFS']['Layers'][:-1] == source['RootFS']['Layers']
    assert actual['Architecture'] == 'amd64' and actual['Os'] == 'linux'
    save(out / 'image_inspect.json', {'source': source, 'actual': actual})
    for arm in ('base', 'candidate'):
        name = 'rh2-' + ns.job + '-' + arm
        record = {'arm': arm, 'job_id': ns.job, 'status': 'started', 'raw_reward': None}
        try:
            launched = await docker(*profile.docker_run_args(name=name, network='none', image=cfg['runtime_image_id'],
                labels=('--label', 'rh2.run_id=' + ns.job)))
            assert launched.exit_code == 0
            record['sanitize'] = await run_git_sanitize(docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
            assert record['sanitize']['HEAD_AFTER'] == cfg['base_commit']
            record['init'] = await run_trusted_init(docker, name=name, script=rollout_trusted_init_script(profile), timeout=profile.init_timeout_seconds)
            written = await docker('exec', '-i', name, 'bash', '-c',
                'mkdir -p /rh2 && cat > ' + BASH_ENV_PATH + ' && chmod 0644 ' + BASH_ENV_PATH,
                input_bytes=spec.env_activation_script.encode())
            assert written.exit_code == 0
            env = agent_shell_env(profile, activation_file=BASH_ENV_PATH)
            activation = await run_rollout_activation_check(docker, name=name, profile=profile, env=env,
                expected_interpreter_prefix=spec.expected_interpreter_prefix)
            record['activation'] = activation.to_dict()
            assert activation.ok
            # 修改前两臂原源码必须相同；候选只重放实际模型的唯一源码 entry。
            checked = await docker('exec', name, 'sha256sum', '/testbed/moto/rds/models.py', '/testbed/moto/neptune/models.py')
            assert checked.exit_code == 0
            assert checked.stdout.splitlines() == [cfg['base_rds_sha256'] + '  /testbed/moto/rds/models.py',
                cfg['base_neptune_sha256'] + '  /testbed/moto/neptune/models.py']
            if arm == 'candidate':
                candidate = HERE / 'candidate_rds_models.py'
                assert sha(candidate) == cfg['candidate_sha256'] and candidate.stat().st_size == cfg['candidate_bytes']
                applied = await docker('exec', '-i', name, 'bash', '-c',
                    'cat > /testbed/moto/rds/models.py && chmod 0644 /testbed/moto/rds/models.py',
                    input_bytes=candidate.read_bytes())
                assert applied.exit_code == 0
            identity = await docker('inspect', name)
            assert identity.exit_code == 0
            live = json.loads(identity.stdout)[0]
            record['actual_image_id'] = live['Image']
            record['actual_profile'] = {k: live['HostConfig'][k] for k in ('NanoCpus', 'Memory', 'PidsLimit', 'ShmSize', 'NetworkMode')}
            assert record['actual_image_id'] == cfg['runtime_image_id']
            assert record['actual_profile'] == {'NanoCpus': 2000000000, 'Memory': 4294967296,
                'PidsLimit': 512, 'ShmSize': 67108864, 'NetworkMode': 'none'}
            argv = ['exec', '-i', '--user', str(profile.agent_uid), '-e', 'HOME=/home/' + profile.agent_user]
            for key, value in env.items():
                argv.extend(['-e', key + '=' + value])
            command = 'cd /testbed; PYTHONDONTWRITEBYTECODE=1 python -c ' + shlex.quote((HERE / 'probe.py').read_text())
            observed = await docker(*argv, name, 'bash', '-c', command)
            record['probe_exit_code'] = observed.exit_code
            assert observed.exit_code == 0
            data = json.loads(observed.stdout)
            record['observed'] = data
            assert data['uid'] == data['gid'] == 54321 and data['cwd'] == '/testbed' and data['home'] == '/home/agent'
            assert data['python'] == '/opt/miniconda3/envs/testbed/bin/python' and data['moto_file'].startswith('/testbed/')
            assert data['rds_file'] == '/testbed/moto/rds/models.py' and data['neptune_file'] == '/testbed/moto/neptune/models.py'
            assert data['rds_sha256'] == cfg['base_rds_sha256' if arm == 'base' else 'candidate_sha256']
            assert data['neptune_sha256'] == cfg['base_neptune_sha256']
            record['status'] = 'observations_returned'
        except BaseException as error:
            record.update(status='failed', error_type=type(error).__name__)
            raise
        finally:
            ownership = await docker('inspect', name)
            if ownership.exit_code == 0:
                assert (json.loads(ownership.stdout)[0]['Config']['Labels'] or {}).get('rh2.run_id') == ns.job
                removed = await docker('rm', '-f', name)
                record['remove_rc'] = removed.exit_code
                assert removed.exit_code == 0
            remaining = await docker('ps', '-a', '--filter', 'label=rh2.run_id=' + ns.job, '--format', '{{.ID}}')
            networks = await docker('network', 'ls', '--filter', 'label=rh2.run_id=' + ns.job, '--format', '{{.ID}}')
            record['cleanup'] = {'container_query_rc': remaining.exit_code, 'containers': remaining.stdout.split(),
                'network_query_rc': networks.exit_code, 'networks': networks.stdout.split()}
            save(out / (arm + '.json'), record)
            assert remaining.exit_code == networks.exit_code == 0 and not remaining.stdout.strip() and not networks.stdout.strip()
        rows.append(record)
    save(out / 'observations.json', {'job_id': ns.job, 'scope': cfg['cpu_job_scope'], 'rows': rows,
        'original_gpu_reward_changed': False, 'grading_executed': False, 'model_attempts': 0, 'reference_list_changed': False})
    original, candidate = [r['observed']['cases'] for r in rows]
    assert all(c['before_status'] == 'available' and c['present_before'] for c in original + candidate)
    assert original[0]['outcome'] == 'returned' and original[0]['returned_status'] == 'started' and original[0]['present_after']
    assert original[1]['outcome'] == 'returned' and original[1]['present_after'] is False
    assert candidate[0]['outcome'] == 'exception' and candidate[0]['exception_type'] == 'InvalidDBClusterStateFault'
    assert candidate[1]['outcome'] == 'exception' and candidate[1]['exception_type'] == 'AttributeError'
    assert all(c['present_after'] for c in candidate)
    save(out / 'result.json', {'job_id': ns.job, 'status': 'two_original_name_delegation_regressions_confirmed',
        'tools_manifest_sha256': sha(HERE / 'manifest.json'), 'formal_cpu_accepted': False, 'raw_reward_override': None})
    print(json.dumps({'job_id': ns.job, 'status': 'two_original_name_delegation_regressions_confirmed'}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job', required=True)
    ns = parser.parse_args()
    assert re.fullmatch(r'moto6114-neptune-[0-9a-f]{12}', ns.job)
    assert not any(os.environ.get(k) for k in ('RH2_IMAGE_OVERLAYS_PATH', 'RH2_IMAGE_OVERLAYS_SHA256'))
    asyncio.run(run(ns))


if __name__ == '__main__':
    main()
