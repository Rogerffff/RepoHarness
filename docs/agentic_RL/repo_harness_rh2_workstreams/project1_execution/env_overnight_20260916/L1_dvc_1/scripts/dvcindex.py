# dvc 35 题跨题索引：共享 gold/test_patch 文件、base_commit 提交距离
import json,re,collections,subprocess
S2='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/dvc'
G={};V={}
for line in open(f'{S2}/ingest/grading_bundles_v2_v0.jsonl'):
    d=json.loads(line)
    if d['repo']=='iterative/dvc': G[d['instance_id']]=d
for line in open(f'{S2}/ingest/validation_bundles_v0.jsonl'):
    d=json.loads(line)
    if d['instance_id'] in G: V[d['instance_id']]=d
def paths(diff): return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
mine=set(json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/ASSIGNMENT.json'))['tasks'])
rows={t:{'base':d['base_commit'],'ver':d.get('version'),'gold':paths(V[t]['golden_patch']),'tp':paths(d['test_patch'])} for t,d in G.items()}
print(f'dvc 题数: {len(rows)}（本包 {len(mine)}）')
for label,key in (('gold','gold'),('test_patch','tp')):
    idx=collections.defaultdict(list)
    for t,r in rows.items():
        for p in r[key]: idx[p].append(t)
    print(f'\n== 共享 {label} 文件的题组 ==')
    for p,ts in sorted(idx.items()):
        if len(ts)>1: print(f'  {p:34s} {sorted(ts)}  [本包: {sorted(set(ts)&mine)}]')
order=[]
for t,r in rows.items():
    ts=subprocess.run(['git','-C',R,'show','-s','--format=%ct',r['base']],capture_output=True,text=True).stdout.strip()
    order.append((int(ts) if ts else 0,t,r['base'][:9],r['ver']))
order.sort(); prev=None
print('\n== base_commit 提交距离（按提交时间排序，* = 本包）==')
for ts,t,b,v in order:
    mark='*' if t in mine else ' '
    if prev:
        n=subprocess.run(['git','-C',R,'rev-list','--count',f'{prev}..{b}'],capture_output=True,text=True).stdout.strip()
        print(f'{mark} {t:26s} v={v:6s} base={b}  距上一题 base {n} 个提交')
    else: print(f'{mark} {t:26s} v={v:6s} base={b}')
    prev=b
