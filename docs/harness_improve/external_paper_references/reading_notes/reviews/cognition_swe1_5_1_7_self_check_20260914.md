# SWE-1.7 主读与 1.5/1.6 演进：作者自查记录

日期：2026-09-14。成品：[SWE-1.7](../cognition_swe1_7.md)、[SWE-1.6 Preview](../cognition_swe1_6_preview.md)、[SWE-1.5](../cognition_swe1_5.md)。

**状态：三篇正文、已提供技术图表及1.7全部展开示例阅读完成；作者自查完成；没有独立reviewer，也没有训练复现。** 当前工具没有创建独立研究子agent的能力，不能沿用其他线程的独立审查通过标签。没有编造reviewer ID、effort或GPU检查结果。

## 1. 输入和固定范围

输入为用户的 `02_SWE17_16_15.md/.zip`，采集日期2026-09-11；压缩包包含102个条目、约10.5MB解压数据，路径安全检查后读取。正文快照时间：1.5为09:43:13.419Z、1.6为09:42:40.145Z、1.7为09:47:55.261Z。本轮三个官方URL均返回可读正文，核标题、署名、日期和重要段；没有另行归档所有实时动态页面，因此图表/展示事实仍以源包快照为准。

远程基线为 `miles-migration@2484c93cad304588b41abeb38b6b6b976dfbda0d`，即SWE-2阅读提交。检查现有阅读目录，未找到本轮目标文件。未修改SWE-2、源材料包、共享批次计数、任务集、训练代码或配置。

本轮不重读Kimi、R3、Dynamo、SWE-grep、Kevin、Muon、FrontierCode等引用的全部正文／代码；它们在本组三篇中的披露与引用身份已记录。模型基座身份和后训练继承以每篇实际文字为准，不以版本编号画成必然的连续训练链。

## 2. 实际图文覆盖

| 来源 | 正文范围 | 图像／动态材料 |
| --- | --- | --- |
| SWE-1.5 | 发布、Motivation、Agent-Model Interface、Environments、Training、Public Evals、Speed、What's Next | 3幅原始PNG；能力/速度表、跨harness表、速度—分数图全部核对 |
| SWE-1.6 Preview | 导言、Evaluation Details、Scaling RL、6×性能、GPU Allocation/Staleness、Model UX及结尾 | 9幅原始PNG；4个公式白底查看并转写；全部benchmark柱值、两训练曲线端点、staleness轴、Arena值 |
| SWE-1.7 | 导言、entropy、multi-cluster、fault tolerance、compaction、data、behaviors、evaluation、18条references | 5个网页图截图、5个SVG及6个状态截图，映射视觉PDF16页；三个CoT和三个注释案例JSON全读 |

合计覆盖附件视觉索引28页对应的现有图像／状态。这里没有把截图PDF当作者论文，也没有声称28页均是互不重复的独立实验。1.7 chart-01/02为同一区域双图，chart-03/04为地图不同状态；技术正文的5幅SVG另行渲染。所有SVG/PNG均直接阅读，不使用OCR，不用曲线路径像素制造精确训练step。

透明公式／SVG最初在普通RGB转换后背景变黑，随后改用白底alpha合成和白底SVG渲染，重新核对标签与公式。这个渲染问题已经消除，不留下无法看清却标已读的公式。网页主文不包含需要补读的独立附录。

## 3. 数学与数据检查：真实执行，但不是模型复现

使用本地Python/NumPy和JSON解析，未执行下载JavaScript。完成：

1. 1.7三份CoT每模型均为5个thinking block；逐行读取中间工具名。空白分词数依次为85/241、78/108、67/84；tool记录行为19/12、8/6、10/9。这些不是token统计或整个run计数。
2. 三个长程案例全部读取，区分作者summary、thinking摘录、tool和toolResult；确认字段`swe2`显示为SWE-1.7。
3. `array-135251`的8模型×3benchmark与正文主表核对；`data.json`单列new_score/correct/cost/harness和null字段，不以新增Fable条目回填发布主表。
4. 三token局部例取概率(0.70,0.29,0.01)、advantage=-1，小步0.001，更新方向为(0.70,0.29,-0.99)，entropy由0.6547077降到0.6545716。只验证一个说明性局部例，不是普遍证明。
5. 固定logits=(1.2,0.3,-1.0)，kept-set={0,1}，对logprob做中心差分，梯度约(0.2890505,-0.2890505,0)，与解析式一致；singleton kept-set={0}的梯度为零。未测试真实SGLang或trainer实现。
6. 1.6平衡公式用说明性常数N=8、s_roll=100、s_train=900、r=2、B=64、L_out=1000检查，n_t=2、n_i=6时两阶段时间相等。**这些不是测量值，也不是向项目推荐2/6分卡。**
7. 独立算术：51.7−40.1=11.6pp，相对28.93%；7958/4245≈1.875；40.08−34.47=5.61pp，40.08−29=11.08pp；950/69≈13.77、950/142≈6.69。原文近似措辞仍并列保留。

内部检查JSON仅是可重算诊断，没有作为新训练数据或独立评测结果发布。下列最小代码可复算概率与资源恒等式，不依赖私有资产：

```python
import numpy as np

x = np.array([1.2, 0.3, -1.0])
h = 1e-6
for keep in ([0, 1], [0]):
    keep = np.array(keep, dtype=int)
    def log_q(z):
        a = z[keep]
        m = a.max()
        return z[0] - (m + np.log(np.exp(a - m).sum()))
    grad = np.array([
        (log_q(x + h * e) - log_q(x - h * e)) / (2 * h)
        for e in np.eye(3)
    ])
    q = np.zeros(3)
    a = x[keep] - x[keep].max()
    q[keep] = np.exp(a) / np.exp(a).sum()
    assert np.allclose(grad, np.array([1., 0., 0.]) - q, atol=1e-8)

N, sr, st, r, B, L = 8, 100, 900, 2, 64, 1000
nt = N / (1 + st / (sr * (1 + r)))
ni = N - nt
assert np.isclose(B * L / (ni * sr), B * L * (1 + r) / (nt * st))
```

## 4. 关键修正与解释边界

| 核对点 | 原始事实 | 成品处理 |
| --- | --- | --- |
| 1.6 r方向 | 列表output/input，后文in/out，公式采用1+r | 明示冲突，再用与公式一致的后一定义推导，不静默改源文 |
| 1.6并发单位 | n_i先为GPU数，c又按engine定义 | 保留原式，另列多卡engine时需换算的读者分析 |
| 1.6“11%”与“2×” | 图为51.7/40.1和7958/4245 | 源文与算术分开，不把近似标题当精确相对提升 |
| 1.6 utilization图 | 实际纵轴Concurrent Requests | 不写成GPU百分比或MFU |
| 1.7 mismatch图 | 原SVG只有一条蓝线，alt提及naive对照 | 不虚构第二条曲线或精确双曲线消融 |
| 1.7 entropy图 | recipe与baseline起点不同，轴无数值 | 不恢复绝对训练step，不归因给一个开关 |
| 1.7 CoT压缩 | 词句风格与总内容量不同 | 列示例词数但不称反证；不把短句等于少总token |
| 1.7边界图 | hypotheticals=21/21 | 不写所有类别均增多；mentions不等于正确验证 |
| hidden contract案例 | 作者说部分需求未明示，hidden tests有检查 | 保留相对verifier成功，要求区分需求恢复和猜测试，不自行裁定所有替代解 |
| uv案例 | Kimi已经运行其他失败命令但限制scope | 不概括为基座永不实验；重点是证据后的范围决策 |
| 1.7数据资产 | JSON有Fable新增行，静态表无；correct≠new_score | 不混发布时点、指标或benchmark harness |
| 1.7在途缓存 | 新权重继续且KV保留 | 不称数值等价，也不在未读私有实现下判定错误 |
| 1.5 draft | 明确位于Cerebras部署速度优化 | 不记为RL rollout线上draft训练收益 |
| 三代模型关系 | 1.5未命名base；1.6同pretrained base；1.7 K2.7 | 不画未经证实的逐checkpoint续训链 |

这些主要是源文适用范围、口径或表述不一致，不应统一宣传成发现论文bug。阅读目标是使后续引用不会丢掉这些条件。

## 5. 交付前检查与剩余工作

本轮对Markdown进行UTF-8、相对来源链接映射、内部anchor、引用定义、代码围栏、数学分隔符和末尾空格检查。三个正文独立维护，演进表集中在1.7 §10。提交采用新文件；提交前刷新分支，非强制更新，提交后回读文件及差异；不在成功前预填commit。

当前新包没有阻塞性缺失，无需用户重新补传这三篇图表。尚不可得的是未公开的训练/数据/权重/协议，以及没有提供的完整原始rollout、per-task成绩和模型内部日志；源码静态网页材料不替代这些资产。

独立复查建议优先看：1.7 replay的支持集与零梯度范围；1.6公式中的单位和输入比；三份annotated案例与主文泛化主张；三代评测与速度的分母。未进行独立审查、训练或GPU故障实验的状态必须保留。
