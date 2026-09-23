import json,os,re
M='runs/env_overnight_20260916/L1_dvc_2/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
BASE='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
ASG=json.load(open(f'{BASE}/L1_dvc_2/ASSIGNMENT.json'))
SIG={d['instance_id']:d for d in json.load(open(f'{BASE}/task_signals_swegym.json'))}
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
def istest(p):
    b=os.path.basename(p)
    return p.startswith('tests/') or '/tests/' in p or b.startswith('test_') or b=='conftest.py' or b.endswith('_test.py')
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    p=json.load(open(f'{M}/{tid}/public.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    r={'base_commit':g['base_commit'],'version':g.get('version'),'py':g.get('python_version'),
       'eval_cmd':g.get('eval_cmd'),'image':p.get('image'),'workdir':p.get('workdir'),
       'ps_chars':len(p['problem_statement']),'hints_chars':len(raw.get('hints_text') or ''),
       'public_hints':p.get('public_hints'),'allowed_tools':p.get('allowed_tools'),
       'test_patch_paths':tp,'gold_paths':gp,
       'test_patch_nontest':[x for x in tp if not istest(x)],
       'gold_touches_test':[x for x in gp if istest(x)],
       'f2p':f2p,'n_f2p':len(f2p),'n_p2p':len(p2p),'p2p_sample':p2p[:5],
       'trunc_f2p':[x for x in f2p if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in p2p if x.count('[')!=x.count(']')],
       'nonascii':[x for x in f2p+p2p if any(ord(c)>127 for c in x)],
       'signals':{k:SIG[tid][k] for k in ('in_e2','fragile_reference_id','stage1','deepseek_candidate_oracle') if tid in SIG and k in SIG[tid]},
      }
    for kind in ('gold','empty'):
        sp=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(sp): r[kind]='NO_LOG'; continue
        sm=json.load(open(sp))
        r[kind]={'n':len(sm),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'}}
    out[tid]=r
json.dump(out,open('runs/env_overnight_20260916/L1_dvc_2/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"### {tid} base={r['base_commit'][:10]} ver={r['version']} py={r['py']} ps={r['ps_chars']} hints={r['hints_chars']} f2p={r['n_f2p']} p2p={r['n_p2p']}")
    print(f"    eval_cmd={r['eval_cmd']}")
    print(f"    tp={r['test_patch_paths']}")
    print(f"    gp={r['gold_paths']}")
    print(f"    sig={r['signals']}")
    fl=[]
    if r['test_patch_nontest']: fl.append(f"TP_NONTEST={r['test_patch_nontest']}")
    if r['gold_touches_test']: fl.append(f"GOLD_TEST={r['gold_touches_test']}")
    if r['trunc_f2p']: fl.append(f"TRUNC_F2P={r['trunc_f2p']}")
    if r['trunc_p2p']: fl.append(f"TRUNC_P2P={len(r['trunc_p2p'])}")
    if r['nonascii']: fl.append(f"NONASCII={r['nonascii'][:2]}")
    if r['n_p2p']==0: fl.append('P2P_EMPTY')
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': fl.append(f'{kind}=NO_LOG'); continue
        if k['f2p_missing']: fl.append(f"{kind}.f2p_missing={k['f2p_missing'][:3]}")
        if k['p2p_missing']: fl.append(f"{kind}.p2p_missing({len(k['p2p_missing'])})={k['p2p_missing'][:3]}")
        if k['f2p_notpass']: fl.append(f"{kind}.f2p_notpass={list(k['f2p_notpass'].items())[:3]}")
        if k['p2p_notpass']: fl.append(f"{kind}.p2p_notpass({len(k['p2p_notpass'])})={list(k['p2p_notpass'].items())[:3]}")
    for f in fl: print('    !',f)
