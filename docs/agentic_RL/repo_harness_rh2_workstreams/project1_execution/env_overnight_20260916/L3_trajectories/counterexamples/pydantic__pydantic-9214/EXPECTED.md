# pydantic__pydantic-9214 · 反例预期与证明力

**疑点（`solvability_review_20260909/01_failure_cases.md` §3）：** 题面原例（RootModel +
`Field(description='abc')`）在候选上**已经修好**，官方 F2P 也通过；失分来自另一条 P2P——
docstring 与 Field description 同时存在且不同时，谁优先。题面里两处描述恰好都是 'abc'，
无法消歧；能消歧的维护者说明只在**未曝光的 `hints_text`** 里。

## 输入

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9214:latest` |
| workdir | `/testbed`，base_commit `7af856a1098406aea84bcadfd0f3de6b7901526c` |
| 候选（仅生产代码） | `patches/pydantic__pydantic-9214.candidate.src_only.diff`（只含 `pydantic/json_schema.py`） |
| gold | `patches/pydantic__pydantic-9214.gold.diff`（改的是 `pydantic/_internal/_generate_schema.py`） |
| 官方 test_patch | `patches/pydantic__pydantic-9214.test_patch.diff` |
| 官方 F2P | `tests/test_root_model.py::test_model_with_field_description`（1 条） |
| 官方 P2P | 54 条，含 `tests/test_root_model.py::test_model_with_both_docstring_and_field_description` ← 候选在这条上失分 |
| 关键缺失信息 | `hints_text`（`s2/raw/swe_gym_lite_full_f70b1a29.jsonl:190`）："为了向后兼容，两者同时存在时用 docstring" |

注意候选 `candidate.diff` 里还有 `pdm.lock` / `pyproject.toml`，**不是模型乱改**：
轨迹起始的 `git status`（`stream.jsonl:48`）就已经报告这两个文件有改动。`src_only` 版本已滤掉。

## 逐条预期

### 四格矩阵

| 用例 | base | gold | candidate | 说明 |
| --- | --- | --- | --- | --- |
| `test_matrix_1_no_description_at_all` | PASS | PASS | PASS | 对照：不凭空加 description |
| `test_matrix_2_only_field_description` | **FAIL** | PASS | PASS | 题面目标 = 官方 F2P；候选确实修好了 |
| `test_matrix_3_only_docstring` | PASS | PASS | PASS | 既有 workaround 行为不变 |
| `test_matrix_4_both_present_and_different__docstring_wins` | PASS | PASS | **FAIL** | 分歧点：候选让 Field 覆盖了 docstring |
| `test_matrix_4b_both_present__which_source_wins` | PASS（打印 `DOCSTRING_SOURCE`） | PASS（`DOCSTRING_SOURCE`） | PASS（打印 `FIELD_SOURCE`） | 不预设答案，只把"谁赢"写进日志；三态都 PASS 说明分歧是**选择**而非崩坏 |

第 4 格与第 4b 格要一起读：4b 三态全 PASS 证明候选没有产生非法输出，
分歧纯粹是两种都说得通的优先级选择；4 则说明这个选择改变了 base 已有的输出。

### 护栏

| 用例 | base | gold | candidate | 说明 |
| --- | --- | --- | --- | --- |
| `test_guard_plain_basemodel_docstring_unaffected` | PASS | PASS | PASS | 普通模型不受影响 |
| `test_guard_plain_basemodel_field_description_stays_on_property` | PASS | PASS | PASS | 属性级描述不得被提升到 model 级 |
| `test_guard_nested_root_model_description_lands_on_definition` | **FAIL** | PASS | **需实测** | 两种实现走的是不同路径（`modify_model_json_schema` vs `_update_class_schema` 的 `$ref` 解析）；这条把嵌套场景固定下来 |
| `test_guard_root_field_json_schema_extra_still_applies` | PASS | PASS | PASS | 候选改写了这段分支，确认没改坏 |
| `test_guard_both_json_schema_extra_sources_still_raise` | PASS | PASS | PASS | 同上 |
| `test_guard_json_schema_extra_can_still_override_description` | PASS | PASS | PASS | 界定插入位置：description 必须写在 `json_schema_extra` 的 `.update()` 之前 |

### 官方面

| run | base | gold | candidate |
| --- | --- | --- | --- |
| `official_f2p` | FAIL | PASS | **PASS** |
| `official_p2p_both` | PASS | PASS | **FAIL** |
| `official_full_file`（`tests/test_root_model.py`，56 条） | 1 failed | 全绿 | 1 failed |
| `base_root_model_tests`（未打 test_patch，54 条） | 全绿 | 全绿 | **全绿**（预期）——说明 base 自带测试抓不到这个优先级变化，抓到它的是官方**新增**的那条 |

`base_root_model_tests` 这一格很关键：如果它在 candidate 上也全绿，就说明
"docstring 优先"这条既有行为在 base 的测试里**没有被固定**，官方是靠新增 test_patch
才把它变成 P2P。这决定了该把本题算作"合理的兼容性要求"还是"事后追加的要求"。

## 这证明什么 / 不证明什么

**能证明（如果结果如表）：**
1. 候选解决了题面写的问题（矩阵第 2 格），却因为一条题面无法推出的优先级被判 `RESOLVED_NO`。
   这类题在 RL 里给的是"做对了主目标仍然 0 分"的信号。
2. 分歧是**选择**不是**崩坏**：4b 三态全 PASS，六条护栏三态全 PASS。
   所以不能用"候选实现有 bug"来解释失分。
3. `base_root_model_tests` 的结果直接回答"这条要求是不是事后追加的"。

**不能证明：**
- 不能证明"docstring 优先"不合理。向后兼容是真实约束，gold 的选择有依据；
  本反例只证明**依据没有出现在 agent 能看到的材料里**。
- 不能证明补上 `hints_text` 候选就会选对。
- `test_guard_nested_root_model_description_lands_on_definition` 在 candidate 上的结果
  写的是"需实测"，没有预判；实测前记 `not_checked`，不要按猜测写。

## 落到筛查记录的字段

- `issues[]`：`{category: "spec_ambiguity_prompt_gap", severity: "P2", note: "优先级判据只在未曝光的 hints_text 里；题面两处描述同为 'abc' 无法消歧", evidence_refs: ["s2/raw/swe_gym_lite_full_f70b1a29.jsonl:190"], proposed_action: "把'两者同时存在时以 docstring 为准'写进 public_view，或把本题标为 spec_gap", next_experiment: "本 run_matrix.sh"}`
- `issues[]`：`{category: "budget_truncation", severity: "P3", note: "error_max_turns，首个 Edit 在第 50 个工具调用，末尾三次缺依赖后即到上限", evidence_refs: ["trajectory_facts.json#tasks.pydantic__pydantic-9214.result", "…package_install_commands"]}`
- `proposed_regression_tests[]`：四格矩阵 + 六条护栏。
- `file_rules.additional_exclusions`：**不新增**；`pdm.lock`/`pyproject.toml` 是镜像出厂就有的改动（`stream.jsonl:48`），属于补丁提取口径问题。

## 执行注意

- 需要 `pytest`（轨迹末尾显示本镜像默认没有 pytest / pytest-benchmark / dirty-equals）。
  若 `tests/test_root_model.py` 因缺 `dirty_equals` 收集失败，**只跑 `diagnostic` 这一项**
  （它只 import pydantic 本体），其余记 `unknown`，不要在容器里装依赖。
- 三态之间的复位只作用于容器内一次性的 `/testbed`。
