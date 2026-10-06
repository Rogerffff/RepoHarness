# orange3 22e98：隔离 R-f 修订独立复核

2026-09-29，Codex。**结论：隔离材料修订通过。** `r2e-mr-064` 准确落实了已通过公开阅读的题面；48题中仅本题改变公开正文，其余47题逐行字节不变。本题评分内容也未改变，只有修订登记与关联摘要更新。**这不是共享入口激活、实际 Claude Code 交付或转第1类的证明。**

本轮只读本批候选、必要父版本和旧审查原件，使用本地 JSON/文本/SHA256 比较；没有运行安装器、项目代码、测试、SSH、容器或模型，也没有修改生产源码。唯一新增文件是本报告。维护测试采用实现者提供的原始日志，不能表述为本 reviewer 重新运行。

## 输入与父版本

以下路径均相对仓库根：

- 候选记录目录 `C = runs/category2_repair_20260929/r2e/orange22_rf_v1/`。
- 隔离树 `S = runs/category2_repair_20260929/frozen_r2e_statement_v1/`；其中材料根为 `S/docs/agentic_RL/repo_harness_rh2_workstreams/s2_r2e/`。
- 新读者报告：[orange22_public_reading.md](orange22_public_reading.md)。公开包仍为 `runs/category2_repair_20260929/r2e/orange3_22e98_public_v1/`。

核实 `C/source_record.json` 的三项绑定：

| 对象 | 本轮实算 SHA256 |
|---|---|
| 父修订单 material_v11 | `03acd34d7421bcf9c379612d0b8a5ce3d4292fdee0ee67327661eae5169d5c33` |
| 原批准修订草案 | `2605b9a7eeefb6c3bb9838536342c7e73cea79d260953378a49d00660aedc9e9` |
| fresh 公开读者报告 | `ce5e6c116638b6bc88a5c591f73e0847911424450831c30ed56dcb84a1e557c6` |

隔离父修订单与当前共享 v11 的字节完全相同；隔离归档 `ingest_history/material_v11_20260929/` 的旧 public、grading、environment 三份48行文件也均与当前共享原件逐字节相同。新 v12 的前63条修订单与父版本逐项完全相同，仅追加064；没有改写旧修订。

## 新条目与公开读者所见一致

`C/new_entries.json` 只有一条：本题的 `statement_text_replace`，目标为 `problem_statement`，`revised_file=null`、`expected_change=null`。三处 `edits` 与旧批准草案 `statement_edits` 完全一致；本轮在内存逐处应用，每处旧文本恰好命中一次。

原正文摘要为 `0d196bc2ef106b2f053da4acdc09718b142561e72c912d9d36f86f98d0296698`，应用后三处替换的实算摘要为 `f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`，与064前后摘要、旧草案全文、隔离新 public 正文、读者包 `public_task.json` 正文一致；同一正文也确实出现在读者的 `user_prompt.txt` 中。

变更仍只包括：删除直接实现答案、换成导入仓库函数的复现、改正 base 实际输出、用值而非打印容器格式表达原期望。不增加算法、隐藏输入或返回类型要求。新读者独立推导出首次出现顺序、逐位置映射及重复值共用索引，报告未发现核心歧义；其指出的旧公开测试盲点不等于本次新增缺陷，也不构成让题面泄露解法的理由。

## 48题产物逐题比较

对三份 JSONL 均确认前后48行、相同题目顺序；只有第23行本题不同。其它47行是字节级一致，不只是语义相等。

| 产物 | 本题实际变化 | 保持不变 |
|---|---|---|
| public_bundles | 仅 `problem_statement`、`problem_statement_sha256` | 所有其它公开字段，包括工具、提示、镜像、base及工作目录 |
| grading_bundles | 仅 `material_revisions: [] → ["r2e-mr-064"]` | expected原文与摘要、隐藏文件清单与各摘要、隐藏树摘要、run_tests原文与摘要、parser/规则版本等所有评分字段 |
| environment_packages | 仅 `public_bundle_digest`、`grading_bundle_digest` | 所有其它环境字段 |
| validation_bundles | 全48行、整文件字节未变 | 摘要 `763cd1b9e05025cfd0ab6bf1f03dd1536457d4e9283f1b61e56c9abbea447c11` |

因此，“评分内容未变”成立；不能写“grading bundle文件未变”，因为它记录了新增修订号，导致 bundle摘要及environment关联摘要变化。这些元数据变化符合来源可追溯要求，不是修改分数或测试语义。

新产物文件摘要均与新 ingest manifest 的4项记录一致，每项计数48；v13 pins的5项来源摘要全部与隔离原件一致。相比v12 pins，只有材料修订单来源从v11变成v12，另有 schema/purpose 的版本登记更新。

| 冻结对象 | SHA256 |
|---|---|
| `C/new_entries.json` | `750f5d151df1e004af95c448339afbd057e9423e87d38cd328355f31ab3bda7b` |
| material_revisions_v12.json | `2adf1118bd3c3f28d9d08c9182a909623625c0854dc685a2ab70e117318d46de` |
| t1_input_pins_r2e_v13.json | `c1c4346195462ce45ba537f042f1fba9f24957ebdb14fcb97032106511c5e5b4` |
| ingest_manifest_v0.json | `39674dc552f319f26d1473c7aa149ebb4e46aee668e349a2ccbc80d12d6dea15` |
| 新 public JSONL | `df3d2b1362e1056872350f6960a04e0217d291dcccbf2ae52a392497c57798b9` |
| 新 grading JSONL | `27006bf3dc5dac9b892025780c4e29207618fee0ee90f0411ecffc2e07aa11a6` |
| 新 environment JSONL | `31f11db11bb848c85221a22aa371d10d0b8ccf3a737a62ca47ad93d1fa975c60` |

## 安装器、测试与失败记录

隔离 `install_round.py` 与共享原脚本逐字相同。本轮比对隔离代码变化：`ingest_r2e_subset.py` 仅更新材料/pins/manifest常量与版本注释；`build_r2e_ingest.py` 仅更新pins说明；`test_ingest_r2e_subset.py` 仅追加授权项064及对应题数说明。三个派生镜像测试文件与共享原件逐字相同，没有删除断言或放宽断言。

原安装器确实先完成v12/pins_v13/48题摄入，随后测试失败并返回1；`C/install_result.json` 如实保留 `returncode=1`。`install_and_tests.log` 记录10 failed、63 passed；`tests_full.log` 的完整10项失败均落到缺失的 SWE pins、R2E配方脚本或其env pins，未见题面内容或评分语义断言失败。

实现者随后补入38个来源文件，记录在 `frozen_inputs_added_after_missing_files.json`；本轮逐个重算隔离副本摘要，全部吻合。补齐后的 `tests_after_material_completion.log` 明确记录 **73 passed in 5.97s**，其SHA256为 `decb1d7b5e46ce28f75919f8453bde06fe85d8964b595c8cf53c6d12b13bc4f8`。不能据此将最初 install_result 改写为成功：正确叙述是“材料生成已完成，首轮因快照缺失输入未过，补齐后维护测试通过”。

本轮查到的复跑文件只有pytest输出，尚未见单独保存的复跑命令、工作目录及退出状态元数据；建议实现者补存以便独立复现。这不改变73项通过的日志事实，也不妨碍本次基于产物和内容差异的隔离材料审查通过，但不能将该日志包装成 reviewer 自己执行的运行证据。

## 通过范围与下一步

没有发现需要修改064正文或评分材料的问题。可以在这份冻结隔离候选上继续核对当前consumer、实际公开消息、actor开发身份和准备预算；这几项是已授权后续工作，无需新增文本审批。

共享入口仍是父版本。本报告不授权混写全局v11，也不假定隔离修订已实际送达Claude Code。正式激活前需由唯一负责人复核共享父版本/编号占用，并把版本与consumer一致地接上；改变源码或材料后，本报告只对仍同摘要的部分有效。

不重跑未变的noop/gold/DG评分矩阵。仍需实际交付和当前运行条件证据后，才能重评普通探针分类；本次保留第2类，不授予训练或留出准入。
