# Infra07 作者自查与执行记录

日期：2026-09-08。正文：[训练—推理一致性](../Infra07_train_inference_consistency.md)。

**状态：限定范围内的精读与作者自查完成；独立审查未执行；GPU／模型／训练复现未执行。** 没有调用独立sub-agent工具，不填写虚构reviewer、线程ID或effort。

## 1. 实际来源和版本

读RepoHarness的 `miles-migration@d2df06d49e42b93436d10d1b7a12d4e1f0ae3be5`。连接器没有给出可以唯一认定为用户新工作分支的名字；另一个可见research分支属于NeMo任务6，因此采用任务7隔离分支，不改共享README和任何生产文件。

主读TML确定性文章、SGLang确定性文章及官方文档；vLLM版本化概率文档、#48305/#42259、#49577说明；Open-Instruct #1473。网页静态正文、技术代码与文字表值已读，交互图、附图未做逐点复现。没有声称每个RFC子链接都审完；#42259只读前四条评论。

源码：项目SGLang `4e230c3d85cefdab5b65eeb6f6f87793a707a6fb`，当前SGLang `554f817948c26e8e9c8338b4a33e94a609d6f0fb`，当前miles `3de96596f16b9e6d23ba550c4c47de3479c9f14c`；项目capture与faithful DIS按上述RepoHarness基线。完整路径和阅读范围见正文§1.3。没有用当前main替代项目pin，没有完整clone或运行上游。

## 2. 主要核对与修订

| 项目 | 核查结论 |
| --- | --- |
| 同名logprob | raw、temperature、支持集条件概率必须分开；greedy返回的model LP不等于delta行为LP |
| 采样支持质量 | 实际S并不普遍等于top-p参数；CPU反例使用S=0.9而threshold=0.8 |
| 目标支持覆盖 | IS无法恢复behavior从不采到的区域；固定历史K是条件目标，不等于全词表目标 |
| 现有项目能力 | 实际P2捕获已替换成effective sampling LP，P3也按同K归一化；不重复建议“增加已经有的功能” |
| Debug recompute | 当前miles可覆写rollout LP；来源标签必须保留，不能改写之后当生成真值 |
| 采样与梯度 | selected LP与loss相同仍不保证stop-gradient一致；用torch反例验证 |
| 指标 | signed mean和ESS均可假正常；all-masked不是PASS，NaN不填零 |
| 支持矩阵 | 2025博客、2026文档、当前main与项目pin分别记录；SM100和SM120不等同 |
| 资料状态 | vLLM#49577已合并，但不推定所有下游版本含它；Open-Instruct已关闭但没有公开根因说明 |
| 性能分母 | SGLang约2.8倍是deterministic内部CUDAgraph开关；非普通服务对比 |
| 观察开关副作用 | C7已见metrics条件下接回TIS loss，但没审所有guards；列待验证而非已复现bug |
| 分支与写入 | 不覆盖NeMo任务和共享索引；只交付正文、自查与诊断附件 |

## 3. 已执行的检查

在Python3.13.5、torch2.10.0+cpu下运行 `test_replay_check.py`：**33 tests，0 failures，0 errors，0 skipped**。另执行py_compile；离线CLI正负对照与结果解析进行冒烟验证。详细test IDs、运行环境和数值在 [CPU结果](../probes/infra07/cpu_results_20260908.json)。

测试为我们独立编写的合同、数学、autograd与localhost mock协议测试。没有导入SGLang、vLLM、miles；没有GPU；未安装transformers。`score-hf`仅通过语法检查，未加载模型；真实SGLang HTTP未运行。不能把33项测试当成上游测试通过、模型逐位对齐或实验复现。

脚本显式容差，无默认通过阈值；不匹配返回INCOMPARABLE，无有效token返回INSUFFICIENT。权重标签由操作者声明，不能证明实际张量；routing未提供时不声称route parity。capture只允许简单causal文本，复杂位置／mask／多模态拒绝，不静默降级。

## 4. 残余限制和后续独立复查重点

优先核P2/P3真实概率列、C5重算覆盖行为，以及C7三个policy身份。再查min-check的causal shift和first-None处理是否适配目标服务版本；如不适配，应新增明确adapter而非裁剪到相同长度。实际GPU步骤应首先冻结token和权重，不能仅设置学习率0后观察aggregate均值。

尚未审完整的参数互斥条件、model routing实现、weight publication/cache invalidation、分布式loss reducer。因此正文所有潜在优化/PR都保持条件性，不将静态风险写成生产故障或给出未经测量的加速比。

来源与代码事实、我们的数学推导、执行结果、项目候选分别成节；没有改训练合同、taskset、配置、阈值或依赖。远程提交是否成功与最终commit由交付回复和实际回读确认，不在提交前预填。
