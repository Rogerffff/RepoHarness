# RepoHarness 训练数据处理全过程指南

本文是数据处理工作的**叙事性指南**：按时间顺序讲清楚每一步做了什么、为什么这样做、踩了什么坑、留下了什么规则。目标读者是项目所有者本人——读完应能不依赖对话记录完全掌握数据侧的所有决策与产物。后续数据处理（S2 ingestion、环境验证门、GPU 预筛、success run 数据组装）继续在本文追加章节。

执行账本与证据在别处：逐条决策记录见 `implementation-notes.md`，产物清单与 digest 见 `freeze_manifest_v0.json`，收口报告见 `data_freeze_report.md`。本文不重复它们，只讲"为什么"。

---

## 1. 全景：我们到底有几种"数据"，各自扮演什么角色

先建立全局图，这是理解一切处置规则的前提：

```text
┌─ 评测面（绝不训练）────────────────────────────────────┐
│ SWE-bench Verified（500 题，12 个 Python 仓库）        │
│   角色：外部参考面。OpenAI 已公告它有污染与坏测试，      │
│   所以只报方向，不作成败判据。                          │
│ 自建 frozen held-out（从训练数据集切出 4 个 repo）      │
│   角色：主判据面——before/after 提升看这里。             │
└──────────────────────────────────────────────────────┘
┌─ 训练面 ─────────────────────────────────────────────┐
│ S1 基建冻结集（8 题，来自 Verified）                    │
│   角色：调基础设施的 smoke 集。允许来自 Verified 是因为  │
│   原本"只调不训"；后来 7a 引入真实训练步，所以补了       │
│   "checkpoint 用后即弃"硬条款。                         │
│ bring-up 训练集（SWE-Gym Lite 筛后 ~100-200 题）        │
│   角色：第一次链路级训练，不做能力结论。                 │
│ success run 训练集（300~800 题，R2E-Gym-Subset ≥50%）  │
│   角色：真正证明 RL 信号的能力 run。                    │
└──────────────────────────────────────────────────────┘
```

**为什么这样分**：评测与训练必须在**仓库级**完全隔离（同一个 repo 的题绝不能一边训一边测——模型会背下仓库结构而非学会修复），这是比"题目不重叠"强得多的约束。行业教训：SWE-rebench 只做了"时间去污"（按日期切），结果与 Verified 仓库大量重叠，被我们直接排除出候选。

四个数据源的选型依据（详见实验设计文档附录 B）：SWE-Gym 与 R2E-Gym-Subset 是仅有的"仓库级去污 + 有公开 RL 战绩 + 带预构建 Docker 镜像"的开源数据集；R2E 排到 success run 主力（≥50%）是因为 DeepSSWE 的逐字证据——他们在 SWE-Gym/SWE-Smith 上"limited improvements、high solve-none"，R2E-Gym 效果最好。

## 2. DF-1：元数据获取与互斥断言——"冻结"从取数开始

### 做了什么

从 HuggingFace datasets-server 拉四个数据集的行级元数据落地为 `meta/*.jsonl`（Verified 500 / Lite 230 / SWE-Gym 全量 2438 / R2E 4578），然后跑 `assert_repo_disjoint.py` 断言三方互斥。

### 为什么这样做，以及两个坑

**坑一：R2E 的行里藏着巨型字段。** 最初用 rows API 每页 100 行拉取，R2E 反复超时——因为它每行带 `parsed_commit_content`（金标修复 commit 全文）等字段，单页响应超过 100MB。解法是改用 **parquet 列裁剪**（HfFileSystem + pyarrow，只读 4 个轻字段），4578 行一次拿全。教训写成了规则：**取数时就只取需要的列，答案字段连本地磁盘都不该落**（后来 strip_spec 的哲学与此一致）。

**坑二：官方数字也要实测。** 文档链条里一直写 "Lite 234 题"，HF size 端点实测是 **230**。数字不大但说明一件事：任何进入冻结账本的数量都要以 API 实测为准，不采信转述。

**互斥断言为什么是脚本而不是一次性检查**：数据集在 HF 上会更新版本，repo 构成可能变。断言脚本（纯 stdlib、可重跑、fail-closed 非零退出）让"训练池 ∩ Verified = ∅"从一句话变成每次数据变更都能一键复验的不变量。实测结果：三方互斥全 PASS，唯一的跨源重复是 **pandas 同时出现在 SWE-Gym 和 R2E**——这不违反互斥（都在训练侧），但 S2 池化两源时要按 `(repo, base_commit)` 去重，防同一真实 commit 的题被采样两次。

## 3. DF-2：R2E 镜像"修复前状态"核验——一个可能推翻数据源的检查

### 为什么必须做

R2E 每行有个 `commit_hash` 字段，但语义没人说清：指修复 commit 还是它的 parent？更要命的问题：**镜像里的代码到底是修复前还是修复后？** 如果是修复后，那模型在 rollout 里看到的就是答案——整个数据源作废。这是前期调查留下的唯一"可能推翻性"待核项。

### 怎么验的（codex 执行）

抽 3 个不同仓库的实例（orange3/coveragepy/numpy——特意跨仓库，因为发现 R2E 行序按 repo 聚集，取前 5 行全是 orange3），拉镜像进容器：`git log` 看 HEAD、对照 `parsed_commit_content` 的 diff 检查关键修复行是否**不存在**于容器内文件。

### 结论与沉淀

三个镜像全部处于修复前状态；`commit_hash` = 金标修复 commit 本身，容器 HEAD = 它的 parent。这个语义被直接写成 S2 ingestion 的**物化断言**：每题物化时检查"容器 HEAD 必须是 commit_hash 的 parent，相等即 fail-closed"——把一次抽样核验升级为每题自动复验。顺带的副产品规则：**R2E 任何抽样必须跨 offset/分层，禁止取前 N 行**。

## 4. DF-3：strip_spec——每个字段的命运都要有明文判决

### 核心思想

数据集的每一行除了题面，还带着一堆**答案和答案线索**。处置原则不是"删掉危险的"，而是**白名单反转**：每个字段必须显式分类，ingestion 遇到 spec 没列的字段一律拒绝（fail-closed）——这样数据集将来加新字段时不会静默泄漏。

六类处置（`strip_spec.yaml`）：

```text
model_visible       可进 agent 上下文（仅 problem_statement，且要过泄漏扫描）
env_materialization 环境物化用的元数据（repo/base_commit/docker_image）
grader_only         评分资产，只在评分沙箱可见（test_patch/FAIL_TO_PASS/…）
validation_only     金标解，只供环境验证门用（patch/parsed_commit_content）
pipeline_meta       无害统计量（num_non_test_files 等）
strip               归档后从一切下游剥离（hints_text/modified_files/…）
```

**为什么要新增 validation_only 这一类**（原设计只有其余五类）：金标 patch 处境特殊——它绝不能进 rollout 或模型补丁的评分（那是作弊），但环境验证门跑 "golden patch 必须通过" 检查时又必须用它。原有类别表达不了"对 A 隐藏、对 B 开放"的双重约束，所以单独立类。这是数据层对最小权限原则的落实。

**具体例子帮助记忆**：SWE-Gym 的 `hints_text` 是 issue 评论区——线程调查实测里面常有维护者直接贴修复方向甚至代码，所以整体 strip；R2E 的 `modified_files`（修复触及哪些文件）看着无害，实际是**强定位泄漏**（等于告诉模型去改哪个文件），strip。

## 5. DF-4/5：静态质量打标——用 agent 额度在 GPU 之前挡住坏题

### 为什么需要这一层

GPU pass-rate 预筛很贵（每题要目标模型采样 8~16 次）。SPICE 论文证明"题意清晰度/可验证性/解法泄漏"三类标签可以用 LLM 自动标注（$5/千题级），在 GPU 之前先剔掉"题面含糊、测试没法断言、答案写在题里"的题，省下的都是真金白银的卡时。

### 校准协议——顺序为什么不能反

```text
第一步：我亲自读 5 题打标并锁定（此时不看任何模型输出）
第二步：claude headless 跑 20 题试点
第三步：对照一致率 ≥80% 才放行批量
```

顺序的关键在第一步的"不看模型输出"：如果先看了模型标签再做人工判断，人的判断会被锚定，校准就失去意义。实测一致率 15/15 = 100%（口径：5 题 × 3 标签的**标签级**判定），放行。

### 三个真实例子（正例/反例对比，见 `labels/calibration_human.jsonl`）

- **dask-7138（泄漏 fail 的典型）**：issue 里直接写了修复后的完整函数 `def ravel(array_like): return asanyarray(array_like).reshape((-1))`——这题模型不用"修"，抄就行。剔除。
- **MONAI-3326（批量里揪出的另一个 fail）**：题面原话 "The only change necessary, is to add the `affine` parameter and to forward it..."，附代码。剔除。
- **hydra-1783（容易误判成泄漏的正例）**：题面给出了期望的错误消息文本——这**不算泄漏**，因为"期望输出"是需求本体（消息类 bug 的需求必然含目标文本），实现在哪改一个字没提。保留。这条区分（需求本体 vs 实现提示）写进了打标 prompt 的锚点。

### D7 口径修正——本阶段最重要的一次"设计自纠"

最初正则扫描把题面和评论区合并判，命中 38/230（16.5%）。分字段归因后画面反转：**题面（模型可见面）只有 2 题命中（0.9%），另外 36 题的泄漏全部只在 hints_text 里**——而 hints 按 strip_spec 本来就整体剥离。由此确立规则：**泄漏门只对模型可见面生效**，仅 hints 来源的泄漏记录不剔题（否则会白白扔掉 36 道好题）。

LLM 语义层的同口径结果更有说服力：109/230（47.4%）的题存在仅 hints 来源的泄漏（评论区里的软泄漏比正则可测的 hash/URL 多得多），全部被剥离策略中和。**"剥离 issue 评论区"这一条决策消掉了 95% 以上的泄漏面**——这个数字直接进了 E8 的治理证据。

### 最终漏斗（Lite 230）

```text
230 题
 ├─ 剔 held-out repo（hydra 11 + bokeh 1）      −12   ← D5 不变量，见 §7
 ├─ 剔 test_adequacy fail（dvc-2017：打包/文档   −1
 │   整理任务，无可断言的运行时行为差异）
 ├─ 剔题面泄漏 fail（MONAI-3326）                −1
 └─ 存活 216 题 → 进入 GPU pass-rate 预筛候选池
     （其中 13 题 ps-warn 带 leakage_watch 标记进池，evidence 随行）
```

## 6. DF-6：镜像清单——一个"照惯例做必然全军覆没"的坑

SWE-Gym 数据行里**没有镜像字段**，镜像名要按 instance_id 拼。SWE-bench 官方惯例是把 `__` 替换成 `_1776_`，此前的调查文档也这么写。DF-6 的任务提示里特意要求"先实测 2~3 个再批量生成"——codex 实测发现 **SWE-Gym/OpenHands 用的是 `_s_` 替换**（`getmoto__moto-5752` → `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5752`）。若照惯例拼名，S2 拉镜像会 100% 失败。教训：**任何"按惯例推导"的机器可读产物，批量生成前必须抽样实测**。

其余产出：两份逐行验证过的镜像引用清单（直接消费，别再拼名）；磁盘外推 Lite ~0.5 TiB / SWE-Gym 全量 ~5.3 TiB / R2E ~2.3 TiB（显著高于早期粗估，success run 扩容前按 `image_manifest.md` 重新规划）；DockerHub 限流规避（三个数据源的镜像全挂在个人账号下，免费额度一个 batch 就打满——必须先同步到本地 registry）。

## 7. DF-7：held-out 切分——主判据面的出身

按 E5 定案从训练数据集**整仓库切出**：R2E 的 tornado(261) + pyramid(189)、SWE-Gym 的 hydra(66) + bokeh(26)，共 542 候选，将来经同一套门（静态 → 环境验证 → pass-rate 中段）冻结出 T≥50 的主判据集。

**为什么主判据不用 Verified**：一是 OpenAI 公告的坏测试与预训练污染问题；二是更根本的——主判据要回答"RL 在训练分布上学到了没有"，用与训练同分布、同治理门、同 harness 的 held-out 才是干净的自我对照，Verified 留作公开可比性的参考面。

**D5 不变量的由来**：抽试点样本时发现 Lite 230 里就含 hydra 11 题 + bokeh 1 题——如果 bring-up 拿 Lite 全量训练，就碰了主判据面的仓库。虽然 bring-up checkpoint 本来就即弃，但"**一切训练 run（含 bring-up）排除 held-out repos**"作为无例外规则的成本是零（去 12 题剩 218），于是立为不变量。原则：能用结构消灭的风险不靠纪律兜底。

## 8. DF-8 与评审修复：什么才叫"冻住了"

初版 manifest 有两个被检查线程（codex + claude 双评审）抓住的洞，修复过程本身有教学价值：

**洞一：revision 是假的。** fetch 脚本里 `jq -r '.dataset_info | keys[0]'` 抓到的是配置键字面量 `"default"`，不是 HF 数据集的 commit sha——即"冻结包"无法证明上游是哪个快照。修复：从 `https://huggingface.co/api/datasets/{id}` 取真实 `.sha` 写入 manifest 四源。教训：**声称"pin 住了"之前，先验证 pin 的值真的是版本标识**（"default" 这种值一眼就该起疑）。

**洞二：digest 账本只盖了 12 个文件，四个原始元数据 jsonl 都不在内**——意味着本地文件被改动无法被发现。修复：扩到 24 项（含全部数据文件、脚本、prompt），并跑 digest 自检。现在 manifest v0.1 满足两条：上游可证（4 个真实 revision）、本地可审（改动即可被 inspector 抓到）。

**抽检的口径选择**：评审要求补 10% 随机抽检，我们改做**门控相关标签全查**——2 个 fail 题人工读题复核（剔除均正确）+ 13 个 ps-warn 归因全部程序复核。理由：影响准入决定的判定只有这 15 个，全查它们比随机抽 23 题的证据效力更高。这个"按决策影响面分配复核预算"的思路后续复用。

## 9. 执行方式备忘（多 agent 分工与工程坑）

```text
分工模式：本线程写协议/规格/prompt 并做人工校准 →
  codex 干需要 docker/网络的重活（DF-2/DF-6）→
  claude headless（claude -p）跑批量打标（230 题零解析错误）。
坑1：后台驱动 codex exec 必须 `< /dev/null` 关闭 stdin，否则它把
  管道 stdin 当输入源无限阻塞且不报错（首次 DF-2 空转 2 小时）。
  配套规则：所有后台 agent 任务挂"日志增长探针"确认真的开工。
坑2：批量 LLM 作业先小试点校准再放量（20 题试点 → 230 批量），
  且 runner 要支持断点续跑（按 instance_id 去重追加写）。
```

## 10. 数据侧当前状态与遗留（截至 2026-07-08）

```text
已冻结：meta 四源（带真实 revision）/ strip_spec / Lite 静态门存活 216
  / held-out 候选 542 / 镜像清单与磁盘账 / manifest v0.1（24 digest）
已交接 S2：strip_spec 执行、镜像 _s_ 规则、R2E 物化断言、
  (repo, base_commit) 跨源去重、重抓数据必须重跑 fail-closed 字段检查
待做（按序）：
  1. S2 环境验证门（golden 必过/空 patch 必败/确定性，需 rh2 库）
  2. 单卡 GPU 作业：pass-rate 预筛 [0.1,0.8] + pre-RL 行为诊断
     （合并同批 rollout；输入 = 环境门存活集）→ bring-up 题单冻结
  3. R2E 打标（success run 题单确定后分批，复用 prompt v1；
     R2E 无 hints 字段，只扫 problem_statement）
  4. held-out 四道门走完 → 冻结 T≥50 主判据集
  5. success run 数据组装（R2E ≥50% + SWE-Gym 补多样性）
```

---

## 附：后续追加区

（S2 ingestion、环境验证门结果、GPU 预筛结果、held-out 冻结、success run 组装的过程与决策，按发生顺序追加在此。每条注明日期与决策编号，保持与 implementation-notes 的引用关系。）
