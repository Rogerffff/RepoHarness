# L1_dvc_1 · 逐题静态审查小结

范围：iterative/dvc 17 题（ASSIGNMENT.json 顺序）。方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆的 `git show <base_commit>:<path>` / `git grep` 读取（COMMON.md 允许的只读操作），未建 worktree、未起 Docker、未实跑测试、未调模型 API。
逐题记录：`records/<instance_id>.json`。脚本在 `scripts/`：`extract.py`（抽四面材料）、`prescan.py`（逐题预扫）、`p2pcov.py`（P2P 覆盖对账）、`logscan.py`（解析污染/截断碰撞）、`idscan.py`（**216 题全量**的脆弱测试 ID 与漏收扫描）、`rootscan.py`（**216 题全量**的 root 身份失败归因）、`dvcindex.py`（dvc 35 题跨题索引）、`show.py`/`rec.py`（查看与落盘辅助）。大产物在 `runs/env_overnight_20260916/L1_dvc_1/`：`mat/`（四面材料）、`prescan.json`、`p2pcov.json`、`logscan.json`、`signals.json`、`idscan.{txt,json}`、`covscan.json`、`dvcindex.txt`。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| iterative__dvc-5822 | 题面（含完整 traceback）/gold（2 行）/F2P 三者干净对应，但 **P2P 只有 1 条**：同文件 51 条里 46 条 FAILED + 24 条 SKIPPED，根因是**安装解析到的 `pathspec` 版本与 dvc 2.0 的 `dvc/ignore.py` 不兼容**（`re.error: redefinition of group name 'ps_d'`），任何走 `dvc add` 的用例都炸。另：`tests/requirements.txt`/`test-requirements.txt` 在 base 不存在，安装被 `\|\| true` 吞掉仍记 rc=0 | needs_repair | 二分 pathspec 版本找到 `dvc/ignore.py` 可用的上界，修好后 base/gold 重跑整文件重建 P2P |
| iterative__dvc-9395 | **"合理替代解被拒"的实测反例**：F2P 两条里 `test_repro_pulls_mising_data_source` 对应题面，`test_restore_pull` 却要求题面从未提及的"repro 前把远端整份 run-cache 拉下来"，并用 `assert mock_checkout.call_count == 3` 锁内部调用次数；DeepSeek 候选（题面字面实现）ledger 记 `f2p_status={data_source: PASSED, restore_pull: FAILED}` → RESOLVED_PARTIAL。另：**gold 跑不过自己 test_patch 带来的 `test_repro_pulls_mising_import`**（pygit2 移除 `GIT_OBJ_COMMIT`，scmrepo 后端 import 失败），该条被从 F2P/P2P 两边剔除 | needs_repair | 把 DeepSeek 补丁 + gold 的 `stage_cache.pull(None)` 拼起来重跑两条 F2P；钉 `pygit2<1.14` 后单跑 mising_import |
| iterative__dvc-4185 | **gold 判 RESOLVED_NO 是纯假阴性**：P2P 常量 `test_run_with_invalid_stage_name[\]`（len 70）与运行时 ID `...[\\]`（len 71，实测 PASSED）差一个反斜杠，源于 pytest `ascii_escaped` 版本差异。另：**networkx `from fractions import gcd` 在 Python 3.9 直接 ImportError**，tests/func/test_run_multistage.py 33 条里 20 条双侧失败（含本题最相关的三条 params 用例）。题面列了 2 个问题而 gold 只修第 2 个；hints 直接给出修复代码 + base 行号 permalink | needs_repair | 镜像里 `pytest --collect-only` 核对实际 ID 并对 216 题全量对账；`networkx==2.5` 后重跑整文件 |
| iterative__dvc-1661 | **环境最干净的一题**（gold 21 passed / 0 failed / 0 skipped，P2P=20 覆盖整个 tests/test_add.py）。缺陷在题面与断言：题面是用户提问（"Is this expected?"），**可复现脚本与 state 机制说明只在不可见的 hints 里**；F2P 用 `spy(RemoteLOCAL.collect_dir_cache)` + `call_count == 1` 锁内部方法名与调用次数，memoize 类或重构类的合法解会被拒；且只断言次数不断言存进 state 的 checksum 是否正确 | needs_review | 用"给 collect_dir_cache 加 lru_cache"的替代实现跑 F2P，预期 FAILED，形成合法解被拒反例 |
| iterative__dvc-1681 | 环境干净、gold 正确、配套单元测试有正反两条 wdir 断言（默认值 `.` 与非默认 `..` 各锁一个 md5 常量）。缺陷：F2P 新增 `assertEqual(stage.dumpd()[PARAM_WDIR], ".")` **把修法钉死在 `dumpd`**，等价的 `_compute_md5` 内归一化会被判 0；gold 顺带删掉 `Stage.dump(fname=None)` 参数（范围外但无 caller 受影响）；`stage.dump()` 的 8 个调用点零回归。另：触碰文件 `tests/unit/stage.py` **不匹配 pytest 默认 `python_files`**，是"不能按文件名通配判测试文件"的具体证据 | needs_review | 写"只改 `_compute_md5`"的替代实现跑 F2P，预期被拒 |
| iterative__dvc-1712 | **本包题面质量最好的一题**（4911 字符，完整 Debug SQL 日志 + 完整 traceback）；base 里 `_to_sqlite` 在 6 处写入路径都调了、唯独查询入口 `get_state_record_for_inode` 漏掉，gold 一行修复。F2P 的"必须在方法内部修"约束**有正当理由**（只在调用点修会漏掉 `dvc/remote/local.py:706`）。短板：整个 tests/test_state.py 只有 3 条用例，P2P=2 已取满；F2P 只断言"查到非 None"不校验内容，`WHERE inode={} OR 1=1` 的假修复能过 | ready_for_probe | 跑 `WHERE ... OR 1=1` 假修复验证当前 F2P 放行；把 tests/test_add.py 纳入 P2P |
| iterative__dvc-1808 | **"要求缺失"最干净的一例**：F2P 第三段断言 `main(["remote","add","-f",name,url]) == 0`，要求实现题面从未提及的 `-f/--force` 开关，而本题 **`hints_text` 为空**——这条需求在可见与不可见材料里都不存在，只按题面实现（同名报错）的解会因 argparse `unrecognized arguments: -f` 判 0。次要：F2P 只看退出码，"先覆盖再返回 1" 的错误实现也能满分，而题面关心的正是 config 被悄悄改掉 | needs_repair | 只实现"同名报错"跑 F2P，确认第三段失败；再跑"先 _set 再 return 1"假修复确认满分 |
| iterative__dvc-1877 | 题面是 261 字符的维护者 TODO，`hints_text` 为空；F2P 逐字匹配题面没给的警告文本 `"Build cache is ignored when persisting outputs."`，并隐含要求"首次创建 stage 时不警告"（gold 用 `os.path.exists(path)` 实现）。**首次发现容器以 root 运行导致 `os.access(p, os.W_OK)` 恒 True**，3 条 `TestRunUnprotectOuts*` 双侧失败被排除（同因影响 2254、3620）。整文件耗时 **388 秒**，同文件在 0.51 版只要 14.9 秒 | needs_repair | 非 root 用户重跑 unprotect 相关用例；`--durations=20` 定位 388 秒的来源 |
| iterative__dvc-2126 | **本包最严重的题面/任务错配**：题面是"RFC：提议新增 `dvc version` 命令"，而 base 里 `dvc/command/version.py` 已完整实现该命令，gold 只是给输出加一行 `Binary: {is_binary()}`——"Binary" 这个词在题面与 hints 里一次都没出现（最近的线索只是 TODO 里一句关于 PyInstaller 的问句）。**P2P = 0**（整文件仅 2 条用例且都进 F2P），断言只查子串，`logger.info("Binary: False")` 硬编码即可满分 | reject_revision（除非重写题面） | 原样交给模型跑一次看它是否会去动 version.py；再跑硬编码假修复确认满分 |
| iterative__dvc-2141 | **F2P 验的恰好是题面没要求的那一半**：题面报告 `dvc metrics show -T` 混进了 master（用户给的两个建议还都是改文档），gold 却把三件事捆在一起（无条件 yield working tree／重命名成小写／删掉 `branches is None` 时的 active_branch）。F2P 只新增期望键 `"working tree"`（小写只在 hints 里），而题面报告的 master 混入**零覆盖**——F2P 走 `all_branches=True` 分支，gold 删掉的代码根本不执行；全仓库唯一用 `all_tags` 的测试在 `tests/func/test_gc.py`，不在评分文件里。`brancher` 的另一消费者 `used_cache`（gc/push/pull/status）也无回归 | needs_repair | 跑"只加 `yield 'working tree'`、不动 active_branch"的半修复，预期满分（题面缺陷仍在） |
| iterative__dvc-2231 | 题面有完整可复制的复现脚本、gold 复用已有 `safe_remove`、F2P 是行为级断言（`assert not os.path.exists`），质量较好。两个缺陷：(1) **networkx 漂移方向与 4185 相反**——装到的 networkx ≥2.4 删掉了 `G.node`，dvc 0.50 的 `dvc/repo/__init__.py:178` 仍在用，`checkout --with-deps` 退出码 255，唯一覆盖 `--with-deps` 的 `TestCheckoutWithDeps::test` 双侧失败被排除；(2) F2P 只用 `force=True`，忽略 `force` 直接删文件的实现能满分（比原 bug 更危险） | needs_repair | 镜像里 `networkx<2.4` 后重跑整文件；再跑"无条件 remove"实现验证 F2P 放行 |
| iterative__dvc-2254 | **本包评分设计最健康的一题**：题面简短完整、hints 为空（无信息落差）、gold 与 base 第 858 行既有写法一致、F2P 只断言返回真值；**P2P 的 8 条 `test_run_deterministic*` 有真实判别力**——`test_run_deterministic` 要求相同输入第二次仍跳过，能挡住"删掉 `stage.is_cached`"的过度修复，另 6 条从反方向钉住"输入变了必须抛 StageFileAlreadyExistsError"。注意：与 **dvc-1877 改的是同一段跳过条件**（persist 守卫 vs callback 守卫），划分必须同侧；3 条 `TestRunUnprotectOuts*` 因 root 身份被排除 | ready_for_probe | 非 root 用户重跑 unprotect 用例后补进 P2P |
| iterative__dvc-3315 | 题目小而干净、gold 用 `shlex.quote` 正解、测试阶段仅 0.18 秒（本包最快）。缺陷：F2P 逐字匹配 `shlex.quote` 的输出 `"git add 'fname with spaces.txt' 'тест' foo"`——**要求给不含空格的非 ASCII 名 `тест` 也加引号**（这是 `shlex.quote` 的 `re.ASCII` 行为，题面只说空格），且把顺序固化（测试把 base 的 `files_to_track = set()` 直接赋成 list，于是 `sorted()` 这种让输出确定化的合理改进反被拒）。两条 P2P 都是 `mock.Mock(spec=NoSCM)` 级别，**不执行被改代码**，除 F2P 外零回归 | needs_review | 跑 `if " " in path` 的题面字面实现，预期因 `тест` 失败 |
| iterative__dvc-3527 | 题面完整（含 `[Errno 30]`、两份 config、部署背景）、F2P 行为级（mock chmod 抛 EROFS 断言不抛）、P2P 取满同文件、0.18 秒。两处需裁定：(1) **gold 捆了一处范围外且零覆盖的语义收紧**——`actual & mode != mode` → `stat.S_IMODE(actual) != mode`，共享 cache 下 0o644 从"算已保护"变成"报错"，题面只字未提；(2) 把整个 `except OSError` 体改成 `return`（吞掉所有错误）可拿满分。另：本题的 `test_is_protected` 在 root 下能过（读 stat mode 位而非 `os.access`），与 1877/2254/3620 形成对照 | needs_review | 写"吞掉所有 OSError"假修复验证满分；base/gold 各跑一条 0o644 用例确认语义变更 |
| iterative__dvc-3576 | **题面与评分方向不同**：题面第 ④ 项写的是"把 `No changes.` 挪到 STDERR"（保留消息、换流），F2P 要求 `_show_diff({}) == ""`（取消消息）；按题面字面实现（改写 stderr、字符串不变）判 0。决定改成空输出的依据只在 hints 讨论里，且 hints 里两位维护者一开始意见相反。题面另外 3 项（单版本 diff／JSON 缺 old 值／错误信息）gold 一项没做。**P2P 6 条逐字比对 Texttable 输出，有真实判别力**（`return ""` 的破坏性修复会全挂） | needs_repair | 实现"写 stderr、字符串不变"跑 F2P，预期判 0 |
| iterative__dvc-3620 | 题面质量高（贴出 `remove` 与 `_chmod` 源码并直接点明"`os.chmod` 跟随 symlink 改到了 cache 文件"），gold 正确且不强制唯一实现。**但题目主题是 unprotect，而唯一直接验证它的 `tests/func/test_unprotect.py::TestUnprotect::test` 因容器以 root 运行（`os.access` 恒 True）双侧失败被剔出评分**；gold 改的是被 6 个模块使用的通用 `dvc/utils/fs.py::remove()`，P2P 只有 4 条单元测试，"删掉 `_chmod` 回退"的实现也能满分。另：`test_is_protected[symlink\|hardlink]` 在 **dvc-3527 是 P2P（旧语义）、在本题是 F2P（语义翻转）**，跨题按 ID 聚合会出错 | needs_repair | 非 root 用户重跑两个文件，比较 base/gold 逐 case 状态 |
| iterative__dvc-3665 | 三处硬伤：(1) **F2P 直接调用 gold 新抽出的私有静态方法 `Config._to_relpath(conf_dir, path)`**，题面只要求"输出用正斜杠"——在 base 既有的内嵌 `rel()` 里加 `as_posix()` 这种正确修法会 `AttributeError` 判 0，等于考"照抄 upstream 的重构"；(2) **测试 ID 里嵌了绝对签出路径**：参数取 `os.getcwd()`，冻结常量是 `test_to_relpath[/testbed-/testbed]`，workdir 一变就假阴性（与 4185 并列的另一种脆弱 ID）；(3) **P2P 漏收 11 条**在 base 与 gold 两侧都通过的用例（含 test_patch 自己改过的 `TestCmdCacheDir::test_relative_path`），本包其余题漏收均为 0，说明是上游冻结清单偏小 | needs_repair | 写"内嵌 rel() 加 as_posix()"的实现跑 F2P（预期 4 条 AttributeError）；对 216 题扫描 ID 里含绝对路径的用例 |

## 覆盖与统计

- 覆盖 **17/17** 题，全部落盘 `records/<instance_id>.json`（均为合法 JSON，字段齐全，`checks.status` 取值合法）。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 2（1712、2254）、`needs_review` 4（1661、1681、3315、3527）、`needs_repair` 10（1808、1877、2141、2231、3576、3620、3665、4185、5822、9395）、`reject_revision` 1（2126）。
- 记录 issue 数：P1 17 条、P2 20 条、P3 11 条。
- 方法与限制：全部为**静态审查**，未启动 Docker、未实跑任何测试、未调用模型 API、未连接任何远程机器。base 代码用裸克隆的 `git show <base_commit>:<path>` / `git grep` 读取（COMMON.md 允许的只读操作），未建 worktree。运行时证据全部来自 2026-09-10 阶段一离线日志与 2026-09-08 的 DeepSeek 候选 ledger。凡标 `pass` 的检查都附了文件行号或日志路径；未做的检查写 `not_checked`，证据不足写 `unknown`。

## 仓库级与跨题发现

证据文件在 `runs/env_overnight_20260916/L1_dvc_1/`：`prescan.json`、`p2pcov.json`、`logscan.json`、`idscan.{txt,json}`、`covscan.json`、`dvcindex.txt`。

### 1. dvc 的评分方式是"整文件跑"，回归保护结构上优于 mypy，但被三类环境问题侵蚀

17 题的 `eval_cmd` 全是 `pytest -rA <test_patch 触碰的完整文件列表>`（例：`pytest -rA tests/func/test_run_multistage.py tests/unit/dependency/test_params.py`），**没有 `-k` 选择器**。因此 P2P ≈「这些文件里在 base 与 gold 两侧都通过的全部用例」，中位数 18 条，最多 51 条（1877）。这和 mypy 那种「diff 邻接 + `-k` 子串过选、14/40 题 P2P 为空」是两种完全不同的机制；dvc 这边只有 1 题 P2P 为空（2126，因为整个测试文件只有 2 条用例且都进了 F2P）。

代价是这份保护被三类环境问题直接削掉：

- **依赖版本漂移，三个方向各不相同**（每个都有实测日志）：
  - dvc 2.0（5822）：装到的 `pathspec` 给每条 `GitWildMatchPattern` 生成同名捕获组，`dvc/ignore.py:43-44` 把多条 pattern 拼成一个正则时 `re.error: redefinition of group name 'ps_d'` → tests/func/test_api.py **51 条里 46 条 FAILED**，P2P 只剩 1 条。
  - dvc 1.1（4185）：networkx **太旧**，`networkx/algorithms/dag.py:23` 的 `from fractions import gcd` 在 Python 3.9 上 ImportError → tests/func/test_run_multistage.py 33 条里 20 条双侧失败，包括本题最相关的三条 params 用例。
  - dvc 0.50（2231）：networkx **太新**，≥2.4 已删 `G.node`，而 `dvc/repo/__init__.py:178` 还在用 → `checkout --with-deps` 退出码 255，唯一覆盖该开关的用例双侧失败。
  - dvc 2.56（9395）：pygit2 删了 `GIT_OBJ_COMMIT`，scmrepo 的 pygit2 后端 import 失败 → `test_repro_pulls_mising_import` 在 gold 侧永久 FAILED（这是 gold 自己 test_patch 带来的用例）。
  另外 5822/4185 的安装阶段都有 `ERROR: Could not open requirements file ... 'tests/requirements.txt'`、4185 还有 `ERROR: Could not find a version that satisfies the requirement pyyaml==5.4.1`，但因为安装行用 `|| true` 与 `;` 串联，**`rc_install` 仍记 0**。
- **评分容器以 root 执行测试**（ledger 记 `"exec_user_test": "root"`）：`os.access(path, os.W_OK)` 对 root 恒为 True，dvc 的 protect/unprotect（只读权限位）语义整体失效。本包 7 条用例因此双侧失败被剔出评分：1877 与 2254 各 3 条 `TestRunUnprotectOuts{Copy,Symlink,Hardlink}::test`，3620 的 `tests/func/test_unprotect.py::TestUnprotect::test`。**最刺眼的是 3620——它的题目主题就是 unprotect，而唯一直接验证 unprotect 的功能测试被环境问题去掉了。** 对照组：3527 的 `test_is_protected` 在 root 下能通过，因为它读的是 stat 的 mode 位而不是 `os.access`；也就是说只要把测试用户换成非 root，这 7 条都有希望恢复。**规模已量化**（`scripts/rootscan.py`）：对 181 个有 gold 日志的题扫描"失败断言里直接出现 `os.access(` "，全语料只命中 **3 题，全部在本包**（1877、2254、3620），且这 3 题 gold 侧的失败用例 **100% 由这一条造成**（3+3+1=7 条）。换句话说，改非 root 在 216 题尺度上只能挽回 7 条用例，但对 dvc-3620 而言那是它唯一的主题级功能测试。
- **成本极不均匀**：同一个 `tests/func/test_run.py`，0.35 版（1877）跑 **388 秒**，0.51 版（2254）只跑 **14.9 秒**，差 26 倍；其余题多在 0.2–45 秒。原因未查（`not_checked`）。

### 2. 参考清单里"环境相关的测试 ID"——216 题全量扫描（`idscan.txt`）

对全部 216 题的 `fail_to_pass ∪ pass_to_pass` 做了模式扫描，结论比较干净：

- **反斜杠 ID：280 条，覆盖 9 题**；其中 4 题的常量与运行时对不上：`iterative__dvc-4185`（1 条）、`modin-project__modin-6780`（3）、`pandas-dev__pandas-48106`（3）、`pandas-dev__pandas-50319`（1）。机理是 pytest 的 `ascii_escaped`：参数值里的单个 `\` 在 nodeid 里变成 `\\`（dvc-4185 的常量 len=70、运行时 len=71，实测日志 `test_output.txt:2725` 记 PASSED）。另外 5 题（dask-10972/6818、modin-5940/6937、pydantic-8977 的一部分）常量与运行时一致，不受影响。
- **非 ASCII ID：9 条，覆盖 6 题**（moto-5417/5545/5562/5701/6308 的 `💩`/`unîcode`，pydantic-8977 的 `\x81`），同属 `ascii_escaped` 机理。
- **两类合计命中的 10 题，`task_signals` 里的 `fragile_reference_id` 全部为 True，且 gold 判定全部是 `RESOLVED_NO`，`f2p_missing=0` 而 `p2p_missing≥1`** —— 也就是说这 10 题（181 个有日志的题的 5.5%）的 gold 失败**完全由 ID 转义不一致造成，题目和 gold 本身没有问题**。这 10 题恰好就是 `task_signals_swegym.json` 里 `fragile_reference_id=True` 的全部题目——本次是独立复核并给出了具体机理与可核对的长度差；另有 5 题（MONAI-1121、MONAI-3205、moto-4799、moto-4833、modin-5940）gold 也判 RESOLVED_NO 但不属这一类，需要单独归因（本包未查，`not_checked`）。
- **ID 里嵌绝对签出路径：全 216 题只有 `iterative__dvc-3665` 一题**（`test_to_relpath[/testbed-/testbed]`，参数取 `os.getcwd()`）。这是与转义问题机理不同的另一种脆弱性：workdir 一旦不是 `/testbed`（换挂载点、换镜像布局、宿主机复现）就假阴性。（扫描里 dvc-5188 的两条是 `gdrive://root/test` URL，属误报。）
- **参考清单内部按解析器口径（第一个空白前）的同名碰撞：0 题**。1293 条"方括号不配对"的 ID（覆盖 35 题）是上游冻结时就被同一个 parser 截断过的产物，与评分时的截断口径一致，因此自洽，没有造成歧义。

### 3. `pytest -rA` 的 SKIPPED 行丢掉测试身份（`logscan.json`、`covscan.json`）

pytest 的跳过摘要格式是 `SKIPPED [N] path:line: reason`，而 `swegym_parsers.parse_log_pytest`（`rh2/src/repoharness2/envpack/swegym_parsers.py:45-57`）取 `test_case[1]` 作为键，于是键变成 `[N]` 而不是 nodeid。实测：

- 181 个有 gold 日志的题里，**19 题**（MONAI/conan/dask/getmoto/iterative/modin）的 SKIPPED 条目共 **41 条**全部丢失身份；dvc-5822 一题就丢了 24 条（`SKIPPED [6] ... gs tests not enabled`、`SKIPPED [12] ... no docker installed`、`SKIPPED [6] ... gdrive tests not enabled`——注意两组 `[6]` 还会互相覆盖）。
- **唯一保留 nodeid 的是 6 道 pydantic 题**，因为它们的 `eval_cmd` 是 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header`，`-vv` 把状态放在行尾，正好被 `parse_log_pytest_pydantic` 的 `elif line.endswith(x)` 分支接住。
- 后果：`scoring.py:24` 声明的"SKIPPED 不进成功/失败任何一桶"对其余 8 个仓库**不可达**——被跳过的参考测试会落进 `reference_missing`，按"缺席计失败"处理。实测印证：**181 题里 `reference_skipped` 实际非空的条数是 0**。
- 同一个 parser 还会把日志行当成测试结果：本包 13 题的 status_map 里有 `ERROR: Could not ...` → 键 `Could`、`ERROR dvc.remote.base:base.py:304 ...` → 键 `dvc.remote.base:base.py:304` 之类的垃圾键（`logscan.json` 全量）。当前没有一条与 F2P/P2P 撞名，但这是候选可控 stdout 的一个注入面（现行 v2 评分要求 `>>>>> Start/End Test Output` 切段，已收窄；阶段一日志里没有这对标记，所以整份日志都被解析了）。

### 4. P2P 漏收：真正的漏收很罕见，dvc-3665 是异常值（`covscan.json`）

把 181 题的 gold 侧 `status_map` 里 PASSED 的 nodeid 与 `F2P ∪ P2P` 对账：只有 **13 题**有"通过但未评分"的条目，合计 34 条。其中 **8 条是上面第 2 条说的 ID 转义镜像**（运行时那个转义后的 ID 当然不在清单里），剩下的真正漏收只有两题：**`iterative__dvc-3665`（11 条）** 与 `dask__dask-8820`（4 条）。dvc-3665 漏掉的包括 `TestExternalCacheDir::test`、`TestSharedCacheDir::test`、`TestCacheLinkType::test`、`test_shared_cache[*]`、`test_partial_push_n_pull` 等，**而且其中 `TestCmdCacheDir::test_relative_path` 正是 test_patch 自己改过的那条**。结论：上游冻结的 P2P 在绝大多数题上确实等于"base 侧通过集"，不需要整体重建；**需要单独补的是 dvc-3665 和 dask-8820**。

### 5. 题面与评分的落差：dvc 的主要缺陷不在环境，而在"题面说的和测试考的不是一回事"

17 题里有 **7 题**的 F2P 要求无法从公开材料推出，形态分四种：

| 形态 | 题 | 具体 |
| --- | --- | --- |
| 题面与 base/gold 不是同一任务版本 | 2126 | 题面是"提议新增 `dvc version` 命令"，base 里该命令已完整实现，gold 只加一行 `Binary:` 字段，而 "Binary" 在题面与 hints 里一次都没出现 |
| 要求缺失（hints 也没有） | 1808 | F2P 要求 `dvc remote add -f`，题面没提，`hints_text` 为空 |
| 方向不同 | 3576、2141 | 3576 题面要"把 `No changes.` 挪到 STDERR"、F2P 要"返回空串"；2141 题面报告 master 混入、F2P 只验 hints 里才有的 `Working Tree`→`working tree` 重命名，而 master 混入零覆盖 |
| 白盒断言锁实现 | 9395、3665、1661 | 9395 的 `mock_checkout.call_count == 3`（DeepSeek 候选实测因此只得 RESOLVED_PARTIAL）；3665 直接调 gold 新抽出的私有静态方法 `Config._to_relpath`；1661 用 `spy(RemoteLOCAL.collect_dir_cache)` + `call_count == 1` |

其中 **9395 是本夜唯一一个有实测反例的**：`docs/.../env_probe_20260909/ledger/cc_candidate_grading.jsonl` 记 `f2p_status={test_repro_pulls_mising_data_source: PASSED, test_restore_pull: FAILED}` → `RESOLVED_PARTIAL`。DeepSeek 的补丁实现的正是题面字面要求（拉缺失的数据源），挂在题面从未提及的"repro 前把远端整份 run-cache 拉下来"＋内部调用次数上。

另外两条正面样本：**2254 的 P2P 有真实判别力**（`test_run_deterministic` 要求相同输入第二次仍跳过，能挡住"删掉 `stage.is_cached`"的过度修复，另 6 条从反方向钉住"输入变了必须抛 `StageFileAlreadyExistsError`"）；**3576 的 6 条 P2P 逐字比对 Texttable 输出**，`_show_diff` 一律返回空串的破坏性修复会全挂。dvc 并非普遍缺乏判别力，问题集中在题面一侧。

### 6. 数据划分约束（`dvcindex.txt`，覆盖 dvc 全部 35 题）

- **共享 gold 文件**：`dvc/stage.py` = {1681, 1877, 2254}（全在本包，且 **1877 与 2254 改的是同一段 `if not ignore_build_cache and stage.is_cached:` —— 一个加 persist 守卫、一个加 callback 守卫，2254 的 base 里能直接读到 1877 的参考解**）；`dvc/remote/local.py` = {1661, 3527}；`dvc/scm/git/__init__.py` = {3315, 3677, 5148}；`dvc/command/remote.py` = {1808, 3794}；`dvc/command/metrics.py` = {3576, 5839}；`dvc/ignore.py` = {4066, 4166}；`dvc/utils/__init__.py` = {4778, 4961}。
- **共享 test_patch 文件**：`tests/unit/remote/test_local.py` = {3527, 3620, 5336}——**注意 `test_is_protected[symlink|hardlink]` 在 3527 里是 P2P（旧语义 `assert not is_protected(foo)`），在 3620 里被 test_patch 翻转成 F2P（`assert is_protected(foo)`）；任何按测试 ID 跨题聚合的工具都会把两者混为一谈**。其余：`tests/func/test_run.py` = {1877, 2254}；`tests/func/test_remote.py` = {3665, 3794}；``tests/unit/command/test_metrics.py`` = {3576, 4124, 5839}；`tests/func/test_ignore.py` = {4066, 4125, 4166}；`tests/unit/scm/test_git.py` = {3677, 5148}。
- **base_commit 极近的相邻对**（同一条 dvc 历史上，后一题的 base 已含前一题的修复）：4166 → **4185 仅 3 个提交**；3665 → 3677 仅 4 个；9391 → **9395 仅 6 个**；5822 → 5839 仅 8 个；3315 → 3527 仅 10 个。这些对必须同侧。

## 最值得用户裁定的 3 个问题

1. **这 10 道被 ID 转义判成 RESOLVED_NO 的题怎么救？** 已确认它们（dvc-4185、modin-6780、pandas-48106、pandas-50319、moto-5417/5545/5562/5701/6308、pydantic-8977 的一部分）失败纯粹是 pytest `ascii_escaped` 与冻结常量不一致，题目和 gold 都没问题，占 181 题的 5.5%。两条路：**(a) 评分时对参考清单与运行时 ID 同时做一次规范化**（对 `[...]` 段做 `encode("unicode_escape")`），实现便宜但有把本来就不同的两条参数化用例合并的风险；**(b) 按镜像里实际的 pytest 版本重新采集一次参考清单**，更准但要为这 10 题各跑一次 collect。另外 dvc-3665 的 `test_to_relpath[/testbed-/testbed]` 是独立的第三种形态（ID 里嵌绝对签出路径），(a)(b) 都救不了，需要固定 workdir 或给参数加 `ids=`。**选 (a)、(b)，还是先按 (b) 修这 10 题再把 (a) 作为长期兜底？**

2. **评分容器要不要换成非 root 执行测试？** dvc 有一整类"只读权限位"语义的测试（protect/unprotect）在 root 下必然失败，本包 7 条用例因此被剔出评分，其中 dvc-3620 的题目主题就是 unprotect、而唯一的功能测试正好是被剔掉的那条。换非 root 会牵动镜像准备、挂载权限、conda env 可写性和 RH2 的控制面权限布置（`manager.py` 里那套 sticky 目录与 official test 文件在位判据都是按当前身份设计的），不是小改动。**是接受"dvc 的权限类测试不参与评分"，还是把非 root 执行列为一个独立的接线任务？** 量化后收益并不大：全语料只有 3 题 7 条用例受影响（且都在本包）。所以我倾向的答案是**不为此改整条链路**，而是给这 3 题单独处理——最省事的是在 dvc-3620 的 `tests/func/test_unprotect.py` 上验证一次非 root 结果，若确认能恢复，就把"该题用非 root 执行"作为题级配方例外，而不是全局默认。若用户希望彻底消除这类失真，再考虑做一次对照实验（`useradd -m t && chown -R t /testbed && su t -c pytest`）评估全局切换的成本。

3. **题面与评分不一致的 7 题怎么处置？** 我给的建议是 2126 `reject_revision`（题面与任务版本完全错配，且 P2P=0、`logger.info("Binary: False")` 硬编码即可满分），1808/3576/2141 补题面（各一句话就能补齐：`-f` 开关、"无差异时不输出任何内容"、"master 不该出现在 `-T` 结果里且顺便改小写"），9395/3665/1661 改断言（把内部调用次数/私有方法名换成行为级断言）。但这三类的代价不同：补题面改的是可见输入、会改变任务难度分布；改断言等于修改上游测试、要重新确认 gold 仍通过。**是统一按"能补题面就补题面、补不了才改断言"处理，还是把需要改断言的三题直接排除在训练集之外、只留作评测？** 另外 dvc 有 5 题的关键信息（根因判断、维护者裁定、复现脚本）躺在不可见的 `hints_text` 里（1661、1681、1712、2141、3527），**hints 里属于"报告者补充的复现步骤"的部分要不要并入题面（而把"维护者直接点名修复位置"的部分继续隐藏）？** 这是一个可以统一执行的规则，但需要拍板。
