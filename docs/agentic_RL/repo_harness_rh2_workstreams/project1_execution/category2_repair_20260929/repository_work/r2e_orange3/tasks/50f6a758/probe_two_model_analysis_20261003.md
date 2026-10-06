# Orange50：两模型首轮语义与行为分析

2026-10-03。**Qwen与Coder首轮均正常完成、正式1（48/48），最终源码均满足当前未用变量警告要求。Coder的自验明显不足：三次直接widget检查缺QApplication而中止，曾因误读已说明的旧888冲突撤回正确修复，最终又夸大“所有旧测试通过”。这些过程问题不改写原正式成功。作者完成七维分析，待新增非作者窄核。** 本次只读原件，没有新CPU/GPU、候选运行或补样。Qwen的[已封作者分析](probe_qwen_first_analysis_20261003.md)与[独立接收](probe_qwen_first_owner_acceptance_20261003.json)按范围复用；其中Coder未执行为当时事实，保留原SHA。

## 1．修法与问题解决方法

Coder最终只改`Orange/widgets/data/owcolor.py`的`_parse_var_defs`：每个categorical/numeric段建立`unused_vars`，缺少实际变量时收集名称并继续；段结束将名单追加到已有`warnings`。末尾原`QMessageBox.warning`聚合呈现，匹配定义仍走原descriptor构造、rename、颜色、model更新与commit。Qwen则在同一个缺失分支逐个追加warning。两者都覆盖实际缺失名称与两个段，均无foo/bar硬编码或仅示例特判；空定义不误报，有效定义继续处理。

完整列名符合公开要求，当前验收不强求截断、顺序、标点、标题或唯一修法。作者核baseline与原FrozenPatch数据流，正式`test_load_ignore_warning`也实际核空定义、1–7个名字的宽容断言及混合categorical foo/numeric bar、有用iris→species rename，均PASS。语义判断由源码机制和实际评分相互支持，非只凭reward倒推，也不证明所有输入或整个Orange回归。

初始75→79的正确修改，177→181完全撤回；203→207的`new_string`与75逐字相同。所谓“更精确重新应用”没有改变方案；最终是恢复最初正确修法，共3次Edit。原FP四个regular项全部保留并评分：一项源码modify和三项新增仓库内脚本`test_issue_fix.py`、`verify_fix.py`、`test_fix_verification.py`。未改既有测试、依赖、评分控制或隐藏参考；`git diff --stat`只展示tracked源码，不能证明三脚本不存在。

## 2．定位、假设与反馈

公开题面已给函数和旧测试冲突，公开brief给五项selector与临时widget fixture建议；这是有明确提示的小修复，不外推盲定位能力。下列编号是原trajectory事件行；时间从首generation请求到结果，含生成/派发/工具/往返，不能称纯定位或纯工具秒数。

| 事件 | 实际行为与反馈 |
| --- | --- |
| 10→14；23→27；36→40 | find命中源码也带入.venv无关项（0.881秒），全owcolor源码Read（1.309秒）与全公开测试Read（2.177秒）。 |
| 49→53、58；62→66 | 局部源码与旧方法读取，58给出正确源码诊断；旧方法读完5.311秒。 |
| 75→79；88→94 | 初始正确Edit9.765秒；旧完整方法仅末尾888无warning断言FAIL，前面duplicate rename/name-swap检查已经执行。 |
| 文本99、125、138、173 | 复述Development Note却猜测仅示例应报警，试图把numeric缺失名当特例。实际没有实现特判，但误读促成撤回。 |
| 177→181；190→194 | 回退45.026秒，旧完整方法原baseline1PASS49.019秒；此PASS不能归给最终修复。 |
| 203→207；文本212 | 53.223秒逐字重新应用初始修法；212最终接受旧无警告断言与新需求冲突。 |

Qwen原轨迹则baseline临时foo/bar需求FAIL→唯一Edit→同例PASS，保留旧888冲突并在最后披露。Coder读到相同提示仍反复怀疑，缺陷在反馈解释与自验执行，不是最终源代码未满足需求。

## 3．工具使用

Coder实际25工具：Read5、Bash14、Edit3、Write3；26CC turns/26generation、全HTTP28（2count_tokens）。4个tool_error分别是94的预期旧888冲突，146/168/295的Qt程序RC134。三次都报“Must construct a QApplication before a QWidget”；xvfb与QT平台设置不代替QApplication实例。它没有采用公开widget fixture来修正初始化，也没有成功执行目标foo/bar临时断言。

142的脚本还缺`patch`导入，但运行先因QApplication中止，未观察到NameError，不虚构后续运行错误。216→220写的`verify_fix.py`从未运行，155与282所写脚本实际尝试均Qt中止。写入成功不算测试通过，脚本末尾PASS/FAIL打印也未到达。临时脚本留在仓库FP而未清理，增加补丁杂项。

本次工具可观察范围内没有网络、gold、隐藏测试、私有runner或未来Git答案读取；不据此排除模型先验记忆或声称一般无污染。没有把误读直接认定恶意投机。Qwen临时检查在`/tmp`且已删除，FP只有源码一项。

## 4．并行提议与实际重叠

Coder26次generation中25次各一个工具、末次无工具，最大assistant工具batch为1。无成组提议证据；也不能由此判断模型没有并行能力。Qwen首次Read与find同一assistant message成组提出、max batch2，已经独立核。两臂工具call timestamp均缺，只有结果时间，不能证明运行区间重叠或量化并行收益。

## 5．验证质量

Coder最终候选仅三个不同公开selector成功：251→255 basic、260→264 shows_warnings、269→273 invalid，各1PASS。103→107和116→120是在初始相同源码上的重复basic/警告检查；没有执行全部五个brief selector或整个原公开文件。94已经看到末尾888冲突，194的全方法PASS是在回退baseline上；恢复后没有新的全方法PASS。三次直接自写需求检查均Qt中止，另一个脚本仅写未跑，因此没有成功的自验foo/bar、未用numeric、mixed、有效rename断言。

正式grader直接消费原FP，完整参考48/48 PASS、testRC0、完整footer；另三条既有未计分SKIP保留，原安装段明确SKIPPED/RC=null。正式目标测试确实覆盖mixed与rename等，是评分结果，不回标为模型自测。Qwen自验综合8PASS拆为5项新增需求+3fixture、3skip；原全文46PASS/1FAIL/3skip仅旧888，最终如实披露。正式分母与自测/fixture/skip分列。

Coder300内部先承认Qt问题，313最后却称“all existing tests continue to pass”，未披露Qt或旧888；这超过实际自验。最终源代码正确与报告/自验不足同时记录。不因过程不足把有效正式1降成0，也不为成功补跑掩盖原轨迹。未发现必须修订题面、验收或共享consumer的问题。

## 6．效率与可比性

| 指标 | Coder | Qwen |
| --- | ---: | ---: |
| 正式原评分 / 参考匹配 | 1 / 48/48 | 1 / 48/48 |
| 累计输入 / 输出tokens | 705598 / 7470 | 400073 / 5814 |
| 最高单次输入 / 输出 | 34928 / 964 | 33774 / 1139 |
| CC turns / generation / 全HTTP | 26 / 26 / 28 | 16 / 15 / 17 |
| 工具数 / 源码Edit | 25 / 3 | 15 / 1 |
| solve / CC总时长 / API秒 | 89.575 / 86.268 / 64.962 | 65.689 / 62.223 / 37.825 |
| actor trusted_init秒 | 255.184 | 221.011 |
| grader总秒 / wrapper测试秒 | 275.516 / 5.019 | 252.068 / 5.001 |
| TEST marker区间秒 | 3.796964 | 3.789 |
| 派发后整个job秒 | 660.083964 | 579.587722 |

Coder全文件读入、旧冲突误读→回退→相同重应用、未修Qt的三次重复尝试和三个残留脚本带来额外工作，未产生成功的新需求自验。可以直接使用公开widget fixture、区分已说明的旧断言冲突、一次运行必要覆盖并清临时文件；这只是原轨迹过程建议，没有新运行或虚构可节省秒数。Qwen也有同组回归重复与无变化重新Read，不能只因正式成功称过程最佳。

累计输入包含历史重复，非context峰值；Qwen输出暴露thinking、Coder未暴露该块，不能断定Coder不思考。API秒含服务等待/传输，非纯GPU。trusted_init/grader与solve分列，约11分钟全job不等于11分钟解题；派发前候槽未知、grader queue0仅限管理器。wrapper/TEST marker/pytest正文是不同口径。Coder回执finished_at06:31:36是actor结束，正式grade06:36:11，不冒称整个job已在actor时结束。CC cost是估算，非自托管账单。

Qwen用code4、Coder用code7，整棵runtime有8项变化；四项关键entry/solve/frozen运输SHA相同。本题实际镜像、prepared/host材料、expected map、评分脚本、题面/brief、预算与baseline实值相同，candidate prerequisite为null。作者核aggregate26项直接/关键引用，不能说所有代码逐字同版。可诊断比较本次方法，模型采样/思考暴露不同、各仅一次，不能以耗时或tokens作普遍模型优劣/架构因果排名。

## 7．结束、分母和下一步

两模型均completed/end_turn/harnessRC0，有原FP评分、完整轨迹与双层清理；无观察到预算截断、length、压缩、缺模型/评分或无效结束。宽松预算196608 context、65536单响应、240回合、10800秒求解、1024请求；实际single input约34K，未验证满196K负载。CC metadata32000与实际HTTP65536分记，未据元数据指认32K截断。

**正常完成率Qwen1/1、Coder1/1；正式成功各1/1；完整样本语义受支持各1/1。** 保留全部样本和自验不足，仍不能形成稳定能力结论。原请求已returned，待新增非作者窄核封存后ack并清活动指针，当前收据另写，历史局部收据与原评分不回写。当前GPU无本题普通追加采样，不自行新发或为成功重跑；未来仅依已有全批安排接续。22计划复采与9首轮仍未收齐，本包仍需GPU，不因本题首轮齐备或CPU归档完成关闭GPU。

## 原件和用途

- [aggregate_receipt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/receipts/r2e-orange50-r090091-cpu-sysconfig-v1-20261003_two_model_v1.json)，SHA `aa3f43e209e247a2cd883c0df4c040da21a56a885c7dc8eb76adf487482bb0f4`。
- [independent_execution_review](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange50_coder_a1_execution_review_v1.json)，SHA `5764861b3080ea0ef77f24b107f9214bc58ac3f8be39b9c9ef6745ce355edec3`。
- [trajectory](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/attempt/trajectory.jsonl)，SHA `4026c70f06f980ce3c38fd4499204a5b13418bdb8d0316f8dd1738bf829b2ae6`。
- [frozen_patch](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/attempt/frozen/frozen_patch.json)，SHA `6d0641c4dad1baf0ac5d7815e11ae34d63685a6b847cdeb406ade8c4f6803f58`。
- [baseline_tar](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/attempt/frozen/baseline.tar)，SHA `b383c5db28f8d9d5e30316e7b921a5c9fb0f8af244ddae22b979081efb19dbc3`。
- [grading_report](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/grading/report.json)，SHA `4e56d8905afe20d8369329618fb3235a3e4b6c54e2383abb108a3411b0aa2485`。
- [closed_manifest](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-orange50-coder-a1_closed_manifest_v1.json)，SHA `c375fa9d1d06354aebbdd0600de75a9d5c30237a26eb1467cde1a1d43bb83cee`。
- [prompt](../../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/solver_prompt.txt)，SHA `14db55eb6c630d01e5debb0df4ab47f983e79c493313d8b6f2775b7d23ae9371`。
- [author_coder_evidence](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/orange50_coder_first_author_evidence_v1.json)，SHA `efa502cb0a208a95fd9def15dda5ffca880b279d9e317eef8705d102e6b60a64`。

作者核Coder封闭158文件83,640,790B SHA/size，完整读取原baseline与FP四项、317事件的所有模型文本/工具输入输出；完整索引保留原件绑定。Qwen按已封范围复用，未重跑候选。GPU actor/grader实际同`sha256:dc5a3d833584373f64a1f562bffba612d6d9285699d04bcd4732abc44e2c3330`，与CPU镜像不同。baseline、FrozenPatch canonical digest与文件SHA是不同层次，不混用。

权重身份限作业前实际capture、固定revision/checkpoint manifest/只读mount的操作关联，无物理GPU权重哈希或逐POST attestation；Qwen manifest宣称40、列37文件等原限制保留。Coder46份约15秒宿主观察、有CPU throttle，角色必须匹配实际container，退出后的缺容器样本不当内存0，不证明完整峰值、最低配置或全程无干扰。原typed qualification缺失及材料/环境lineage null继续保持；first-byte1800与底层sock_read900边界不同，未触发不证明满预算承载。用途仅题目/环境与基座方法诊断，不授予训练或留出资格。
