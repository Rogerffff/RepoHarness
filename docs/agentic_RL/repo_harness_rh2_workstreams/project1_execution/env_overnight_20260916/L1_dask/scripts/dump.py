import json,sys,os,re,subprocess
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dask/mat'
tid=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'all'
pub=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
if what in ('all','ps'):
    print('######## PROBLEM_STATEMENT ########'); print(pub['problem_statement'])
    print('######## public_hints ########'); print(repr(pub.get('public_hints'))[:500])
    print('######## base',g['base_commit'],'ver',g.get('version'),'image',pub.get('image'),'workdir',pub.get('workdir'))
if what in ('all','tp'):
    print('######## TEST_PATCH ########'); print(g['test_patch'])
if what in ('all','gold'):
    print('######## GOLDEN_PATCH ########'); print(v.get('golden_patch'))
if what in ('all','ids'):
    print('######## F2P ########'); [print(' ',x) for x in g['fail_to_pass']]
    print(f'######## P2P n={len(g["pass_to_pass"])} ########'); [print(' ',x) for x in g['pass_to_pass']]
if what in ('all','hints'):
    print('######## HINTS ########'); print(raw.get('hints_text'))
