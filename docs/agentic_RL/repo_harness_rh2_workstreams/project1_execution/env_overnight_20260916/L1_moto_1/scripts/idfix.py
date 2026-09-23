import json,os,re
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_moto_1/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_1/ASSIGNMENT.json'))
def ascii_escaped(s):
    # mimic pytest _pytest.compat.ascii_escaped for str
    return s.encode('unicode_escape').decode('ascii')
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(tests/\S*::\S.*)$')
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ids=g['fail_to_pass']+g['pass_to_pass']
    bad=[x for x in ids if any(ord(c)>127 for c in x)]
    if not bad: continue
    p=f'{L}/{tid}/gold/offline/a1/test_output.txt'
    runtime=set()
    if os.path.exists(p):
        for line in open(p,errors='replace'):
            m=pat.match(line.rstrip('\n'))
            if m: runtime.add(m.group(2).strip())
    print(f'### {tid}')
    for x in bad:
        base,_,param=x.partition('[')
        cand=[r for r in runtime if r.startswith(base+'[')]
        # build the escaped form
        if param:
            esc=base+'['+ascii_escaped(param.rstrip(']'))+']'
        else: esc=x
        print(f'  常量: {x!r}')
        print(f'  ascii_escaped 推算: {esc!r}')
        match=[c for c in cand if c==esc]
        print(f'  运行时同名前缀候选: {cand}')
        print(f'  推算是否命中运行时: {bool(match)}')
