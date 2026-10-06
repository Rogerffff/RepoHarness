"""新宿主 UID／激活／工作区模块补查；原 production helper，非 CC 或模型尝试。"""
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
    config = json.loads((HERE / 'tasks.json').read_text())
    task = config['tasks']['getmoto__moto-' + ns.instance]
    release = ROOT / 'releases' / config['release_id']
    assert sha(release / 'manifest.json') == config['release_manifest_sha256']
    assert Path(sys.executable) == ROOT / 'runtime_cpu_v2/rh2/.venv/bin/python'
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

    summary_path = Path(ns.prepared_summary)
    assert summary_path.is_relative_to(ROOT / 'packages/swe_moto/moto_r13_v1')
    assert sha(summary_path) == ns.prepared_summary_sha256
    summary = json.loads(summary_path.read_text())
    assert summary['task_ids'] == [task['task_id']]
    out = ROOT / 'packages/swe_moto/moto_r13_uid_v1' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    assert profile.cpus == 2 and profile.memory_bytes == 4 * 1024**3 and profile.pids_limit == 512
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=profile,
        grader_profile=grader_profile_from_env(os.environ), artifacts_dir=out / 'unused', run_id=ns.job)
    view = ctx.rollout_views[task['task_id']]
    spec = rollout_spec_from_view(view, time_budget_seconds=300)
    assert spec.grading_spec is None and spec.image == task['original_actor_image']
    assert spec.base_commit == task['base_commit'] and view.public_bundle_digest == task['public_bundle_digest']
    assert view.environment_package_digest == task['environment_package_digest']
    calls = []

    async def docker(*args, input_bytes=None):
        result = await asyncio.wait_for(default_docker_runner(*args, input_bytes=input_bytes), timeout=300)
        calls.append({'argv': args, 'exit_code': result.exit_code, 'stdout': result.stdout, 'stderr': result.stderr})
        save(out / 'docker_calls.json', calls)
        return result

    name = 'rh2-' + ns.job
    record = {'job_id': ns.job, 'task_id': task['task_id'], 'scope': task['scope'],
        'release_manifest_sha256': config['release_manifest_sha256'], 'prepared_summary_sha256': ns.prepared_summary_sha256,
        'tools_manifest_sha256': sha(HERE / 'manifest.json'), 'original_actor_image': spec.image,
        'public_bundle_digest': view.public_bundle_digest, 'runtime_image_id': task['runtime_image_id'],
        'profile_digest': profile.digest(), 'actor_executed': False, 'model_attempts': 0, 'status': 'started'}
    try:
        recipe = task['environment']
        source_ref = recipe['source_image'].split(':')[0] + '@' + recipe['source_image_manifest_digest']
        inspected = await docker('image', 'inspect', source_ref, task['runtime_image_id'])
        assert inspected.exit_code == 0
        source, actual = json.loads(inspected.stdout)
        assert source['Id'] == recipe['source_config_id'] and source_ref in source['RepoDigests']
        assert actual['Id'] == task['runtime_image_id'] and actual['Architecture'] == 'amd64' and actual['Os'] == 'linux'
        if recipe.get('derived_image_id'):
            assert actual['Id'] == recipe['derived_image_id']
            assert actual['RootFS']['Layers'][:-1] == source['RootFS']['Layers']
            assert {'PIP_NO_INDEX=1', 'PIP_FIND_LINKS=/opt/rh2/build-wheels'}.issubset(actual['Config']['Env'])
        else:
            assert actual['Id'] == source['Id']
        save(out / 'image_inspect.json', {'source': source, 'actual': actual})
        launched = await docker(*profile.docker_run_args(name=name, network='none', image=task['runtime_image_id'],
            labels=('--label', 'rh2.run_id=' + ns.job)))
        assert launched.exit_code == 0
        record['sanitize'] = await run_git_sanitize(docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
        assert record['sanitize']['HEAD_AFTER'] == task['base_commit']
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
        identity_code = ('import hashlib,importlib,json,os,pathlib,sys,boto3,botocore,moto\n'
            'p=pathlib.Path(importlib.import_module(' + repr(task['module']) + ').__file__).resolve()\n'
            "print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'cwd':os.getcwd(),'home':os.environ.get('HOME'),'python':sys.executable,'prefix':sys.prefix,'moto_file':moto.__file__,'module_file':str(p),'module_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'boto3':boto3.__version__,'botocore':botocore.__version__}))")
        command = 'cd /testbed; PYTHONDONTWRITEBYTECODE=1 python -c ' + shlex.quote(identity_code)
        argv = ['exec', '--user', str(profile.agent_uid), '-e', 'HOME=/home/' + profile.agent_user]
        for key, value in env.items():
            argv.extend(['-e', key + '=' + value])
        result = await docker(*argv, name, 'bash', '-c', command)
        assert result.exit_code == 0
        record['identity'] = json.loads(result.stdout)
        identity = record['identity']
        assert identity['uid'] == 54321 and identity['gid'] == 54321 and identity['cwd'] == '/testbed' and identity['home'] == '/home/agent'
        assert identity['python'].startswith(spec.expected_interpreter_prefix + '/')
        assert identity['moto_file'].startswith('/testbed/') and identity['module_file'] == '/testbed/' + task['module_rel']
        assert identity['module_sha256'] == task['module_sha256']
        live = await docker('inspect', name)
        assert live.exit_code == 0
        container = json.loads(live.stdout)[0]
        host = container['HostConfig']
        record['actual_container'] = {k: host[k] for k in ('NanoCpus', 'Memory', 'PidsLimit', 'ShmSize', 'NetworkMode')}
        assert record['actual_container'] == {'NanoCpus': 2 * 10**9, 'Memory': 4 * 1024**3,
            'PidsLimit': 512, 'ShmSize': 64 * 1024**2, 'NetworkMode': 'none'}
        assert container['Image'] == task['runtime_image_id']
        record['status'] = 'new_host_identity_activation_import_passed_pending_independent_review'
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
        else:
            record['ownership_inspect_rc'] = ownership.exit_code
        remaining = await docker('ps', '-a', '--filter', 'label=rh2.run_id=' + ns.job, '--format', '{{.ID}}')
        networks = await docker('network', 'ls', '--filter', 'label=rh2.run_id=' + ns.job, '--format', '{{.ID}}')
        record['cleanup'] = {'container_query_rc': remaining.exit_code, 'containers': remaining.stdout.split(),
            'network_query_rc': networks.exit_code, 'networks': networks.stdout.split()}
        save(out / 'result.json', record)
        assert remaining.exit_code == networks.exit_code == 0 and not remaining.stdout.strip() and not networks.stdout.strip()
    print(json.dumps({'job_id': ns.job, 'status': record['status'], 'cleanup': record['cleanup']}), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance', choices=('5960', '6408', '6185', '7584'), required=True)
    parser.add_argument('--job', required=True)
    parser.add_argument('--prepared-summary', required=True)
    parser.add_argument('--prepared-summary-sha256', required=True)
    ns = parser.parse_args()
    assert re.fullmatch('moto' + ns.instance + r'-uid-[0-9a-f]{12}', ns.job)
    assert not any(os.environ.get(k) for k in ('RH2_IMAGE_OVERLAYS_PATH', 'RH2_IMAGE_OVERLAYS_SHA256'))
    asyncio.run(run(ns))


if __name__ == '__main__':
    main()
