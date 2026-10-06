import json,re,collections
S='docs/agentic_RL/repo_harness_rh2_workstreams/s2'
tb=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/tasks_by_repo.json'))
want=set(tb['Project-MONAI/MONAI'])
G={};V={};P={};RAW={}
for p,dst,key in [(f'{S}/ingest/grading_bundles_v2_v0.jsonl',G,'instance_id'),
                  (f'{S}/ingest/validation_bundles_v0.jsonl',V,'instance_id'),
                  (f'{S}/ingest/public_bundles_v0.jsonl',P,'instance_id'),
                  (f'{S}/raw/swe_gym_lite_full_f70b1a29.jsonl',RAW,'instance_id')]:
    for line in open(p):
        r=json.loads(line)
        if r[key] in want: dst[r[key]]=r
def paths(d): return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', d or '', re.M)))
gold_by_path=collections.defaultdict(list); tp_by_path=collections.defaultdict(list)
base_by=collections.defaultdict(list)
rows=[]
for t in sorted(want):
    g=G[t]; v=V[t]
    gp=paths(v.get('golden_patch')); tp=paths(g['test_patch'])
    for x in gp: gold_by_path[x].append(t)
    for x in tp: tp_by_path[x].append(t)
    base_by[g['base_commit']].append(t)
    rows.append((t,g['base_commit'],RAW[t].get('created_at'),gp,tp))
print('=== gold path shared by >1 task ===')
for k,v2 in sorted(gold_by_path.items()):
    if len(v2)>1: print(f'  {k}: {v2}')
print('=== test_patch path shared by >1 task ===')
for k,v2 in sorted(tp_by_path.items()):
    if len(v2)>1: print(f'  {k}: {v2}')
print('=== same base_commit ===')
for k,v2 in base_by.items():
    if len(v2)>1: print(f'  {k[:10]}: {v2}')
print('=== per-task ===')
for t,b,c,gp,tp in sorted(rows,key=lambda r:r[2] or ''):
    print(f'{t} base={b[:10]} created={c} gold={gp} tp={tp}')
