# B 线设计建议稿：训练什么、用什么题、怎么评、要什么环境

日期：2026-09-09。作者：Claude（B 线）。性质：**建议稿，未经用户拍板；不构成题单、预算或训练语义的批准。**

```yaml
status: draft
owner_decision: 待用户逐项决定（见 §9）
supersedes: 本目录 00_B_reading_synthesis_and_first_round_plan.md 的 §3–§4 中与本稿冲突的部分
relation_to_codex: 与 b_supplement_reading_and_decisions_20260909.md 的五项建议（B1–B5）对照，见 §8
```

用户 2026-09-09 的要求：不把 216 题和旧实验设计原样推进，而是在读完外部资料后，**有理由地设计要训练的能力、题源、评测和环境**，然后再做环境数据处理和基座初评。本稿就是这一步的产物。先给结论，再给理由，最后列决定。

---

## 0. 结论（一页版）

| 问题 | 建议 | 一句话理由 |
| --- | --- | --- |
| 训练什么能力 | **真实 Python 仓库中的缺陷修复并保持回归**，在 Claude Code 里完成，用隐藏测试判分 | 唯一同时具备可信奖励链、同规模 RL 正例、外部评测坐标的能力面；terminal、多语言、功能开发都缺其中至少一项 |
| 主训练题源 | **SWE-Gym**：先用本地 216 题（Lite 存活集）做诊断，**扩容路径是同 9 仓库的 SWE-Gym Full（约 2,300 题）**，不是换来源 | 唯一已有 rh2 ingestion 的来源；同镜像格式、同 parser；Dressage 用 SWE-Gym 293 题子集 + Claude Code 在 4B 上训出 Verified +5.2pp，是与我们链路最接近的正例 |
| 对照题源 | **R2E-Gym Subset（Prime 清洗版）取 12 题**做环境与难度对照；首轮不进正式训练池 | 直接 RL 证据最强（DeepSWE、SkyRL-Agent、OpenThoughts RL 榜第 2）；rh2 的 held-out 规则已预留 tornado/pyramid，说明设计时就考虑过它 |
| 暂不接入 | SWE-smith、ScaleSWE、SWE-rebench V2、任何合成/课程生成 | 各自缺关键条件（测试可见、只有 SFT 证据、多语言、动作语义未验证），作为第二轮扩容候选保留 |
| 评测结构 | 三层：**开发探针**（≤40 题 SWE-Gym + 12 题 R2E，反复用）→ **内部保留**（SWE-Gym 保留仓库 hydra/bokeh + R2E 保留仓库 tornado/pyramid，冻结）→ **外部坐标**（SWE-bench Verified 按仓库分层 100 题，Claude Code 固定版本/预算，训练前后各跑 3 次） | 开发用与最终证明分开；仓库级隔离比随机切分可信；Verified 只作可比坐标，不当无污染证明 |
| 环境/评分 | 复原 SWE-Gym 官方 fork 的完整评分契约（mypy `-k`、conan `eval_commands`、pydantic 专用 parser），fresh grader 不变；**同时记录"官方宽松判定"和"严格判定"两个结果** | 官方 scorer 对 SKIPPED/空参考集是宽松的（O04 §7.5）；改判分语义是 T0，先记两份事实再定 |
| 基座 | 先测当前 pin 的 `Qwen/Qwen3-30B-A3B`；**预先写死"换基座"的触发条件**（§6.3） | 同规模 2507 变体在 Verified 只有 23–25%，Coder 变体 51.6%；起点选择直接决定"我们的提升"能否归因，应是显式决定而不是默认 |
| 顺序 | 评分契约复原 → 24 题四门 + 语义审计 → 24 题 × 4 次基座诊断 → 用两个预注册的数字门决定训练池与配方（§7） | 与 Codex "小批环境验证 → 真实基座诊断" 一致，本稿补的是每步的判据和数字 |

---

## 1. 新读的 9 份材料改变了什么（给尚未读原稿的用户）

只列会改变 B 决策的结论，每条注来源。

| 材料 | 对本稿设计的直接影响 | 必须保留的限定 |
| --- | --- | --- |
| O04 SWE-Gym（全文 + 官方 fork 代码） | ① 本地 parser `KeyError` 是**接入问题**，官方 fork 有全部 11 仓 parser；② mypy 测试命令是 `pytest -rA -k "case_a or case_b"`，从 test_patch 里的 `[case NAME]` 提取，不能按文件名拼；③ 官方 scorer 把 SKIPPED 排除在分母外、参考集为空时判 FULL——**gold 通过不等于测试真跑了**；④ Lite 是按 gold 补丁简单性筛的训练子集，不是"对当前模型容易"；⑤ OpenHands 自产 868 条成功轨迹再 SFT 反而 15.3%→8.7% | 官方 fork 未实际启动；skip/空集边界是静态事实，触发率未测 |
| O02 DeepSWE | ① Qwen3-32B thinking **直接 RL**（无 SFT）在 R2E-Gym 上 42.2%，证明同量级模型不必先 SFT；② 换 SWE-Gym/SWE-smith 时"改善有限、全失败组多"，Claude 轨迹 SFT 起点再 RL 无改善——**负结果，但条件未披露，不能推广**；③ 评分超时 300 s 记 0；④ 64 题 × 8 条/步，约 200 步 | dense 32B，R2E scaffold，非 Claude Code；原始日志缺失 |
| O05 ScaleSWE | 20,181 题公开（论文说 100k）、5.2k 仓库；**只有 SFT 证据**（22→64）；任务含功能请求不只是 bug；工作目录不是 `/testbed`；两种测试字段并存；评分器 fast path 只看 pytest 退出码 | 附录 E 和原图未取得 |
| O28a/b SWE-rebench 运维与演讲 | 153K 候选→21K 任务（不是坏题率）；每月 1–2 次无效模型运行；**重试规则必须实验前定**；五次重复分别报 mean / pass@5 / all-5；时间切分只挡一种污染通道；作者估计逐题人工核验约一人日 | 视频/幻灯片未取得；数字是口述近似 |
| Prime SWE tasksets（代码级） | ① 三来源 reward 语义**不同**（R2E 比对预期状态映射；rebench/Scale 比对目标 ID 全 PASSED）；② `Verified` 标签 ≠ 稳定：R2E 首检失败再试 10 次有一次过就保留；③ `--only-setup` 不做 no-op；④ 三条 taskset 都在**求解沙箱内评分**，捕获的 patch 不等于可重放交付工件；⑤ SWE-rebench V2 过滤版 32,079→6,272，Scale 20,181→17,202 | 未下载全量、未跑镜像 |
| Real-World Code Repair（LinkedIn） | 简化流程内 RL 提升（validation 7→27），回完整流程几乎没有恢复；训到 3K 步出现**删除验证代码**的奖励利用；按"初始构建 <100 s"筛题会偏置分布 | 企业内部数据；多条件同时变化，不能单因归因 |
| OpenThoughts-Agent | **SFT 与 RL 的好题源排序不同**：SWE-Smith 是 SFT 第 1 但 RL 一般；pymethods2test（单函数题）SFT 第 85 却是 RL 第 1；R2E-Gym RL 第 2；ColdSFT+RL 比最强 SFT-100K 只高 0.5pp 且 SWE 反低 7pp；主 RL 后期 reward 崩溃、超时率到 80% | 8B、Terminus-2、三个开发集选配方 |
| E3 Envs-FORGE（补全文） | 预测难度 ≠ 实测难度；Case V 的"保持难度多样化"实际把任务收窄并直接给出答案 | 无 solver-off 对照；本项目首版不做 |
| Dressage（B 相关章节） | **最接近我们的正例**：Qwen3.5-4B + Claude Code + SWE-Gym 293/23 子集（SkyRL-v0-293），fresh official harness 评分，Verified 32.6→37.8（+5.2pp）；训练 64K/80 turns，评测 256K/160 steps | 4B dense；GPU-hour、CI 未给；训练与评测预算不同 |

综合起来，这批材料把三件事钉死了：**(a)** 评分契约要逐仓库复原并同时记宽松/严格两份判定；**(b)** 题源价值取决于训练方式和模型，不能给题源打永久分；**(c)** 训练 harness 必须等于评测 harness（Claude Code），否则收益可能不迁移。

---

## 2. 训练什么：能力目标的选择与理由

### 2.1 候选与判据

判据五条：① 有可复现的可信奖励链；② 有同规模（约 30B 或以下）模型的 RL 正例；③ 有可比的外部评测坐标；④ 与项目主张（真实 coding harness 的可靠 RL 链路）直接相关；⑤ 首轮适配成本。

| 候选能力面 | ① 奖励链 | ② 同规模 RL 正例 | ③ 外部坐标 | ④ 贴合主张 | ⑤ 成本 | 判断 |
| --- | --- | --- | --- | --- | --- | --- |
| **A. 真实 Python 仓库缺陷修复 + 回归保持（Claude Code）** | 有：fresh grader + 隐藏 F2P/P2P，已批准 | 有：Dressage 4B（Claude Code）、SAO 30B-A3B 23.0→27.0、SkyRL-Agent 32B 24.4→39.4、DeepSWE 32B | SWE-bench Verified | 直接 | 216 题 ingestion 已有；parser 待接 | **推荐** |
| B. SWE + terminal 联合训练 | terminal 侧无 grader、无题源接入 | OpenThoughts 8B 有，但 Terminus-2 | TB2.0 | 部分 | 要建第二条评分线 | 首版只作迁移探针 |
| C. 函数级可执行代码题（pymethods2test 类） | 容易：unittest 即可 | OpenThoughts RL 第 1，且迁移到 SWE100 | 无直接坐标 | 弱：不走多轮仓库工作流 | 最低 | 只可作 learner 冒烟，不作能力主张 |
| D. 真实 PR 功能实现（ScaleSWE 类） | 有但评分器语义待核 | **无**（只有 SFT） | Verified | 直接 | 新 ingestion + 新 scorer | 第二轮候选 |
| E. 多语言（SWE-rebench V2） | parser 逐语言 | 无 | SWE-bench Multilingual | 部分 | 高 | 不做 |

### 2.2 推荐 A，并把它写成可测的主张

建议把能力目标写成一句可以被证伪的话：

> 在固定的 Claude Code 版本、工具面、上下文与轮次预算下，用本项目链路在 SWE-Gym 的 N 道任务上做 GRPO 后，`Qwen/Qwen3-30B-A3B` 在**未训练仓库**（内部保留仓库 + Verified 100 题子集）上的单次解决率提高；提升来自训练而不是评分或题目筛选变化（原始候选漏斗、失败分布、宽松/严格两份判定都保留）。

三点说明：

- **"缺陷修复"而不是"issue 解决"。** SWE-Gym Lite 的筛选规则本来就是单文件、gold 小、题面清楚（O04 §3.1）；ScaleSWE 那种功能请求题不在首轮范围。这限制了能力主张的宽度，但换来奖励可信和归因干净。
- **"在 Claude Code 里"是能力定义的一部分。** Harness 敏感性数据（同一模型 Claude Code 60.3 vs OpenHands 70.3）和 LinkedIn 的迁移失败都说明，脱离 harness 谈能力没有意义。训练与评测都用 Claude Code，OpenHands 只作可选的文献可比坐标。
- **不追求两位数提升。** 同规模锚点：SAO 一轮 GRPO+DIS 在 30B-A3B 上 +4pp，Dressage 4B +5.2pp。首轮"有无学习"的判据应设在这个量级（§7.2）。

### 2.3 为什么不先做 C 类便宜题

OpenThoughts 的结果确实诱人：单函数题做 RL 反而在 SWE100 上最好。但那是 8B、ColdSFT 起点、Terminus-2 下的结果，没有人在 Claude Code 上复现过。更重要的是，本项目的价值主张是"真实 harness 的可靠链路"，用不经过多轮仓库工作流的题训练，即使涨分也说明不了链路。**唯一合理的用法**：如果 SWE 环境成本一时打不通，用 C 类题做一次"learner 会不会让 reward 上升"的冒烟，报告时明确它不是能力结果。这不需要现在决定。

---

## 3. 用什么题：题源比较与选择

### 3.1 逐来源对照

| 来源 | 规模（公开可得） | 任务类型 / 测试可见性 | 评分契约 | 镜像 | RL 证据 | 与 Verified 的隔离 | rh2 接入成本 | 结论 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| **SWE-Gym Lite（本地 216）** | 216 题 / 9 仓库（hydra、bokeh 已按 held-out 规则移除） | 真实 issue 缺陷修复；测试隐藏，评分时写入 | 官方 fork 的 spec+parser 可复原（O04 §7） | `xingyaoww/sweb.eval.x86_64.*`，digest 已核，约 480 GiB | Dressage（293 子集，Claude Code，4B，+5.2pp）；DeepSWE 负结果条件不明 | 构造时仓库不相交 | **已有 ingestion**；parser 待接 | **首轮诊断池** |
| **SWE-Gym Full（同 9 仓库）** | 约 2,346 题（2,438 − hydra 66 − bokeh 26） | 同上；gold 平均 69.8 行、2.5 文件，比 Lite 难 | 同上，同 parser | 同一镜像命名规则 | 同上 | 同上 | **最低**：只多下载镜像与 ingestion 行 | **指定扩容路径** |
| **R2E-Gym Subset / Prime Verified** | 4,578 → 4,522 题 / 10 仓库（pandas 31.5%、numpy 17.1%、pillow、orange3、aiohttp、tornado、scrapy、pyramid、datalad、coveragepy） | 真实 commit 反译题面，测试隐藏在 `/r2e_tests` | **不同语义**：比对预期状态映射，不是"全 PASSED"（Prime §3.3） | 作者 registry；Prime 有转存 | **最强**：DeepSWE 42.2、SkyRL-Agent 24.4→39.4、OpenThoughts RL 第 2 | Subset 已去除 SWE-bench 仓库 | 新 adapter（reward、隐藏测试目录、`/testbed`）；rh2 的 held-out 规则已含 tornado/pyramid | **对照池 12 题**；正式训练第二轮 |
| SWE-smith | 50,137 → 卡片 59,136 题 / 128 仓库 | 合成 bug（LM/程序化/PR mirror）；**F2P 测试对 agent 可见** | 当前代码按状态交集 | 128 基础镜像，约 295 GB | 官方称 SkyRL 用过 GRPO，无受控收益；OpenThoughts SFT 第 1、RL 一般 | 排除 12 个 SWE-bench 仓库 | 新 adapter；测试可见性与本项目 hidden-test 语义冲突 | 不做；第二轮扩容候选 |
| ScaleSWE / Prime Verified | 20,181 → 17,202 题 / 5.2k 仓库 | 真实 PR，含功能请求；题面重写；`f2p_patch` 与 `f2p_script` 并存 | JUnit ID 匹配，fast path 宽松（O05 §8.3） | `aweaiteam/scaleswe:*`，892 镜像被 Prime 排除 | **只有 SFT** | 排除 Verified 仓库 | 新 adapter + 工作目录/字段差异 | 不做；仓库多样性不足时再评估 |
| SWE-rebench V2 Filtered | 6,272 题 / 17 语言 | 真实 issue；LLM 元数据筛选 | 逐语言 parser | Prime 转存 | 无 | 时间切分 | 多语言 parser | 不做 |
| SkyRL-v0-293 | 293 / 23 | SWE-Gym 子集 | 官方 harness | 同 SWE-Gym | Dressage 正例 | 同 SWE-Gym | 与 216 题重叠度未查 | 作为 Dressage 可比参照核对重叠 |

### 3.2 推荐及理由

**主训练池 = SWE-Gym，诊断从 216 题起，扩容走同 9 仓库的 Full。**

1. 这是唯一有 ingestion、有 digest 冻结、有 fresh grader 投影的来源；换来源等于把 T2-c 重做一遍。
2. Dressage 是与我们链路最接近的正例（Claude Code、fresh official harness、SWE-Gym 子集），而且只用 293 题。这直接回答了"216 题够不够"：**题量不是首要瓶颈，有信号的题占比才是**（§7.1）。
3. DeepSWE 对 SWE-Gym 的负结果不能推翻上面两条：它用 R2E scaffold 和 dense 32B，没有披露预算与评分；OpenThoughts 的排序反转也说明题源价值随训练方式变。
4. 扩容走 Full 而不是新来源，是因为 Full 与 Lite 共享镜像命名、parser 与 held-out 规则，边际成本最低；而且 Full 更难（gold 更大），可以补 Lite 里"过易"的那一端。

**对照池 = R2E-Gym 12 题（Prime 清洗版），首轮只做环境与难度对照。** 理由是它的 RL 证据最强、仓库与 SWE-Gym 完全不同，能回答"我们的模型在 SWE-Gym 上的失败是题的问题还是模型的问题"。首轮不进训练池，因为 reward 语义不同（预期状态映射），混训会让归因失效。

**明确不做的：** SWE-smith 的测试对 agent 可见，与本项目 hidden-test 的奖励定义冲突，而且 OpenThoughts 显示它对 RL 不比对 SFT 有用；ScaleSWE 没有任何 RL 证据；Envs-FORGE 类合成没有 solver-off 对照且已见到语义漂移案例。这些都保留为第二轮扩容候选，**触发条件写在 §7.3**。

### 3.3 216 题内部的已知问题（来自资产盘点，需在四门中核）

| 事实 | 处理 |
| --- | --- |
| 22 题 `PASS_TO_PASS` 为空 | 不据此剔题；记为"无回归证据"，四门只跑 F2P 门 |
| 19 题 `python_version` 为 None | O04：dask/pandas 版本可由 environment.yml 决定，按官方 spec 取，不擅自补 |
| mypy 40 题、conan 12 题 | 命令契约特殊（`-k` 表达式、`eval_commands` 设 `PYTHONPATH`），各取 3 题、2 题进首批 |
| leakage warn 13 题 | 取 2 题进首批，人工看题面是否给出修法 |
| moto 59 题占 27% | 训练池按仓库配额（每仓 ≤30%），避免 moto 主导 |

---

## 4. 怎么评：三层评测结构

### 4.1 结构

| 层 | 题集 | 用途 | 使用频率 | 能证明什么 / 不能证明什么 |
| --- | --- | --- | --- | --- |
| **L1 开发探针** | SWE-Gym ≤40 题（9 仓分层，与训练池按 `(repo, base_commit)` 互斥）+ R2E 12 题 | 调预算、选配方、A 线做投影/消费核验的交接题单、中间 checkpoint 抽查 | 反复 | 只证明链路与配方；**不能事后改称独立测试** |
| **L2 内部保留** | SWE-Gym 保留仓库 hydra（Full 66 题）、bokeh（26 题）；R2E 保留仓库 tornado、pyramid | 仓库级泛化；本项目最可信的"训练前后"对比 | 训练前 1 次、训练后 1–2 次 | 仓库隔离 + 同分布；对预训练污染无免疫，但 SWE-Gym 是 2024-12 才发布的训练集，风险低于 Verified |
| **L3 外部坐标** | SWE-bench Verified 按仓库分层 100 题（固定题单与版本） | 与文献可比；Claude Code 为主 harness，OpenHands 可选一次 | 训练前后各 3 次 | 可比性；**不当作无污染证明**，用 N13a 审计清单标注已知问题题目但不剔除 |
| L4 迁移探针（可选） | Terminal-Bench 2.0 全 89 题 | 看 SWE 训练是否伤害/帮助终端任务 | 训练后 1 次 | 只报告，不进完成条件 |

hydra 需要 Java、bokeh 需要 bokehjs（O04 §7.3），可行性在四门阶段核；若不可行，改为从 9 仓库中整仓保留 modin（5 题）与 pandas（5 题）——这两个仓库在 216 里题最少，损失最小。

### 4.2 协议（固定后写入每次运行的记录）

| 字段 | 取值方式 | 来源依据 |
| --- | --- | --- |
| 模型 | 精确 checkpoint + tokenizer revision + 推理精度（bf16 为正式；量化版单列） | Codex B5、GLM-5.2 schema |
| harness | Claude Code 版本 pin（当前 2.1.205）、工具面、子 agent 与压缩设置、系统提示 | E1、E8、Dressage |
| 预算 | turn 上限、wall-clock 上限、上下文；**训练与评测预算可以不同但必须分别记录**（Dressage 训练 64K/80 turns、评测 256K/160 steps） | A 线第 1 组决定 |
| 采样 | temperature、top-p；每题 n 次 | O28b |
| 分母 | 同时报 **成功/全部计划尝试**（含系统错误）和 **有有效评分的条件成功率**；mean、pass@n、all-n 分开 | O28b §4、Codex B4 |
| 重试 | 实验前列出允许重试的系统原因与次数；重试不折成 pass@1 | O28b §3.6 |
| 判定 | 官方宽松判定与严格判定并列（§5.2） | O04 §7.5 |
| 成本 | 每尝试 token、工具调用数、墙钟、评分时长 | 全部 |

### 4.3 划分规则

- 训练池与 L1 在 `(repo, base_commit)` 上互斥；同环境不同题放同侧。
- L2 按仓库整体保留；不允许后续把保留仓库的题"借"进训练。
- 一旦某题用于选配方或调预算，永久归 L1。
- 记录每题的来源 revision、镜像 digest、scorer 版本；L3 记 Verified 数据版本与 100 题清单的 hash。

---

## 5. 要什么环境：评分契约、四门与成本

### 5.1 评分契约复原（B1，从"接 parser"改为"复原官方 fork 的完整契约"）

O04 之后，B1 的范围要比之前写的大：不只是 `repo → parser` 映射，而是逐仓库复原官方 fork 的 `(test command, eval_commands, parser, F2P/P2P 匹配规则)`。具体：

| 仓库 | 命令要点 | parser | 首批题数 |
| --- | --- | --- | --- |
| mypy | `pytest -rA [-n0] -k "<case1> or <case2> ..."`，case 从 test_patch 全文提取（含删除与上下文行） | 普通 pytest | 3 |
| conan | 额外 `eval_commands` 设 `PYTHONPATH` 为仓库目录 | 普通 pytest | 2 |
| pydantic | `pytest -rA --tb=short -vv -o console_output_style=classic --no-header` | **专用** `parse_log_pytest_pydantic` | 2 |
| moto | `make init` 后 `pytest -n0 -rA` | 普通 | 4 |
| dask / pandas / modin | Python 版本可由 environment.yml 决定 | 普通 | 各 2 |
| dvc / MONAI | 安装子命令带 `\|\| true`，spec 存在 ≠ 已装好 | 普通 | 各 2 |

验收：对首批 24 题，本项目生成的命令与官方 fork `make_test_spec` 生成的命令逐字一致；日志解析出的状态映射与参考 F2P/P2P 完整匹配（含参数化测试名的空格截断规范化）。

### 5.2 两份判定并列（T1 记录，改 reward 是 T0）

官方 scorer 的宽松点（O04 §7.5、§7.8）：SKIPPED 不进分母；参考集为空判 FULL；`set -xo pipefail` 使脚本退出码不代表测试结果；OpenHands 入口空补丁直接判失败不跑测试；远程 wrapper 超时后仍读日志判分。

建议每次评分同时输出：

```text
official_verdict : 按官方 fork 规则（保留可比性）
strict_verdict   : F2P 全 PASSED 且 P2P 无 FAILED/ERROR 且参考集非空且无 SKIPPED 进参考集
execution_facts  : 测试是否真跑、parser 是否找到全部参考 case、超时/setup 错误分别记
```

训练 reward 用哪一份是 A/B 合并的 T0；本稿只要求两份都落盘。

### 5.3 四门与语义审计（B4，保留原案，改首批为 24 题）

首批 = SWE-Gym 12 题（按 §5.1 配额）+ R2E 12 题（按仓库分层，避开只抽最便宜的）。每题跑：空补丁必败（前提是测试真跑）、gold 必过、fresh 容器 N=3 确定性、无关文件补丁必败；另对 4–6 题写合法替代解探针。每次一行 jsonl，字段沿用 Prime §9.2 的薄结果表。

**这张表同时是 A 线两个决定的证据来源**：超时/零解析是否改判 reward 0；wall-clock 上限设多少（要看每题评分时长分布：pandas/dask 的测试可能远超 DeepSWE 的 300 s）。

### 5.4 R2E adapter 的最小范围

只为 12 题对照做：读 `docker_image`、`problem_statement`、`expected_output_json`；setup 时搬走 `/r2e_tests`，评分时在 fresh 容器恢复并运行 `run_tests.sh`；reward 按预期状态映射精确匹配。**不改 rh2 通用 grader**，作为 environment adapter 挂接。gold 由 `parsed_commit_content` 重建（只取非测试 Python 文件）。

### 5.5 成本估算（供决定，不是承诺）

| 项目 | 估算 | 依据 |
| --- | --- | --- |
| x86 CPU 机（16 核、1 TB 盘、无 GPU） | 0.3–0.8 美元/小时 | s2_1 计划 |
| 首批 24 题镜像 | 约 55 GiB（216 题平均 2.2 GiB/题） | 资产盘点 |
| 四门执行次数 | 24 题 × (空 1 + gold 1 + 确定性 3 + 探针 1) ≈ 144 次，另 6 题各加 2 组 ≈ 12 次 | Codex 第二段 |
| 四门墙钟 | 每次 2–15 分钟，并发 4，约 10–20 机时 | O04 测试规模、DeepSWE 300 s 超时 |
| 基座诊断 24 题 × 4 次 | 96 次尝试，每次 20–40 分钟，并发 4–8，约 8–16 GPU 机时 | Dressage 80 turns/64K |
| 216 题 × 8 次全量画像（若做） | 1,728 次尝试，约 150–300 GPU 机时；建议并入 A 的 GPU spike，不单独租 | 同上 |

---

## 6. 基座诊断：对象、协议与换基座的触发条件

### 6.1 对象

先测仓库 pin 的 `Qwen/Qwen3-30B-A3B`（原版混合思考模型），不是 `-Instruct-2507`、`-Thinking-2507`，也不是 `Qwen3-Coder-30B-A3B`。A 线的 tokenizer/模板核验对应这个 pin。

已知同规模锚点（都不是 Claude Code）：

| 模型 | harness | Verified | 来源 |
| --- | --- | --- | --- |
| Qwen3-30B-A3B-Thinking-2507 | OpenHands，300 turns，128k | 23.0 | R15 SAO |
| Qwen3-30B-A3B-Instruct-2507 | Terminus-KIRA，256k | 25.2 | R14 CompactionRL |
| Qwen3-30B-A3B-Instruct-2507 | OpenHands | 22.0 | O05 Table 3 |
| Qwen3-Coder-30B-A3B-Instruct | OpenHands | 51.6 | O05 Table 3 |
| GLM-4.7-Flash-30A3B | OpenHands | 59.2 | O05 Table 3 |

Claude Code 下原版 Qwen3-30B-A3B 的数字没有任何文献锚点；旧的 Qwen3-4B × 8 题探针（5/32、1/32）不能外推。

### 6.2 协议

沿 Codex B5：先 2–4 条完整轨迹人工看，再 24 题 × 4 次；精度用拟训练的 bf16（若先用 5090 量化版探索，单列为另一条件）。记录：请求体原样（A 线 REALIGN 根因要用）、工具调用分布、结束原因、F2P/P2P 结果、token/墙钟/成本；失败按"定位/修改/验证/交付"四阶段 + Intern-S2 类别人工标前 20 条。

### 6.3 预先写死"换基座"的触发条件（T0，请用户定阈值）

不预先决定换不换，但把判据写死，避免看到数字后再找理由：

| 观测（24 题 × 4 次） | 含义 | 建议动作 |
| --- | --- | --- |
| 工具协议失败（格式错、工具名错、JSON 键序漂移导致的重试）占尝试 > 30% | harness 适配问题，不是能力问题 | 先修适配，同题重跑；不换基座、不 SFT |
| 协议正常，但 24 题中有任一成功的题 < 3 题 | 几乎采不到成功路径 | 扩到 216 × 4 再看；仍 < 10% 题有成功则进入换基座比较 |
| 有成功的题 ≥ 5 且组内有正负 | 可以直接 RL | 不 SFT，进入 §7 的训练池判据 |
| 成功集中在 1–2 个仓库 | 训练池需按仓库配额，并优先从 Full 补其他仓库 | 见 §7.3 |

换基座的候选只比较一个：`Qwen3-Coder-30B-A3B-Instruct`（同架构、同显存）。代价是它已经过 agentic RL，起点 51.6 使"我们的提升"更难显著且更难归因；好处是几乎不会出现全失败。这是典型 T0。

---

## 7. 用诊断结果决定训练池与配方：两个预注册的数字门

### 7.1 门 1：训练池够不够（取代"216 题够不够"的争论）

定义 **有信号题占比** = 在 n=8 下 0 < 成功次数 < 8 的题数 / 总题数。参考：SkyRL-Agent 训练初 50/64 组全失败（有信号约 22%）仍训出 +15pp；DeepSWE 用 64 题 × 8 条/步跑约 200 步。

| 有信号题占比（216 题） | 有信号题数 | 判断 |
| --- | --- | --- |
| ≥ 30% | ≥ 65 | 216 题足够做首轮（每步 32 题 × 8，50–100 步，每题被采 7–15 次） |
| 15–30% | 32–65 | 可以开训，但同时从 Full 按仓库配额补 200–400 题 |
| < 15% | < 32 | 先按 §6.3 排查协议/预算/评分；确认是能力问题后再比较基座 |

全失败题**不剔除**：Codex §2.4 的算术（p=0.2 时 8 次全失败仍有 16.8%）成立；它们保留在池里但按 A 线组准入规则处理（全零组不产梯度是 GRPO 的自然结果，不需要新规则）。

### 7.2 门 2：训练后"有无学习"的判据

- L2 内部保留仓库：训练后单次解决率（3 次均值）高于训练前，且差值超过 3 次运行的标准误 × 2；
- L3 Verified-100（Claude Code）：同上，期望量级 +3 到 +6pp（SAO +4、Dressage +5.2）；
- 同时报告：全部尝试分母下的完成率是否下降（LinkedIn 与 OpenThoughts 都出现过"条件均值降、全尝试均值升"或反向）；中间 checkpoint 在 L1 上抽查是否出现测试文件/控制面篡改（rh2 投影已挡，但要看日志）。

达不到不算失败：先分辨是评分、预算还是策略问题（Codex 第三段的分流表适用）。

### 7.3 第二轮扩容的触发条件（现在只登记，不做）

| 触发 | 扩容动作 |
| --- | --- |
| 有信号题不足且集中在少数仓库 | SWE-Gym Full 同仓库补题（最低成本） |
| 9 仓库全部饱和（训练后 L1 成功率 > 70%） | 接 R2E-Gym Subset 进训练池（reward 语义已在对照阶段核过） |
| 需要仓库多样性主张 | 评估 ScaleSWE Prime 清洗版，但先补 RL 证据 |
| 需要大量便宜题做课程 | 评估 SWE-smith，前提是接受"测试可见"的奖励定义并单列报告 |

---

## 8. 与 Codex 补充稿五项建议的异同

| 项 | Codex 建议 | 本稿 | 差异性质 |
| --- | --- | --- | --- |
| B1 能力目标 | A：SWE 扎实，terminal 作补充评测 | 同意，并写成可证伪主张（§2.2），明确 Claude Code 是能力定义的一部分 | 细化 |
| B2 题源 | SWE-Gym 12 + R2E 12 共 24 题起步；后续比较 ScaleSWE/SWE-rebench | 同意 24 题；**扩容路径指定为 SWE-Gym Full 同仓库，ScaleSWE/rebench 后置**（§3.2、§7.3） | **不同**：Codex 把多来源放同一优先级，本稿认为 Full 边际成本最低且不破坏 held-out |
| B3 评分可信 | 复用来源命令/parser，正反控制 | 同意；补"官方宽松/严格两份判定并列"的具体规则（§5.2） | 细化 |
| B4 划分与评测 | 24 题全归开发；仓库层面预留独立测试；公开基准补可比性 | 同意；具体化为三层（§4.1），指定 hydra/bokeh + tornado/pyramid 为保留仓库，Verified 固定 100 题分层子集，Claude Code 为主 harness | **不同**：Codex 未指定 harness 与题量，本稿指定 |
| B5 基座 | 先测当前 checkpoint，失败归因后再比较更合适起点 | 同意；**预先写死换基座的触发条件和唯一候选**（§6.3） | 细化，避免事后择优 |
| （新增） | — | 两个预注册数字门（§7.1、§7.2）和第二轮扩容触发（§7.3） | 新增 |
| 方案 C（函数级题） | 拒绝 | 拒绝作为能力面；保留为可选 learner 冒烟（§2.3） | 微差 |

---

## 9. 需要用户决定的事项（T0，按决策包格式）

**D1 能力目标。** 选项：A 缺陷修复（推荐）/ B SWE+terminal 联合 / D 功能实现。推荐 A，理由 §2；长期代价：首版不能主张通用终端或多语言；以后可扩。

**D2 题源与扩容路径。** 选项：(i) SWE-Gym 主池 + R2E 12 题对照，扩容走 Full 同仓库（推荐）；(ii) Codex 原案，扩容时多来源并列比较；(iii) 只做 216 题不预设扩容。推荐 (i)，理由 §3.2；代价：仓库多样性主张推迟到第二轮。

**D3 评测结构。** 选项：(i) 三层 + Verified-100 分层 + Claude Code 主 harness（推荐）；(ii) 只做 L1 + Verified 全 500 题；(iii) 加 OpenHands 作第二 harness 每轮都跑。推荐 (i)；代价：Verified-100 的置信区间较宽（单题 = 1pp），需 3 次重复。

**D4 保留仓库。** hydra + bokeh（SWE-Gym）与 tornado + pyramid（R2E）；若 hydra/bokeh 环境不可行则改 modin + pandas 整仓保留。需要用户接受"保留仓库永不进训练"。

**D5 基座与换基座阈值。** 先测 `Qwen/Qwen3-30B-A3B`；§6.3 的阈值（协议失败 30%、有成功题 < 3/24）请确认或改数；唯一换基座候选 Coder-30B-A3B。

**D6 两份判定。** 接受"官方宽松 + 严格"并列落盘（T1）；训练 reward 采用哪份留到四门结果出来后与 A 合并决定（T0）。

**D7 资源授权（沿前案）。** x86 CPU 机租用（四门 24 题预计 < 20 美元）；基座诊断载体（单 5090 量化 vs 双卡 bf16）；这两项不在本稿新增，只是前置。

**D8 门的阈值。** §7.1 的 30%/15% 与 §7.2 的 +3–6pp 期望，是本稿从文献锚点推的，请确认或改。

---

## 10. 拍板后的执行顺序（不变的部分）

1. **B1′ 评分契约复原**（§5.1）：可立即做，不依赖任何决定；产出命令对照表 + parser 单测。
2. **B3′ 首批 24 题题单**：按 §3.3、§5.1 配额与 R2E 仓库分层给出，用户确认。
3. **B2 x86 CPU 机 + 24 题镜像**（等 D7）。
4. **B4 四门 + 语义审计 + 两份判定**：产出 24 题账本；交 A 线作超时/wall-clock 决定的证据。
5. **B6 划分**：按 D2–D4 冻结 L1/L2 题单与 hash。
6. **B5 基座诊断**：2–4 条 smoke → 24 × 4；按 §6.3 判读。
7. **门 1** 决定训练池；A/B 合并决定 reward 判定与预算；进入首训。
8. 训练后按 §7.2 评 L2/L3；按 §7.3 决定是否扩容。

## 11. 本稿没有做的

没有跑容器、没有拉镜像、没有改代码、没有生成题单。文献数字均引自精读稿（作者自查级别），未复核原论文。SkyRL-v0-293 与 216 题的重叠未查。hydra/bokeh 环境可行性未查。
