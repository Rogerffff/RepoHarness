# 数据扩量：外部任务资产独立核查

依据与整理日期：2026-10-05。作者：Codex 外部来源调查切片。本文是**来源核查与试接建议**，不构成题目准入、训练配方或评分语义的批准。未读 `tmp/数据扩大方案设计_claude.md`。先检索精读索引及 O03、O11、E5 线索，关键事实重新核对作者论文源文件、官方仓库、HF 数据卡/API 与公开评分代码；未运行第三方代码、拉取镜像、启动容器、使用模型或访问远端作业。

## 先决定什么值得试接

**最快扩出小批候选的第一顺位是 SWE-Gym Full 中能复用现有仓库/版本配方的非 Lite 任务；备用试接选 Prime 过滤后的 SWE-rebench V2 Python 子集。** 这不是 Full 质量更高的结论：Full 的一次性评分接入较小，但难题与噪声比例可能更高；V2 的公开预筛选更完整、仓库覆盖更广，但需要新增任务来源和评分适配。应以小批实际产出合格题的成本决定后续份额。

| 顺位与用途 | 当前可确认供给 | 为什么排在这里 | 首个实际障碍 |
| --- | --- | --- | --- |
| 1：最快增量候选 | SWE-Gym Full：2,438 题、11 个 Python 仓库；包含 Lite 的 230 题 | 有题面、修复补丁、测试补丁、版本、F2P/P2P；已有 RH2 SWE 评分经验可复用 | 当前 RH2 来源名是 `swe_gym_lite`，不能将 Full 冒名接入；更复杂的任务还需重新资格化 |
| 2：明确备用来源 | Prime V2：6,272 题，当前统计 16 语言，其中 **Python 1,952** | 已有语义元数据筛选、两轮 gold、no-edit 和失败审计；Python 子集可减少首次适配范围 | `install_config`/parser 与现有 SWE-Gym 评分并不相同；Prime 镜像名也不是 RH2 现有镜像引用 |
| 3：有限扩展，按仓库选 | Prime R2E Verified：4,522 个 train 行，来自上游 4,578 题/10 仓库 | 参考补丁可重建、现有 R2E 通路可用、确有精确 Coder30B 的外部 RL 证据 | Prime 保留 flaky 行，未改题意/测试；RH2 正式装载还固定 48 题、pins 与镜像事实 |
| 4：容量储备/合成任务对照 | SWE-smith-py：50,908 题、131 仓库与镜像 | 一仓一镜像、现有测试和可逆 bug 提供便宜正控，长期供给大 | 有空题面；`patch` 是注入 bug 的方向，不能当普通 gold 正向应用；新初始化与 grader |
| 5：有实物的新来源探针 | MiMo-V2.6-RL-oss/code：2,698 题 | 官方公开小数据文件、镜像映射与镜像、隐藏测试及评分入口 | 无公开 gold 字段的样本；需要 RH2 退出码评分适配及独立正控/语义核查 |
| 6：后续储备 | OpenSWE：作者报告 45,320 环境/12.8k 仓库，筛选后约 9k 环境/13k 轨迹 | 真实 PR、多仓库、Dockerfile/评分脚本开放，作者 SFT 实验支持价值 | HF 文件访问需接受条件；不是无需构建即可直接用的 45k 镜像；部分 gold 要自行恢复 |

表中数量不可相加：它们有子集关系、同仓库重叠或不同任务生成方式，也都不是本项目的 ready 数。以上顺位是**时间优先的工程建议**。若 Full 首个小批仍大量需要逐题语义修订，应立即转备用；不能因为已有接线就无限维护同一来源。

## 逐来源：公开了什么、尚缺什么

### SWE-Gym Full：少一种 grader，不等于少题目审查

**公开事实。** 数据卡列出 2,438 行、11 仓库和 `base_commit/version/patch/test_patch/FAIL_TO_PASS/PASS_TO_PASS`。论文 v2 §SWE-Gym Environment 明确 Lite 是其中的 230 题；它筛去多文件、题意欠明、复杂参考 diff、错误信息断言等实例。Full 不只增加数量，也重新纳入这些成本因素；理论非 Lite 量为 2,208，仍需与本地已见题单按 ID 求差集。官方 README 的 “Lite 234” 与论文/数据不一致，本报告不用这个旧数字。[固定数据卡](https://huggingface.co/datasets/SWE-Gym/SWE-Gym/blob/bb94ed9e39bbeb96a7fcbfb533b80f25a7fd59cb/README.md)、[论文 v2 环境部分](https://arxiv.org/html/2412.21139v2)、[官方环境入口](https://github.com/SWE-Gym/SWE-Gym/blob/b681068ca20628c6987b7416cc4cf03f06b77ba5/README.md#reproducing-results)。

**资产方向。** `patch` 是基于 `base_commit` 的人类修复；`test_patch` 用于评分时加入测试；F2P 是应从失败变通过的键，P2P 是应保持通过的键。镜像使用 `xingyaoww/sweb.eval.x86_64.*`，安装和日志 parser 在作者 SWE-Bench-Fork；论文报告全量镜像合计 6 TB，这是作者发布口径，并非应一次性拉取的目标。

**最少 RH2 工作（设计推断）。** 显式新增 Full 来源身份、把来源与 SWE 评分面绑定、生成固定 taskset/版本配方/镜像 digest 与公开/私有面；能复用已有 grader 的前提是逐题版本与命令确实受当前 vendored specs 支持。对新增版本检查 candidate 身份可编辑/安装/运行必要测试，并按现有预算和网络策略走正式 fresh grader。已有 Lite 的 good/bad 事实应按实例复用，不能按仓库全部继承。

**证据边界。** 原论文训练 Qwen2.5-Coder 系列，采用 OpenHands/MoatlessTools；不是本任务的 Qwen3-Coder-30B + Claude Code 实验。Full 的可用测试数并不能证明题目核心需求都被测试约束。仓内 9 月 SWE CPU 审查已出现“错误候选得 1、gold 引入回归”的实际例子；那批按疑点选题，不能据其比例估算 Full 缺陷率。[本地最近记录](../env_data_eval.md)。

### R2E 与 Prime Verified：通路清洗，不是语义重写

**当前版本。** 上游 Subset 4,578 行；Prime Verified 的 `train=4,522`、`dropped=56`。旧 `...-Validated` URL 本次实际返回相同 revision 和相同数据卡，应视为同一来源的旧名，不能重复计算。Prime 的检验是重建 `parsed_commit_content` 中的修复、运行镜像内 `/testbed/run_tests.sh`、比对 `expected_output_json`；失败行再试十次，只有 **0/10** 才剔除，因此 ≥1/10 通过的 flaky 行还在 train。[上游固定卡](https://huggingface.co/datasets/R2E-Gym/R2E-Gym-Subset/blob/2e8108ff942f24fcb5686badfaf7f9a8808566d5/README.md)、[Prime 固定卡“Changes vs upstream”](https://huggingface.co/datasets/PrimeIntellect/R2E-Gym-Subset-Verified/blob/b91b703c6e6d4000e609b931bafad193d226ebe0/README.md)。

**资产与语义。** 有题面、镜像名、提交内容、期望状态映射；参考解要从提交序列化格式提取源文件差异。`expected_output_json` 并非“所有测试都必须 PASSED”，其中历史失败/错误也是待比对状态，不能私自替换成通用 SWE 全通过评分。官方 Prime taskset 含测试隐藏/恢复、gold 重建和 exact outcome 检验，适合作为运输对账参考；当前 RH2 已有自己的固定材料和批准过的 R2E 语义，不能覆盖回上游。[固定 taskset 源码](https://github.com/PrimeIntellect-ai/research-environments/blob/ff40b61dcf898e1cdba7a617ac158a50466797aa/environments/swe/r2e_gym/r2e_gym/taskset.py)。

**最少 RH2 工作。** 对 upstream/Prime ID 与本地 48 题及修订单求交差集，保留 Prime dropped 原因；扩展正式 loader、pins、镜像事实和来源 provenance，再按仓库成批装载。Prime 未改行内容，故我方已确认的题面泄漏、弱断言、fixtures/编译问题不会因换成其名字消失。

**本地证据仅作反例。** 9 月 R2E 前两批已找到错误/漏修候选得 1、合理修复误拒、同仓别题初态含修复线索等；已修正口径以最新独立复核为准。它足以反驳“同来源天然低成本”，不足以推出所有 4,522 题不值得训练。[R2E 第二批独立复核](../r2e_static_batch2_review_20260925/README.md)。

**当前资料冲突。** 上游固定卡已标 Apache-2.0；Prime 当前卡仍说上游未声明数据许可证。本文保留冲突，不把 Prime 旧说明当成上游现状，也不以项目代码许可证替代逐仓数据来源信息。

### SWE-rebench V2：首选备用，但要从 Python 小片接起

**原始资产。** 原始 V2 32,079 行、20 语言；作者论文描述 3,600+ 仓库。行含真实 issue、合并 PR 描述、正向修复 `patch`、`test_patch`、base、镜像、F2P/P2P、`install_config`（安装命令、测试命令、parser 名称）及质量元数据。当前 HF 卡明确只排除了原 SWE-bench 的仓库，**未全面排除其他 benchmark**；跨来源和本地 held-out 仍要去重。[固定数据卡“Dataset Summary/Structure”](https://huggingface.co/datasets/nebius/SWE-rebench-V2/blob/10483de0f50fe5da545942705a76c6150171af7f/README.md)、[论文 v2](https://arxiv.org/html/2602.23866v2)。

**Prime 实际筛了什么。** 其 6,272 行从原 V2 筛出：要求元数据 `code=A`、intent 完整、无 B 类问题、confidence≥0.95、无外部 URL；剔除 issue/PR 引用、坏语言/镜像/仓库；要求两轮 gold、no-edit 不通过，再根据 GLM-5.2 训练 all-zero 组复查移除 3 行。不是只改名字。数据卡写 17 语言，但本次 datasets-server `partial=false` 全量统计实际 **16 语言/Python 1,952**，应以固定行集重新计数，不沿用旧卡数字。[固定 Prime 卡“Changes vs upstream/Generation”](https://huggingface.co/datasets/PrimeIntellect/SWE-rebench-V2-Filtered-Verified/blob/6a0d56b425a893b018616587cdb71aa499c5fc99/README.md)、[本次统计快照](../../../../../runs/data_expansion_design_codex_20261005/sources_external/PrimeIntellect__SWE-rebench-V2-Filtered-Verified.statistics.json)。

**不能转移的保证。** 作者论文 §Task Analysis 把隐式命名、外部信息和测试耦合列为失败模式，同时指出 P2P 捕捉合法回归不能自动算坏题；质量标签是模型判定，不是人工证明。Prime 的 easy 半批 flaky 清理还包含 infra 非通过，属于偏保守选择；上游坏镜像与 Prime sandbox 转换失败也不是同一错误类型。不能将 6,272/32,079 当成语言或任务固有的可解比例。

**最少 RH2 工作。** 新增来源与专有 grading data，锁住 `install_config`/parser/命令；把 `patch` 保留在私有正控面，测试只在 grader 注入。现 Prime taskset 会恢复测试路径、执行包围标记段、归一化测试名并检查 F2P/P2P，可定点复用逻辑，但不能盲拷其“找不到 parser/parse异常就返回 0”的失败归因。镜像字段被重写为 `prime/primeintellect/...`；若继续 Docker RH2，应回连原始 V2 的同 ID Docker Hub 引用并实际 pin digest，或验证 Prime 镜像的真实可取方式。[固定 Prime taskset](https://github.com/PrimeIntellect-ai/research-environments/blob/ff40b61dcf898e1cdba7a617ac158a50466797aa/environments/swe/swerebench_v2/swerebench_v2/taskset.py#L183-L254)。

**版本区别。** `SWE-rebench-V2-PRs` 是另一个约 126k、以 PR 生成题面的发布，不能加到 V2 的直接候选容量。普通 SWE-rebench、V2、Prime V2、OpenHands trajectories 也不能互相替代证据。

### SWE-smith：参考解反向、题面与环境状态必须分开验

**版本更正。** 论文 v2 的 50,137/128 仓库是历史发表集合；旧 monolith 当前元数据为 59,136 行，卡片已于 2025-12-14 宣告转向按语言维护。当前推荐 Python 集 `SWE-smith-py` 为 50,908 行、131 仓库/镜像。数据统计与 viewer 显示题面长度可为 0，不能把整包当成可直接交给 Claude Code 的任务。本文没有统计所有非空题面数量。[旧集合固定卡](https://huggingface.co/datasets/SWE-bench/SWE-smith/blob/ea6d7173829c7ec8fa16c22055699ff2e9188091/README.md)、[Python 固定卡](https://huggingface.co/datasets/SWE-bench/SWE-smith-py/blob/77cab9055d42ab4a5c25c89a8f937096db13558e/README.md)、[统计快照](../../../../../runs/data_expansion_design_codex_20261005/sources_external/SWE-bench__SWE-smith-py.statistics.json)。

**可取资产与方向。** 每仓镜像、每题 bug 分支、合成题面、F2P/P2P、注入 bug 的 `patch`。官方 `RepoProfile.get_container` 从公共仓库镜像 checkout `instance_id`；官方 gold 评估明确用 `git apply --reverse`。因此有可恢复的正确基态，但数据行的 patch 方向与 SWE-Gym/V2 相反。还必须移除 agent 可访问的干净分支/历史/别题答案，不能把原始多分支镜像原样暴露。[初始化](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/swesmith/profiles/base.py#L493-L523)、[反向 gold](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/swesmith/harness/utils.py#L70-L83)。

**最少 RH2 工作。** 新来源、按 repo profile 构造 actor 初态、反向正控、独立 grader/parser 与测试保护、非空题面筛选。首先只试 Python、少数轻仓库、带可审查题面的任务；同一函数的多种 bug 不能作独立留出，建议按原仓库/基态/生成家族去重并划分。合成扰动、重复定位模式和题面自动生成误差会改变分布。

**训练证据。** 原论文给的是 Qwen2.5-Coder-32B + SWE-agent 的 SFT；官方后来列出 SkyRL 的 GRPO 接线，证明有实现路线，不能写成已经验证本底座、本 harness 的训练收益。[论文 v2 §Experiments](https://arxiv.org/html/2504.21798v2)、[官方 README 训练段](https://github.com/SWE-bench/SWE-smith/blob/9b74ac08118a85c39c356802f7961893af73e07f/README.md#%EF%B8%8F-train-swe-agents)。

### MiMo 公开 code：无 gold 不是不可用，有 verifier 也不是自动可训

**实际可取。** 官方 `XiaomiMiMo/MiMo-V2.6-RL-oss` 的 code 配置有 2,698 行；根目录 `code.parquet` 为 13,314,620 字节，`image-mapping.jsonl` 495,593 字节。下载的映射有 3,764 条，覆盖多个领域，**不是 code 题量**。例如 `format-code-task-001457:latest` 明确映到 `docker.io/xiaomimimo/mimo-v2.6-rl-oss:format-code-task-001457`。只抽查 Docker Hub tag/digest 元数据，未拉取层，也未证明每个 code 镜像可运行。[固定卡](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/blob/639865fd3374018d6cb29b9fb82dd531406fcf5f/README.md)、[官方映射](https://huggingface.co/datasets/XiaomiMiMo/MiMo-V2.6-RL-oss/blob/639865fd3374018d6cb29b9fb82dd531406fcf5f/image-mapping.jsonl)、[三行原始快照](../../../../../runs/data_expansion_design_codex_20261005/sources_external/XiaomiMiMo__MiMo-V2.6-RL-oss.code.rows.json)。

**字段与 grader。** 三行抽样解开 `extra_info.instance_json` 后都有 `cwd/dataset_type/docker_image/instance_id/problem_statement/test_command/test_patch/verifier_timeout_sec`，期限均 1,800 秒；没有 gold/base/repo 标准字段，`reward_model.ground_truth` 为空。这里只能声称抽样与契约缺参考字段，未逐行证明全包永远无法恢复参考解。mimoagent 公开实现按“恢复测试涉及路径→注入 test_patch（含 verifier 脚本）→运行命令，退出 0 得 1”评分。其代码说明历史截断、无遗留答案、工具链 PATH 是镜像构建前提；运行时只有较轻的历史检查，不能将注释当已验证镜像事实。[固定公开实现 module docstring、`_do_calculate_reward`](https://github.com/XiaomiMiMo/mimoagent/blob/467f0a19016f0ac4d63b8d17a1f0da9ba07f232c/src/mimoagent/environments/datasets/opensource_code.py)。

**最少 RH2 工作。** 把嵌套 JSON 和镜像映射正规化，实测初态与 cwd，建立私有 test patch/退出码 grader 及故障分类，走当前正式冻结导出与 fresh grader；不需要把 actor 换成 MiMo agent。mimoagent 的 `cc-agent` 是自写 Claude 工具目录循环，而 `claude-code` 是真实 CLI adapter，二者不可混称。公开 contract 没要求 gold，并不意味着我方现行准入规则已允许无 gold。

**无 gold 路线（建议）。** 若当前标准要求 gold，先保留该要求并由主方案提出显式等价正控：可信历史修复恢复，或独立解题产生候选、由另一审查者确认题意和核心行为、用隐藏测试与额外反例复验。仍须有 noop 负控、错误候选、稳定性和评分保护。若无法在小预算内取得任何可信正控，只保留诊断用途；不是判来源在理论上不可训练。公开 MiMo 模型训练主张也不能分离出这 2,698 题对 Qwen 的因果增益。

### OpenSWE：源码供给强，但当前可访问性与重建成本优先澄清

**作者主张与发布。** 官方 README 报告 45,320 个环境、12.8k 仓库；约 9k 筛选环境和 13k 轨迹是另一漏斗阶段，不是可直接相加的额外任务。`openswe_oss.jsonl` 和 `openswe_other.jsonl` 区分资产授权与发布范围；后者给 Dockerfile/eval script，作者明确建议通过 daVinci-Dev 管线恢复 gold。公开模型训练结果主要来自 Qwen2.5 系列 SFT，并非精确目标模型。[固定 README“Use Released Data/Overview”](https://github.com/GAIR-NLP/OpenSWE/blob/c2294ce55b9eda60078ca6e69123f21705883bd4/README.md#1-use-released-data)。

**本次实际边界。** HF metadata revision `a8db93…` 可读、`gated=auto`，未认证读取 README 文件返回 401；官方页面要求填写姓名/组织并接受条款。未申请或填写身份，也未下载受限数据。故没有声称对其中行、gold 或去重数量做过本地验证。[官方访问说明](https://huggingface.co/datasets/GAIR/OpenSWE)、[metadata 快照](../../../../../runs/data_expansion_design_codex_20261005/sources_external/GAIR__OpenSWE.api.json)。

**最少 RH2 工作。** 先解决已获授权的数据访问与固定行集；再只对一个公开许可、材料齐全的任务构建镜像和 grader，核 gold/base/test 方向及评测入口。大部分资产形式是可重建环境说明，不能与现成可拉取、已过我方双控的镜像等价。现阶段不作为最快备用。

## 额外来源只作储备，不分散首批

- **Prime Scale-SWE-Verified**：17,202/20,181 个 Python 任务，卡片公开删去 892 坏镜像、2,061 gold 失败、15 noop 通过和 11 稳定 infra 失败；有 `f2p_patch/f2p_script`，与现有 grader 仍需适配。体量大但本次没有核完整逐题生成质量，不排到 V2 小片之前。[固定卡](https://huggingface.co/datasets/PrimeIntellect/Scale-SWE-Verified/blob/2c29b67e0ea4d7819f60d8a10d7475a7ad89ccd6/README.md)。
- **Prime SWE-Lego-Real-Data-Verified**：可用 split 名是 `resolved`，4,323/4,432；不是卡片下方原发布 18k 的全量。它也是 0/10 才剔除、保留 flaky。带 OpenHands 成功轨迹和参考资产，适合后续 SFT/解法材料调查；不直接替换真实 Claude Code 的 on-policy 样本。[固定卡](https://huggingface.co/datasets/PrimeIntellect/SWE-Lego-Real-Data-Verified/blob/0a1b227ec41f0e96cb8f5c7a1c225258a80edb8d/README.md)。
- **Nebius OpenHands trajectories**：67,074 条轨迹、32,161 成功轨迹、3,792 已解决问题、1,823 仓库；轨迹数不是独立训练题数。其 30B RFT 底座是 `Qwen3-30B-A3B-Instruct-2507`，Qwen3-Coder-30B 是比较基线，不能误报成精确同底座收益。旧 SWE-rebench 上的这些轨迹也不是 V2。[官方轨迹卡](https://huggingface.co/datasets/nebius/SWE-rebench-openhands-trajectories)、[官方模型卡](https://huggingface.co/nebius/SWE-rebench-openhands-Qwen3-30B-A3B/blob/614d0184b295a9484a72a9d3cf0a2538fe20a46d/README.md)。

## 精确目标模型与真实 Claude Code 的证据

本轮找到的最直接可行性旁证来自 **Uni-Agent 作者官方仓库**，而不是上述数据论文。固定 commit `00b20d72…`（2026-10-01）的 README 分别列出：

| 模型与 actor | 训练来源标签 | 配置 | 作者报告 Base→RL | 可以支持什么 |
| --- | --- | --- | --- | --- |
| Qwen3-Coder-30B-A3B / Claude Code | SWE-reBench | Colocate Async，200 turns，128K | 40.2→46.2 | 精确 Coder 家族沿真实 CLI 训练存在公开正向报告 |
| Qwen3-Coder-30B-A3B / ReAct | SWE-reBench | 同上 | 47.4→54.2 | 另一 harness 的结果，不能当作 Claude Code 行 |
| Qwen3-Coder-30B-A3B / ReAct | R2E-Gym | Fully Async，100 turns，128K | 46.2→52.0 | 相同模型的 R2E 训练旁证，未验证我方 48 题或 Prime 版本 |

[固定 README 第 73–79 行](https://github.com/verl-project/uni-agent/blob/00b20d72d35816a3d66e6137c424a5b60e92d062/README.md#L73-L79)。配套 [RL-training 第 7–14 行](https://github.com/verl-project/uni-agent/blob/00b20d72d35816a3d66e6137c424a5b60e92d062/docs/source/benchmark/rl-training.md#L7-L14) 将模型全名写为 `Qwen3-Coder-30B-A3B-Instruct`，并说 Base/RL 使用各任务的 validation metric；该文档表未列 Claude Code 行。**不要把三行拼成一次实验，也不要擅自补成已核清的相同 SWE-bench Verified 评测协议。** “SWE-reBench”未锁到 V2/Prime 的特定行集，当前证据不能证明选择 Prime V2 会复现 +6。没有在 RH2 重现这些训练。本轮未发现上述来源在 Qwen3.6 上的同条件独立数据贡献证据，3.6 只宜作为另定对照。

## 一个能很快判定去留的备用试接

**对象：Prime V2 的 1,952 个 Python 行。建议首片只取 12 题、至少 4 仓库，优先非空明确题面、标准 Python parser、无巨型编译/外部服务、短测试命令。** 这些是减少首次接线变量的选择，不是全来源代表样本；先按原仓库+base+PR/patch 和已用题、评测集去重，再固定 selection seed/完整候选分母。不得只报告成功的 12 题。

1. 静态阶段只下载元数据和所需小文件：确认来源字段、两类 patch 方向、测试键、parser、真实镜像引用、公开/私有内容及许可证来源记录。实现一个共享的 V2 转换/评分通路，不为每题写临时 grader。
2. 在既有运行授权和预算内，按风险分层核对正式 actor 初态与 fresh grader：逐题具备适用于当前版本的 noop 和可信正控证据，已有证据满足复用条件时直接复用；新环境或评分家族的代表题做重复对照，并用针对核心需求的错误或漏修候选做强反控，再按风险和随机抽查补充检查。保留退出码、解析结果、测试键、安装/测试时间及错误分类；若反控被接纳，不以 gold 通过核销语义缺陷。具体次数与复用条件服从主方案，不要求每题机械双跑或新造反例，本节不叠加额外准入门槛。
3. 只有这个小片产生足够可信任务，再沿真实 Claude Code + RH2 用目标 Qwen 取得行为数据；训练和基座探针批次另按主方案，公开来源的 RL 成绩不代替本批验收。

**可选停查示例（不是既有政策或主方案新增硬门槛）**：可在首片 12 题汇总时，用“少于 8 题能不改题意/测试地具备适用正负控”或“≥3 题需要逐题语义重写”提示是否暂停扩量、先交付归因。8/12 与 3 题仅是控制试接成本的示例，是否采用及实际停止条件服从主方案，不能当作缺陷率统计推断。发现答案/隐藏测试泄漏、不可追溯镜像或 grader 把运行故障当正常零分时，按主方案处理受影响模板。共享适配若超出一次来源/一种 Python 评分类型的小改范围，应报告实际缺口，勿顺带迁移整个运行框架。Full 同样适用有限小片比较，不能让同来源维护无限吞噬扩量预算。

## 两个应明确反驳的强推论

**“同来源天然低成本”不成立。** 接线复用只减少一次性成本；可训题的总成本还包括版本/构建、语义审查、稳定性、去重与真实 actor 适配。Full 正好重新引入 Lite 排除的复杂任务，R2E Prime 则保留 flaky、未改弱断言。应比较“合格独立任务数 / 总人工+CPU+模型时间”，不是下载题数或接口相似度。

**“无 gold 必不可用”也不成立。** RL 的 reward 不必来自参考补丁，MiMo 的公开契约就是可执行测试判分。缺 gold 失去便宜的环境正控和可解性证据，确实可能提高小批成本；但可用独立已审查解、可信历史修复或其他正控补齐。反过来，gold 能得 1 也不能证明测试拒绝了合理的漏修。具体是否容许替代正控仍服从项目当前标准，本文不自行改准入。

## 证据存档与复查边界

结构化索引见 [external_sources.json](external_sources.json)；抓取 URL、文件 SHA-256 和失败记录见 [fetch_manifest.json](../../../../../runs/data_expansion_design_codex_20261005/sources_external/fetch_manifest.json)。小型原件放在 [本地来源原件目录](../../../../../runs/data_expansion_design_codex_20261005/sources_external/)。论文用 read-arxiv-paper 技能抓 TeX，定点读：SWE-Gym v2 环境/统计和训练入口；SWE-rebench V2 v2 安装/元数据/任务诊断；SWE-smith v2 生成/训练与官方 gold 路径。未声称全文复审、独立复现实验或图表视觉验收。当前数据统计服务不接受这里的 pinned revision 参数，快照是检索当日 current 数据的独立观测，生产冻结前仍应对 pinned 行集重算。

本轮本地完成的是资料获取、schema/源码静态核对和小型统计分析；**所有来源本次新增 RH2 已运行数=0、已准入数=0**。本地历史审查只作为已有证据引用，没有回写或替换。
