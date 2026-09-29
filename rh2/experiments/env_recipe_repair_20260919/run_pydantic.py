"""先8500安装敏感候选，再扩展其余19题。PDM开发者全套安装改为项目+测试依赖。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time

ROOT=Path('/work/env_recipe_repair_20260919/pydantic_v1')
OLD=Path('/work/full216_20260919')


def save(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    plan=json.loads((ROOT/'plan.json').read_text())
    plan.sort(key=lambda x:(x['instance_id']!='pydantic__pydantic-8500',x['instance_id']))
    recipe='ARG BASE_IMAGE\nFROM ${BASE_IMAGE}\nCOPY wheels/ /opt/rh2/build-wheels/\nENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels\n'
    (ROOT/'assets/Dockerfile').write_text(recipe)
    save(ROOT/'assets_manifest.json',[{'filename':p.name,'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
                                     for p in sorted((ROOT/'assets/wheels').glob('*.whl'))])
    for item in plan:
        iid=item['instance_id'];dest=ROOT/'tasks'/iid;dest.mkdir(parents=True,exist_ok=False)
        base=json.loads(subprocess.check_output(['docker','image','inspect',item['image']],text=True))[0]
        assert base['Id']==item['image_id']
        tag='rh2-envrepair/'+iid.lower()+':20260919-install-v1'
        with (dest/'build.log').open('w') as log:
            subprocess.run(['docker','build','--pull=false','--build-arg','BASE_IMAGE='+base['RepoDigests'][0],
                            '-t',tag,str(ROOT/'assets')],stdout=log,stderr=subprocess.STDOUT,timeout=600,check=True)
        image=json.loads(subprocess.check_output(['docker','image','inspect',tag],text=True))[0]
        assert image['RootFS']['Layers'][:-1]==base['RootFS']['Layers']
        save(dest/'image.json',{'base_id':base['Id'],'image_id':image['Id'],'base_layers_preserved':True,'recipe':recipe})
        for kind in (['noop','gold','canary'] if iid.endswith('8500') else ['noop','gold']):
            run=dest/kind;run.mkdir()
            candidate='noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold')
            if kind=='canary':
                patch=run/'candidate.patch';patch.write_text((OLD/'replay/gold'/(iid+'.gold.patch')).read_text()+'\n'+
                                                             (ROOT/'candidate_dependency.patch').read_text())
                candidate='patch:'+str(patch)
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),
                 '--code-root',str(OLD/'code/rh2'),'--recipe',str(ROOT/(iid+'.json')),'--audit-dir',str(run/'recipe'),
                 '--','run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                 '--candidate',candidate,'--derived-image',image['Id'],'--derived-image-recipe','pydantic-install-v1',
                 '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            save(ROOT/'status.json',{'task':iid,'kind':kind,'command':cmd,'at':time.time()})
            with (run/'driver.log').open('w') as log:
                subprocess.run(cmd,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID='er19-pyd1-'+iid+'-'+kind),
                               check=True,timeout=4800,stdout=log,stderr=subprocess.STDOUT)
            row=json.loads((run/'ledger.jsonl').read_text())
            assert row['stage_error'] is None and row['cleanup']['removed'],row.get('stage_error')
            if iid.endswith('8500'):
                assert row['install']['install_rc_last_command']==0, '先解释代表题安装失败，再扩大'
                assert row['report']['reward']==(0 if kind=='noop' else 1)
                if kind=='canary':
                    assert row['observations']['RH2_OBS_INSTALL_PROBE_PRE']=='absent'
                    assert 'site-packages' in row['observations']['RH2_OBS_INSTALL_PROBE']
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
    save(ROOT/'done.json',{'at':time.time(),'attempts':41,'meaning':'execution only; audit separately'})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save(ROOT/'failed.json',{'at':time.time(),'error':repr(exc)})
        raise
