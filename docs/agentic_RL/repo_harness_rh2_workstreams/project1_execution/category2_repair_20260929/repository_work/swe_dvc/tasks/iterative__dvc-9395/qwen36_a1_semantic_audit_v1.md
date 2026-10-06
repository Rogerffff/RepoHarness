# DVC9395：Qwen 首臂题主语义审计

2026-10-04。作业 `gpu1003-dvc9395-qwen36-a1`，材料 `dvc9395-behavior-v2-draft@R20`，首轮宽预算。只读封存原件；没有运行候选、重评分、追加模型样本或云操作。

**执行完整，正式 raw reward=0；候选是部分修复，不能接受为本题正确解。** 它把恢复放到缺失检查之前，能恢复普通数据源和一个 frozen 场景；但未处理仓库导入和远端 run-cache，并在没有缺失、源码已修改时强制请求远端。实际 F2P 为 1/3、P2P 为 36/37。两模型摘要中的“P37/37”曾写错；原评分和双模型回执一直是 P2P fail=1/37，探针线程已保留旧摘要并更正看板。

## 原件与范围

[完整工具／响应读回](qwen36_a1_owner_evidence_readback_v1.json) SHA256 `52b0a14e91451c197fd5b73cd0d05581627d35ce36aee0610b0ba9d3785ddad1`：429 个封存成员、45,840,124 字节全 SHA／大小匹配；615 条基线 tar 条目核对象类型、执行位和内容；1264 行轨迹中的 88 个工具输入／结果及所有模型陈述均读回。88 请求／响应／adapter turns 与 SSE 工具身份匹配。纯文本回放另核 29 次 Read、8 次成功 Edit 和最终 FP 内容完全一致：`runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_qwen_source_read_consistency_v1.json` SHA256 `3443cb1d1fabd7661d81ac6601375f7273572b311d7bbd214c8f0b2cd8c5be80`。

baseline canonical SHA256 `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`；FP canonical SHA256 `bca0a3a7a04f2259a21b1f0aa7904b12ceff777f234dc2bde16f28345f45d476`。完整 FP 共三条：stage 实现、repro 命令帮助及追加公开测试。评分 projection 仅应用前两条源码，测试改动仍保留在原 FP；hygiene clean／test_files_modified=false 描述该投影，不能解读成模型没有改测试。

原正式 eval SHA256 `e69b70cd673b8df8c6c30f812798ef1eed01bcfd9a08178c7e3384ed7ca272fd`：6309–6349 行为全部 41 个实际节点，37 passed／4 failed；40 条正式引用是 3F＋37P，无 missing／skipped；额外 `test_repro_pulls_mising_import` 失败而不计分。parser 42 条还含捕获日志中的 `dvc.commands.freeze:freeze.py:19=ERROR`，不是实际测试节点。

## 1. 根因、修法与错误边界

模型正确定位到数据源／frozen 的 `Stage.run()` 分支只有 `_check_missing_outputs()`；最终在该检查之前、`not dry` 内调用 `_pull_and_checkout_outs()`。这避免了 Coder 先检查缺失导致恢复不可达的问题，也正确保留非 pull 和 dry 的入口条件。

helper 对整个 stage 的 `get_used_objs()` 结果调用 `repo.cloud.pull(objs)`，随后仅对有 hash 且不存在的 out 做 checkout。**判断“需要拉取”的位置太晚**：尚未检查任何输出缺失就调用 cloud.pull。已修改但存在的数据源仍触发 run，正式 P2P `test_pull_without_remote_preserves_modified_source` 在 eval 1999–2006 行沿新增 helper 进入远端配置读取，2056 行抛 NoRemoteError，2066–2069 行显示目标应使用现有 modified 源码。其他无远端“无变化”场景通过，是因为 reproduce 提前 skip，不能据此证明此边界正确；该失败是多余的远端依赖，日志没有证明源码内容已被覆盖。

原 F2P `test_repro_pulls_mising_data_source` 的普通 source 恢复及“已修改但有远端”的前半段均已走过；失败发生在后半段仓库导入数据恢复，eval 939–946 行明确为 imported.dvc。基线 `Output.get_used_objs()` 1077–1079 行对 `stage.is_repo_import` 返回空映射，候选没有走 repo.fetch 的 imports 恢复逻辑，却在 helper 直接 checkout 缺失缓存，874–875 行触发 CheckoutError。额外原 import 测试同样失败，不能把一个复合 F2P 失败概括成所有普通 source 恢复失败。

原 F2P `test_restore_pull` 的正式版本会 push(run_cache=True) 并删除本地 run-cache（eval 2404、2415–2418 行）；候选未修改 StageCache.restore 的远端 run-cache 获取。该节点在 run→save→save_outs 以 bar 不存在失败（2373–2386 行）；原有公开测试仅删除输出缓存、保留本地 run-cache，因此公开通过不能覆盖正式场景。新增 frozen 下游恢复 F2P 通过；dry、no-run-cache、HTTP＋本地 run-cache 等其余九个新增 P2P 通过。依据这些明确失败及源码，不需要改材料或判为环境无效。

## 2. 定位与纠偏

工具 19 读到已有 StageCache.restore 的 cloud.pull；工具 29／31 读到缺失检查分支及“缺失即抛错”，工具 37 读到 changed 路径，工具 43 已读到 cloud.pull 总会先解析远端。工具 50（首请求起约 51.031–52.897 秒）先加本地 checkout helper，52（53.696–55.585 秒）把调用放在检查之前，54（57.088–59.866 秒）加入 cloud.pull，却凭空导入 `big_file_size/big_file_traceback` 并从错误模块导入 OutputDoesNotExistError。

工具 55／56 公开测试仍通过；真实恢复工具 57 明确 exit65280且输出未创建，58 唯一标记 is_error，exit255／ImportError。59–61查源码后，62（88.459–91.310 秒）删不存在导入、改为 dvc.output，并合并 helper；63 起真实普通 source 恢复成功。后续没有再改业务实现，未追查仓库导入、远端 run-cache 或 modified／无远端边界。这是有效局部纠偏，尚未形成完整修复。

## 3. 工具使用

88 次工具为 Bash51、Read29、Edit8；只有工具58标记错误，但工具5路径不存在、20正则错误、57实际恢复失败、71／73／74追加测试失败都需读正文才能识别。源码读取已与当时工作区文本逐行匹配。与旧 Coder 的弱 mock 不同，本轮用临时 Git＋DVC 仓库、local remote、push、删除工作区／缓存和真实 repro 检查恢复。

临时命令没有显式重复公开说明的 PYTHONPATH 设置；公开模型源码导入检查显示 /testbed/dvc，真实恢复又随候选导入修复从失败变成功，支持它在运行候选。轨迹没有逐次临时命令的 import-path 独立检查，不能把公开说明要求写成每次显式执行完成。

## 4. 实际并行机会

第一个 gateway 请求同时产生工具1／2；其余工具请求单工具，最后请求仅总结。因此 88 requests、88 tools 与 CC num_turns89分别保留，不能从总数推断每轮恰好一个工具或实际物理并行。记录给出生成／工具结果进入下一请求的边界，缺乏每个工具真实开始／结束时刻。

源码／帮助检索可合并；恢复→检查依赖候选变更，复用同一个 /tmp/test_pull 的多次实验必须顺序或隔离。工具82的80项测试48.63秒、工具67的两模块13.65秒和工具88的82项10.35秒是明显等待段；这些是日志 pytest 时间，不是精确并行加速收益或将 solve 减 API 后得到的工具总时间。

## 5. 自测、测试改动与最终陈述

工具55／56为原公开10＋17通过，67重复两模块27通过，不累计重复节点。追加两项真恢复测试后，71为1失败／1通过：裸 target=data 被当作 dvc.yaml stage；72改为 data.dvc，73仍1失败／1通过：使用对象 identity 判断不同加载对象。74核到 `Stage is Stage` 断言问题，75改比较 addressing，保留文件存在及精确内容断言，76两项通过。这是修正测试目标与不合理身份断言，没有删掉恢复断言或改原 test_restore_pull 内容。

77最终run_cache模块12项、78multistage17项、82repro80项、83command2项、88stage82项均有完整结束摘要，五组公开节点总193项（含追加2项）；没有把更早重复27项再计入。管到head/tail的输出本轮均保留这些 pytest 完成摘要，但 Bash管道返回本身仍不是 pytest RC证明。86的最后过滤器含空正则分支，抹掉全部 repro输出；保留了此前缺失、此后两个文件存在和 output内容为source data的观察，不能依据过滤结果声称该命令单独核到了退出码。63／64／66另有明确恢复日志；87确认不带pull时失败且源文件未恢复。

最终如实列出三个改动及新增恢复测试，没有宣称正式参考全通过；但“pull all missing files”总体完成结论过宽。它未观察到任何正式私有测试结果，不能要求其隐瞒已见失败；应记录为公开自测完整、边界覆盖不足、最终完成判断超过候选正确性。193项公开通过并不抵消正式40引用的两个目标失败和一个保持行为失败。

## 6. 效率、服务身份与资源

solve260.000秒；CC256.437、API116.264秒；gateway response加总114.399秒，首请求至最后响应256.371秒。输入累计3,068,590／输出16,725 token，单次最大60,117／1,110；累计输入不是上下文峰值。CC估算cost15.761075美元不作实付。相比 Coder215.507秒是两次单次观察，不能判定稳定速度排名；Coder另有后台测试停止、弱自测及原GPU评分缺失，直接总时长排名更不充分。

88请求实际max_tokens65536，HTTP200／attempt1／SSE完成、无stream_error；预算context196608、CC240、solve10800秒、requests1024、first byte1800秒、idle14400秒，未见耗尽、截断或compact／恢复。metadata maxOutputTokens32000保持原值，与实际请求分开；本次最大输出1110不能证明65536上限实际可达。

`runs/category2_repair_20260929/repository_work/swe_dvc/dvc9395_pair_operational_owner_readback_v1.json` SHA256 `1d973ecc693b065e29697630cfcc65795c5a1f1faf16f28faf41af5adf6f16c7` 核34个执行pins、两模型同prompt字节／image／HEAD／baseline／profile（仅模型端口不同）、16:51:21–22 UTC实时只读mount／容器／HTTP配置以及Qwenrevision `995ad96eacd98c81ed38be0c5b274b04031597b0`。下载清单头部40、实际列出37（26权重分片）、37个实际大小全部相同，总71,926,788,362字节；未重新逐片权重SHA／GPU内存证明，config-only字段及checkpoint_identity_verified=false不回填。

评分268.066秒，与solve分开；env reset17.656、prep0.297、runner test21.321，候选install3.933／test16.848、pytest15.87，trusted setup228.024776秒小于本题setup900，也小于旧300。不能以此次结束声称900必需或旧故障原因已证明。profile2CPU／4GiB／PID512；39个有限monitor样本中actor20／grader18／relay20，采样kernel memory.peak最大990,486,528／1,004,756,992／28,016,640字节，pids.peak26／12／7，采样OOM/PID事件0。报告960.875MiB与有限grader采样约958.211MiB范围不同；resource_facts及baseline环境lineage仍null，不能声称全程峰值、全程无OOM或最低配置。

## 7. 结束原因、复核与当前用途

CC success／end_turn、harness0／completed，输入身份和原FP封存正确；candidate UID54322前置及安装0、测试1、segment completed。solver停止屏障residual0／双读稳定，gateway revoke后active_requests0，solver清理true；grader created1／removed1、open/supply/cleanup_failures空，cleanup true，无新增regrade。精确unit的PID1 journal成功事件支持本轮退出；退休unit的默认ExecMainStatus0不作证明。

新[非作者执行核查](../../reviews/non_author_dvc9395_pair_execution_review_20261004_v1.md)已返回；新非作者候选／七维语义复核另存。Coder原GPU null／entry1／cleanupfalse保持；[同原FP CPU补评分验收](coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)单列raw0、F0/3、P37/37，复用固定身份，不新增模型样本、不覆盖原GPU故障。

本轮将作为有效失败诊断用于训练信号分析：Qwen局部恢复正确，但恢复范围、远端run-cache及非缺失边界不完整；Coder在顺序和远程拉取上更早错修。材料保持R20，普通重复采样暂缓，稳定性／训练资格／最终用途未判定。核收两模型请求须待非作者语义复核闭合；ACK只是题主已读回结果，不表示候选修复通过。
