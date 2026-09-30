"""把 probe_matrix / probe_extra 的输出按公开要求期望压成 ✓/✗ 表（供 review_v3.md 引用）。
用法：python matrix_table.py out/sim
"""
import json
import sys
from pathlib import Path

sys.argv = [sys.argv[0], sys.argv[1], '/dev/null']
SIM = Path(sys.argv[1])
exec(compile(Path(__file__).with_name('summarize.py').read_text().split("\nrows = {}")[0].split("g = next(")[0], 'summarize_head', 'exec'))
src = Path(__file__).with_name('summarize.py').read_text()
start = src.index('DOC_Y =')
end = src.index('\n\n\ndef simgrade')
exec(src[start:end])
EXPECT.update({
    'S24_field_default_gt_then_ser_pv': ['Gt', -5, {'x': '#-5'}, '{"x":"#-5"}'],
    'S25_strictbool_ser_pv': [True, {'z': '1'}, '{"z":"1"}'],
    'S26_positiveint_ser_pv': [-5, {'z': '#-5'}],
})
COLS = [
    ('S02_docs_validator_ordering', '文档排序例'),
    ('S03_strictbool_pv', 'StrictBool+PV'),
    ('S04_positiveint_pv_minus5', 'PositiveInt+PV'),
    ('S05_field_default_gt_pv_minus5', '=Field(gt)+PV'),
    ('S06_field_default_strict_pv', '=Field(strict)+PV'),
    ('S07_field_default_maxlen_pv', '=Field(max_len)+PV'),
    ('S24_field_default_gt_then_ser_pv', '=Field(gt)+[ser,PV]'),
    ('S25_strictbool_ser_pv', 'StrictBool+[ser,PV]'),
    ('S09_before_left_of_ser_pv', 'Before 在左'),
    ('S10_wrap_left_of_ser_pv', 'Wrap 在左'),
    ('S08v_A08_between_after_validation', '夹中间验证器不运行'),
    ('S13v_nested_alias_ser_after_then_pv', '嵌套别名验证器不运行'),
    ('S12_ser_field_ge_pv', '[ser,Field(ge),PV]'),
    ('S11_ser_withjsonschema_pv', '[ser,WJS,PV]'),
    ('S23_ser_strict_pv_between_nonwrapping', '[ser,Strict,PV]'),
    ('S08s_A08_between_after_dump', 'A08 序列化'),
    ('S14_info_serializer_before_pv', '带 info 的 ser'),
    ('S19_wrapserializer_before_pv', 'WrapSerializer'),
    ('S16_both_sides_serializers', '两侧都有 ser'),
    ('S15_unknown_type_pv', '未知类型'),
]
rows = []
for d in sorted(p for p in SIM.iterdir() if p.is_dir()):
    got = {}
    for f in ('probe.out', 'probe_extra.out'):
        p = d / f
        if p.exists():
            for ln in p.read_text().splitlines():
                if ln.startswith('RH2PROBE '):
                    r = json.loads(ln[9:])
                    got[r['id']] = r['got']
    marks = []
    for cid, _ in COLS:
        marks.append('—' if cid not in got else ('✓' if got[cid] == EXPECT[cid] else '✗'))
    rows.append((d.name, marks))
print('| 候选 | ' + ' | '.join(c for _, c in COLS) + ' |')
print('|' + ' --- |' * (len(COLS) + 1))
for name, marks in rows:
    print(f'| `{name}` | ' + ' | '.join(marks) + ' |')
