"""8316：在本机纯 re 复现 base 与 gold 的 to_snake，比较判分面内外的差异。
不需要 pydantic，直接 `python3 to_snake_diff.py`。"""
import re
def base(camel):  # alias_generators.py:42-44 @20c0c6d9
    s=re.sub(r'([a-zA-Z])([0-9])',lambda m:f'{m.group(1)}_{m.group(2)}',camel)
    s=re.sub(r'([a-z0-9])([A-Z])',lambda m:f'{m.group(1)}_{m.group(2)}',s)
    return s.lower()
def gold(camel):  # golden_patch 后的 to_snake
    s=re.sub(r'([A-Z]+)([A-Z][a-z])',lambda m:f'{m.group(1)}_{m.group(2)}',camel)
    s=re.sub(r'([a-z])([A-Z])',lambda m:f'{m.group(1)}_{m.group(2)}',s)
    s=re.sub(r'([0-9])([A-Z])',lambda m:f'{m.group(1)}_{m.group(2)}',s)
    s=re.sub(r'([a-z])([0-9])',lambda m:f'{m.group(1)}_{m.group(2)}',s)
    return s.lower()
GRADED=['camel_to_snake','camelToSnake','camel2Snake','_camelToSnake','camelToSnake_','__camelToSnake__','CamelToSnake','Camel2Snake','_CamelToSnake','CamelToSnake_','CAMELToSnake','__CamelToSnake__','Camel2','Camel2_','_Camel2','camel2','camel2_','_camel2']
UNGRADED=['CAMEL2','HTTP2','HTTPResponse','A1B2','HTTP2Response','XMLHttpRequest','IOError']
for title,xs in (('判分面内的 18 组 parametrize 参数',GRADED),('判分面之外的输入',UNGRADED)):
    print('---',title,'---')
    for p in xs:
        b,g=base(p),gold(p)
        print(f'{"DIFF" if b!=g else "    "} {p:20s} base={b:22s} gold={g}')
