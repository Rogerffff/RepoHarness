"""R8：同仓库跨题答案泄漏扫描。
把每题 gold 的新增有效行拿去 grep 更晚题目 base 快照的同一文件，
命中比例高说明晚题的初始仓库里直接包含早题的参考解。
用法：python3 crossleak.py （需要 prescan.py 先生成 prescan.json）"""
import json,re,subprocess,os
BASE='runs/env_overnight_20260916/L1_pydantic'
R='runs/env_overnight_20260916/repos/pydantic'
P=json.load(open(f'{BASE}/prescan.json'))
def show(c,p):
    r=subprocess.run(['git','-C',R,'show',f'{c}:{p}'],capture_output=True,text=True)
    return r.stdout if r.returncode==0 else None
rows=[]
for tid,r in P.items():
    raw=json.load(open(f'{BASE}/mat/{tid}/raw.json')); v=json.load(open(f'{BASE}/mat/{tid}/validation.json'))
    added=[l[1:].strip() for l in (v['golden_patch'] or '').split('\n')
           if l.startswith('+') and not l.startswith('+++')]
    added=[a for a in added if len(a)>=15 and not a.startswith('#')]
    rows.append((raw['created_at'],tid,r['base'],r['gold_paths'],added))
rows.sort()
pairs=[]
for i,(ca,ta,ba,ga,aa) in enumerate(rows):
    for cb,tb,bb,gb,ab in rows[i+1:]:
        for f in set(ga)&set(gb):
            src=show(bb,f)
            if src is None: continue
            norm=re.sub(r'\s+','',src)
            hit=[a for a in aa if re.sub(r'\s+','',a) and re.sub(r'\s+','',a) in norm]
            if len(hit)>=max(2,len(aa)//2):
                pairs.append((ta,ca[:10],tb,cb[:10],f,len(hit),len(aa)))
for ta,ca,tb,cb,f,h,n in pairs:
    print(f'{ta}({ca}) gold → {tb}({cb}) base:{f}  {h}/{n} 行命中')
print(f'合计 {len(pairs)} 对')
