"""把 records/<tid>.json 写盘；从 stdin 读 JSON 片段并与 prescan 元数据合并。"""
import json,sys,os
P='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_2/prescan.json'
OUT='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records'
pre=json.load(open(P))
d=json.load(sys.stdin)
tid=d['task_id']
r=pre[tid]
rec={
 'task_id':tid,'source':'swe_gym_lite','task_revision':'upstream',
 'materials_refs':{
   'public_bundle':'docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl',
   'grading_bundle':'docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/grading_bundles_v2_v0.jsonl',
   'validation_bundle':'docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/validation_bundles_v0.jsonl',
   'raw':'docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl',
   'repo_clone':'runs/env_overnight_20260916/repos/dvc',
   'base_commit':r['base_commit'],'version':r['version'],'python_version':r['py'],
   'eval_cmd':r['eval_cmd'],'image':r['image'],'workdir':r['workdir'],
   'test_patch_paths':r['test_patch_paths'],'gold_paths':r['gold_paths'],
   'n_f2p':r['n_f2p'],'n_p2p':r['n_p2p'],
   'stage1_log':f"runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/{tid}/{{gold,empty}}/offline/a1/",
   'signals':r['signals'],
 },
 'public_view':d['public_view'],'checks':d['checks'],'issues':d.get('issues',[]),
 'file_rules':d.get('file_rules',{'additional_exclusions':[],'rationale':'','evidence_refs':[]}),
 'proposed_regression_tests':d.get('proposed_regression_tests',[]),
 'disposition_hint':d['disposition_hint'],'costs':d.get('costs',{'minutes':0}),
 'by':'L1_dvc_2 (Claude Opus 5, 2026-09-16, 静态审查)',
}
os.makedirs(OUT,exist_ok=True)
json.dump(rec,open(f'{OUT}/{tid}.json','w'),ensure_ascii=False,indent=1)
print('wrote',f'{OUT}/{tid}.json','checks=',len(rec['checks']),'issues=',len(rec['issues']))
