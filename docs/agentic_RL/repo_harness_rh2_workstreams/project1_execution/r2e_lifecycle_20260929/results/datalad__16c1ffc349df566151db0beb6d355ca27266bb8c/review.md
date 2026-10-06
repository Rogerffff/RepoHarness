# datalad `16c1ffc3` 独立复核·第二步（review.md）

- 角色：独立复核者（单题闭环试行，按统一标准 v1）。写于 2026-09-29 约 07:30（+08，本机时钟）。第一步初判 `reviewer_initial.md` 保持原样，没有改动。
- 路径缩写（均相对仓库根）：
  - `OUT` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_lifecycle_20260929/results/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`
  - `NEW` = `runs/r2e_lifecycle_20260929`；`INV` = `NEW/inv/datalad_16c1`；`DC` = `NEW/devcheck/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`
  - `H` = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_env_repair_20260924`
  - `PRIV`、`WT` 与初判相同（私有包、公开工作树）

## 0. 结论先行

**同意**

- 主审定稿：S1，`needs_repair`。R-c 必做；R-b 与 R-c 同批，不能单独做。
- 用途四项：问题定位 yes，能力比较 conditional，训练候选 no，留出 no。
- 我逐一读了账本行与日志，确认执行证据坐实了三处 S1 与一处误拒：
  - 退化候选 D 得 1.0；
  - 错误修法 N 得 1.0；
  - 合理替代解 C2 得 0.0，失败点正是 `sadfilter`；
  - 另一合理替代解 C1 得 1.0。

**修改**（都不改变处置）

1. **第 3 步的退化候选改认 D。** 我初判的 C-deg 与主审的 N 是同一处一行改动。N 更适合归在第 4 步，见 §3.1。
2. **验收里 F 从“可选”改为“必跑”。** “R-b 必须与 R-c 同批”这条约束，理由完全建立在 F 上。
3. **B.1 与 B.3 必须一起上；B.2 只能与二者进同一版本。** R2E 的键集要求严格相等：只上 B.1，观测会多出 2 个期望里没有的键（unexpected），gold 判 0。
4. **记录更正。** 新机器上的全部正式评分、devcheck 和行为对照，用的都是配方 `r2e_derive_v1+sysconfig_v1`。主审记录说只有私有行为对照是这个配方，不准确。
5. **链路条件的写法要补全三件事**（建议文本见 §5）：放宽的是哪个时限；怎么放宽的（实验包装在运行时替换函数）；放宽值记在哪里（只在运行日志首行，账本行里没有）。
6. **事后审计要读输出行，不能读外层退出码。**
   - D 下 `repro_issue_example` 的退出码是 0，只是打印 `RESULT []`。
   - 私有行为对照 JSON 的顶层 `rc` 在 N 下也是 0，真正的退出码在 stdout 的 `RH2_CMD_RC=1`。

**保留**

- R-b 是否属于 P5（任务目标层面的两种读法）：我与主审都判“不是”，交 Codex 复核。
- 一条可选加固：过滤器抛出的非 `ValueError` 异常应当传出（T3）。是否并入由协调者决定，不是开做的前提。

**修订可以开做。**把 B.1、B.2、B.3 作为同一个新材料版本实施，按 §4 跑验收，再交 Codex 复核。

## 1. 第二步实际读取范围

- **公开读者**：`OUT/public_read.md`、`OUT/commands.json`（全文）。
- **主审**：`OUT/analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`（全文）；`OUT/cands/` 下 4 个补丁与 3 个 `pcheck_*.sh`（全文）。
- **历史**（按 `runs/r2e_static_prep_20260924/v3/history/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/refs.json`）：
  - 本题三件：`H/tasks/datalad__16c1ffc3…/findings.md` 全文；`screening_record.json` 的 disposition、issues、solver_conditions；`facts.json` 的键与片段。
  - `H/known_issues.json` 的三族；`H/decisions.md` 的 E06、E10、E14 行；`H/results_20260924.md:20-24`。
  - `H/repros/datalad__16c1ffc3….py` 全文；`H/packages/p2/README.md` 的 §2.5、§2.6、§6。
- **新机器实跑**：
  - `NEW/env_verify/ledger_l2_{noop,gold}.jsonl` 第 2 行；`NEW/budget_v5/ledger_{noop,gold}.jsonl` 第 1 行，以及 `NEW/budget_v5/{noop,gold}.log`。
  - `INV/ledger_{D,N,C2,C1}_budget1200.jsonl` 第 1 行。
  - `INV/logs_*/*.eval.log`：D 读了全段；N、C1 读了摘要；C2 读了失败段。
  - `INV/pcheck_*.json` 全部 6 份；`INV/inv_16c1_{a,b}.sh`、`INV/run_{a,b}.log`。
  - `DC/orig/attempt.json`（checks、stages、commands_result、overlay、image_facts 等）；`DC/orig/captures/*.out` 全部；`DC/private_control.json`。
- **代码**：`rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py` 全文。本地副本 sha256 前缀 `3cdcd287`；与远端 `/work/code_v7/rh2` 的副本是否相同，未核。
- **草稿区核对**：
  - 把 `PRIV` 的 expected 与隐藏测试复制到 scratchpad，从 `card.md` 附录 B 抽出 B.1–B.4；
  - 只做了 `git apply --check`、`git hash-object` 和 `py_compile`（后者只查语法，不执行）。
- **没读**：`*.diagnostics.json`、其它题的账本行、devcheck 的 trajectory 与桩请求、本批 README / `board.json` / `assignments.json`。
- 没有运行项目代码，也没有开容器或远端。

## 2. 逐项核主审的决定性主张

| # | 主审主张 | 我的核对（引用是否支持；证据是否对应本题、当前材料、对应身份） | 结论 |
| --- | --- | --- | --- |
| 1 | 第 2 步 T2c：核心断言只用了题面示例 | `PRIV/hidden_tests/test_1.py:426-429` 与题面示例同命令、同 `4`、同 `dataset='awesome'`、同一个“键存在”检查 | 同意（与初判一致） |
| 2 | 第 3 步：D 正式评分 1.0 | 见下方“D 的证据” | 同意，详见 §3.1 |
| 3 | 第 4 步：N 正式评分 1.0，且破坏旧式 filter | 见下方“N 的证据” | 同意；N 与我的 C-deg 等价 |
| 4 | T1：C2 正式评分 0.0 | 见下方“C2 的证据” | 同意，另加一条限定，见下方 |
| 5 | C1 正式评分 1.0，可作替代正对照 | `INV/logs_C1/…516e4496.eval.log:113-117` 行号后移到 `generator_func:1047`，说明加载的是候选代码 | 同意，限定同第 4 行 |
| 6 | 5 个死键（T5）；历史结论“不影响评分正确性”部分推翻 | 四个候选的日志里，这 5 键都是 `TypeError: … multiple values for argument 'path'` | 同意 |
| 7 | devcheck 检查项全真，开发路径已验 | 见下方“devcheck 的证据” | 同意 |
| 8 | 历史复现“与题面逐字一致”其实是脚本自己写的消息 | `H/repros/datalad__16c1ffc3….py:30` 自行拼出 `"'dataset' not found in %r"`；真正逐字一致的证据是评分日志里 `assert_in` 给出的消息 | 同意这项更正 |
| 9 | 本机评分须把时限放宽到 1200 s（E3） | 实质同意 | 写法需补全，见 §5 |
| 10 | `recipe_ref`：新机器重建 `r2e_derive_v1`，只有私有对照是 `+sysconfig_v1` | 不准确，见下方“配方身份” | 更正引用（记录层面）。对结论无影响：noop、gold 在新旧两种配方下逐键相同 |
| 11 | delta 里写“gold 只在给了 dataset 的调用里收到” | 措辞不精确：gold 只在 `dataset` 以关键字给出（或由 Dataset 方法自动补上）时收到；按位置传入时，gold 收到的是 `[]`（`DC/private_control.json` 的 `positional_dataset []`） | 改措辞。这正是已登记的 A2（T3）；B.1 刻意不用按位置传参，对两种读法中立，这样做是对的 |

**D 的证据**

- 账本：`INV/ledger_D_budget1200.jsonl:1` 为 8/8。
- 补丁 sha256 `0bcb50fc…` 与 `OUT/cands/datalad_16c1_D.patch` 相同；以 `agent/54321` 应用；投影只含 `datalad/interface/utils.py`。
- 日志 `INV/logs_D/…03e96f24.eval.log`：
  - `:1` 为 ` M datalad/interface/utils.py`；
  - `:119-122`、`:139-142` 共 4 条 `not reporting result ('dataset' not found in {} …)`；
  - `:147` 为 `PASSED …::test_result_filter`。
- 行为对照：`INV/pcheck_repro_issue_example_D.json` 打印 `RESULT []`；gold 打印 `[0, 1, 2, 3]`。

**N 的证据**

- 账本：`INV/ledger_N_budget1200.jsonl:1` 为 8/8。
- 补丁 sha256 `5ea0edbc…` 与 cands 中的副本相同。
- 日志 `:139` 为 `PASSED …::test_result_filter`。noop 恰好在这个键上失败，所以 N 的改动确已生效。
- 行为对照：`INV/pcheck_filters_backcompat_N.json` 的 stderr 为 `TypeError: __call__() got an unexpected keyword argument 'dataset'`；gold 打印 `BACKCOMPAT_OK`。

**C2 的证据**

- 账本：`INV/ledger_C2_budget1200.jsonl:1` 为 7/8，不符键只有 `test_result_filter`。
- 日志：
  - `:138-140`：调用栈经过 C2 自己的 `_result_filter`，即 `return result_filter(res, **_call_kwargs)`；
  - `:148`、`:153`：`'dataset' unexpectedly found in {'number': 4, 'dataset': None}`。
- 行为对照：`INV/pcheck_filter_kwargs_probe_C2.json` 五行都是 `['dataset', 'number']`。
- **限定**：“C2 兼容旧式 filter”目前只有静态推断。
  - 现行隐藏测试从不在带关键字参数的调用里使用单参 filter，所以 C1 的 1.0 也证明不了这一点。
  - R-c 验收时，C2 和 C1 都要通过 `test_result_filter_plain_callables_with_call_kwargs`，届时 T1 的前提才由执行证据闭合。

**devcheck 的证据**

- `DC/orig/attempt.json`：`checks` 13 项全为 true。
- `DC/orig/captures/`：
  - `repro_issue_example.out`：agent 身份，rc 1，调用栈停在 `utils.py:1030`；
  - `filters_backcompat.out`：base 上打印 `BACKCOMPAT_OK`；
  - `filter_kwargs_probe.out`：五行都是 `[]`；
  - `public_tests_narrow.out:200`：18 passed；
  - `env_imports.out`：`/usr/bin/git-annex` 在。
- `DC/private_control.json`（root 身份，应用 gold）：`RESULT [0, 1, 2, 3]`、`BACKCOMPAT_OK`；kwargs 探针逐行等于公开读者按 `_kwargs` 读法做的预测。

**配方身份（第 10 行）**

- 以下各处都记为 `r2e_derive_v1+sysconfig_v1`（recipe_sha256 `e2e17bf1…`，镜像 `3874afba…`，tag `…-r2e_derive_v1s`）：
  - `NEW/budget_v5/ledger_{noop,gold}.jsonl:1`；
  - `INV/ledger_*_budget1200.jsonl:1`；
  - `NEW/env_verify/ledger_l2_{noop,gold}.jsonl:2`；
  - `DC/orig/attempt.json` 的 `overlay`。
- 旧机器是 `r2e_derive_v1`（镜像 `c2578ef0…`，recipe_sha256 `0da821a1…`）。
- `sysconfig_v1` 改了什么，我没有核，请在记录里链接它的定义。
- 版本口径：主审写 v3–v8，协调者说 v3–v9，以协调者为准。

## 3. 复核重点逐条回答

### 3.1 D 作为第 3 步退化候选：成立

- **位置**：`datalad/interface/utils.py:1032` 的 `except ValueError`，在 gold 改写的过滤调用块（`WT/datalad/interface/utils.py:1028-1034`）之内。写这个补丁不需要知道 gold 的任何实现细节。
- **类型**：属于 v1 列举的“吞掉错误、抑制症状”。
- **违反的公开要求**（两条都有公开依据）：
  1. **核心要求根本没实现。**D 下过滤器仍然收不到 `dataset`；题面原例里 `custom_filter` 的断言照样失败，只是被吞掉了，调用返回 `[]` 而不是 4 条结果（行为对照已证）。题面的 Expected Behavior 是“收到 `dataset` 并正常运行”，D 两点都不满足。
  2. **过滤语义被改变。**
     - 文档只把“返回假值”和“抛 `ValueError`”列为排除结果的方式（`WT/datalad/interface/utils.py:864-867`），base 代码也只捕获 `ValueError`（`:1032`）；
     - 题面的 Actual Behavior 本身就是过滤器的 `AssertionError` 传到调用方；
     - D 把这类异常一律变成静默丢弃。
- **评分证据有效**：补丁确已交付，目标测试确已执行（§2 第 2 行）。4 条 debug 行证明，得 1 恰恰是因为吞掉了 `greatfilter` 的断言。
- **根因**：隐藏测试的正向断言写在过滤器回调里，外层不检查调用的返回结果（`PRIV/hidden_tests/test_1.py:426-429`）。
- **与我初判的差别**：我原把 C-deg（即 N）列为第 3 步，理由是“关掉检查”。但 base 里本来没有这个检查，它是 gold 新增的；N 实现了功能，只破坏了旧行为，更像“常见的半对修法”。D 连功能都没实现却得 1，是更典型的第 3 步证据。
- **N 与 C-deg 等价**：N 的补丁（`OUT/cands/datalad_16c1_N.patch`，hunk 在 `utils.py:1030`）与我描述的 C-deg 文字相同。
- **C2 与 C-bind 等价**（就本题而言）：
  - 判断过滤器是否接受 `**kwargs`：C2 用 `inspect.signature` 且失败时回退；我用的是 gold 式的 `getfullargspec` 加 `Constraint.__call__` 展开。对函数、lambda、Constraint 实例，两者结果相同。
  - 组装参数：C2 手工 zip、补默认值后再 `update(_kwargs)`；我用 `Signature.bind(...).apply_defaults()`。对 `Test_Utils.__call__(number, dataset=None)` 的各种调用，两者得到的 dict 逐项相同。
  - 两处差别都在隐藏测试之外：C2 遇到签名之外的关键字参数不会报错，更稳，所以是更好的代表。
- **我接受主审的划分**：D 为第 3 步（T2b），N 为第 4 步。两者都是 S1，处置不变。

### 3.2 R-b 必须与 R-c 同批（候选 F）：成立

F 是故意写错的候选：给接受 `**kwargs` 的过滤器固定传 `dataset=None`，与调用无关（`OUT/card.md` 附录 B.4）。

| 材料状态 | `greatfilter`（只查键在不在） | `sadfilter` | 新测试 `…_gets_call_kwargs` | F 的得分 |
| --- | --- | --- | --- | --- |
| 现材料 | 过（键在） | 挡住（严格要求键不存在） | — | 0 |
| 只上 R-b | 过 | 过（放宽后 `None` 合格） | — | **1（新漏洞）** |
| R-b 与 R-c 同上 | 过 | 过 | 挡住：`kw.get('number') == 4`、`kw.get('dataset') == 'awesome'` | 0 |

- 现材料里，`sadfilter` 的“过严”恰好是唯一挡住“有键无值”这类候选的断言。
- 结论：理由成立。补两点：
  1. **F 改为必跑。**同批约束的依据就是 F；跑一次 F，还能同时证明 B.1 的取值断言确实执行了。
  2. **B.1、B.2、B.3 进同一个新材料版本，不留“先 R-b 后 R-c”的中间版本。**若 Codex 认定 R-b 属于 P5 而撤回，R-c（B.1 + B.3）照做；此时 F 仍被严格的 `sadfilter` 挡住，C2 型尝试单列为争议。

### 3.3 两版 R-c：采用主审的 B.1

| 方面 | 主审 B.1 | 我初判的 R-c |
| --- | --- | --- |
| 组织方式 | 两个新测试函数，新增 2 个 PASSED 键（需要 B.3） | 追加在 `test_result_filter` 里，键集不变 |
| 非示例实例 | 以关键字给出的 `number`；list 与 generator 两种模式；Dataset 方法调用（要求 `dataset is ds`） | 只有 list 模式下的 `number` |
| filter 的去留决定是否被遵守 | 断言结果为 `[1, 3]` | 断言结果为 `[0, 1, 2]` |
| filter 确实被调用 | `ok_(seen)` | 无，只靠取值断言间接保证 |
| 旧式 filter | `EnsureKeyChoice`、`&` 组合（即 `Create.result_filter` 与命令行过滤器的形状）、lambda；直接调用与 Dataset 方法两条路径 | `EnsureKeyChoice`、lambda；只有直接调用 |

**结论：采用 B.1，不必合并我那一版。**

- B.1 覆盖了我那版的全部内容，还多出 generator 模式、Dataset 方法、`&` 组合，以及“filter 确实被调用”。
- 分成独立的键更好：失败时能直接看出哪条要求没满足，便于事后分析；reward 仍然是全有或全无。

**我对 B.1 的静态核对（未实跑）**

- **补丁本身**：
  - 在草稿副本上，B.1、B.2、B.3 能同时应用，`py_compile` 通过；expected 共 10 个键，新函数名唯一；
  - 新测试只用了已导入的 `assert_equal`、`ok_`、`Dataset`、`EnsureKeyChoice`；
  - 不带装饰器，不受 `path` fixture 冲突影响，也不需要 git-annex。
- **对合理读法中立**：
  - 只用 `.get('number')`、`.get('dataset')` 取值，不断言调用次数，也不断言 kwargs 的完整内容；
  - `number` 以关键字传入，Dataset 方法路径由 `datasetmethod` 转成关键字；
  - 所以以下实现都能通过：只传显式关键字参数（gold、C1）、传全部参数（C2）、连公共参数一起传、先传 kwargs 遇 `TypeError` 再回退。
  - 我没有找到会被 B.1 误拒的合理实现。
- **一处取值依赖（A3）**：`kw.get('dataset') == 'awesome'` 要求原样传值。依据足够：
  - `eval_results` 本身不做参数约束转换；
  - 渲染器先例也是原样传；
  - 上游后来的 `get_allargs_as_kwargs` 同样原样传（`runs/r2e_static_prep_20260924/v3/public/datalad__58ba5165…/worktree/datalad/interface/base.py:608-634`）。
- **解析（低风险，验收时顺带核）**：
  - 新键名较长。N 下 `FAILED r2e_tests/test_1.py::test_result_filter_plain_callables_with_call_kwargs` 约 79 列，pytest 在 80 列终端下会省去 ` - 消息` 后缀。
  - R2E 解析取 `::` 之后、` - ` 之前的部分，没有后缀也能拿到正确的键。
  - 验收时核对 N 的 `mismatched` 恰为这一键，`missing` 与 `unexpected` 为空即可。

### 3.4 B.3 与已批准的期望修订：不冲突

- **本题没有任何已批准的修订。**
  - `PRIV/revisions.json` 为 `[]`（sha256 `37517e5f…`）；`PRIV/grading_bundle.json` 与 `PRIV/run_refs.json` 的 `material_revisions` 都为空；
  - 历史处置表里本题也没有修订（`H/results_20260924.md:22`）。
  - 因此 B.3 不与任何已批准修订冲突，它将是本题第一个材料修订。
- **B.3 基于当前材料制作**：
  - `git hash-object` 算出 `expected_output.json` 为 `325e99f…`、`hidden_tests/test_1.py` 为 `b961d0d…`，与 B.1–B.3 补丁的 index 行一致；
  - 原文件末尾没有换行，与 B.3 的 `\ No newline at end of file` 一致。
- **键**：新键不与现有键撞名；格式与现有模块级测试一致，只有函数名。
- **实施要点**：
  1. **原子性。**B.1 与 B.3 必须同时上：只上 B.1 会多出 2 个 unexpected 键，gold 判 0；只上 B.3 会少 2 个键（missing）。
  2. **登记。**在 `revisions.json` 写明：
     - 新版本，以及父版本（expected `97ecb569…`、隐藏测试树 `a5ddfbe5…`）；
     - 理由：T2c、T2b、第 4 步、T1；
     - 触发反例：D、N、C2、F。

     同时更新评分面行里的两个摘要。
  3. **镜像。**环境卡 §1 说隐藏测试会移到镜像内的 root 私有目录，其它题的材料修订用 `+material_vN` 配方重建过镜像。如果本题也是这样，就按同一方式重建，并登记配方身份。
  4. **验收日志**要看到新的 `RH2_SETUP_HIDDEN_TESTS_TREE`、`collected 10 items`、`expected_count 10`。

### 3.5 “评分需放宽时限”这一链路条件的写法：见 §5

## 4. 修订可以开做：条件与验收

**条件**

1. B.1、B.2、B.3 作为同一个新版本实施。
2. 若担心返工，可以先就“R-b 是否属于 P5”单独问一次 Codex。否则照常同批实施；事后若撤回 B.2，按 v1 §5，对撤回后的版本至少补跑 gold、noop、C2、F。

**验收矩阵**

- 在放宽时限下做正式评分。
- 每次都核对：`APPLY_RC=0`、投影只含该文件、`collected 10 items`、新的隐藏测试树摘要、`missing` 与 `unexpected` 为空，并从日志确认失败位置与下表一致。

| 候选 | 必跑 | 预期得分 | 预期失败位置 |
| --- | --- | --- | --- |
| noop | 是 | 0 | `test_result_filter`（`greatfilter`）；`…_gets_call_kwargs`（`number` 为 None）。`…_plain_callables…` 为 PASSED |
| gold | 是 | 1 | — |
| C1 | 是 | 1 | —。同时以执行证据确认它兼容旧式 filter |
| C2 | 是 | 1（带 R-b） | —。同上；若 R-b 撤回则为 0，失败仍在 `sadfilter` |
| D | 是 | 0 | `…_gets_call_kwargs`：`kw.get('number')` 为 None |
| N | 是 | 0 | `…_plain_callables…`：`TypeError: … unexpected keyword argument 'dataset'` |
| F | 是（原为可选） | 0 | `…_gets_call_kwargs`：缺 `number` |
| C-ign | 可选 | 0 | `…_gets_call_kwargs`：结果为 `[0, 1, 2, 3]`，不是 `[1, 3]` |

- **C-ign 的改法**：在 gold 上，把包装函数的 `return result_filter(res, **_kwargs)` 改成 `result_filter(res, **_kwargs); return True`，即调用接受 kwargs 的 filter 但忽略它的返回值。
- C-ign 是唯一专门打到“去留决定”断言的候选：D、N、F 都先在别处失败。它在现材料上也会得 1，是第 4 步的又一例，不影响处置。
- 验收通过后交 Codex 复核；复核前不作正式材料。

## 5. 链路条件的建议写法

替换 `card.md` 与 `screening_record.json` 里“本机评分的控制面保护时限要放宽到 1200 s”一句。它是本机、本批的评分链路条件（E3），不是本题的属性，不写成“本题需要 1200 s”。

> **评分链路条件（E3，本机，非题目缺陷）**
>
> - **是哪个时限。**评分前有两步：控制面保护（`chown -R <评分用户> /testbed`，`.venv` 在其中）和基线重建 census。两步共用 `GradingEnvSpec.env_reset_timeout_seconds`，缺省 300 s，CLI 与环境变量都不能改。
> - **本机实测。**
>   - 可信 setup 在两路并发时耗时 152.6–152.8 s（`NEW/budget_v5` 两行）和 210.2–221.8 s（`INV` 四行）；
>   - `NEW/env_verify` 那一轮超过 300 s（并发度未核），结果记为 `failed_to_grade / infra_failure: grading_control_surface_protect_timeout_after_300s`，不会误记为 0 分。
> - **怎么放宽的。**本题现有的新机器评分证据，都用实验包装 `rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py --env-reset-timeout 1200` 取得。它在运行时替换 `build_grading_spec_from_host_view`，只抬高这一个时限。
> - **值记在哪里。**只记在每次运行日志的首行：`NEW/budget_v5/{noop,gold}.log:1` 与 `INV/run_{a,b}.log`。账本行的 `budgets` 字段只有 900 / 120 / 3600 / 1800 四项，不含它。引用这些账本时要同时引用日志首行。
> - **判分语义未变。**以下各项与旧机器相同：`grader_version`、parser、`scripts_digest`、runner digest、隐藏测试树与入口脚本摘要、评分用户与资源 profile。noop 与 gold 的逐键结果也与 09-23 / 09-24 相同。镜像配方改为 `r2e_derive_v1+sysconfig_v1`，内容待链接。
> - **谁来处理。**进入探针或训练前，由 A 线二选一：把这一时限做成正式可配置并写进账本；或者降低 chown 开销。在此之前，本题在本机评分须带同一包装。
> - **解题侧。**从容器启动到 init 约 434 s（`DC/orig/attempt.json` 的 stages，未拆分），会影响回合预算的估计，同样交 A 线。包装脚本的注释说 orange3 也受这一时限影响，本复核没有核。

## 6. 主审可能没想到的范围（新增，均为静态推断）

1. **D′：正确转发，但把异常一律吞掉。**
   - 改法：gold 加上 `except Exception`。
   - 修订后它仍能得 1，因为修订后所有正向断言都不再依赖异常传出。
   - 它不能钻核心要求（必须先正确转发 kwargs 才过得了新测试），只是破坏“非 `ValueError` 异常要传出”这一旧行为。定为 T3，登记即可。
   - 若想顺手堵上，可在 B.1 的 `test_result_filter_gets_call_kwargs` 末尾加下面几行：

     ```python
         # errors raised by a filter other than ValueError are not swallowed
         def brokenfilter(res, **kwargs):
             raise RuntimeError('broken filter')
         assert_raises(RuntimeError, Test_Utils().__call__, 4,
                       dataset='awesome', result_filter=brokenfilter)
     ```

   - 公开依据：
     - 文档只列了两种排除方式（`WT/datalad/interface/utils.py:864-867`）；
     - 题面的 Actual Behavior 就是过滤器的异常传到调用方；
     - base 只捕获 `ValueError`（`:1032`）。
   - 各候选的预期：
     - noop、gold、C1、C2、以及“先传 kwargs、遇 `TypeError` 再回退”的实现都通过（`RuntimeError` 不是 `TypeError`）；
     - D 与 D′ 失败。
   - 这是 R-c 里另一个窄问题。是否并入由协调者决定；若并入，把 D′ 加进验收，预期 0。
2. **事后审计的判据**（若用现材料进入探针或能力比较）：
   - D 型：跑公开命令 `repro_issue_example`，判据是输出行 `RESULT [0, 1, 2, 3]`。D 下它的退出码是 0（`INV/pcheck_repro_issue_example_D.json`），不能用退出码判。
   - N 型：跑公开命令 `filters_backcompat`，判据是 `BACKCOMPAT_OK` 行。私有行为对照 JSON 的顶层 `rc` 在 N 下是 0，真正的退出码在 stdout 的 `RH2_CMD_RC=1`（`INV/pcheck_filters_backcompat_N.json`）。
   - 这与 v1 §8“打印型脚本要写明读哪一行、什么算失败”一致。
   - 改动了 `datalad/tests/` 或 `.venv` 的得 1 补丁单列，主审已写。
3. **正对照的前提**：C1、C2 满足全部公开要求这一点，目前旧式兼容部分只有静态推断，由 §4 的验收闭合（§2 第 4 行）。
4. **其它合理实现对 B.1 的风险**：见 §3.3。我没有发现新的 T1。按位置传 `dataset`（A2）和值是否转换（A3）两点，B.1 分别保持中立或有依据。

## 7. 用途与探针就绪差距（复核意见）

同意主审的四项用途和差距表，补充如下：

- **`capability_comparison` 的条件写法**：
  - 条件 1 改用 §5 的写法：它是本机、本批的评分链路条件，不是题目条件；
  - 条件 2 的审计判据按 §6.2 写成“读输出行”。
- **`training_candidate`**：R-c（与 R-b）验收通过、并经 Codex 复核后重评。届时要登记的 S2 缺口有：
  - G1→T3：gold 遇到拿不到签名的可调用对象会报错；
  - A2、A3（T3）；
  - D′（T3，若未加固）；
  - T5 死键；
  - X1。
- **`heldout_candidate`**：no。修订后只能作为标明版本的自建题。
- **探针就绪差距补两条**：
  1. 新材料版本的登记，以及（如需要）派生镜像重建，由协调者补；
  2. 时限正式化与账本自描述，由 A 线补。

## 8. 保留与未决

- **R-b 是否属于 P5**：我与主审一致，判“不是”。
  - 两种读法都完成了任务目标，差别只在“没给的参数”怎么表示；
  - 放宽后，错误的或残留的值仍会被拒绝；
  - 待 Codex 复核。
- **`sysconfig_v1` 的内容**：未核。
- **gold 对拿不到签名的可调用对象会不会报错**：仍只有静态推断（主审与我一致），不影响处置。
- **解题侧约 434 s 的启动开销**：没有拆分，交 A 线。
- **真实模型求解**：未跑（清单第 33–36 项）。
