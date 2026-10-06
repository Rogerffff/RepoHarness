# pydantic__pydantic-8793 · 反例期望

- 仓库/版本：`pydantic/pydantic` @ `832225b90672c68e2d4067bd0ffecf834d62b48b`（version 2.7，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8793:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header`
- 判分面：F2P 3 条、P2P 364 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_pydantic / records/pydantic__pydantic-8793.json issues[0]`
- 断言编号：oracle_accepts_wrong_fix P2（check 25）
- 原文摘要：在镜像里只改 `is_required()`，跑官方 367 条确认全绿。（proposed_action：在判分面补 `Model.model_fields['bar'].default is PydanticUndefined` 一类的状态断言，或把 tests/test_annotated.py 的 merge_field_infos 三条并入 P2P）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/pydantic__pydantic-8793.fake.diff` | 只把 `FieldInfo.is_required()` 改成『default 是 PydanticUndefined 或 Ellipsis 都算必填』，不修 `merge_field_infos`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：3 条 F2P 断言的都是生成出来的 JSON schema（`'required': ['bar']`、字段没有 `default` 键）。pydantic 是靠 `is_required()` 决定要不要给字段包 with-default schema 的，所以改这一个方法就能让 schema 正确。而 gold 修的是 `merge_field_infos` 里 `default=Ellipsis` 被原样 `setattr` 进 FieldInfo 的 bug —— 假修复下 `Model.model_fields['bar'].default` 仍然是 `Ellipsis`，判分面没有任何一条看这个状态。

## 4. 正确评分器应该抓到什么

`Model.model_fields['bar'].default is PydanticUndefined`；以及 `tests/test_annotated.py` 里 merge_field_infos 的三条。

判别用例脚本：`kits/pydantic__pydantic-8793/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_pydantic_8793.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
