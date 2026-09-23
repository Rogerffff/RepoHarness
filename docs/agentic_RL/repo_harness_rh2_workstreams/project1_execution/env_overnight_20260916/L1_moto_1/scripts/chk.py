import json,sys,os
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_moto_1/mat'
L='${REPO_ROOT}/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910'
tid=sys.argv[1]
g=json.load(open(f'{M}/{tid}/grading.json'))
f2p=g['fail_to_pass']; p2p=g['pass_to_pass']
print(f'F2P n={len(f2p)} P2P n={len(p2p)}')
def trunc(x): return x.count('[')!=x.count(']')
print('truncated F2P:',[x for x in f2p if trunc(x)])
print('truncated P2P:',[x for x in p2p if trunc(x)])
for kind in ('gold','empty'):
    p=f'{L}/{tid}/{kind}/offline/a1/status_map.json'
    if not os.path.exists(p): print(kind,'NO LOG'); continue
    sm=json.load(open(p))
    miss_f=[x for x in f2p if x not in sm]; miss_p=[x for x in p2p if x not in sm]
    bad_f=[(x,sm[x]) for x in f2p if x in sm and sm[x]!='PASSED']
    bad_p=[(x,sm[x]) for x in p2p if x in sm and sm[x]!='PASSED']
    print(f'--- {kind}: statusmap n={len(sm)} f2p_missing={len(miss_f)} p2p_missing={len(miss_p)} f2p_notpass={len(bad_f)} p2p_notpass={len(bad_p)}')
    if miss_f: print('   MISS F2P:',miss_f[:6])
    if miss_p: print('   MISS P2P:',miss_p[:6])
    if bad_f: print('   BAD F2P:',bad_f[:6])
    if bad_p: print('   BAD P2P:',bad_p[:6])
    # collision check
    from collections import Counter
    c=Counter(sm.keys())
