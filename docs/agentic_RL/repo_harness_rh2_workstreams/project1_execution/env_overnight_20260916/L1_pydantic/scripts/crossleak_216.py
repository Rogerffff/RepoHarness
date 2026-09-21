"""附-2：跨题答案泄漏扫描，覆盖 9 个仓库 216 题。
判据：早题 gold 新增的有效行（>=15 字符、非纯注释）在晚题 base 的同一文件里命中 >= 半数。
只读 s2 ingest 与 runs/env_overnight_20260916/repos/* 裸克隆。从仓库根目录运行。
局限：只比对同一文件、只比对 gold 新增行，会漏掉跨文件与被重构过的修复，结果是下界。"""
import json,re,subprocess,collections
ING='docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest'
REPOS='runs/env_overnight_20260916/repos'
name={'Project-MONAI/MONAI':'MONAI','conan-io/conan':'conan','dask/dask':'dask','getmoto/moto':'moto',
      'iterative/dvc':'dvc','modin-project/modin':'modin','pandas-dev/pandas':'pandas',
      'pydantic/pydantic':'pydantic','python/mypy':'mypy'}
raws={json.loads(l)['instance_id']:json.loads(l) for l in open('docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl')}
vals={json.loads(l)['instance_id']:json.loads(l) for l in open(f'{ING}/validation_bundles_v0.jsonl')}
def paths(d): return sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', d or '', re.M)))
byrepo=collections.defaultdict(list)
for l in open(f'{ING}/grading_bundles_v2_v0.jsonl'):
    g=json.loads(l); tid=g['instance_id']; gp=vals[tid].get('golden_patch') or ''
    added=[x[1:].strip() for x in gp.split('\n') if x.startswith('+') and not x.startswith('+++')]
    byrepo[g['repo']].append((raws[tid]['created_at'],tid,g['base_commit'],paths(gp),
                              [a for a in added if len(a)>=15 and not a.startswith('#')]))
cache={}
def show(repo,c,p):
    k=(repo,c,p)
    if k not in cache:
        r=subprocess.run(['git','-C',f'{REPOS}/{name[repo]}','show',f'{c}:{p}'],capture_output=True,text=True)
        cache[k]=re.sub(r'\s+','',r.stdout) if r.returncode==0 else None
    return cache[k]
tot=0; tasks=set()
for repo,rs in sorted(byrepo.items()):
    rs.sort(); pairs=[]
    for i,(ca,ta,ba,ga,aa) in enumerate(rs):
        if not aa: continue
        for cb,tb,bb,gb,ab in rs[i+1:]:
            for f in set(ga)&set(gb):
                src=show(repo,bb,f)
                if src is None: continue
                hit=sum(1 for a in aa if re.sub(r'\s+','',a) in src)
                if hit>=max(2,len(aa)//2): pairs.append((ca[:10],ta,cb[:10],tb,f,hit,len(aa)))
    print(f'### {repo}  n={len(rs)}  泄漏对={len(pairs)}')
    for ca,ta,cb,tb,f,h,n in pairs:
        print(f'   {ta}({ca}) gold → {tb}({cb}) base:{f}  {h}/{n}'); tasks.add(ta); tasks.add(tb)
    tot+=len(pairs)
print(f'\n合计 {tot} 对，涉及 {len(tasks)} 题 / {sum(len(v) for v in byrepo.values())}')
