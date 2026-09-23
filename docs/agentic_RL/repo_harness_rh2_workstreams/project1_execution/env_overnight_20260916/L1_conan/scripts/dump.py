import json,sys
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_conan/mat'
t=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'all'
p=json.load(open(f'{M}/{t}/public.json')); g=json.load(open(f'{M}/{t}/grading.json'))
v=json.load(open(f'{M}/{t}/validation.json')); r=json.load(open(f'{M}/{t}/raw.json'))
if what in ('all','ps'):
    print('='*20,'PROBLEM STATEMENT','='*20); print(p['problem_statement'])
    print('  workdir=',p.get('workdir'),' allowed_tools=',p.get('allowed_tools'))
if what in ('all','gold'):
    print('='*20,'GOLDEN PATCH','='*20); print(v.get('golden_patch'))
if what in ('all','tp'):
    print('='*20,'TEST PATCH','='*20); print(g['test_patch'])
if what in ('all','ids'):
    print('='*20,'F2P','='*20); [print(' ',x) for x in g['fail_to_pass']]
    print('='*20,'P2P','='*20); [print(' ',x) for x in g['pass_to_pass']]
if what=='hints':
    print(r.get('hints_text'))
