"""扫描 216 题：test_patch 里含 new file mode / deleted file mode 的题。
动机：rh2 v2 setup 的恢复步骤（prepared_task_face.py:199-210）只对 base 里存在的
official test 路径做 git checkout，新建路径跳过；若候选在同名路径写了自己的测试，
随后的 git apply 会冲突 → official_test_patch_apply_failed。"""
import json,re
S='docs/agentic_RL/repo_harness_rh2_workstreams/s2'
tb=json.load(open('docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/tasks_by_repo.json'))
allt={t for v in tb.values() for t in v}
rows=[]
for line in open(f'{S}/ingest/grading_bundles_v2_v0.jsonl'):
    r=json.loads(line); tid=r['instance_id']
    if tid not in allt: continue
    tp=r['test_patch']
    new=re.findall(r'^diff --git a/(\S+) b/\S+\nnew file mode', tp, re.M)
    dele=re.findall(r'^diff --git a/(\S+) b/\S+\ndeleted file mode', tp, re.M)
    if new or dele: rows.append((tid,new,dele))
for tid,n,d in sorted(rows): print(f'{tid} new={n} deleted={d}')
print(f'total {len(rows)} / {len(allt)}')
