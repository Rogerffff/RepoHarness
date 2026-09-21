# 环境筛选流水线：对阶段设计的反思、外部做法综述与重构方案

日期：2026-09-11。作者：Claude（B 线）。性质：**分析与设计建议**，供用户审阅后决定；没有新实验、没有改代码。输入：阶段一执行记录（[morning_followup_20260911.md](morning_followup_20260911.md)、`ledger/stage1_offline_20260911_summary.json`）、用户与 Codex 关于网络阶段的问答、A 线 [第四组评分决策](../batch4_scoring_20260910/README.md)，以及精读库（含远端 `research/deepseek-v41-flash-20260910` 新增的 R6c、miles 两篇，本机尚未合入，直接从分支读取）。

## 0. 结论

1. **你的判断基本成立：之前的阶段是按"今晚能跑什么"排的，不是按环境生命周期排的。** 最直接的证据是 MONAI-1121：离线 gold 判 NO，预置权重后判 FULL。没有"资源预置"这一步，任何门的结果都不是题目结论，而只是"在某个未声明条件下的观察"。阶段一的数据没有白跑，它给出的正是流水线必须处理的故障分类；错的是把它当验收。
2. **网络不是开关，是按阶段声明的策略。** 至少五个阶段各有不同需求：环境预置、agent 解题、评分安装/构建、测试执行，以及被忽略的第五个：参考结果（F2P/P2P、expected map）本身是在什么条件下生成的。modin 与 coveragepy 两例说明上游参考集的生成条件不可知，必须在我们自己的策略下重验证。
3. **重构后的顺序：真实评分链先通（含策略与预置钩子）→ 流水线设计定案 → 在 216 + 24 上实施并迭代 → 用定型的流水线扩容。** 原"阶段 3 环境包与迁移预检"取消独立地位，它的产物（环境资产清单、pin）是流水线的自然副产品。
4. 外部资料里没有任何一家用"empty/gold 过了就算环境好"；所有成熟流水线都有独立的**预置**、**合同构造**、**执行验证（重复）**、**质量复审（LLM + 人 + 求解轨迹）**、**泄漏与完整性控制**、**冻结清单**、**训练后重审**这几层。我们缺的是前两层和最后一层，以及把它们接到真实评分链上。

---

## 1. 阶段一暴露了什么（按流水线环节归类）

| 现象（阶段一 / 昨夜） | 它属于哪一环 | 之前的设计把它当成了什么 |
| --- | --- | --- |
| MONAI-1121 离线 NO、预置 ResNet 权重后 FULL；MONAI-3205 依赖 Hippocampus 测试数据下载 | **资源预置**（权重、测试数据是环境资产） | 当成"题目在离线下不可解" |
| moto-4799/4833 的网络测试在 mock 停止时打真实 EC2；modin S3 测试有网 NoSuchBucket、无网 PASSED | **测试执行的网络策略 + 参考集生成条件** | 当成"网络敏感题"二元标签 |
| 离线安装失败 116 次（moto 74、pydantic 40、dask 2）但判定不变 | **评分安装阶段策略**（install 与 test 应分开） | 当成"install 可省" |
| 10 题参考 ID 与镜像内 pytest 输出不一致 | **任务合同**（参考集要在我们的 parser/镜像下重生成） | 当成"数据坏" |
| datalad 新断言引用旧仓库测试 fixture，gold 排除测试文件导致 fixture 未移植 | **任务合同**（测试材料完整性） | 未覆盖 |
| coveragepy 上游 expected 记录了历史环境失败（mock 不可见） | **参考集生成条件** | 未覆盖 |
| MONAI-763 共享内存 64 MiB → SIGBUS；pandas 重编译 700 s；modin 18 min | **资源与超时配置** | 当成"噪声" |
| MONAI-2454 候选新建官方同名测试文件 | **评分投影语义**（rh2 已有处理，需真实链核） | 当成 grader 缺陷 |
| DeepSeek 三条轨迹下载上游修复 | **agent 解题阶段的网络策略与泄漏控制** | 当成探针瑕疵 |
| Pydantic-5706 官方通过但破坏 Sequence 行为 | **质量复审（测试覆盖）** | 未覆盖 |
| 镜像工作区自带未提交改动：R2E 镜像 2–7 行（aiohttp、pandas 为 7 行），SWE-Gym 镜像 0–2 行（pydantic 2 行；mypy/dvc/MONAI 部分 1 行），具体文件未记录 | **环境资产基线** | 未覆盖 |

十一类现象里，能被"empty/gold 门"正确归因的只有 ID 一类；其余都需要先有"预置状态"和"阶段策略"的声明才能判读。这就是"乱测"感的来源。

---

## 2. 外部资料怎样做环境/数据流水线

只摘与流水线结构直接相关的做法，每条注来源笔记。

| 来源 | 预置（环境怎么来） | 合同（测试/参考怎么定） | 执行验证 | 质量复审 | 泄漏与完整性 | 冻结 | 训练后重审 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| SWE-Gym（O04） | 11 仓库按版本半人工装环境，约 200 人时 + 10k CPU 时，镜像约 6 TB | 官方 fork 的 spec：安装、`eval_commands`、测试命令（mypy `-k`）、逐仓 parser；F2P/P2P 由 gold vs base 差分 | gold/empty 各一次的 validation runner（中间布尔 ≠ 最终 F2P/P2P 判定） | Lite 只按 gold 简单性筛，无题意审计 | 去 origin 但历史保留 | HF revision + 镜像 tag（非 digest） | 无 |
| R2E-Gym（O03） | 依赖版本组合逐一试装，作者自认半人工难扩展 | 隐藏测试目录 `/r2e_tests`；expected 是**状态映射**（可含 FAILED/ERROR）；测试生成时可见 gold；补丁最小化 | F2P 验证；无 fresh 重复稳定性报告 | 无 | 修复提交留在镜像 git 历史（我们已实测） | HF revision；`docker_image` 字段 | 无 |
| SWE-smith（E5） | **环境先行**：每 repo@commit 装一次（>80% 测试通过，人核 Dockerfile + parser），一镜像承载多题 | 逆向 bug patch；测试对 agent **可见** | 候选必须打破 ≥1 测试；>2 min 丢弃 | 明说未做题意/泄漏审计 | 无 | 数据卡 | 无 |
| SWE-rebench V2（O11） | LLM agent（mini-SWE-agent）在每仓最新快照上交互生成 install/test 配置，复用于历史任务；按语言的 base Dockerfile | 全套件 base+gold 跑；LLM 逐仓生成 parser（稳定可区分参数化 ID）；编译语言显式 rebuild；JVM 优先 JUnit XML | **×3 重跑结构化结果一致**才保留 | 三 judge ensemble 判题面清晰度；元数据 A/B1–B7（难度、完整性、外链…）；现成模型求解诊断 | 时间切分标注污染；评测时清未来 git 历史、轨迹审计（O28b） | 数据卡 + 版本化 builder | 用求解结果反查 always-fail |
| ScaleSWE（O05） | EBA agent 交互建环境后提炼 Dockerfile；每仓 ≤10 锚点，邻近 PR 复用 | UCA 生成/补测试；PSWA 重写题面并说明必要接口；`f2p_patch` 与 `f2p_script` 并存 | base/gold 四条件；固定执行顺序 | 4 人抽审 100 题 94 有效 | Appendix D 的 git 清理脚本 | HF + `aweaiteam/scaleswe:<id>` tag | 无 |
| Prime tasksets（prime） | 复用上游镜像，转存 registry | 逐来源 reward 语义（R2E 状态映射 / rebench、Scale 目标 ID 全 PASSED）；setup 时搬走隐藏测试 | gold 验证；R2E 失败再试 10 次 | 元数据过滤（rebench）；always-fail 反查 | 2026-09 放开 solver 出网 + fair-use 提示 | 数据卡 + 排除清单 | RL 全零组触发 gold 复验 |
| LinkedIn 修复（task09） | 固定依赖、关闭自动更新后，历史修复重建失败率从 40% 降；1% 不改也通过 | — | 按初始构建 <100 s 过滤（承认偏置） | — | — | — | 3K 步出现删验证代码 |
| DeepSeek V4.1 Flash（R6c §6） | **独立环境搭建 agent**：装依赖、准备工作目录与测试、自测、清泄漏痕迹、打成新 image layer | 任务 = (problem, environment, verification)；F2P/P2P evaluation points + construction report；可取网络资源 | 多个求解器试做 | **独立质检 agent**：环境、事实、题面—评价点错配、可 hack 性，读 solver 轨迹；repair agent 修后再验 | 清理泄漏痕迹 | 未公开清单 | **每次 RL run 的新轨迹都作为质量重审证据** |
| FrogNano（frognano） | SWE-rebench 快照 | 五件套；生成器构造题面/gold/hidden F2P，继承 P2P | 执行验证 | 策略相对校准（N 次采样，目标 0<p≤0.5）；题面 refinement 改变信息量而非难度 | Appendix F/G 记录恢复哪些文件、可见哪些历史/网络 | 逐轮冻结 | 每轮 |
| OpenAI 审计（N13a/b） | — | — | — | agent 逐题调查稳定失败题，分测试过窄/过宽/覆盖不足/题面误导；Verified 未稳定解决的 138 题里 59.4% 有题目问题 | — | — | 用求解结果驱动审计 |
| Nemotron / Dressage（R2 摘、dressage §4） | — | — | fresh official harness | 轨迹分析器 include/exclude 规则 | 重写 git 历史、命令过滤 remote git/HTTP；Dressage 事后检测 clone/curl/gh 并归零 | — | — |

**共同的骨架**（凡是做过大规模训练的团队都有）：

```text
来源接入与过滤 → 环境预置（联网、可迭代、产出可固定的资产）→ 任务合同构造
→ 执行验证（base/gold、重复、重建）→ 质量复审（LLM judge + 人工抽审 + 求解轨迹）
→ 泄漏与完整性控制（历史、网络、命令）→ 冻结与清单 → 训练/求解后重审
```

我们现在有：来源接入（216 + 24）、执行验证（oracle runner）、部分泄漏控制（rh2 git-sanitize、deny_all）、冻结（digest、bundle）。缺：**预置**、**合同的本地重生成**、**质量复审**、**训练后重审**，以及把执行验证接到真实评分链。

---

## 3. 流水线设计（供审阅）

### 3.1 对象模型：把"题"拆成五个可独立验证的东西

```text
Task         = SourceRow@revision（题面、base、上游参考材料）
EnvAsset     = image@digest + 预置配方（额外下载：权重/测试数据/包缓存；服务桩；派生层 digest）+ 资源配置（cpu/mem/shm/超时）
Contract     = 测试命令（含 eval_commands、-k）+ parser + 测试材料（隐藏测试、fixture 完整）+ 参考结果（本地重验证的 F2P/P2P 或 expected map）+ 参考生成条件
Policy       = 五个阶段各自的网络与权限策略（见 3.2）
QualityRec   = 执行证据 + 审计标签 + 求解轨迹证据 + 决策与 lineage
```

一道题"通过"必须写成：`在 EnvAsset X、Policy Y 下，Contract Z 的 empty/gold/重复/探针结果`。没有前三者的声明，结果不进池。

### 3.2 五阶段策略（把你和 Codex 的四阶段加上第五个）

| 阶段 | 网络 | 权限 | 谁执行 | 备注 |
| --- | --- | --- | --- | --- |
| P0 预置 | 允许联网 | root | 流水线（一次性） | 下载权重/测试数据/包缓存，固定版本与 sha256，打成派生层或缓存卷；派生镜像记新 digest；gold、私有测试、密钥不进 agent 可见层 |
| P1 agent 解题 | rh2 rollout profile：只通模型代理 | agent/54321 | rollout | 是否放开文档/包源是**训练设计选择（T0）**，单独报告；默认 deny |
| P2 评分安装/构建 | 默认离线（用 P0 缓存）；确需联网的走"可信 setup"白名单包源，且**不在联网状态下执行候选代码** | root 可信步骤 | grader | 编译型仓库的 build 会执行候选修改过的 setup.py，因此 build 必须离线；离线不能 build 的题标 `build_needs_network` 隔离 |
| P3 测试执行 | deny_all；服务依赖用本地桩（moto server 等）或 P0 预置 | rh2grader/54322 | grader | 需要真实外部端点的测试标 `test_needs_service`，不进训练池 |
| P4 参考生成 | **与 P2/P3 相同策略下本地重生成** | — | 流水线 | 上游 F2P/P2P、expected 只作对照；本地重验证结果才是训练 reward 的参考；差异逐条记录（ID、环境失败、状态漂移） |

P4 是本设计最重要、也最需要你拍板的一条：它意味着训练池的参考集定义是"我们的策略下 base 失败、gold 通过、三次一致的测试集合"，而不是上游字段。对外部评测坐标（Verified）仍用上游定义。这是 T0。

### 3.3 流水线环节与门

| 环节 | 输入 | 动作 | 输出 / 门 | 归因类别 |
| --- | --- | --- | --- | --- |
| E0 接入 | 上游行 @revision、镜像 ref | digest 冻结、11 列完整行、镜像基线（脏文件、未来历史、控制文件）记录 | Task + 基线事实 | — |
| E1 预置 | Task + 首次离线 gold 失败日志 | 识别缺失资产（权重/数据/包/服务），P0 下载固定，派生层 | EnvAsset（配方 + digest）；`provision_status` | resource_missing |
| E2 合同 | 官方 spec + 镜像 | 生成命令/parser/隐藏测试布置；核 fixture 完整（测试文件 import 的仓库测试模块是否随 gold 变化） | Contract 草案；`fixture_incomplete` | contract |
| E3 执行验证（真实 rh2 grader） | EnvAsset + Contract + Policy | empty、gold、×3 fresh；无关补丁；编译型 rebuild 检查 | 本地参考集（P4）；`env_valid`；耗时/内存/shm 事实 | policy / resource / contract / task |
| E4 质量复审 | E3 产物 + 题面 + gold + 测试 | 静态 rubric（四类 + 环境/parser）；扩展回归（显式选择规则）；手工反例与替代解；求解轨迹复核 | `quality_labels` + 证据；处置建议 | task_intrinsic |
| E5 难度/可学习性 | 目标基座 | N 次采样、成功分布、轮数与成本 | `learnability`（后做） | — |
| E6 冻结与划分 | 全部记录 | 训练候选 / 评测候选 / 隔离 / 待核 四态；lineage；清单 | 池清单 + 数据卡 | — |
| E7 训练后重审 | RL/求解轨迹 | always-fail / suspicious-pass 反查、hack 迹象 → 回 E1–E4 | 更新标签 | — |

阶段一的 11 类现象都能落在 E1–E4 的某一类；E1 与 E2 是新增环节，E3 从 oracle runner 换成真实 rh2 grader。

### 3.4 rh2 侧需要什么（阶段 S1 的范围，T1/T0 分开）

| 需求 | 现状（代码事实） | 性质 |
| --- | --- | --- |
| parser 与命令按来源分派（SWE-Gym fork 的 parser、mypy `-k`、conan `eval_commands`） | `scoring.parse_official_eval` 用 swebench 4.1.0；`_v2_candidate_test_lines` 只拼 `eval_cmd + 文件` | T1，B 写 A 复核（A 第四组 I06 已列） |
| 可信 setup 阶段的预置资产注入（缓存目录、权重、测试数据） | trusted setup 只做 checkout + test_patch | T1（新增注入点）；资产来源与 digest 由流水线给 |
| P2 安装/构建的网络策略（离线优先；白名单包源） | grader deny_all | 放开任何出网是 T0；先只做离线 + 预置 |
| P3 服务桩（例如 moto server 本地起） | 无 | 逐来源需求，先记录哪些题需要 |
| 资源旋钮：`shm_size`、按仓库 memory/timeout | profile 有 cpu/mem/tmpfs，无 shm | T1 加字段；数值 C 校准 |
| 候选执行失败 → 0 的表达；控制面 glob 收窄；缓存过滤；文件变目录 | A 第四组 A–D 四项待定 | A 线 T0，B 提供对照工件 |
| 本地参考集（P4）在 grader 中作为 reward 依据，上游参考集作对照 | GradingReport 按 bundle 的 F2P/P2P | **T0**（改变训练 reward 的参考定义） |

### 3.5 质量复审怎样接进来（原阶段 5 的内容，这次放进流水线而不是单独阶段）

- **自动层（E3 附带）**：参考覆盖、网络敏感、shm、ID 一致性、install/test 分列、编译型 rebuild 生效检查（候选修改的模块是否被导入）。
- **审计层（E4）**：本地 agent 按固定 rubric（先不看 gold）产标签；首批 24–32 题混合已知反例/正常/随机，测漏检与耗时，再扩全池轻量。
- **对照层（E4）**：扩展回归用显式规则（候选轨迹跑过且失败的测试 + 同包目录测试，base/gold/candidate 三方）；手工反例与合法替代解校准。
- **求解层（E4/E7）**：受控出网（复用 rh2 relay，上游指 API 主机）+ 起始工作区基线，之后才用 DeepSeek 或目标基座的轨迹做复审；DeepSeek 已有 24 条轨迹先复用。

---

## 4. 重构后的阶段（每阶段单独确认）

| 新阶段 | 内容 | 前置 | 交付 |
| --- | --- | --- | --- |
| **S1 真实评分链接通**（原阶段 2，扩大） | 3.4 表中的 T1 项 + 与 A 对齐第四组四项；用阶段一的失败题当对照：MONAI-1121（预置）、modin-6937（P3 网络）、pandas-48106（ID）、datalad（fixture）、MONAI-2454（投影）、moto-4799（服务）、MONAI-763（shm）；输出每题在 `EnvAsset/Policy/Contract` 声明下的真实 grader 结果与归因 | A 的第四组决定；frozen delta 入口 | 216 + 24 在真实链下的首份归因表；rh2 变更清单 |
| **S2 流水线定案**（本稿 → 审阅 → 决策） | 3.2 五阶段策略、P4 本地参考集（T0）、E1–E7 环节、门与标签定义、账本字段、处置四态 | S1 的真实数据 | 定案文档 + 决策记录 |
| **S3 在 216 + 24 上实施**（原阶段 5 + 环境预置） | E1 预置（MONAI 权重/数据、moto 桩、包缓存）、E2 合同重生成、E3 真实链 ×3、E4 复审首批、E6 首份池清单（训练候选 / 评测候选 / 隔离 / 待核） | S2 | 首个"经流水线验证"的池 + 失效分类账 |
| **S4 扩容**（原阶段 4） | 用定型流水线跑 Full 256 / R2E 128 / rebench 16–32；评测候选仓库单独计数 | S3 | 候选池扩展与单位成本 |
| 取消独立的"环境包与迁移预检" | 其产物（EnvAsset 清单、pin、主机记录）是 S1/S3 的副产品；训练机预检在 S3 之后按需做 | — | — |

S1 的代码部分由我做（你已定）；S1 同时需要 A 对第四组四项与 frozen delta 入口的决定。S2 是文档与决策，不占机器。S3 开始前机器要恢复到可用状态（阶段一已证明 CPU 机够用）。

---

## 5. 现在需要你决定的

1. **接受重构**：S1 → S2 → S3 → S4，取消独立的迁移预检阶段。
2. **P4 原则**（T0）：训练池参考集改为"我们策略下本地重验证"的结果，上游参考集作对照与外部评测坐标；或者保持上游定义、把不一致题隔离。
3. **P1 agent 网络**：默认 deny（现状），是否为文档/包源开白名单作为训练设计选择，可以推迟。
4. **P2 安装网络**：先只做离线 + 预置；是否允许可信 setup 阶段的白名单包源，等 S1 数据。
5. **S1 范围**：3.4 表中哪些进入 S1（我建议：parser/命令分派、预置注入点、shm 旋钮；A 第四组四项由 A 线定；P4 与出网策略留 S2）。

## 6. 本稿没有做的

没有跑实验、没有改代码；外部做法只摘笔记中与流水线结构直接相关的部分，各笔记的证据边界按原稿；R6c 与 miles 两篇只从远端分支读了相关章节，未合入本机。
