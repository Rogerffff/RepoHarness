import json,os,re
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/ASSIGNMENT.json'))
def paths(diff): return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
def istest(p):
    b=os.path.basename(p)
    return p.startswith('tests/') or '/test_' in p or b.startswith('test_') or b=='conftest.py'
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    pub=json.load(open(f'{M}/{tid}/public.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    r={'base_commit':g['base_commit'],'version':g.get('version'),'py':g.get('python_version'),
       'eval_cmd':g.get('eval_cmd'),'image':pub.get('image'),'workdir':pub.get('workdir'),
       'allowed_tools':pub.get('allowed_tools'),'public_hints':pub.get('public_hints'),
       'test_patch_paths':tp,'gold_paths':gp,
       'test_patch_nontest':[p for p in tp if not istest(p)],
       'gold_touches_test':[p for p in gp if istest(p)],
       'trunc_f2p':[x for x in f2p if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in p2p if x.count('[')!=x.count(']')],
       'nonascii_ids':[x for x in f2p+p2p if any(ord(c)>127 for c in x)],
       'f2p':f2p,'n_p2p':len(p2p),
       'p2p_files':sorted(set(x.split('::')[0] for x in p2p)),
       'f2p_files':sorted(set(x.split('::')[0] for x in f2p)),
       'ps_len':len(pub['problem_statement']),
       'ps_dup': pub['problem_statement'][:len(pub['problem_statement'])//2]==pub['problem_statement'][len(pub['problem_statement'])//2:] if len(pub['problem_statement'])%2==0 else False,
       }
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
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"### {tid} v={r['version']} py={r['py']} ps={r['ps_len']}")
    print(f"    gold_paths={r['gold_paths']}")
    print(f"    tp_paths={r['test_patch_paths']}")
    print(f"    f2p_files={r['f2p_files']} p2p_files={r['p2p_files'][:6]}{'...' if len(r['p2p_files'])>6 else ''} n_p2p={r['n_p2p']}")
    print(f"    eval_cmd={r['eval_cmd']}")
    fl=[]
    if r['test_patch_nontest']: fl.append(f"TP_NONTEST={r['test_patch_nontest']}")
    if r['gold_touches_test']: fl.append(f"GOLD_TEST={r['gold_touches_test']}")
    if r['trunc_f2p']: fl.append(f"TRUNC_F2P={r['trunc_f2p']}")
    if r['trunc_p2p']: fl.append(f"TRUNC_P2P={len(r['trunc_p2p'])}:{r['trunc_p2p'][:2]}")
    if r['nonascii_ids']: fl.append(f"NONASCII={r['nonascii_ids'][:2]}")
    if r['ps_dup']: fl.append("PS_DUPLICATED")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': fl.append(f'{kind}=NO_LOG'); continue
        if k['f2p_missing']: fl.append(f"{kind}.f2p_missing={k['f2p_missing'][:3]}")
        if k['p2p_missing']: fl.append(f"{kind}.p2p_missing={k['p2p_missing'][:3]}")
        if k['f2p_notpass']: fl.append(f"{kind}.f2p_notpass={list(k['f2p_notpass'].items())[:3]}")
        if k['p2p_notpass']: fl.append(f"{kind}.p2p_notpass={list(k['p2p_notpass'].items())[:3]}")
    for f in fl: print('    !',f)
