# B 线首轮：外部资料综合 + 资产现状 + 工作安排建议

日期：2026-09-08。作者：Claude（B 线分叉线程）。性质：**讨论稿**，不是定案；所有"建议"都待用户拍板，涉及 T0 的地方已标出。

支撑材料（同目录）：
- [reading_extract_recipe_notes.md](reading_extract_recipe_notes.md)：从 16 篇模型团队技术报告类笔记里抽出的环境、数据、评测、基座诊断事实（逐篇 9 项 + 跨篇对照表）。
- [repo_asset_inventory.md](repo_asset_inventory.md)：仓库里 216 题、镜像、评分链、四门、划分、eval、基座实测、外部工具的实际产物状态（实测，不是读文档）。

我本人全文读的笔记：E2 CalibForge、E5 SWE-smith、O03 R2E-Gym、O11 SWE-rebench V2、E8 ECHO、N13a/N13b OpenAI 两篇评测审计、N06 Hardening Agent Benchmarks、E1 Harness Interplay。其余 16 篇由子代理逐行抽取，我核对了对照表。

---

## 0. 一句话结论

精读库对"什么算可信环境、怎么评、基座怎么诊断"已经给出足够具体的做法，不需要再读更多才能开工；而资产盘点显示 **216 题从未在任何容器里跑过一次评分，且当前代码对它们必然 parser `KeyError`**（swebench 4.1.0 与 vendored fork 都没有 SWE-Gym 9 个仓库的 parser 映射）。所以 B 线首轮不是写设计，而是**在真实 x86 Linux 上把一小批题跑通四门并出第一份 pass/fail 账**，同时把基座诊断的记录格式和失败分类定下来。

---

## 1. 阅读综合：对 B 线最有用的 12 条（每条附来源）

### 环境有效性

1. **可执行 ≠ 可学 ≠ 有价值，三层要分开测。** CalibForge 把"环境能启动 + 初始全测试失败 + 作者自解通过"（`V(τ)`）和"指定 solver 有成有败"（`Cγ`）分成两个门，首次探测只有 19% 落在目标区间、61% 全过、16% 全失败（E2 §7.4）。SWE-smith 用难度评分器分层训练发现更难的任务并不带来更高 SFT 收益（E5 §5.3）。SWE-rebench V2 的 A/B 诊断标签在 5 模型上 A 类 pass@1 14–28% vs B* 类 0–6%（O11 §7.2）。对我们：216 题先证明"环境有效"，再用目标基座采样证明"当前可学"，两件事分开记账。
2. **四门是共识最小集，但 golden pass 只是存在性检查。** empty patch 必败、golden 必过、fresh reset 重复稳定（N=3）在 SWE-smith（验证 = 至少打破一个通过测试，超 2 分钟丢弃）、R2E-Gym（F2P 双态执行）、SWE-rebench V2（三次重跑结构化结果一致）、MAI（empty 多轮 fail + gold pass + 筛 flaky）都有对应。N06 用 KernelBench 的反例说明 gold 通过不能证明合法替代解也能通过：修补后攻击率归零但良性通过率也归零，靠事后 autopatch 才恢复（N06 §5.3–5.5）。CalibForge B.3 的"逐字段 nonce:ciphertext:tag 布局"误杀合法整体加密解也是同类。对我们：四门之外，对抽样题做 2–3 个**合法替代解**探针。
3. **题意与测试错配是高频问题，不是边角。** OpenAI 审计 SWE-bench Verified 里 o3 稳定失败的 138 题，59.4% 有实质题意/测试问题（35.5% narrow、18.8% wide）；SWE-bench Pro 731 题约 30% broken，四类是 overly strict tests、low-coverage tests、misleading prompt、underspecified prompt（N13a §4、N13b §4–5）。SWE-Gym Lite 的 216 题没有任何这类审计，只有 LLM 三标签静态打标（issue_clarity / test_adequacy / solution_leakage）。对我们：对首批 20 题做一次 N13b 式的"题意-测试-gold"对照审查，报告分母，不宣称全库比例。

### 控制面与反作弊

4. **verifier 完整性清单已有成熟版本，逐项对照 216 镜像即可。** Intern-S2 §4.4.3：gold patch、held-out tests、评分 test ID 不进 workspace；git 历史清成单 baseline commit、删 remote refs；agent 停止后恢复 canonical tests 再打 gold test patch；all-correct（目标修复 + 回归都过）；**缺 grading 工件/执行故障/verifier 输出不可解析单独记账，与任务失败分离**（E10 §5.6）。Nemotron 3 Ultra 把容器 git 历史物理重写为 base 时刻 fresh clone 并拦 remote git 与 GitHub HTTP（R2）。Qwen3-Coder-Next 删 remotes/branches/tags 并做 repo link×网络关键词 blocker（R3）。对我们：先检查 `xingyaoww` 镜像的 `git log` 是否暴露修复 commit（E10 为此改了 SWE-bench Pro 官方镜像）；rh2 现有 git-sanitize 已覆盖大半，缺的是"跑完恢复 canonical tests"的实证和 infra/task 分账。
5. **收紧 verifier 必须同时测良性通过率。** N06 Terminal Bench 77 题：无提示攻击成功率 39.2%→16.7%，同时良性通过率 76.1%→65.2%；八类 hint 单独看没有一类在 Bonferroni 下显著；共享防御池在一种配置下反而把 judge 过滤后的 hinted 攻击率**提高** 7.8pp（N06 §6）。对我们：rh2 的 F2 权限机制、控制面 glob 等任何改动，都要在同一批题上报"攻击样例通过率 + gold 通过率 + 合法替代解通过率"三个数，不能只报攻击率。

### 难度与采样

6. **难度分带是通行做法，但都是 T0 级准入决策。** MAI early 16 条筛 [0.05,0.8]、全组 [0.1,0.8]；Nemotron-Cascade 2 用中间模型 16 条采样"删全过、全失败随机留 10%"；Nemotron 3 Ultra STEM 用 pass rate 0.25–0.80；SkyRL Deep Research 用 4 次 rollout 分 0/1/2/3 of 4 且 4/4 不纳入（reading_extract §1、§4、§5、§12）。对我们：基座诊断跑 n=8 后按 pass@8 分带只是**记录**，是否据此筛训练池归 C 包/用户。

### 划分与污染

7. **没有一篇公开 SWE 训练切分与污染细节；时间截止也证明不了预训练干净。** N13a 展示三个模型在诱导提示下复述 Verified 的修复细节；SWE-smith 用 Verified 题面做风格示例、用 Verified 标注训练难度评分器，所以"排除 12 个测试仓库"不等于零接触（E5 §6.2）。对我们：现有仓库级 held-out 规则（tornado/pyramid/hydra/bokeh）+ Verified 作为外部坐标已经是合理最小做法；不要在污染审计上投入超过"记录切分、记录探针覆盖"的成本。

### 评测协议

8. **协议记录 schema 直接抄 GLM-5.2。** 每个 benchmark 记 harness + 版本（Claude Code 2.1.167）、CPU/内存、timeout、max_new_tokens、max_turns、context、runs 数，五次均值（R5b §7）。MiniMax-M2 用 Claude Code 统一 scaffold 并覆盖默认 system prompt、4 trials 平均、TB 用 8 vCPU/16 GB/2 h（R4 §5）。对我们：诊断和评测的 run 记录按这个 schema 写。
9. **harness 敏感性大到必须固定版本。** Nemotron 3 Ultra 同一模型在 Verified：Claude Code 2.1.126 得 60.3 vs OpenHands 1.17.0 得 70.3，七个 harness 均值 60.6（R2 图 17）。Kimi K3 的 TB2.1 取跨 harness 最优（R13）。对我们：所有基座数字必须写明 Claude Code 版本，第二 harness 的数字单列。
10. **样本量决定能看到多大的差。** SWE-rebench V2 附录 C 每语言 60 题的 95% CI 半宽约 ±4–6pp（O11 §7.3）；设计建议 §7.2 的算术：100 题 ±9.8pp、200 题 ±6.9pp 单比例。对我们：dev 探针集少于 60 题只能看到十几个点的差；首训"有无学习"判据要和这个精度匹配（见第 11 条锚点）。
11. **同量级基座的期望锚点。** Qwen3-30B-A3B-Thinking-2507 在 OpenHands/300 turns/128k 下 SWE-bench Verified 23.0，GRPO+DIS 一轮 +4pp、SAO 29.8（R15）；Qwen3-30B-A3B-Instruct-2507 在 Terminus-KIRA/256k 单窗口 25.2、TB2.0 5.34（R14 表 2）；SkyRL 用 Qwen3-32B 起步时 64 组里 50 组全失败（O01 §4.2）。对我们：Claude Code + 600 s + 25 轮的条件比这些都紧，216 题 SWE-Gym Lite 的基座通过率大概率低于 20%，0/8 组比例可能过半。这决定了"有没有可学任务"要先量，而不是先训。

### 成本

12. **单位成本可估，别再空想。** SWE-rebench V2 每仓 setup 推理约 $0.087、每次 Docker 构建均值 2.71 min、每任务存储约 0.84 GiB（O11 §9）；SWE-smith 128 仓 295 GB（E5 §6.1）。我们 216 题镜像抽样外推约 480 GiB 拉取量；四门 216×8 次评分按 s2_1 计划估 x86 CPU 机 1–2 天、$15–40。

**对笔记本身的两条提醒**：前两批 14 篇有线程内独立审查；外部 Pro 的 9 篇只有作者自查（README 已标），O11 的 Table 8、N06 的 Table 4–8 尚未做原页目视核验；R5c GLM-5.3 与 E3 Envs-FORGE 原文都没取到，它们的数字不能引用。

---

## 2. 资产现状：有什么、没什么（盘点要点，细节见 repo_asset_inventory.md）

| 项 | 状态 | 关键事实 |
| --- | --- | --- |
| 216 题四面 bundle | 有产物，复核通过 | 7 pins + 5 数据文件 + trusted loader 216/216 通过。**只覆盖 9 个仓库**（hydra 11 + bokeh 1 已作 held-out 剔除），文档里"11 仓库"指 Lite 全集 |
| 镜像 | 有 digest 实证，无本地副本 | Docker Hub `xingyaoww/…:latest`，216 题逐题 manifest/config digest；本机 0 个；体积约 480 GiB（外推） |
| 评分链 | **对 216 题全部不可评分** | `parse_log` 实测 `KeyError('getmoto/moto')`；manager 判 `test_log_parse_failed` → infra → 整组丢；swebench 4.1.0 与 vendored fork 都无 parser 映射；216 题 eval_cmd 全是 pytest 变体 |
| 四门 runner | 零代码 | 规格详尽（empty/golden/determinism N=3 + 假阳性探针），`grade_controlled_patch`/`EnvValidationReport` 全仓无 |
| 真实评分记录 | 仅 8 题 Verified | 216 题零次；两个未验证边界：mypy 40 题 eval_cmd 以 `-k` 结尾却被拼上文件路径；conan 12 题的 `eval_commands` 未被渲染器消费 |
| 静态质量标签 | 有产物 | issue_clarity/test_adequacy/solution_leakage 三标签；13 题 leakage warn 的标记没进 bundle |
| 划分 | 只有规则 | 仓库级 held-out 常量；542 题 held-out 候选只有元数据；无 train/dev/test 产物 |
| eval 资产 | 1 条冒烟 prompt | Verified django-11099；无 SWE-Gym eval 题单 |
| 基座实测 | 仅 Qwen3-4B × 8 题 Verified | run8 5/32、run9 1/32 resolved；无轮数/失败位置归因；CC 2.1.202 与当前 pin 2.1.205 不同 |
| 本机 | 无权重、无 CC tarball、Apple Silicon | x86 镜像只能 QEMU 模拟，四门与诊断都不该在本机跑 |
| 外部源 | 无本地克隆 | SWE-smith/R2E-Gym/SWE-Gym 官方仓/swe-rebench 都没 clone；`rh2/.venv` 有 swebench 4.1.0、huggingface_hub、datasets |

**文档与实际不符的两处最要紧**：(a) 06 计划 T2-d/T2-e 写"由既有数据线程继续"，但 2026-07-20 之后数据线零进展；(b) T2-a 报告推论"运行期评分 = test_cmd + 选择器 + 官方 parser"，官方 parser 对这 9 个仓库根本没有条目。

---

## 3. 建议的首轮工作（按依赖顺序，标注谁做、要什么、怎么验收）

### B1 · parser 适配（不依赖任何决定，可立即做）

- 做什么：给 9 个仓库接 pytest 系 parser。swebench `log_parsers.python` 已有 `parse_log_pytest` / `parse_log_pytest_v2` 等；写一个 `repo → parser` 的小映射（约 30 行）+ 单测，用 SWE-Gym fork 的 `test_cmd` 形态（`-rA`、`-n0`、`--color=no`、`--tb=long`）各挑一题构造真实日志样例。
- 归属：评分投影/通用 grader 是 A 的，但"这 9 个仓库用哪个 parser"是任务适配，属 B；改动落在 `envpack/scoring.py`（去掉 `make_test_spec` 依赖，直接调 parser + `get_eval_tests_report`），需要 A 复核。这也是 A 线 P0-3 里"parser 缺失 → 应启动预检"的前置。
- 验收：对 20 题的 golden 日志解析出非空 status map，且 F2P/P2P 判定与手工核对一致。

### B2 · x86 Linux 验证基质 + 首批镜像

- 做什么：租一台 x86 CPU 机（16 核以上、1 TB 盘即可，不要 GPU），起本地 `registry:2`，按 `image_manifest.md` 的 runbook 拉首批 20 题镜像（约 45 GiB），核 digest。
- 为什么不在本机：Apple Silicon 跑 x86 镜像是 QEMU，测试时长和 flakiness 都不可信；四门要"同一基质"才能与 T5 全量比。
- 费用：按 s2_1 计划的估算 $0.3–0.8/h；20 题 × 8 次评分一天内跑完。

### B3 · 首批 20 题选题（我可以直接给题单）

覆盖原则：9 个仓库都至少 1 题；8 种 eval_cmd 各至少 1 题；mypy `-k` 边界 3 题、conan `eval_commands` 边界 2 题；P2P 为空的 22 题里取 2 题；leakage warn 13 题里取 2 题；F2P 数 1 与 >5 各有。同一 (repo, version) 不重复以多测 toolchain。

### B4 · 四门 + 语义审计（B 主责，产出第一份账）

- 四门：empty patch 必败（前提是 parser 解析成功且测试真跑）、golden 必过（F2P 全过 ∧ P2P 零失败）、各 N=3 fresh 容器确定性；探针层：无关文件 patch 应 FAIL。每次运行写一行 jsonl（task_id、gate、image_digest、attempt、verdict、F2P/P2P 集合、时长、infra 错误），不建 schema 平台。
- 语义审计：对 20 题按 N13b 四类做"题意 ↔ 测试 ↔ gold"对照；对 3–5 题写合法替代解探针（改不同文件/不同结构实现同一行为），记录是否被误杀。
- 验收：一张 20 题 × {empty, golden, determinism, alt-solution, spec-test 审查} 的表 + 时长分布 + 每题 infra 错误清单。**这张表是 A 线判断"超时/零解析改 reward 0"是否安全的证据。**

### B5 · 基座诊断准备（与 A 交接，等用户定推理方案）

- 记录格式：按 GLM-5.2 schema（harness 版本、CPU/内存、timeout、turns、context、runs），每条轨迹记轮数、生成 token、工具调用分布（read/grep/edit/bash/test）、结束原因、评分结果、墙钟；请求体原样保存（A 线 REALIGN 根因分析要用）。
- 失败分类：先用 Intern-S2 §5.5 的类别（parse/格式、工具名/参数错、重复或失败调用、context/turn/session 上限终止）+ Nemotron Ultra 轨迹分析器的规则（禁用 git 操作、edit 后不测试、残留调试打印、反复 edit-test 循环）**只统计不惩罚**；再叠"定位/修改/验证/交付"四阶段的人工标注（前 20 条）。
- 需要 A 提供：只起推理（SGLang + adapter + sandbox + grader）不起 learner 的入口；盘点显示现在没有这样的脚本（`fa_audit_only` 仍要 Ray + 训练容器，`j2_sglang_30b.sh` 不接 harness）。
- 需要用户定：推理载体。单张 5090（32 GB）放不下 bf16 30B-A3B，要 FP8/INT4；量化后采样分布与训练侧 bf16 不同，得到的是"量化变体的行为与成本画像"，能回答工具使用、失败位置、轮数、上下文，通过率不能直接当训练侧基座数字。两张大显存卡 bf16 TP2 更贴近正式链。

### B6 · 划分建议（T0，等讨论）

- 216 题内：按仓库分层抽 **≤40 题作 dev 探针集**（可反复用于调参、选修法），其余为候选训练池；两者在 (repo, base_commit) 上互斥（两簇同环境不同题要放同一侧）。
- 最终测试：SWE-bench Verified 是仓库不相交的外部坐标（SWE-Gym 构造时排除了这些仓库），但对预训练污染无免疫；建议取 100–200 题分层子集固定版本、固定协议，只在最后跑。R2E tornado/pyramid held-out 需要另一套 ingestion，首版不做。
- 与 A 的接口：dev 探针集就是 A 做投影/消费核验的"真实交接点"题单。

### 不建议现在做的

- 不做 SWE-smith/R2E/Scale-SWE 的新 ingestion（216 题还没跑通一次）。
- 不做 terminal 训练题；terminal 只在首训后作评测探针（TB2.0 89 题 + Terminus-2，固定 8 vCPU/16 GB/2 h）。
- 不建通用环境质量平台、`EnvValidationReport` 大 schema、LLM judge。
- 不在污染审计上超过"记录切分 + 记录探针覆盖"。

---

## 4. 需要用户决定的（按紧急度）

1. **B1 parser 适配由 B 做、A 复核**，是否接受这个归属。
2. **x86 CPU 机租用**：形式与预算（四门 20 题一天内，$10 以内；后续 216 全量 1–2 天）。
3. **基座诊断的推理载体**：单 5090 量化 vs 双卡 bf16；以及是否先用 API 模型（如 DeepSeek/GPT）跑一遍环境有效性（便宜、与目标模型无关，但不能替代基座画像）。
4. **20 题题单**：我给出候选后你确认。
5. **划分（T0）**：≤40 题 dev 探针 + Verified 子集作最终坐标。
6. **超时/零解析改判 reward 0**（A 线 T0）：B 的四门表是证据来源，需要在 B4 之后再定。

---

## 5. 精读库里 B 相关但还没有笔记的来源（是否补读）

| 来源 | 对 B 的价值 | 建议 |
| --- | --- | --- |
| O04 SWE-Gym 论文（2412.21139） | 我们的数据源本身：构建方式、镜像、原始验证做了什么 | **补读**，短；决定我们对 216 题的信任起点 |
| O28 SWE-rebench 经验谈 + Nebius 基建博客 | 真实评测运维教训（flaky、超时、隔离） | 补读，短 |
| O05 Scale-SWE | 若 216 题可学任务不足，最近的候选来源 | 等 B4 结果再定 |
| N14 Terminal-Bench 2.1/4.0 版本说明 | terminal 探针协议 | 做 terminal 探针时再读 |
| N15 DeepSWE benchmark（Datacurve） | 外部坐标候选之一 | 若选它作最终坐标再读 |
| E4 Endless Terminals、N03 Socratic-SWE | terminal 合成、自演化 | 首版不需要 |
| O19 Prime Environments Hub、O26 OpenEnv、O23 AEnvironment | 环境接口通用性 | 首版不需要 |

---

## 6. 本轮没有做的

- 没有跑任何容器、没有拉镜像、没有改代码；parser 缺口的实证来自 `rh2/.venv` 里的离线探针。
- 没有复核外部 Pro 那 9 篇笔记的原文；引用它们的数字时已标注"作者自查"。
- 侧边栏 REALIGN 讨论（A 线）没有读；B5 的"请求体原样保存"是给 A 线留的接口。
