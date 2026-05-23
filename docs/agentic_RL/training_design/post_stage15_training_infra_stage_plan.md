# Stage 15 之后的训练实验导向基础设施路线

```text
status: planning_draft_after_stage15_2
scope: training_experiment_driven_infra_plan
created_from:
  - docs/agentic_RL/training_design/实验设计.md
  - docs/agentic_RL/training_design/RL_algorithm_design.md
  - /Users/roger/Desktop/claude-code/docs/resume/swebench-verified-score-gap-investigation-progress.md
  - /Users/roger/Desktop/claude-code/docs/resume/pre-verl-persistent-diagnostic-session-implementation-plan.md
assumption:
  - Stage 15.2 已经证明 fully async partial checkpoint / resume / policy loss / parameter sync 的短程 smoke 可以跑通。
  - 但这仍然只是短程基础设施 smoke，不等于已经具备正式 SWE model 强化学习实验所需的完整训练语义、数据治理、工具质量和评估治理。
```

## 1. 当前判断

当前异步链路已经基本打通到“可以开始设计训练实验基础设施”的阶段。具体来说，RepoHarness 已经具备：

1. `RepoHarnessRuntime.start_episode(...)` 异步启动 episode。
2. `RepoHarnessVerlAgentLoop` 调用真实 `real_episode`。
3. `VerlLLMGateway` 通过 verl 管理的推理服务拿到 token、mask、log probability 和 generation record。
4. 受控 turn boundary 生成 `PartialEpisodeCheckpoint`。
5. 同 runtime 内 resume，恢复到 terminal episode result。
6. 只把恢复后的完整、终态、可训练、`route=verl` 样本送入 policy loss。
7. 真实 fully async trainer smoke 中完成 optimizer step 和 parameter synchronization。

因此，下一阶段的重点不应继续停留在“证明异步链路能不能跑”本身，而应该转向：

```text
用实验设计反推基础设施能力：
需要什么样的数据、轨迹、reward、batch、advantage、工具、评估和可复现实验包，
就按这些目标继续改造 harness infra 和 RL training infra。
```

但是也必须明确：当前链路还没有满足正式 SWE model 强化学习实验的全部要求。它还缺少：

1. 真实任务池和训练数据治理。
2. SWE-Gym / R2E-Gym 的 policy-visible 与 reward-only 字段边界。
3. 持久 shell / 公开测试入口 / 官方验证健康门槛等更真实的软件工程动作空间。
4. chunk / segment / compressed-state 训练样本语义。
5. 确定性 process reward 和 efficiency reward 状态机。
6. DAPO 风格 group filtering、length control、all-zero rescue、staleness gate。
7. BS-Chunk-DAPO 的 chunk-level reward-to-go、advantage 和 loss aggregation。
8. 小规模到中规模训练的 profile、监控、评估和可复现实验报告。

## 2. 目标算法对基础设施的要求

两份训练设计文档建议的主线可以概括为：

```text
BS-Chunk-DAPO:
Bounded-Staleness Chunk-aware DAPO for SWE Agents
```

这里的核心不是“再换一个强化学习算法名字”，而是对基础设施提出了非常具体的约束。

### 2.1 必须保留异步 rollout 的新鲜度事实

每条样本至少需要保留：

```text
episode_id
prompt_id
rollout_id
rollout_policy_version
adapter_version
min_global_steps
max_global_steps
old_logprobs
generation_records
trajectory_param_versions
staleness
```

这些字段用来判断样本是否还能进入当前 policy loss。异步链路中，不能只看“样本最终成功或失败”，还必须知道它是哪个策略版本生成的、距离当前训练步有多旧、是否超过 staleness gate。

### 2.2 必须把 SWE agent 的行动拆成 chunk

建议第一版 chunk 定义为：

```text
从一次 assistant 生成开始，
到下一次 tool observation 或 final answer 结束。
```

更具体地说，一条轨迹可以被拆成：

```text
read / search chunk
edit chunk
test chunk
repair chunk
submit chunk
```

训练时不能只把整条 response 当成一长串 token。需要记录：

```text
chunk_offsets
chunk_type
chunk_start_turn
chunk_end_turn
chunk_response_mask
chunk_local_process_reward
chunk_reward_to_go
```

后续 advantage 可以先从 terminal reward 广播到整条轨迹，再逐步升级到 chunk-level reward-to-go。

### 2.3 压缩上下文后，逻辑 episode 不拆，但训练样本必须拆成 segment

如果长任务中发生 context compaction，训练表示必须遵守：

```text
logical episode 仍然是一条完整任务轨迹；
training sample 必须按 compaction boundary 拆成多个 segment。
```

压缩后的 segment 训练输入必须等于 rollout 时模型真实看到的输入：

```text
system prompt + issue + summary + recent raw turns
```

不能在训练时偷偷把压缩前完整历史重新拼回来。否则 `old_logprobs`、policy ratio 和 state distribution 都不再对应 rollout 时的真实状态。

每个 segment 需要记录：

```text
logical_episode_id
segment_id
num_segments
visible_context_hash
summary_id
summary_text
summary_prompt_hash
compressed_range
summary_quality
segment_response_ids
segment_response_logprobs
segment_chunk_offsets
segment_loss_weight = 1 / num_segments
```

summary 本身由外部 compactor 或工具产生时，默认 `loss_mask=0`，不能作为 policy action token 训练。

### 2.4 Reward 必须分层，且 process reward 不能泄漏 oracle

建议 reward 结构：

```text
R_total =
  terminal_reward
  + process_reward
  + efficiency_reward
  + overlong_or_compaction_penalty
```

其中 terminal reward 仍然占主导。process reward 只奖励可验证的软件工程状态变化，例如：

1. 读取 traceback 指向文件。
2. 找到相关 symbol。
3. 产生非空且可 apply 的 patch。
4. edit 后运行相关公开测试。
5. 根据测试失败继续 repair。
6. 失败数量下降。

process reward 不能查看 gold patch、hidden test、`FAIL_TO_PASS` selector、`PASS_TO_PASS` selector、R2E-Gym 的 `expected_output_json`、`relevant_files` 或 `modified_files`。这些只能在 reward-only 或 evaluator-only 层使用。

### 2.5 DAPO 需要 SWE 专用过滤指标

不要只用 `acc` 或 `resolved` 做 group filtering。建议构造 `swe_filter_metric`：

```text
3：final verifier accepted
2：patch applies，并且运行过相关公开测试或自写复现
1：patch applies，但测试证据弱
0：普通模型失败
-1：timeout、严重无效工具调用、环境不可用、上下文不可用
```

DAPO group filtering 应该：

1. 保留有分差的 prompt group。
2. 对全成功或全失败 group 做过滤。
3. 但 early training 阶段保留一小部分 all-zero rescue quota，用来学习有过程进展但未解决的轨迹。
4. 把 harness 错误、环境错误、权限误拦截、验证环境不健康与模型失败分开。

## 3. 另一个 worktree 的改造必须纳入后续路线

另一个 worktree 的 SWE-bench Verified 分数差距排查说明：当前 harness 的软件工程动作空间仍然不够真实。这个问题会直接影响后续强化学习训练质量。

### 3.1 必须吸收的改造

后续不能直接在当前工具能力上扩大训练。至少需要吸收这些能力：

1. **持久诊断执行环境。**

   原来的 `bash` 过于受限，不能代表真实 SWE agent 的 shell 能力。另一个 worktree 中的 `diagnostic_shell` 和 persistent diagnostic session 证明，同题内持久 shell / 持久容器可以显著改善“复现、编辑、测试、修复”的闭环。

2. **完整 shell 的防泄漏边界。**

   一旦提供完整 shell，就必须禁止：

   ```text
   .git 历史访问
   git log / git show / git cat-file / git rev-list 等历史命令
   /repo-harness-run
   gold_patch
   test_patch
   FAIL_TO_PASS / PASS_TO_PASS selector
   hidden_test
   official verifier evidence
   ```

   同时仍然允许：

   ```text
   git status
   git diff
   git grep
   git ls-files
   ```

3. **公开环境入口提示。**

   不能给模型 hidden selector，但应该告诉模型：

   ```text
   当前仓库根目录是什么
   每次 shell 默认从哪里执行
   可以使用的 setup 命令模板
   可以使用的公开测试命令模板
   不要把依赖安装进仓库目录
   ```

4. **每题独立可写层，跨题共享依赖环境只读。**

   Stage 12.5 的共享依赖环境方向是正确的，但训练时还需要每题可写的 `HOME`、`TMPDIR`、cache 和 overlay。模型不能污染共享依赖环境，也不能把临时依赖目录混入 final patch。

5. **最终补丁卫生。**

   需要过滤 `patch.txt`、`*.orig`、临时备份文件、诊断脚本产物，避免把它们当成模型对仓库的真实修复。

6. **官方验证健康门槛。**

   在 SWE-bench Verified 这类任务上，gold patch healthcheck 必须先通过。否则本地镜像依赖漂移会把正确补丁误判为失败。

7. **内部 verifier 与官方 verifier 分层。**

   在没有完全复用官方 instance image、官方依赖环境和官方 evaluator 前，内部 verifier 只能作为 proxy 或 diagnostic。正式分数和最终 reward finality 需要绑定可信 verifier。

8. **工具可见注册表与实际执行注册表一致。**

   模型可见工具和实际可执行工具不能不一致。否则 RL 会产生大量本不该出现的工具错误负样本。

### 3.2 为什么这些改造要在算法实验前做

如果不先吸收这些 harness 改造，后续训练会出现严重污染：

1. 模型学到的不是“如何修软件”，而是“如何在受限 shell 下反复搜索”。
2. 权限误拦截会把本来合理的公开测试行为标成失败。
3. 依赖环境漂移会把正确补丁标成失败。
4. patch 污染会让 SFT、RL 和偏好数据包含无关文件。
5. Git 历史泄漏会让部分样本变成作弊样本。

因此，另一个 worktree 的改造应被视为后续训练扩大前的基础设施前置条件，而不是旁支评测优化。

### 3.3 Claude Code 工具系统对 Stage 16 的启发

对照 `reference/claude-code-typescript-src` 可以看到，Claude Code 的工具面不是“只给模型一个完整 Bash，然后让模型用 Bash 完成所有事情”。它采用的是分层工具系统：

```text
Read / Grep / Glob / Edit / Write：
  承担读文件、搜索、文件发现、编辑和写文件等高频动作。

Bash：
  承担测试、构建、项目命令、Git / GitHub 命令、复杂诊断和后台任务。
```

这个分层在参考源码中有明确提示。例如 `BashTool` 的提示词要求：

```text
Read files: Use Read (NOT cat/head/tail)
Edit files: Use Edit (NOT sed/awk)
Write files: Use Write (NOT echo >/cat <<EOF)
```

`GrepTool` 也明确要求搜索任务使用 `Grep`，不要通过 Bash 调 `grep` 或 `rg`。这说明产品态 Claude Code 虽然有强大的 Bash 工具，但仍然把读、搜、改、写这些高频动作放在结构化工具中，让权限、审计和用户审查更清楚。

RepoHarness 的训练环境比产品态 Claude Code 更严格，原因是：

1. 训练时没有真人逐条确认权限。
2. SWE-Bench-like 任务有 evaluator-only artifact、gold patch、test patch、official selector 和 run directory 泄漏风险。
3. online reinforcement learning 会把工具失败、权限误拦截、隐藏信息泄漏和环境污染都写进训练分布。
4. 共享依赖环境、workspace snapshot、runtime-private 目录和 verifier artifact 都必须保持模型不可见。

因此，Stage 16 不能把 Claude Code 的 Bash 行为简单复刻成一个无边界的 `execute_bash`。更合理的设计是：

```text
结构化工具作为正式训练主路径：
  read_file / grep / list_files 或 glob_files / edit_file / git_diff

execute_bash 作为安全最小 shell 面：
  允许少量可审计、可脱敏、不会污染共享环境的诊断命令。

persistent diagnostic shell 作为后续高权限能力：
  在 Stage 16B 先完成协议和基础生命周期；
  在 Stage 16B.5 再证明远端训练机器可以正常运行 Docker backend。

项目测试和复现能力通过受控入口补齐：
  run_public_tests / run_project_test / python_probe 或 scratch_python / task-declared project command。
```

这里的核心不是增加大量模型可见工具，而是让每个能力有清晰所有权：

```text
读文件不要靠 cat/head/tail，而靠 read_file。
搜索不要靠裸 grep/rg，而靠 safe grep 工具。
编辑不要靠 sed/awk/python 脚本，而靠 edit_file。
测试不要靠模型写 source conda activate && pytest，而靠 harness-owned test routing。
临时 Python 复现不要靠 cat > /tmp/x.py && python /tmp/x.py，而靠受控 python_probe。
复杂 shell 诊断放到 persistent diagnostic session，而不是 Stage 16A 默认正式工具面。
```

注意：本文中提到的结构化 `grep` 或 safe grep，指的是 RepoHarness 自己拥有的搜索工具，
不是 `execute_bash` 里直接执行的裸 `grep` 命令。Stage 16A 可以保留一个极窄的裸
`rg` / `grep` 允许子集，用来做过渡期 smoke 和公开文本搜索，但后续正式训练主路径应逐步回到
harness-owned 搜索工具。这样可以把路径可见性、隐藏文件过滤、runtime-private 过滤和输出脱敏
放在工具实现里统一处理，而不是让模型通过 shell 参数自己组合。

这种设计既接近 Claude Code 的真实工具系统，又符合训练和测评场景的防泄漏要求。

## 4. 建议后续 Stage 顺序

下面的 Stage 编号是建议路线。它可以作为后续更新 `01-sequential-implementation-plan.md` 的基础，但本文件先作为实验设计导向的独立路线草案。

### Stage 16：Harness 动作空间和验证环境加固

目标：把 SWE agent 真实解题所需的工具、公开环境入口、持久执行环境和验证健康门槛合入当前 verl 分支。

这个阶段不能再做成一个粗粒度端到端 smoke。它需要拆成几个可单独验收的子阶段，避免“3 到 5 个任务能跑通”掩盖工具、权限、验证环境和证据链中的系统性噪声。

#### Stage 16A：工具动作空间与防泄漏边界

主要改造：

1. 固定正式训练主线里的模型可见 shell 工具名和 schema，第一版使用 `execute_bash`。
2. 明确 `execute_bash` 第一版不是完整产品态 Bash，而是安全最小 shell 面。它只允许经过 command policy 证明可审计、可脱敏、不会污染共享依赖环境的命令。
3. 把 Claude Code 的结构化工具优先原则写入正式 scaffold：读文件用 `read_file`，搜索用 `grep` 或 `list_files` / `glob_files`，编辑用 `edit_file`，查看补丁用 `git_diff`，不要让模型通过 `cat`、`sed`、`find`、`grep -R`、`python open(...)` 来替代这些工具。
4. 加入 Git 历史防泄漏、evaluator-only 防泄漏、词元级权限匹配，避免误伤 `test_patches.py` 这类公开文件名。
5. 禁止 `.git` 历史、run directory、hidden verifier、gold patch、test patch、官方 selector、共享依赖环境写入、越界路径、隐藏路径和 runtime-private 路径访问。
6. 收紧 `rg` / `grep` / inline Python 的默认 shell 能力，避免 `--hidden`、`--no-ignore`、`--unrestricted`、递归 grep、文件读取、路径枚举和环境枚举绕过结构化工具。
7. 工具可见注册表、provider / verl tool schema 和实际执行注册表必须一致。
8. 公开 evidence 无路径泄漏、无 hidden verifier 泄漏。
9. Stage 16A 只建立 `execute_bash` 的协议、最小 allowlist、拒绝语义、输出脱敏和注册表一致性；不承诺完整 persistent shell、项目命令 routing 或受控 Python 复现工具已经完成。

#### Stage 16B：persistent diagnostic session 生命周期

主要改造：

1. 合入 persistent diagnostic session 的协议和 Docker 实现。
2. 合入 local filesystem-persistent diagnostic session 的本机开发和测试形态，但默认仍然不能把普通 `local_process` 样本作为正式训练候选。
3. Docker persistent shell 必须证明同题复用、跨题隔离、timeout 后强制销毁 session、`keep_workspace=True` 时也不能保留活动容器。
4. local filesystem-persistent shell 必须明确不是完整常驻 shell 进程，只保证同题 `HOME`、`TMPDIR`、cache 和文件系统状态持久。
5. Stage 16B 不直接把远端训练环境中的 local filesystem-persistent shell 放入正式训练主线；它只作为开发和诊断 fallback。正式训练主线优先使用可正常运行 Docker 的远端 VM、裸机或完整机器。
6. `run_dir_mount_enabled=false`、session id、session backend、session cleanup status 必须进入结构化事实。

#### Stage 16B.5：远端 Docker-capable 训练执行后端验证

背景：

前一版计划考虑过在无法 Docker-in-Docker 的远端训练实例上继续加固 remote-local filesystem-persistent profile。经过重新评估，这条路线会把文件系统隔离、进程清理、`HOME` / `TMP` / cache 隔离、并发 episode 隔离、资源限制和网络限制都压到 RepoHarness 自己实现，开发和维护成本过高。正式 SWE agent 训练不应该长期依赖这个方案。

Stage 16B.5 的新目标是：在更适合训练的 GPU 服务商上，优先租用具备完整 root 权限、可以正常运行 Docker 和 NVIDIA Container Toolkit 的 VM、裸机或完整机器，用 Docker 后端承担底层执行隔离。`local_process` 和 local filesystem-persistent session 只保留为开发、诊断和紧急 fallback，默认不能作为正式训练隔离后端。

Stage 16B.5 不需要租用昂贵的多卡训练机器。第一版只需要一台低成本单卡 GPU 机器，验证远端执行后端能力即可。多卡 A100、H100 或 RTX PRO 6000 这类资源应保留给后续 fully async 训练吞吐验证和正式实验。

建议 profile 名称：

```text
remote_docker_capable_training_backend
```

Stage 16B.5-A：远端 Docker 能力预检

1. 验证远端实例具有真实 root 权限，可以安装或启动 Docker。
2. 验证 Docker daemon、NVIDIA Container Toolkit、`docker run --gpus all` 和容器内 `nvidia-smi` 可用。
3. 验证容器可以设置 `HOME`、`TMPDIR`、cache、workspace mount、资源限制和网络策略。
4. 验证容器退出、timeout、取消和 cleanup 后没有残留容器、残留进程或跨 episode 可见状态。
5. 记录 `remote_docker_backend_preflight_passed=true`、GPU 型号、驱动版本、CUDA 版本、Docker 版本、NVIDIA Container Toolkit 版本和镜像 digest。

Stage 16B.5-B：RepoHarness Docker diagnostic session smoke

1. 在远端 Docker-capable 机器上跑通 `RepoHarnessVerlAgentLoop -> real_episode -> Docker workspace backend -> diagnostic_shell -> final verifier -> TrainingView -> AgentLoopOutput`。
2. 验证 Docker diagnostic session 不挂载真实 run directory，不暴露 hidden verifier、gold patch、runtime-private artifact、共享依赖环境真实路径或宿主敏感路径。
3. 验证模型在容器内看到的是 workspace-relative 路径；命令输出和工具 typed metadata 继续通过路径脱敏和 visibility gate。
4. 验证 public source 修改可以被 final verifier、final patch capture、TrainingView 和审计证据看到；临时脚本、`HOME`、`TMP`、cache 和诊断私有文件不会进入 final patch。
5. 验证至少两个 episode 并发运行时，workspace、container、HOME、TMP、cache、artifact manifest、final patch 和 run directory 不互相污染。
6. 验证 cleanup、container removal、background process cleanup、projection sync、hidden path guard、shared dependency guard、visibility、token provenance、reward boundary 和 formal online RL gate 全部通过后，样本才可以成为正式训练候选。
7. 远端 evidence 明确记录 `remote_docker_diagnostic_profile_verified=true`。

本阶段不做：

```text
不实现 Stage 16C 的公开测试入口。
不实现官方 verifier healthcheck。
不实现 fully async 多卡训练吞吐测试。
不要求租用多卡 A100、H100 或 RTX PRO 6000。
不继续投入完整 remote local filesystem-persistent training profile。
不允许把普通 local_process 后端直接标记为训练安全。
不把 shared dependency environment 变成可写环境。
```

出口验收：

1. 低成本单卡远端 GPU 实例上通过 Docker 能力预检。
2. `docker run --gpus all` 和容器内 `nvidia-smi` 成功，且 evidence 记录驱动、CUDA、Docker、NVIDIA Container Toolkit 和镜像 digest。
3. RepoHarness Docker diagnostic session smoke 跑通至少一个 terminal sample，并通过 formal online RL gate。
4. 至少两个 episode 并发运行的 Docker 后端隔离测试通过。
5. 公开 evidence 通过路径泄漏扫描；runtime-private raw log 可以保留真实路径，但不能进入模型可见输出、TrainingView、AgentLoopOutput、DataProto 或公开 summary。
6. timeout、取消、cleanup failed、container removal failed、projection sync failed、background process uncertain、hidden path guard failed 的样本全部 `invalid_for_training=true`。
7. 如果远端 Docker 能力预检失败，Stage 16B.5 不能标记完成；可以把该机器作为 local diagnostic fallback，但不能把它作为正式训练执行后端。

#### Stage 16C：公开环境入口和模型行为提示

主要改造：

1. 加入 public environment context builder，告诉模型公开 setup/test 入口。
2. 提示模型默认工作目录、相对路径使用方式、公开测试命令模板、不要把依赖安装进仓库目录。
3. 不暴露 `FAIL_TO_PASS`、`PASS_TO_PASS`、gold patch、test patch、hidden verifier 或官方验证结果。
4. 增加 prompt/scaffold 对照，确认模型不再大量猜测 `/workspace`、`/repo-harness-run`、conda 路径或无效测试入口。

#### Stage 16D：official verifier / gold patch / no-op healthcheck

主要改造：

1. 加入 official image digest / gold patch healthcheck 门槛。
2. 加入 no-op / empty patch healthcheck 门槛。gold patch 通过只能证明验证环境能识别正确答案；no-op 或 empty patch 失败才能证明这个任务的 verifier 有基本区分力。像 `django__django-10097` 这类 no-op 也可能被判 resolved 的样本，必须标记为 `environment_or_oracle_invalid` 或等价状态，不能作为模型成功或模型失败样本进入训练。
3. 明确内部 verifier、官方 verifier、proxy reward、diagnostic reward 的边界。
4. 补齐内部 verifier 与官方 verifier 差异治理：`/testbed` 布局、官方 instance image、依赖版本漂移、内部 verifier 假阴性、`evaluation.rerun_final_verifier=false` 跳过控制流和 `final_verifier_boundary.json` 都必须有回归测试或结构化 evidence。
5. official verifier manifest 至少包含：

   ```text
   official_image_source
   official_image_digest_locked
   local_rebuild_environment
   gold_healthcheck_backend
   noop_healthcheck_backend
   remote_image_correction_applied
   proxy_validation_backend
   proxy_official_disagreement
   ```

#### Stage 16E：patch hygiene 和训练目标清洁度

主要改造：

1. 加入 patch hygiene，过滤 `patch.txt`、`*.orig`、临时备份文件、仓库内临时依赖目录和诊断脚本产物。
2. 把 patch hygiene 写成最终补丁捕获 ignore policy 和回归测试。
3. 被过滤文件可以保留为诊断 artifact，但不能进入 `final.patch`、SFT target、RL reward 证据或 preference pair。

出口验收：

1. 每个子阶段都有独立单元测试、集成测试和 visibility / path leak 测试。
2. 3 到 5 个真实任务先证明链路能走：

   ```text
   RepoHarnessVerlAgentLoop
   -> real_episode
   -> persistent shell
   -> edit / test / patch
   -> final verifier
   -> TrainingView
   -> AgentLoopOutput
   ```

3. 工具注册表一致性测试通过。
4. gold patch healthcheck 不通过的任务不能作为模型失败样本进入训练。
5. no-op / empty patch healthcheck 异常通过的任务不能作为模型成功或失败样本进入训练。
6. persistent shell 的同题复用、跨题隔离、timeout 清理和 run directory 不挂载事实可机器验收。
7. `final.patch`、SFT target、preference pair、reward evidence 都不能包含 `patch.txt`、`*.orig`、仓库内临时依赖目录或诊断脚本产物。

### Stage 16.5：20 到 30 题代表性 harness 诊断扩展

目标：在进入训练数据治理前，证明 harness 噪声已经低到可以扩大训练。3 到 5 题只能证明链路能跑，不能证明工具、验证环境、权限和 patch hygiene 足够稳定。

建议样本覆盖：

```text
原始 resolved
原始 unresolved
空 patch / no-op 风险
预算耗尽
公开回归
不同仓库类型
不同依赖复杂度
不同测试入口
```

验收指标：

```text
gold_healthcheck_pass_rate
noop_healthcheck_fail_rate
official_environment_unhealthy_count
permission_false_positive_count
diagnostic_shell_session_reuse_rate
would_require_diagnostic_shell_count
non_empty_patch_rate
public_test_run_rate
final_patch_hygiene_pass_rate
proxy_official_disagreement_rate
resolved_rate_under_official_harness
```

通过标准：

1. 20 到 30 题代表性样本有完整 harness signal summary。
2. gold patch 健康检查失败、no-op 异常通过、权限误拦截、环境漂移样本都被单独分类。
3. 不把 harness 噪声、环境问题或 verifier 无区分力样本作为模型失败训练。
4. 如果 20 到 30 题仍发现系统性 harness 问题，先修 Stage 16A 到 Stage 16E，不进入 Stage 17。

### Stage 17：训练任务和数据边界

目标：把 R2E-Gym、SWE-Gym 和内部微型任务池转成可训练、可验证、无 oracle 泄漏的任务 registry。

主要改造：

1. 新增 dataset adapter：

   ```text
   SWEGymPolicyInputBuilder
   SWEGymRewardOnlyBuilder
   R2EGymPolicyInputBuilder
   R2EGymRewardOnlyBuilder
   ```

2. 固定 policy-visible 字段：

   ```text
   problem_statement
   base repo
   visible repository files
   visible existing tests
   model-created reproduction tests
   model-visible shell stdout/stderr
   ```

3. 固定 reward-only 字段：

   ```text
   gold patch
   test_patch
   FAIL_TO_PASS
   PASS_TO_PASS
   expected_output_json
   relevant_files
   modified_files
   parsed_commit_content
   ```

4. 建立任务 manifest：

   ```text
   dataset_name
   task_id
   repo
   base_commit
   image_digest
   verifier_health_status
   noop_health_status
   official_validation_backend
   proxy_validation_backend
   healthcheck_timestamp
   split
   contamination_group
   oracle_fields_sha256
   policy_input_sha256
   reward_only_ref
   ```

5. 建立 train / validation / final test 分层。第一版建议使用下面的分层口径，具体数量可以在执行计划中根据预算调整，但必须写入 manifest：

   ```text
   SFT-train：300 到 800 条自有 harness 成功轨迹，优先来自 R2E-Gym non-overlap 和 SWE-Gym train
   SFT-dev：50 到 100 条同 schema 轨迹，用于检查工具格式和 replay
   RL-train phase 1：R2E-Gym 1000 到 1500 个任务
   RL-train phase 2：SWE-Gym 300 到 500 个任务
   RL-dev-fast：R2E-Gym held-out 100 到 150 个任务
   RL-dev-real：SWE-Gym held-out 50 到 100 个任务
   RL-dev-behavior：30 到 50 个行为诊断任务，专门观察 shell、测试、patch hygiene、重复搜索和权限误拦截
   final：SWE-bench Verified 500 或用户指定最终评测集
   secondary final：SWE-Gym held-out / R2E-Gym held-out 300，用于辅助解释泛化和环境差异
   ```

6. 每个 split 必须记录去重规则：

   ```text
   repo-level exclusion
   issue-level exclusion
   base_commit / gold_commit exclusion
   contamination_group
   task_family
   difficulty_label
   source_dataset
   healthcheck_denominator_policy
   ```

出口验收：

1. 任意 policy prompt、tool metadata、TrainingView、DataProto 中都不出现 reward-only 字段。
2. 每个 task 有可复查的 manifest 和 sha256。
3. 同 repo / 同 issue / 同 gold commit 污染边界可追踪。
4. task manifest 能携带 Stage 16 产生的 gold / no-op healthcheck 结果，并能被 sampler 用于排除 verifier 无区分力或环境不健康的任务。
5. healthcheck 后分母处理规则固定：`environment_or_oracle_invalid` 样本保留诊断记录，但默认不进入训练分母、不进入模型失败统计、不进入 policy loss。

### Stage 18：轨迹 chunk、segment 和压缩上下文 schema

目标：把当前 episode result 升级为支持 BS-Chunk-DAPO 和 compressed-state training 的训练样本表示。

主要改造：

1. 新增 `LogicalEpisode`、`TrainSegment`、`TrajectoryChunk` 或等价结构。
2. 从 `GenerationRecord`、tool observation、response spans 中构造 chunk。
3. 支持 compaction boundary：

   ```text
   logical_episode_id
   segment_id
   summary_id
   summary_artifact_ref
   summary_prompt_hash
   visible_context_hash
   post_compaction_prompt_hash
   compressed_range
   raw_history_ref
   summary_quality
   ```

4. summary、tool observation、environment observation 默认 `loss_mask=0`。
5. post-compaction segment 的 prompt 必须等于 rollout 时真实可见上下文。
6. 保存 chunk offsets、chunk type、turn offsets、tool_call_id、model_call_id、context_revision。
7. 保存 compaction event、summary artifact、summary prompt hash、真实 post-compaction prompt hash，以及 segment token / logprob 对齐事实。
8. 增加 summary quality gate。summary quality 不直接作为 policy reward，第一版只作为数据质量过滤或样本权重：

   ```text
   summary_quality >= 0.75：正常训练
   0.50 <= summary_quality < 0.75：可以保留，但降低 sample_weight 或只进入诊断
   summary_quality < 0.50：post-compaction segment 不进入 policy loss
   summary 生成失败、空 summary、visible_context_hash 不一致：fail-closed
   ```

9. summary quality 第一版可以用 critical atom recall 近似计算，重点检查：

   ```text
   failing tests
   traceback files
   changed files
   latest test result
   inspected files
   issue keywords
   rejected hypotheses
   next action
   ```

出口验收：

1. 一个无 compaction episode 能生成单 segment。
2. 一个含 compaction episode 能生成多个 segment。
3. 训练样本不能把压缩前完整历史拼回压缩后 segment。
4. chunk 与 generation record 的 token / logprob 对齐。
5. 如果无法证明 segment 的 prompt 来自 rollout 时真实模型可见上下文，该 segment 不得进入 policy loss。
6. 低质量 summary、summary 生成失败、summary prompt hash 不匹配、post-compaction prompt hash 不匹配都会结构化拒绝进入 policy loss。

### Stage 19：确定性 reward builder 和过滤指标

目标：实现可审计、不可泄漏、可用于 DAPO filtering 和 chunk reward-to-go 的 reward 体系。

主要改造：

1. Terminal reward：

   ```text
   final verifier accepted / rejected / invalid / timeout / infrastructure_error
   ```

2. Process reward 状态机：

   ```text
   read file indicated by visible traceback / public test failure / visible import path / grep hit
   inspect traceback file
   generate non-empty patch
   patch applies
   run relevant public test
   repair after failure
   failure count decreases
   no-op edit penalty
   repeated search/read penalty
   invalid tool schema penalty
   ```

3. Efficiency reward：

   ```text
   turns per resolved
   tool calls per resolved
   wall time per resolved
   tokens per resolved
   repeated command rate
   ```

4. `swe_filter_metric`：

   ```text
   3 resolved
   2 patch applies and useful public test evidence
   1 patch applies
   0 normal model failure
   -1 invalid / timeout / infrastructure / severe no-progress
   ```

5. Reward audit：

   ```text
   reward_component
   evidence_ref
   visibility_class
   oracle_used=false for process reward
   reward_only_used=true only for terminal reward
   ```

6. 数值边界和权重 schedule 必须在执行计划中固定，建议第一版采用保守口径：

   ```text
   terminal_reward：主导项，建议 resolved=1.0，trusted rejected=0.0 或负向小分，invalid/infrastructure 不训练
   process_reward_per_chunk：建议限制在 [-0.10, +0.10]
   process_reward_episode_sum：必须 capped，不能超过 terminal reward 主导地位
   efficiency_reward：只在 resolved 或明确 patch progress 时允许正分
   overlong_penalty：只作为长度控制，不应压过 terminal reward
   early schedule：process / efficiency 权重更小，随着工具格式稳定后再提高
   ```

7. 增加 reward hacking 负例 fixture：

   ```text
   重复运行无关测试
   制造大量无效读文件
   写 no-op patch
   写只影响测试的 patch
   生成不可 apply patch
   运行公开测试但不修改源码
   通过 shell 试探 hidden path
   ```

出口验收：

1. reward builder 不读取 gold patch 或 hidden test 内容来生成 process reward。
2. terminal reward 可以使用 hidden verifier，但只能留下 opaque ref。
3. trainable negative 与 invalid sample 分类稳定。
4. all-zero rescue candidate 可以被识别但不能绕过 formal batch validator。
5. process reward 明确禁止读取 `relevant_files`、`modified_files`、`expected_output_json`、`FAIL_TO_PASS`、`PASS_TO_PASS`、`test_patch` 和 `gold patch`。如果需要判断“相关文件”，只能来自模型可见的 traceback、公开测试失败、公开 import 路径、搜索命中、已读文件和当前 diff。
6. adversarial negative fixture 不能通过堆工具调用、堆测试命令、no-op patch 或 hidden path 探测获得正向 process reward。

### Stage 19.5：`run_episode` 产物、旧 CLI 和 offline export 桥接

目标：把在线训练主线和旧评测 / 离线导出主线的事实来源统一起来。短期不需要大规模迁移旧 `run_task(...)`，但必须证明 `RepoHarnessRuntime.run_episode(real_episode)` 的产物可以被测评、SFT、rejection export 和 audit 工具稳定消费。

主要改造：

1. 定义 `run_episode(real_episode)` run directory 的最低 export 契约：

   ```text
   transcript / messages
   events
   artifacts manifest
   final patch
   verifier summary
   reward metadata projection
   timing summary
   resource summary
   TrainingView
   generation records
   partial checkpoint / resume facts，可选
   ```

2. 增加实验性 bridge：

   ```text
   run_episode result -> SFT export
   run_episode result -> rejection / preference export
   run_episode result -> offline audit report
   run_episode result -> old run directory inspector compatible projection
   ```

3. 保持旧 `run_task(...)` 路径兼容，但不能让它成为训练数据主路径的另一个事实来源。
4. 同一 episode 的 reward、verifier、artifact、timing、resource、TrainingView 在两条链路中不能产生互相矛盾的解释。

出口验收：

1. 一个 `run_episode(real_episode)` 样本可以导出 SFT 样本，并通过 visibility gate。
2. 一个失败但可信的 trainable negative 可以导出 rejection / preference 数据。
3. old CLI inspector 能读取 bridge projection，或明确给出不支持字段的结构化说明。
4. 不迁移旧 `run_task(...)` 主实现，不影响正在进行的 SWE-bench 评测工作。

### Stage 20：Warm start 轨迹生产和 SFT / rejection 数据导出

目标：在正式 RL 前，让模型先学会当前 harness 的 action grammar、工具协议、提交协议和基础修复闭环。

主要改造：

1. 使用强模型或当前最好模型生成 300 到 800 条高质量成功轨迹。
2. 过滤条件建议：

   ```text
   resolved=true
   patch_applies=true
   has_run_relevant_public_test=true
   invalid_tool_calls=0
   no hidden leak
   turns <= configured limit
   tokens <= configured limit
   ```

3. SFT export 只训练 assistant action tokens。
4. tool observation、summary、external compactor output 不做 loss。
5. 同步导出 rejection / preference 数据：

   ```text
   success trajectory
   failed but useful trajectory
   invalid trajectory
   infrastructure failure excluded
   ```

   其中 `invalid trajectory` 只能进入诊断导出或格式失败分析，默认不能进入 SFT、preference、policy loss 或 reward training。这样可以避免与前面“invalid / infrastructure 样本不训练”的规则冲突。

出口验收：

1. SFT 样本通过 visibility gate。
2. 轨迹可回放到相同 final patch。
3. 每条 SFT 样本可追溯到 task manifest、run artifact、verifier summary。
4. Stage 20 是 Stage 21 DAPO 的硬前置门槛：工具格式解析率、bash 使用质量、隐藏信息不泄漏、replay 成功率和 export visibility gate 必须达标。

### Stage 21：Token-level DAPO baseline

目标：先建立一个简单、可信、可对照的 DAPO 主线，再进入 chunk-aware 版本。

主要改造：

1. Group sampler：

   ```text
   每个 prompt 采 n 条 rollout
   记录 group_id
   记录 sample_id
   记录 policy_version
   ```

2. DAPO group filtering：

   ```text
   过滤全成功 / 全失败 group
   保留一小部分 all-zero rescue group
   使用 swe_filter_metric 而不是单纯 acc
   ```

3. Length control：

   ```text
   max turns
   max model calls
   max tool calls
   max bash seconds
   repeated search/read cap
   overlong penalty
   ```

4. Formal batch builder：

   ```text
   route=verl
   response_logprobs exists
   generation_records all route=verl
   rollout_policy_version
   adapter_version
   min_global_steps
   max_global_steps
   old_logprobs_source=rollout
   visible_context_hash
   no overflow
   reward finality complete
   staleness within threshold
   ```

5. 最小 refill / resample 边界：

   ```text
   明确 owner：RepoHarness batch collector 或 repo_harness_verl trainer helper
   目标 valid sample 数
   最大 rollout attempt 数
   最大 wall time
   任务去重规则
   insufficient valid batch 时 fail-closed，不能静默用不足样本训练
   ```

6. 异步分布漂移基础监控：

   ```text
   old / new logprob mismatch
   adapter_version bucketed stale ratio
   policy_version bucketed stale ratio
   bounded queue age
   windowed FIFO acceptance rate
   stale sample filtered count
   ```

7. Remote smoke：

   ```text
   7B / 8B 小模型
   小任务池
   token-level DAPO
   只证明训练稳定、样本分类正确、指标可观测
   ```

出口验收：

1. policy loss 消费样本全部可回查。
2. invalid / infrastructure / stale / hidden leak 样本不进入 policy loss。
3. 每个 trainer step 有 valid sample count、rejected count、diagnostic count。
4. DAPO group filtering 之后的补样、最大尝试次数和 insufficient valid batch 处理都有结构化报告。
5. 异步样本的 staleness、policy_version 和 adapter_version 分桶统计可解释。

### Stage 22：BS-Chunk-DAPO batch builder 和 loss 接入

目标：实现主算法最有价值的部分：chunk-level reward-to-go、trajectory-equal normalization 和 chunk-equal loss。

主要改造：

1. Chunk reward-to-go：

   ```text
   G_chunk_k = local_process_reward_k + future_process_rewards + terminal_reward
   ```

2. Trajectory-equal group normalization：

   ```text
   在同一个 prompt group 内归一化
   长轨迹不能因为 chunk 多而支配 mean/std
   每条 episode 在 group normalization 中权重相同
   segment 拆分后不能把同一个 logical episode 当成多个独立 rollout 破坏 group 统计
   ```

3. Chunk-equal loss：

   ```text
   chunk_loss = mean(token_loss inside chunk)
   episode_loss = mean(chunk_loss)
   batch_loss = mean(episode_loss)
   ```

4. Segment-equal loss：

   ```text
   logical episode 被拆成多个 segment 后，
   每个 segment loss_weight = 1 / num_segments
   ```

5. verl 接入：

   ```text
   DataProto non_tensor_batch 记录 chunk metadata
   tensor batch 或 meta_info 记录 chunk offsets / advantages / weights
   trainer hook 或 reference/verl patch 接入 chunk-aware loss
   ```

出口验收：

1. token-level DAPO 和 chunk-aware DAPO 在同一任务池上可对比。
2. chunk 数不同的 trajectory 不会造成 loss 权重偏置。
3. tool observation token 保持 `loss_mask=0`。
4. chunk advantage 与 generation record token 范围一致。

### Stage 23：训练观测、refill / resample 和实验面板

目标：把训练从“能跑”变成“能解释、能调参、能复现”。

主要指标：

```text
trainer_idle_ratio
rollouter_idle_ratio
valid_samples_per_minute
rejected_samples_per_minute
stale_samples_processed
rollout_corr/kl
log_ppl_abs_diff
chi2_token
old_new_logprob_mismatch_p50/p95
adapter_version_stale_ratio
policy_version_stale_ratio
bounded_queue_wait_seconds
windowed_fifo_drop_count
partial_checkpoint_ratio
resume_success_rate
policy_loss_valid_sample_ratio
rollout_tokens_per_second
prefill_seconds
decode_seconds
prefix_cache_hit_rate
GPU utilization
actual_prompt_tokens_p50/p95
actual_response_tokens_p50/p95
padded_token_ratio
loss_mask_token_ratio
turns_per_resolved
tool_calls_per_resolved
bash_seconds_per_resolved
tokens_per_resolved
invalid_tool_rate
repeated_search_rate
empty_edit_rate
public_test_run_rate
official_verifier_health_rate
gold_healthcheck_pass_rate
noop_healthcheck_fail_rate
proxy_official_disagreement_rate
permission_false_positive_rate
patch_hygiene_filtered_file_count
```

主要改造：

1. 明确 refill / resample 所有权。
2. 设定每个 batch 的目标 valid sample 数。
3. 设定最大 attempt、最大 wall time、任务去重规则。
4. insufficient valid batch 必须结构化失败，而不是静默训练不足样本。
5. 每次训练 run 生成可机器验收的 experiment bundle。

出口验收：

1. 训练曲线和样本质量报告可自动生成。
2. 可以解释一次训练的主要瓶颈在模型推理、工具、verifier、workspace、reward 还是 padding。

### Stage 24：7B / 8B 中等规模实验

目标：用成本可控的模型验证训练方法是否有信号。

建议实验：

```text
A：SFT warm start only
B：SFT + token-level DAPO
C：SFT + BS-Chunk-DAPO
D：SFT + BS-Chunk-DAPO without process/efficiency reward，可选
```

默认不要同时加入太多新算法。这里的目标是证明：

1. chunk credit assignment 是否改善 sample efficiency。
2. process / efficiency reward 是否改善工具行为。
3. 训练后是否降低 invalid tool rate、重复搜索率、空编辑率。
4. resolved-rate 是否在 held-out dev 上有提升。

出口验收：

1. 固定 dev 集上有可复现对比。
2. 每个实验有相同数据边界、相同 verifier 口径、相同模型初始化说明。
3. 失败样本有结构化 case study。
4. 指标必须数字化，不能只写“有提升”。建议最低报告：

   ```text
   resolved_rate_delta_vs_token_dapo
   tokens_per_resolved_delta
   timeout_rate_delta
   invalid_tool_rate_delta
   repeated_search_rate_delta
   empty_edit_rate_delta
   proxy_official_disagreement_delta
   public_test_run_rate_delta
   ```

   Stage 24 的通过标准可以先是“有统计可解释的正向信号”，不要求一次训练就达到最终分数目标。
5. Stage 24 至少记录随机种子、任务采样种子、模型初始化、训练步数和重复运行计划。如果预算不足以多次完整重复，必须提供 bootstrap confidence interval 或等价的不确定性说明，避免把单次训练波动误读成算法提升。

### Stage 25：14B LoRA 或正式目标模型实验

目标：进入更接近最终论文或技术报告的正式实验。

建议默认：

```text
Qwen2.5-Coder-14B-Instruct
LoRA r=64 或用户确认的等价配置
8 * 96GB GPU 或等价资源
SFT warm start
BS-Chunk-DAPO 主实验
token-level DAPO baseline
少量关键消融
```

此阶段不建议再大改 harness 语义。进入 Stage 25 前，Stage 16 到 Stage 23 的数据、reward、batch、visibility、verifier、profile、evidence 都应该冻结。

出口验收：

1. 训练过程可复现。
2. 训练数据和评测数据没有 repo-level 泄漏。
3. 最终指标包括 resolved-rate、成本、样本效率和行为指标。
4. 输出完整 experiment report 和 acceptance bundle。
5. 正式实验必须给出相对 baseline 的数字化结论，至少包括：

   ```text
   相对 token-level DAPO baseline 的 resolved-rate 变化
   tokens per resolved 变化
   timeout 率变化
   invalid tool rate 变化
   proxy / official disagreement 变化
   trainable negative 消费比例
   verifier healthcheck 通过率
   ```
6. Stage 25 必须记录 seed、重复次数、任务采样方式、bootstrap confidence interval 或等价统计说明。正式报告不能只给一次训练 run 的单点结果。

### Stage 26：可选算法增强

只有在 Stage 21 到 Stage 25 基线稳定后，再考虑：

1. GSPO / sequence-level correction。
2. DrGRPO 改进。
3. learned PRM。
4. 更复杂的 IPA / chunk importance sampling。
5. 跨进程 durable resume。
6. KV cache resume。
7. context-management policy，让模型主动决定何时压缩上下文。

这些不应阻塞主线，因为主线价值已经可以由 BS-Chunk-DAPO 与 token-level DAPO 对比体现。

## 5. 需要用户决策的问题

下面这些问题无法仅靠代码检查决定，需要用户根据预算、目标和论文叙事取舍。

### 5.1 正式模型和算力目标

需要确认：

1. 正式结果是否按训练设计建议使用 `Qwen2.5-Coder-14B-Instruct + LoRA`。
2. 7B / 8B 是否只作为 smoke 和 ablation。
3. 是否确定未来主要使用 `8 * 96GB GPU`。
4. 如果 14B LoRA 的远端 weight sync 不稳定，是否接受先用 7B full training 做中期结果。

建议：

```text
工程阶段继续用 1.5B / 7B / 8B 小模型降低成本；
正式报告阶段再上 14B LoRA 或用户指定目标模型。
```

### 5.2 是否先做 SFT warm start

训练设计文档建议先生成 300 到 800 条成功轨迹做 warm start。需要确认：

1. 是否愿意使用强模型生成 teacher trajectories。
2. 是否接受 provider 成本。
3. 是否优先使用自有 harness 生成的轨迹，而不是直接混用公开轨迹。

建议：

```text
先做小规模 SFT warm start。
原因是当前工具协议和 action grammar 很具体，直接 RL 容易浪费样本在格式和工具调用错误上。
```

### 5.3 process reward 的激进程度

需要确认 process reward 是保守辅助，还是更强地塑造行为。

建议：

```text
第一版保守：
terminal reward 主导；
process reward 单 chunk 小幅度；
总 process reward capped；
效率 reward 只在 resolved 或明确有 patch progress 时正向奖励。
```

避免模型学会“跑很多看起来有用的命令”，却不真正解决任务。

### 5.4 context compaction 是自动触发还是模型可调用工具

两种路线差异很大：

1. Harness 自动触发：summary 是外部状态转换，summary token 不做 policy loss。
2. 模型主动调用 `context_compact`：这变成策略动作，需要训练模型何时压缩、如何压缩、是否压缩过早。

建议：

```text
第一版用 harness 自动触发；
先把 compressed-state segment 训练语义做正确；
模型主动 context-management 放到后续可选阶段。
```

### 5.5 完整 shell 是否进入正式训练工具集

另一个 worktree 的证据说明，完整 shell 对 SWE 任务非常重要。但完整 shell 也带来泄漏和污染风险。

已确认口径：

1. 正式训练主线必须有模型可见的 shell 类工具名，第一版固定为 `execute_bash`。
2. `execute_bash` 在 Stage 16A 中只代表安全最小 shell 面，不代表已经开放完整 persistent shell。
3. 完整 shell 语义仍然是正式 SWE agent 训练最终需要的能力，但它必须放在 Stage 16B 及之后，通过 persistent diagnostic session、路径脱敏、共享依赖只读、runtime-private 隔离和证据验收后再逐步启用。
4. 旧版受限 `bash` 或 `safe_argv` 诊断命令执行器不足以支撑正式 SWE agent 训练；但是直接把所有真实 shell 命令加入 `execute_bash` allowlist 也不安全。
5. Stage 16A 的模型默认应该学习 Claude Code 式工具分工：读、搜、改、写走结构化工具；测试、构建和复杂诊断才逐步走 shell 或受控 test routing。
6. shell-only scaffold 可以作为对照实验，但第一版正式训练主线仍建议同时保留结构化 `read_file`、`grep`、`list_files` / `glob_files`、`edit_file`、`git_diff`、`run_public_tests` 和 `finish` / `submit`。

建议：

```text
主线工具集使用：
read_file
grep
list_files / glob_files
edit_file
git_diff
execute_bash，也就是 Stage 16A 的安全最小 shell 面
run_public_tests，Stage 16C 之前至少需要设计清楚，正式训练前应进入主线
finish / submit

shell-only scaffold 作为对照，不作为第一版正式训练主线。

Stage 16A 的 execute_bash 必须禁止：
  Git 历史访问
  hidden verifier / run directory / gold patch / test patch / official selector 访问
  共享依赖环境写入
  越界路径访问
  隐藏路径、runtime-private 路径、环境路径枚举

Stage 16B 之后的 persistent shell 仍然必须继承这些禁止项，并额外证明同题复用、跨题隔离、timeout invalidation 和 cleanup。
```

### 5.6 官方 verifier 与 proxy verifier 的成本取舍

正式 reward 越接近官方 verifier，成本越高；proxy verifier 越快，噪声越大。

已确认口径：

1. 训练中需要尽可能保证吞吐，不能要求每条 episode 都跑完整官方 verifier。
2. 训练中使用可信 proxy verifier 和 healthcheck。
3. 关键 dev checkpoint 周期性跑官方 verifier，用来校准 proxy verifier 是否偏离。
4. 最终结果用官方 harness 或官方 evaluator 作为权威判定。

这里的 proxy verifier 指训练期间使用的较快、近似、成本更低的验证器，例如：

```text
patch 是否能 apply
目标公开测试或自写复现是否通过
一小组公开 smoke tests 是否通过
import / lint / type check 是否通过
内部 verifier worker 在当前训练环境中的结果
```

proxy verifier 可以为在线强化学习提供高吞吐 reward 信号，但不能伪装成最终官方评测结论。

建议：

```text
训练中使用可信 proxy + healthcheck；
关键 dev checkpoint 周期性跑官方 verifier；
最终结果用官方 harness。
```

还需要确认：SWE-bench Verified 是否使用官方 instance image 和官方 evaluator 作为最终 reward finality。如果使用 proxy verifier 训练，报告里必须区分：

```text
proxy accepted
official accepted
proxy / official disagreement
gold healthcheck failed
no-op healthcheck unexpectedly resolved
```

### 5.7 R2E-Gym oracle 字段是否完全不进入 SFT

建议默认不进入。`relevant_files`、`modified_files`、`expected_output_json` 这类字段会降低任务难度，可能让训练结果不能代表真实 SWE agent。

如果要用这些字段，只建议作为单独的 oracle-hint 消融，不进入主线结果。

### 5.8 local persistent shell 是否进入远端训练

已确认口径：

1. 正式远端训练优先租用可以正常运行 Docker 的 VM、裸机或完整机器。
2. local filesystem-persistent shell 只保留为开发、诊断和紧急 fallback，默认不能作为正式训练执行后端。
3. Docker persistent shell 负责正式训练中高权限 diagnostic session 的底层隔离。
4. 跨 episode 复用的共享依赖环境仍然是正确设计方向，但必须只读。
5. 如果无法证明共享依赖环境只读边界，不应该拒绝 Docker backend；应该拒绝“共享依赖环境复用模式”，退回每个 episode 私有环境或更保守的运行模式。

建议：

```text
Docker persistent shell 优先用于本机、可 Docker 化评测和正式远端训练；
Stage 16B.5 验证远端 Docker-capable backend，而不是继续深挖 local_process 隔离；
共享依赖环境负责快，episode 私有 overlay 负责真实交互和可写持久化；
模型不能把临时安装、卸载或文件写入跨 episode 共享环境；
不能证明共享环境只读时，禁用共享环境复用，而不是禁用 Docker backend。
```

### 5.9 是否现在冻结 dev / final split

需要确认：

1. 是否现在冻结第一批 R2E-Gym / SWE-Gym dev split。
2. gold / no-op healthcheck 后被剔除的任务是否从分母中移除，还是保留为 environment_or_oracle_invalid 诊断样本。
3. SWE-bench Verified 是否只用于最终评测和少量 checkpoint 校准。

建议：

```text
先冻结小规模 dev-fast / dev-real；
healthcheck 不通过的任务不进入训练分母；
保留诊断记录，但不把它们当作模型失败训练。
```

### 5.10 是否把旧 CLI / offline export 统一进 run_episode 主线

当前在线 RL 主线已经走 `run_episode(real_episode)`，但旧的评测和离线导出仍主要沿用 `run_task(...)` 和历史 run directory。

需要确认：

1. 是否在 Stage 16 到 Stage 20 期间同步推进旧入口统一。
2. 还是先保持双入口，等训练主线稳定后再迁移。

建议：

```text
短期保持双入口；
先定义 run_episode 产物如何满足旧 export 契约；
再新增实验性 run-episode CLI；
最后迁移 run-task / run-batch。
```

Stage 16 不应同时大规模迁移旧 `run_task`。短期只做 `run_episode` 产物兼容和必要桥接，避免冲击当前已经跑通的 Stage 15.2 异步链路。

## 6. 建议立即开始的下一步

建议下一步不是直接写大规模训练脚本，而是先写：

```text
Stage 16A 执行计划：工具动作空间与防泄漏边界
```

Stage 16A 的执行计划应该明确：

1. 从另一个 worktree 合入哪些文件或等价能力。
2. 哪些改造只用于诊断，哪些进入正式 RL 主线。
3. Stage 16A 的 `execute_bash` 只完成安全最小 shell 面，而不是完整 persistent shell。
4. 结构化工具优先原则如何写入正式 scaffold，避免模型继续用 `cat`、`sed`、`find`、裸 `grep`、裸 Python 文件读取替代已有工具。
5. `execute_bash` 的 visibility、path leak、Git history、防 evaluator-only 泄漏测试。
6. 工具可见注册表和实际执行注册表如何保持一致。
7. 哪些旧 `run_task` 路径先不动，避免影响现有 SWE-bench 测试。
8. `run_public_tests`、`python_probe`、task-declared project command 是 Stage 16A 后续需要补的能力，不应通过无限扩大 `execute_bash` allowlist 变相实现。

Stage 16A 通过后，再依次进入 Stage 16B、Stage 16B.5、Stage 16C、Stage 16D、Stage 16E 和 Stage 16.5。Stage 16B.5 通过前，不建议扩大正式远端训练；Stage 16.5 代表性诊断通过前，不建议扩大正式 RL 训练。因为如果工具动作空间、远端 Docker 执行后端和验证环境还不稳定，后续算法实验会把 harness 噪声误当成算法信号。

## 7. 综合复核意见摘要

本路线综合了三类复核意见：

1. 训练算法设计复核：
   - 确认主线应围绕 BS-Chunk-DAPO / Compressed-State Chunk-DAPO。
   - 强调必须支持 chunk、segment、context compaction、process reward、efficiency reward、DAPO group filtering 和 staleness gate。

2. 另一个 worktree harness 诊断复核：
   - 确认当前 harness 的 bash / shell 能力、公开测试入口、持久执行环境、Git 历史防泄漏、patch hygiene、官方 verifier 健康门槛必须进入后续训练主线。
   - 建议把这些改造视为训练扩大前的基础设施前置条件。

3. 当前 Stage 15 链路复核：
   - 确认当前代码已经具备 asynchronous episode、partial checkpoint、same-process resume、fully async bridge 和验收器能力。
   - 同时提醒短程 smoke 不等于正式训练平台，还需要数据、reward、batch、profile 和远端运行产品化。

综合判断：

```text
Stage 15.2 之后可以认为异步链路基本打通；
Stage 16 之后的主线应转为实验设计驱动；
最先补的是 harness 动作空间和验证环境，
然后是数据边界、chunk/segment schema、reward builder、DAPO baseline、BS-Chunk-DAPO 主算法和正式评估包。
```
