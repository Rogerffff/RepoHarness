# Dask9378 Qwen3.6 首轮：非作者候选与轨迹核查

2026-10-04。对象 `gpu1003-dask9378-qwen36-a1`，base `8b95f983c232c1bd628e9cba0695d3ef229d290b`。本报告仅新建审查文件；没有 SSH、容器、CPU、模型或 pytest 重跑，没有修改共享源码、原件、题卡或总账。

**接受当前用户 B 的默认 mask／ones、zeros 有效值修法。实际正式 3F＋134P 共137项全部通过，raw reward＝1；未发现模型测试污染正式分或当前B目标的确定语义阻断。** 这个结论不授予全参数兼容、稳定模型能力或训练资格。本次审查零新增运行、零新增样本。

## 当前范围及候选

[B有效测试](../tasks/dask__dask-9378/effective_test.patch)按已决定路线验收：有 `da.ma.<like>` 时要求该入口正确；缺失时接受正确顶层路线。三项逐元素 mask，ones／zeros 再核有效值，empty 的未初始化值不作判据。dtype、order、chunks、name、shape 的全面兼容及顶层入口同时修复没有变成本轮新要求。

[实际FrozenPatch](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask9378-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask9378-qwen36-a1/attempt/frozen/frozen_patch.json)规范JSON摘要为 `7f8f4df42646b599d31d4cd6b27bf6bc5d30637f6199fdaec2838400de916c86`，两条entry：`ma.py`（6,541B，内容SHA `3e4d82eb2441e903e92c0c3580b6278dae3091b5bc92748d387a6e0a6c5f559c`）和模型自写的 `test_masked.py`（15,401B，内容SHA `2e53b5b4fe4b0c4d7bb31a1509db6b67f1748da1778087d3a81f22c86033a078`）。全部8次成功Edit以actual baseline成员在内存中顺序重放，逐字节得到这两条FP，未执行候选。

生产文件仅在原192行后追加三个dtype helper和 `(a, dtype=None)` 三函数。默认经 `asanyarray` 保留输入数组，再逐块调用 `np.ma.ones_like`／`zeros_like`／`empty_like`；mask及有效值的实际B测试支持这条路线。未见测试名、评分输出或环境特判。

与已封存Coder边界要分开记录：Qwen初版也出现dtype元信息与计算结果不一致（轨迹L206、L220），但这次真正修正了它。最终helper把 `dtype_arg` 传入NumPy，同时设置map_blocks元信息（FP ma.py:195–237）；L462真实computed dtype为float64，L648／L664的三函数float、float32、int32自测通过。不能把Coder的dtype实败继续写成Qwen最终缺陷，也不能把有限自测扩大为正式全参数矩阵。

Qwen三个最终签名不支持order／chunks／name／shape这些关键字；这与Coder接受后静默忽略不同。默认shape/chunks沿输入是源码与当前实际检查的范围，可选参数反例没有重跑。`creation.py`未改，因此原顶层调用仍为原逻辑属于静态推断；B允许新增ma路线。

## 正式分与测试投影

[投影](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask9378-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask9378-qwen36-a1/grading/projection.json)只包含 `dask/array/ma.py`，模型追加的7个测试留在轨迹FP中，未进入正式评分。报告 `test_files_modified=false` 是评分投影口径，不能改写为“原FP没有测试改动”。

[原评分日志](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask9378-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask9378-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask9378-qwen36-_e96b67c1.eval.log)第215行只有ma.py为dirty；第638–690行打印最终生产补丁；第692–703行恢复base测试、核对base SHA后应用B测试。第986行收集137项，第1122–1124行三项目标全PASSED，第1276行 `137 passed in 4.32s`。Start／End为第978、1278行。片段内逐项输出及summary各有137个唯一PASSED ID，两套集合均与实际host grading的3F／134P精确相等，缺席、额外、skip及unaccounted均为0；双份输出没有相加。

host grading的test.patch逐字节等于当前有效测试，SHA `9fc1a9d5ae885d9cc30388a875ab7ed629081de7ba7bdcc8571f3aca604a248a`。它对empty只比较mask，不继承模型的empty值oracle。diagnostics确认install rc0、无failed命令、未跳过；实际安装1.0秒、测试标记间隔5.302秒、candidate segment完整，runner摘要未变。评分总406.519秒，其中trusted setup383.921秒；不要把这段准备成本归成模型求解成本。

完整机器运输、code9／R25实际绑定和ack由父线程处理；本报告只核读件及候选分的证据，不冒称独立重验全部163件或运行环境。

## 模型过程与验证范围

[完整轨迹](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask9378-qwen36-a1/queue_qwen_dask4_r25_code9_v1/results/gpu1003-dask9378-qwen36-a1/attempt/trajectory.jsonl)共732行，622,672B，与harness副本字节一致。读取ma／creation／原masked测试／导出后，L152／L156实际重现顶层丢mask；选择新增ma符合公开建议和B。dtype修正经历了重复给绑定方法传a的错误：L294、322、336、350失败，之后读map_blocks及原方法，L444去掉多余数组参数，L462验证computed dtype已一致。L406另一次错误来自临时helper的关键字名不匹配。这些是实际探索失败，不能记成运行基础设施失败。

自写测试另有两次把NumPy mask结果当Dask调用compute的错误（L536、L592），分别修正；L620普通数组类型oracle错误地用 `np.<like>` 比较新增ma路线，L630改为 `np.ma.<like>`，与本接口语义一致。最终生产Edit在L444，最后测试Edit在L630；L648为4 passed／0.31秒，L664完整141 passed／4.39秒（134原公开项＋7自写项），之后仅运行例子、读取生产源码，没有再改文件。这个141不是私有137正式分。

最终L728准确列出新增ma三个接口和dtype wrapper，没有声明所有可选参数均支持。仍有两项P2局限，均不阻断B分：

| 局限 | 精确证据与影响 | 后续使用条件 |
| --- | --- | --- |
| **F1：自写empty值oracle无效** | FP test_masked.py:450、475、491对独立empty输出的有效数据做assert_eq；L578／648／664通过是真实记录，但未初始化值不保证相等，可能偶然通过或换内存状态失败。测试文件已排除，正式分不受它影响。 | 若复用这些测试，empty仅比较mask及承诺属性；ones／zeros继续比较有效值。当前只登记，不重跑或改B。 |
| **F2：所谓精确原例及NumPy标签不精确** | L674／678及L710／714改用da.ma.ones_like；L714的np.ones_like标签仍打印Dask函数，L718不能作为新的NumPy参考。最终L728已明确ma路线。 | 只能称新增ma路线示例；只有真的测试顶层才可声称顶层修复。无欺骗动机推断，不因标签重跑。 |

两项的行为、违反条件、影响、分期、精确行号、静态核法和后续验收条件均见JSON。未发现当前默认mask目标的新反例。

实际49次模型响应，51工具（33 Bash、10 Read、8 Edit），51结果全部返回，其中8次工具结果错误。三次响应含两项独立工具（L11／15、L30／34、L133／137），并非全程每响应一个工具；这只证明本臂小组多工具，不能推训练并发规模。可更早读取绑定Array.map_blocks方法以避免反复传a；独立读件也可合并。正常求解112.663秒，CC109.128秒、API85.340秒；累计输入1,346,685 token、输出13,027，最大请求输入55,372／输出976，全部finish_reason为stop，未见预算截断。CC num_turns＝52与49模型响应是不同口径。实际gateway max_tokens＝65536，CC modelUsage的maxOutputTokens＝32000为另一观察字段，不拿后者改写实际请求预算。报告queue_wait＝0不代表派发前排队已知为0。

## 公开投递与复用边界

实际prepared spec.prompt、solver_prompt、attempt/prompt及首gateway用户题面完全同字节（998B，SHA `78a0f438f711b24dec6ffc48368df66ec33b007e277bc2866c3bf137b1f4a04d`），实际model_sent为 `Qwen3.6-35B-A3B`。prepared view仍有旧public_hints，但全部49个actual gateway body均没有“不改测试”或预激活说明关键句，cc_home归档无CLAUDE.md。没有证据把追加测试判为违反已收到的“不改测试”指令。

这沿用[已有效的GPU口径澄清](../../../../../../../../runs/category2_repair_20260929/swe_dask/model_analysis_20261003/dask7656_qwen36_a1_v1/public_hint_scope_GPU_clarification_v1.json)：unchanged只保持prepared spec.prompt，不自动追加全部旧hints；不是本轮新缺陷、待对齐事项或重跑依据。初始原公开masked文件无私有3F；候选测试名也与私有项不同，本次观察未发现私有评分材料泄漏。该观察不是抽象全链安全证明。

已封存Coder原GPU infra None及同FP CPU raw1按各自证据保留，Qwen最终dtype修正与其区分。本次只审已计划的Qwen首轮，不为通过结果追加样本。停止条件已满足：当前B语义、137逐参考状态及测试排除已核清；可选API与两项验证局限只登记，不扩oracle、不授稳定能力或训练资格。

本审查实际读取／哈希41件，共22,738,286B，另外记录baseline内4个精读成员的SHA／大小。完整读件清单、FP规范摘要、Edit重放及逐参考核法见[机器审查](non_author_9378_qwen36_a1_candidate_review_20261004.json)。历史报告为封存来源；现行题卡及总账由父线程更新。
