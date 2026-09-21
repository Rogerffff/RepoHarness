# python__mypy-15139 · 反例期望

- 仓库/版本：`python/mypy` @ `16b936c15b074db858729ed218248ef623070e03`（version 1.4，python 3.11）
- 镜像：`xingyaoww/sweb.eval.x86_64.python_s_mypy-15139:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA -k`
- 判分面：F2P 1 条、P2P 0 条
- 阶段一基线：未跑（task_signals.stage1 = null）

## 1. 断言来源

- 来源包：`L1_mypy_2 / records/python__mypy-15139.json issues[0]（issues[2] 的 file_boundary 见 mypy-10424 的 fake_helpers）`
- 断言编号：grading_coverage P1
- 原文摘要：写无条件小写的假修复跑当前 F2P（预期满分），再跑 check-classes.test 全量（预期大面积失败），量化当前评分的盲区。（证据：P2P=0；check-lowercase.test 有 8 条现成对称 case）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/python__mypy-15139.fake.diff` | `mypy/messages.py::format_literal_value` 的 TypeType 分支无条件返回小写 `type[...]`，不看 `options.use_lowercase_names()`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：唯一的 F2P `testTypeLowercaseSettingOff` 带 `--no-force-uppercase-builtins`，期望的正是小写；P2P=0。gold 的分支判断被丢掉之后，默认（大写）模式下所有 `Type[...]` 的既有期望全部失效，但那些 case 一条都没进判分面。

## 4. 正确评分器应该抓到什么

check-lowercase.test 里 8 条对称的大写 case，以及 check-classes.test 里所有期望 `Type[...]` 的既有 case。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_uppercase_cases` | `mypy/test/testcheck.py -k check-lowercase or check-classes` | L1 要求的量化面：无条件小写会让默认模式下的大写期望大面积失败 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一没跑过，本次兼作首次基线）
