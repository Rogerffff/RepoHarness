"""复验两件事：
1) 所有 F2P/P2P 的 case 名是否与 mypy/test/**.py 里的函数/类名或文件名构成子串关系（会被 -k 误选）；
2) 每个评分 case 的宿主 .test 文件是否在本题 test_patch 里（不在 = 既不被 eval 还原也不受 hygiene 保护）。
只读操作：git grep / git ls-tree。"""
import json,subprocess,re,os
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/mypy'
RUN='${REPO_ROOT}/runs/env_overnight_20260916/L1_mypy_2'
PRE=json.load(open(f'{RUN}/prescan.json')); KS=json.load(open(f'{RUN}/kscan.json'))
cache={}
def pynames(commit):
    if commit in cache: return cache[commit]
    p=subprocess.run(['git','-C',R,'grep','-n','-E','^\\s*(def|class) ',commit,'--','mypy/test/'],capture_output=True,text=True)
    names={m.group(1) for m in (re.search(r':\s*(?:def|class)\s+(\w+)',l) for l in p.stdout.split('\n')) if m}
    q=subprocess.run(['git','-C',R,'ls-tree','-r','--name-only',commit,'--','mypy/test/'],capture_output=True,text=True)
    files={x.split('/')[-1] for x in q.stdout.split('\n') if x.endswith('.py')}
    cache[commit]=(names,files); return cache[commit]
coll=[]; unprot=[]
for tid,r in PRE.items():
    names,files=pynames(r['base_commit'])
    for s in sorted({x.split('::')[-1] for x in r['f2p']+r['p2p']}):
        hit=[n for n in names if s in n and n!=s]+[f for f in files if s in f]
        if hit: coll.append((tid,s,hit[:5]))
    for row in KS[tid]['rows']:
        if row['home_files_in_base'] and not any(row['home_protected']):
            unprot.append((tid,row['case'],row['home_files_in_base']))
print('== 选择器与 mypy/test/*.py 名字的子串冲突 ==')
print('\n'.join(map(str,coll)) or '  无')
print('== 评分 case 的宿主 .test 文件不在 test_patch（不受保护） ==')
print('\n'.join(map(str,unprot)) or '  无')
