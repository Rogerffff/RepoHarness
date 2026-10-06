# R2E actor 接线独立追踪（2026-09-25）

角色：Production Tracer / Falsifier。仅审任务面 → 正式编排 → 镜像 / lease → 评分面，以及 8 题 devcheck 对这条链的覆盖。未修改实现、维护测试或原始 evidence；未运行 SSH、Docker、模型或实际评分。当前工作树的相关文件 SHA-256 见 [probe_actor_binding.json](probe_actor_binding.json)。

**结论：任务面两侧按派生镜像 ID 接线成立，旧 orange3 覆盖条目确实已被拒绝。主 finding 为 P2：修订只绑定了通用安装步骤名，没有绑定批准的依赖。另有一个非阻塞的 P3 简化项：覆盖表摘要校验与解析分两次读文件，在输入并写时可以消费另一份内容。它们均不是“8 题现有运行已经出错”的证据。**

保存的 8 题启动证据可重建为 8 次真实 CC 2.1.205 运行、47 条 Bash 命令（含 8 条 R2E 预检），全部完成。它们证明本批派生环境和正式启动组件在桩端点下可用，不能提升为完整 `BringupService → RolloutOrchestrator → grader → miles` 或 Qwen adapter 已实测。

## 1. 正式调用链与所有权

```text
miles rollout actor 进程
  Rh2MilesGenerateFn.__call__                         generate_fn.py:139–142
    ensure_fa_started → BringupService.get            bringup.py:3061–3068
      PreparedTaskFace.load                          bringup.py:1394–1413
        prepared manifest / rollout / host grading 校验
        load_overlays_input(path, sha)               prepared_task_face.py:454–470
        overlay_binding_mismatch                     prepared_task_face.py:491–508
        RolloutTaskSpec：派生 image ID、local_build、.venv
      attempt assignment → 对应训练 / 评测 face      bringup.py:2039–2078
      RolloutOrchestrator(task_resolver, grading_spec_resolver)
                                                      bringup.py:1693–1701
        _prepare_workspace                           generate.py:3875–3928
          image inspect → SandboxLease.image_digest  generate.py:4779–4803
          profile.docker_run_args(image=task.image)   generate.py:4859–4861
          血缘 → sanitize → init → public bundle / bash_env → prelaunch
                                                      generate.py:4897–5021
          baseline census → activation check         generate.py:3905–3947
        ClaudeCodeDriver.run(env_injections)          generate.py:2945–3006
        评分取数按相同 assignment，惰性一次           generate.py:2880–2887
          face.grading_spec：重验 host view，R2E spec
          同一派生 image ID / image_local_build_id   prepared_task_face.py:575–612
```

- `PreparedTaskFace` / overlay 字典由每个 rollout actor 进程内的 `BringupService` 持有；本次新增数据在构造时加载，执行期间从内存消费。未增加跨线程可变 owner。
- 容器与网络生命周期仍属于既有 orchestrator / audit；lease 在 `docker run` 前建立。镜像不可用在 inspect 阶段报 `rollout_image_inspect_failed`，不会回退来源镜像。
- 两侧 `image_local_build=True` 会跳过 registry RepoDigests 检查（`generate.py:5161`、`manager.py:2465`）。当前 R2E 工厂给的是完整 `sha256:<64hex>` image ID，而非可重指 tag，因此跳过 registry 检查本身不是镜像漂移 finding。lease 的实际 ID进入 baseline，评分面 local-build 资格身份也使用该 ID。
- `PreparedTaskFace.load` 未显式传覆盖参数时读 `RH2_IMAGE_OVERLAYS_PATH` / `RH2_IMAGE_OVERLAYS_SHA256`；路径与摘要缺一拒绝。缺 R2E 条目、来源镜像错配、隐藏树摘要 / 位置错配、配方关键 facts 缺失均在 face 构造阶段拒绝，不成为候选 reward=0。
- 本地 CPU 使用当前真实摄入产物与 `derived7` 的真实 orange3 覆盖条目，经环境变量调用 `PreparedTaskFace.load`，实际得到两侧同为 `sha256:f27e31c6…`、解释器前缀 `/testbed/.venv`；公开 payload 保留来源镜像记录。详见 [探针结果](probe_actor_binding.json)。

## 2. Finding A1：修订依赖绑定的是安装器名称，不是批准的 SciPy 配方（P2）

**标签：`production_reachable`。** 触发配置为正常 `build_r2e_derived.py --env-pins <文件>` 输入里，该题仍用 `env_v2.sh`，但 pins 指向其它包或其它版本。无需改代码、伪造覆盖表或放松 schema。

- **当前行为 / 位置**：`environment_overlay.py:49–54` 仅以 `component in recipe_id` 判定；表项 `:40` 把 `r2e-mr-020` 映射成 `+env_v2`。`build_r2e_derived.py:477–499` 的 recipe ID 只由步骤名派生，实际 pins 内容只进入另一个 `recipe_sha256`；这个摘要没有参与 `overlay_binding_mismatch` 的修订要求校验（`prepared_task_face.py:399–408`）。
- **违反的不变量**：mr-020 的两个 PASSED 期望与已批准的 SciPy 1.5.4 环境配套。`env_v2.sh` 是通用 wheel 安装器，其版本号表示读元数据方式兼容 Python 3.7，不能代表 SciPy 1.5.4（`env_v2.sh:2–12,59–70`）。
- **证据 / 复现**：真实 `build_one` CPU 探针使用仓库现存 hypothesis 6.24.1 的 universal wheel、URL 和 sha，仅把条目交给 orange3 并选择 `env_v2.sh`。`load_env_pins` 接受，材料 guard 返回 None，构建抵达第一条 Docker inspect。正确 SciPy 配方和这个错误配方的 `recipe_id` 都是 `r2e_derive_v1+env_v2`，内容摘要分别为 `51227719…`、`0fd613f3…`。不给环境步骤的负控则在 Docker 前被拒。结果见 [probe_actor_binding.json](probe_actor_binding.json)；输入在 [wrong_package_pins.json](wrong_package_pins.json)。
- **探针边界**：未构建错误镜像，不能声称实测“错误镜像构建成功”。源码后续核对只验证安装后的版本等于该输入自己的 pins（`build_r2e_derived.py:558–565`），没有再次核对 SciPy 要求；隐藏树、git、解释器等检查也不核对该依赖。因而这是当前配置入口的缺口，不是任意改 `recipe_id` 的伪造测试。
- **影响**：若误把其它 `env_v2` 配方给该题，镜像可保留来源的 SciPy 1.7.3，而后续正常产出的 overlay 仍满足同一字符串 guard；回放与正式 actor 共用这个判据。已有上一轮真实日志证明来源环境配 mr-020 的 gold 为 11/13、reward 0，批准环境为 13/13、reward 1。当前 `derived7` 和本轮 devcheck 确实是 SciPy 1.5.4，未发现它们发生这种错配。
- **建议分期 / 最小修复**：在关闭“mr-020 环境已绑定”这项之前补齐；无需扩成依赖状态机。把批准的配方内容摘要或明确依赖事实作为修订要求，构建与消费共用。若允许多种等价配方，显式列出批准集合，不能把任意 `+env_v2` 当成等价。owner 建议为 B 线环境覆盖生产者；A 线核共用消费点。
- **修复验收**：当前真实 `derived7` 通过，旧 `r2e_derive_v1` 拒绝；`env_v2 + hypothesis`、`env_v2 + 错误 SciPy 版本` 在构建前拒绝，消费端也拒绝对应不符摘要；无该修订的既有 numpy `+env_v1` 不受影响。

这是配置漂移风险，合理频率未知，不升 P0/P1。修复应只拒绝与已批准材料不配套的环境，在 rollout 前失败；不能将其转成候选 reward=0 或样本缺失后继续补采。

## 3. A2：覆盖表校验的字节不是实际解析的字节（P3，非阻塞简化项）

**标签：`production_reachable`，CPU 已在真实 `PreparedTaskFace.load` 做确定性交错；未观察当前远程运行发生并写。**

- **当前行为 / 位置**：`prepared_task_face.py:465–470` 用 `Path(path).read_bytes()` 校验外部 SHA，之后调用 `load_environment_overlays(path)`；后者在 `environment_overlay.py:96` 重新 `read_text()`。两次打开之间，构建 / 同步进程可以替换文件。当前 `build_r2e_derived.write_overlays` 本身就会整文件重写（`:633`），其构建目录锁不覆盖 actor 读取。
- **违反的不变量**：调用方提供的外部摘要应绑定最终选用的 overlay 内容与派生镜像，而不是只绑定一个未被解析的先前快照。
- **证据 / 复现**：使用现存 `derived6` 与 `derived7` 的真实 orange3 条目，所有字段保持原样。传入 A 的摘要，在第一次 read 返回后完整替换审查目录副本为 B。真实 face 构造成功，并选用了 B 的 `f27e31c6…`，而外部摘要绑定的 A 是 `2798313d…`。两份条目均满足当前静态互检。详见 [probe_overlay_read_race.py](probe_overlay_read_race.py) 和 [结果](probe_overlay_read_race.json)。
- **影响**：单次启动可以静默选择与作业配置摘要不符的镜像。若所有 overlay 文件都先冻结且启动期间不可替换，不会触发；本批 8 题没有这个竞态的观测证据。
- **建议分期 / 最小修复**：当前按冻结快照启动时不触发，不作为本轮阻塞项；未证明实际作业会同时运行覆盖表生产者与消费者。可顺手直接解析刚校验的那份 bytes，或在将来允许消费可更新的构建目录前处理；不需加锁、重试或长期状态 owner。也不要通过“再次比较当前文件 SHA”形成新的读取窗口。
- **修复验收**：相同交错下只能选用已验证的 A，或明确拒绝；绝不能成功返回 B。保留空行处理、重复 task_id 拒绝和 schema 校验。正常输入无新增轨迹拒绝和热路径开销。

## 4. 8 题 evidence 与 devcheck 覆盖边界

[existing_evidence_audit.json](existing_evidence_audit.json) 逐题保存了原始文件 SHA、重算的 CC 事件 / 命令数量、镜像 / HEAD / profile / 激活 / 预检事实；[重建脚本](audit_existing_evidence.py) 只读原证据。

| 题（前缀） | Bash 条数，含预检 | recipe | 原始证据结论 |
| --- | ---: | --- | --- |
| aiohttp 61833518 | 6 | derive_v1 | 已核对 |
| coveragepy 5dbbe143 | 5 | derive_v1 | 已核对 |
| numpy 18b7cd9d | 6 | derive_v1 | 已核对 |
| orange3 22e98f8f | 6 | derive_v1 | 已核对 |
| orange3 9b5494e2 | 6 | derive_v1+env_v2 | 已核对 |
| pandas 32dd55cb | 6 | derive_v1+material_v2 | 已核对；见下方激活检查说明 |
| pillow 2b061b68 | 7 | derive_v1 | 已核对 |
| scrapy 9a15fcf8 | 5 | derive_v1 | 已核对 |

共同支持的事实：真实 CC init 版本 2.1.205；Bash tool 数等于命令清单数；无未运行或超时命令；CC exit 0、有 result 事件；`message_start` 数与桩端点请求计数一致；实际容器 image / spec / overlay ID 一致；HEAD 等于公开 base；agent UID 54321；2 CPU / 4 GiB；激活核查和 R2E 三项预检通过；保存的清理记录无容器 / 网络残留。没有把公开 pytest 的非零 rc 或失败测试算作启动链失败。

**pandas 的 false check 不构成安全失败，也不要求否定“8 题激活文件不可写”。** `attempt.json.checks.bashenv_denied_for_agent=false` 来自 `acceptance_startup_2.py:346` 在 CC 工具输出里搜索标记，而 pandas 命令清单没有那条标记。该题 `orig/prelaunch.json` 仍有 `ACTIVATION_WRITE=DENIED`、`ACTIVATION_STAT=0:644`；生产 `sandbox_profile.py:1221` 以 agent 身份实际执行追加写入探针。因此是 8 题 prelaunch 实测不可写、7 题另在 CC Bash 命令层复测，不能写成 8 题均在后者复测。

`r2e_devcheck.py:52–57,81–94` 使用真实 `PreparedTaskFace.load`，然后临时替换辅助 runner 导入的 `rollout_spec_from_view`。`acceptance_startup_2.py:211–254` 自行串起正式组件，`:299–301` 调真实 `ClaudeCodeDriver.run`。这不是 `RolloutOrchestrator.generate`：

| 环节 | 保存的 8 题是否覆盖 |
| --- | --- |
| prepared + overlay 静态互检、两侧 spec 选择 | actor rollout spec 真实加载；评分 spec 由本次 CPU 探针核对 |
| profile 容器、relay / 网络、sanitize、init、激活、prelaunch、CC driver | 是，复用正式函数 |
| 正式 assignment / service bootstrap / lease owner | 否；devcheck 自行装配 |
| 血缘 probe、正式 baseline census / frozen delta / grading queue | 未走完整正式顺序；8 题证据不能代替这些环节 |
| R2E preflight | devcheck 注入第一条 CC 命令；正式 `generate.py` 仍未接入，作者已明确登记 |
| 真正发给 CC 的题面与 public bundle 物化 | devcheck 用固定 prompt；不能据此声称正式题面已经 CC 验证 |
| Qwen adapter、count_tokens、提醒 / EOS / 溢出、模型求解能力 | 否，作者已明确未测；不据此报 bug |
| formal grader 与真实 reward | 此 8 题 devcheck 不证明；独立回放证据另算 |

R2E 预检尚未进入 formal generate 是已登记的补验 / 接线项；现存批准镜像已由构建和此开发验证证明通过，不能仅凭“少一条重复预检”声称当前镜像已泄漏。已登记的 root PATH 安全修复（infra 09-25 的 E2b，R2E 正式运行前修）也不在本子任务重复展开。

## 5. Ray 输入运输与停止条件

仓内唯一现成 GPU `rh2/experiments/miles_gpu_spike/launch.sh:394–420` 显式生成 Ray `env_vars`，没有新增 overlay 两变量；它也没有 prepared 题包的新变量。**这不是本次新增的当前 actor bug**：第五组 README §6.2 已决定实际启动命令随八卡方案重写，不沿用旧 spike 默认值。`bringup.py:1394–1413` 只要求最终 actor 进程能读到那对变量；本地 CPU 已证明该消费点可用。

建议把实际 Ray 作业中两变量、文件可达性和本机 image ID 可用性留给启动方案的核验，不能说“环境变量在 driver shell 设置过”就证明到达 rollout actor。这里没有实测 Ray 传播，也没有批准新增 launcher 工程。

本次子审停止于 A1 的 P2、A2 的非阻塞 P3 简化项和明确的运行边界。A1 用批准的环境事实 / 内容身份绑定即可局部收口；A2 若改，用单份已校验字节解析即可。不建议继续扩展到整个 infra 状态机或任意未来 recipe 体系。已足以保留 8 题的开发条件结论、继续逐题审查；正式 R2E rollout / grader 与 Qwen 接缝仍按作者已列计划补验。

适用维度：A/D/F/G/H/E 为主（失败关闭、真实配置消费、修订与环境绑定、正式入口及证据有效性）；B/I 覆盖失败归因、拒绝范围和分期；J/K 仅检查此处是否需要新增复杂度，建议均为局部修复；C 未新增挡板；L 无新增执行期队列或热路径，本轮不重审容量；M 有逐题 artifact 可复核但不扩展新观测工程；N 核 CC 2.1.205 与来源身份，Qwen / Ray 真机兼容性明确未测。

## 6. 复跑 CPU 审查

从仓库根运行，所有写入都位于本目录；不调用 Docker / 网络：

```bash
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/actor/probe_actor_binding.py
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/actor/probe_overlay_read_race.py
rh2/.venv/bin/python -B docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_static_actor_review_20260925/actor/audit_existing_evidence.py
```

`probe_actor_binding.py` 现在每次新建 `probe_runs/<随机ID>/`，stdout 给出 `run_dir`，因此可重复运行而不删除首次证据。也可用 `--run-dir <本审查目录内的全新目录>` 固定输出位置。竞态探针默认复用首次 prepared 证据；若要接上新一轮产物，传 `--binding-run-dir <上条命令的run_dir>`。

本子任务三条脚本均完成；未新增 / 运行 pytest、skip 或 xfail。维护测试及主审的上轮修复核销由主审汇总。
