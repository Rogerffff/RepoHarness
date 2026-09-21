import json,os,re,collections
L='runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
M='runs/env_overnight_20260916/L1_dask/mat'
ASG=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/ASSIGNMENT.json'))
pat=re.compile(r'^(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\s+(\S.*)$')
for tid in ASG['tasks']:
    g=json.load(open(f'{M}/{tid}/grading.json'))
    ref=set(g['fail_to_pass'])|set(g['pass_to_pass'])
    for kind in ('gold',):
        p=f'{L}/{tid}/{kind}/offline/a1/test_output.txt'
        if not os.path.exists(p): print(tid,kind,'NO LOG'); continue
        full=collections.defaultdict(set)
        nlines=0; skipped=[]
        for line in open(p,errors='replace'):
            m=pat.match(line.rstrip('\n'))
            if not m: continue
            verdict,rest=m.group(1),m.group(2)
            if verdict=='FAILED': rest=rest.replace(' - ',' ')
            nlines+=1
            trunc=rest.split()[0]
            full[trunc].add((rest.strip(),verdict))
            if verdict in ('SKIPPED','XFAIL','XPASS'): skipped.append((trunc,verdict,rest.strip()[:150]))
        coll={k:v for k,v in full.items() if len(v)>1}
        inref_coll={k:v for k,v in coll.items() if k in ref}
        print(f'== {tid}/{kind}: result_lines={nlines} keys={len(full)} collided_keys={len(coll)} collided_in_ref={len(inref_coll)} skipped={len(skipped)}')
        for k,v in list(inref_coll.items())[:6]:
            print('   REF-COLLIDE',k,'->',sorted(v)[:4])
        for k,v in list(coll.items())[:3]:
            if k not in inref_coll: print('   collide(not in ref)',k,'->',sorted(v)[:3])
        for s in skipped[:12]:
            print('   SKIP',s[1],s[0],'| inref=',s[0] in ref)
