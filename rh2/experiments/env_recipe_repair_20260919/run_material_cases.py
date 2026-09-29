"""私有fixture/helper及gold上下文修订的真实评分；不把金标或私有材料放入rollout镜像。"""
from pathlib import Path
import json
import os
import subprocess
import time

ROOT=Path(os.environ.get('RH2_MATERIALS_ROOT','/work/env_recipe_repair_20260919/materials_v1'))
OLD=Path('/work/full216_20260919')


def save(name,data):
    (ROOT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    tasks=json.loads((ROOT/'materials.json').read_text())['tasks']
    cases=['Project-MONAI__MONAI-1121','Project-MONAI__MONAI-4109','Project-MONAI__MONAI-6775',
           'python__mypy-10308','python__mypy-11352']
    if (ROOT/'cases.json').exists():
        cases=json.loads((ROOT/'cases.json').read_text())
    py=str(OLD/'code/rh2/.venv/bin/python')
    for iid in cases:
        image=None
        if iid=='Project-MONAI__MONAI-1121':
            image=json.loads((ROOT.parent/'round2b/evidence/dependency_images.json').read_text())['monai1121-numpy-v2']['image_id']
        if iid.startswith('python'):
            other=ROOT.parent/'install_wave1/tasks'/iid
            while not (other/'done.json').exists():
                if (ROOT.parent/'install_wave1/failed.json').exists() or (other/'failed.json').exists():
                    raise RuntimeError('前序安装验证中断；先解释错误。')
                save('status.json',{'state':'waiting_installation','task':iid,'at':time.time()})
                time.sleep(30)
            image=json.loads((other/'image.json').read_text())['image_id']
        kinds=['gold_context_rebased'] if iid.endswith('11352') else ['noop','gold']
        for kind in kinds:
            dest=ROOT/'runs'/(iid+'-'+kind);dest.mkdir(parents=True,exist_ok=False)
            if iid in tasks:
                command=[py,str(ROOT/'replay_with_install_recipe.py'),'--code-root',str(OLD/'code/rh2'),
                         '--materials',str(ROOT/'materials.json'),'--audit-dir',str(dest/'materials'),'--']
            else:
                command=[py,str(OLD/'code/rh2/scripts/replay_grade.py')]
            candidate='noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold')
            if kind=='gold_context_rebased':
                candidate='patch:'+str(ROOT/'mypy11352.context-rebased.patch')
            command+=['run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                      '--candidate',candidate,'--eval-log-dir',str(dest/'eval_logs'),
                      '--artifacts-dir',str(dest/'artifacts'),'--ledger',str(dest/'ledger.jsonl')]
            if image:
                command+=['--derived-image',image,'--derived-image-recipe','verified-assets-dependencies+materials-v1']
            save('status.json',{'state':'grading','task':iid,'kind':kind,'command':command,'at':time.time()})
            with (dest/'driver.log').open('w') as log:
                subprocess.run(command,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID='er19-mat1-'+iid+'-'+kind),
                               stdout=log,stderr=subprocess.STDOUT,check=True,timeout=4800)
            row=json.loads((dest/'ledger.jsonl').read_text())
            assert row['stage_error'] is None and row['cleanup']['removed'],row.get('stage_error')
            print('GRADED',iid,kind,json.dumps(row.get('report')),flush=True)
    save('done.json',{'at':time.time(),'attempts':sum(1 if iid.endswith('11352') else 2 for iid in cases),
                      'meaning':'execution finished; inspect target and helper/fixture states'})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save('failed.json',{'at':time.time(),'error':repr(exc)})
        raise
