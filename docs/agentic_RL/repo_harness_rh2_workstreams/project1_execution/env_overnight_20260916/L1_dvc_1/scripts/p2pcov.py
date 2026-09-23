# P2P 覆盖率：gold 侧实跑 status_map 里 PASSED 的条目有多少进了 P2P/F2P
import json,os
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/ASSIGNMENT.json'))
res={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ids=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): continue
        sm=json.load(open(p))
        if kind=='gold':
            passed=[k for k,v in sm.items() if v=='PASSED']
            notsel=[k for k in passed if k not in ids]
            other={}
            for k,v in sm.items():
                other[v]=other.get(v,0)+1
            res[tid]={'gold_total':len(sm),'gold_status_hist':other,'gold_passed':len(passed),
                      'graded':len(ids),'passed_not_graded':len(notsel),'sample_not_graded':notsel[:8]}
for tid,r in res.items():
    print(f"{tid:26s} gold_run={r['gold_total']:4d} passed={r['gold_passed']:4d} graded={r['graded']:3d} passed_but_ungraded={r['passed_not_graded']:4d} hist={r['gold_status_hist']}")
    if r['sample_not_graded']: print('     e.g.',r['sample_not_graded'][:4])
json.dump(res,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1/p2pcov.json','w'),ensure_ascii=False,indent=1)
