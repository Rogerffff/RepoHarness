import json,sys,os
D='${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records'
M='${REPO_ROOT}/runs/env_overnight_20260916/L1_dvc_1/mat'
def write(tid, public_view, checks, issues, file_rules, tests, disp, minutes, extra=None):
    g=json.load(open(f'{M}/{tid}/grading.json')); pub=json.load(open(f'{M}/{tid}/public.json'))
    rec={'task_id':tid,'source':'swe_gym_lite','task_revision':'upstream',
     'materials_refs':{
       'public':'docs/.../s2/ingest/public_bundles_v0.jsonl#'+tid,
       'grading':'docs/.../s2/ingest/grading_bundles_v2_v0.jsonl#'+tid,
       'validation':'docs/.../s2/ingest/validation_bundles_v0.jsonl#'+tid,
       'raw':'docs/.../s2/raw/swe_gym_lite_full_f70b1a29.jsonl#'+tid,
       'base_commit':g['base_commit'],'version':g.get('version'),'python_version':g.get('python_version'),
       'image':pub.get('image'),'eval_cmd':g.get('eval_cmd'),
       'stage1_logs':f'runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/{tid}/'+'{gold,empty}/offline/a1/',
       'repo_clone':'runs/env_overnight_20260916/repos/dvc'},
     'public_view':public_view,'checks':checks,'issues':issues,'file_rules':file_rules,
     'proposed_regression_tests':tests,'disposition_hint':disp,'costs':{'minutes':minutes},
     'by':'L1_dvc_1 (Claude Opus 5, 静态审查)'}
    if extra: rec.update(extra)
    os.makedirs(D,exist_ok=True)
    json.dump(rec,open(f'{D}/{tid}.json','w'),ensure_ascii=False,indent=1)
    print('wrote',f'{D}/{tid}.json')
def C(status,ev,note,by='static'):
    return {'status':status,'evidence_refs':ev if isinstance(ev,list) else [ev],'note':note,'by':by}
