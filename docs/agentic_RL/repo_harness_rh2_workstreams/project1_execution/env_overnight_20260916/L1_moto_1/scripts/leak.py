import json,re
M='runs/env_overnight_20260916/L1_moto_1/mat'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_1/ASSIGNMENT.json'))
def norm(s): return re.sub(r'\s+','',s)
rows=[]
for tid in ASG['tasks']:
    pub=json.load(open(f'{M}/{tid}/public.json')); val=json.load(open(f'{M}/{tid}/validation.json'))
    ps=norm(pub['problem_statement'])
    added=[l[1:].strip() for l in (val.get('golden_patch') or '').split('\n')
           if l.startswith('+') and not l.startswith('+++')]
    added=[a for a in added if len(a.strip())>=12 and not a.strip().startswith('#')]
    hit=[a for a in added if norm(a) and norm(a) in ps]
    rows.append((tid,len(added),len(hit),hit[:4]))
rows.sort(key=lambda r:-(r[2]/r[1] if r[1] else 0))
for tid,n,h,ex in rows:
    frac=f'{h}/{n}' if n else '0/0'
    mark='LEAK' if h else '    '
    print(f'{mark} {tid} gold_added_lines={n} matched_in_statement={frac}')
    for e in ex: print('        ',e)
