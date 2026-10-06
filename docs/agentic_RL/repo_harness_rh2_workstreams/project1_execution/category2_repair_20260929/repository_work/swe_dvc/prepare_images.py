"""只准备 DVC 公开依赖镜像；经 cpu_slot.py --mode prepare 调用。

不复制 gold、私有测试或正式评分材料。容器有资源限制，退出时只清理本次标签。
每次输入/输出目录不可覆盖。正式源码与材料仍由共用发布者冻结。
"""
from __future__ import annotations
import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
import urllib.request
import zipfile

PYTHON = '/opt/miniconda3/envs/testbed/bin/python'


def networkx_compatibility(source, destination):
    # 复用 E13 的确切 gcd 修法。新wheel的容器格式SHA单独记录，不冒用旧wheel身份。
    replacement = b'''from math import gcd as _math_gcd


def gcd(a, b):
    if type(a) is int is type(b):
        return -_math_gcd(a, b) if (b or a) < 0 else _math_gcd(a, b)
    while b:
        a, b = b, a % b
    return a
'''
    with zipfile.ZipFile(source) as archive:
        data = {n: archive.read(n) for n in archive.namelist() if not n.endswith('/')}
    dag = 'networkx/algorithms/dag.py'
    before = data[dag]
    assert before.count(b'from fractions import gcd') == 1
    data[dag] = before.replace(b'from fractions import gcd', replacement)
    old, new = 'networkx-2.3.dist-info/', 'networkx-2.3+rh2.1.dist-info/'
    metadata = data.pop(old + 'METADATA')
    assert b'Version: 2.3\n' in metadata
    data[new + 'METADATA'] = metadata.replace(b'Version: 2.3\n', b'Version: 2.3+rh2.1\n', 1)
    data = {n.replace(old, new): v for n, v in data.items() if not n.endswith('/RECORD')}
    record = io.StringIO(); writer = csv.writer(record, lineterminator='\n')
    for name, value in sorted(data.items()):
        writer.writerow([name, 'sha256=' + base64.urlsafe_b64encode(hashlib.sha256(value).digest()).decode().rstrip('='), len(value)])
    writer.writerow([new + 'RECORD', '', '']); data[new + 'RECORD'] = record.getvalue().encode()
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, value in sorted(data.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 19, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, value)
    return {'scope': 'E13 dependency compatibility; no DVC/test edits',
            'upstream_wheel_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'wheel_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(),
            'dag_before_sha256': hashlib.sha256(before).hexdigest(),
            'dag_after_sha256': hashlib.sha256(data[dag]).hexdigest(),
            'source_replacement': replacement.decode(), 'metadata_version': '2.3+rh2.1'}


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('plan')
    parser.add_argument('--out', required=True)
    parser.add_argument('--attempt', required=True)
    args = parser.parse_args()
    plan = json.loads(Path(args.plan).read_text())
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    label = 'rh2.swe_dvc.attempt=' + args.attempt
    state = {'purpose': 'public_dependency_preparation_only', 'started_at': time.time(),
             'plan_sha256': hashlib.sha256(Path(args.plan).read_bytes()).hexdigest(),
             'resources': {'cpus': 2, 'memory': '4g', 'pids': 512}, 'results': []}
    with (out / 'commands.log').open('w') as log:
        def run(cmd, *, timeout=600, optional=False, env=None):
            log.write('$ ' + shlex.join(cmd) + '\n'); log.flush()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            log.write(result.stdout + result.stderr + '\nRC=' + str(result.returncode) + '\n'); log.flush()
            if result.returncode and not optional:
                raise RuntimeError('command failed (see commands.log): ' + cmd[0])
            return result

        def inside(image, command, *, mount=None, network='none', optional=False):
            cmd = ['docker', 'run', '--rm', '--init', '--cpus', '2', '--memory', '4g',
                   '--pids-limit', '512', '--label', label, '--network', network]
            if mount:
                cmd += ['-v', mount]
            cmd += ['--entrypoint', 'bash', image, '-c', command]
            return run(cmd, optional=optional)

        try:
            for item in plan:
                directory = out / item['instance_id']
                wheels = directory / 'context/wheels'
                wheels.mkdir(parents=True)
                image = item['base_ref']
                run(['docker', 'pull', '--platform', 'linux/amd64', image], timeout=3600)
                base = json.loads(run(['docker', 'image', 'inspect', image]).stdout)[0]
                if base['Id'] != item['base_id']:
                    raise RuntimeError('base config identity mismatch')
                before = inside(image, f'{PYTHON} -I -m pip freeze --all').stdout
                source = inside(image, 'cd /testbed && git rev-parse HEAD && git status --porcelain && git diff --binary').stdout
                if source.splitlines()[0] != item['base_commit']:
                    raise RuntimeError('source base commit mismatch')
                download = shlex.join([PYTHON, '-I', '-m', 'pip', 'download', '--index-url', 'https://pypi.org/simple',
                                      '--no-deps', '--only-binary=:all:', '-d', '/wheels', *item['pins']])
                inside(image, download, mount=str(wheels.resolve()) + ':/wheels', network='bridge')
                hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(wheels.glob('*.whl'))}
                if hashes != item['expected_wheels']:
                    raise RuntimeError('wheel filename/hash differs from historical evidence')
                compatibility = None
                if item.get('networkx_compat_source'):
                    source_info = item['networkx_compat_source']
                    archive_source = wheels / 'networkx-2.3.zip'
                    with urllib.request.urlopen(source_info['url'], timeout=120) as response:
                        archive_source.write_bytes(response.read())
                    if hashlib.sha256(archive_source.read_bytes()).hexdigest() != source_info['sha256']:
                        raise RuntimeError('networkx source archive identity mismatch')
                    inside(image, shlex.join([PYTHON, '-I', '-m', 'pip', 'wheel', '--no-index', '--no-deps',
                                             '--no-build-isolation', '-w', '/wheels', '/wheels/networkx-2.3.zip']),
                           mount=str(wheels.resolve()) + ':/wheels')
                    upstream = wheels / 'networkx-2.3-py2.py3-none-any.whl'
                    compatible = wheels / 'networkx-2.3+rh2.1-py2.py3-none-any.whl'
                    compatibility = networkx_compatibility(upstream, compatible)
                    archive_source.rename(directory / archive_source.name)
                    upstream.rename(directory / upstream.name)
                    hashes[compatible.name] = compatibility['wheel_sha256']
                    dump(directory / 'networkx_compatibility.json', compatibility)
                dockerfile = ('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\n'
                              f'RUN {PYTHON} -I -m pip install --no-index --no-deps /opt/rh2/build-wheels/*.whl\n'
                              'ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n')
                (directory / 'context/Dockerfile').write_text(dockerfile)
                tag = 'rh2-swe-dvc/' + item['instance_id'].replace('__', '-') + ':' + args.attempt
                run(['docker', 'build', '--force-rm', '--pull=false', '--memory', '4g', '--cpu-period', '100000',
                     '--cpu-quota', '200000', '--build-arg', 'BASE_IMAGE=' + image,
                     '-t', tag, str(directory / 'context')], timeout=1800,
                    env=dict(os.environ, DOCKER_BUILDKIT='0'))
                built = json.loads(run(['docker', 'image', 'inspect', tag]).stdout)[0]
                if built['RootFS']['Layers'][:len(base['RootFS']['Layers'])] != base['RootFS']['Layers']:
                    raise RuntimeError('base layers not retained')
                after = inside(built['Id'], f'{PYTHON} -I -m pip freeze --all').stdout
                source_after = inside(built['Id'], 'cd /testbed && git rev-parse HEAD && git status --porcelain && git diff --binary').stdout
                if source_after != source:
                    raise RuntimeError('dependency build changed source worktree')
                pip_check = inside(built['Id'], f'{PYTHON} -I -m pip check', optional=True)
                rec = dict(item, image_id=built['Id'], tag=tag, wheels=hashes, compatibility=compatibility,
                           dockerfile_sha256=hashlib.sha256(dockerfile.encode()).hexdigest(),
                           base_layers_preserved=True, source_worktree_unchanged=True,
                           freeze_before=before.splitlines(), freeze_after=after.splitlines(),
                           pip_check_rc=pip_check.returncode, pip_check_output=pip_check.stdout + pip_check.stderr)
                (directory / 'source_worktree_before.txt').write_text(source)
                dump(directory / 'image.json', rec)
                state['results'].append(rec)
                dump(out / 'summary.json', state)
                print(item['instance_id'], built['Id'], 'pip_check_rc=' + str(pip_check.returncode), flush=True)
            state['status'] = 'prepared_not_qualified'
        except BaseException as exc:
            state.update(status='preparation_failed', error=str(exc))
            raise
        finally:
            remaining = run(['docker', 'ps', '-aq', '--filter', 'label=' + label], optional=True).stdout.split()
            if remaining:
                run(['docker', 'rm', '-f', *remaining], optional=True)
            residual = run(['docker', 'ps', '-aq', '--filter', 'label=' + label], optional=True).stdout.split()
            state.update(finished_at=time.time(), remaining_containers=residual)
            dump(out / 'summary.json', state)
            if residual:
                raise RuntimeError('own container cleanup incomplete')


if __name__ == '__main__':
    main()
