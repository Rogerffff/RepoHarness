# mypy-15184 R10：非作者 Falsifier / Simplifier 增量审查

日期：2026-10-03。角色：按 `review-standards.md §10.4` 尝试推翻本轮正式评分的语义解释，并检查方案是否最小充分。已读作者、gold 与私有材料，**不是 fresh 公开读者**。

只核 `mypy15184-nested-nominal-types-v2` 的新五参考、四候选正式 CPU 增量。只读本地原件、计算 SHA、解析 JSON 和原始日志；未 SSH、Docker、运行测试或模型。唯一写入为本报告。未重跑旧矩阵、10174、私有校准或未变公开输入，未修改 shared、输入、旧报告或 JSON。

## 结论与用途

**本范围没有可证实的新 finding。** 独立回读支持正式奖励 `noop/gold/bad/top_only = 0/1/0/0`：两类已知错解均在目标断言正文上被拒绝，没有发现安装失败、未执行、缺席解析或额外 `-k` 节点混算造成的误拒。

本报告支持 **15184 新材料的普通 GPU intake CPU 条件**；主审还需结合 Production Tracer 的运行链路结果裁决。实际 GPU 首条 solver 消息交付、兼容 freeze、模型求解与题级终审由后续入口核实。一次 CPU 结果不证明稳定模型能力或正式训练资格，`env_qualification=absent` 也没有被本报告改写为 qualified。

## 固定身份与五参考

证据根为 `runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa`；冻结来源为 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1`。独立重算公开与评分 bundle 的规范化 digest，分别为 `sha256:77b85678b3f20ef5689e4a9b646518ae1247407ff44b250803563c11dce3ea7e`、`sha256:3a3c4e78c7dc1b1dce9187d36d00079c4d08621f7019140e6544e77b9f2db4bf`，与 [binding](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184_r10_binding_v1.json) 及四条 ledger 一致。环境 digest 均为 `sha256:de06cc63c20f88a4691b7037dfeaeae5f31c4dc13f09cf703161cf6df2954f1e`；实际派生镜像均为 `sha256:76b5b2646a9eb134e6349ee8e214bb84eb6030c34a234e167351acdec5dd8c54`。

为方便阅读，以下缩写只用于本报告；完整参考键仍是事实来源。

| 本报告名称 | 正式分区 | 完整参考键 |
| --- | --- | --- |
| F1 | 原 F2P | `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::testAssertTypeFail1` |
| F2 | 原 F2P | `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::testAssertTypeFail2` |
| N | 新 F2P | `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::testAssertTypeFailNestedNominalTypes` |
| P3 | 原 P2P | `mypy/test/testcheck.py::TypeCheckSuite::check-assert-type-fail.test::testAssertTypeFail3` |
| P | 新增已有 P2P | `mypy/test/testcheck.py::TypeCheckSuite::check-expressions.test::testAssertType` |

比较 [来源原 patch](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/private/python__mypy-15184/test.patch)、[冻结 effective patch](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/mypy15184_nested_f2p_p2p_v1/effective_test.patch) 和作者 nested_v2 草案：原三个 case 的前 28 行逐行完全保留，仅追加一个 12 行嵌套 case；原补丁的无末尾换行标记没有改变任何原断言正文。effective patch 三方字节一致，SHA 为 `e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532`。原两 F2P、一 P2P 的键及分区保留；新增各一键，没有升格另外四个开发回归。

`check-assert-type-fail.test` 在精确 base 中不存在，正式流程记录先确认不存在并删除候选同名文件，再恢复公开 `check-expressions.test`（SHA `f541a878…`）和应用新建文件 patch。四份 diagnostics 均记录 setup apply 成功、两文件齐全、无不规则文件及保护成功。没有把新建私有测试当成 base 既有公开节点。

## 原始执行结果与反证尝试

`PASSED` 指 pytest case 的实际输出匹配预期；失败断言 case 通过仍意味着 mypy 报告预期类型错误。

| 候选 | F1 | F2 | N | P3 | P | reward | 本次实际失败依据 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| noop | FAILED | FAILED | FAILED | PASSED | PASSED | 0 | 原两 case 未限定 array；嵌套仍输出 `List[C]` / `List[C]` |
| gold | PASSED | PASSED | PASSED | PASSED | PASSED | 1 | 无失败 |
| bad | PASSED | PASSED | PASSED | PASSED | FAILED | 0 | 给合法 `int/int` 与 `Literal[42]/Literal[42]` 额外报错 |
| top_only | PASSED | PASSED | FAILED | PASSED | PASSED | 0 | 只处理顶层同名 Instance，嵌套 C 仍未限定 |

- **尝试解释成未执行或解析缺席：不成立。** 四份 raw eval 都显示 `collected 5 items`，段内 summary 各恰好五个不同完整节点。我用原始 `PASSED/FAILED` 行独立重建状态，节点集合等于五参考，逐节点状态与 diagnostics/ledger 四分区完全一致；不是只读作者的奖励摘要。每条 ledger 仅一行，missing/skipped/unaccounted 均空，`num_parsed_outside_segment=0`。
- **尝试解释成安装失败：不成立。** 四份 raw eval 完整记录 `python -m pip install -r test-requirements.txt` 和 `python -m pip install -e .`，editable wheel 成功构建/安装，没有失败 trap；`RH2_INSTALL_RC=0`、install 未跳过、日志完整，观测导入 `/testbed/mypy/__init__.py`。安装两条命令未分别输出数值 rc，因此这里的依据是完整成功正文、无失败 trap 与安装段完成，不能声称有独立逐命令 rc 记录。
- **尝试解释成 extra `-k` 混算：不成立。** 冻结 [spec_vendor.py](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/repo/rh2/src/repoharness2/envpack/spec_vendor.py) 的 15184 分支（215–229 行）移除 vendor 前缀末尾尚无表达式的 `-k`，拼接五个完整节点；四份 raw eval 实际命令确实是 `pytest -n0 -rA` 加五节点，收集/summary 也只有这五个。旧公开 actor 的宽 `-k testAssertType` 收集结果没有并入新正式参考。
- **尝试把 top_only 的 0 分降为格式小差别：不成立。** [top_only 原始 eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/top_only/eval_logs/evallog_replay-swe-mypy-mypy1518_18eeed97.eval.log) 501–520 行，期望 `List[a.C]` / `List[b.C]`，实际 `List[C]` / `List[C]`。类型错误依然发生，但诊断不能区分不同类，正好违反公开行为目标；另四节点通过排除了基础行为整体失效。
- **尝试把 bad 的 0 分降为纯候选标签拒绝：不成立。** [bad 原始 eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/bad/eval_logs/evallog_replay-swe-mypy-mypy1518_2ea87688.eval.log) 504–533 行显示公开 `testAssertType` 实际产生合法断言误报；私有负对照将公开 base 的 `if not is_same_type(...)` 改为无条件报错，gold 文案修复同时保留。评分拒绝依据为新 P2P 正文失败，未发现通过候选名称、补丁 hash 或源码修法名定向判 reward。

[noop 原始 eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/noop/eval_logs/evallog_replay-swe-mypy-mypy1518_7256eb23.eval.log) 466–511 行支持原两消歧失败及嵌套失败；[gold 原始 eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/gold/eval_logs/evallog_replay-swe-mypy-mypy1518_233b3249.eval.log) 485–496 行显示五正式节点全通过。四条 ledger 都为 projectable，非测试源码投影、无 ignored_paths、无 stage_error，runner digest 未变，cleanup removed=true。[slot status](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/slot/status.json) 的子进程 rc 与 [launch receipt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/launch/receipt.json) 的 wrapper rc 均为 0，结束时间分别为 `2026-10-02T21:55:18Z`、`21:55:19Z`，两 stderr 文件为空。

## 公开依据、gold 偏置与最小充分性

**新 P2P 有独立公开依据。** 精确公开 base 的 [check-expressions.test](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/test-data/unit/check-expressions.test) 931–942 行已经覆盖合法 `assert_type(a, int)`、合法 literal、返回表达式的 int 类型以及真实失配；新评分复用整个既有 case。[公开 assert-type 文档](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/docs/source/error_code_list.rst) 884–896 行要求推导类型匹配给定类型，并公开包含 list[int]/list[str] 示例；[checkexpr.py](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/mypy/checkexpr.py) 3911–3932 行仅对非相同类型报错并返回 source_type。题面最后一段也明确要求合法断言继续成功与保留表达式类型。因此 bad 的拒绝没有要求 solver 猜隐藏的新语义。

**嵌套 F2P 是公开行为目标的直接组合。** 公开题面要求不同类型共用短名时诊断能区分它们，没有把目标局限在顶层。[messages.py](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/mypy/messages.py) 2559–2602 行的既有 collect/find overlaps 会遍历 type arguments，2350–2370 行递归格式化参数，2638–2661 行已有 jointly format types 的公共惯例。这支持用 `list[a.C]` 与 `list[b.C]` 检查相同消歧目标。它没有要求新型类型关系、改变判相等或额外实现步骤。

**List 的 v2 修正有公开来源，而非仅照顾 gold。** [testcheck.py](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/mypy/test/testcheck.py) 128–129 行对不含 `lowercase` 的测试文件强制 uppercase builtins；[options.py](../../../../../../../../runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15184/base/mypy/options.py) 361–364 行及 `messages.py:2409–2411` 将该配置解析为既有 builtin alias `List`。新增 case 所在文件符合这个配置，即使 case 指定 `--python-version 3.9` 也如此。历史私有 v1 错误 oracle 的小写 list 失败记录保留，本报告不重审或回写它。

gold 候选的原始来源 patch 与本轮 artifact SHA 都是 `365adadc…`；只把失配消息改为共同格式化两类型，没有针对新 case 名、模块 a/b 或 List 字面量的分支。冻结评分依据节点结果和 F2P/P2P 分区，gold 的成功不单独证明任意合法替代修法都会通过，但未发现仅 gold 可满足的实现约束。

对于**本次两个已知漏洞**，各新增一节点已最小充分：删 N，top_only 的另外四节点全通过；删 P，bad 的另外四节点全通过。增加开发四 case、再加状态机、重复旧矩阵或广泛拒绝候选源码均没有本轮证据要求。新 N 拒绝嵌套名称仍歧义的部分修复，新 P 拒绝破坏有效断言的候选；这些是公开要求不完整或被破坏的候选，没有本轮证据证明系统性拒绝正常解法。真实模型中的发生率未知，四个预造候选不能估计训练分布比例。

## 公开输入和实际 solver 交付边界

发布 public record 与 [fresh 已审 bundle 草案](../python__mypy-15184/public/public_bundle_draft.json) 解析后完整 JSON 对象相等；按冻结 `_base.py` 规范化规则重算得到同一个 `77b85678…`。题面 UTF-8 字节与独立 `problem_statement_v1.txt` 完全相等，SHA `c1765909…`。[fresh 固定输入 manifest](../python__mypy-15184/public/reader_input_manifest.json) 的六文件 SHA 全部仍匹配；[既有 fresh 报告](fresh_public_reader_20261003.md) 本身 SHA 也与发布请求固定值一致。因此可以复用该 bundle 的既有 fresh 静态审，不把 JSONL 的序列化排版与草案文件原始字节 SHA 混为一项。

新 [GPU 公开辅助说明](../python__mypy-15184/public/development_note_20261003.md) 只陈述已核解释器/源码路径、公开两模块复现方式、失配退出 1 的含义与既有公开 `testAssertType` 精确命令。未看到私有 nested case、gold 修法或新隐藏标准。它不是原 fresh 六输入的一部分；本次只做这几行的非 fresh 边界核查，不能写成原 fresh 已审此新增说明。环境文字复用既有 actor/CPU 事实，GPU 实际入口仍须核其当前解释器与源码。

[本次 prepared prompt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/prepared/prompts.jsonl) 含新版题面和 `77b85678…` 身份，可证明准备产物正确；**不能证明真实 solver 首条消息已经收到它**。本轮四候选是预先冻结的 noop/patch replay；ledger `candidate.kind=cc` 与既有 Claude Code 控制桩运行也不是模型求解证据。实际 GPU 首条消息与新题面完整交付仍未发生，后续必须保存真实首条消息/身份回执，并核对没有私有 grading、gold、坏候选或评分参考泄漏。

## 停止条件与残留范围

本角色的停止条件已满足：已从原始 ledger/eval/diagnostics 核成 20/20 正式节点状态、两类错解的真实失败点、原三 case 保留、公开依据、extra 选择范围与公开 bundle 身份。**停止本 CPU 增量审，不新增探针或扩大审核。** 可由题主汇合运行链路审查后把本版提交普通 GPU intake；这里没有要求新的用户决策或重复 fresh 审。

普通 GPU 接续应保持本 binding 的 public/grading/environment/patch 身份、五参考和已验证冻结 consumer 语义；兼容 freeze 由入口另核。如果这些身份或实际测试选择变更，按影响复核；不能直接复用本版结果。真实 solver 消息交付应作为后续入口验收事实记录，不能由旧控制 prompt 或本 prepared 文件替代。

仍未证明：全部可能错解均被拒绝、所有表达语义等价但输出不同的方案均能通过、并发/跨机重复稳定性、模型能力、GPU 完整运行或正式训练准入。四原件都有 `env_qualification=absent`。这些边界应随结果登记，不以纯假设增加本 CPU 审阻塞；后续真实模型结果暴露具体题目缺陷时，才按实际影响回到题级修复。

## 关键原件 SHA-256

独立重算作者索引的本 job 55/55 原始文件 SHA 全部一致；冻结 release 中本范围选取的 12 个材料/producer/consumer 文件与 manifest 全部一致。未将此窄核写成独立重验 release 全部 950 文件。下列 SHA 均在本次直接计算，非照抄作者索引。

| 原件 | SHA-256 |
| --- | --- |
| [release manifest](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/manifest.json) | `00ac5c375629f59543f548fbc7b0cb3cbe7d1418f7a956d9deebcefab2e8a87c` |
| [R10 binding](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184_r10_binding_v1.json) | `a3d4a085a8d3f28db88f1184025d54018d3874bb95a2b37f9a6ca57495786bef` |
| [作者 publication 索引](../python__mypy-15184/publication_readback_20261003.json) | `21fe8784130cf251c4cf5033316d6fb3983506f8ba4481a0954f310a207b418f` |
| [作者 revised CPU 索引](../python__mypy-15184/revised_cpu_readback_20261003.json) | `b662e4f29b7ec14663faef82484faf6526cc772769052183e1aa047cf077ae86` |
| [revision registry](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/mypy15184_nested_f2p_p2p_v1/material_revisions.json) | `7abfdf350875e5d28c679ac196f20c8a44efdce184fa7be00ddf97cb2009740c` |
| [effective test patch](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/mypy15184_nested_f2p_p2p_v1/effective_test.patch) | `e6d5eb0ef39aeeb08a945d3ce6aeb340a7f8b4fd56e599247dbef3b99bf4e532` |
| [公开 P2P base 文件](../../../../../../../../runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe14_preflight_v1/repo/docs/agentic_RL/repo_harness_rh2_workstreams/s2/revisions/mypy15184_nested_f2p_p2p_v1/public_tests/python__mypy-15184/test-data/unit/check-expressions.test) | `f541a8781c01edf4a27209cc1569e61d1d8a4741c3d4bc381548d0b1239ce3b9` |
| [fresh 报告](fresh_public_reader_20261003.md) | `02bcf5a6c2c06dab40d165b889433d9e4871c57ea04df92f6b0c16ba56438bda` |
| [public bundle 草案](../python__mypy-15184/public/public_bundle_draft.json) | `129e7341efd8699b2a379262647bb4868c8569429903d745cf5c15d54dba7606` |
| [公开题面](../python__mypy-15184/public/problem_statement_v1.txt) | `c17659095d0b4ab71caf2fab52dfaa52e9da009212381a7dc46053c015499178` |
| [新增 GPU 公开辅助说明](../python__mypy-15184/public/development_note_20261003.md) | `0fe106b96bd74d6f28ba226bdc2c8be1b67326048509a5636b8d600e35f3d1e7` |
| [slot status](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/slot/status.json) | `fc1a0f85ea97eea438ec50445ae1eb0e392b3a150c02408919108fc1a4efae8b` |
| [launch receipt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/launch/receipt.json) | `2d1461205e44b7dd48f8cc9a0bee67c295ce6052b5f340b02bc7024455ce876d` |
| [prepared prompt](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/prepared/prompts.jsonl) | `9956e3513a8441e5bb45e5dbf1e0cb0c7f2e9ffd601b005a84d65ceb4573c061` |
| [noop ledger](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/noop/ledger.jsonl) | `e28712d41e72b6ea9c368004fb1f1f9ec89e67302bec00ce45790bc919c214a9` |
| [noop diagnostics](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/noop/eval_logs/evallog_replay-swe-mypy-mypy1518_7256eb23.diagnostics.json) | `3d3488269ac977e7508629859b5ff2764124746af3dca8cb296b49b04ef1527d` |
| [noop raw eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/noop/eval_logs/evallog_replay-swe-mypy-mypy1518_7256eb23.eval.log) | `a8cc45338123ecc600a20093f506f5d55f1ef37f6834550f2bb9296e22f28abe` |
| [gold ledger](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/gold/ledger.jsonl) | `d8d4b047ffadcc86545ff1b7406937a1403e990ad0420cb6264fd00f78f32df8` |
| [gold diagnostics](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/gold/eval_logs/evallog_replay-swe-mypy-mypy1518_233b3249.diagnostics.json) | `e1774951c210a4c388a4b87d405f69dc199ef16e414728f9bd2338e4150dc9cc` |
| [gold raw eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/gold/eval_logs/evallog_replay-swe-mypy-mypy1518_233b3249.eval.log) | `17e5c4c5c153597c788d185835564d84b505a47fa7169a1af58be052e3aff35e` |
| [bad ledger](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/bad/ledger.jsonl) | `e564ad131d0454dbad3731298bdae724e1606ed30cc3ecd7a701a9add40b1802` |
| [bad diagnostics](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/bad/eval_logs/evallog_replay-swe-mypy-mypy1518_2ea87688.diagnostics.json) | `baaa34eef39662111c220795edfff31591d5aaf43966e3509de5a9571a2bed36` |
| [bad raw eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/bad/eval_logs/evallog_replay-swe-mypy-mypy1518_2ea87688.eval.log) | `2520976bb86cb0014fc91d9a8f3b3ffd36c88220718210f8954cd93fcf3fe179` |
| [top_only ledger](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/top_only/ledger.jsonl) | `abd8d92cefba8d789b4e64d1387a0ab475aaf7658420d492daf010a49bb808cf` |
| [top_only diagnostics](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/top_only/eval_logs/evallog_replay-swe-mypy-mypy1518_18eeed97.diagnostics.json) | `8666d42da3e8233866f1306edfb9b031bfeaed58326e16135ab64499b1df5b9e` |
| [top_only raw eval](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_mypy/cpu_a_round1/mypy15184-revised-r1-20261002T214419Z-e743aa/attempt/top_only/eval_logs/evallog_replay-swe-mypy-mypy1518_18eeed97.eval.log) | `7e9189f6a48b7817441825e21293d0bfc5f2357361b28bf6ac7f75fe0e822244` |
