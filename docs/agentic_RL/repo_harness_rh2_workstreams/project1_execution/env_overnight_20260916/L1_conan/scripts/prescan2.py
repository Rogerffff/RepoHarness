# conan-aware prescan: conan test files live under conans/test/ (singular) and many end with _test.py
import json,os,re
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/ASSIGNMENT.json'))
def paths(diff): return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff, re.M)))
def is_test(p):
    b=os.path.basename(p)
    return (p.startswith('conans/test/') or p.startswith('tests/') or b.startswith('test_')
            or b.endswith('_test.py') or b=='conftest.py')
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    r={'base':g['base_commit'],'version':g.get('version'),'py':g.get('python_version'),
       'eval_cmd':g.get('eval_cmd'),
       'test_patch_paths':tp,'gold_paths':gp,
       'test_patch_nontest':[p for p in tp if not is_test(p)],
       'gold_touches_test':[p for p in gp if is_test(p)],
       'f2p':g['fail_to_pass'],'p2p':g['pass_to_pass'],
       'trunc_f2p':[x for x in g['fail_to_pass'] if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in g['pass_to_pass'] if x.count('[')!=x.count(']')],
       'nonascii':[x for x in g['fail_to_pass']+g['pass_to_pass'] if any(ord(c)>127 for c in x)],
       'ws_in_id':[x for x in g['fail_to_pass']+g['pass_to_pass'] if re.search(r'\s',x)]}
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): r[kind]='NO_LOG'; continue
        sm=json.load(open(p))
        from collections import Counter
        r[kind]={'n':len(sm),'verdict_counts':dict(Counter(sm.values())),
                 'skipped':[k for k,vv in sm.items() if vv=='SKIPPED'][:20],
                 'n_skipped':sum(1 for vv in sm.values() if vv=='SKIPPED'),
                 'f2p_missing':[x for x in r['f2p'] if x not in sm],
                 'p2p_missing':[x for x in r['p2p'] if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in r['f2p'] if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in r['p2p'] if x in sm and sm[x]!='PASSED'}}
    out[tid]=r
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/prescan2.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"### {tid} v={r['version']} py={r['py']}")
    print(f"    gold={r['gold_paths']}")
    print(f"    tp={r['test_patch_paths']}  nontest={r['test_patch_nontest']} goldtest={r['gold_touches_test']}")
    print(f"    f2p={len(r['f2p'])} p2p={len(r['p2p'])} trunc_f2p={r['trunc_f2p']} n_trunc_p2p={len(r['trunc_p2p'])} ws_ids={len(r['ws_in_id'])}")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f'    {kind}: NO_LOG'); continue
        print(f"    {kind}: n={k['n']} {k['verdict_counts']} skipped={k['n_skipped']} f2p_miss={len(k['f2p_missing'])} p2p_miss={len(k['p2p_missing'])} f2p_np={len(k['f2p_notpass'])} p2p_np={len(k['p2p_notpass'])}")
    print(f"    eval_cmd={r['eval_cmd']}")
