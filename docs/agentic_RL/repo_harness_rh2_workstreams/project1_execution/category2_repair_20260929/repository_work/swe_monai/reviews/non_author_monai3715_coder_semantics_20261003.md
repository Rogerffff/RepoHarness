# MONAI3715 Coder 首次候选：非作者语义与验证质量窄核

日期：2026-10-03。审查者：GPT-6.1 Sol / high，非材料或候选作者。适用 job：`gpu1003-monai3715-coder-a1`，模型 `Qwen3-Coder-30B-A3B-Instruct`。

## 结论

**本次候选正确修复公开字符串mode问题，保留原枚举、train/eval上下文、真实forward／梯度与状态恢复；正式3参考实际通过。没有发现需要修题、修环境或停止后续GPU的新具体阻断。** 候选不是按gold文字匹配判正确：局部 `mode_enum` 是合理的另一种实现，实际FrozenPatch只有该单文件改动。

**模型自身没有执行验证。** 完整62事件只有3 Read＋1 Edit，没有修改前复现、修改后测试、Bash或Saliency运行。正式grader的通过是外部验收证据，不能写成模型自行验证充分；也不能把未自测归因为环境不可测。Coder最终只解释修法，没有虚构具体测试通过日志。作者分析的主要正确性／验证质量结论与本次独立原件核对一致。

本次不是fresh盲审。本人已接触3715私有修订、controls、CPU结果和Qwen首次候选；复用[既有Qwen语义窄核](non_author_monai3715_qwen36_semantics_20261003.md)的固定公开要求／base／oracle语义，旧报告SHA仍 `5a3ab2715891caf020d4e695bbceebbb4553b9d1f54bb7b5b4b3fc685d53eb4b`。本轮新增读取Coder实际diff、FP／baseline、完整harness轨迹、正式diagnostics／eval.log、真实HTTP请求／响应及题主新分析；不重核CPU或GPU运输全套、不SSH／Docker／模型调用或项目测试，不修改旧报告／请求／检查单／原件，只新增本报告，同名文件此前不存在。按现行 `coordination_workflow_20261003.md` 题主安排非作者subagent窄核规则接续，不承接总账ack／resubmit或训练准入。

## 实际版本与复用范围

证据根：`runs/ordinary_gpu_probe_20261002/remote/queue_v21/results/gpu1003-monai3715-coder-a1/`。

| 绑定 | 值 |
| --- | --- |
| 固定请求／SHA256 | `swe-monai3715-string-modes-r5-20261003-v1`／`6a348f0a92f54a054eacf3e51d22cb14f769fb8d7d13f11d279a1889c0b14d67` |
| Coder runtime／source manifest SHA256 | `code_v7`／`be705a777484c70af2afe9a34b6dd288bd85c2b1f536c6d57bd59aecb4eb0352` |
| 固定base／materialized HEAD | `d36b835b226ab95ffae5780629a5304d8df5883e` |
| 实际actor／grader image ID | `sha256:6cbdf6b5eefbe27e97db5839aa8586584cc57f20759fb6c408690fddc8202e38` |
| 原vendor RepoDigest／grader诊断identity | `sha256:503ca39274e12c0aa0d06d0e77ad4f41628516a7b175feb4a5c10f940e2d1ab8` |
| material revision | `monai3715-string-modes-forward-cpu-v1` |
| registry SHA256 | `9fd5f38bbd3f0d09027d2270a6f3f3c1af1bae84da9c6b7c9b553bbafd7a9cb0` |
| grading materials identity | `sha256:a88992c71eed8c4b9ac3482294a198ba253b1467e6963e1078cd98f9c48abd03` |
| scripts digest | `sha256:1db4935fb130e3d87fb17e05c555772354eaf2dc6358992b4fdb67d73785f6e2` |
| baseline canonical digest | `sha256:8b9dce40cf01c128757fe7c97323fb8357b75b74e4ed7e6c6b44195307520b1c` |
| Coder FrozenPatch canonical digest | `sha256:04cb190e572c360ce07a7778d505a4aa99e7e15d707afe23832999d970f362e4` |
| 候选evaluator.py内容SHA256 | `c79a94bda2811d26a3431ef3584fd2f01eb4b71917b49f1291d0e2641732d34b` |

复用GPU非作者 `runs/ordinary_gpu_probe_20261002/reviews/monai3715_coder_a1_execution_review_v1.json`，SHA `7570d703cca68cfc43dc8687eea59739705e300b8e0c80b2e691a134c15b7ebd`。其scope是本地执行／运输原件、原FP／完整912项基线和同请求Qwen复用，**未终审候选语义或通读完整轨迹**；这两项由本轮补足。其122成员闭包、真实Coder服务／checkpoint绑定、完整SSE、实际容器身份、清理与42项有限资源采样范围沿用，不机械重复全部census，不冒称本轮重新远端验机。closed manifest SHA `2af2495936d97e481aa3ef98488daf9c46ca3eb169c0adb9bc2fb6b197aac618`，闭包只对应此job，不证明Q21全队列idle。

Qwen原臂为code_v4，source manifest `e3a33fd824021b75c9ed32fe7a82800f4158bfcf5d5a9d0ca8a8329380716469`；Coder为code_v7。GPU核4个关键运输文件同字节：entry.py、r2e_solve_attempt.py、solve_attempt.py、frozen_transport.py；同题请求／材料／实际镜像／完整baseline／公开prompt／3参考／评分脚本摘要／预算保持。**完整runtime不同**：prepared_task_face.py、replay_grade.py、bundles_v2.py、environment_overlay.py、spec_vendor.py、swe_material_revisions.py、manager.py、material_revision.py八个共享成员不同，原摘要与各SHA均保留在运输审查。不能称整棵代码同版、两个FP相同或严格无版本差异的配对实验；本轮不将旧Qwen重新绑定code_v7。

## 公开要求、根因与候选字节

公开问题是 `Evaluator` 的 `mode` 不接受字符串：Saliency使用场景需要training mode，传入 `"train"` 却报unsupported。公开API类型为 `Union[ForwardMode,str]`，默认ForwardMode.EVAL，文档明确train／eval映射。题面没有要求改CAM算法、强制always-train、放弃非法输入拒绝或重写上下文。

固定base的 `ForwardMode` 是普通Enum，TRAIN／EVAL的value分别为train／eval。`look_up_option` 对匹配字符串strip后返回对应enum，对有效enum返回原值，对不支持值或不合适类型仍ValueError；旧构造器把结果存进self.mode，却在后两分支比较原始mode，因此字符串归一化成功后仍进入unsupported。

实际diff仅把 `self.mode = look_up_option(...)` 改为局部 `mode_enum = ...`，两处分支比较mode_enum，仍把self.mode赋给原eval_mode／train_mode，原else ValueError正文保持。这样归一化值用于选择，self.mode继续是原上下文函数；没有改变enum、lookup或网络上下文实现。非法值拒绝由不变helper和fallback静态支持，**本次模型／正式三节点没有新增非法值实跑，不声称本臂实际测过该边界**。

本人只从baseline.tar读取相关成员，核其SHA对baseline entries：evaluator.py `97b99b4ef4a524ec976d5370de8ea5eb8cefc55830bd8fc79caa08693e5a60b4`、module.py `5cfd264ae1c50560a71ffa60d27b83de22f1c91637a5a91751bdb48ce514f4da`、enums.py `660358a36d3ccb4b6eb32795bdbb07392284b6cc30a46c3e2280512977858c9c`、networks/utils.py `19f70852b0a5dad5e0437d7873d3084431935facd9e16f80e0a8699a0202a2e9`。三次Read结果按行号去除显示编号后与这三份实际base全文一致，末尾额外空显示行保留，未误判源码不一致。

实际Edit的old_string在原evaluator完整字节中唯一出现；内存内一次精确替换后，整个文件与FP解码content逐字节相等，内容SHA一致。diff只包含该相同单hunk；FP只有一个regular modify `monai/engines/evaluator.py`，不含test／fixture／conftest，excluded_pathset_changed=false，classification／正式patch_hygiene保留clean。独立重算baseline和FP canonical摘要与实际projection、result绑定一致；不是旧FP换材料身份。

未变的SupervisedEvaluator／EnsembleEvaluator迭代仍在 `with self.mode(network)` 内执行真实inferer。eval_mode以torch.no_grad和network.eval执行并finally恢复原training；train_mode以torch.set_grad_enabled(True)和network.train执行并finally恢复原eval状态，grad上下文退出亦恢复。候选只修选择入口，不把self.mode留成Enum／字符串、不关闭train梯度、不移除finally，也不修改真实forward。

## 正式三参考与验证范围

完整 `grading/eval_logs/evallog_gpu1003-monai3715-coder-_e686ad62.eval.log` 66,269字节，SHA `5a5aa9e0daa9f7a14688d005a88ce39e09eedad99569b8b34901ea6161d9f4b4`；直接读完整正文而非只看report reward。真实collected3、footer `3 passed,17 warnings`，三条带node ID摘要为：

| 分区 | 参考 | 实际状态 |
| --- | --- | --- |
| 原F2P | TestPrepareBatchDefault::test_content | PASSED |
| 原P2P | TestPrepareBatchDefault::test_empty_data | PASSED |
| 新F2P | TestPrepareBatchDefault::test_evaluator_string_modes_forward_and_restore_cpu | PASSED |

三节点均在 `tests/test_prepare_batch_default.py`，与diagnostics分区逐项相同；missing／skipped／unaccounted为空，num_parsed_outside_segment=0，apply_ok=true。empty_data的“skip the run”是原空工作流行为提示，节点真实PASSED，不是pytest skip；TestNet构造器collection warning是helper类，不是正式参考缺席。

沿既有固定oracle语义，新增节点真实执行4模式（两个字符串＋两个enum）×初始training2×初始grad2，共16组合。RecordingNet在forward记录training／grad-enabled，非空image的prediction=image×2；检查requires_grad、train下autograd输入梯度全2、网络training及外层grad状态恢复。它不是仅构造器或mode名称断言。原F2P还执行字符串eval完整run，原P2P保留默认enum／空数据行为。正式实际PASS与不变上下文共同支持修复正确和已有行为保留，但不证明完整Saliency/CAM算法端到端或所有边界已覆盖。

root恢复一原测试、固定修订clean apply与control protection实际成功，正式安装／测试以已核runner角色执行。完整安装段保留原vendor sed、types-pkg-resources／pytest、requirements-dev和setup.py develop，真实installRC0、testRC0、无实际pip ERROR或RH2_INSTALL_CMD_FAILED输出；trap声明不算失败marker。install17.420s／test9.351s，candidate_segment_completed=true、log_partial=false、install_skipped=false，pre/post runner digest一致，import指向/testbed/monai/__init__.py、prefix owner54322。候选exec0和段RC0分别核对，不用包装退出掩盖错误。

实际安装保留pkg_resources、easy_install、setup.py install弃用警告，正式测试17warnings含SciPy旧namespace等；无“没有警告”结论。本次普通探针env_qualification=absent原样保留，评分通过不授予环境／训练typed actor资格。

## 模型轨迹与自身验证质量

两份 `attempt/harness/trajectory.jsonl`、`attempt/trajectory.jsonl` 同SHA `2dad6c1ea12f4d2ee88af9c368233a4aa3a385ac8088c0c0ae489176be0f2216`、155,861字节，62合法JSON事件：stream42／assistant9／system6／user4／result1。完整逐事件读取；tool_use ID与tool_result唯一配对，四个结果皆无is_error，harness stderr零字节。

| 调用事件→结果事件 | 操作 | 实际范围 |
| --- | --- | --- |
| 10→14 | Read evaluator.py | 读取真正构造器及迭代实现 |
| 23→27 | Read enums.py | 确认ForwardMode为普通Enum |
| 36→40 | Read module.py | 确认look_up_option归一化规则 |
| 49→53 | Edit evaluator.py | 一次唯一替换成功，结果等于实际FP |

事件45首次明确指出“比较原参数而非转换结果”。该解释有一句误称原mode被overwrite，实际赋值目标是self.mode；后面同事件和最终事件58／62都正确区分两者，最终解法用局部mode_enum且不含该错误。保留这处措辞边界，不据一句话抹掉正确诊断，也不隐藏它。

事件53成功Edit后直接进入最终说明，没有Read回看、复现、pytest、梯度／状态检查或真实Saliency验证。最终“fixed／maintains backward compatibility”是模型静态判断，补丁语义和外部正式评分支持其结果，但它没有产生自测证据，也没有声称具体tests passed。与Qwen先前捕获API失败后输出“All tests passed”的问题不同，Coder本次是**验证缺席**，不能混作相同虚假测试声明。

四次调用均串行，每个assistant消息至多一个tool_use。独立读取在理论上有合并空间，但没有实际并行尝试，执行器并行支持未由本轨迹证明；不推断模型不会并行。没有格式拒绝、工具权限拒绝、任意环境异常或length／compact截断，亦没有证据说明未测试是环境迫使。

## 输入交付、指标与观察边界

本人另读实际gateway `remote/services_v19/coder/gateway/gpu1003-monai3715-coder-a1/requests.jsonl`、responses.jsonl和usage.json（均在owner索引16件内），从 `solver_prompt.txt` **read_bytes().decode()** 后与首个真实HTTP用户text块精确相等，12处CRLF保留，原prompt SHA `d10a8af37019d8bf5fdf98bb9225042511eab4d8abd444c07dbaa2e3f6863e79`。不用read_text换行归一化证明原字节交付。actual first prompt与public_delivery=unchanged吻合；这是GPU实际正式题面交付，区别于此前generic CPU devcheck首prompt。

真实5请求／5响应，model_sent为Qwen3-Coder-30B-A3B-Instruct，每次HTTP200、stream_error=null，前四tool_use／末次end_turn，requests与响应seq绑定一致；完整SSE边界复用运输核查。实际max_tokens五次均65536。响应usage独立合计input62,060／output957，最大单请求input18,638／output454，与CC结果和owner指标一致。**62,060是多轮累计输入，不是上下文占用**；CC显示maxOutputTokens32000原值保留，实际HTTP输出限额为65536。196608 context／240轮／10800s求解预算由运输审查实际配置支持，本次没有跑到限额，也未触发长上下文压缩。

CC duration8.290s／API8.178s，entry solve11.687s；评分554.02s，其中trusted setup513.712495s、候选install17.420s、test9.351s（评分test phase30.007s另含装配）。不要把554秒当模型推理；无自测也降低了工具时间／tokens，本次快速静态修复不证明普遍效率或吞吐优势。CC cost是估算值，不当独立API账单。

GPU运输审查的42项有限采样与角色时间窗沿用：actor4项仅3项有内存值，null保未知；grader36项运行期采样，install／test窗口各只有1项。实际生命周期高水位4GiB和memory.events.max计数2810不等于测试最低内存、连续峰值或全程无OOM；root chown单点没有独立不可变原件，不能把513秒全部归因于它。diag resource_facts=null保留。只复用此job双层清理／gateway drain／entry0，不推断整队列或GPU宿主idle，也不新增退租判断。

## 作者结论、原件SHA与当前用途

回读题主 `probe_analysis_3715_coder_a1_20261003.md`，SHA `1011ccff0f2b89aef061583d9ec3ef54d23a31eae31583cab7ac534e9f8f9ad0`；机器索引 `checks/monai3715_coder_a1_owner_analysis_20261003.json` SHA `5207f4049b91ad87cb1e49db983818ff1a2eeabf75f2fe242c6576d9f708f3b9`。其16份绑定原件SHA／bytes全部独立匹配，四调用事件／输入／result SHA、实际候选、3参考和指标支持主要结论。检查单是索引，未只信其摘要。

| 本次关键原件 | SHA256 |
| --- | --- |
| candidate／Project-MONAI__MONAI-3715.diff（820字节） | `c7e0b3b86ef5927230c8b38c8c25832b2ba7cef569138fe81b17ea4bdf28ff31` |
| frozen／frozen_patch.json（30,132字节） | `1341735811427626f8265e28c889cc9711699168be0992de35d0dbbc0acb8e9c` |
| frozen／baseline_manifest.json | `e3d21631865b66151fa8db939ece7fbdf4e7156d793c81c1a9876f55b8325dff` |
| frozen／baseline.tar | `1daeebc659138e3bea1e1bd94e269e4290a3edd9ca3609aff94444ef25d2735f` |
| attempt／attempt.json | `2c2be8cf5755d0ea84536b1b81ac6a0c6a4ad13b70e5ba669cee72e109d34841` |
| grading／projection.json | `b4f1a9edb616e60241ec35f5f4e94edf734cea24163ee3909b04dc673e65f941` |
| grading diagnostics.json | `009a6f003c923d2593a2d87c7fbcfcda53898cbb547ad40b55fe08ccfe056c94` |
| result.json | `1dad497889835de8e2340165c712f99dbf9ceda0dbcc05ae46daf7cb6a51c008` |
| gateway requests.jsonl | `c9b0ddafd10b4f0dcac1e3cfa5d5104e4984d7b94de70ac6d30679e865f7d0a9` |
| gateway responses.jsonl | `7165ee76e14a86910c73f01f1d1aacf769b68440686fdda19db015c83a8ed9d1` |

上表candidate／frozen路径在证据根attempt下；diagnostics／eval.log完整文件名见前文，所有原文件不改。两模型总回执SHA `36740efe35e1d98af4c9efcc90e00e3c9582194feb3795d875f59ae94070e832`只按生成时冻结原状态读回；行政发送／returned不是本次语义核查负责的动作，不静默修not_sent字段或据此重提请求。

本报告仅Coder首次候选的语义和验证质量；Qwen旧报告按其版本复用，各模型各一次成功不估计稳定解决率、不证明训练饱和、完整训练actor capture／消费／loss或留出资格。当前无具体新修题／环境阻断，无依据机械重跑有效尝试；按现行覆盖优先规则暂缓普通追加，后续用途由题主保留版本差异、单次范围和未覆盖项维护。
