# MONAI2446：两模型首次诊断完成

2026-10-04。**Coder和Qwen各首次一次，原评分均1，四参考每臂全过；题主与非作者候选审查支持两种最终修法。没有新的确定修题/环境阻断，本轮可核收关闭。** 这是两次单臂探索诊断，不能报告稳定解决率、训练资格或全外部接口兼容。

公开问题要求SmartCacheDataset在shuffle=True时保留调用方列表，同时内部继续shuffle并正确初始化/更新缓存。R15 CPU控制已有noop/gold/关闭shuffle坏修/constructor复制合理替代=0/1/0/1，本轮不重跑。正式每臂1 F2P＋3 P2P、完整模块9通过；新增节点实际输入为list[np.ndarray]，不能扩称顶层ndarray容器全面验证。

| 本题首次证据 | Qwen3-Coder-30B-A3B-Instruct | Qwen3.6-35B-A3B |
| --- | --- | --- |
| job | gpu1003-monai2446-coder-a1 | gpu1003-monai2446-qwen36-a1 |
| 最终修法 | constructor先list(data)，再走原randomize | randomize复制并返回，constructor接收局部data |
| 修改/返工 | 一次Edit，无返工 | 两初版Edit＋一次纠正Edit；初版copy被父构造覆盖 |
| 自测弱项 | 两新脚本只打印，无assert | 初版只assert输入保持，内部未shuffle仍误打印SUCCESS |
| 实际回归行为 | SmartCache7P、Cache17P | 原shuffle1F/6P检出初版；修正后7P、17P、Handler1P |
| 最终完整FP | dataset.py＋两个根目录脚本 | dataset.py单项 |
| 轮/工具/生成 | 14/13/14 | 19/18/19 |
| 累计输入/输出tokens | 263,780/2,736 | 446,780/5,789 |
| entry求解/正式评分秒 | 52.755/420.102 | 77.264/408.025 |

两种最终修法都复制外层容器、保留元素，符合公开问题。Coder方案保持randomize旧协议；Qwen方案改变可观察的原地/返回协议，但固定baseline唯一调用点已接收返回值，真实子类无旧override依赖。外部直接调用或旧自定义override未验，是兼容边界；没有已存在的版本内漏改证据，不能据任意假设阻断其他GPU作业。实际回归能抓住“外层保持但内部不shuffle”，模型初版错误与随后纠正过程都保留。

两模型同题主输入SHA `22aea4dfe7a04e2f8f7b5669a8fb1bdf70137537941cc8a251cb3f0113d88cd2`、相同base/实际image/public/prompt/baseline/materials/预算及grader版本。两臂solve均code_v8；Coder engine/adapter旧code_v4，Qwen服务code_v8，gateway分别18081/18082，profile仅model_proxy_upstream不同。**这些绑定支持同题同参考比较，不证明全部服务运行版本一致。** 两次单样本过程差异不转为稳定能力排名。

执行总回执 `runs/ordinary_gpu_probe_20261002/migration_20261003/swe-monai2446-r15-shuffle-cache-nib4-20261003-v1_pair_execution_receipt_v1.json` SHA `46dd39910e0f837fb8bd83a4c3b8ea57648ce4b24d773f1534ca76085c38cf74`支持两首臂完整终态、原FP评分、参考及cleanup。Coder旧独立执行与候选验收保持；Qwen机械回执限定运输/解析，新增非作者报告补语义/轨迹，不将null语义字段静默改写。资源有限样本、环境谱系null、env_qualification=absent、stdout边界、无GPU内存权重证明及长上下文/训练接线未覆盖全部保留。

- [Coder题主分析](probe_analysis_2446_coder_a1_20261003.md)、[首次验收](checks/monai2446_coder_a1_first_diagnosis_accepted_20261003.json)、[非作者语义](reviews/non_author_monai2446_coder_semantics_20261003.md)。
- [Qwen题主七方面分析](probe_analysis_2446_qwen36_a1_20261004.md)、[42件/逐调用核查](checks/monai2446_qwen36_a1_owner_analysis_20261004.json)、[非作者语义与轨迹](reviews/non_author_monai2446_qwen36_semantics_20261004.md)。
- [两模型核收绑定](checks/monai2446_two_model_first_diagnosis_20261004.json)为本轮完成依据；共享总账ACK与活动请求释放使用工具完成，无新增求解/重新评分/CPU作业。

旧首Coder报告“另一模型待”等保留写入时历史快照；当前结论以本汇总和核收绑定为准。6975仍是本仓唯一未收齐的双模型诊断，不能据2446成功关闭它或重提已在途请求。
