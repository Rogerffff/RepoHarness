"""仅离线读取本地证据；仅写同目录 local_evidence.json，不运行模型/容器。"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
from hashlib import sha256
from math import ceil
from pathlib import Path
from statistics import median
import json

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
BASE = Path('docs/agentic_RL/repo_harness_rh2_workstreams')
EX = BASE / 'project1_execution'
CAT = EX / 'category2_repair_20260929'
OWNER = CAT / 'repository_work'


def read(path):
    return json.loads((ROOT / path).read_text())


def jsonl(path):
    return [json.loads(x) for x in (ROOT / path).read_text().splitlines() if x.strip()]


def evidence(path):
    p = ROOT / path
    return {'path': str(path), 'bytes': p.stat().st_size, 'sha256': sha256(p.read_bytes()).hexdigest()}


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


def stats(values):
    v = sorted(values)
    if not v:
        return {'n': 0}
    return {'n': len(v), 'sum_seconds': round(sum(v), 3),
            'mean_seconds': round(sum(v) / len(v), 3),
            'median_seconds': round(median(v), 3),
            'p90_nearest_rank_seconds': round(v[ceil(.9 * len(v)) - 1], 3),
            'max_seconds': round(max(v), 3)}


NAV_PATH = EX / 'dataset_status/tasks.json'
INDEX_PATH = CAT / 'experiment_artifact_index_20261004.json'
BOARD_PATH = CAT / 'repository_work_packages_20261002.json'
nav = read(NAV_PATH)
index = read(INDEX_PATH)
board = read(BOARD_PATH)
nav_by = {t['instance_id']: t for t in nav['tasks']}
board_by = {t['instance_id']: t for g in board['groups'] for t in g['tasks']}
swe_path = BASE / 'data_freeze/meta/swe_gym_full.jsonl'
r2e_path = BASE / 'data_freeze/meta/r2e_subset.jsonl'
swe = jsonl(swe_path)
r2e = jsonl(r2e_path)
heldout = {'hydra', 'bokeh', 'tornado', 'pyramid'}
pool_ids = set(nav_by)
current_ids = {t['instance_id'] for t in nav['tasks'] if t['work_group'] == 'current52'}
assert len(current_ids) == 52 and len(pool_ids) == 264
assert {t['instance_id'] for t in index['tasks']} == current_ids

# 以下只改变本报告分析字段，不修改原reward、原材料和共享账本。
manual = {
 'dask__dask-7138': (0, 'normal_failure', '同原FP CPU补评0；漏array=兼容；原GPU null保留。', OWNER/'swe_dask/preparation.md'),
 'dask__dask-7305': (0, 'normal_failure', '同原FP CPU补评0；大uint64重分区端点错误；原GPU null/PID143保留。', OWNER/'swe_dask/preparation.md'),
 'dask__dask-9378': (1, 'bounded_success', '同原FP CPU补评1；按已选B默认mask/有效值目标成立，dtype/可选参数缺陷仍在。', OWNER/'swe_dask/preparation.md'),
 'dask__dask-8801': (1, 'diagnostic_or_material_hold', '行为45参考通过，但fresh23中4项诊断失败；v7仅诊断，不把行为1视为完整成功/训练reward。', OWNER/'swe_dask/preparation.md'),
 'iterative__dvc-9395': (0, 'normal_failure', '同原FP CPU补评0：F0/3、P37/37；原GPU relay清理异常/null保留。', OWNER/'swe_dvc/tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_owner_readback_v1.md'),
 'aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52': (0, 'normal_failure', '原58键raw1；R22新增取消清理P2P后完整原FP58/59，失败；未来新求解须新runtime binding。', OWNER/'r2e_aiohttp/revision_1c1_cancelled_main_p2p_20261003/results_five_rows_20261003_v2.json'),
 'aiohttp__240da100151933883d7dea0528d45877df025b92': (None, 'normal_failure', '原null/参考未执行；候选自行checkout撤回兼容层致SyntaxError，语义归因候选失败，不补写reward0。', OWNER/'r2e_aiohttp/240d_trajectory_analysis_20261003.md'),
 'aiohttp__618335186f22834c0d8daabcf53ccf44d42488a2': (None, 'normal_failure', '原null/参考未执行；候选自行checkout撤回兼容层致SyntaxError，语义归因候选失败，不补写reward0。', OWNER/'r2e_aiohttp/6183_trajectory_analysis_20261003.md'),
 'coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5': (0, 'normal_failure', '原R17/49键raw1；R28/51键完整原FP补评50/51=0。新版actor/overlay资格未验。', OWNER/'r2e_coveragepy/tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/cpu/scoring51_final_acceptance_20261004_v1.json'),
 'datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb': (0, 'diagnostic_or_material_hold', '正常16/17=0、转义冒号路径回归有证；CPU/GPU baseline环境血缘null的formal gate未闭，单独留作诊断。', BOARD_PATH),
}
qwen_overrides = {
 'pydantic__pydantic-6283': (0, 'normal_failure', '原Qwen FP在v2补评0，合法PrivateAttr回归；与新Coder求解环境不同。'),
 'pydantic__pydantic-8511': (0, 'normal_failure', 'R27/177键原完整FP补评0：旧173过、新4项失败；原raw1保留。'),
 'coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5': (0, 'normal_failure', 'R28/51键原完整FP补评50/51=0；旧49/raw1保留。'),
 'dask__dask-8801': (1, 'diagnostic_or_material_hold', '行为分1；fresh13=9pass/4fail，完整诊断失败，v7仅诊断。'),
 'datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb': (0, 'diagnostic_or_material_hold', '正常16/17=0但环境血缘formal gate未闭。'),
}
timings = defaultdict(lambda: defaultdict(list))
raw_counts = defaultdict(Counter)
source_raw = defaultdict(Counter)
intervals = []
rows = []
hash_mismatches = []
selected_timing = defaultdict(lambda: defaultdict(list))
for t in index['tasks']:
    iid = t['instance_id']
    nt = nav_by[iid]
    attempts = []
    for a in t['attempts']:
        ap = Path(a['attempt'])
        payload = read(ap)
        if sha256((ROOT/ap).read_bytes()).hexdigest() != a['attempt_sha256']:
            hash_mismatches.append(str(ap))
        rp = ap.parent.parent/'grading/report.json'
        r = read(rp) if (ROOT/rp).exists() else {}
        indexed_report = next((x for x in a['local_artifact_files'] if x['path']==str(rp)), None)
        if r and indexed_report and sha256((ROOT/rp).read_bytes()).hexdigest()!=indexed_report['sha256']:
            hash_mismatches.append(str(rp))
        vals = {'solve_seconds': payload.get('solve_seconds')}
        if payload.get('started_at') and payload.get('finished_at'):
            vals['actor_wall_seconds'] = (dt(payload['finished_at'])-dt(payload['started_at'])).total_seconds()
        for k in ['total_grading_seconds', 'env_reset_seconds', 'prep_seconds', 'test_seconds']:
            vals[k] = r.get('timings', {}).get(k)
        if payload.get('started_at') and r.get('graded_at_utc'):
            vals['start_to_grade_seconds'] = (dt(r['graded_at_utc'])-dt(payload['started_at'])).total_seconds()
            intervals.append((dt(payload['started_at']), dt(r['graded_at_utc'])))
        for k, v in vals.items():
            if isinstance(v, (int, float)):
                timings[a['model']][k].append(v)
        reward = r.get('reward')
        raw_counts[a['model']][str(reward)] += 1
        source_raw[t['source']+'::'+a['model']][str(reward)] += 1
        attempts.append({'job_id': a['job_id'], 'model': a['model'], 'attempt_ref': str(ap),
                         'attempt_sha256': a['attempt_sha256'], 'raw_report_ref': str(rp) if r else None,
                         'raw_reward': reward, 'raw_outcome': r.get('outcome'),
                         'failure_category': r.get('failure_category'),
                         'grader_version': r.get('grader_version'),
                         'termination': payload.get('termination'), 'started_at': payload.get('started_at'),
                         'base_commit': a['base_commit'], 'actor_image_id': a['actor_image_id'],
                         'candidate_digest': payload.get('candidate', {}).get('frozen_patch_digest'),
                         'timing_seconds': {k: round(v, 6) if v is not None else None for k, v in vals.items()}})
    coder = [a for a in attempts if a['model']=='coder']
    qwen = [a for a in attempts if a['model']=='qwen36']
    assert len(coder)==1
    c = coder[0]
    q = max(qwen, key=lambda a:a['started_at'])
    route = 'bounded_success' if c['raw_reward']==1 else ('normal_failure' if c['raw_reward']==0 else 'unknown')
    cr = {'route': route, 'latest_observed_scoring_result': c['raw_reward'],
          'score_origin_scope': '原始report，分数不等于训练资格',
          'reason': nt['quality_summary'], 'evidence_ref': str(BOARD_PATH),
          'material_scope': '按题目已核范围；非稳定能力/训练准入'}
    if iid in manual:
        score, route, reason, ref = manual[iid]
        cr.update(route=route, latest_observed_scoring_result=score, reason=reason, evidence_ref=str(ref))
        cr['score_origin_scope'] = '关联同原FP CPU评分；原始report不回写'
    if iid.startswith(('aiohttp__240d','aiohttp__6183')):
        cr['score_origin_scope'] = '原始null；候选失败为独立语义归因，不制造reward0'
    if iid.startswith('aiohttp__1c1c'):
        cr['score_origin_scope'] = '新59键CPU五行的reward_new_material_diagnosis=0；不是未来runtime/训练资格'
    if iid=='dask__dask-8801':
        cr['score_origin_scope'] = '同原FP CPU行为分1；fresh诊断失败，两层结果不能合并成完整成功'
    if iid.startswith('datalad__6b6f'):
        cr['score_origin_scope'] = '原始report0；环境血缘formal gate未闭'
    if iid=='pydantic__pydantic-8511':
        cr['material_scope'] = 'Coder只保留旧173参考下0；未发现新177参考下Coder完整FP补评，不冒充最新材料成绩。'
        cr['current_material_exact_reward'] = 'unknown'
    qr = {'selected_job_id': q['job_id'], 'route': 'bounded_success' if q['raw_reward']==1 else 'normal_failure',
          'latest_observed_scoring_result': q['raw_reward'], 'reason': nt['quality_summary']}
    if iid in qwen_overrides:
        score, route, reason = qwen_overrides[iid]
        qr.update(route=route, latest_observed_scoring_result=score, reason=reason)
    for sel in [c,q]:
        for k,v in sel['timing_seconds'].items():
            if v is not None: selected_timing[sel['model']][k].append(v)
    bp = board_by[iid]['progress']
    rows.append({'instance_id': iid, 'source': t['source'], 'repository': t['repository'],
                 'current_material': bp.get('material_version'), 'current_checkpoint_at': bp.get('updated_at'),
                 'coder': cr, 'qwen_control': qr, 'original_attempts': attempts,
                 'latest_owner_checkpoint': bp.get('checkpoint'), 'specific_limit': bp.get('blocker'),
                 'next_action_from_owner': bp.get('next_action'),
                 'original_attempt_count': len(attempts),
                 'training_admission': 'not_established_by_this_audit',
                 'semantic_verification_scope': '本次复用题主/既有独立语义结论，未重新逐轨迹语义审查',
                 'navigation_ref': str(NAV_PATH), 'source_board_ref': str(BOARD_PATH),
                 'owner_directory': t['owner_directory']})

def repo_short(s): return s.split('/')[-1].lower()
swe_current = [r for r in swe if r['instance_id'] in pool_ids]
swe_train = [r for r in swe if repo_short(r['repo']) not in heldout]
swe_out = [r for r in swe_train if r['instance_id'] not in pool_ids]
r2e_train = [r for r in r2e if r['repo_name'] not in heldout]
r2e_out = [r for r in r2e_train if r['repo_name']+'__'+r['commit_hash'] not in pool_ids]
assert len(swe_current)==216
assert len(r2e_train)-len(r2e_out)==48
groups216 = {(r['repo'],str(r['version'])) for r in swe_current}
groups52 = {(r['repo'],str(r['version'])) for r in swe if r['instance_id'] in current_ids}
group_rows = []
for repo, version in sorted({(r['repo'],str(r['version'])) for r in swe_train}):
    filt=lambda x: x['repo']==repo and str(x['version'])==version
    group_rows.append({'repo':repo, 'version':version,
                       'current216_count':sum(filt(x) for x in swe_current),
                       'current52_swe_count':sum(filt(x) and x['instance_id'] in current_ids for x in swe_current),
                       'outside216_count':sum(filt(x) for x in swe_out)})
old6=[t for t in nav['tasks'] if t['work_group']=='old17' and not t['has_model_execution_record']]
unprobed=[t for t in nav['tasks'] if t['work_group']=='quality142' and not t['has_model_execution_record']]
assert len(old6)==6 and len(unprobed)==129
full_r2e_path=Path('runs/env_overnight_20260916/M3/probe_data/r2e_candidates_full.jsonl')
full_r2e=jsonl(full_r2e_path)
cross={(repo_short(x['repo']),x['base_commit']) for x in swe}&{(x['repo_name'],x['commit_hash']) for x in r2e}
verified=jsonl(BASE/'data_freeze/meta/verified.jsonl')
verified_repos={repo_short(r['repo']) for r in verified}
train_repos={repo_short(r['repo']) for r in swe_train}|{r['repo_name'] for r in r2e_train}

out={
 'schema':'rh2.data_expansion_local_evidence.v1',
 'as_of':'2026-10-05', 'scope':'本地只读重算；未运行远端、容器、模型；只新增本设计目录文件。',
 'summary':{'task_count':52,'historical_attempt_count':sum(len(t['original_attempts']) for t in rows),
             'original_raw_reward_counts':dict(raw_counts),'original_raw_by_source':dict(source_raw),
             'coder_routes':dict(Counter(r['coder']['route'] for r in rows)),
             'qwen_control_routes':dict(Counter(r['qwen_control']['route'] for r in rows)),
             'routes_are_not_training_admission':True,
             'extra_historical_qwen_tasks':[r['instance_id'] for r in rows if r['original_attempt_count']>2],
             'attempt_sha_checked_count':sum(len(t['original_attempts']) for t in rows),
             'original_report_count':sum(a['raw_report_ref'] is not None for t in rows for a in t['original_attempts']),
             'attempt_hash_mismatches':hash_mismatches},
 'classification_rules':{
   'bounded_success':'已核定题目范围内的成功；不是全部API正确、稳定成功或训练已准入。',
   'normal_failure':'包括有效0、同原FP补评0及有证据的候选失败/raw null；三者字段分开。',
   'diagnostic_or_material_hold':'本轮Dask8801仅诊断及Datalad环境血缘缺口，不计完整成功/可直接训练。',
   'unknown':'证据不足时保留unknown；本轮没有把未知补写为0/1。',
   'admission_limit':'本盘点不建立准入，不表示历史无training_candidate标签，也不证明尚未训练；实际准入/训练运行事实需查对应原件。',
   'comparison_limit':'按每题最新已核范围分流，不合并成同材料严格模型胜率；Pydantic等有跨求解环境，旧Qwen可能只补评。'},
 'tasks52':rows,
 'pool_recount':{
   'swe_full':{'rows':len(swe),'unique_instance_ids':len({r['instance_id'] for r in swe}),
      'unique_repo_base_commit':len({(r['repo'],r['base_commit']) for r in swe}),
      'heldout_rows':len(swe)-len(swe_train),'after_heldout':len(swe_train),'current216':len(swe_current),
      'outside_current216':len(swe_out),'repo_counts_full':dict(Counter(r['repo'] for r in swe)),
      'repo_counts_outside216':dict(Counter(r['repo'] for r in swe_out)),
      'groups_in_current216':len(groups216),'groups_in_current52_swe34':len(groups52),
      'outside_rows_matching_216_repo_version':sum((r['repo'],str(r['version'])) in groups216 for r in swe_out),
      'outside_rows_matching_52_repo_version':sum((r['repo'],str(r['version'])) in groups52 for r in swe_out),
      'matching216_by_repo':dict(Counter(r['repo'] for r in swe_out if (r['repo'],str(r['version'])) in groups216)),
      'metadata_fields':sorted(swe[0]),'repo_version_groups':group_rows},
   'r2e_subset':{'rows':len(r2e),'unique_repo_fix_commit':len({(r['repo_name'],r['commit_hash']) for r in r2e}),
      'heldout_rows':len(r2e)-len(r2e_train),'after_heldout':len(r2e_train),'current48':48,
      'outside_current48':len(r2e_out),'repo_counts_full':dict(Counter(r['repo_name'] for r in r2e)),
      'repo_counts_outside48':dict(Counter(r['repo_name'] for r in r2e_out)),
      'metadata_fields':sorted(r2e[0]),'same_version_reuse':'unknown: 元数据无version或真实base_commit；commit_hash为fix commit。',
      'local_full_payload_checked':str(full_r2e_path),'local_full_payload_rows':len(full_r2e),
      'local_full_payload_outside_current48':sum(r['repo_name']+'__'+r['commit_hash'] not in pool_ids for r in full_r2e)},
   'heldout_repositories':sorted(heldout),'train_verified_repo_overlap':sorted(train_repos & verified_repos),
   'cross_source_swe_base_vs_r2e_fix_textual_matches':len(cross),
   'cross_source_match_warning':'34组均pandas；base与fix commit语义不同，不能当独立任务去重或相同环境证明。',
   'old6_no_model_records':[{k:t[k] for k in ['instance_id','source','repository','quality_summary','next_action']} for t in old6],
   'quality142_unprobed129_by_repo':dict(Counter(t['repository'] for t in unprobed)),
   'quality142_unprobed129_ids':[t['instance_id'] for t in unprobed],
   'availability_boundary':'2130/4080是元数据候选数；本次未核远端registry、镜像实际可拉取性/离线恢复或池外完整题包。'},
 'timing':{'historical_all_attempts':{m:{k:stats(v) for k,v in d.items()} for m,d in timings.items()},
   'latest_model_attempt_per_task_not_cpu_regrades':{m:{k:stats(v) for k,v in d.items()} for m,d in selected_timing.items()},
   'first_attempt_start_utc':min(s for s,e in intervals).isoformat(),
   'last_original_grade_utc':max(e for s,e in intervals).isoformat(),
   'observed_window_seconds':(max(e for s,e in intervals)-min(s for s,e in intervals)).total_seconds(),
   'limits':['solve_seconds、actor起止、grader总耗时是不同区间；prep等子阶段不可重复相加。',
     '多attempt有重叠和人工调度间隔；区间总和不是实际墙钟或GPU占用。',
     'queue_wait=0只描述grader内部队列，不包括GPU派发排队、材料等待或人工审查。',
     '原105份评分含infra失败，且不含后续CPU补评成本；DVC9395原grader未运行。',
     '未测新数据分布、冷镜像拉取、首次构建、训练learner、稳定并发；不能给生产吞吐承诺。']},
 'source_evidence':[evidence(p) for p in [NAV_PATH,INDEX_PATH,BOARD_PATH,swe_path,r2e_path,
       BASE/'data_freeze/meta/heldout_candidates.jsonl',BASE/'data_freeze/meta/verified.jsonl',
       BASE/'data_freeze/heldout_proposal.md',full_r2e_path]],
}
assert out['summary']['historical_attempt_count']==106
assert not hash_mismatches
assert len(rows)==52
(HERE/'local_evidence.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'summary':out['summary'], 'swe_outside':len(swe_out), 'r2e_outside':len(r2e_out),
                  'written':str((HERE/'local_evidence.json').relative_to(ROOT))},ensure_ascii=False,indent=2))
