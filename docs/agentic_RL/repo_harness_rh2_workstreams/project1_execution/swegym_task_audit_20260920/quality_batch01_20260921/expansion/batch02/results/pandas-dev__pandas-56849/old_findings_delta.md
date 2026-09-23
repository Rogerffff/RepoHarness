# pandas-dev__pandas-56849：历史差量

无历史初稿已由协调者封存，SHA256=`9d48e0f2531053df00fcc01e35dbed722f72898525894d54d6c61354539a10d2`，未回写。随后按 `runs/swegym_quality_batch02_20260921_v2/history/pandas-dev__pandas-56849/refs.json:1–5` 开放本题旧记录。下文路径均相对 `${REPO_ROOT}`；P/B/V/N/G/W 缩写沿封存初稿。

旧记录 `H=docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-56849.json` 全文1–71。额外读取本题 `S=runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/pandas-dev__pandas-56849` 的 gold eval.sh1–59；gold/empty status_map 全JSON计数与唯一F2P条目；gold test_output 的安装/重编译/收尾匹配行4193–4287、4519、4748–4752；empty 的目标 traceback/status/收尾匹配行4271–4294、4550–4558、5076–5077。没有运行旧脚本或新实验。

| 旧主张 | 复核结论 | 决定性证据与影响 |
| --- | --- | --- |
| base 确含 m 回归，gold恢复，419 P2P命中（H24–25、69） | 确认，收窄“判分链干净” | S 两侧raw/status_map支持旧观测；更新的W ledger11/12及N/G目标traceback/重编译/收尾也独立支持。真实426节点、评分420键须分开，不能由全部参考命中推断身份无损。 |
| F2P要求警告“逐字精确”且明确断言结果freq=ME（H30、48） | 推翻这两个表述 | `_warnings.py:147–163` 是re.search，非严格相等；`asserters.py:181–349` 和 `core/indexes/datetimelike.py:141–175` 不比较DatetimeIndex.freq。expected构造含freq不代表result.freq受测。当前发现相反的属性覆盖缺口。 |
| FutureWarning、ME 都只能由隐藏测试知道，因此严重规格不足（H17、20、30、48–50） | 大部推翻，仅保留warning措辞自由度 | 标题明说deprecated M；base `offsets.pyx:4863–4871`、旧date_range测试149–166和MonthEnd `_prefix=ME`、公开别名文档1239–1266已给依据。不能只读题面旧repr忽略当前仓库接口。没有理由直接要求补题面所有隐藏断言。 |
| 规范化后打印M的合理解会被小写m匹配拒绝（H31、41–45） | 确认静态疑点，未升格已测误拒 | 全test.patch、warning helper和公开规格支持；合理候选须仅规范化已识别旧别名，不能无条件upper破坏ms/MS。未发现其所建议候选的执行原件；一份候选也不能“量化合理解拒绝比例”。唯一后续实验沿初稿。 |
| warning filter使P2P依赖官方patch，前缀改成 `Freq 'm'...` 可令大量P2P变红（H51–55） | 耦合确认，例子和规模推断推翻 | marker只加在 `test_to_offset_invalid`，其中m相关两例为2h20m与-m（base50、66）；regex为 `.*'m' is deprecated.*`，容许 `Freq `前缀，因此旧建议反例不区分。大小写改M才可能超出filter。官方补充marker可合理适配新warning，不单凭它判题无效。 |
| 题面原例被F2P直接完整覆盖、419 P2P足以挡回归（H32–33） | 收窄 | F2P只2点，原例20点；m倍数、共享to_offset入口、freq属性缺检查。相关P2P有价值但没有Period测试；“建议回归测试列表”不是执行或通过证据。 |
| gold未改Period是待对齐局限（H34、65） | 不采纳为缺陷 | is_period是公开分离的接口语义，Period用M且ME报错（base scalar/period/test_period.py60–63、78–92）；不能要求对齐大小写而没有公开需求。Period回归可作定点保护，但无需把整文件当准入硬门。 |
| Meson可增量重编、旧约49.7秒install/6.5秒test（H36） | 旧局部运行确认，适用边界收窄 | S/gold/test_output4193–4270、4286–4752支持该时间及编译；新G3066–3069亦证候选扩展被编译。不能用于当前actor/54321：新ledger明确是grader/54322安装测试，apply_user只是应用补丁身份。旧耗时不填本轮costs。 |
| 420键对应426运行测试、4键发生碰撞（H38、56–60） | 确认；归原清单19而非11 | 新N/G的10节点合并为4键，parser源44–55明确空白切键及后写覆盖。两次现有合并节点均PASSED，不改变既有分差；未来失败混入时的实际错分尚未做实验。 |
| 同族无重复、公开hints为维护者原文、无泄漏（H26、29、35） | 未核实或对当前包过时 | 本次没有跨题关系审查或actor可见文件/网络验收。当前P/public_bundle.json的public_hints是harness操作/环境声明，不能沿用旧raw hints描述当作实际消息。旧泄漏扫描未读原件，保留未知。 |

处置不变：needs_review/static_review，development_diagnostic。维持空额外排除，无原题/环境/测试修订；warning措辞误拒只作静态疑点，尚待合理候选对照。reviewer待核。

封存初稿引用勘误：需求表中的 `B/offsets.pyx:4863–4871` 应展开为 `B/pandas/_libs/tslibs/offsets.pyx:4863–4871`；该源码已实际读取，证据内容不变，初稿保持原哈希。

阅读范围偏差已即时向协调者报告：试图查看旧record引用的 `runs/env_overnight_20260916/L1_modin_pandas/collide_detail.json` 文件结构时，误读前3行，仅暴露下一题键名与 `scoring_keys_with_collision=2`；随即停止，未读其余正文。本题初稿封存前无此暴露；此微量他题历史信息不得伪装为下一题完全无历史。
