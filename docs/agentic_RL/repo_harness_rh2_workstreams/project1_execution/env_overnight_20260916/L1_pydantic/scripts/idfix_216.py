"""附-1：在全部 216 题上验证参考 ID 的 unicode_escape 回退规则。
规则：先按原样在 status_map 里查；查不到再用 ref.encode('unicode_escape').decode('ascii') 查一次。
只读 s2 ingest 与 stage1 离线日志，不需要容器。从仓库根目录运行。"""
import json,os,collections
S='docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
VALID={'PASSED','FAILED','ERROR','SKIPPED','XFAIL','XPASS'}
tot=collections.Counter(); rows=[]
for line in open(S):
    r=json.loads(line); tid=r['instance_id']; tot['tasks']+=1
    ids=r['fail_to_pass']+r['pass_to_pass']
    tot['ws_ids']+=sum(1 for x in ids if any(c.isspace() for c in x))
    p=f'{L}/{tid}/gold/offline/a1/status_map.json'
    if not os.path.exists(p): continue
    tot['with_log']+=1; sm=json.load(open(p))
    tot['bogus']+=sum(1 for v in sm.values() if v not in VALID)
    miss=[x for x in ids if x not in sm]
    fixed=[x for x in miss if x.encode('unicode_escape').decode('ascii') in sm]
    tot['miss']+=len(miss); tot['fixed']+=len(fixed); tot['still']+=len(miss)-len(fixed)
    if miss:
        st=sorted({sm[x.encode('unicode_escape').decode('ascii')] for x in fixed})
        rows.append((tid,len(miss),len(fixed),st))
print(dict(tot))
for tid,m,f,st in rows: print(f'  {tid}: missing={m} escape回退修复={f} 回退后状态={st}')
