# 污染探针：候选补丁与 gold / 隐藏 test_patch 的逐行重合度。
# 隐藏 test_patch 求解者不可见；高重合 = 记忆上游 PR 的强证据。
import json,os,re
D='runs/env_probe_20260909_final_sync/ledger/logs_cc'
BASE='docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest'
def load_jsonl(p,key='instance_id'):
    d={}
    for line in open(p):
        line=line.strip()
        if line:
            o=json.loads(line); d[o[key]]=o
    return d
G=load_jsonl(f'{BASE}/grading_bundles_v2_v0.jsonl'); V=load_jsonl(f'{BASE}/validation_bundles_v0.jsonl')
def added(diff):
    return [l[1:].rstrip() for l in (diff or '').split('\n')
            if l.startswith('+') and not l.startswith('+++') and l[1:].strip()]
rows=[]
for tid in sorted(os.listdir(D)):
    f=f'{D}/{tid}/candidate.diff'
    if not os.path.exists(f) or tid not in G: continue
    cand=added(open(f,errors='replace').read())
    gold=added(V[tid].get('golden_patch')); tp=added(G[tid]['test_patch'])
    cs=set(cand)
    mg=sum(1 for l in gold if l in cs); mt=sum(1 for l in tp if l in cs)
    rows.append((tid,len(gold),mg,len(tp),mt))
rows.sort(key=lambda r:-(r[4]/r[3] if r[3] else 0))
print(f"{'task':42s} gold_add  match  test_add  match  test_frac")
for tid,ng,mg,nt,mt in rows:
    frac=mt/nt if nt else 0
    flag='  <== 强污染信号' if frac>=0.5 else ('  <== 可疑' if frac>=0.2 else '')
    print(f'{tid:42s} {ng:6d} {mg:6d} {nt:8d} {mt:6d} {frac:8.2f}{flag}')
