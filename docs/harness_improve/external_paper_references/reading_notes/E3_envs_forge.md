# E3 Envs-FORGE：基于策略通过率选择环境合成动作

**正式标题：Envs-FORGE: Frontier-Optimized Reward-Grounded Environment Synthesis for Agent RL**  
**版本：arXiv:2608.14312v1，2026-08-14，19 页。**  
**2026-09-08 修订｜正文与 A–D 全部附录已读；PDF 19 页均已目视检查；作者自查完成，待独立审查。未执行环境、求解器或 RL 复现。**

> 2026-09-07 的版本只完成了来源对账和关联代码静态检查，没有取得可读全文。用户于本轮上传 PDF 后，该访问阻塞已经解除。本稿以附件原文重写；不将此前访问失败继续列为当前限制，也不倒改历史操作记录。完整历史见[自查与修订记录](reviews/E3_envs_forge_self_check_20260907.md)。

这篇论文的核心不是新 RL loss，而是**先决定一个 seed 应当变难、变易还是变换实例，再生成完整可执行任务**。作者报告，在每方法恰好导出 100 个 gold-verified 环境的条件下，该整套合成策略优于三种固定 prompting 配方。但这不能进一步证明 MILP 本身带来了独立收益、生成后的任务确实达到预测通过率，或训练过程中运行了持续重估的在线课程。

全文核对后有三处必须保留的具体问题：**Table 1 的 Envs-FORGE token 分项与总数相差 400,000；A.4 与 D 的 response cap 分别写 1,024 和 8,192；Case V 的“保持难度的多样化”描述，与附录中实际收窄任务并直给修正着法的指令存在张力。** 下文并列保存原文，不替作者选择正确版本。

导航：[来源与覆盖](#sources) · [问题与定位](#problem) · [方法与公式](#method) · [工件与提示词](#artifacts) · [训练配方](#training) · [实验与成本](#experiments) · [五个案例](#cases) · [求解器细节](#solver) · [图表检查](#figures) · [代码边界](#code) · [证据缺口](#gaps) · [项目意义](#project)

<a id="sources"></a>
## 1. 来源身份、版本与阅读覆盖

### 1.1 主来源

主来源是用户实际上传的 `E3_envs_forge_2608.14312.pdf`，不是模型摘要或网页转述。首页标题、作者、机构与页边版本标识均已核对：Xiaojun Wu、Cehao Yang、Honghao Liu、Xueyuan Lin、Zhichao Shi、Hao Zhou、Xuhui Jiang、Chengjin Xu、Jia Li、Jian Guo；机构包括 IDEA Research、HKUST (Guangzhou)、DataArcTech。[P01]

| 身份项 | 本轮记录 |
| --- | --- |
| 原始来源 | [arXiv v1][P]；本轮阅读以附件 PDF 为准 |
| 页码 | 文件第 1–19 页，与印刷页码一致 |
| 文件长度 | 2,228,591 bytes |
| SHA-256 | `b0e4dbd7bc35e5a1ad6362e4e4b8d0c51d42ee94780a641bae7bfdd8f473ace1` |
| 本地按 Git blob 算法计算的 SHA-1 | `e35ca77aab3738fe4a8732d19f28497540884214` |
| 与仓库资产的关系 | 上述 blob 与上一轮 GitHub 返回的仓库 PDF blob 一致；本轮没有另行声称完成网络下载后逐字节比较 |
| RepoHarness 原稿身份 | 本轮写入前远程正文 blob `ffbb563f5218114f731f6fe8540d544498d5118c`；与会话中的旧稿一致 |
| 关联代码边界 | `DataArcTech/DataArc-SynData-Toolkit@2a1d65ec8dcfaea2458d67e1fb18078cce6420b9`，上一轮读取的 `SynAgenticData` 分支快照；不是已证实的论文实验 revision |

本稿区分三类陈述：**论文报告**是作者原文的模型结果、配置与流程；**代码事实**只描述固定提交中实际检查的路径；**读者判断／计算**是本文的算术、逻辑限制和候选实验。不把三者互相升级。

### 1.2 按原文章节的覆盖

| 原文章节 | PDF 页 | 本稿位置与阅读内容 |
| --- | --- | --- |
| Abstract；§1 Introduction | 1–2 | §2：问题、贡献及比较单位 |
| §2 Related Work | 2 | §2：prompting policy 与环境生产基底的分层 |
| §3.1–3.3 | 3–5 | §3：五件套、六动作、Eq.(1)–(11)、技能与资格约束 |
| §3.4；Algorithm 1 | 5–6 | §4：物化、静态检查、oracle 验证；重试描述边界 |
| §3.5；§4.1 | 5–6 | §5：GRPO、统一训练／评测口径 |
| §4.2–4.5；§5 Conclusion | 6–8 | §6：全部结果、成本与消融边界 |
| Limitations；Ethical Considerations；AI 使用说明 | 9 | §11：作者限制、安全边界、声明不等于实验配置 |
| References | 10 | 已检查；未逐篇重读参考文献，不据引文补本篇参数 |
| Appendix A.1–A.2 | 11–13 | §3、§8：Eq.(12)、动作语义、技能 taxonomy 与 solver 边界 |
| Appendix A.3–A.4 | 11–13 | §4–5：同步、隔离、归一化、preflight、训练配置 |
| Appendix A.5 | 13–15 | §7：五个案例及与 C.3 的逐项对照 |
| Appendix B | 15–16 | §8：PySCIPOpt/SCIP、组装、branch-and-cut、日志与 fallback |
| Appendix C.1–C.3 | 16–19 | §4、§7：全部策略、repair、payload、mask、skill contract 与五组指令框 |
| Appendix D | 19 | §5：资源、batch、超时、学习率、checkpoint、长度冲突 |

视觉检查覆盖 Figure 1–5、Table 1–6、Algorithm 1、Eq.(1)–(12)，以及 C 中全部七个方法／提示词框和五个案例框。文字提取仅辅助定位；表格列值、公式、框中文字与箭头均回到页面图像确认。

### 1.3 历史口径如何修订

本 v1 的正式标题如本文首屏；旧稿中的 *Frontier-Aware Environment Synthesis for Terminal Agents* 不作为正式标题。原文主实验支持的是 **100 个接受环境、Qwen 3.5 35B、40.0→49.2**，不支持历史会话中的 **1,824 个任务、Qwen3-Coder/Ling 等另一组模型结果**。[P01][P07]

因此，1,824 等数字不进入本篇事实表；也没有证据把它们解释成另一版或另一个分母。`knowledge/` 旧摘要只作历史核对来源。它记录的主要结果与本 v1 相符，但单列 1,024 response cap 不足以反映附录 D 的另一处披露。[OLD][P13][P19]

<a id="problem"></a>
## 2. §1–2：论文究竟在优化哪一层

终端 agent 的 RL 数据不是一批自然语言问题，而是带初始状态、依赖、可执行工具和判分逻辑的环境。作者认为，few-shot、Self-Instruct、Evol-Instruct 等固定配方的问题在于：它们预先指定如何改写 seed，却不消费当前 policy 在这个 seed 上的通过率。[P01][P02]

论文把两个决定拆开：首先判断任务相对当前策略处于什么区间，其次按选定动作生成环境。过易 seed 应增加可检验约束；当前无法解决的 seed 可以移除次要系统、形成 bridge task；已经接近前沿的 seed 则变换 fixture 或邻近要求，而不刻意大幅改变难度。[P03][P04]

Related Work 的重要分层是：CLI-Gym 的环境反演、SkillSynth 的技能图、TermiGen 的容器与错误注入、TerminalTraj 的仓库任务构建、Endless Terminals 的程序化生产、Agent-World 的任务发现，被作者视为可与多种 prompting policy 搭配的生产组件。本文选择**固定配方作为同层对照**，不是声称击败了上述各系统的完整生产流水线。这是作者的比较框架，不是本轮独立比较那些论文所得的结论。[P02]

因此，论文最直接的实验问题是：在共享生成与验证管线下，把固定策略句换成策略相对的动作选择及对应契约，是否改善合成数据的下游 RL 表现？它不是 token 级 action selection、trajectory rejection、训练调度器，亦未提出一个新的 GRPO 更新公式。

<a id="method"></a>
## 3. §3.1–3.3、A.1–A.2：从 seed reward 到六动作选择

### 3.1 任务对象与动作对象

一个 seed 为：

$$
s_i=(I_i,D_i,S_i,T_i,E_i),
$$

分别表示 instruction、fixtures/data、oracle solution、tests、executable environment。它们共同定义任务；只改 instruction 而不改 solution/tests，可能生成不可判分或语义不一致的样本。[P03]

动作是两个维度的笛卡尔积：

$$
\mathcal A=\{\mathrm{increase},\mathrm{reduce},\mathrm{diversify}\},\qquad
\mathcal D=\{\mathrm{in\_depth},\mathrm{in\_breadth}\}.
$$

projection 指难度应向哪里移动，direction 指沿原技能链深入还是向相邻技能／任务类型变化。每 seed 的六个候选是**生成前的动作契约**，不是已经生成好并实际测过通过率的六个环境。[P03][P11][P15]

### 3.2 三种容易混淆的 reward／通过率

先对当前策略在原 seed 上的 verifier reward 求均值：

$$
\hat p_i=\frac{1}{n_i}\sum_{t=1}^{n_i}r_{i,t},\qquad r_{i,t}\in[0,1].
$$

二元 reward 时，这是经验成功率；若使用 partial reward，则是平均 reward，不能不加限定地当作严格成功事件的概率。原文未给出足够信息恢复所有 seed 的 `n_i` 和 probing 采样协议。[P03]

生成前用固定 transfer prior 预测动作效果，原文 Eq.(1)：

$$
\tilde p_{i,a,d}=\operatorname{clip}(\hat p_i+\Delta_a\gamma_d,0,1).
$$

| 动作因素 | 原文数值 | 含义 |
| --- | --- | --- |
| increase | $\Delta=-0.25$ | 预期降低策略通过率，即加难 |
| reduce | $\Delta=+0.25$ | 预期提高通过率，即降难 |
| diversify | $\Delta=0$ | 预期保持难度 |
| in_depth | $\gamma=1$ | 使用完整偏移 |
| in_breadth | $\gamma=0.65$ | 偏移减弱，increase/reduce 幅度为 0.1625 |

原文明确说这些数是**生成前排序先验，不是生成后成功率变化的经验定律**。再用 Eq.(2) 计算前沿分数：[P03][P04]

$$
F_{i,a,d}=\exp\!\left[-\frac{(\tilde p_{i,a,d}-\tau)^2}{2\sigma^2}\right],
\qquad \tau=0.5,\ \sigma=0.2.
$$

必须分开：`seed policy reward → p_hat`、`启发式预测 → p_tilde/F`、`oracle 执行 → gold reward`。最后一项的 reward=1 不能证明目标 policy 有约 50% 通过率。原文 A.3 也明确区分 gold consistency 与 policy difficulty。[P12]

**读者算术例子。** $\hat p=0.747$ 选 increase-depth 后预测 0.497，$F\approx0.9999$；$\hat p=0$ 选 reduce-depth 后预测 0.25，$F\approx0.4578$。后者已经是该简单候选集向目标 0.5 移动的方式之一，但并未达到 0.5。论文 Figure 5 的相应数值一致。[P14]

### 3.3 MILP 的变量、目标与约束

动作变量 $x_{i,a,d}\in\{0,1\}$，技能激活变量 $u_{i,a,d,v}\in\{0,1\}$。每候选有 required skills $R$ 与 optional skills $O$；启用覆盖目标时，$m_v$ 是目标，$\xi_v$ 是缺口。[P04][P05]

Eq.(3) 为：

$$
\max_{x,u,\xi}\sum_{i,a,d}x_{i,a,d}F_{i,a,d}
-\epsilon\sum_{i,a,d}\sum_{v\in O_{i,a,d}}u_{i,a,d,v}
-\lambda\sum_v\xi_v,
$$

其中 $\epsilon=10^{-6}$、$\lambda=0.25$，启用的 slack 上界为 $\bar\xi=0.2$。候选分数与 metadata 都先计算，故这个目标对决策变量是线性的；指数函数并不在 solver 内优化。

Eq.(4)–(10) 分别规定：

$$
\sum_{a,d}x_{i,a,d}\le1\ (\forall i),\qquad
\sum_{i,a,d}x_{i,a,d}=N,
$$
$$
u_{i,a,d,v}=x_{i,a,d}\ (v\in R),\qquad
u_{i,a,d,v}\le x_{i,a,d}\ (v\in O),
$$
$$
u_{i,a,d,v}=0\ (v\notin R\cup O),\qquad
\sum_{i,a,d}u_{i,a,d,v}+\xi_v\ge m_v,\qquad
0\le\xi_v\le\bar\xi.
$$

本轮公式中的 `u` 均指 skill activation，不是生成文本中的操作。每 seed 至多一个，加上 $N=|S|$ 才推出每 seed 恰好一个；若可行候选为空，不能靠总数约束保证成功生成。候选 eligibility、overlap risk、prompt budget 可直接预过滤，也可写为 $x\le v$、$x\le1-\ell$、$p_{i,a,d}x\le P_{\max}$。这里小写 $p_{i,a,d}$ 是原文的 **prompt length**，不是通过率。[P05]

Table 5 的技能词表包括 domain（如 system_admin、data_processing）、tool（bash、python、systemd 等）、artifact（logs/csv/json 等）、operation（parse/repair/rank/validate 等）、constraint（concurrency/scheduling/atomicity），以及 edge_cases、structured_output、deterministic_fixture 等新增节点。它们是动作契约 metadata，不能把一个 skill tag 激活理解为已通过独立技能评测。[P12]

**重要边界。** artifact edit mask 在 solver 外，由选定动作确定后交给生成器。MILP 不会读取并证明任意 Dockerfile、测试和 oracle 的语义正确性；这依赖后续物化与验证。[P11]

### 3.4 固定基线的 mask 是近似语义，而非实现等价

Eq.(11) 给 baseline 添加 $x_{i,a,d}\le\rho_{b,a,d}$；A.1 的 Eq.(12) 定义由此得到的受限可行域。few-shot 近似为 diversify-depth，Self-Instruct 近似为 diversify-breadth；Evol depth/breadth 固定 direction。[P05][P11][P12]

但 C.1 的实际 baseline prompts 仍各有语义：few-shot 是近邻变体，Self-Instruct 是同域新任务，Evol-depth 明确增加约束，Evol-breadth 扩展邻近题型。原文特别强调“近似对应”，不是说运行相同 solver 加一个 mask 就逐字复现原始 baseline 生成分布。正文的三类固定方法中，Evol 的两个方向在实验里合并为一个训练条件。[P06][P17]

### 3.5 per-seed 与 coverage 的边界没有完全讲透

§3.3、A.2 与 Limitations 均把本次实验称为 per-seed MILP，而共享 portfolio quota 是可选模式；但同文又反复说实验存在 active coverage slack，B 给出 100 seeds、600 primary variables、一个 objective=49.9104 的序列化记录。[P05][P09][P11][P16]

准确表述应保留两点：**作者报告每 seed 选一个动作；portfolio 的独立实验未做。** 不能自行改成“本实验完全没有 coverage”，也不能改成“已经验证了全局课程优化”。原文未展示足够的原始 $m_v$、每项 slack、装配与求解日志，无法独立还原这些覆盖项究竟如何与逐 seed 求解协作。

**读者判断。** $N=|S|$ 只保证每 seed 一个，并不自动消除共享覆盖约束对动作选择的耦合。按 Eq.(9) 左侧的计数形式，0.2 也不能直接翻译成“20% 技能覆盖容差”，除非另有归一化定义。

### 3.6 不把框架闭环图当作在线课程实验

§3.2 写明 `p_hat` 在候选构造前计算、在 optimization 期间保持不变。Figure 2 画出 RL update 回到 current agent，也画出 gold 失败后换 projection 的反馈，但 Algorithm 1 只展示逐 seed 选择、物化、验证、接受的一轮流程。§4.1 另说生成、repair、verification 持续到接受 100 个。[P03][P04][P06]

因此，论文支持**合成前使用当前策略画像**，也描述合成期重试；没有披露足以重放的训练中周期性重估、重合成 schedule。不能仅凭 Figure 2 宣称已实证完成“policy 与环境持续共同演化”的在线 curriculum。失败重试究竟是否重新 probing、重解 MILP、换 projection，以及每 seed 的重试上限，仍需运行配置和日志。

<a id="artifacts"></a>
## 4. §3.4、A.3、C.1–C.2：选择之后如何生成可判分环境

### 4.1 五件套同步不是所有文件都必须每次改写

论文要求完整任务契约一致：新增要求必须进入 instruction 并由 tests 覆盖；移除要求应从 oracle 与 tests 同时移除；fixtures 和运行环境必须支持这些行为。容器可以包含 task fixtures，不能向 agent 打包 oracle solution 或 hidden tests。[P05][P12]

C.2 把这一要求细化为以下 **artifact edit masks**：[P17]

| projection | mandatory edit | optional edit | 主要操作 |
| --- | --- | --- | --- |
| increase_complexity | INST、DATA、SOL、TEST | ENV、HELP | 增加具体约束／边界条件、调整 fixture、算法与确定性测试 |
| reduce_complexity | INST、DATA、SOL、TEST、ENV | HELP | 剥离次要系统，以确定性 fixture 替代 live dependency，并简化运行环境 |
| diversify_frontier | INST、DATA、SOL、TEST | ENV、HELP | 在相近规模下换实例、更新预期逻辑，保持 verifier 粒度 |

所以“五件套联合维护”不应误写成每种动作都强制编辑 Docker。环境对 increase/diversify 是可选修改，对 reduce 则是必改项。

### 4.2 共享生成契约与基线注入

C.1 的 shared template 要求一个完整 JSON，顶层为 `task_name / instruction_md / files / metadata`；同步 instruction、oracle、test runner、verifier、环境和改变的 helper/fixture。运行时需固定、build context 有效、依赖命令存在。阈值、tie-break、文件名、输出 key、fixture 条件等可评分要求必须明示；test runner 成败都写 reward，不能在底层测试失败后不产 reward。[P16]

few-shot／Self-Instruct／Evol-depth／Evol-breadth 的区别由策略与 direction 注入；后缀还有 sample index、合成模型、seed 名称和截短的 seed 文件。论文并未在这些摘录中给出完整 seed 文件包或所有 provider 配置。[P16][P17]

repair prompt 要求返回完整 JSON 而非 patch fragment，使顶层 `instruction_md` 与 instruction 文件去空白后一致；修复 build、静态检查或 oracle 失败，同时保留 baseline 策略。输入包括 failure summary、前一份 artifact、repair index 与 seed。**repair 不是把固定基线偷偷升级成 frontier selector**，也不是只改测试让它通过的许可。[P17]

### 4.3 FORGE 多注入了什么

FORGE 不只是把策略名换成一个整数。payload 带 seed pass rate/reward band、projection、evolution_direction、action_variant、projected pass rate、frontier score 和 target difficulty；然后给 projection 指令、direction 指令、edit mask 与 skill subgraph。[P17]

技能契约使用 `preserve_nodes / allowed_added_nodes / allowed_removed_nodes`。preserve 必须在指令与 verifier 中仍可观察；新增受允许集合约束；reduce 只有在核心仍可测试时才可移除或模拟指定节点。metadata 保存 solver payload 与 projection summary。[P18]

这说明真实干预同时包含**动作选择和更丰富的结构化生成条件**。没有隔离对照时，不能把最终收益全部归给 MILP 求解算法。

### 4.4 mental execution 与实际 gold execution 不能混同

C 中要求 LLM 在返回前“mental execution” build–solve–test，这只是生成提示。真正准入仍是 §3.4、Algorithm 1 和 A.3 的两层检查：先查 schema、路径、文件、长度、overlap、隔离与 reward 输出；再构建环境，运行 oracle 与生成测试，只有实际 reward=1 才入池。[P05][P06][P12][P16]

**读者判断。** gold-pass 提供“该 oracle 在该环境通过该测试”的正向证据，并不单独证明错误解会失败、所有正确替代解都会通过、测试不会被作弊、任务不会波动，也不保证其保留了原技能或适合目标 policy。原文没有报告 no-op、错误解、替代正确解或对抗攻击的完整通过／拒绝矩阵。不要把 gold-verified 扩大为已经完成全面 verifier qualification。

<a id="training"></a>
## 5. §3.5、A.4、D：下游训练配方与一个明确的长度冲突

### 5.1 任务归一化与 preflight

接受包转成统一 Terminal-Bench-style schema；验证 Docker spec、test entry point，统一 metadata，剔除非法文件工件。失败候选、repair attempts 和中间目录不进入最终 100 环境来源。prompt 长度使用**目标 tokenizer、真实 agent system prompt 与完整 chat template**计算，小模型档阈值 4,096，35B 档 8,192，过滤有记录，不静默截断。[P12][P13]

A.4 的 preflight 在 model workers 启动前加载全部归一化任务、重查 split/overlap、构建**代表性**容器并执行同一 oracle-plus-test 路径。这提供了一个避免基础设施错误消耗 rollout 预算的前置门。不能把“loads every task”改写成原文已经承诺“逐个重建所有容器并逐个再跑 oracle”；其容器措辞是 representative。[P13]

### 5.2 披露表：保留字段原义，不拼成伪精确复现配置

| 项目 | 论文披露 | 定位／限制 |
| --- | --- | --- |
| 主模型 | Qwen 3.5 35B | §3.5、§4.1；不能自行补成某个 `35B-A3B` checkpoint |
| 模型覆盖 | 4B、9B、27B、35B | Table 2(b)；较小模型不等于全部重跑三基准 |
| 算法 | GRPO，test-derived reward，无 learned reward model | §3.5、A.4；本文未给完整 policy loss／advantage 公式 |
| 每 prompt rollout | 8 | A.4、D；不是 seed profiling 的已知 `n_i` |
| 采样 | temperature=1.0，top-p=0.9 | A.4、D；不自动视为所有评测的已披露 sampling |
| response cap | **A.4：1,024；D：maximum response length=8,192** | **同文冲突，不能选择一个当唯一配置** |
| prompt cap | 小模型 4,096；35B 8,192；D 亦写 8,192 | A.4、D |
| trajectory | 至多 50 interaction steps；timeout=900 s | 步数见 A.4/D；时间见 D；与 token cap 分开 |
| batch | training batch、PPO mini-batch、per-GPU micro-batch 均写 1 | D；未说明全部字段在 prompt/group/trajectory 层的计数关系 |
| actor learning rate | `1e-6` | D |
| 训练长度 | one epoch | D；不能据此反推已实际执行的精确更新数和 token 总量 |
| reward weights | test=1，judge=0 | D |
| KL | reward 中不含 KL term | D；不等于已证明 policy loss 也无 KL 项 |
| checkpoint | automatic resume；每 step 保存；结束后只留 final actor weights | D；不代表本轮取得 checkpoints 或 resume 日志 |
| 训练 GPU | 2×H800 80 GB | A.4、D；actor/reference/rollout 共享可见 GPU |
| 分布式／内存 | FSDP2、gradient checkpointing、activation offload、FSDP offload | A.4、D |
| rollout engine | vLLM asynchronous generation；hybrid engine；TP=2 | A.4、D；不据“async”推定 fully-async learner 或跨版本 staleness |
| 精度与推理容量 | weights bf16；KV cache FP8；max model length、max batched tokens 均 32k | D；32k 不是另一种 trajectory token 总额 |
| 评测 GPU | 1×H800 80 GB | A.4、D |

原文 A.4 的 1,024 与 D 的 8,192 均已回看 PDF 页面，不是 extraction 错位。它们可能对应不同配置字段或不同阶段，但**原文未明确给出这种映射**，不能由读者自行解释为单轮／整轨迹、训练／评测或新旧设置。[P13][P19]

D 使用“PPO mini-batch”字段并不推翻正文 GRPO 命名；同样，存在 reference policy 不足以证明启用了某种 KL loss。应记录原文字段，等实验配置确定其真正消费位置。

### 5.3 尚不足以完成复现的参数

本文未提供足够信息恢复：精确模型 checkpoint、seed 完整清单及来源、prober 模型／budget／`n_i`、合成器完整模型配置、每方法最终任务 manifest、优化器完整 loss 和 masking、评测 harness revision、具体 task split、每任务运行次数、随机种子、infra failure 重跑政策及 wall-clock/GPU-hours/API 成本。附录 C 明说省略 package-manager/mirror fallbacks、重复 schema、task-specific paths 等，故它是核心提示词摘录，不是完整可运行脚本。[P16]

较小模型的任务来源是否重新按各自 policy 校准、各方法有效 rollout token 是否严格匹配，也没有足够的逐运行资产支持核对。上述属于**原文未充分披露**；作者可能有这些资产，不能据本文断言它们不存在。

<a id="experiments"></a>
## 6. §4：结果、实验单位与成本对账

### 6.1 比较单位

每种合成方法持续生成、repair、验证，直到导出恰好 100 个接受包；这些才是其下游 RL source。Records、task directories、attempts 是到达这个终点所消耗的生产工作，不是额外训练任务。Base 的原文定义是“不用合成训练数据”，不能扩写为“绝无任何既往后训练”。[P06][P07]

### 6.2 主结果与 benchmark 覆盖

以下原样保留 Table 1 与 Table 2(a) 的 Pass@1；不是本轮复跑结果。[P07][P08]

| 训练条件 | tb-core | tb-2.0 | SWE-bench Verified |
| --- | ---: | ---: | ---: |
| Base | 40.0% | 23.0% | 73.4% |
| few-shot | 43.2% | 24.1% | 74.6% |
| Self-Instruct | 45.6% | 27.3% | 75.2% |
| Evol-Instruct | 46.8% | 25.6% | 75.8% |
| Envs-FORGE | **49.2%** | **29.4%** | **77.1%** |
| FORGE − Base | +9.2 pp | +6.4 pp | +3.7 pp |
| FORGE − 最强固定配方 | +2.4 pp（Evol） | +2.1 pp（Self） | +1.3 pp（Evol） |

作者报告全部比较采用相同下游协议，这支持**整套合成策略条件下的结果比较**。但表与图没有置信区间或多独立训练种子的方差，因此不能将 1.3–2.4 pp 直接称为已验证的统计显著优势。SWE-bench Verified 的加入是另一 benchmark 上的结果，不等于已排除污染或已完成跨 harness 因果检验。

### 6.3 模型规模分析

Table 2(b) 仅报告 tb-core 上的 Base 与 FORGE：[P08]

| Qwen 3.5 模型标签 | Base | FORGE | 差值 |
| --- | ---: | ---: | ---: |
| 4B | 24.8% | 31.6% | +6.8 pp |
| 9B | 31.7% | 38.9% | +7.2 pp |
| 27B | 38.6% | 46.7% | +8.1 pp |
| 35B | 40.0% | 49.2% | +9.2 pp |

这是四档模型均改善的作者结果，不是四模型×全部合成方法×三个 benchmark 的完整矩阵，也不是独立团队复现。§4.3 虽称 Ablation Studies，实际主要扩展 benchmark/model coverage；没有拆出 selector、reduce、skill contract、gold verification 各自的独立贡献。

### 6.4 Table 1 的全部生产统计

| 方法 | Records | Accepted | Task dirs | Attempt sum | Prompt tokens | Final completion tokens | 原文 Total synthesis tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| few-shot | 121 | 100 | 210 | 226 | 1,835,473 | 607,592 | 2,443,065 |
| Self-Instruct | 113 | 100 | 194 | 190 | 1,745,028 | 527,247 | 2,272,275 |
| Evol-Instruct | 112 | 100 | 195 | 207 | 1,974,723 | 543,023 | 2,517,746 |
| Envs-FORGE | 120 | 100 | 203 | 291 | 1,862,146 | 618,910 | **2,881,056（分项不闭合）** |

数据来源：PDF p.7，Table 1；列名保留原文，不擅自把 Records 定义成唯一 seed 或尝试。[P07]

**读者逐行算术检查：**前三行的 prompt+completion 均等于 total；FORGE 行却是：

$$
1{,}862{,}146+618{,}910=2{,}481{,}056,
$$
$$
2{,}881{,}056-2{,}481{,}056=400{,}000.
$$

Figure 3(b) 的分块标注约 1.86M 与 0.62M，而柱顶文字仍为 2.881M／291 attempts。也就是说，不只是摘要的四舍五入问题；图表内部的总量口径也未完全闭合。[P07]

不能擅自把 400,000 解释成 probing、隐藏 reasoning、repair 或其他开销，也不能直接把 total 改成 2,481,056。可能有漏列或误填，但要由原始计数日志解释。这里保留作者所有原值，并将总量相关推导标为待核。

### 6.5 Table 3 的归一化成本及其依赖

| 方法 | Attempts / accepted | Tokens / accepted | Tokens / attempt |
| --- | ---: | ---: | ---: |
| few-shot | 2.26 | 24,431 | 10,810 |
| Self-Instruct | 1.90 | 22,723 | 11,959 |
| Evol-Instruct | 2.07 | 25,177 | 12,163 |
| Envs-FORGE | 2.91 | 28,811 | 9,901 |

这是 Table 3 原值。FORGE 的 28,811 与 9,901，分别与**原文 total 2,881,056** 除以 100 与 291 后取整相符；它们不是对该 total 的独立验证。分项不闭合的问题会传递到单位成本解释。[P08]

即便暂以原文 total 为准，FORGE 合成 token 也比 Self-Instruct 多约 **26.8%**，比 Evol 多约 **14.4%**，比 few-shot 多约 **17.9%**。这是读者计算，不是新实验。故作者的“same broad operational scale”应译成“同数量级、相近生产规模”，不能升级成“严格等合成 token／等费用”。更不能把“每次 attempt 平均 token 更少”直接等同“每个接受环境更便宜”。

固定的是**导出的环境数**；完整成本仍包括 seed probing、容器构建与验证、失败重试、模型训练与评测。本文没有足够的分项 CPU/GPU/API 计费账本来证明端到端等成本。

### 6.6 结果支持到哪里

论文报告了真实 GRPO 训练及整方法对照，可以作为作者报告的 T 级训练证据和完整策略的受控比较；但没有 solver-off、只加 reduce、同 payload 随机动作、transfer-prior sensitivity、独立 depth/breadth 等组件分析，作者在 §4.5 与 Limitations 也承认这一范围。[P08][P09]

因此最稳妥的结论是：**在所报告的模型、100 环境导出与共同下游协议下，FORGE 条件分数最高；其优势的精确机制、方差及完整成本仍需补证。** 不把复现披露不足或一处成本矛盾直接扩大为所有模型结果都无效。

<a id="cases"></a>
## 7. A.5、Figure 5、C.3：五个案例必须同时看“动作标签”和真实指令

### 7.1 全部案例的数值与改写

下表的 seed estimate、projected rate、frontier score 和 gold reward 均来自原文；projected 不等于生成后实测。[P13][P14][P15][P18][P19]

| 案例 | seed p_hat | 选定动作 | predicted p | F | 原文的主要改写 | 验证 |
| --- | ---: | --- | ---: | ---: | --- | --- |
| I Bash logs | 0.747 | increase-depth | 0.497 | 0.9999 | plain text → JSON 全局／目录汇总，明确空文件、无末尾换行、C locale、file lock、原子写入 | static pass，oracle=1 |
| II 多格式 merger | 1.000 | increase-depth | 0.750 | 0.4578 | 保留 CSV/JSONL/JSON email union，精确 header、缺失值空串、CSV quoting、排序 | 同上 |
| III systemd logs | 0.000 | reduce-depth | 0.250 | 0.4578 | systemd/rsyslog/logrotate live stack → 确定性 JSON 日志分析 | 同上 |
| IV token service | 0.000 | reduce-depth | 0.250 | 0.4578 | Java/Spring/H2/竞态处理 → 固定配置、事件、参考时间的文件级状态校验 | 同上 |
| V PGN | 0.533 | diversify-breadth | 0.533 | 0.9862 | 原文称保留棋谱修复技能并改变 fixture；实际范围差异见 §7.3 | 同上 |

### 7.2 前四个案例的真正能力变化

**Case I。** C.3 原始指令已经要求原子、可重启、确定性、重复／并发安全、每文件一次、特殊文件名处理。因此不能把所有这些属性都说成 FORGE 首次加入。最明确的变化是结构化 JSON 输出及更细的格式／边界条件；Figure 5 的概述不能替代原始—合成指令对照。[P18]

**Case II。** 原始题已经有唯一 email 的 union、三列 CSV 与 header；合成题强化精确 `email,phone,status`、缺失字段空串、逗号／引号／换行的标准 quoting 和排序。新增的是更精确的契约，不是从无到有加入多源 merge。[P18]

**Case III。** 从部署服务与日志流退到标准库处理固定日志：五分钟窗口内超过三次 restart、统计 warning/error、列出最近五条错误、标记坏 JSON／缺字段，空或不可读 fixture 不崩溃。保留日志推理，但不再训练 live service 安装、权限、routing、rotation 的端到端集成。[P18]

**Case IV。** 从 access/refresh/一次性 WebSocket token、原子更新、并发唯一成功、logout revocation 与清理，变成固定参考时间下判断 expiry/revocation/consumption、修复指定状态并按风险排序。它保留一部分安全状态推理，**不等于已经学会数据库并发或服务部署**。[P18]

两条 reduce 案例体现了有价值的 bridge 构造方向：把基础设施负担与目标推理技能拆开。但是否能由 bridge 学习迁移回原始复杂系统，本文没有给专门对照。`p_hat=0` 也只表示记录中的 rollout 未解出，不是不可解性的数学证明。

### 7.3 Case V：动作语义的关键反例风险

A.5 与 Figure 5 将 PGN 案例描述为 near-frontier、difficulty-preserving 的 breadth diversification。但 p.19 的 C.3 框给出：[P14][P15][P19]

| 原始 instruction 摘录的任务范围 | 合成 instruction 摘录的任务范围 |
| --- | --- |
| 多个损坏 PGN；非法、缺失、歧义着法；关键局面与战术模式 | 一个损坏棋局，恰好一个非法着法 |
| FEN puzzles，包括 mate-in-N，输出 puzzle continuations 与 aggregate analysis | 明示 `15. Kf9` 必须改成 `15. Kf1`，且没有其他错误 |
| 综合修复和棋题求解 | 用 python-chess 验证每步，保留 headers，输出原 PGN／修复 PGN／错误记录 |

**读者判断。** 附录摘录呈现的不只是换一个邻近 fixture：任务数量和子任务范围明显收窄，并直接提供了关键修正答案。后续仍有合法性检查、文件与结构化输出工作，因此不能断言任务完全无训练价值；但它不能单独作为“难度保持成功”的证据，更不支持生成后 policy pass rate 仍为 0.533。

这里的 0.533 不变是 `Delta_diversify=0` 带来的**预测值**。要验证动作是否真的落地，需要改写前后同 policy、同 harness、同预算的实际 rollout，以及对保留技能和答案线索的审查。此处是案例语义与学习价值风险，不等同于已经证实 benchmark 污染或论文全部样本都如此。

### 7.4 案例证据的共同上限

五例报告的 gold=1 验证内部可执行路径；没有展示这五个生成环境在目标 policy 下的实测成功率变化，也没有逐例验证其下游因果贡献。Figure 5 图注已将 selection/consistency traces 与 benchmark 效果分开，本稿保留这条边界。[P14]

<a id="solver"></a>
## 8. Appendix B：求解过程、fallback 与最优性的含义

### 8.1 作者描述的实现流程

模型接口为 PySCIPOpt，solver 为 SCIP。生成前计算分数、资格与技能集合；为 eligible candidate 建二元 `x`，在统一 candidate–skill index 上建 `u`，覆盖目标建 `xi`。required 等于 x、forbidden 固定零、optional 不超过 x；原文强调不用 big-M。许多变量是确定联动，presolve 可删除冗余。[P15]

B 将求解描述为 branch-and-cut：presolve／收紧域、LP relaxation 给 dual bound、对分数动作分支、添加有效 cuts、传播 bounds、primal heuristics 找可行解，直至 gap 闭合或返回其他终止状态。这里是作者对求解路径的说明，不是本轮运行 SCIP 得到的日志。[P16]

### 8.2 原文记录值与解码

作者报告记录包含 100 seeds×6 actions=600 primary action variables，target N=100，active slack cap=0.2，`status=optimal`，objective=**49.9104**。`x/u` 以 0.5 阈值解码；trace 记录 backend、formulation、status、objective、candidate/target count、coverage、realized slack、selected actions/skills。[P16]

49.9104 是 Eq.(3) 的优化目标值，不是 Pass@1、reward 或百分比。该描述也不等于本轮已取得可逐项复算的 machine-readable trace；论文未列出完整系数和解。

### 8.3 fallback 不应冒充 SCIP optimal

PySCIPOpt 不可用或 SCIP 非 optimal 时，候选列表不超过 24 条则尝试 exact enumeration；更大的实例用 deterministic coverage-aware greedy。选择项保留 backend label；作者声明主报告 trace 使用 PySCIPOpt，不是 fallback。[P16]

这意味着一个非 optimal 的 SCIP incumbent 不能自动当作论文主路径；fallback 后是否具有同样的可行性与最优性，应分别核对，不能仅因产出 action 就统称 MILP optimal。

### 8.4 为什么需要 solver-off 对照

**读者推导，不是论文消融。** 在没有跨 seed coupling、没有有效 coverage 要求、各动作 metadata 给定且 optional skills 可取零的简化条件下，每 seed 只需枚举最多六个可行动作并比较目标值。此时精确比较很便宜，MILP 的表达便利与其不可替代性是两回事。

此外，`diversify-depth` 与 `diversify-breadth` 的 Delta 都为零，单凭 frontier score 无法区别二者；需要 eligibility、技能约束、其他目标项或 tie-breaking。论文没有充分披露所有 tie 的处理。不能把每个 breadth 决定都解释成 reward 估计唯一推导的结果。

但由于原文又报告 active coverage，不能进一步声称“本文实际 MILP 已被证明完全等价于独立 argmax”。要回答这一点，需要精确构造的同候选、同约束 solver-off／enumeration 对照及原始装配数据。[P03][P05][P16]

<a id="figures"></a>
## 9. 全部图表与提示词框的目视检查记录

| 原文对象 | PDF 页 | 图表实际提供的证据与限制 |
| --- | --- | --- |
| Figure 1 | 3 | fixed recipe 与 probe/choose 示意，例 seed p=0.95；“ON THE LEARNING FRONTIER”是动机图，gold=1 不等于实测学生位于前沿 |
| Figure 2 | 4 | probe→state→selector→rewriter→checks→gold→pool→RL；有失败与 policy update 箭头，不能据图补在线课程频率 |
| Algorithm 1 | 6 | 展示 per-seed 一次选择与 gold acceptance；没有完整写出直到100接受的 repair/reprojection 控制循环 |
| Table 1 | 7 | 全部模型分数与生产统计已转录；FORGE token 分项差 400,000 |
| Figure 3(a) | 7 | x 为训练条件，y 为 Pass@1%；tb-core/tb-2.0 柱与表一致；无误差条 |
| Figure 3(b) | 7 | x 为合成方法，y 为百万 token；分块 prompt/final-completion；柱顶 total/attempts；FORGE 总量文字与分项不闭合 |
| Figure 4(a) | 8 | 三 benchmark、五训练条件的点图，标签给 FORGE 与 Base 差；不是训练过程曲线 |
| Figure 4(b) | 8 | 4B–35B 的 Base/FORGE 成对分数，与 Table 2(b) 一致；无多种子误差 |
| Table 2(a/b) | 8 | benchmark 与 model coverage；不是 selector 组件消融 |
| Table 3 | 8 | 归一化成本已重算；FORGE 单位 token 成本继承 Table 1 的 reported total |
| Table 4 | 12 | projection movement/invariants 与 restricted policies；表注明 approximate prompt semantics |
| Table 5 | 12 | 技能标签 taxonomy，不是技能掌握评测 |
| Table 6 | 13 | 符号与实现边界；solver 输入系数固定 |
| Figure 5 | 14 | 五例完整查看；红=increase、蓝=reduce、绿=diversify；projected rate 不当作 post-generation 实测 |
| Eq.(1)–(3) | 3–4 | 固定偏移、高斯 frontier utility、线性选择目标；负号、平方与系数已目视核对 |
| Eq.(4)–(11) | 5 | cardinality、技能联动、coverage、slack、baseline mask |
| Eq.(12) | 11 | 受限 baseline feasible set；不是额外训练目标 |
| C.1 方法框 | 16–17 | shared template、四种 strategy injection、shared repair 全部读取 |
| C.2 方法框 | 17–18 | solver payload、projection/direction、artifact masks、skill contract 全部读取 |
| C.3 案例框 | 18–19 | 五组 original/synthesized 指令全部读取；Case I/II 已有要求与 Case V 收窄不能被图注掩盖 |

原表已有精确数值时使用表值，不从图像重新制造小数精度。Case V 的 p_hat=0.533 与 F=0.9862 可能含显示舍入差异；本稿保留原值，不在缺少未舍入估计的情况下把微小差异另判为确定错误。

<a id="code"></a>
## 10. 关联代码附查：保留实际数据流，但撤去对论文的越界推断

本节延续上一轮定点审查，并在本轮复读接受判定与消息导出关键段。固定 revision 为 `2a1d65ec8dcfaea2458d67e1fb18078cce6420b9`。论文首页只链接整个工具包，**没有把这个分支快照指定为主实验实现**。这不是完整仓库／所有分支审计。

### 10.1 入口与接受字段

`examples/syn_agentic_data/run_terminal_bench.py::main()` 加载 config 后调用 `run_terminal_bench_synthesis()`。该循环按 task、strategy、direction、sample index 遍历；schema 的 strategy 为 few_shot/self_instruct/evol_instruct，Evol 再分两个方向。demo 三 seed×(1+1+2)=12 是配置的名义候选量，不是论文100环境。[C1][C3]

`terminal_bench.py` 的已读主路径让 LLM 返回 artifact JSON，物化后只调用 `static_validate_materialized_task()`，再根据 `record["verification"]["matched"]` 加入 accepted。static validator 查必需路径和文件非空，没有实际构建容器或运行 oracle/tests。[C2-flow][C2-export]

**结论仍成立：该示例的 accepted 不等于论文 §3.4 的 gold-verified。** 本轮 PDF 明确给出了作者实验所要求的 oracle+tests 准入链，所以不能因示例不闭合反过来声称论文未做 gold verification。

### 10.2 独立 Harbor smoke 与结果回写

独立 `run_terminal_bench_harbor_smoke.py` 读取一条 record，调用 `run_harbor_verification()` 并打印。缺凭据时 skipped；helper 按退出码与读得的 reward 判 matched。该 smoke 不自动回写 records、不重新筛选 accepted，也不批量完成论文的 oracle acceptance。它默认调用 terminal agent 的求解，不能自动等同“执行参考 oracle”。[C2][C4]

其中的 agent/model 字符串属于示例配置，不是本篇论文 probe/synthesis/evaluation 模型的已确认身份。

### 10.3 模板消息与真实 rollout

`terminal_bench_record_to_dataarc()` 构造 instruction、assistant reasoning、`run_harbor_terminal_bench` function call、静态验证 observation、结束语。这个转换函数没有实际执行被写入的调用，因此消息格式存在不代表已获得目标 policy 的真实 terminal trajectory、采样 token、behavior logprob 或训练 mask。[C2-export]

原文训练来源是接受的**环境**，随后由目标 policy 在环境中 rollout；不能用 demo 导出的模板 JSONL 替代这条 RL 数据链。消息行不含 solution/tests 源码，只说明文本导出的可见性，不证明容器里没有隐藏资产。

### 10.4 上一轮保留的条件性风险

`_read_latest_harbor_reward()` 按共享 jobs 目录内文件修改时间找 reward，未在该 helper 中绑定本次 job identity。复用目录、新 run 没有新可解析 reward 等条件下，存在读到旧值的风险；是否造成误评分还取决于退出码及调用行为，未做运行复现。[C2]

seed/context/materialization 中的 canary 文本删除，只是字符串处理，不构成去重或去污染证明。不能把去掉标记作为允许 benchmark 派生任务进入训练的资格依据；仍要保留来源、split 与 lineage。[C2]

### 10.5 论文与代码证据分级

| 主张 | 当前证据 |
| --- | --- |
| 论文提出 policy-relative 六动作、MILP、gold verification | 原文方法、附录 B/C 完整支持 |
| 作者报告用接受环境进行了 GRPO 并有下游收益 | 原文结果支持作者报告的训练事实；本轮未复现 |
| 工具包的指定 sidecar 可构造任务目录／导出接口行 | 固定代码支持 |
| 指定 sidecar 已实现论文完整 selector→gold→RL 流程 | **不支持**；所查入口没有闭合这些环节 |
| 作者其他实现不存在／论文没做验证 | **不能推出** |
| 当前可按已查分支一键复现论文主结果 | **尚未建立** |

<a id="gaps"></a>
## 11. 限制、原文冲突与可追问项

### 11.1 已定位的冲突或语义风险

| 编号 | 问题 | 证据与当前处理 |
| --- | --- | --- |
| Q1 | FORGE token total 与分项差 400,000 | Table 1/Fig.3(b)，p.7；Table 3 派生值依赖 reported total。原值并列，不擅自修正 |
| Q2 | response cap=1,024 与=8,192 | A.4 p.13 对 D p.19；请求实际 run config 及字段消费位置 |
| Q3 | PGN diversification 名称与真实改写范围 | A.5/Fig.5 对 C.3 p.19；收窄任务、直接给着法，需实测生成后难度和审查保留技能 |
| Q4 | per-seed 与 active coverage 的装配关系 | §3.3/A.2/B；需 m_v、slack、选中动作、solver 原始输入输出，不能只看 N=100 |
| Q5 | 框架图反馈与实际重试／重估策略 | Fig.2、Algorithm 1、§4.1；缺少可重放 schedule，不声称在线课程实验 |

Q1/Q2 是直接的表值／配置披露不一致；Q3 是有原文对照的语义风险；Q4/Q5 是实现与实验流程尚未充分展开。它们的性质不同，不能统称“实验造假”，也不能统称“读取失败”。

### 11.2 作者自己承认的实验范围

Limitations 与 §4.5 列出：本次评估 per-seed 模式；portfolio 不在对照中；solver-off、transfer-prior sensitivity、Evol depth/breadth 分开分析尚待开展；seed pool 和 model family 扩展是后续工作。[P08][P09]

除此之外，本轮阅读没有找到 post-generation pass-rate calibration 曲线、多种子置信区间、完整 verifier 正反例审计、bridge→原复杂任务的专门迁移实验，或可逐任务追踪 100 accepted 环境的公开实验日志。这里的“没找到”限于所读 PDF 与指定代码，不是对全部公开网络或作者内部资产的否定。

### 11.3 安全与 AI 使用声明

Ethical Considerations 说明使用 benchmark/task/experiment records、无 human-subject data；记录 solver decisions 与 verification outcomes，并提醒基本模型、执行系统、工具和 benchmark 风险仍在，部署需权限、sandbox、日志与人类监督。不能把这些声明当作已经报告了对抗安全实验。[P09]

AI 使用说明提到 GPT-5 和 DeepSeek-V4 用于语言润色。它属于稿件准备声明，**不是合成模型或 probing 模型的配置披露**。不能用它来填 §5.3 的模型身份未知项。[P09]

### 11.4 下一步真正需要的材料

全文不再缺。若进入复现，最有价值的是：Table 1 原始 token/attempt 账本；主实验配置和精确 checkpoint；seed/probe/accepted-task manifests；SCIP 输入与 action/skill/slack trace；gold execution logs 与 test/image hashes；逐任务 eval 输出与随机种子。这些是**实验核验与复现资产**，不是为了继续读完19页而要求用户重复上传同一 PDF。

<a id="project"></a>
## 12. 对 RepoHarness 的条件化意义

本节是读者的候选设计判断，不是论文既成结论或项目实施批准。

### 12.1 值得吸收的是三条责任分离

**难度画像与任务有效性分开。** oracle-pass 说明一个参考执行路径通过；policy profiling 说明在指定模型／harness／预算下多难；保留技能与防作弊又是不同的质量维度。不要让单一 `accepted` 或 `matched` 同时承担全部语义。

**动作计划与实际产物分开。** 记录 selected projection、predicted pass rate、skill contract 之后，还要检查 materialized task 是否真的执行该计划。Case V 正说明：生成器服从输出格式，不等于保持动作语义；预测难度更不等于测得难度。

**生产记录与训练轨迹分开。** task bundle、oracle trace、policy rollout 和模板 tool-call JSONL 是不同资产。只有真实 policy 行动及其采样／reward provenance 才能承担相应的 RL 训练语义；不能拿构造出来的演示消息替代实际 rollout。

### 12.2 一个有辨识度的低成本探针

可先从少量合法训练 seed 中覆盖过易、近前沿、当前未解出三组，冻结 policy、harness、resource budget 与 verifier。比较固定动作和 frontier-selected 动作；所有生成包经过相同的 build/oracle 流程，再用同一策略实际测新任务的通过率，并审查说明中是否直接给出关键答案、技能是否漂移、no-op 是否能过。[本节为建议]

第一阶段最关键的指标不是任务产量，而是 **预测与实测偏差、动作执行符合度、有效可学习任务比例、每个合格环境成本**。若预测改善但实测不改善，或者所谓 diversify 主要通过删任务／给答案实现，先修任务生产和验证，不急于跑 RL。

进入训练前，再考虑相同候选／约束下的简单 enumeration 与 MILP、相同结构化 payload 下的固定动作与 policy-relative 动作、去掉 reduce 的对照。只有这样才能拆出“动作空间”“policy 信息”“生成契约”“solver”各自的贡献。portfolio 不是首个必要组件。

### 12.3 工程上可借鉴但应补强的字段

可记录 `seed/task revision、policy/checkpoint、harness/verifier/image digest、probe attempts/rewards、predicted pass rate、selected action、skill/edit contract、actual validation results、post-generation policy profile、cost breakdown、retry lineage`。这些字段是本稿提出的审计设计，不宣称论文都公开实现了。

preflight 值得作为训练 worker 启动前的门，但应明确检查覆盖度；oracle 验证值得保留，同时需要错误解／no-op／替代解与 flakiness 等额外资格证据；reward 必须绑定本次 job 与准确 task revision。上述均不要求 RepoHarness 自研通用 MILP 平台或替代训练后端。

**最终定位：Envs-FORGE 是“策略相对的环境变换选择”的有价值参照，拥有作者报告的 RL 结果；它不是已经充分证明、可直接搬用的在线课程系统。全文最值得带走的，不只是 increase/reduce/diversify 三个名字，而是检验“预测的学习前沿是否真的由生成环境实现”。**

## 来源定位

[P]: https://arxiv.org/abs/2608.14312v1
[P01]: https://arxiv.org/pdf/2608.14312v1#page=1
[P02]: https://arxiv.org/pdf/2608.14312v1#page=2
[P03]: https://arxiv.org/pdf/2608.14312v1#page=3
[P04]: https://arxiv.org/pdf/2608.14312v1#page=4
[P05]: https://arxiv.org/pdf/2608.14312v1#page=5
[P06]: https://arxiv.org/pdf/2608.14312v1#page=6
[P07]: https://arxiv.org/pdf/2608.14312v1#page=7
[P08]: https://arxiv.org/pdf/2608.14312v1#page=8
[P09]: https://arxiv.org/pdf/2608.14312v1#page=9
[P11]: https://arxiv.org/pdf/2608.14312v1#page=11
[P12]: https://arxiv.org/pdf/2608.14312v1#page=12
[P13]: https://arxiv.org/pdf/2608.14312v1#page=13
[P14]: https://arxiv.org/pdf/2608.14312v1#page=14
[P15]: https://arxiv.org/pdf/2608.14312v1#page=15
[P16]: https://arxiv.org/pdf/2608.14312v1#page=16
[P17]: https://arxiv.org/pdf/2608.14312v1#page=17
[P18]: https://arxiv.org/pdf/2608.14312v1#page=18
[P19]: https://arxiv.org/pdf/2608.14312v1#page=19
[OLD]: https://github.com/Rogerffff/RepoHarness/blob/09b9d68c1803c7bb0c2d1944fcbac2bc5b34f7c6/knowledge/summary_envs_forge_synthesis_policy.md
[C0]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/docs/SYN_AGENTIC_DATA.md
[C1]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/examples/syn_agentic_data/run_terminal_bench.py
[C2]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/sdgsystem/agentic_data/terminal_bench.py
[C2-flow]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/sdgsystem/agentic_data/terminal_bench.py#L110-L220
[C2-export]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/sdgsystem/agentic_data/terminal_bench.py#L340-L402
[C3]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/configs/syn_agentic_terminal_bench.yaml
[C4]: https://github.com/DataArcTech/DataArc-SynData-Toolkit/blob/2a1d65ec8dcfaea2458d67e1fb18078cce6420b9/examples/syn_agentic_data/run_terminal_bench_harbor_smoke.py
