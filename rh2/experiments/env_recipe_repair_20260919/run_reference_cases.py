"""10题参考绑定修订的真实RH2 noop/gold；旧材料不回写，parser版本单列。"""
from pathlib import Path
import json
import os
import subprocess
import time

ROOT = Path('/work/env_recipe_repair_20260919/reference_v1')
OLD = Path('/work/full216_20260919')


def save(name, data):
    (ROOT / name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')


def main():
    previous = ROOT.parent / 'round2b/evidence'
    while not (previous / 'dependency_batch_done.json').exists():
        if (previous / 'dependency_batch_failed.json').exists():
            raise RuntimeError('前序作业失败，需要先检查；没有自动跳过。')
        save('status.json',{'state':'waiting_previous_batch','at':time.time()})
        time.sleep(30)
    tasks=json.loads((ROOT / 'reference_bindings_v1.json').read_text())['tasks']
    ordered=sorted(tasks,key=lambda x:(x.startswith('pandas'),x))
    py=str(OLD / 'code/rh2/.venv/bin/python')
    for iid in ordered:
        for kind in ('noop','gold'):
            dest=ROOT / 'runs' / (iid+'-'+kind)
            dest.mkdir(parents=True,exist_ok=False)
            command=[py,str(ROOT / 'replay_with_install_recipe.py'),'--code-root',str(OLD / 'code/rh2'),
                     '--bindings',str(ROOT / 'reference_bindings_v1.json'),'--audit-dir',str(dest/'bindings'),
                     '--','run','--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),
                     '--task-ids',iid,'--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                     '--eval-log-dir',str(dest/'eval_logs'),'--artifacts-dir',str(dest/'artifacts'),
                     '--ledger',str(dest/'ledger.jsonl')]
            save('status.json',{'state':'grading','task':iid,'kind':kind,'at':time.time(),'command':command})
            with (dest/'driver.log').open('w') as log:
                subprocess.run(command,env=dict(os.environ,MILES_RH2_RUN_ID='er19-ref-v1-'+iid+'-'+kind),
                               cwd=OLD/'code/rh2',stdout=log,stderr=subprocess.STDOUT,check=True,timeout=4800)
            row=json.loads((dest/'ledger.jsonl').read_text())
            assert row['cleanup']['removed'] and row['stage_error'] is None, row.get('stage_error')
            print('GRADED',iid,kind,json.dumps(row.get('report')),flush=True)
    save('done.json',{'at':time.time(),'attempts':len(tasks)*2,'meaning':'execution finished; review required'})


if __name__=='__main__':
    try:
        main()
    except BaseException as exc:
        save('failed.json',{'at':time.time(),'error':repr(exc)})
        raise
