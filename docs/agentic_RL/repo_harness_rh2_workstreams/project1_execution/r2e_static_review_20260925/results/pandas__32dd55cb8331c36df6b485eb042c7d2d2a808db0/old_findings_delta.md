# pandas__32dd55cb8331c36df6b485eb042c7d2d2a808db0：旧结论核对（读历史后）

- 角色：R2E 私有主审，2026-09-25。前稿是 `analysis_before_history.md`（协调者已原样保存，本文不改它）。T1、T2、C1–C4、`W/`、`H/` 的含义沿用前稿。
- 读取的历史：按 `history/.../refs.json` 打开了以下文件：
  - 环境阶段逐题记录：`screening_record.json`、`findings.md`、`facts.json`；
  - `known_issues.json`：列出的两族，另外扫了与本题机制相关的 5 族；
  - `decisions.md`：E09、E10、E16、E21、E24、T0-3、T0-4、T0-6 各行；
  - `results_20260924.md`、材料修订提案、复现脚本、P3 包 README。
- 读取的原始证据（上述文件所引）：
  - `p3/fixture_check/` 下本题的 `result.txt` 与 `inner.sh`；
  - `p3/dev_probe/` 下本题的 `agent_probe.log` 与 `root_init.log`；
  - `derived7/` 下本题的 `facts.json`；
  - R-f gold 日志：只用来比较键集合。
- 没有打开：`analysis_b3.json`、`reconcile.json`（汇总文件，本次核对不需要）。

## 1. 逐条核对

| # | 旧主张（出处） | 判定 | 新的决定性证据 |
|---|---|---|---|
| H1 | 13 个期望 ERROR 键全是隐藏测试搬出原目录后 fixture 不可达；结果确定，与参考一致（findings；R06 previous；P3 README §2.1；known_issues `test_material:pandas_fixture_unreachable`） | 确认 | R-f noop 日志 L33-132 有 13 条 `fixture '…' not found`。M3 a1/a2 都是 `79 passed, 1 skipped, 13 errors`。pytest 只沿 rootdir（`/testbed`）到 `r2e_tests/` 这条路径加载 conftest，而工作树顶层没有 `conftest.py` |
| H2 | fixture 可达时，base 公开文件在原位的同名测试全部 PASSED，整个文件 91 passed / 1 skipped（提案；P3 README §2.1） | 确认 | `runs/r2e_env_repair_20260924/p3/fixture_check/pandas__32dd…/result.txt`：`PT_RC=0`、`91 passed, 1 skipped`，12 个测试名共 13 项全部 PASSED（root 身份、一次性容器、无网络） |
| H3 | r2e-mr-016 从 base conftest 链原样摘出 7 个 fixture，不加 autouse/hook，不导入工作区 conftest；第一版草稿漏了 `int_frame`、`mixed_float_frame`，改为静态计算后补齐（revisions.json；decisions E21） | 确认 | 7 个 fixture 用 AST 切片逐个比较，全部逐字相同。`conftest_sources/` 下的两个文件与工作树 base 文件逐字节相同。请求 fixture 的 12 个测试函数（13 键）需要的正好是这 7 个，现稿全都有 |
| H4 | r2e-mr-017 只把 13 键从 ERROR 改为 PASSED，键集合与顺序不变；其余 79 键与来源期望逐键相同；本题 fixture 不带参数，不会展开（revisions.json；E21） | 确认 | 修订前 R-f gold 的观测（与来源期望 92/92 相符）和当前期望的键集合相等，逐键差异恰好是这 13 键。7 个 fixture 都是不带参数的 `@pytest.fixture` |
| H5 | 修订后真实 grader 下 noop 0（90/92）×2、gold 1（92/92）×2，与试跑逐键相同，目标键不变（findings 顶注；R02/R08/R13/R15；E24） | 确认 | b5 的两份 noop 日志归一化后逐行相同，两份 gold 日志也逐行相同。账本：`ledger_b5_noop.jsonl` 与 `ledger_b5_gold.jsonl` 各第 5、6 行。另有 `dryrun_b3r2` 中 fix_a/fix_b 的汇总行 |
| H6 | 修订前 R16 = issue：T2 在 noop 下失败只因 Period 报错文字，题面没提；换一种修法可能不改文字而得 0；属题意覆盖问题，不属环境（R16 previous；findings；P3 README §2.5；known_issues `prompt_quality_candidates`） | **确认，并加强** | 三点新证据：<br>① 公开的 `W/pandas/tests/frame/test_analytics.py:899` 断言的是相反的文字，而且这个用例在 base 上通过（H2 的 `PT_RC=0`）。<br>② 候选只要不让 Period 列走 `PeriodArray.mean`，在 T2 上执行的就是与 noop 相同的代码；noop 日志 L51-109 显示这段代码的结果是 FAILED。<br>③ 几条具体的合理路线都会得 0：C1（只对数值 EA 分派）、C2（只在 `numeric_only=True` 时分派）、在 nanops 层支持掩码、窄修 `IntegerArray.sum`。<br>证据级别：静态推断加 noop 执行；候选层面尚未在 CPU 上实跑 |
| H7 | 修订后 R16 改为 pass，理由是"目标键不变……不改变题目的判别键"（screening_record R16，批次三写回） | **部分推翻** | 事实部分成立：目标键与修订前相同，新恢复的 13 键在 noop 下都是 PASSED。但把 R16 从 issue 改成 pass，就丢掉了 Period 文字问题。修订没有碰 T2，`H/test_1.py:899` 仍然要求新文字，问题在当前材料里原样存在 |
| H8 | issues[1]（T2 是隐含要求）标为 status=verified，resolution 写"用户批准 T0-6 第二步……期望里已无 ERROR 键，候选在根目录建 conftest 翻转键的路径随之消失"（screening_record） | **推翻** | 这段 resolution 逐字复制自 issues[0]（fixture 问题），与 T2 无关。同一批历史里，known_issues `prompt_quality_candidates` 仍把本题列为 open，P3 README §4 也写明"题意观察没有展开核实影响面"。这一项应为 open，并且应该像 pillow（T0-3）、scrapy（T0-4）那样记成带 `deferred_to` 的未完成项 |
| H9 | disposition 为 `qualified_with_revision`，reason 写"无未完成项"，`pending_checks` 为空；`results_20260924.md` 中本题一行的"未完成项"和"issue 项"都是"-"（screening_record；results） | **过时 / 不完整** | 就环境范围而言，资格成立：本次复核的环境与评分证据都支持它。但把它当作入池参考，会漏掉 H6 的题意与测试问题。本次静态处置是 `needs_review`，两者的范围不同。建议在环境记录里补一条 deferred 未完成项 |
| H10 | 修订后"期望里已无 ERROR 键，候选建根目录 conftest 翻转键的路径随之消失"（issues[0] resolution；known_issues） | 确认（仅限这条路径） | 当前 92 键全部 PASSED，"候选在根目录建 conftest，让 ERROR 键翻成 PASSED"这条特定路径不存在了。但评分时 rootdir 是 `/testbed`（日志 L22），候选新增的 `/testbed/conftest.py`、`setup.cfg` 里的 pytest 段、对 `pandas/_testing.py` 的改动，仍会在评分时生效。这属于共享的控制面通道（清单 31），不是本题特有，也不据此扣分 |
| H11 | 有 1 个测试因缺 SciPy 被 skip，因此 expected 绑定"无 SciPy"（R06 previous；P3 README §2.1） | 确认 | 当前日志 L282：`SKIPPED [1] r2e_tests/test_1.py:564: Missing SciPy requirement`（`test_kurt` 带 `@td.skip_if_no_scipy`）。装上 SciPy 后会多出 `TestDataFrameAnalytics.test_kurt` 这个键，键集合不等，得 0。前稿只记了"缺 SciPy"，没有写成绑定条件，这里补上 |
| H12 | 公开复现脚本（只依据公开题面写成）以 agent 身份运行，rc=0、REPRO_OBSERVED=1，报出 'dtype' 参数不支持（R09；findings） | 确认 | `agent_probe.log` L2 显示 `uid=54321(agent)`；L134-139 为 `EXC=ValueError the 'dtype' parameter is not supported…`。脚本用的是题面原例，没有关掉 bottleneck |
| H13 | 解题侧条件：<br>- `python` 指向 `/testbed/.venv/bin/python` 3.7.9；<br>- pytest 7.4.4；<br>- pip 24.0，`pip check` 通过；<br>- 无网络；<br>- 经 `.pth` 导入，cwd 不限；<br>- 有 gcc、make，没有 xvfb-run、uv；<br>- `setup.cfg` 被改写，pandas 自带的 pytest 配置不生效；<br>- 不要 reset 5 个自带的已跟踪改动。<br>（R05；solver_conditions） | 前六项确认；最后两项的后果未核实 | 前六项在 `agent_probe.log` L1-30 逐项可见。Cython 0.29.37 未核对（没有打开 hygiene_check）。"不要 reset"一条，历史自注其后果"未测" |
| H14 | 派生镜像已清理 git，fix_present=no，refs/remotes/reflog 都为 0，私有目录权限 700，隐藏测试对 agent 与评分用户都不可读（R17；R01） | 对派生镜像确认；**对正式链已过时** | `runs/r2e_t0_batch3_20260924/derived7/pandas__32dd…/facts.json` 中 `root_facts.fix_present=no`、`integrity.hidden_tests_unreadable_as_agent_uid.ok=true`，镜像 ID 3d40959d… 与 b5 账本一致。但环境卡（09-25 核对）指出，正式 actor 目前用的是来源镜像：`/r2e_tests` 可读，修复提交可达（M3 事实）。R17 的结论要等正式链换成派生镜像后才成立 |
| H15 | public_hints 里的 conda 说法对 R2E 不成立，属全局问题 E09，不计入本题（R03） | 确认，并补充 | 同一段提示中"不要改测试文件，评分会重置测试文件"对 R2E 同样不准确，而且在本题有具体后果：它让解题者倾向于让公开的 `test_analytics.py` 保持全部通过，也就是保留 T2 要否定的旧文字 |
| H16 | 资源：gold 峰值 714 MB（限额的 17%），setup 28 s，测试 2–3 s（R12） | 确认 | 当前 b5 运行峰值 726–728 MB，noop 账本 `test.seconds` 为 1.84–1.87 s |
| H17 | 修订前与独立 runner 逐键一致；修订后没有同版本的独立 runner，改用一次性容器试跑（R15） | 确认 | M3 a1/a2 的汇总行；`dryrun_b3r2` 的汇总行 |
| H18 | 提案推荐"6 题 A 维持现状"，并说"修好后，带 fixture 参数化的测试会展开成多个键"（提案；P3 README §3） | 过时；对本题不适用 | 用户已批准方案 B（T0-6 第二步）并已实施。本题的 fixture 不带参数，键集合不变（见 H4） |
| H19 | "全池只此一题属可翻转键"（decisions T0-4，指 scrapy；known_issues `expected_key_flippable_by_legit_fix`） | 在该族范围内确认；需补充 | 这一族只管一种机制：期望为 FAILED，而更完整的修复会让它变成 PASSED。本题 T2 是另一种惩罚合理解的机制：期望为 PASSED，但只有 gold 路线的副作用才能满足。历史把 T2 归入题面质量族，与 T0-4 不矛盾；但不能据 T0-4 的说法认为全池只有 scrapy 一题会误拒合理解 |
| H20 | known_issues 建议的自动检查："题面 Actual Behavior 的报错文本应出现在 noop 目标键的原因行里" | 确认，对本题有效 | T1 的 noop 原因行就是题面原文（日志 L187）；T2 的原因行是正则不匹配（L107-109）。这条检查会正确标出 T2 |

## 2. 主审改判与理由

| 前稿判断 | 读历史后 | 理由 |
|---|---|---|
| 解题侧 bottleneck：推断与评分侧相同，actor 待验 | 镜像层面已实测：未启用 | 见 H12：agent 身份跑题面原例，没有关 bottleneck，得到的正是 nanops 非 bottleneck 分支上的 ValueError |
| 清单 10（本地开发验证）：unknown | pass（镜像层面；正式链仍待 actor 验证） | 见 H2、H12、H13：agent 能跑公开测试与复现脚本；`test_analytics.py` 在 base 原位是 91 passed / 1 skipped（root 身份）；本题不在 `public_test_noise` 族里。以 agent 身份跑 `test_analytics.py` 仍未实测 |
| 清单 6 / 环境钉：只记了"无 scipy" | 补上"expected 绑定无 SciPy" | 见 H11 |
| 开发需求 | 补两条：不要 reset 5 个自带改动；pandas 自带 pytest 配置不生效 | 见 H13；reset 的后果历史未测，因此只作为建议记录 |
| 暂定处置 `needs_review`（题意/测试争议），唯一下一步是 C1 的 CPU 反例 | **不变** | 历史只把 T2 记为"可能得 0"并移交题意筛查，没有任何证据显示合理的替代解能过 T2；修订也没有碰 T2。历史里 R16 改为 pass、issues[1] 标为 verified 是记录错误（见 H7、H8），不构成反证 |

## 3. 与历史的主要分歧

环境阶段在批次三写回时，把 T2 的 Period 文字问题当成已解决：R16 改为 pass，issues[1] 标为 verified，而且 resolution 是从 fixture 问题复制过来的。本题的环境记录因此显示"无未完成项"。本次核对确认，这个问题在当前材料中原样存在，而且比历史描述的更具体：T2 与公开的旧测试直接冲突，会让几条自然的合理修法得 0。
