# pydantic__pydantic-8500 · 反例期望

- 仓库/版本：`pydantic/pydantic` @ `069d0205424f98912f8b670b1bc5cfc7df37b2f3`（version 2.6，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8500:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header`
- 判分面：F2P 1 条、P2P 44 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_pydantic / records/pydantic__pydantic-8500.json issues[1]`
- 断言编号：oracle_accepts_wrong_fix P2（check 25）
- 原文摘要：在镜像里对 `model_construct` 尾部加 `m.__dict__ = dict(sorted(m.__dict__.items()))` 后跑官方 45 条，确认全绿。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/pydantic__pydantic-8500.fake.diff` | 不改 base 的『默认值最后 update』逻辑，只在写回 `__dict__` 前按字段名字母序排一遍。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `test_retain_order_of_fields` 用的模型是 `a: str = 'a'` / `b: str`，声明序恰好等于字母序，所以字母序排序也能得到 `{"a":"a","b":"b"}`。gold 要的是『保持 `cls.model_fields` 的声明序』，两者在这一条用例上无法区分。

## 4. 正确评分器应该抓到什么

把字段声明成非字母序（例如 `b: str = 'b'` 在前、`a: str` 在后）再 `model_construct(a='a')`，gold 给 `{"b":"b","a":"a"}`，假修复给 `{"a":"a","b":"b"}`。

判别用例脚本：`kits/pydantic__pydantic-8500/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_pydantic_8500.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：L3 已经用 DeepSeek 原始候选跑过本题的三态（`L3_trajectories/counterexamples/pydantic__pydantic-8500/`）。本条是**另一个**假修复（字母序），与 L3 的候选补丁不同，不要合并解读。
