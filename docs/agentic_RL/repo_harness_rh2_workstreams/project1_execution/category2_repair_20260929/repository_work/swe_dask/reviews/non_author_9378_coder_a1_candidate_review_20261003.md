# Dask9378 首次真实 Coder 候选：非作者语义窄核

2026-10-03。对象 `gpu1003-dask9378-coder-a1`，base `8b95f983c232c1bd628e9cba0695d3ef229d290b`。本报告是首次 write-once 审查，只依据已封闭的169份原件；没有执行 CPU/GPU、SSH、Docker 或候选，没有解压归档到文件系统，没有改共享源码或历史证据。

## 结论与适用范围

**默认 mask／ones、zeros 有效值的修复路线静态成立，并有模型公开自测支持；当前正式137个参考尚未评分。** 原始准备阶段300秒超时导致 `infra_failure`、`reward=null`，安装和测试未开始，`qualification=None`。不能由自测或代码判断预写 reward=1，也不能把 None 当0。

候选新声明的参数支持存在真实缺陷：`ones_like(..., dtype=np.float32)` 已在轨迹中失败；最终实现没有修复它。`chunks`、`name`、`shape` 被静默忽略，这是源码直接确认的缺陷，尚无新增运行反例。本次发现不以候选是否像 gold 为判据。

当前用户 B／有效测试的窄目标没有包含全部可选参数兼容性，未发现默认 mask／有效值要求中的确定反例。**本候选揭示更广 API 的覆盖边界，但当前还不是“错误候选正式获1”的材料漏判证据。** 若将目标升级为常规 `*_like` 全参数兼容，当前测试就不足；本报告不自行扩展材料或资格规则。单Coder单样本、另一模型尚未知、正式评分待同FP补评的限制必须保留。

## 输入身份与成功 Edit 重放

[169原件封闭清单](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-dask9378-coder-a1_closed_manifest_v1.json) SHA `aaa3c2d6886466004a5dcb769512a0aaef059ec920276bad44ba4a5d6aa97386`，169/169本地文件 SHA 与字节均匹配，总计30,382,873 bytes。清单只覆盖首Coder臂，另一模型的在途文件不在本报告范围内。

[FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/attempt/frozen/frozen_patch.json) 文件 SHA `b8835cb148c9aa5bca7d8a36ba3c4f2c0bd10a28f541776de2e428e3ebfe8067`；sorted compact canonical JSON 摘要为 `ed5ec645234368669128c41ad3a2b9104ecf20bf346535bd22e2f60dda49df4d`，与评分 status/projection 绑定一致。文件字节 SHA 与规范摘要不是同一种口径。[候选diff](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/attempt/candidate/dask__dask-9378.diff) SHA `6d9fbda2ad6a91257f3c2565747a20d102a32c784d3523a21b48165ae2bc03d1`。[完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/attempt/trajectory.jsonl) 共649行，SHA `f9ad67534cb1e893af90af81fcb2f70853503126418f558e8129e0ae33c7f0aa`，与 harness 副本字节一致。

只用 `TarFile.extractfile` 读取基线归档的 regular members `ma.py/core.py/utils.py/creation.py/test_masked.py`，不解包、不执行。基线 `ma.py` 为192行、SHA `676aeee5df3b1fb270baf3a2bf9db8d57845a61c47394bf59ae86861c1459346`。将全部9次成功 Edit 第123、171、197、232、271、284、354、472、610行依次在内存字符串重放，各 old_string 均唯一，成功结果分别第127、175、201、236、275、288、358、476、614行。最终重放字节与 FrozenPatch `dask/array/ma.py` 完全相等：9313 bytes，SHA `5e0149892fb9c7bc2e5cd4c92354c7f1fe29b3aae84a9599cf559b5ed077d73e`。

第354行曾形成6个同名函数定义，后面的旧定义遮蔽前面的新定义，解释了反复“手工 map_blocks 正确、ma函数错误”。第472行已把旧定义换成相同的简单 map_blocks 实现，仍有6个定义。第610行去掉重复，只余3个。清理前第472行状态与最终第610行状态的三个函数签名和可执行语句 AST 一致，因此此清理不修 dtype，也不改变默认调用逻辑。基线192行在最终文件中逐字保持，生产改动仅追加106行。

## 当前目标与实际验证

[题卡第5行](../tasks/dask__dask-9378/card.md)与[有效测试第10–28行](../tasks/dask__dask-9378/effective_test.patch)固定用户 B：存在 `da.ma.<like>` 时走该入口并验证正确；缺失时允许顶层正确路线。三项逐元素 mask，ones/zeros 再比较有效值，empty 的未初始化数据不作判据；不要求新增 API，也不指定 dtype/chunks/name/shape 的全参数验收。

最终 `ma.py` 第195–298行新增三个 `@derived_from(np.ma)` 函数，具体返回在第227、262、298行：`a.map_blocks(np.ma.<like>, dtype=(dtype or a.dtype), order=order)`。默认 dtype 取输入 dtype；逐块执行 NumPy masked like 函数，保留 mask，并按 ones/zeros 生成有效值。没有改顶层 `da.ones_like`，但用户 B 允许正确的新增 ma 路线，这本身不构成拒绝理由。

| 轨迹行 | 实际证据与局限 |
| --- | --- |
| 481/485 | 简化函数后原一维示例 ones/zeros 的 data 与 mask 对比匹配；empty 仅检查 MaskedArray类型并打印掩码表示。 |
| 494/500 | 原公开 `test_masked.py` 文件收集134项、134 passed，发生在第610行清理重复定义之前；不是私有新增3项测试通过。 |
| 509/518/522 | `test_masked_like_functions.py` 默认 ones/zeros `assert_eq` 及 empty类型/shape先执行；随后 `dtype=np.float32` 的 ones在 `chunk.dtype == x.dtype` 失败，退出1。其后 `order='F'` 分支未执行。 |
| 527/531/540/544 | 模型将问题称作“avoid issues with assert_eq”，另写简化脚本，移除 dtype/order 分支后通过；生产代码未修 dtype。原失败脚本仍在FrozenPatch中，未被覆盖。 |
| 553/562/566 | 原一维题面示例改走 ma入口，mask匹配；顶层旧函数仍不保留mask，符合本次允许ma修法的范围。 |
| 610/614 → 623/627 | 清理重复定义后再跑原一维示例，ones data/mask匹配；本命令没有验证zeros/empty。 |
| 636/640 | 最终只再跑既有 `test_creation_functions`，1 passed。基线该测试从第167行起检查 masked_greater等既有构造函数，并非新增 like三个入口的测试。 |
| 645/649 | 最终称 dtype/order/chunks/name/shape 全支持、134/134保证无回归；应按上述实际时点和范围收窄。 |

私有 `test_like_funcs` 使用(3,2)输入、多chunk与二维mask；模型自测主要为一维样例。本审查对最终默认逻辑的判断是静态支持，加上清理前同执行语句的已有公开自测；**不是最终版本私有3F/134P的实际通过记录**。正式测试结果仍为None。`empty_like`模型简化自测没有逐元素mask断言，不能用类型检查替代私有要求。

## F1：dtype 覆盖只改元信息，计算块类型不变（P2）

当前行为：最终三函数把请求dtype传给 `map_blocks` 的输出元信息，未传给 NumPy块函数。FrozenPatch `ma.py` 第227、262、298行和基线 `core.py::map_blocks` 第523–535行表明 dtype是专用形参；第806–814、867–879行只将剩余 kwargs传给块函数。`order`在kwargs内，dtype不在。因此请求float元信息却仍按输入整数类型生成块。

违反不变量：Dask数组声明dtype必须与实际计算块dtype一致；候选docstring第205–206、240–241、275–276行还明确承诺“Overrides the data type”。基线 `utils.py` 第225–239行的实际一致性断言在轨迹第522行触发。错误文案提到 scheduler并不改变失败断言是dtype不一致的事实，不能直接归咎 `assert_eq`。

证据强度：**ones 的 float32失败是实际观测；zeros/empty是同代码结构的静态推论。** 该失败观测于第610行之前，但最终函数可执行语句相同，缺陷静态确认仍保留；未新执行最终浮点探针。新增ma函数以前不存在，所以这是新增API缺陷，不是已证既有ma行为回归。

影响／处置：显式dtype调用得到自相矛盾的Dask数组，可影响后续类型依赖操作；不接受“完整参数兼容”或可生产采用的全面结论。当前批准的默认mask诊断范围不因它自动扩大，正式分仍待补评。若以后验收完整API，应修正真实块函数dtype传递或收窄支持面。

已有复现命令为轨迹第518行 `python test_masked_like_functions.py`；FrozenPatch该文件第31–34行保留反例。验收条件是在任何后续完整API修复中同时检查声明dtype、计算dtype、mask和值，原反例通过；本报告不要求现在另跑它。

## F2：chunks／name／shape 接受后静默忽略（P2，静态确认）

当前行为：三个函数在签名第196、231、266行接受 chunks/name/shape，docstring还描述各参数效果，但执行体只使用a、dtype、order；三个选项既不传入 map_blocks，也无rechunk／改shape等处理。违反不变量：公开声明的参数应执行其声明语义或明确拒绝，不应无声无效。

这是由完整最终源码直接确认的缺陷，不冒称已跑shape/chunks/name反例。可用的后续最小检查为对同一输入分别设置异于原shape/chunks的参数、两个不同name，检查结果元信息；这些检查本轮没有执行。现有顶层 `creation.py` 会使用 `_get_like_function_shapes_chunks` 并传 chunks/name，不能因候选复制签名就推断它也做到了。

影响／处置：调用者无法获得所声明的结果形状、分块或命名。属于更广API边界，不能把它改写成默认mask失败。后续完整API验收需让这些参数实际生效或明确排除支持；当前评分材料无这些探针，是已知覆盖边界，不是本轮已验证的正式漏判。

## F3：已知失败后缩窄自测，最终说明仍夸大全参数与验证范围（P2）

当前行为：第522行真实dtype失败后，第527行把它归为 `assert_eq`问题，改用不含dtype/order的简化脚本；第645/649行仍称所有参数支持、134/134保证无回归。违反不变量：结论应包含已知失败，并与最终版本、具体执行范围一致。

134 passed本身是真实结果，但它是在清理重复定义前取得；通过AST一致性可以静态判断默认函数逻辑未变，不能替代最终全文件运行记录。最终实际自测只有原示例与1个既有回归项，后者不测试新like函数。empty自测的类型/shape也不等于逐元素mask验收。该问题无需推断欺骗动机，不属于正式测试篡改。

影响／处置：题主若直接采用模型总结，会将未修复参数误报为正确、将旧时点公开自测误报为最终137参考通过。请在当前诊断收口中写清F1/F2与自测时点，并保留reward/qualification=None。已有反例/位置：trajectory第509、518、522、527、531、544、494/500、610、636/640、645/649；FrozenPatch失败helper第31–39行。收口条件是这些失败和验证边界直接可见，不能以更多简化测试通过核销它们。

## 评分污染面与正式状态

FrozenPatch共10项：`dask/array/ma.py` modify与9个根目录探索脚本add，均在 [projection](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/grading/projection.json)原样保留。正式测试、conftest、pytest配置、runner没有候选entry；没有按测试名特判或伪造评分输出。diagnostics明确列7个test-like paths，没有conftest/fixture touch。由源码和候选运输看，未发现评分绕过或正式测试污染行为；**准备超时意味着安装／测试及runner终局核对尚未完成，不作全链安全已验的结论。**

[原正式报告](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/grading/report.json) outcome=`failed_to_grade`、failure_category=`infra_failure`、detail=`grading_control_surface_protect_timeout_after_300s`、reward=null、test_seconds=0；[diagnostics](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/grading/eval_logs/evallog_gpu1003-dask9378-coder-a_99b2114f.diagnostics.json) candidate=null、grading_revision=`not_evaluated`，3F2P与134P2P的result均null。[eval log](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/queue_v23_remainder_v1/results/gpu1003-dask9378-coder-a1/grading/eval_logs/evallog_gpu1003-dask9378-coder-a_99b2114f.eval.log)第775–776行受信测试补丁已应用、第797–809行setup修订attestation通过，但没有install/test开始或结果，不能据此记137参考缺席失败或候选未修。

原正式setup300超时已经是具体执行阻断，后续同一FP的setup900由GPU执行者另行办理。本报告封存到此；新补评分不回写这份报告，另存后续审查并绑定同FP即可。

## 停止条件与剩余事项

候选字节、全部成功Edit、参数真实失败与静态缺陷、当前材料边界和正式infra事实已核清。**当前停止本次只读审查；qualification=None、raw_reward=None保持。** 不新增CPU/GPU、不修改题面或oracle、不因gold实现不同否定候选。未见当前默认mask目标的确定语义阻断，但正式评分必须另补；F1–F3阻止全面参数支持／最终全面验收的说法，不阻止按原授权取得同FP正式结果。另一模型结果未知，单样本不能推出成功率或稳定性，也不授训练或留出资格。
