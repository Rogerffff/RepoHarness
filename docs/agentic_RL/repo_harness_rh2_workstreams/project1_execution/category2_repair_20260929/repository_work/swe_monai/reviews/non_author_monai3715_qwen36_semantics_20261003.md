# MONAI3715：首 Qwen36 候选语义与验证质量非作者窄核

日期：2026-10-03。审查者：GPT-6.1 Sol / high，非材料作者。

## 结论

首模型这一次候选是合理根因修复：实际源码只把 Evaluator 两处条件由原输入 `mode` 改为转换结果 `self.mode`，保留字符串/枚举的 train/eval 上下文和非法输入拒绝。正式原 F2P、新增 F2P、原 P2P 三项真实通过，reward1有对应行为证据。没有发现需要修题、停止其它 GPU 作业或重跑本次首尝试的新具体阻断。

同时，本次模型验证有明确弱项：未先运行失败复现；修后大量检查停在构造；五次 Saliency/API 使用错误中三次被捕获为正常 shell 退出，且失败后仍打印“All tests passed”或“The bug is fixed”。这些具体错误可以归于本次模型的 API 查询/验证纪律，不能据此认定新增环境缺陷。正式评分通过不消除模型自测弱项；单次修复通过也不证明稳定能力、paired 完成或训练资格。

第二模型尚未完成，原请求保持原状态；本次不 ack/resubmit、不修改 request/check/题主报告，不改变全批完成口径。

## 范围与复用

这不是 fresh 公开读者盲审。审查者此前已读 3715 私有 oracle、controls、CPU矩阵及本包其它材料；本次又接触题主分析和检查单。新增窄核公开要求、实际 base/FP/diff、相关 API、305事件工具行为和正式三参考日志，复用已有 GPU 非作者运输审查，不重查全529成员、SSE全套运输或全 GPU现场。

复用 `runs/ordinary_gpu_probe_20261002/reviews/monai3715_qwen36_a1_execution_review.json`，SHA256 `c7849df53b8d58bb2fecc5baa5dfef023843553c09c16ef7257c0ea52b0705e3`。它的范围是执行运输/回执，无failed_checks，未替题主判断候选语义；本报告补本次语义与验证行为。其资源现场、长上下文压缩、训练捕获/消费、engine common.py sock_read900s与gateway1800s并非全链1800s等限制原样保留。

只读本地原件，标准库 SHA/JSON/tar 定点成员读取/字节比较，无SSH/Docker/CPU复跑、无任务代码执行或其它共享写入。本报告首次创建，同名文件原先不存在。

## 公开要求与实际候选

job `gpu1003-monai3715-qwen36-a1`；原请求 `swe-monai3715-string-modes-r5-20261003-v1` SHA256 `6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67`。实际 code_v4 source manifest `e3a33fd824021b75c9ed32fe7a82800f4158bfcf5d5a9d0ca8a8329380716469` 与 entry绑定复用既有运输核查；不因其source.adapter_code_scope文案提到既验code_v3运输而改写实际code_v4身份。

本次 solver_prompt 与 attempt public_delivery 为 unchanged，原prompt SHA256 `d10a8af37019d8bf5fdf98bb9225042511eab4d8abd444c07dbaa2e3f6863e79`。公开问题是 Evaluator 的字符串模式（尤其saliency所需train）被错误拒绝，要求字符串与枚举输入正确选中已有模式；它没有要求改写 CAM API或实现一个新的saliency功能。本次实际公开内容运输沿已有审查复用，区别于此前 CPU scripted actor 的通用首prompt。

从实际 `attempt/frozen/baseline.tar` 只读取有关成员，逐一匹配 baseline_manifest 登记内容SHA，不解压写入工作区。base commit `d36b835b226ab95ffae5780629a5304d8df5883e`；base evaluator SHA256 `97b99b4ef4a524ec976d5370de8ea5eb8cefc55830bd8fc79caa08693e5a60b4`。实际原diff721 bytes、FP只有 `monai/engines/evaluator.py` 一个regular modify；无测试/依赖/API文件变动。

独立解码FP完整源码，与base严格作两处指定替换逐字节相同，候选内容SHA256 `cf1e7a184698efac488e0e7a1ff27fd119a35402bb352361310a782efd300c6c`。因此确实没有其它隐藏源码改动。FP digest为 `01300a9ee5f40d4f71e4dca42070d6e419ec268cbda4384438b2f421d28ca397`；projection/applied-entry/重建身份复用运输核查。候选与gold全文不同不是拒绝理由。

根因：`look_up_option` 对合法字符串strip后返回 `ForwardMode` 枚举，对已有枚举返回本身，对无支持值抛ValueError；`ForwardMode` 是普通Enum，TRAIN/EVAL的值为train/eval。旧构造先得到正确枚举，却以原字符串与枚举比较，于是落入unsupported分支。候选用转换后的self.mode比较，随后仍绑定原 `train_mode` 或 `eval_mode` 函数。

实际base `SupervisedEvaluator._iteration` 用 `with self.mode(self.network)` 执行inferer。`train_mode` 开启grad、设network.train并在finally恢复原eval状态；`eval_mode` 用torch.no_grad、设network.eval并恢复原train状态。两上下文函数未修改。非法输入仍先被lookup拒绝，fallback unsupported分支也原样保留；模型第79/85事件另真实检查invalid产生ValueError。不能把私有三参考说成额外运行了一个非法值节点，该部分依据是原代码路径及模型构造自测。

## 正式行为证据

读取完整988行、66170bytes eval.log，其SHA与report/作者记录匹配。冻结材料 `monai3715-string-modes-forward-cpu-v1`，registry SHA `9fd5f38bbd3f0d09027d2270a6f3f3c1af1bae84da9c6b7c9b553bbafd7a9cb0`、grading identity `a88992c71eed8c4b9ac3482294a198ba253b1467e6963e1078cd98f9c48abd03` 与既有修订一致。

| 正式参考 | 实际结果 | 证明范围 |
| --- | --- | --- |
| test_content，原F2P | PASSED | 非空原eval字符串路径 |
| test_evaluator_string_modes_forward_and_restore_cpu，新增F2P | PASSED | 字符串/枚举train/eval真实forward、预测、梯度、恢复 |
| test_empty_data，原P2P | PASSED | 原空数据兼容性 |

新增节点遍历4种mode ×2种初始network.training ×2种初始grad设置，共16组合，单独RecordingNet真实forward记录training/grad；预测等于image×2，requires_grad按train/eval正确，train输入梯度为2，network/grad上下文都恢复。测试正文与已核固定材料一致，正式日志节点通过支持全部组合。这里是一个node的16组合，不能写成16独立试验。

实际pytest collected3、3 passed/17warnings，三个完整PASSED node齐全；diagnostics全部分区success、missing/skipped/unaccounted空。无ERROR/skip或异常替代目标断言。原P2P自身按设计警告空dataloader跳过run，但pytest节点为PASSED，不是pytest SKIPPED；不能把它当非空forward证明。TestNet collection warning是辅助network类非测试节点，不是正式参考缺失。

trusted setup应用RC0、protect成功；实际install/test段完整、未skip/partial、RC均0，源码import为/testbed/monai/__init__.py，runner pre/post digest不变。安装17.534s和测试9.12s为候选段时间，原日志有setuptools/pkg_resources/install弃用警告，未见pip ERROR或实际失败命令输出。17个测试warnings保留，不称原日志无警告。env_qualification=absent保留；普通探针评分通过不授予actor训练资格。

## 305事件：定位与模型验证行为

独立解析全部305事件，并核18份tool_use/result的事件号、ID、输入及result文本SHA，与作者索引逐项相同。实际4 Read、13 Bash、1 Edit；仅第245、259事件tool_result is_error=true。没有工具参数格式拒绝。每个assistant message最多一个tool_use，本次为串行；无证据评判并行能力或宣称执行器已支持并行。

事件11读取evaluator，21已准确定位“转换后值未被条件使用”，随后29/43读取lookup，61一次Edit、65成功，无再次Edit或patch返工。Edit之前没有Bash执行失败复现，不以作者/历史CPU复现冒充本次模型前后验证。

79/85检查字符串eval/train、枚举eval/train构造及invalid；127/131运行test_ensemble_evaluator.py，真实1 passed/16warnings footer可见。命令用了head -60，其pipeline RC通常不能单独证明pytest成功，但此次node和完整footer实际可见，支持这一具体测试通过。287/291最终仅检查SupervisedEvaluator构造和绑定函数，没有run/forward，不等于端到端梯度验证。

| 调用/结果事件 | 实际错误 | 归因与退出 |
| --- | --- | --- |
| 209/213 | SaliencyInferer()缺cam_name、target_layers | 固定API需要两必填参数；try/except捕获，shell正常退出 |
| 227/231 | cam_name=features | 固定API只支持CAM/GradCAM/GradCAMpp；捕获失败后仍打印All tests passed |
| 241/245 | 从monai.inferers导入GradCAMpp | 实际该包不导出它，base定义在monai.visualize.class_activation_maps；Bash RC1 |
| 255/259 | 从monai.utils导入get_torch_device_state_ctx | 实际utils不导出此符号；在进入待测逻辑前ImportError，Bash RC1 |
| 269/273 | CAM默认fc层未提供 | 模型只有features/classifier，CAM默认fc_layers=fc，真实异常Could not find fc；捕获后仍打印The bug is fixed |

已对照固定base SaliencyInferer签名/合法cam_name、CAM的fc_layers默认值及get_layer路径、两包导出；相应文件未被候选修改。因此五次错误都可由模型输入/API假设解释，解释器、导入原MONAI与正式非空行为测试实际可用，未见应新增为环境修复的具体证据。

事件231的成功宣称是模型所写测试程序无条件打印，紧邻FAILED原输出，并非真实测试结果；273亦同。工具is_error=false只反映异常被捕获后的正常shell结束，不能当测试通过。模型最终声明“complete and verified”只在构造检查与已有测试范围内成立，未完成正确Saliency端到端运行。正式测试的forward/gradient证据来自评分侧，不能归功为模型已经自测充分。建议把这种原轨迹归为本次验证纪律弱项；不因最终reward1删掉失败过程。

## 指标、用途与运输边界

19轮/19模型请求，累计input257849、output5556；单请求最大input18973、output669。terminal与已验运输usage一致。累计input是多轮请求之和，不是一次上下文占用，也不能据它超过context196608断言发生溢出。没有压缩事件，不覆盖长上下文/压缩稳定性。

CC duration57.377s，duration_api34.4s；entry solve61.005s。总评分539.19s中trusted setup约496.634s；报告test29.92s是评分测试阶段合计，与候选安装17.534/测试9.12s口径不同。这些准备/评分秒数不能算模型推理秒数。定位与一次修改较快，修改后的猜API和重复构造检查增加了调用量；没有paired/重复样本，不能推算稳定效率。

有效context196608、实际HTTP max_tokens65536/adapter max_new_tokens65536、240轮、求解10800s复用既验transport/budget。CC展示maxOutputTokens32000原值保留，不改成实际65536；本次实际终止end_turn/completed，无length截断。CC估算cost不当额外API账单。

运输审查的actor/relay/network/grader/gateway清理/drain证据复用，无需为本次语义窄核重扫全GPU。报告4096MB与resource_facts=null保留为报告值，不称独立实测峰值或全GPU空闲。source.adapter_code_scope写“code_v3运输”是所复用既验链说明；实际输入pin和job使用code_v4，以原字段分别保留。

## 原件SHA与可追溯范围

入口题主分析文件SHA256 `680ac2d9e58c4e8ed0130aef39b58ac14bb41ed0f44570fb572c57e8912ccea2`；作者check SHA256 `b494afe936c89114decbb810075364a216b0860601cede61bc35b10dbb2a5349`。其11份绑定原件的SHA/bytes本次独立全部匹配，未扩成全文件census。关键原件根为 `runs/ordinary_gpu_probe_20261002/remote/queue_v12/results/gpu1003-monai3715-qwen36-a1/`：

| 原件 | SHA256 |
| --- | --- |
| attempt/harness/trajectory.jsonl，230397bytes | `0b246013faf00aa9f2f8e67bb03653438a09292a7b18176d707f20863ab7a3bc` |
| attempt/frozen/frozen_patch.json | `5151f227f615d43bd865b7006a4a8a7b50dd80b9ae1403bd2db3b325356e2a48` |
| attempt/candidate/Project-MONAI__MONAI-3715.diff | `2e4477e768f6218ef4b5a6b94d04a9c235b2bb0955dd60a9d4a0600e01ac5a49` |
| grading/eval_logs/evallog_gpu1003-monai3715-qwen36_3177aec2.eval.log | `73654c46da4047d58b5e1dfba60736a0ff9102dd0563eeac283fd4122e9199ef` |
| result.json | `6867d53359f04ce047e4b1b92997dee63c866887dfee1765799c557a1ceec4d1` |

相关base定点成员SHA：lookup所在module.py `5cfd264ae1c50560a71ffa60d27b83de22f1c91637a5a91751bdb48ce514f4da`；contexts所在networks/utils.py `19f70852b0a5dad5e0437d7873d3084431935facd9e16f80e0a8699a0202a2e9`；inferer.py `49f49d6eaa92a86eee5a90883249e9bbfe52cbdbd338a9cc34a0f6eaaef18613`；CAM源码 `20f3bf47ec535fe704cbc4d09f6f415ca5481806f1c5e9a6eefcc4e256c3eb13`。这些用于核本次根因和误用归因，不宣称全仓库API验收。

窄核支持题主“首候选修法合理、正式三项通过、模型自测较弱、未发现新增题目环境阻断”的判断；不增加稳定能力、第二模型完成、训练/留出或全现场资源结论。
