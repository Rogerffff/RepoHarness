import json,sys,subprocess,re
M='runs/env_overnight_20260916/L1_pydantic/mat'
R='runs/env_overnight_20260916/repos/pydantic'
tid=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'ps'
pub=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
if what=='ps':
    print('### workdir',pub['workdir'],'image',pub['image'])
    print('### allowed_tools',pub.get('allowed_tools'))
    print('### public_hints',repr(pub.get('public_hints'))[:500])
    print('### PROBLEM STATEMENT');print(pub['problem_statement'])
elif what=='hints': print(raw.get('hints_text') or '(empty)')
elif what=='tp': print(g['test_patch'])
elif what=='gold': print(v['golden_patch'])
elif what=='f2p':
    print('F2P:');[print('  ',repr(x)) for x in g['fail_to_pass']]
    print('P2P n=',len(g['pass_to_pass']));[print('  ',repr(x)) for x in g['pass_to_pass'][:8]]
elif what=='p2p': [print(repr(x)) for x in g['pass_to_pass']]
elif what=='meta':
    print(json.dumps({k:raw.get(k) for k in ('created_at','version','base_commit')},indent=1))
