<!-- 协调者注（2026-09-25）：宿主不允许子会话写报告文件（"Subagents should return findings as text"），本文由协调者从该会话被拒的写入调用中原样取出保存，未改一字。 -->
# coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9：私有主审初判（读历史前）

- 角色：R2E 私有主审（静态审查）。2026-09-25 写成，写于阅读任何历史调查之前。
- 暴露范围：看过隐藏测试、expected、gold 和运行日志。没有读 `history/`、`docs/.../r2e_env_repair_20260924/`、其它审查目录，也没有读 `runs/` 下的分析或汇总文件。
- 执行边界：没有运行项目代码或容器。唯一的"执行"是在 scratchpad 的复制件上用 `patch` 和 `git hash-object` 做文本核对（附录 A4）。
- 题目：base `8240c58c`（coverage 5.0.2a1，Python 3.7.9）。题面要求私有方法 `Coverage._warn` 接受 `once` 参数，并让 `once=True` 的警告"只显示一次"。
- 评分依据：期望映射共 75 个键，全部是 PASSED；目标键只有 `ApiTest.test_warn_once` 一个。

## 0. 摘要（暂定）

- **材料与评分**：可复现、且与本题对应。
  - 哈希全部一致。
  - 当前材料下 noop 跑了两次，都只错目标键，失败原因就是题面所写的 `TypeError`。
  - gold 跑了两次，都是 75/75；M3 在来源镜像上的两次 gold 也都是 75/75。
- **主要问题：去重键（题意与测试的争议）**：
  - 隐藏测试要求：第二条 `once=True` 警告与第一条 slug 相同、消息不同，它**不能**显示。也就是说，实现必须按 slug 去重，或者比 slug 更粗。
  - 题面没有说按什么判定"重复"。"displayed only once each, preventing duplicate warnings"最字面的读法是按消息去重，那样两条都会显示，结果判 0。
  - 公开材料里有支持"按 slug"的线索，但公开读者在隔离条件下独立阅读后，结论是"无法裁决"。
- **次要问题**：
  - 测试过宽：像"第一次 once 之后所有 once 警告都不显示"这样的错误实现也能得 1。
  - gold 有一个未测的副作用：它在首次调用 `_warn` 时快照 `disable_warnings`。
  - 隐藏测试导入的是 base 版 `tests/coveragetest.py`，其中的假 `_warn` 不接受 `once`。这只会惩罚题面没要求的越界改动。
  - 本题 gold 原样出现在同批另外 4 道 coveragepy 题的 base 中。
- **暂定处置**：`needs_review`，原因归为"题意/测试争议（去重键）"。建议做最小的公开规格修订后，再作为静态候选待 actor 验证：题面补一句"once 按 slug 判定"。
- **共享阻塞**：正式 actor 仍然使用来源镜像，其中隐藏测试可读、git 历史里有修复提交。修好之前本题不能进探针。

## 1. 八方面覆盖

| 方面（清单编号） | 已查 | 结论 | 未查 / 缺项 |
| --- | --- | --- | --- |
| 公开需求（3、23） | `user_prompt.txt`、`public_hints`、公开读者报告、base `coverage/control.py`、`doc/cmd.rst` 的警告一节、`doc/config.rst:156-158` | 去重键没有约定（§2 R4）。hints 里"conda 已激活"和"测试文件会被重置"两句与 R2E 不符（共享问题 E09） | 模型实际收到的消息没有看到 |
| 材料与初始问题（1、2、27） | hidden tests、expected、gold、`run_tests.sh` 与摄入行逐一核对 sha256；worktree 初始 diff 为 0 字节；两份 noop 日志 | 初态确实有问题：noop 在 `r2e_tests/test_1.py:545` 抛 `TypeError: _warn() got an unexpected keyword argument 'once'` | — |
| 测试是否测到要求（18–20、25、32） | `test_1.py`、`test_2.py` 全文及它们与 base 的 diff；6 份日志的逐键机器比对 | 测到了三点：接受参数、第一条显示、同 slug 的第二条不显示。没测到：不同 slug 各显示一次、非 once 调用不受影响、`slug=None` | — |
| 误拒合理解（24、28） | §3 的 6 种候选 | 按消息或按（消息, slug）去重的实现会判 0。这是静态推断，确定性高 | 没做 CPU 反例 |
| 回归与 gold 完整性（26、27） | gold 逐行；`config.set_option`、`override_config`；全部 `_warn` 调用点与回调 | gold 修到了原例，并且是上游对 `control.py` 的完整改动（附录 A4）。有 3 个未测副作用（§4） | — |
| agent 开发条件（6–15） | `environment_brief.md`、环境卡、账本 `observations` | 评分侧已实测；解题侧只有镜像层面实测，正式链待验（§6） | 正式 actor 链 |
| 交付与评分边界（4、16–17、21–22、29–31） | 账本 `projection`；`setup.cfg`；`tests/conftest.py` 的作用域；隐藏测试的 import | 合法修复只需改 `coverage/control.py`；隐藏测试依赖 base 版测试辅助（§5 d） | 共享机制没有重审 |
| 题目关系与用途（5、29–30、37–40） | 同批 5 道 coveragepy 题的公开 base 中 `_warn` 的相关行 | 本题 gold 原样出现在另外 4 题的 base 中（§7） | 预训练污染无法评估 |

## 2. 需求与断言的双向映射（核心表）

| # | 公开要求 / 合理旧行为 | 公开依据 | 测试 ID / 决定性断言 | 覆盖情况 | 执行证据 / 下一步验证 |
| --- | --- | --- | --- | --- | --- |
| R1 | `_warn(..., once=True)` 不抛 `TypeError` | `user_prompt.txt:7,13-14,21` | `ApiTest.test_warn_once`（`test_1.py:545-546` 的两次调用） | 覆盖 | noop 两次 FAILED（TypeError）；gold 两次 PASSED |
| R2 | 第一条 once 警告照常写到 stderr | `user_prompt.txt:18`；`control.py:345-350` | `assertIn("Warning, warning 1!", err)`（`test_1.py:548`），只查消息子串，不查前缀和 slug 的格式 | 覆盖（断言较宽） | gold 日志捕获的 stderr：`Coverage.py warning: Warning, warning 1! (bot)` |
| R3 | 重复的 once 警告不再输出 | `user_prompt.txt:18` | `assertNotIn("Warning, warning 2!", err)`（`test_1.py:549`） | 只覆盖"同 slug、不同消息"一种情形 | — |
| R4 | **去重键** | 题面没有写。<br>支持按 slug 的线索：示例刻意用同一 slug、不同消息；docstring 写着"For warning suppression, use `slug`"（`control.py:339`）；`disable_warnings` 按 slug 抑制（`control.py:341`）；`doc/cmd.rst` 的警告一节把每条警告写成"带 XXX 可变部分的消息 + (slug)"。<br>反向线索："only once each"、"duplicate" | 同上断言，它强制按 slug 或更粗的键去重 | **歧义，而且最字面的读法与断言相反** | 静态推断；待 CE1/CE2 执行 |
| R5 | 不传 once 的调用行为不变 | 现有调用点都不传 once | `ApiTest.test_warnings` 要求 stderr 含 4 行块，其中两条 `module-not-imported` 同 slug，都要显示；另有 `test_two_getdata_only_warn_once`、`test_two_getdata_warn_twice`、`test_combining_corrupt_data`、`SourceIncludeOmitTest.test_source_include_exclusive`、`NamespaceModuleTest.test_bug_572` | 候选不动调用点时覆盖。"once 之后同 slug 的非 once 调用"没测 | noop 与 gold 各两次，全部 PASSED |
| R6 | `disable_warnings` 按 slug 抑制 | `control.py:341`；`doc/config.rst:156-158` | `ApiTest.test_warnings_suppressed`（`.coveragerc` 在构造对象时读入） | 部分：没测"已经发过警告后再 `set_option`" | gold 在这条路径上有未测的变化（§4 G1） |
| R7 | `_warnings` 记录已发出的警告 | `control.py:207-208,345` | 本文件没有断言 | 缺失。题面没要求，不算缺陷 | — |
| R8 | 回调兼容：`warn(msg)` 与 `warn(msg, slug=...)` | `control.py:437,468,485`；`collector.py:90-92`；`ctracer/tracer.c:605` 只传一个参数 | 间接覆盖：各 start / stop / combine 路径 | 间接覆盖 | — |
| R9 | `slug=None`、once 与非 once 混用、状态作用域 | 没有约定 | 无 | 没有约定，也不应测 | — |

反查：
- 决定性断言 `assertNotIn("Warning, warning 2!", err)` 的公开依据，只有"示例结构 + 仓库用 slug 标识警告"这一推断，题面文字没有直接给出。
- 其余 74 个键都是同文件的回归键，base 下就已经通过。实际阅读范围：与 `_warn` 路径相关的 7 个键逐条读过；其余键只核对了 import、fixture 和 PASSED 状态。

## 3. 替代实现与部分实现（静态推断，未执行）

| 候选 | 做法 | 预期 `test_warn_once` | 预期得分 | 判断 |
| --- | --- | --- | --- | --- |
| CE1 按消息去重 | `if once: if msg in self._once: return; self._once.add(msg)` | FAILED：第二条消息不同，会打印出 `Warning, warning 2! (bot)` | 0 | 符合"only once each"的字面读法，属于**误拒风险** |
| CE2 按（消息, slug）去重 | 同 CE1，只是 key 取 `(msg, slug)` | FAILED | 0 | 同上 |
| CE3 按 slug、独立集合 | 与 gold 的差别：不快照 config，只影响 once 调用。也可以写成 keyword-only 的 `*, once=False`，或把状态借放在 `config.disable_warnings` 上 | PASSED | 1 | 与 gold 不同的合法解，会被接受 |
| CE4 过粗的实现 | `if once: if self._once_used: return; self._once_used = True`，即第一次 once 之后，所有 once 警告都不显示 | PASSED | 1 | 无论按哪种读法，都违反了"each"（不同 slug 的警告也被压掉），属于**漏测** |
| CE5 只收参数 | 接受 `once=False` 但不做任何去重 | FAILED | 0 | 正确拒绝 |
| CE6 越界改动 | 给 `control.py:697` 的警告加上 `once=True` | `test_two_getdata_*` 失败：base 的假 `capture_warning(msg, slug=None)` 会抛 TypeError | 0 | 题面没要求改调用点，只惩罚越界改动（§5 d） |

## 4. gold 检查

- **原例**：示例中的第二条被压掉了。gold 日志捕获的 stderr 只有 `Coverage.py warning: Warning, warning 1! (bot)`。
- **范围**：只改了 `coverage/control.py`，账本 `projection.included_paths` 也只有这个文件。
  - 在复制件上应用 gold 后，blob 从 `6e59078c` 变为 `4358a541`，与补丁 index 行一致（附录 A4）。
  - M3 行的 `gold_meta.included` 只列出这个文件，所以 gold 就是上游提交对非测试文件的全部改动。
  - gold 的 docstring 写着"only show this warning once (determined by the slug.)"，这正是题面缺少的那句话。
- **未测副作用**（静态推断，都不影响评分）：
  - **G1 快照**：`_no_warn_slugs = list(self.config.disable_warnings)` 只在第一次调用 `_warn` 时取值。之后 `set_option("run:disable_warnings", ...)` 用 `setattr` 换掉整个列表（`config.py:414-435`），gold 看不到这个改动；base 每次调用都读 `self.config.disable_warnings`。
    - 例：依次执行 `_warn("a", slug="x")`、`set_option("run:disable_warnings", ["y"])`、`_warn("b", slug="y")`。base 不显示 `b (y)`，gold 会显示。
    - 公开读者的 C4 预期"base 与修复后输出相同"，对 gold 不成立。
    - 这个变化与 once 无关：任何调用 `_warn` 的路径都会触发快照。
  - **G2 once 与非 once 共用一个列表**：一个 slug 以 once 方式显示过之后，同 slug 的非 once 警告也会被压掉。
  - **G3 `once=True, slug=None`**：None 会被加入列表，之后所有不带 slug 的警告都被压掉，包括 `control.py:455,707`、`html.py:88`、`data.py:115`、`inorout.py:276`、`tracer.c:605` 发出的警告。当前快照里没有调用点传 once，所以 G2、G3 是潜伏行为。
- **结论**：gold 满足题面与测试。G1 是混进来的一个小幅旧行为变化（清单 26/27，严重度低）。本审查不以"与 gold 不同"为理由判任何候选。

## 5. R2E 专项

- **（a）非 PASSED 键**：期望里没有，75 个键全是 PASSED，所以"更完整的修复把 FAILED 翻成 PASSED 而判 0"不适用。风险在反方向：把 once 推广到调用点，会让回归键失败。
  - `test_warnings` 期望两条同 slug 的 `module-not-imported` 都显示。
  - base 的假 `_warn` 不接受 `once`。
  - 题面没要求改调用点，所以这不算误拒。
- **（b）题面报错是否出现在 noop 失败原因中**：出现了，原样出现。两份 noop 日志第 30-32 行都是 `TypeError: _warn() got an unexpected keyword argument 'once'`，位置 `r2e_tests/test_1.py:545`。
- **（c）泄漏**：
  - 题面点名了 `_warn` 和 `once`，等于直接给出修改位置。
  - 示例就是 `test_1.py:543-546` 的输入原样。
  - 去重语义没有泄漏，反而缺失。
- **（d）测试辅助、搬迁伪影、撞键**：
  - `test_1.py:24` 导入的是**仓库内的 base 版** `tests.coveragetest`。评分不会重置它，候选可以改它。它的假实现 `capture_warning(msg, slug=None)`（base `tests/coveragetest.py:267`）不接受 `once`。
  - `test_2.py` 是上游修复后的 `tests/coveragetest.py`，与 base 唯一的差别是假函数多了 `once=False`（`test_2.py:267-269`）。但它被放在 `r2e_tests/` 下，没有任何模块导入它，也没有测试方法，是一个不起作用的搬迁伪影。它只让 `RH2_SETUP_RESTORED=3`，不产生任何键。
  - 后果：在上游测试环境里，"给调用点加 once"不会因为假函数抛 TypeError 而失败；在本评分里会。这只影响越界改动（CE6）。另外，隐藏测试导入的 `tests/coveragetest.py` 候选可以改（环境卡 §3 已述的共享机制），public_hints 所说的"测试改动永不计分"对本题不成立。合法解不需要改它。
  - 撞键：无。75 个键全部来自 `test_1.py`，日志逐键解析没有重复。
  - `tests/conftest.py` 的三个 autouse fixture（`set_warnings`、`reset_sys_path`、`fix_xdist_sys_path`）不作用于 `r2e_tests/`。`setup.cfg:2` 的 addopts（`-n3 --strict --no-flaky-report --failed-first`）会作用于评分，日志里能看到 gw0 到 gw2 三个 worker。6 次运行都没有看到这两点造成影响。
  - 隐藏测试相对 base 的 `tests/test_api.py`，还改了 `test_warnings_suppressed` 的一处断言：不再要求行尾换行。这是放宽，没有影响。
- **（e）时间、随机、资源敏感**：
  - 目标键没有这类敏感点。
  - 回归键里有几处随机或时间相关代码，都不影响断言：`_init()` 按 `time.time() % 2` 选择 configure 对象（只在有 configurer 插件时才有意义，本文件没有）；随机模块名；并行数据文件名后缀含随机数。
  - 运行条件与表现：xdist 3 个 worker 跑在 2 CPU 上；峰值内存约 297–303 MB；测试段约 3.4–4.4 s。
  - 稳定性：当前材料下 noop 两次、gold 两次逐键一致，M3 的 gold 两次也一致。这只是有限证据。
- **（f）材料修订**：无，`revisions.json` 为 `[]`，不适用。

## 6. 开发需求（逐题）

| 项 | 事实 | 证据级别 |
| --- | --- | --- |
| 导入 | 评分时 `coverage` 解析到 `/testbed/coverage/__init__.py`，版本 5.0.2a1 | 评分侧实测（账本 `observations`） |
| 解释器 | `python` 指向 `/testbed/.venv/bin/python`，版本 3.7.9 | 镜像层面实测（brief） |
| 测试依赖 | 评分镜像里有 pytest 4.x（汇总行格式为 "in N seconds"）、pytest-xdist、flaky、unittest_mixins | 评分侧实测；解题侧在同一派生镜像上跑过开发探针；正式链 actor 待验 |
| 包管理 | 有 pip，但不能出网；本题不需要安装任何包 | 镜像层面实测 |
| 资产 | 不需要 | 静态 |
| 权限 | agent（uid 54321）可写 `/testbed` 和 home；补丁以 agent 身份应用，测试以 54322 运行 | 镜像层面实测 / 评分侧实测 |
| 网络 | 准备、解题、安装、测试四个阶段都不需要 | 静态；评分侧 `deny_all` 已实测 |
| 构建 | 不需要：改动是纯 Python，C tracer 只以单个参数调用 `warn` | 静态 |
| 提交边界 | 只需改 `coverage/control.py`；`.coverage` 和 `.pytest_cache` 被 `.gitignore` 忽略 | 评分侧实测（gold 的 projection） |
| 本地验证 | 可以自己写示例验证，建议在临时目录里跑，因为 `load()` 会新建 `.coverage`；公开测试可用 `python -m pytest -o addopts="" tests/test_api.py -k warn` | 静态建议，actor 待验 |
| 正式链 | 正式 actor 取来源镜像：`/r2e_tests` 所有人可读；M3 facts 记录 `fix_reachable=commit`、`commits_after_head=2401`。另外 hints 写的是 conda | 共享阻塞（环境卡 §2），待 B 线修复 |

## 7. 题目关系与用途

- 同批另外 4 道 coveragepy 题的公开 worktree 里，`coverage/control.py` 的 `_warn` 已经包含本题 gold：
  - 016af5f6、97997d2c、f5eb5f21 三题的 base 是 5.0.2a1 或 5.0.5a0，`_warn` 与本题 gold 逐行相同；016af5f6 的 `control.py:589` 还出现了首个调用者 `slug="dynamic-conflict", once=True`。
  - ea6906b0 的 base 是 6.1.0a0，`_warn` 是在此基础上演进过的版本。
  - 解题时各题容器相互独立，所以不构成解题泄漏。但划分训练集与留出评测集时，应把它们视为同族（清单 5）。
- 任务类型：私有 API 的小功能补全，题面包装成了一个 TypeError bug；改动范围是一个函数。基座成功率不从静态阅读推断。

## 8. 缺口与建议队列（交协调者安排）

1. **CPU 反例**：用当前派生镜像和 RH2 回放评分跑 CE1、CE2（预期都是 0）、CE4（预期 1）、CE3（正对照，预期 1）。目的是把误拒和漏测从静态推断变成执行证据。
2. **公开规格修订**（清单 37：改公开规格，不改测试）：在 Expected Behavior 后补一句，依据是 gold docstring 里的"(determined by the slug.)"。例如：
   > Whether a warning has already been shown is determined by its `slug`: later `once=True` warnings with the same slug are not shown, even if the message differs.

   修订后用 CE1（仍判 0，但此时它违反了题面）和 CE3（应判 1）复验。

   备选方案是改测试，让两种去重键都通过：删掉"不同消息"那条断言，改成"同消息同 slug 重复两次只显示一次"。这会偏离上游语义，也会让题面示例失去诊断作用，不推荐。
3. **可选加强**：只在修订题面时一并考虑。补一条断言"不同 slug 的 once 警告各显示一次"，可以堵住 CE4。它有公开依据（"only once each"），gold 也能通过。
4. **真实模型求解**：修订前后各做少量盲解，记录求解者选择的去重键（清单 33–36）。
5. **正式 actor 链的来源镜像泄漏**：属于共享问题，已由 B 线跟进。

## 9. 暂定处置

- `disposition.scope=static_review`，state 为 `needs_review`。
- reason：题意/测试争议。题面没有给出去重键，隐藏测试强制按 slug 去重，按消息去重的合理实现会判 0。
- 如果按 §8-2 修订题面，可以转为"静态候选待 actor 验证"。
- 唯一最值得先做的下一步：跑 CE1 与 CE4 的 RH2 回放评分，并以 CE3 作正对照，拿到误拒与漏测的执行证据，再决定是否修订题面。
- 最关键的未知项：真实求解者有多大比例会选择按消息去重，也就是误拒在实际中的发生率。

---

## 附录 A：运行证据与核对

A1. RH2 运行（`material=current`；配方 `r2e_derive_v1`；派生镜像 `sha256:81bf06a0…`；每份日志的 sha256 都已与 `run_refs.json` 核对一致）：

| 账本（行 7） | 候选 | 得分 | 匹配 | 失配键 | 日志 |
| --- | --- | --- | --- | --- | --- |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_noop.jsonl` | noop | 0 | 74/75 | `ApiTest.test_warn_once` | `…rf-all-noop-c_9844300f.eval.log`：`1 failed, 74 passed in 2.53 seconds` |
| `runs/r2e_rf_20260923/remote/ledger_r2e_all_gold.jsonl` | gold | 1 | 75/75 | — | `…rf-all-gold-c_b3411386.eval.log`：`75 passed in 2.53 seconds` |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_noop.jsonl` | noop | 0 | 74/75 | `ApiTest.test_warn_once` | `…envrepair-rer_ce6fdfd2.eval.log`：`1 failed, 74 passed in 2.14 seconds` |
| `runs/r2e_env_repair_20260924/_rerun2/ledger_gold.jsonl` | gold | 1 | 75/75 | — | `…envrepair-rer_53c27c0b.eval.log`：`75 passed in 2.16 seconds` |

四行的共同点：
- `segment_completed=true`，`num_parsed_tests=75`，`num_parsed_outside_segment=0`，`keys_equal=true`。
- `RH2_SETUP_RESTORED=3`，`RH2_SETUP_TEST_FILES=4`。
- 评分策略：2 CPU / 4 GiB / tmpfs 1 GiB，uid 54322，网络 `deny_all`。

A2. M3 独立 runner：`runs/env_overnight_20260916/M3/gold_ledger/r2e_gold_m3.jsonl` 第 23、70 行，来源镜像，gold 两次都是 `75 passed`。
- `gold_meta` 列出的是：included `coverage/control.py`，excluded `tests/coveragetest.py` 与 `tests/test_api.py`。
- 该行的 `gold_matches_git_diff_changed_lines=false`，含义未核实。在全表中，有 78 行同样排除了测试文件，但这个标志是 true，所以"排除了测试文件"解释不了它。A4 显示 `control.py` 的内容没有差异。

A3. 逐键机器比对：从 6 份日志的 short test summary 解析出 `类名.测试名`，与 `expected_output.json` 比较。
- noop 两份：只有 `ApiTest.test_warn_once` 不同（FAILED 对 PASSED）。
- gold 两份、M3 两份：与期望完全相同。
- 6 份都没有重复键，也没有 rerun 或 warnings summary 段。

A4. 文本核对：把 base 的 `coverage/control.py` 复制到 scratchpad，用 `git hash-object` 算 blob，结果是 `6e59078c6c39…`。应用 `gold.patch` 之后是 `4358a5414a21…`，与补丁 index 行 `6e59078c..4358a541` 一致。

## 附录 B：隐藏测试结构

- `r2e_tests/__init__.py` 是空文件。
- `test_1.py` 是修复后的 `tests/test_api.py`，共 1128 行、75 个键：
  - 新增 `test_warn_once`（第 542-549 行）；
  - 放宽了 `test_warnings_suppressed` 的一处断言（第 535-538 行）。
- `test_2.py` 是修复后的 `tests/coveragetest.py`，只改了 `capture_warning` 的签名并加一行注释，没有测试方法。
- 键的构成：`ApiTest` 33 个，`CurrentInstanceTest` 1 个，`NamespaceModuleTest` 2 个，`SourceIncludeOmitTest` 14 个，`ReportIncludeOmitTest` 8 个，`XmlIncludeOmitTest` 8 个，`AnalysisTest` 1 个，`TestRunnerPluginTest` 4 个，`ImmutableConfigTest` 1 个，`RelativePathTest` 3 个，合计 75 个。

## 附录 C：阅读范围

- **全文读过**：
  - 角色卡与四份方法文档；`public_read.md`。
  - 公开包：`user_prompt.txt`、`public_bundle.json`、`environment_brief.md`；`worktree_manifest.json` 的顶层字段。
  - 私有包：`hidden_tests/` 下三个文件、`expected_output.json`、`gold.patch`、`run_tests.sh`、`revisions.json`、`run_refs.json`；`grading_bundle.json` 与 `validation_bundle.json`（按字段读）。
  - 账本：上述 4 条 RH2 账本行，以及 M3 的第 23、70 行。
- **读过片段**：
  - 日志：6 份日志的头部、FAILURES 段、`test_warn_once` 的 PASSES 段和 short test summary。
  - worktree 的 `coverage/`：`control.py`（40-80、180-520、560-720 行）、`config.py`（405-440 行，另加检索）、`inorout.py`（268-282、336-396 行）、`report.py`（76-90 行）、`html.py`（84-92 行）、`data.py`（104-118 行）、`collector.py`（86-94 行）、`pytracer.py`（226-236 行）、`ctracer/tracer.c`（600-610 行）。
  - worktree 其它：`tests/conftest.py`、`setup.cfg`、`.gitignore` 读了全文；`doc/cmd.rst` 读了警告一节；`doc/config.rst` 读了 152-164 行。
  - 隐藏测试与 base 对应文件之间的 diff。
- **同批另外 4 道 coveragepy 题**：只读了 `public_bundle.json` 的 instance_id、base_commit 和标题，以及 `coverage/control.py` 中与 `_warn` 相关的行。
- **没读**：
  - diagnostics.json；unittest_mixins 的源码（不在 worktree 中）。
  - `tests/coveragetest.py` 除 diff 之外的部分，以及其余测试文件。
  - 其余 74 个回归键中，与 `_warn` 无关的断言只核对了状态，没有逐条读。
