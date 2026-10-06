# P-A 新规则的有界反证（2026-09-16）

范围：仅复核 `impl_plan_20260915.md` §7 的 P-A / R2；未检查 e1、S1 或其它切片。生产源码、主计划和昨日证据只读。本轮运行仅本机 CPU，未运行 Docker、SSH、模型、GPU 或 API。

证据：[探针](p_a_falsifier_probe.py)、[结果](p_a_falsifier_result.json)。探针仅在临时目录创建候选源码，调用真实 pytest、当前 RH2 parser、manager 的解析方法及 scoring 函数。资源项明确模拟未来分支输入，并非真实 OOM 实验。结果内保存所读源码与计划的 SHA256；运行时 Python 3.12.13、pytest 9.1.1，未声称覆盖所有任务镜像版本。

从仓库根目录复核：

```sh
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/impl_plan_followup_20260916/p_a_falsifier_probe.py
```

本次退出码 0，stdout 为 `P-A probe assertions passed; result written to p_a_falsifier_result.json`。所有关键结论有 assert；日志中的临时工作目录写为 `/testbed`。

## 已解决的入口问题

默认 pytest 运行候选 `src/thing.py` 的语法错误：rc=2，parser 得到 `{tests/test_thing.py: ERROR}`，`num_parsed_tests=1`，唯一参考 case 缺席，当前评分为 `tests_failed / reward=0`。日志同时包含 `ERROR collecting`、`Interrupted: 1 error during collection` 和指向候选源码的 `File` 行。新挂点能覆盖昨日真实反例，不再要求它进入零解析分支。

## 两项应在 producer 启用前收口的问题

1. **非零 `py_compile` 退出码不能证明 SyntaxError，且命令有写入和模块查找副作用。** 计划 §6 S2 / §7 R2（187、213 行）以同解释器 `python -m py_compile <path>` 失败作为语法复证。合法源码在 `src/__pycache__` 为普通文件时也返回 1，原因是写 pyc 时 `Not a directory`；相同源码用内存 `compile(bytes, filename, "exec")` 成功。正常 `py_compile` 即使加 `-B` 和 `PYTHONDONTWRITEBYTECODE=1` 仍写 pyc。此外，工作目录的 `py_compile.py` 会被 `-m` 选中，本探针的无害替身被执行并返回 1。以上不代表当前 P-A 已有生产误判，只直接推翻计划中的“失败即语法证明”。

   最小替代：用同一任务解释器执行可信的内存编译片段，读取目标源码字节，仅把捕获到的 `SyntaxError`（含其子类）当作正向语法事实；I/O、权限、进程失败等保持未知。沿现有候选非 root 身份执行，避免 CWD 同名模块查找和 pyc 写入。不为此扩展 D3 运行器完整性或建立通用平台。

2. **资源证据只否决新类别，无法阻止已有 reward 0 回落。** 计划 §7 R2（213 行）规定资源事实任一为真或读不到就“不产出新类别”；新挂点的当前分支却仍经 `manager.py:1462–1465` 调用 `scoring.grading_outcome_fields`，其余未解决结果统一成为 `tests_failed / reward=0`（`scoring.py:274–288`）。探针使用第一项真实 pytest verdict，分别假设 `oom_kill > 0` 或必需资源读取不可用，模拟否决新类别后保留旧函数，输出仍为 0。它只证明分支组合，未模拟或声称复现 OOM。

   最小替代：在已选中的“参考全缺席 + collection 全局失败”窄路径内，明确资源失败及归因所必需的未知事实先进入已有 infra / 无 reward 路径，优先于新类别和旧 `tests_failed` 回落。只补这条控制流，不给所有测试新增资源准入闸门。已确认资源失败不作负样本是 README §0 / §2 的既定语义，无需新一轮授权。

## 一项可递延的覆盖边界

候选根 `conftest.py` 启动时存在 SyntaxError，真实 pytest rc=4、parser={}、无 `ERROR collecting` 摘要，但回溯有候选文件且可复证 SyntaxError。当前 manager 按 `manager.py:2616–2622` 保持 `eval_log_zero_parsed_tests / infra`。因此计划 176 行关于零解析形态“正是证据最弱”的解释不成立。

可以分片，但当前 §7 仅把零解析留为 infra，尚未给这类已复证的语法错误列后续安排，不能据此核销原 R2 / A 的负样本遗漏。最小方案二选一：将同类 conftest 语法错误纳入，或标明 P-A 仅部分完成，并由 P-A 实现者登记后续切片、在规模筛查前验证这类形态。这里不要求首片覆盖所有导入错误、把空日志一律给 0，或研究更多 traceback 选项。

## 停止条件

正常 collection 路径的 rc / parser / 候选回溯已有真实命中证据，不继续泛化。producer 启用前，将语法事实改为无写入的类型化结果，并明确资源失败／必需证据未知的无 reward 分支；用对应窄控制流测试验证后即可继续。conftest 启动失败可纳入同类规则，或以 partial 状态、P-A 后续负责人和规模筛查前验收条件递延。以上不阻塞其它已授权切片或观测账本工作，不以本报告作为 P-A 的实现验收。
