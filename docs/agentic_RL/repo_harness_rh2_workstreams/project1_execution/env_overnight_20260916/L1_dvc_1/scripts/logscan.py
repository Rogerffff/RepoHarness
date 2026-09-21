# 解析污染扫描：test_output.txt 里被 RH2 状态解析器当成"测试结果"的非 nodeid 行；以及同 key 重复出现
import json,os,re,collections
M='runs/env_overnight_20260916/L1_dvc_1/mat'
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/ASSIGNMENT.json'))
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')
out={}
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ids=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): continue
        seen=collections.defaultdict(list)   # first-token -> [(verdict, fullline)]
        for line in open(p,errors='replace'):
            m=pat.match(line.rstrip('\n'))
            if not m: continue
            v,rest=m.group(1),m.group(2)
            seen[rest.split()[0]].append((v,rest.strip()[:120]))
        garbage={k:v for k,v in seen.items() if '::' not in k}
        dupdiff={k:set(x[0] for x in v) for k,v in seen.items() if len(set(x[0] for x in v))>1}
        collide={k:sorted(set(x[1] for x in v)) for k,v in seen.items() if len(set(x[1] for x in v))>1 and '::' in k}
        hit=[k for k in garbage if k in ids]
        out[f'{tid}/{kind}']={'garbage_keys':sorted(garbage),'garbage_hits_graded':hit,
                              'verdict_conflict':{k:sorted(v) for k,v in dupdiff.items()},
                              'trunc_collision':collide}
        flags=[]
        if garbage: flags.append(f'GARBAGE={len(garbage)}:{sorted(garbage)[:6]}')
        if hit: flags.append(f'!!GARBAGE_HITS_GRADED={hit}')
        if dupdiff: flags.append(f'VERDICT_CONFLICT={ {k:sorted(v) for k,v in list(dupdiff.items())[:4]} }')
        if collide: flags.append(f'TRUNC_COLLISION={len(collide)}:{list(collide.items())[:2]}')
        if flags: print(f'--- {tid}/{kind}'); [print('   !',f) for f in flags]
json.dump(out,open('runs/env_overnight_20260916/L1_dvc_1/logscan.json','w'),ensure_ascii=False,indent=1)
