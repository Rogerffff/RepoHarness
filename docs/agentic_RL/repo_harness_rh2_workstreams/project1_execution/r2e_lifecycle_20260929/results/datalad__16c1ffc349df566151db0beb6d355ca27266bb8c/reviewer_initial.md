# datalad `16c1ffc3` 独立复核·第一步初判（未读主审产物）

- 角色：独立复核者（单题闭环试行，按统一标准 v1）。写于 2026-09-29 约 07:10（+08，本机时钟）。
- 只依据原件与方法文档；未读公开读者、主审的产物，也未读任何历史结论。
- 路径缩写（均相对仓库根）：
  - `PUB` = `runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`，`WT` = `PUB/worktree`
  - `PRIV` = `runs/r2e_static_prep_20260924/v3/private/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c`
  - `R0` = `runs/r2e_rf_20260923/remote`，`R1` = `runs/r2e_env_repair_20260924/_rerun2`

## 0. 结论先行

| 项 | 初判 | 证据级别 |
| --- | --- | --- |
| 题目目标 | `eval_results` 应把 API 调用的关键字参数交给接受 `**kwargs` 的 `result_filter`；不接受额外参数的过滤器照旧只收结果字典 | 公开题面 + base 源码 |
| 材料与初态 | 一致。gold、expected、隐藏测试、`run_tests.sh` 的摘要与账本和日志逐项对上；noop 在目标键上的报错与题面 “Actual Behavior” 逐字相同 | 历史真实 RH2（current 行） |
| 严重度 | **S1**。第 2 步命中（T2c，对照测试输入即可确认）；第 3 步的退化候选 C-deg 静态预测得 1（T2b，待正式评分确认） | 静态推断，待实跑 |
| 误拒风险 | `sadfilter` 断言 `assert_not_in('dataset', kwargs)`，会拒绝“连同默认值一起传入”的实现，而上游后来正是这样实现的。记为 P3→T1，conditional | 静态推断 + 同仓公开包事实；C-bind 待跑 |
| 期望 FAILED 的 5 键 | 迁移伪影：R2E conftest 的 `path` fixture 与 datalad 的 `with_tempfile` / `with_tree` 装饰器冲突，测试体没有执行。正确修复不会被它们惩罚，但它们也不提供任何回归保护（T5，登记） | noop、gold、M3 日志一致 |
| 题目关系 | X1：本题修复（经重构）和改写后的测试，出现在同仓 `58ba5165`、`19f5b450` 的公开初态中；机械扫描漏报 | 逐文件核对公开包 |
| 用途 v1 | 问题定位 yes；能力比较 conditional；训练候选 no（当前材料）；留出 no | 见 §12 |
| 唯一优先下一步 | 用正式评分实跑 C-deg（只改一行）；同一批次顺带跑 C-bind | — |

## 1. 实际读取范围

- **方法与口径**
  - `roles/reviewer_r2e.md`：全文。
  - `roles/investigator_r2e.md`：Read 返回了全文（约 53 行）。只把“材料”“R2E 的评分口径”“第二批补充规则”“单题闭环试行补充”四节当作口径。
  - `quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md`、`task_screening_standard_v1_20260925.md`：全文。
- **公开包**
  - `PUB/user_prompt.txt`、`public_bundle.json`、`environment_brief.md`。
  - `worktree_manifest.json`：只读 export、initial_diff、untracked 三组字段。
  - `WT` 下的定点文件：
    - `datalad/interface/utils.py`：1–90 行、840–1138 行。
    - `datalad/interface/tests/test_utils.py`：与隐藏测试逐行 diff。
    - `datalad/support/constraints.py`：Constraint 家族的 `__call__`。
    - `datalad/distribution/dataset.py:404-453`、`datalad/distribution/create.py:80-100,295-320`。
    - `datalad/interface/base.py:315-340`、`datalad/interface/save.py:155-170`、`datalad/interface/unlock.py:140-160`。
    - `datalad/tests/utils.py`：第 34 行、410–440 行、540–570 行。
    - `datalad/utils.py:548-563`、`tox.ini`。
  - 另在全仓 grep 了 `result_filter` 的用法。
- **私有包**
  - `PRIV/expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`（空）、`run_refs.json`、`grading_bundle.json`、`validation_bundle.json`。
  - `hidden_tests/` 下三个文件全文。
  - 以上逐个核对了 sha256。
- **运行原件**（`run_refs.json` 中 `material=current` 的 4 行；四个日志的 sha256 均与 `run_refs.json` 一致）
  - 09-23 R-f 全池：`R0/ledger_r2e_all_noop.jsonl:11`、`R0/ledger_r2e_all_gold.jsonl:11`；日志 `R0/eval_logs_r2e/…noop-d_ff9ede96.eval.log`、`…gold-d_dff48178.eval.log`，读了摘要段。
  - 09-24 中央复跑：`R1/ledger_noop.jsonl:11`、`R1/ledger_gold.jsonl:11`；日志 `R1/eval_logs/…rer_dcc2c830.eval.log`（noop，全文）、`…rer_a280b0c2.eval.log`（gold，头部与 88–148 行）。
  - independent_reference：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:3`（前 600 字符），以及 `…/datalad/16c1ffc349df/gold/{a1,a2}/test_output.txt` 的摘要行。
- **同仓其它题**（只读公开包）
  - `datalad__58ba5165…`、`datalad__19f5b450…`：标题、`version.py`、`CHANGELOG.md` 开头；`interface/utils.py`、`interface/base.py`、`interface/tests/test_utils.py` 的定点 grep 与片段。
  - `datalad__9ba5de09…`：`user_prompt.txt`，`utils.py` grep。
  - `datalad__6b6fa389…`：标题、版本。
- **跨题比对**：两份扫描的 method 字段，以及所有涉及 datalad 的 pair。
- **读取顺序**：先读公开题面和公开包，随后同一步打开了私有 expected、gold、`run_refs.json`，再读隐藏测试。所以下文的替代实现不是在没见过 gold 的情况下构造的。不过 C-bind 的依据来自题面措辞和同仓后续版本的公开源码，不来自 gold。
- **未读**
  - OUTPUT_DIR 其它文件、任何 `history/`、各审查目录、本批 README / `board.json` / `assignments.json`、`runs/` 下其它分析与汇总。
  - 账本引用的 `*.diagnostics.json`。
  - 协调者提到的今晚 `*_budget1200` 账本（`run_refs.json` 未列）。
  - devcheck 目录（本步未提供）。
  - M3 `facts/…/initial.diff`：只用了 manifest 里记的“0 字节、空串摘要”。

## 2. 公开目标（仅从公开包抽出）

**题面**（`PUB/user_prompt.txt`）：接受额外关键字参数的自定义 `result_filter` 收不到 API 调用的 kwargs。示例如下：

```python
def custom_filter(res, **kwargs):
    assert 'dataset' in kwargs
    return True

Test_Utils().__call__(4, dataset='awesome', result_filter=custom_filter)
```

- 期望：过滤器收到 `dataset`，不报错。
- 实际：`AssertionError: 'dataset' not found in {}`。
- 示例用到的 `Test_Utils` 是公开类，定义在 `WT/datalad/interface/tests/test_utils.py:329-352`。

**由公开材料推出的要求**

- **R1（核心）**：过滤器接受 `**kwargs` 时，应拿到本次调用的关键字参数，包括名字和值。题面是一般性表述，`dataset` 只是一个例子。
- **R2（旧行为）**：不接受额外参数的过滤器（单参函数、`Constraint`）仍只收结果字典。依据：
  - `result_filter` 的文档（`WT/datalad/interface/utils.py:863-868`）写的是 “each to-be-returned status dictionary is passed to this callable”；
  - 公开旧用法在带关键字参数的调用里使用单参 lambda：`WT/datalad/interface/tests/test_clean.py:38-39`、`WT/datalad/distribution/tests/test_get.py:244`、`WT/datalad/distribution/tests/test_uninstall.py:156-157`；
  - `ds.save(…, result_filter=is_ok_dataset)`（`WT/datalad/interface/tests/test_save.py:119`，`is_ok_dataset(r)` 定义在 `WT/datalad/interface/results.py:66-67`）；
  - 类级过滤器 `Create.result_filter`（`WT/datalad/distribution/create.py:89-91`）；
  - 命令行拼出的约束过滤器（`WT/datalad/interface/base.py:324-336`）；
  - 题面本身也限定为 “a custom `result_filter` that expects additional keyword arguments”。
- **R3（旧行为）**：过滤器返回假值或抛 `ValueError` 时，该结果不返回（`utils.py:864-867`、`1028-1034`）。接受 kwargs 的过滤器同样适用。

**公开材料没有规定的**：没传的参数应当缺席，还是以默认值出现；位置参数是否要按参数名给出；是否要带上 `return_type` 等公共参数。

**代码先例**：同一函数里，`custom_result_renderer(res, **_kwargs)` 与 `result_renderer(res, **_kwargs)`（`utils.py:1046-1050`）已经只把“显式传入、去掉公共参数后的关键字参数”交给钩子。这是 gold 读法的公开线索，但不是文档化的要求。

## 3. 隐藏测试、键与运行原件

**测试内容**

- `PRIV/hidden_tests/test_1.py` 与公开旧测试 `WT/datalad/interface/tests/test_utils.py` 只差两处：
  - 9 行相对导入改成了绝对导入（36–44 行）；
  - `test_result_filter` 末尾新增了 `greatfilter` 与 `sadfilter`（424–434 行）。
- 期望映射：
  - PASSED 3 个：`test_interface_prep`、`test_eval_results_plus_build_doc`、`test_result_filter`；
  - FAILED 5 个：`test_dirty`、`test_paths_by_dataset`、`test_save_hierarchy`、`test_get_dataset_directories`、`test_filter_unmodified`。

**键的分类**

- **目标键**：只有 `test_result_filter`，两次 noop 账本的 `mismatched` 都只列这一键。
- **活回归键**：
  - `test_interface_prep`：只测 `Save._prep`，与本题无关；
  - `test_eval_results_plus_build_doc`：测文档拼接（含 “dictionary is passed”）、类识别的 debug 日志、签名保持、结果个数，不用过滤器。
- **死键**：5 个期望 FAILED 键，见 §5(a)。

**运行原件**

- noop：两次 current 运行都是 7/8。`test_result_filter` 失败在 `greatfilter` 的 `AssertionError: 'dataset' not found in {}`，调用栈经过 `datalad/interface/utils.py:1030 if not result_filter(res)`（`R1/…rer_dcc2c830.eval.log:120-145`；摘要在 `:189-197`）。
- gold：两次 current 运行都是 8/8。
  - 日志首行 ` M datalad/interface/utils.py`；行号偏移（debug 行变成 `utils.py:980` / `1046` / `1048`），说明加载的是补丁后的源码（`R1/…rer_a280b0c2.eval.log:1,137-145`）。
  - 账本的 `projection.included_paths` 为 `['datalad/interface/utils.py']`。
- 材料一致性（均已核对）：
  - gold 的 sha256 `cdd8f96c…` 与账本的 `candidate.patch_sha256`、validation bundle 一致；
  - expected `97ecb569…`、隐藏测试树 `a5ddfbe5…`、`run_tests.sh` `8285765f…`，与日志的 `RH2_SETUP_*` 行和 grading bundle 一致；
  - 镜像 `rh2-r2e-derived/datalad:16c1ffc349df-r2e_derive_v1`，ID `sha256:c2578ef0…`。
- M3 独立 runner（来源镜像、来源材料）的两次 gold：同样是 3 PASSED、5 FAILED，且是同一个 TypeError（`…/gold/a1/test_output.txt:19,122-130`）。所以 5 个 FAILED 在 R2E 原始材料中就存在，不是派生镜像带来的。
- 今晚的 `*_budget1200` 运行：本步未读。
  - 协调者说明的 chown 超时属 E3 链路问题，不影响题目判断。
  - 09-23 与 09-24 的账本中，`phases.grader_trusted_setup` 已约 66 s，测试本身约 2 s。
  - 如果今晚的派生镜像是重建的，镜像 ID 可能与 `c2578ef0…` 不同，应以新账本的镜像身份为准。

## 4. 需求—断言双向表

| 公开要求或旧行为 | 依据 | 隐藏断言 | 覆盖 | 证据或下一步 |
| --- | --- | --- | --- | --- |
| R1 例子：`**kwargs` 过滤器收到 `dataset` | 题面示例 | `test_1.py:426-429` `greatfilter`：`assert_in('dataset', kwargs)` | 覆盖。但只用了题面字面值，且只查键在不在，不查值 | noop 失败、gold 通过（日志） |
| R1 一般情形：其它关键字参数，且值正确 | 题面的一般表述 | 无 | **缺失**（T2c） | C-ds；R-c |
| R3：kwargs 过滤器的返回值决定结果去留 | `utils.py:864-867` | 无（`greatfilter`、`sadfilter` 恒返回 `True`） | 缺失 | R-c 一并补 |
| R2：调用带关键字参数时，单参过滤器与约束照旧工作 | 文档、公开旧测试、`Create.result_filter`、命令行过滤器 | 无。`test_1.py:409-422` 的约束与 lambda 只在 `_kwargs == {}` 的调用下执行 | **缺失**，可被蒙混（T2b 待跑） | C-deg；R-c |
| R2 基线：没有额外 kwargs 时，约束与 lambda 照常过滤 | 旧行为 | `test_1.py:401-422` | 覆盖 | noop、gold 均通过 |
| 未传入的 `dataset` 不得出现在 kwargs 中 | **无公开依据**（只有 `_kwargs` 代码先例） | `test_1.py:431-434` `sadfilter`：`assert_not_in('dataset', kwargs)` | 有冲突风险（P3→T1） | C-bind；R-b |
| 文档、类识别日志、签名保持 | 公开旧测试 | `test_1.py:355-397` | 覆盖 | 活键 |
| 真实命令（`create`、`save`、`add`）经 `eval_results` 的行为 | 旧行为 | 本应由 5 个死键覆盖，但它们没有执行 | 无效 | §5(a) |

## 5. R2E 专项

**(a) 5 个期望 FAILED 键会不会惩罚正确修复：不会。**

- 失败位置：`datalad/tests/utils.py:564`（`with_tempfile` 的 `newfunc`）和 `:429`（`with_tree`）。
- 报错：`TypeError: test_x() got multiple values for argument 'path'`。
- 机制：
  1. `functools.wraps`（`WT/datalad/tests/utils.py:34`）在包装函数上留下 `__wrapped__`；
  2. pytest 据此看到原签名，把 `r2e_tests/conftest.py:6-9` 的 `path` fixture 以关键字参数传入；
  3. 装饰器又按位置追加一个临时路径，于是 `path` 被传了两次。
- 测试体一行都没执行；noop、gold、M3 三处结果相同。
- 只改业务源码的修复（包括更完整的修复）都无法翻转它们。只有改 `datalad/tests/utils.py` 这类测试辅助才可能翻转，而公开提示明确写了不要改测试文件。
- 处理：按 T5 的固定来源，解释为无效断言，登记即可，本轮不必做 R-a。
- 代价：这 5 键本应保护的真实命令路径完全没有保护。例如 `ds.create()` 要经过 `Create.result_filter`，恰好是 C-deg 会弄坏的路径。

**(b) 题面报错是否出现在 noop 目标键上：出现，且一致。**`R1/…rer_dcc2c830.eval.log:145` 为 `AssertionError: 'dataset' not found in {}`，位置在 `r2e_tests/test_1.py:427 in greatfilter`，经过 `datalad/interface/utils.py:1030`。

**(c) 题面是否泄漏修法：没有泄漏实现，不算 P1。**

- 题面没提 `**kwargs` 探测、`Constraint.__call__` 展开等实现细节。
- 但示例代码就是隐藏测试里的正向断言本身，只是把 `assert_in` 写成了 `assert`。这属于测试层面的示例拟合，见 §7 第 2 步。

**(d) 测试支撑与撞键：无撞键，迁移语义等价（`path` 冲突除外）。**

- 隐藏测试导入的 `datalad.tests.utils`、`nose.tools`、`datalad.api.create` 都是 base 版本，评分时不会重置。
- 只有一个测试文件，没有跨文件撞键；键是模块级函数名。
- `Test_Utils` 类名以 Test 开头，但没有 test 方法。收集 8 项，与日志一致。
- 迁移只改了导入写法，语义等价；`path` 冲突见 (a)。
- autouse fixture `setup_git_config` 会改 HOME，对活键没有影响。

**(e) 时间、随机、资源敏感的键：没有。**活键都是纯内存、确定性的。

**(f) 材料修订：无。**`PRIV/revisions.json` 为 `[]`，`run_refs.json` 的 `material_revisions` 也为空。

## 6. gold 检查

**改动内容**（`PRIV/gold.patch`）：只改 `datalad/interface/utils.py`。

- 新增 `Constraint` 导入；
- 文档补一句；
- 在 `generator_func` 里用 `inspect.getfullargspec(...).varkw` 判断过滤器是否接受 `**kwargs`，接受才把 `**_kwargs` 转给它。

**评价**

- 修好了原例。
- 没有无关改动，也不依赖未交付的文件。
- 语义：只转发显式传入、去掉公共参数后的关键字参数；位置参数不按名转发；不含默认值。这与 `utils.py:1046-1050` 的渲染钩子先例一致。

**未测的边缘**（G1→T3，静态推断，不作处置依据）

1. 对拿不到签名的可调用对象（例如 `result_filter=bool` 这样的内建类型），Python 3.7 的 `inspect.getfullargspec` 会抛 `TypeError('unsupported callable')`。gold 下整条命令直接崩溃，而 base 可用。这种用法罕见。
2. 过滤器用具名关键字形参来“期望”参数时（如 `def f(res, dataset=None)`），gold 不会转发。题面措辞可以包含这种情形，但示例是 `**kwargs` 形式，不影响评分。

**上游后来改了语义**（见 §11）：改成把“全部参数”交给过滤器，包括默认值，位置参数也按名给出。这不说明 gold 错，但说明 C-bind 是一种合理实现。

## 7. 严重度（v1 §4 五步）

- **第 1 步：不命中。**核心要求“接受 kwargs 的过滤器收到调用的关键字参数”有直接断言（`greatfilter`）。
- **第 2 步：命中，S1（T2c）。**
  - 唯一的正向断言与题面示例逐字同形：同一命令 `Test_Utils().__call__`，同一位置参数 `4`，同一关键字 `dataset='awesome'`，同一 `**kwargs` 形态，同一种“键存在”检查。
  - `sadfilter` 也只针对同一个 `dataset` 键。
  - 因此，只转发 `dataset` 的补丁（C-ds），或只转发键名、不转发值的补丁，都能满分。
- **第 3 步：静态预测得 1；正式评分确认后为 S1（T2b）。**退化候选是 C-deg：关掉 gold 新增的“是否接受 `**kwargs`”检查。
- **第 4 步：不适用。**当前证据里除 noop 与 gold 外没有已有候选，要等真实模型候选出现后再看。
- **合并判断**：S1。T2c 已确认，T2b 待确认。另外登记 T1（conditional）、T5、G1→T3、X1，以及 E3（链路问题，已知）。

## 8. 可区分候选（每个都能直接改成补丁；供协调者用正式评分实跑）

### C-deg：退化候选，第 3 步，类型为“关掉检查”

- **改法**：只改 `datalad/interface/utils.py:1030`，把 `if not result_filter(res):` 改成 `if not result_filter(res, **_kwargs):`，不加任何签名判断。`_kwargs` 已在 `generator_func` 的作用域内，base 的 1048、1050 行已经在用。
- **违反的公开要求**：R2，即文档写明的单参接口、公开旧测试中的用法、题面限定的“expects additional keyword arguments”。
- **怎样看出来**：`Test_Utils().__call__(4, dataset='awesome', result_filter=lambda x: x['somekey'] in (0, 2))`。base 与 gold 都返回 `[0, 2]`；C-deg 抛 `TypeError: <lambda>() got an unexpected keyword argument 'dataset'`。异常不是 `ValueError`，不会被 `utils.py:1032` 捕获，于是整条命令崩溃。经由 datasetmethod 调用的 `Create.result_filter`（一个 `Constraints` 对象）也会在同一处抛 TypeError。
- **预期得分**：1，即 8/8。
  - `test_1.py:409-422` 中的单参过滤器只在 `_kwargs == {}` 时被调用；
  - `greatfilter`、`sadfilter` 照常通过；
  - 5 个死键照旧失败在装饰器上。
- **实跑时须核对**：补丁确已交付（`projection.included_paths` 含该文件），且日志中 `test_result_filter` 为 PASSED。得 1 即确认 T2b。

### C-ds：第 2 步的示例拟合示意

- **改法**：在 gold 基础上，把 `def _result_filter(res): return result_filter(res, **_kwargs)` 改成 `return result_filter(res, **({'dataset': _kwargs['dataset']} if 'dataset' in _kwargs else {}))`。
- **违反的公开要求**：R1 的一般情形。
- **怎样看出来**：`Test_Utils().__call__(number=2, dataset='awesome', result_filter=f)`，其中 `f` 读 `kwargs['number']`。gold 下 `f` 能拿到 `number=2`；C-ds 下拿不到。
- **预期得分**：1。本候选可选跑；第 2 步的判断不依赖它的实跑结果。

### C-bind：T1 疑点，一个合理替代解

- **改法**：在 gold 基础上，于 `generator_func` 开头加三行：
  - `_ba = inspect.signature(wrapped).bind(*_args, **_kwargs)`
  - `_ba.apply_defaults()`
  - `_allkw = dict(_ba.arguments)`

  然后把包装函数改为 `return result_filter(res, **_allkw)`。`inspect` 已在 `utils.py:15` 导入；是否转发的判断与 gold 相同。
- **是否满足公开要求**：满足 R1–R3，也不破坏单参过滤器。
- **与上游的关系**：这正是上游后来的语义：
  - `datalad__58ba5165` 公开初态的 `datalad/interface/base.py:608-634` 有 `get_allargs_as_kwargs`，注释写明 “incl. defaults and args given as positionals”；
  - 同一初态的 `datalad/interface/utils.py:371-391,469,475,749-762` 用它把全部参数交给过滤器。
- **预期得分**：0，不匹配键为 `test_result_filter`。`sadfilter` 会收到 `{'number': 4, 'dataset': None}`，报 `AssertionError: 'dataset' unexpectedly found in {...}`。
- **结论**：若实跑为 0，则 T1 成立：`sadfilter` 的否定要求没有公开依据，却拒绝了合理解。

### 验收时可选加跑的已知错误候选

- **C-ign**：对接受 kwargs 的过滤器照常调用，但忽略它的返回值。它违反 R3，在现行测试下预计也能得 1，因为两个过滤器都恒返回 `True`。

## 9. 修订建议（v1 §5；由协调者实施与实测，Codex 复核）

### R-c：针对 T2c，以及确认后的 T2b

- **改哪里**：在 `PRIV/hidden_tests/test_1.py` 的 `test_result_filter` 末尾（第 434 行之后）追加下面的代码。
- **键不变**：`expected_output.json` 不改，`test_result_filter` 仍为 PASSED；只有隐藏测试树的摘要会变。

```python
    # non-example instance: a filter accepting **kwargs sees the actual values
    # of the call's keyword arguments (not only `dataset`), and its return
    # value still decides which results are reported
    def numberfilter(res, **kwargs):
        assert_equal(kwargs.get('dataset'), 'awesome')
        return res['somekey'] < kwargs['number'] - 1
    assert_equal(
        [r['somekey'] for r in Test_Utils().__call__(
            number=4, dataset='awesome', result_filter=numberfilter)],
        [0, 1, 2])

    # filters that do not accept **kwargs keep working when the API call
    # carries keyword arguments
    for filt in (
            EnsureKeyChoice('somekey', (0, 2)),
            lambda x: x['somekey'] in (0, 2)):
        assert_equal(
            [r['somekey'] for r in Test_Utils().__call__(
                4, dataset='awesome', result_filter=filt)],
            [0, 2])
```

**公开依据**

- 第一段：题面的一般表述（“additional keyword arguments … these `kwargs`”）加上 `result_filter` 文档中的返回值语义。`number` 是用关键字显式传入的，gold、C-bind 和“只传显式 kwargs”的实现都会给出这个参数，所以断言对这些读法中立。
- 第二段：R2 的全部依据（§2）。

**不扩大需求**：不要求位置参数按名转发，不要求带默认值，也不要求带公共参数。

**我对 gold 的静态核对**

- 第一段：`_kwargs == {'number': 4, 'dataset': 'awesome'}`，结果保留 0、1、2。
- 第二段：lambda 没有 varkw；`EnsureKeyChoice.__call__` 经 `getfullargspec` 看是 `(self, value)`，也没有 varkw，所以两者都不会被包装，行为不变。

**验收计划**

| 候选 | 预期 | 预期失败位置 |
| --- | --- | --- |
| gold | 1 | — |
| noop | 0 | 仍停在 `greatfilter` |
| C-deg | 0 | 单参过滤器循环里的 TypeError |
| C-ds | 0 | `numberfilter` 中的 `KeyError: 'number'` |
| C-ign（可选） | 0 | 得到 `[0,1,2,3]`，不等于 `[0,1,2]` |

- 每个错误候选都要从日志确认它失败在预期断言上，以证明新增代码确实执行了。
- 保存新版本、父版本、理由和触发反例（C-deg、C-ds）。

### R-b：针对 T1，条件是 C-bind 实跑为 0

- **改法**：把 `test_1.py:432` 的 `assert_not_in('dataset', kwargs)` 改成 `assert_equal(kwargs.get('dataset'), None)`。
- **理由**：“缺席”和“以 `None` 出现”两种读法都没有被公开材料排除。两版上游测试正好各要求一种：
  - 本题的隐藏测试要求缺席；
  - 上游后来的测试写的是 `assert_equal(kwargs.get('dataset', 'bob'), None)`，要求键存在且为 `None`（见 `datalad__58ba5165` 的 `datalad/interface/tests/test_utils.py:335-338`，以及 `datalad__19f5b450` 的 `:337-340`）。
- **放宽后仍保留的保护**：过滤器看到错误的或残留的 `dataset`（例如跨调用缓存 kwargs、硬编码注入）仍判 0。
- **验收**：
  - gold 为 1，noop 为 0，C-bind 为 1（误拒得到纠正）；
  - C-deg、C-ds 在叠加 R-c 后仍为 0；
  - 可选：一个“缓存上一次调用 kwargs”的错误候选仍为 0。
- **可能的分歧**：如果有人认为“是否带默认值”属于 P5，即任务目标层面的两种读法，那么它超出 R-b 模板，转“待用户决定”；我的判断是它不属于目标层面的分歧。

### 不建议的修订

- 5 个死键不必本轮做 R-a。可选做法是把测试函数和 expected 键一起删；删掉只能消除“改测试辅助导致键翻转”的风险，不会增加保护。
- 不需要 R-f。

## 10. 开发需求与交付

**评分侧（实测）**：Python 3.7.9，pytest 7.4.4，nose 可导入，`datalad` 从 `/testbed/datalad` 导入（账本 `RH2_OBS_IMPORT_PATH`）；网络 deny_all；测试约 2 s。

**解题侧**（依据环境说明与环境卡；本题的真实启动核对我没看到，一律记为 actor 待验）

- `/testbed/.venv/bin/python`，没有 pip 也不能联网。本题不需要安装任何东西，没有构建步骤，也没有资产。
- 复现示例：从 `datalad.interface.tests.test_utils` 导入 `Test_Utils` 即可跑题面示例。
- 公开旧测试：在 pytest 下跑 `datalad/interface/tests/test_utils.py`，5 个装饰器测试会报 `fixture 'path' not found` ERROR（静态推断，与本题无关，属于恒失败的公开测试）；公开版的 `test_result_filter` 在 base 上就能通过。所以解题者需要自己写复现，或用 `-k` 收窄。
- HOME 没有 git 身份：本题用不到。

**交付**：gold 只改一个 `.py` 文件；R2E 按文件字节差异导出，没有问题。候选可以改测试辅助 `datalad/tests/utils.py`，这可能翻转死键；但公开提示禁止改测试文件，所以只登记，不算题目缺陷。

## 11. 题目关系

- **两份机械扫描**：没有任何涉及 `16c1ffc3` 的 pair。扫描只是下限。本题的新增测试是加在已有测试函数里的，按函数名比对的 test 扫描看不出；上游又重构了修复，逐行比对的 gold 扫描也会漏。
- **人工核对后的 X1**（上游版本晚于本题的 0.5.1）：
  - `datalad__58ba5165`（0.17.9）的公开初态含本题修复的重构版：
    - `datalad/interface/utils.py:233-240` `get_result_filter`；
    - `:371-391` `allkwargs`；
    - `:469,475` 与 `:749-762` `keep_result(…, **allkwargs)`。

    同一初态还含改写后的测试：`datalad/interface/tests/test_utils.py:330-338`。
  - `datalad__19f5b450`（1.1.3）同样含重构版修复，测试在 `:332-340`。
  - 影响：训练时控制重复采样；留出按 D3 以仓库划分，同仓都在一侧。修订 R-b 的依据也来自这里。
- **反向线索（只读了对方公开包，需在对方题卡核对）**：`datalad__9ba5de09`（0.4.1）要求 “eval_results 装饰后返回结果列表而不是 FunctionWrapper”。本题 base 的 `utils.py:1063-1082` 已具备这一行为（重构后），可能构成对方答案出现在本题初态的关系。
- **与 `6b6fa389` 的关系**：领域不同，版本 0.2，无关。

## 12. 用途（v1 §2）与探针就绪差距

**用途四项**

- `problem_localization`：**yes**。
- `capability_comparison`：**conditional**，还差三项：
  1. 本题在本批有效条件下的 actor 开发核对证据（我未见 devcheck）；
  2. T1 争议须单列，或先完成 R-b，因为 C-bind 这类合理解在当前材料上预计判 0；
  3. 今晚机器的 `budget1200` 链路条件要写进批次记录（E3）。
- `training_candidate`：**no**（当前材料）。有未处理的 S1（T2c），T2b 待确认；R-c（必要时加 R-b）验收并经 Codex 复核后重评。
- `heldout_candidate`：**no**。S1 未处理；修订后只能作为“标明版本的自建题”；同仓后续题的初态含本题修复（X1）。

**探针就绪差距**：本批 README §3 按规定未读，下面对照 v1 §2 与 §5 列出。

- 已满足：
  - 当前材料下 noop 两次为 0、gold 两次为 1，镜像 ID 相同，材料摘要一致；
  - 目标键的初态失败与题面一致；
  - 期望 FAILED 键已按来源解释；
  - 核心要求→断言的映射见 §4。
- 未满足：
  1. C-deg 的正式评分（第 3 步），由协调者补。
  2. R-c 的修订与验收，由协调者补，Codex 复核。
  3. C-bind 实跑，以及 R-b 的决定与验收，由协调者补，Codex 复核；若按 P5 处理则交用户。
  4. 本题 actor 开发核对（复现示例、公开命令），由协调者补。
  5. `budget1200` 链路问题，由 A 线处理。
  6. X1 登记，以及对 9ba5de09 的反向核对，由协调者或该题负责人补。

## 13. 未知项与最值得先做的下一步

**未知**

- C-deg、C-bind、C-ds 的实际得分：目前都是静态预测。
- 解题侧能否导入 `Test_Utils` 并跑通示例：actor 待验。
- 镜像里是否有 git-annex：只影响死键，与评分无关。
- 今晚重建镜像与 09-23 镜像是否等价：未读新账本。

**唯一优先下一步**：在当前材料上用正式评分实跑 C-deg（`datalad/interface/utils.py:1030` 改一行）。得 1 即确认 S1（T2b），并与 T2c 合并进同一轮 R-c；同一批次顺带跑 C-bind，以决定是否一并做 R-b。
