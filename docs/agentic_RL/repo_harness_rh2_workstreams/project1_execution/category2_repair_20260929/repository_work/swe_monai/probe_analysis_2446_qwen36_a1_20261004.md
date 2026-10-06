# MONAI2446：Qwen 首次尝试的题主分析

2026-10-04。**最终候选合理修复了调用方列表被原地重排的问题，保留内部shuffle和缓存更新，原评分1，1 F2P＋3 P2P全部通过。模型初版漏把复制结果交给父构造，经真实旧回归失败后承认并修正；不能用最终成功抹掉早期检查弱项。** 未发现本版本漏接新返回值的确定缺陷或需修题、修环境的新阻断。

job `gpu1003-monai2446-qwen36-a1`，solve及本Qwen服务code_v8，实际Qwen3.6-35B-A3B。固定题主请求SHA `22aea4dfe7a04e2f8f7b5669a8fb1bdf70137537941cc8a251cb3f0113d88cd2`未变；执行job请求SHA `493f515c022ff779d057372f45f18a6ac6cc3129e46f04cf956d2acd6a7b91c9`是另一个记录。权威封包为 `runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-monai2446-qwen36-a1/`，manifest SHA `aed8456172e67c855e8b2478022cf6ffea1eda4af92e5b0526745cd233673226`。题主直接核完整331事件、实际单项FP和42件相关字节绑定，包含机械receipt的34件sourcepaths；394成员整体运输复用回执范围，不重跑任何测试或模型。

1. **根因和修法。** 原`self.R.shuffle(data)`原地修改外层列表。最终方法先`data_copy = list(data)`、使用原RNG shuffle、返回copy；constructor改为`data = self.randomize(data)`，将局部data传父构造。False路径、seed及缓存更新逻辑保持。复制外层符合公开问题，无需深拷贝元素。与Coder constructor先copy相比，这一方案改变了公开`randomize`的原地/返回协议；本baseline唯一SmartCache调用点已同步接收，真实子类SmartCachePatchWSIDataset无override且shuffle=False。外部直接忽略返回值或旧自定义override兼容未验，不能称全接口兼容，也不把任意假设当本仓已存在缺陷。
2. **定位和返工。** 11搜索、25整读、39准确定位原地shuffle，61→65实跑原例确认外层改动。79＋93初版先写self.data再让父构造使用原data；父构造覆盖复制结果，外层保持但内部不shuffle。147→153旧test_shuffle确实1失败/6通过；167读测试、185调试，199承认父构造覆盖，203改为局部data接收。221→225内部顺序和更新末项18/13/5与旧期待吻合。三次Edit按原baseline顺序应用，与最终FP全文逐字节相同；两个候选版本不是两次正式采样。
3. **工具使用。** 18次：Bash11、Read4、Edit3，无Write，无工具参数/权限拒绝。四Read行号文本分别匹配原baseline或当时编辑版本，最终FP/projection只含dataset.py，未改受信tests/fixture或依赖。pytest经head/tail，工具正常返回不等于pytest RC0；旧失败按真实AssertionError/footer识别，最终通过按真实footer核对，不用pipeline退出状态代替测试结果。
4. **并行。** 每次单一tool_use、实际串行。未尝试并行也未验证执行器并行支持，模型能力不可判断。独立模块检查有理论并行空间，但先修复被回归检出的逻辑错误再验证符合依赖关系。
5. **验证质量。** 111→115自测真的assert调用方保持，却不检查内部shuffle。129→133打印内部仍0/1/2/3/4，但无条件打印SUCCESS并称内部已shuffle，是明确验证弱项。真实旧回归153抓到问题后模型修正；最终245 SmartCache7通过/20warnings，263原例输入保持assert通过，283 Cache17通过/17warnings，299 Handler1通过/15warnings。正式评分完整9通过/20warnings，四参考逐条PASSED、无缺席/skip，安装RC0、测试RC0。新增节点实测`list[np.ndarray]`在True/False下内部顺序和缓存值，原P2P保证seed及缓存更新，未直接以顶层ndarray输入作验收。自测、受信正式参考及未验范围分别保留。
6. **效率。** 19轮、19生成，HTTP20条中1条count_tokens；累计输入446,780/输出5,789，单生成最大32,198/945。CC73.692秒、API37.590秒、entry求解77.264秒；评分408.025秒，受信准备377.204秒、候选安装14.346秒、测试6.791秒。整文件读取、初版返工和重复打印增加输入与工具轮数。累计输入不是单轮上下文；评分时间不等于模型推理时间，也不从两次单臂样本推稳定能力排名。
7. **完成和用途。** success/completed/end_turn，无length截断，19生成HTTP200且末次end_turn，两层cleanup正常。有效context196608、实际输出请求65536、240轮、求解10800秒；CC显示32000原值保留，不当作生效HTTP限制。每模型首轮一次，只支持本题首次探索诊断，不估稳定成功率或授予训练/留出资格；不追加普通重复采样。

实际actor/grader image为 `sha256:28959a332c8a17ebfb2db681d3afaf79f8fd6e845ba51406fc7772f32453bcdd`（grader合法`local_build:`前缀保留），base `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`，materials `sha256:7b12ba8af3b62aee6ceba5d5d94255efabd68614dc91514994b22bfcdc87752a`。公开prompt首HTTP原字节相同，image/public/baseline/参考材料同Coder；模型服务版本与gateway不同，不称整棵runtime相同。

服务捕获绑定checkpoint revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、下载manifest SHA `32bd30f61860366b3783eabc9d75bee0cd28c474d9c07de8be8d9ae60a4552ab`、真实engine/adapter前后ID及启动时间/零重启、只读模型挂载与配置/template SHA。它不证明GPU内存权重摘要，也未重复哈希大权重；gateway `checkpoint_identity_verified=false`仍保留为该工具能力范围。终态依完整RC0与精确PID1成功journal，不拿retired unit的not-found默认0当退出证明。37资源样本有未知间隔，env_qualification=absent、baseline环境谱系null、stdout信任边界保持；4GiB记录不证明最低内存或连续资源峰值。

[题主机器核查](checks/monai2446_qwen36_a1_owner_analysis_20261004.json) SHA `9c9fdab471c813906df8209e18199d7b736630078a32b2dad7b564571ac67864`。[非作者窄核](reviews/non_author_monai2446_qwen36_semantics_20261004.md) SHA `8804213d964423aa2638ad045d7c602f90744b1bcfd98045501e63dc6a9cdefc`独立核实际修改、完整轨迹、版本内调用链及四参考；审查者曾读私有材料，非fresh公开读者盲审。CPU/Coder旧验收按原范围复用，旧报告中的待字样留作写入时快照；当前两模型结论见[首次诊断汇总](probe_summary_2446_two_model_20261004.md)。
