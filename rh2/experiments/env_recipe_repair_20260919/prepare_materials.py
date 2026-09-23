"""从原始checkout+test_patch形成私有材料修订；仅在短命容器内改测试文件。"""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path('/work/env_recipe_repair_20260919/materials_v1')
OLD=Path('/work/full216_20260919')
TASKS={'python__mypy-10308':None, 'Project-MONAI__MONAI-1121':'tests/utils.py',
       'Project-MONAI__MONAI-4109':'tests/test_subpixel_upsample.py',
       'Project-MONAI__MONAI-6775':'tests/test_generalized_dice_loss.py'}
COMMIT='c0490b4c2d2bc3f385c548089245c929ca4b0448'
SCRIPT=r'''
import json, pathlib, subprocess, sys
config=json.loads(pathlib.Path('/input/config.json').read_text())
subprocess.run(['git','apply','-'],input=config['test_patch'],text=True,check=True,cwd='/testbed')
evidence={}
if config['append_to']:
 p=pathlib.Path('/testbed')/config['append_to']
 p.write_text(p.read_text()+'\n# RepoHarness materials-v1: imported helper remains callable; not a standalone pytest test.\ntest_script_save.__test__ = False\n')
 evidence['append_to']=config['append_to']
else:
 rel='test-data/unit/fixtures/object_hashable.pyi'
 content=subprocess.check_output(['git','show',config['commit']+':'+rel],text=True,cwd='/testbed')
 (pathlib.Path('/testbed')/rel).write_text(content)
 subprocess.run(['git','add','-N',rel],cwd='/testbed',check=True)
 evidence={'fixture':rel,'commit':config['commit'],'content':content}
patch=subprocess.check_output(['git','diff','--no-ext-diff','--binary'],text=True,cwd='/testbed')
print(json.dumps({'test_patch':patch,'evidence':evidence}))
'''


def main():
    views={r['instance_id']:r for r in map(json.loads,(OLD/'replay/private/host_grading_views.jsonl').read_text().splitlines())}
    result={}
    for index,(iid,append) in enumerate(TASKS.items()):
        inv=json.loads((ROOT.parent/'inventory/records'/(iid+'.json')).read_text())
        g=views[iid]['grading'];dest=ROOT/'prep'/iid;dest.mkdir(parents=True)
        (dest/'config.json').write_text(json.dumps({'test_patch':g['test_patch'],'append_to':append,'commit':COMMIT}))
        (dest/'prepare.py').write_text(SCRIPT)
        name='er19-materials-prep-'+str(index)
        try:
            p=subprocess.run(['docker','run','--rm','--init','--name',name,'--network','none','--cpus','1','--memory','1g',
                              '--pids-limit','128','-v',str(dest)+':/input:ro',inv['image_id'],
                              '/opt/miniconda3/envs/testbed/bin/python','-I','/input/prepare.py'],
                             text=True,capture_output=True,timeout=120,check=True)
            (dest/'stderr.log').write_text(p.stderr)
            value=json.loads(p.stdout)
            result[iid]={**value,'original_patch_sha256':hashlib.sha256(g['test_patch'].encode()).hexdigest(),
                         'base_commit':g['base_commit'],'base_image_id':inv['image_id'],
                         'decision':'private grading materials only; no target assertions changed'}
        finally:
            subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)
    (ROOT/'materials.json').write_text(json.dumps({'version':'materials-v1','tasks':result},ensure_ascii=False,indent=2)+'\n')
    iid='python__mypy-11352'
    source=(OLD/'replay/gold'/(iid+'.gold.patch')).read_text()
    old='         from mypy.plugins import ctypes\n'
    assert source.count(old)==1
    revised=source.replace(old,'         from mypy.plugins import ctypes, singledispatch\n',1)
    assert [l for l in source.splitlines() if l.startswith(('+','-'))]==[l for l in revised.splitlines() if l.startswith(('+','-'))]
    (ROOT/'mypy11352.context-rebased.patch').write_text(revised)
    (ROOT/'gold_rebase.json').write_text(json.dumps({'instance_id':iid,'change':'context import includes singledispatch; added/deleted lines identical',
          'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'revised_sha256':hashlib.sha256(revised.encode()).hexdigest()},indent=2))
    print('prepared',len(result),'private material revisions and one context-only gold rebase')


if __name__=='__main__':
    main()
