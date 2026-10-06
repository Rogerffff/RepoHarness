# iterative__dvc-9395 独立复核：初判（封存）

2026-09-29，独立复核者（新会话，不继承作者上下文）。本稿写于任何实跑之前，也写于阅读作者 `result.md`、`evidence/` 以及 `rh2/experiments/category3_cloud_20260929/dvc9395/` 下除 `gold.patch`、`test.patch` 以外的文件之前；写完后不再修改。

## 已读范围与暴露

- 规则：`task_screening_standard_v1_20260925.md` 全文，重点 §3–§5、§9。
- 原件：`s2/ingest/` 三份 JSONL 的第 146 行（本题）。实验目录里的 `gold.patch`、`test.patch` 与 bundle 逐字节相同（sha256 分别为 `4a5017f1…667d4a`、`1252952e…09c71`，gold 的值等于 `golden_patch_sha256`）。
- 既有调查：`swegym_task_audit_20260920/quality_batch01_20260921/results/iterative__dvc-9395/` 下的 card、review、public_read、analysis_before_history、reviewer_initial、old_findings_delta、screening_record 全部已读。
- 源码：从镜像 `xingyaoww/sweb.eval.x86_64.iterative_s_dvc-9395:latest`（base `c75a5583b`）导出后只读，主要看 `dvc/repo/reproduce.py`、`dvc/stage/__init__.py`、`dvc/stage/cache.py`、`dvc/stage/run.py`、`dvc/repo/{pull,fetch,checkout}.py`、`dvc/data_cloud.py`、`dvc/output.py`、`dvc/prompt.py`、`dvc/commands/repro.py`、`tests/func/test_run_cache.py`、`tests/func/test_repro.py` 的相关段落，以及镜像内 `dvc_data/hashfile/checkout.py`。
- 已知暴露：任务说明里点名了作者的 `alt_ds_only.patch`、`gold_guarded.patch`、`revised_test_v1.patch`，我也用 `ls` 看到过实验目录的文件名，但没有打开。批次 README 本题一行只写着“辨别实验／待做”。镜像自带 pygit2 1.15.1，历史配方固定为 1.14.1。

本稿全部结论都是**静态推断**，没有运行任何东西。

## (a) 公开核心要求：`--pull` 应拉取什么

题面标题是 “Make that `dvc repro --pull` pulls all missing files”。正文先引用旧帮助：`--pull` 只拉取“从 run-cache 恢复的输出”所缺的缓存；随后指出，只有输出、没有命令的数据源（`dvc add` 生成的 `.dvc`）缺失时不会被拉取；最后提议改成 “pull whatever is missing and necessary for this repro”。

据此，核心要求是：

1. **必须做**：在本次 repro 所选的图里，数据源（`cmd is None` 的 stage）的输出如果缺失，`repro --pull` 要把它从 remote 拉回并检出到工作区，使下游 stage 能正常运行。base 在这里直接报错：`Stage.run` 的数据源分支只做 `_check_missing_outputs`，缺文件就抛 `MissingDataSource`（`dvc/stage/__init__.py` 的 `run`）。
2. **保留**：原有能力不变，即从 run-cache 恢复的输出，其缓存对象缺失时照样拉取（`StageCache.restore` 的 `pull and not dry` 分支）。
3. **一般表述可以推出、但题面没有点名的**：本地 run-cache 记录缺失、remote 上有，`--pull` 也应把记录拉回来，从而不必重算。依据是 “all missing” 加上 `--pull` 本来就服务于 run-cache 恢复。不过严格说，没有 run-cache 记录时重跑命令同样能完成 repro，所以这一条的公开依据只能算中等（见 (c)）。
4. **范围限制**：“missing and necessary for this repro” 意味着只处理缺失的文件，不包括用户改过的文件，也不包括与本次图无关的数据。公开旧测试 `tests/func/test_repro.py` 里的 `test_repro_changed_data`、`test_repro_data_source` 说明，数据源被改过后 repro 应采用新内容。`--dry` 在 CLI 帮助里的说明是 “Only print the commands…”，而 base 代码对拉取与检出一贯加了 `not dry` 保护。

## (b) 隐藏测试断言了什么

| 测试 | 断言 | 结果行为还是实现细节 |
| --- | --- | --- |
| F2P `test_repro_pulls_mising_data_source` | `assert dvc.reproduce(pull=True)` 为真 | 结果行为。foo 必须真的回到工作区，否则数据源检查报错，`cp foo bar` 也会失败。但测试不核对 foo、bar 的内容 |
| F2P `test_restore_pull`（修改版） | `push(run_cache=True)`；删除 bar、`dvc.lock`、bar 的缓存和**本地 run-cache 目录**；`(stage,) = reproduce(..., pull=True)` 只返回一个 stage | 结果行为，要求 remote 上的 run-cache 能被用上 |
| 同上 | `mock_restore.assert_called_once_with(stage, pull=True, dry=False)` | 内部调用形状，但 base 的公开测试已有同一断言，解题者看得到 |
| 同上 | `mock_run.assert_not_called()` | 行为：命令没有被重跑 |
| 同上 | **`mock_checkout.call_count == 3`**（base 公开版是 2） | **纯实现细节**。它统计的是 `dvc.output` 模块里 `dvc_data` 的 `checkout` 函数被调用了几次。gold 在逐 stage 预拉取时，会对还没有 hash 的 bar 多做一次什么也不产出的 checkout（`checkout(obj=None)` 只会告警 “It won't be created”）。之后 restore 检出一次、commit 重链接一次，一共 3 次。题面没有任何关于次数的依据 |
| 同上 | bar、foo、`dvc.lock` 存在 | 结果行为（只查存在，不查内容） |
| P2P `test_repro_pulls_intermediate_out` | 返回真 | base 就能通过（靠 lock 或 run-cache 恢复，或者重跑 echo），没有区分力 |
| 新增的 `test_repro_pulls_mising_import` | — | 不在 F2P／P2P 里，不计分 |

## (c) 合理实现，以及 F2P 能否全部接受

我认为以下几种都合理：

- **A**：gold 的写法。顶层整体拉 run-cache，再对每个 changed stage 执行 `repo.pull(addressing, allow_missing=True)`。
- **B**：只对数据源预拉取，run-cache 仍在顶层拉取（或在 restore 找不到记录时按需拉取）。有命令的 stage 继续走原有的 restore 路径。
- **C**：在 `Stage.run` 的数据源分支里，于 `_check_missing_outputs` 之前拉取缺失输出（加 `not dry` 保护），run-cache 在 restore 里按需拉取。
- **D**：A 的收紧版，只在输出真正缺失时才预拉取，不因“被修改”就拉。

预计 B、C、D 在 `test_restore_pull` 场景中的外部行为与 gold 相同，但不会产生那次多余的 checkout，计数为 2，于是只因 `== 3` 得 0。所以 **F2P 不能接受全部合理实现，T1 基本成立**；是否确实“只因计数失败”，要实跑确认。

另外，只修数据源、完全不处理 remote run-cache 的实现（旧 DeepSeek 候选属于这一类），会因为 bar 恢复不了而失败。这一条算“一般表述可推出”的要求，我登记为 P3 风险，不作为阻断。

## (d) gold 在相邻路径上的回归（均待实跑）

1. **`--dry`**：gold 新增的两处拉取都不看 dry。预计 `repro --pull --dry` 会下载 runs，并对 changed stage 做 fetch 和 checkout，于是缺失的数据源在 dry 模式下被写回工作区和缓存；base 两者都不会改。`--pull --dry` 这个组合题面没有涉及，属于少见路径，**倾向 S2**。
2. **未配置 remote**：顶层的 `stage_cache.pull(None)` 会走到 `get_remote_odb`，即使什么都不缺也会抛 `NoRemoteError`。不过 base 里有 run-cache 命中的 changed stage，在 `pull=True`、没有 remote 时同样会从 `cloud.pull` 抛 `NoRemoteError`，只是触发面更窄。带 `--pull` 却不配 remote 属于误用，**倾向 S2**。
3. **我新增的疑点：用户改过的数据源加 `--pull`**。`stage.changed()` 把“modified”也算作 changed，gold 于是对旧 hash 做 `force=False` 的 checkout。按 `dvc_data` 的 `_remove` 逻辑：工作区内容不在缓存里，就要 prompt；非 TTY 时直接抛 `PromptError`，转成 `ConfirmRemoveError`，这个异常不被 `Output.checkout`、`Stage._checkout` 捕获，最终成为 `ReproductionError`；在 TTY 下则会询问是否删除用户的修改。base 在同样情况下会接受修改，并更新 `.dvc`。“改数据后 repro”是有公开旧测试覆盖的常用行为，题面的范围又是 “missing”。所以**若实测成立，这是 §4 第 4 步的 S1 候选**（破坏了有文档、常用的公开行为），不能简单并入“边缘路径”。
4. **我新增的疑点：HTTP remote**。`StageCache.transfer` 对 HTTP 文件系统会抛 `RunCacheNotSupported`，gold 顶层没有捕获，预计默认 remote 为 HTTP 时 `repro --pull` 整体失败，数据源这个核心实例也在内。base 的 restore 加拉取在 HTTP 下可以工作。这算核心要求的“其它实例”还是“罕见路径”，需要判断，暂列 conditional。
5. 小问题：`--no-run-cache --pull` 时 gold 仍然会拉 runs。另外，changed stage 的输出在工作区已存在却还没有 hash（例如新 stage、输出是先前手工生成的）时，预拉取的 `checkout(obj=None)` 会试图删除它，也可能触发 prompt 错误。这两点都待实跑。

## (e) 初判处置

- **T1 成立（待实跑确认）**：`call_count == 3` 没有公开依据，走 R-b。删除这一行，或者改成有依据的行为断言，例如 bar 的内容与 foo 相同。restore 调用形状、`cmd_run` 未调用、产物与 lock 存在这几条保留。删除后仍需确认“不拉 remote run-cache”的退化候选得 0。
- **G1 不能整体判为“边缘 S2”**：dry 和未配置 remote 两项我倾向同意 S2。但第 (d)3 项（改过的数据源）若实测成立，按 §4 第 4 步应判 S1，需要 R-c 补一条“`--pull` 时保留用户修改”的断言；gold 会通不过，只能按 D4 用经独立核实的替代解作正对照，否则暂挂。HTTP 一项先记 conditional。
- 在 SWE-Gym 修订机制（D6）落地之前，本题不进训练。修订只能作为诊断草案，交第 2 类线程。
