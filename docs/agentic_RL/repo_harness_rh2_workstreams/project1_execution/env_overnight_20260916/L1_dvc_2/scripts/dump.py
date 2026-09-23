import json,sys,os
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_2/mat'
tid=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'all'
p=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
if what in ('all','ps'):
    print('='*20,'PROBLEM_STATEMENT','='*20); print(p['problem_statement'])
    print('--- base_commit:',g['base_commit'],' workdir:',p.get('workdir'),' image:',p.get('image'))
    print('--- public_hints:',repr(p.get('public_hints'))[:300],' allowed_tools:',p.get('allowed_tools'))
if what in ('all','tp'):
    print('='*20,'TEST_PATCH','='*20); print(g['test_patch'])
if what in ('all','ids'):
    print('='*20,'F2P','='*20)
    for x in g['fail_to_pass']: print(' ',repr(x))
    print('='*20,f"P2P n={len(g['pass_to_pass'])}",'='*20)
    for x in g['pass_to_pass']: print(' ',repr(x))
if what in ('all','gold'):
    print('='*20,'GOLDEN_PATCH','='*20); print(v.get('golden_patch'))
if what in ('all','hints'):
    print('='*20,'HINTS (不可见)','='*20); print(raw.get('hints_text'))
    print('--- created_at:',raw.get('created_at'))
