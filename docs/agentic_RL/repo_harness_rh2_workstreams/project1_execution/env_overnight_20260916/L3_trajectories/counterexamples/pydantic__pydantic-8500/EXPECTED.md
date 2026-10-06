# pydantic__pydantic-8500 · 反例预期与证明力

**疑点（`solvability_review_20260909/01_failure_cases.md` "追加交叉核验"）：** 官方判
`RESOLVED_FULL`（F2P 1/1、P2P 44/44），但题面给的那个最小例子在候选上仍然输出 `{'b','a'}`。
审查同时指出：候选最终的生产改动与 **gold 完全相同**（逐行对比见下），所以这不是候选的缺陷，
而是**题面要求与官方验收面不是同一件事**。本反例把这一点变成一次可复核的运行结果。

同时，本题是"上游修复曝光"的样本：轨迹 `stream.jsonl:13119-13126` 下载 pydantic 2.6.0 wheel 读到
已修 `model_construct`，`:13636-13645` 下载 sdist 读到官方新增测试，`:19077-19078` 直接取 PR 8500 diff。
反例脚本本身不评价这件事，只记事实（在 `trajectory_facts.json` 里）。

## 输入

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-8500:latest` |
| workdir | `/testbed`，base_commit `069d0205424f98912f8b670b1bc5cfc7df37b2f3` |
| 候选（仅生产代码） | `patches/pydantic__pydantic-8500.candidate.src_only.diff`（只含 `pydantic/main.py`） |
| gold | `patches/pydantic__pydantic-8500.gold.diff`（同样只含 `pydantic/main.py`） |
| 官方 test_patch | `patches/pydantic__pydantic-8500.test_patch.diff` |
| 官方 F2P | `tests/test_construction.py::test_retain_order_of_fields`（1 条） |
| 官方 P2P | 44 条，全在 `tests/test_construction.py` |

**先做一次零成本核对：** `diff patches/pydantic__pydantic-8500.candidate.src_only.diff patches/pydantic__pydantic-8500.gold.diff`
应该只在 diff 头（`index` 行、hunk 上下文里的函数名标注）上有差别，改动本体一致。
如果确实一致，那么下表里 gold 与 candidate 两列**必须完全相同**；若实测不同，说明补丁应用
或环境有问题，整张表作废（记 `unknown`）。

## 逐条预期

| 用例 | base | gold | candidate | 差异说明什么 |
| --- | --- | --- | --- | --- |
| `test_problem_statement_example_dump_order` | FAIL | **FAIL** | **FAIL** | 题面原例三态都没修好 → 官方 F2P 覆盖的不是题面问题 |
| `test_problem_statement_example_json_order` | FAIL | FAIL | FAIL | 同上，排除 dump / dump_json 走不同路径 |
| `test_problem_statement_example_intermediate_state` | PASS | PASS | PASS | 把"缺失必填字段不进 `__dict__`"固化为可见输出；这是原例修不好的机制原因 |
| `test_official_scenario_retain_order_of_fields` | FAIL | PASS | PASS | 官方 F2P 的同款断言 |
| `test_official_scenario_with_default_factory` | FAIL | PASS | PASS | 修复对 `default_factory` 同样生效（官方没测） |
| `test_official_scenario_with_alias` | FAIL | PASS | PASS | 修复对 alias 字段同样生效（官方没测） |
| `test_model_construct_still_allows_missing_required_field` | PASS | PASS | PASS | 护栏：不得靠塞占位字段"修"顺序 |
| `test_model_fields_set_excludes_defaults` | PASS | PASS | PASS | 护栏：`model_fields_set` 语义不变 |
| `test_model_fields_set_respects_explicit_argument` | PASS | PASS | PASS | 护栏 |
| `test_model_fields_set_with_alias` | PASS | PASS | PASS | 护栏 |

| run | base | gold | candidate |
| --- | --- | --- | --- |
| `base_construction_tests`（`tests/test_construction.py`，未打 test_patch） | 全绿 | 全绿 | 全绿 |
| `official_f2p` | FAIL | PASS | PASS |
| `official_full_file` | 1 failed | 全绿（45） | 全绿（45） |

## 这证明什么 / 不证明什么

**能证明（如果结果如表）：**
1. 题面描述的缺陷（construct 后再赋值的顺序）在 gold 上也没有被修复 → 这道题的 reward
   信号奖励的是"官方换过场景的那个用例"，不是题面写的问题。对后训练来说，这类题会
   教模型"对齐官方用例"而不是"对齐题面"，而模型在训练时**看不到**官方用例。
2. `default_factory` 与 alias 两条说明真实修复面比官方 F2P 宽；官方只测了一个点。
3. 护栏四条三态全绿 → 排除"靠塞占位字段把顺序做出来"这种会被官方用例接受的坏解法
   （当前 gold/candidate 都没这么干，但这四条应进回归集，防止后续改动走这条路）。

**不能证明：**
- 不能证明官方用例"错了"。维护者修的是 `model_construct` 的构造顺序，这本身是真实缺陷。
  问题在于 **题面文本与验收面之间的落差没有被标注出来**。
- 不能证明候选独立解出本题。轨迹在定稿前已接触发布版实现与官方测试（见上文行号），
  这一点由 `trajectory_facts.json` 的 `self_distribution_download_commands` /
  `upstream_urls_in_commands` 记录，不由本脚本判定。
- `test_model_construct_still_allows_missing_required_field` 里的 `pytest.raises(AttributeError)`
  依赖该版本 `BaseModel.__getattr__` 的行为。若三态**同时**失败，那是环境事实，不是反例信号，
  按 `unknown` 记并改成只断言 `'a' not in m.__dict__`。

## 落到筛查记录的字段

- `issues[]`：`{category: "problem_statement_vs_oracle_mismatch", severity: "P1", note: "题面原例在 gold 上也不通过；F2P 验收的是另一个场景", proposed_action: "本题的 public_view 里显式标注'验收面只覆盖 construct 期顺序，不含构造后赋值'，或在数据层把此类题标为 spec_gap", next_experiment: "本 run_matrix.sh"}`
- `issues[]`：`{category: "answer_exposure", severity: "P2", note: "轨迹在定稿前下载了发布版源码与 PR diff", evidence_refs: ["trajectory_facts.json#tasks.pydantic__pydantic-8500.self_distribution_download_commands"], proposed_action: "见 L3_report.md §网络通道"}`
- `proposed_regression_tests[]`：`test_official_scenario_with_default_factory`、`..._with_alias` 与四条护栏。
