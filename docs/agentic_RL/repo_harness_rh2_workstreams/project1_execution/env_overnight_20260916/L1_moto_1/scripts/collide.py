import json,os,re,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_moto_1/ASSIGNMENT.json'))
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')
for tid in ASG['tasks']:
    for kind in ('gold','empty'):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): continue
        full=collections.defaultdict(set)   # truncated-key -> set of (fullid, verdict)
        with open(p,errors='replace') as f:
            for line in f:
                m=pat.match(line.rstrip('\n'))
                if not m: continue
                verdict,rest=m.group(1),m.group(2)
                # RH2-style truncation: first whitespace-delimited token
                trunc=rest.split()[0]
                full[trunc].add((rest.strip(),verdict))
        coll={k:v for k,v in full.items() if len(v)>1}
        if coll:
            print(f'--- {tid}/{kind} COLLISIONS={len(coll)}')
            for k,v in list(coll.items())[:5]: print('   ',k,'->',sorted(v))
