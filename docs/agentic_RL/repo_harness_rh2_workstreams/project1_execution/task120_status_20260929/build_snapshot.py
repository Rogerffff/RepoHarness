"""Aggregate a manually reconciled task inventory; never infer findings by keyword."""

import csv
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'AGENTS.md').is_file() and (p / 'rh2').is_dir())
OUT = Path(__file__).resolve().parent
EXEC = ROOT / 'docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution'
OLD = EXEC / 'swegym40_status_20260929'
NEW = EXEC / 'swegym_task_audit_20260920/quality_expansion_20260925'
CPU = EXEC / 'swegym_cpu_preprobe_20260929'
R2E = EXEC / 'r2e_lifecycle_20260929'

LABELS = {
    'C': '核心或常用行为的测试覆盖不足',
    'B': '已登记的边界／非核心覆盖限制',
    'T': '测试约束过窄或存在误拒风险',
    'P': '题面、复现说明或验收范围不一致',
    'G': '尚待处置的参考修复缺陷',
    'E': '开发环境存在兼容性或工具限制',
    'R': '评分材料、解析、安装或版本接入问题',
    'O': '公开旧测试与目标修复冲突',
    'D': '任务要求与现有补丁交付方式冲突',
    'H': '公开题面直接提供修法或答案',
}
ACTIONS = {
    1: '未留必须先修的已知题级问题，可衔接普通探针',
    2: '先完成明确修复或验收收口',
    3: '先做有明确目标的诊断或范围核定',
}
BLOCKERS = {
    'scope': '公开目标与验收关系尚需核定',
    'diagnostic': '已有具体疑点，先做辨别实验',
    'positive_control': '参考修复不可靠，先确认有效正对照',
    'unreviewed': '题目质量调查尚未完成',
    'audit': '已有受限比较决定，须执行约定语义审计',
    'condition': '复用已验证题级条件，另核公共运行入口',
    'repair': '具体修法和验证方向已明确',
    'closeout': '主要剩独立验收、版本登记或卡片收口',
    'implementation_dependency': '题级修法明确，等待共用实现支持',
}


def read_json(path):
    return json.loads(path.read_text())


def rel(path):
    path = Path(path)
    if not path.is_absolute():
        path = ROOT / path
    return str(path.relative_to(ROOT))


def link(path, label='依据'):
    return f'[{label}](/{rel(path)})'


def md_link(path, label='依据'):
    import os
    return f'[{label}]({os.path.relpath(ROOT / path, OUT)})'


def main():
    policy_review = read_json(OUT / 'ordinary_probe_review_v2.json')
    review_by_key = {(r['source'], r['key']): r for r in policy_review['tasks']}
    assert len(review_by_key) == 38
    authored = {}
    with (OUT / 'classification.tsv').open() as f:
        for row in csv.DictReader(f, delimiter='\t'):
            k = (row['source'], row['key'])
            assert k not in authored, k
            assert row['action'] in ('1', '2', '3'), row
            for col in ('confirmed', 'suspected'):
                row[col] = row[col].split(',') if row[col] else []
                assert set(row[col]) <= set(LABELS), row
            assert not set(row['confirmed']) & set(row['suspected']), row
            authored[k] = row

    old = read_json(OLD / 'status.json')['tasks']
    new = read_json(NEW / 'manifest.json')['tasks']
    r2e = read_json(R2E / 'board.json')['tasks']
    assert len(old) == 40 and len(new) == 32 and len(r2e) == 48
    assert not {t['instance_id'] for t in old} & {t['instance_id'] for t in new}
    rows = []
    used = set()

    for source, batch, tasks in [('SWE', 'original40', old), ('SWE', 'new32', new), ('R2E', 'r2e48', r2e)]:
        for task in tasks:
            iid = task['instance_id']
            key = iid.split('__')[-1] if source == 'SWE' else task['short']
            k = (source, key)
            if k in authored:
                authored_row = authored[k]
                used.add(k)
            else:
                assert source == 'R2E' and task['state'] in ('queued', 'public_read'), k
                partial = task['state'] == 'public_read'
                authored_row = {
                    'action': '3', 'blocker': 'unreviewed',
                    'confirmed': ['R'] if key == 'numpy__2f4a9650' else [], 'suspected': [],
                    'situation': '尚无完整题目质量结论；' + ('公开阅读交付未完成。' if partial else '已有环境记录，不能据此判断题面／测试正常。'),
                    'next_action': '从现有材料继续公开阅读、主审与独立复核，同时验证必要开发操作；复用已有环境证据。',
                }
                if key == 'numpy__2f4a9650':
                    authored_row['situation'] += '本机未采用已登记资源配方，gold 141/142。'
                    authored_row['next_action'] += '按题恢复 /tmp 6 GiB、内存 12 GiB 配方后重验资源路径。'
            refs = []
            extra_refs = []
            if source == 'SWE':
                if batch == 'original40':
                    refs.append(rel(OLD / 'status.json'))
                    if task.get('review_file'):
                        p = Path(task['review_file'])
                        if not p.is_absolute() and not (ROOT / p).exists():
                            p = OLD / p
                        if p.exists() or (ROOT / p).exists():
                            extra_refs.append(rel(p))
                    static = Path(task['static_result_dir'])
                    if not static.is_absolute():
                        static = ROOT / static
                    if (static / 'card.md').exists():
                        refs.append(rel(static / 'card.md'))
                else:
                    refs += [rel(NEW / 'results' / iid / x) for x in ('card.md', 'screening_record.json', 'review.md')]
                cpu = CPU / 'tasks' / iid / 'result.md'
                if cpu.exists():
                    refs.insert(0, rel(cpu))
                    extra_refs.append(rel(CPU / 'reviews/root_progress_review.md'))
                if key in ('pandas-50319', 'pandas-53958'):
                    b = '03_20260921_v1' if key == 'pandas-50319' else '02_20260921_v2'
                    extra_refs.append(f'runs/swegym_quality_batch{b}/public/{iid}/user_prompt.txt')
            else:
                d = R2E / 'results' / iid
                for name in ('probe_card.md', 'card.md', 'revision_plan.md', 'screening_record.json', 'review.md', 'public_read.md'):
                    if (d / name).exists():
                        refs.append(rel(d / name))
                if not refs:
                    refs = [rel(R2E / 'board.json')]
                overrides = {
                    'pandas__4ec87eb9': 'review_decision_pandas_4ec8.md',
                    'pillow__4bc64835': 'review_revision_pillow_4bc6.md',
                    'pillow__2b061b68': 'review_revision_pillow.md',
                    'orange3__9b5494e2': 'review_revision_orange3.md',
                    'orange3__22e98f8f': 'review_revision_orange3.md',
                }
                if key in overrides:
                    f = R2E / 'codex_reviews' / overrides[key]
                    if not f.exists() and key.startswith('orange3__'):
                        options = list((R2E / 'codex_reviews').glob('review_revision_orange*.md'))
                        assert len(options) == 1, options
                        f = options[0]
                    refs.insert(0, rel(f))
                if key in ('aiohttp__4075c653', 'pillow__2d01f7d0'):
                    refs.insert(0, rel(R2E / 'codex_reviews/status_check_20260929.md'))
                if key == 'numpy__2f4a9650':
                    refs.insert(0, rel(R2E / 'README.md'))
                extra_refs.append(rel(R2E / 'codex_reviews/status_check_20260929.md'))

            row = {
                'source': source, 'batch': batch, 'instance_id': iid,
                'short_name': key, 'repo': task.get('repo'),
                'next_action_category': int(authored_row['action']),
                'next_action_category_label': ACTIONS[int(authored_row['action'])],
                'reason_code': authored_row['blocker'], 'reason_label': BLOCKERS[authored_row['blocker']],
                'confirmed_issue_tags': authored_row['confirmed'],
                'suspected_issue_tags': authored_row['suspected'],
                'current_situation': authored_row['situation'],
                'next_action': authored_row['next_action'],
                'evidence_refs': list(dict.fromkeys(refs + extra_refs)),
                'classification_is_recommendation_not_new_admission': True,
            }
            if k in review_by_key:
                review = review_by_key[k]
                assert row['next_action_category'] == review['new_category'], k
                row['ordinary_probe_review_v2'] = review
                row['evidence_refs'] = list(dict.fromkeys(row['evidence_refs'] + review['evidence_refs']))
            if row['next_action_category'] == 1:
                assert k in review_by_key and review_by_key[k]['new_category'] == 1, k
                assert review_by_key[k]['why_no_required_repair'], k
                assert row['reason_code'] != 'audit', k
            if source == 'SWE' and batch == 'original40':
                row['historical_probe_pool_19'] = bool(task['task2_probe_pool_0925'])
                row['prior_current_use'] = task['current_use']
                row['previous_repairs'] = task['verified_repairs']
            if source == 'R2E':
                row['author_board_state'] = task['state']
                row['previous_environment_state'] = task['environment_state_0928']
            assert row['evidence_refs'], iid
            assert all((ROOT / f).is_file() for f in row['evidence_refs']), (iid, row['evidence_refs'])
            rows.append(row)
    assert used == set(authored), set(authored) - used
    assert len(rows) == 120 and len({(r['source'], r['instance_id']) for r in rows}) == 120

    summary = {}
    for source in ('SWE', 'R2E', 'ALL'):
        group = [r for r in rows if source == 'ALL' or r['source'] == source]
        summary[source] = {
            'tasks': len(group),
            'next_actions': {str(k): sum(r['next_action_category'] == k for r in group) for k in ACTIONS},
            'category3_reasons': dict(Counter(r['reason_code'] for r in group if r['next_action_category'] == 3)),
            'confirmed_tags': {k: sum(k in r['confirmed_issue_tags'] for r in group) for k in LABELS},
            'suspected_tags': {k: sum(k in r['suspected_issue_tags'] for r in group) for k in LABELS},
            'at_least_one_confirmed_issue_or_limit': sum(bool(r['confirmed_issue_tags']) for r in group),
            'only_suspected_issues': sum(not r['confirmed_issue_tags'] and bool(r['suspected_issue_tags']) for r in group),
            'quality_review_incomplete': sum(r['reason_code'] == 'unreviewed' for r in group),
        }
    inputs = [OUT / 'classification.tsv', OUT / 'ordinary_probe_review_v2.json', OLD / 'status.json', NEW / 'manifest.json', R2E / 'board.json']
    evidence_files = sorted({rel(f) for f in inputs} | {f for r in rows for f in r['evidence_refs']})
    index = {f: {'sha256': hashlib.sha256((ROOT / f).read_bytes()).hexdigest(), 'bytes': (ROOT / f).stat().st_size} for f in evidence_files}
    result = {
        'schema': 'task120_issue_and_action_inventory_v2',
        'as_of': datetime.now(ZoneInfo('Asia/Singapore')).isoformat(),
        'scope': 'SWE original40 plus disjoint new32; R2E subset48; no new experiment or admission',
        'method': 'Manual task-level reconciliation of current cards and later independent reviews. Confirmed includes static source facts; not all are runtime failures. Tags overlap and include nonblocking limitations. Closed repairs excluded from current tags. Missing investigation is not a healthy verdict.',
        'label_definitions': LABELS, 'action_definitions': ACTIONS,
        'classification_policy': policy_review['policy'],
        'prior_snapshot': 'history/initial_v1/snapshot.json',
        'summary': summary, 'tasks': rows,
    }
    (OUT / 'snapshot.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'evidence_index.json').write_text(json.dumps(index, ensure_ascii=False, indent=2) + '\n')

    for source in ('SWE', 'R2E'):
        group = [r for r in rows if r['source'] == source]
        lines = [f'# {source} 逐题现状（{len(group)}题）', '',
                 '整理：2026-09-29。这里是当前证据对应的下一步建议，不新增准入授权。**实**表示原件或已有运行支持，**疑**表示仍需验证的风险；静态确认不冒作运行实证。已关闭的修复不计当前问题。', '',
                 '类别1仅保留没有必须先修的已知题级缺陷、且影响结论的具体疑点已处置的题；旧受限比较许可不作豁免。类别2先修复或验收，类别3先诊断或核定范围。共用链路、镜像迁移与 GPU 预算仍须统一核对；进入探针不等于训练准入。', '']
        for action in ACTIONS:
            chosen = [r for r in group if r['next_action_category'] == action]
            lines += [f'## {action}．{ACTIONS[action]}：{len(chosen)}题', '', '| 题目 | 当前问题和已完成事项 | 下一步与依据 |', '| --- | --- | --- |']
            for r in chosen:
                tags = '；'.join([LABELS[k] + '（实）' for k in r['confirmed_issue_tags']] + [LABELS[k] + '（疑）' for k in r['suspected_issue_tags']])
                if not tags:
                    tags = '质量尚未查完，不能判断无问题' if r['reason_code'] == 'unreviewed' else '当前记录未列未解除问题'
                refs = ' / '.join(md_link(f, '依据' if n == 0 else f'补充{n}') for n, f in enumerate(r['evidence_refs'][:2]))
                reason = ''
                if action == 1:
                    reason = ' 当前不需先修的依据：' + r['ordinary_probe_review_v2']['why_no_required_repair']
                lines += [f"| {r['short_name']} | {tags}。{r['current_situation']} | {r['next_action']}{reason} {refs} |"]
            lines.append('')
        (OUT / f'{source.lower()}_tasks.md').write_text('\n'.join(lines))
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
