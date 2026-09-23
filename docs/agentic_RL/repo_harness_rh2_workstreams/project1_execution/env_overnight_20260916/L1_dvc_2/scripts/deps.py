import json,os,re,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
B='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
ASG=json.load(open(f'{B}/L1_dvc_2/ASSIGNMENT.json'))
# 全部 dvc 题（两包），用 tasks_by_repo
byrepo=json.load(open(f'{B}/tasks_by_repo.json'))
allsdvc=byrepo.get('iterative/dvc') or byrepo.get('dvc') or []
if isinstance(allsdvc,dict): allsdvc=allsdvc.get('tasks',[])
tot=collections.Counter(); rows=[]
for tid in (allsdvc or ASG['tasks']):
    p=f'{L}/{tid}/gold/offline/a1/test_output.txt'
    if not os.path.exists(p): rows.append((tid,'NO_LOG',0,0,{})); continue
    fails=[]
    for line in open(p,errors='replace'):
        if line.startswith('FAILED '): fails.append(line.rstrip())
    reasons=collections.Counter()
    for f in fails:
        m=re.search(r' - (.*)$',f)
        r=(m.group(1) if m else 'NO_REASON_SHOWN')
        key=r.split(':')[0][:48]
        reasons[key]+=1
    ps=sum(v for k,v in reasons.items() if 're.error' in k)
    rows.append((tid,'',len(fails),ps,dict(reasons.most_common(4))))
    tot['tasks']+=1
    if ps: tot['tasks_with_pathspec']+=1
    tot['fails']+=len(fails); tot['pathspec_fails']+=ps
for tid,flag,n,ps,r in rows:
    mark='PS' if ps else ('  ' if not flag else flag)
    print(f'{mark} {tid} gold_FAILED={n} re.error={ps} {r}')
print('TOTAL',dict(tot))
