# 改编自 L1_moto_1/scripts/collide.py：统计"截断 ID -> 多个完整 ID"的污染对，并区分是否落在 F2P/P2P 常量里
import json,os,re,collections
PKG='L1_modin_pandas'
M=f'runs/env_overnight_20260916/{PKG}/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open(f'docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/{PKG}/ASSIGNMENT.json'))
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    consts=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    f2p=set(g['fail_to_pass'])
    rec={}
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): continue
        full=collections.defaultdict(set)
        for line in open(p,errors='replace'):
            m=pat.match(line.rstrip('\n'))
            if not m: continue
            verdict,rest=m.group(1),m.group(2)
            full[rest.split()[0]].add((rest.strip(),verdict))
        coll={k:sorted(v) for k,v in full.items() if len(v)>1}
        # 只保留会影响判分的：截断键出现在 F2P/P2P 常量里
        scoring={k:v for k,v in coll.items() if k in consts}
        mixed={k:v for k,v in scoring.items() if len({vv[1] for vv in v})>1}
        rec[kind]={'n_collisions_all':len(coll),'n_collisions_in_scoring':len(scoring),
                   'n_mixed_verdict_in_scoring':len(mixed),
                   'mixed_examples':{k:v for k,v in list(mixed.items())[:5]},
                   'scoring_examples':{k:v for k,v in list(scoring.items())[:3]},
                   'f2p_collisions':{k:v for k,v in scoring.items() if k in f2p}}
    out[tid]=rec
    for kind,r in rec.items():
        print(f"{tid}/{kind}: collisions_all={r['n_collisions_all']} in_scoring={r['n_collisions_in_scoring']} mixed_verdict={r['n_mixed_verdict_in_scoring']} f2p={len(r['f2p_collisions'])}")
        for k,v in r['mixed_examples'].items(): print('    MIXED',k,'->',v[:4])
        for k,v in r['f2p_collisions'].items(): print('    F2P-COLL',k,'->',v[:4])
json.dump(out,open(f'runs/env_overnight_20260916/{PKG}/collide.json','w'),ensure_ascii=False,indent=1)
