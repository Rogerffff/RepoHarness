import json,os,re
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dask/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ref=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): continue
        sm=json.load(open(p))
        extra={k:v for k,v in sm.items() if k not in ref}
        bogus={k:v for k,v in extra.items() if not k.startswith('dask/')}
        realextra={k:v for k,v in extra.items() if k.startswith('dask/')}
        print(f'{tid}/{kind}: n={len(sm)} ref={len(ref)} extra={len(extra)} bogus={sorted(bogus.items())} real_extra_notpass={ {k:v for k,v in realextra.items() if v!="PASSED"} }')
