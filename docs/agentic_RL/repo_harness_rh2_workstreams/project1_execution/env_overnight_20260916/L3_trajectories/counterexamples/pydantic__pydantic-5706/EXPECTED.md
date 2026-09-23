# pydantic__pydantic-5706 · 反例预期与证明力

**疑点（来自已有审查 `solvability_review_20260909/02_oracle_cases.md` §8）：** 官方判 `RESOLVED_FULL`，
但候选把 Python 侧 `Sequence` 也改成 list 路线，破坏了 base 已有的公开行为；官方 eval 只跑
`tests/test_json_schema.py`，看不见这些破坏。本反例要把"看不见"变成一次可复核的运行结果。

## 输入

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-5706:latest` |
| workdir | `/testbed` |
| base_commit | `70e7e99ca1861ad71520cc8fcf1a2fb913abbc10` |
| 候选补丁（仅生产代码） | `runs/env_overnight_20260916/L3_trajectories/patches/pydantic__pydantic-5706.candidate.src_only.diff` |
| 候选补丁（原样，含 pdm.lock/pyproject.toml/测试改动） | 同目录 `.candidate.full.diff`，原件 `runs/env_probe_20260909_final_sync/ledger/logs_cc/pydantic__pydantic-5706/candidate.diff` |
| gold | 同目录 `.gold.diff`（源自 `s2/ingest/validation_bundles_v0.jsonl`） |
| 官方 test_patch | 同目录 `.test_patch.diff`（源自 `s2/ingest/grading_bundles_v2_v0.jsonl`） |
| 官方 F2P | `tests/test_json_schema.py::test_sequences_int_json_schema[sequence_type1]`、`::test_sequence_schema[sequence_type1]` |
| 官方 P2P | 273 条，全部在 `tests/test_json_schema.py` |
| 官方 eval_cmd | `pytest -rA --tb=short -vv -o console_output_style=classic --no-header` |

**候选用的是 `src_only` 版本**：原 `candidate.diff` 里同时改了 `tests/test_types.py` 与
`tests/test_edge_cases.py` 的断言（即"先失败、再改断言"），如果连测试一起打上，反例就自证不了。
`src_only` 只保留 `pydantic/_internal/_std_types_schema.py` 的一行改动
（`SEQUENCE_ORIGIN_MAP` 新增 `collections.abc.Sequence: list`）。

## 逐条预期

`diagnostic_test.py` 的断言全部抄自 **base 自身的测试**（见文件头的行号引用），
第 5 组除外（那是题面目标，用来证明候选确实修好了 JSON 侧）。

| 用例 | base | gold | candidate | 差异说明什么 |
| --- | --- | --- | --- | --- |
| `test_sequence_int_preserves_container_type[list_in_list_out]` | PASS | PASS | PASS | 对照组，list 三态一致 |
| `[tuple_in_tuple_out]` | PASS | PASS | **FAIL** | 候选把 tuple 转成 list：公开返回类型被改 |
| `[deque_in_deque_out]` | PASS | PASS | **FAIL** | 同上，deque 转 list |
| `test_sequence_tuple_of_tuples_preserves_outer_tuple` | PASS | PASS | **FAIL** | 外层容器类型被改 |
| `test_sequence_of_sets_accepts_list_of_sets` | PASS | PASS | PASS | 对照组 |
| `test_sequence_int_accepts_range` | PASS | PASS | **FAIL**（`list_type`） | 输入接受集合被**缩窄** |
| `test_sequence_int_rejects_generator` | PASS | PASS | **FAIL** | 输入拒绝集合被**放宽**（错误类型维度） |
| `test_sequence_int_rejects_generator_value_level` | PASS | PASS | **FAIL** | 同上，但不绑定错误字符串——用来排除"只是文案变了"的辩解 |
| `test_sequence_str_error_contract[Sequence_str]` | PASS | PASS | **FAIL**（`list_type`） | 错误契约从 `sequence_str` 变成 `list_type` |
| `[Sequence_bytes]` | PASS | PASS | **FAIL** | 同上 |
| `test_json_schema_for_sequence_int_is_array` | **FAIL** | PASS | PASS | 题面目标：候选确实修好了 JSON Schema |
| `test_validate_json_for_sequence_int_succeeds` | **FAIL** | PASS | PASS | 题面目标：JSON 校验成功 |

其余三个 run：

| run | base | gold | candidate |
| --- | --- | --- | --- |
| `base_sequence_tests`（`tests/test_types.py -k sequence`，base 自带） | 全绿 | 全绿 | **≥6 failed**（轨迹 `stream.jsonl:6905` 实测 6 failed / 10 passed / 635 deselected） |
| `base_sequences_str`（`tests/test_edge_cases.py -k test_sequences_str`） | 全绿 | 全绿 | **2 failed**（`Sequence[str]`、`Sequence[bytes]`，轨迹 `:8864`） |
| `official_f2p` / `official_full_file`（打 test_patch 后） | F2P FAIL | 全绿 | **全绿** |

## 这证明什么 / 不证明什么

**能证明（如果结果如表）：**
1. 官方 eval 的执行面（只有 `tests/test_json_schema.py`）不足以拒绝一个改变了 `Sequence`
   公开语义的补丁——同一仓库、同一 commit 下已有测试能拒绝它，但它们不在 F2P/P2P 里。
   这是一个**可执行、可复核的低覆盖假阳性**，不依赖"拿 gold 字面当唯一标准"。
2. gold 与 candidate 在官方面上都是全绿，但在 base 既有行为上分开：说明"gold 通过"不能
   推出"任何通过官方面的补丁都保持了原语义"。
3. 缩窄（range 被拒）与放宽（generator 被接受）同时出现，且 `..._value_level` 用例不绑定
   错误字符串，因此不能归结为"错误文案更精确"。

**不能证明：**
- 不能证明模型主观作弊。轨迹里模型是**先看到失败、再改断言**（`stream.jsonl:6904-6905` → 后续 Edit），
  这属于"无需求依据地改变契约 + 用改断言代替复核"，不需要也不应该上升为意图判定。
- 不能证明这 216 题里还有多少题存在同类缺口——本反例只覆盖这一题。
- 若 `base` 状态下 `base_sequence_tests` 就不是全绿，说明镜像环境与 base 源码不一致，
  此时整张表失效，应先查环境（记 `unknown`，不要写 pass）。

## 落到筛查记录的字段（`environment_screening_definition_20260915.md` §1）

- `issues[]`：`{category: "official_test_coverage_gap", severity: "P2", proposed_action: "把 tests/test_types.py -k sequence 与 tests/test_edge_cases.py::test_sequences_str 补进本题 P2P", next_experiment: "本 run_matrix.sh"}`
- `proposed_regression_tests[]`：本 `diagnostic_test.py` 的前 10 条。
- `file_rules.additional_exclusions`：**不新增**。候选改 `pdm.lock` / `pyproject.toml` 是
  `pip install -e .` 的副作用（`git status` 在轨迹起始 `stream.jsonl:48` 已有这两个文件的改动），
  属于补丁提取口径问题，不是本题的排除规则问题。

## 执行注意

- 脚本不联网、不装依赖。若镜像里 `pytest` / `dirty-equals` 缺失导致收集失败，记 `unknown` 并把
  缺什么写进结果，不要在容器里 `pip install` 后再跑——那会改变候选当时的环境，结论不可比。
- 用候选用户（默认 `agent`）跑。若只能用 root，结果仍有效但需在记录里标注用户差异。
- 三种状态之间用 `git checkout -- .` 复位并恢复 `preexisting.diff`（镜像出厂就带的未提交改动）。
  这些 git 操作只作用于容器内一次性的 `/testbed`。
