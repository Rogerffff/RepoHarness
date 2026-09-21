# Terminal、其他环境与执行框架：逐篇环境处理汇总

阅读日期：2026-09-15。除特别标注的 E4、E6、RLVE 外，本章是对**已有精读中环境章节的专题复核**，没有重新完整精读各篇原文，也没有运行环境。运行框架条目记录其固定版本的做法，不把当前代码补成历史论文实验。纯损失、概率一致性和 packing 材料的排除理由见 [检查清单](terminal_inventory.json)。

## 一、环境生产与任务筛选

### E2 · CalibForge：不仅检查能否做对，还利用失败修订题目

- **实际处理：**author 先查工程资料、试依赖和资源，联合生成说明、Dockerfile、初始文件和测试；检查初态全部测试失败，再在独立 sandbox 自解。随后让多个 solver 或强弱 solver 分别求解，读取测试结果与轨迹，修订后重新验证。去污染同时比对评测说明与测试代码。
- **值得看的实例与边界：**全失败可能通过补齐缺失语义修复；强模型失败、弱模型成功的个案则是测试绑定实现布局，作者改成验证安全属性，使合法替代解通过。校准是在**改变任务**，不是证明原题天然无效；同版本重复稳定性与 infra 错误处置未完整披露。
- **定位：**[精读 §4.1–4.4](../reading_notes/E2_calibforge.md)；[原文 §2.2–2.3、附录 B/D](https://arxiv.org/pdf/2608.06352v1)。

### E3 · Envs-FORGE：同步维护说明、环境、解答与测试

- **实际处理：**按 seed 表现选择增难、减难、扩展等合成动作；修改约束时同步 instruction、fixture、oracle、tests 及必要环境。减难可用确定性 fixture 替换 live dependency。先查结构与隔离，再真实构建、执行 oracle 和测试；失败反馈用于修复。训练前以目标 tokenizer、真实 system prompt/chat template 检查长度，并预检代表性容器。
- **边界：**原文未给错误解、合法替代解及波动的完整矩阵。精读核查的公开示例主路径仅静态检查便标 accepted，与论文的真实 oracle 验证并非同一保证，不能把示例导出的模板消息当 rollout。
- **定位：**[精读 §4–5、§10](../reading_notes/E3_envs_forge.md)；[原文 §3.4、A.3–A.4、C](https://arxiv.org/pdf/2608.14312v1)。

### E4 · Endless Terminals：把“初态成立”和“任务完成”分开检查

- **实际处理：**从类别、复杂度和场景三个轴生成任务，并把只供构造和验证的 ground truth 与 agent 可见说明分开。生成容器及初态测试，检查文件、目录、进程或仓库；构建失败最多修订三轮。另生成终态测试，确认初态不能通过；用 o3 求解 16 次，至少成功一次才保留。
- **边界：**过滤掉约半数候选、最终得到 3,255 题，不能据此认定被删题都客观无解。原文也承认规格偏程序题风格，以及 solver 能力对保留分布的限制。
- **定位与本次核查：**[既有摘要](../../../../knowledge/summary_endless_terminals.md)；[本地 PDF](../pdfs/E4_endless_terminals_2601.16443.pdf)。本次读取 v3 §3，并目视 p.4；[官方 v3](https://arxiv.org/pdf/2601.16443v3)。仍待完整精读。

### E8 · ECHO：复用并扩展合成环境，再用强模型筛可解性

- **实际处理：**从 Endless Terminals 与 OpenThoughts 中取筛后的 2,700 题，另用修改版 Endless 管线生成 6,170 题，包含 specification、Dockerfile 验证和 Harbor 导出；要求 GPT-5 至多 16 次尝试中至少一次成功。最终池 8,870 题。Docker/Harbor 承载工具与测试，生成控制由 SkyRL/vLLM 保持；终局单测给二元反馈。
- **边界：**原候选数与逐阶段损耗不齐，不能按加法推出构建率或筛选零淘汰。没有完整公开 empty/gold、合法替代解、测试隔离与波动资格流程；其新损失并不补足这些证明。
- **定位：**[精读 §3、§8](../reading_notes/E8_echo.md)；[原文 §4](https://arxiv.org/pdf/2605.24517v1#page=4)。

### Nemotron-Terminal：有测试的合成任务与无测试的格式适配要分开

- **实际处理：**adapter 将数学、代码、SWE 输入改成终端交付任务，**没有配套测试**。另两条合成路线由 seed 或技能组合生成自包含说明、输入文件和可加权 pytest；使用九个预构建领域镜像，agent 可装额外依赖。作者明确不自动生成 oracle。训练前做与 TB2 的 14-gram 重叠移除及基础过滤。
- **边界：**“No filter”仅指不再追加完成/成功轨迹过滤，不能推成取消环境资格检查。生成用 Harbor/Singularity，评测用 Daytona；作者承认前者存在少量 fakeroot overlay 失败，未给完整故障损耗账。
- **定位：**[精读 §3、§5.2、§7.3](../reading_notes/nemotron_terminal_data_engineering_2602.21193.md)；[原文 §4.1–4.4、§5.1](https://arxiv.org/pdf/2602.21193v1)。

### OpenThoughts-Agent：环境有效性、示范价值与 RL 价值并非同一排序

- **实际处理：**比较 95 种来源/生成策略，转成可执行 agent 任务；在来源混合、说明改写、教师回答长度筛选及轨迹筛选上做对照。RL 另比较八类来源，其中 pymethods2test 把程序题转成单函数 Python contract、docstring 与 unittest。不同来源的实际输出需匹配预期 PASS/FAIL，而非统一要求全部 PASSED。
- **边界：**SFT 优胜来源未必是 RL 优胜来源；回答长也不是测试可信的证明。原文没有为 95 条路线提供统一构建—oracle—质量审查漏斗，不应继承被引用上游的全部资格保证。
- **定位：**[精读 §3、§5.1、§8.2](../reading_notes/task08_openthoughts_agent_2606.24855.md)；[原文 §3–5](https://arxiv.org/pdf/2606.24855v1)。

### Agent Lightning v1.0：静态缺陷过滤、模型校准与答案通道治理

- **实际处理：**从 59,136 条 SWE-Smith 任务中移除空描述、镜像缺问题分支及测试数大于 200 的任务；随后用 Qwen3.5-9B 每题四次校准，去掉 4/4 成功题，保留成败混合题并补入部分 0/4 题。发现 Git 历史、公网和 pip 下载源代码的捷径后，隐藏 `.git`、禁止 Git，并使用 K8s 出网白名单。
- **边界：**测试数量过滤会改变分布，0/4 未被全部淘汰。没有逐层互斥损耗、过滤消融或修补后的完整攻击率；公开配置要求部署方设置网络策略，不是所有启动默认已有隔离。
- **定位：**[精读 §7.1–7.2](../reading_notes/agent_lightning_v1_2608.17528.md)；[原文 §4.3](https://arxiv.org/html/2608.17528v1)；[固定 SWE 文档](https://github.com/microsoft/agent-lightning/blob/218f1f7c0bac0800de4d5a4e5e6f61cf7b5038b4/docs/75-example-coding-agent.md)。

### RLVE：人工设计生成器和验证器，允许多个正确输出

- **实际处理：**人工构造 400 个“输入模板＋问题生成器＋verifier”的程序化环境，按家族设计难度参数；利用解题与验证的不对称，例如先生成完整数独再挖空，按约束验证任何合法补全。训练按各家族表现升高难度，并用完全留出的环境家族测泛化。
- **边界：**作者尝试全自动环境工程后，仍难保证说明无歧义、生成有效且多样、验证器接受多样合法输出，因此选择人工工程。这主要是禁工具的程序化推理任务，不是 SWE 容器配方；难度控制也不是通用题目质量分。
- **定位与本次核查：**[既有摘要](../../../../knowledge/summary_rlve.md)；本次核对[原文 v1 §2–3、§7](https://arxiv.org/html/2511.07317v1)，未完整重读全文。本次补存的 v2（原文缓存未发布：`docs/harness_improve/external_paper_references/environment_processing_survey_20260915/sources/rlve_2511.07317v2.pdf`）留给后续精读，未用其替换本条 v1 证据。

## 二、验证器、任务说明与反馈

### N06 · Hardening Agent Benchmarks：修漏洞还要测试正常解能否保持

- **实际处理：**先由 solver 预检，再循环 hacker 找取巧路径、fixer 改 tests/environment、solver 检查修改后仍能正常解题；角色使用新环境，通用防护通过共享池传播。独立攻击者再评攻击与正常求解表现。
- **关键反例：**单一 reference 没用到的 CUDA 编译路径被防护误伤；共享池还会把过严改动传回已修任务。Terminal 主实验攻击率降低的同时，benign pass 从 76.1% 降至 65.2%。论文原循环接受补丁不单列“原攻击重放必须失败”；当前代码的可选 replay 不能倒填成历史实验必开。
- **定位：**[精读 §3、§5.5、§6、§8](../reading_notes/N06_hardening_agent_benchmarks.md)；[原文 Algorithm 1、§4](https://arxiv.org/pdf/2606.08960v1)。

### E1 · Harness 与后训练：可见信息也是任务条件

- **实际处理：**把 ALFWorld 的文本动作改为结构化工具；分别给不同详细程度的工具描述、当前可用工具名及持有物品信息，并比较训练/测试信息条件和工具 schema 变化。任务按最少子目标数划分难度，使用标准 seen/unseen split。
- **边界：**这是家庭文本环境的控制实验，不是 SWE 清洗线。较丰富说明与状态字段同时改变，不能把收益单归某字段。对我们有用的是把“agent 实际能看到哪些信息、需自己探索什么”纳入验证对象，而非只检查数据行及镜像。
- **定位：**[精读 §3.1–3.3](../reading_notes/E1_harness_interplay_posttraining.md)；[原文 §3、附录 B](https://arxiv.org/pdf/2606.25447v1)。

### N07 · SDPO：公开反馈测试与最终评价的边界必须写清

- **实际处理：**LCBv6 代码实验使用 131 道题，从原 private tests 随机拿一半供训练；执行后提供编译/运行错误、失败输入及预期结果，作为自蒸馏反馈。这里是 LeetCode 风格执行环境，不是开放仓库 agent 任意访问隐藏评分材料。
- **边界：**没有把题目划成训练题和未见题；精读核到当前代码的验证集保留完整测试，含已公开的一半。故它支持研究如何利用反馈，不能据成绩当成未见 SWE 泛化证据，更不能据此把全部 hidden tests 交给训练 agent。
- **定位：**[精读 §6.1、§10.1](../reading_notes/N07_sdpo.md)；[原文 v2 §4](https://arxiv.org/pdf/2601.20802v2#page=9)。

### E6 · Surge 办公任务：按最终状态的多个条件评分

- **实际处理：**用 MCP 暴露文档、表格、日历、浏览器等 27 类专业工作流，403 题分成 363 训练与 40 留出。作者围绕强模型尚不稳定完成的真实任务构造，并监控工具、题型及失败模式的多样性。每题一个确定性 Python grader 检查最终状态；训练给满足条件的比例，严格成功要求全部满足。
- **边界：**没有 SWE 训练题。原文未公开完整初始化/reset、外部服务冻结、重复稳定性和 verifier 修复方法；不能只凭确定性 Python 函数就断言外部服务状态可复现。
- **定位与本次核查：**[既有摘要](../../../../knowledge/summary_surge_office_rl_transfer.md)；[本地 PDF](../pdfs/E6_surge_office_rl_2608.01604.pdf)。本次读取并目视 §5.1–5.2、p.8；[官方 v1](https://arxiv.org/pdf/2608.01604v1)。仍待完整精读。

## 三、环境运行、评分与恢复

### O01 · SkyRL-Agent / SA-SWE：分开初始化、交互与评分容量

- **实际处理：**把 rollout 拆成 Init→Run→Eval，按环境负担选整条限流或分阶段流水线。SWE 复用 R2E-Gym，增加 AST 搜索、查询提示和工具失败/预算提示。研究搜索任务使用网页缓存和摘要，观察到在线检索拿到公开答案后屏蔽部分域名；GUI 示例使用可重置的固定 VM。
- **边界：**SWE 工具改动改变了探索机会，不能与调度加速合算为一项功劳。引用 R2E 并未披露自己的逐题质量漏斗。搜索服务容量不足也曾产生 timeout、污染 rollout；服务故障不能直接解释成模型能力失败。
- **定位：**[精读 §3–4、§7](../reading_notes/O01_skyrl_agent_sa_swe.md)；[原文 §3.2、§4–5](https://arxiv.org/pdf/2511.16108v1)。

### R0 · Polar：阶段池、评分预热与已有镜像的复用

- **实际处理：**gateway 负责 runtime/harness 准备、执行、评分与清理，拆成 INIT/READY/RUNNING/POSTRUN，READY 有界缓冲；需要干净评分环境时，可与 agent 执行重叠预热。支持 Docker 和 rootless Apptainer。SWE-Gym 离线案例从参考镜像生成 SIF，装 Node/harness，在目标 commit fresh checkout 解题，按 F2P/P2P 留轨迹。
- **边界：**超时后保留 partial traces 不等于成功评分或全部进入训练。已有镜像和终局通过筛选不等于它重新审查了题意、替代解和波动；示例网络参数也不是通用隔离保证。
- **定位：**[精读 §3、§7](../reading_notes/R0_polar.md)；[原文 §3.3、§4.2](https://arxiv.org/pdf/2605.24220v1)。

### R11 · RollArt：镜像分发与连接恢复本身会决定供给稳定性

- **实际处理：**拆开 Environment、Reward、ActorGen、ActorTrain；每环境独立推进 reset/step，完成后异步评分。生产中针对并发拉镜像、CPU/磁盘争用和网络抖动，使用内部 registry、分布式负载均衡缓存、持久连接及指数退避，并分别安排环境、评分、推理和训练恢复。
- **边界：**作者报告的 >99.99% 成功率针对 reset，不能写成 SWE 任务成功率或评分正确率；镜像缓存没有证明跨任务状态隔离。对小规模项目最直接的是分别测 reset、step、grade 的失败与长尾，不能预设需要整套异构集群。
- **定位：**[精读 §3、§4、§9.3](../reading_notes/R11_rollart.md)；[原文 v2 §8](https://arxiv.org/pdf/2512.22560v2#page=13)。

### Dressage：真实 Claude Code、fresh grader 与较严格的路径策略

- **实际处理：**SWE-Gym 子集通过官方 TestSpec 转出脚本、parser 和 F2P/P2P；复用原镜像并安装 CLI。运行前清 Git refs/remotes/reflogs 等修复线索，保留 ignored 缓存。捕获 patch 后，在同源镜像的新 sandbox 跑官方评分，finally 清理；用轨迹和路径检查检测上游修复下载及测试/控制文件修改。
- **边界：**检测是事后策略，不是强制断网；禁止配置路径可能与合法任务冲突。部分传输、timeout、marker 缺失也返回零奖励，说明 fresh 环境仍需单独处理评分失败归因，不能照搬所有严格规则。
- **定位：**[精读 §4](../reading_notes/dressage_claude_code_step_balance.md)；[固定实验说明](https://github.com/Accio-Lab/Dressage/blob/3e3142fe8ea07e4504c3b20a936a4c201a3de44c/docs/blackbox-swegym-claude-code-experiment-en.md)。

### Prime stack · R2E 路径：隐藏测试后原环境评分

- **实际处理：**固定版本的 R2E taskset 读镜像、任务说明与 expected map，整理 venv/pycache，将 `/r2e_tests` 打包到 host 并移出 agent 文件系统。执行后先捕获 patch，再把测试放回**原 runtime**执行，解析逐测试状态并精确比对 expected；validate helper 应用 gold 后再评分。
- **边界：**expected 可以包含非 PASSED 状态。隐藏测试和导出 patch 不等于 fresh grader；helper 的存在也不证明所有任务已通过 no-op、波动及替代解检查。HF revision 未在 loader 固定，代码 pin 不能代替任务版本。
- **定位：**[精读 §4](../reading_notes/prime_stack_20260908.md)；[固定 taskset 源码](https://github.com/PrimeIntellect-ai/prime-envs/blob/1f1e050ab0cd273bca39eed5c3e5315e6a8ae9d1/environments/swe/r2e_gym/r2e_gym/taskset.py)。同项目的题集验证见[第一章 Prime 条目](01_swe_tasks_and_quality.md)，此处仅补运行边界，不另算一篇论文。

### AReaL · SWE 示例：外部 agent/environment 才拥有实际评分路径

- **实际处理：**wrapper 调用外部 AEnvironment/AweAgent：创建并检查环境、运行 SWE/CC agent、收 patch、评分、finally 释放。固定配置 `rl_test:true` 选择独立 SWE-bench patch 评测；另有 gold/empty helper。数据 loader 检查 ID/说明，短列表会重复扩展，并不自动完成训练/验证划分。
- **边界：**默认 SWE 示例仍走 v1，不能称已验证的 v2 SWE recipe。helper 存在不等于题目资格已验证；部分环境/评分异常落成 reward=0。最外层采样参数也未必逐字段传到真实 agent，应检查最终请求。
- **定位：**[精读 §3、§10](../reading_notes/areal_v2_services_control_flow.md)；[固定 SWE 入口说明](https://github.com/areal-project/AReaL/blob/f289b989bc5d1930d5c6d592d335e2ffaf8c2f01/examples/swe/README.md)。

### Slime · coding-agent 示例：源环境结束后再评冻结 diff

- **实际处理：**固定版本支持 Claude Code/Codex，依次做可评估性检查、新 sandbox/CLI 安装、workspace 准备、运行、捕获 diff、退出 agent sandbox、独立评分、导出训练段。agent、grader 与外层编排各有预算；CLI 非零退出仍可能对已有 diff 评分，外层编排异常则产生 ABORTED。
- **边界：**这是具体接线与资源生命周期，不是新数据清洗方法。README 的“新评分 sandbox”不能单独支持完全防作弊；精读也未审完所有 provider/评分实现，故只复用已核到的控制流。
- **定位：**[精读 §4](../reading_notes/slime_01_architecture_and_recent_changes.md)；[固定 generate.py](https://github.com/THUDM/slime/blob/4c193f1f37509cca70f0e88807a9305b70f63f4e/examples/coding_agent_rl/generate.py)。

### N11 · Miles Agentic/Harbor 文档：转换任务格式不等于验证任务

- **实际处理：**Harbor 示例按 `instance_id` 找任务目录，每次执行建立 sandbox，模型请求走 Miles session，返回 verifier reward；converter 将原字段放进 metadata。文档规定外部 agent timeout 应小于客户端 timeout，避免客户端先放弃但远端继续占资源；另有 `/flush` 清理 hook。
- **边界：**converter 未进行构建、污染、gold/no-op 或 public/private 划分。缺 reward 在示例中可能默认零，flush 失败只告警；因此调用成功和任务真实失败还须区分。不要把与 Harbor 对接完成写成环境已经合格。
- **定位：**[精读 §4](../reading_notes/N11_miles_agentic_rollout.md)；[固定 SWE 示例](https://github.com/radixark/miles/tree/f2b7c79298a53c53861514d099f7def73bd29f4a/examples/swe-agent-harbor-docker)。

### Miles v0.1 论文：复用官方 terminal 镜像与任务脚本

- **实际处理：**GLM-5.2 案例通过 OpenEnv 为每 episode 创建 Daytona sandbox，复用 Terminal-Bench-2 官方任务镜像和测试脚本 raw score，限制轮数、token 与墙钟，并使用分离的留出任务。系统以 session 亲和路由减少多轮重复 prefill，并把生成放弃、用户过滤和策略过旧分开统计。
- **边界：**本篇没有新任务生产或 verifier 资格流程，也没有披露原始候选—构建—gold/no-op—波动的完整漏斗。它提供执行接入和观测参考，不能由官方镜像或 raw score 推出任务意图与奖励完全一致。
- **定位：**[精读 §3、§9](../reading_notes/miles_v0_1_2609.08368.md)；[原文 §9](https://arxiv.org/pdf/2609.08368v1#page=28)。
