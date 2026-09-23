import json,os,re,unicodedata
M='runs/env_overnight_20260916/L1_conan/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/ASSIGNMENT.json'))
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff, re.M)))
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    nontest=[p for p in tp if not (p.startswith('tests/') or '/test_' in p or os.path.basename(p).startswith('test_') or p.endswith('conftest.py'))]
    goldtest=[p for p in gp if p.startswith('tests/') or '/test_' in p or os.path.basename(p).startswith('test_')]
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    truncF=[x for x in f2p if x.count('[')!=x.count(']')]
    truncP=[x for x in p2p if x.count('[')!=x.count(']')]
    nonascii=[x for x in f2p+p2p if any(ord(c)>127 for c in x)]
    r={'test_patch_paths':tp,'gold_paths':gp,'test_patch_nontest':nontest,'gold_touches_test':goldtest,
       'trunc_f2p':truncF,'trunc_p2p':truncP,'nonascii_ids':nonascii,'f2p':f2p,'n_p2p':len(p2p),
       'eval_cmd':g.get('eval_cmd'),'version':g.get('version'),'py':g.get('python_version')}
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
json.dump(out,open('runs/env_overnight_20260916/L1_conan/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    flags=[]
    if r['test_patch_nontest']: flags.append(f"TP_NONTEST={r['test_patch_nontest']}")
    if r['gold_touches_test']: flags.append(f"GOLD_TEST={r['gold_touches_test']}")
    if r['trunc_f2p']: flags.append(f"TRUNC_F2P={r['trunc_f2p']}")
    if r['trunc_p2p']: flags.append(f"TRUNC_P2P={len(r['trunc_p2p'])}:{r['trunc_p2p'][:2]}")
    if r['nonascii_ids']: flags.append(f"NONASCII={r['nonascii_ids'][:2]}")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': flags.append(f'{kind}=NO_LOG'); continue
        if k['f2p_missing']: flags.append(f"{kind}.f2p_missing={k['f2p_missing'][:3]}")
        if k['p2p_missing']: flags.append(f"{kind}.p2p_missing={k['p2p_missing'][:3]}")
        if k['f2p_notpass']: flags.append(f"{kind}.f2p_notpass={list(k['f2p_notpass'].items())[:3]}")
        if k['p2p_notpass']: flags.append(f"{kind}.p2p_notpass={list(k['p2p_notpass'].items())[:3]}")
    print(f"### {tid}  gold_paths={r['gold_paths']}")
    for f in flags: print('    !',f)
