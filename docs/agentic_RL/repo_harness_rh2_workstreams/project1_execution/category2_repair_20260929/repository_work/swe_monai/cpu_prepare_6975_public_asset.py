"""6975 官方公开 NIfTI 的 COPY-only 修复；必须在本包 cpu_slot prepare 内执行。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import time

ASSET_SHA = 'c01a50caa7a563158ecda43d93a1466bfc8aa939bc16b06452ac1089c54661c8'
SOURCE = ('xingyaoww/sweb.eval.x86_64.project-monai_s_monai-6975@sha256:'
          '0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055')
BASE_COMMIT = '392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'base-job', 'actor-job', 'asset', 'job', 'out'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    for value in (args.base_job, args.actor_job, args.job):
        if not re.fullmatch(r'[a-z0-9][a-z0-9_.-]{0,100}', value):
            parser.error('invalid job id')
    root = Path(args.root).resolve()
    package = root / 'packages/swe_monai'
    out, asset = Path(args.out).resolve(), Path(args.asset).resolve()
    assert out.is_relative_to(package / 'outputs') and asset.is_relative_to(package)
    assert sha(asset) == ASSET_SHA
    base_dir = package / 'outputs' / args.base_job
    base = json.loads((base_dir / 'preparation.json').read_text())
    assert base['task'] == '6975' and base['source_image'] == SOURCE
    assert base['status'] == 'image_prepared_not_task_accepted'
    assert base['source_identity']['head'] == BASE_COMMIT
    assert base['cleanup'] == {'rm_rc': 0, 'query_rc': 0, 'remaining': []}
    actor_dir = package / 'outputs' / args.actor_job
    actor = json.loads((actor_dir / 'attempt.json').read_text())
    assert actor['image'] == base['actual_image_id'] and actor['harness_exit_code'] == 0
    assert actor['cleanup']['container_rm'] == actor['cleanup']['stub_rc'] == 0
    assert not actor['cleanup']['residual_after_force']
    original = (actor_dir / 'captures/public_nifti_original.out').read_text()
    observation = json.loads(next(line.removeprefix('PUBLIC_NIFTI_FILE ')
                                 for line in original.splitlines()
                                 if line.startswith('PUBLIC_NIFTI_FILE ')))
    assert observation == {'path': 'tests/testing_data/ref_avg152T1_LR.nii.gz', 'exists': False}
    assert 'AssertionError: public example NIfTI asset missing' in original
    out.mkdir(parents=True, exist_ok=False)
    state = {'schema': 'monai.public_asset_image_preparation.v1', 'task': '6975',
             'job': args.job, 'status': 'preparing', 'steps': [], 'started_at': time.time(),
             'source_image': SOURCE, 'base_job': args.base_job, 'missing_actor_job': args.actor_job,
             'base_receipt_sha256': sha(base_dir / 'preparation.json'),
             'actor_receipt_sha256': sha(actor_dir / 'attempt.json'),
             'asset_sha256': ASSET_SHA, 'script_sha256': sha(__file__),
             'scope': 'COPY-only official public fixture; no source/test/dependency/prompt repair',
             'actor_verified': False, 'new_test_executed': False, 'formal_acceptance_passed': False}
    child = None
    container = 'rh2-swe-monai-' + args.job

    def save():
        temporary = out / 'preparation.json.tmp'
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n')
        temporary.replace(out / 'preparation.json')

    def stop_child():
        nonlocal child
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        child = None

    def interrupted(signum, _frame):
        stop_child()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)

    def run(name, command, seconds=120):
        nonlocal child
        start = time.time()
        path = out / (name + '.log')
        with path.open('xb') as stream:
            child = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                     start_new_session=True)
            try:
                rc = child.wait(timeout=seconds)
            finally:
                stop_child()
        state['steps'].append({'name': name, 'command': command, 'rc': rc,
                               'seconds': time.time() - start, 'log_sha256': sha(path)})
        save()
        if rc:
            raise RuntimeError(name + ' nonzero: ' + str(rc))
        return path

    try:
        save()
        base_log = run('base_inspect', ['docker', 'image', 'inspect', SOURCE])
        facts = json.loads(base_log.read_text())[0]
        assert facts['Id'] == base['actual_image_id'] and SOURCE in facts['RepoDigests']
        assert facts['Os'] == 'linux' and facts['Architecture'] == 'amd64'
        build = out / 'build'
        build.mkdir()
        copied = build / 'ref_avg152T1_LR.nii.gz'
        copied.write_bytes(asset.read_bytes())
        copied.chmod(0o444)
        dockerfile = build / 'Dockerfile'
        dockerfile.write_text('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\n'
                              'COPY ref_avg152T1_LR.nii.gz /testbed/tests/testing_data/ref_avg152T1_LR.nii.gz\n')
        tag = 'rh2-category2-20261003/swe-monai-6975-public-asset:' + args.job
        run('build', ['docker', 'build', '--pull=false', '--network=none', '--build-arg',
                      'BASE_IMAGE=' + SOURCE, '--label', 'rh2.package=swe_monai', '--label',
                      'rh2.run_id=' + args.job, '-t', tag, str(build)], 1800)
        derived_log = run('derived_inspect', ['docker', 'image', 'inspect', tag])
        derived = json.loads(derived_log.read_text())[0]
        layers = facts['RootFS']['Layers']
        assert derived['RootFS']['Layers'][:len(layers)] == layers
        assert len(derived['RootFS']['Layers']) == len(layers) + 1
        state.update(base_image_id=facts['Id'], actual_image_id=derived['Id'], tag=tag,
                     dockerfile_sha256=sha(dockerfile), source_layer_prefix_verified=True)
        probe = '''import os,json,hashlib,subprocess,nibabel
from pathlib import Path
p=Path('/testbed/tests/testing_data/ref_avg152T1_LR.nii.gz')
paths=json.loads(__import__('sys').argv[1])
print(json.dumps({'uid':os.getuid(),'asset_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
 'nifti_shape':list(nibabel.load(str(p)).shape),'asset_readable':os.access(p,os.R_OK),
 'head':subprocess.check_output(['git','-c','safe.directory=/testbed','rev-parse','HEAD'],text=True).strip(),
 'porcelain':subprocess.check_output(['git','-c','safe.directory=/testbed','status','--porcelain'],text=True),
 'source_sha256':{x:hashlib.sha256(Path(x).read_bytes()).hexdigest() for x in paths}}))
'''
        run('create_identity', ['docker', 'create', '--name', container, '--network', 'none',
                               '--cpus', '2', '--memory', '4g', '--pids-limit', '512',
                               '--label', 'rh2.run_id=' + args.job, '--label', 'rh2.package=swe_monai',
                               '--user', '54321:54321', '--workdir', '/testbed',
                               '--env', 'PYTHONDONTWRITEBYTECODE=1',
                               '--entrypoint', '/opt/miniconda3/envs/testbed/bin/python',
                               derived['Id'], '-I', '-B', '-c', probe,
                               json.dumps(list(base['source_identity']['source_sha256']))])
        inspect = json.loads(run('container_inspect', ['docker', 'inspect', container]).read_text())[0]
        config = inspect['HostConfig']
        assert inspect['Image'] == derived['Id'] and inspect['Config']['User'] == '54321:54321'
        assert config['NanoCpus'] == 2000000000 and config['Memory'] == 4294967296
        assert config['PidsLimit'] == 512 and config['NetworkMode'] == 'none'
        output = run('source_identity', ['docker', 'start', '-a', container], 600)
        identity = json.loads(output.read_text())
        assert identity['uid'] == 54321 and identity['head'] == BASE_COMMIT
        assert identity['asset_readable'] and identity['asset_sha256'] == ASSET_SHA
        assert identity['nifti_shape'] == [91, 109, 91]
        assert identity['source_sha256'] == base['source_identity']['source_sha256']
        assert identity['porcelain'] == base['source_identity']['porcelain']
        state.update(source_identity=identity, status='image_prepared_not_task_accepted')
    except BaseException as exc:
        state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        stop_child()
        removal = subprocess.run(['docker', 'rm', '-f', container], text=True, capture_output=True, timeout=120)
        query = subprocess.run(['docker', 'ps', '-aq', '--filter', 'label=rh2.run_id=' + args.job],
                               text=True, capture_output=True, timeout=120)
        (out / 'cleanup_removal.log').write_text(removal.stdout + removal.stderr)
        (out / 'cleanup_query.log').write_text(query.stdout + query.stderr)
        state['cleanup'] = {'rm_rc': removal.returncode, 'query_rc': query.returncode,
                            'remaining': query.stdout.split()}
        state['finished_at'] = time.time()
        save()
        if state['status'] == 'image_prepared_not_task_accepted':
            assert removal.returncode == query.returncode == 0 and not query.stdout.strip()


if __name__ == '__main__':
    main()
