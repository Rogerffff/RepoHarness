import json,os,re
M='runs/env_overnight_20260916/L1_dask/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
SIG={d['instance_id']:d for d in json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/task_signals_swegym.json'))}
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    p=json.load(open(f'{M}/{tid}/public.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    nontest=[x for x in tp if not (x.startswith('dask/tests/') or '/tests/' in x or os.path.basename(x).startswith('test_') or os.path.basename(x)=='conftest.py')]
    goldtest=[x for x in gp if '/tests/' in x or os.path.basename(x).startswith('test_') or os.path.basename(x)=='conftest.py']
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    r={'base':g['base_commit'],'version':g.get('version'),'py':g.get('python_version'),'eval_cmd':g.get('eval_cmd'),
       'image':p.get('image'),'workdir':p.get('workdir'),
       'tp_paths':tp,'gold_paths':gp,'tp_nontest':nontest,'gold_touches_test':goldtest,
       'n_f2p':len(f2p),'n_p2p':len(p2p),'f2p':f2p,
       'trunc_f2p':[x for x in f2p if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in p2p if x.count('[')!=x.count(']')],
       'nonascii':[x for x in f2p+p2p if any(ord(c)>127 for c in x)],
       'ps_len':len(p.get('problem_statement') or ''),
       'hints_len':len(raw.get('hints_text') or ''),
       'gold_len':len(v.get('golden_patch') or ''),
       }
    s=SIG.get(tid) or {}
    r['signals']=s
    for kind in ('gold','empty'):
        sp=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(sp): r[kind]='NO_LOG'; continue
        sm=json.load(open(sp))
        r[kind]={'n':len(sm),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'},
                 'skipped_any':sorted([k for k,vv in sm.items() if vv in ('SKIPPED','XFAIL','XPASS')])[:20],
                 'n_skipped':sum(1 for vv in sm.values() if vv=='SKIPPED')}
    out[tid]=r
json.dump(out,open('runs/env_overnight_20260916/L1_dask/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"== {tid} ver={r['version']} py={r['py']} base={r['base'][:10]} F2P={r['n_f2p']} P2P={r['n_p2p']} ps={r['ps_len']} hints={r['hints_len']} gold={r['gold_len']}")
    print(f"   eval_cmd={r['eval_cmd']!r}")
    print(f"   tp={r['tp_paths']}")
    print(f"   gold={r['gold_paths']}")
    if r['tp_nontest']: print(f"   ** TP_NONTEST={r['tp_nontest']}")
    if r['gold_touches_test']: print(f"   ** GOLD_TOUCHES_TEST={r['gold_touches_test']}")
    if r['trunc_f2p'] or r['trunc_p2p']: print(f"   ** TRUNC f2p={r['trunc_f2p'][:3]} p2p={r['trunc_p2p'][:3]}")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f"   {kind}: NO_LOG"); continue
        print(f"   {kind}: n={k['n']} f2p_miss={len(k['f2p_missing'])} p2p_miss={len(k['p2p_missing'])} f2p_np={len(k['f2p_notpass'])} p2p_np={len(k['p2p_notpass'])} skipped={k['n_skipped']}")
        if k['f2p_missing']: print('      MISSF2P',k['f2p_missing'][:4])
        if k['f2p_notpass']: print('      BADF2P',list(k['f2p_notpass'].items())[:4])
        if k['p2p_notpass']: print('      BADP2P',list(k['p2p_notpass'].items())[:4])
