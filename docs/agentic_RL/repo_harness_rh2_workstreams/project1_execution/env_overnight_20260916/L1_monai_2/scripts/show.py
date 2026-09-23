import json,sys,os
PKG='L1_monai_2'
M=f'${REPO_ROOT}/runs/env_overnight_20260916/{PKG}/mat'
tid=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'all'
pub=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
if what in ('all','ps'):
    print('===== PROBLEM STATEMENT ====='); print(pub['problem_statement'])
    print('----- workdir/allowed_tools/public_hints:', pub.get('workdir'), pub.get('allowed_tools'), repr(pub.get('public_hints'))[:200])
if what in ('all','f2p'):
    print('===== F2P ====='); [print(' ',x) for x in g['fail_to_pass']]
    print('===== P2P (n=%d) ====='%len(g['pass_to_pass'])); [print(' ',x) for x in g['pass_to_pass']]
if what in ('all','tp'):
    print('===== TEST PATCH ====='); print(g['test_patch'])
if what in ('all','gold'):
    print('===== GOLDEN PATCH ====='); print(v.get('golden_patch'))
if what in ('all','hints'):
    print('===== HINTS (%d ch) ====='%len(raw.get('hints_text') or '')); print(raw.get('hints_text'))
    print('===== created_at:',raw.get('created_at'))
