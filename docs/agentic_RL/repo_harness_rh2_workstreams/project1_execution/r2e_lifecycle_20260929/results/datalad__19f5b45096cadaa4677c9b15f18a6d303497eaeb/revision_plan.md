# datalad `19f5b450` 修订方案（R-c：exit 5、输入缺失、ignore 模式）

2026-09-29 · 修订执行者（Claude，单题闭环试行）。规则：[统一标准 v1](../../../task_screening_standard_v1_20260925.md) §4 第 2、4 步，§5 R-c 与验收；本批 [README §3](../../README.md)。本文只是修订草案与试跑记录，**不是正式修订单**；试跑不是正式评分（工具差别见 `rh2/experiments/r2e_lifecycle_20260929/trial_grade.py` 文件头）。

路径缩写（均相对仓库根）：

- `PUB/` = `runs/r2e_static_prep_20260924/v3/public/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/`，`W/` = `PUB/worktree/`
- `PRIV/` = `runs/r2e_static_prep_20260924/v3/private/datalad__19f5b45096cadaa4677c9b15f18a6d303497eaeb/`
- `CANDS/` = `runs/r2e_actor_20260925/grader_cands/`，`LEDG/` = `runs/r2e_actor_20260925/grader/`
- `B2/` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_review_batch2_20260925/`
- `CX2` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_batch2_review_20260925/README.md`

## 0. 结论

- **模板 R-c**，一处修订：在隐藏测试 `test_1.py` 中新增 3 个测试函数（每个只断言进程退出码）；期望映射**新增 3 键、均为 PASSED**，原 19 键不变、无删除。原目标测试 `test_run_exit_code` 一字不改。
- **旧修订情况**：本题 `PRIV/revisions.json` 为 `[]`，`docs/.../s2_r2e/revisions/material_revisions_v3.json` 也没有本题条目。任务说明里"本包两道题都已有已批准的材料修订"对本题不成立；因此 `test_1.py` 与期望映射都是**首次修订**，不存在与旧修订合并的问题。
- **试跑**：见 §5。修订草案 v1 下 gold 与合理替代解 K1 为 1；noop、K4 为 0；三个触发候选 K2、K3、H 由原来的 1 变为 0，各自只在预期的新键上失败。
- **状态**：修订草案已试跑通过，待 Codex 复核；正式修订单、材料摘要、派生镜像材料步骤与正式评分由协调者落。

## 1. 要纠正的 S1 与触发候选

唯一目标键 `test_run_exit_code`（`PRIV/hidden_tests/test_1.py:214-223`）只测题面原例 `run --explicit 'exit 3'` 退出 3。第二批正式评分（`LEDG/ledger_d19f5_*.jsonl`，派生镜像 `sha256:851a10b63cec…`，配方 `r2e_derive_v1`，当前材料）中，三个错误候选都得 1：

| 缺口 | v1 §4 | 触发候选（补丁 sha256 前 8 位） | 原版正式评分 | 违反的公开要求（公开侧对照 `B2/grader_candidates.md:172-182`） |
| --- | --- | --- | --- | --- |
| G1 只测示例字面值（退出码 3、`--explicit` 形态） | 第 2 步，T2c | H：`CANDS/datalad_19f5_H_hardcode_exit_3.patch`（`f84d6fdd`），分支里写死 `exit_code = 3` | 1（19/19） | 任意 N 应转发；H 对任何失败都退 3，输入缺失也退 3 |
| G2 非命令失败的退出码无断言 | 第 4 步 | K3：`CANDS/datalad_19f5_K3_first_failed_exit_code_no_fallback.patch`（`b3d00aab`），取首条失败记录的 `exit_code`，缺字段不回退 | 1（19/19） | 输入缺失时 `sys.exit(None)`，进程以 **0** 退出，把失败报成成功 |
| G3 `--on-failure ignore` 的退出码无断言 | 第 4 步 | K2：`CANDS/datalad_19f5_K2_propagate_command_error.patch`（`18d8b1fc`），删掉 `run.py::_execute_command` 的 `try/except`，让 `CommandError` 直接上抛 | 1（19/19） | ignore 模式仍退 3；公开侧另见 `test_run.py::test_basics`、`test_rerun.py::test_run_failure` 失败（Python API 改变） |

这三项正是 v1 §11 为本题列的 "exit 5、输入缺失、ignore 模式"，也是 Codex 第二批复核 `CX2:86` 接受的最小补测范围。

## 2. 公开依据（逐项）

**G1 → 新键 `test_run_exit_code_other_value`：`run 'exit 5'` 应退出 5。**

- 题面 `PUB/user_prompt.txt:7`："When executing the `datalad run` command with a task that is expected to fail with a specific non-zero exit code, the command does not exit with the intended code."；`:22`："should exit with the same non-zero exit code (e.g., `3`) that the underlying command returns"。3 是 "e.g." 给出的示例值，要求是"与底层命令相同的退出码"。
- 设计文档 `W/docs/source/design/cli.rst:65-71`：第 3 类错误 "exit code relayed from underlying command … the exit code of the DataLad process matches the exit code of the underlying command"，不区分是否 `--explicit`。
- 不带 `--explicit`：题面第 7 行泛指 `datalad run`；v1 §4 第 2 步把"同一个输入形态"列为示例拟合的一种，所以非示例实例同时换退出码和调用形态。已有公开侧对照：gold 下 `run 'exit 3'` 退 3（`B2/grader_candidates.md:176`）。

**G2 → 新键 `test_run_missing_input_exit_code`：`run --explicit -i does-not-exist 'exit 3'` 应退出 1。**

- `W/docs/source/design/cli.rst:61-63`："2. Incomplete results (exit code 1) — While processing an error occurred."
- `W/datalad/core/local/run.py:105-109`（`Run` docstring）："A command execution will not be attempted, by default, when an error occurred during input or output preparation."——命令根本没执行，不存在可转发的底层退出码；`run.py:490-496` 对缺失输入产出 `status="error"`、不带 `exit_code` 的记录。
- `W/datalad/cli/main.py:200-201`：失败时退出码起始值为 1；`W/CHANGELOG.md:1191`："`run` continues to exit with a non-zero exit code in case of an error"。
- 这是 base 已有、题面没有要求改变的行为：base 与 gold、K1 在公开侧对照中都退 1（`B2/grader_candidates.md:176-177`）。

**G3 → 新键 `test_run_on_failure_ignore_exit_code`：`--on-failure ignore run --explicit 'exit 3'` 应退出 0。**

- `W/datalad/cli/common_args.py:95-99`（`--on-failure` 帮助）："'ignore' and continue with remaining operations, the error is logged but does not lead to a non-zero exit code of the command"。
- `W/docs/source/design/result_records.rst:80-86`：失败结果"can lead to an `IncompleteResultsError` being raised on command exit, or a non-zero exit code on the command line"，而 "with `on_failure='ignore'` the command will not error even when failures occurred"。
- base、gold、K1 在公开侧对照中都退 0（`B2/grader_candidates.md:176-177`）。

**保留的有依据要求**：原目标测试（含 `run_main` 默认 `expect_stderr=False` 的 Python 层 stderr 为空约束）不改，K4 仍为 0。

## 3. 具体改动

**放进哪个文件**：`PRIV/hidden_tests/test_1.py`。锚点 `# https://github.com/datalad/datalad/issues/6814\n`（原文件第 226 行，全文恰好出现一次），在它之前插入下面三个函数；即紧跟在 `test_run_exit_code` 之后。修订条目见 `revision_draft.json` 的 `revisions`（`hidden_test_text_replace`，`target: test_1.py`），与试跑用的 `trials/draft_edits_v1.json` 逐字相同。

```python
# R2E material revision (R-c): the exit-code relay must hold beyond the
# example literal (another code, plain call without --explicit), and the
# documented exit codes of non-command failures and of '--on-failure ignore'
# must be preserved. Only the exit code is asserted in these three tests.
@with_tempfile(mkdir=True)
def test_run_exit_code_other_value(tempdir=None):
    create(dataset=tempdir, annex=False)
    with chpwd(tempdir):
        run_main(['run', 'exit 5'], exit_code=5, expect_stderr=True)


@with_tempfile(mkdir=True)
def test_run_missing_input_exit_code(tempdir=None):
    # input preparation fails, the command is never executed:
    # "Incomplete results (exit code 1)"
    create(dataset=tempdir, annex=False)
    with chpwd(tempdir):
        run_main(['run', '--explicit', '-i', 'does-not-exist', 'exit 3'],
                 exit_code=1, expect_stderr=True)


@with_tempfile(mkdir=True)
def test_run_on_failure_ignore_exit_code(tempdir=None):
    # 'ignore': the error is logged but does not lead to a non-zero exit code
    create(dataset=tempdir, annex=False)
    with chpwd(tempdir):
        run_main(['--on-failure', 'ignore', 'run', '--explicit', 'exit 3'],
                 exit_code=0, expect_stderr=True)
```

设计取舍：

1. **三个独立函数、各用新数据集**：每个窄问题一个键，失败时直接看出是哪条要求；互不依赖数据集状态。
2. **`expect_stderr=True`（只断言退出码）**：这三处的窄问题都是退出码。原测试的"Python 层 `sys.stderr` 为空"约束，公开信号两边都有（第二批独立复核 `B2/results/datalad__…/review.md` §3.1：题面示例的 `run_main` 默认值支持它，`cli.rst:68-71` 与 `_communicate_commanderror` 的"像直接执行一样报告错误"指向另一边）。新测试不把这条有争议的约束扩到新路径（例如在输入缺失时多打一行说明的候选不应因此新增判 0）。原测试保持原样，所以对题面原例这条约束照旧有效。
   - 草案 v0 曾用默认 `expect_stderr=False`（`trials/draft_edits_v0.json`）；v0 下 gold 22/22、noop 只错两键（`trials/v0_draft_gold.json`、`v0_draft_noop.json`），说明 gold 在三条新路径上 Python 层 stderr 本来就是空的。定稿改为 v1 只是收窄断言范围，不影响任何已知候选的判定。
3. **用 `run_main`**：与原目标测试和题面示例同一个进程内入口；`--on-failure` 作全局选项放在 `run` 之前，与公开读者命令 C1（`B2/results/datalad__…/public_read.md:154-160`）和第二批公开侧对照一致。
4. **没有加**：Python API 仍抛 `IncompleteResultsError` 的断言（主审曾列为第 4 类，可选）。K2 已被 ignore 键挡住；加它要引入 `test_run.py` 用例与 git-annex 依赖、增加键数，不是 v1 §11 所列范围。

## 4. 期望映射的逐键变化

| 键 | 修订前 | 修订后 |
| --- | --- | --- |
| `test_run_exit_code_other_value` | （无） | PASSED（新增） |
| `test_run_missing_input_exit_code` | （无） | PASSED（新增） |
| `test_run_on_failure_ignore_exit_code` | （无） | PASSED（新增） |
| 其余 19 键 | PASSED | 不变 |

- 父版本：`PRIV/hidden_tests/test_1.py` sha256 `b2c90c1b48789330875141a734bd619f502a9649e86155472285ec7934bb084f`；`PRIV/expected_output.json` sha256 `42b8016a185a44e753aab46db7f2fc96d81f110605eb0bd3cb8172baa1079a77`；无材料修订。
- 修订后：`test_1.py` sha256 `6f1d831dea1f254513c6f0cc4f2efdc45883af7cb14742708b325363b58b2f61`（469 行）；完整期望映射见 `revision_draft.json` 的 `expected_after`，文件 `trials/expected_after.json` sha256 `ae8aef576a096376f277978fb1b4d9771fe99a1b0f675b0e6f1858796a9603e3`（22 键）。
- 新期望的来源是 §2 的公开行为，不是复制 gold 输出；键名来自新测试函数名，不带参数，不与已有键撞名。

## 5. 验收计划与试跑结果

正对照用 gold（`PRIV/gold.patch`，sha256 `adfb3a3b…`），它满足全部新断言，不需要替代正对照。试跑机为本批 R2E CPU 机，派生镜像 `sha256:77f982d03e3a7149d468a5da410984d0f4594159560106feaa8cf6f3e9c30a7f`，配方 `r2e_derive_v1+sysconfig_v1`；每个候选跑 1 次。

**环境确认（当前材料，`--expected current`）**：noop 为 mismatch，只错 `test_run_exit_code`（`assert 1 == 3`），`trials/base_noop_current.json`；gold 为 match 19/19，`trials/base_gold_current.json`。与第二批正式评分和 09-23/24 的 noop/gold 结论一致。

**修订草案 v1 下**（`--edits trials/draft_edits_v1.json --expected trials/expected_after.json`）：

| 候选（补丁） | 原版 | 修订后预期 | 修订后试跑 | 失败键与失败信息（试跑的 short test summary） |
| --- | --- | --- | --- | --- |
| gold（`PRIV/gold.patch`） | 1（正式 19/19；本机试跑 match） | 1 | **match 22/22**（`trials/rev_gold.json`） | — |
| noop | 0（本机试跑：只错原目标键） | 0 | **mismatch**（`trials/rev_noop.json`） | `test_run_exit_code`（`assert 1 == 3`）、`test_run_exit_code_other_value`（`assert 1 == 5`）；输入缺失、ignore 两键 PASSED（base 本来就退 1、0） |
| K1（`CANDS/datalad_19f5_K1_communicate_first_run_error.patch`） | 1（正式 19/19） | 1 | **match 22/22**（`trials/rev_K1.json`） | — |
| K2（`CANDS/datalad_19f5_K2_propagate_command_error.patch`） | 1（正式 19/19） | 0 | **mismatch**（`trials/rev_K2.json`） | 仅 `test_run_on_failure_ignore_exit_code`（`assert 3 == 0`） |
| K3（`CANDS/datalad_19f5_K3_first_failed_exit_code_no_fallback.patch`） | 1（正式 19/19） | 0 | **mismatch**（`trials/rev_K3.json`） | 仅 `test_run_missing_input_exit_code`（`assert None == 1`） |
| H（`CANDS/datalad_19f5_H_hardcode_exit_3.patch`） | 1（正式 19/19） | 0 | **mismatch**（`trials/rev_H.json`） | `test_run_exit_code_other_value`（`assert 3 == 5`）、`test_run_missing_input_exit_code`（`assert 3 == 1`） |
| K4（`CANDS/datalad_19f5_K4_gold_plus_stderr_print.patch`） | 0（正式 18/19） | 0 | **mismatch**（`trials/rev_K4.json`） | 仅 `test_run_exit_code`（Python 层 stderr 非空，`assert 'data…' == ''`），与原版相同 |

每次试跑都观测到 22 键、无缺键与多余键，修订草案已应用（`RH2_TRIAL_EDITS_APPLIED=1`），补丁都干净应用（`RH2_APPLY_RC=0`）；每个候选只在上表列出的键上失败，与预期逐键一致。

"原版"一列：gold、K1–K4、H 取第二批正式评分账本（`LEDG/ledger_d19f5_{gold,K1_…,K2_…,K3_…,K4_…,H_…}.jsonl`，镜像 `851a10b6…`，与今晚镜像同为当前材料；两者只差 `+sysconfig_v1` 这一编译配置步骤，与本题纯 Python 行为无关，今晚环境确认的 noop/gold 结果与旧账本一致）。

**验收要点（v1 §5）**：

1. 正对照为 1、noop 为 0：见上表。
2. 本次要纠正的误判已纠正：G1/G2/G3 的触发候选 H、K3、K2 由 1 变 0，且只在对应新键上失败。
3. 已知相关错误候选仍为 0：K4 仍只错原目标键（stderr 约束），没有因新测试多错或少错。
4. 修订后仍受保护的公开要求：题面原例（原目标键，含 Python 层 stderr 约束）；任意非零码转发与非 `--explicit` 调用（新键 1）；非命令失败退 1（新键 2）；ignore 模式退 0（新键 3）；其余 18 个 CLI 回归键。
5. 合理替代解 K1（只处理 `action == 'run'` 的 `CommandError`，并经 fd 2 报告）仍为 1，说明新断言没有新增误拒。

## 6. 边界与未做

- 没有改 gold、题面、`run_tests.sh` 或解析规则；没有为保住 gold 放宽任何断言；新期望都来自公开文本与 base 行为。
- 未覆盖（不在本次修订范围）：`--on-failure continue`、一次调用中多条失败且退出码不同、rerun、run-procedure 等（公开读者 R8/R10：公开材料未约定，属多解，不应加断言）；Python API 保持抛 `IncompleteResultsError`（公开读者 R6）仍只由公开 `test_run.py`/`test_rerun.py` 保护、不计分——已知违反它的 K2 已被 ignore 键挡住，剩余风险按 S2 登记。
- 试跑工具不核隐藏测试树与入口摘要，权限布置也简化；定稿后须走正式修订单、派生镜像材料步骤与正式评分（noop、gold 各 ≥1 次，K1–K4、H 各 1 次）。
- 不需要用户决定。

## 7. 交协调者落正式修订单时

1. `hidden_test_text_replace`，`target: test_1.py`：一条 edit（锚点见 §3），父 sha256 `b2c90c1b…`，子 sha256 `6f1d831d…`。
2. `expected_text_replace` 或整文件替换：新增 3 键（§4），父 sha256 `42b8016a…`，子文件见 `trials/expected_after.json`。本题此前无期望修订，不需要合并。
3. 触发反例与依据：§1、§2；试跑原件在 `trials/`。
