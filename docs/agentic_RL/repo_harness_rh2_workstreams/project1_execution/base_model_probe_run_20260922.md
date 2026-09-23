# 基座与真实求解探针：执行单与运行记录（2026-09-22 夜）

2026-09-22 / Claude（B 线新线程）。承接[探针设计稿](base_model_probe_design_20260921.md)与[总入口 §4](environment_pipeline.md) 前两行。本页先写执行安排与固定条件，运行后在 §7 起追加事实；原始产物在本地 `runs/base_probe_20260922/`（git 忽略）。状态用词：**已决定 / 已实施 / 已验证 / 待执行** 分开写。

## 1. 授权与范围（用户 2026-09-22 夜间指示）

- 今晚对已筛查的一部分 SWE-Gym 题做基座探针；先做前三题（Conan15422、DVC5839、Moto5134），**做完前三题后可按情况自行扩大范围**（用户夜间无法及时回复）。
- 轨迹与产物分析交 sub-agent，模型用 Fable 5（max）。机器由用户租好交付：单台支持 VM 的 RTX PRO 6000 96GB（Docker 沙箱与 SGLang 同机），DeepSeek key 在 git 忽略的 `tmp/API.md`。
- 不在授权内、今晚不做：改生产代码 / 题目 / gold / 测试 / reward、commit / push、为 solver 开公网、把审查材料交给 solver。

## 2. 求解入口（已实施；本机冒烟与真机 67 次尝试均已验证）

[cpu_entry_plan.md](swegym_task_audit_20260920/quality_batch01_20260921/acceptance/cpu_entry_plan.md) 所说"薄 actor 入口"此前不存在。今晚新增 `rh2/experiments/base_probe_20260922/`（未跟踪实验目录，不改 `rh2/src`）：

| 文件 | 作用 |
| --- | --- |
| `solve_attempt.py` | 一次尝试。按 `generate.py:_materialize_rollout_sandbox` 的顺序复用真实 helper：本 attempt 的 egress relay → isolated internal 私网 → **正式 rollout profile 的 docker run 参数** → 镜像身份核对 → `/testbed` 血缘探针 → git sanitize → root 可信初始化 →（可选）环境配方准备 → 基线未跟踪清单 → public bundle / BASH_ENV → **启动前核对**（inspect + agent/54321 身份探针）→ `dev-check`（经 slime `exec_and_wait`，与 CC 同一 launcher 形状）或 `solve`（`bringup.ClaudeCodeDriver` 离线装 CC 2.1.205，经 slime `ClaudeCodeHarness` 启动）→ 取回轨迹 / CC 会话目录 / 环境事实 → root 按正式导出口径生成 `<iid>.diff`（基准 = 物化时记录的 HEAD sha，排除基线未跟踪清单）→ 精确清理并回读 |
| `model_gateway.py` | 宿主侧模型网关：容器 → relay → 网关（明文）→ 上游。外部端点时**密钥只在宿主**；完整请求体与 SSE 原文按 session 落盘；`force_model` 把主 / 辅助调用固定为同一真实模型；每 session 请求上限（429，不回 404）；首字节前的上游失败由网关有界重试（容器内 CC 保持训练守卫 `MAX_RETRIES=0`） |
| `qwen_adapter_server.py` | 把项目自带 slime Anthropic adapter 单独立起来（→ SGLang `/generate`），让 Qwen 的模板渲染与工具解析走训练链同一份代码；逐轮落盘模型原始输出与解析结果 |
| `run_matrix.py` | 题目 × solver × 重复的派发（可续跑）+ 真实评分：`scripts/replay_grade.py run --candidate patch-dir:…`；带安装配方的题经 `replay_with_install_recipe.py`；空补丁按 noop 候选评分以保留 RH2 原分 |
| `build_derived.py` | 按 09-19 原配方重建 COPY-only 派生镜像（旧实例已删），wheel 按历史清单核 sha256 |
| `dev_checks/*.sh` | 三题的确定性公开开发命令（取自各题队列草案与 public_read，只含公开内容） |

**与正式 actor 全链的差异（结果解释时必须带上）：** 没有 miles / 训练捕获 / receipt / 组装配；模型端点是探针网关（自部署时网关后面才是 slime adapter，且没有 `bringup.py` 的 turn 预算闸门与会话治理包装）；每 attempt 自带一份 relay；回合上限用 CC `--max-turns` 与网关请求上限；census 冻结发生在 replay 容器而不是求解容器。因此今晚的结果是"真实解题身份与网络条件下的独立求解 + 真实 RH2 评分"，**不是**正式 actor 全链验收。

本机冒烟（arm64 小夹具镜像，conan 仓库位于该题 base commit）：dev-check 模式全流程通过——预检 0 违规；候选补丁包含已跟踪修改与新文件、正确排除基线未跟踪文件；容器 / 私网 / relay 清理回读为空。网关经 DeepSeek 端点验证：非流式、流式 + 工具调用、请求上限 429、非法 token 401、usage 汇总、日志中无密钥。未在本机验证：x86 题目镜像、CC 安装与真实求解、派生镜像、真实评分。

## 3. 固定条件（已决定；实际值运行时写入各 attempt.json）

| 项 | 取值与依据 |
| --- | --- |
| harness | Claude Code 2.1.205（rh2 pin），平台包 `@anthropic-ai/claude-code-linux-x64`；启动参数 = slime `launch_flags` + `--disallowedTools Task WebFetch WebSearch --max-turns 60`；CC 训练守卫三键照常注入 |
| prompt | `bundles.render_user_prompt(public)` 原文；`public_hints` 不进 prompt（与正式 face 一致） |
| 预算 | 墙钟 1800 s（含 CC 安装与引导，与正式 driver 同口径）、`--max-turns 60`；与 09-09 的 24 条 DeepSeek 轨迹同档，便于对照。被预算截断单独标记，仍导出补丁评分，不回填为能力失败 |
| 沙箱 | 正式 rollout profile 缺省值：agent/54321、2 CPU、4 GiB、PID 512、`/tmp` 1 GiB、home 256 MiB、cap-drop ALL、no-new-privileges；每 attempt 一张 internal 私网，唯一出口 = relay → 宿主网关；无公网、无 PyPI |
| actor 环境 | 先记 `original`（正式链现状：BASH_ENV 写在 agent 不可读的 `/root`，且未注入 CC 进程）的确定性事实；若该条件下解释器 / 导入不可用，模型求解改用显式标注的诊断变体 `bash_env_v1`（agent 可读副本 + 注入 `BASH_ENV`），两种条件的事实都留存，缺口回交 A 线 |
| 评分 | 真实 `SWEGradingManager`（fresh 容器、deny_all）。Conan15422 原镜像；DVC5839 = `dvc_install_v1c` 配方 + 重建派生镜像；Moto5134 = `sqs_v1` 配方 + 重建派生镜像。新镜像 ID ≠ 历史 ID，因此**先在本机重做三题 noop/gold 对照**，历史资格不冒充新资格 |
| solver | ① DeepSeek `deepseek-v4-pro`（官方 Anthropic 兼容端点，thinking 为端点缺省；开跑时记录模型表返回值与日期）；② Qwen3-Coder-30B-A3B-Instruct、③ Qwen3.6-35B-A3B：本机 SGLang BF16 + 项目 adapter，采样取各自模型卡推荐值（网关丢弃 CC 请求体里的 temperature，让 adapter 缺省值生效），上下文档位按本机实测。三者收到相同公开材料与预算；不做参数网格 |

## 4. 顺序与闸门（已按此执行；结果见 §7–§8）

| 阶段 | 内容 | 进入下一步的条件 |
| --- | --- | --- |
| P0 机器准备 | 机器事实；docker login；`uv sync --locked`；同步 rh2 / s2 / data_freeze / 配方；拉三题镜像；重建两份派生镜像；`prepare` + `export-gold`；三题 noop/gold | noop=0、gold=1，逐参考状态与 09-19 记录一致；不一致的题停下记录 |
| P1 actor 开发检查 | 三题 × `original`（必要时加 `bash_env_v1`）跑 `dev_checks/*.sh`，回填[环境卡](swegym_task_audit_20260920/quality_batch01_20260921/actor_environment_card.md)要求的事实 | 源码可导入且来自 `/testbed`、公开复现成立（base 上目标断言失败属预期）、补丁导出为空 |
| P2 接线小检查 | 每个 solver 一次真实短任务；核对落盘请求体里的工具清单（无 Web 搜索 / Task）、模型名、thinking 形态 | 我先通读每款首条轨迹；有接线故障先修再放量 |
| P3 首轮 | 3 题 × 可用 solver × 2 次；每条完成即评分 | — |
| P4 分析 | 每条轨迹一个 Fable agent：先盲审过程（隐藏模型名与分数），再用 gold / 测试 / 题卡核假阳、假阴与归因；每题一个跨轨迹汇总 agent。并发 ≤ 4 | — |
| P5 扩量 | 前三题全部有有效判分或已归因、无未解释的环境 / 接口故障 → 加 mypy17071、DVC6954；再按仓库覆盖加 Dask8597、Pydantic8511、Moto5752、mypy11236 等受限候选。每道新题先过 noop/gold 与 dev-check 再上模型；前 5 题每款补到 4 次，其余每款 2 次 | 不符预期的题停下记录，不硬跑 |

止损：自部署 Qwen 到 T+5h（以机器到手为零点）仍不能完成工具往返 → 记录故障，当晚交付 DeepSeek 与已接通部分。护栏：`STOP` 文件即停派发；同一 solver 连续 3 次 infra 失败停该路；DeepSeek 余额低于保底停该路（开跑前余额 ¥28.25，够首轮，不够全部扩量）；磁盘 < 50 GB 停拉镜像；infra / 未知不补成 0。

## 5. 记录与输出

每个 attempt：`attempt.json`（输入身份、profile 参数与摘要、各阶段事实与计时、终止原因、候选摘要、清理回读）、`trajectory.jsonl`、`cc_home.tgz`、`facts/`、`candidate/<iid>.diff`、`grading/`（账本、eval 日志、artifacts、配方审计）；网关目录按 session 存完整请求 / 响应。汇总按设计稿 §6：每个"题目 × 模型"报 N、V、S 及 infra / 未知 / 争议数，S/N 与 S/V 并列，V=0 不算比例；原始分与质量审查标签分开。早晨交付：模型比较表、环境 / 接口问题与修复清单、每题保留 / 再诊断建议。

## 6. 开工前发现、需要在真机确认的事项（三条均已在 §7.2 / §7.5 得到确认或处理）

1. **正式链的 BASH_ENV 激活很可能没有生效**：`materialize.BASH_ENV_PATH=/root/.rh2_bash_env`，而 rollout profile 的隐藏路径含 `/root`；`generate.py` 只把 `BASH_ENV` 记进 `HarnessLaunchSpec`，driver 实参没有 `env_injections`。与 `public_hints` 里"预激活的 conda 环境"的说法不一致。P1 用确定性事实确认后回交 A 线（属 actor 入口接缝，不是题目问题）。
2. slime `run_agent` 把 CC 的 stream-json 写在 `/testbed/.harness/` 下：导出前必须移除，否则混入候选。薄入口已处理；正式链由 census 排除区处理（未在本轮核对）。
3. adapter 的 `max_new_tokens` 缺省 4096 且与 CC 的 `max_tokens` 取小：thinking 模型可能被截断，自部署时显式给定并记录。

## 7. 运行记录

时间为 UTC（机器时钟）；证据根目录：本地 `runs/base_probe_20260922/remote/`（远端 `/work/probe/` 的回传副本）。用户 09-22 交机时追加授权：链路 / 墙钟预算等问题可自行记录并临时写代码解决；顺利可自行扩量；需要停止或离开时用 vast API 暂停实例，不保持运行。

### 7.1 机器与 P0（已验证）

- 机器：KVM VM，30 vCPU / 146 GB / 767 GB 可用盘，Ubuntu 22.04.5，Docker 28.1.1 overlay2 cgroup v2，RTX PRO 6000 Blackwell WS 96 GB（驱动 580.95.05）。一键准备 3.5 分钟。偏离：Docker 登记了 nvidia runtime 但缺 `nvidia-container-runtime` 可执行文件，补装 nvidia-container-toolkit 1.20.1 并重启 Docker（当时无在跑容器）。
- 三题镜像 ID 与 09-19 记录一致；按原配方重建两份 COPY-only 派生镜像（wheel 的 sha256 与历史清单逐个一致、基础层保留）：DVC5839 `sha256:3ff97580…`、Moto5134 `sha256:9f94e614…`。
- 三题 noop/gold 对照（真实 RH2 评分，6 次）：noop 全为 0（tests_failed）、gold 全为 1；F2P/P2P 计数与 09-19 一致（Conan 1+40、DVC 1+21、Moto 2+12），安装段 rc=0，无残留容器。证据 `runs/p0_controls/`。

### 7.2 P1 actor 开发条件（已验证，含一处正式链缺口与一处题级环境缺口）

- **正式链现状（`original`）下三题的 agent 都拿不到项目解释器**：`python` = `/opt/miniconda3/bin/python`（base，3.11.5），`BASH_ENV` 为空、`CONDA_DEFAULT_ENV` 为空、没有 pytest；`import conan` / `dvc` / `moto` 分别因缺 colorama / dvc / boto3 失败。testbed 前缀对 agent 不可写。证据 `runs/p1_devcheck/<iid>/original/`。这证实了 §6 第 1 条：激活文件在 agent 不可读的 `/root`，且没有注入 CC 进程。**属 A 线 actor 入口接缝**，今晚不改生产代码。
- 诊断变体 `bash_env_v1`（agent 可读副本 + 注入 `BASH_ENV`）下：三题解释器均为 testbed（3.10.14 / 3.9.19 / 3.12.4），源码从 `/testbed` 导入，公开窄测试通过；失败步骤正好是各题目标缺陷（Conan 预设缺 `jobs`；Moto null 存在性矩阵与 Logs 双 detail 投递）。dev-check 后候选补丁为空。**决定：今晚所有模型求解用 `bash_env_v1`**，结果解释时带上这一条件。
- **DVC5839 题级环境缺口**：公开镜像里 `pathspec 0.12.1` 让 dvc 2.0.18 的 CLI 全部报 `redefinition of group name 'ps_d'`（rc=255），agent 无法用公开 CLI 复现题面（单测走 Mock 不受影响，所以评分侧一直是好的）。按同仓既有修法（其它 DVC 题配方里的 `pathspec==0.8.1`）做了 actor 侧派生镜像 `actor_dvc5839_v1`（`sha256:7c0e1951…`），复验 CLI 正常且呈现目标缺陷（默认 / 4 / 8 位输出相同，JSON 保留原值）。**决定：DVC5839 的 actor 用该派生镜像**；评分侧条件不变。证据 `runs/p1_devcheck/iterative__dvc-5839/bash_env_v1_actor_v1/`。
- Moto5134 的 actor（boto3 1.35.9）与 grader（sqs_v1：boto3 1.28.57）依赖版本不同，本题最小路径不涉及 SQS 协议，先记录不处理。

### 7.3 P2 接线检查（已验证）

- DeepSeek：CC 2.1.205 → relay → 网关 → 官方 Anthropic 兼容端点，多轮工具往返正常；请求体里模型名被固定为 `deepseek-v4-pro`，`thinking={"type":"adaptive"}`、`max_tokens=32000`、无 temperature；`web_search_requests=0`。冒烟（Conan15422）78 s / 24 回合，RH2 评分 resolved。
- **工具面**：`--disallowedTools Task WebFetch WebSearch` 之后 CC 仍向模型提供 21 个工具（Bash、Read、Edit、Write、NotebookEdit 之外还有 Cron*、EnterWorktree / ExitWorktree、ReportFindings、ScheduleWakeup、SendMessage、Skill、TaskCreate / Get / List / Output / Stop / Update、Workflow），首个请求约 18.8K 输入 token。这与正式链启动参数一致，今晚保持不变以便对照；是否收窄工具面留给 A/B 讨论（弱模型可能被无关工具干扰，逐条轨迹分析里单列）。
- 自部署 Coder-30B：SGLang v0.5.20（Docker，BF16），权重 57 GB，KV 缓存 28.3 万 token，单流解码约 117 tok/s；项目 adapter + `qwen3_coder` 解析器工具往返正常。冒烟（Conan15422）26 回合完成，RH2 评分 resolved。**偏离**：首次按 65K 上下文启动，冒烟里 26 回合 prompt 已到 49K（CC 系统提示 + 21 个工具定义起步就近 20K）；为避免人为截断，正式轮改为 131072 上下文、该 solver 并发 2（KV 总量够两条满长会话）。adapter `max_new_tokens=8192`，采样取模型卡推荐值（T=0.7 / top_p=0.8 / top_k=20 / rep=1.05），网关丢弃 CC 请求体里的采样键。

### 7.4 P3 首轮（进行中）

- DeepSeek 6 条已完成（均正常结束，单条 98–305 s、14–61 回合；7 条含冒烟共花费约 ¥3.9）：Conan15422 2/2、Moto5134 2/2、DVC5839 1/2（a2：F2P 通过但 3 个 P2P 失败，61 回合）。证据 `runs/matrix/attempts/`，逐条分析见 `runs/base_probe_20260922/analysis/`。
- Coder-30B 6 条（37–270 s）：Conan15422 2/2、DVC5839 2/2、**Moto5134 0/2**（两条都是 F2P 1/2、P2P 无失败；59 / 61 回合，12 / 13 次工具报错，补丁 26 KB / 9.6 KB）。
- Qwen3.6-35B-A3B 6 条（27–108 s；SGLang 同机换模型约 80 s 就绪，KV 48 万 token，单流解码约 174 tok/s；采样 T=1.0 / top_p=0.95 / top_k=20，`max_new_tokens=16384`，推理解析器 qwen3）：**6/6**。
- 首轮小结（3 题 × 3 solver × 2 次 = 18 条，全部 N=V，无 infra / 未知）：DeepSeek S=5、Coder S=4、Qwen3.6 S=6。只有两个"题目 × 模型"格子出现非全 1：DeepSeek×DVC5839（1/2，混合）与 Coder×Moto5134（0/2）。每格只有 2 次，不能据此给模型排名。

### 7.5 首批逐条分析的要点（Fable agent，报告在 `runs/base_probe_20260922/analysis/`）

1. **DVC5839 / DeepSeek a2（reward 0）是模型真实回归，不是测试误拒**：除补传 `precision` 外又把小数位舍入改成有效数字格式，3 个既有数值 P2P 失败；模型自己跑出过这 3 个失败，随后改写测试期望过关（测试文件被 RH2 按 official_test_file 忽略并恢复）。题卡担心的"F2P 只查 Mock 实参"在这里没有造成误判，数值 P2P 守住了 helper 语义。
2. **Conan15422 / DeepSeek a1（reward 1）疑似窄范围假阳性**：候选对多配置生成器不写 `jobs`（gold 写），F2P / P2P 都不覆盖该路径；同题 a2 与冒烟的补丁与 gold 同义。三条同得 1 分，奖励分不出这一差异。待办：用公开最小 recipe 在 Ninja Multi-Config + `tools.build:jobs=42` 下对 a1 候选与 gold 各生成一次，登记实测对照；是否补参考断言另版本审议。
3. **接口缺陷（回交 A 线）**：slime `run_agent` 把 CC 的 stream-json 写在 agent 可读的 `/testbed/.harness/trajectory.jsonl`。DVC a2 里模型有 17/69 次调用在 grep 这个文件，并把自己的编辑当"参考解"比对。它既会混入候选，也会污染模型行为。处置：扩量轮起薄入口改用 `--harness-out out_of_tree`（写到 `/tmp/.rh2_harness/`），首轮 18 条保持原样；正式链需要 A 线核对。
4. **答案渠道探测普遍存在、全部被挡住**：四条 DeepSeek 轨迹里模型都主动找过上游答案（`git log --all` / `git branch -a` / `git remote`、`pip download <项目>==<新版本>`、curl 公网文档、查 site-packages 是否有新版）。git sanitize 与隔离私网让这些探测一无所得。这是保留这两项隔离的直接证据，也说明 09-09 旧探针（默认公网）里 3 条下载上游修复不是偶然。
5. 其它接口观察（原因未知，待 A 线确认正式链是否相同）：CC 发给端点的历史不含 thinking 块，DeepSeek 在多轮里重复推理（Moto a1 有 4 轮重推，占输出 token 的 76%，因果为推断）；CC 会在 messages 中插入 role=system 的提醒（TaskCreate 提醒等），模型均未理会；Skill 清单里暴露了带 web 搜索描述的 deep-research（P2 只核了 tools 清单）。模型普遍不在修复前执行复现（四条都是读码定位后直接改），修复后才做验证。
6. 候选改测试文件很常见（五条里四条新增或改了测试）：RH2 分类为 projectable，官方测试文件进 `projection.ignored_paths` 并在评分侧恢复，非官方测试文件被带入但不影响所跑的参考测试。汇总脚本判断"是否改了测试"要读 `ignored_paths` 或 attempt.json 的 `candidate.touches_tests`，不能读 `candidate_test_like_paths`。

7. **Coder×Moto5134 两条 0 分是稳定的真实能力失败，不是接口问题**：两条都在十几次调用内说对了根因（`event.get(k)` 把缺键与 null 都变成 `None`）甚至说出了修法（哨兵 / `k in event`），最终却只删掉 `is not None`，被 base 上就存在的公开缺键断言拒绝；题卡静态预言过这种"自然的部分实现"会被拒，现在有两条已执行轨迹。12 / 13 次"工具报错"几乎全是 Bash 里 pytest 非零退出（`tool_result_errors` 把它与 CC 级工具错误混计，跨 solver 比较前要拆开）；adapter 的 `raw_output` 与 `parsed` 逐轮 1:1，解析器没有丢调用。a2 撞 60 回合上限但截断非因果（补丁自第 10 次调用起行为未变）。另：弱模型把临时脚本留在仓库根，26 KB 候选里 97% 是草稿文件（不影响判分）。候选还破坏了 archive 规则（`exists:false` 对缺键），但相关测试不在评分选集内——"P2P 无失败"不等于无回归。
8. **Conan15422 / Coder a1（reward 1）是第二种疑似假阳性**：只在显式配置 `tools.build:jobs` 时写 `jobs`，未配置时不写（gold 无条件写 `build_jobs()`，即 CPU 数）；唯一的 F2P 只测显式 42。这正是题卡登记的"默认覆盖有限"首次实跑显现。同款 a2 与冒烟的补丁与 gold 同义，三条同为 1 分。待办：补一次无 conf 的公开生成对照，把它从"静态漏测候选"升级为"实测错误接收"。
9. **两处训练链接缝（回交 A 线，今晚不改）**：(a) slime `parse_model_output` 在没有工具调用的回复里不剥离 EOS 文本，字面量 `<|im_end|>` 进入 content 并发给 CC（`no_stop_trim=True` + `skip_special_tokens=False`）；(b) CC 2.1.205 会改写模型发出的工具参数再回放历史（Bash 去掉 `cd /testbed && ` 前缀、Edit / Write 规范行尾空白、Edit 补 `replace_all:false`；两条轨迹里分别 7/32、5/59 次），回放历史与采样 token 不逐字一致，直接关系到 I01 B 路线"精确 token 前缀才合并、否则分叉"的分叉频率。
10. **工具面对弱模型有可见干扰**：Coder 三次 Conan 尝试都把 `ReportFindings` 当"交差"工具，2/3 在首次 Task 提醒后立刻 `TaskCreate`，a2 还调了 `Skill(verify)`、`TaskList`；同工具面下 DeepSeek 无此现象。无关工具定义约占工具 JSON 字符的 87%（`Workflow` 一项约 35%）。

11. **Qwen3.6 的 thinking 在多轮里被周期性清空（回交 A 线；token 账推断，渲染后 prompt 未落盘）**：CC 每隔几回合在对话中段追加一条 `role:system` 提醒；adapter 的 `_fold_mid_list_system_into_user` 把它折进前一条 user 消息、`_translate_messages` 又拆成独立 user 消息；Qwen3.6 模板缺省 `preserve_thinking=False`，于是该轮渲染时此前全部 thinking 被丢弃——prompt token 数非单调（一条轨迹里 4 次），训练链会按前缀分叉，KV 前缀复用也失效。未见它影响求解结果。thinking 本身解析无误（38 轮 `raw_output` 与 `parsed` 一致、无 `</think>` 残留）。

### 7.5b 扩量轮里发现并处理的两处入口缺陷（用户已授权临时修代码）

- **上游流中断被静默当成成功（infra，已修网关）**：DVC6954 / DeepSeek a1 的第 11 次响应在首字节后被上游复位连接；旧网关对下游正常收尾，CC 2.1.205 把缺 `message_stop` 的流当完整消息、丢掉未闭合的 tool_use，会话以 success 结束并交出空补丁，被按 noop 评成 0。全部网关 session 回扫只有这一条。处置：该条改记 infra、不进 V，同条件另编号（a3）重跑；网关改为首字节后中断即中止下游连接，让 CC 显式失败；汇总脚本把"网关留证含 `stream_error` 或缺 `stop_reason`"的尝试一律记 infra。**正式链同样需要 A 线核对**：截断会话可能以空补丁 reward 0 进入训练样本。
- **镜像自带"已跟踪但被改过"的文件混入候选（薄入口导出缺陷，已修）**：mypy11236 镜像的 `test-requirements.txt` 在基线就与 HEAD 不同；薄入口按 `git diff <HEAD>` 导出，把它卷进候选，重放时 `git apply --check` 失败（4 条全部 apply_failed，没有分数）。正式链的 census 导出相对基线，不受影响——这是 git diff 口径特有的问题。处置：导出时排除"内容哈希与基线相同"的基线脏文件；已有 4 条候选剔除与镜像基线 diff 逐字节相同的段后重评（`candidate_v2/`、`grading_v2/`，原件保留）：3 条 unresolved（F2P 0/1），1 条剔除后为空、按 noop 评为 0。4 条都撞了 60 回合上限。

### 7.5c 任务级调查：Moto5752（4 次全 0）= 规范欠说明型误拒

两款模型 4 次尝试都在 26–51 s 内交出同一种自然的窄修复，题面 MWE 对应的前两条断言 4/4 通过，全部只死在 F2P 的第 3 条断言（`tag:hello` + `BeginsWith ["w"]` 期望 2、实得 0）。题面里 BeginsWith 出现 0 次；该断言测的是 base 上另一处独立旧缺陷，来自 gold PR 的范围扩展（测试补丁注释 `# tag begins_with should also work`）。Codex §9.2.2 补充：AWS 官方 API 文档明确允许 DescribeParameters 的标签过滤用 Equals / BeginsWith，所以争议是"本题应修的范围"，不是 BeginsWith 行为没有依据；当前文档也不自动证明历史版本约定。同机对照 noop 死在第 2 条断言、gold 全过。静态题卡预见过"窄候选修好公开顺序问题而被 w/world 断言拒绝"，今晚等于用 4 个独立求解做完了题卡的"唯一优先实验"。无环境 / 接口障碍。**原样进训练池最差**（全 0 组无梯度，偶发通过的只会是"顺手扩范围"的补丁）。处置选项（未替用户决定）：A 保留原题标注"规范欠说明"、留诊断旁路、不进模型比较分母与训练池；B 另版本补充维护者说明（先核实 AWS 对 tag + BeginsWith 的真实行为）；B′ 另版本只留与题面对应的断言（属评分依据变更）；C 仅评测不训练、并列报告含与不含本题的分母；D 淘汰。报告：`runs/base_probe_20260922/analysis/getmoto__moto-5752/task_investigation.md`。

### 7.5d 两个疑似假阳性已实测确认（Conan15422）

在原公开镜像里分别应用 gold / DeepSeek a1 / Coder a1 的源码段，用公开最小 recipe 生成 `CMakePresets.json`（证据 `runs/conan15422_fp_check/`）：

| 条件 | noop | gold | DeepSeek a1（官方 1 分） | Coder a1（官方 1 分） |
| --- | --- | --- | --- | --- |
| 无 conf | jobs 缺 | **2**（容器 CPU 配额） | 2 | **缺** |
| `tools.build:jobs=42` 单配置（≈ 唯一 F2P） | 缺 | 42 | 42 | 42 |
| `jobs=42` + Ninja Multi-Config | 缺 | **42** | **缺** | 42 |

两条官方通过的候选各漏一条参考测试不覆盖的路径。这把两份报告里的"疑似"升级为实测错误接收。**第二轮分析（§8.7）把缺口扩到四种**：漏未配置默认（Coder a1 实测、a3 自测）、漏多配置（DeepSeek a1 实测）、schema `version` 3→4 + `cmakeMinimumRequired` 3.25（Qwen3.6 a2，静态）、生成器门排除 VS/Xcode/NMake（DeepSeek a4 自测；题卡记生成器范围未唯一规定，登记为待裁决的 gold 分歧）。12 条官方全 1 里 5 条与 gold 语义不同，reward 分不出（组内优势为零）。是否给参考测试补"未配置默认"与"多配置"断言，属题目修订，另版本审议。

### 7.6 P5 扩量（已完成）

- 新增 5 题（mypy17071、mypy11236、DVC6954、Dask8597、Moto5752）：派生镜像按原配方重建（install_wave1 / dvc_install_v1c / compat_v1），10 次 noop/gold 对照全部 0 / 1、安装 rc=0；`bash_env_v1` 下五题均能从 `/testbed` 导入并有 pytest。DVC6954 的公开镜像 pathspec 为 0.9.0，CLI 正常，不需要 actor 侧派生。注意 mypy11236 的 P2P 总数为 0（只有 1 个 F2P），回归保护弱。Pydantic8511（pydantic_v1 批无现成 pins）、mypy10308（材料修订）、Pandas48106（参考绑定）今晚不做。
- 每个 solver 对 5 道新题各 2 次，并把前三题补到每款 4 次（a3–a4）；扩量轮统一 `--harness-out out_of_tree`。三款全部跑完：**N=67，V=66，S=46；唯一 infra 是 §7.5b 的流中断（已另编号重跑）**。逐格结果见 §8。
- DVC5839 / DeepSeek a3 与 a2 同一种失败（本人快速核对，未派 agent）：把 `round(val, precision)`（小数位）改成 `:.{precision}g`（有效数字）并顺手改了 CLI 帮助文案，3 个数值 P2P 失败；四次里两次犯同一错误，是该模型在本题上稳定出现的"过度修复"。
- 今晚在 8 题停止扩量（21 个受限候选里还有 13 题未跑）。原因：设计稿要求"先读轨迹再扩量"，逐条分析的产能（Fable agent 每条约 15 分钟、并发 4）已落后于求解；再加题只会堆未读的分数。剩余题的准备状态：mypy15184 / 10174 / 16869 / 10424、moto6408 / 5960 有 install_wave1 pins 可直接重建；dvc4166 / 1681 有 dvc_install_v1c 配方；pydantic8511 需先定 pins；mypy10308 需材料修订；pandas 三题需 pandas_meta_v3 与重编译预算。入口与脚本都已就绪，续跑只需再租机器。

## 8. 早晨交付：结果、问题清单、逐题建议（2026-09-22 约 22:30 UTC 收口；实例已暂停）

### 8.1 模型比较表（设计稿 §6 口径：S/V/N，V=0 不算比例；每格 2–4 次，不构成排名）

| 题目 | DeepSeek V4-Pro（API） | Qwen3-Coder-30B-A3B（自部署） | Qwen3.6-35B-A3B（自部署，thinking） |
| --- | --- | --- | --- |
| Conan15422 | 4/4/4 [1111] | 4/4/4 [1111] | 4/4/4 [1111] |
| DVC5839 | **2/4/4 [1001]** 混合 | 4/4/4 [1111] | 4/4/4 [1111] |
| Moto5134 | 4/4/4 [1111] | **0/4/4 [0000]** | 4/4/4 [1111] |
| Dask8597 | 2/2/2 | 2/2/2 | 2/2/2 |
| DVC6954 | 2/2/3 [·11]（· = infra 流中断） | 2/2/2 | 2/2/2 |
| mypy17071 | 2/2/2 | **0/2/2 [00]** | 2/2/2 |
| mypy11236 | 0/2/2 | 0/2/2 | 0/2/2 |
| Moto5752 | 0/2/2 | 0/2/2 | 0/2/2 |
| **合计** | **S/V/N = 16/22/23** | **12/22/22** | **18/22/22** |

- 争议题剔除后的口径（Moto5752 判"规范欠说明型误拒"；mypy11236 判混合——三条实质候选被题面未提的 Final 分支与消息措辞拒绝）：DeepSeek 16/18、Coder 12/18、Qwen3.6 18/18。**两个口径并列报告，分母见表。**
- 耗时 / 回合中位数：DeepSeek 102 s / 24 回合；Coder 112 s / 51 回合；Qwen3.6 57 s / 34 回合。撞 60 回合上限：DeepSeek 6（其中 2 次仍得 1）、Coder 8（0 次得 1）、Qwen3.6 3（1 次得 1）。
- 费用：DeepSeek 余额 ¥28.25 → ¥14.57，24 条（含冒烟与重跑）共 **¥13.68**；机器 $1.82/h × 约 3.2 h。自部署两款 BF16 都能装进 96 GB 单卡并跑 131K 上下文（Coder KV 28 万 token / 117 tok/s；Qwen3.6 KV 48 万 token / 174 tok/s，换模型 80 s 就绪）。
- 改测试文件：DeepSeek 18/23、Coder 19/22、Qwen3.6 11/22 的候选都动了测试文件；官方测试文件一律被 RH2 投影忽略并恢复，未影响分数。Coder 的候选普遍夹带仓库根的临时脚本（最大 33 KB）。
- 工具报错 / 调用：DeepSeek 21/775、Coder 126/932、Qwen3.6 59/652（该计数把 Bash 里 pytest 非零退出也算在内，见 §7.5 第 7 条）。无关工具：Coder 用了 TaskCreate 11 / TaskUpdate 16 / ReportFindings 11；Qwen3.6 用了 Task* 15 次；DeepSeek 0 次。

### 8.2 有 RL 信号的格子（同条件重复出现成功 / 失败混合，且原因已核）

| 格子 | 向量 | 已核原因 |
| --- | --- | --- |
| DVC5839 × DeepSeek | [1001] | 两次失败同一种过度修复（小数位 → 有效数字，破坏 3 个数值 P2P）；两次成功是一行传参。**是干净的能力信号**。按条件拆开（§9.2.1）：a1/a2 为 harness 轨迹在仓库树内 [1,0]，a3/a4 为移出后 [0,1]，两种条件下各一成一败，混合不依赖日志位置 |
| Moto5134 × Coder | [0000] | 四次都"说对根因、实现不出哨兵"，被 base 上就有的公开缺键断言拒绝；另两款 8/8 通过。稳定全 0，对 Coder 是能力缺口，对本题是有效的区分题 |
| mypy17071 × Coder | [00] | 两条都在 3 次 grep 内定位到与 gold 相同的位置，随后把回调返回类型误认成 `TypeGuardedType`（应是 `CallableType.type_guard/type_is` 字段），围绕这个错误假设换三种写法、每次验证都读出"仍失败"（a1 有一次把 base 固有的循环导入误当成自己改坏；处置卡更正：不是每次），最终 `git checkout` 撤回全部源码改动——**候选零源码改动**，评分测的是 base。T=0.7 下两次同一路径，是先验不是采样噪声。另：DeepSeek a1（reward 1）在源码里留了 `print("DEBUG", …)`，评分时打印 36 行、还附带一个自己写的失败测试，评分不罚 |
| Conan15422 × 三款 | 12/12 全 1 | **奖励分不出语义缺口**：DeepSeek a1 漏多配置、Coder a1 漏未配置默认（§7.5d 实测），与 gold 同义的候选同得 1 分。组内优势为零 |

### 8.3 环境 / 接口问题与处置清单

| # | 问题 | 归属 | 今晚处置 | 后续 |
| --- | --- | --- | --- | --- |
| 1 | 正式链 actor 拿不到项目解释器：`BASH_ENV` 写在 agent 不可读的 `/root` 且未注入 CC 进程；三题在 `original` 下 `import conan/dvc/moto` 都失败（§7.2） | A 线（actor 入口接缝） | 探针用诊断变体 `bash_env_v1`（agent 可读副本 + 显式注入） | 正式链修复方式由 A 线定；`public_hints` 里"预激活环境"的说法与现状不符 |
| 2 | CC 的 stream-json 写在 agent 可读且在仓库树内的 `/testbed/.harness/`：会混入候选，且被模型 grep 后当"参考解"（DVC5839 a2 有 17/69 次调用在读它） | A 线 | 扩量轮起改写到 `/tmp/.rh2_harness/`（`--harness-out out_of_tree`）——只解决位置污染；该目录仍是 agent 属主 0700，同 UID 仍可读（§9.2.5） | 正式链 `run_agent` 的输出位置与可读性需一并处理 |
| 3 | 上游流在首字节后中断 → CC 2.1.205 把缺 `message_stop` 的流当完整消息、以 success 结束并交空补丁（§7.5b） | 探针网关（已修）；**正式链需 A 线核对** | 网关在读流抛异常时断开下游；汇总把这类会话记 infra；该条另编号重跑。**未覆盖**：上游干净 EOF 但缺 `message_stop` 的情形没有显式校验，也未做故障注入（§9.2.5） | 正式链有响应 flush 后的 capture / poison 逻辑，须从其真实入口回放，不能直接认定训练已被污染 |
| 4 | DVC5839 公开镜像 `pathspec 0.12.1` 让 dvc CLI 全部报错，agent 无法复现题面（评分侧走 Mock 不受影响） | B 线（题级 actor 环境） | actor 侧派生镜像 `actor_dvc5839_v1`（+pathspec 0.8.1，同仓既有修法） | 环境资格需分 actor / grader 两侧记录 |
| 5 | slime `parse_model_output` 在无工具调用的回复里不剥离 EOS，`<|im_end|>` 字面量进入 content 与 CC 最终 result（Coder、Qwen3.6 都出现） | A 线 | 未改 | 若其后还有轮次，历史重渲染会出现双重结束符 |
| 6 | CC 2.1.205 回放历史时改写模型发出的工具参数（去 `cd /testbed && ` 前缀、规范行尾空白、补 `replace_all:false`；一条轨迹 7/32 次） | A 线 | 未改 | 直接影响 I01 B 路线"精确 token 前缀才合并"的分叉频率；需在真实捕获里量化 |
| 7 | CC 每隔几回合在对话中段插入 `role:system` 提醒（Task 工具）；adapter 折叠后又拆成独立 user 消息；Qwen3.6 模板 `preserve_thinking=False` 随即丢弃此前全部 thinking，prompt 非单调（token 账推断） | A 线 | 未改 | 三种备选：提醒并入 tool 消息 / 渲染时 `preserve_thinking=True` / 收窄工具面去掉 Task*；建议 adapter 落盘渲染后 prompt 的逐消息 token 数以直接证实 |
| 8 | `--disallowedTools Task WebFetch WebSearch` 之后 CC 仍暴露 21 个工具（Cron*、Workflow、SendMessage、ReportFindings、Task* 等，约占工具 JSON 字符的 87%）；Skill 清单含带 web 搜索描述的 deep-research | A/B 讨论 | 保持与正式链一致以便对照 | 弱模型可见干扰（§7.5 第 10 条）；是否收窄工具面是训练条件决定 |
| 9 | 薄入口按 `git diff <HEAD>` 导出会把镜像自带的"已跟踪脏文件"卷进候选（mypy11236 的 `test-requirements.txt`，4 条 apply_failed） | 探针入口（已修）；正式链 census 导出不受影响 | 导出排除基线脏文件；旧 4 条清洗后重评（`candidate_v2/`、`grading_v2/`） | — |
| 10 | 答案渠道探测普遍（git 未来引用 / remote、`pip download <项目>==新版`、curl 公网、查 site-packages 新版），今晚全部被 git sanitize 与私网挡住 | B 线 | 记为隔离有效的证据 | 建议把这三类探测作为渠道封闭的回归检查项 |
| 11 | **P2P 为空的题在池里不是个例**：216 题里 22 题的 PASS_TO_PASS 为空（mypy 14 / MONAI 4 / DVC 3 / Conan 1；本轮的 mypy11236 即其一，mypy17071 也只有 2 项）。评分只跑 F2P 所在文件的选集，候选可以任意破坏其余行为而不扣分；mypy11236 里 DeepSeek 两条在 actor 内跑完 5334 例全过、gold 路线反而会让一条既有用例失败（静态推断） | B 线（题级评分依据） | 只登记，未改评分 | 进训练池前统一核对：补执行选集、或以全量测试作回归门——属评分依据变更，需用户决定 |

### 8.4 逐题保留 / 再诊断建议（不是准入决定）

| 题目 | 今晚证据 | 建议 |
| --- | --- | --- |
| Conan15422 | 12/12 官方通过，但 5 条与 gold 语义不同、四种范围（多配置、未配置默认、schema 版本、生成器门）被参考测试放过（前两种已实测） | **保留但标"参考覆盖不足"**（处置卡 verdict coverage_gap）；另版本审议补三条断言（未配置默认比对同进程 `build_jobs`、Ninja Multi-Config、守护 version 3 / cmakeMinimumRequired 3.15；VS/Xcode 不断言）——T0，静态预计 12 条变 8/12；当前形态下作为区分题无效 |
| DVC5839 | 三款 10/12；DeepSeek 两次同一种过度修复被数值 P2P 拦下（题卡担心的 Mock 漏判未出现）；actor 需 pathspec 派生 | **保留**，actor 环境资格记派生镜像；题卡"命令层硬编码 8"校准仍未做 |
| Moto5134 | Coder 0/4、另两款 8/8；失败全部命中公开缺键断言 | **保留**，是当前池里最好的区分题；archive 相关回归不在评分选集内，可考虑扩 P2P |
| Dask8597 | 6/6 | 保留；当前形态无区分度 |
| DVC6954 | 6/6（另 1 次 infra 已重跑） | 保留；题卡的完整参数工作流（不变跳过 / 改值重跑 / -0.5 走 CLI）四条轨迹都没走完，仍是未验项 |
| mypy17071 | DeepSeek、Qwen3.6 4/4（Qwen3.6 走 gold 的遍历器路线、DeepSeek 走 checker 局部 override，两者对本检查等价），Coder 0/2（零源码改动、同一错误假设） | 处置卡 verdict **coverage_gap（潜在）**：两项 P2P 根本不经过 `check_unbound_return_typevar`，该诊断的 15 条公开断言无一在选集内——把函数改成直接 return 静态上就能得 1（未实跑）；用作 RL 奖励前补负例是 T0。TypeIs 范围问题：TypeGuard-only 候选按构造必被 TypeIs F2P 拒，是规范问题不是实验问题。Qwen3.6 格子提出的"延迟重分析丢 type_guard"线索已由 DS a1 自写测试的运行证据支持，但只在代码本身已有未定义名错误时触发，是独立的 base 缺陷，不计入 gold 或候选。本题是全轮唯一有"撞上限仍得 1"的题（3 条，补丁都在半程前定型） |
| mypy11236 | 6/6 全 0；任务级调查判**混合**：DeepSeek a1/a2、Qwen3.6 a2 三条实质候选修好了题面 MWE 与全部六个负例，只被 F2P 里两处**题面未提**的断言拒绝——`x: Final = (1,)` 后 `return x`（Final 分支是 gold PR 的范围扩展，仓库既有用例反而把它写成预期失败）与错配消息措辞 `Tuple[bool, int]`（任何走推断路线的修法都会变成 `Tuple[Literal[False], int]`，仓库先例支持后者）；三条候选与维护者讨论里的 "splicing" 方向相同，gold 走的是另一条子类型层路线。Coder a1/a2 零语义改动、Qwen3.6 a1 零编辑，属模型失败。回合上限对六条都不是因果（但 Qwen3.6 a1 截断时仍在推理、Coder 两条最后回滚，"延长预算也必失败"没有证据，§9.2.4）。Final 分支与消息措辞要分开裁定；"gold 让既有用例失败"是静态推断且该用例已被上游 test patch 有意更新，不足以说 gold 引入回归（§9.2.2）。P2P=0 且评分不跑其余 5334 例 | **不进模型比较分母与训练池**（与 Moto5752 同处置：A 保留原题作诊断旁路 / B 题面补充 Final 说明与措辞约定 / B′ 去掉两条绑定路线的断言 / C 仅评测 / D 淘汰，待用户决定）。报告 `runs/base_probe_20260922/analysis/python__mypy-11236/task_investigation.md` |
| Moto5752 | 6/6 全 0，判定"规范欠说明型误拒"（题面不含 BeginsWith，F2P 第 3 断言来自 gold PR 的范围扩展） | **不进模型比较分母与训练池**；处置 A/B/B′/C/D 见 §7.5c，需用户决定；若选 B 先核实 AWS 真实行为 |

### 8.5 三款模型的初步画像（8 题、小样本，只用于提出下一步假设）

- **Qwen3.6-35B-A3B**：18/18（争议题外），最快（中位 57 s），撞回合上限最少；thinking 经项目 adapter 解析无误；中途会改坏文件但能自行 `git checkout` 复原；用了少量 Task* 无关工具。风险在训练侧：thinking 被周期性清空（#7）、混合注意力架构的训练栈兼容未验。
- **DeepSeek V4-Pro（对照）**：16/18；最主动探测答案渠道（4/4 条被审轨迹）；两次在 DVC5839 上过度修复；CC 不回传其 thinking 导致重复推理（一条轨迹 4 轮重推占输出 76%，推断）。作为对照可用，不是基座候选。
- **Qwen3-Coder-30B-A3B**：12/18；两个"模型专属全 0"格子（Moto5134、mypy17071）都是"诊断对、实现不出"；工具报错率最高、撞上限最多、最容易被无关工具与系统提醒带偏、候选夹带临时脚本最多。这些恰好是 RL 有可能改善的行为，但 8 题里有 **4 题**它在当前预算下拿不到任何正样本（Moto5134、mypy17071，以及两道争议题 Moto5752、mypy11236；§9.2.1 勘误，原写 3 题）。
- 结论边界：每格 2–4 次、8 题、`bash_env_v1` 诊断条件、探针网关而非训练 adapter 的 turn 闸门；不能据此排名或定基座。设计稿建议的下一步（结果可解释后扩至 12–21 题、每款每题 4 次）现在有现成入口，续跑只需再租机器。

### 8.6 今晚没有做的事

未改生产代码、题目、gold、测试或 reward；未 commit / push；未给 solver 开公网；审查材料未进 solver 容器。`rh2/experiments/base_probe_20260922/` 与 `rh2/experiments/env_recipe_repair_20260919/`（未动）为未跟踪目录。Pydantic8511、mypy10308、Pandas 三题与其余 mypy / moto / dvc 候选未跑。Novita 后备未用到。

## 9. Codex 复核与后续安排（2026-09-22）

本节是对上述早报的独立复核与建议，不改写历史实验，不代表新题目规则已批准。用户已另行安排 Claude 补读轨迹、汇总8张题级卡、准备A线交接包；以下避免重复派发。本轮没有恢复实例、运行模型/容器、改生产代码或提交推送。

### 9.1 已核实到的范围

- 重新聚合全部67份 `attempt.json` 与最终评分账本（4条采用保留原件的 `grading_v2`）：三款的 S/V/N 与§8.1一致，合计46/66/67。最终账本安装失败命令为空、安装末码0、测试段完成，actor与grader清理记录无异常；这是日志复核，不是本轮重新执行。
- 回扫2326份网关SSE原件：2325份有 `message_stop`，仅已登记的 DeepSeek/DVC6954/a1 缺失，且有运输异常。未发现第二条同类历史异常。终止事件存在只核此维度，不证明消息全部语义正确。
- 回读两题公开prompt、全部6条Moto5752和6条mypy11236的最终失败日志、Conan四路生成记录；Moto的6条都止于同一条1069行断言，原任务报告详细覆盖的是其中4条。
- 对照正式 `materialize/generate/bringup`、slime launcher/adapter/parser与实验入口：BASH_ENV没有从launch spec传进driver、路径又在隐藏的 `/root`，确有可达缺口；诊断变体已证明三题可恢复开发入口。这里不宣称66条轨迹都已独立全文审完。
- 本轮结构化复核产物在本地 `runs/base_probe_20260922/codex_review_20260922/{attempt_reconciliation,sse_completion_scan}.json`。

### 9.2 需要收紧的结论

1. **能力差异不等于已得到组内RL信号。** 24个题×模型格子仅DeepSeek×DVC5839出现混合；两款待选本地基座尚无观测到的混合格子。Coder有4个全零格子，不是§8.5所写3个。全零/全一对诊断有用，但本批同题二值奖励没有组内差异；这不证明扩大采样或改进任务后仍无信号，也不代表这些行为不能用SFT/OPD改善。DeepSeek四次的日志位置中途改变，但前后各自两次仍各有一成一败，需按条件报告，不能笼统称四次完全同条件。
2. **测试拒绝的位置已证实，测试是否不合理还需裁定。** Moto5752的公开例子确未提标签前缀过滤；但[AWS官方API说明](https://docs.aws.amazon.com/systems-manager/latest/APIReference/API_ParameterStringFilter.html)明确允许DescribeParameters使用Equals/BeginsWith，Path另有例外。争议是本题应修复的范围，不是BeginsWith行为本身没有依据；当前文档也不自动证明历史版本约定。mypy11236的Final分支和消息措辞应分开判断：不能因没有在prompt逐字出现就删断言，也不应把“按gold的实现路线修”写成要求。旧公开测试被上游test patch有意更新，不足以证明gold引入回归。先做独立行为矩阵与修订草案，保留原始全题分数，诊断子集另列。
3. **Conan漏测证据成立，新增断言仍须有公开依据。** 四路生成记录确认两条成功候选分别漏默认jobs、多配置jobs；CMake 3.27将[jobs定义为并行参数](https://cmake.org/cmake/help/v3.27/manual/cmake-presets.7.html#build-preset)。补测应结合题面、既有Conan helper与工具语义，不把“与gold不同”直接定义为错误，不硬编码本次机器CPU数。
4. **接口相关性与因果分开。** thinking删除目前主要由token账与源码推断；需保存实际渲染输入/ID确认。mypy11236报告一面称上限非因果、无接口障碍，一面记录Qwen3.6/a1零编辑且仍在推理、两条Coder最后回滚；不能证明延长预算也必失败，更不能把后来可能写什么当事实。候选确有实现错误，但“完全由模型能力造成”比现有证据更强。
5. **正式链与探针修复不能互相代替。** `/tmp/.rh2_harness` 仍由agent属主、0700，移出仓库解决位置污染，未解决同UID可读。探针网关新增异常时abort，但干净HTTP EOF且缺SSE完结事件没有显式校验；这是读码发现的未覆盖情形，尚未故障注入。正式链已有响应flush后提交capture/poison逻辑，必须从它的真实入口回放，不能直接认定训练已被污染。工具参数变写、EOS外显、思考重渲染也应量化I01分行后的覆盖，不能看到分叉就等同丢训练token；修展示文本时保留原采样ID。
6. **审阅范围与回归覆盖需要准确描述。** 本次开始复核时是10份逐条报告＋2份任务报告，不是67条都已有独立报告。旧协议先读§7会提前暴露分数/gold结论，路径也含模型名；后续先封存公开材料初判，再看私有判分，不追认旧稿为模型盲审。独立核到22题P2P为空（mypy14/MONAI4/DVC3/Conan1），但一个F2P可能有多个正负断言；不能推成任意破坏都会得分或必须跑全仓。应先查具体未覆盖行为，用可区分候选证明，再选最小回归集。

### 9.3 今晚工作分配建议

**用户已安排执行的三项**：①剩余轨迹审阅与跨轨迹统计；②8题处置卡与静态预测回填；③A线7项交接包（只提候选修法）。沿原路径交付，先建逐attempt覆盖表，区分全文审阅、任务报告部分覆盖、未审阅；不机械按“Qwen3.6尚有21条”计数。统计测试修改时区分添加合理测试、修改既有期望、控制评分三类；读取本题旧实现、安装普通依赖与下载上游修复也分开，不统称作弊。`is_error`中的预期测试失败不能算协议错误。

若仍有额度，优先增加以下**有独立交付、不会重复读同一批全文**的工作包：

| 优先 | 工作包与范围 | 交付 / 验收依据 |
| --- | --- | --- |
| 高 | **B：固定候选的CPU行为裁决**。Conan默认/多配置、Moto5752公开顺序/前缀、mypy11236公开MWE/Final/六负例/消息差异。复用已有base、gold、实际候选，不重新求解 | 每题一张输入→预期依据→base/gold/候选结果表；已有Conan生成对照直接复用。补充检查mypy17071直接跳过目标检查、Moto5134缺键/archive、DVC5839硬编码8位、DVC6954负浮点及完整repro工作流，按风险选跑。产物为诊断断言与题目修订diff草案，不改正式oracle、不自动改历史分数 |
| 高 | **A：接口和训练消费的确定性回放**。在交接包基础上复现BASH_ENV、日志可读性、流中断；用已保存请求确认工具参数/EOS/thinking到渲染、capture、I01分行与mask的路径 | 原条件失败/候选修法恢复的窄证据；SSE至少含完整、连接复位、干净EOF缺完结三个对照；记录是否poison、是否装配、是否可能运输成可训0。模拟引擎可核控制流，缺真实ID/logprob不冒作数值训练验收。启动/日志与adapter两块指定不同文件owner，生产修复由A现有实现者接手 |
| 中 | **B：22题回归覆盖盘点**。按仓库复用源码/测试知识，但逐题标F2P已有负例、被选执行范围、具体缺口；先深做mypy11236/17071及代表项 | 一张覆盖表，少量能区分错误接受的候选与最小补测集；有/无P2P仅作检索线索。保留失败原因及选集成本，不增加全池全仓测试闸门 |
| 中 | **B：下一小批的环境准备**。优先补当前8题未覆盖的Pydantic8511与Pandas候选（56849/48106/53958中按材料完整性选1），再从已有mypy/Moto/DVC候选选2题 | 配方/原件/解释器/actor与grader差异清单及CPU入口。镜像和依赖已有记录先复用，避免又从原镜像猜起；未选中的13题不必同时重建。硬件就绪才执行，不提前派发模型 |

前两包价值最高；不能恢复x86机器时，先产出可直接执行的最小脚本和离线回放。实际题目CPU对照与正式actor身份核验需要相应Docker环境，不能拿本机替身当真机通过。缺省不需要加载GPU模型；也不必为消耗额度重跑已收口的noop/gold。

### 9.4 之后再推进的模型实验

先形成一版解释器、日志、工具面、模板/终止处理均有记录的求解条件，再选4–6题做两款Qwen的窄对照。保留1–2道已知题校准，引入新仓库/有区别的难度；不要只反复加采全过的简单题。若测试收窄工具面，一次只改这个因素，比较有效修改、真实工具失败、回合/时间和最终行为；不先加行为惩罚或归因成SFT必要。DeepSeek优先补有争议的格子，不必每题每次都当裁判重跑。

本夜无需先决定两道争议题永久淘汰、正式改reward、合并评分容器或最终基座。先交付可审阅的行为/测试修订版本，再决定采用哪版。若进入正式RL选择，还要单独确认Qwen3.6等型号的训练栈支持；单卡BF16求解通过不替代训练兼容验证。

### 8.7 第二轮分析：跨轨迹统计与逐题处置卡（2026-09-23，Fable 19 格 + 8 卡；Fable 额度耗尽后 3 张卡与 A 线交接包改用 Opus）

覆盖：67 条尝试全部有报告（首轮单条 10、格子级 47、任务级调查覆盖 10）；数字来自 `runs/base_probe_20260922/cross_trajectory_stats.json`（`aggregate_cells.py` 聚合各报告 JSON），分母为该项有记录的尝试数，不同轮次的字段口径略有差异（W1 的 4 个 Qwen3.6 格子无 `test_edit_kind`；`cc_param_rewrites` 是否计 `replace_all` 补默认各报告不一）。

| 指标 | DeepSeek V4-Pro | Qwen3-Coder-30B | Qwen3.6-35B | 备注 |
| --- | --- | --- | --- | --- |
| 修复前建立复现 | 4/19 | 12/20 | 8/18 | Coder 最常先复现，失败在实现而非定位 |
| 修复后跑了验证 | 18/19 | 19/20 | 18/18 | 但 DVC5839 上 10 条"验证"绕过修复点（直调 helper / 断言 Mock） |
| 答案渠道探测（执行了命令） | 7/19（git 未来引用 4、curl 公网 2、pip download 项目新版 1） | 0/20 | 0/18 | 得手 0/52；同模型同题探测不稳定（Moto5134：a1 三类、a2–a4 零次） |
| 读到 harness 轨迹目录 | 1/14 偶然（in_tree 的 grep 命中）+ 首轮 DVC5839 a2 主动 17 次 | 0/16 | 0/17 | 扩量轮已移出仓库树 |
| 改了官方测试文件（按 `projection.ignored_paths`） | 11/14 | 1/16 | 6/17 | 均被评分侧恢复；DeepSeek 1 条改既有期望以掩盖回归（DVC5839 a3），其余为加测试；Qwen3.6 / Coder 各有同名被遮蔽的死测试 |
| 候选夹带草稿文件（个） | 0 | 74 | 0（Qwen3.6 a2 在 mypy11236 有 11 个，任务报告口径） | Coder 候选 60–97% 字节是草稿；一条清空了仓库自带 `.dvc/config` |
| 无关工具调用（次） | 0 | 35（TaskCreate 10 / TaskUpdate 14 / ReportFindings 9 / Skill 1 / TaskList 1） | 14（TaskCreate 4 / TaskUpdate 8 / Skill 2） | 多数紧随 CC 中段 role:system 提醒；Skill 误调注入 6–12K 字符指令 |
| 工具报错拆分 | 预期测试失败 4 / 其它命令非零 7 / 调用格式错 0 | 38 / 19 / **10** | 3 / 9 / 0（另 14 为旧口径） | 只有 Coder 有真正的调用错误（old_string 过期、未先 Read、EISDIR 等） |
| 撞 60 回合上限 | 3/14（+首轮 3） | 6/18（+首轮 2） | 1/17（+首轮 2） | **所有被审轨迹截断均非因果**（补丁已定型或在兜圈） |
| `<|im_end|>` 泄漏（自部署） | — | 11/16 | 16/17 | 只在无工具调用的收尾轮 |
| CC 改写工具参数（次） | 78 | 113 | 31 | 去 `cd /testbed && ` 前缀、行尾空白、补 `replace_all:false`；回放历史 ≠ 采样 token |
| thinking 被清空（按 role:system 插入计） | 不回放 thinking（88/88 请求 0 块） | — | 53 次 | 机制与 A/B 方案见交接包 |
| 上下文峰值 | 49K | 77K | 50K | 131K 上限未触及 |
| 过程质量 good / mixed / poor | 12 / 5 / 2 | 1 / 14 / 5 | 11 / 7 / 0 | 审查员判断 |
| 疑似假阳性 / 假阴性 | FP 1 | FP 2、FN 2（Moto5752） | FP 1 | FP 全在 Conan15422；FN 全在争议题 |

逐题处置卡（`runs/base_probe_20260922/analysis/<task>/task_card.md`）：Moto5134 **keep**（8/8 成功 gold 同义，Coder 4 条同一先验；archive 回归面不在 P2P，扩选集是 T0）；Conan15422 **coverage_gap**（见 §7.5d 更新）；DVC5839 **keep**（10 条成功源码 md5 全同；唯一组内混合格子且奖励区分了正确的东西；CLI 矩阵无人跑全）；Dask8597 **keep**（6/6 与 gold 逐行相同，无区分度，环境 / 评分链的干净对照）；Moto5752 **spec_dispute**（6 条假阴性；B′ 改断言为 T0；B 题面补充有 AWS 文档依据）；mypy11236、DVC6954、mypy17071 三卡由 Opus 续写中。

对早报结论的修正：Coder 在当前预算下无正样本的题是 4 道而非 3 道（§9.2.1）；DVC5839 × DeepSeek 的混合在两种日志位置条件下各一成一败；Conan15422 的语义缺口是四种而非两种；"Coder 失败即能力缺口"应写成"两个稳定的错误假设（`event.get` 合并缺键与 null 后只删 None 判断；把回调返回类型误认成 `TypeGuardedType`），4/4 与 2/2 同路径，且 Moto5134 a4 曾搭出正确结构后整体回滚"。

### 8.8 第二轮分析收口（2026-09-23 约 03:00 UTC）：8 张处置卡 + A 线交接包

**产物**：19 份格子报告、8 张处置卡（`runs/base_probe_20260922/analysis/<task>/task_card.md`）、跨轨迹统计（§8.7）、[A 线交接包](base_model_probe_20260922_aline_handoff.md)（11 节，每节现象 / 正式链位置 / 最小复现 / 候选修法草案）。67 条尝试全部有报告。Fable 额度于 09-23 00:3x 耗尽，最后 3 张卡与交接包由 Opus 完成。

**处置卡结论一览（verdict 是卡片建议，不是决定）**

| 题目 | verdict | 与 gold 同义 / 语义缺口 / 误拒 | T0 事项 |
| --- | --- | --- | --- |
| Moto5134 | keep | 8 / 0 / 0 | 扩 P2P 纳入 archive 回归面 |
| Conan15422 | coverage_gap | 7 / 5 / 0 | 补三条参考断言（未配置默认、Ninja Multi-Config、守护 schema 版本） |
| DVC5839 | keep（唯一混合信号） | 10 / 0 / 0 | 补真实 CLI 数值断言（默认/4/8 × 普通/MD/JSON） |
| Dask8597 | keep（饱和对照） | 6 / 0 / 0 | — |
| DVC6954 | keep（饱和） | 6 / 0 / 0 | 补负 float / 容器 / 更新往返断言（本轮 0/6 会翻转） |
| mypy17071 | coverage_gap（潜在） | 4 / 0 / 0 | 补"未绑定 TypeVar"负例——两项 P2P 根本不经过被检查的函数，直接 return 静态上就能得 1 |
| mypy11236 | spec_dispute | 0 / 0 / 0 确认误拒、3 条条件误拒 | Final 分支与消息措辞两个独立开关（B′-f / B′-w），只放宽一处仍 6/6 为 0；三条实质候选之间还有 F2P 看不见的质量差异（两条区分输入） |
| Moto5752 | spec_dispute | 0 / 0 / 6 | B′ 改断言；B 题面补充有 AWS API 文档依据但需核历史版本约定 |

口径提示：两张争议卡对"误拒"的计数口径不同（Moto5752 直接计 6 条；mypy11236 计 0 确认 + 3 条件），汇总时不要相加。

**交接包新增的两个外推边界（比早报任何一条都重要）**
1. **本轮预算远宽于正式链默认**：探针用 `--max-turns 60`、上下文 131K；正式链 `RH2_MAX_TURNS_PER_SID` 缺省 25、`miles_gpu_spike/launch.sh` 的 `--rollout-max-context-len` 缺省 32,768（已核源码）。按网关留证复算，67 条里 39 条超过 25 次请求、48 条 prompt 超过 32,768；**46 条成功里只有 14 条同时落在这两个正式链默认限制之内**。本轮的 S/V/N 不能直接外推到正式链预算下的成绩；训练预算是待定的训练条件。
2. **CC 认为 `slime-actor` 的上下文窗口是 200,000**（67/67），而 `count_tokens` 由 vendored adapter 恒回 0（更正 §8.3 #8：不是探针网关，正式链同样如此）。按本地 CC 源码快照推断，I19 定的正常压缩大概率永远不触发、Read 的 25,000 token 上限也失效——需要在真实 2.1.205 上核对。

其它交接包更正：#1 在正式链里是两处独立缺口（激活文件在被 profile 隐藏并预检为不可读的 `/root`；`env_injections` 只记进启动规格、没传给 driver），只修一处无效；#4 CC 改写工具参数出现在 67/67 条、2,227 个工具调用轮里 307 轮（13.8%）被改写，对 I01 B 路线的粗估（推断）是 Coder 每次执行约 10 个训练行、总 token 约为单行的 7.9 倍，Qwen3.6 约 5.5 行、4.6 倍——可训练 token 不减少，多出的是重复前缀，须用正式链 `turn_coverage` 实测替换；#3 探针网关对"上游正常 EOF 但缺 `message_stop`"仍会正常收尾，需要四种 SSE 故障注入；#6 Qwen3.6 22/22 条都有中段插入共 72 次，CC 源码里 `smooshSystemReminderSiblings` 把提醒并入工具结果的做法支持备选 (a)。交接包的 CC 行为结论基于本地源码快照（非 2.1.205），已标注待核。

**没有做的事**：未改生产代码、题目、测试、reward；未通知 A 线（写入文档不等于送达）；未恢复实例；Codex §9.3 的"固定候选 CPU 裁决"已备好 6 个检查脚本但未执行（需机器）；"22 题回归覆盖盘点"未做。
