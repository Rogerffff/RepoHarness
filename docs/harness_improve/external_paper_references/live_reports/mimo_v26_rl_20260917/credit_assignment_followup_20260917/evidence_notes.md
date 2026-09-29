# 来源、核对范围与限制

日期：2026-09-17。作者：Codex。以下为本轮作者自查记录，没有独立审稿、训练复现或代码运行结果。

## 保存范围

- `sources/manifest.json`：12 篇主检索论文的原始 HTML、版本、抓取时间、SHA-256；同名 `.txt` 是便于阅读的派生文本。
- `sources/supplement_manifest.json`：SWE-RM、RLAnything 的补充 HTML，以及最初 GitHub API 403 的尝试记录；403 未被当作仓库不存在。
- `sources/code_manifest.json`：随后通过公开 Git HEAD 和 immutable raw URL 取得的 4 份实现资料，含 commit 与 SHA-256。
- `sources/tex_manifest.json`：从 arXiv export e-print 获取的 11 篇论文的 73 份 TeX。保存所有相关源文件不等于声称逐字审计了每份表格或提示词。
- `verification.json`：本轮文件摘要、报告相对链接、引用数字及说明性算例的检查结果。它验证整理过程，不验证作者的实验可复现性。

首选 arXiv `/src/` 请求返回 406，使用同版本 `https://export.arxiv.org/e-print/<id>` 取得源文件；没有用不同版本静默替代。下载的源码只用于阅读，没有执行其训练或安装命令。

## 论文检查清单

| 论文 / 固定版本 | 本轮主要核对内容 | 保存位置 |
| --- | --- | --- |
| [SWE-RM / 2512.21919v1](https://arxiv.org/html/2512.21919v1) | §3、§5、附录 E，混合奖励、GSPO/组 advantage、51.8/54.8、概率校准与 TTS 区别；非 SWE 迁移表 | `sources/swe_rm.*`；`sources/tex/swe_rm/Sections/5_rl_experiments.tex`、`iclr2026_conference.tex` |
| [SWE-TRACE / 2604.14820v1](https://arxiv.org/html/2604.14820v1) | rubric 与 PRM 训练；completed-trajectory score；γ margin；GRPO；同 SFT 起点的 RL 消融；crucial steps 只用于 memory | `sources/swe_trace.*`；`sources/tex/swe_trace/main.tex` |
| [Agentic Rubrics / 2601.04171v1](https://arxiv.org/html/2601.04171v1) | rubric repo 探索、judge 输入、实验评价口径；确认属于 inference-time verification | `sources/agentic_rubrics.*`；`sources/tex/agentic_rubrics/` |
| [DRACO / 2609.04094v1](https://arxiv.org/html/2609.04094v1) | 方法、设置、结果与标准差表、judge 成本、credit 附录、归因 prompt 与组等待；对照源码确认 hook 顺序 | `sources/draco.*`；`sources/tex/draco/sections/`、`tables/`；3 份 `draco_*` 实现文件 |
| [IAPO / 2608.24588v1](https://arxiv.org/html/2608.24588v1) | support/failed-use 图、正负分支、token 长度加权守恒、领域/标注模型、主要消融 | `sources/iapo.*`；`sources/tex/iapo/iapo_arxiv.tex` |
| [OAR / 2601.07408v1](https://arxiv.org/html/2601.07408v1) | 扰动/梯度两个重要性估计、sum-preserving 权重、数学任务与额外计算 | `sources/oar.*`；`sources/tex/oar/latex/OAR.tex` |
| [PaTR / 2607.15610v1](https://arxiv.org/html/2607.15610v1) | judge/PRM 决定树扩展，仍用 outcome RL；SWE 表、随机树对照、模型/预算 | `sources/patr.*`；`sources/tex/patr/` |
| [OpenClaw-RL / 2603.10165v1](https://arxiv.org/html/2603.10165v1) | 环境过程评分与 OPD 的区别；SWE 数据、曲线、reward ablation 的实验领域；SWE 可选 PRM 接口 | `sources/openclaw_rl.*`；`sources/tex/openclaw_rl/main.tex`；`sources/openclaw_README.md` |
| [TRIAGE / 2606.32017v1](https://arxiv.org/html/2606.32017v1) | role 标签、加性 advantage、随后 whitening、任务和 judge；没有 SWE 实验 | `sources/triage.*`；`sources/tex/triage/main.tex` |
| [AEM / 2605.00425v1](https://arxiv.org/html/2605.00425v1) | response 熵权重、SWE 消融、profiling 范围 | `sources/aem.*`；`sources/tex/aem/neurips_2026.tex` |
| [RTMC / 2604.11037v1](https://arxiv.org/html/2604.11037v1) | 状态/动作签名、经验 Q/V、prior、小访问量；SWE 表与评测口径 | `sources/rtmc.*`；`sources/tex/rtmc/main.tex` |
| [SWE-Shepherd / 2604.10493v1](https://arxiv.org/html/2604.10493v1) | HTML 筛选方法与实验性质；未建立 ADV 训练消融证据 | `sources/swe_shepherd.*` |
| [HCAPO / 2603.08754v1](https://arxiv.org/html/2603.08754v1) | HTML 筛选方法与评测领域；仅作非 SWE 旁证 | `sources/hcapo.*` |
| [RLAnything / 2602.02488v1](https://arxiv.org/html/2602.02488v1) | HTML 筛选 coding 任务与 agent 任务；不能将函数级 coding 结果写成 repo 级 SWE | `sources/rlanything.*` |

## 实现核对

**DRACO 固定 commit：`cfafd0f81f2c49aa36a4b25a2a7b6ac6e119f47b`。**

- `training/src/verl_appworld/credit_advantage_patch.py`：`install_credit_masking_hook` 先调用原始 `compute_advantage`，再调用改写函数；`_reallocate_advantages_for_sample` 有正负分支、按步骤长度分摊、gap 置零及无效信息回退。
- `training/src/verl_appworld/credit_assignment.py`：核对步骤质量及 token 映射相关函数；没有运行 tokenizer 或训练代码。
- `training/docs/CREDIT.md`：说明 rubric union/dropout 的组等待，no-citation 等 fallback。其 “gradient mass” 用语须受论文附录的限制：不是参数梯度向量守恒。
- 文档/代码的默认 reward scale 与论文简写不完全相同；没有把“代码存在”升级为“完全复现论文配置”。

**OpenClaw-RL 固定 commit：`f48ac358adf9873b5cb2210f1cb234a52ed8a8a3`。**

- `swe-rl/README.md` 明确包含 `swe_prm.py` 可选组件和带 PRM 的训练脚本。
- 这里只核对了接线说明，没有据此断言所有默认 SWE 运行都启用了 PRM，也没有审计该仓库所有 reward-to-advantage 路径。

## 最容易被夸大的结论

| 说法 | 本轮核对后的修正 |
| --- | --- |
| MiMo 确定在单条 rollout 内做动作级 credit | 已有 advantage 行重写记录，但行内位置差异、顺序、公式仍未公开 |
| SWE-TRACE 的 process reward 是逐步骤数值奖励 | 方法明确给完成轨迹一个标量；关键步骤索引服务 memory |
| DRACO / IAPO 已证明 SWE 有效 | 两篇的相关实验不是 repo 修复 |
| PaTR 的 +5 分来自 LLM judge 改 ADV | +5 是 PRM 树对平坦 GRPO；judge 树对随机树 +1.2，而且改的是采样 |
| OpenClaw 的过程奖励消融就是 SWE 消融 | 对应消融域是 GUI/tool-call；SWE 训练曲线不等于 held-out 因果对照 |
| AEM 在 SWE 只增 1.1% 成本 | 该 profiling 是另一领域的小模型设置 |
| 冻结模型只做推理，所以 judge 一定便宜 | 多轮长输入、重复判断和组同步均有成本；缺少同预算 critic 比较 |
| 保持 advantage 总和等于保持梯度或无偏 | 各 token 的梯度不同，且 loss mask / DIS / clipping 会改变有效权重 |
| 小 judge reward 系数一定是小干预 | 同结果组的标准化可能消掉公共正比例系数 |

IAPO v1 特别限制：正文指向若干附录，但本次 HTML 与源码包未包含相应完整附录内容。只能报告已取得的方法与表格，不能宣称附录成本和误差审计已核实。

数值均从作者表格/正文或冻结 MiMo JSON 对应目录取值，没有从曲线截图猜读。报告中的两个动作、group scaling 与 mask 守恒算例是自行构造的解释，不是论文或 MiMo 实验。
