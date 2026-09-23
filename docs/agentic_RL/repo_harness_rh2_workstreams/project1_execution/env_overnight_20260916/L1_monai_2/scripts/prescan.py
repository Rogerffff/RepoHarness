import json,os,re
PKG='L1_monai_2'
M=f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open(f'${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff, re.M)))
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    p=json.load(open(f'{M}/{tid}/public.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    nontest=[x for x in tp if not (x.startswith('tests/') or '/test_' in x or os.path.basename(x).startswith('test_') or x.endswith('conftest.py'))]
    goldtest=[x for x in gp if x.startswith('tests/') or '/test_' in x or os.path.basename(x).startswith('test_')]
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    ps=p['problem_statement']
    half=len(ps)//2
    dup = len(ps)%2==0 and ps[:half].strip()==ps[half:].strip()
    r={'version':g.get('version'),'py':g.get('python_version'),'eval_cmd':g.get('eval_cmd'),
       'base':g['base_commit'],'test_patch_paths':tp,'gold_paths':gp,'test_patch_nontest':nontest,
       'gold_touches_test':goldtest,'f2p_n':len(f2p),'p2p_n':len(p2p),'f2p':f2p,
       'ps_chars':len(ps),'ps_dup_halves':dup,'hints_chars':len(raw.get('hints_text') or ''),
       'public_hints':p.get('public_hints'),'allowed_tools':p.get('allowed_tools'),'workdir':p.get('workdir'),
       'trunc_f2p':[x for x in f2p if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in p2p if x.count('[')!=x.count(']')],
       'nonascii':[x for x in f2p+p2p if any(ord(c)>127 for c in x)],
       'ps_has_url':re.findall(r'https?://\S+',ps)[:6],
       'ps_has_img':re.findall(r'!\[[^\]]*\]\([^)]*\)|<img',ps)[:4]}
    for kind in ('gold','empty'):
        sp=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(sp): r[kind]='NO_LOG'; continue
        sm=json.load(open(sp))
        r[kind]={'n':len(sm),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'},
                 'skipped_all':sum(1 for vv in sm.values() if vv=='SKIPPED')}
    out[tid]=r
json.dump(out,open(f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/scan/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"### {tid} v{r['version']} py{r['py']} f2p={r['f2p_n']} p2p={r['p2p_n']} ps={r['ps_chars']}ch hints={r['hints_chars']}ch")
    print(f"    tp={r['test_patch_paths']}")
    print(f"    gold={r['gold_paths']}")
    print(f"    eval_cmd={r['eval_cmd']}")
    for k in ('test_patch_nontest','gold_touches_test','trunc_f2p','trunc_p2p','nonascii','ps_has_url','ps_has_img'):
        if r[k]: print(f"    ! {k}={r[k]}")
    if r['ps_dup_halves']: print("    ! PS_DUP_HALVES")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f'    ! {kind}=NO_LOG'); continue
        msg=f"    {kind}: n={k['n']} skipped={k['skipped_all']}"
        if k['f2p_missing']: msg+=f" F2P_MISS={k['f2p_missing'][:3]}"
        if k['p2p_missing']: msg+=f" P2P_MISS={k['p2p_missing'][:3]}"
        if k['f2p_notpass']: msg+=f" F2P_BAD={list(k['f2p_notpass'].items())[:3]}"
        if k['p2p_notpass']: msg+=f" P2P_BAD={list(k['p2p_notpass'].items())[:3]}"
        print(msg)
