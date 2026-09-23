"""对每题的 F2P/P2P 逐条判断：该用例是否被 pytest.importorskip / mark.skipif 守卫。
做法：从 base 树取出测试文件（test_patch 只追加/改测试体，不改模块级守卫，故用 base 足够），
按顶层 def/class 切段，找出每条参考 ID 对应的函数体，扫描体内的 importorskip / skipif，
并单独列出模块级 importorskip（影响整文件）。"""
import json,os,re,subprocess,collections
R='${REPO_ROOT}/runs/env_overnight_20260916/repos/dask'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dask/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
def show(c,p):
    r=subprocess.run(['git','-C',R,'show',f'{c}:{p}'],capture_output=True,text=True)
    return r.stdout if r.returncode==0 else None
mod_pat=re.compile(r'importorskip\(\s*["\']([^"\']+)')
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json')); base=g['base_commit']
    ids=g['fail_to_pass']+g['pass_to_pass']
    f2p=set(g['fail_to_pass'])
    byfile=collections.defaultdict(list)
    for x in ids: byfile[x.split('::')[0]].append(x)
    rep={'module_guards':[], 'guarded_refs':{}, 'n_ref':len(ids)}
    for fpath,xs in byfile.items():
        src=show(base,fpath)
        if src is None: rep['module_guards'].append(f'{fpath}: NOT IN BASE'); continue
        lines=src.split('\n')
        # module-level guards (top-level statements, col 0)
        for i,l in enumerate(lines):
            if 'importorskip' in l and not l.startswith((' ','\t')):
                rep['module_guards'].append(f'{fpath}:{i+1}: {l.strip()}')
        # split top-level defs
        bounds=[]
        for i,l in enumerate(lines):
            m=re.match(r'(?:async )?def (\w+)\(',l) or re.match(r'class (\w+)',l)
            if m and not l.startswith((' ','\t')): bounds.append((i,m.group(1)))
        bounds.append((len(lines),None))
        body={}
        for (s,name),(e,_) in zip(bounds,bounds[1:]):
            if name: body[name]=(s,'\n'.join(lines[s:e]))
        for x in xs:
            fn=x.split('::')[-1].split('[')[0]
            if fn not in body:
                # maybe Class::method form
                parts=x.split('::')
                fn2=parts[1] if len(parts)>2 else fn
                if fn2 not in body: continue
                fn=fn2
            s,b=body[fn]
            guards=[]
            for mm in mod_pat.finditer(b): guards.append(('importorskip',mm.group(1)))
            for mm in re.finditer(r'@pytest\.mark\.skipif\(([^\n]*)',b): guards.append(('skipif',mm.group(1)[:70]))
            if guards: rep['guarded_refs'][x]={'kind':'F2P' if x in f2p else 'P2P','guards':guards,'line':s+1}
    out[tid]=rep
    ng=len(rep['guarded_refs']); nf=sum(1 for v in rep['guarded_refs'].values() if v['kind']=='F2P')
    print(f"== {tid}: 参考集 {rep['n_ref']} 条，其中被守卫 {ng} 条（F2P {nf} 条）")
    for m in rep['module_guards']: print('   [模块级]',m)
    for k,v in list(rep['guarded_refs'].items())[:8]:
        print(f"   {v['kind']} {k.split('::')[-1]} @line{v['line']} -> {v['guards']}")
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_dask/refskip.json','w'),ensure_ascii=False,indent=1)
