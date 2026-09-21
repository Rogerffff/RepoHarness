# R6c DeepSeek-V4.1-Flash：作者自查记录

日期：2026-09-10。正文：[R6c_deepseek_v41_flash.md](../R6c_deepseek_v41_flash.md)。

**状态：上传版正文、附录和原图精读完成；作者自查完成；独立审查、代码复现与训练复现未进行。** 当前没有实际独立 reviewer，不填写虚构线程 ID、子 agent 配置或“独立通过”标签。

## 1. 固定来源与代码库边界

主来源为用户上传的 `DeepSeek_V41_Tech_Report.pdf`，51 页，1,809,802 bytes，SHA-256：

```text
ba68e2e40408125ae6d2f63a9a241b61c73910691c74ec1a2a7023c851eac08d
```

文件创建／修改 metadata 为 2026-09-10 05:49:49 UTC。正文无单独 arXiv/version 编号；未凭文件 metadata 推定官方上线时间。官方 HF blob/model 页读取 cache miss，另尝试 metadata/resolve 入口亦失败；容器 requests 无可用外网连接。没有把这一访问缺口写成“模型或代码没有公开”，也未用第三方摘要填充原文。

RepoHarness 文档读取基线为 `miles-migration@2e1e857fe3b8b0b84305ef5a5ed03d98d5927951`。沿用当前 `NOTE_TEMPLATE.md`；`CURRENT-STATE-BRIEF.md` 仍标 2026-09-05，故只做带前提的 A/B 设计映射，不主张审查了最新代码。新建独立文档分支 `research/deepseek-v41-flash-20260910`，不修改共享索引／实施配置。原分支上计划正文路径经 fetch 确认为不存在，避免覆盖其他线程已有文件。

## 2. 实际阅读与视觉覆盖

全部 51 页用 PyMuPDF 读取原生文本、逐页保存并渲染；Files 补读了初始上下文未包含的正文后半和全部附录；未使用 OCR。主文 §1–6、Appendix B/C 读全；References 和 Appendix A 核验来源身份、页序与尾部完整性，不扩读全部引文、不复述作者名单。

| 图表／公式 | PDF 页 | 已检查内容 |
| --- | --- | --- |
| Fig.1 | 1 | 四项 agent 指标的比较对象；global KV 389120/48068/3514/890 bytes；不是总显存 |
| Fig.2 | 5 | context 4K→1M；BF16/FP8/FP4 加权 FLOPs；不是 latency 曲线 |
| Fig.3 | 7 | 20+20 层、encoder 与 decoder 的共享依赖、Engram、DSpark |
| Fig.4/5 | 10/11 | Full/Reindex/Reuse；candidate pool 与最终 Top-K 的区别 |
| Eq.(1)–(7)、Algorithm 1 | 9、12–16 | CED KV 源、mHC coefficient shift、内存流量、Nesterov 与 Sinkhorn 更新 |
| Table 1、Fig.6 | 24/25 | 20 项 benchmark 行、各 shots/指标；三种内部 BPB 的全部 9 个值 |
| Fig.7/8 | 27/28 | cumulative steps、断段 merging、512K/1M、no-gpu subset、多 scaffold 浅／深线 |
| Eq.(8)–(10)、Table 2 | 29/30 | `(x,b)` subgroup；扣分 cap；有限训练 levels；low/high/max=50/75/100 |
| Table 3 | 33 | 全部 19 行、7 个模型列、† text-only、Pass@5/Almost@1/Resolved/rating 区分 |
| Fig.9、Table 4 | 35 | effort 局部回落；8 配置结果；N=8/3、1M、500 model-generation rounds、无网条件 |
| Fig.10 | 36 | 172 golden tasks、516 planned rollouts、deadline、ProgramBench 8h peak、MA/SA 两条曲线 |
| Table 5 | 48 | 四个 Claude 版本、所报 average 按未舍入数值计算 |
| Fig.11/12 | 49/50 | 跨 scaffold effort 校准、局部非单调；HLE-Text 标签；虚线是 output token |
| Eq.(11)–(17) 与末段 | 49–51 | 未封顶、内点、指数边际收益假设；p.51 对局部模型与 cap 激活的限制 |

图页有单页与原分辨率联系图两种查看方式，密集表和关键公式另看单页。没有按像素估读生成精确训练曲线数据；仅转录正文或图上明确标注的数字。

## 3. 关键核查结论与写法约束

| 核查点 | 最终处理 |
| --- | --- |
| 后训练是否真有新优化算法 | 保留作者“无算法创新、重点数据”的说法，但不把它当作排除所有其他变量的普遍因果定律 |
| 552B 与 196B、8B/16B | backbone、Engram、prefill/decode 激活分开，不能按 8B dense 成本估算 |
| 架构变更与 kernel 优化 | mHC shift、QAT、hierarchical candidate restriction、bounded replay 不是任意旧模型可无损插入的 serving 开关 |
| 样本调度与 GRPO 组 | 完成计数触发容量补位，不等于任意混组算 advantage；训练 G 未披露 |
| 异步 vs 共置 | 同设备 time-share，但未完成轨迹跨 checkpoint；不改写成严格 on-policy 或始终双池并行 |
| routing replay 与 KV 复用 | 保存行为路径不自动证明 fresh-recompute 一致；同权重近似 replay 与跨权重状态重用分开 |
| stale token mask | 自身梯度、别人的 baseline、上下文、分母是不同影响，原文未给完整合同 |
| agent-caused crash | 按原文记 failed trajectory 与 repercussion，不擅自归成可删除 infra error |
| OPD 异构教师 | 40+、full vocab 与动态切换确有披露；KL 方向、tokenizer、placement、精度、总成本不补写 |
| effort 强单调说法 | 正文／B.3 与 Fig.9/11/12 的局部回落分开；B.2 自己也承认 accuracy 不单调 |
| effort 控制是否零样本转移 | p.29 用于 agentic RL 与 p.34 单响应迁移说法并列，不自行调和 |
| 多 scaffold 泛化 | 实际训练、固定 checkpoint 测试、未见 scaffold 泛化三个证据层分开 |
| 评测 N | 8/3 是重复采样，不写 Pass@8/3，也不充当训练 group size |
| 多 agent 结果 | strongest observed configs、golden/no-gpu 子集、按 deadline 比较；不写等 token 因果收益 |
| >95% 真实任务 | 记录为缺少定义／分母的概括性主张，不当实测成功率 |
| Table 3 的最新性 | 没有 Fable-5/GPT-6 Astra 列，不能拿结尾文字增补排行榜 |
| 公开性与访问失败 | 原文未披露和本轮未取得严格分开；不凭外网失败判断作者没发布 |

这些是证据核查与防止误归因，不是一份“发现论文若干 bug”的声明。图文的局部差异没有统计原始数据，不能推定其大小或显著性。

## 4. 已执行的算术与文本检查

本地转录 Table 1/3/4/5 和 Fig.6 到结构化中间文件，以脚本生成正文表格；复核数据行数为 20/19/2/2，BPB 为 3×3。中间 JSON 只用于本次质量检查，不将其包装为作者开放数据。

独立复算：global KV 比为 3514/890≈3.948、389120/890≈437.213；Table 4 的两项跨 scaffold 范围为 8.7/6.5 pp；Table 5 内 Claude 版本范围为 1.4/1.1 pp；ProgramBench peak 差为 9.65 pp、FrontierSWE 20h 差为 4.70 pp。所有差值明确标为读者算术，不是显著性检验。

Appendix C 用任意示例正参数在未封顶内点区间数值核对 Eq.(14)–(17)，示例参数不写成报告超参。扣分到 cap 后导数为零与原文 p.51 一致。

检查正文的本地导航锚点、引用定义、相对文档路径、数学分隔符、替换字符与未展开模板标记；正文与自查两个文件按仓库目标路径打包。没有运行 CUDA、模型 forward/backward、sandbox 或论文训练。

## 5. 后续独立复查的最有用范围

优先对照 p.29–32 的 subgroup、样本补位、KV 跨版本续写、OPD 配置切换是否被准确拆开；再核 p.34 与 pp.48–50 关于单调性的文字／曲线差异。其次核数据生产是否被误写成现成公开 taskset，以及 DSec 并发容量是否被误写为唯一环境数量。最后检查全部 Table 3/4/5 的指标、脚注和多 agent 子集边界。

若未来能取得固定 HF revision，应对比本稿上传文件身份后决定是否更新，不让新的 `main` 静默替换原文。只有实际完成独立检查后，再追加 reviewer 与修订记录；本记录不预先声明通过。
