# pydantic__pydantic-8567 · 反例期望

- 仓库/版本：`pydantic/pydantic` @ `8060fa1cff965850e5e08a67ca73d5272dcdcf9f`（version 2.6，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8567:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header`
- 判分面：F2P 1 条、P2P 158 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_pydantic / records/pydantic__pydantic-8567.json issues[1]`
- 断言编号：oracle_weak_assertion P2（check 25(a)）
- 原文摘要：实现『无条件 str()』的错误修复跑官方 159 条。（proposed_action：把 F2P 的 isinstance 断言改成值断言（'0'/'1'））

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/pydantic__pydantic-8567.fake.diff` | 给 `PlainValidator` 挂一个无条件 `str()` 的序列化器，而不是 gold 的『把内层 schema 的序列化行为接回来』。 | **unknown** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 unknown）**：F2P `test_plain_validator_plain_serializer` 只断言 `isinstance(data['foo'], str)` / `isinstance(data['bar'], str)`，无条件 str() 在类型上必然满足（值会是 'True'/'False' 而不是题面要求的 '0'/'1'）。写 unknown 是因为这个改动对**所有** PlainValidator 字段生效，158 条 P2P 都在 `tests/test_validators.py` 内，其中可能有比较序列化后具体值的用例会因此变红 —— 必须实跑才知道。

## 4. 正确评分器应该抓到什么

值断言：`blah.model_dump()['foo'] == '0'` 且 `['bar'] == '1'`（gold 会把 PlainSerializer 的结果接回来）。

判别用例脚本：`kits/pydantic__pydantic-8567/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_pydantic_8567.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **不确定，必须实跑**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
