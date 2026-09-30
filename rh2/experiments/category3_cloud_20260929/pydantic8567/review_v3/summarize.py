"""汇总 v3 聚焦复核的私有模拟评分与私有行为矩阵（不是正式评分）。

用法：python summarize.py <out/sim 目录> <grading_bundles_v2_v0.jsonl>
- 模拟评分：按评分包参考名单（F2P 1 项、P2P 158 项）逐名读 pytest -rA/-vv 的 PASSED/FAILED 行；
  reward=1 当且仅当 F2P 与 P2P 全部 PASSED 且无缺席。另记 F2P 的失败行号与第一条 `E ` 行。
- 行为矩阵：期望值按公开要求写（题面、validators.md、PlainValidator docstring、base 行为），不以 gold 为答案。
"""
import json
import re
import sys
from pathlib import Path

SIM, BUNDLES = Path(sys.argv[1]), sys.argv[2]
g = next(json.loads(x) for x in open(BUNDLES) if json.loads(x)['instance_id'] == 'pydantic__pydantic-8567')
F2P, P2P = g['fail_to_pass'], g['pass_to_pass']

DOC_Y = ['wrap-4: pre', 'before-4', 'wrap-3: pre', 'before-3', 'plain', 'after-3', 'wrap-3: post', 'after-4', 'wrap-4: post']
EXPECT = {
    # 题面核心要求的实例
    'S01_issue_example': [False, True, {'x': '0', 'y': '1'}, {'x': '0', 'y': '1'}, '{"x":"0","y":"1"}'],
    'S17_typeadapter_list': [[False, True], '["0","1"]'],
    'S18_when_used_json_before_pv': [{'x': 1234}, '{"x":"1,234"}'],
    'S21_optional': [{'z': None}, {'z': '1'}],
    'S14_info_serializer_before_pv': [{'z': '5:python'}, '{"z":"5:json"}'],
    'S11_ser_withjsonschema_pv': [True, {'z': '1'}, '{"z":"1"}'],
    'S12_ser_field_ge_pv': [-3, {'c': '#-3'}],
    'S23_ser_strict_pv_between_nonwrapping': [True, {'z': '1'}],
    # 已登记 T3 的核心要求边缘实例
    'S08s_A08_between_after_dump': [{'z': '#7'}, '{"z":"#7"}'],
    'S13s_nested_alias_ser_after_then_pv_dump': [{'z': '0'}, '{"z":"0"}'],
    'S19_wrapserializer_before_pv': {'z': 'w1'},
    'S16_both_sides_serializers': {'z': 'B'},
    # 要保护的 PlainValidator 公开行为（取代左侧/内层验证；短路；未知类型）
    'S02_docs_validator_ordering': DOC_Y,
    'S03_strictbool_pv': True,
    'S04_positiveint_pv_minus5': -5,
    'S05_field_default_gt_pv_minus5': -5,
    'S06_field_default_strict_pv': True,
    'S07_field_default_maxlen_pv': 'abcdef',
    'S08v_A08_between_after_validation': 7,
    'S09_before_left_of_ser_pv': [True, {'z': '1'}],
    'S10_wrap_left_of_ser_pv': [True, {'z': '1'}],
    'S10b_after_left_of_ser_pv_v3shape': [True, {'z': '1'}],
    'S13v_nested_alias_ser_after_then_pv': False,
    'S15_unknown_type_pv': ['Unsupported', 'Unsupported'],
    'S20_short_circuit': 'abc',
    'S22_strictbool_after_ser_pv_v3fix_shape': [True, {'z': '1'}],
}


def simgrade(path: Path):
    if not path.exists():
        return None
    text = path.read_text(errors='replace')
    st = {}
    for m in re.finditer(r'^(tests/\S+) (PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b', text, re.M):
        st.setdefault(m.group(1), m.group(2))
    f2p_ok = sum(st.get(t) == 'PASSED' for t in F2P)
    p2p_ok = sum(st.get(t) == 'PASSED' for t in P2P)
    missing = [t for t in F2P + P2P if t not in st]
    reward = int(f2p_ok == len(F2P) and p2p_ok == len(P2P) and not missing)
    loc, eline = '', ''
    m = re.search(r'_+ test_plain_validator_plain_serializer _+\n(.*?)(?:\n_{5,} |\n=+ )', text, re.S)
    if m:
        body = m.group(1).splitlines()
        locs = [ln for ln in body if re.match(r'^tests/test_validators\.py:\d+', ln)]
        loc = locs[0].split(':')[1] if locs else ''
        es = [ln for ln in body if ln.startswith('E ')]
        eline = es[0][1:].strip()[:110] if es else ''
    return {'reward': reward, 'f2p': f'{f2p_ok}/{len(F2P)}', 'p2p': f'{p2p_ok}/{len(P2P)}', 'missing': len(missing),
            'line': loc, 'E': eline}


def probe(path: Path):
    res = {}
    if not path.exists():
        return res
    for ln in path.read_text(errors='replace').splitlines():
        if ln.startswith('RH2PROBE '):
            r = json.loads(ln[len('RH2PROBE '):])
            res[r['id']] = r
    return res


rows = {}
for d in sorted(p for p in SIM.iterdir() if p.is_dir()):
    row = {'sim': {}, 'dev': {}, 'warn': {}}
    for tv in ('t_v3', 't_v3s', 't_v3sx', 't_v3sv2', 't_v3b'):
        row['sim'][tv] = simgrade(d / f'{tv}.out')
    pr = probe(d / 'probe.out')
    for cid, exp in EXPECT.items():
        r = pr.get(cid)
        if r is None:
            row['dev'][cid] = 'MISSING'
            continue
        if r['got'] != exp:
            row['dev'][cid] = r['got']
        if r['warn']:
            row['warn'][cid] = r['warn']
    rows[d.name] = row

print('## 私有模拟评分（reward；失败行号：第一条 E 行）')
for name, row in rows.items():
    cells = []
    for tv, s in row['sim'].items():
        if s is None:
            cells.append(f'{tv}=NA')
        else:
            extra = f" L{s['line']} {s['E'][:60]}" if s['reward'] == 0 and s['line'] else ''
            extra += f" p2p={s['p2p']}" if s['p2p'] != '158/158' else ''
            extra += f" missing={s['missing']}" if s['missing'] else ''
            cells.append(f"{tv}={s['reward']}{extra}")
    print(f'{name:30s} ' + ' | '.join(cells))
print()
print('## 行为矩阵：与公开要求期望不同的项')
for name, row in rows.items():
    devs = '; '.join(f'{k}={v!r}'[:160] for k, v in row['dev'].items())
    print(f'{name:30s} {devs or "（无偏差）"}' + (f"  warnings={row['warn']}" if row['warn'] else ''))
(SIM / 'summary.json').write_text(json.dumps(rows, ensure_ascii=False, indent=1, default=repr) + '\n')
