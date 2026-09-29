"""合并已分别验证的安装与参考绑定，避免两个单独成功替代完整配方。"""
from pathlib import Path
import json
import os
import subprocess
import time
ROOT=Path('/work/env_recipe_repair_20260919/combined_v1')
OLD=Path('/work/full216_20260919')


def main():
    for iid,parent,recipe in [
        ('pydantic__pydantic-8977','pydantic_v1','pydantic_v1/pydantic__pydantic-8977.json'),
        ('getmoto__moto-6308','install_wave1',None),
    ]:
        task=ROOT.parent/parent/'tasks'/iid
        if parent=='install_wave1':assert (task/'done.json').exists()
        else:assert (ROOT.parent/parent/'done.json').exists()
        image=json.loads((task/'image.json').read_text())['image_id']
        for kind in ['noop','gold']:
            run=ROOT/'runs'/(iid+'-'+kind);run.mkdir(parents=True,exist_ok=False)
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),'--code-root',str(OLD/'code/rh2'),
                 '--bindings',str(ROOT/'reference_bindings_v1.json'),'--audit-dir',str(run/'audit')]
            if recipe:cmd+=['--recipe',str(ROOT.parent/recipe)]
            cmd+=['--','run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                  '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                  '--derived-image',image,'--derived-image-recipe',parent+'+reference-bindings-v1',
                  '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            (ROOT/'status.json').write_text(json.dumps({'at':time.time(),'task':iid,'kind':kind,'command':cmd}))
            with (run/'driver.log').open('w') as f:
                subprocess.run(cmd,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID='er19-com1-'+iid+'-'+kind),stdout=f,stderr=subprocess.STDOUT,timeout=4800,check=True)
            row=json.loads((run/'ledger.jsonl').read_text());assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            print('GRADED',iid,kind,json.dumps({'report':row['report'],'install':row['install']}),flush=True)
    (ROOT/'done.json').write_text(json.dumps({'at':time.time(),'attempts':4}))


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        (ROOT/'failed.json').write_text(json.dumps({'at':time.time(),'error':repr(exc)}));raise
