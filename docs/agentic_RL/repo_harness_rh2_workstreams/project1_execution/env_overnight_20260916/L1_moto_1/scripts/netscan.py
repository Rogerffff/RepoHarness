import json,os,re,subprocess
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/moto'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_moto_1/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_1/ASSIGNMENT.json'))
def show(commit,path):
    p=subprocess.run(['git','-C',R,'show',f'{commit}:{path}'],capture_output=True,text=True)
    return p.stdout if p.returncode==0 else None
def marked(src):
    """return set of test names decorated with @pytest.mark.network (function or class)"""
    out=set(); lines=src.split('\n'); pend=False
    for i,l in enumerate(lines):
        s=l.strip()
        if s.startswith('@pytest.mark.network') or s=='@mock.patch' and False: pend=True; continue
        if s.startswith('@'): continue
        m=re.match(r'(?:async )?def (\w+)\(',s) or re.match(r'class (\w+)',s)
        if m:
            if pend: out.add(m.group(1))
            pend=False
        elif s and not s.startswith('#'):
            pend=False
    return out
res={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    base=g['base_commit']; ids=g['fail_to_pass']+g['pass_to_pass']
    files={}
    for x in ids:
        f=x.split('::')[0]; files.setdefault(f,[]).append(x)
    hits=[]
    for f,xs in files.items():
        src=show(base,f)
        if src is None: hits.append(('FILE_MISSING',f)); continue
        nm=marked(src)
        for x in xs:
            rest=x.split('::')[1:]
            if rest and (rest[0].split('[')[0] in nm or (len(rest)>1 and rest[1].split('[')[0] in nm)):
                hits.append(('NETWORK',x))
    res[tid]=hits
    if hits: print(tid, len(hits), hits[:8])
    else: print(tid,'clean')
json.dump(res,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_moto_1/netscan.json','w'),ensure_ascii=False,indent=1)
