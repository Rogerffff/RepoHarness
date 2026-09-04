# Prime Intellect 生态现成环境资产调查（2026-09-02）

> 来源：Claude 主线程派出的仓库探索 subagent（very thorough 档），2026-09-02。
> 调查对象：`reference/research-environments`（HEAD `3093d72a`，2026-07-03）+
> `reference/verifiers`（HEAD `5885ab9c`，2026-07-03）+ 本项目 `rh2/` 对接现状。
> 关键前提：`rh2/pyproject.toml:47-48` 把 verifiers pin 死在
> `5885ab9c54152e707af2a11797aa52c3eb1752da`，与 reference checkout 完全一致——
> 下文对 verifiers 的结论对本项目**直接生效**。
> ⚠️ 时效注意：上游 verifiers 已发 v0.2.1/v0.3.0/v0.3.1（旧 API 移入
> `verifiers.legacy`），本文描述的是 pin 版本的事实；升级影响面见同目录
> `verifiers_v031_primerl_v090_impact_20260902.md`。

---

## 0. 前置更正

`reference/research-environments/AGENTS.md`（2026-07-06 由前序 agent 写的中文导览）在**抽象层描述上已过时**：通篇按 v0 的 `ComposableEnv / SandboxTaskSet / vf.Rubric` 讲解，但当前 checkout 的 73 个环境里 **61 个已迁到 `verifiers.v1` 的 `Taskset/Task/@reward` API**，只有 9 个还用 `ComposableEnv`。本文以实际代码为准。

## 1. research-environments：组织与环境清单

### 1.1 组织结构

- **73 个环境目录**（`environments/`），每个是**独立可安装 Python 包**（hatchling）。`lean_v1` 内含 6 个子包，taskset id 总数约 78。
- **命名即代际**：`*_v1` 后缀 = 新 `verifiers.v1` Taskset API；无后缀 = 旧 v0 API。CI 硬编码此约定（`tests/test_envs.py:78` 排除 `*_v1`，交给 `tests/test_envs_v1.py`）。
- 没有 `tasksets/`、`harnesses/` 顶层目录（README 历史残留）。SWE taskset 工厂与 OpenCode harness 实际在 verifiers v0 包内（`verifiers/envs/experimental/composable/`）。
- 代际统计（实测 grep）：`verifiers.v1` = 61；`ComposableEnv`(v0) = 9；纯 v0 `SingleTurnEnv/ToolEnv` ≈ 12。

### 1.2 分类清单

#### A. SWE 类（11 个，全部 `NEEDS_CONTAINER`）

| 环境 | 数据源 | 任务量级 | verifier | sandbox |
|---|---|---|---|---|
| `swebench_v1` | `PrimeIntellect/SWE-Bench-Verified-Quick` | 百级 | 执行测试：上游 swebench TestSpec + 官方 log parser 判 F2P/P2P | Prime registry 预建镜像 |
| `swebench_verified_v1` | Harbor `swe-bench/swe-bench-verified` | 500 | 执行测试（Harbor `solved` reward） | `ignore_dockerfile=True` + Prime 预建镜像 |
| `swebench_pro_v1` | Harbor `scale-ai/swe-bench-pro` | 千级 | 同上 | 公开 `jefzda/sweap-images` |
| `multiswe_v1` | `PrimeIntellect/Multi-SWE-RL` | 万级 | 执行测试 | per-instance 镜像 |
| `openswe_v1` | `GAIR/OpenSWE` | 万级 | 执行测试 | per-instance 镜像 |
| `r2e_gym_v1` | `PrimeIntellect/R2E-Gym-Subset-RL` | 8k+ | 执行测试（sandbox pytest） | per-instance 镜像 |
| `swesmith_v1` | `SWE-bench/SWE-smith-{py,go,java,js,ts,rs,cpp,php}` | 多语言万级 | 执行测试 | per-instance 镜像 |
| `swelego_v1` | `PrimeIntellect/SWE-Lego-Real-Data` | — | 执行测试 | per-instance |
| `scaleswe_v1` | `PrimeIntellect/Scale-SWE`（100k 验证实例） | 10 万级 | 执行测试 | per-instance |
| `swerebench_v2_v1` | `PrimeIntellect/SWE-rebench-V2` | — | 执行测试 + 自实现 parser（含 `test_patch` 可见性控制） | per-instance |
| `rlm_swe`（v0） | 多后端聚合 | — | 执行测试 + behavior LLM judge | Prime sandbox |

#### B. terminal 类（本次调查最有价值的发现）

| 环境 | 数据源 | 任务量 | verifier | sandbox |
|---|---|---|---|---|
| **`terminal_bench_2_v1`** | Harbor Hub `terminal-bench/terminal-bench-2` | 百级 | Harbor `solved` | 每任务自带 `[environment].docker_image` |
| **`terminal_lego_v1`** | `PrimeIntellect/Terminal-Lego-15k`（**私有 HF repo**，git clone） | **~13.8k** | Harbor `solved` | Prime registry 预建镜像 |
| **`tmax_v1`** | Harbor `tmax@2026-07-01`，registry 在本仓库 | **14,600**（registry.json 实测） | Harbor `solved` | Prime 预建镜像 |
| `openthoughts_tblite_v1` | Harbor `openthoughts/openthoughts-tblite` | — | Harbor `solved` | 预建镜像 |
| `uuid_ctf_v1` | 全合成 | 可无限生成 | 执行式（answer.json 回读比对） | 任意容器 |

**这些环境的实现代码分别只有 15/90/25/25 行**——全部是 `verifiers.v1.tasksets.harbor.HarborTaskset` 的薄壳（例：`environments/terminal_bench_2_v1/terminal_bench_2_v1/taskset.py` 全文 18 行）。

#### C. function-calling / tool 类（8 个）

| 环境 | 任务量 | verifier | sandbox |
|---|---|---|---|
| `bfcl_v3`（v0） | **4,441** | **AST checker**（官方 bfcl_eval，确定性） | **无**（纯进程内） |
| `general_agent_v1` | **4,417** | `db_hash` 精确匹配或任务自带 `verify(db)` | MCP Toolset（per-rollout 起服务器） |
| `tau2_bench_v1` / `tau3_bench_v1` | 四域/一域 | 官方 Tau2 evaluator | 无容器，但**自带 harness**（见 §2.5） |
| `mcp_atlas`（v0） | 500 | `vf.JudgeRubric`（LLM judge） | Prime sandbox + 官方 Atlas 容器 |
| `forth_lang_v1` | 419 | 执行测试（gforth 隐藏用例） | baked 镜像 |
| `wikispeedia_v1` | SNAP 图生成 | 状态标记 | 无 |

#### D. 搜索/研究类（8 个）：`browsecomp_v1 / deepdive_v1 / openseeker_v1 / redsearcher_v1 / wideseek_v1 / papersearchqa_v1(60k) / s1_deepresearch_v1 / arxivmath_v1`。verifier 基本全是 LLM judge；sandbox 需求为零；**但 taskset 不提供 search 工具，依赖 harness 自带 web search**——换 harness 必须自带搜索，否则退化成闭卷问答。

#### E. 数学/推理类（~22 个）：`math-verify` 规则匹配跑在 runtime 内 PEP 723 uv 脚本里（`math_env_v1` 等）；`lean_v1` 六子集 Lean4 编译验证；`prolog_v1` 程序化生成 + 约束式验证（多解全收、改事实骗不到 reward，质量很高）。

#### F. 代码（非 SWE）：`livecodebench_v1`、`i3_code_v1`（runtime 内 uv 脚本跑隐藏测试）、`programbench_env`（v0 自建三件套，支持 4 种 harness_mode + network_lockdown）。

#### G. 长上下文（7 个）：长文档上传 `/workspace/context.txt`，agent 用 REPL 扫描，答案写文件回读。

## 2. verifiers v1：抽象与 ownership

导览：`reference/verifiers/verifiers/v1/ARCHITECTURE.md`、`GUIDE.md`。

### 2.1 三件套

```
Taskset  = data + scoring（@reward/@metric/@group_reward + 生命周期钩子）——唯一判决权威
Harness  = 驱动模型逐轮的那个"程序"——只能定义 @metric，不能定义 reward
Runtime  = 程序（及 taskset 的 tools/user sim）在哪儿执行
```

- `Taskset`（`v1/taskset.py:104`）：泛型 `Taskset[TaskT, ConfigT, StateT]`；`load_tasks()` + 可选 `tools()/user()/setup()/finalize()/validate()`；ClassVar `NEEDS_CONTAINER`。
- `Harness`（`v1/harness.py:80`）：只需实现 `launch()`；能力 ClassVar：`SUPPORTS_MCP / SUPPORTS_USER_SIM / SUPPORTS_MESSAGE_PROMPT / APPENDS_SYSTEM_PROMPT`。
- `Task`（`v1/task.py:51`）：frozen pydantic，基类带 `image/workdir/resources/timeout`；**会随 trace dump 序列化**（rh2 A6 私有材料不上 Task 的直接原因）。
- **Rubric 在 v1 已不存在**：拆成 taskset 上的 `@reward/@metric` 装饰器 + 可插拔 `Judge`（`v1/judge.py` + `judges/{reference,rubric}.py`）。
- **Sandbox 统一为 `Runtime`**（`v1/runtimes/{base,subprocess,docker,prime,modal}.py`）：`start/stop/cleanup、run、run_background、run_uv_script、read/write、expose`。

### 2.2 环境如何声明任务来源/verifier/sandbox

三者全在 Taskset 一侧：任务来源 = config 字段；sandbox 需求 = ClassVar + 逐 Task `image` 字段；verifier = `@reward` 装饰器方法。

**Harbor `solved` reward 是最好的 harness-agnostic verifier 范例**（`v1/tasksets/harbor/taskset.py:322-341`）：rollout 结束后才把 `tests/` tar 上传进 runtime、跑 `test.sh`、读 `/logs/verifier/reward.txt`——**agent 全程看不到测试**，且对 docker/prime/subprocess runtime 完全 opaque。

### 2.3 组合与解耦

- v1 中组合发生在配置层：`EnvConfig` 两字段 = taskset + harness；同一 taskset 可以 `--harness.id mini-swe-agent / rlm / codex` 直接切换（`v1/README.md:118-124`）。
- 构造期 fail-fast 三门（`v1/env.py:301-331`）：taskset 有 `tools()` 而 harness 无 `SUPPORTS_MCP` → 拒；有 `user()` 而无 `SUPPORTS_USER_SIM` → 拒；`NEEDS_CONTAINER` 而 runtime 是 subprocess → 拒。
- **例外**：`tau2_bench_v1/tau3_bench_v1` 自带 Harness 子类（唯二），换 harness = 重写，**只能当数据源不能当环境**。
- 21 个环境显式声明 harness-agnostic；Harbor 系天然 harness-agnostic。
- BYO harness 契约（`GUIDE.md:701-707`）："harness 从不自己构建 trace，只把一个程序指向 endpoint"——程序用三种 dialect 之一发请求，interception server 自动记账。内置 7 harness：`default/null/rlm/codex/mini-swe-agent/kimi-code/terminus_2`。

## 3. 本项目对接现状

- **Form A/B 定案**（`00-project-status.md:70` + `s0/topology_ab_report.md`）：B（slime `custom_generate` 直调 SGLang）为训练主线；A（verifiers TrainClient + vLLM shim）保留为协议基线——分水岭是 top-p tape（vLLM/verifiers wire/prime-rl 三端零支持，形态 B 只需 slime 官方 patch 镜像）。
- **实际依赖已收窄成一条细线**：唯一生产 import 是 `taskset/swebench_smoke.py`（vf.Taskset 薄壳）+ 四个契约测试（graph token identity / rollout lifecycle / envserver wire / trainclient protocol，pin 5885ab9c）。
- **显式不用并有单测钉死**：envpack 库层零 verifiers import；grading 容器直接用 docker CLI 不经 verifiers `DockerRuntime`——因为后者**硬编码 `--network host`**（`v1/runtimes/docker.py:99-102`）且不支持 label，而评分容器需要 `--network none` + label 记账；`contracts/sandbox.py:43` 把 `host_open` 列为禁止表示。
- `adapters/verifiers_projection.py`（412 行，S1-8）：verifiers Trace → 中立 `TrajectoryProjection` 投影，评测/导出线。EvalClient 文本中继显式降级（loss_mask 全 0 + 理由码 + `VerifiersEvalRelayNoRenderer` 哨兵），token-faithful 轨迹直接拒收不静默降级。

## 4. Environments Hub

- 分发机制：`prime env install <org>/<name>[@version]`；代码级 `ensure_installed()`（`v1/utils/install.py:30-42`）在 load 时自动从 Hub 安装，taskset/harness/judge 三种插件全走这条路。
- 规模参考：本地调研笔记（`tmp/fa_vs_miles_architecture_review_brief_20260823.md:58`）记 "Hub 2500+ 环境，73 个官方生产环境，SWE 系全覆盖"。
- research-environments 两条正交分发通道：Python 包通道（环境代码，`uv pip install -e`）+ Harbor registry 通道（任务数据，仓库根 `registry.json` 4.9MB 登记 `general-agent@2026-06-25`(4,417) 和 `tmax@2026-07-01`(14,600)）。
- **最诚实的可用性清单**：`tests/test_envs_v1.py:32-68` 的 `SKIP_EVAL` 白名单——34 个环境上游自己承认普通 CI 跑不动（需 docker/prime、私有 HF repo、judge key 等），接入前必读。

## 5. 对"扩展第二可验证域"的可复用度判断

### 直接可用（改动 < 50 行）
1. **Harbor terminal 系（terminal_bench_2 / terminal_lego / tmax / openthoughts_tblite）——最优选项**：verifier 边界与 rh2 隔离要求天然同构（测试 rollout 后注入）；任务量 28k 级；镜像全部预建；完全 harness-agnostic；实现代码 15~90 行。
2. **零 sandbox 判定类**（bfcl_v3 4,441 AST checker / math_env 系 / unscramble / verbatim_copy）：最便宜的 function-calling 冒烟面。

### 需要适配
| 环境 | 适配面 |
|---|---|
| SWE 系 | verifier 隔离：reward 跑在 agent 用过的同一容器（已知缺陷）→ 换 `SWEGradingManager` clean-checkout 重放；任务格式与镜像可直接复用 |
| 搜索/研究系 | harness 需自带 web search + 网络出口与 sandbox 契约 `deny_all/allowlist` 冲突 + LLM judge 治理 |
| `general_agent_v1` | MCP Toolset 生命周期与 sandbox lease 对齐（verifier `db_hash` 天然确定性可离线重放，质量好） |
| `prolog_v1/forth_lang_v1/uuid_ctf_v1` | 专用镜像准备（verifier 质量很高） |
| 所有 docker runtime 环境 | `--network host` 硬编码 → rh2 已有绕行（直接 docker CLI） |

### 不可用 / 不建议
`tau2/tau3_bench_v1`（自带 harness，只能当数据源）；`mcp_atlas`（四重外部依赖）；`rlm_*`（v0 过渡态 + RLM harness 强绑）；纯 prime runtime 环境（需平台账号——但仅 runtime 层不可用，taskset 可配 docker + 自建镜像站）。

### 推荐路径
**第二可验证域选 terminal，载体选 Harbor 格式**（terminal_bench_2_v1 评测面 + terminal_lego/tmax 训练面）：唯一同时满足 (a) verifier 隔离已达标 (b) 任务量到万 (c) harness-agnostic (d) 镜像预建 (e) 实现 < 100 行 的选项。适配收敛到两条：镜像分发（Prime registry → 自建镜像站）、runtime 网络策略——两条 rh2 都有现成方案。

## 附：关键文件路径速查

| 想看什么 | 路径 |
|---|---|
| v1 框架内部设计 | `reference/verifiers/verifiers/v1/ARCHITECTURE.md` |
| v1 作者指南（BYO harness 模板） | `reference/verifiers/verifiers/v1/GUIDE.md:633-748` |
| 组合 fail-fast 三门 | `reference/verifiers/verifiers/v1/env.py:290-331` |
| **Harbor 通用 taskset（terminal 复用核心）** | `reference/verifiers/verifiers/v1/tasksets/harbor/taskset.py` |
| docker runtime `--network host` 硬编码 | `reference/verifiers/verifiers/v1/runtimes/docker.py:99-102` |
| Hub 按需安装 | `reference/verifiers/verifiers/v1/utils/install.py:30-42` |
| v1 环境真实可用性白名单 | `reference/research-environments/tests/test_envs_v1.py:32-68` |
| Harbor registry（2 dataset，19k 任务） | `reference/research-environments/registry.json` |
| rh2 verifiers 投影（Form A 评测线） | `rh2/src/repoharness2/adapters/verifiers_projection.py` |
| rh2 唯一 import verifiers 的生产文件 | `rh2/src/repoharness2/taskset/swebench_smoke.py` |
| rh2 为何不用 verifiers DockerRuntime | `rh2/src/repoharness2/grading/manager.py:36-46` |
| Form A/B 定案报告 | `docs/agentic_RL/repo_harness_rh2_workstreams/s0/topology_ab_report.md` |
| verifiers pin | `rh2/pyproject.toml:47-48` |
