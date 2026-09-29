# pydantic__pydantic-6043 · 反例期望

- 仓库/版本：`pydantic/pydantic` @ `d476599cdd956284595034d7d9fd046569a0574c`（version 2.02，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-6043:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header`
- 判分面：F2P 1 条、P2P 303 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_pydantic / records/pydantic__pydantic-6043.json issues[0]`
- 断言编号：oracle_almost_empty P1（check 25）
- 原文摘要：在镜像里只对 `generate()` 返回值的顶层 properties 做一次 sorted()，跑官方 304 条看是否全绿。（proposed_action：本题不宜作为训练样本；F2P 是改写既有断言得到的单条 key 顺序检查，最小 hack 即可满分）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/pydantic__pydantic-6043.fake.diff` | 只在 `GenerateJsonSchema.generate()` 末尾把顶层 `properties` 排序，不递归、不碰 `$defs`、不碰 `generate_definitions()`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_by_alias` 只断言 `list(model_json_schema(by_alias=True)['properties'].keys()) == ['Crackle','Snap']`。gold 是递归排序整个 schema 并且同样处理 `generate_definitions`，判分面对这两点都没有断言。

## 4. 正确评分器应该抓到什么

嵌套 `$defs` 内部的 key 是否有序；`generate_definitions()` 出口是否有序。

判别用例脚本：`kits/pydantic__pydantic-6043/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_pydantic_6043.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
