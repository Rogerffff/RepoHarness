# 用 stage1 gold/empty 的真实 -rA 摘要行，检验 parse_log_pytest 的 split()[1] 截断是否产生碰撞
import json,os,re,collections
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_conan/ASSIGNMENT.json'))
STAT=("FAILED","PASSED","SKIPPED","ERROR","XFAIL")
out={}
for tid in ASG['tasks']:
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): continue
        seen=collections.defaultdict(set)
        skipline=[]
        for line in open(p,errors='replace'):
            line=line.rstrip('\n')
            if not any(line.startswith(x) for x in STAT): continue
            if line.startswith('FAILED'): line=line.replace(' - ',' ')
            tc=line.split()
            if len(tc)<=1: continue
            key=tc[1]
            if key.startswith('['):   # SKIPPED [1] file:line: reason 形态
                skipline.append(line); continue
            # 真实 nodeid = 从 tc[1] 起到行尾（PASSED 行没有额外后缀）
            full=' '.join(tc[1:]) if tc[0] in ('PASSED','SKIPPED','XFAIL') else tc[1]
            seen[key].add(full)
        coll={k:sorted(v) for k,v in seen.items() if len(v)>1}
        trunc={k:sorted(v) for k,v in seen.items() if any(vv!=k for vv in v)}
        out[f'{tid}/{kind}']={'collisions':coll,'truncated':trunc,'skip_summary_lines':skipline}
        if coll or trunc or skipline:
            print(f'--- {tid}/{kind}')
            if coll: print('  COLLISION:',json.dumps(coll,ensure_ascii=False))
            if trunc: print('  TRUNCATED:',json.dumps(trunc,ensure_ascii=False))
            if skipline: print('  SKIP_SUMMARY(键被解析成',[l.split()[1] for l in skipline],'):')
            for l in skipline: print('      ',l)
json.dump(out,open('${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/collide.json','w'),ensure_ascii=False,indent=1)
