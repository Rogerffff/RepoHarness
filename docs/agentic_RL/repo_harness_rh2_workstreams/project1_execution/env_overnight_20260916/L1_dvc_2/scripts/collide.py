import json,os,re,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
B='docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
M='runs/env_overnight_20260916/L1_dvc_2/mat'
ASG=json.load(open(f'{B}/L1_dvc_2/ASSIGNMENT.json'))
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    graded=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): print(tid,kind,'NO_LOG'); continue
        full=collections.defaultdict(set)
        with open(p,errors='replace') as f:
            for line in f:
                m=pat.match(line.rstrip('\n'))
                if not m: continue
                verdict,rest=m.group(1),m.group(2)
                trunc=rest.split()[0]
                full[trunc].add((rest.strip(),verdict))
        coll={k:v for k,v in full.items() if len(v)>1}
        graded_coll={k:v for k,v in coll.items() if k in graded}
        truncated_keys=[k for k in full if any(k==x for x in graded) and k.count('[')!=k.count(']')]
        if coll or truncated_keys:
            print(f'--- {tid}/{kind} collisions={len(coll)} graded_collisions={len(graded_coll)} graded_truncated_keys={len(truncated_keys)}')
            for k,v in list(graded_coll.items())[:5]: print('   GRADED-COLL',repr(k),'->',sorted(v))
            for k,v in list(coll.items())[:3]:
                if k not in graded_coll: print('   coll',repr(k),'->',sorted(v)[:3])
