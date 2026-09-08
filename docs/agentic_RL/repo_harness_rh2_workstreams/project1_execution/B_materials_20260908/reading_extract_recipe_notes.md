# B 线资料提取：16 篇精读笔记中的环境 / 数据 / 评测 / 基座诊断事实

整理日期 2026-09-08。范围：`docs/harness_improve/external_paper_references/reading_notes/` 下 16 篇笔记（只读，未改仓库文件）。每条事实后括号内为**笔记章节**及笔记转引的**原文位置**；笔记没写的一律标"笔记未提"。"对我们可用"条目均以当前基线为前提：216 题 SWE-Gym Lite（11 仓库、每题一镜像）、Claude Code CLI in Docker、Qwen3-30B-A3B、miles + GRPO n=8 + faithful DIS、≤8×RTX PRO 6000、二元 F2P/P2P reward。凡涉及样本准入 / reward / 拒绝路径的候选，按协作协议属 **T0**，这里只列为候选，不是定案。

---

## 1. R1 MAI-Thinking-1（Microsoft AI 技术报告）

**1. 来源与版本。** 无 arXiv；官方 PDF 两版：本地 L（SHA `7d4f13dd…`，元数据 2026-06-02）与官方快照 W（SHA `a267d745…`，2026-06-06），均 109 页，后训练主配方无实质差异；页码指 L（笔记 §1）。

**2. 环境与任务供给。**
- SWE 镜像 = 固定 commit 仓库 + 预装依赖 + 题面 + 评分测试；**hidden test changes 推理期隐藏、评分时才应用**；工具 bash + `str_replace_editor`（App. D）；SEE 每任务新容器、完成即销毁、默认断网、需联网走缓存代理 + allowlist（笔记 §6.1；原文 §3.3 pp.40–41）。
- Organic SWE 漏斗（笔记 §6.2；原文 §3.3.1 p.42）：102,000,000 公开 PR → 约 4,870,000 候选（merged 到 main、改动 <15 文件、含 code+test、关联 issue；支持 GitHub/Jira/Bugzilla/YouTrack/Phabricator/Launchpad/Linear）→ 2,080,000（42.8%）自动建环境通过（LLM agent 读仓库生成 Dockerfile，排除依赖/环境错误）→ 745,452（15.3%）reference signal 通过（base+test diff 对比 base+test+code diff 取 F2P/P2P，无 surviving F2P 丢弃）→ 265,617（5.5%，94,044 unique repos）SEE+grader 验证通过（**empty patch 多轮 fail、golden patch pass、筛非确定测试**；轮数未给）→ 质量过滤 + 题面 rewriting（clarity、test quality、leakage、feasibility）：**最终数未给**。三个百分比的共同分母是 4.87M 候选。合成题复用"可执行但未过质量验证"的环境，数量未给。
- 单位成本（笔记 §6.4；原文 App. F pp.97–98）：two-pool Ray 集群约 30,000 CPU cores；性能段配置 10,000 CPU cores + 12M LLM tokens/min capacity，prompt cache hit 83%，产出约 **20 grading-passed environments/min**，瓶颈是 LLM token 消耗。按 repo 持久 Ray actor 复用 BuildKit layers。笔记明确不能据此算"每题 60 万 token"或美元。
- 通用工具环境另有 >150 environments / 130,000 tasks，不属 SWE 漏斗（笔记 §6.5）。

**3. 数据划分与污染。**
- 预训练去污染：移除 HF 及镜像来源、20-gram fuzzy matching / 80% 阈值；App. A.4 的 GitHub PR 数据明确排除 SWE-bench Verified PR；预训练来源截止 GitHub 2025-06（表 4），**不是后训练 SWE PR 截止**（笔记 §3.1；原文 §2.3.1、App. A.4）。
- STEM/竞赛代码三层去重（SHA-256 精确、n-gram/MinHash LSH、embedding cosine）并对 App. G benchmark 去污染，阈值未给（笔记 §5.1；原文 §3.2.3）。
- SWE 后训练的时间切分、仓库 held-out、dedup 阈值、gold 可见性：**笔记 §10.1 明列为未披露**。
- 评分隔离：**grader 在 agent 同一 container 内跑测试**（原文 §3.3.1 p.41；App. H p.101）。反作弊（p.43）：限网；清除 base commit 之后的 commits/refs/branches；reset agent 改过的 test files 再应用隐藏 test changes；LLM monitor 审 rollout + 人工复核 flagged；作者承认 monkey-patch 测试框架等仍可能作弊（笔记 §6.3）。

**4. 难度筛选与采样。**
- 两级筛选（笔记 §4.4；原文 §3.1.3–3.1.5）：先 G_early=16 估 early pass rate（positive reward 比例），仅 `[0.05, 0.8]` 内继续；完整组筛 `[0.1, 0.8]`，去掉近全对/全错低方差组。G=128 total rollouts，但 §3.6.2 写"先 16 再 additional 128"，原文冲突。
- 长度惩罚按题目 pass rate ρ_q 加权，难题惩罚弱（笔记 §4.3；式 12 p.33）。最大生成 8k→16k→32k→64k→128k 课程（笔记 §4.4）。
- 失败处置（笔记 §7.1）：build dependency 错误在生产阶段排除；worker/request 故障重试；预算终止的完整轨迹仍送 grader；stale rollout 丢弃；**timeout/解析错/工具错/grader timeout 各自的 reward、mask、是否进组、补采上限均未披露**。

**5. 评测协议（笔记 §8.1–8.2；原文 §4.1、App. G/H）。**
- 默认 4 runs 均值、temperature=1、top-p=0.97；pass@1 = 单采样成功概率估计，不是 pass@4。
- SWE-bench Verified 73.5%（500 题；bash+editor；总 context 256k、每次最大输出 8k、最多 1000 steps）；SWE-Bench Pro 52.8%（731 题）；Terminal-Bench 2.0 46.0%（89 题；bash only；256k、32k/次、1000 steps；**忽略预设 timeout**）。评分在同一 SEE。无每题 seed/CI、harness commit、环境 hash、wall-clock。外部模型分数取官方卡片，非统一协议。没有 terminal 专项训练环境，TB 结果是迁移（笔记 §6.5；原文 §4.1）。

**6. 基座诊断。** 初始 RL 从未接触 reasoning traces 的 checkpoint 开始，无第三方 CoT SFT 冷启动路径（笔记 §3.2；原文 §3 pp.30–31）。自蒸馏是"收集 RL rollout → 对 mid-trained checkpoint SFT → 继续 RL"：O(1M) traces 足够、只用成功轨迹、取后期多 checkpoint、随机抽样优于启发式、短轨迹 SFT 会遗忘长上下文（笔记 §3.2；pp.35–37）。训练前对基座的工具使用/失败位置/成本诊断：**笔记未提**（App. C 只有 CoT 行为演化的挑选案例，笔记 §8.5）。

**7. 成本口径（笔记 §9）。** 环境生产：上述 10k CPU / 12M tok/min / 20 env/min，无 wall time、CPU-hour、API 账单。RL：最大 job 4,864 GB300（4,096 推理 + 768 学习）；W 版另写 RL climb 4.6K GB300s；无 GPU-hour。评测：有预算无费用。

**8. 对我们直接可用。**
- 把 216 题分成三道独立门：①镜像可构建、测试可收集；②grader 有效：empty patch 多次 fail、gold patch pass、跨轮次筛 flaky（MAI 做多轮但轮数未给，我们自定 ≥3 轮并记账）；③题面充分性（spec 对 test 盲审）。笔记 §11 第一行原话即"优先审现成 SWE-Gym 小池，不预设自建百万 PR 采集器"。
- pass-rate 分带筛题是 T0 候选：MAI 用 early 16 条筛 `[0.05,0.8]`；我们 n=8 只能用基座 pass@8 分带（例如去掉 8/8，保留 0/8 一部分），笔记 §11 明说"不将 early 128 采样搬到 n=8 首训"。
- MAI 承认"同容器评分 + reset tests"不够 → 我们的 fresh grader / 可信投影是自选设计，用代表性 test-reset/配置/plugin 反例做真实评分测试并记误杀/漏判（笔记 §11 第二行）。
- **不要照搬**：20 env/min、10k CPU 的产能与 G=128；TB 2.0 46.0 是忽略 timeout 的分数，不能作可比参照。

**9. 笔记标注的未知项（B 相关）。** early/full 128 vs 16+128（§10.1）；timeout/parse/tool/grader 错误如何进组/loss；quality rewriting 后最终有效任务数、mirror 数、synthetic 占比；SWE 时间切分/仓库 held-out/dedup 阈值/gold 可见性；质量 judge 模型与阈值、rewrite 前后保留率与成本。

---

## 2. R3 Qwen3-Coder-Next（arXiv:2603.00729v1）

**1. 来源与版本。** arXiv:2603.00729v1，提交 2026-02-28；23 页；SHA `4be52e37…`；模型卡 `Qwen/Qwen3-Coder-Next@a7fbcb5c…`、Base `@1b6df59d…`；仓库 `QwenLM/Qwen3-Coder@33bc6aab…`（笔记 §1、§8.2）。

**2. 环境与任务供给。**
- 管线 A 真实 PR → 可执行 repository instance（笔记 §4.1；原文 §2.1 p2）：挖关联 issue 的 PR，排除下游 benchmark 重叠，拆 buggy state / fix / test patch；environment-building agent 建 Docker + 验证脚本，要求执行能区分 buggy/fixed；自动检测过滤 non-functional verifiers；训练专门构建模型；镜像复用；QA agent 剔除描述含糊、环境不一致、测试与需求错配。细节转引 SWE-Universe。Table 10（p19）：**807,693 instances / 52,960 repos**（Python 202,302/13,098；JS/TS 175,660/11,604；Go 121,062/5,554；Java 86,105/4,700；Rust 74,180/4,445；C/C++ 37,228/3,405；C# 24,387/1,929；Others 86,769/8,225），均 15.25/repo，Avg Eval Lines 28.21。**原始 PR 数、构建失败率、QA 各阶段剔除量未给。**
- 管线 B 可复用仓库 → 新 bug（笔记 §4.2；原文 §2.1 p2–3、Figure 2）：AST/tree-sitter 定位函数/类注入 bug；`PASS_TO_FAIL` 非空判定 bug 触发原测试；回退 patch 须恢复通过；生成 NL issue；排除 bug-triggering test files。Table 11（p19）：raw/cleaned/used repos → tasks：SWE-smith 134/134/130→74,003；SWE-Flow 2,203/2,203/1,987→384,541；SWE-rebench 3,468/2,912/2,727→373,125；SWE-smith-multi 133/133/118→13,663；Multi-SWE-RL 74/74/57→6,566；合计 6,012/5,456/5,019→**851,898**；按策略 lm_rewrite 145,450 / lm_modify 233,369 / func_pm 460,578 / others 12,501；均 169.7 bugs/repo。两池不能相加为去重训练集。
- Harness 多样性证据：中训轨迹用 SWE-agent、Mini-SWE-agent、OpenHands、Claude-Code、Qwen-Code、Terminus 六框架 + 480B teacher（笔记 §3.1、§4.3；原文 §3.1.2 p5）；Figure 3（p5）横轴 1/2/4/8B 中训轨迹 tokens：OH→OH、SA→SA 提升；**OH→SA 在 8B 端两指标约 0；SA→OH 部分迁移非单调**；Figure 5（p8）固定数据量下工具模板数 1/2/4/8 → Verified 约 48.0/52.0/53.4/53.8%（读图）；Table 12 实列 20 个模板（正文写 21）（笔记 §3.5）。
- SWE RL pool：SWE-Gym、SWE-rebench 等开源任务 + 自建环境，pass-rate 筛选（笔记 §4.3 表）。

**3. 数据划分与污染（笔记 §4.4）。** SWE expert 的 **SFT 与 RL prompts 完全互斥**（仅 prompt 层面，跨 PR/仓库/派生 bug 未定义）；PR 挖掘与中训均有 benchmark overlap 去除，无 manifest/规则/阈值/计数；天然语料截止 2025-09-30 只属预训练说明。no-op / alternate-solution / fresh reset / flakiness / grader 隔离 / gold 可见性均未披露。

**4. 难度筛选与采样。** 估计训练实例 pass-rate 分布，移除 overly easy 与 noisy failure cases（采样次数/阈值未给）（笔记 §4.4；原文 §4.2.4 p10）。RL 三层：outcome reward、超最大轮数惩罚（值未知，不能用评测 300 填）、turn 级 tool-format token 惩罚（笔记 §5.2）。反作弊（笔记 §5.3；p10–11）：删 remotes/branches/tags；RL 后期 agent 学会重建 remote、clone/curl 取历史；保留网络供依赖安装/查文档，但阻止"同时含 repository link 与 git/curl/wget 关键词"的调用并反馈；Figure 7：有 blocker 75.1% Verified，无 blocker 84.6%（作弊高分）；平均 turns 50→130。

**5. 评测协议（笔记 §7.2；原文 §5.1 p11–12、Tables 3–5）。** 每 scaffold 重跑所有 baseline，均删 remotes/branches/tags；max turns 300。SWE-Bench Verified：SWE-Agent 70.6 / MiniSWE-Agent 71.1 / OpenHands 71.3；Multilingual 62.8/56.2/64.3；Pro 42.7/38.7；Terminal-Bench 2.0：Terminus2-xml 34.2 / Terminus2-json 36.2 / **ClaudeCode 30.9** / QwenCode 25.8（Opus 4.5 同序 58.4/57.3/53.9/51.7）。破折号=未可靠获得。**无 dataset revision/split/题数、harness commit、seed/重复/CI、token/时间预算。** Table 2 五个匿名 scaffold 的工具格式准确率 98.0/83.0/98.0/91.5/93.0（均 92.7）。附录 packing 消融用 Agentless 代理指标（patch similarity/empty rate），非测试通过率（笔记 §7.5）。

**6. 基座诊断。** SFT 用 Mini-SWE-agent 扮终端用户执行回答代码做验证过滤（笔记 §3.3）；中训混少量 IF 数据以便"较早监测 downstream 指标"（笔记 §3.1；§3.1.3 p5）；中训轨迹丢弃无终止信号/任务失败/tool-call 格式错误。训练前基座工具使用/失败位置诊断：**笔记未提**。

**7. 成本口径（笔记 §8.1）。** 全部无数值：无 API 调用数、构建成功分母、CPU/GPU-hour、镜像存储；仅 80B/3B 激活与"万亿量级"中训 token。

**8. 对我们直接可用。**
- 镜像预处理：对 216 题镜像删除 remotes/branches/tags，并在基座诊断中检查 Claude Code 是否出现"重建 remote / git fetch / curl 取历史"行为（R3 观察到 RL 后期会学到）；我们 Docker 联网策略需先定（T0：新增拒绝路径）。
- 若后续做 SFT，遵循 SFT/RL prompt 互斥：216 题里用于 RL 的题不得再作 SFT 轨迹来源。
- Figure 3 说明单 scaffold 训练难迁到另一 scaffold → 首版评测固定 Claude Code；第二 harness（如 mini-swe-agent）只作评测探针，笔记 §10 也是这个建议。
- **不要照搬**：80 万级实例规模与多模板训练（首版单 harness）；300 turns 是评测预算非训练预算。

**9. 笔记标注的未知项（§9.2）。** 构建/QA/pass-rate 漏斗与 noise 判据；harness/split revisions、重复次数、CI；fresh grader/投影/隐藏材料/网络 blocker 覆盖率与误杀抽检量；各阶段实际消费与成本。

---

## 3. N01 KAT-Coder-V2.5（arXiv:2607.05471v1）

**1. 来源与版本。** arXiv:2607.05471v1，2026-07-06；24 页；TeX 已存 `sources/N01/`；无可核训练代码/权重/数据发布入口（笔记 §1）。

**2. 环境与任务供给（笔记 §4.1；原文 §2.1 p4、图 2 p3）。**
- 任务 = 清晰描述 + 可执行仓库环境 + 验证测试；problem statement 主要依据 golden patch，requirements 依据 test patch，接口约束从两者推断，再做清晰性检查（歧义/不完整/矛盾删除）。
- AutoBuilder：build agent 生成"clean checkout 装依赖跑测试"脚本；verification agent 在隔离沙箱执行并解析**结构化测试框架输出**；接收条件 = **收集到 >90% 预期测试 且 pass/fail 跨运行可复现**（不是 90% 通过）；失败结构化信息回送迭代；预配置底座/语言模板/成功配置检索库。构建成功率 **16.5%→57.2%**（分母未给）；**>100,000 environments、12 languages**（≠ 仓库数/镜像数/题数）。参考变更中非编程性的依赖/配置改动预先应用；清除 git history、commit metadata。
- 近成功恢复（笔记 §4.2；§2.2 p5）：原零通过任务给"读哪里/核什么"过程提示后通过率约 20%；再冻结已验证 patch、从原上下文重新生成**无提示**轨迹，只留通过执行验证、无提示泄漏、与 patch/测试一致的样本；存活率未给。
- 过程过滤：规则层去无效/不稳定/作弊；启发式过程层评探索、定位、修改前推理、规格忠实、仓库惯例、patch 最小性、验证质量、恢复、诚实；通过但硬编码/绕机制/改测试的降权或删除。
- Harness randomization（笔记 §4.3）：工具名/参数约定/输出格式/prompt 模板随机改写、功能不变；注入缺失依赖、瞬态命令失败、截断输出、噪声日志；概率/权重未给。RL 中白盒 mini-swe-agent 与黑盒 ClaudeCode/Codex/OpenClaw/OpenHands 均参与（笔记 §6.1；§4.1 p9–10）。
- **沙箱故障审计**（笔记 §6.3；§4.2.2 p11–12）：V2 早期慢收敛先归因算法，抽审发现约 **16%** 轨迹含 ≥1 次 sandbox 故障（最严重边界错位使后续约 40 步 observation 为空）；镜像 GC/初始化超时导致无效 rollout 约 6–7%→<1%；远程初始化环境变量覆盖系统配置使 verifier 读错、约 6–7% 样本输出受污染→<1%（相当于翻转 reward）；总沙箱反馈错误 16%→<2%；磁盘峰值 95%→稳态 60%；collapse 频率降约一个数量级。审计样本数/窗口未给。

**3. 数据划分与污染。** 清除 git history/commit metadata；**未给仓库/PR 派生切分、时间截止、基座污染审计**（笔记 §4.1 末段）。KAT Code Bench：冻结 base commit/环境/verification 入口；剔除不可复现环境/flaky tests、过绑定参考实现误杀替代解、描述–verifier 不符、模板化泄漏；题数/split/时窗/与训练池隔离未知（笔记 §7.1；§6.1 p17）。

**4. 难度筛选与采样。** 无 pass-rate 分带；对零通过题走近成功恢复链（见上）。Core reward 仅 F2P+P2P 全过得满分，另有失败轨迹部分奖励（File Search F₂、Unit Test Pass Rate）（笔记 §5.3；表 1 p23）——与我们二元 reward 不同。

**5. 评测协议（笔记 §7.2；表 4 p19）。** SWE-Bench Pro 65.2、KAT Code Bench 53.1、PinchBench 94.9（榜单 2026-07-02）、KAT Claw Bench 85.5、Terminal-Bench **2.1** 60.7、SciCode 50.3；除 PinchBench 外统一 Claude Code、固定工具/context budget/执行环境/decoding；**题数、重复、预算、CI、harness 版本均未给**。

**6. 基座诊断。** 无 base 参数规模/架构（笔记 §3）。最有价值的诊断做法是 §6.3：**先抽审轨迹区分环境故障与模型失败，再调算法**。训练前基座工具使用诊断：笔记未提。

**7. 成本口径（笔记 §8）。** 只有构建成功率与环境规模；CPU/存储/人工/API/GPU-hour 全无。

**8. 对我们直接可用。**
- 216 题验证用**结构化测试输出**而不是 exit code：报 collected/expected 测试数、跨 ≥2 次运行 pass/fail 一致性，再跑 no-op/gold/合法替代解；笔记 §10 原话"不能盲照 90% 阈值"。
- 基座诊断阶段做一次"沙箱故障 vs 模型失败"审计：对 216×8 首批 rollout 逐条标记容器启动/初始化超时、环境变量/配置污染、observation 为空等，分母=全部尝试，错评分/timeout/成本单列（笔记 §10 第三行）。
- 0/8 组处理候选：等 API 预算下比较"普通重试"与"过程提示修复→无提示重建"的保留率与 held-out 收益（笔记 §10 第四行）；属后续、非首版。
- **不要照搬**：PPO hindsight critic / GRM / 十项 reward（二元 reward 已定）；harness randomization 训练（首版单 harness，第二 harness 先评测）。

**9. 笔记标注的未知项（§9.1）。** 候选分母、仓库/PR 数、时间窗、许可、切分；无提示重建保留率；扰动注入概率；harness 版本/配比；评测题数/重复/预算；沙箱审计样本数。

---

## 4. E11 Nemotron-Cascade 2（arXiv:2603.19220v2）

**1. 来源与版本。** v1 2026-03-19、v2 2026-03-22，主读 v2（63 页）；HF 模型 `nvidia/Nemotron-Cascade-2-30B-A3B@6327cdbc…`；RL 数据 `@05bbaf03…`；SFT 数据 `@9f36020d…`（笔记 §1、§11.2）。底座 Nemotron-3-Nano-30B-A3B-Base（非 Qwen）。

**2. 环境与任务供给。**
- SWE SFT（笔记 §3.4；原文 §3.2.9 p9）：125K agentic samples，问题源 SWE-Gym、SWE-rebench、R2E-Subset，Qwen3-Coder-480B-A35B-Instruct 生成，scaffold OpenHands/SWE-Agent/Mini-SWE-Agent/agentless；389K agentless samples（定位/修复/测试生成，修复用 DeepSeek-V3.2 重建）；agentic 用 non-thinking、agentless 用 thinking。加 agentless 后 OpenHands/Verified pass@1/pass@4 48.9/62.8→49.9/65.2（非等预算）。
- Terminal SFT：Terminal-Task-Gen，DeepSeek-V3.2 在隔离 Docker 内执行反馈循环，Terminus 2；490K（分项 486K：数学 162K、代码 32K、SWE 32K、seed 120K、skill 140K）；**Fig.2 无独立 terminal RL 阶段**（笔记 §3.4）。
- Agentless RL（笔记 §7.1；§4.8.1 pp.15–16）：多数实例无可执行 Docker → GPT-OSS-120B 作修复 reward model；prompts 混 golden localization 与 top-5 retrieved localization；128×16，最大 seq 98,304；若一题所有 rollout reward ≤0.5 则该题 loss 屏蔽。
- Execution RL（笔记 §7.2；§4.8.2 p16、Table 10 p26）：OpenHands 提供文件检查/搜索/编辑/测试；编译/单元测试评分（scalar 组合未披露）；**16 prompts × 64 rollouts = 1024/step**；256K context / ≤200 轮；T=0.8；数据 SWE-Gym + R2E-Subset。
- Code RL verifier 吞吐：每步 2,048 份程序，异步 reward server 在 384 CPU cores 上 427.2 s（笔记 §5.5）。
- 公开 RL 数据卡：SWE 3,612 条，约 20% SWE-Gym / 80% R2E-Subset（发布混合，非训练配比）（笔记 §11.2）。
- 笔记 §3.4 明确：**未恢复"候选仓库/PR→镜像→gold/no-op→稳定可解→保留轨迹"漏斗**，也无 grader 隔离/替代解/flakiness/未来 git/费用。

**3. 数据划分与污染。** 竞赛代码 I/O fingerprint + n-gram 去重去掉约 24.2% 自重复（笔记 §3.2）；SWE 的 split/去污染：笔记未提。

**4. 难度筛选与采样（笔记 §7.2、§5.5、§5.1）。**
- Execution RL 离线预筛：**中间模型每实例生成 16 条；全通过题删除；全失败题随机丢弃 90%、保留 10%**。
- Code RL：剔除 GPT-OSS-120B 8/8 全对题 → 3.5K hard prompts。
- IF-RL：动态过滤全对/全错组；超长未结束 → 零 reward。
- Agentless RL：过滤相对简单题；全 rollout ≤0.5 的题整题屏蔽。

**5. 评测协议（笔记 §10.3；Appendix A.6 pp.23–24）。** SWE-bench Verified 500 题、OpenHands、**non-thinking、avg@4**、256K context、≤200 turn、保留完整交互历史 → 50.2；Terminal-Bench 2.0 89 题、Terminus2 默认、avg@5 → 21.1；τ²-Bench airline avg@16、retail/telecom avg@8，目标 SE ≤1.5pp。Table 4 同时报 avg@4 与 pass@4（Agentless Mini 41.9/55.2→44.3/57.4；OpenHands 49.8/64.2→50.8/65.0）。avg@k=多次平均，非 pass@k。HLE 改用 `\boxed{}` 格式带来约 6–7 分（笔记 §10.2）。

**6. 基座诊断。** 先做覆盖十类能力的大规模 SFT（33,000 steps、256K packing、约 1.5 epochs）（笔记 §3.1）；分阶段观察干扰后用同源 checkpoint MOPD 恢复（笔记 §2）。训练前基座诊断：笔记未提；最接近的是 execution RL 的"中间模型 16 条预筛"。

**7. 成本口径（笔记 §11.1）。** 仅 384 CPU verifier 服务器数字；无 GPU 型号/数量/GPU-hour/墙钟/SFT 生成费/镜像 CPU 成本。

**8. 对我们直接可用。**
- 预筛规则可直接改造到 216 题（T0 候选）：用基座 n=8 采样，**删 8/8 全通过题；0/8 题不全删，随机保留一部分**（E11 保留 10%）；保留题量与 0/8 保留率是要拍板的数。
- 评测同时报 avg@4 与 pass@4，固定 Claude Code + 固定轮数/context，前后协议一致；E11 的 Table 4 是这种双指标的样板。
- 区分"廉价修复监督（agentless）"与"真实执行"：我们有镜像，不需要 agentless；但若做 SFT，可参考 agentic non-thinking / agentless thinking 的模式区分。
- **不要照搬**：64 rollouts/prompt；八阶段 cascade；MOPD。

**9. 笔记标注的未知项（§12.2）。** execution RL 总步数、最终题单、硬件/时长、timeout/重试/mask；SWE 评分隔离与精确 reward；固定算力的阶段顺序/多 harness/执行 RL 消融；SFT 卡数与论文数不一致（SWE 439,610 vs 514K；terminal 822,213 vs 490K）。

---

## 5. R2 Nemotron 3 Ultra（NVIDIA 技术报告 2026-06-09）

**1. 来源与版本。** 无 arXiv；官方 PDF 65 页，与本地 `cmp` 相同；HF 四模型 public；Evaluator recipe `@9758d8d5…`（笔记 §1、§9）。

**2. 环境与任务供给。**
- SWE SFT（笔记 §3.2、§4.2；原文 p.17）：任务源 SWE-Gym/R2E-Gym/SWE-rebench/v2；teacher MiniMax-M2.5 thinking 与 Qwen3-Coder-480B non-thinking；scaffold OpenHands/SWE-agent/Mini-SWE-agent/Opencode。轨迹分析器逐条 include/exclude：有效提交、禁用 git 操作（push/pull/fetch/clone/cherry-pick/reflog/fsck/remote/ls-remote）、反复 edit-test 或自我回滚、只探索很少编辑、频繁坏 tool-call、最终 patch 残留 print/pdb/breakpoint、编辑后未测试；阈值/误杀率未给。
- SWE teacher RL（笔记 §4.2；p.22）：Ultra base → agentic SFT → 单步 PivotRL → 多轮端到端 SWE RL；hidden tests 二元 reward；生成 ≤192K、≤200 turns。
- 泄漏防线：容器 git 历史物理重写为 base 时刻 fresh clone（future objects 低层不可恢复）；runtime command filter 拦 remote git 与 GitHub web/raw/Pages HTTP 下载；**不等于完整网络隔离**；隐藏测试投放时点、gold/no-op/替代解、fresh grader 未给。
- Terminal SFT（p.17）：约 370K 多轮 conversations，seed 来自 OpenCodeReasoning/OpenMathReasoning/SWE-bench/SWE-Fixer-Train-110K/SWE-rebench/SWE-smith，在 Harbor Terminus-2 真实执行；terminal-use teacher 任务超时可到 1 小时（p.23）。
- 训练 harness 覆盖（笔记 §8.2；A.2 pp.64–65）：五类垂直任务，每类至少用 Stirrup/OpenHands/OpenCode/Terminus/Droid/custom 中两种。
- RL 软件故障构成（笔记 §7.2；表 7）：56% generation engine failure/timeout、36% sandbox/tool、8% other；无分母。

**3. 数据划分与污染。** 预训练新增截至 2025-09-30 的 173B GitHub code tokens；QA 用公开 train split 作种子、不用 held-out test split（来源策略）（笔记 §2）。ProfBench/PinchBench 只在 final model 评一次，不用于 checkpoint 选择（笔记 §8.1；p.39）。SWE 任务/环境漏斗、测试资格、cutoff、train/dev/test 去重：**未披露**（笔记 §10）。

**4. 难度筛选与采样。** STEM teacher 内部 RL 评测集 3,000 题筛 pass rate 0.25–0.80 且正确解中位长 <64K（笔记 §4.3；p.25–26）；竞赛代码删 teacher 8/8 全对题 → 3.5K（p.26）；RLVR 课程沿 Nano 的 Gaussian approach，未展开（笔记 §3.3）。SWE：达 max turns 或 agent/eval timeout 的未完成轨迹 **mask trajectory loss**（是否进组统计/补采未给）；malformed reasoning/tool-call token 给负 advantage（笔记 §4.2）。

**5. 评测协议（笔记 §8.1–8.2）。** Evaluator SDK；NeMo Gym/Skills/Harbor（AWS ECS sandbox）；模型间 agentic CPU/timeout/prompt/repeats 相同，但 temperature/top_p/max tokens 按各 model card。表 10：TB2.1 56.4、SWE Verified 70.7 / Multilingual 67.7；表 5 中间：SWE Verified SFT 63.5→RLVR 65.8→MOPD1 70.1→MOPD2 71.7（teacher 72.5）；TB2.0 34.5→44.5→50.8→54.0。**图 17 harness 敏感性（p.65）**：同一 Ultra 在 SWE-bench Verified：Mini SWE Agent 2.3.0 65.0、OpenCode 1.14.33 67.3、Pi v0.72.1 70.4、**Claude 2.1.126 60.3**、Hermes 69.9、OpenHands 1.17.0 70.3、Codex 21.1，均 60.6；TB2.1 对应 55.1/46.7/52.1/47.2/52.8/52.6/35.5，均 48.9。ProfBench 16 次、TauBenchV3 8 trials、FAB 200 题 validation。

**6. 基座诊断。** 两阶段通用 SFT（stage1 204,800 samples、stage2 19,200）→ 统一 RLVR 前"刷新数据、做 reward profiling"（笔记 §3.3；p.20，未展开）→ MOPD 前轻量 warmup SFT。训练前基座工具诊断：笔记未提。

**7. 成本口径（笔记 §9）。** 无 GPU-hour/总账；GB200 生产；3K+ GPU 是 GCS 观察规模、1K+ GPU 是 cold-init 测量；MTP k=5 使每步 rollout 生成快 1.46×；PTQ 资源表（4×B300 约 2h / 16×B300 约 45min）仅量化。

**8. 对我们直接可用。**
- 把 SFT 轨迹分析器的规则当**基座诊断清单**：统计 216×8 rollout 中禁用 git 操作、edit-without-test、残留调试打印、反复 edit-test 循环的比例；笔记 §11 提醒这些不能变成永久 RL 资格。
- 镜像泄漏检查：把 216 题镜像 git 历史重写为 base commit fresh clone，并核对是否存在 future objects；Claude Code 联网时拦 remote git / GitHub raw 下载。
- 图 17 说明同一模型 Claude Code 与 OpenHands 差约 10pp → 我们的基座数字必须固定 Claude Code 版本并单列；第二 harness 结果不能混算。
- **不要照搬**：192K/200 turns、1 小时 terminal timeout、多教师 MOPD、Gaussian 课程（未披露参数）。

**9. 笔记标注的未知项（§10）。** SWE 漏斗、测试资格、cutoff、去重；failure/timeout 的 reward/组统计/梯度/补采四件事只确证 loss mask；故障构成分母；SWE 镜像数/CPU-hour/API/flakiness/超时秒数。

---

## 6. R13 Kimi K3（arXiv:2607.24653，本地 PDF 与 v1 技术正文一致）

**1. 来源与版本。** 本地 47 页 PDF（2026-07-27），arXiv v1 2026-07-27 / v2 2026-08-07，技术正文无实质差异；模型卡 `moonshotai/Kimi-K3@f831ab66…`；AgentENV 仓库 MIT（笔记 §1）。

**2. 环境与任务供给（笔记 §5–6）。**
- 白盒 harness：可配置工具接口/system prompt/context management/skills/memories/subagents，可实例化 Kimi Code、Claude Code、Codex、OpenClaw、Hermes；RL 按 task group 动态构造配置；无 commit/消融（§5.1；原文 §4.2.1 p14–15）。
- 知识图谱 DAG 出题；各域 verifier（§5.2；§4.2.3–4.2.7 p15–16）：kernel 数值误差超阈=0、匹配专家=0.5、逼近 roofline→1，惩罚 CUDA graph replay/缓存输入/降精度作弊；AET：独立 verifier 看最终环境状态，**公开 verifier 给诊断、hidden verifier 评 held-out 情境**，提交预算 + penalty；webdev 构建失败/运行错误/伪造产物=0。
- SWE：列为 coding domain，**无漏斗**；全训练+评测共 1,505,678 images / 51,219,741 sandbox creations（含重复启动，不能倒推题数）（§5.3、§6.2；原文 §5.3.2）。
- AgentENV：container / GPU sandbox / Firecracker microVM；checkpoint/resume 最低 133ms/49ms；pause 等推理最多占生命周期 98%；fork 用于评分副作用隔离；6.5× memory overcommit；早期容器曾被 agent 操作引发 kernel panic/deadlock（§6.2）。

**3. 数据划分与污染。** §5.3 明列：数据时间、仓库切分、许可、hints/gold 剥离、污染防控、no-op/golden/替代解、flaky 重复与误杀率**配置不足**；预训练去重 ≠ 后训练 benchmark 去污染（§9）。

**4. 难度筛选与采样。** 无 pass-rate 分带。effort 预算 reward：输出超 τ·b0(x) 得 **−1**（b0 由 cold-start 模型估计；agentic 计累计输出含 reasoning 与 tool-call 参数）（§4.3；p13）；GRM 比较中超过 σ·ℓ0 的候选自动输。partial rollout 暂停阈值 λNK，N/K/λ 未给（§4.1）。构建错误/不可评分/超时/解析错的 reward 与组处理不完整（§5.3）。

**5. 评测协议（笔记 §7.1–7.3；原文 §6.1 p25–27）。** 全部 max effort、T=1.0；单步 top-p 0.95、agentic top-p 1.0。Coding 用 Kimi Code/Claude Code/Codex 之一；**Terminal-Bench 2.1 对所有模型取跨 harness 最好分**；DeepSWE v1.1 自测 67.5（官方 mini-SWE-agent 67.3）；SWE-Marathon 用 2026-07-09 H20 校准 branch；PostTrainBench Harbor/H20 三次均值；FrontierSWE 2026-07-16 官方脚本重算 dominance；BrowseComp 300K 触发 compaction 91.2 vs 1M 无 CM 90.4；MCP-Atlas 500 题公开子集、100-turn、Gemini 3.1 Pro judge；视觉三次均值。表 2：Terminal 2.1 88.3、DeepSWE 67.5、FrontierSWE 81.2、SWE-Marathon 42.0。内部 bench（KCB 80 题等）持续更新、属开发诊断非 holdout；有 fallback/拒答脚注。多数项无预算/seed/CI。
- 每题推理费用（§8；§6.4 图 13）：KCB2.0 相对 Fable/Claude Code 低 4 分、38% 费用；BrowseComp $2.03/题。

**6. 基座诊断。** SFT 冷启动来自此前 Kimi 领域模型合成的长程轨迹 + 多阶段验证 + 人工标注（§3）；b0/ℓ0 由 cold-start 模型估计（一种预算校准）。训练前基座工具诊断：笔记未提。

**7. 成本口径（§8）。** 只有每题推理美元；每 1M-context RL 实验控制在"几百 GPU"（无型号/数）；无 GPU-hour、教师费、每题生产成本。

**8. 对我们直接可用。**
- "公开诊断 vs 隐藏评分"分工：216 题只把仓库既有测试暴露给 agent，官方 F2P/P2P 作 hidden verifier；在可信投影上跑 no-op/参考解/不完整解/替代解/parser 攻击样例并报误奖励/误杀（笔记 §10.2 第二行）。
- 基座诊断按任务族记生成/训练 token、discard、wall time、成功率（笔记 §10.2 第三行）；是否引入 −1 预算 reward 由自己实验定，不因 K3 有就改 reward（T0）。
- 评测口径：K3 的 TB2.1 是跨 harness 取最优，不可与固定 Claude Code 的分数横比；我们必须写明 harness。
- **不要照搬**：microVM/KV 池/fleet；九专家；effort −1 reward。

**9. 笔记标注的未知项（§9）。** SWE 漏斗/时间/仓库切分/许可/gold 剥离/污染；no-op/gold/替代解/flaky 率；失败 reward 规则；N/K/λ、τ/σ/b0。

---

## 7. R4 MiniMax-M2 Series（arXiv:2605.26494 v1/v2）

**1. 来源与版本。** v1 2026-05-26、v2 2026-07-30，35 页；仅 `app.tex`（贡献者名单）变化；N10 是另一篇官方文章（笔记 §1）。

**2. 环境与任务供给（笔记 §3）。**
- SWE 六阶段（§3.1；原文 §4.1.1 p7–9、Fig.3）：宽松许可公开 GitHub PR + issue + diff + tests → 逐 PR Docker 构建（env agent 用专家知识与执行反馈迭代修脚本；**非 Python 较不可靠**，难点 Java/Go/Rust/C++ 工具链版本、异构测试接口；十余种语言，**无逐语言成功率**）→ 任务类型 tagging/routing → 测试 reward → 模型检查题意与测试一致性 → 任务转换扩增。类型与接受信号：bug fix = 提取 F2P/P2P、golden patch 通过才有效、solver sandbox 同时验修复与回归；feature addition = 新功能测试点 + golden 通过；performance = P2P 稳定 + 性能差异稳定显著（重复数/阈值未给）；bug injection / commit merging；SWE-Test（写 pre-patch 失败 post-patch 通过的测试）；code review（**无 runnable env**，第二 LLM 一致性）。
- AppDev（§3.2）：专家 meta queries、MinHash 去重、LLM 过滤；AaaV 三层验证（执行层硬门：文件/语法/依赖/构建/服务/HTTP/JS 错误；交互层 Playwright；视觉层），每项二值 pass/fail 要证据。
- Terminal-Gym（§3.3；§4.1.3 p11–12）：完整 Stack Overflow → 去无 accepted answer/低分/过长 → 按 tag 留终端操作/系统配置/调试/脚本 → 标注质量/类别/可验证性/复杂度/环境，仅留可脚本化、terminal、可验证、Linux/Docker、难度适中 → 改成结构化任务，四档留前两档 → agent 合成 Dockerfile + 测试脚本，失败返回结构化诊断迭代至通过或**达最大重试数（值未给）** → 有控制地删 hints/路径/预期输出、同一套 LLM 测试 → **排除过易任务，偏好 hints 少且 zero-shot pass rate 低的变体，参考 reference solver 历史通过率与环境修复次数**（solver 身份/重复数/区间未给）。
- 漏斗数字：原始仓库/PR、有效环境、验证任务、轨迹、RL 消费**均未给**（§3.4）。

**3. 数据划分与污染（§3.4、§4.1）。** SWE 宽松许可；AppDev MinHash；**GDPval seed 用于训练同时评 GDPval-AA，无去重/切分说明**；无全局 repo/time split、benchmark 去污染、测试不可见性证明。

**4. 难度筛选与采样。** Terminal-Gym 排除过易、偏好低 zero-shot pass（见上）；推理数据按阶段/难度饱和/弱项动态调 query/response 比例（§4.2）；混合领域课程各域 context 逐阶段变长、难度变难（§5.4；§6.1.6 p18–19）。Reward 含过程项、完成速度项（h 单调递减于 T_completion/T_baseline）、任务表现项（§5.3）。

**5. 评测协议（§7.1；原文 §8.1 p26–27）。** 默认 T=1.0、top-p 0.95。SWE-bench Pro/Multilingual/Multi-SWE/NL2Repo：内部设施、**Claude Code 统一 scaffold 并覆盖默认 system prompt**、GPT-5.4 用 native CodeX、**4 trials 平均**；scaffold 版本/token/时间 cap/split 未给。Terminal-Bench 2.0：Terminus-2 XML、`zai-org/terminal-bench-2-verified`、**8 vCPU/16GB、2h timeout、4 trials**。VIBE-Pro 3 trials、Claude Code verifier。MLE Bench Lite：22 competitions、每题单 A30 24h、3 trials → 66.6%（最佳 run 15/22=68.2%）。表 4：SWE-bench Pro 55.4→56.2、Multilingual 74.1→76.5、Multi-SWE 51.3→52.7、TB2.0 51.7→57.0、**MMLU-Pro 85.2→81.8 退化**。无误差条。

**6. 基座诊断。** SFT 学 interleaved thinking 轨迹作 RL 冷启动（§2 第 2 条；原文 §5 p16）。训练前基座诊断：笔记未提。§7.4 自演化 harness（30%–50% 日常迭代、100 轮 scaffold 改进内部提升 30%）是运行工作流，非基座诊断。

**7. 成本口径（§8）。** 无；1,584 A30-hour 只是评测沙箱满额上限；40× 训练加速无 baseline/硬件。

**8. 对我们直接可用。**
- 216 题都是 bug-fix 类型，与 R4 的 bug-fix 接受信号（F2P/P2P + golden 通过 + solver 沙箱验修复与回归）一致；按笔记 §9 第一行做 golden/no-op/替代解 + 失败分类，并记候选→消费漏斗。
- 评测模板：Claude Code 统一 scaffold、覆盖默认 system prompt、4 trials 平均、记录 vCPU/内存/timeout（R4 TB 用 8 vCPU/16GB/2h）——我们 Docker 资源与 timeout 需固定并写入协议。
- Terminal 补充评测若做，采用 `terminal-bench-2-verified` + Terminus-2 的固定资源口径；Terminal-Gym 的"低 zero-shot pass + 少 hints"选题法留作后续。
- **不要照搬**：多领域 cowork verifier、速度 reward、GDPval 式 seed 与评测同源。

**9. 笔记标注的未知项（§8）。** 各环节数量；逐语言构建成功率；terminal 重试上限；时间范围/许可；GDPval seed 去重；scaffold 版本、token/时间 cap、benchmark split；超时/坏环境/截断 reward。

---

## 8. E10 Intern-S2-Preview（arXiv:2608.13505v1）

**1. 来源与版本。** arXiv:2608.13505v1，2026-08-13；35 页、无附录；HF 卡 `internlm/Intern-S2-Preview@4f57cab5…` 是 **35B**（≠ 论文 397B）；xtuner `@76e70513…`（笔记 §1）。

**2. 环境与任务供给（笔记 §5）。**
- Table 1（p.17）公开来源库存（tasks / environments）：SWE-bench/SWE-smith 59,136/222；**SWE-Gym 2,438/2,401**；R2E-Gym-V1 7,480/8,101；SWE-rebench-V2 32,100/32,075；Scale-SWE 20,200/19,472；Nemotron-Terminal-Synthetic-Tasks 80,000/8；ClawGym-Task 13,500/1。归一化：物化 base repo/container/assets，issue→目标，原 tests/reward program 保留为 verifier。**无逐源"候选→构建→gold→可解→消费"、跨源重叠、采样比例、revision/许可、split**（§5.3）。
- Harness×task：黑盒 OpenClaw、Claude Code、OpenCode、OpenHands、Mini-SWE 经原生 CLI/SDK/API 接入；Shared Sandbox Provider 抽象环境，容器/网络权限/fresh grader 拓扑/TTL 未给（§5.1）。
- 社区 skill 合成（§5.4）：过滤不可执行/不安全/低质/冗余 skill；skill-state graph 组合；environment→instruction→verifier 每阶段可执行 validator；失败局部 repair；离线轨迹错误步骤标 `skip` 不进 imitation loss。
- **Verifier integrity（§5.6；原文 §4.4.3 pp.19–20）**：gold patch、held-out tests、精确 scoring test IDs 不放 workspace；git history 清为单 baseline commit、删 remote refs、必要时去掉暴露 upstream issue 的 task ID；agent 停止后恢复/覆盖 canonical tests 并应用 gold test patch；SWE all-correct（target-fix + regression 均过）；有 canonical expected test-state map 的任务要求精确匹配；**缺 grading 工件/执行故障/verifier 输出不可解析单独记账，与任务失败分离**。无 no-op/gold/替代解数量、重复评分稳定性、误杀率、网络隔离。

**3. 数据划分与污染。** 未给 repo/time split、去重、污染评估（§5.3）。

**4. 难度筛选与采样。** 推理 RL 在线丢弃 reward 全同组并补采（§4.2）；agentic 过程 annotator 对 parse/格式、工具名/参数错、重复或失败调用、context/turn/session limit 终止加 `adv_penalty`（不改 reward/labels）（§5.5；Eq.30 p19）。无 pass-rate 分带。

**5. 评测协议（§8.2；原文 §5.1–5.2 p22–25）。** SciCode 49.11；SGI-Bench 49.37；ResearchClawBench 18.44（ResearchHarness v0.0.49，40 题）；SkillsBench 50.03（OpenClaw 2026.5.7，87 题）；**Terminal-Bench 2.1 67.42**（Terminus 2；89 题；28 题较 2.0 修订；部分取自 AA）；**SWE-Bench Pro 61.56**（Mini-SWE-Agent；**修改官方 eval image 防 git log 暴露 ground truth**；1,865 题/41 repo 为总库描述，实际 split 未写）；Multilingual 81.67（Mini-SWE-Agent；300 题/42 repo/9 语言；F2P+P2P）；WildClawBench 44.68。对照 GLM-5.2 TB2.1 77.90、Claude 84.60。预算/重复未给。Fig.11 训练曲线（160 steps，SWE 面板含 Claude Code/Mini-SWE/OpenClaw/OpenCode/OpenHands）有先降后升，local smoothing、无 seed。

**6. 基座诊断。** 广域 SFT（含安全、工具、长 horizon 轨迹；Intern-S1-Pro 等 rejection sampling 生成 CoT，人工验证）→ 同一 SFT 分叉两专家（§3）。训练前基座诊断：笔记未提。

**7. 成本口径（§9.1）。** 四类成本均无 GPU×时长或金额。

**8. 对我们直接可用。**
- §5.6 是最贴近我们二元 F2P/P2P 的 verifier 完整性清单，可逐项落到 216 镜像：workspace 剥离 gold/test patch/评分 test ID；单 baseline commit + 删 remote refs；run 后恢复 canonical tests 再打 gold test patch；all-correct 语义；**infra 故障与任务失败分账**（这正是我们"剔除面"登记要求）。
- 检查 SWE-Gym Lite 镜像 `git log` 是否暴露修复 commit（E10 为此改了 SWE-Bench Pro 官方镜像）。
- 基座诊断失败分类直接用 §5.5 的类别：parse/格式、工具名/参数、重复或失败调用、context/turn/session 上限终止——首版只统计，不做 adv_penalty。
- **不要照搬**：skill-graph 合成；GEPO/长度正则；两专家 OPD。

**9. 笔记标注的未知项（§9.2）。** 逐源漏斗、重叠、采样比例、split/去重/污染；no-op/gold/替代解/flaky 统计；重复评分稳定性；评测预算/重复/温度。

---

## 9. R5b GLM-5.2 官方文章（HF blog 2026-06-17）

**1. 来源与版本。** HF Team Article `zaiorg/glm-52-blog`（页面标 2026-06-17）；模型卡 `zai-org/GLM-5.2`（Footnote 提交 2026-06-23）；GitHub `zai-org/GLM-5@008de4db…`；**原技术图/曲线与登记 PDF 未取得**（笔记 §1）。

**2. 环境与任务供给。** 长程 coding-agent 训练场景扩展到复杂实现、自动研究、性能优化、调试；**任务数/仓库数/token/生成器/质量漏斗未披露**（笔记 §2.1）。反作弊（§5.2；U Anti-Hack 段）：每步工具请求 → 规则筛查（提高召回）→ LLM judge 判意图（提高精度）→ 违规则**阻断该调用、返回 dummy observation、任务继续**；同一模块用于 RL 与评测；例子含读评分材料、复制上游提交答案、直接取目标源码。检测器精度/召回/成本、违规动作是否负 reward/mask、hidden grader 是否隔离均未披露（§5.3）。

**3. 数据划分与污染。** 笔记未提（§9.2：验证漏斗、去污染、合法多解检查"正文未披露"）。

**4. 难度筛选与采样。** 笔记未提。

**5. 评测协议（§7；B/M Footnote）。**
| 评测 | harness / 资源 | 采样与限制 |
| --- | --- | --- |
| SWE-bench Pro 62.1 | OpenHands，tailored instruction | T=1，top_p=1，max_new_tokens 32k，context 400K |
| NL2Repo 48.9 | 规则+LLM 阻止恶意操作 | 48k / 400k |
| DeepSWE 46.2 | 官方 pier + mini-swe-agent；2 CPU/8GB；隔离无网 | T=1，top_p=1，timeout 2h，400K |
| ProgramBench 63.7 | 200 题；**Claude Code 2.1.156**；4 CPU/8GB；无网 | max_tokens 64000，max_turns 2000，sample_timeout 6h，effort max，400K |
| TB2.1 Terminus-2 81.0 | parser=json；4 CPU/8GB | timeout 4h，max_new_tokens 48k，max_episodes 500，256K |
| TB2.1 Claude Code 82.7 | **2.1.167**；保留每题 CPU/mem；**5 runs 平均** | T=1，top_p 0.95，max_new_tokens 131072；透明代理把 CLI 64k 输出上限改 128k；**取消 wall-clock** |
| MCP-Atlas 76.8 | 500 题 public；Gemini-3.0-Pro judge | 每题 10 分钟 |
| FrontierSWE/PostTrainBench/SWE-Marathon | Proximal / PostTrainBench / Abundant AI 执行 | 1M context，effort max，最大输出 128K |
5.1 基线 TB2.1 Terminus-2 63.5（C/D 文字写 62.0）。跨载体冲突：CritPt 16.7 vs 20.9；MCP-Atlas 76.8 vs 77.0；GPT-5.5 PostTrainBench 28.4 vs 25.0（§8.2）。

**6. 基座诊断。** 笔记未提。

**7. 成本口径。** 仅"OPD 阶段约两天"（无卡数）（§4.2）。

**8. 对我们直接可用。**
- 评测记录 schema：每个 benchmark 记 harness+版本（如 Claude Code 2.1.167）、CPU/内存、timeout、max_new_tokens、max_turns、context、runs 数——直接复制到我们基座诊断的运行记录（笔记 §10.2 第三条）。
- Claude Code 细节：其 CLI 有 64k 输出限制，GLM 用透明代理改 128k 并取消 wall-clock——我们在 Docker 里跑 Claude Code 时要先确认对 30B 的输出上限与 wall-clock 是否成为截断来源。
- 反作弊探针：比较"违规即结束"与"阻断该调用后继续"的合法完成率、后续违规率、误报与成本，再决定 reward（笔记 §10.2 第二条）；属 T0。
- **不要照搬**：1M context；critic-PPO；>10 专家 OPD；"两天"当预算。

**9. 笔记标注的未知项（§9.2）。** 任务/仓库/镜像/轨迹数、合成与人工占比、验证漏斗、去污染、合法多解；检测器精度/召回/成本、训练惩罚、mask、最终评分、guard-off 效果；原图。

---

## 10. R5c GLM-5.3 官方文章（预读，未完成）

**1. 来源与版本。** 官方博客 `z.ai/blog/glm-5.3` 与开发文档**均未取得正文**；仅核 GitHub README `zai-org/GLM-5@008de4db…`（2026-09-01）与模型卡搜索片段；状态"未完成精读，不能计入已读"（笔记 §1）。

**2–4.** 环境/任务供给、划分/污染、难度筛选：**未核验**（不是"未披露"）。U 登记待核主题（§3）：真实工作模式→长程可执行环境、judge 检查可解性；verifier 不看 reference；oracle / no-op / unsolved-state 检查；solver 轨迹审计；SAO+compaction；logprob 差 `1e-7`；吞吐 `>2.3×`——**全部未从原文核得**。

**5. 评测协议。** 未核验；仅 README 声明：与 GLM-5.2 同 base、增益来自后训练；内部 Z.ai Code Bench 改善约 50%（分母未知）；CyberGym 领先、利用类 benchmark 相对 5.2 超两倍（§2.1、§2.4）。接口：`reasoning_effort=low/high/max` 默认 max；`clear_thinking` 默认 false（§2.3）。744B-A40B；Flash 320B-A18B 是另一 base（§2.2）。

**6. 基座诊断。** 未核验。

**7. 成本口径。** 未核验。

**8. 对我们直接可用。** 目前只有方法论纪律：待核问题清单（§3 右列）可作为我们读到原文后的核对模板；"未核验"与"未披露"必须分开标注。**不要**引用 `1e-7`/`>2.3×` 当一手事实。

**9. 未知项。** 全部（§1.2 表）。

---

## 11. Nemotron-Terminal 数据工程（arXiv:2602.21193v1）

**1. 来源与版本。** arXiv 2602.21193v1，2026-02-24，24 页；HF collection；Corpus `@a1667c4f…`（2026-02-27）；Synthetic-Tasks `@7e53648e…`；8B 模型卡 `@bb141357…`（笔记 §1、§8.1）。

**2. 环境与任务供给（笔记 §3）。**
- Dataset adapters（§3.1；原文 §4.1 p5）：Math 约 163K prompts（Cascade Stage-2）；Code 79K→约 35K；SWE 127K instances（SWE-Bench-Train、SWE-reBench、SWE-smith、SWE-Fixer-Train）→约 32K unique prompts；规则适配为 Terminus 格式 + suffix（写 `/app/solution.txt|py|patch`）。**adapters 只有 instruction 与 environment，没有 test cases**（§4.1.2）。
- Seed-based（§3.2）：重新生成任务 + pytest，参考解只供出题者设计测试、不给 solver。Skill-based（§3.3）：九领域模块、每题 3–5 项 primitive skills；模板输出 `prompt/tests/weights/info/files/test_requirements`（Fig.11 p19）。
- 任务包（§3.4；§4.2.3 p7）：说明 + 带权重 pytest + 输入文件 + 领域 Docker；**明确不生成 oracle solutions**（自动生成可信 ground-truth 难）；"solution isolation"只指 prompt 不含解法；**九个预构建基础镜像**，agent 仍可装依赖；无镜像 digest/构建成功数/耗时对照。
- 数量（Table 5 p10；A.1）：adapters 162,692 / 31,960 / 31,661 = 226,313；seed 124,366；skill 139,841；synthetic 合计 264,207；两路线合计 490,520 样本（轨迹）；公开 Corpus 366,154 行（adapters + skill，不含 seed）。轨迹 tokens 均值 17,507 / 17,363，turns 均值 17.5 / 16.3（Fig.5–6）。
- Teacher：DeepSeek-V3.2 出题并在 Terminus 2 生成轨迹；生成用 Harbor + Singularity（HPC，fakeroot overlay 少量失败可接受）；评测用 Daytona（§4.1、§5.2）。Teacher 校验 Table 2：AIME 93.33、LCB v6 67.20、SWE-bench Verified 52.40、TB2.0 38.2±2.9。

**3. 数据划分与污染（§3.6；§4.4 p8）。** 移除与 TB2.0 test samples 有 **14-gram** 重叠的 prompt；基础过滤（身份泄漏、含中文字符）；tokenizer/规范化/去除量/派生关系切分未展开。

**4. 难度筛选与采样（§7）。** Adapter complete-only vs no filter：All 8.09 vs 9.66（Math 反而 7.19 vs 5.39）；Synthetic：complete-only 6.74（保留 39.6%）、success-only 5.06（31.6%）、no filter 12.4（100%）——**无等 token/等更新对照**；上下文 Table 8：32K 训 / 40K 评 13.0，65K 训 10.3，YaRN2 11.9；课程 Table 9：单阶段混合 13.03 vs 先 adapters 后 synthetic 10.39；数据规模 Fig.4：0/10/100% 约 2.5/9.5/13.0（8B）。SFT 配置 §5.1：lr 2e-5、2 epochs、32,768 seq、batch 128、32 GPU（8B/14B）/128 GPU（32B）、veRL。

**5. 评测协议（§6；§3.1、§5.2）。** TB2.0，89 题，Terminus 2，Daytona。Table 3：Qwen3-8B 2.47±0.5→13.0±2.2；14B 4.04±1.3→20.2±2.7；32B 3.37±1.6→27.4±2.4；开放参照 Qwen3-Coder-480B 23.9、MiniMax M2 30.0、Kimi K2 Thinking 35.7、DeepSeek-V3.2 38.2。**± 未绑定统一统计定义（Fig.4 单独标 95% CI）；无重复次数/温度/turn 上限/timeout/effort**。Table 4 类别：SE（24 题）32B 5.00→31.7；Scientific Computing 32B 2.90→0（回退）；Math/Games/Video 全零；单题类别不能外推。

**6. 基座诊断。** 基座 Qwen3 在 TB2.0 仅 2.5–4%；teacher 三项外部 benchmark 作 teacher 选择证据（非学生迁移）。这是 SFT-only 论文，RL 列未来工作（§2.2）。

**7. 成本口径（§9）。** GPU 数有、型号/时长/费用无；API 费无；构建成功率无。

**8. 对我们直接可用。**
- Terminal 补充评测直接用 TB2.0（89 题）+ Terminus 2 作固定参照面，自行做重复以补 ± 定义；按类别报，预期部分类别为零。
- "SFT 资产 ≠ RL 任务资格"：Corpus adapters 无 tests、synthetic 无 oracle → 若将来引入 terminal 训练题，必须补 tests + oracle/no-op 检查后才能进二元 reward RL（笔记 §10 第二行）。
- 基础镜像复用思路：216 题来自 11 仓库，可评估"11 个仓库基底镜像 + 每题薄层"是否比每题独立镜像省构建/存储（笔记 §10 第一行）。
- **不要照搬**："no filter 更好"当作失败轨迹独立价值证据；32K 截断作 horizon 策略；128 GPU 规模。

**9. 笔记标注的未知项（§9）。** 候选量/构建成功率/镜像大小；teacher API 费；loss mask；± 定义；每题 CPU/RAM/时限、重跑规则；oracle/no-op/替代解/flakiness/隐藏 grader 隔离实证。

---

## 12. O01 SkyRL-Agent / SA-SWE-32B（arXiv:2511.16108v1）

**1. 来源与版本。** arXiv 2511.16108v1，2025-11-20，16 页（Work in Progress）；代码 `NovaSky-AI/SkyRL@0b286bac…`（2026-09-05，晚论文约十个月）；模型 `NovaSky-AI/SA-SWE-32B`（笔记 §1）。

**2. 环境与任务供给（笔记 §4）。** **4.5K R2E-Gym instances**；Qwen3-32B（dense）直接 RL；每 batch 64 tasks × 8 rollouts；评测选 step 125 checkpoint。真实仓库交互、提交 patch 后按项目测试判定；**F2P/P2P 清单、评分隔离、反作弊、替代解、flakiness 未给**；无原始 PR→环境漏斗（引用 R2E-Gym）。训练期加入 AST 搜索工具（LocAgent 式，含下一步查询提示）与恢复 hints（工具失败后动作、临近 step/context 预算、缺失/错误函数调用、检查失败编辑）（§4.2–4.3；原文 §3.4、§4.2 pp.7–9）。Init→Run→Eval 三阶段调度；Async Pipeline vs Async Batch(Bounded) 在 64 任务×8 rollout、2×8 H100 上 generation 阶段约 1.55×，GPU util 约 90%（§3.2；Fig.1(b)）。

**3. 数据划分与污染。** 未披露 manifest/revision/仓库切分/污染核验（§4.1 表、§9）。Deep Research 中在线检索能直接找到公开答案，屏蔽 HF/GitHub/GitLab/Chegg 域名（§7.1）。

**4. 难度筛选与采样。**
- SWE：无难度筛选披露；训练初 **50/64 none-resolved**（任务组尺度）（§4.2）；平均搜索调用 3→4、turns 18→25（§4.3 p11）。
- Deep Research（§7.1；§5.1 pp.11–12）：50K 候选，Qwen3-8B thinking 每题 4 次离线 rollout 分层：0/4 Impossible 25%、1/4 Hard 30%、2/4 Medium 30%、3/4 Easy 15%、**4/4 不纳入**；最终题数未给。
- Horizon 处置（§5.2；§4.2 p9）：因外部 context/turn 上限停止的轨迹，**reward 与 advantage 统计不变，只屏蔽该样本梯度**；reward 不必为 0；未给分母 D 与全 masked 组补采。当前代码 finish reason（context、max iterations、runtime、evaluation、bad response、loop、cmd timeout）置零 loss mask 但保留 reward；空结果 fallback 深拷贝同 instance 其他结果（§8.4–8.5）。
- 训练限制：32K context、50 turns；lr 1e-6；LOO；KL/entropy 关（§5.1）。

**5. 评测协议（§6；Table 2–3 p10）。** Simple ReAct：bash + file editor（OpenHands ACI），**40K context / 100 steps**，每实例一份 patch，无 AST。SWE-Bench Verified：Qwen3-32B 24.4；SA-SWE-32B 39.4；DeepSWE 36.4（reported 42.2）；Qwen3-Coder-30B 45.0；SWE-agent-LM-32B 38.0（reported 40.2）。H100-hours 4,601 vs DeepSWE 9,180（约减半）。迁移 Table 3：Terminal-Bench **v0.1.1、80 题、OpenHands** 13.75→16.25；BrowseComp-Plus 18.1→19.4（turns 3.68→4.60）；WebArena 15.8→17.0；无重复/CI。Deep Research HLE-500 judge 敏感：general verifier 12.6→18.8，gpt-oss-20b 9.2→10.2/11.0（§7.1）。Computer use：训练 reward 上升、validation 几乎不改善（§7.3）。

**6. 基座诊断（§4.2）。** 观察到较弱模型反复 `view` 分块看文件、不善用 grep/find、无关内容占满上下文 → 加 AST 搜索；起始 50/64 未解决；base 24.4。无 SFT（"pure RL"）。

**7. 成本口径（§6.3、§7.1）。** 4,601 H100-hours（不含 CPU runtime/API/任务构建/评测/失败尝试）；Fig.1(b) 16 H100 仅该对照；Deep Research summarizer 服务 2,101.6 s/iter（单 H200 Qwen3-32B）→592.1 s/iter（Qwen API）。

**8. 对我们直接可用。**
- 基座诊断模板：216 题×8 先测 none-resolved 任务比例（对应 50/64）、每题平均 turns、搜索/查看类调用比例、上下文占用来源（是否被 view 输出填满）——判断瓶颈是定位/工具误用还是根本采不到成功路径（笔记 §10.1 第二行、§10.2 第一条）。
- 为我们的 Docker 分别计时 init（容器起）/run/eval（测试）三段，用于设定并发与找出等待空洞（§10.1 第一行）。
- Horizon 语义三分（reward / 组成员 / 自身梯度）必须在 C 包明确；O01 给出"保组屏蔽"与"删后重算"数值差异的算例（§5.2）；属 T0。
- **不要照搬**：注入 AST 工具（Claude Code 自带 grep/glob）；1.55× / 4,601 h 作预算；32B dense 的无 SFT 结论推到 30B-A3B。

**9. 笔记标注的未知项（§9）。** 精确 SWE 数据与划分；环境筛选漏斗与评分隔离；horizon 命中率；reward 为零/未完成 patch/超时/补采合同；AST/hints 独立增益；10.2/11.0 含义。

---

## 13. R14 CompactionRL（arXiv:2607.05378v1）—— 只取任务/评测/预算设定

**1. 来源与版本。** arXiv 2607.05378v1，2026-07-06，13 页；slime 训练；Harbor + Terminus-KIRA 评测（笔记 §1、§3.3）。

**2. 环境与任务。** 训练数据 **SWE-Dev 开放训练数据**（release/split/实例数/镜像数未给）；30B 分支 = GLM-4.7-Flash 直接 RL；106B 分支 = GLM-4.5-Air 先用 GLM-4.7 轨迹 SFT（§3.1–3.2；原文 §5.1 p6）。终局 R 由任务正确性决定，F2P/P2P/hacking/flakiness 实现未给。

**3. 数据划分与污染。** 未披露（§3.2）。

**4. 长程/截断/上下文预算设定（§6.1；§5.1 pp.6–7、Table 3）。** 峰值上下文 30B 64k / 106B 80k；压缩触发 = 剩余 <10,240 tokens；保留最近 k=2 交互；每 rollout 至多 3 次压缩（"有效预算 4×Peak"是命名额度，非 token 总数）；单次 assistant 响应 ≤10,240；评测 interaction turns ≤250；T=1.0、top-p=1.0；global batch 128、group=1。Long 对照 = 2×Peak 不压缩。

**5. 评测协议与结果（§6.2、§7.2–7.5；Table 1–3、Fig.3）。** SWE-bench Verified **随机 200 题子集**、TB2.0 全量；Pass@1 = 两次评测均值；无题单/seed/CI。Table 2（64k）：GLM-4.7-Flash SWE Single 47.5 / Comp 50.5，TB 14.6 / 13.4；+RL 无压缩 50.0/48.0、16.9/12.4；+CompactionRL **43.7/56.0、16.9/20.2**（single-window 退化）。Table 3 反例：无压缩 128k 训练在 TB Comp 23.6 高于完整方法 20.2、SWE Long 59.0。外部参照行：**Qwen3-30B-A3B-Instruct-2507，256k Single：SWE 25.2、TB2.0 5.34**（Terminus-KIRA）；Qwen3-Coder-30B-A3B-Instruct 51.9/14.6。Table 1 换 summarizer：Qwen3.5-27B 55.5、GLM-4.7-Flash 50.5、Qwen3-30B-A3B 49.0（每 trace 摘要 1.010/1.075/1.126 次）。Fig.3（106B）：compactions/trace 0.21–0.58、tool calls/trace 48.2–90.8、触发压缩任务 Pass@1 29.0–47.7。

**6. 基座诊断。** 笔记未提（critic 50 步 value 预训练不是基座诊断）。

**7. 成本口径。** 无 GPU/CPU/API（§8）。

**8. 对我们直接可用。**
- 先测量：216 题 × Claude Code 下每 trace 是否触发上下文压缩、压缩次数、tool calls、总 token（对应 Fig.3 三个量）；笔记 §11 原话"已有数据若很少触发压缩，先补足基线比接入完整 CompactionRL 更可解释"。
- 若 Claude Code 开启 compaction，评测同时报 Single-window 与 compacted 两个面（R14 显示压缩训练后单窗口退化）。
- 粗锚点：Qwen3-30B-A3B-Instruct-2507 在 Terminus-KIRA/256k 单窗口 SWE-bench Verified 25.2、TB2.0 5.34；30B-A3B 级别 RL 后 comp 56.0（GLM-4.7-Flash 底座）。
- **不要照搬**：critic-PPO；250 turns/64k；200 题子集分数当全量。

**9. 笔记标注的未知项（§9.4）。** SWE-Dev release/split/实例数；overlong 率；200 题 ID/seed/原始两次结果；超时/parser 错/窗口溢出/三次压缩耗尽处置；GPU/CPU/API 费用。

---

## 14. R15 SAO（arXiv:2607.07508v1）—— 只取任务/评测/预算设定

**1. 来源与版本。** arXiv 2607.07508v1，2026-07-08，14 页，CC BY 4.0（笔记 §1）。

**2. 环境与任务（§3.2）。** Coding 分支：**Qwen3-30B-A3B-Thinking-2507 直接 RL**（不经 TIR SFT）；SWE 训练任务集名称/数量、环境构建、工具可见性、reward 函数、超时处置**均未披露**；OpenHands 为 SWE-Bench Verified scaffold。数学分支：GPT-OSS-120B 生成 TIR 数据 3 epochs SFT。

**3. 数据划分与污染。** 未披露（§3.1–3.2）。

**4. 预算设定（§6.1）。** 最大训练长度 128k；SWE 300 interaction turns、128k context；DIS 区间 coding ε_low/high 0.8/3.0 → (0.2, 4.0)；数学 50 turns。

**5. 评测协议（§6.2、§6.4；Table 2 p6）。** top-p=1.0、T=1.0、最大生成 128k；SWE ≤300 OpenHands turns；数学 AIME/HMMT/IMOAnswerBench 16 次运行均值、BeyondAIME 4 次；**SWE 重复次数/误差条未给**。SWE-Bench Verified：输入模型 **23.0** → GRPO+DIS **27.0** → SAO **29.8**。

**6. 基座诊断。** 笔记未提；输入模型 23.0 是基座锚点。

**7. 成本口径（§8.1）。** 无 GPU 型号/数量/GPU-hour；无 SWE 环境成本。

**8. 对我们直接可用。**
- 期望值锚点：同为 30B-A3B（Thinking-2507）在 OpenHands/300 turns/128k 下 23.0，GRPO+DIS 一轮 +4pp；我们首批小规模用 Claude Code 应以此量级设定"有无学习"判据，而不是期待两位数提升。
- 评测固定 top-p=1/T=1/128k，并**自行补 SWE 重复次数**（SAO 未给）。
- **不要照搬**：single-rollout + critic；DIS 区间数值当我们的 faithful DIS 参数。

**9. 笔记标注的未知项（§9）。** SWE 数据、reward、grader、超时、重复、后端、成本。

---

## 15. N07 SDPO（arXiv:2601.20802v2）—— 任务、失败反馈构造、评测

**1. 来源与版本。** arXiv 2601.20802v2，2026-02-16，50 页；代码 `lasgroup/SDPO@7c457fc1…`（2026-07-01，基于 verl）（笔记 §1）。

**2. 用了什么任务（§2.2、§5.1、§6.1、§7.2）。**
- §3：SciKnowEval L3 四科（Chemistry/Physics/Biology/Materials）+ ToolAlpaca（API spec→调用）；**按题 train/test split**；Qwen3-8B、Olmo3-7B-Instruct。
- §4：**LCBv6 2025-02～05 子集 131 题**；随机取原 private tests 的 50% 作训练可用 public tests，"private tests 验证"；**未把 131 题分成训练/未见验证题**；代码 `data/split_tests.py`：`test.json` 保留完整 tests、`train.json` 保留一半 → 验证含已暴露一半（§10.1）。
- §5 TTT：按 Qwen3-8B 定义 hard（pass@64<0.5）、very hard（<0.03），再只保留三种方法中至少一种在 512 steps×5 seeds 内解过的题 → 19 hard / 9 very hard；Q9 因环境 rounding 验证问题被删。

**3. 失败反馈如何构造（§4.1；Table 2 p5；§6.6 Table 6 p13；F.3）。** 教师输入 = 原题 + （若有）同组学生成功解 + （若失败且无成功解）执行反馈 + 求解要求；教师 assistant 段放**原回答 y** 重算概率（不生成新答案）。反馈内容：编译/运行错误类型、行号、失败输入、实际与 expected output；MemoryError/IndexError 给堆栈与最后输入（过长截断）。Table 6（step 60）：仅环境 output → 39.9；仅 own solution → 42.6；两者 → 48.3；再加完整失败回答 y → 44.5（锚定，entropy 0.23）。代码默认排除"用自己的成功回答指导自己"，与 Table 2 不同（§10.2）。

**4. 难度筛选。** hard/very hard 由基座 pass@64 定义；LCB 官方 easy/medium/hard 分层增益 +1.6/+8.8/+7.3pp（Fig.15，训练期平均）。

**5. 评测（§5.1、§6.1、§6.5、§7.3）。** §3：avg@16，报 1h/5h 墙钟内最高验证分（不含初始化/validation）；§4：avg@4、3 seeds、validation T 0.6/top-p 0.95；LCBv6 27.9→41.2（GRPO）→48.8（SDPO）；Table 5 holdout（IFEval/ArenaHard/MMLU-Pro）均值 43.5→42.4（仍低于基座）；§5：discovery@k、5 seeds、bootstrap 90% CI；2750 generations 下 very hard SDPO 53.2 / best-of-k 41.5 / multi-turn 35.6；Table 10 逐题均值 hard 894 vs 1145/1141。

**6. 基座诊断。** 基座 pass@64 用于任务分层；Table 11：初始教师一次 reprompt 后 19 题中 15 题正确率 0.00%。

**7. 成本口径（§8.2）。** 单节点 4×GH200；§3 每 run 约 6h（约 24 GPU-hours 算术）；SDPO 单步用时相对 GRPO 不计环境 +17.1%、计环境 +5.8%（micro-batch 2）。

**8. 对我们直接可用。**
- 基座诊断时记录每题失败的测试名/错误类型（F2P 中哪些未过、异常类型），作为"0/8 组是否含可用信息"的证据；但这些是 hidden grader 材料，**能否喂给模型属 T0**（笔记 §12 明说不能把"重跑 hidden tests 后把失败详情全部传给模型"当普通实现）。
- 按基座 pass@8 分层（对应其 pass@64）并按层报增益，避免只报总均值。
- 划分纪律：N07 §4 不是题目级 split → 我们在 216 题内做训练/held-out 划分时按**题目/仓库**冻结未见集，再谈泛化（笔记 §12 第五行）。
- **不要照搬**：SDPO 目标与 TTT；LCB 式"同题不同测试"验证当作泛化。

**9. 笔记标注的未知项（§11）。** 科学任务题数/切分比例；LCB 非题目级 split；反馈的反作弊/噪声压力测试；长程 SWE/多 harness 无实证。

---

## 16. E3 Envs-FORGE（arXiv:2608.14312，全文待补）

**1. 来源与版本。** arXiv:2608.14312，提交 2026-08-14；**PDF/HTML/TeX 均未取得**，仅 arXiv 摘要；关联代码 `DataArcTech/DataArc-SynData-Toolkit` 分支 `SynAgenticData@2a1d65ec…`（笔记 §1）。

**2. 环境与任务供给（仅摘要，§2）。** 用 verifier 通过率刻画 seed；围绕学习前沿对六个 projection–direction 动作评分；逐 seed MILP 选动作；动作驱动 instruction、fixtures、oracle、tests、Docker 联合改写；**只有 gold-verified 包进入 RL**；每种合成方法导出 100 个验证环境；合成 token 2.27M–2.88M。历史口径另有 1,824 任务（未核）（§3）。
- 代码（§4）：策略只有 few_shot/self_instruct/evol_instruct；**未见 pass-rate profiling/六动作/MILP 调用**；`static_validate_materialized_task()` 的 `matched=True` 只检查路径存在、文件非空，**不跑 Docker/oracle/tests**，主循环据此 accepted；Harbor 验证是独立 smoke 脚本（退出码 0 且 reward=1 判 matched），不回写 accepted；`_read_latest_harbor_reward()` 按 mtime 取最近 `reward.txt`，未绑定 job ID（复用目录可能读旧结果）；删 canary 行 ≠ 去污染。

**3–4.** 划分/污染、难度筛选：待读取（§5）。

**5. 评测（仅摘要）。** Qwen 3.5 35B：tb-core 40.0→49.2（高于最强固定配方 2.4pp）；tb-2.0 23.0→29.4（+2.1pp）；SWE-bench Verified 73.4→77.1；版本/显著性未知。

**6–7.** 基座诊断、成本：待读取。

**8. 对我们直接可用。** 工程教训（§6）：任务"结构完整""能启动验证""验证成功""结果绑定到导出任务""轨迹可训练"是五件事，不能用一个 `accepted` 字段代替——我们的准入标记必须绑定实际执行结果与 job ID。摘要里"按 verifier 通过率刻画 seed"只是候选想法，未读原文前不建 MILP/在线课程。**不要**把摘要数字当已核事实。

**9. 未知项。** 全部（§5 表）；状态是"待读取"不是"未披露"。

---

## 跨篇对照表

| 来源 | 任务供给方式 | 可执行性门 | 难度筛选 | 划分/污染 | 评测预算与重复 | 基座诊断/SFT |
| --- | --- | --- | --- | --- | --- | --- |
| R1 MAI | 102M PR→4.87M 候选→265,617 验证通过（5.5%）；hidden tests 评分时才应用；≈20 env/min @10k CPU | 自动 Dockerfile 构建；base+test vs base+test+code 取 F2P/P2P；empty patch 多轮 fail + gold pass + 筛非确定测试；grader 同容器 | early 16 条筛 [0.05,0.8]，全组 [0.1,0.8]；G=128（与 16+128 冲突） | 预训练 20-gram/80% 去污、排 SWE-bench Verified PR；SWE 后训练切分/held-out 未披露；清 base 后 commits/refs | Verified 500 / Pro 731 / TB2.0 89；256k、8k/32k 每次、1000 steps；4 runs 均值 T=1 top-p .97；TB 忽略 timeout | 从无 reasoning trace 的 checkpoint 直接 RL；自蒸馏 SFT 用成功轨迹 O(1M)；基座工具诊断未提 |
| R3 Qwen3-Coder-Next | 真实 PR 807,693 实例/52,960 repo + 派生 bug 851,898/5,019 repo | env-building agent 区分 buggy/fixed；过滤 non-functional verifier；QA agent；PASS_TO_FAIL 非空 + 回退恢复 | pass-rate 分布去 overly easy/noisy failure（阈值未给） | SFT/RL prompt 互斥；benchmark overlap 去除无阈值；删 remotes/branches/tags + repo link×网络关键词 blocker | Verified/Multilingual/Pro 三 harness、TB2.0 四配置；max turns 300；无重复/CI/版本 | 执行验证 SFT（Mini-SWE-agent 用户模拟）；四专家蒸馏；基座诊断未提 |
| N01 KAT | >100K env/12 语言；描述由 golden/test patch 重建 | 结构化测试输出：>90% 预期测试被收集 且 跨运行可复现；构建成功 16.5→57.2% | 零通过题过程提示→约 20%→无提示重建；过程启发式过滤 | 清 git history/metadata；无切分/时窗/污染审计 | 六 bench 统一 Claude Code（Pinch 例外）；题数/重复/预算未给 | 抽审发现 16% 轨迹含沙箱故障→<2%；无基座规模；MOPD 冷启动 |
| E11 Cascade 2 | SFT 125K agentic + 389K agentless（SWE-Gym/rebench/R2E）；execution RL 用 SWE-Gym+R2E-Subset；RL 卡 SWE 3,612 条 | 编译/单元测试（scalar 未披露）；无 gold/no-op 漏斗 | 中间模型 16 条：全过删、全失败随机留 10%；代码 RL 删 8/8 | 竞赛代码去重 24.2%；SWE 切分未提 | Verified 500/OpenHands/non-thinking/avg@4/256K/200 turns；TB2.0 avg@5；同报 avg@4+pass@4 | 33K 步大 SFT；同源 MOPD 恢复；基座诊断未提 |
| R2 Ultra | SFT 源 SWE-Gym/R2E-Gym/rebench；teacher RL hidden tests 二元；terminal 370K conv. | 轨迹分析器 include/exclude 规则；git 历史重写 fresh clone；command filter 拦 remote git/GitHub HTTP | STEM pass 0.25–0.80；代码删 8/8→3.5K；SWE 未完成轨迹 mask loss | 预训练 code 截止 2025-09-30；ProfBench/Pinch 仅终评一次；SWE 切分未披露 | 表 10 TB2.1 56.4 / Verified 70.7；图 17 七 harness（Claude 60.3 vs OpenHands 70.3）；repeats 部分给 | 两阶段 SFT→RLVR（reward profiling 未展开）→MOPD；基座诊断未提；故障构成 56/36/8 |
| R13 K3 | 白盒可配置 harness；知识图谱出题；AET 公开/隐藏 verifier；1.5M images/51M sandbox | 各域 verifier 零分规则；SWE 漏斗未给 | 无分带；超预算 reward −1；λNK partial rollout | 明列切分/污染/no-op/gold 不足 | max effort T=1；TB2.1 跨 harness 取优；多 bench 3 次均值；内部 bench 非 holdout | SFT 冷启动来自旧模型合成轨迹；b0/ℓ0 由 cold-start 估计；基座诊断未提 |
| R4 MiniMax-M2 | 六阶段 SWE（按任务类型 verifier）；Terminal-Gym 从 Stack Overflow 合成 | golden 通过才有效；F2P/P2P；AaaV 执行层硬门；terminal Dockerfile 合成重试上限未知 | terminal 排过易、偏好低 zero-shot pass；阶段课程 | 宽松许可；GDPval seed 与评测同源无说明；无全局切分 | Claude Code 统一 scaffold 覆盖 system prompt，4 trials；TB2.0 Terminus-2、8 vCPU/16GB/2h、4 trials；MMLU-Pro 退化 | interleaved-thinking SFT 冷启动；基座诊断未提 |
| E10 Intern-S2 | 七公开源库存（SWE-Gym 2,438/2,401 等）+ skill 合成 | workspace 剥离 gold/test/评分 ID；单 baseline commit；run 后恢复 canonical tests+gold test patch；all-correct；infra 故障分账 | 组 reward 全同丢弃补采；过程 adv_penalty | 未给 | TB2.1 67.42 Terminus 2；SWE Pro 61.56 Mini-SWE-Agent（改镜像防 git log 泄漏）；预算/重复未给 | 广域 SFT→两专家→OPD；基座诊断未提 |
| R5b GLM-5.2 | 长程 coding 场景（数量未披露） | 规则→LLM judge 逐调用阻断+dummy+继续 | 未提 | 未提 | 逐 bench 脚注：harness 版本、CPU/mem、timeout、max_new_tokens、turns、context、runs（Claude Code 2.1.167 五次均值） | 未提 |
| R5c GLM-5.3 | 未核验 | 未核验（U 登记 oracle/no-op/unsolved-state） | 未核验 | 未核验 | 未核验 | 未核验 |
| Nemotron-Terminal | adapters 226,313（无 tests）+ synthetic 264,207（无 oracle）；9 基础镜像 | pytest 带权重；14-gram 去污；complete/success 可选过滤 | no filter 12.4 > success-only 5.06（无等 token 对照） | 14-gram vs TB2.0 | TB2.0 89 题 Terminus 2 Daytona；± 定义未绑定；无重复数 | SFT-only（Qwen3-8/14/32B）；teacher DeepSeek-V3.2 三 bench 校验 |
| O01 SkyRL-Agent | 4.5K R2E-Gym；训练期 AST 工具 + hints | 项目测试判 patch；隔离/反作弊未给 | 无（Deep Research 用 4 次 rollout 分层 0/1/2/3 of 4） | 未给；检索泄漏屏蔽域名 | Simple ReAct 40K/100 steps；Verified 24.4→39.4；TB v0.1.1 80 题 OpenHands；无重复 | 观察 view 分块/grep 缺陷→加 AST；50/64 未解决；无 SFT |
| R14 CompactionRL | SWE-Dev 开放数据（数量未给） | 终局 R 由测试决定（实现未给） | 无 | 未给 | Verified 随机 200 题 + TB2.0 全量；两次评测均值；64k/80k 峰值、≤3 压缩、≤250 turns、T=1 top-p=1 | 未提；外部锚 Qwen3-30B-A3B-Instruct-2507 SWE 25.2/TB 5.34 |
| R15 SAO | SWE 数据未披露；Qwen3-30B-A3B-Thinking-2507 直接 RL | 未给 | 无 | 未给 | OpenHands 300 turns/128k、T=1 top-p=1；SWE 重复未给；23.0→27.0→29.8 | 未提；基座 23.0 锚点 |
| N07 SDPO | SciKnowEval L3 + ToolAlpaca；LCBv6 131 题；TTT 19 题 | 执行反馈（错误类型/行号/输入/expected） | 基座 pass@64 定 hard/very hard | §3 按题切分；§4 同题按测试切分（非泛化） | avg@16（1h/5h 墙钟）；avg@4×3 seeds；discovery@k 5 seeds 90% CI | 基座 pass@64 分层；初始教师 15/19 题 0% |
| E3 Envs-FORGE | 摘要：pass-rate 刻画 seed→MILP 选六动作→gold-verified 包；100 env/方法 | 代码示例 `accepted` 仅静态路径检查；Harbor 验证独立且未回写 | 待读 | 待读 | 摘要：tb-core 40.0→49.2、tb-2.0 23.0→29.4、Verified 73.4→77.1 | 待读 |
