# SWE-Bench Pro Verified：官方接入核查与全文续读底稿

**状态：论文全文精读未完成。** 本次已读官方研究说明、完整运行指南，以及固定版本的 benchmark 主实现、网络策略和 Docker recipe；论文 PDF/HTML 与完整修订数据均未成功取得。仓库登记的 37 页 v1 PDF 仅保存在另一台机器的未发布缓存中，本会话也无可用原件。因此本文只保存可独立核实的官方材料与代码事实，不用历史摘要、搜索片段或第三方解读补写论文实验、附录和修订案例；不能加入“全文精读完成”数量。

当前材料明确区分 **anti-hacking** 与 **task refinement**：前者改变执行时的信息可达性，后者修订任务内容。最值得进一步核验的是“为什么改这项要求／测试，以及修订是否真的进入评分环境”。当前代码能说明一次评测如何执行，不能单独证明修订依据合理、102 道修改全部落地或论文中的效果已复现。

导航：[来源与范围](#sources) · [官方披露](#official) · [实际执行链](#runtime) · [代码边界](#limits) · [修题依据与项目映射](#project) · [续读位置](#resume)

<a id="sources"></a>
## 1. 来源、版本与实际阅读范围

日期：**2026-09-23**。项目基线：`Rogerffff/RepoHarness@0554dafd633cd982288bd60a54f75da65e5c54d4`，分支 `codex/project-status-20260923`。本文在其基础上独立维护，不包含另一个 MiMo 阅读分支的自动合并，也不改变 A/B 的实现与任务定案。

### 1.1 主论文与配套来源

拟精读主论文为 Pujun Zheng、Zixin Shang、Shufan Jiang、Wenhui Tian、Dongsheng Zhu、Zerun Ma、Dingbo Yuan、Qi Zhang 的 *SWE-Bench Pro Verified: A Reliable Benchmark for Software Engineering Agents*，arXiv `2609.08149`，首次提交日期 2026-09-08。标题、作者和日期可由 [arXiv 索引][P] 以及 [官方研究说明][D1] 交叉定位；**这不表示已获取正文或独立确认后续版本历史**。

本轮所有 AgentCompass 文档和源码固定于：

```text
open-compass/AgentCompass
5a71ecbbe3799b7b2dc07a28e831fd062f5925d5
```

这是本轮实际读取的代码快照，不宣称它等于论文实验所用 revision，也不将“当前实现”反写成“论文使用了”。

| 来源 | 实际阅读状态 | 可以支持什么 |
| --- | --- | --- |
| arXiv 论文索引 | 已取得搜索索引中的摘要与身份；abs/PDF/HTML 正文访问失败 | 身份与研究主题；不能恢复目录、公式、实验或局限 |
| 37 页 v1 PDF | 未取得；37 页来自项目的来源登记，不是本轮数页 | 不能宣称逐页精读、图表或附录已检查 |
| 官方研究说明 D1 | 全文读取 | 两类问题、总体方法与官方入口 |
| 官方运行指南 D2 | 全文读取，包括 MDX 中全部表格和 Tabs 下命令 | 任务数量、分类、运行步骤、参数、错误与指标说明 |
| benchmark 主实现 C1 | 全文件读取；较长输出按范围补读至文件结束 | 任务加载、准备、隔离、工件与评分逻辑 |
| 网络策略 C2、Docker recipe C3 | 全文读取 | 策略声明、实际镜像与路径选择 |
| HF 完整数据卡、JSONL 与 revision | 未成功取得；只看到一个 README 修改讨论片段 | 不作为逐题修改、731 行计数或数据版本核验 |
| 原始 Pro 数据与逐题 scripts | 本轮未逐题取得和比较 | 不支持修订前后 diff、脚本等价或结果重评分 |
| Docker provider、harness 执行器及测试目录 | 未完整审计、未运行 | 不能把策略声明等同真实网络隔离或完整信息不可达保证 |

没有取得原始 PDF，因而没有可用的 PDF 截图对象，也没有做 OCR。失败的来源获取不是“作者未披露”的证据。本文不构造一个推测的论文目录，也不把旧笔记的章节号当成本轮已读覆盖表。

### 1.2 复用的旧稿及边界

复用 [环境专题 §4](../environment_processing_survey_20260915/06_new_quality_sources.md) 和 [原文登记](../environment_processing_survey_20260915/07_source_intake_and_reading_queue.md) **定位续读问题**。旧稿记录了候选筛查、优先修改题面、部分测试修改和三组实验；这些在本轮未回到原文核查，不提升为本稿的已核实论文事实。

同步包说明原始下载缓存没有随文档上传。所需原件原路径为：

```text
docs/harness_improve/external_paper_references/
  environment_processing_survey_20260915/sources/
  swe_bench_pro_verified_2609.08149v1.pdf
```

这是来源定位，不是本分支已经存在的可点击附件。

<a id="official"></a>
## 2. 官方材料明确说了什么

### 2.1 两条不同干预

官方研究说明将问题分为：**reward hacking**，即执行过程中获得泄漏的解法或隐藏评测信息；以及 **task quality issues**，即误导题面或不合适的测试。对应处理为访问防护与定点任务修订。文档说论文评估这些改变并分析轨迹，当前文档本身不包含完整实验表。[D1]

因此，本稿不把以下三件事混成一个结论：模型参数中已有的信息、运行中取得的解法、题目／测试定义的变化。这里只能确认来源明确讨论后两类，不能据此宣称排除了训练污染。

这是一项基准与执行协议研究。已读官方说明没有提供优化模型权重的训练流程；不为套用通用精读模板而补写 SFT、RL、OPD、reward shaping 或训练资源。

### 2.2 数量与分类

运行指南声明共有 **731 个任务**，所有任务采用四类防护；另修订 **102 个确认存在质量问题的任务**。[D2，导言]

| 官方分类原词 | 数量 | 本轮解释边界 |
| --- | ---: | --- |
| misleading descriptions | 22 | 不根据分类名称推定每题缺失了什么 |
| overly narrow tests | 75 | 不擅自合并成“低覆盖”或“只接受 gold”；具体含义待正文案例 |
| overly broad tests | 3 | 不把题面未逐字写出的要求自动归入此类 |
| other issues | 2 | 未取得具体问题明细 |
| 合计 | 102 | 22+75+3+2；官方报告数量，不是本轮重审结果 |

102/731 约为 13.95%，这里只是对报告值的算术换算。它不是本轮随机抽样估计，也不是“其余 629 题已被证明无问题”的概率性结论。未取得完整数据，不声明已经独立检查所有 ID、分类互斥性或修订分布。

### 2.3 不重建模型成绩表

本稿**不转抄第三方文章或前序聊天中的模型分数、下降幅度、通过→失败归因和零误杀说法**。恢复这些结果需要原始表图、样本集合、harness、预算、重复次数以及作者的判定过程。当前官方运行参数是复用指南，不能倒填为论文原始实验设置。

<a id="runtime"></a>
## 3. 固定官方代码的一次实际执行链

主文件是 [C1] `src/agentcompass/benchmarks/swebench_pro_verified/swebench_pro_verified.py`；不要与原始 `swebench_pro` 类或另一个同名 harness 混读。

```text
本地缓存或 HF JSONL
  → TaskSpec（含控制侧完整 metadata）
  → Docker recipe 选镜像和路径
  → 准备基础仓库
  → 隐藏指定测试、重建单提交 Git
  → PreparedTask（限定 metadata + 渲染后的任务说明）
  → harness 修改代码并输出 patch
  → fresh evaluation 环境
  → reset / checkout / apply patch
  → official run_script.sh / parser.py
  → passed-test 集合与 F2P∪P2P 比较
  → correct、status、原始日志与诊断
```

这张图是已读代码与文档的合并说明；本轮没有执行这条路径，也没有核查外层 scheduler 是否在所有异常情况下都遵守 fresh 约定。

### 3.1 数据与镜像不是仅靠一个代码 pin 就冻结

`load_tasks()` 从 `opencompass/SWEBench-Pro-Verified/swebench_pro_verified.jsonl` 取得数据。当前常量 `_VERIFIED_JSONL_REVISION` 为 **`main`**。本地文件已存在时直接使用；不存在时下载。每行显式要求 `instance_id` 和 `problem_statement`，完整 record 留在 task metadata；后续渲染还使用 `requirements` 和 `interface`。[C1，`load_tasks`、`_render_prompt`]

[C3] 的 Docker recipe 从记录中的 `dockerhub_tag` 选择 `jefzda/sweap-images:<tag>`，并将推理和评分路径设为 `/app`。若调用者已显式设置镜像，recipe 不匹配。对 OpenHands 或 ClaudeCode 的 plan，它还设置 `enable_glibc_repair=True`；本轮没有继续核验 glibc 修复内部实现。

每题默认申请 4 CPU、8192 MB，允许配置覆盖。[C1，`_DEFAULT_TASK_RESOURCES`；D2] 这不是本篇所有模型评测实际资源，也不是 RepoHarness 必须使用的容量。

**读者推论：**同一个 AgentCompass commit 可能配合不同本地缓存、HF main、镜像 tag 和脚本 main 运行。复核特定结果时应固定这些实际资产；不能只记录训练／评测框架 commit。这里没有做“资源已经漂移”的测量。

### 3.2 仓库清理具体改变什么

`_prepare_repository()` 区分 `git_clone` 与 `prebaked`，定位 `base_commit`。`_isolate_agent_repository()` 依据 `selected_test_files_to_run` 生成隐藏路径，验证路径为仓库相对路径，拒绝绝对路径和 `..`；随后清理未跟踪文件、删除指定测试文件、移除原始及嵌套 `.git`，重新初始化、加入文件、创建单提交基线，禁用 Git hooks。[C1]

实现还先记录原来被跟踪但匹配 ignore 规则的文件，再重新强制加入，以免一次简单 `git add --all` 改变这类源码的跟踪状态。对隐藏测试所在范围还使用 `git clean -ffdx` 清理未跟踪／ignored 残留。

**边界：**实现删除的是指定文件，而不只是某个断言；可能影响正常开发时可见的测试内容。代码说明“做了什么”，不能单独证明所有实例的正常求解能力完全不受影响。只检查工作仓库中的 `.git` 也不等于检查整个镜像里所有副本、缓存与答案工件。

### 3.3 元数据过滤与网络是两个独立边界

`prepare_evaluation()` 的公开 metadata 白名单为 `instance_id`、`repo`、`base_commit`、`problem_statement`、`requirements`、`interface`，其中 instance ID 被转换为一个确定性的 32-bit hash 名称。prompt 本身组合 problem statement、requirements 与 new interfaces，并附加不通过代码托管／镜像／版本探测取得答案的规则。[C1]

控制侧 `TaskSpec`／`PreparedTask` 仍持有真实 task_id 和 ground_truth。**这本身不证明泄漏**：需要追到实际传给 harness／模型／沙箱的序列化边界。本轮只核了 benchmark 与 recipe，没有宣称这些内部字段全部暴露或全部不可达。

[C2] 声明 `denylist`，列出 GitHub、GitLab、Gitee、Bitbucket、Hugging Face 等具体 host。`load_tasks()` 设置 baseline 网络为 public，run 与 evaluation 使用该 source policy。因此这不是全部断网，也不是只允许经过日期验证的依赖仓库。

运行指南在该文档版本将 Docker 描述为可支持该 blacklist 的公共 provider，Daytona／Modal 不支持同样模式。[D2] 这是固定文档的兼容性说明；本轮没有独立查询全部供应商的新接口，更没有验证 DNS、代理或运行时出口规则。不能把声明的域名表等同于已经证明无绕过。

### 3.4 candidate patch 与 fresh 评分

benchmark 声明 `evaluation_environment_mode='fresh'`。`_extract_patch()` 优先读取约定输出文件 artifact，否则使用 `final_answer`。`_strip_binary_hunks()` 丢弃 `Binary files … differ` 或 `GIT binary patch` 所在 diff section。[C1]

因此送入评分的 patch 在包含二进制段时可能不同于提交工件；实际任务是否允许二进制变更，需要额外核任务定义，不能把该行为默认为任意 SWE 任务都适用。

评分使用控制侧的 `<instance_id>/run_script.sh` 和 `parser.py`；本地缺失则从 `scaleapi/SWE-bench_Pro-os/main/run_scripts` 下载。当前 `_create_entryscript()` 提取 Dockerfile 的 `ENV`，仅取 `before_repo_set_cmd` 的末行，按以下次序生成 shell：切换仓库 → reset/checkout → apply candidate patch → 前置命令 → 运行选定测试 → parser。[C1]

这里没有把 `git apply` 的成功直接定义成任务成功，也没有通过与 reference patch 的文本相似度评分。另一方面，“fresh 容器”不自动排除候选代码对测试流程的影响；当前候选可修改哪些文件、所有 evaluator 控制面是否隔离，需要继续沿真实 task/image/scripts 检查。

### 3.5 resolution、退出码与错误状态

`_evaluate_patch()` 读取 parser 产生的 `output.json`，收集状态为 `PASSED` 的 test name。其判据是：

\[
F2P\cup P2P\subseteq PassedTests.
\]

这是对 **当前代码** 的数学重述，不是声称原论文给了这一编号公式。[C1]

若测试仍在输出但状态不是 PASSED，或者根本未被收集，都不会满足相应必需项；返回结果分别列出 missing F2P 和 missing P2P。`completed=true` 只是完成解析并作出判定，不等于 resolved。

超时、无法解析输出、环境缺失等会记 `completed=false`。外层 `evaluate()` 根据 harness error 和 eval error 区分 run error、eval error 或二者；同时保留 binary `correct`、原始评分数据和日志。[C1]

**复用时要核的边界：**当前成功集合判定不额外要求全部输出测试通过；不在必需集合中的失败是否应该使任务失败，取决于任务的既定评分定义。代码也没有将总 shell returncode=0 作为 resolved 的必要条件，不能只抄一个进程退出码就重现原结果。

<a id="limits"></a>
## 4. 三个需要继续核验的实现问题，不先判为漏洞

### 4.1 修订后的测试怎样进入 fresh 环境？

指南说加载的是完整修订数据。但在本轮读到的 benchmark 与 Docker recipe 中，评分主要依赖数据行的 image tag、base commit、选测列表、F2P/P2P 和原始官方 run_script/parser；没有看到一个通用步骤把 JSONL 中的新版 `test_patch` 再应用到评分仓库。[C1–C3]

**不能据此断言新版测试没生效。** 它可能通过镜像、base commit、脚本或不同字段进入；目前没有 JSONL、镜像和原始实例的对照，无法裁定。这个问题恰好是必须核查修订资产而不是只看方法简介的原因。

续读时，应挑一题确实修改测试的实例，建立原始行／新版行、镜像状态、实际被执行测试和判定集合之间的对应关系。不能只检查新版描述已显示在 prompt，就宣布整项 task refinement 已接通。

### 4.2 前序命令失败是否一定中止？

当前生成的 entryscript 没有显式 `set -e`，最终评分可以在 parser 成功产生 JSON 后走到集合判定；因此不能从代码表面推定 reset、checkout、apply patch 的任一失败都会自动中止。[C1]

这是一项静态边界，不是已复现的 false positive。测试可能正确拒绝未应用补丁，运行环境也可能另有约束。应通过故意无法应用的补丁、完整命令日志和结构化输出检查，区分“正常任务失败”与“执行前提未成立但仍被当作有效评分”。

### 4.3 空参考集与重复测试名的语义

集合包含判据在 F2P/P2P 都为空时为真；将 test name 转为 set 也会合并重复名称。这是数学／代码性质，不证明公开数据存在相应坏记录。[C1]

本轮没有完整 JSONL，故不报告违规题数。应用前需要检查数据保证与 parser 命名语义，而非直接改变上游成功定义。该检查与当前 RepoHarness “P2P 单独为空不自动等于缺少所有回归测试”的边界一致；这里说的是两集合都空或 ID 冲突，不应混淆。

## 5. 运行指南里的预算和指标：不能回填论文实验

以下均来自固定版本 [D2]，只是当前指南：

| 层级 | mini-SWE-agent 示例／说明 | OpenHands 示例／说明 |
| --- | --- | --- |
| 单次仓库命令 | `command_timeout=2400` | `command_timeout=1800`；无变化软限制 600 |
| agent loop | `step_limit=250`、`cost_limit=3.0` | `max_iterations=250` |
| 完整 inference | 文档控制表允许 unset；推荐 CLI 显式设 12000 秒 | 控制表默认 9600 秒；示例可显式设 12000 秒 |
| fresh 评分 | `evaluation_timeout_seconds=3600` | 同左 |
| 模型参数 | 示例 temperature=0、max_tokens=32768、timeout=3600、high effort | 使用 provider 对应参数，含独立 retry 配置 |

推理任务的超时、单个命令的超时、模型请求的超时和评分超时不是同一个限制。`max_tokens` 也不能未经 provider 定义就称为全轨迹 context budget。

指南的 Metric Contract：`k=1` 为 native series；`k>1` 时 `avg` 同时产生 `correct.avg@k` 与 `correct.pass@k`，`pass` 可提前停止而只产生 pass@k。[D2，Outputs] 本轮没有审计聚合器具体公式，不能从这些名称反推论文评测做了几次。

没有运行任何模型、容器、网络或 CPU 单测。本文不提供新 leaderboard、预算报价、模型排名或推断训练收益。

<a id="project"></a>
## 6. 本篇最重要的修题问题：目前哪些能回答，哪些不能

| 用户真正需要的问题 | 本轮证据 | 当前可写结论 |
| --- | --- | --- |
| 是否把题目质量与答案泄漏分开处理？ | 官方研究说明与指南 | 是，两条明确干预；应分别追踪 |
| 为什么某道题修改题面而不改测试？ | 缺正文案例、提示词和逐题修订数据 | 尚不能裁定；不提升旧摘要为原文证据 |
| 专家依据 issue、公开接口、历史行为还是 gold 决定？ | 当前指南没有完整审核规程 | 需主文／附录；不是“作者一定未公开” |
| 是否检查合法替代解、部分修复、回归与稳定性？ | 有“修订102题”的官方汇总；缺对应实验 | 不宣称全部逐题通过这些检查 |
| 修订数据是否真的控制了实际评分？ | 已查 loader/recipe/evaluator，仍缺具体资产 diff | 需要一题测试修改的端到端资产核对 |
| 防护是否损害正常开发能力？ | 有实施办法；无本轮轨迹／实验重审 | 不能宣称零误杀或完整不影响 |
| 防护与修题各自带来多少分数变化？ | 原文表图未取得 | 不引用第三方重建的数值表或因果解释 |

### 6.1 对 RepoHarness 的有限映射

项目现状取自 [9 月 23 日同步入口][S1]，只作为问题背景：Conan 有自然候选的覆盖缺口，Moto5752/mypy11236 有验收范围争议；保留原始分数与争议子集，题目修订和新 reward 均未因本次阅读获批。

**读者分析，而非本文作者已验证的流程：**题面、公共规范、历史行为、测试和 reference patch 应分别记录。发现某个测试拒绝候选之后，先判断它测试的行为是否属于选定任务目标，而不是只检查候选是否像 gold。若目标本身改变，应把它写成新版本的任务定义，不用“澄清”掩盖范围变更。

候选修订可记录一个简短的依据表：

| 项 | 内容 |
| --- | --- |
| 原实例身份 | 原始数据 revision、repo/base commit、原评分定义 |
| 争议行为 | 不是“哪个模型做错”，而是哪个可观察行为存在分歧 |
| 公开依据 | issue、requirements、接口、历史文档或既有测试；相互冲突时保留冲突 |
| 候选变更 | 改题面、改断言、加回归检查或暂不改，各自改变什么 |
| 对照对象 | 原始 noop/gold、自然替代解、部分修复；选择依据与样本量 |
| 验证层次 | 静态判断、CPU/容器检查、solver 重跑分别记录 |

这不是要求每题新增一套强制审批，也不是让论文替 B 裁定已有八题。最小有辨识力的实验，是固定其他条件，只修改有明确依据的一项要求或断言，检查被纠正的误判和可能新引入的误判；同时保留原版结果。

本轮官方代码核查可直接支持两项设计检查：一是版本记录需要包含实际数据／镜像／脚本，而不只是框架 commit；二是内部参考信息与模型可见输入要按真实序列化边界区分。是否采用 AgentCompass、是否变更网络策略或评分控制面，均留给现有 A/B 任务，不在阅读文档中实施。

<a id="resume"></a>
## 7. 取得原件后从这里继续，不重复已完成的源码导读

首先取得 `swe_bench_pro_verified_2609.08149v1.pdf` 或完整 HTML/TeX，核封面、arXiv 版本历史与总页数，按原文目录建立正文／附录覆盖表，再逐页核关键图表。本稿没有预填“第几页已经读完”。

必须完成的主文与附录问题：

1. 作者实际如何定义各类 task quality issue；候选来源、筛查、修法起草和专家决策的真实流程及分母。
2. 修题优先级与最小修改的原则、反例，以及何时改变 problem statement/requirements/interface、何时改变测试或排除任务。
3. 代表实例的原文案例与发布数据逐项对照；尤其包含描述修改、测试修改和边界不确定的情形。
4. Baseline、防护、修订条件是否确为原文实验，以及每组的模型版本、harness、预算、重复次数、样本集合和成本。
5. 所有实验表图、成功→失败／失败→成功归因、正常执行是否受损、LLM 审核的校准和局限。
6. 原文局限与附录提示词／案例全覆盖，不只摘与项目争议相同的部分。
7. 核对数据 revision、原版—新版字段 diff、镜像／测试／parser 的对应；分别标明论文方法、现代代码和本轮实测。

旧环境专题提到的候选数、测试修改题数、封面日期差异及“优先改题面”只作为此清单的检索线索；在原文核查前不进入论文结果摘要。

## 8. 检查与交付状态

本文对应用户批准的第一项阅读任务，但**当前只交付可核实的官方资料／接入核查与续读底稿，不是完整论文精读**。未做独立审查、模型实验、容器验证、JSONL 全量扫描或评分重现。没有改变项目代码、数据、题目或网络设置。

详见 [作者检查与获取记录](reviews/swe_bench_pro_verified_2609.08149_self_check_20260923.md)。完整原文取得后在同一文件续写，保留本次固定代码与获取边界，不必另建一个重复摘要。

## 来源链接

正文中的 D1/D2/C1–C3 指以下固定资料；原论文链接仅作为待核入口。

- **D1**：[官方研究说明][D1]。
- **D2**：[官方运行指南][D2]，含全部参数表、运行 Tabs 和输出字段。
- **C1**：[benchmark 主实现][C1]，正文已经给出对应函数名。
- **C2**：[网络策略][C2]。
- **C3**：[Docker recipe][C3]。
- **P**：[arXiv 论文入口][P]；[v1 PDF][PDF]、[v1 HTML][HTML] 本轮未取得。
- **DS**：[官方修订数据集][DS]，本轮未取得全量数据。
- **S1**：[项目同步入口][S1]。

[P]: https://arxiv.org/abs/2609.08149
[PDF]: https://arxiv.org/pdf/2609.08149v1
[HTML]: https://arxiv.org/html/2609.08149v1
[DS]: https://huggingface.co/datasets/opencompass/SWEBench-Pro-Verified
[D1]: https://github.com/open-compass/AgentCompass/blob/5a71ecbbe3799b7b2dc07a28e831fd062f5925d5/docs/en/research/papers/swebench_pro_verified.mdx
[D2]: https://github.com/open-compass/AgentCompass/blob/5a71ecbbe3799b7b2dc07a28e831fd062f5925d5/docs/en/user_guide/modules/benchmarks/swebench_pro_verified.mdx
[C1]: https://github.com/open-compass/AgentCompass/blob/5a71ecbbe3799b7b2dc07a28e831fd062f5925d5/src/agentcompass/benchmarks/swebench_pro_verified/swebench_pro_verified.py
[C2]: https://github.com/open-compass/AgentCompass/blob/5a71ecbbe3799b7b2dc07a28e831fd062f5925d5/src/agentcompass/benchmarks/swebench_pro_verified/network_policy.py
[C3]: https://github.com/open-compass/AgentCompass/blob/5a71ecbbe3799b7b2dc07a28e831fd062f5925d5/src/agentcompass/recipes/swebench_pro_verified/docker.py
[S1]: https://github.com/Rogerffff/RepoHarness/blob/0554dafd633cd982288bd60a54f75da65e5c54d4/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/external_sync_20260923/README.md
