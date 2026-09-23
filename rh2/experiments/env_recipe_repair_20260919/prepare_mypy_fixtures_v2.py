"""恢复10308同一来源提交里同时缺失的两份fixture，保留原测试函数。"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path('/work/env_recipe_repair_20260919/materials_v2')
OLD=Path('/work/full216_20260919')
IID='python__mypy-10308'
COMMIT='c0490b4c2d2bc3f385c548089245c929ca4b0448'
SCRIPT=r'''
from pathlib import Path
import subprocess,json
config=json.loads(Path('/input/config.json').read_text())
subprocess.run(['git','apply','-'],input=config['test_patch'],text=True,cwd='/testbed',check=True)
paths=['test-data/unit/fixtures/object_hashable.pyi','test-data/unit/fixtures/typing-full.pyi']
patch=subprocess.check_output(['git','diff',config['commit']+'^',config['commit'],'--',*paths],cwd='/testbed',text=True)
subprocess.run(['git','apply','-'],input=patch,text=True,cwd='/testbed',check=True)
subprocess.run(['git','add','-N',paths[0]],cwd='/testbed',check=True)
revised=subprocess.check_output(['git','diff','--no-ext-diff','--binary'],cwd='/testbed',text=True)
print(json.dumps({'test_patch':revised,'evidence':{'commit':config['commit'],'upstream_fixture_patch':patch}}))
'''


def main():
    views={r['instance_id']:r for r in map(json.loads,(OLD/'replay/private/host_grading_views.jsonl').read_text().splitlines())}
    grading=views[IID]['grading']
    inv=json.loads((ROOT.parent/'inventory/records'/(IID+'.json')).read_text())
    dest=ROOT/'prep';dest.mkdir()
    (dest/'config.json').write_text(json.dumps({'test_patch':grading['test_patch'],'commit':COMMIT}))
    (dest/'prepare.py').write_text(SCRIPT)
    args=['docker','run','--rm','--init','--network','none','--memory','1g','--cpus','1',
          '-v',str(dest)+':/input:ro',inv['image_id'],'/opt/miniconda3/envs/testbed/bin/python','-I','/input/prepare.py']
    result=subprocess.run(args,text=True,capture_output=True,timeout=120,check=True)
    (dest/'stderr.log').write_text(result.stderr)
    entry={**json.loads(result.stdout),'original_patch_sha256':hashlib.sha256(grading['test_patch'].encode()).hexdigest(),
           'base_commit':grading['base_commit'],'base_image_id':inv['image_id'],
           'decision':'restore both omitted fixture changes from exact upstream commit; test assertions unchanged'}
    (ROOT/'materials.json').write_text(json.dumps({'version':'materials-v2','tasks':{IID:entry}},indent=2)+'\n')
    (ROOT/'cases.json').write_text(json.dumps([IID])+'\n')


if __name__=='__main__':main()
