"""DVC 草案的私有 pytest 诊断。不是 RH2 正式评分，不生成 reward。

经 cpu_slot.py --mode run 启动；一个作业内串行执行各候选，每个候选用全新受限容器。
不改共享发布版本。完整日志和 pytest RC 保留，预期失败不会被改记为通过。
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import time

PYTHON = '/opt/miniconda3/envs/testbed/bin/python'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('material_dir')
    p.add_argument('--image-record', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--attempt', required=True)
    p.add_argument('--versions', nargs='+', choices=['original', 'effective'], default=['original', 'effective'])
    args = p.parse_args()
    materials = Path(args.material_dir).resolve()
    revision = json.loads((materials / 'revision.json').read_text())
    image = json.loads(Path(args.image_record).read_text())
    assert image['base_commit'] == revision['base_commit']
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    label = 'rh2.swe_dvc.attempt=' + args.attempt
    manifest = {str(f.relative_to(materials)): hashlib.sha256(f.read_bytes()).hexdigest()
                for f in sorted(materials.rglob('*')) if f.is_file()}
    expected = {'original_test.patch': revision['original_test_patch_sha256'],
                'effective_test.patch': revision['effective_test_patch_sha256']}
    expected.update({c['patch']: c['patch_sha256'] for c in revision['acceptance_matrix']})
    for file, sha in expected.items():
        assert 'sha256:' + manifest[file] == sha
    summary = {'purpose': 'private_pytest_diagnostic_not_formal_grading', 'started_at': time.time(),
               'instance_id': revision['instance_id'], 'revision_id': revision['revision_id'],
               'input_file_sha256': manifest, 'image_id': image['image_id'],
               'resources': {'cpus': 2, 'memory': '4g', 'pids': 512, 'network': 'none'}, 'runs': []}

    def save():
        (out / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')

    with (out / 'commands.log').open('w') as log:
        def run(cmd, *, timeout=120, allow_failure=False):
            log.write('$ ' + shlex.join(cmd) + '\n'); log.flush()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            log.write(result.stdout + result.stderr + '\nRC=' + str(result.returncode) + '\n'); log.flush()
            if result.returncode and not allow_failure:
                raise RuntimeError('preparation command failed: ' + cmd[0])
            return result

        def inside(name, script, *, timeout=120, allow_failure=False):
            return run(['docker', 'exec', '-e', 'PATH=/opt/miniconda3/envs/testbed/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
                        '-e', 'PYTHONPATH=/testbed', '-e', 'DVC_TEST=true', '-w', '/testbed',
                        name, 'bash', '-c', script], timeout=timeout, allow_failure=allow_failure)

        try:
            inspection = json.loads(run(['docker', 'image', 'inspect', image['image_id']]).stdout)[0]
            assert inspection['Id'] == image['image_id']
            for version in args.versions:
                patch = version + '_test.patch'
                if version == 'original':
                    selected = sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+$', (materials / patch).read_text(), re.M)))
                else:
                    selected = revision['selector']['files']
                for index, candidate in enumerate(revision['acceptance_matrix']):
                    directory = out / version / candidate['candidate']
                    directory.mkdir(parents=True)
                    name = 'rh2-dvc-' + args.attempt + '-' + version + '-' + str(index)
                    row = {'version': version, 'candidate': candidate['candidate'], 'selected_files': selected,
                           'candidate_patch_sha256': candidate['patch_sha256'], 'test_patch_sha256': expected[patch]}
                    try:
                        run(['docker', 'run', '-d', '--init', '--name', name, '--cpus', '2', '--memory', '4g',
                             '--pids-limit', '512', '--network', 'none', '--label', label,
                             '--entrypoint', 'sleep', image['image_id'], 'infinity'])
                        run(['docker', 'cp', str(materials) + '/.', name + ':/in'])
                        head = inside(name, 'git rev-parse HEAD').stdout.strip()
                        assert head == revision['base_commit']
                        (directory / 'initial_tree.txt').write_text(inside(name, 'git status --porcelain && git diff --binary').stdout)
                        restore = """import hashlib,json,shutil
from pathlib import Path
r=json.loads(Path('/in/revision.json').read_text())
for t in r['test_files']:
 p=Path('/testbed')/t['path']
 if t['base_exists']:
  source=Path('/in/public_tests')/t['path']
  assert 'sha256:'+hashlib.sha256(source.read_bytes()).hexdigest()==t['base_sha256']
  p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,p)
 elif p.exists(): p.unlink()
"""
                        inside(name, PYTHON + ' -c ' + shlex.quote(restore))
                        if candidate['candidate'] != 'noop':
                            inside(name, shlex.join(['git', 'apply', '--check', '/in/' + candidate['patch']]))
                            inside(name, shlex.join(['git', 'apply', '/in/' + candidate['patch']]))
                        inside(name, 'git apply --check /in/' + patch + ' && git apply /in/' + patch)
                        packages = list(dict.fromkeys(['dvc', 'pytest', *revision['environment_requirements']]))
                        identity_code = ('import sys,json,dvc,importlib.metadata as m; '
                                         'print(json.dumps(dict(python=sys.executable,dvc=dvc.__file__,versions={x:m.version(x) '
                                         'for x in ' + repr(packages) + '})))')
                        identity = inside(name, PYTHON + ' -c ' + shlex.quote(identity_code))
                        (directory / 'identity.json').write_text(identity.stdout)
                        if index == 0:
                            collection = inside(name, shlex.join([PYTHON, '-m', 'pytest', '--collect-only', '-q', *selected]), timeout=600, allow_failure=True)
                            (directory / 'collection.log').write_text(collection.stdout + collection.stderr)
                            row['collection_rc'] = collection.returncode
                        test = inside(name, shlex.join([PYTHON, '-m', 'pytest', '-rA', '-v', *selected]), timeout=1800, allow_failure=True)
                        (directory / 'pytest.log').write_text(test.stdout + test.stderr)
                        row['pytest_rc'] = test.returncode
                        # 原6954/4166的参数ID可含空白；私有诊断保留整行，不能split第一个词。
                        row['executed_node_statuses'] = [line for line in (test.stdout + test.stderr).splitlines()
                                                         if re.match(r'^tests/.+?\s+(?:PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b', line)]
                        (directory / 'applied.diff').write_text(inside(name, 'git diff --binary').stdout)
                    finally:
                        cleanup = run(['docker', 'rm', '-f', name], allow_failure=True)
                        exists = run(['docker', 'ps', '-aq', '--filter', 'name=^/' + name + '$'], allow_failure=True).stdout.strip()
                        row.update(cleanup_rc=cleanup.returncode, container_remaining=bool(exists))
                        summary['runs'].append(row); save()
                    print(version, candidate['candidate'], 'pytest_rc=' + str(row.get('pytest_rc')), flush=True)
            summary['status'] = 'diagnostics_completed_not_qualified'
        except BaseException as exc:
            summary.update(status='diagnostic_failed', error=str(exc)); raise
        finally:
            summary.update(finished_at=time.time(), remaining_containers=run(
                ['docker', 'ps', '-aq', '--filter', 'label=' + label], allow_failure=True).stdout.split())
            save()


if __name__ == '__main__':
    main()
