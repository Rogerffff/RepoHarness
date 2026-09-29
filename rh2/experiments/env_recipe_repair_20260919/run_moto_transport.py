"""把两条公网AuthFailure断言改为明确的离线运输对照，保留mock启停和原断言。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
ROOT=Path('/work/env_recipe_repair_20260919/moto_transport_v1')
OLD=Path('/work/full216_20260919')
PREP=r'''
import ast,json,pathlib,subprocess
cfg=json.loads(pathlib.Path('/input/config.json').read_text())
subprocess.run(['git','apply','-'],input=cfg['test_patch'],text=True,cwd='/testbed',check=True)
p=pathlib.Path('/testbed/tests/test_core/test_decorator_calls.py');before=p.read_text();s=before
assert s.count('def test_context_manager(aws_credentials):')==1
assert s.count('def test_decorator_start_and_stop():')==1
s=s.replace('def test_context_manager(aws_credentials):','def test_context_manager(aws_credentials, rh2_offline_ec2_transport):')
s=s.replace('def test_decorator_start_and_stop():','def test_decorator_start_and_stop(rh2_offline_ec2_transport):')
lines=s.splitlines(keepends=True)
for node in sorted([n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef) and n.name in ['test_context_manager','test_decorator_start_and_stop']],key=lambda n:n.end_lineno,reverse=True):
 lines.insert(node.end_lineno,'    assert rh2_offline_ec2_transport.call_count == 1\n')
s=''.join(lines)+'\n\n'+pathlib.Path('/input/fixture.py').read_text();p.write_text(s)
# 来源内所有既有assert仍逐条存在；只新增运输边界计数。
asserts=lambda text:[ast.dump(n) for n in ast.walk(ast.parse(text)) if isinstance(n,ast.Assert)]
old_asserts=asserts(before);new_asserts=asserts(s)
assert all(x in new_asserts for x in old_asserts)
old_funcs={n.name:n for n in ast.parse(before).body if isinstance(n,ast.FunctionDef)}
new_funcs={n.name:n for n in ast.parse(s).body if isinstance(n,ast.FunctionDef)}
for name in ['test_context_manager','test_decorator_start_and_stop']:
 assert [ast.dump(x) for x in old_funcs[name].body] == [ast.dump(x) for x in new_funcs[name].body[:-1]]
patch=subprocess.check_output(['git','diff','--no-ext-diff','--binary'],text=True,cwd='/testbed')
print(json.dumps({'test_patch':patch,'original_file':before,'revised_file':s,'existing_asserts_preserved':len(old_asserts),
                  'simulation':'fixed AuthFailure at URLLib3Session.send, not live AWS validation; one real transport call per target test'}))
'''


def main():
    views={r['instance_id']:r['grading'] for r in map(json.loads,(OLD/'replay/private/host_grading_views.jsonl').read_text().splitlines())}
    tasks={}
    for iid in ['getmoto__moto-4799','getmoto__moto-4833']:
        inv=json.loads((ROOT.parent/'inventory/records'/(iid+'.json')).read_text());g=views[iid]
        prep=ROOT/'prep'/iid;prep.mkdir(parents=True,exist_ok=False)
        (prep/'config.json').write_text(json.dumps({'test_patch':g['test_patch']}));(prep/'prepare.py').write_text(PREP)
        (prep/'fixture.py').write_text((ROOT/'moto_transport_fixture.py').read_text())
        r=subprocess.run(['docker','run','--rm','--init','--network','none','--memory','1g','--cpus','1','-v',str(prep)+':/input:ro',
                          inv['image_id'],'/opt/miniconda3/envs/testbed/bin/python','-I','/input/prepare.py'],capture_output=True,text=True,timeout=120,check=True)
        tasks[iid]={**json.loads(r.stdout),'original_patch_sha256':hashlib.sha256(g['test_patch'].encode()).hexdigest(),
                    'base_image_id':inv['image_id'],'base_commit':g['base_commit'],'decision':'E15 versioned offline transport test; keep original live-network source variant'}
    (ROOT/'materials.json').write_text(json.dumps({'version':'moto-transport-v1','tasks':tasks},ensure_ascii=False,indent=2)+'\n')
    for iid in tasks:
        for kind in ['noop','gold']:
            run=ROOT/'runs'/(iid+'-'+kind);run.mkdir(parents=True,exist_ok=False)
            cmd=[str(OLD/'code/rh2/.venv/bin/python'),str(ROOT/'replay_with_install_recipe.py'),'--code-root',str(OLD/'code/rh2'),
                 '--materials',str(ROOT/'materials.json'),'--audit-dir',str(run/'materials'),'--','run',
                 '--prepared-summary',str(OLD/'replay/prepared/replay_summary.json'),'--task-ids',iid,
                 '--candidate','noop' if kind=='noop' else 'gold-dir:'+str(OLD/'replay/gold'),
                 '--eval-log-dir',str(run/'eval_logs'),'--artifacts-dir',str(run/'artifacts'),'--ledger',str(run/'ledger.jsonl')]
            (ROOT/'status.json').write_text(json.dumps({'at':time.time(),'task':iid,'kind':kind,'command':cmd}))
            with (run/'driver.log').open('w') as f:
                subprocess.run(cmd,cwd=OLD/'code/rh2',env=dict(os.environ,MILES_RH2_RUN_ID='er19-tv1-'+iid+'-'+kind),stdout=f,stderr=subprocess.STDOUT,check=True,timeout=4800)
            row=json.loads((run/'ledger.jsonl').read_text());assert row['stage_error'] is None and row['cleanup']['removed'],row['stage_error']
            print('GRADED',iid,kind,json.dumps(row['report']),flush=True)
    (ROOT/'done.json').write_text(json.dumps({'at':time.time(),'attempts':4}))


if __name__=='__main__':
    try:main()
    except BaseException as exc:
        (ROOT/'failed.json').write_text(json.dumps({'at':time.time(),'error':repr(exc)}));raise
