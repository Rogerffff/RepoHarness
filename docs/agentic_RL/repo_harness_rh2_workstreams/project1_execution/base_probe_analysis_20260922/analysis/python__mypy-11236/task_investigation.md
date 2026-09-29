# python__mypy-11236 任务级调查（基座探针 2026-09-22，B 线）

## 结论摘要

1. **判定：混合——DS a1/a2、Qwen3.6 a2 三条实质候选属 task_or_test_dispute（规范欠说明 + 实现路线绑定），Coder a1/a2、Qwen3.6 a1 三条属 model_failure；60 回合上限对六条的分数都不是因果；无环境 / 接口故障。置信度 high**（拒绝机制是确定性 diff，"是否属验收范围"留给用户裁定）。
2. 唯一 F2P 期望 7 行诊断，三条实质候选只差两处：`main:18`（`x: Final = (1,)` 后 `return x` 仍报错，题面未提 Final）和 `main:34/36`（`got "Tuple[Literal[False], int]"` 而非 `"Tuple[bool, int]"`，措辞随路线而变）。另三条与 noop 输出逐字相同。
3. 三条实质候选都是"把 Union 里多个同长元组按位置拼成推断上下文"，即上游讨论（模型不可见）里维护者提出的 "splicing" 方向；gold 走的是同一讨论里被称为 "quick-and-dirty (?)" 的另一条（子类型层比较 `last_known_value`）。F2P 只接受后者。
4. DS 两条在 actor 里跑完整 testcheck（5334 例）全过，既有用例 `testLiteralFinalGoesOnlyOneLevelDown` 反而把 Final 元组不匹配写成预期（带 TODO），同一 PR 的测试补丁改写了它但不在执行集——actor 可见的测试反馈与奖励反向。
5. 撞上限原因各异：DS 修好后反复验证（全量 75 s × 3）且从不发最终文本；Coder 在错误函数上循环 / 漫游；Qwen3.6 a1 只读不改；a2 在第 60 次调用才让复现通过。
6. P2P=0，评分不跑其余 5334 例。题卡两条静态预言（Final 未修、措辞变 Literal）3/3 应验。

## 1. 失败断言原文、六个候选与 gold

F2P `testLiteralAndInstanceSubtyping` 的 Expected 共 7 行：`main:14` note 与 `main:26/30/34/36/40/42` 六个 `Incompatible return value type` 错误。各候选 Actual 的差异：

| 尝试 | 候选改动 | Actual 多出 / 不同的行 |
| --- | --- | --- |
| noop | — | 多 `main:10/12`（Union 双分支合法返回被拒）、`main:18`（Final 元组） |
| DS a1 | `checkexpr.visit_tuple_expr`：多个同长元组时按位置 `UnionType.make_union` 拼上下文；在 `check-tuples.test` 加 4 例（非官方文件，投影带入） | 多 `main:18`；`main:34/36` 的 got 变为 `Tuple[Literal[False], int]` / `Tuple[Literal[True], str]` |
| DS a2 | 同上，用 `make_simplified_union`；在官方 `check-literal.test` 加 1 例（投影忽略） | 同 DS a1 |
| Qwen3.6 a2 | 同类：取 Union 中第一个含 Literal 的元组作上下文，`typeops.is_literal_type_like` 加 TupleType 分支；11 个草稿文件 | 同 DS a1 |
| Coder a1 | `subtypes.py`：`visit_tuple_type` 加空 `pass` 分支，`visit_literal_type` 加一条本就为真的提前返回，语义无变化；6 个草稿文件 | 与 noop 逐字相同 |
| Coder a2 | `checkexpr.py` 仅改注释；`subtypes.py` 改动在第 60 次调用回滚；10 个草稿文件 | 同上 |
| Qwen3.6 a1 | 零编辑；清洗后空补丁，按 noop 评分 | 与 noop 相同 |

gold 只在 `subtypes.SubtypeVisitor.visit_instance` 加两行：右侧是 `LiteralType` 且左侧 Instance 带 `last_known_value` 时，改为比较 `last_known_value`。它不改推断，`(False, 5)` 仍是 `bool?`、消息显示 `bool`；Final 变量的 `Tuple[Literal[1]?]` 在子类型层被接受。三条实质候选改的是推断阶段：Final 变量赋值时已定型为 `Tuple[int?]`，返回时不再推断，故 `main:18` 仍错；有了 Literal 上下文，`False` 推断为 `Literal[False]`，消息随之改变。六个负例六条候选全部仍报错。

## 2. 要求能否从公开材料唯一推出

| 行为 | 题面 | 测试要求 | 候选给了什么 |
| --- | --- | --- | --- |
| Union 里含 Literal 元组时，字面量元组返回合法 | MWE + "fails to recognize `(1,)` is a `Tuple[Literal[1]]`" | `main:10/12` 无错 | 3 条实质候选通过，3 条无改动失败 |
| 值 / 类型 / 分支错配仍报错 | 可由 Literal 语义推出 | 六个 E 行 | 6/6 通过 |
| `x: Final = (1,)` 后 `return x` 合法 | 无 | `main:18` 无错 | 0/6。仓库线索反向：`check-literal.test:2690-2694` 把 `force2(b)` 报错写成预期（TODO 注释链接 #7399，沙箱断网） |
| 错配消息保持 `Tuple[bool, int]` | 无 | `main:34/36` 精确文本 | 3 条实质候选给 `Tuple[Literal[False], int]`，与仓库先例一致：有 Literal 上下文时消息显示 Literal（`check-literal.test:1458`、`:1520`） |

结论 **partial**：核心行为可推出；Final 分支是 gold PR 的范围扩展（用例注释同时引用 #7399 与 #11232），措辞是 gold 路线的副产物——任何给推断加 Literal 上下文的路线都必然改变它，仓库约定还指向相反方向。DS a1 写过 "same error, different message maybe. Fine"；Qwen3.6 a2 在第 41 次调用后写出两条路线（改子类型检查 vs 改推断上下文）并选后者。gold 除修复题面现象外，还改变了 Final 元组的子类型关系，同 PR 改写了既有用例（不在执行集）。

## 3. 六次撞回合上限

| 尝试 | 最后一次实质源码编辑（调用序号） | 之后在做什么 | 截断是否因果 |
| --- | --- | --- | --- |
| DS a1（572 s，60 调用） | #31 功能编辑；#56 仅类型注解 | 全量 testcheck × 3（75 s/次）、子集、加测试例、mypy 自检；第 60 次仍是全量 | 否：候选自 #31 未变，只差总结 |
| DS a2（426 s，69 调用） | #25 功能；#66 注解 | 多组反例、全量 `-n0`（92 s）、子集、加测试、自检；第 69 次 `git diff` | 否 |
| Coder a1（168 s） | #60（第 6 次改 `visit_literal_type`） | 每次改完跑同一复现、同样报错 | 未知；错误假设未纠正，无收敛 |
| Coder a2（128 s） | #60（回滚 subtypes 改动） | 建 10 个草稿、只改注释、试 hack 后回滚 | 未知；无收敛 |
| Qwen3.6 a1（178 s） | 无 | 60 次读码 / 复现；thinking 在第 35/43/53 轮后被清空，之后重复同一追踪 | 对空补丁是因果；推理已指向上下文路线，补齐后大概率同样被拒（推断） |
| Qwen3.6 a2（198 s） | #61（删调试打印） | #60 起复现通过，#62–63 复确认，未跑回归 | 对分数否：候选与 DS 同类 |

题目不慢：全量 5334 例 75–92 s，子集 6–14 s，单例 <1 s。DS 是修好后充分验证且不结束会话，弱模型是循环。

## 4. 若按"模型共同失败"看

三条无改动候选的共同点是误读机制：Coder a1 认为左侧 `int` 会进入 `visit_literal_type`（实际 Instance 走 `visit_instance`），反复改无关函数；Coder a2 从未定位到 `last_known_value`；Qwen3.6 a1 定位到但未动手。三条实质候选无共同错误。

P2P=0 对训练信号：奖励只看 1 个用例，其余 5334 例不保护回归；题卡担心的"漏长度检查也能过"今晚未出现，但通过样本可破坏其它行为而不扣分。更直接的问题是 actor 反馈与奖励反向：走 gold 路线会让既有 `testLiteralFinalGoesOnlyOneLevelDown` 失败（静态推断，与测试补丁改写该用例相符），走上下文路线全量通过却得 0。

处置选项（不替用户决定）：
- A：保留原题原测试，标"规范欠说明 + 实现路线绑定"，留诊断旁路，不进比较分母与训练池。
- B：另版本，题面补维护者说明（Final 声明的字面量元组也应被接受；修复放在子类型层，保持既有消息措辞），原版保留；这等于把路线写进题面。
- B′：另版本，F2P 去掉 `does_work` 与 `incorrect_return1`（保留 `incorrect_return2` 与四个负例），两条路线都可通过；偏离 SWE-Gym 官方评分，属评分依据变更。
- C：仅评测不训练，并列报告含 / 不含本题的分母。
- D：淘汰。

原样进训练池最差：全 0 组无梯度；偶发通过的只会是恰好选中 gold 路线的样本，奖励区分的是路线而非能力。

## 5. 环境 / 接口排查

无障碍。`bash_env_v1` 下 `python -m mypy`、`pytest`（pytest.ini `addopts = -nauto`，2 CPU 上 "bringing up nodes" 约 6 s）可用。六条 `is_error` 共 48 次：除 Coder a1 一次 Edit 目标串不存在（该区域已改过）和 Qwen3.6 a1 一次草稿语法错误外，全是 mypy 报出预期诊断的非零退出；DS a2 试 `-p no:xdist` 因 ini 含 `-nauto` 报错后改用 `-n0`。网关 6 个 session 共 361 个响应全 200、无 stream_error；adapter 四条 240 轮 finish_reason 全 `stop`、`raw_output` 与 `parsed` 1:1、上下文峰值 64K（上限 131K）；Qwen3.6 的 prompt token 非单调（a1 3 次、a2 6 次）即已知的 thinking 清空。无 harness 目录访问、联网、pip 或无关工具。评分侧：v1 导出 4 条因基线脏文件 `test-requirements.txt` apply_failed，v2 清洗后应用成功、安装 rc=0、1 例被解析，镜像与 noop/gold 相同。

## 6. 与题卡静态结论是否一致

一致，题卡更准。review.md 明写"上下文方案可能把 incorrect_return1 的 got 由 Tuple[bool,int] 改为 Tuple[Literal[False],int]"和"只做 tuple 上下文拼接也不自动修好先赋值的 Final"，今晚 3/3 应验；card.md 记的"官方 patch 改 `testLiteralFinalGoesOnlyOneLevelDown` 但不在执行集"是关键。题卡说"未证明唯一 gold 或实际误拒"，今晚补上三条与维护者建议同向的候选被拒的实测，"是否误拒"仍是规范裁定。题卡的"唯一优先实验"（MWE 与 `(2,)`/`(1,999)` 负例）未按原样执行；替代证据是三条候选在 actor 里 MWE 复现通过、六条对六个负例仍报错。题卡未预见 6/6 撞回合上限与弱模型 3 条零改动。

## 证据指针表

路径前缀：`M` = `runs/base_probe_20260922/remote/runs/matrix/attempts/python__mypy-11236`，`X` = `runs/base_probe_20260922/remote/runs/x1_controls/python__mypy-11236`，`G` = `runs/base_probe_20260922/remote/gateway`，`CARD` = `docs/.../expansion/batch02/results/python__mypy-11236`，`PUB` = `runs/swegym_quality_batch02_20260921_v2/public/python__mypy-11236`。"调用 #n" 指 `trajectory.jsonl` 里第 n 个 `tool_use`。

| 结论 | 证据 |
| --- | --- |
| 题面只有 MWE，无 Final、无消息措辞要求；六份 prompt md5 相同 | `M/*/*/prompt.txt`:3、14–18、21 |
| F2P 用例 42 行、`main:N` 行号对应；同一补丁改写 `testLiteralFinalGoesOnlyOneLevelDown`；P2P=[] | `docs/.../s2/ingest/grading_bundles_v2_v0.jsonl` 本题行 `test_patch`、`fail_to_pass`、`pass_to_pass`、`eval_cmd` |
| noop 多 main:10/12/18；gold 1 passed | `X/noop/eval_logs/*.eval.log`:568–592；`X/gold/eval_logs/*.eval.log`:576；两份 `ledger.jsonl` 的 `report` |
| DS a1 v2：多 main:18、main:34/36 措辞变 | `M/deepseek-v4-pro/a1/grading_v2/eval_logs/*.eval.log`:631–655 |
| DS a2 v2 同上 | `M/deepseek-v4-pro/a2/grading_v2/eval_logs/*.eval.log`:607–631 |
| Qwen3.6 a2 v2 同上 | `M/qwen3.6-35b-a3b/a2/grading_v2/eval_logs/*.eval.log`:628–652 |
| Coder a1/a2、Qwen3.6 a1（noop）与 noop 逐字相同 | `M/qwen3-coder-30b-a3b-instruct/a1/grading/eval_logs/*.eval.log`:615–639；`.../a2/grading/eval_logs/*.eval.log`:603–627；`M/qwen3.6-35b-a3b/a1/grading_v2/eval_logs/*.eval.log`:568–592 |
| 评分有效：apply rc=0、安装 rc=0、1 例解析、同一派生镜像 | 各 `ledger.jsonl` 的 `candidate`、`install`、`verdict_diagnostics`、`derived_image_recipe`；v1 apply_failed 见 `M/{deepseek-v4-pro,qwen3.6-35b-a3b}/*/grading/ledger.jsonl` |
| 六个候选与清洗记录 | `M/deepseek-v4-pro/*/candidate_v2/*.diff`、`cleaning.json`；`M/qwen3.6-35b-a3b/a2/candidate_v2/*.diff`；`M/qwen3.6-35b-a3b/a1/candidate_v2/empty_graded_as_noop.json`；`M/qwen3-coder-30b-a3b-instruct/*/candidate/*.diff` |
| gold 两行 | `runs/base_probe_20260922/remote/gold/python__mypy-11236.gold.patch` |
| base 的 `visit_instance` 无 Literal 分支；既有用例把 Final 元组不匹配写成预期（TODO + #7399）；有 Literal 上下文时消息显示 Literal | `PUB/base/mypy/subtypes.py`:243–297；`PUB/base/test-data/unit/check-literal.test`:2677–2696、1448–1465、1512–1526 |
| 上游讨论提出 "splicing" 与 "quick-and-dirty (?)" `is_subtype` 两条路线（模型不可见） | `docs/.../s2/raw/swe_gym_lite_full_f70b1a29.jsonl`:201 `hints_text` |
| DS a1 功能编辑、全量 5334/5335 通过、"different message maybe. Fine" | 调用 #30–31、#38、#49、#60；`M/deepseek-v4-pro/a1/transcript.md`:1767、2373、2860、3253 |
| DS a2 功能编辑、全量 5334（-n0 92 s）、发现 `make_simplified_union` 折叠问题 | 调用 #25、#52、#63；`M/deepseek-v4-pro/a2/transcript.md`:1809、2891、3412 |
| Qwen3.6 a2 明确看到两条路线并选上下文；复现在最后通过 | 调用 #41 后 thinking、#60–63；`M/qwen3.6-35b-a3b/a2/transcript.md`:2308、2376、3154、3214、3245 |
| Qwen3.6 a1 零编辑、找到 `last_known_value`、重复推导 | 调用 #57–60；`M/qwen3.6-35b-a3b/a1/transcript.md`:3226；`G/q36_adapter/bp22-qwen3-6-35b-a3b-mypy-11236-a1.turns.jsonl` 第 35/43/53 轮 prompt_tokens 下降 |
| Coder a1 误认 `int` 走 `visit_literal_type`，6 次改同一函数 | 调用 #41、#50、#51、#53、#58、#60；`M/qwen3-coder-30b-a3b-instruct/a1/transcript.md`:2170、2307–2308、2349 |
| Coder a2 注释级改动与回滚 | 调用 #34/#35/#49、#56/#60；`M/qwen3-coder-30b-a3b-instruct/a2/transcript.md`:2333、2533 |
| 终止、回合、耗时、工具错误计数 | `M/*/*/attempt.json` 的 `trajectory_summary.cc_result`、`solve_seconds`、`tool_result_errors` |
| 网关全 200、无 stream_error；adapter 无截断、无丢解析 | `G/{deepseek,coder,q36}/<attempt_id>/responses.jsonl`；`G/{coder_adapter,q36_adapter}/<attempt_id>.turns.jsonl` |
| 题卡预言与范围疑点 | `CARD/review.md`:16、19；`CARD/card.md`:9、16、18；`CARD/public_read.md`:23、56 |
| 运行条件（bash_env_v1、--max-turns 60、harness_out=out_of_tree） | `docs/.../project1_execution/base_model_probe_run_20260922.md` §3、§7.2、§7.5b、§7.6；`M/*/*/attempt.json` 的 `actor_env`、`cc_extra_args`、`deviations` |

```json
{"task": "python__mypy-11236", "verdict": "mixed: task_or_test_dispute (deepseek a1/a2, qwen3.6 a2) + model_failure (coder a1/a2, qwen3.6 a1)", "confidence": "high", "failed_test": "mypy/test/testcheck.py::TypeCheckSuite::testLiteralAndInstanceSubtyping", "requirement_derivable_from_public": "partial", "turn_cap_causal": false, "per_attempt": [{"attempt": "deepseek-v4-pro/a1", "candidate_summary": "checkexpr.visit_tuple_expr：Union 里多个同长元组时按位置 UnionType.make_union 拼推断上下文；另在 check-tuples.test 加 4 例；actor 内全量 testcheck 5334/5335 通过", "failure_reason": "F2P 多出 main:18（Final 元组 return x 仍报错）；main:34/36 的 got 变为 Tuple[Literal[False], int] / Tuple[Literal[True], str]（期望 bool/str）；题面 MWE 与六个负例均正确", "last_substantive_edit_call": 31}, {"attempt": "deepseek-v4-pro/a2", "candidate_summary": "同类：按位置 make_simplified_union 拼上下文（会把 Union[int, Literal[1]] 折叠为 int，模型自己发现但未改）；在官方 check-literal.test 加 1 例（投影忽略）；全量 5334 通过", "failure_reason": "同 a1：main:18 与 main:34/36 措辞", "last_substantive_edit_call": 25}, {"attempt": "qwen3-coder-30b-a3b-instruct/a1", "candidate_summary": "subtypes.py：visit_tuple_type 加空 pass 分支，visit_literal_type 加本就为真的提前返回，语义无变化；6 个草稿文件；未跑 pytest", "failure_reason": "输出与 noop 逐字相同；误认左侧 int 走 visit_literal_type，在无关函数上改了 6 次", "last_substantive_edit_call": 60}, {"attempt": "qwen3-coder-30b-a3b-instruct/a2", "candidate_summary": "checkexpr.py 仅注释改动；subtypes.py 的 hack 在第 60 次调用回滚；10 个草稿文件；未跑 pytest", "failure_reason": "输出与 noop 逐字相同；从未定位 last_known_value，无收敛", "last_substantive_edit_call": 60}, {"attempt": "qwen3.6-35b-a3b/a1", "candidate_summary": "零编辑；60 次读码 / 复现；thinking 三次被清空后重复推导；清洗后空补丁按 noop 评分", "failure_reason": "无补丁；推理已指向上下文路线，补齐后大概率仍被 main:18/34/36 拒绝（推断）", "last_substantive_edit_call": 0}, {"attempt": "qwen3.6-35b-a3b/a2", "candidate_summary": "取 Union 中第一个含 Literal 的元组作上下文，typeops.is_literal_type_like 增加 TupleType 分支；11 个草稿文件；复现在第 60 次调用才通过（#62–63 复确认），未跑回归", "failure_reason": "同 DS：main:18 与 main:34/36 措辞", "last_substantive_edit_call": 61}], "disposition_options": ["A 保留原题原测试，标注规范欠说明 + 实现路线绑定，留诊断旁路，不进模型比较分母与训练池", "B 另版本：题面补充维护者说明（Final 声明的字面量元组也应被接受；修复放在子类型层，保持既有错误消息措辞），原版保留；等于把实现路线写进题面", "B′ 另版本：F2P 去掉 does_work 与 incorrect_return1，保留 incorrect_return2 与四个负例，两条路线都可通过；偏离 SWE-Gym 官方评分，属评分依据变更", "C 仅作评测不作训练，报告并列含与不含本题的分母", "D 淘汰"], "followups": ["在固定 grader 上对 gold 跑 base 版 testLiteralFinalGoesOnlyOneLevelDown，把'走 gold 路线会让既有用例失败'从静态推断变成实测（题卡归属方）", "若选 B′：用 DS a1 候选重放新版 F2P 作对照，确认上下文路线在新版下通过且六个负例仍报错", "把今晚 3 条上下文路线候选的实测回填题卡的'唯一优先实验'与两条静态预言", "P2P=0 的 mypy 题（grading_bundles_v2_v0 里 40 道 mypy 题有 14 道，含本题）在进训练池前统一核对：是否需要补充执行选集或以全量 testcheck 作回归门（评分依据变更，需用户决定）", "Qwen3.6 thinking 周期性清空已在 §7.5 第 11 条登记；本题 a1 的重复推导是其可见后果，回交 A 线时可引用", "弱模型把草稿文件留在仓库根（Coder 6/10 个、Qwen3.6 a2 11 个）被投影带入候选；不影响本题判分，但汇总'候选大小'时要剔除"]}
```
