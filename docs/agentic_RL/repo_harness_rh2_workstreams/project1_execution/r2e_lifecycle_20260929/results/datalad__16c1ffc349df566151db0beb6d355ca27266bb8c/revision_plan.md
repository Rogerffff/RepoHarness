# datalad 16c1ffc3：R-c + R-b 同一版本修订方案，与 R-b 的 P5 决定包

2026-09-29 约 08:20（+08，本机时钟）· 修订执行者（Claude，单题闭环试行；统一标准 v1 §5 模板内由 Claude 执行、Codex 复核）。

**状态**
- **修订版已试跑，8 个候选全部与预期一致**（试跑工具，不是正式评分）。修订版把 `card.md` 附录 B.1（R-c，新增两个测试）、B.2（R-b，放宽 `sadfilter`）、B.3（期望加两个键）放在同一个版本里。gold、C1、C2 得 1；noop、D、N、F、C-ign 得 0，且都只在预期的键上失败。
- **两项必须同批，已有执行证据**：只上 R-c 时，C2 仍为 0，误拒没有纠正；只上 R-b 时，F 得 1，出现新漏洞；两项同批时 C2 为 1、F 为 0（§5.4）。
- **需要一次判断：R-b 是否在预授权模板内。** R-b 放宽的是"调用没给的参数不得出现在 kwargs 里"。我核查后认为，严格与放宽两种读法都有公开依据，但都偏弱。按 v1 §3 P5 和 Codex 对 f5eb 的判法，我不能断定 R-b 属于预授权模板，因此写成决定包（§7），交 Codex 判断：判为模板内，就按 `revision_draft.json` 落地；判为 P5，就交用户选，执行者建议选 A，即本修订版。
- **R-b 未获批时的默认**：只落 R-c，即 `revision_draft_rc_only.json`（B.1 + B.3）。已试跑：gold 1、noop 0、C2 0、F 0。
- 不需要环境修复。本机正式评分仍须带 1200 s 放宽包装，这是链路条件，不是题目问题（§6 第 5 条）。

路径约定（相对仓库根；`trials/`、`cands/`、`revision_draft*.json` 相对本目录）：
- `PUB` = `runs/r2e_static_prep_20260924/v3/public/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/`，`W` = `PUB/worktree`，即解题者看到的 `/testbed`。
- `PRIV` = `runs/r2e_static_prep_20260924/v3/private/datalad__16c1ffc349df566151db0beb6d355ca27266bb8c/`。
  - `HT` = `PRIV/hidden_tests/test_1.py`，父版本，434 行；
  - `HT'` = 修订版（R-c + R-b），490 行；
  - `HT_rc` = 只上 R-c 的版本，488 行。
- `INV` = `runs/r2e_lifecycle_20260929/inv/datalad_16c1/`，协调者的正式评分与私有行为对照。
- 键名简写：`RF` = `test_result_filter`（原目标键）；`GK` = `test_result_filter_gets_call_kwargs`；`PC` = `test_result_filter_plain_callables_with_call_kwargs`。

## 1. 模板与要纠正的误判

| 改动 | 模板 | 要纠正的问题 | 触发反例（当前材料） | 出处 |
| --- | --- | --- | --- | --- |
| B.1 第一个测试 → `GK` | R-c | T2c：唯一正向断言 `HT:426-429` 与题面示例同形（同一命令、同一 `4`、同一 `dataset='awesome'`，只查键在不在）。T2b：断言写在过滤器回调里，外层不看结果；第 3 步退化候选 D（`except ValueError` 改成 `except Exception`）吞掉断言后得 1 | D 正式评分 1.0（`INV/ledger_D_budget1200.jsonl:1`） | `card.md` "问题与证据"；`review.md` §3.1 |
| B.1 第二个测试 → `PC` | R-c | v1 §4 第 4 步：N（无条件 `result_filter(res, **_kwargs)`）得 1，但调用带关键字参数时，Constraint 与单参过滤器报 `TypeError` | N 正式评分 1.0（`INV/ledger_N_budget1200.jsonl:1`）；行为对照 `INV/pcheck_filters_backcompat_N.json` | 同上 |
| B.2 → `RF` 里的 `sadfilter` | R-b（是否在模板内待判，§7） | T1：C2 只因 `assert_not_in('dataset', kwargs)` 得 0。C2 把位置参数按名给出并补上默认值 | C2 正式评分 0.0（7/8，`INV/ledger_C2_budget1200.jsonl:1`） | `review.md` §2 第 4 行、§3.2 |
| B.3 | 随 B.1 | R2E 的键集必须严格相等，`GK`、`PC` 要同时进期望 | — | `review.md` §3.4 |

**不在本轮：**
- R-a：5 个死键照旧登记；
- 可选加固"过滤器抛出的非 `ValueError` 异常要传出"：协调者决定不并入，按 T3 登记（§8）。

## 2. 公开依据

### 2.1 `GK`：同一核心要求的非示例实例

- **题面是一般表述。**
  - 标题："`result_filter` does not receive `kwargs`"（`PUB/user_prompt.txt:5`）；
  - 描述："a custom `result_filter` that expects additional keyword arguments from the API call, the filter does not receive these `kwargs`"（`:8`）；
  - 示例（`:12-17`）只是其中一个实例。
- **新测试与示例有四处不同，各有依据：**
  1. **换一个关键字参数，并核对取值。** 以关键字给出 `number=4`，要求过滤器看到 `number == 4`、`dataset == 'awesome'`。依据：`eval_results` 不做参数约束转换，约束只在命令行解析时充当 argparse 的 `type`（`W/datalad/interface/base.py:279-280`）；同一函数里的渲染钩子原样收到调用的关键字参数（`W/datalad/interface/utils.py:1048,1050`）。
  2. **generator 模式。** list 与 generator 两种模式共用 `generator_func`（`W/.../utils.py:1063-1064,1082`）。
  3. **Dataset 方法调用。** `datasetmethod` 把 `dataset=self` 与其余参数都转成关键字（`W/datalad/distribution/dataset.py:441-451`），过滤器应看到 `dataset is ds`、`number == 4`。
  4. **过滤器的去留决定照常生效。** 结果应为 `[1, 3]`。依据是参数文档：返回假值的结果不返回（`W/.../utils.py:863-868`）。
- **断言放在测试函数体里。** 取值与结果都在外层断言，所以吞掉过滤器异常（D）或忽略过滤器返回值（C-ign）都会被发现。
- **对合理读法中立。**
  - 只用 `.get('number')`、`.get('dataset')` 取值，不断言调用次数，也不断言 kwargs 的完整内容；
  - `number` 以关键字给出；Dataset 方法路径下，`datasetmethod` 会把参数转成关键字；
  - 所以只传调用方写出的关键字参数（gold、C1），与连位置参数、默认值一起传（C2），都能通过；
  - 按位置传 `dataset` 时是否转发（A2），不测。

### 2.2 `PC`：调用带关键字参数时，旧式过滤器照常工作（回归断言）

- **参数文档**：每条结果 "is passed to this callable"（`W/.../utils.py:863-868`），即单参接口。
- **库内的 Constraint 型过滤器**：
  - `Create` 的类级默认过滤器（`W/datalad/distribution/create.py:89-91`），经 `W/.../utils.py:979-983` 成为每次 `create` 的默认值；
  - 命令行 `--report-status/--report-type` 组合出的过滤器（`W/datalad/interface/base.py:325-336`），随后 `:338` 把全部参数按关键字传入；
  - `Constraint.__call__(self, value)` 只收一个参数（`W/datalad/support/constraints.py:54,290,420`）。
- **单参函数**：
  - `is_ok_dataset(r)`（`W/datalad/interface/results.py:66-67`），公开测试 `W/datalad/interface/tests/test_save.py:119` 以 `ds.save(..., result_filter=is_ok_dataset)` 使用它；
  - `W/datalad/interface/tests/test_clean.py:39-40` 在 `clean(dataset=ds, ...)` 里用单参 lambda。
- **base 本来就满足这一点**：noop 在 `PC` 上 PASSED。现有活键里没有"调用带关键字参数"的情形，本可覆盖它的 `test_dirty` 等都是死键（T5）。
- **覆盖面**：三种过滤器（`EnsureKeyChoice`、`&` 组合、单参 lambda）× 两条调用路径（直接调用带 `dataset='awesome'`、Dataset 方法）。没看过隐藏测试的公开读者，也把同一组检查写成了公开命令 `filters_backcompat`（`commands.json` 第 3 条）。

### 2.3 R-b：放宽 `sadfilter`

- 改动：`assert_not_in('dataset', kwargs)` → `assert_equal(kwargs.get('dataset'), None)`。
- 含义：调用没给 dataset 时，过滤器不能拿到一个 dataset 值；键可以缺席，也可以是 `None`。
- 两边的公开依据与判断见 §7。

## 3. 具体改动

- **目标文件**：`r2e_tests/test_1.py`，即唯一的隐藏测试文件 `HT`。
- **草案条目**：一条 `hidden_test_text_replace`，含两处 edit。按正式摄入的规则依次替换，每处 `old` 在当时的文本里恰好出现一次：
  1. R-b：`old` = `HT:431-432`（`def sadfilter` 与 `assert_not_in` 两行），`new` 换成放宽后的断言，外加两行注释；
  2. R-c：`old` = 文件最后一行 `HT:434`（`Test_Utils().__call__(4, result_filter=sadfilter)`），`new` = 原行 + 两个新测试函数。
- **修订后位置**：`HT'` 共 490 行。R-b 在 `HT':431-436`，`GK` 在 `:439-470`，`PC` 在 `:473-490`。精确的 old / new 见 `revision_draft.json`。
- **来源与核对**：
  - 两处改动逐字取自 `card.md` 附录 B.1、B.2，与 `analysis_before_history.md` 附录 B 逐字相同；
  - 草案由脚本从补丁生成，没有手抄；
  - 在仓库外副本上，B.1、B.2、B.3 单独、合并、换顺序做 `git apply --check`，都通过；
  - 打补丁得到的文件，与按草案重放得到的文件逐字节相同；试跑工具和 `rh2/src/repoharness2/envpack/ingest_r2e_subset.py` 的 `_apply_edits` 两种重放规则都核过；
  - 修订后的文件通过 `py_compile`。

```python
    def sadfilter(res, **kwargs):
        # no dataset was given in the call: the filter must not be handed
        # one (the argument may be absent or None)
        assert_equal(kwargs.get('dataset'), None)
        return True
    Test_Utils().__call__(4, result_filter=sadfilter)


def test_result_filter_gets_call_kwargs():
    # a filter that accepts **kwargs gets the keyword arguments of the API
    # call -- not only `dataset` -- also in generator mode and when the
    # command is called as a Dataset method (all arguments become keyword
    # arguments); the filter's decision is honored
    seen = []

    def kwfilter(res, **kwargs):
        seen.append(kwargs)
        return res['somekey'] in (1, 3)

    for rtype in ('list', 'generator'):
        del seen[:]
        assert_equal(
            [r['somekey'] for r in Test_Utils().__call__(
                number=4, dataset='awesome', return_type=rtype,
                result_filter=kwfilter)],
            [1, 3])
        ok_(seen)
        for kw in seen:
            assert_equal(kw.get('number'), 4)
            assert_equal(kw.get('dataset'), 'awesome')

    del seen[:]
    ds = Dataset('/does/not/matter')
    assert_equal(
        [r['somekey'] for r in ds.fake_command(4, result_filter=kwfilter)],
        [1, 3])
    ok_(seen)
    for kw in seen:
        assert_equal(kw.get('number'), 4)
        ok_(kw.get('dataset') is ds)


def test_result_filter_plain_callables_with_call_kwargs():
    # filters that do not accept **kwargs -- Constraints (as used for the
    # class-level default filter of `create` and for the --report-status /
    # --report-type command line options) and plain one-argument callables
    # (e.g. datalad.interface.results.is_ok_dataset) -- keep working when
    # the API call has keyword arguments
    ds = Dataset('/does/not/matter')
    for filt in (
            EnsureKeyChoice('somekey', (0, 2)),
            EnsureKeyChoice('status', ('ok',)) & EnsureKeyChoice('somekey', (0, 2)),
            lambda x: x['somekey'] in (0, 2)):
        assert_equal(
            [r['somekey'] for r in Test_Utils().__call__(
                4, dataset='awesome', result_filter=filt)],
            [0, 2])
        assert_equal(
            [r['somekey'] for r in ds.fake_command(4, result_filter=filt)],
            [0, 2])
```

**设计说明**
- **只用文件里已导入的名字**：`assert_equal`（来自 nose.tools）、`ok_`、`Dataset`、`EnsureKeyChoice`（`HT:17,25,27,34`）。
- **不受死键问题影响**：不带 `@with_tempfile` 一类装饰器，不会与 conftest 的 `path` fixture 冲突，也不需要 git-annex。
- **确定性**：都是纯内存调用，不涉及时间、随机数或网络。
- **刻意不测**：
  - 调用次数，以及 kwargs 的完整内容；
  - 按位置传 `dataset`（A2）；
  - 只声明具名 `dataset=None`、不声明 `**kwargs` 的过滤器（T3）；
  - 拿不到签名的可调用对象（G1）；
  - 过滤器抛出非 `ValueError` 异常时是否传出（D′，§8）。

## 4. 期望映射逐键变化

- **原 8 键不变**：`test_interface_prep`、`test_eval_results_plus_build_doc`、`RF` 为 PASSED；5 个死键为 FAILED。
- **新增 2 键**：`GK: PASSED`、`PC: PASSED`。合计 10 键，完整映射见 `revision_draft.json` 的 `expected_after`。
- **正式修订单的写法**：用 `expected_file_replace`，`added` 为这两键，`changed`、`removed` 为空（草案的 `formal_expected_change`）。修订后的文件可以直接用 B.3 补丁的结果：保持原格式，末尾没有换行，sha256 `96162fea…`。
- **期望从哪里来**：两键的 PASSED 来自 §2 的公开语义；`RF` 在 R-b 后仍为 PASSED。gold 通过是验收结果，不是依据，没有复制 gold 的输出作期望。
- **与已批准的期望修订不冲突**（按任务要求先核）：
  - `PRIV/revisions.json` 为 `[]`（sha256 `37517e5f…`）；
  - 当前正式材料 `docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/ingest/grading_bundles_r2e_v0.jsonl:11` 的 `material_revisions` 为空，摘要与下表父版本一致；
  - pins v10 所指的 `material_revisions_v9.json` 与 v1–v8 都没有本题条目；
  - 所以 `review.md` §3.4 的判断成立：本修订是本题第一个材料修订，不与任何已批准修订冲突。
- **版本记录**（全长哈希见 `revision_draft.json`）：

  | 文件 | sha256 |
  | --- | --- |
  | 父版本 `test_1.py`（`HT`，434 行，git blob `b961d0d`） | `92ef9efa…` |
  | 父版本 `expected_output.json`（8 键，git blob `325e99f`） | `97ecb569…` |
  | 父版本隐藏测试树 | `a5ddfbe5…`，`material_revisions` 为空 |
  | 修订版 `test_1.py`（`HT'`，490 行） | `73f08e74…` |
  | 只上 R-c 的 `test_1.py`（`HT_rc`，488 行） | `46c436ea…` |
  | 修订后 `expected_output.json`（B.3 补丁结果，10 键） | `96162fea…` |
  | 试跑用 `draft_full.json` / `draft_rc_only.json` / `draft_rb_only.json` | `fcee2689…` / `10e8723d…` / `e8cbea7d…` |
  | 试跑用 `expected_after.json`（10 键） | `bc1633e9…` |

## 5. 验收计划与试跑结果

### 5.1 试跑条件

- **工具**：`rh2/experiments/r2e_lifecycle_20260929/trial_grade.py`（远端 `/work/code/rh2`），只作试跑。
  - 与正式评分的差别见文件头：不做基线重建比对；不核隐藏测试树与入口摘要；候选补丁以 root 应用；权限布置简化为把整个 `/testbed` 交给评分用户。
  - 不经控制面保护，所以不需要放宽时限。
- **镜像**：派生镜像 `sha256:3874afbac47a…`，配方 `r2e_derive_v1+sysconfig_v1`。与 `INV` 四份正式账本和 `runs/r2e_lifecycle_20260929/budget_v5/` 两份账本的 `image_id_actual` 相同。
- **评分入口**：以 uid 54322 跑来源入口 `bash run_tests.sh`，用正式解析器逐键比对。
  - 有补丁的每次都是 `RH2_APPLY_RC=0`；带草案的每次都报 `RH2_TRIAL_EDITS_APPLIED=1`；
  - 修订版每次 10 键全部解析，没有 missing / extra。
- **补丁核对**：
  - 所有候选补丁都在仓库外的 base 副本上 `git apply --check -v` 通过。副本里 `datalad/interface/utils.py` 的 blob 是 `7c35619`，与各补丁的 index 行一致；
  - D、N、C1、C2 与协调者正式评分所用补丁的 sha256 相同；
  - 上传到远端的 11 个文件取回后与本地逐字节相同，试跑输入另存于 `trials/inputs/`。
- **次数与耗时**：
  - 共 15 次：当前材料 2 次，修订版 8 次，只上 R-c 4 次，只上 R-b 1 次；每个候选在每个版本上跑 1 次；
  - 同一时间最多 2 次；
  - 单次墙钟 172–447 s，主要花在容器里的 `chown -R /testbed`，随机器负载变化；测试段 3.1–6.6 s。
- **日志的局限**：
  - 结果文件只保留日志最后 8000 字符。候选通过的测试多时，PASSES 段会把失败详情挤出去；
  - 修订版上的 D、F、C-ign 只看得到"`GK` FAILED、`AssertionError`"，具体是哪条断言由源码推出（见 §5.3 判读）；
  - 有两处执行旁证：修订版 noop 与只上 R-c 的 F，日志尾部保留了同一条断言的失败详情（`None != 4`，位于 `HT':459` / `HT_rc:457`）。

### 5.2 当前材料上的对照（不进 acceptance）

| 候选 | 结果 | 出处 |
| --- | --- | --- |
| noop | 0：只差 `RF`，失败在 greatfilter（`HT:427`，`'dataset' not found in {}`） | `trials/env_noop_current.json`；正式评分 `runs/r2e_lifecycle_20260929/budget_v5/ledger_noop.jsonl:1` |
| gold | 1：8/8 | `trials/env_gold_current.json`；`budget_v5/ledger_gold.jsonl:1` |
| D、N、C1 | 都是 1.0（8/8） | `INV/ledger_{D,N,C1}_budget1200.jsonl:1`（协调者正式评分，1200 s 放宽时限，§6 第 5 条） |
| C2 | 0.0（7/8）：只差 `RF`，失败在 `sadfilter` | `INV/ledger_C2_budget1200.jsonl:1` |
| F、C-ign | 未跑。静态判断：F 为 0，被严格的 `sadfilter` 挡住（§5.4 只上 R-c 的 F 印证了这一点）；C-ign 为 1，因为 greatfilter、sadfilter 恒返回 True，没有断言检查去留决定 | — |

### 5.3 修订版（R-c + R-b）下的验收

结果文件为 `trials/rev_<候选>.json`。"当前材料"一列取 §5.2。

| 候选 | 补丁 | 角色 | 应得 | 应不符的键与位置 | 试跑结果 | 当前材料 |
| --- | --- | --- | --- | --- | --- | --- |
| gold | `PRIV/gold.patch` | 正对照 | 1 | — | 1，10/10 | 1 |
| noop | 无 | 空补丁 | 0 | `RF`（greatfilter，`HT':427`）；`GK`（`HT':459`，`None != 4`） | 0，恰好这 2 键；`GK` 的位置与消息见日志尾部，`RF` 只剩摘要 `'dataset' no…` | 0 |
| C1 | `cands/datalad_16c1_C1.patch` | 替代正对照（读法 S，签名拿不到时回退旧调用） | 1 | — | 1，10/10 | 1（正式） |
| C2 | `cands/datalad_16c1_C2.patch` | 合理替代解（读法 D），R-b 的触发反例 | 1 | — | **1**，10/10 | **0**（正式） |
| D | `cands/datalad_16c1_D.patch` | 第 3 步退化候选 | 0 | `GK`（`HT':459`） | 0，只有 `GK`（`AssertionError`） | **1**（正式） |
| N | `cands/datalad_16c1_N.patch` | 第 4 步错误修法 | 0 | `PC`（`TypeError`） | 0，只有 `PC`：`TypeError: __call__() got an unexpected keyword argument 'dataset'`，位于 `datalad/interface/utils.py:1030` | **1**（正式） |
| F | `cands/datalad_16c1_F.patch` | 故意写错：固定传 `dataset=None` | 0 | `GK`（`HT':459`） | 0，只有 `GK`（`AssertionError`） | 0（静态） |
| C-ign（可选） | `cands/datalad_16c1_Cign.patch`（本轮新写） | 调用接受 kwargs 的过滤器，但忽略其去留决定 | 0 | `GK`（`HT':452-456`，得到 `[0, 1, 2, 3]`） | 0，只有 `GK`（`AssertionError`） | 1（静态） |

**判读**
- **正对照 1、noop 0**：成立。gold 本身满足公开要求：
  - 只给声明了 `**kwargs` 的过滤器传调用的关键字参数，旧式过滤器照旧；
  - 行为对照 `INV/pcheck_filters_backcompat_gold.json` 打印 `BACKCOMPAT_OK`，`INV/pcheck_repro_issue_example_gold.json` 打印 `RESULT [0, 1, 2, 3]`。
- **误判已纠正**：
  - D、N 在当前材料正式评分为 1，修订版上都是 0，而且各自只在针对它的键上失败；
  - C2 由 0 变 1（R-b 的作用）。
- **D、F、C-ign 失败在哪条断言**：日志尾部被截断（§5.1），由源码推出，而且都是该候选在 `GK` 里唯一可能失败的断言：
  - D、F 下，`kwfilter` 正常返回去留决定，`[1, 3]` 与 `ok_(seen)` 都成立，唯一可能失败的是 `HT':459`：D 下 `kw` 为 `{}`，F 下 `kw` 为 `{'dataset': None}`；
  - C-ign 下，kwargs 正确送达，但结果是全部 4 条，唯一可能失败的是 `HT':452-456`；
  - D 的日志里另有 RF 的 greatfilter 断言被吞的 debug 行（`'dataset' not found in {}`），说明 D 在 `RF` 上"通过"靠的是吞掉异常。
- **已知相关的错误候选仍为 0**：D、N、F、C-ign 都是 0。C-ign 是唯一专门打到"去留决定"断言的候选，它的 0 说明这条断言确实生效。
- **没有误拒**：C1、C2 都是 1。两者都通过 `PC`，把复核 §2 第 4 行"C2 兼容旧式过滤器只有静态推断"变成了执行证据。
- **旧键不受影响**：各候选在原 8 键上的结果与当前材料相同，唯一例外是 C2 的 `RF` 由 FAILED 变 PASSED，这正是 R-b 的作用；5 个死键在所有 15 次试跑中都是同一个 `TypeError`。

### 5.4 只上 R-c、只上 R-b 的对照：两项必须同批

| 版本 | 候选 | 应得 | 应不符的键 | 试跑结果（结果文件） |
| --- | --- | --- | --- | --- |
| 只上 R-c（B.1 + B.3，`HT_rc`） | gold | 1 | — | 1，10/10（`trials/rc_gold.json`） |
| | noop | 0 | `RF`、`GK` | 0，恰好这 2 键；`GK` 在 `HT_rc:457`，`None != 4`（`trials/rc_noop.json`） |
| | C2 | 0 | `RF`（严格 `sadfilter`，`HT_rc:432`） | **0**，只有 `RF`：`AssertionError: 'dataset' un…`（摘要截断，即 `'dataset' unexpectedly found`）；`GK`、`PC` 通过（`trials/rc_C2.json`） |
| | F | 0 | `RF`、`GK` | 0，恰好这 2 键；`GK` 在 `HT_rc:457`，`None != 4`（`trials/rc_F.json`） |
| 只上 R-b（B.2，期望仍为原 8 键） | F | 1（新漏洞） | — | **1**，8/8（`trials/rb_F.json`） |
| R-c + R-b（§5.3） | C2 / F | 1 / 0 | — / `GK` | 1 / 0 |

**判读**
- **只上 R-c**：C2 仍为 0。R-c 不纠正 T1，要纠正必须有 R-b。
- **只上 R-b**：F 得 1。放宽后的 `sadfilter` 接受 `None`，greatfilter 只查键在不在，于是"与调用无关、固定传 `dataset=None`"的错误实现拿到满分。所以 R-b 不能单独上。
- **同批**：C2 为 1、F 为 0。F 失败在 `GK` 的取值断言上。
- **只上 B.1、不上 B.3**：没有试跑。按 R2E 键集严格相等的规则，观测会多出 `GK`、`PC` 两个期望外的键，gold 也判 0（`review.md` §3.4）。
- **只上 R-c 的版本就是默认版本**（`revision_draft_rc_only.json`），在 R-b 撤回或待决时使用。它的 gold、noop、C2、F 已试跑。D、N、C1、C-ign 没有另跑：它们在 `sadfilter` 那次调用里收到的都是 `{}`（调用没给 dataset，也没有其它关键字参数），严格写法与放宽写法结果相同。

### 5.5 对照 v1 §5 的验收条目

- **正对照为 1、noop 为 0**：满足。修订版与只上 R-c 的版本都试跑过。
- **本次要纠正的误判已纠正**：D、N 由 1 变 0；在 A 版上，C2 由 0 变 1。
- **已知相关的错误候选仍为 0**：D、N、F、C-ign。
- **公开核心要求有直接断言**：见 §8。
- **保存新版本、父版本、理由和触发反例**：见 §1、§3、§4 与 `revision_draft.json`；触发反例的正式账本在 `INV/`。
- **Codex 复核**：待做，同时判断 R-b 是否在模板内（§7）。

## 6. 复核（`review.md`）修改要求的落实

1. **第 3 步的退化候选认 D，N 归第 4 步。** 本文件与两份草案的 `role` 都按此标注。修订版试跑中 D 为 0，只在 `GK` 失败。
2. **F 改为必跑。**
   - 用脚本从 `card.md` 附录 B.4 原样取出，没有经过 Write 工具，存为 `cands/datalad_16c1_F.patch`（sha256 `20b0d5ea…`）；
   - 在仓库外 base 副本上 `git apply --check -v` 通过；
   - 三个版本都跑了：修订版 0，只上 R-c 0，只上 R-b 1。
3. **B.1 与 B.3 一起上，B.2 只与二者进同一版本。**
   - `revision_draft.json` 是一个版本：一条隐藏测试修订含两处 edit，加 10 键期望；
   - 不留"先 R-b 后 R-c"的中间版本；
   - §5.4 给出两项必须同批的执行证据；
   - 若 R-b 撤回，默认版本是 `revision_draft_rc_only.json`（B.1 + B.3）。
4. **记录更正：配方身份。**
   - **哪里写错了**：`screening_record.json` 的 `recipe_ref.derived_image` 写的是"r2e_derive_v1，新机器重建……私有行为对照记录的配方标签为 r2e_derive_v1+sysconfig_v1"。
   - **实际情况**：新机器上所有评分用的派生镜像配方都是 `r2e_derive_v1+sysconfig_v1`，即镜像 `sha256:3874afbac47a…`、tag `rh2-r2e-derived/datalad:16c1ffc349df-r2e_derive_v1s`、`recipe_sha256` `e2e17bf1…`。以下各处都是这个配方：
     - 正式评分账本的 `overlay`：`env_verify/ledger_l2_{noop,gold}.jsonl:2`、`budget_v5/ledger_{noop,gold}.jsonl:1`、`INV/ledger_{D,N,C1,C2}_budget1200.jsonl:1`；
     - devcheck `orig/attempt.json` 的 `overlay`；
     - 私有行为对照 `INV/pcheck_*.json`；
     - 本次 15 次试跑。
   - **旧机器**（09-23、09-24）用的是 `r2e_derive_v1`：镜像 `c2578ef0…`，`recipe_sha256` `0da821a1…`。
   - **`sysconfig_v1` 是什么**：定义在 `rh2/scripts/r2e_derive/sysconfig_v1.sh`，由 `rh2/scripts/build_r2e_derived.py --sysconfig-fix` 启用（本批 README §8，09-29 凌晨条）。它只把 `/opt/py/<PYDIR>` 里文本文件中的旧 `/root` 前缀改到新位置，并重编 `_sysconfigdata`；不动 `/testbed`、`.venv` 与 `/root`。
   - **对本题的影响**：datalad 是纯 Python，这一步不影响本题；新旧两种配方下，noop、gold 的逐键结果相同。
   - 本文件不改原件，请协调者更正 `screening_record.json` 与题卡。
5. **链路条件的写法。** 用下面这段替换 `card.md` 与 `screening_record.json` 里"本机评分的控制面保护时限要放宽到 1200 s"一句。它是本机、本批的评分链路条件，不写成"本题需要 1200 s"。

   > **评分链路条件（E3，本机本批，不是题目缺陷）**
   > - **是哪个时限**：评分前有两步，基线重建 census 与控制面保护（`chown -R <评分用户> /testbed`，`.venv` 在其中）。两步共用 `GradingEnvSpec.env_reset_timeout_seconds`，缺省 300 s，CLI 与环境变量都调不了。
   > - **本机实测**：
   >   - 可信 setup 两路并发时，`budget_v5` 两行为 152.6–152.8 s，`INV` 四行为 210.2–221.8 s；
   >   - `env_verify` 那一轮 300.5 s 超时，记为 `failed_to_grade / infra_failure: grading_control_surface_protect_timeout_after_300s`，没有记成 0 分。
   > - **怎么放宽的**：本题在新机器上的正式评分，都经实验包装 `rh2/experiments/r2e_lifecycle_20260929/replay_grade_budget.py --env-reset-timeout 1200` 运行。它在运行时替换 `build_grading_spec_from_host_view`，只把这一个时限抬到 `max(1200, 缺省值)`。
   > - **值记在哪里**：
   >   - 只记在每次运行的日志里，即包装脚本打印的第一行 `{"replay_grade_budget": {"env_reset_timeout_seconds": 1200.0}}`；
   >   - 具体位置：`runs/r2e_lifecycle_20260929/budget_v5/{noop,gold}.log:1`；`INV/run_a.log:1`（D）与 `:6`（N）；`INV/run_b.log:1`（C2）与 `:6`（C1）；
   >   - 账本行的 `budgets` 只有 `candidate_stage_seconds`、`cleanup_seconds`、`grading_deadline_seconds`、`image_pull_seconds` 四项，没有它；
   >   - 引用这些账本时，要同时引用对应的日志行。
   > - **判分语义不变**：
   >   - 与 09-23 的账本相同：`grader_version`、`scripts_digest`、`baseline_policy_version`、runner 摘要（`RH2_OBS_RUNNER_DIGEST`）、隐藏测试树与期望摘要；
   >   - 评分用户、CPU、内存、网络、pids、shm、tmpfs 这些 policy 字段也相同；
   >   - 但 `grader_profile_digest` 不同：09-23 为 `1bb8e0cf…`，现在为 `3ec1bfa8…`。可能来自 09-23 之后的沙箱改动（例如 `83760b15` 把 tmpfs 由 noexec 改为 exec），本文没有逐项核对。`review.md` §5 写的"评分用户与资源 profile 相同"要加这一限定；
   >   - noop、gold 的逐键结果与 09-23、09-24 相同。
   > - **谁来处理**：进探针或训练前，由 A 线二选一：把这一时限做成正式可配置并写进账本；或者降低 `chown` 的开销。在此之前，本题在本机的正式评分须带同一包装，并单独记账。
   > - **解题侧**：从容器启动到 init 约 434 s（devcheck `orig/attempt.json` 的 stages，未拆分），会影响回合预算的估计，同样交 A 线。
6. **事后审计要读输出行，不能读外层退出码。**
   - 修订落地后，D 型、N 型已由 `GK`、`PC` 挡住。审计只在"用现材料进探针"或查 D′ 时才需要。
   - **D 型**：跑公开命令 `repro_issue_example`，以输出行 `RESULT [0, 1, 2, 3]` 为通过。D 下这条命令的退出码是 0，只打印 `RESULT []`（`INV/pcheck_repro_issue_example_D.json`）。
   - **N 型**：跑公开命令 `filters_backcompat`，以输出行 `BACKCOMPAT_OK` 为通过。私有行为对照 JSON 的顶层 `rc` 在 N 下也是 0，真正的退出码在 stdout 的 `RH2_CMD_RC=1`（`INV/pcheck_filters_backcompat_N.json`）。
   - 这与 v1 §8 一致：打印型脚本要写明读哪一行、什么算失败。
7. **可选加固不并入。** 协调者决定本轮不加"过滤器的非 `ValueError` 异常要传出"这条断言。
   - D 已由 `GK` 挡住，修订版试跑为 0；
   - "正确转发，但把异常一律吞掉"的 D′ 在修订版上静态判断仍得 1，按 T3 登记（§8）。
8. **R-b 是否属于 P5**：见 §7。

## 7. R-b 是否属于 P5：公开依据与决定包

### 7.1 争议的范围

- **争议只有一点**：调用时没给的参数，过滤器的 kwargs 里是缺席，还是以默认值（`dataset=None`）出现。
- **两种读法一致的要求**，修订版对两种读法同样严格：
  - 给出的参数原样送达（`GK`）；
  - 旧式过滤器照常工作（`PC`）；
  - 没给 dataset 时，过滤器不能收到一个 dataset 值（`sadfilter`，严格与放宽两种写法都拒绝非 `None` 值）。
- **两种读法的代表**：
  - 读法 S（严格：没给就不出现）：gold、C1，只传调用方写出的关键字参数；
  - 读法 D（含默认值）：C2，位置参数按名给出并补上默认值。
- **R-b 的效果**：放宽后同时接受 S 与 D；不放宽只接受 S。

### 7.2 两边的公开依据（只算解题者能看到的材料）

**读法 S（现 `sadfilter` 的 `assert_not_in`）的依据**
1. **同一函数里的代码先例。**
   - `eval_results` 先把 eval 参数从调用的 kwargs 里取走（`W/datalad/interface/utils.py:979-983`），剩下的 `_kwargs` 就是调用方写出的关键字参数（`:986`）；
   - 渲染钩子收的正是这份 `_kwargs`（`:1048`、`:1050`）；
   - 沿用这个先例，`Test_Utils().__call__(4, result_filter=f)` 时过滤器收到 `{}`，gold 就是这样做的。
2. **题面字面。** 描述说的是 "additional keyword arguments from the API call"（`PUB/user_prompt.txt:8`）。按 Python 的说法，一次调用的关键字参数就是调用里写出的那些；没写 `dataset`，它就不在其中。

**强度**：代码先例，不是文档；先例是给渲染器的，不是给过滤器的；题面没有提到"没给"的情形。所以这一要求**有公开依据，但偏弱**。
- 复核初判说它"无公开依据（只有 `_kwargs` 代码先例）"（`reviewer_initial.md:138`），事实部分我同意；
- 但按 Codex 在 f5eb 的标准，"依据弱不等于没有公开依据"（`../../codex_reviews/review_revision_coveragepy_f5eb.md` §3），它不能算作"没有公开依据的实现约束"。

**R-b 放宽后接受的写法（没给时可以是 `None`）的依据**
1. **本仓命令行入口本来就把没给的参数以默认值作为关键字参数传入。**
   - `setup_parser` 给带默认值的 API 参数设 argparse 默认值（`W/datalad/interface/base.py:274-275`）；`call_from_parser` 把全部 API 参数收进 kwargs（`:311`），再 `cls.__call__(**kwargs)`（`:338`）；
   - 所以同一份 `_kwargs`，从命令行调用、没给 `-d` 时是 `{'dataset': None, ...}`，渲染钩子（`W/.../utils.py:1048`）收到的也是它；
   - 也就是说，在 base 的设计里，"没给 dataset"本来就有两种表示：Python API 调用时缺席，命令行调用时是 `None`。写钩子的人不能靠"键不存在"来判断"没给"。
2. **题面的叫法。** 期望行为把它称作 "the `dataset` keyword argument"（`:21`），指的是 `__call__(number, dataset=None)` 里这个带默认值的形参。按这种叫法，"关键字参数"也可以理解为形参连同默认值。这一条弱。

**强度**：命令行事实是间接依据，因为命令行只能组合出 Constraint 型过滤器，它们本来就收不到 kwargs；措辞依据弱。

**不算公开依据**：上游后来的实现与测试。
- 事实：同仓 `58ba5165`、`19f5b450` 的公开初态里，`get_allargs_as_kwargs` 的注释写明 "incl. defaults"（`runs/r2e_static_prep_20260924/v3/public/datalad__58ba5165234cb16de0e8463ee75097362099835f/worktree/datalad/interface/base.py:608-634`），`sadfilter` 改成了 `assert_equal(kwargs.get('dataset', 'bob'), None)`，即要求键存在且为 `None`（同一工作树 `datalad/interface/tests/test_utils.py:335-336`；`19f5b450` 在 `:337-338`）。
- 这些是解题者看不到的未来版本。与 f5eb 决定包的处理一致，本文只把它当作训练池事实（X1）。
- 它也说明，反方向的严格写法"必须带默认值"会拒绝 gold 的读法 S，所以不可选（§7.4）。

### 7.3 判断

- **两种读法都有公开依据，都偏弱。** 按 v1 §3 P5（"两种读法都有依据，就属于任务目标选择"）和 v1 §5 R-b 的边界（"任务目标层面的分歧不在本模板内"），再加上 Codex 对 f5eb 的判法，**我不能断定 R-b 属于预授权模板。**
- **主审与复核的看法**：都判"不是 P5"（`analysis_before_history.md` §8、`review.md` §8）。理由是两种读法都完成了任务目标，差别只在"没给的参数"怎么表示。这一判断有道理，交 Codex 裁定。
- **供 Codex 判断的差异**（与 f5eb 相比）：
  1. **争议性质不同。** f5eb 争的是"多出来的输出"（每文件 summary 多两键），严格一侧有公开旧测试锁定。这里争的是"同一信息的两种表示"（没给 dataset：缺席或 `None`），两种表示在 base 自己的两个入口都会出现；严格一侧只有代码先例。
  2. **反方向的考虑。** 题面示例本身用"键在不在"（`'dataset' in kwargs`）判断是否收到 dataset。用这种写法的过滤器在两种读法下行为不同，所以两种表示对使用者并不完全等价。
- **Codex 的三种可能结论与去向**：

  | Codex 结论 | 依据 | 去向 |
  | --- | --- | --- |
  | 严格要求只是表示方式的细节，没有公开依据可言 | 主审、复核的看法 | R-b 在模板内，按 `revision_draft.json` 落地（选项 A） |
  | 只有读法 S 有公开依据（认为命令行事实不足以支持读法 D） | v1 §3 P5 第一分支："测试采用的读法有公开依据，走 R-f 补一句" | 模板内的路径是选项 B：R-f 加只上 R-c。A 须用户批准 |
  | 两种读法都有公开依据（本文的看法） | v1 §3 P5 第二分支 | 交用户在 A、B、C 中选；未选前按 §7.6 的默认处理 |

### 7.4 选项

| | A. R-b 与 R-c 同一版本（执行者建议） | B. 选读法 S，用 R-f 补一句，只落 R-c | C. 维持读法 S，不改题面，只落 R-c |
| --- | --- | --- | --- |
| 做什么 | `revision_draft.json`：放宽 `sadfilter`，接受缺席或 `None`；加两个新测试 | 题面补一句（草稿见下）；隐藏测试用 `revision_draft_rc_only.json` | 只落 `revision_draft_rc_only.json`；把读法 S 定为本题目标，C2 型得 0 登记为已知风险 |
| C2 | 1 | 0：违反修订后的题面，属于正确拒绝 | 0：有争议地拒绝 |
| F / D / N | 0 / 0 / 0 | 0 / 0 / 0 | 0 / 0 / 0 |
| 前提 | Codex 判为模板内；否则须用户选 A | 题面修订类已实现并经 Codex 复核（`../../codex_reviews/review_code_A_B_20260929.md`）。具体题面还要逐项验收：没看过隐藏测试与 gold 的新公开读者复读，逐行核对没有隐藏细节与答案，Codex 复核，出新版修订单与 pins | 用户明确接受 |
| 验收 | 已试跑（§5.3） | 评分材料同 C；另加新公开读者验收 | 已试跑（§5.4）：gold 1、noop 0、C2 0、F 0；D、N、C1、C-ign 与 A 相同 |
| 额外成本 | 无，草案与试跑已完成 | 一轮新公开读者，外加题面修订的落地与复核 | 无 |

**B 的题面草稿**（未验收，只在选 B 时启用）
- old：`PUB/user_prompt.txt:21`，在公开包 `problem_statement` 里恰好出现一次：
  > The `custom_filter` should receive the `dataset` keyword argument and operate without errors.
- new：在原句后接一句：
  > Only keyword arguments that are actually passed in the API call are forwarded to such a filter; parameters the caller did not pass are not added.
- 逐行核对：
  - 没有隐藏测试的测试名、调用或输入；
  - 没有实现细节，不提 `_kwargs`，也不提签名检查；
  - 依据是同一函数里渲染钩子的 `_kwargs` 先例（`W/.../utils.py:979-983,1048,1050`）。

**不可选**
- **改成上游后来的"必须带默认值"**，即 `kwargs.get('dataset', 'bob')` 为 `None` 的写法：会拒绝 gold 与 C1 的读法 S，而读法 S 有公开依据；它的依据又来自解题者看不到的未来版本。
- **删掉 `sadfilter`**：会放过"把上一次调用的 dataset 残留给这次调用"一类错误，而两种读法都拒绝这类错误（§7.1）。这超出了 R-b 的边界。

### 7.5 对四项用途的影响

前提：所选版本已按正式材料评分（本机带放宽包装），并经 Codex 复核。

| 选项 | 问题定位 | 能力比较 | 训练候选 | 留出评测 |
| --- | --- | --- | --- | --- |
| A | yes | conditional：链路条件（§6 第 5 条） | conditional：同左 | conditional：D3 按仓库划分、X1、标明版本的自建题、链路条件 |
| B | yes | 同 A，另待 R-f 验收 | 同 A，另待 R-f 验收 | 同 A，另标题面版本 |
| C | yes | 同 A；C2 型结果按 §7.6 单列 | 同 A；登记 C2 型风险 | 同 A |
| 不裁定（默认） | yes | 若 Codex 判为 P5：暂挂为问题定位，同 f5eb 的处理 | conditional：差裁定 | conditional |

- **链路条件的先例**：同仓 `19f5b450` 带着同一链路条件标了 probe_ready，三项记 conditional（本批 README §8，05:38 条）。
- **训练侧的 X1 风险**（推测，未实测）：`58ba5165`、`19f5b450` 若同在训练池，它们的初态就是读法 D 与反向的 `sadfilter`，可能让 C2 型输出更常见。选 C 时，这类解在本题会稳定得 0。

### 7.6 不裁定时的默认

- **材料**：只落 R-c（`revision_draft_rc_only.json`，B.1 + B.3）。它挡住 D、N、F（F 同时被严格 `sadfilter` 与新测试挡住）；试跑 gold 1、noop 0。
- **C2 型记为"待决争议"**，不写成"正确拒绝"，也不写成"误拒"。
- **单列规则（预先登记）**：
  - **条件**：得 0，唯一不符的键是 `RF`，失败在 `sadfilter`，消息为 `'dataset' unexpectedly found in {…'dataset': None…}`；
  - **处理**：单列为疑似规格争议，原始 reward 保留；
  - **是否算对**：用私有核对读 `filter_kwargs_probe` 的输出行，看 `no_dataset` 一行是否含 `dataset`；再看其余 9 键是否都与期望一致。
- **能力比较与探针**：若 Codex 判为 P5，按 f5eb 的处理，用户裁定前本题暂挂为问题定位，不标 probe_ready。
- 不阻塞其它题（v1 §5）。

### 7.7 执行者意见（建议，不是决定）

**建议选 A。** 理由：
1. **争议不在核心要求上。** 三个选项对以下三点一样严格：给出的参数原样送达，旧式过滤器照常工作，没给时不收到 dataset 值。
2. **两种表示在 base 自己的设计里都会出现。** Python API 调用时缺席，命令行调用时为 `None`。只接受其中一种，等于把一个入口的表示当成了要求。
3. **放宽很窄。** 它只多接受读法 D 本身。它打开的唯一漏洞是 F（固定传 `None`），已由 R-c 挡住，有执行证据：只上 R-b 时 F 得 1，两项同批时 F 得 0（§5.4）。
4. **成本最低。** 不改题面，不需要新公开读者。R-c 已让本题成为标明版本的自建题，R-b 不增加这方面的代价。

**反方理由也成立**：题面示例用"键在不在"判断是否收到 dataset，读法 S 也更贴近 `_kwargs` 先例。如果用户更看重"没给的参数不要加进去"这一训练信号，选 B。

**不建议把 C 用于训练**：它会把一类核心正确的解稳定判 0，而 X1 可能让这类解更常见。

## 8. 修订后仍受保护的公开要求、未覆盖范围与剩余事项

**受保护的公开要求**（A 版；只上 R-c 时，`sadfilter` 为严格写法，其余相同）
- **带 `**kwargs` 的过滤器收到调用的关键字参数**：
  - 示例实例：`RF` 的 greatfilter；
  - 非示例实例：`GK`，覆盖 `number` 与 `dataset` 的取值、generator 模式、Dataset 方法。
- **过滤器的去留决定照常生效**：无 kwargs 时由 `RF` 前半段检查（`HT:402-422`）；带 kwargs 时由 `GK` 的 `[1, 3]` 检查（C-ign 试跑为 0，说明这条断言生效）。
- **调用带关键字参数时，Constraint、`&` 组合与单参过滤器照常工作**：`PC`。
- **没给 dataset 时，过滤器拿不到 dataset 值**：`RF` 的 `sadfilter`。A 版接受缺席或 `None`，R-c 版只接受缺席。
- **文档与签名**：`test_eval_results_plus_build_doc`。`test_interface_prep` 与本题无关，照旧。

**仍未覆盖，维持登记**
- **T3（D′）**：正确转发 kwargs，但把过滤器的非 `ValueError` 异常一律吞掉。修订版上静态判断得 1，因为修订后没有任何断言依赖异常传出。
  - 公开线索：文档只列了两种排除方式（`W/.../utils.py:864-867`）；base 只捕获 `ValueError`（`:1032`）；题面的 Actual Behavior 是过滤器的 `AssertionError` 传到调用方。
  - 协调者判断依据不够明确，本轮不并入。
  - 事后审计可以读 diff，看 `generator_func` 里的 `except ValueError` 有没有被放宽。
- **G1 → T3**：gold 用 `getfullargspec` 判断，遇到拿不到签名的可调用对象（如 `bool`）会报错；只有静态推断。
- **T3（A2、A3）**：按位置传 `dataset` 时是否转发，不测；值要原样传递，这一点由 `GK` 要求，依据见 §2.1 第 1 条。
- **T5**：5 个死键照旧；R-a 可选，本轮不做。
- **E3**：
  - 链路条件（§6 第 5 条）；
  - 隐藏测试用的 `assert_in` 等来自 `datalad/tests/utils.py`，候选可以改它，评分时又不重置。这是通用控制面问题，交 A 线；本题事后审计要标出改动了 `datalad/tests/` 或 `.venv` 的得 1 补丁。
- **X1**：
  - 同仓 `58ba5165`、`19f5b450` 的初态含本题修复的重构版，以及上游后来的 greatfilter / sadfilter（读法 D）；
  - 本题初态含 `9ba5de09` 的修复；
  - 训练时控制同族重复采样；留出评测按 D3 以仓库划分。
- **P4**：照旧。
- **试跑不是正式评分**：正式材料上的评分待协调者跑。每个候选试跑 1 次；新测试是确定性的。
- **真实模型求解**：未跑。

## 9. 边界与交接

- **做了什么，没做什么**：
  - 只做了 v1 §5 模板内的 R-c。R-b 做成与 R-c 同一版本的草案并试跑了，是否落地待 Codex 判断（§7）；
  - 没有删键，没有为保 gold 放宽要求，没有复制 gold 输出作期望，没有改题面，选项 B 的句子只是草稿；
  - 没写 `s2_r2e` 下的正式修订单与 pins，没改生产代码，没改任何原件；
  - 远端只做了建目录、上传、试跑和取回。
- **协调者待办**：
  1. 送 Codex 复核：修订内容（本文件、`revision_draft.json`、`revision_draft_rc_only.json`、`trials/`），以及 §7 的判断。
  2. 按 Codex 结论落材料：
     - 判 R-b 在模板内，或用户选 A：把 `revision_draft.json` 的 `revisions` 落为正式修订单（一条 `hidden_test_text_replace`，两处 edit），另加 `expected_file_replace`（`added` 两键）；
     - 判为 P5 且用户未定：只落 `revision_draft_rc_only.json` 与同一条期望修订，决定包交用户。
  3. 按 v4–v9 各题的做法，重建材料与派生镜像（`+material_v2+sysconfig_v1`）。
  4. 正式评分：本机带 1200 s 放宽包装，单独记账，并引用日志首行。
     - A 版至少跑 gold、noop、C1、C2、D、N、F，C-ign 可加；
     - R-c 版至少跑 gold、noop、C2、F；
     - 每次核对：`RH2_SETUP_APPLY_RC=0`；投影只含 `datalad/interface/utils.py`；`collected 10 items`；新的隐藏测试树摘要；`missing` 与 `unexpected` 为空；失败键与 §5 一致。
  5. 按 §6 第 4、5 条更正 `screening_record.json` 与题卡。
- **之后**：按 v1 §2 重判四项用途（§7.5）。
