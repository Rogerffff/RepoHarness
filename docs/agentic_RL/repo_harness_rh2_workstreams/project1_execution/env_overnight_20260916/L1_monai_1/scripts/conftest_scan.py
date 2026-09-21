"""逐题核对 base_commit 下是否存在任何 conftest.py。
动机：rh2 构造 SWE spec 时 HygieneRules.test_globs=()（grading/manager.py:672），
候选改动里的 conftest.py 既不被投影剔除（随 cleaned.patch 落进评分树，manager.py:2592），
也不被 trusted setup 恢复（只恢复 hygiene.test_files = test_patch 触碰的路径，
adapters/slime/prepared_task_face.py:199-210）；manager.py:566-577 只把它记进 sidecar 观测字段。
trusted_projection.py:18-20 已把它登记为「已知不足（登记不修）」。
base 里没有 conftest.py 的仓库暴露面最干净：候选新建即生效，且不会与任何既有内容冲突。"""
import json,subprocess,collections
ROOT='.'
S=f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
REPOS=f'{ROOT}/runs/env_overnight_20260916/repos'
RD={'Project-MONAI/MONAI':'MONAI','python/mypy':'mypy','getmoto/moto':'moto','iterative/dvc':'dvc',
    'conan-io/conan':'conan','dask/dask':'dask','modin-project/modin':'modin',
    'pandas-dev/pandas':'pandas','pydantic/pydantic':'pydantic'}
seen=collections.defaultdict(list)
for line in open(f'{S}/ingest/grading_bundles_v2_v0.jsonl'):
    g=json.loads(line); r=RD.get(g['repo'])
    if r is None: continue
    seen[g['repo']].append((g['instance_id'],g['base_commit']))
for repo,rows in sorted(seen.items()):
    r=RD[repo]; zero=0; tot=0; ex=[]
    for tid,c in rows:
        p=subprocess.run(['git','-C',f'{REPOS}/{r}','ls-tree','-r','--name-only',c],capture_output=True,text=True)
        if p.returncode!=0: continue
        conf=[x for x in p.stdout.split('\n') if x.endswith('conftest.py')]
        tot+=1
        if not conf: zero+=1
        elif len(ex)<2: ex.append((tid,len(conf),conf[:2]))
    print(f'{repo:24s} {zero}/{tot} 个 base 下没有任何 conftest.py')
    for e in ex: print('     有 conftest 的例子:',e)
