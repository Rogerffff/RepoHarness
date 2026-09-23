# 216 题全量：参考清单里"环境相关/易变"的测试 ID 扫描 + P2P 漏收统计 + SKIPPED 身份丢失统计
import json,os,re,collections
S2='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
OUT='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1'
G={}
for line in open(f'{S2}/ingest/grading_bundles_v2_v0.jsonl'):
    d=json.loads(line); G[d['instance_id']]=d
print('tasks in grading bundle:',len(G))

abs_pat=re.compile(r'\[[^\]]*(?:/testbed|/tmp/|/root/|/home/|/usr/|[A-Za-z]:\\)')
bs_pat=re.compile(r'\\')
res={'abs_path_id':[], 'backslash_id':[], 'nonascii_id':[], 'unbalanced_bracket':[]}
for tid,d in G.items():
    for kind in ('fail_to_pass','pass_to_pass'):
        for x in d[kind]:
            if abs_pat.search(x): res['abs_path_id'].append((tid,kind,x))
            if bs_pat.search(x): res['backslash_id'].append((tid,kind,x))
            if any(ord(c)>127 for c in x): res['nonascii_id'].append((tid,kind,x))
            if x.count('[')!=x.count(']'): res['unbalanced_bracket'].append((tid,kind,x))
for k,v in res.items():
    tids=sorted(set(t for t,_,_ in v))
    print(f'== {k}: {len(v)} 条, 覆盖 {len(tids)} 题')
    for t,kind,x in v[:12]: print(f'   {t} [{kind}] {x!r}')
    if len(v)>12: print(f'   ... 共 {len(v)} 条')

# P2P 漏收 + SKIPPED 丢失
cov=[]; skip=[]
nlog=0
for tid,d in G.items():
    p=f'{L}/{tid}/gold/offline/a1/status_map.json'
    if not os.path.exists(p): continue
    nlog+=1
    sm=json.load(open(p))
    ids=set(d['fail_to_pass'])|set(d['pass_to_pass'])
    passed=[k for k,v in sm.items() if v=='PASSED']
    ungraded=[k for k in passed if k not in ids and '::' in k]
    if ungraded: cov.append((tid,len(ungraded),len(ids)))
    # SKIPPED 身份丢失：值为 SKIPPED 但键不是 nodeid
    lost=[k for k,v in sm.items() if v=='SKIPPED' and '::' not in k]
    kept=[k for k,v in sm.items() if v=='SKIPPED' and '::' in k]
    if lost or kept: skip.append((tid,len(lost),len(kept)))
print(f'\n== gold status_map 可用的题数: {nlog}')
cov.sort(key=lambda r:-r[1])
print(f'== P2P 漏收（gold 侧 PASSED 但不在 F2P∪P2P 的 nodeid）: {len(cov)}/{nlog} 题命中, 合计 {sum(c[1] for c in cov)} 条')
for t,n,g in cov[:20]: print(f'   {t:38s} ungraded={n:4d} graded={g}')
print(f'\n== SKIPPED 身份丢失: {len(skip)} 题有 SKIPPED 记录')
tot_lost=sum(s[1] for s in skip); tot_kept=sum(s[2] for s in skip)
print(f'   键不是 nodeid 的 SKIPPED 条目共 {tot_lost} 条；键是 nodeid 的共 {tot_kept} 条')
for t,l,k in sorted(skip,key=lambda r:-r[1])[:10]: print(f'   {t:38s} lost_keys={l} nodeid_keys={k}')
json.dump({k:[list(x) for x in v] for k,v in res.items()},open(f'{OUT}/idscan.json','w'),ensure_ascii=False,indent=1)
json.dump({'p2p_undercollect':cov,'skipped_identity':skip},open(f'{OUT}/covscan.json','w'),ensure_ascii=False,indent=1)
# 注：本脚本的输出已保存到 runs/env_overnight_20260916/L1_dvc_1/{idscan.txt,idscan.json,covscan.json}
