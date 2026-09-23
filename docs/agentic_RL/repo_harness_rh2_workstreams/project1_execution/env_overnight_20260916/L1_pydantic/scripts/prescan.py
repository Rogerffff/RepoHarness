import json,os,re,unicodedata
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_pydantic/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/ASSIGNMENT.json'))
SIG=json.load(open(f'{M}/signals.json'))
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
def is_test(p):
    b=os.path.basename(p)
    return p.startswith('tests/') or '/test_' in p or b.startswith('test_') or b=='conftest.py'
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    pub=json.load(open(f'{M}/{tid}/public.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    nontest=[p for p in tp if not is_test(p)]
    goldtest=[p for p in gp if is_test(p)]
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    ctrl=[x for x in f2p+p2p if any(ord(c)<32 or ord(c)==127 for c in x)]
    nonascii=[x for x in f2p+p2p if any(ord(c)>127 for c in x)]
    trunc=[x for x in f2p+p2p if x.count('[')!=x.count(']')]
    r={'base':g['base_commit'],'version':g.get('version'),'py':g.get('python_version'),
       'eval_cmd':g.get('eval_cmd'),'image':pub.get('image'),'workdir':pub.get('workdir'),
       'ps_chars':len(pub['problem_statement']),
       'test_patch_paths':tp,'gold_paths':gp,'tp_nontest':nontest,'gold_touches_test':goldtest,
       'f2p':f2p,'n_p2p':len(p2p),'ctrl_ids':ctrl,'nonascii_ids':nonascii,'trunc_ids':trunc,
       'sig':SIG[tid]}
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): r[kind]='NO_LOG'; continue
        sm=json.load(open(p))
        r[kind]={'n':len(sm),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'}}
    out[tid]=r
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_pydantic/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    s=r['sig']
    print(f"### {tid} v={r['version']} py={r['py']} ps={r['ps_chars']}c f2p={len(r['f2p'])} p2p={r['n_p2p']} in_e2={s['in_e2']} frag={s['fragile_reference_id']} ds={s['deepseek_candidate_oracle']}")
    print(f"    stage1: gold={s['stage1']['gold']} empty={s['stage1']['empty']}")
    print(f"    tp={r['test_patch_paths']}  gold={r['gold_paths']}")
    if r['tp_nontest']: print('    ! TP_NONTEST=',r['tp_nontest'])
    if r['gold_touches_test']: print('    ! GOLD_TEST=',r['gold_touches_test'])
    if r['ctrl_ids']: print('    ! CTRL=',[repr(x) for x in r['ctrl_ids'][:3]])
    if r['nonascii_ids']: print('    ! NONASCII=',[repr(x) for x in r['nonascii_ids'][:3]])
    if r['trunc_ids']: print('    ! TRUNC=',r['trunc_ids'][:3])
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f'    ! {kind}=NO_LOG'); continue
        if k['f2p_missing']: print(f"    ! {kind}.f2p_missing={k['f2p_missing'][:3]}")
        if k['p2p_missing']: print(f"    ! {kind}.p2p_missing({len(k['p2p_missing'])})={k['p2p_missing'][:3]}")
        if k['f2p_notpass']: print(f"    ! {kind}.f2p_notpass={list(k['f2p_notpass'].items())[:3]}")
        if k['p2p_notpass']: print(f"    ! {kind}.p2p_notpass({len(k['p2p_notpass'])})={list(k['p2p_notpass'].items())[:3]}")
