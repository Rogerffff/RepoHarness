# E3 Envs-FORGE：作者自查与修订记录

**当前状态（2026-09-08）：已取得用户上传的 v1 PDF，正文与 A–D 全部附录精读完成，19 页均已目视检查；作者自查完成，待独立审查。**

对应[正文](../E3_envs_forge.md)。本文件沿用原路径，避免并行线程的引用失效；2026-09-07 的原始记录在下方折叠区逐字保留。用户提供的 Codex 检查证明它已取得原文，不等于 Codex 已审查本次新稿或下列新发现。

## 1. 本次输入与来源身份

主来源为实际附件 `E3_envs_forge_2608.14312.pdf`，不是仅有链接。使用 PyMuPDF 提取文本和渲染页面，不使用 OCR。首页核对正式标题 *Envs-FORGE: Frontier-Optimized Reward-Grounded Environment Synthesis for Agent RL*、`arXiv:2608.14312v1`、`14 Aug 2026`、作者和机构，页数为19。

| 项目 | 校验值 |
| --- | --- |
| PDF bytes | 2,228,591 |
| PDF SHA-256 | `b0e4dbd7bc35e5a1ad6362e4e4b8d0c51d42ee94780a641bae7bfdd8f473ace1` |
| 按 Git blob 算法计算的 PDF SHA-1 | `e35ca77aab3738fe4a8732d19f28497540884214`，与上一轮 GitHub 记录一致 |
| 写入前正文 blob | `ffbb563f5218114f731f6fe8540d544498d5118c`，远程读取与会话旧稿相符 |
| 写入前历史自查 blob | `aaf8052386dd2c4632dff86a38c71a320281cdd6`，下方保留的原文块已按此 blob 校验 |

没有声称本轮重新下载远程 PDF 并比较两个下载文件。原文访问不再阻塞本次精读；当前尚未取得的主要是实验配置、日志和 manifest，而非全文。

## 2. 按原文章节完成的阅读

| 范围 | 检查内容 |
| --- | --- |
| 正文 §1–2 | 任务动机、prompting policy 与环境生产组件分层、基线比较对象 |
| §3.1–3.3 | 五件套、六动作、reward均值与预测先验、Eq.(1)–(11)、技能和资格约束 |
| §3.4–3.5、Algorithm 1 | 联合物化、gold verification、GRPO来源；图与算法的闭环边界 |
| §4.1–4.5、Conclusion | 全部结果、全部生产统计、单位成本、benchmark/model coverage与组件消融的区别 |
| p.9–10 | Limitations、Ethics、AI使用声明、参考文献；未逐篇重读所有被引论文 |
| A.1–A.2 | Eq.(12)、baseline近似语义、技能taxonomy、solver外部edit mask |
| A.3–A.4 | 同步契约、隐藏资产、归一化、真实chat-template长度、代表性容器preflight、训练配置 |
| A.5 | 五例全部读取，并逐例与C.3原始/合成指令对照 |
| B | 模型组装、SCIP branch-and-cut、49.9104 objective、解码、fallback、保证范围 |
| C.1–C.2 | 七个方法/提示词框全部读取：共享生成、baseline注入、repair、solver payload、动作/方向、edit masks、skill contract |
| C.3 | 五个案例框全部读取；重点核对已有要求、保留/移除技能与答案直给 |
| D | 资源、batch、response长度、学习率、超时、epoch、checkpoint、reward/KL、engine容量 |

本次确实查看了全部19页渲染图：第1–6、8–15页按相邻两页逐组查看，第7、16、17、18、19页单独查看。正文附有Figure 1–5、Table 1–6、Algorithm 1、Eq.(1)–(12)与全部提示词/案例框的定位表。小字表值和框中文字同时使用原PDF文本核对，没有仅凭低分辨率目测构造高精度数据。

## 3. 数值与公式自查

### 3.1 通过的核对

Table 1/2 的所有Pass@1与差值已检查：tb-core 40.0→49.2（+9.2 pp，较Evol +2.4）；tb-2.0 23.0→29.4（+6.4，较Self +2.1）；SWE-bench Verified 73.4→77.1（+3.7，较Evol +1.3）。Table 2(b) 的四档增益为6.8/7.2/8.1/9.2 pp，没有写成所有规模均完整比较三基准。

Eq.(1)的increase=-0.25、reduce=+0.25、diversify=0、depth=1、breadth=0.65；Eq.(2)的tau=0.5、sigma=0.2；Eq.(3)的epsilon=1e-6、lambda=0.25；slack上界0.2；Eq.(4)至Eq.(12)的变量与约束均核对。手工/脚本算术例0.747→0.497→F≈0.9999、0/1→0.25/0.75→F≈0.4578与原文一致。

Case V显示p_hat=0.533、F=0.9862，可能由未显示精度造成；不能据显示值直接制造一个新的确定错误，更不能由小数反推prober的具体rollout数。

### 3.2 实际发现的三个关键问题

**Q1：成本分项不闭合。** p.7 Table 1中FORGE prompt=1,862,146，final completion=618,910，二者相加2,481,056，原表total却是2,881,056，差400,000。前三方法分项闭合。Fig.3(b)保留约1.86M+0.62M的分块和2.881M总量文字；p.8 Table 3的28,811/9,901来自reported total而非独立账本。正文保留全部原值，没有擅自改总数或虚构额外成本类别。

**Q2：响应长度冲突。** A.4 p.13明确写1024-token response cap；D p.19明确写max prompt与max response均8192。原PDF目视确认两处文字。正文并列，不自行解释为per-turn/trajectory、train/eval或历史/新版。

**Q3：PGN案例的动作语义风险。** A.5/Fig.5称diversify-breadth保持难度；C.3 p.19却从多PGN、多种错误、战术分析和FEN/mate-in-N，变成一局一个错误，且明示15.Kf9应改15.Kf1。正文保留仍有合法性验证/结构化输出的工作，不将其夸大为完全无任务；但明确它不能证实难度保持，更不能将预测0.533当生成后实测。

### 3.3 另外两项未闭合的解释边界

**Q4：per-seed与active coverage。** 原文既称逐seed求解/portfolio可选，也写active slack和一个600-primary-variable记录。N=100=seed count只约束每seed选一个，不能证明无跨seed耦合。缺原始m_v、slack与装配日志，正文不自行归并。

**Q5：图示反馈与实测闭环。** Fig.2有policy update及gold失败反馈；Algorithm 1没有完整repair/reprojection循环；§4.1说持续生成修复直至100接受。正文记录可支持的离线policy-relative构造与合成期重试，不将图升级为训练期周期重估的在线课程结果。

## 4. 此前结论如何修订

| 原状态/表述 | 本次处理 |
| --- | --- |
| 全文未取得 | 改为2026-09-07历史状态；当前全文、附录、图表均已读 |
| 只有摘要支持100环境及结果 | 已由Table 1/2、正文与附录确认 |
| 正式标题不确定 | 用v1首页标题；旧别名不作正式标题 |
| 1,824及另一组模型 | 本v1无相应支持，不当作不同版本或不同分母自动调和 |
| 1,024单响应可直接进入配方 | 增补D的8,192冲突；保留待实际配置核查 |
| portfolio未测，所以本实验无coverage | 不采用这种简化；保留active slack原文与装配未知 |
| 每种动作必改Docker | 按C.2修正：increase/diversify的ENV可选，reduce必改 |
| preflight重建全部容器 | 原文为加载全部任务、构建代表性容器；不扩大检查覆盖 |
| reward=1说明位于学习前沿 | 拆为seed policy reward、predicted difficulty、oracle gold reward |
| 示例accepted不是gold，故论文链路存疑 | 前半为固定代码事实；后半不能据此推出。PDF独立说明作者gold链 |
| messages/tools格式即可视为真实训练轨迹 | 保留旧代码结论：模板导出与目标policy rollout不同 |

## 5. 代码附查范围

沿用上一轮固定提交`DataArcTech/DataArc-SynData-Toolkit@2a1d65ec8dcfaea2458d67e1fb18078cce6420b9`的阅读记录。本轮重新读取`terminal_bench.py:110–250`与`:340–435`，核对generation→static_validate→matched→accepted及模板messages导出；blob仍为`d1c1c461cfaba1a5210e30cbc356a2011c95fddf`。

完整sidecar文档、入口、配置、Harbor helper/smoke与canary处理的全文件检查来自上一轮，不谎称本轮再次逐行审计全文件。原文与固定代码分节，没有把该分支等同论文历史实验实现；没有声称对所有分支搜索完毕。

reward从共享jobs目录按mtime读取的风险仍保留触发条件；未做运行复现。Harbor smoke默认agent执行也不自动等于oracle执行；正文已补该限定。

## 6. 本轮完成与未完成的工作

完成的是原文通读、页面视觉核对、公式解释、表值转录及读者算术、旧结论修订、限定代码数据流复读、Markdown引用/锚点检查。reader arithmetic不是SCIP、Docker、Harbor或GRPO复现。

未执行环境构建、oracle验证、目标policy probing、求解器最优性重放、真实训练或评测；未取得完整实验revision、100-task manifests、run configs、token账本和逐任务日志。未给结果置信区间或独立复现标签；也未把未取得的日志说成作者从未公开。

没有独立reviewer。本轮状态是“作者已完成全文精读和自查，待独立审查”，不是“Codex已经审核通过新稿”。

## 7. 建议独立复核优先位置

优先回到PDF p.7的Table 1/Fig.3(b)、p.13 A.4、p.19 D，以及p.14/15与p.19 Case V的对照。然后复核per-seed与active coverage的措辞、ENVs必改/可选mask、代表性preflight、reward中无KL与loss中无KL的区分。以上已给出可定位原文；不需要用户再重复上传同一PDF。

若进一步复现，应索取token/attempt账本、实际配置、seed/probe/accepted manifests、solver trace、gold与eval日志。这是后续复现需求，不是当前精读未完成。

## 8. 写入范围与历史保存

仅更新本线程的`reading_notes/E3_envs_forge.md`与本文件。README、SOURCE_CATALOG、共享进度、knowledge旧稿、原始PDF、其他线程正文和训练代码均不修改。保存前读取最新远程文件SHA；最终commit与回读结果在交付回复中报告。

本地另存算术检查和供本地Codex使用的变更补丁；这些不扩大远程写入范围。下方历史块内容逐字保留，hash对应本次读取的旧自查blob。

---

<details>
<summary>2026-09-07 历史记录原文（不是当前状态）</summary>

# E3 Envs-FORGE：本轮作者自查与续读记录

日期：2026-09-07。对应文档：[E3_envs_forge.md](../E3_envs_forge.md)。

**本轮交付是来源核验和定点代码检查，不是全文精读完成。没有独立 reviewer，没有执行论文或代码实验。**

## 1. 使用了 Codex 的哪些反馈

依据 [O01 质量反馈](15_O01_codex_quality_review_20260907.md)：优先追实际入口和数据去向，不凭功能说明推断闭环；保留图表条件与量级；一手、现代代码、读者推论分层；只写本线程的正文与检查记录。

本次原文不可读，图表检查无法完成，因此不能继承 O01 的全文覆盖状态。也不写“作者未披露公式/资源”来掩盖本轮未读正文。

## 2. 已完成的检查

- 读取项目的质量反馈、笔记规范、E3 来源登记，以及 `knowledge/summary_envs_forge_synthesis_policy.md`；旧稿只作核验清单。
- 检索到 arXiv 当前摘要与文献信息，记录当前 100 个验证环境的口径；历史会话的 1,824 数字不直接进入事实表。
- 确认仓库原始 PDF 的路径与 blob；没有取得可阅读字节，未声称看过封面、页数、附录或图表。
- 读取关联仓库 `SynAgenticData@2a1d65ec8dcfaea2458d67e1fb18078cce6420b9` 的完整 sidecar 文档、terminal 合成模块、两份实际入口与 YAML。没有把该分支自动等同论文正式 release。
- 沿真实数据流追到 static validation → accepted → manifest/messages 导出，并核查独立 Harbor smoke 是否回写；实际没有把执行结果自动闭合到主导出链。
- 检查 reward 文件选择和 canary 处理的边界；只给带触发条件的静态风险，没有标为复现漏洞。
- 算术检查名义 demo 候选数：三个 seed ×（few-shot 一条 + self-instruct 一条 + Evol 两方向）=12；不作为论文任务量。

## 3. 访问阻塞记录

| 路径 | 实际结果 | 结论 |
| --- | --- | --- |
| arXiv abs 检索 | 取得完整摘要 | 可报告摘要级声明，不能恢复实验全文 |
| arXiv PDF/HTML/TeX 正常入口 | cache miss 或不可访问 | 没有全文、截图或 TeX 可供本轮检查 |
| GitHub PDF 文本／blob | 空内容或二进制 UTF-8 解码限制 | 路径存在不等于字节已读取 |
| 连接器文件物化 | 无可用 materializer | 没有生成本地 PDF |
| 容器直连与下载 | 网络／代理失败 | 不能进行本地 PDF 提取和渲染 |
| reading_notes/sources | 本轮目录中未找到 E3 来源副本 | 不能借用其他篇来源目录补本篇 |

这些是本线程的访问结果，不是论文撤稿、作者未公开或仓库缺文件的证据。部分二手网站有长摘要，但没有拿它们填正文、公式和实验表。

## 4. 特别防止的误写

| 误写 | 本稿处理 |
| --- | --- |
| 新旧标题不同必然说明新版论文 | 保留差异，待封面／版本历史核验 |
| 100 个与历史 1,824 是同一实验的不同分母 | 没有原文关系，不能自行合并 |
| 旧稿注明“依据 TeX”就等于本轮精读原文 | 只将其作为待核验提纲 |
| official repo 有 GRPO 就是论文的 RL 配方 | 不从通用训练入口补论文算法 |
| `accepted` 代表 gold-verified | 当前示例只来自静态检查，单独标注 |
| 生成了 tool-call JSONL 就执行了工具并收集真实轨迹 | 当前是模板构造行，不是主合成入口真实 rollout |
| 局部入口没调用 MILP就证明整个项目没发布 | 只描述所检查文件／分支的边界 |
| 缺 PDF 仍标“全文完成，待补截图” | 明确全文精读未完成，不改共享完成数 |

## 5. 下一次续读所需材料及顺序

最直接的原始输入是 `docs/harness_improve/external_paper_references/pdfs/E3_envs_forge_2608.14312.pdf` 的实际会话上传，或同版本完整 TeX/HTML 和图资源。

取得后先核封面、版本、目录、页数和主实验表，解决历史口径差异；再通读方法、全部训练／评测章节和附录，逐图表目视核验，并补齐正文 §5 的问题。最后才判断当前关联代码与论文的关系，修订此稿状态。

## 6. 保存范围

本轮仅创建 `E3_envs_forge.md` 与本文件；不改 README、SOURCE_CATALOG、其他线程文件、历史笔记、原始 PDF、训练实现或项目定案。提交结果与回读情况由交付回复说明。

</details>
