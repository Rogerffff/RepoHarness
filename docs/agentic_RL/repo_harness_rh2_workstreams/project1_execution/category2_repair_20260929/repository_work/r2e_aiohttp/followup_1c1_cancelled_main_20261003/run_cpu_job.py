"""cpu_slot内串行执行一个公开输入的三侧；不建像、不调用模型或评分。"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ap=argparse.ArgumentParser()
ap.add_argument('--inputs',required=True,type=Path)
ap.add_argument('--out',required=True,type=Path)
ap.add_argument('--run-id',required=True)
ns=ap.parse_args()
root=Path('/work/rh2-category2-20261003')
release=root/'releases/cat2-cpu-r2e080087-swe8-git-20261003-v1'
repo=release/'repo'
python=root/'runtime_cpu_v2/rh2/.venv/bin/python'
manifest=json.loads((ns.inputs/'input_manifest.json').read_text())
assert not ns.out.exists(),'new output required'
for row in manifest['files']:
    assert 'sha256:'+hashlib.sha256((ns.inputs/row['name']).read_bytes()).hexdigest()==row['sha256'],row['name']
assert 'sha256:'+hashlib.sha256((release/'manifest.json').read_bytes()).hexdigest()==manifest['release_manifest_sha256']
ns.out.mkdir()
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(repo/'rh2/src'),SLIME_AGENT_CC_PLATFORM_TARBALL=str(root/'cc/claude-code-linux-x64-2.1.205.tgz'))

def invoke(label,argv):
    started=datetime.datetime.now(datetime.timezone.utc).isoformat()
    with (ns.out/(label+'.stdout.log')).open('xb') as stdout,(ns.out/(label+'.stderr.log')).open('xb') as stderr:
        rc=subprocess.run(argv,cwd=repo/'rh2',env=env,stdout=stdout,stderr=stderr).returncode
    record={'stage':label,'argv':argv,'started_at':started,'ended_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'returncode':rc}
    with (ns.out/(label+'_process.json')).open('x')as f:json.dump(record,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(record),flush=True)
    return rc

iid=manifest['task_id']
rc=invoke('prepare_public_task',[str(python),'-B',str(repo/'rh2/scripts/replay_grade.py'),'prepare','--repo-root',str(repo),'--out-dir',str(ns.out/'prepared'),'--private-dir',str(ns.out/'private'),'--sources','r2e_gym_subset','--task-ids',iid])
if rc:raise SystemExit(rc)
publics=[json.loads(line) for line in (ns.out/'prepared/rollout_task_views.jsonl').read_text().splitlines()]
assert len(publics)==1 and publics[0]['task_id']==iid
assert publics[0]['public_bundle_digest']==manifest['public_bundle_digest']
rows=[]
for index,case in enumerate(['baseline','coder_full_frozen','qwen_full_frozen'],1):
    folder=ns.out/case
    run_id=ns.run_id+'-'+str(index)
    prepared_summary=ns.out/'prepared/replay_summary.json'
    prepared_sha='sha256:'+hashlib.sha256(prepared_summary.read_bytes()).hexdigest()
    rc=invoke(case,[str(python),'-B',str(ns.inputs/'run_fixed_public_probe.py'),'--fixed-repo',str(repo),'--input-manifest',str(ns.inputs/'input_manifest.json'),'--case',case,'--expected-prepared-summary-sha256',prepared_sha,'--prepared-summary',str(prepared_summary),'--overlays',str(ns.inputs/'original_overlays.jsonl'),'--task',iid.split('::')[-1],'--commands',str(ns.inputs/(case+'_commands.json')),'--out-dir',str(folder),'--attempt-id',run_id,'--stub-host','172.17.0.1','--stub-port','18213','--wall-seconds','600'])
    records=list(folder.glob('*.json'))
    actual=[]
    for path in records:
        obj=json.loads(path.read_text())
        if isinstance(obj,dict) and obj.get('cancelled_main_public_observation'):
            actual.append((path,obj))
    if len(actual)!=1:
        rows.append({'case':case,'returncode':rc,'valid_runner_record_count':len(actual),'status':'failed_before_complete_observation'})
    else:
        path,record=actual[0]
        observation=record['cancelled_main_public_observation']
        checks=record.get('checks') or {}
        rows.append({'case':case,'returncode':rc,'runner_record':str(path),'observation':observation,'checks':checks,'cleanup':record.get('cleanup'),'status':'observed' if rc==0 and checks.get('cancelled_main_input_executed_and_observed') else 'failed_or_incomplete'})
    with (ns.out/'progress.json').open('w')as f:json.dump({'rows':rows,'new_model_sampling':False,'new_formal_grade':False},f,ensure_ascii=False,indent=2);f.write('\n')
    if rc or rows[-1]['status']!='observed':raise SystemExit(rc or 5)
with (ns.out/'summary.json').open('x')as f:json.dump({'rows':rows,'all_three_observed':True,'owner_attribution_pending':True,'non_author_narrow_review_pending':True,'raw_original_grade_changed':False},f,ensure_ascii=False,indent=2);f.write('\n')
