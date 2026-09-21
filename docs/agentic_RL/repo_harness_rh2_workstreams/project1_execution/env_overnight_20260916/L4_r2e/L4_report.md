# L4 报告：R2E 48 题事实、风险分层与方案 A 接入前的待决问题

日期：2026-09-16 夜 · L4 · 全静态分析（未起容器、未连远程机器、未调模型）。
产物：`r2e_tasks_48.json`（清单）、`r2e_task_facts.json`（逐题事实）、`L4_r2e_adapter_card.md`（来源适配器一致性卡）、`machine_checks.md`（机器待查清单，M3 取用）、`build_tasks_48.py` / `build_task_facts.py`（可重跑的生成脚本）。

## 1. 48 题清单核对

**结论：确实是 48 道 R2E，不是跨来源候选表。**

- 旧 24（`group=core24`）来自 `r2e_ledger_v3.jsonl` 的 24 个 `commit_hash`；新 24（`group=night_expansion24`）来自 `runs/env_probe_stage1_20260910/r2e_expansion_preparation/candidate_manifest.jsonl`。两边**交集为 0**，并集 48。
- 48 题 `source` 全部是 `R2E-Gym/R2E-Gym-Subset`，`source_revision` 全部是 `e8b9fcbce43eaca0dc2c0d4798ee6f3e965f590a`。
- 与协调者给的 `r2e_images_48.txt` **逐条相等**；48/48 满足 `image_ref == namanjain12/<repo>_final:<commit_hash>`。
- 仓库分布：numpy 7、orange3 7、pandas 7、pillow 7、aiohttp 5、coveragepy 5、datalad 5、scrapy 5。
- **易混淆点**：`docs/.../b_probe_preparation_20260909/candidate_manifest.jsonl` 里 48 行是 **24 SWE-Gym + 24 R2E**，按 `source` 过滤后才是旧 24；这份文件不能直接当 R2E 48 题清单用。核对字段与逐项结果写在 `r2e_tasks_48.json` 的 `reconciliation`。

## 2. 风险分层计数

分层依据是 `r2e_task_facts.json` 的 `risk_flags`：

| 层 | 含义 | 数量 | 题 |
| --- | --- | --- | --- |
| **T1** | 来源自身已经给不出正确信号（gold 拿不到 1，或入口不是 pytest） | **3** | coveragepy `016af5f6`（期望 FAILED 实测 PASSED）、datalad `58ba5165`（隐藏测试 import 被 gold 排除的文件）、pillow `3ac9396e`（`unittest_custom_runner.py`，非 pytest 入口） |
| **T2** | 期望映射里带非 PASSED 状态，或隐藏测试 import 了 gold 排除的文件 | **20** | pandas 全 7 题、scrapy 3、datalad 3、aiohttp 2、orange3 2、pillow 2、coveragepy 1 |
| **T3** | 只有"需要记录但不直接影响判分"的事实（隐藏测试 import 仓库测试模块、镜像自带脏树、期望键带 ANSI、parser 丢弃 SKIPPED/XFAIL、只跑过一次） | **17** | pillow 4、orange3 5、numpy 3、scrapy 2、aiohttp 1、coveragepy 1、datalad 1 |
| **T4** | 本轮静态证据里没有发现已知风险 | **8** | numpy 4、aiohttp 2、coveragepy 2 |

按批次：旧 24 = T2 10 / T3 6 / T4 8；新 24 = T1 3 / T2 10 / T3 11。
**T1 只出现在新 24、T4 只出现在旧 24，主要是证据覆盖不均，不是难度差别**：旧 24 没有镜像内隐藏测试快照，`hidden_tests_*` 与 `image_ships_dirty_tracked_files` 两类旗标在旧 24 上天然查不出来；新 24 的 T1 之所以存在，是因为只有新 24 跑过那两次 gold reward 0。`static_coverage`：新 24 = `mostly_complete` 24 题，旧 24 = `partial` 24 题。**T4 只表示"本轮没发现"，不能读成 pass。**

单项计数（逐题证据在 `r2e_task_facts.json.flag_counts`）：

- `gold_excludes_test_files` 48/48（结构性：gold 按 Prime 规则排除所有测试路径）
- `expected_has_FAILED` 13、`expected_has_ERROR` 8（合计 20 题、93 个非 PASSED 期望键 / 总 2,650 键）
- `hidden_tests_import_repo_test_modules` 16/24（只在新 24 可查）
- `hidden_test_imports_gold_excluded_file` 2（datalad `58ba5165` 已失败；coveragepy `5dbbe143` 潜伏）
- `image_ships_dirty_tracked_files` 6/24（只在新 24 可查）
- `expected_keys_ansi` 6（全是 pillow）
- `parser_drops_skipped_or_xfail` 14（单次 gold 运行合计 38 个用例被丢弃）
- `gold_reward_0` 2、`non_pytest_runner` 1、`single_attempt_only` 22
- `noop_reward_1`、`expected_key_collision`、`*_missing_keys`、`*_extra_keys` 均为 **0**（96 个 gate 组的 `n_missing/n_extra` 全是 0）

## 3. 本轮最值得注意的事实

1. **期望映射里的非 PASSED 状态几乎全是环境/抽取缺陷的快照，不是题目语义。** 58 个 ERROR 键全部是 `fixture 'X' not found`（pandas 7 题 + orange3 1 题）——测试被抽到 `/testbed/r2e_tests/` 后仓库 `conftest.py` 不再生效。FAILED 键里也大量是 py2→py3 迁移残留、C 扩展没构建、测试资产缺失。**把环境修好会让这些题的 gold 从 1 掉到 0。**
2. **镜像初态不是干净树，而且恢复"干净"会弄坏环境。** aiohttp 3 题把 `asyncio.async` 改成 `asyncio.create_task` 留在未提交状态，pandas 3 题删了 `pyproject.toml`。任何 `git reset --hard` / `git checkout .` 都会破坏可运行性；候选 delta 也不能用 `git diff HEAD`。rh2 现有的 baseline census 路线正好正确，不要为 R2E 改成 git-based。
3. **仓库自带测试目录是可写的评分控制面。** 评分 setup 只恢复 `/testbed/r2e_tests`，不恢复仓库自带测试/helper；而 16/24 新题的隐藏测试 import 了 `datalad.tests.utils_pytest`、`tests.coveragetest`、`Orange.widgets.tests.base`、`pandas.util.testing` 这类模块。改写它们就能直接操纵判分，SWE-Gym 靠 `test_patch` 全量恢复挡住了，R2E 没有对应机制。
4. **有效信号只有一个测试，噪声面最大 323 个键。** noop 与期望的差异键数：1 个 → 33 题，2 个 → 11 题，3/6/15 个 → 各 1/2/1 题。reward 是整张映射的逐键与，任何无关用例抖动都把 1 变成 0。
5. **SKIPPED / XFAIL 被 parser 静默丢弃，14/48 题受影响（单次运行 38 个用例）。** 跳过原因基本都是环境条件：`Missing SciPy requirement`（pandas 3 题，其中 19c5eea5 一条就盖住 9 个用例）、`C based HTTP parser not available`（aiohttp）、orangewidget 的 GUI 判定（orange3 5 题）。上游用同一 parser 生成 expected，所以两侧都不在、正常不影响判分——但**只要我们把环境补齐，键数就变，`len(parsed) != len(expected)` 直接判 0**。而且 pytest `-rA` 的跳过行连测试 id 都没有，想支持也恢复不出名字。
6. **pillow 的 6 题在 Prime 原版 parser 下 reward 恒为 0。** 期望键 100% 带 `\x1b[1m…\x1b[0m`，而 Prime 的 `_decolor` 只删 `[数字m` 不删 ESC 字节，日志侧却已经被完整去色 → 两侧永不相等。我们的 `r2e_probe/0.3` 做了对称去色才拿到 1。**这不是 bug fix，是我们和来源的口径分歧，必须显式定版本。**
7. **题面与隐藏测试的映射在 1 题上是显式的。** 扫描 48 个 `problem_statement`，5 题里出现测试样标识；其中 aiohttp `240da100` 的复现片段逐字给出了 `class ProxyConnectorTests` / `def test_request_port`，而这正是该题 noop 与期望唯一不同的那个键。R2E 的题面由 commit + 测试 diff + 执行结果反译生成，复现片段像测试代码是设计使然，所以这不是强泄漏；但它说明"题面不提测试函数/文件"只是生成 prompt 的要求，不是实测保证（`O03_r2e_gym.md` §2.3 已提示过这一点）。逐题结果在 `r2e_task_facts.json.public_statement_scan`。

## 4. 方案 A 接入前必须先决定的问题

以下都是用户/决策级问题，本包不替代决定；每条给出可选项与判断依据。

### Q1（最优先）期望里的 FAILED/ERROR 在我们的条件下变成 PASSED，算什么？

**证据**：coveragepy `016af5f6` 已经实际发生（期望 `MockingProtectionTest.test_os_path_exists=FAILED`，我们的容器里 PASSED，gold reward 0）。58 个 ERROR 键只要我们补上 conftest 就会全部翻转。20/48 题受影响。
**而且问题不只是状态翻转，还有键集变化**：14 题的 SKIPPED/XFAIL 用例两侧都不在映射里（§3 第 5 条），补上 scipy / 构建 C 扩展会让它们重新出现 → `len(parsed) != len(expected)` → 0。所以 Q1 的任何选项都要同时回答"键集怎么对齐"，不能只处理状态。
**可选项**：
- (a) **按来源原样判**：严格精确匹配，"环境变好"就扣分。好处：与 Prime/R2E 官方口径一致，reward 可复现；坏处：训练信号里混进"不要修好环境"的反向激励，并且我们一旦升级镜像/依赖，reward 分布会整体漂。
- (b) **把非 PASSED 期望键剔出参考集**，只对 PASSED 键做精确匹配。好处：去掉环境噪声；坏处：这是**任务修订**（清单第 37 项），结果不能冒充原版分数；且 datalad `16c1ffc3` 这类题剔完只剩 3 个键。
- (c) **本地重验证生成修订版 expected**（在我们的条件下跑 noop+gold 各 N 次，取稳定态）。好处：与 P4"本地重验证参考集"一致；坏处：成本最高，且要先定 N 与稳定判据。
**一条支持 (b) 的具体证据**：把 20 题的 noop 判别键（noop 与期望不同的那些键）逐一查过，**19/20 题的判别键期望值都是 PASSED**，唯一的例外正是 coveragepy `016af5f6`（判别键之一是期望 FAILED 的 `MockingProtectionTest.test_os_path_exists`）。也就是说剔掉非 PASSED 键在这 19 题里**不会削掉有效信号**，只会去掉噪声；代价是键数变少（datalad `16c1ffc3` 从 8 键降到 3 键）。
**建议的判断顺序**：先在机器上把 20 题的非 PASSED 键逐个归因（machine_checks M-01/M-10 能拿到 conftest 与 fixture 事实），再决定；在归因完成前**不要**把这 20 题放进训练题单。

### Q2 parser 的 ANSI 口径按 Prime 原版还是按我们的对称修法？

> **勘误（2026-09-20，B 线 Claude）**：下文关于"Prime `_decolor` 只删 `[数字m`、不删 ESC，pillow 6 题按原版 gold 恒为 0"的说法是误读，已撤回。固定源码 `prime-envs@c4d04dfe…/environments/swe/r2e_gym/r2e_gym/taskset.py` 的正则是 `\x1b\[\d+m`（ESC 是源文件里的不可见字节）；A 线用固定源码的三个纯函数重放 336 份既有日志，与本地 runner 的 reward 全部相同，pillow 六题 24 次 gold 全为 1。见 [R2E 接线计划复核](../../r2e_grading_wiring_review_20260920/README.md) R1 与 [09-09 远端核查 §3.1](../../env_probe_20260909/codex_remote_check_20260909.md)。原文保留不改。

影响 pillow 6 题（`2b061b68 / 2d01f7d0 / 3a61c9e9 / 4bc64835 / a682ceaf / f9d3ee0f`）。选 Prime 原版 → 这 6 题 gold 恒 0，等于放弃；选对称修法 → 与官方分数不可比，必须在报告里带 `normalization_version`。本包建议选对称修法并显式标注，但这是**改变了来源判定**，属清单第 37 项的"接入修复"还是"任务修订"需要拍板。

### Q3 泄漏清理做到什么程度？

48/48 的修复提交对象在镜像 git 库里可达，HEAD 之后还有 710–31,448 个提交、83–327 个 ref、77–289 个 tag，且 `remotes=1`。
可选项：(a) 派生镜像，重写 git 历史只保留 HEAD 及以前；(b) 保留历史但删 refs/tags/remote（对象仍在，`git cat-file` 还能取）；(c) 直接删 `.git`（会破坏依赖 git 的测试与 versioneer 类构建，pandas 三题风险最高）。
需要 machine_checks M-05/M-09 的结果（`git branch --contains`、`git ls-remote` 能否成功）才能判断每个选项的实际收益。**在清理方案落地前，R2E 不适合作为训练来源**——这条在 2026-09-15 的决策包 §5 已经写明，本轮只是补齐了泄漏面的量化。

### Q4 `/r2e_tests` 与 `run_tests.sh` 的搬运边界

Prime 只搬走 `/r2e_tests`，`run_tests.sh` 留在工作区。rh2 要不要一起搬走？搬走 → 与来源入口不一致，需要自己合成等价命令（那 1 题非 pytest、7 题要 xvfb）；不搬 → agent 可改评分入口。建议搬走并在评分时恢复原文 + 校验 digest，但这需要 M-02 的权限事实支撑。

### Q5 仓库自带测试模块要不要恢复？

R2E 没有 `test_patch`，所以没有"官方恢复清单"。可选项：(a) 什么都不恢复（现状，漏洞见适配器卡 §7.3）；(b) 按隐藏测试的 import 闭包，把被 import 的仓库测试模块在评分前恢复到 base 版本；(c) 把整棵 `tests/` 恢复到 base。(b) 需要先有每题的 import 清单——新 24 已有，旧 24 要等 M-01。注意第四组 §0/§6.5 的决定是"额外排除默认为空"，本项属于**恢复**不是**排除**，不与那条决定冲突，但要单独立项。

### Q6 是否接受"33/48 题只有一个有效测试"的信号宽度

这不是接入阻塞，但会影响这批题在训练里的价值与 flakiness 容忍度。需要与 Q1 一起看：如果按 (a) 原样判，一个无关键抖动就清零，而有效信号只有一个键。

## 5. 未完成与未检查

- 旧 24 的隐藏测试内容、初态脏树逐文件清单、期望键的原始 ANSI 逐键计数：`machine_checks.md` M-01 / M-06。
- node id 折键碰撞：4 个双文件题已做 AST 级检查（无跨文件同名），参数化展开后仍要实跑收集确认：M-11；旧 24 连测试文件个数都不知道。
- venv 属主/可写性、修复提交可发现性、默认网络下的出网：M-03 / M-05 / M-09。
- `probe_unrelated` gate（无关补丁不得给分）**48 题一次都没跑过**；`r2e_probe.py` 有实现，账本里只有 noop/gold。
- 重复稳定性：旧 24 各 3 次一致，新 24 22 题只跑过 1 次、2 题跑过 3 次。flakiness 记 `unknown`，不因"没看到抖动"写 pass。
- 合法替代解 / 错误解的双向验证（清单第 24、25 项）本轮完全没做，记 `not_checked`。R2E 造题时测试可见 gold，这两项风险偏高。

## 6. 与既有记录的关系

- 方案 A 的契约字段与 `expected_map_matches` **已在工作区实现但未提交**（`git show HEAD:rh2/src/repoharness2/contracts/grading.py` 里没有 `grading_semantics`）。本包没有改动 `rh2/src` 任何文件。`rh2/src` 里目前还没有 R2E 的 parser、taskset ingest 或入口执行代码。
- 本报告不修改 `env_data_eval.md` / `infra.md`；按 COMMON.md，夜间产物只落在本包目录。
