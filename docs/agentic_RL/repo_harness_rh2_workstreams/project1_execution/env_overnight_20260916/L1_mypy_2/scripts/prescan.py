import json,os,re
PKG='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_mypy_2/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
SIG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/task_signals_swegym.json'))
ids=json.load(open(f'{PKG}/ASSIGNMENT.json'))['tasks']
sig = {s['instance_id']:s for s in SIG} if isinstance(SIG,list) else SIG
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
out={}
for tid in ids:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    p=json.load(open(f'{M}/{tid}/public.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or v.get('patch') or '')
    def istest(x): return x.startswith('test-data/') or x.startswith('tests/') or '/test' in os.path.basename(x) or os.path.basename(x).startswith('test') or x.endswith('conftest.py') or '/test/' in x
    nontest=[x for x in tp if not istest(x)]
    goldtest=[x for x in gp if istest(x)]
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    # case names added in test_patch
    added_cases=sorted(set(re.findall(r'^\+\[case (\w+)\]', g['test_patch'], re.M)))
    ctx_cases=sorted(set(re.findall(r'^ \[case (\w+)\]', g['test_patch'], re.M)))
    ps=p['problem_statement']
    r={'test_patch_paths':tp,'gold_paths':gp,'test_patch_nontest':nontest,'gold_touches_test':goldtest,
       'f2p':f2p,'p2p':p2p,'n_f2p':len(f2p),'n_p2p':len(p2p),
       'eval_cmd':g.get('eval_cmd'),'version':g.get('version'),'py':g.get('python_version'),
       'base_commit':g['base_commit'],'added_cases':added_cases,'ctx_cases':ctx_cases,
       'ps_len':len(ps),'ps_has_url':bool(re.search(r'https?://',ps)),
       'ps_dup_half': ps[:len(ps)//2].strip()==ps[len(ps)//2:].strip() if len(ps)>40 else False,
       'hints_len':len(raw.get('hints_text') or ''),
       'sig': sig.get(tid)}
    for kind in ('gold','empty'):
        sp=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(sp): r[kind]='NO_LOG'; continue
        sm=json.load(open(sp))
        r[kind]={'n':len(sm),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'},
                 'extra':[x for x in sm if x not in f2p and x not in p2p]}
    out[tid]=r
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_mypy_2/prescan.json','w'),ensure_ascii=False,indent=1)
for tid in ids:
    r=out[tid]
    print(f"### {tid} v{r['version']} py{r['py']} base={r['base_commit'][:9]} eval={r['eval_cmd']!r}")
    print(f"    tp={r['test_patch_paths']} gold={r['gold_paths']}")
    print(f"    F2P={r['n_f2p']} P2P={r['n_p2p']} ps_len={r['ps_len']} url={r['ps_has_url']} dup={r['ps_dup_half']} hints={r['hints_len']}")
    if nontest:=r['test_patch_nontest']: print('    ! TP_NONTEST',nontest)
    if r['gold_touches_test']: print('    ! GOLD_TEST',r['gold_touches_test'])
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f'    ! {kind}=NO_LOG'); continue
        msg=[]
        if k['f2p_missing']: msg.append(f"f2p_missing={k['f2p_missing'][:3]}")
        if k['p2p_missing']: msg.append(f"p2p_missing={len(k['p2p_missing'])}:{k['p2p_missing'][:2]}")
        if k['f2p_notpass']: msg.append(f"f2p_notpass={list(k['f2p_notpass'].items())[:3]}")
        if k['p2p_notpass']: msg.append(f"p2p_notpass={list(k['p2p_notpass'].items())[:3]}")
        if k['extra']: msg.append(f"extra_run={len(k['extra'])}:{k['extra'][:2]}")
        print(f"    {kind}: n={k['n']} "+ ('; '.join(msg) if msg else 'all-ok'))
