# Orange9b：两模型首轮修法与行为分析

更新：2026-10-04（Asia/Singapore），原作业均于10月3日UTC执行。**两模型各一次均正常完成、原分1、13/13来源期望状态匹配。两份最终补丁都修复默认L1真实拟合错误，并保留默认L2、多分类概率及既有可用配置；未发现需修的材料或consumer缺陷。实际正式测试均11通过、2个既有expected FAILED、1跳过，testRC1；不能写全部测试通过。** 作者两模型七维分析完成，新增非作者窄核待封。原请求已returned，独立核查结束后再ACK并清活动指针。

本轮只读取已有原件，没有CPU/GPU/候选运行、模型重求解或新增采样。Coder首次已独立验收，完整轨迹和390成员核验按既有有效范围复用；旧单Coder报告、局部收据和原始成绩不回写。本报告补齐Qwen并比较两份真实样本，当前验收及总账操作另存收据。

## 1．修法与验收目标

Coder在`super().__init__`前改局部solver，随后由原`self.params=vars()`保存；Qwen保持原初始化，再改`self.params["solver"]`。两者条件均为`penalty=="l1" and solver=="lbfgs"`，改成`liblinear`，L1 penalty保留。原`SklLearner.params` setter会筛入sklearn参数；Qwen对筛后字典更新实际用于`_initialize_wrapped()`与`fit`，与Coder同一行为。Qwen最终仅修改源文件，内容SHA `9b1a23c683c2109647607c28aa26cd05e77a4df697593e632c28cd78b4b37952`；Coder还有`test_l1_fix.py`新增helper，两项均纳入其原生FP评分，没有事后替它删脚本。

默认L2/lbfgs/multi_class=auto、none和可用显式solver不进入新分支，没有改测试、依赖、评分入口或默认多分类方式。正式auto_solver通过包括iris多分类与heart二分类的真实L1模型、保持L1、可用solver，及默认L2/lbfgs、repr、none、默认概率关系。**默认概率比较是原L2 auto/lbfgs与显式multinomial，不要求新L1/liblinear等于multinomial。** 新L1用OvR符合目标，不等于旧G1全局改默认OvR的退化。未覆盖全部不兼容显式solver、多分类、dual组合，不能据此保证整个参数空间或全Orange兼容。

## 2．定位、假设与纠错

题面及brief已给类名、错误、真实fit原例和两个公开selector，两者都属于提示明确的定位。工具结果相对首generation请求的秒数含生成、派发、工具和往返，不能当纯工具秒。

| Qwen事件 | 可观察行为与含义 |
| --- | --- |
| 11→19、15→20 | 同assistant组读完整公开测试及广域find/grep；后者命中目标和多个无关路径。 |
| 30→34 | 1.810秒读43行目标源码，定位默认lbfgs。 |
| 48→56、52→57 | 同assistant组：真实Orange L1 fit复现ValueError；另读sklearn版本0.22.2.post1并真实lbfgs fit失败。两脚本捕异常，工具RC0不等于需求成功。liblinear“OK”仅来自构造，不能单独证明fit。 |
| 67→71、81→87、97→101、111→115、125→129 | 读默认值并多次查找/分段读SklLearner。params setter筛参数、_initialize_wrapped构造、clf.fit实际拟合。 |
| 文本135、153、143→147 | 135误把L1支持校验归到创建sklearn实例；153说liblinear是唯一支持L1的solver，与此前列出的saga矛盾。143重读未变源文件收到“Wasted call”。 |
| 157→161 | 25.501秒唯一Edit，仅L1且lbfgs时改params.solver；没有按错误“唯一支持”文字扩大修改。 |
| 175→179 | 实际iris L1拟合成功，输出模型为liblinear，纠正后的行为成立。 |

Coder在构造矩阵后曾错误推断lbfgs支持L1、怀疑版本/校验过严，最终读安装的_check_solver并采用正确条件；Qwen更早承认真实fit失败，仍有校验阶段/唯一支持solver的错误说法。两者实际修法正确与中间推理局限分开保留。没有将这些误判定性为恶意投机。

## 3．工具与代码边界

| 指标 | Coder | Qwen |
| --- | ---: | ---: |
| 工具总数 | 23 | 21 |
| Bash / Read / Edit / Write | 18 / 3 / 1 / 1 | 15 / 5 / 1 / 0 |
| tool_is_error结果数 | 1 | 2 |
| 最终FP entries | 源码与新增helper共2 | 源码1 |

Qwen两次tool error为215候选整个公开文件与243临时原版两个scorer；56/57捕获fit错误仍RC0。工具状态与功能成功分别记录。225→229看到候选diff，239→243执行`git stash`并对原版两个scorer重测，257→261成功pop，275→279读回候选，307→311最后两个公开selector再通过；FP与读回源码一致，无遗忘恢复。一次Edit不代表workspace没有短暂回退。

未观察到联网、hidden/gold、私有grader或未来Git答案读取；Qwenstash在清洗后的当前公开Git内，未当作未来答案通道。观察范围不能排除模型先验记忆。两者没有修改现有测试、依赖或评分控制面。Coder原helper保留并评分；Qwen未新增helper。

## 4．成组请求与实际并行

Coder最大assistant工具组1；Qwen最大2，两组分别11/15（Read+Bash）与48/52（两个Bash）。Qwen22个CC turns、20次generation、20全部HTTP；Coder24/24/24，无额外count_tokens。工具数与CC回合数、HTTP次数不是同一计数口径。

Qwen有同message成组调用，缺各工具开始/结束区间，结果时间相近不证明实际重叠，也不能计算并行收益。两份单次轨迹不足以评估稳定使用并行的能力；不把两次组调用写成“已证明并行加速”。

## 5．验证质量、原版对照及expected FAILED

Qwen193→197两个公开selector实际2PASS。211→215整个公开文件2FAIL/10PASS/1SKIP、RC1，fail70为major vessels colored≠chest pain、92为aquatic≠legs。239→243 stash后的**原版两selector**仍以相同行、相同不等值失败，提供直接原版对照；没有跑整个原版文件，不扩写它的范围。257 pop并读回正确补丁后，289→293实际拟合六种配置：默认L2、默认L1、none、显式L2/lbfgs、显式L1/liblinear、显式L1/lbfgs，均输出成功。第七项概率布尔打印True，但没有assert，表达式仍是公开`.all()`形式，不是逐值严格概率误差检查；七项打印成功不能叫七个pytest PASS。最后307→311公开两项2PASS。

Coder修后真实L1/L2 fit、两公开selector各PASS、整个文件2FAIL/10PASS/1SKIP成立；新增helper打印3/3，但非pytest、未严格概率断言或失败退出，最终精确fit成功。它仅猜测原版scorer失败；Qwen实际执行了原版对照。这项验证区别不能转换为模型总体优劣排名。

正式原评分与期望映射已逐键核对：两臂相同13键，11PASSED/2FAILED，另1SKIP不在来源键集；完整日志结束，testRC1、安装SKIPPED/null、无infra失败。formal比公开全文多新增test_auto_solver一项，因此11PASS而非10。两次正式结果及自测次数不相加作样本数。

| 来源固定expected FAILED | 两臂实际首失败 | 未执行的后续断言 |
| --- | --- | --- |
| test_learner_scorer | 70：major vessels colored≠chest pain | 71形状检查 |
| test_learner_scorer_multiclass | 92：aquatic≠legs | 93–100其余排名与形状 |

这些方法构造默认L2，候选条件不进入，score/Normalize/coef及默认参数不变；既有CPU对照复用且Qwen实际原版复查相同失败，当前没有新默认退化证据。来源允许FAILED不意味着这些特征排序在所有用途都正确。保留原FAIL与RC，不调评分、不重试。

Qwen最终321声称两个公开selectorPASS及原版同FAIL属实，披露了两FAIL；称其“flaky”无重复统计证据，不能沿用。Coder最终只声称两相关selectorPASS但省略全文FAIL，full backward compatibility超出自验覆盖。两者修复语义支持与验证/报告不充分同时成立。

## 6．效率、身份、材料和资源

| 指标 | Coder首次 | Qwen首次 |
| --- | ---: | ---: |
| raw / 来源状态匹配 / testRC | 1 / 13/13 / 1 | 1 / 13/13 / 1 |
| 累计输入 / 输出tokens | 209848 / 4589 | 203005 / 4543 |
| 最高单次input / output | 13609 / 682 | 15719 / 787 |
| solve秒 | 52.192 | 48.526 |
| CC总秒 / CC API秒 | 48.834 / 33.347 | 45.202 / 28.050 |
| gateway responses seconds_total合计 | 32.786 | 27.559 |
| actor trusted_init秒 / attempt墙钟秒 | 114.785 / 201.451818 | 105.515 / 187.608427 |
| grader总秒 / wrapper测试秒 | 124.793 / 3.482 | 125.113 / 3.540 |
| TEST marker区间秒 | 2.463198 | 2.490123 |
| 派发后整个job秒 | 327.728305 | 314.232041 |

Qwen广域find与碎片base查询、未变Read和重复公开selector可减少；它的原版scorer对照有明确因果作用，不视为浪费。Coder构造支持误判后的重复构造/版本调查增加往返，可更早读真实校验与fit；没测省秒。Qwen本次solve略短，但单次、不同服务状态和准备耗时不足以推出稳定速度或能力优势。累计input不是上下文峰值；CC/API/gateway含服务等待与传输，不是纯GPU；两臂准备/求解/评分/全job分列。Qwen实际started_at→finished_at为187.608427秒，与solve48.526分列；不能因字段不叫ended_at就记作缺失。派发前排队未知，grader queue0只限管理器；pytest正文1.93秒、TEST marker2.49、wrapper3.54口径不同，CC cost是元数据估算而非自托管账单。

作者核Qwen封闭快照manifest选中191成员、71,270,833B的全部size/SHA，目录193文件另含manifest与sync元数据。Coder复用sealed390成员/73,151,319B核验。两臂input_check的task/020092材料、prepared25b300…、host4632b7…、默认expected SHA cd0340…、baseline policy/manifest与完整grader重建census、exact solver prompt23b45f…、brief33d7e3…、grading预算与entry bdf806…逐值/逐SHA相同。Qwen确实用code8/source09ddb8…；本题实际actor/grader镜像084702…与最终CPU镜像相同，完整配方050316…未沿用旧020-only摘要。两份FP不同但base一致。不能把同入口名或机械回执布尔当所有事实；原件关联、实际HTTP与正式日志已核。

Qwen本job预启动capture为14:41:20.229311–.387601 UTC，绑定13:24/13:26启动且restart0的实际engine/adapterID、只读checkpoint mount，核37权重文件size及实际配置/HTTP；不是本次重复全部权重SHA、物理GPU或逐POST attestation。Coder当前09:30预启动capture与历史03:48操作绑定按已封scope复用，不把旧时间重标成本次。input_check旧config_only/readback=false、checkpoint_identity_verified=false及typed grading_materials_identity/revision/qualification null均保留；新机械补证按操作scope使用，不冒称训练typed租约或物理权重证明。

Qwen资源22份有限样本，actor/relay各13、grader8；Coder24份、14/14/8。有cgroup telemetry，profile声明2CPU/4GiB/512PIDs/swap0与实际采样分列，没有本job HostConfig/cpu.max/memory.max/PidsLimit直接连续读回，空containers不代表资源使用0，全程峰值/无OOM/无干扰不能外推。正式grader peak1185.148MB为已有指标，resource_facts空保留。实际import路径为Orange/__init__.py，没有logistic模块已加载字节SHA读回；原FP重放、baseline及实际结果支持当前归因，保留观测边界。

## 7．结束、分母与接续

Qwen325轨迹事件，completed/end_turn、harnessRC0；20 HTTP均200/无stream_error、网关撤销/active0/drained、静止屏障成立、原FP完整投影评分、baseline重建、actor/grader清理无遗留。终端proof是当前完整RC0及确切PID1成功日志，未把systemd not-found默认0当退出证明。Coder结束与清理按已封证据复用。无观察到预算截断、缺模型/轨迹/评分或infra失败。

两臂实际HTTP单响应预算65536，context196608、240CC回合、solve10800、1024请求。CC modelUsage.maxOutputTokens32000与实际HTTP65536分记，不指认为32K截断；底层sock_read900与declared first-byte1800不是同一边界，没触发不能证明满预算承载。

**每模型正常完成1/1、原评分成功1/1、公开修复语义支持1/1，共2份首轮完整样本。** 首轮覆盖齐，不作稳定能力、模型排名、训练或留出资格结论。独立窄核完成后仅核收原请求并清active，不创建新请求/重试/手修模型候选。GPU最新v2覆盖优先计划已取代v1，并明确暂缓Orange22的a2/a3，ordinary_repeat_dispatch_allowed=false；旧v1计划接收保留历史。四题两模型首轮在本题核收后全部完成，当前没有已知CPU/GPU待执行步骤；未来复采仅依全批后续选择，暂缓项不冒称在途或当前必做。整机退租仍由资源负责线程按用户授权处理。

## 原件与适用范围

- [execution_partial_receipt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/orange9b_qwen36_execution_receipt_v1/execution_receipt.json)，SHA `e3ee8b2230766aaa0f0fd41ebee0de46ce5b458c92667d8d93107ebe2f9b7f8f`。
- [closed_manifest](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/qwen_next12_closed_v1/gpu1003-orange9b-qwen36-a1/closed_manifest.json)，SHA `b9920c8415c096a7220ffbf11082248c8ee042676d616da156f45c523bbc9107`。
- [closed_sync_verified](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/sync_receipt_v4.json)，SHA `58bb3e6ecd2e6201d9605caf37eb953f24e622fea572c2ca70285517d78a61d1`。
- [result](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/result.json)，SHA `41527d4f8d93691b6806165b4843dbe2e0e50384d881d3d31d8230b4d54cd21d`。
- [input_check](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/input_check.json)，SHA `8860437dda00f2dfd0071fbdf1f20378b95177629782786dcd58036ff9260a08`。
- [attempt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/attempt.json)，SHA `068192d976e37f09598384f0a9a30fb27ca32ff545f7340e0cb6352c4fc905f1`。
- [trajectory](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/trajectory.jsonl)，SHA `0fc90a622b796cbb03c058549b45a038c993da9a910e69236918b43a211a0318`。
- [frozen_patch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/frozen/frozen_patch.json)，SHA `62a3b8bd2d60d3c9439830a93c32821153592f6f4978efc21cd7ece487aaef78`。
- [baseline_manifest](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/frozen/baseline_manifest.json)，SHA `221636a94d2dbca490bc4a31c3b63de8bdf79404cb17deba5b12f52fcfa660ef`。
- [baseline_tar](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/attempt/frozen/baseline.tar)，SHA `d0e849d185566aad727bdc398ed22b0e73a9a02a80280f409c875db7c5d3f389`。
- [grading_report](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/report.json)，SHA `6feaa1caf5d3a90918749e2a3e1b13c4d4ff3ee5c23cf683834cf5e9cd34de40`。
- [grading_status](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/status.json)，SHA `fb4095e4a260ce8b6a2cc460330a7ba88ac9828c1a377acebb6a8dec55db4371`。
- [gateway](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/next12-v1/gpu1003-orange9b-qwen36-a1/requests.jsonl)，SHA `74244e78c27d4702f51eaae514ae83e39d7b361f38b29ff2295272446d6137c2`。
- [terminal_snapshot](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/qwen_next12_closed_v1/gpu1003-orange9b-qwen36-a1/terminal_snapshot.json)，SHA `89d6030761346bcb8e40cb06f9f5519fec45d04c10fb329abad9bc34a30a2e4f`。
- [prompt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/solver_prompt.txt)，SHA `23b45f4dd7ca7ecb0ba967409612a767fcd4c6b298fee57d43346838f9f71963`。
- [host_grading](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/prepared_moto_orange_code8_v1/orange9b/private/host_grading_views.jsonl)，SHA `4632b750bd377d38ce903b5b8abcf5ebd96f16a0bc7855be40f7a608087ea45b`。
- [rollout_view](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/prepared_moto_orange_code8_v1/orange9b/prepared/rollout_task_views.jsonl)，SHA `531d85b647b040699c50308166121974a4e7ba54339fc286bdc41c40676e30ec`。
- [public_brief](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/prepared_moto_orange_code8_v1/orange9b/public/development_brief.md)，SHA `33d7e34f091c820c6b1456133fd53578e9b0bc7bad87b38814f358c19d5e3c06`。
- [source_manifest](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/code_v8/source_manifest.json)，SHA `09ddb8bfdeecd3ffaa38c1048a574161ef6fa6053b2855da50166e8e8677899d`。
- [projection](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/projection.json)，SHA `e16675f1f8676ecaced678c2ba49d51a7454059a459937fd6b731d72ce1d3212`。
- [formal_eval](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/eval_logs/evallog_gpu1003-orange9b-qwen36-_593ba0d3.eval.log)，SHA `79575f16d0f7cabf54a929b8f85376a55957428e9f29e323d85ae276da219e7b`。
- [formal_diagnostics](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/eval_logs/evallog_gpu1003-orange9b-qwen36-_593ba0d3.diagnostics.json)，SHA `f67dc57b4af4f43a61602215e267aebbe14f4f4e60189ce573563ca0a20a34a8`。
- [engine_binding](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/services_qwen_code8_v1/qwen36/engine_launch_v1.json)，SHA `603bec65f047c9b87967c58be43b8933ef3b662f9eab7052ac8ee64c3ae9e9f7`。
- [current_prejob_capture](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/diagnostics/QUEUE_QWEN_NEXT12_V1_gpu1003-orange9b-qwen36-a1_before/capture_receipt.json)，SHA `04f0ceae8b270d927bb6c53e920ddfec2517ddadefdc615c9d51527dfaa16f61`。
- [gateway_responses](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/next12-v1/gpu1003-orange9b-qwen36-a1/responses.jsonl)，SHA `db49649cf607ef73c16df65e23c11b737ba77511607cfab0e92dc08e76498e73`。
- [resource_samples](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/qwen_next12_closed_v1/gpu1003-orange9b-qwen36-a1/resources.jsonl)，SHA `bc23e60eb09469d14b3bfd91391c5d5377c45790bd94ac88c498612617f1809f`。
- [baseline_rebuild_census](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/queue_qwen_next12_v1/results/gpu1003-orange9b-qwen36-a1/grading/baseline_rebuild_census.txt)，SHA `a0c62815205de29c1772436cfb398c34b632e6542701fa02b52b1476d2a756a3`。
- [cpu_acceptance](cpu_acceptance.json)，SHA `91bc5f96f046b41292487630a13a70663a6ef1ecace6d3e20a392ab610370fc2`。
- [current_fixed_hidden_source](files/r2e_tests/test_1.py)，SHA `b2bd45b7c11b63c19fa147e0fcc485aa5b80b540a460f36163a4d7331f6f87df`。
- [owner_request](probe_request.json)，SHA `f407bcc020122d70df1d2b801d3c976dabdd10c25b87f021a85781883f9a5fc9`。
- [pair_execution_receipt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/r2e-orange9b-r020092-cpu-sysconfig-v1-20261003_pair_execution_receipt_v1.json)，SHA `48144f980659de9beabeecd76798578031eb414cfdbd8b3ed7e44fbd5fbe7fef`。
- [Coder_sealed_analysis](probe_coder_first_analysis_20261003.md)，SHA `3655d5a280e987191194ce129c48b36029aefd5030ab7538331251063904a465`。
- [Coder_sealed_analysis_json](probe_coder_first_analysis_20261003.json)，SHA `901728cf958855fc5d77a9ed28fba68a1703f6555b8eb7ff624862c89422a85e`。
- [Coder_sealed_review](../../reviews/orange9b_coder_first_semantic_behavior_review_20261003.json)，SHA `3c9948f5206676d83f85f3fb2cf839812c2f45fe3aa6013cbe17a03c06198146`。
- [Coder_partial_owner_acceptance](probe_coder_first_owner_acceptance_20261003.json)，SHA `11c15aa6a184c5d7a6be1196c0cd2fefdbc054fdf169a4c843449b6c17939280`。
- [author_Qwen_evidence](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange9b_qwen_first_author_evidence_v1.json)，SHA `05fb89628ca2a419142df242641931eb136b5df10e6e79758432083b29eaf8b9`。
- [author_Qwen_binding](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange9b_qwen_first_binding_v1.json)，SHA `34a52954e15a449f70d4a6ed6eff4567674f95933e8776f2eeb590583f767631`。
- [Qwen_current_terminal_proof](../../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-orange9b-qwen36-a1/diagnostics/QUEUE_QWEN_NEXT12_V1_gpu1003-orange9b-qwen36-a1_before/current_terminal_evidence_v3/success.json)，SHA `c25bf4a6558df5fe57c071dbce15f2f3c9fe155ab3cc2da538b54c41e933d2f2`。
- [CPU_retirement_dependency](../../cpu_retirement_dependency_20261003.json)，SHA `2c138cd183badab77ba311a02176d5de506c513df78b1578b73ee665dd89bd09`。

Qwen完整模型文本、21工具输入/输出及源码前后/差异见作者索引。机械执行回执只证明其明确链路scope，题级语义和两模型分析由本报告与新增独立窄核负责。现有参考源码和固定hidden只读用于离线核结果，未再次执行。旧生成时状态由当前收据续接，不覆盖历史材料。

- [current_coverage_first_plan_v2](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/stage2_repeat_plan_v2_coverage_first.json)，SHA `576d5ffddee4554bad2a5f45f15a86bb79bbb77f045b8f37c8f139a4fa89c4ba`；本次接续核对有效政策，旧v1不回写。
