import json,os
S='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
OUT='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_2/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/ASSIGNMENT.json'))
want=set(ASG['tasks'])
files={'public':f'{S}/ingest/public_bundles_v0.jsonl','grading':f'{S}/ingest/grading_bundles_v2_v0.jsonl',
       'validation':f'{S}/ingest/validation_bundles_v0.jsonl','envpkg':f'{S}/ingest/environment_packages_v0.jsonl',
       'raw':f'{S}/raw/swe_gym_lite_full_f70b1a29.jsonl'}
for kind,p in files.items():
    if not os.path.exists(p): print('MISSING',p); continue
    n=0
    for line in open(p):
        line=line.strip()
        if not line: continue
        d=json.loads(line)
        tid=d.get('task_id') or d.get('instance_id') or d.get('id')
        if tid in want:
            os.makedirs(f'{OUT}/{tid}',exist_ok=True)
            json.dump(d,open(f'{OUT}/{tid}/{kind}.json','w'),ensure_ascii=False,indent=1)
            n+=1
    print(kind,n)
