"""Conan11594 仅补 Ninja 的独立 CPU 复验；准备交付，不由作者执行。

远端：python conan_ninja_followup_v1.py
固定新目录 ninja-v1；保留 mixed-v1、inputs_v1 和 code_v1，不重复原 actor。
外层仍须由 root 使用有界 systemd 作业管理整个进程组。
"""
from __future__ import annotations

import json
import re
import signal
import subprocess
import time
from pathlib import Path

import mixed_followups as mixed
from mixed_followups import Campaign, ROOT, digest, load, require, write

IID = 'conan-io__conan-11594'
ATTEMPT = 'ninja-v1'
MIXED_SHA256 = '605f4326beb120c00cbbb6a6bbc36f04a03ce6a64f834cd557edc9fba4d799c6'
PIN = '1.10.2.4'
PYTHON = '/opt/miniconda3/envs/testbed/bin/python'

# 只在远端源镜像解释器中执行；取得固定版本元数据后选择本解释器兼容 wheel。
DOWNLOAD = r'''
import hashlib,json,os,pathlib,re,subprocess,sys,urllib.parse,urllib.request
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import parse_wheel_filename
root=pathlib.Path('/cache')
url='https://pypi.org/pypi/ninja/1.10.2.4/json'
with urllib.request.urlopen(url,timeout=60) as response:
    assert response.geturl()==url, response.geturl()
    raw=response.read()
(root/'pypi_metadata.json').write_bytes(raw)
meta=json.loads(raw)
assert meta['info']['name'].lower()=='ninja' and meta['info']['version']=='1.10.2.4'
ranks={tag:i for i,tag in enumerate(sys_tags())}
candidates=[]
for item in meta['urls']:
    if item['packagetype']!='bdist_wheel' or item.get('yanked'):
        continue
    name,version,build,tags=parse_wheel_filename(item['filename'])
    scores=[ranks[t] for t in tags if t in ranks]
    if name=='ninja' and str(version)=='1.10.2.4' and scores:
        candidates.append((min(scores),item['filename'],item))
assert candidates, 'no compatible non-yanked wheel'
item=sorted(candidates,key=lambda x:(x[0],x[1]))[0][2]
filename=item['filename']; parsed=urllib.parse.urlsplit(item['url'])
assert re.fullmatch(r'[A-Za-z0-9_.-]+\.whl',filename), filename
assert parsed.scheme=='https' and parsed.hostname=='files.pythonhosted.org'
assert not parsed.query and not parsed.fragment
assert urllib.parse.unquote(parsed.path.rsplit('/',1)[-1])==filename
expected=item['digests']['sha256']; size=item['size']
assert re.fullmatch(r'[0-9a-f]{64}',expected) and isinstance(size,int) and size>0
receipt={'metadata_url':url,'metadata_sha256':hashlib.sha256(raw).hexdigest(),
         'project':'ninja','distribution_version':'1.10.2.4','filename':filename,
         'url':item['url'],'sha256':expected,'bytes':size,'python':sys.version,
         'selection':'best compatible wheel by pip vendored packaging.sys_tags'}
(root/'wheel_selection.json').write_text(json.dumps(receipt,indent=2)+'\n')
wheels=root/'wheels'; wheels.mkdir()
env=dict(os.environ,PIP_CONFIG_FILE=os.devnull,PIP_NO_INDEX='1',PIP_DISABLE_PIP_VERSION_CHECK='1')
cmd=[sys.executable,'-I','-m','pip','--isolated','--no-cache-dir','download','--no-index','--only-binary=:all:',
     '--no-deps','--dest',str(wheels),item['url']+'#sha256='+expected]
print('PIP_DOWNLOAD_COMMAND='+json.dumps(cmd),flush=True)
subprocess.run(cmd,env=env,check=True,timeout=600)
assert sorted(x.name for x in wheels.iterdir())==[filename]
f=wheels/filename
assert f.stat().st_size==size and hashlib.sha256(f.read_bytes()).hexdigest()==expected
receipt['verified']=True
(root/'wheel_verified.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('NINJA_WHEEL_VERIFIED='+json.dumps(receipt),flush=True)
'''

PROBE = r'''
import hashlib,json,pathlib,shutil,subprocess,sys
result={'python':sys.executable,'python_version':sys.version}
for tool in ('cmake','ninja'):
    path=shutil.which(tool)
    row={'path':path}
    if path:
        resolved=pathlib.Path(path).resolve()
        row.update(realpath=str(resolved),sha256=hashlib.sha256(resolved.read_bytes()).hexdigest(),
                   mode=resolved.stat().st_mode & 0o7777)
        p=subprocess.run([path,'--version'],capture_output=True,text=True,timeout=30)
        row.update(rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
    result[tool]=row
print('TOOL_INVENTORY='+json.dumps(result,sort_keys=True))
'''


class NinjaCampaign(Campaign):
    def cleanup_container(self, name, receipt):
        facts = {'name': name}
        try:
            proc = subprocess.run(['docker', 'rm', '-f', name], capture_output=True, text=True, timeout=120)
            facts.update(rm_rc=proc.returncode, rm_stdout=proc.stdout, rm_stderr=proc.stderr)
        except BaseException as exc:
            facts['rm_error'] = repr(exc)
        try:
            proc = subprocess.run(['docker', 'ps', '-a', '--filter', 'name=^/' + name + '$',
                                   '--format', '{{.Names}}'], capture_output=True, text=True, timeout=60)
            facts.update(query_rc=proc.returncode, remaining=proc.stdout.split(), query_stderr=proc.stderr)
        except BaseException as exc:
            facts['query_error'] = repr(exc)
        write(receipt, facts)
        require(facts.get('query_rc') == 0 and facts.get('remaining') == [],
                'container cleanup unconfirmed: ' + name)

    def named_container(self, step, image, code, *, network='none', mount=None, timeout=180):
        name = 'cpu29-conan11594-ninja-v1-' + step.replace('_', '-')
        args = ['docker', 'run', '--name', name, '--rm', '--label', 'rh2.cpu29.owner=' + name,
                '--cpus', '1', '--memory', '2g', '--pids-limit', '128', '--network', network,
                '--read-only', '--tmpfs', '/tmp:rw,nosuid,nodev,size=256m',
                '--entrypoint', PYTHON, '-e', 'PYTHONDONTWRITEBYTECODE=1',
                '-e', 'PATH=/opt/miniconda3/envs/testbed/bin:/opt/miniconda3/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin']
        if mount:
            args += ['-v', str(mount) + ':/cache']
        try:
            self.run(step, args + [image, '-I', '-c', code], timeout=timeout)
        finally:
            self.cleanup_container(name, self.out / (step + '_cleanup.json'))

    def inventory(self, step, image):
        self.named_container(step, image, PROBE)
        rows = [json.loads(x.split('=', 1)[1]) for x in (self.out / (step + '.log')).read_text().splitlines()
                if x.startswith('TOOL_INVENTORY=')]
        require(len(rows) == 1, 'tool inventory absent/ambiguous')
        write(self.out / (step + '.json'), rows[0])
        cmake = rows[0]['cmake']
        require(cmake.get('rc') == 0 and cmake['stdout'].splitlines()[0] == 'cmake version 3.22.1',
                'CMake baseline changed; stop')
        return rows[0]

    def execute(self):
        require(digest(Path(mixed.__file__)) == MIXED_SHA256, 'reviewed mixed_followups changed')
        self.verify_inputs()
        previous = ROOT / 'results' / IID / 'mixed-v1'
        prior = load(previous / 'actor_original/attempt.json')
        require(prior.get('result') == 'ran' and prior.get('cleanup', {}).get('residual_after_force') == []
                and not prior.get('cleanup', {}).get('network_failures')
                and not prior.get('cleanup', {}).get('relay_failures'), 'previous actor cleanup unconfirmed')
        self.state['reuse'] = {'original_actor': str(previous / 'actor_original'),
                              'attempt_sha256': digest(previous / 'actor_original/attempt.json')}
        base = self.inspect(self.recovery['source_image'])
        require(base.get('Architecture') == 'amd64' and base.get('Os') == 'linux', 'unexpected source platform')
        require(base['Id'] == load(previous / 'original_image.json')['Id'], 'source image identity changed')
        require(self.recovery['source_image'] in base.get('RepoDigests', []), 'pinned source digest absent')
        require(self.inspect(self.public['image'])['Id'] == base['Id'], 'public tag changed')
        write(self.out / 'original_image.json', base)
        before = self.inventory('tools_before', base['Id'])
        require(before['ninja'].get('path') is None, 'Ninja already on PATH; diagnose instead of installing another')
        dest = self.out / 'dependency_build'
        dest.mkdir()
        self.named_container('download_wheel', base['Id'], DOWNLOAD, network='bridge', mount=dest, timeout=900)
        wheel = load(dest / 'wheel_verified.json')
        metadata = load(dest / 'pypi_metadata.json')
        require(wheel.get('verified') is True and wheel['distribution_version'] == PIN, 'wheel verification absent')
        require(digest(dest / 'pypi_metadata.json') == wheel['metadata_sha256'], 'metadata digest mismatch')
        records = [x for x in metadata['urls'] if x['filename'] == wheel['filename']]
        require(len(records) == 1, 'metadata filename ambiguous')
        item = records[0]
        require(item['url'] == wheel['url'] and item['size'] == wheel['bytes']
                and item['digests']['sha256'] == wheel['sha256'], 'wheel receipt disagrees with PyPI metadata')
        files = list((dest / 'wheels').iterdir())
        require(len(files) == 1 and files[0].name == wheel['filename']
                and files[0].stat().st_size == wheel['bytes'] and digest(files[0]) == wheel['sha256'],
                'host recheck of downloaded wheel failed')
        dockerfile = ('ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/ninja-wheels/\n'
                      'RUN ' + PYTHON + ' -I -m pip --isolated install --no-index --no-deps '
                      '/opt/rh2/ninja-wheels/' + wheel['filename'] + '\n')
        (dest / 'Dockerfile').write_text(dockerfile)
        recipe = {'source_image': self.recovery['source_image'], 'source_id': base['Id'], 'wheel': wheel,
                  'dockerfile_sha256': digest(dest / 'Dockerfile'), 'preserve': ['CMake3.22.1', 'source', 'public commands',
                  'formal tests/reference bindings', 'setup900/test/whole1800 budgets'], 'scope': 'Ninja dependency only'}
        write(dest / 'recipe.json', recipe)
        recipe_sha = digest(dest / 'recipe.json')
        old_mode = self.plan['mode']
        require(old_mode == 'use_original_no_repair', 'unexpected original plan mode')
        self.plan = dict(self.plan, mode='rebuild_dependency_image')
        self.state['runtime_plan_override'] = {'old_mode': old_mode, 'new_mode': self.plan['mode'],
                                               'recipe': str(dest / 'recipe.json'), 'recipe_sha256': recipe_sha,
                                               'old_inputs_modified': False}
        self.save()
        tag = 'rh2-cpu29/conan-io-conan-11594:ninja-v1'
        try:
            self.run('build_ninja', ['docker', 'build', '--pull=false', '--network=none', '--force-rm',
                     '--build-arg', 'BASE_IMAGE=' + self.recovery['source_image'], '-t', tag, dest], timeout=1200)
        except BaseException:
            self.state['build_cleanup'] = 'unconfirmed after failed/interrupted build; stop for root inspection'
            raise
        built = self.inspect(tag)
        require(built['RootFS']['Layers'][:len(base['RootFS']['Layers'])] == base['RootFS']['Layers'],
                'immutable base layers changed')
        write(dest / 'image.json', {'base': base, 'derived': built, 'recipe_sha256': recipe_sha})
        after = self.inventory('tools_after', built['Id'])
        require(after['cmake'] == before['cmake'], 'CMake executable/version/path changed')
        ninja = after['ninja']
        require(ninja.get('rc') == 0 and re.fullmatch(r'1\.10\.2(?:[.\-+][^\s]+)?', ninja['stdout'].strip()),
                'Ninja binary is not expected upstream 1.10.2 family; preserve output and stop')
        self.state['ninja_actual_version'] = ninja['stdout'].strip()
        self.state['derived_image'] = built['Id']
        self.save()
        self.actor('actor_revised', built['Id'], require_expected=True)
        self.private_behavior(built['Id'])
        for kind in ('noop', 'gold', 'degenerate'):
            self.grade(kind, built['Id'])
        self.state['status'] = 'executed_pending_review'
        self.state['remaining'] += ['正式题面/public_hints交付未由Devcheck证明', 'Ninja版本/新配方独立复核']


def main():
    campaign = NinjaCampaign(IID, ATTEMPT)

    def interrupted(signum, _frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    try:
        campaign.execute()
    except BaseException as exc:
        campaign.state.update(status='stopped_needs_diagnosis', error=repr(exc))
        raise
    finally:
        campaign.state['finished_at'] = time.time()
        campaign.save()


if __name__ == '__main__':
    main()
