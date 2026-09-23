import json,subprocess,re,os
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/dvc'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_2/mat'
B='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
ASG=json.load(open(f'{B}/L1_dvc_2/ASSIGNMENT.json'))
out={}
for tid in ASG['tasks']:
    num=tid.split('-')[-1]
    g=json.load(open(f'{M}/{tid}/grading.json'))
    base=g['base_commit']
    # find commit whose subject mentions (#num)
    p=subprocess.run(['git','-C',R,'log','--all','--oneline','--grep',f'(#{num})'],capture_output=True,text=True)
    cands=p.stdout.strip().split('\n') if p.stdout.strip() else []
    res={'base':base,'pr_commits':cands[:4]}
    # the child of base on the main path
    p2=subprocess.run(['git','-C',R,'log','--oneline','--reverse','--ancestry-path',f'{base}..origin/main'],capture_output=True,text=True)
    kids=p2.stdout.strip().split('\n')[:1]
    res['first_child']=kids
    # stat of the PR commit(s)
    for c in cands[:2]:
        sha=c.split()[0]
        p3=subprocess.run(['git','-C',R,'show','--stat','--format=%H%n%s','-m','--first-parent',sha],capture_output=True,text=True)
        res.setdefault('stats',{})[sha]=p3.stdout[:1400]
    out[tid]=res
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_2/upstream.json','w'),ensure_ascii=False,indent=1)
for tid,r in out.items():
    print('###',tid,'base',r['base'][:9]); print('  PR:',r['pr_commits']); print('  child:',r['first_child'])
