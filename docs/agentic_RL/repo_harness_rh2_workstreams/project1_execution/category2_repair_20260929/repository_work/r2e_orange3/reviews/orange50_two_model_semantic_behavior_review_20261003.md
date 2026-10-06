# Orange50 两模型首轮：独立语义与行为窄核

2026-10-03，非作者 subagent。**新增作者分析受支持，无作者材料、题面、验收或共享 consumer 必修项。Coder 与 Qwen 的最终源码均满足当前公开需求；原正式评分各为 1，48/48 个参考键匹配，另各有 3 条既有未计分 SKIP。** Coder 自验不足、反复误读已说明的旧断言冲突，并在最终答复中夸大验证；这些事实与有效正式成功同时保留，不改写原分。

本轮只读已回收原件，新增 Coder 候选语义与七维行为核查，并核对[两模型作者分析](../tasks/50f6a758/probe_two_model_analysis_20261003.md)。Coder 的[原执行审查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/orange50_coder_a1_execution_review_v1.json)与 Qwen 已封执行、语义、行为审查按原范围复用，不重复 43 项执行检查、封闭文件运输审计、fresh 阅读或公共 101。没有 CPU/GPU/SSH、模型、候选运行或新增测试；只新增本报告及[结构化报告](orange50_two_model_semantic_behavior_review_20261003.json)。旧作者原件、旧报告、评分、请求和总账均未修改。

## 语义与评分的承接

从原 FrozenPatch 解码的 Coder 最终源码 SHA 为 `1f4c9bba4868886bddbf5b7c2025637d240012f981c6e8c671446305d47793a8`。两个段共用现有循环，每段收集查不到的真实变量名，在段结束将完整名单加入已有 `warnings`，由末尾原 `QMessageBox.warning` 聚合显示。空段不追加警告；有效变量仍进入原 descriptor 构造与解析；重复 rename 检查、有效定义替换、模型刷新和 commit 保留。没有 foo/bar 硬编码、只示例特判或隐藏键适配。完整列名符合公开要求，不强求缩写、标点或唯一实现。

这项判断由数据流与正式结果共同支持。固定目标 `TestOWColor.test_load_ignore_warning` 实际断言空定义不 warning、1–2 个名字完整点名、3–7 个名字的宽容长名单，以及 mixed categorical foo/numeric bar 都点名且有效 iris→species 输出 rename 保留；[原正式日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/grading/eval_logs/evallog_gpu1003-orange50-coder-a_f2a5d499.eval.log)该目标 PASS，完整 48 PASS/3 SKIP，testRC0，footer 完整。模型临时检查没有成功验证这些需求，正式评分不能回标为模型自测，也不证明全部 Orange 输入或整个回归集。

原 FP 四项是源码 modify 加 `test_issue_fix.py`、`verify_fix.py`、`test_fix_verification.py` 三项新增脚本；三脚本都保留并进入正式投影。原执行审查已核原生冻结/运输/投影、baseline、fresh grader、完整键集与清理。完整轨迹中未见修改既有测试、依赖或评分控制，未见 gold、隐藏测试、私有 runner、网络或未来答案读取；不以此排除先验记忆或声称一般无污染。未将需求误读推断为恶意绕过。

## 七维事实与作者结论

以下编号均为 Coder [原 trajectory](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v20/results/gpu1003-orange50-coder-a1/attempt/harness/trajectory.jsonl)一基事件行。JSON 包含 25 个工具的 call/result 行、工具 ID、结果及分组索引；Qwen 引用沿[旧独立行为审查](orange50_4014_qwen_first_behavior_review_20261003.json)复用。

1. **方法。** 75→79 首次 Edit 已正确收集两段缺失名；177→181 恢复原 baseline；203→207 的 `new_string` 与 75 逐字相同，最终恢复初始正确修法。三个工具分别为 `toolu_bcecf84b2b65e9d0`、`toolu_cc6cf7cfd6f90f10`、`toolu_0a427badbaedc4d7`。后一次没有形成“更精确”的新方案；未实际实现其文本设想的特例。Qwen 在 104→108 唯一 Edit 中逐名追加 warning，同样覆盖两段并保留有效处理。

2. **定位与纠错。** 23→27 全源码 Read（`toolu_7d7f400077812c28`）、36→40 全公开测试 Read 后，45 已概括诊断“缺失变量不 warning”；49→53 局部源码 Read 后，58 具体指出 `var is None` 分支只 continue。作者 JSON 的 `first_source_grounded_diagnosis=58` 按首次明确具体分支理解，不当作首次理解问题，不要求回写已封原件。88→94（`toolu_d8f00983254185ef`）只在旧方法末尾 888 `assert_not_called` 失败；前面 duplicate rename/name-swap 检查已执行。99 曾正确识别冲突、引用 Development Note，随后 125/138/173 等又讨论仅示例特判，177 实际撤回，190→194（`toolu_7826b23c1713a8e9`）的 1 PASS 属于恢复后的 baseline。212 最终接受旧断言与新需求冲突。不能说它全程正确解释了反馈，也不能把 194 归给最终候选。

3. **工具与实际反馈。** 25 次工具为 Bash14、Read5、Edit3、Write3，均有结果。四次 is_error 为 94 旧888 RC1，以及 142→146（`toolu_e6be5f38c0a8667d`）、164→168（`toolu_6469b214cd269d7e`）、291→295（`toolu_7925bb74639cdb34`）的 RC134；三次均报须先创建 QApplication 才能创建 QWidget。Qt 平台设置及 xvfb 不能代替 QApplication，173 承认原因却没有修复后再验证。142 还缺 patch 导入，但先前已中止，未实测到 NameError。216→220（`toolu_491cb0e6426818f7`）仅写 verify_fix，未运行。不是三次成功需求检查，也不是共同环境无效或新的 OOM 证据。

4. **并行。** Coder 的 26 个 generation 为 25 个单工具组及最终无工具组，最大工具 batch1；没有多工具成组提议。Qwen 首次 Read+find 确在同一 `msg_2c17cec8a10164cbb6b73cb8`：11/15 调用、19/20 结果，工具 `toolu_10bbd2eec1aeeb18` 与 `toolu_1e0be2c05ec3bfcb`。两臂缺完整工具执行起止与执行层能力确认，只能比较提议分组，不能证明实际重叠、并行收益或任一模型不会并行。

5. **验证。** Coder 最终三个不同 selector 成功是 251→255 parse、260→264 shows_warnings、269→273 invalid，工具 `toolu_5877150c9e8462e5`、`toolu_153bc2619b496311`、`toolu_de71c1556c177feb`。初始相同补丁还有 103→107、116→120 的前两项重复；没有运行全部五个 brief selector 或整个原公开文件。三次直接 widget 检查均未到需求断言，另一个仅写未跑；没有成功的模型自验 foo/bar、numeric、mixed 或实际 rename 检查。94 旧888是题面明确接受的冲突；194 是 baseline。Qwen 综合 194→198 的 8 PASS 只含 5 项新增需求和 3 项继承 fixture，另有 3 SKIP；176→180 仅 warning 文本，194 才含 rename assert。其全文 212→216 为 46 PASS/1 FAIL/3 SKIP，sole FAIL 是旧888；管道 RC 不能单独证明 pytest 退出码，实际正文与旧审查支持该范围。

6. **效率。** 公开模块、入口与 fixture 建议已经给出。Coder 广域 find、全文件读入后再次窄读、反复解释已说明冲突、回退再逐字重用、重复两个 selector，以及三次没有修正 QApplication 的尝试增加了工作；有用的既有回归反馈未转成成功需求自验。没有实测可节省秒数，也不把所有调用都判为无用。累计 tokens 是多轮合计而非 context 峰值；下表的环境、solve、评分与整个 job 分列。Qwen 也有重复回归/重新 Read，单样本不能证明方法最佳或普遍更高效。

7. **结束与稳定性。** 317 实际 success/end_turn/completed，harnessRC0；原冻结评分与清理按执行审查复用，无观察到预算截断或无效结束。300 文本先承认 Qt 初始化问题，313 最终答复却声称 “all existing tests continue to pass”，未披露三次中止或已知旧888，这超过实际自验；作者已如实指出。Qwen 262 最终明确披露旧冲突，266 正常结束。两臂正常完成、正式成功、完整样本语义支持的分母分别各 1/1，不评价稳定性、泛化或训练资格。

## 数字与可比范围

新增作者关键数字与独立提取全部一致；其 20 项顶层 evidence_refs 的 SHA/size 全部匹配。Coder 封闭 158 文件/83,640,790B 的整体完整性沿既有执行审查复用，不重复全套。

| 实际指标 | Coder | Qwen（已封范围复用） |
| --- | ---: | ---: |
| 原 reward / 参考匹配 | 1 / 48/48 | 1 / 48/48 |
| 累计输入 / 输出 tokens | 705598 / 7470 | 400073 / 5814 |
| 最高单次输入 / 输出 | 34928 / 964 | 33774 / 1139 |
| CC turns / generation / 全 HTTP | 26 / 26 / 28 | 16 / 15 / 17 |
| count_tokens HTTP | 2 | 2 |
| 工具 / 源码 Edit | 25 / 3 | 15 / 1 |
| solve / CC 总 / API 秒 | 89.575 / 86.268 / 64.962 | 65.689 / 62.223 / 37.825 |
| gateway generation seconds_total 求和 | 64.378 | 37.380 |
| actor trusted_init 秒 | 255.184 | 221.011 |
| actor attempt 总墙钟秒 | 382.849805 | 326.138970 |
| grader 总 / wrapper 测试秒 | 275.516 / 5.019 | 252.068 / 5.001 |
| TEST marker 区间秒 | 3.796964169 | 3.789 |
| 派发后整个 job 秒 | 660.083964 | 579.587722 |

Coder 首 Read 23→27 从其 generation 请求到结果 0.413842 秒，从首 generation 到结果 1.308567 秒；首次正确 Edit 75→79 分别 4.437543/9.764567 秒，恢复同修法 203→207 分别 4.192553/53.222567 秒。这些时间含生成、派发、工具与返回，不是纯定位、工具执行或 GPU 计算时间。模块入口已公开，不作盲定位能力结论。API/gateway 含服务与传输；约 11 分钟全 job 不等于 11 分钟解题。派发前队列未知，grader queue0 仅管理器；CC cost 只是估算。

两臂本题实际 GPU 镜像 `dc5a3d833584373f64a1f562bffba612d6d9285699d04bcd4732abc44e2c3330`、prepared/host 材料、expected map、评分 scripts、题面/brief、预算和 baseline 实值相同，candidate prerequisite 为 null；不能把 baseline 内容相同说成两个归档文件字节 SHA 相同。Qwen code4 与 Coder code7 的整棵 runtime 有 8 项共享成员变化，只有已核的四项关键 entry/solve/frozen 运输相同；保留旧比较范围，不称整树逐字同版。公开提示明确、采样与 thinking 暴露不同、各仅一次，耗时或 tokens 不构成模型普遍优劣或架构因果排名。

## 边界与当前接收

最高单次输入约34K，未验证满196608上下文；CC metadata32000 与实际 HTTP65536 分记，不据元数据认32K截断。原安装段 SKIPPED/RC=null，不能说新安装成功。有限约15秒资源观察、有 CPU throttle，不证明全程峰值、最低配置、完整无干扰或全程零 OOM；角色按实际容器，退出后缺容器不当内存0。权重身份沿原实际 capture/只读 mount/argv/HTTP 的操作关联，非逐POST物理 GPU 权重证明；Qwen checkpoint manifest 宣称40/列37及原 typed qualification/lineage null 限制保留。first-byte1800 与 sock_read900 不同，未触发不证明满预算承载。

当前两臂均 returned。新独立语义/行为审查完成，`necessary_fixes=[]`；父线程另封当前接收并处理 ack/活动指针，本报告不执行这些操作。作者原 `new_non_author_review_complete=false` 是生成时状态，历史文件不回写。没有为通过重跑或新增普通采样；本题首轮完成不关闭全包 GPU，不授予训练或留出资格。

## 文件绑定

| 被审作者文件 | SHA256 |
| --- | --- |
| 新两模型 MD | `0f992aefd2273ea2330404c812f8fa885652dca88fc2bb97de8773d84c2883ef` |
| 新两模型 JSON | `dd57afe65c0c8784d49798bea522d2b673335bc59e19ae4c1b03ef8d5a4215e9` |
| 复用 Qwen 作者 MD | `7add6cb374875f5daa7fa7f8082913bf67eeaac7a49af1c6f2707291b23fc05b` |
| 复用 Qwen 作者 JSON | `3e03200a96b83037b41854f5564f7fa6af50ae148df5e8c31287a28b674472a2` |

复用 Coder 执行 JSON SHA `5764861b3080ea0ef77f24b107f9214bc58ac3f8be39b9c9ef6745ce355edec3`；Qwen 执行/语义 JSON SHA `e76588ce04a4da831ce5c9a88eaa3e8426f143865e2c052c6a98e249da7b8d1d`；已封 Qwen 行为窄核 JSON SHA `ab7a413a3494a3a309fc3e65742fde58080a6b452ffafed42b45eec55c48554a`。

总回执 SHA `aa3f43e209e247a2cd883c0df4c040da21a56a885c7dc8eb76adf487482bb0f4`；原 trajectory SHA `4026c70f06f980ce3c38fd4499204a5b13418bdb8d0316f8dd1738bf829b2ae6`；原 FP SHA `6d0641c4dad1baf0ac5d7815e11ae34d63685a6b847cdeb406ade8c4f6803f58`；实际交付 prompt SHA `14db55eb6c630d01e5debb0df4ab47f983e79c493313d8b6f2775b7d23ae9371`。其他依据、SHA/size、七维逐事件索引与限制见本报告 JSON。

