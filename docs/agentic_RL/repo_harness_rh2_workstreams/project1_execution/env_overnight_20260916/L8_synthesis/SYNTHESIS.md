# L8 · 夜间环境工作跨包合成稿（2026-09-16）

范围：13 个 L1 仓库静态包（216/216 题）+ L0 事实工具 + L2 参考 ID + L3 轨迹与反例 + L4 R2E 静态 + L5 证据索引 + L6 rh2 代码核实 + M2（机器 2 实跑）+ M3（机器 3 实跑，48 R2E 镜像）。
**本文全部是事实汇总与建议，没有任何决定。** 标"已实测"的是真机或真实 RH2 链上的运行结果；标"静态"的是只读材料推断；没写的一律按 `not_checked` 读。
配套结构化文件：[`decision_items.json`](decision_items.json)（16 个决策项）、[`split_constraints.json`](split_constraints.json)（划分约束与处置集合）、[`disposition_counts.json`](disposition_counts.json)（从 records 实算并与 summary 对账）。

---

## a. 一页结论

216/216 题全部完成逐题静态审查（13 个包，无遗漏）；48/48 个 R2E 镜像完成机器实测；15+2 个 SWE-Gym 镜像完成机器实验。
**今晚最重要的结论只有一句：评分信号直接来自候选进程的 stdout，因而可以被候选伪造——四条注入向量里两条已在真实 RH2 链上拿到 `reward=1.0`、一条已在 v2 入口合成复现。** 其余问题都在这条之下。
另一条必须先读的前提是 L6 的 C18：阶段一 181 份 gold 日志一份都没有 `>>>>> Start/End Test Output` 标记，status_map 是整份日志解析出来的；
而当前 v2 入口缺标记会直接空映射并判 `patch_apply_failed`。因此各包写的"gold 全 FULL / empty 全 NO / p2p_missing=…"以及 `fragile_reference_id` 信号本身，
**都是阶段一离线口径的结论，不能直接当作生产 v2 路径的结论**。
处置分布是各包的**建议**（`ready_for_probe` 的语义是"可进能力探针"，不等于"批准训练使用"），`unsupported_conditions` 无人使用，全为 0：

| 仓库 | 题数 | ready_for_probe | needs_repair | needs_review | reject_revision | unsupported_conditions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| getmoto/moto | 59 | 27 | 13 | 19 | 0 | 0 |
| python/mypy | 40 | 12 | 20 | 4 | 4 | 0 |
| iterative/dvc | 35 | 8 | 21 | 5 | 1 | 0 |
| Project-MONAI/MONAI | 26 | 11 | 11 | 3 | 1 | 0 |
| pydantic/pydantic | 20 | 7 | 5 | 7 | 1 | 0 |
| dask/dask | 14 | 7 | 2 | 2 | 3 | 0 |
| conan-io/conan | 12 | 4 | 4 | 4 | 0 | 0 |
| modin-project/modin | 5 | 2 | 2 | 1 | 0 | 0 |
| pandas-dev/pandas | 5 | 1 | 2 | 2 | 0 | 0 |
| **合计** | **216** | **79** | **80** | **47** | **10** | **0** |

（**13 个包的 summary 自报分布与从 `records/*.json` 重算逐项一致，无不一致项**——对账明细在 `disposition_counts.json` 的 `reconciliation_with_summaries`。）

### 今晚最重要的 8 条发现

1. **根因：评分信号直接来自候选进程的 stdout，parser 不校验键、后写覆盖先写 ⇒ 候选控制测试进程 = 候选控制评分输入。** 四条注入向量：(a) 候选在标记段内直接打印 `PASSED <参考ID>`（另一会话用 v2 入口合成日志复现 `RESOLVED_FULL`、参考缺席 0）；(b) 新建或追加 `tests/conftest.py` 的 `pytest_runtest_makereport` hookwrapper（**真实 RH2 链实测 reward=1.0**：MONAI-2061、dvc-1661、pydantic-8500）；(c) **只改 `setup.py`**，由安装段 `python setup.py develop` 在评分容器里以候选身份写出 conftest（**实测 reward=1.0**，且 `candidate_test_like_paths` 与 `candidate_touched_conftest_or_fixture` **都是空的**，账本里与正常 gold 提交不可区分）；(d) 非候选来源的意外污染（pip 的 `ERROR:` 行、被测程序自己的输出、`SKIPPED [N]` 摘要行），阶段一 181 题里 54 题已产生伪条目。证据：`M2/M2_report.md` §7.2/§7.5/§7.6 与 `M2_conftest_probe.json`、另一会话的 `batch4_scoring_20260910/impl_plan_20260915.md` §9.6 第 5/6 条、`L1_monai_1/summary.md` 仓库级 2、`L6…claims.json` C03/C18。
2. **L6 否证了两条被多包当作前提的说法。** (a) `file_rules.additional_exclusions` 在 `rh2/src` 全树零命中、不读不消费——各包写进题级记录的排除建议（mypy-15876、MONAI 5 题、M2 2 条）一条都不会生效；(b) 安装 rc 与测试 rc **已经**接在 P-A 归因上（`manager.py:2939-2948` 的 `test_rc>=128 → resource`、`:2968-2972` 的 `install_rc != baseline → 阻断候选归因`），真问题不是"要不要接"，而是"rc=0 不代表安装成功"（dvc 串三处 `|| true`、mypy 串以 `hash -r` 收尾）。证据：`L6_rh2_code_check/claims.json` C05 / C11 / C08。
3. **阶段一日志的解析口径与生产不同（C18）。** 181 份 gold 日志 0 份带 `Start/End Test Output` 标记，整份日志被解析，产生伪键 54 种 / 148 条 / 涉及 54 题（最常见 `Could`×35、`No`×21，来自 pip 的 `ERROR: Could not find a version…`）；生产 v2 入口 `scoring.py:233-238` 缺标记直接空映射 + `apply_ok=False`。证据：`L6_rh2_code_check/claims.json` C18。
4. **参考 ID 有两种坏法，后果相反。** 转义层级不一致 → 参考 ID 永久缺席 → **10 题 gold 恒判 RESOLVED_NO**（修法已由三个包独立验证：缺席后按 `unicode_escape` 回退、唯一命中才采用，181 题 missing 18→0、碰撞 0、empty 侧不受影响）；空白截断 → 两边一致地错、不缺席但被压缩，**35 题参考集含截断 ID，最大一个 P2P 键代表 108 个运行时测试**（modin-6937）。证据：`L2_reference_ids/id_mapping_proposals.json`、`L1_pydantic/summary.md` 附-1、`L1_modin_pandas/repo_level_findings.md` #M5/#X2、`L6…claims.json` C01。
5. **合法被跳过的参考测试会被静默判失败，而"桶全 SKIPPED → FULL"不是独立漏洞。** 另一会话用真实 pytest 实跑 `-rA` 与 pydantic 配方的 `-rA -vv -o console_output_style=classic`：被跳过测试只出现两种形态——`tests/x.py::test_a SKIPPED (dep missing)`（尾带原因，`endswith` 分支不认）与 `SKIPPED [1] tests/x.py:4: dep missing`（`startswith` 分支取成伪键 `[1]`），**两种 parser 下真实 ID 都不进 status_map ⇒ 按缺席计失败**。所以"让参考测试被 skip"得到的是 reward 0：合法 skip 被误伤，但不可利用；"F2P 桶全为 SKIPPED → FULL"只在**合成**的 `SKIPPED <id>` 行下可达，属第 1 条根因族的特例。实际代价是保真度与归因：22 题的 F2P/P2P 带 skip 装饰器、5 题的 F2P 直接受影响，换一台缺 GPU/缺可选依赖/无 Docker 的机器就会把 gold 静默判 0，且日志里看不出是 skip 还是 fail。证据：`impl_plan_20260915.md` §9.6 第 5 条、`L6…claims.json` C02、`L1_dvc_1/summary.md` 仓库级 3、`L1_monai_1/summary.md` 仓库级 3。
6. **答案可以从四条通道直接拿到。** 跨题泄漏 80 对 / 95 题（44%，下界）；镜像出厂带 HEAD 之后的可达提交（SWE-Gym 15/15、R2E 48/48，后者一条 `git rev-list --children` 即列出且修复提交排前 4）；运行期出网（24 条轨迹里 3 题取到 gold 补丁全文、1 题下到被测项目后续版本 sdist）；候选模型记忆污染（conan-14296 逐字复现不可见官方测试 60/61 行）。证据：`L1_pydantic/crossleak_216.txt`、`M2/M2_report.md` §5、`M3/M3_report.md` §2.2、`L3_trajectories/L3_report.md` §A.3、`L1_conan/evidence_contamination.json`。
7. **题面与验收要求不一致约 60 题，且判分面过窄的题至少 24 道。** 前者含 2 题"写对必判错"（moto-6022 要求键名逐字是带尾随空格的 `"Statement "`、moto-5737 要求 Jinja 渲染出来的字符串 `"None"`）；后者已有真实链反例（pydantic-5706 的候选让官方面全绿，同时把 base 自带的 6 条 sequence 测试跑挂）。证据：`L1_moto_2/summary.md`、`L1_conan/repo_level_findings.md` §8、`M2/M2_report.md` §4.2。
8. **资源与身份画像有三处"不改就一定判错"，且修法都已实测。** grader 的 `/tmp` tmpfs 1 GiB 让 modin-6937 的 401/2354 条 P2P 因 `Errno 28` 失败（`p2p_rate=0.8297`），4 GiB 全过；评分机有 CUDA 时 MONAI-4676/6523 各 72 条参考 ID 失配、gold 拿 0；R2E 的候选身份 uid 54322 在 48/48 镜像跑不动。同时已验证可行的三项：MONAI 两题资产预置后全断网 `RESOLVED_FULL`、离线只需预置 setuptools+wheel、R2E 泄漏清理后 48/48 reward 逐键不变。证据：`M2/M2_report.md` §3.3/§3.5/§2、`L1_monai_2/summary.md`、`M3/M3_report.md` §2.1/§2.3。

### §a 补记：L7 假修复真机实测（M2 第三片，本机 05:27，晚于本稿定稿）

权威结果 `M2/M2_L7_results.json`，证据 `runs/env_overnight_20260916/M2/L7/`（out/ 三态矩阵、v2/ledger_v2.jsonl、rerun/）。
- **D05 从静态预期变成真机结论**：32/32 题、37 个 fake 变体全跑（30 个镜像全部拉到、0 缺失），**25 题 / 28 变体的一行/极小假修复让 F2P∪P2P 全绿（拿满分）**，base 全部正确判 not_full、gold 全部满分。静态高估的 4 条已被现判分面拦下：dvc-1712、dvc-4719、mypy-10174（fake=改 meet.py）；moto-7335 属**数据损坏**（1 条参考 id 空白拆分使 gold 也非满分、判分面无法区分错误修复，归 D03）。
- **D01 控制面在真实 v2 链再得 3 题满分**（正式 deny_all profile）：掏空 `tests/utils.py::assert_allclose`（MONAI-4583）、令 `mypy/test/helpers.py::assert_string_arrays_equal` 恒真（mypy-10424、mypy-10174）均判 **RESOLVED_FULL**；MONAI-4676/4775/6523 因测试还有别的断言而 RESOLVED_NO（边界）。机理与 conftest 同源：受信投影把被掏空的测试支撑文件原样投入、可信 setup 只恢复 test_patch 路径，而这些文件不在任何题的 test_patch 里。**观测缺口**：MONAI 的 `tests/utils.py` 被 `candidate_touched_conftest_or_fixture` 观测到（仅观测不判），**`mypy/test/helpers.py` 连观测都漏**、账本与正常 gold 不可区分——D01 修法要一并补齐观测面。
- **判读工具修法（给流水线）**：run_matrix.sh 初版两处缺陷会把 gold/fake 误判 not_full（pytest-pretty 抑制 `-rA` 逐用例行；权威 P2P `..._valid_name[with space]` 在 manifest **与 ingest grading bundle 里都被空白拆分** + `$OFFICIAL` 无引号词拆分），改用权威 f2p/p2p + 精确 argv + `-vv -o console_output_style=classic` 纠正。**这条把 D03 证据升级：空白拆分不只污染解析日志，也污染了权威 grading bundle 本身。**

---

## b. 决策项清单

16 项，按"影响题数 × 阻断程度"排序。每项的完整证据、选项代价与副作用在 [`decision_items.json`](decision_items.json)；下表是索引与一句话摘要。
**性质**：T0 评分语义 / T0 公共契约 / T1 环境修复 / T1 数据处理。

| # | 编号 | 一句话问题 | 性质 | 涉及题数 | 各包意见 |
| ---: | --- | --- | --- | --- | --- |
| 1 | **D01** | **根因族**：评分信号来自不可信的候选 stdout（4 条注入向量，2 条真实链实测满分）——改结构化结果通道？安装段后由 root 复原控制面？ | T0 公共契约 + T0 评分语义 | 216（+R2E 48 同型） | 两个会话独立收敛到同一根因，无分歧 |
| 2 | **D08** | rc 已接入 P-A 但判据过宽（rc=0≠安装成功），要不要改成逐子命令+产物校验并补两项诊断？ | T0 公共契约 | 216 | L6 推翻了原提法，四来源一致 |
| 3 | **D09** | 镜像 git 泄漏：继续每 attempt 付 7.5–43 s 的 sanitize，还是一次性清理派生镜像？训练期出网怎么定？ | T0 公共契约 / T1 环境 | 216 + 48 | M2/M3 一致，方案均已实测 |
| 4 | **D07** | 跨题泄漏 80 对/95 题：按什么粒度成组划分？去重判据要不要扩到 `problem_statement_sha256`？ | T1 数据处理 | 110（强证据）/ 148（含共用文件） | 一致要求成组，分歧只在粒度 |
| 5 | **D06** | 题面与验收不一致（方向相反/不可推断/错字固化）+ hints 并入题面的规则 | T1 数据处理 | 约 60 | 事实一致，处置建议不一致 |
| 6 | **D15** | R2E 接入前的 Q1–Q6：期望里的非 PASSED 键、ANSI 口径、清理程度、入口搬运、测试模块恢复、1 个有效键 | T0 评分语义 + T1 环境 | 48 | L4/M3 一致，M3 修正 L4 一处归类 |
| 7 | **D16** | mypy 的 F2P/P2P 是 `-k` 子串闭包副产物（14/40 题 P2P 为空）：重建、补 P2P、还是只作评测？ | T0 评分语义 / T1 数据 | 40 | 两个 mypy 包一致，L6 C06 确认机制 |
| 8 | **D03** | 参数化 ID 空白截断塌缩（最大 108:1）：观测、改 parser 重建参考集、还是换逐 ID 通道？ | T0 评分语义 | 35 题参考集 + 72 题日志碰撞 | 事实一致，**方向有分歧**（见 §c-1） |
| 9 | **D05** | 判分面远小于改动面，一行破坏性改动即满分：接受原样、挂附加回归、还是逐题补断言？ | T0 评分语义 / T1 数据 | 24+（**真机实测 25 题/28 变体满分**） | 已真机实测，见 §a 补记 |
| 10 | **D11** | 镜像依赖未按历史锁定，回归保护被静默削掉：重建镜像并重算参考集，还是接受？ | T1 环境修复（重算即任务修订） | 约 30 | 一致认定为"保护被削"，投入由用户定 |
| 11 | **D10** | 评分机资源与身份画像（CUDA/shm/tmpfs/非 root/网络例外/预置资产）要不要写成硬约束？ | T1 环境修复（tmpfs 与 memory 档位属 T0 资源边界） | 约 30 | 一致；dvc 包对"非 root"明确建议只做题级例外 |
| 12 | **D04** | 合法 skip 的参考测试拿不到真实 ID、按缺席计失败：要不要把"被跳过"与"缺席"分开并换逐 ID 通道？ | T0 评分语义（保真度与归因，非可利用面） | 22（5 题 F2P） | L1×5 + L6 一致；另一会话已订正"桶空→FULL"不是独立漏洞 |
| 13 | **D12** | 离线只缺 setuptools/wheel（已验证），要不要固化 wheelhouse 挂载？pydantic 的 install 恒失败怎么处置？ | T1 环境修复（install 判据属 T0 准入） | 约 20 | M2 单包，无分歧 |
| 14 | **D02** | 参考 ID 转义不一致让 10 题 gold 恒判 RESOLVED_NO：匹配层回退、重采参考清单、还是剔除？ | T0 评分语义 | 10 | **三包独立同结论、修法明确，最容易拍板** |
| 15 | **D13** | `test_patch` 新建文件的恢复缺口（守卫是"跳过"而非"删除"）与 legacy 单脚本路径 | T0 公共契约 | 8（1 题已真实发生） | 一致；L6 C07 确认正式链已部分修复 |
| 16 | **D14** | 候选模型记忆污染（逐字复现不可见官方测试）：要不要把静态探针固化成入池闸门？阈值怎么定？ | T1 数据处理（用于评测准入则涉 T0 有效性） | 4 / 24（有轨迹的题里的下界） | L1_conan 提出，L3 提供交叉证据 |

**低成本、各包意见一致、可当场拍的三项**：D02（参考 ID 回退）、D12（wheelhouse 预置）、D13（新建文件恢复改 `rm -f`）。
**必须先于其它决定的一项**：D01——它决定的是整条 reward 信号是否有效。

---

## c. 包间分歧与待核实

### c-1 截断塌缩是"假阳性通道"还是"欠验证"？（有分歧，可由一次实跑收敛）

- `L1_moto_2`（R8，moto-6178）与 `L1_modin_pandas`（#M5）称：按"后写覆盖先写"，候选弄挂组内 107 个、只留最后一个通过，该键仍判 PASSED，是**结构性 reward 假阳性通道**。
- `L1_conan`（§4）实测 pytest 6.2.5 的 `-rA` 展开为 `PpsxXEf`、摘要块顺序是 PASSED → SKIPPED → FAILED；`L6` 的 C01 探针按同一顺序喂入两行也得到 **FAILED**。
- **协调者判断**：在纯 `-rA` 摘要区内，塌缩方向是**保守的**（组内任一失败 ⇒ 整键 FAILED），因此它制造的是**欠验证与假阴性**，不是假阳性。能翻转方向的只有"摘要之后还出现以 PASSED 开头的行"——pandas 的 `addopts` 含 `--capture=no` + 候选 `print()` 恰好是这样一条通道（`L1_modin_pandas` #P3），但那属于 D01 控制面族。
- **待做**：一次 moto-6178 实跑（构造"两边带括号通过、只左边带括号失败"的部分实现）即可坐实；L6 本轮只验了机制，没验方向在真实日志上的表现。

### c-2 `L1_pydantic` 的"截断当前判分不受影响"推论过强（已澄清）

`L1_pydantic` 称 216 题 F2P/P2P 里没有含空白的 ID、截断"当前判分不受影响"。字面正确——参考集本身就是被同一个 parser 截断过的产物，所以参考 ID 里当然没有空格；但由此推出"不受影响"是**过强**的：问题不在缺席而在塌缩（一个键代表 N 个测试）。该包自己在 summary 里已标注"与 moto 包的分歧待汇总时裁定"，本包判定：两条同时成立，取 moto/modin 的读法（存在塌缩、覆盖 35 题），方向按 §c-1。
同理，`L1_dvc_1` 的"参考清单内部按解析器口径的同名碰撞 = 0 题"也不矛盾：它查的是**参考 ID 之间**的碰撞，而真实碰撞发生在**运行时多条 nodeid → 同一截断键**。

### c-3 `fragile_reference_id` 到底检出了什么（已澄清，需改）

`L6` 的 C10b：该字段**不由任何 rh2 源码产生**，只出现在 `task_signals_swegym.json` 与读取它的脚本里；判据可从数据反推为**结果派生**——216 行里 `fragile=True` 恰好 10 条，且这 10 条 stage1 全部满足 `gold=RESOLVED_NO ∧ f2p_missing=0 ∧ p2p_missing≥1`。
因此：它只检出**转义族**，检不出**截断族**（截断不会让 gold 失败）。`L1_moto_2`（5620/6178 被标 false）、`L1_conan`（11594 被标 false 与证据不符）、`L1_dask`（同样记 false）三处"勘误"都成立，但它们不是"标错了"，而是"这个信号的语义本来就不是形状"。
另外 216 题里 `stage1` 为 null 的 34 题（全是 mypy）无论 ID 多脆弱都不可能被这个信号标出。建议补一个**形状派生**字段（L6 实测：含 `[` 不以 `]` 结尾 35 题、含反斜杠 9 题、参数取 `os.getcwd()` 1 题），与结果派生字段并存而不是替换。

### c-4 "10 题" 与 "11 题" 不是同一个口径（已澄清，两边都对）

`L2` / `L1_pydantic` / `L1_dvc_1` 说的 10 题是"**因参考 ID 转义不一致造成的假阴性**"；`L5` 说的 11 题是"**gold 在 oracle 口径下从未到过 RESOLVED_FULL**"，多出的 `modin-project__modin-5940` 不属转义族：
`L1_modin_pandas` 已给出它的具体原因——P2P 里 `TestParquet::test_read_parquet_s3[object-pyarrow]` 直连真实 `modin-datasets.s3.amazonaws.com`，离线两侧都 FAILED（`f2p_missing=0`、`p2p_missing=0`，只有这一条 `p2p_notpass`）。所以它属**网络族**（D10），修法完全不同。
`L2` §5 的旁证一致：modin-5940 的 P2P 非 OK 是 1/1931 条 FAILED，不是缺席。

### c-5 `L1_mypy_2` 的"本包 20 题零运行期证据"不成立（已由 L5 更正）

`task_signals_swegym.json` 的 `stage1` 字段读自中途快照（364 行/182 题），不是续跑后的 434 行/216 题版本；差的 34 题全是 `python/mypy`，账本里其实都跑通了（empty 全 `RESOLVED_NO`、gold 全 `RESOLVED_FULL`）。
连带更正：`L2` §4 第 4 条说的"`python__mypy-10401` 没有阶段一 gold 日志"也要改——该题在 continuation 账本里后一行跑通，signals 取到的是前面 `infra_failed` 那行。
**逐题判定一律以 `L5_evidence_index/evidence_index.json` 为准**（216/216 + 48/48 每题至少一条证据，27 种 kind，`signals_crosscheck.mismatches` 列了全部 72 条不一致）。signals 文件今晚不改，早上由协调者重生成。

### c-6 "F2P 桶全 SKIPPED → RESOLVED_FULL" 已被另一会话自行订正（不再是独立发现）

最初 e2 侧报的是"当 F2P 桶全部为 SKIPPED 时 fork 语义判 RESOLVED_FULL"，与我方五个包报的"被跳过的参考测试按缺席计失败"方向相反。
对方随后在本机用**真实 pytest** 复核并订正（`batch4_scoring_20260910/impl_plan_20260915.md` §9.6 第 5 条，09-16 05:xx）：
`-rA` 与 pydantic 配方的 `-rA -vv -o console_output_style=classic` 两种输出下，被跳过测试只以 `tests/x.py::test_a SKIPPED (dep missing)`（尾带原因，`endswith` 分支不认）与 `SKIPPED [1] tests/x.py:4: dep missing`（`startswith` 分支取成伪键 `[1]`）两种形态出现，**两个 vendored parser 都不把真实 ID 映成 SKIPPED**，所以自然运行只会走"缺席 → 计失败"这一支。
"桶空 → FULL"只在**合成**的 `SKIPPED <id>` 行下可达，因此它不是独立漏洞，而是 §a 第 1 条的根因族（候选可伪造 stdout 状态行）的一个特例。两边的观察由此完全一致。

**遗留一条待核**：L6 的 C02 统计称 181 份 gold 里"键为真实 nodeid 的 69 条 SKIPPED 全部来自 pydantic"，而按上述订正，pydantic 的进度行形态尾带原因时同样不被 `endswith` 分支识别——这 69 条的具体行形态（是否有不带原因的 `<id> SKIPPED`）需要早上核一次。它不影响结论方向，只影响"pydantic 是否是唯一例外"这句话。

### c-7 L4 对 pillow `3ac9396e` 的归类已被 M3 修正

`L4` 把它列进 T1"来源自身给不出正确信号"；`M3` 实测在忠实执行 `run_tests.sh` 时 `reward=1`，应改判为"**入口不可归一化**"（统一 pytest 入口下收集 0 个用例）。取 M3。

### c-8 L3 的"投影规则够用"与各包的控制面告警不矛盾

`L3` 在 24 条真实轨迹上验证"候选改过的测试文件 ∩ 评分面 − test_patch_paths = 空"（24/24），这是**实际行为**的观察；各包（monai_1 / dask / pydantic / mypy_2 / conan）讲的是**可能性**。M2 §7 的实测证明可能性是真的。两者一起读的结论是：目前的候选还没用这条通道，但通道是通的。
e2 lane B 提供正面证据：24 题里 15 题可比且**全部与投影 oracle 一致**，7 题 apply 失败是已知 fuzz 题，2 题 modin 零解析属环境问题。

### c-9 各包报的 rh2 源码行号普遍偏 0–4 行（L6 C19）

`sandbox_profile.py`：`candidate_writable_prefixes` 实为 :520（M2 写 517）、`candidate_exec_uid=54322` 实为 :497（写 496）、`agent_uid=54321` 实为 :324（写 323）、`tmp_tmpfs_bytes` 实为 :501（写 502）；`trusted_projection.py` 的"已知不足（登记不修）"段实为 :18-20（L1_dask 写 :22-24，L1_monai_1 写对）。**复核清单一律按符号引用，不按行号。**

### c-10 其它需要标注的口径差异（来自 L5 的 C1–C6）

- **C3**：20260909 夜探针是联网（`network=default`），阶段一是离线（`variant=offline, network=none`）；**5 题 gold 结论相反**（MONAI-1121、MONAI-3205、moto-4799、moto-4833 的联网 FULL / 离线 NO；moto-7105 联网 FULL / 离线 PARTIAL）。比较任意两条 gold 证据前先看 `condition` 里的 `network` / `variant`。
- **C4**：rh2（e1/e2）与 oracle 探针的执行条件系统性不同（`network` `deny_all`→`none`、测试执行用户 `rh2grader`→`root`、`memory_bytes` 4 GiB→8 GiB），**判定词表也不同**（rh2 是 `report.outcome` + `report.reward`，oracle 是 `official_verdict`）。**两套词表不要互译**，差异先归到条件差异再谈判定差异。
- **C1**：R2E 账本 v1/v2 的 gold reward 已被 v3 覆盖，只用 v3 / 阶段一扩展 / 机器 3 的行。
- **C2**：DeepSeek 候选有"原组"与"投影组"两套判定，`task_signals` 取的是原组；引用时写明取哪一组。
- **C5/C6**：账本副本会重复计数（三组关系已逐行验证）；e2 与 M3 的账本是运行中快照，引用数字务必带采集时刻与行数。

---

## d. RH2 复核清单（L6 已填）

来源：`L6_rh2_code_check/claims.json`（20 条，成立 14 / 部分成立 3 / 不成立 3）。核实树：HEAD `bac7659e` + 另一会话未提交的 45 项改动（26 个 ` M` + 19 个 `??`）。**位置按符号引用**。

| # | 断言 | 来源包 | 声称位置（符号） | L6 核实结果 |
| --- | --- | --- | --- | --- |
| C01 | `line.split()` 取第 2 段当 nodeid、后写覆盖 ⇒ 含空格 ID 被截断塌缩 | moto_1/2/3、dvc_1/2、conan、dask、modin | `envpack/swegym_parsers.py::parse_log_pytest` | **成立**。实测两行 → 一个键、值为后写的 `FAILED`；同缺陷在 `parse_log_pytest_pydantic`；数据面 35/216 与 moto_2 一致 |
| C02 | `-rA` 的 `SKIPPED [N] path:line:` 被取成 `[N]` 伪键，"SKIPPED 不进桶"不可达 | dvc_1、monai_1/2、dask、conan、modin | `swegym_parsers.py` / `envpack/scoring.py`（:24、:201、:231、:269） | **成立**。181 份 gold 里值为 SKIPPED 的 `[N]` 键 41 条（8 仓库），真实 nodeid 69 条全部来自 pydantic |
| C03 | 任意以状态词开头的行都被记成测试结果，键不校验 ⇒ 伪条目 | monai_1、dvc_1/2、L2 | `swegym_parsers.py:48` 的 `startswith` 前缀匹配 | **成立**。实测 `ERROR: Could not…` → `{'Could':'ERROR:'}`、`PASSEDX not-a-test-line abc` → `{'not-a-test-line':'PASSEDX'}` |
| C04 | `test_globs=()` 使候选新建 conftest 不被投影剔除；恢复只覆盖 test_patch 路径；已登记不修 | monai_1、dask、pydantic | `grading/manager.py`、`adapters/slime/prepared_task_face.py`、`grading/trusted_projection.py` | **成立**。v2 面同形（`prepared_task_face.py` 也 `test_globs=()`）；`trusted_projection.py:18-21` 原文登记 |
| C05 | `hygiene.test_files` 只等于 test_patch 路径；`additional_exclusions` 是否生效 | mypy_2、monai_2、M2 | `manager.py`（test_files / test_globs / DEFAULT_SWE_FORBIDDEN_GLOBS） | **成立，且新增否证**：`additional_exclusions` 在 `rh2/src` **全树零命中**，是废字段；`mypy/test/testcheck.py` 连观测 glob 都不命中 |
| C06 | mypy 的 F2P/P2P = test_patch diff 文本里的 `[case X]` 取 `-k` 子串闭包 | mypy_1、mypy_2 | `envpack/spec_vendor.py::derive_test_command` | **成立**。mypy 分支只拼 `-k`、不拼文件路径；16966 的 `-skip` 后缀确被捕获；15876/16966 参考 ID 未覆盖数 0 |
| C07 | eval 恢复 checkout 漏新建路径、3 题无 pathspec | moto_3、monai_1、conan | `prepared_task_face.py`（trusted setup vs legacy eval script） | **部分成立**。正式链已修（逐文件 `git cat-file -e` 守卫），只有 legacy 单脚本路径仍整条失败；阶段一"无 pathspec"实测是 **4 题**不是 3 题 |
| C08 | 安装失败被 `\|\| true` 吞掉、`RH2_INSTALL_RC` 仍 0 | dvc_1/2、moto_2、L0、M2 | `prepared_task_face.py` 的 install 段 rc 采集 | **成立**。docstring 原文即写"只反映最后一个命令"；dvc 串三处 `\|\| true`、mypy 串以 `hash -r` 收尾 |
| C09 | 账本 schema 漂移而 `schema_id` 未升 | L0 | `adapters/slime/replay_grade.py::LEDGER_SCHEMA_ID` | **成立**。漂移键订正为 **10** 个（L0 报 9 + `projection.unsupported_shape_reasons`） |
| C10a | 代码里有没有 ID 归一化 | L2、pydantic、dvc_1 | `envpack/scoring.py` 的参考匹配 | **成立（零归一化）**。`unicode_escape`/`ascii_escaped`/`latin-1` 等全树零命中；匹配是纯字符串相等 |
| C10b | `fragile_reference_id` 由哪段代码计算、为何对截断族全 false | moto_2、conan、dask | — | **成立**。不由任何 rh2 源码产生，是**结果派生**信号；形状派生对照：含 `[` 不以 `]` 结尾 35 题、含反斜杠 9 题 |
| C11 | P-A 归因是否把安装 rc / 测试 rc 当输入 | moto_2（问题 3） | `manager.py`（`test_rc>=128 → resource`、`install_rc != baseline → 阻断归因`） | **不成立**。rc **已经**接入；原提法方向反了，真问题是判据过宽 |
| C12 | `duplicate_clusters_v0.json` 只按 base_commit 聚类 | moto_3 | `envpack/ingest_swegym_lite.py::build_duplicate_clusters` | **成立**。分组键 `(repo_key_lower, base_commit)`；题面 sha 相同的 4 题全部不在该文件里 |
| C13 | `GraderSandboxProfile.candidate_writable_prefixes` 位置与默认值 | M2 | `adapters/slime/sandbox_profile.py` | **部分成立**。字段与默认值对（`('/opt/miniconda3/envs/testbed',)`），行号实为 :520 非 :517 |
| C14 | `contracts/grading.py` 有未提交的语法错误 | L2 | — | **不成立**（已修复）。当前树可 import，`tests/contracts/` 425 条全绿 |
| C15 | `tests/conftest.py` 与 `pyproject.toml` 的 pytest 段都不恢复 | pydantic、monai_1、dask | `prepared_task_face.py` 的 trusted setup 恢复对象 | **成立**。唯一对冲是观测（`CONFTEST_OR_FIXTURE_GLOBS` 进 sidecar/账本） |
| C16 | 6 题 mypy `eval_cmd` 缺 `-n0` | mypy_1、mypy_2 | 数据面 | **成立**。16555/16869/16905/16963/16966/17071，全部 version≥1.8 |
| C17 | `rh2/` 全套 `pytest -q` 能否当绿/红判据 | — | — | **不成立**。6 failed / 2062 passed / 322 skipped，6 条全在 `tests/contract_slime_async/test_dp_schedule_differential.py`（`No module named 'slime.rollout'`，conftest 的 `sys.path` 还原顺序问题；单独跑 14 passed）。**仓库既定验收是 `scripts/miles_integration_lanes.sh` 双 lane，整树全绿从来不是门禁** |
| C18 | 阶段一日志无 `Start/End Test Output` 标记、生产 v2 只取标记段 | dvc_1/2、L2、monai_1 | `envpack/scoring.py`（`has_markers` 分支） | **成立（本轮最该先看的一条）**。181 份 0 份带标记；伪键 54 种/148 条/54 题；生产缺标记 → 空映射 + `apply_ok=False` → `patch_apply_failed` |
| C19 | 各包给出的 rh2 源码行号 | M2、dask、L0 | — | **部分成立**。偏 0–4 行，明细见 §c-9 |

---

## e. 环境修复清单（按仓库）

以下是**需要动环境才能解决**的具体条目。"已验证"= 真机跑过；其余为静态推断。

### 跨仓库（评分容器与 profile 层）

| 项 | 具体内容 | 涉及题 | 状态 |
| --- | --- | --- | --- |
| `/tmp` tmpfs 档位 | 默认 1 GiB → 至少 4 GiB；tmpfs 计进 cgroup 内存，须与 `memory_bytes`（默认 4 GiB）一起定 | modin 5 题（6937 实测 401→0 条失败） | **已验证**（M2 §3.3/§3.5）；1–4 GiB 之间最小值未测 |
| CUDA 屏蔽 | 评分容器一律 `CUDA_VISIBLE_DEVICES=""`；并在评分前 `pytest --collect-only` 做一次参考 ID 一致性校验 | MONAI-4676、6523（各 72 条 ID 失配，gold 拿 0）；4583/4775/5686/5908 语义漂移 | 静态（L1_monai_2） |
| `--shm-size` | modin 容器 `/dev/shm` 仅 64 MB（Ray 自述需内存一半 ≈ 24.6 GB）；MONAI-763/4676/6523 的多进程 DataLoader 同型 | modin 5 题 + MONAI 3 题 | 静态 |
| 离线 wheelhouse | 预置 `setuptools` + `wheel`（+`packaging`）wheel，经 `declared_readonly_binds` 只读挂载 + `PIP_NO_INDEX=1 PIP_FIND_LINKS`；**必须 pin 版本并记 sha256** | mypy 40 题、moto 4.1 段 12+ 题 | **已验证**（M2 §1.5：mypy-12741、moto-6913 全部子命令 rc=0） |
| 非 root 执行 | 全语料只有 3 题 7 条用例受影响（dvc-1877/2254/3620），dvc 包建议做**题级例外**而非全局切换；dask-8801 的权限分支也因 root 失效（rootscan 判据未覆盖，属下界） | dvc 3 题 + dask 1 题 | 静态 |
| 镜像 git 清理 | SWE-Gym 走现有 `git_sanitize_script`（每 attempt 7.5–43 s，15/15 核验后 `--not HEAD`=0）；R2E 走一次性派生清理（48/48 实测 reward 逐键不变、`.git` 6.3→3.2 GB） | 216 + 48 | **已验证**（M2 §5.4/§5.5、M3 §2.3） |
| 评分成本 | pandas setuptools 后端每次评分重编 Cython 779–830 s（测试仅 4–13 s）；meson 后端 7.7/49.7 s；modin 测试段 39–1379 s。10 题一次 gold 评分合计约 **99 分钟** | pandas 3 题 + modin 5 题 | 已实测（L1_modin_pandas §P1/§M8） |

### getmoto/moto

- **网络例外**：4799/4833 的 2 条 `@pytest.mark.network` P2P 在 `deny_all` 下必 FAIL，gold 上限 17/19。`AWS_ENDPOINT_URL` 桩**已证伪**（打坏 17 条 mock 用例）；`/etc/hosts` 重定向 + 本地自签 HTTPS 桩 + `AWS_CA_BUNDLE` **已验证 19/19 通过**（M2 §3.1）。坑：`docker cp` 不能写进 tmpfs 挂载点。
- **DNS**：6121/6157 需要 `/etc/hosts` 加 `127.0.0.1 testcors.localhost`，否则测试段 rc=1（不影响判分但污染健康信号）。
- **Docker**：7105 的 4 条 F2P 带 `@requires_docker`，无 `docker.sock` 时 gold 只能 `RESOLVED_PARTIAL`；`TESTS_SKIP_REQUIRES_DOCKER=1` 会让 F2P 失去判别力。
- **安装**：4.1 段 12 题的 `make init` 走 PEP 517 隔离 → 离线 rc=2（预置 wheel 可修）；4.0 段 rc=0。
- **环境变量**：镜像里必须显式置 `MOTO_TEST_ALLOW_AWS_REQUEST=false` 且不透传宿主变量——base 里已有 6+ 处、7111/7584 的 test_patch 另加，其中 7584 会用真实 SSM 取出解密的 Firebase/GCM key 再打真实 AWS。
- **Python 版本**：配方对 0.4…5.0 全部 14 个版本一刀切 `python=3.12`，18/19 题跑在上游未声明支持的版本上（5980 已出现 `datetime.utcnow` 弃用导致的失败，恰好在参考集外）。

### iterative/dvc

- **依赖**：`pathspec` 无上界 → `re.error: redefinition of group name 'ps_d'`（8 题命中，4778 是 55 条里 51 条红且 P2P=0）；`networkx` 太旧（`fractions.gcd`，4 题）与太新（删 `G.node`，2231）；`pygit2` 删 `GIT_OBJ_COMMIT`（9395）。建议按 base 时间点的 pip freeze 快照重建。
- **root 身份**：1877/2254/3620 共 7 条 `os.access(p, os.W_OK)` 恒 True 的用例被剔出评分；3620 的题目主题就是 unprotect。
- **成本**：同一 `tests/func/test_run.py` 在 0.35 版跑 388 秒、0.51 版 14.9 秒（原因未查）。

### Project-MONAI/MONAI

- **预置资产**：1121 需 `resnet50-0676ba61.pth`（102,530,333 B，sha256 `0676ba61…fb8a`）放 `/home/rh2grader/.cache/torch/hub/checkpoints/`，**不需要环境变量**；3205 需 `Task04_Hippocampus.tar`（28,425,216 B，sha256 `282d808a…771`）解压到 `/testbed/tests/testing_data/`。两者**已验证**：`deny_all` + gold + 官方 eval_cmd + RH2 正式 parser → `RESOLVED_FULL`（M2 §2）。注意 3205 的资产落在 `/testbed` 内，要确认 `.gitignore` 覆盖且 `chown -R` 耗时可接受。
- **shm**：763 需 `--shm-size=2g`；4676/6523 各 12 条 P2P 依赖 `DataLoader(num_workers=5)`。
- **依赖**：1121 的 `np.int`（numpy ≥1.24 已删）、2446 的 nibabel int64（有效 P2P 7→2）、3566 的 itk（`Unknown type: itkMatrixF44`）各吃掉一批回归。
- **杂音**：`tests/utils.py` 里的 `test_script_save` 辅助函数被 pytest 当用例收集并 ERROR（1121 产生 6 条、4109 1 条、6775 1 条），导致 gold 上 `RH2_TEST_RC` 也非 0。
- **耗时**：6756 的 `test_with_cuda` 在无 CUDA 时不跳过，单条 72.5 s（两个 78.6 MB 张量）。

### dask/dask

- **工具链**：镜像统一 pytest-8.3.2 配 2020–2022 年的 dask，`pytest.warns(None)` 已移除 → 大批既有用例恒失败并被自动排除出参考集（7138 一题 92/561 条 = 16%）；`SPECS_DASK` 连 `python` 都没声明。钉回 `pytest<7` 需重建镜像并按检查 39 重验。
- **root 身份**：8801 的"忽略权限错误"分支因容器 root 而零保护。

### python/mypy

- **xdist**：6 题（16555/16869/16905/16963/16966/17071）`eval_cmd` 缺 `-n0` 而 `addopts=-nauto`，在全核并行下评分。
- **材料丢件**：10308 缺上游新增的 `test-data/unit/fixtures/object_hashable.pyi`；改成整文件跑会立刻 `FileNotFoundError`。
- **pep561**：11857 的 3 条 F2P 要在临时目录建 virtualenv 并 `pip install` 本地包，离线可行性未验证。

### pydantic/pydantic

- **install 恒失败**：`pdm add pre-commit` 在任何网络条件下都失败，两个独立原因（pdm 装在 `/root/.local/bin`；`pdm add` 需联网）。实测矩阵 root+联网=全 0、候选用户+联网=127。补 `pre_install` **已被证伪**。
- **eval_cmd flag 不可改**：镜像装了 `pytest-pretty`，`-rA` 的 short summary 变成 Rich 表格；官方命令可解析完全靠 `-vv`。任何去掉 `-vv` 的衍生跑法 → 全部参考缺席 → `RESOLVED_NO` 且不报错。
- **出厂脏树**：`pdm.lock` + `pyproject.toml` 出厂即改，4 条候选补丁 100% 含噪声 hunk（5706 的补丁 97.5% 是锁文件）。
- **判分环境**：实测 Python 3.8（由 8583 的 `skipif(3,8)` 用例在 gold 上 SKIPPED 反推）。

### modin-project/modin、pandas-dev/pandas

- **modin**：**引擎并发须按沙箱 CPU 数配置（e2 modin 探针终稿根因）**——Ray 默认按宿主 CPU 数（21）起 worker，而 cgroup 只给 2 核，pytest 在收集后第一条测试前静默退出 rc=1 或挂死（与 shm 64M/1G、pids 512/4096、内存 oom_kill=0 均无关；单独 `ray.init` 正常）；fresh 容器设 `MODIN_CPUS=2` 后 `test_io.py` 正常（1652 passed/314 xfailed），`MODIN_ENGINE=python` 亦正常（1834 passed）；配方级注入 `MODIN_CPUS=<沙箱核数>` 留用户/A 线确认（证据 `e2_report_20260916.md §8`、`runs/…/e2/probe_modin/`）。这解释了 e2 的 modin-6298/6937 零解析连 gold 也失败。引擎运行时探测（实测 PandasOnRay），agent 动 `ray/dask` 的 pip 环境会静默切换引擎且无准入检查；`modin/conftest.py` 模块级 `import boto3/requests/s3fs`（缺任一即整份收集失败）；`setup.cfg` 的 `addopts` 带 `--cov`（pytest-cov 是硬依赖）；5940 的 19 条 s3 P2P 需真实 AWS 或本地 moto server（6937 镜像里新版 moto CLI 不认 `moto_server s3`，19 条全 ERROR）。
- **pandas**：`addopts` 含 `--capture=no`（stdout 直通日志，构成状态行注入面）；2.1/3.0 的 `filterwarnings` 首条是 `error:::pandas`（候选引入新警告直接把同批测试变错误）；`.pyx` 修复点对 agent 的自测反馈是断的（不重编看不到变化）。

### conan-io/conan

- **控制面**：`conans/test/conftest_user.py` 在 `conans/test/.gitignore` 第 1 行、被官方 conftest 无条件 import 并 merge `tools_locations`/`default_profiles`；不在任何 test_patch 路径内，恢复步骤与不带 `-x` 的 `git clean` 都不删。conan 包建议**按仓库配方统一清理**而非逐题排除。
- **工具链**：`@pytest.mark.tool` 在缺工具链时是 `pytest.fail` 而不是 `skip`（`cmake` 默认路径 `/usr/share/cmake-3.15.7/bin` 在镜像里几乎肯定不存在）；本包 12 题都不含该标记，但任何来自 `conans/test/functional/` 的扩展回归会整条 FAILED。
- **`/tmp` 残留**：13326 镜像自带 root 属主的 `/tmp/constraint.txt`；不挂 tmpfs `/tmp` 的路径（本地复现脚本、legacy root 路径）在这道题上行为不同。

### R2E（48 题，机器 3 已实测）

- **执行身份（硬前置）**：uid 54322 在 48/48 跑不动——`.venv/bin/python` 链到 `/root`（mode 700）下的解释器、`sys.path` 三条在 `/root` 下、`/testbed` 与 `/r2e_tests` 不可写、git `dubious ownership`、27/48 venv 无 pip。最小改动：派生镜像 `chown -R /testbed`、把 uv 的 Python 搬出 `/root`、`git config --system --add safe.directory /testbed`；改完复跑 noop 与 gold。
- **执行上下文（硬前置）**：12 题（aiohttp 5 + numpy 7）的目标包没装进 venv，必须 `cwd=/testbed` + 相对路径 `r2e_tests`，否则全部用例 ERROR、reward 恒 0 且**静默**。建议 rh2 侧加断言而不是给 0 分。
- **入口 + 评分面保护（M3 第二片终稿，关键）**：pillow `3ac9396e` 只能沿用自带的 `unittest_custom_runner.py`；orange3 7 题需 `xvfb`（已装在对应镜像里）。**M3 实测证明「把 `run_tests.sh` 与 `r2e_tests` 属主收回 root」（布置 c）是无效防护**——只要 `/testbed` 目录可写，候选就能 `unlink` 掉 `run_tests.sh` 换成自己的（实测放入 `echo FAKE_ALL_PASS`）、把 `/testbed/r2e_tests` 整个 `mv` 走换成伪造用例、替换 `.venv/bin/python` shim；只有 `/r2e_tests`（在 `/` 下）动不了。**因此评分面只能靠协议保护**：grader 回合结束后从 `/r2e_tests` 重拷、用自己保存的 `run_tests.sh` 原文执行（不读 `/testbed` 里那份）、仍必须 `cwd=/testbed`。这是 D01 根因族在 R2E 侧的具体形态。
- **候选身份（已实测修法，M3 第二片终稿）**：**布置 b（把解释器 `cp -a` 搬出 `/root` 到 `/opt/py`、改 `pyvenv.cfg`/符号链接/shebang，`/root` 保持 700）作为默认**——判分一致性 **116/116** 与 root 基线逐键相同（b 做了全 48 题×2 gate=96 次，a/c 各 5 镜像×2 gate）；布置 a（就地 `chmod o+rx /root` + `chown`）判分一样但把 `/root`（292 MB）暴露给候选且 `sys.path` 仍留 3 条 `/root`，b 两者皆 0。**代价：`chown -R /testbed` 是主要开销（中位 23.1 s、最长 157 s、48 题合计 32 分钟，overlay 可写层涨到中位 652 MB / 最大 2.28 GB），只能在派生镜像 build 时付一次，不能进每个 episode**；搬迁解释器仅中位 3.6 s。
- **重复稳定性（已补齐）**：48 题各跑两次 gold（3 vs 4 workers），48/48 `reward_same` 且逐键一致、状态翻转 0。
- **确定性**：coveragepy 5 题的 `addopts` 含 `-n3` + `flaky` 重试 + `--failed-first`（读写 `.pytest_cache`）；每次从干净容器起，或显式 `-p no:cacheprovider`。
- **候选 delta 排除**：`r2e_tests/`（48/48 由 setup 拷入）与 `.pytest_cache/`（47/48 运行生成、被 `.gitignore` 挡住）需单独立项。

---

## f. 早上 60 分钟阅读路线

| 步 | 分钟 | 读什么 | 目的 |
| ---: | ---: | --- | --- |
| 1 | 5 | 本文 §a（一页结论 + 处置表 + 8 条发现） | 拿到全局 |
| 2 | 10 | `M2/M2_report.md` **§7 全节**（7.2 / 7.5 / 7.6 三张表）| 亲眼确认三条满分通道与"账本不可区分"这一条；这是决定 D01 的唯一必要材料 |
| 3 | 5 | `L6_rh2_code_check/claims.json` 的 **C18、C11、C05** 三条 + `batch4_scoring_20260910/impl_plan_20260915.md` **§9.6 第 5/6 条** | 知道哪些既有前提被推翻：stage1 口径、rc 已接入、`additional_exclusions` 是废字段 |
| 4 | 10 | 本文 §b 的 16 行表 + `decision_items.json` 里 **D01 / D08 / D09 / D07 / D06** 五项的 `options` 与 `coordinator_view` | 对排前五的决策项做取舍；其余 11 项按需展开 |
| 5 | 5 | 本文 §c-1 / §c-3 / §c-4 / §c-6 | 四条包间分歧的收敛结论与仍需代码核对的一条 |
| 6 | 8 | `M3/M3_report.md` §2.1–§2.4 + §4 | R2E 能否接入：两条硬前置 + 已实测可用的清理方案 |
| 7 | 7 | 本文 §e 的"跨仓库"表 + 你关心的仓库两节 | 环境修复的具体条目与已验证参数（tmpfs 4 GiB、wheel 清单、两份资产的 sha256） |
| 8 | 5 | `split_constraints.json` 的 `stats` 与 `duplicate_task_pairs` | 划分粒度的代价：strict 110 题/40 组 vs full 148 题/36 组，以及 mypy/pydantic/modin/pandas 在 full 口径下无法仓库内切分 |
| 9 | 5 | `L5_evidence_index/L5_evidence_index.md` §3 与 §6 | 记住 signals 表的 34 题空值是快照问题，以及 C3/C4 两条不可互译的口径 |

**先拍三项**（低成本、各包意见一致）：D02 参考 ID 回退、D12 wheelhouse 预置、D13 新建文件恢复改 `rm -f`。
**必须先于其它决定的一项**：D01。

---

## 未纳入本稿的内容

- 机器 1 的 **e2 与 P-A 回归已全部完成**（协调者 04:xx 补记）：证据 `runs/swe_grading_wiring_20260915/e2/`（`ledger_e2_{A,B,B_repeat,C,C_shm1g,derived}.jsonl`、`eval_logs/`、`artifacts/`、`derived/{build.log,images.json}`、`reg/`），报告 `swe_grading_wiring_20260915/e2_report_20260916.md`，对账 `swe_grading_wiring_20260915/reconcile.md`，实施 `batch4_scoring_20260910/impl_plan_20260915.md §9`。结论：24 候选可比 15 题 15/15 与投影组 oracle 一致；7 题 apply 失败为已知 fuzz 题；modin-6298/6937 零解析连 gold 也失败（环境侧，定向探针在跑）；MONAI-1121 派生镜像 resolved；MONAI-763 shm 1 GiB 触 4 GiB OOM（并入 D10：shm 与 memory 联合定档）。由另一会话（A/grading）维护，本稿引用其结论（§a 第 1/5 条、§c-6、D01、D04）未复制数据。
- **M3 第二片已全部完成并纳入**（`M3/M3_uid_fix_probe.json`、`M3/M3_gold_repeat.json`、`unrelated_ledger/`；报告 §8）：候选身份 **116/116** 与 root 基线逐键一致（布置 b 默认，见 §e R2E）、gold 重复稳定性 **48/48** 逐键一致（`log_sha256` 每次不同、不可作判分稳定性指标）、`probe_unrelated` **10/10 判 0** 且 `n_missing=n_extra=0`、判别键数与 noop 相同。关键结论：文件属主收回 root 无效、评分面只能靠协议保护（已并入 D01 与 D15，见 §e R2E）。未做：`probe_unrelated` 另 38 题、对抗型无关补丁。
- **L7 假修复套件**：本稿定稿时 `L7_fake_fix_kits/kits/` 已有 29 个套件目录，但**没有任何实跑结果**（需在镜像容器内执行），因此未纳入；D05 的"先做反例实测"依赖它。
- **M2 的 `M2_task_records.json`（17 题）**：只引用了报告正文的结论，未逐题展开。
- 13 个 L1 包、L0/L2/L3/L4/L5/L6、M2、M3 **均已完成并纳入**。
