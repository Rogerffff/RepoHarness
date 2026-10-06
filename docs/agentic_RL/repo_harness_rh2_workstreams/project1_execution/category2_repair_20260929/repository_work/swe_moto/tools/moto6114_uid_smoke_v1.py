"""补新宿主 actor UID／激活／导入条件；复用原 CC 开发证据，不运行模型或评分。"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path('/work/rh2-category2-20261003')
RELEASE = ROOT / 'releases/cat2-cpu-r2e088-swe12-git-20261003-v1'
IMAGE = 'sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5'
BASE = 'f01709f9ba656e7cf4399bcd1a0a07fd134b0aec'
TID = 'swe_gym_lite::getmoto__moto-6114'
sys.path.insert(0, str(RELEASE / 'repo/rh2/src'))


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str) + '\n')


async def run(ns):
    from repoharness2.adapters.slime.replay_grade import load_context
    from repoharness2.adapters.slime.prepared_task_face import rollout_spec_from_view
    from repoharness2.adapters.slime.sandbox_profile import (default_docker_runner, rollout_profile_from_env,
        grader_profile_from_env, run_git_sanitize, run_trusted_init, rollout_trusted_init_script,
        agent_shell_env, run_rollout_activation_check)
    out = ROOT / 'packages/swe_moto/moto6114_host_identity' / ns.job
    out.mkdir(parents=True, exist_ok=False)
    summary_path = Path(ns.prepared_summary)
    assert hashlib.sha256(summary_path.read_bytes()).hexdigest() == ns.prepared_summary_sha256
    summary = json.loads(summary_path.read_text())
    profile = rollout_profile_from_env(os.environ, model_proxy_upstream_host='127.0.0.1', model_proxy_upstream_port=1)
    assert profile.cpus == 2 and profile.memory_bytes == 4*1024**3 and profile.pids_limit == 512
    ctx = load_context(prepared_dir=summary['prepared_dir'], private_dir=summary['private_dir'],
        manifest_sha256=summary['prepared_manifest_sha256'], rollout_profile=profile,
        grader_profile=grader_profile_from_env(os.environ), artifacts_dir=out/'unused', run_id=ns.job)
    view = ctx.rollout_views[TID]
    spec = rollout_spec_from_view(view, time_budget_seconds=300)
    assert view.public.base_commit == BASE and view.public_bundle_digest == 'sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2'
    assert spec.grading_spec is None
    calls = []

    async def docker(*args, input_bytes=None):
        result = await asyncio.wait_for(default_docker_runner(*args, input_bytes=input_bytes), timeout=300)
        calls.append({'argv':args, 'exit_code':result.exit_code, 'stdout':result.stdout, 'stderr':result.stderr})
        save(out/'docker_calls.json', calls)
        return result

    name = 'rh2-' + ns.job
    record = {'scope':'new-host actor UID/activation/import only; no CC, model, baseline export or grader',
        'task_id':TID, 'job_id':ns.job, 'prepared_summary_sha256':ns.prepared_summary_sha256,
        'public_bundle_digest':view.public_bundle_digest, 'environment_package_digest':view.environment_package_digest,
        'runtime_image_id':IMAGE, 'container_name':name, 'profile_digest':profile.digest(),
        'activation_script_sha256':hashlib.sha256(spec.env_activation_script.encode()).hexdigest()}
    try:
        inspect = await docker('image','inspect',IMAGE)
        assert inspect.exit_code == 0 and json.loads(inspect.stdout)[0]['Id'] == IMAGE
        launched = await docker(*profile.docker_run_args(name=name, network='none', image=IMAGE,
                                             labels=('--label','rh2.run_id='+ns.job)))
        assert launched.exit_code == 0
        record['sanitize'] = await run_git_sanitize(docker, name=name, workdir=spec.workdir, timeout=profile.sanitize_timeout_seconds)
        assert record['sanitize']['HEAD_AFTER'] == BASE
        record['init'] = await run_trusted_init(docker, name=name, script=rollout_trusted_init_script(profile), timeout=profile.init_timeout_seconds)
        # 与生产 actor 一样写 root 所有的激活文件；仅在这个独占容器中操作。
        from repoharness2.envpack.materialize import BASH_ENV_PATH
        write = await docker('exec','-i',name,'bash','-c',
            'mkdir -p /rh2 && cat > '+BASH_ENV_PATH+' && chmod 0644 '+BASH_ENV_PATH,
            input_bytes=spec.env_activation_script.encode())
        assert write.exit_code == 0
        env = agent_shell_env(profile, activation_file=BASH_ENV_PATH)
        activation = await run_rollout_activation_check(docker,name=name,profile=profile,env=env,
                                                        expected_interpreter_prefix=spec.expected_interpreter_prefix)
        record['activation'] = activation.to_dict()
        assert activation.ok
        command = "cd /testbed; PYTHONDONTWRITEBYTECODE=1 python - <<'PY_ID'\nimport hashlib,json,os,sys,pathlib,boto3,botocore,moto,moto.rds.models\np=pathlib.Path(moto.rds.models.__file__).resolve()\nprint(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'cwd':os.getcwd(),'python':sys.executable,'prefix':sys.prefix,'moto_file':moto.__file__,'moto_rds_file':str(p),'moto_rds_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'boto3':boto3.__version__,'botocore':botocore.__version__}))\nPY_ID"
        argv = ['exec','--user',str(profile.agent_uid),'-e','HOME=/home/'+profile.agent_user]
        for key,value in env.items():
            argv += ['-e',key+'='+value]
        result = await docker(*argv,name,'bash','-c',command)
        record['identity_rc'] = result.exit_code
        assert result.exit_code == 0
        record['identity'] = json.loads(result.stdout)
        assert record['identity']['uid'] == 54321 and record['identity']['cwd'] == '/testbed'
        assert record['identity']['python'] == '/opt/miniconda3/envs/testbed/bin/python'
        assert record['identity']['moto_rds_file'] == '/testbed/moto/rds/models.py'
        assert record['identity']['moto_rds_sha256'] == 'a614a137f21dce20445cad98611e578b435d4f09a592ced584d887d9edb9250c'
        host = await docker('inspect',name)
        config = json.loads(host.stdout)[0]
        record['actual_container'] = {key:config['HostConfig'][key] for key in ['NanoCpus','Memory','PidsLimit','ShmSize']}
        record['actual_image_id'] = config['Image']
        assert record['actual_container']['NanoCpus'] == 2000000000 and record['actual_container']['Memory'] == 4294967296
        record['status'] = 'new_host_actor_identity_passed_pending_historical_reuse_review'
    finally:
        ownership = await docker('inspect',name)
        if ownership.exit_code == 0:
            labels = json.loads(ownership.stdout)[0]['Config']['Labels'] or {}
            assert labels.get('rh2.run_id') == ns.job, '不删除不同归属的同名容器'
            remove = await docker('rm','-f',name)
            record['remove_rc'] = remove.exit_code
        else:
            record['remove_rc'] = None
            record['ownership_inspect_rc'] = ownership.exit_code
        remaining = await docker('ps','-a','--filter','label=rh2.run_id='+ns.job,'--format','{{.ID}}')
        networks = await docker('network','ls','--filter','label=rh2.run_id='+ns.job,'--format','{{.ID}}')
        record['cleanup'] = {'container_query_rc':remaining.exit_code,'containers':remaining.stdout.split(),
            'network_query_rc':networks.exit_code,'networks':networks.stdout.split()}
        save(out/'result.json',record)
        assert remaining.exit_code == networks.exit_code == 0 and not remaining.stdout.strip() and not networks.stdout.strip()
    print(json.dumps({'job':ns.job,'status':record['status'],'identity':record['identity'],'cleanup':record['cleanup']}),flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--job',required=True)
    parser.add_argument('--prepared-summary',required=True)
    parser.add_argument('--prepared-summary-sha256',required=True)
    ns = parser.parse_args()
    assert re.fullmatch(r'moto6114-uid-[0-9a-f]{12}',ns.job)
    assert Path(ns.prepared_summary).is_relative_to(ROOT/'packages/swe_moto/moto6114_r7')
    return asyncio.run(run(ns))


if __name__ == '__main__':
    main()
