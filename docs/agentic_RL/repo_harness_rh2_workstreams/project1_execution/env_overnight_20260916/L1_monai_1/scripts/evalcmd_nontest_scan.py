"""两项跨仓库核对：(1) 216 题的 eval_cmd 分布（按仓库）；(2) test_patch 里的非 test_* 文件。
动机：MONAI 的 eval_cmd 是 `pytest -rA` + 整份测试文件（不是 -k 选择器），与 mypy 完全不同；
test_patch 里的非 test_* 文件会被恢复步骤覆盖，MONAI 的两个还会被当 pytest 目标直接传入。"""
import json,re,os,collections
ROOT='${REPO_ROOT}'
S=f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/s2'
E=f'{ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916'
tb=json.load(open(f'{E}/tasks_by_repo.json'))
allt={t for v in tb.values() for t in v}
mine=set(json.load(open(f'{E}/L1_monai_1/ASSIGNMENT.json'))['tasks'])
cmds=collections.Counter(); byrepo=collections.defaultdict(collections.Counter); nontest=[]
def is_test(p):
    b=os.path.basename(p)
    return b.startswith('test_') or b.endswith('_test.py') or p.startswith('test-data/') or b=='conftest.py'
for line in open(f'{S}/ingest/grading_bundles_v2_v0.jsonl'):
    g=json.loads(line); tid=g['instance_id']
    if tid not in allt: continue
    c=(g.get('eval_cmd') or '').strip(); cmds[c]+=1; byrepo[g['repo']][c]+=1
    tp=sorted(set(re.findall(r'^diff --git a/(\S+) b/\S+', g['test_patch'], re.M)))
    bad=[p for p in tp if not is_test(p)]
    if bad: nontest.append((tid,g['repo'],bad))
print('=== eval_cmd 分布（216 题）===')
for c,n in cmds.most_common(): print(f'  {n:4d}  {c!r}')
print('\n=== 各仓库的 eval_cmd ===')
for r in sorted(byrepo): print(f'  {r:24s} {dict(byrepo[r])}')
print('\n=== test_patch 里的非 test_* 文件 ===')
per=collections.Counter()
for tid,repo,bad in sorted(nontest):
    per[repo]+=1
    print(f"  {tid:38s}{' <<MINE' if tid in mine else '       '} {bad}")
print(f'--- 共 {len(nontest)} 题；按仓库 {dict(per)} ---')
