import json,sys,re
M='runs/env_overnight_20260916/L1_mypy_2/mat'
PRE=json.load(open('runs/env_overnight_20260916/L1_mypy_2/prescan.json'))
KS=json.load(open('runs/env_overnight_20260916/L1_mypy_2/kscan.json'))
tid=sys.argv[1]; part=sys.argv[2] if len(sys.argv)>2 else 'all'
p=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
r=PRE[tid]
if part in ('all','ps'):
    print('='*20,'PROBLEM_STATEMENT','='*20); print(p['problem_statement'])
if part in ('all','meta'):
    print('='*20,'META','='*20)
    print('base',r['base_commit'],'version',r['version'],'py',r['py'],'eval',r['eval_cmd'])
    print('test_patch_paths',r['test_patch_paths']); print('gold_paths',r['gold_paths'])
    print('F2P:'); [print('  -',x) for x in r['f2p']]
    print('P2P:'); [print('  -',x) for x in r['p2p']]
    print('kscan:'); [print('  ',json.dumps(row,ensure_ascii=False)) for row in KS[tid]['rows']]
if part in ('all','gold'):
    print('='*20,'GOLDEN_PATCH','='*20); print(v.get('golden_patch') or v.get('patch'))
if part in ('all','tp'):
    print('='*20,'TEST_PATCH','='*20); print(g['test_patch'])
if part in ('all','hints'):
    print('='*20,'HINTS','='*20); print(raw.get('hints_text'))
if part=='pubkeys':
    print(sorted(p.keys())); print(sorted(raw.keys()))
