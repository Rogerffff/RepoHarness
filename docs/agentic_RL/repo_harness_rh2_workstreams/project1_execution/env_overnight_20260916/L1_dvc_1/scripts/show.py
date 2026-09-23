import json,sys
M='runs/env_overnight_20260916/L1_dvc_1/mat'
tid=sys.argv[1]; what=sys.argv[2] if len(sys.argv)>2 else 'ps'
pub=json.load(open(f'{M}/{tid}/public.json')); g=json.load(open(f'{M}/{tid}/grading.json'))
v=json.load(open(f'{M}/{tid}/validation.json')); raw=json.load(open(f'{M}/{tid}/raw.json'))
if what=='ps': print(pub['problem_statement'])
elif what=='tp': print(g['test_patch'])
elif what=='gold': print(v['golden_patch'])
elif what=='hints': print(raw.get('hints_text') or '(empty)')
elif what=='ids':
    print('BASE',g['base_commit'],'VER',g.get('version'),'PY',g.get('python_version'))
    print('IMAGE',pub.get('image'),'WORKDIR',pub.get('workdir'))
    print('PUBLIC_HINTS',repr(pub.get('public_hints'))[:300])
    print('--- F2P',len(g['fail_to_pass']))
    for x in g['fail_to_pass']: print('  ',x)
    print('--- P2P',len(g['pass_to_pass']))
    for x in g['pass_to_pass']: print('  ',x)
elif what=='meta':
    print(json.dumps({k:v2 for k,v2 in pub.items() if k!='problem_statement'},ensure_ascii=False,indent=1))
