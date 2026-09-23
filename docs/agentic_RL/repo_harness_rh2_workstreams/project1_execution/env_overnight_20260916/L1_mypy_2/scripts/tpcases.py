"""把 test_patch 的每个改动行归属到所在 [case X]，用 base 文件内容定位。"""
import json,sys,re,subprocess
R='runs/env_overnight_20260916/repos/mypy'
M='runs/env_overnight_20260916/L1_mypy_2/mat'
PRE=json.load(open('runs/env_overnight_20260916/L1_mypy_2/prescan.json'))
tid=sys.argv[1]
g=json.load(open(f'{M}/{tid}/grading.json')); base=PRE[tid]['base_commit']
diff=g['test_patch']
cur=None; oldln=0
res={}   # path -> {case: {'add':n,'del':n,'new':bool}}
basecache={}
def baselines(path):
    if path not in basecache:
        p=subprocess.run(['git','-C',R,'show',f'{base}:{path}'],capture_output=True,text=True)
        basecache[path]=p.stdout.split('\n') if p.returncode==0 else None
    return basecache[path]
path=None
for line in diff.split('\n'):
    m=re.match(r'^diff --git a/(\S+) b/',line)
    if m: path=m.group(1); res.setdefault(path,{}); continue
    m=re.match(r'^@@ -(\d+)(?:,(\d+))? \+',line)
    if m:
        oldln=int(m.group(1))
        bl=baselines(path)
        cur='<unknown>'
        if bl:
            for i in range(min(oldln,len(bl))-1,-1,-1):
                mm=re.match(r'^\[case (\w+)',bl[i])
                if mm: cur=mm.group(1); break
        continue
    if path is None or line.startswith('---') or line.startswith('+++'): continue
    if line.startswith('+'):
        mm=re.match(r'^\+\[case (\w+)',line)
        if mm: cur=mm.group(1); res[path].setdefault(cur,{'add':0,'del':0,'new':True})
        d=res[path].setdefault(cur,{'add':0,'del':0,'new':False}); d['add']+=1
    elif line.startswith('-'):
        d=res[path].setdefault(cur,{'add':0,'del':0,'new':False}); d['del']+=1
    elif line.startswith(' '):
        mm=re.match(r'^ \[case (\w+)',line)
        if mm: cur=mm.group(1)
        oldln+=1
f2pc={x.split('::')[-1] for x in PRE[tid]['f2p']}
p2pc={x.split('::')[-1] for x in PRE[tid]['p2p']}
allc=[]
for path,cases in res.items():
    for c,d in cases.items():
        allc.append((path,c,d))
print(f'--- {tid}: test_patch 改动涉及 {len(allc)} 个 case，F2P {len(f2pc)} 个 case 名，P2P {len(p2pc)} 个')
for path,c,d in allc:
    tag = 'F2P' if c in f2pc else ('P2P' if c in p2pc else '***UNGRADED***')
    nw='NEW' if d['new'] else '   '
    print(f'  {tag:15s} {nw} +{d["add"]:<3d} -{d["del"]:<3d} {c}  ({path})')
ungraded=[(p,c) for p,c,d in allc if c not in f2pc and c not in p2pc]
print(f'>>> 改了但未参与评分的 case 数 = {len(ungraded)}')
