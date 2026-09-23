"""扫描 216 题：F2P/P2P 名单里的用例在 base 源码中是否带 skip 装饰器。
动机（见 MONAI-3547 / MONAI-4109 记录）：pytest `-rA` 的 SKIPPED 摘要行格式是
`SKIPPED [n] file:line: reason`，**不含 nodeid**；swegym_parsers.parse_log_pytest
只会记下键 `[n]`。于是被 skip 的 F2P/P2P 用例在 status_map 里找不到自己的 nodeid，
被 get_eval_tests_report 当作「缺席」计为失败。换机器/换依赖就可能让 gold 假判 RESOLVED_NO。
本扫描是静态近似：只看装饰器文本，不判断条件是否成立。"""
import json,re,subprocess,collections,os
ROOT='.'
S=f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
REPOS=f'{ROOT}/runs/env_overnight_20260916/repos'
REPO_DIR={'Project-MONAI/MONAI':'MONAI','python/mypy':'mypy','getmoto/moto':'moto','iterative/dvc':'dvc',
          'conan-io/conan':'conan','dask/dask':'dask','modin-project/modin':'modin',
          'pandas-dev/pandas':'pandas','pydantic/pydantic':'pydantic'}
SKIP_RE=re.compile(r'@(?:\w+\.)*(?:pytest\.mark\.)?(?:skip\w*|Skip\w*|requires?\w*|has_\w*|.*skip.*)', re.I)
def show(repo,commit,path):
    p=subprocess.run(['git','-C',f'{REPOS}/{repo}','show',f'{commit}:{path}'],capture_output=True,text=True)
    return p.stdout if p.returncode==0 else None
def decorated(src):
    """返回 {名字: [装饰器行]}，名字取 def/class 的标识符（不带参数化后缀）。"""
    out=collections.defaultdict(list); pend=[]
    for line in src.split('\n'):
        s=line.strip()
        if s.startswith('@'): pend.append(s); continue
        m=re.match(r'(?:async\s+)?def\s+(\w+)\s*\(', s) or re.match(r'class\s+(\w+)\b', s)
        if m:
            if pend: out[m.group(1)].extend(pend)
            pend=[]
        elif s and not s.startswith('#'):
            pend=[]
    return out
rows=[]
for line in open(f'{S}/ingest/grading_bundles_v2_v0.jsonl'):
    g=json.loads(line); tid=g['instance_id']; repo=REPO_DIR.get(g['repo'])
    if repo is None: continue
    ids=list(g['fail_to_pass'])+list(g['pass_to_pass'])
    f2p=set(g['fail_to_pass'])
    byfile=collections.defaultdict(list)
    for x in ids:
        if '::' in x: byfile[x.split('::')[0]].append(x)
    hits=[]
    for f,xs in byfile.items():
        src=show(repo,g['base_commit'],f)
        if src is None: continue
        dec=decorated(src)
        for x in xs:
            parts=x.split('::')[1:]
            names=[p.split('[')[0] for p in parts]
            for n in names:
                for d in dec.get(n,[]):
                    if 'parametrize' in d: continue
                    dl=d.lower()
                    if ('skip' in dl) or dl.startswith('@requires') or '.requires' in dl or 'skipif' in dl:
                        hits.append((x, n, d, x in f2p))
    if hits: rows.append((tid,hits))
print('=== F2P/P2P 用例在 base 带 skip 类装饰器的题 ===')
nf2p=0
for tid,hits in sorted(rows):
    infp=[h for h in hits if h[3]]
    if infp: nf2p+=1
    mark='  <<F2P受影响' if infp else ''
    ds=sorted({h[2] for h in hits})
    print(f'{tid:38s} 命中 {len(hits):3d} 条{mark}')
    for d in ds[:4]: print(f'      {d}')
    for x,n,d,isf in infp[:3]: print(f'      F2P: {x}  <- {d}')
print(f'--- 共 {len(rows)} 题命中，其中 {nf2p} 题的 **F2P** 用例带 skip 装饰器 ---')
