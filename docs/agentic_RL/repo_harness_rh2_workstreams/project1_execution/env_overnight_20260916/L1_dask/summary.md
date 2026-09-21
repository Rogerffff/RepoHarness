# L1_dask · 逐题静态审查小结

范围：dask/dask 14 题（ASSIGNMENT.json 顺序）。方法：先只看 `problem_statement` + base 代码写 `public_view`，再读 `test_patch` / `fail_to_pass` / `pass_to_pass` / `golden_patch` / `hints_text`。
base 代码用裸克隆的 `git -C runs/env_overnight_20260916/repos/dask show <base_commit>:<path>` / `git grep` 读取（COMMON.md 允许的只读操作），**未建 worktree、未起 Docker、未装依赖、未连远程机器、未调模型 API**。
逐题记录：`records/<instance_id>.json`（14/14，均为合法 JSON）。仓库级共性事实：`repo_level_findings.md`（R0–R12），题级记录用 `repo_level_findings.md#R<n>` 引用。
辅助产物在 `runs/env_overnight_20260916/L1_dask/`：`mat/`（四面材料抽取）、`prescan.json`（路径/参考集/日志交叉表）、`refskip.json`（逐条参考 ID 的依赖守卫扫描）。脚本在 `scripts/`：`prescan.py`、`collide_skip.py`（ID 塌缩与跳过扫描）、`extrakeys.py`（status_map 伪键/参考集外失败）、`depscan.py`（可选依赖与网络标记）、`prefail.py`（工具链版本与恒失败统计）、`refskip.py`（逐条 F2P/P2P 是否被 importorskip/skipif 守卫）、`dump.py`（逐题材料打印）。

| task | 主要发现 | 建议处置 | 下一实验 |
| --- | --- | --- | --- |
| dask__dask-7656 | 题面 **Fix** 段直接给出修复代码；gold 改了 `unpack_collections` 与 `to_task_dask` 两处，**F2P 只走前者**（P2P 里的 `test_to_task_dask` 不含 dataclass 用例）；DeepSeek 候选用语义不同的 `if f.init`（无条件丢弃 init=False 字段，gold 是保留已赋值的）却同判 RESOLVED_FULL；gold 漏掉 `dask/base.py:431` 同源 bug（候选主动补了） | needs_review | 只改 `delayed.py:109` 一处跑 F2P+48 P2P，预期满分 |
| dask__dask-7894 | **本包判别力最好的一题**：7 个参数点覆盖单轴/双轴/标量 drop_axis，depth 与 boundary 逐轴不同；base 就通过的 2 个参数点自动进 P2P 构成反向保护。缺口：`da.random.standard_normal` **无随机种子**，输入每次不同 | ready_for_probe | 同一参数点连跑 20 次看稳定性 |
| dask__dask-10972 | **题面与评分不是同一问题**：题面要"让 strict xfail 行为一致"（且归因 s390x 大端，x86_64 镜像不可复现），评分要 BOM 编码下 read_csv 结果正确；题面字面方案只能改被禁止的测试文件。另：唯一 `rc_install=1` 的题（2024.2 PEP 517 离线）；3 条截断 P2P ID | reject_revision | 题面原样喂基座 3 次，统计几次改到 `dask/dataframe/io/csv.py`（预期 0） |
| dask__dask-6626 | F2P 直接断言 `meta_nonempty`，**题面的 set_index 场景无任何覆盖**；同函数另一分支用例 `test_nonempty_series_sparse` 因 pytest 8 移除 `pytest.warns(None)` 恒失败被排除；好的一面是 P2P 的 `test_meta_nonempty_empty_categories` 用 `type(categories)` 检查能拦住写死空 object Index | needs_review | gold/base 各跑题面两段代码确认一致/不一致 |
| dask__dask-6801 | 题面"代码跑 4 次"→F2P"写回后 read-parquet 的 BlockwiseParquet 层仍在"隔着长推理链；题面主诉的一半（schema='infer' 的 4x）按维护者裁定是 WONTFIX；**判分只覆盖 pyarrow**（72 条 fastparquet 用例全 SKIPPED），而 gold 重写的是两引擎共用的写路径 | needs_repair | 只把 `to_delayed()` 改成 `to_delayed(optimize_graph=False)` 跑 4 条 F2P |
| dask__dask-6818 | 干净：gold 三行（把 blocksize 放进 tokenize），F2P 断言"不同 blocksize 名字不同"、P2P 的 `test_multiple_read_csv_has_deterministic_name` 断言"相同参数名字相同"，正反互补堵住随机化假修复。保留：题面 MCVE 依赖 S3 与 distributed 集群，容器内不可复现；3 条截断 P2P ID | ready_for_probe | `--junitxml` 跑同命令比对逐 ID 集合 |
| dask__dask-7138 | 题面逐字给出修复（`asasanyarray(array_like).reshape((-1))`）；gold 两行；F2P/P2P 判别力完整。**同文件 92/561 条用例（16%）因 pytest 8 恒失败**，是本包工具链错配最严重的一题 | ready_for_probe | 镜像装 `pytest<7` 重跑，统计恢复条数 |
| dask__dask-7305 | **最该裁定的一题**：唯一的 F2P 是修法副作用（小整数 divisions 从 `{1,2,3,4}` 变 `{1,2,4}`），公开材料推不出；hints 里维护者自己倾向的方案 2（安全转换检查）能正确修好 uint64 却会被判 0；而真正复现题面 bug 的新增用例 `test_set_index_interpolate_large_uint` **在 base 上就 PASSED**、落进 P2P、零判别力 | reject_revision | 在 base 实现 hints 方案 2 跑 F2P，预期 FAILED |
| dask__dask-8597 | gold 一行（`or other_numel == 0`）；F2P 与题面逐字对应；P2P 的 `test_take_avoids_large_chunks` 能拦住"无条件 inf"偷懒修法。保留：题面 traceback 被省略号截断，出错行只在不可见的 hints 里 | ready_for_probe | 装 `pytest<7` 后把 `test_getitem_avoids_large_chunks` 纳入 P2P |
| dask__dask-8792 | **题面逐字给出的"应有实现"与 F2P 要求的行为不一致**：题面保留 `if token:` 分支，gold 删掉该分支改为对完整 key 求 token；`clone_key("inc-1-2-3",123)` 因此不同 —— 照题面做必判 0。F2P 用 4 个逐字 md5 常量做验收标准，还锁死了 `tokenize` 的哈希行为 | needs_repair | 原样实现题面那段函数跑 F2P，预期第一条即 FAILED |
| dask__dask-8801 | **题面是没有任务的求助帖**（7784 字符里 ~90% 是 conda 安装回显），"应当给出更好的报错"这条裁定只在不可见的 hints 里；F2P 把 `is malformed` / `original error message` / `must have a dict` 三段英文文案固化成验收标准。另：gold 的"忽略权限错误"分支因**容器以 root 运行**导致 `test_collect_yaml_permission_errors` 恒失败而零保护 | reject_revision | 写文案不同但语义正确的修复跑 F2P，预期 FAILED |
| dask__dask-8820 | 干净：gold 8 行（DelayedLeaf 上加 `__name__`/`__doc__` property）。缺口：题面只提 `__name__`，F2P 还要 `__doc__`；**base 已含 dask__dask-7656 的 gold**（跨题泄漏，P2P 交集 43/45） | ready_for_probe | 只实现 `__name__` 跑 F2P 确认第二条失败 |
| dask__dask-9212 | 题面直接给出 gold 的完整实现（`@normalize_token.register(Enum)`）。判据设计好：4 个枚举类型里 base 就通过的 `IntEnum`/`IntFlag` 自动进 P2P，`tokenize(RED)!=tokenize(BLUE)` 堵住返回常量的假修复，且**不含逐字哈希常量**（与 8792 对照）。**base 已含 dask__dask-8792 的 gold** | ready_for_probe | 全池做"A 的 gold 是否已在 B 的 base 里"交叉检查 |
| dask__dask-9378 | **链路最干净**（137 条结果行 = 137 个键，0 skip / 0 伪键 / 0 恒失败）；三个 `*_like` 参数点判别力独立，`empty_like` 只比掩码不比数据，断言边界处理得当。缺口：题面复现用顶层 `da.ones_like`、评分要 `da.ma.*`，存在会被判 0 的合理解读分叉 | ready_for_probe | 只改 creation.py 让顶层保留掩码，跑 3 条 F2P 预期全 FAILED |

## 覆盖与统计

- 覆盖 **14/14** 题，全部落盘 `records/<instance_id>.json`。**未做清单：空**。
- 处置建议分布：`ready_for_probe` 7（7894、6818、7138、8597、8820、9212、9378）、`needs_review` 2（7656、6626）、`needs_repair` 2（6801、8792）、`reject_revision` 3（10972、7305、8801）。
- 记录 issue 数：P1 14 条、P2 19 条、P3 10 条。逐项检查状态：`pass` 165、`issue` 63、`unknown` 2（7305 检查 2、6801 检查 24）。
- `file_rules.additional_exclusions`：**14/14 题均为 `[]`**。依据：14 题的 `test_patch` 各只触碰 1 个测试文件、`golden_patch` 各只触碰 1 个源码文件，无混合职责（`repo_level_findings.md#R6`）。
- 链路健康度（stage1 离线日志）：14/14 题 `gold=RESOLVED_FULL`、`empty=RESOLVED_NO`，`f2p_missing=p2p_missing=0`；13 题 `rc_install=0`，仅 10972 为 1（离线 PEP 517，不影响判分）。
- 方法与限制：全部为**静态审查**。凡标 `pass` 的检查都附了具体文件行号或日志路径；未做的检查写 `not_checked`，证据不足写 `unknown`（7305 的检查 2、6801 的检查 24 是本包仅有的两条 `unknown`）。

## 仓库级（跨题）发现摘要

详见 `repo_level_findings.md`，此处只列结论与锚点。

1. **#R2（新机制，与 moto 的 R8 不同）**：`pytest -rA` 的 SKIPPED 行格式是 `SKIPPED [<计数>] <文件>:<行号>: <原因>`，不含 `::` 测试 ID。`parse_log_pytest` 取 `split()[1]` 得到 `[3]` 这类**计数括号伪键**，于是 —— (a) 所有被跳过用例的真实 ID **完全不进 status_map**；(b) status_map 混入 1–9 个非测试的伪键（6801 有 9 个）。直接后果：某条 F2P/P2P 一旦在重建镜像里因缺可选依赖变成 SKIPPED，它在 status_map 里表现为"不存在"而不是"被跳过"。**RH2 把"参考 ID 缺失"算失败还是算 infra 异常，会决定这类环境漂移被判 0 还是被判基础设施错误** —— 需要用户裁定。
2. **#R3**：镜像是 **pytest-8.3.2 + 2020–2022 年的 dask**，`pytest.warns(None)` 已被移除，导致大批既有用例恒失败并被自动排除出参考集。最极端的是 7138（92/561 条、16%）；最要命的是 6626（与 gold 同函数另一分支的唯一回归用例被排除）与 8597（同段代码的 getitem 侧用例被排除）。这不是"参考集被污染"（参考集在同一镜像上生成，自洽），而是**回归保护被系统性削弱**，且检查 6 的"历史工具链已恢复"在 dask 上不成立（`SPECS_DASK` 连 `python` 都没声明）。
3. **#R1 / #R4**：moto 的 ID 截断塌缩机制在 dask 同样存在（10972/6818 各 3 条截断 P2P ID，`fragile_reference_id` 同样记 false），并在 9212 出现**真实塌缩**（3 个截断键各吞 2 条用例，均不在参考集内）。另发现第三种污染：捕获日志里顶格的 `ERROR <logger>:<file>:<line> ...` 行会被当成一条"测试"写进 status_map（6801 的 `dask.dataframe.shuffle:shuffle.py:1205`）。
4. **#R5**：dask 根目录有 `conftest.py`（2024.x 还有 `dask/conftest.py`），里面已定义 `pytest_addoption`/`pytest_runtest_setup`；14/14 题的 test_patch 都不碰它，因此它不属控制面（`HygieneRules.test_files` 只取 test_patch 精确路径、`test_globs=()`），候选对它的修改会被重放进评分容器。这是 `rh2/src/repoharness2/grading/trusted_projection.py:22-24` 已登记的缺口在 dask 上的**直接可达性证据**，不是新漏洞；dask 适合作该缺口的最小反例。
5. **#R13（协调者点名的三项）**：逐条核对 **1706** 条参考 ID —— 被依赖守卫覆盖的 103 条里 **F2P 只有 1 条**（7656 的 `importorskip("dataclasses")`，标准库，不会触发），stage1 gold 侧 **没有任何 F2P/P2P 被 SKIPPED**；6801 的 `fastparquet`/`snappy` 守卫是条件式的、只对缺席引擎的参数生效，而参考集里只有 `[pyarrow-*]`。**xdist**：14 题 `eval_cmd` 全带 `-n0`，dask 各版本 `addopts` 也无 `-n auto`，与 mypy 情况相反。**时间敏感/随机**：`@pytest.mark.slow` 全被跳过且不在参考集内，唯一随机性是 7894 的 `da.random.standard_normal` 无种子。**网络**：参考测试文件里无 `mark.network`、无真实 s3/http 端点；需要网络的只有 6818 与 10972 的**题面复现脚本**（不进判分，但 agent 无法在容器内复现现象）。真正的风险不在"现在"，而在换镜像后会被 #R2 掩盖成 `f2p_missing`。
6. **#R11**：本包内有两对"后一题的 base 已含前一题的 gold"（7656→8820、8792→9212），且都**不会被按 `problem_statement` 或 `base_commit` 的去重逻辑命中**。8792→9212 尤其严重：9212 的 P2P 里就含 `test_clone_key`，带着 8792 修好后的期望哈希常量。

## 最值得用户裁定的 3 个问题

1. **参考 ID 在 status_map 里"缺失"应判什么？**（#R2）dask 上被跳过的用例真实 ID 一条都不进 status_map，只留 `[1]`/`[2]` 伪键。当前 14 题的参考集恰好没有落在跳过用例上，所以问题被掩盖；一旦镜像重建或可选依赖变化（fastparquet / lz4 / matplotlib / pyarrow），受影响的题会静默变成"F2P 缺失"。请裁定：缺失 = 失败（判 0）还是 = infra 异常（不计入 reward）？以及是否改用 `--junitxml` 之类的逐 ID 输出替代文本 parser。
2. **"公开材料推不出 F2P"的题怎么处置？**本包 4 题（10972、8801、7305、8792）属于此类，其中 8792 更糟——题面逐字给出的实现与评分要求相反，照题面做必判 0；7305 的唯一 F2P 是修法副作用，维护者自己倾向的另一种正确修法同样判 0。请裁定是"改题面 + 放宽断言后保留"、"整体剔除"，还是"保留但只做训练不做评测"。这一类在 moto 侧也已出现（错误文案固化），建议形成全池统一口径。
3. **工具链口径：要不要把 pytest 钉回各版本 CI 的历史区间？**（#R3）dask 配方连 `python` 都没声明，镜像一律 pytest-8.3.2，代价是 7138 有 16% 的用例是死的、6626/8597/8801 各自最相关的回归用例被排除。钉回 `pytest<7` 能恢复大量 P2P，但要重建镜像并按检查 39 重验全部 dask 题。请裁定是否值得，以及在此之前是否要把"参考集外恒失败数"作为题级健康度字段落进 facts。
