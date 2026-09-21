import json,os,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
M='runs/env_overnight_20260916/L1_dvc_2/mat'
B='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
ASG=json.load(open(f'{B}/L1_dvc_2/ASSIGNMENT.json'))
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    graded=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    r={}
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
        if not os.path.exists(p): r[kind]='NO_LOG'; continue
        sm=json.load(open(p))
        real={k:v for k,v in sm.items() if '::' in k or k.endswith('.py')}
        noise={k:v for k,v in sm.items() if k not in real}
        ungraded={k:v for k,v in real.items() if k not in graded}
        r[kind]={'n':len(sm),'real':len(real),'noise':sorted(noise.items())[:12],
                 'counts':dict(collections.Counter(real.values())),
                 'ungraded_notpass':{k:v for k,v in ungraded.items() if v!='PASSED'},
                 'ungraded_pass_n':len([k for k,v in ungraded.items() if v=='PASSED'])}
    out[tid]=r
json.dump(out,open('runs/env_overnight_20260916/L1_dvc_2/smstat.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print('###',tid)
    for kind in ('gold','empty'):
        k=r[kind]
        if k=='NO_LOG': print('  ',kind,'NO_LOG'); continue
        print(f"   {kind}: real={k['real']} counts={k['counts']} noise={len(k['noise'])} ungraded_pass={k['ungraded_pass_n']} ungraded_notpass={k['ungraded_notpass']}")
    if r['gold']!='NO_LOG' and r['gold']['noise']: print('    noise_keys:',[n[0] for n in r['gold']['noise']])
