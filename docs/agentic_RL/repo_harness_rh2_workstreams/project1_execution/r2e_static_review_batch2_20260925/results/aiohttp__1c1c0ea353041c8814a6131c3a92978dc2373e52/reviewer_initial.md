# aiohttp__1c1c0ea3 独立复核初判（reviewer_initial）

2026-09-25 · 独立复核者第一步。没有读公开读者产物、主审产物或任何历史结论。证据级别：**【静态】** 源码与测试推断；**【日志】** 复读已有评分运行原件（不是独立重跑）；**【devcheck】** 协调者提供的真实 actor 环境执行结果。

下文简写：`PUB` = `runs/r2e_static_prep_20260924/v3/public/aiohttp__1c1c0ea353041c8814a6131c3a92978dc2373e52/`，`PRIV` = 同名 `private/` 目录，`DC` = `runs/r2e_actor_20260925/devcheck/aiohttp__1c1c0ea353041c8814a6131c3a92978/`。

## 0. 初判摘要

- **题目**：base `87342c79`（aiohttp 3.10.6.dev0）中，`web.run_app()` 在应用启动失败时会把同一个异常抛出一次、又通过 `_cancel_tasks({main_task}, loop)` → `loop.call_exception_handler(...)` 记录一次。题面要求：异常照常抛出，但不再记录。
- **题面、测试与 gold 一致；没有发现合理解被误拒。** 唯一的目标键是 `test_run_app_raises_exception[pyloop]`，它同时断言“原异常被抛出”和“`loop.call_exception_handler` 没被调用”，走的正是题面示例那条路径。56 个期望键全部是 PASSED，所以不存在“更完整的修复把 FAILED 键改成 PASSED、反被判 0”的风险。7 次 noop 运行都只在该键的 `assert not m.called` 处失败；7 次 gold 运行都是 56/56。【日志】
- **问题 1（漏测，影响中低）**：用 Ctrl+C 或 `GracefulExit` 正常停服后，取消 `main_task` 会运行清理钩子；如果钩子抛出异常，这个异常最终去了哪里，没有任何测试键检查。gold 把它改成抛出。静态推断下，下面两种实现也都能得 1：一种保持 base 的做法，只记录不抛出（候选 A）；另一种既不抛出也不记录，把异常静默吞掉（候选 B）。候选 B 不符合题面“should raise the exception”的宽泛读法；base 至少还会记录这个错误，候选 B 连记录都没有，所以它是一个可能混过评分的错误实现。【静态】
- **问题 2（环境风险，影响低）**：`TestShutdown` 的 8 个回归键依赖真实 socket、sleep 和墙钟阈值。最紧的是 `test_shutdown_handler_cancellation_suppressed`，静态估计余量约 0.1 s。现有 14 次评分运行、M3 的 2 次运行和 devcheck 都稳定，耗时波动不超过 0.05 s；更高并发负载下还没有验证。【日志】【静态】
- **问题 3（题目关系）**：本题 gold 对 `run_app` 的改动、目标测试和 changelog 条目，都逐字出现在同仓 `aiohttp__22a12cc2` 的公开工作树里（已人工核对）。两题不能一个放训练、一个放评测；否则要登记这项暴露。【静态】
- **暂定处置**：作为静态候选用于 development_diagnostic，并注明问题 1。不需要为了评分正确性改题。
- **唯一优先的下一步**：用正式评分代码实跑候选 A 和 B（预期都得 1），再跑附录 B 的行为脚本，确认三种实现在“正常停服后清理钩子抛错”这条路径上的差别，从而把问题 1 的范围坐实。

## 1. 实际读取范围

- 角色与方法：`roles/reviewer_r2e.md` 全文。`roles/investigator_r2e.md` 被工具整份显示，但只把“R2E 的评分口径”“材料”“第二批补充规则”三节当作口径依据。`quality_review_protocol_20260920.md`、`r2e_environment_card.md`、`record_template.md` 全文。
- `PUB`：`user_prompt.txt`、`environment_brief.md`、`public_bundle.json`、`worktree_manifest.json`（摘要）。`worktree/` 中读了：`aiohttp/web.py:280-540`、`aiohttp/web_app.py:564-590`、`aiohttp/web_runner.py:276-300`、`aiohttp/web_protocol.py:252-297`、`aiohttp/web_server.py:26-71`、`setup.cfg:118-172`、`docs/web_advanced.rst:940-979`；把 `tests/test_run_app.py` 和 `tests/conftest.py` 与隐藏测试做了 diff；另外看了 `.gitignore`（grep）、`CHANGES/` 列表、`install.sh`、`run_tests.sh`，并在全树 grep 了 `_cancel_tasks`、`call_exception_handler`、`6807`。
- `PRIV`：`gold.patch`、`run_tests.sh`、`revisions.json`（`[]`）、`expected_output.json`、`grading_bundle.json`、`validation_bundle.json`、`run_refs.json`，以及 `hidden_tests/` 三个文件的全文；各文件 hash 已与 bundle 核对（附录 A）。
- 运行原件：`run_refs.json` 中 14 条 `material=current` 行对应的账本行（R-f 的 noop 与 gold 两行通读，其余行只取结果、镜像和耗时字段），以及 14 份 `.eval.log`（sha256 全部核对；R-f 的 noop 与 gold 两份通读，其余只抽取汇总行、失败行和耗时）。M3 的 `test_output.txt`（a1、a2）看了汇总与耗时，账本 `r2e_gold_m3.jsonl` 看了第 9、60 行。
- `DC`：`commands_with_preflight.json`、`attempt.json`、`activation_check.json`、`prelaunch.json`（前 40 行）、`captures/*.out`、`post_run_facts_root.txt`（开头）、`cc_version_observed.json`、`private_gold/{private_control.json,stdout.log}`。`harness/trajectory.jsonl` 只数了行数（77 行），没读内容。
- 跨题：`cross_task_gold_scan.json`（`method` 与 aiohttp 相关的 3 对）。同仓 5 题的 `public_bundle.json`（只看 base 和标题）；`aiohttp__22a12cc2` 的 `user_prompt.txt` 开头、`worktree/aiohttp/web.py:430-545`、`worktree/tests/test_run_app.py`（测试名清单和 909-925 行）、`worktree/CHANGES.rst:185-200`。
- **没有读**：OUTPUT_DIR 里的其它文件（包括 `public_read.md`）、`history/`、`docs/.../r2e_env_repair_20260924/`、首批审查目录、Codex 复核目录和其它审查目录、本批 README 与 `assignments.json`、`runs/` 下的分析和汇总文件（env-repair 与 batch2 目录下只打开了 run_refs 指向的账本行和日志）、同仓其它题的私有包。没有运行任何代码或容器。

## 2. 八方面

1. **公开需求（已查）**
   - 题面标题是 “run_app() Logs Exceptions That Are Also Raised”。期望行为：`run_app()` 抛出异常，但不记录。示例：`cleanup_ctx` 在 `yield` 之前抛出 `RuntimeError`。
   - 读代码才能知道的事：唯一的记录通道是 `_cancel_tasks` 对 `main_task` 调用 `loop.call_exception_handler`（`PUB/worktree/aiohttp/web.py:449-459` 和 `:522`）。
   - 公开旧测试说明了另外两条约束。`tests/test_run_app.py` 里的 `test_run_app_cancels_failed_tasks` 要求其它残留任务的异常仍然交给 exception handler。`docs/web_advanced.rst:948-967` 写明了停服顺序：先完成第 1–6 步（main task 的清理），第 7 步才取消剩余任务。
   - 只有看隐藏材料才能知道的要求：没有实质性的。目标键用的观测通道可以从公开代码推出来，因为公开旧测试本来就用 `set_exception_handler` 观测同一个通道；devcheck 的 `pr2_2_cmd` 也是独立地用 handler 调用次数来观测。
   - 歧义：宽泛读法——“When an exception occurs within the application context, run_app() should raise the exception”——会把“正常停服后清理钩子抛错”也包含进来；窄读法按标题——只管“既被抛出又被记录”的异常。测试只覆盖了窄读法。
2. **材料与初始问题（已查）**
   - 材料对得上：隐藏的 `test_1.py` 就是 base 的 `tests/test_run_app.py` 加上新测试，diff 只有第 12 行的 import 和第 909-925 行；`conftest.py` 与 base 完全相同；gold 只改 `aiohttp/web.py`，每次运行中 `git apply` 的返回码都是 0；没有材料修订。按 M3 账本第 9 行的 `gold_meta`，gold 排除了 `CHANGES/6807.bugfix.rst`，它不是代码。
   - 问题在初态确实成立【静态】。调用链：
     1. `_run_app` 的 `await runner.setup()` 在 try 之外（`web.py:337`）；
     2. `app.startup()` 调用 `CleanupContext._on_startup`（`web_app.py:569-573`），用户的 ctx 在这里抛错；
     3. `main_task` 带着异常结束，`run_until_complete(main_task)`（`:518`）把异常抛出来；
     4. finally 里的 `_cancel_tasks({main_task}, loop)`（`:522`）又调用 `call_exception_handler`（`:453`）。
   - 运行证据：
     - noop 失败的位置就是 `test_1.py:923`，见 R-f noop 日志第 107-115 行：`assert not True` / `where True = <function call_exception_handler …>.called`。【日志】
     - 同一份日志第 117-120 行，`test_startup_cleanup_signals_even_on_failure` 的 captured log 正是题面说的那条重复日志：`unhandled exception during asyncio.run() shutdown … exception=RuntimeError()`。gold 日志的 PASSES 段（第 88 行起）不再有这条。【日志】
     - devcheck 以 agent 身份跑题面原例：base 下有 1 条相关日志、handler 被调 1 次、回溯行出现 2 次；gold 下分别是 0、0、1（`DC/orig/captures/pr1-3`、`DC/private_gold/private_control.json`）。【devcheck】
3. **测试是否测到要求（已查，见 §3 的表）**
   - 目标键覆盖了“抛出”和“不走 handler”两半。
   - 没覆盖的有两处：一是 `create_server` 失败这条路径是否还记录（相关键只断言了抛出，没断言记录）；二是正常停服后清理钩子抛错的去向（问题 1）。
   - 还有一个盲点：目标键只观测 `call_exception_handler` 这一个通道，改用 `logging` 直接记录的实现也能通过。但这和题意正相反，可能性很低，不设实验。
4. **是否误拒合理解（已查）**
   - 没有非 PASSED 的期望键。
   - 用 `call_exception_handler` 来判断“是否记录”，有代码依据：它是 run_app 唯一的记录通道。如果一个修法仍然调用 handler、只是让它不输出，就会劫持用户自己装的 handler，不能算合理解。
   - 保守的替代解（候选 A）静态预期得 1。
   - 唯一可能导致“对的解被判 0”的来源，是时序键在负载下偶发失败，属于环境风险（问题 2）。
5. **回归与 gold 完整性（已查）**
   - gold 修好了原例，并保留了三点旧行为：先处理 main task、再 `_cancel_tasks(asyncio.all_tasks(loop))`；`shutdown_asyncgens` 和 `loop.close()` 放在内层 finally，即使 main task 重新抛出异常也一定执行。
   - gold 顺带改了一条路径：正常停服后清理钩子抛的错，从“只记录”变成“抛出”。这符合宽泛读法，但没有测试检查。
   - 没有无关改动。`_cancel_tasks` 没有其它调用者（grep 过）。
   - 回归键实际保护了这些旧行为：
     - 停服顺序：`TestShutdown`；
     - 残留任务的异常仍被报告：`test_run_app_cancels_failed_tasks`，`test_1.py:856`；
     - 正常路径关闭 loop：`test_run_app_close_loop`；
     - 启动失败时抛出异常、清理 handler 只调用一次：`test_startup_cleanup_signals_even_on_failure`。
6. **agent 的开发条件（devcheck 已查；真实模型未验）**
   - 已确认的条件：
     - 预检三项都 ok：解释器可执行；隐藏测试不可读；git HEAD 没有子提交，且 `REFS_REMAINING 0`、`UNREACHABLE_OBJECTS 0`。
     - 身份是 uid 54321，`python` 指向 `/testbed/.venv/bin/python`。
     - `aiohttp` 3.10.6.dev0 从 `/testbed` 导入。
     - 有 pip 23.2.1，但无出网；修复只需要标准库的 `contextlib`。
     - pytest 8.3.2；`python -m pytest tests/test_run_app.py` 以 agent 身份 55 passed，用时 26.92 s，包含真实 socket 和时序测试。
     - 跑完测试后 `RH2_GIT_STATUS_LINES=4`，与初态相同：`.coverage` 和 `__pycache__` 都在 `.gitignore` 里，不会弄脏提交的 diff。
   - 一处小摩擦：包没有装进 venv。在 `/testbed` 之外放脚本再运行（例如 `python /tmp/repro.py`）会导入失败，而公开提示没说这一点。它不阻塞解题，属于“actor 待验”。
   - `setup.cfg` 的 addopts（`--cov`、`-v`、`--showlocals`）评分时同样生效（日志里有 `configfile: setup.cfg` 和覆盖率表）。`filterwarnings = error` 在 `-W ignore` 下是否仍会把测试内的警告升成错误：静态判断会，但没有实测。
   - 没验证的：真实模型能否解出、经 adapter 的链路。
7. **交付与评分边界（部分已查）**
   - gold 的投影只包含 `aiohttp/web.py`。
   - 隐藏测试只依赖包内的 helper（`aiohttp.test_utils.make_mocked_coro`、`aiohttp.pytest_plugin` 里的 `loop` 与 `aiohttp_unused_port`、`aiohttp.web_runner.BaseRunner`）和 pytest-mock 的 `mocker`。这些候选都能改，评分时也不会重置，但没找到针对目标键的蒙混路径：目标键在 loop 实例上自己 patch 了 `call_exception_handler`。
   - 平台层面的规则没有审：候选改 `setup.cfg`、在根目录加 `conftest.py`、改 `tests/` 时会怎样处理。
8. **题目关系与用途（已查）**
   - 与 `aiohttp__22a12cc2` 的包含关系见 §5。
   - 上游 issue #6807 是公开的，外部答案可达；但 actor 无出网，git 历史也已清理。
   - 任务类型：asyncio 停服逻辑中单个函数的小修复，gold 改动 +9/−4 行。题面没有给出修法。

## 3. 核心需求—测试映射

| 公开要求或合理的旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖 | 执行证据或下一步验证 |
| --- | --- | --- | --- | --- |
| 原例：`cleanup_ctx` 启动期抛错，`run_app` 抛出原异常 | 题面 Expected Behavior 与示例 | `test_run_app_raises_exception[pyloop]`：`pytest.raises(RuntimeError, match="foo")`（test_1.py:920-921） | 覆盖 | noop 与 gold 都满足这一半；单凭它区分不了 |
| 不记录，即不走 loop 的 exception handler | 题面；`web.py:449-459,522` | 同一个键：`assert not m.called`（:917-923） | 覆盖（只观测这一个通道） | noop 7/7 在 :923 失败；gold 7/7 通过；devcheck 中 base 调 1 次、gold 调 0 次 |
| 其它“既抛又记”的路径，例如 `create_server` 失败，也不该记录 | 题面的泛化 | `test_startup_cleanup_signals_even_on_failure`（:664-677）只断言抛出和 handler 调用次数 | 部分 | noop 日志有重复记录，gold 没有；该键在两边都通过 |
| 正常停服后清理钩子抛错，不应静默丢失 | 宽泛读法；base 至少会记录 | 无 | 缺失 | 候选 B 实跑，附录 B 的脚本 |
| 其它残留任务的异常仍报告给 handler（停服第 7 步） | 公开旧测试；`docs/web_advanced.rst:967` | `test_run_app_cancels_failed_tasks`：`exc_handler.assert_called_with(patched_loop, msg)`（:856） | 覆盖 | 会拒掉过度抑制的实现（候选 D） |
| 停服顺序：先取消并清理 main task，再取消其余任务 | `docs/web_advanced.rst:948-967` | `TestShutdown.*` 共 8 键（:926-1260），例如 `test_task.exception() is None`（:993）、`finished is True`（:1009） | 覆盖 | 会拒掉删掉 main task 优先那一步的实现（候选 C） |
| 抛出异常时 loop 仍被关闭 | base 行为 | `test_run_app_close_loop`（:96-103）只测正常路径 | 部分 | 可能性低，不设实验 |

## 4. R2E 专项

- **（a）非 PASSED 期望键**：没有，56 个全是 PASSED。不存在翻转风险。
- **（b）题面报错是否出现在 noop 目标键的失败原因里**：出现了。noop 下异常照样抛出（`pytest.raises` 那一半通过），失败原因正是 handler 被调用了（日志第 107-108 行）。题面说的日志文本在同一份日志第 119-120 行可见。
- **（c）题面是否泄漏修法**：没有。题面没提 `_cancel_tasks`、`call_exception_handler`、`suppress`，也没提 main task 的处理方式。本题自己的工作树里也没有 `6807` 的 changelog 或已修好的代码（grep 过）。
- **（d）测试支撑与撞键**：
  - 只有一个测试文件，56 个键互不相同，不存在撞键。
  - 只依赖包内的 helper；conftest 与 base 完全相同，里面的 `pytest_plugins` 作为初始 conftest 加载，运行中正常收集到 56 项。
  - 没有依赖相对路径资源，搬迁到 `r2e_tests/` 不产生伪影。
- **（e）时间、随机与资源敏感键**：
  - `TestShutdown` 共 8 键（:926-1260），用真实 socket，sleep 最长 9 s，有 `< 10`（:1050）、`< 5`（:1207）两个墙钟阈值，还要求严格的事件顺序（:1260）。
  - 最紧的键是 `test_shutdown_handler_cancellation_suppressed`。时间线大约是：
    - 约 0.4 s：客户端超时，handler 被取消，并吞掉这次取消；
    - 约 0.5 s：handler 开始再睡 2 s，同时停服开始，按 `shutdown_timeout=2` 从这时起算（`web_protocol.py:263-275`）；
    - 约 2.4 s：handler 睡完，写下 `DONE`；
    - 约 2.5 s：停服等待到期。

    所以余量约 0.1 s。实测该测试耗时 2.40-2.42 s，与这个估计吻合。
  - 还有几个与环境绑定的键：`test_run_app_preexisting_inet6_socket` 需要能绑定 `::1`，环境不支持时会 SKIPPED，导致缺键，所有候选都判 0；`test_run_app_abstract_linux_socket` 需要 Linux 抽象套接字；`test_run_app_multiple_preexisting_sockets` 要求绑定 `localhost` 后打印出 127.0.0.1。
  - 目前 14 次评分运行、M3 的 2 次、devcheck 的公开测试和私有 gold 对照全部通过，耗时稳定；noop 与 gold 的耗时几乎一样，说明修复本身不改变停服时序。
- **（f）修订**：本题没有修订，不适用。

## 5. 题目关系（同仓跨题包含）

- **核对结果**：`cross_task_gold_scan.json` 记录本题 gold 的 7 条非平凡新增行全部出现在 `aiohttp__22a12cc2`（base `354153e9b706`）的公开工作树里。人工核对确认：
  - 对方的 `worktree/aiohttp/web.py:519-531` 与 gold 修复后的代码逐字相同；与本题 base 在 `run_app` 附近的 diff，除去一行位移，就是 gold 本身。
  - 对方的 `worktree/tests/test_run_app.py:909-923` 含有本题目标测试的全文。
  - 对方的 `worktree/CHANGES.rst:190-194` 有 changelog 条目 “Stopped logging exceptions from web.run_app() that would be raised regardless … issue 6807”。

  也就是说，看过 22a12cc2 工作树的模型，同时看到了本题的答案和隐藏测试。
- **反方向**：扫描没有发现其它题的 gold 包含在本题工作树里。我无法用私有包复核这一点。按 base 的新旧推断：`4075c653`（CHANGES 最大编号 7715）、`240da100`、`618335186`（都没有 CHANGES 目录）的 base 比本题更早，它们的修复可能以某种形式存在于本题工作树中，但没有检查。
- **建议**：两题不要一个进训练、一个进评测；同批训练时记录这项暴露。

## 6. 可直接改成补丁的候选（交给协调者实跑）

四个候选都只改 `aiohttp/web.py`。

- **A（合理替代解，保守版）**
  - 改法：在 `run_app()` 的 finally 里，把 `_cancel_tasks({main_task}, loop)` 改为 `if not main_task.done(): _cancel_tasks({main_task}, loop)`，其余不变。
  - 预期：56/56，得 1。
  - 语义：启动或运行期失败只抛出、不记录；正常停服后清理钩子抛的错保持 base 行为，只记录、不抛出。这符合窄读法。
- **B（可能混过评分的错误实现）**
  - 改法：把同一行换成 `main_task.cancel(); loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))`。等价写法：给 `_cancel_tasks` 加一个 `report=False` 参数，只对 main task 传入。
  - 预期：56/56，得 1。【静态】理由是其余 55 个键走的路径与 base 相同，目标键因为不再调用 handler 而通过。
  - 缺陷：正常停服后清理钩子抛的错既不抛出也不记录，被静默丢失。附录 B 的脚本会显示 `raised: nothing` 和 `handler calls: []`。
- **C（负对照：破坏停服顺序）**
  - 改法：删掉 `_cancel_tasks({main_task}, loop)` 这一行，只保留 `_cancel_tasks(asyncio.all_tasks(loop), loop)`。
  - 预期：得 0。目标键会通过，但 main task 会和测试任务、正在处理的 handler 一起被取消，`TestShutdown` 中依赖“在途任务完成”的键失败，例如 :993 的 `test_task.exception()` 会抛出 CancelledError、:1009 的 `finished is True` 不成立。
  - 判定：这个拒绝有公开依据（`docs/web_advanced.rst:948-967`），是合理的。
- **D（负对照：过度抑制）**
  - 改法：在 `_cancel_tasks` 里删掉整段 `loop.call_exception_handler(...)`。
  - 预期：得 0，失败键是 `test_run_app_cancels_failed_tasks[pyloop]`（:856）。
  - 判定：拒绝合理。其它后台任务的异常本来就不会由 run_app 抛出，删掉报告等于把它们吞掉。

## 7. 未知与暂定处置

- **未知项**：
  1. 候选 A、B 的实际得分目前只是静态推断。
  2. 时序键在训练并发负载下的误判率。
  3. 反方向的跨题包含。
  4. 真实模型能否解出、完整消息与 adapter 链路。
  5. 平台层面对改 `setup.cfg`、根目录 `conftest.py`、`tests/` 的处理。
- **暂定处置**：静态候选，`state` 保持 needs_review，理由写“静态候选待 actor 验证”；另附问题 1 的漏测说明和问题 3 的数据划分约束。
- **如果要补上问题 1 的漏测**：只加一条中性断言——“正常停服后清理钩子抛出的异常，要么被抛出，要么交给 exception handler，但不能静默丢失”。这样 gold 和候选 A 都通过，只拒掉候选 B。**不要**直接要求“必须抛出”：那会把宽泛读法定死成 gold 的行为，窄读法下合理的候选 A 就会被判 0。这属于测试标准变更，要由用户决定；只用于 development_diagnostic 时可以不改。
- **唯一优先的下一步**：用正式评分代码实跑 A 和 B，并跑附录 B 的脚本。如果条件允许，再补一轮并发负载下的 gold 重复评分，观察时序键。

## 附录 A：material=current 运行与材料核对

| 组 | 候选 | 账本:行 | 派生镜像 ID | 结果 | 测试耗时 |
| --- | --- | --- | --- | --- | --- |
| R-f 09-23 | noop | `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl:1` | `ba4b1812` | 55/56，只有目标键 FAILED | 31.7 s |
| R-f 09-23 | gold | `…/ledger_r2e_all_gold.jsonl:1` | `ba4b1812` | 56/56 | 31.6 s |
| 环境轮复跑 | noop | `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl:1` | `ba4b1812` | 55/56，同上 | 31.0 s |
| 环境轮复跑 | gold | `…/_rerun2/ledger_gold.jsonl:1` | `ba4b1812` | 56/56 | 31.8 s |
| 时序加跑 | noop ×5 | `runs/r2e_t0_batch2_20260924/replay_b2/ledger_watch1c1c_noop.jsonl:1-5` | `39f42dc8` | 5 次都是 55/56，同上 | 28.5-29.1 s |
| 时序加跑 | gold ×5 | `…/ledger_watch1c1c_gold.jsonl:1-5` | `39f42dc8` | 5 次都是 56/56 | 28.1-28.9 s |
| M3 独立 runner（来源镜像 `3a2a7377…`） | gold ×2 | `runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl:9,60` | 来源镜像 | 2 次都是 56 passed | 34.7-34.9 s |
| devcheck（agent / 私有 root） | base 公开命令 / gold | `DC/orig/captures/`、`DC/private_gold/private_control.json` | `bd9b7c27` | 见 §2 第 2、6 条 | 公开测试 26.9 s / 26.8 s |

- **日志核对**：14 份日志的 sha256 都与 `run_refs.json` 一致。所有 current 日志的隐藏测试树都是 `RH2_SETUP_HIDDEN_TESTS_TREE=a46a7752…`，入口都是 `RH2_SETUP_ENTRY_SHA256=8285765f…`，与 `PRIV` 一致。
- **材料 hash 核对**：本地 `hidden_tests/{__init__,conftest,test_1}.py` 的 hash 与 `grading_bundle.hidden_test_files` 一致；`expected_output.json` 与 bundle 原文逐字节相同（`a7341a36…`）；`gold.patch` 的 `926c9558…` 与账本里的 `patch_sha256` 一致。
- **派生镜像的差异**：三台机器上的派生镜像 ID 不同（`ba4b1812`、`39f42dc8`、`bd9b7c27`），但配方相同（`r2e_derive_v1`），来源 digest 也相同，初始工作树一致（HEAD `87342c79`，porcelain 为 ` M Makefile` 加 3 个未跟踪脚本），各次结果也一致。
- **TestShutdown 耗时**（14 次评分运行的范围）：
  - `new_conn_rejected` 9.51-9.52 s
  - `pending_handler_responds` 4.01-4.02 s
  - `wait_for_handler` 2.51-2.52 s
  - `handler_cancellation_suppressed` 2.40-2.41 s
  - `timeout_handler` 1.61-1.62 s
  - `timeout_not_reached` 1.50-1.51 s
  - `close_websockets` 1.02-1.08 s
  - `close_idle_keepalive` 1.00-1.01 s
- **一个与本修复无关的既有现象**：noop 和 gold 日志里，`test_shutdown_timeout_handler` 都会记录 `InvalidStateError: invalid state`（`web_protocol.py:460`，R-f noop 日志约第 146-200 行）。它来自非 main 的 `_handle_request` 任务，由 `_cancel_tasks(asyncio.all_tasks(loop))` 报告，与本修复无关，该键照样通过。这也说明 gold 仍会报告非 main 任务的异常，与标题的窄读法一致。

## 附录 B：漏测行为脚本（不是隐藏测试，只用来确认三种实现的差别）

在 `/testbed` 下以 `python - <<'EOF' … EOF` 运行：

```python
import asyncio
from aiohttp import web

async def ctx(app):
    yield
    raise RuntimeError("cleanup boom")

app = web.Application()
app.cleanup_ctx.append(ctx)
loop = asyncio.new_event_loop()
calls = []
loop.set_exception_handler(lambda lp, c: calls.append(c.get("message")))

def stopper(*_):
    def raiser():
        raise KeyboardInterrupt
    loop.call_soon(raiser)

try:
    web.run_app(app, loop=loop, host="127.0.0.1", port=0, print=stopper, handle_signals=False)
except RuntimeError as e:
    print("raised:", repr(e))
else:
    print("raised: nothing")
print("handler calls:", calls)
```

预期（静态推断）：

| 实现 | `raised:` 行 | `handler calls:` 行 |
| --- | --- | --- |
| base 与候选 A | `raised: nothing` | `['unhandled exception during asyncio.run() shutdown']` |
| gold | `raised: RuntimeError('cleanup boom')` | `[]` |
| 候选 B | `raised: nothing` | `[]`（静默丢失） |
