# 改编自 L1_moto_1/scripts/prescan.py：加入 pandas/modin 特有信号（skip 统计、引擎、编译扩展）
import json,os,re
PKG='L1_modin_pandas'
M=f'runs/env_overnight_20260916/{PKG}/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open(f'docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
def paths(diff):
    return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', diff or '', re.M)))
def is_test(p):
    b=os.path.basename(p)
    return ('/tests/' in p or p.startswith('tests/') or '/test/' in p or '/test_' in p
            or b.startswith('test_') or b=='conftest.py' or b.endswith('_test.py'))
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); v=json.load(open(f'{M}/{tid}/validation.json'))
    tp=paths(g['test_patch']); gp=paths(v.get('golden_patch') or '')
    f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
    r={'repo':g['repo'],'version':g.get('version'),'py':g.get('python_version'),
       'eval_cmd':g.get('eval_cmd'),'base':g['base_commit'],
       'test_patch_paths':tp,'gold_paths':gp,
       'test_patch_nontest':[p for p in tp if not is_test(p)],
       'gold_touches_test':[p for p in gp if is_test(p)],
       'trunc_f2p':[x for x in f2p if x.count('[')!=x.count(']')],
       'trunc_p2p':[x for x in p2p if x.count('[')!=x.count(']')],
       'nonascii_ids':[x for x in f2p+p2p if any(ord(c)>127 for c in x)],
       'n_f2p':len(f2p),'n_p2p':len(p2p),'f2p':f2p,
       'p2p_files':sorted(set(x.split('::')[0] for x in p2p)),
       'f2p_files':sorted(set(x.split('::')[0] for x in f2p))}
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): r[kind]='NO_LOG'; continue
        sm=json.load(open(p))
        from collections import Counter
        r[kind]={'n':len(sm),'verdict_hist':dict(Counter(sm.values())),
                 'f2p_missing':[x for x in f2p if x not in sm],
                 'p2p_missing':[x for x in p2p if x not in sm],
                 'f2p_notpass':{x:sm[x] for x in f2p if x in sm and sm[x]!='PASSED'},
                 'p2p_notpass':{x:sm[x] for x in p2p if x in sm and sm[x]!='PASSED'},
                 'skipped_in_p2p':[x for x in p2p if sm.get(x)=='SKIPPED'],
                 'skipped_total':sum(1 for v in sm.values() if v=='SKIPPED')}
    out[tid]=r
json.dump(out,open(f'runs/env_overnight_20260916/{PKG}/prescan.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print(f"### {tid} [{r['repo']} v{r['version']} py{r['py']}] F2P={r['n_f2p']} P2P={r['n_p2p']}")
    print(f"    tp={r['test_patch_paths']}")
    print(f"    gold={r['gold_paths']}")
    for k in ('test_patch_nontest','gold_touches_test','trunc_f2p','nonascii_ids'):
        if r[k]: print(f"    ! {k}={r[k][:4]}")
    if r['trunc_p2p']: print(f"    ! trunc_p2p n={len(r['trunc_p2p'])} ex={r['trunc_p2p'][:2]}")
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print(f'    ! {kind}=NO_LOG'); continue
        print(f"    {kind}: n={k['n']} hist={k['verdict_hist']} skipped_total={k['skipped_total']}")
        for kk in ('f2p_missing','p2p_missing'):
            if k[kk]: print(f"      ! {kind}.{kk} n={len(k[kk])} {k[kk][:4]}")
        for kk in ('f2p_notpass','p2p_notpass'):
            if k[kk]: print(f"      ! {kind}.{kk} n={len(k[kk])} {list(k[kk].items())[:4]}")
