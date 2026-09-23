import json,os
S2='docs/agentic_RL/repo_harness_rh2_workstreams/s2'
OUT='runs/env_overnight_20260916/L1_dvc_1/mat'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/ASSIGNMENT.json'))
want=set(ASG['tasks'])
files={'public':f'{S2}/ingest/public_bundles_v0.jsonl','grading':f'{S2}/ingest/grading_bundles_v2_v0.jsonl',
       'validation':f'{S2}/ingest/validation_bundles_v0.jsonl','envpkg':f'{S2}/ingest/environment_packages_v0.jsonl',
       'raw':f'{S2}/raw/swe_gym_lite_full_f70b1a29.jsonl'}
keyname={'raw':'instance_id'}
for kind,p in files.items():
    n=0
    for line in open(p):
        line=line.strip()
        if not line: continue
        d=json.loads(line)
        tid=d.get('task_id') or d.get('instance_id')
        if tid in want:
            os.makedirs(f'{OUT}/{tid}',exist_ok=True)
            json.dump(d,open(f'{OUT}/{tid}/{kind}.json','w'),ensure_ascii=False,indent=1)
            n+=1
    print(kind,n,'of',len(want))
