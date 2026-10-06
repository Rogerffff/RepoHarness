# pydantic__pydantic-8583 · 反例期望

- 仓库/版本：`pydantic/pydantic` @ `e131d53a07da080c2ba642775efa9e81cb2cf0ba`（version 2.6，python 3.8）
- 镜像：`xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8583:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header`
- 判分面：F2P 1 条、P2P 51 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_pydantic / records/pydantic__pydantic-8583.json issues[0] 与 issues[1]`
- 断言编号：gold_is_workaround P1 + oracle_over_constrained P2（check 27 / check 24）
- 原文摘要：在镜像里把 reversed 换成别的顺序（如按 ref 名排序），看 F2P 是否仍绿——若绿则证明断言绑定的是顺序而非语义。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/pydantic__pydantic-8583.fake.diff` | `clean_schema` 里用 `sorted(schema['definitions'], key=ref)` 代替 gold 的 `list(reversed(...))`。 | **unknown** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 unknown）**：gold 本身就是一个顺序变通（把 definitions 列表倒过来），F2P 是约 60 行的精确字典断言。换成另一种确定性顺序之后，F2P 是否仍绿完全取决于该断言绑定的是『某一具体顺序』还是『discriminator 子结构』——这正是要测的东西，所以预期只能写 unknown。绿=断言绑语义，红=断言把 gold 的具体顺序钉死了。

## 4. 正确评分器应该抓到什么

断言应当收敛到『discriminator 存在且 mapping 正确』这一子结构，而不是整份 definitions 的排列。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 预期结果（当前判分下）

- `fake` → **不确定，必须实跑**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
