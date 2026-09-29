# python__mypy-11352 · 反例预期与证明力

**疑点（`solvability_review_20260909/01_failure_cases.md` §6）：** 候选把题面的
`asynccontextmanager` TypeVar 替换问题**真的修好了**（官方
`testAsyncContextManagerWithGenericFunction` PASSED），但另两条 F2P 失败，
可见差异**只是 `reveal_type` 多显示一个未使用的 SendType `S`**：

    gold:      def [T] (item: T`-1) -> contextlib.GeneratorContextManager[T`-1]
    candidate: def [T, S] (item: T`-1) -> contextlib.GeneratorContextManager[T`-1]

审查当时**没有**下"这两条只是展示差异"的结论，理由是：无法从失败栈排除
"未量化的 `S` 会在别的类型检查入口上改变接受/拒绝集合"。本反例就是去回答这个问题。

**核心判据：** 脚本把诊断分成两层——
`semantic_signature`（退出码 + 每条 error/note 的行号与消息头，**不含** revealed 字符串）
与 `revealed_types`（纯展示）。
- 若存在 case 的 **semantic** 层 gold ≠ candidate → 接受/拒绝的程序集合真的变了，
  候选的失分不是 oracle 过严。
- 若所有差异都落在 **display** 层 → 本题是"exact-string oracle 过严"的可执行证据。

## 输入

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.python_s_mypy-11352:latest` |
| workdir | `/testbed`，base_commit `9bd651758e8ea2494837814092af70f8d9e6f7a1` |
| 候选（仅生产代码） | `patches/python__mypy-11352.candidate.src_only.diff`（只含 `mypy/plugins/default.py`；已滤掉 `test-requirements.txt`——该文件在轨迹起始 `stream.jsonl:71` 就已有改动，不是模型引入） |
| gold | `patches/python__mypy-11352.gold.diff`（同样只改 `mypy/plugins/default.py`，多一个 `detach_callable` 包裹；`detach_callable` 在 base `mypy/checker.py:5738` 已存在） |
| 官方 test_patch | `patches/python__mypy-11352.test_patch.diff`（只改 `test-data/unit/check-default-plugin.test`） |
| 官方 F2P（3 条） | `testAsyncContextManagerWithGenericFunction`、`testAsyncContextManagerWithGenericFunctionAndSendType`、`testContextManagerWithGenericFunctionAndSendType`（都在 `mypy/test/testcheck.py::TypeCheckSuite`） |
| 官方 P2P（1 条） | `testContextManagerWithUnspecifiedArguments` |
| 官方 eval_cmd | `pytest -n0 -rA -k` ← **末尾的 `-k` 没有参数**，属于参考 ID / 命令拼装脆弱项，执行方注意 |

**前置检查（必须先看）：** 镜像里的 mypy 若是 mypyc 编译过的扩展（`mypy/plugins/default.*.so`），
改 `.py` 不生效，三态结果会完全相同，整组证据作废。脚本开头会打印
`mypy.plugins.default.__file__`；不是 `.py` 就把本题记 `unknown` 并先解决这个问题。

## 用例与预期

### A 组：题面原例（语义层，必须有区分度）

| case | base | gold | candidate | 判据 |
| --- | --- | --- | --- | --- |
| `a1_async_identity_problem_statement` | rc≠0（`Incompatible types in assignment`，revealed `_T'-1`） | rc=0，revealed `builtins.int*` | rc=0，revealed `builtins.int*` | 题面问题在 gold 与 candidate 上都已修好 |
| `a2_async_identity_negative` | rc≠0 | **rc≠0**（`number = 'not an int'` 必须报错） | **rc≠0** | 若某一态 rc=0，说明类型被推成 `Any`，那才是真实语义缺陷 |
| `a3_sync_identity_baseline` | rc=0 | rc=0 | rc=0 | 同步版本 base 本来就正确，三态不变 |

### B 组：SendType 的展示差异来源

| case | base | gold | candidate | 判据 |
| --- | --- | --- | --- | --- |
| `b1_sync_sendtype_reveal` | revealed `def [T, S] ...` | revealed `def [T] ...` | **revealed `def [T, S] ...`** | 对应官方 `testContextManagerWithGenericFunctionAndSendType` |
| `b2_async_sendtype_reveal` | base 上 `x` 应为 `T'-1` | revealed `def [T] ...` + `builtins.int*` | revealed `def [T, S] ...` + `builtins.int*` | 对应官方 `testAsyncContextManagerWithGenericFunctionAndSendType` |

B 组两条的 `rc` 与 `semantic_signature` 在 gold / candidate 上**预期相同**，
只有 `revealed_types` 不同 —— 这正是"展示层差异"的定义。

### C 组：语义层候选项（这组才决定结论）

| case | 想抓什么 | 预期（待实测） |
| --- | --- | --- |
| `c1_type_application_one_arg`（`yield_id[int]`） | 未量化的 `S` 会不会让类型参数个数从 1 变成 2 | gold 预期 rc=0；candidate **若报 "Bad number of type arguments"，就是语义差异** |
| `c2_type_application_two_args`（`yield_id[int, str]`） | 反向：gold 上应报参数过多 | gold 预期 rc≠0；candidate 预期 rc=0 |
| `c3_assign_to_exact_callable` | 赋给精确的 `Callable[[int], ContextManager[int]]` | 两态预期都 rc=0；若 candidate 报错就是语义差异 |
| `c4_incompatible_assignment_message` | 官方 SendType 用例里那条负例 | 两态都 rc≠0；差别预期只在消息里的 `[T]` vs `[T, S]`（展示层） |
| `c5_pass_to_higher_order` | 真实用法：传给高阶函数 | 两态预期都 rc=0，revealed 都是 `builtins.int` |
| `c6_indirect_call` | 经变量间接调用时 `S` 是否留下未解类型变量 | 两态预期都 rc=0，`y = 2` 不报错 |

**c1 / c2 是本组最可能出结果的一对**：它们直接测"被量化的类型变量个数"这一可观察语义，
而不是打印字符串。如果 c1/c2 出现 gold ≠ candidate 的 rc 差异，
结论就是"候选确有语义缺口"，而不是"oracle 过严"。

### 官方面

| run | base | gold | candidate |
| --- | --- | --- | --- |
| `official_f2p`（3 条） | 3 failed | 3 passed | **1 passed / 2 failed**（与 `cc_candidate_grading.jsonl` 的 RESOLVED_PARTIAL 一致） |
| `official_p2p`（1 条） | passed | passed | passed |
| `official_default_plugin_file`（`-k ContextManager`） | — | 全绿 | 2 failed |

## 这证明什么 / 不证明什么

**能证明（取决于 C 组实测）：**
- 若 `verdict_hint.cases_with_semantic_diff` 为空、`cases_with_display_only_diff` 非空：
  本题是一个**可执行的 exact-string oracle 过严**例子——候选解决了题面问题、
  在 9 个最小程序上与 gold 接受/拒绝完全一致，仅 `reveal_type` 字符串不同却被判负。
  这对后训练的含义是：这类题的 0 分信号并不对应"代码没修好"。
- 若 `cases_with_semantic_diff` 非空：本题应归为"真实语义缺口"，
  审查里"仅展示差异"的说法被推翻，须把具体 case 写进记录。

**不能证明：**
- 无论哪种结果，都**不能**推广成"mypy 全部题目的 reveal_type oracle 都过严"。
  本反例只覆盖 `contextmanager` / `asynccontextmanager` 这一条插件路径。
- 不能证明候选的实现质量与 gold 等价：gold 用 `detach_callable` 做了更完整的类型变量归一化，
  这本身是更好的写法；本反例只衡量"可观察行为是否不同"。
- 9 个最小程序不是穷举。若 C 组全部无差异，正确措辞是"在这 9 个入口上未发现语义差异"，
  不是"证明没有语义差异"。

## 落到筛查记录的字段

- `issues[]`（待实测填 severity）：`{category: "exact_string_oracle" 或 "semantic_gap", evidence_refs: ["<OUT_DIR>/result.json#verdict_hint"], proposed_action: "见实测结果", next_experiment: "本 run_matrix.sh"}`
- `issues[]`：`{category: "fragile_eval_cmd", severity: "P2", note: "grading bundle 的 eval_cmd 为 'pytest -n0 -rA -k'，-k 后无参数", evidence_refs: ["s2/ingest/grading_bundles_v2_v0.jsonl#python__mypy-11352.eval_cmd"]}`
- `proposed_regression_tests[]`：A 组三条（题面正例 + 负例 + 同步对照）。
- `file_rules.additional_exclusions`：**不新增**；`test-requirements.txt` 的改动在轨迹起始已存在。

## 执行注意

- 先看 `preflight_plugin_path.txt`。不是 `.py` 就停。
- `diagnostic_test.sh` 不需要 pytest，只需要能 `python -m mypy`；官方面那部分才需要 pytest。
  若 pytest 缺失，诊断部分仍然有效，官方面记 `unknown`（**不要**在容器里安装）。
- `a1/a2/b2` 用 `--python-version 3.7`（`asynccontextmanager` 的 typeshed 版本门槛），
  与官方用例的 `# flags: --python-version 3.7` 一致。
- 三态之间的复位只作用于容器内一次性的 `/testbed`。
