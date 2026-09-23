import json,os,re
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dask/mat'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ref=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    p=f'{L}/{tid}/gold/offline/a1/test_output.txt'
    if not os.path.exists(p): print(tid,'NO LOG'); continue
    txt=open(p,errors='replace').read()
    m=re.search(r'platform linux -- (Python \S+), (pytest-\S+)',txt)
    plugins=re.search(r'^plugins: (.*)$',txt,re.M)
    failed=[l.split()[1] for l in txt.split('\n') if l.startswith('FAILED ') and len(l.split())>1]
    notref=[x for x in failed if x not in ref]
    # collect error kinds from the failure sections
    kinds={}
    for pat,name in [(r'pytest\.warns\(None\)','pytest.warns(None) 已在 pytest8 移除'),
                     (r'exceptions must be derived from Warning, not','pytest.warns(None)/pytest8'),
                     (r"has no attribute '_mgr'",'pandas 内部 API 漂移(_mgr)'),
                     (r'DeprecationWarning|FutureWarning','warning 升级为 error'),
                     (r'No module named','缺可选依赖'),
                     (r'AttributeError: module','上游库 API 变更')]:
        n=len(re.findall(pat,txt))
        if n: kinds[name]=n
    print(f'== {tid}: {m.group(1) if m else "?"} {m.group(2) if m else "?"} | plugins={plugins.group(1) if plugins else "?"}')
    print(f'   FAILED total={len(failed)} 参考集外={len(notref)}  参考集内={len(failed)-len(notref)}')
    print(f'   迹象={kinds}')
    if notref: print('   样例:',notref[:5])
