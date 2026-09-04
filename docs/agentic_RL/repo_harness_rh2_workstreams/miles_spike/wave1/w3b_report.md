# W3b 实现报告：唯一正式 rollout Docker profile + 独立 grader profile（创建期强制 + 启动前探针 + run 级记录）

日期：2026-09-04。执行依据：决策包 `miles_spike/decision_package_D2_B.md` v2（owner 2026-09-04 已批）D2-2 / D2-4；06 计划 §1.5 与 §3 W3b 行；前置清理批报告 `wave3_precleanup_report.md`（每轨迹能力事实已删）；W3a 报告 `w3a_report.md`（容器释放点、grader 评分链现状）。owner 细化原文："sandbox profile 只做启动前验证和 run 级记录，不再建立任何逐轨迹 capability eligibility"。本文同时充当本批的 implementation-notes。工作树状态：**未 commit / 未 stash**（任务书禁止）；起点 HEAD = `f450ee73`，写本文时 HEAD 已由集成者推进到 `98f730a2`（W5b 工具链落账，其 commit 注明"expected_counts 待 W3b 落地后同步"）。与 W5b agent 并行；本文只对 §0 清单负责。

## 0. 交付物清单（文件所有权内）

| 文件 | 性质 | 内容 |
|---|---|---|
| `rh2/src/repoharness2/adapters/slime/sandbox_profile.py` | **新增**（约 1800 行，含容器内脚本文本） | 两个 profile（`RolloutSandboxProfile` / `GraderSandboxProfile`）+ 参数摘要 `digest()` / `runtime_profile_digest()`；env 解析 `rollout_profile_from_env` / `grader_profile_from_env`（非法即拒）；`docker_run_args()`（唯一创建入口的参数组装，无可选安全开关）；attempt 私有 isolated 网络（`EgressSubnetPool` / `create_attempt_network` / `connect_relay_to_network` / `teardown_attempt_network`）；本 run egress relay（`start_egress_relay` / `stop_egress_relay`，纯 stdlib asyncio TCP 转发器）；容器内脚本（可信初始化、`git-sanitize`、启动前探针、加长探针、存储预算探针、git-future 探针、grader 三个脚本，首行标记 = 脚本 id）；纯核对函数 `check_rollout_inspect` / `check_rollout_probe` / `check_grader_inspect` / `check_grader_probe` / `git_sanitize_violations`；每容器一次的 `run_rollout_prelaunch_check` / `run_grader_prelaunch_check`（`PrelaunchReport`）；verify/dry-run 入口 `verify_sandbox_profiles()` + `write_runtime_profile_record()`；CLI `verify` / `list-probes` / `dump-probes` |
| `rh2/src/repoharness2/adapters/slime/generate.py` | 修改（容器创建路径 + 一处一行级盖章） | `RolloutOrchestrator(..., sandbox_profile, egress_relay, runtime_profile_digest)`：fa_formal 缺 profile → `StartupCheckError("sandbox_profile_required_in_formal_chain")`（不创建 rollout）；`_materialize_rollout_sandbox` profile 路径 = attempt 网络 → relay 接入 → `profile.docker_run_args` → 镜像 digest/血缘探针 → **git-sanitize（root）→ 可信初始化（建 agent 用户 + chown -R）** → 基线快照/bundle 写入 → **启动前核对（inspect + agent 探针）**，不过 → `FatalExecutionInfrastructureError("sandbox_prelaunch_check_failed")`；新方法 `_create_attempt_network` / `_teardown_attempt_network`；`_cleanup_container` 在容器 rm 成功后删网络；`RolloutAudit` 新字段 `runtime_profile_digest` / `egress_network` / `sandbox_setup` / `prelaunch_check`；`_MaterializedSandbox.network`；**交付面唯一改动 = `_deliver_present_member` 的两行**：`leaf_meta[RUNTIME_PROFILE_DIGEST_METADATA_KEY] = digest`（任务书允许的"接 profile digest 盖章的一行级改动"；评分/投影逻辑零改动） |
| `rh2/src/repoharness2/grading/manager.py` | 修改（`_start_container` / 租约参数 + eval 执行身份） | `GradingManagerConfig.sandbox_profile`（None = 旧参数，只给 s1_compat/单测）；`_start_container` profile 路径 = `profile.docker_run_args(... declared_readonly_binds)` + 租约 `run_as_user=candidate_exec_user` + 新 `_grader_prelaunch`（root 可信初始化 → inspect + 候选用户探针；不过 → 先删容器再抛 **`SandboxProfileViolation(BaselineIntegrityError)`** = run-halt 通道）；`_exec_bash(_checked)` 加 `user`/`home` 参数（缺省形状与之前逐字相同）；`_run_eval`：profile 在场时先 root `chown -R /testbed → 候选用户`，再以候选用户身份跑官方 eval 脚本；`_ContainerRecord.prelaunch`、`SWEGradingManager.prelaunch_checks`（有界 256）；profile 模块按需 import（模块级会经 `adapters.slime` 包 `__init__` 绕回 manager 形成循环 import） |
| `rh2/src/repoharness2/adapters/slime/bringup.py` | 修改（接线 / run 记录 / 关停） | `sandbox_profile_enabled()`（= `EXECUTION_MODE != "s1_compat"`，无 env 开关）；`__init__` 在任何资源型副作用前解析两个 profile（非法 env 启动即拒）；adapter 端口就绪后构造 rollout profile、`runtime_profile_digest`、`harness_adapter_url = http://rh2-egress-relay:18001`（`SlimeBindingConfig.adapter_url` 改用它）；grader profile 注入 `GradingManagerConfig`；`_start_sandbox_runtime()`（`_run_startup_checks` 之后、评分队列之前）：起 relay → `verify_sandbox_profiles()`（同一入口，`expect_upstream_http=True`，探针镜像 = `RH2_SANDBOX_VERIFY_IMAGE` 或任务面第一个镜像）→ 写 `ARTIFACT_DIR/runtime_profile.json` 一次 → 不过 `StartupCheckError("sandbox_profile_verification_failed")`；`async_start` 统一回滚多停 relay；orchestrator 注入三参数；`write_execution_audit_record` 加 `runtime_profile_digest` / `egress_network` / `sandbox_setup` / `prelaunch_check`；startup evidence 加 `runtime_profile_digest` / `harness_adapter_url`；关停链新步 `egress_runtime`（`container_residue` 之后：删残留 attempt 网络 → 删 relay）；`fa_formal` 挡板（`bringup.py` "fa_formal 暂禁"）**原样未动** |
| `rh2/src/repoharness2/shutdown/run_residue.py` | 修改（追加，W5a 文件，见 T1-9） | `list_run_networks` / `remove_networks`：launch trap 的清理与检查把本 run label 的 docker 网络也算残留 |
| `rh2/scripts/sandbox_probes/` | **新增** | `h7_boundary_probes.sh`（H7 runner：调同一 verify 入口）+ 9 个探针脚本副本（`dump-probes` 生成，测试断言与包内逐字一致） |
| `rh2/tests/sandbox_test_support.py` | **新增** | 测试 profile 夹具、`formal_sandbox_kwargs()`、`synthesize_inspect()`（docker run 参数 → inspect JSON 如实合成）、脚本罐头输出、`ProfileFakeState`（替身分派 + 负例旋钮） |
| `rh2/tests/adapters/test_w3b_sandbox_profile.py`（14 例）、`test_w3b_sandbox_docker.py`（14 例，@docker）、`test_w3b_bringup_sandbox_runtime.py`（4 例）、`rh2/tests/grading/test_w3b_grader_profile_docker.py`（3 例，@docker） | **新增** | 见 §9 |
| 既有测试改动 | 修改 | `test_slime_generate.py`（`FakeRolloutDocker.profile_fake` + `build_dense_chain` 对 fa_formal 注入 profile；无 oracle 改动）、`test_w1a_formal_chain.py` / `test_w1b_prepared_chain.py` / `test_w1b_group_admission.py`（fa_formal 构造加 `**formal_sandbox_kwargs()`，共 +19 行，0 新测试）、`test_w5a_shutdown_chain.py`（关停步骤清单 +`egress_runtime`，T1 oracle）、`test_w5a_run_residue.py`（桩 docker 加 `network ls/rm`） |

**未触碰**：`reference/`、`rh2/src/slime`、`contracts/`（零改动——`SandboxLease` 现有 `run_as_user` / `network_policy=allowlist` / `network_allowlist_justification` 字段足以表达，见 T1-5）、`governance/`、`adapters/miles/`、`envpack/`、`generate.py` 评分/投影逻辑（W3a 落地部分逐字未动）、lanes manifest 与 patch 表、`experiments/miles_gpu_spike/launch.sh`。

## 1. 两个 profile 参数表（本地默认值；数值归 C 校准，实际值进 run 记录）

### 1.1 `RolloutSandboxProfile`（`profile_id = rh2.rollout_sandbox_profile.v1`）

| 参数 | env（`RH2_SANDBOX_*`） | 本地默认 | docker 落法 / 核对方式 |
|---|---|---|---|
| `agent_user` / `agent_uid` | `AGENT_USER` / `AGENT_UID` | `agent` / 54321 | 可信初始化按固定 uid 预建（slime `ensure_agent_user` 之后是 no-op）；探针 `id -u` == uid、`WORKDIR_OWNER` == uid |
| `trusted_init_caps` | 固定 | `CHOWN, DAC_OVERRIDE, DAC_READ_SEARCH, FOWNER, KILL` | `--cap-drop ALL --cap-add <每项>`；inspect `CapAdd` 集合精确相等；agent 探针 `CapEff=CapPrm=0` |
| no-new-privileges | 固定 | 开 | `--security-opt no-new-privileges`；inspect 在场且无 `*unconfined`；探针 `NoNewPrivs=1` |
| `pids_limit` | `PIDS_LIMIT` | 512 | `--pids-limit`；inspect `PidsLimit`；cgroup `pids.max` |
| `cpus` | `CPUS` | 2.0 | `--cpus`；inspect `NanoCpus`；cgroup `cpu.max = "200000 100000"` |
| `memory_bytes`（swap 恒 0） | `MEMORY_BYTES` | 4 GiB | `--memory X --memory-swap X`；inspect `Memory == MemorySwap`；cgroup `memory.max` / `memory.swap.max=0` |
| `tmp_tmpfs_bytes` | `TMP_TMPFS_BYTES` | 1 GiB | `--tmpfs /tmp:size=…,mode=1777`；inspect `Tmpfs` 逐字相等 |
| `home_tmpfs_bytes` | `HOME_TMPFS_BYTES` | 256 MiB | `--tmpfs /home/agent:size=…,mode=0750,uid=54321,gid=54321` |
| `writable_layer_quota_bytes` / `require_writable_layer_quota` | `WRITABLE_LAYER_QUOTA_BYTES` / `REQUIRE_WRITABLE_LAYER_QUOTA` | 8 GiB / `0` | 要求时 `--storage-opt size=`；verify 用 `fallocate` 超额 64 MiB **实测**强制与否（`enforced=0/1/UNKNOWN_NO_FALLOCATE`）；要求而未强制 = 验证失败（见开放问题 2） |
| 网络 | 固定形态 | 每 attempt 一张 `--internal` + `gateway_mode_ipv4=isolated` 网络 | 唯一出口 relay；探针实测 |
| `egress_subnet_pool` / `egress_subnet_prefix` | `EGRESS_SUBNET_POOL` / `EGRESS_SUBNET_PREFIX` | `10.212.0.0/16` / 29（8192 槽） | 显式 `--subnet`（守护进程默认地址池只够约 30 张网络——实测第 27 张即耗尽）；`Pool overlaps` 自动换槽 |
| `relay_image` / `relay_alias` / `model_proxy_listen_port` | `RELAY_IMAGE` / 固定 / `RELAY_PORT` | `python:3.12-slim` / `rh2-egress-relay` / 18001 | relay：默认 bridge、`--user 65534:65534 --cap-drop ALL --read-only --pids-limit 64 --memory 256m(=swap)`，每 attempt 网络 `network connect --alias rh2-egress-relay` |
| `model_proxy_upstream_host/port` | bringup：`ADAPTER_PUBLIC_HOST` + adapter 实际端口 | Linux `172.17.0.1`；本机 `host.docker.internal` | relay 的转发目标；探针要求 rollout 容器**直连**它失败 |
| `internal_services` | `INTERNAL_SERVICES`（JSON：alias/upstream_host/upstream_port/listen_port） | `()` | 每项 = relay 多监听一个端口；listen_port 冲突即拒 |
| `hidden_paths` | 固定 | `("/root",)` | agent 探针 `ls`/`cat` 必须被拒 |
| `forbidden_probe_targets` | 固定 | `169.254.169.254:80`（云 metadata）、`1.1.1.1:443`、`8.8.8.8:53`、`172.17.0.1:18001`（docker0 宿主） + 上游直连 | agent 探针 `bash /dev/tcp` 3s 超时必须失败；`getent hosts example.com` 必须失败 |
| bind mount | 固定 | 零 | inspect `Binds=[]`、`Mounts` 只许 tmpfs |
| 超时 | 固定 | init 900s / sanitize 600s / probe 120s | django 官方镜像 `chown -R` 数万文件的既有经验值 |

harness 侧代理地址 = `http://rh2-egress-relay:18001`（`harness_adapter_url()`）。

### 1.2 `GraderSandboxProfile`（`profile_id = rh2.grader_sandbox_profile.v1`）

| 参数 | env（`RH2_GRADER_*`） | 本地默认 | 落法 / 核对 |
|---|---|---|---|
| `candidate_exec_user` / `candidate_exec_uid` | `USER` / `UID` | `rh2grader` / 54322 | 可信初始化预建；官方 eval 脚本 `docker exec -u 54322 -e HOME=/home/rh2grader`；探针 `id -u`；真实评分日志 `RH2_EVAL_UID=54322`（测试注入 prelude 实测） |
| `trusted_init_caps` / no-new-privileges | 固定 | 同 rollout | 同上 |
| `pids_limit` / `cpus` / `memory_bytes`（swap 0） / `tmp_tmpfs_bytes` | `PIDS_LIMIT` / `CPUS` / `MEMORY_BYTES` / `TMP_TMPFS_BYTES` | 512 / 2.0 / 4 GiB / 1 GiB | 同上 |
| `writable_layer_quota_bytes` / `require_…` | 同名 | 8 GiB / `0` | 同上 |
| 网络 | 固定 | `--network none`（deny_all，契约锁死） | inspect `NetworkMode=none`；探针 `ROUTED_IFACES=""`（`/proc/net/route` 无任何带路由接口）、全部目标 DENIED、DNS DENIED |
| bind mount | 固定 | 只许 manager **显式声明**的只读快照（`clone_from_readonly_snapshot` 模式） | inspect `Binds` ⊆ 声明集且 `:ro`、`Mounts.RW=False` |
| 不继承 agent 状态 / 不跨 attempt 污染 / 不复用活动容器 | 既有（W3a fresh grader） | — | 每次评分 fresh 容器，输入只有持久化 frozen artifact（W3a 测试已钉死） |

`runtime_profile_digest` = `sha256(canonical JSON{schema, rollout.parameters, grader.parameters})`。

## 2. 三层边界在 Docker 上的落法（本机实测事实）

实测环境：Docker Desktop 29.4.1（linuxkit 6.12，cgroup v2，overlayfs），全部 profile 探针在真实容器上跑通；以下为设计取舍所依据的实验事实（`w3b` 开工前手工实验 + 测试复现）。

1. **网络（真实阻断）**：普通 `--internal` 网络里，宿主网关（`172.19.0.1`）**仍可达**（CONNECTED），所以"仅 internal"不算证明；加 `com.docker.network.bridge.gateway_mode_ipv4=isolated` 后网桥不配地址，公网（`1.1.1.1:443`、`8.8.8.8:53`）、云 metadata（`169.254.169.254`）、docker0 宿主网关、上游直连全部 `Network is unreachable`，外部 DNS 无法解析；同网络上的 relay 容器按 IP 与嵌入式 DNS 别名可达，且 relay（另挂默认 bridge）能到达宿主侧上游服务（经 relay 的 HTTP 往返实测得到上游状态行）。每 attempt 一张网络（同一 run 的兄弟 attempt 互不可达，"环境声明的内部服务"之外没有任何对端），成本 ≈ 0.27 s/attempt（create 0.03 + connect 0.02 + disconnect 0.09 + rm 0.12）。
2. **权限**：`--cap-drop ALL` 下 root 也 `chown` 失败（EPERM），因此可信初始化需要 CHOWN/DAC_OVERRIDE/DAC_READ_SEARCH/FOWNER（建用户、chown -R、读 agent 的 0600 文件、导出）和 KILL（屏障 `pkill -9 -u agent`）；这五项只进容器 bounding set，非 root 进程 CapEff/CapPrm/CapAmb 全 0、NoNewPrivs=1，`su`（setuid 位存在但不生效）报 Authentication failure、`os.setuid(0)` EPERM；即使误用 `docker exec --privileged -u agent`，非 root 仍拿不到能力（实测 CapEff=0）。
3. **存储预算**：`--storage-opt size=64M` 在本机被**接受但不强制**（写 100 MB 成功）——只有 overlay2-on-xfs(pquota) 才真强制。所以 W3b 不假设，verify 用 `fallocate` 实测并记录（本机 `enforced=0`）；`require_writable_layer_quota=1` 时未强制即启动失败（GPU 主机由 C 决定是否要求，见开放问题 2）。tmpfs 容量限制处处生效（实测 64M）。
4. **Git**：`git-sanitize` = 删远端 → 删所有不是 HEAD 祖先的 ref（未来 tag/分支/stash）→ 删 `.git/logs` 与 reflog → `repack -a -d` + `prune --expire=now` → `fsck --unreachable --no-reflogs --connectivity-only` 自证为零，HEAD 与 `rev-list --count HEAD` 前后相等（base 之前历史保留）。小仓库实测：reset 后未来提交 `cat-file` 可找回 → sanitize 后 `cat-file`/`fsck --lost-found`/`grep -r .git`/`git show <tag>`/分支 全部找不到。真实官方镜像（`swebench/sweb.eval.x86_64.scikit-learn_1776_scikit-learn-14629`，51 MB pack、164k 对象，x86 模拟下）：repack+prune 0.66 s、fsck connectivity-only 0.36 s、`chown -R /testbed`（1480 文件）1.36 s；该镜像自身没有未来对象（`rev-list --all == rev-list HEAD`），但 `chmod -R 777` 并未覆盖全部文件（`.codecov.yml` 等非 world-writable）——非 root agent 必须 chown。
5. **hidden/grader 资产**：rollout 容器只写 public bundle（`contracts.WorkspaceHandle` 在 schema 层拒绝 private 挂载，未动）；探针核对 `/root` 对 agent 不可读、`Binds` 为空；D2-4 canary 在测试里对真实边界验证（§9 `test_private_bundle_canary_absent_from_every_model_visible_surface`）。

## 3. 探针清单与失败语义

### 3.1 每个容器一次的启动前核对（rollout：可信初始化之后、harness 之前；grader：任何评分步骤之前）

| 面 | 项 | 必需 |
|---|---|---|
| `docker inspect`（1 次） | `Privileged=false`；`CapDrop==[ALL]`；`CapAdd == trusted_init_caps`（去 `CAP_` 前缀比较）；`SecurityOpt` 含 `no-new-privileges` 且无 `*unconfined`；`PidsLimit`/`NanoCpus`/`Memory`/`MemorySwap==Memory`/`Tmpfs` 与 profile 逐字相等；`ReadonlyRootfs` 非 True；`Binds` 只许声明的 `:ro`（rollout 零）、`Mounts` 只许 tmpfs/声明 bind 且 `RW=false`；`NetworkMode` == attempt 网络（grader：`none`）且 `Networks` 恰为它；`State.Running`；要求配额时 `StorageOpt.size` 在场 | 全部 |
| 容器内探针（1 次 `bash`，rollout 以 agent uid，grader 以候选 uid，~0.1 s） | `UID` == 固定 uid；`CapEff`/`CapPrm` == 0；`NoNewPrivs=1`；cgroup `pids.max`/`memory.max`/`memory.swap.max=0`/`cpu.max`（v2；v1 路径自动回退）；`ROUTED_IFACES`（`/proc/net/route`）：rollout 恰一个非 lo 接口、grader 为空；`NET_relay=CONNECTED`（rollout）；每个禁止目标 + 上游直连 `DENIED`；`DNS_EXTERNAL=DENIED`；`HIDDEN_*=DENIED`；`GIT_REMOTES=0`、`GIT_REFLOG=0`、`GIT_HEAD` == 血缘探针 HEAD、workdir 可写且属主 == uid；`HOME`/`/tmp` 可写；`RH2_PROBE_OK=1`（探针中断即违规） | 全部 |

### 3.2 verify/dry-run 模式的加长探针（bringup 启动一次 + H7 复跑）

`rollout-trusted-init`、`git-sanitize`（探针镜像有 `/testbed/.git` 时对真实 workdir 跑并记实际值；没有则如实 `skipped`）、`git-future-probe`（容器内自造"base → 未来解法提交（唯一串）→ tag → 分支 → reset"仓库，跑同一 sanitize，判定确定：`cat-file`/`lost-found`/`grep`/tag/分支 五路都找不到，base 历史保留）、`rollout-prelaunch-probe`、`rollout-extended-probe`（`su`/`setuid(0)` 提权必须失败；经 relay 的 HTTP 往返，`--expect-upstream-http` 时要求上游状态行）、`storage-quota-probe`、`grader-trusted-init`、`grader-prelaunch-probe`、`grader-chown-before-eval`（脚本 id 清单 = `python -m repoharness2.adapters.slime.sandbox_profile list-probes`）。

### 3.3 失败语义（拒绝点）

| 情形 | 落点 | 语义 |
|---|---|---|
| 正式 profile 缺必需配置（fa_formal 无 profile / 无 relay / 无 digest；env 非法） | `RolloutOrchestrator.__init__` → `StartupCheckError`；`BringupService.__init__` → `SandboxProfileError` | 启动失败，不创建任何 rollout |
| bringup 启动验证不过（任一必需项） | `_start_sandbox_runtime` → `StartupCheckError("sandbox_profile_verification_failed")`，记录已写盘，回滚停 relay | 训练不启动 |
| 容器创建后核对不过（rollout） | `FatalExecutionInfrastructureError("sandbox_prelaunch_check_failed")`，容器与网络已清 | 不启动 harness、停止 run（既有 Fatal 分支 → `_notify_fatal_halt` → W5a 关停链） |
| 容器创建后核对不过 / 可信初始化失败（grader） | `SandboxProfileViolation`（`BaselineIntegrityError` 子类，grade() 不捕获，generate.py 既有分支转 Fatal） | 停止 run，不记 `failed_to_grade` |
| 本 run 的 relay 不存在/已死 | `FatalExecutionInfrastructureError("egress_relay_unavailable")` | 停止 run（补采无意义） |
| attempt 网络创建/接入的瞬时失败、`docker run` 失败、git-sanitize 未达标、可信初始化失败（rollout） | `SlimeBindingError`（`rollout_egress_network_failed` / `rollout_egress_relay_connect_failed` / `rollout_container_start_failed` / `rollout_git_sanitize_failed` / `rollout_trusted_init_failed`） | 既有 task-local infra 语义（missing/ABORTED，容器按 Q7 清理） |
| `chown -R /testbed` 失败（grader，候选测试前） | `GradingInfraError("grading_testbed_chown_failed")` | 评分动作故障（reward=None），不是模型负样本 |
| 资源限额触发的 OOM/timeout | 未改：仍是既有 infra/timeout 通道（不伪装 reward=0） | — |
| 容器私有路径（/testbed、/tmp、/home/agent）可写 | 不是违规（探针反而要求可写） | — |

## 4. run 级记录字段

- **`ARTIFACT_DIR/runtime_profile.json`**（一次，`schema_id = rh2.runtime_profile_record.v1`）：`run_id`、`verified_at_utc`、`probe_image`、`runtime_profile_digest`、`relay{container_name, alias, image, listen_map}`、`rollout{profile_id, digest, parameters, checks{network_and_start_seconds, trusted_init, git_future_unrecoverable, workdir_git_sanitize, prelaunch{ok, violations, inspect_facts, probe_facts, seconds}, extended, writable_layer_quota{requested, quota_bytes, enforced}}, ok}`、`grader{…同形}`、`failures`、`ok`、`adapter_url_host_side`、`harness_adapter_url`、`execution_mode`。`inspect_facts` = cap_drop/cap_add/security_opt/privileged/pids_limit/nano_cpus/memory/memory_swap/tmpfs/storage_opt/binds/network_mode/networks/mounts/config_user/config_env/running/image；`probe_facts` = 探针全部 KEY=VALUE（实际值：uid、CapEff、NoNewPrivs、cgroup 四值、接口、每个 egress 目标结果、DNS、隐藏路径、Git 状态、可写性）。
- **`startup_evidence.json`** 加 `runtime_profile_digest`、`harness_adapter_url`。
- **每 attempt execution audit**（`fa_execution_audit.jsonl`）加 `runtime_profile_digest`、`egress_network`、`sandbox_setup{network_seconds, egress_network, egress_subnet, container_start_seconds, git_sanitize{HEAD_BEFORE/AFTER, HISTORY_COUNT_BEFORE/AFTER, REFS_DELETED, REFS_REMAINING, REMOTES, REFLOG_ENTRIES, UNREACHABLE_OBJECTS, SECONDS_ELAPSED}, git_sanitize_seconds, trusted_init{AGENT_UID, WORKDIR_PRESENT}, trusted_init_seconds}`、`prelaunch_check{ok, violations, seconds[, inspect_facts, probe_facts 仅失败时]}`。
- **样本 metadata**：只盖一个键 `runtime_profile_digest`（`RUNTIME_PROFILE_DIGEST_METADATA_KEY`），在 `_deliver_present_member` 对真实交付的成员盖章；audit 记录同键供 join。**不做**每轨迹能力事实，不进 eligibility（security 维仍只判执行级事实，前置清理批语义未动）。
- grader 侧：`SWEGradingManager.prelaunch_checks`（进程内有界）+ `_ContainerRecord.prelaunch`；租约 `run_as_user = rh2grader`。

## 5. verify / dry-run 模式用法与 H7 探针脚本清单

- bringup 启动（非 s1 模式自动）：`_start_sandbox_runtime()` 调 `verify_sandbox_profiles(...)`，与下面 CLI 完全同一函数，不复制第二套规则。
- CLI（W7 远端 / H7 租期复跑）：
  `python -m repoharness2.adapters.slime.sandbox_profile verify --image <真实任务镜像> --upstream-host 172.17.0.1 --upstream-port 18001 --out <目录> [--run-id ID] [--no-grader] [--expect-upstream-http]` → 起 relay + 真实容器 → 全部探针 → `<out>/runtime_profile.json`，任一必需项不符非零退出并逐条打印 `FAIL …`；退出前清掉自己起的容器/网络/relay（本机实测零残留）。`RH2_SANDBOX_*` / `RH2_GRADER_*` 与训练 launch 用同一份 env。
- `list-probes`（id + sha256）、`dump-probes --out DIR`（落成文件）。
- H7 runner：`bash rh2/scripts/sandbox_probes/h7_boundary_probes.sh <镜像> <上游地址> <上游端口> <输出目录> [--expect-upstream-http]`；目录内 9 个 `*.sh` 是探针脚本的离线副本（`test_probe_scripts_dir_matches_package_and_cli_lists_them` 断言与包内逐字一致），执行时由 verify 入口按容器内身份 `docker exec` 注入，不要在宿主上手工跑。H7 租期只做两件事：复跑这组探针（判定确定）+ 一条真实 CC 多轮任务（同 profile，`fa_audit_only` 即可接入本 profile，见 T1-6）。本地全部已跑通；GPU 只复跑。

## 6. 本机实测的每 attempt 开销（fixture 镜像，mock harness）

`network_seconds 0.056`、`container_start_seconds 0.139`、`git_sanitize_seconds 0.099`（脚本内 0.039）、`trusted_init_seconds 0.107`、`prelaunch_check.seconds 0.096`；整个 attempt（含基线 census、屏障、导出、持久化、释放、评分桩、交付）1.55 s。真实官方镜像的 sanitize/chown 见 §2-4（x86 模拟，偏保守）。这些段没有并入 W3a 的十三段 `LIFECYCLE_SEGMENTS`（那是 W3a 所有权），单独落在 `sandbox_setup`；GPU spike 报告应把它们与 `materialize_seconds` 一起看。

## 7. T1 决策及理由

1. **T1-1 网络 = 每 attempt 一张 isolated internal 网络 + 每 run 一个 egress relay 容器。** 备选：(a) 普通 `--internal`（宿主可达，否决）；(b) 宿主 iptables（需宿主 root，Docker Desktop 上不可行）；(c) `--network none` + Unix socket 挂载（Linux 可行，macOS 不支持跨 VM socket 挂载，本地测不了）；(d) 一 run 一张共享网络（兄弟 attempt 互通，否决——"环境声明的内部服务"之外不许有对端）。relay 是本模块内 ~40 行 stdlib 转发器，不是外部服务；relay 死亡 = run-fatal（每个 attempt 的启动前探针都会发现）。它是新增的运行时组件：若 owner 认为触"引入重要依赖/服务"，请在复核时明示，我方备选是 (c) 在 Linux 上实现、macOS 只跑替身。
2. **T1-2 权限 = `--cap-drop ALL` + 五项可信初始化能力进 bounding set（而不是 `docker exec --privileged` 做初始化）。** privileged exec 给可信步骤的是全部能力（含 SYS_ADMIN、seccomp unconfined），超出需要；bounding set 里的五项对非 root 进程不可得（no_new_privs 下 setuid/文件能力不生效，实测）。inspect 精确核对 `CapAdd` 集合，多一项即违规。
3. **T1-3 grader 非 root 按"严"读：没有自动回退 root。** 候选执行用户建不出来 / chown 失败 = `SandboxProfileViolation` run-halt，由 owner 在 C 明示处理，而不是运行时按容器悄悄退回 root（那会让同一 run 的评分身份不一致）。prepared 链的 v2 eval 脚本不含官方 install 步（`render_v2_eval_script`：预构建镜像内直接 `eval_cmd`），非 root 可行；可信步骤（clean checkout、baseline 重建、delta 应用、写 eval 脚本）仍 root，候选测试前 `chown -R /testbed`。
4. **T1-4 git-sanitize 每 attempt 在容器内做（可信初始化的一步），不建"已消毒镜像"缓存。** 成本实测在秒级以内（§2-4，django 级大仓库归 C 实测）；镜像级消毒是 D2-1 口径下"等计时证据再做"的优化；也不改 envpack/trusted_prep（非本批所有权）。sanitize 失败按 task-local（其它任务不受影响）。
5. **T1-5 contracts 零改动：`SandboxLease` 现有字段表达。** `run_as_user` = `agent` / `rh2grader`（之前恒 `root`）；`network_policy=allowlist` + `network_allowlist_justification` 改写为"isolated internal 网络 + relay"的事实描述；grader 仍 `deny_all`。没有为 profile/digest 加契约字段（那是 T0）——run 记录走 evidence 文件，样本只盖一个 metadata 键。
6. **T1-6 `fa_audit_only` 也接同一 profile（`sandbox_profile_enabled = EXECUTION_MODE != s1_compat`）。** `fa_formal` 挡板未解，GPU 探针目前只能跑 `fa_audit_only`；若 profile 只在 fa_formal 生效，H7 就验不到真实边界。s1_compat（冻结回退面）零改变。orchestrator 层面 `fa_formal` 强制、`fa_audit_only` 允许缺省（旧探针/测试路径）。
7. **T1-7 存储预算的"要求强制"是 profile 参数（`require_writable_layer_quota`，本地默认 0）而不是固定开。** 本机 Docker Desktop 接受 `--storage-opt` 但不强制、多数 overlay2-on-ext4 守护进程直接拒起；固定要求会让本地无法运行。这是资源事实层的部署能力声明（记录实测 `enforced`），不是 reward 可信边界的开关；GPU 主机由 C 拍板。
8. **T1-8 探针的"只有 loopback"判据 = `/proc/net/route` 无带路由接口，而不是 `/sys/class/net` 只有 lo。** `--network none` 的命名空间里内核仍列出 `tunl0/sit0/gre0…` 桩接口（实测），按接口名判会误报。
9. **T1-9 `shutdown/run_residue.py`（W5a 文件）追加网络残留。** 只加两个函数与报告键（`networks_*`），容器语义不变；不加，崩溃后残留的 attempt 网络会占子网槽位且 launch trap 报"零残留"。属所有权外的最小追加，请 W5a/集成者知悉。
10. **T1-10 `BringupService` 关停链加 `egress_runtime` 步（`container_residue` 之后、`resource_closure` 之前）。** 网络必须没有端点才能删，所以在容器面之后；W5a 步骤清单测试 oracle 相应 +1。
11. **T1-11 `write_execution_audit_record` / `RolloutAudit` 新字段用 `getattr(..., None)` 读。** 关停链测试里存在部分构造的 service/audit；新字段缺省不影响旧记录形状。
12. **T1-12 relay 与 attempt 网络的 run 归属。** `MILES_RH2_RUN_ID` 在场即用它；缺省（本地）用 `local-<pid>` 作 relay 的 run_id 并给 attempt 网络/容器盖同一 `rh2.run_id` label（legacy 路径不变：无 env 不加 label，`test_postrun_probes` 钉死的源码文本原样）。

## 8. 偏离说明

- 任务书"rh2/scripts 下的探针脚本"：脚本的**单一事实来源在包内**（`sandbox_profile.py` 的脚本函数），`rh2/scripts/sandbox_probes/*.sh` 是 `dump-probes` 生成的副本（测试保证逐字一致）+ H7 runner。理由：verify 入口必须能在安装为 wheel 的环境里找到脚本，且脚本内插 profile 参数（uid、端口、目标）。
- 任务书"grader 若镜像做不到由探针记录实际用户并显式标记"：按"严"读为 run-halt（T1-3），没有实现自动记录后回退 root 的路径。
- W3a 报告接缝 1/2（bringup 接 grader 分段计时、audit 记录加 `trusted_projection`）：本批未做（W3a 归属，bringup 的改动只限 W3b 面），保留为接缝。
- 未做：镜像级 Git 消毒缓存、grader 长驻、cgroup v1 主机实测（探针有 v1 回退分支但未在 v1 主机验证）、`postrun_probes.py`（experiments，W7 面）的网络残留查询。

## 9. 测试证据（2026-09-04 实跑；工作树 = HEAD `98f730a2` + 本批未提交改动 + 并行 W5b 未提交改动）

```
cd rh2
uv run pytest tests/adapters/test_w3b_sandbox_profile.py -q                     # 14 passed（纯函数 + 替身链）
uv run pytest tests/adapters/test_w3b_bringup_sandbox_runtime.py -q             # 4 passed（bringup 接线，替身 docker）
uv run pytest tests/adapters/test_w3b_sandbox_docker.py -q                      # 14 passed（真实容器，@docker）
uv run pytest tests/grading/test_w3b_grader_profile_docker.py -q                # 3 passed（真实容器，@docker）
uv run pytest tests/ -q                                                          # 1704 passed, 310 skipped（本机 daemon 在，docker 测试实跑）
uv run pytest tests/adapters_miles/ -q                                           # lane A: 339 passed, 310 skipped
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # lane B: 649 passed, 0 skipped
bash scripts/miles_integration_lanes.sh   # 前置校验全部通过（integration tree c8687c9b…/工作树干净/rh2 patch + 15 个语义 patch/pin）；
                                          # lane A 339p/310s ≠ manifest 339p/277s → 脚本红（原因见下）
uv run ruff check src/repoharness2 tests experiments/s1_parity.py experiments/s1_7a_bringup/export_sample.py   # All checks passed!
python -m repoharness2.adapters.slime.sandbox_profile verify --image rh2-s14-grading-fixture:v1 \
  --upstream-host host.docker.internal --upstream-port 18998 --out <dir> --expect-upstream-http   # ok=True，零残留
```

**计数归因**：全仓 1638（W3a 报告）→ 1704。本批 +35 = 14 + 4 + 14 + 3（新文件）；其余差异来自并行 agent（W5b 33 例 `test_w5b_cold_recovery.py` 已在 HEAD）。`tests/adapters_miles` 本批贡献 **0**（三个文件只加 19 行构造参数）；lane A skip 277→310 与 lane B 616→649 的 +33 = W5b 的 integration_base 测试，HEAD `98f730a2` 的 commit 信息已注明"expected_counts 待 W3b 落地后同步"——manifest 更新归集成者，本批不改 manifest。

**关键测试名**：
- canary（D2-4 真边界）：`tests/adapters/test_w3b_sandbox_docker.py::test_private_bundle_canary_absent_from_every_model_visible_surface`（正向对照：唯一串在宿主侧 `grading_spec.eval_script` 与提交给 grader 的 spec 里；模型可见面：prompt、public bundle、容器内 `/rh2 /testbed /home /tmp /etc /opt` grep、root 视角全盘 grep、`docker inspect` Env/Labels/Mounts、`HarnessLaunchSpec`、adapter 记录 全部无）。
- Git 不可恢复：`test_git_future_solution_unrecoverable_from_agent_view_on_real_testbed`（真实 /testbed 带未来解法提交 + tag + 分支：agent 视角 `cat-file`/`show v9.9`/分支/`fsck --lost-found`/`fsck --unreachable`/`grep -r .git` 全部找不到，历史计数 = base）、`test_git_future_probe_deterministic_unrecoverable`（verify 的确定性探针）、`test_real_testbed_sanitize_deleted_future_refs_and_kept_base_history`。
- egress：`test_rollout_egress_public_direct_ip_metadata_host_denied_relay_reachable`（公网/metadata/docker0/上游直连 DENIED、DNS DENIED、relay CONNECTED、经 relay HTTP 状态行）。
- user/caps/限额/mount/network（inspect + 探针）：`test_rollout_inspect_proves_user_caps_nnp_pids_memory_swap_tmpfs_mounts_network`、`test_hidden_root_unreadable_and_privilege_escalation_denied`。
- grader：`tests/grading/test_w3b_grader_profile_docker.py::test_grader_profile_resolved_with_candidate_code_run_as_nonroot_and_deny_all`（eval 日志 `RH2_EVAL_UID=54322`、`RH2_TESTBED_OWNER=54322`、无带路由接口；resolved reward 1）、`..._tests_failed_is_still_reward_zero_negative_sample`、`..._prelaunch_violation_is_run_halt_channel_and_removes_container`；`test_grader_profile_deny_all_nonroot_and_limits_on_real_container`。
- 正常 rollout 在同 profile 下完成：`test_normal_formal_rollout_completes_under_profile_and_stamps_runtime_profile_digest`（真实容器 + agent 视角 bash 经 relay 拿到上游响应 + 交付样本盖 digest）。
- 配置缺失/探针失败 → 不启动且停 run：`test_formal_chain_requires_profile_relay_and_digest_at_construction`、`test_prelaunch_violation_is_typed_fatal_and_leaves_no_container_or_network`、`test_prelaunch_inspect_violation_is_fatal_too`、`test_relay_missing_is_run_fatal_not_member_loss`、`test_prelaunch_failure_on_real_docker_stops_run_without_starting_harness`（真实 docker 负例：把 relay 列进禁止目标 → 探针实测连通 → fatal、零残留）、`test_verification_failure_blocks_startup_and_rollback_stops_relay`、`test_invalid_profile_env_is_rejected_before_any_resource`。
- run 记录：`test_verify_record_ok_and_digest_matches_profiles`、`test_audit_only_bringup_starts_relay_verifies_and_writes_run_record`（`runtime_profile.json` 一次、digest 与 startup evidence/orchestrator 一致、关停 `egress_runtime` 删 relay）、`test_formal_rollout_orders_network_init_sanitize_prelaunch_before_harness_and_stamps_digest`（顺序 + audit 记录 + 样本 metadata）。
- 每项"未生效即拦"负例：`test_rollout_inspect_check_passes_on_profile_args_and_flags_each_violation`（15 项）、`test_rollout_probe_check_passes_and_flags_each_violation`（21 项）、`test_grader_checks_pass_and_flag_network_user_and_binds`。
- 残留：`test_rollout_container_and_attempt_network_removed_after_attempt`、`test_relay_container_is_hardened_and_zero_verify_residue`、`test_w5a_run_residue.py`（桩 docker 含网络）。

删除面/形状改动机械自检（review-standards §7）：新配置项消费者——`RolloutSandboxProfile` 消费者 = `generate._materialize_rollout_sandbox` / `_create_attempt_network` / `run_rollout_prelaunch_check` / verify；`GraderSandboxProfile` 消费者 = `manager._start_container` / `_grader_prelaunch` / `_run_eval` / verify；`runtime_profile_digest` 消费者 = 样本 metadata、execution audit、startup evidence、`runtime_profile.json`；`_exec_bash` 新参数默认路径参数形状逐字不变（FakeDocker 正则未动）；新拒绝路径登记：`sandbox_prelaunch_check_failed` / `egress_relay_unavailable` / `sandbox_profile_verification_failed`（run-fatal，不是样本剔除）、`rollout_egress_network_failed` / `rollout_egress_relay_connect_failed` / `rollout_git_sanitize_failed` / `rollout_trusted_init_failed`（task-local）、`grading_testbed_chown_failed`（评分 infra）、`SandboxProfileViolation`（run-halt）——全部是"不启动/停 run"或既有 infra 通道，无新的 DROP_GROUP 面；测试 oracle 改动 = `test_w5a_shutdown_chain.py` 步骤清单 +`egress_runtime`（T1-10）。

## 10. 开放问题 / 需 owner 知悉

1. **（T0 候选，本批停下不决）grader 非 root 与数据线验证身份的一致性。** 候选测试以 `rh2grader` 运行会改变部分测试的行为（root 会跳过/放过的权限类测试在非 root 下会真的执行；`site-packages` 对非 root 不可写会让任何 install/编译类 eval 步失败——prepared 链 v2 eval 不含 install，但 conftest/插件级写入仍可能）。如果 T2-e 四门验证是以 root 跑出的 F2P/P2P，grader 非 root 会系统性翻转某些题的 reward——这是改变 reward 语义的决定。本批按 owner 拍板落非 root，并要求：**T2-e/C 用同一 grader profile（`verify` 模式或 `GradingManagerConfig(sandbox_profile=…)`）重新验证题单**，或由 owner 明确首训 pin 到验证时的身份。`runtime_profile_digest` 进样本，事后至少能把评分身份与 run 对上。
2. **（C）容器可写层总预算的强制能力。** 只有 overlay2-on-xfs(pquota) 守护进程真强制；GPU 主机需 `docker info` 核对 backing filesystem，决定 `RH2_SANDBOX_REQUIRE_WRITABLE_LAYER_QUOTA=1` 与否；未强制时 tmpfs 上限仍生效但 `/testbed` 写入无上限（探针实测并记录 `enforced`）。
3. **（C）数值校准**：pids 512 / cpus 2 / memory 4 GiB（swap 0）/ tmp 1 GiB / home 256 MiB 是本地默认；Claude Code 二进制解压到 `/tmp`（tmpfs，计入容器内存），django 级仓库的 `chown -R` 与 repack 时间需在 GPU 主机实测（本机 x86 模拟数字偏保守）。
4. **（launch 前置）relay 镜像 `python:3.12-slim` 须预拉取到 GPU 主机**（没有公网时 `verify` 会在 `egress_relay_start_failed` 停下）；`ADAPTER_PUBLIC_HOST` 的含义现在是"relay 视角的宿主地址"（Linux 默认 docker0 网关 172.17.0.1 不变）。
5. **观察（非本批）**：`envpack.materialize.BASH_ENV_PATH = /root/.rh2_bash_env` 在非 root agent 下不可读；当前 ClaudeCodeHarness 并不把 `BASH_ENV` 注入 CC 子进程（`env_injections` 只记录在 launch spec），所以今天无影响；日后若真接 `BASH_ENV`，该文件须移到 agent 可读位置（如 `/etc/rh2_bash_env`）。
6. **每 attempt 网络的并发上限**：显式 `/29` 子网池 8192 槽；relay 同时挂在 N 张网络上（N = 并发 attempt 数）本机实测 26 张无问题（之后是守护进程默认地址池耗尽，已用显式子网绕开），更高并发（64+）需在 GPU 主机核对 relay 的接口数无异常。
7. **cgroup v1 主机**：探针有 v1 回退分支（`pids/pids.max`、`memory/memory.limit_in_bytes`、`memsw`、`cpu.cfs_*`）但未在 v1 主机验证；若 GPU 主机是 v1，`verify` 会第一时间暴露。
8. **manifest / 文档同步（集成者）**：`integration_base_manifest.json` expected_counts（W5b +33，本批 0）；06 计划 W3b 行与 §6"本次实际能力"措辞改为"run 级 `runtime_profile_digest` + 探针报告"（前置清理批已列）；附录 A 5a 改为"正式 profile 缺必需配置 / 探针未生效 → 不启动/停 run（W3b 创建入口）"；spike-log 落账。
9. **postrun_probes.py**（experiments，W7 面）尚不查网络残留；launch trap（`rh2_run_trap_cleanup.sh` → `run_residue.py`）已覆盖。

## 11. 协作协议五段收尾

**① 待拍板 T0**：无新增 contracts/协议改动。**一项 T0 候选停下**：开放问题 1（grader 非 root 与 T2-e 验证身份一致性——改变 reward 语义的决定，本批按 owner 已拍板的"非 root"落地，是否要求数据线用同一 profile 重验题单请 owner 定）。另请 owner 确认 T1-1 的 relay 容器不算"引入重要服务"。

**② T1 决策及理由**：§7 T1-1 ~ T1-12。请特别知悉 T1-1（每 attempt isolated 网络 + 每 run relay）、T1-3（grader 非 root 无自动回退）、T1-6（fa_audit_only 也接 profile）、T1-7（存储预算"要求强制"是参数）。

**③ 临时挡板新增/命中/解除**：无新增；`bringup.py` 的 fa_formal 挡板原样未触碰（本批只在其后追加 profile 解析，测试 `test_w1b_bringup_builds_prepared_face_without_v1_loader` 的源码顺序断言仍成立）。

**④ 推翻或修正了哪些旧结论**：
- 06 计划 W3b 行原文"每 sandbox 创建后核实并记录正向能力事实……事实进 eligibility"——按 D2-2 改为创建期强制 + 启动前核对 + run 级记录，不进 eligibility（前置清理批已删消费面，本批落实产生面）。
- `SandboxLease.run_as_user="root"` 的 S0 现状与"网络策略 allowlist 只记录意图、包级过滤归 S2"的 S1 注记——rollout 现为 `agent` + 真实阻断；grader 现为 `rh2grader`。
- "grader 只有 `--network none`、root、无资源限制"（决策包事实）——已改。
- W3a 报告 §6 之后的 lane 计数（339/277、615+1）——现为 339/310、649/0（W5b 所致，本批 0）。

**⑤ 测试/证据/账本状态**：§9；manifest 由集成者同步（本批不改）；spike-log 由集成者落账；本机 Docker 残留零（`docker ps -a` / `docker network ls` 无 `rh2-*`，fixture 镜像保留）。

**本轮没有改变哪些已定案语义**：`contracts/` 全部 schema；W3a 的评分正链、可信评分投影、状态所有权转移与十三段计时（`generate.py` 评分/投影逻辑逐字未动，唯一改动是交付面盖一个 metadata 键）；前置清理批的 security 维/第七维语义；W1b 三终态交付面与 admission 载荷；`_exec_bash` 缺省参数形状；s1_compat 冻结路径（无 profile、旧 docker 参数、root grader）；`bringup.py` fa_formal 挡板；W5a 关停链既有步骤语义（只追加一步）；`reference/`、`rh2/src/slime`、lanes manifest 与 patch 表；faithful DIS loss。

---

## 12. codex Wave3 完整审查（`tmp/wave3检查.md`）修复批（2026-09-04，append-only）

范围：F2 / F4 / P2-1 / R2 / P2-4 / F1（F3 归另一 agent，已作为 `1ba4996f` 落地；本批未碰 `engine_router_client.py` / `capture_wire.py`）。起点 = 已落地的 W3b commit `741a7570` 之后的 HEAD（写本节时 HEAD = `1ba4996f`）。工作树未 commit / 未 stash。

### 12.1 F2（P1）：fresh grader 里 candidate 不能再改写 official tests / 控制面

**根因**（codex 复核属实）：旧实现 `chown -R <candidate> /testbed` 后由候选用户跑整段 eval 脚本，official test files 及其父目录都归候选用户，候选 module 的 import/插件副作用可改写尚未执行的测试。

**方案**（三步，`grading/manager.py::_run_eval` profile 分支）：

| 步 | 身份 | 内容 |
|---|---|---|
| 1 trusted setup | root | `spec.trusted_setup_script`（prepared 链 = `render_v2_trusted_setup_script`：conda 激活、`git status/show/diff`、`git checkout <base> -- <official files>`、`git apply` official test_patch）。候选代码此时尚未运行。 |
| 2 权限布置 | root | `sandbox_profile.grader_protect_control_surface_script(profile, hygiene.test_files)`：先 `chown -R <candidate> /testbed`（构建目录、`__pycache__`、缓存全可写），再把每个 official test file 收回 **root:root 0644**，把它们的**每一级祖先目录（含 /testbed 本身）**收回 **root:root 1777（sticky）**；脚本末尾 `stat` 自证（`RH2_PROTECT_OK=1`、`PROTECTED_FILES/DIRS`、`MISSING_FILES`、`TESTBED_STAT`），不达标 = `GradingInfraError("grading_control_surface_protect_failed")`。 |
| 3 candidate eval | 候选 uid（`-u 54322 -e HOME=/home/rh2grader`） | `spec.candidate_test_script`（prepared 链 = `render_v2_candidate_test_script`：conda 激活 + `: '>>>>> Start Test Output'` + `eval_cmd <files>` + End 标记），脚本由 root 写在 root 属主目录（`/rh2`）或 sticky `/tmp`，候选进程无法在执行中改写。 |

日志 = setup 段 + 测试段（形态与官方单脚本一致，parser 未改）。**为什么选 sticky 而不是 0755 或只读挂载**：0755 父目录会误伤要在测试目录里写 `__pycache__`/临时产物的任务；只读 bind mount 需要在 apply test_patch 之后再挂载一层，容器内没有可信挂载通道（cap-drop ALL）；sticky 位正好是"可新建、不可替换"的最小手段：root 0644 文件对候选 EACCES（截断写/chmod EPERM），sticky 目录里 root 属主条目 unlink/rename EPERM，祖先目录本身是 sticky 父目录里的 root 条目所以也 rename 不掉（同路径重建的前提被封）。`.git` 与其余文件仍归候选（评分后没有任何可信步骤再读仓库，无 reward 因果路径；候选测试常需 git 只读访问）。

**评分材料形状**：`GradingEnvSpec` 新增 `trusted_setup_script` / `candidate_test_script`（`manager.py` 内 dataclass，非 contracts/）；prepared 链 `build_grading_spec_from_host_view` 同时给出完整 `eval_script`（记录/legacy）与两段（同一组行构成，`render_v2_eval_script` 文本逐字未变，既有 marker/judge oracle 原样通过）；profile 下缺拆分脚本 = `SandboxProfileViolation("grader_eval_split_required")` run-halt（environment adapter 侧系统性缺陷，不洗成成员损耗）。legacy（无 profile）路径仍 root 整段执行、参数形状逐字不变。

**已知残余（登记不修，与 D2-3 已登记项同类）**：official 测试目录里**非 official** 的候选可写文件（测试数据、`conftest.py`、`pytest.ini` 等通用控制面）不在本 profile 保护面——D2-3 已把通用控制面定义交给最终 environment adapter；本 F2 只封 `hygiene.test_files` + eval 脚本本体。

**测试**（`tests/grading/test_w3b_grader_profile_docker.py`，真实容器）：
- 权限反例 `test_f2_candidate_cannot_truncate_unlink_rename_or_recreate_official_test_file`：official test patch 应用后，候选 uid 对 `tests/test_thing.py` 的截断写 / unlink / rename / 父目录 rename / 同路径重建 / chmod 六种改写全部 `DENIED`，同目录新建文件 `OK`，文件仍 `0 644` 非零长度，评分照常 resolved。
- 行为反例 `test_f2_candidate_import_side_effect_cannot_rewrite_later_official_test`：顺序执行 A/Z 两个 official 测试，A 导入的候选 module 在 import 时六条路径试图改写 Z（write/unlink/rename/目录 rename//testbed rename/chmod）→ 全部 `DENIED:<errno>`，Z 仍 `PASSED`，parser 结果不受影响（resolved，`PROTECTED_FILES=2`）。
- 正例 `test_f2_compile_cache_and_build_writes_still_allowed_for_candidate`（`compileall` 写 `tests/__pycache__` 与 `src/__pycache__`、`build/lib/out.o`、`/tmp`、`$HOME/.cache`、`src/generated.py` 全部 OK 且 resolved）+ 既有 resolved / tests_failed 正例（非 root、断网、限额断言保留）。
- 替身（`tests/grading/test_w3b_grader_profile_unit.py`，3 例）：顺序 root setup → root 权限布置 → 候选 uid 测试；日志拼接；缺拆分脚本 run-halt 且容器已删；legacy 路径逐字不变。
- **T1 oracle 改动**：`test_grader_profile_resolved_with_candidate_code_run_as_nonroot_and_deny_all` 原断言 `RH2_TESTBED_OWNER=<candidate>`（整个 /testbed 属候选用户——codex 指出这是错的）→ 改为 `/testbed` 与 `tests/` `0 1777`、`tests/test_thing.py` `0 644`、`src` 属候选用户。

### 12.2 F4（P1）：egress 清理失败不再假绿

- `BringupService.close()` 的 residue 新增 `egress_cleanup_failures`（`egress_runtime` 步 facts 里的 failures，含 `network_ls_failed`——查询失败 ≠ 零残留）与 `egress_relay_left`（relay 未删成时的容器名）→ `residue_free=False` → `ShutdownReport.ok=False`；step facts 仍保留（证据），不改 W5a 的 chain.py。
- 启动回滚消费 `stop_egress_relay()` 返回值：删除失败时 **handle 保留**（`self.egress_relay` 不清空），错误并入 `_startup_rollback_errors`（`relay_stop: <name>: …`），首因异常照抛不被覆盖。
- `start_egress_relay`：ready-timeout / 镜像 inspect 失败 / digest 不符时自行 `docker rm -f`，rm 失败 → `SandboxNetworkError(..., leftover_containers=(name,))`，消息含"残留"；bringup 把它记到 `service.sandbox_startup_leftovers`、`StartupCheckError` 消息与 rollback errors（`relay_leftover_containers`）。残留容器带 `rh2.run_id` label，launch trap / `run_residue` 的 label 查询可见。
- 测试（`tests/adapters/test_w3b_bringup_sandbox_runtime.py`，替身 docker 的 `containers_with_label()` 模拟 label 残留查询）：`test_f4_attempt_network_remove_failure_marks_shutdown_not_ok_and_lists_failure`、`test_f4_network_list_failure_is_residue_not_zero`、`test_f4_relay_remove_failure_on_normal_shutdown_marks_not_ok_keeps_handle_and_is_label_visible`、`test_f4_relay_ready_timeout_remove_failure_at_startup_keeps_evidence_and_first_cause`、`test_f4_startup_rollback_relay_remove_failure_keeps_handle_and_does_not_mask_first_cause`；`tests/adapters/test_w3b_sandbox_profile.py::test_f4_relay_ready_timeout_with_remove_failure_leaves_leftover_evidence_visible_by_label`（+ rm 成功无残留的对照）。

### 12.3 P2-1：agent 用户/uid 不再是假旋钮

`RolloutSandboxProfile.validate` 显式拒绝非 `agent/54321`（`rollout_agent_identity_fixed_in_first_version`）；`rollout_profile_from_env` 删除 `RH2_SANDBOX_AGENT_USER/UID` 解析（vendored slime harness 与 `ClaudeCodeDriver` 写死用户名 `agent`，未改 vendored slime）。测试 `test_p2_1_agent_identity_is_fixed_and_env_has_no_user_knob` + 参数化负例。

### 12.4 R2：relay 镜像 digest-pinned 并在 run 记录里核对实际镜像

- `RELAY_IMAGE_DEFAULT = python@sha256:78387bc3881b8273120a12ebe6c1ab22b018ccc2c9adf565ae1ac9b536e184ea`（来源：本机 2026-09-04 `docker image inspect python:3.12-slim -f '{{index .RepoDigests 0}}'`，OCI image index digest，多架构；GPU 主机预拉 `docker pull python@sha256:…`）。`relay_image` 必须匹配 `name@sha256:<64hex>`（可变 tag 拒：`rollout_relay_image_not_digest_pinned`），env `RH2_SANDBOX_RELAY_IMAGE` 同规则。
- `start_egress_relay` 就绪后 `docker inspect -f {{.Image}}` + `docker image inspect -f {{json .RepoDigests}}`，钉死引用不在 RepoDigests 里 → `egress_relay_image_digest_mismatch`（rm 容器）；`EgressRelayHandle.image_id / repo_digests` 进 `runtime_profile.json` 的 `relay`。
- 负例 `test_r2_relay_image_id_drift_under_same_reference_is_rejected_and_container_removed`（引用文本不变、RepoDigests 漂移）；正例 `test_r2_relay_start_records_actual_image_id_and_repo_digests`、真实容器 `test_relay_container_is_hardened_and_zero_verify_residue` 断言 `.Image` 与 RepoDigests 含钉死值。

### 12.5 P2-4：W3b 计时进聚合面

`attempt_timing.LIFECYCLE_SEGMENTS` 追加六段（前十三段原样）：`sandbox_network_create` / `sandbox_container_start` / `sandbox_git_sanitize` / `sandbox_trusted_init` / `sandbox_prelaunch_probe` / `grader_trusted_setup`；`generate.py` 在 `sandbox_setup` 之外同时写 `audit.lifecycle_timing`（随 `timing_summary` 落 execution audit，`aggregate_lifecycle_timings` 自动出 p50/p95）；`GRADER_PHASE_SEGMENTS` 加 `grader_trusted_setup`，`GradingTimingRecord.test_seconds` 不再含 root setup。**T1 oracle**：`test_w3a_attempt_timing.py::test_segments_are_exactly_the_thirteen_from_the_decision_package` → `..._plus_w3b_setup_segments`（前十三段逐字钉死 + 六段追加）。

### 12.6 F1（P1，最后做）：删除过期 fa_formal 挡板 + 真入口纵切

- 删除 `bringup.BringupService.__init__` 中的无条件 `raise RuntimeError("fa_formal 暂禁…")`（原 `bringup.py:857-869`，含引用旧 FA 前置的注释），原位留注释说明保留的真实核对：`select_task_face_mode`（fa_formal 缺 `RH2_PREPARED_TASKS_DIR` 即拒，不回退 v1）、`validate_execution_config`（`require_real_weight_versions` + 数值 policy_version + 屏障）、`RolloutOrchestrator`（缺 profile/relay/digest 即拒）、finalization store、`_start_sandbox_runtime`（验证不过 StartupCheckError）。不新建 approval manifest / 新闸门。
- 纵切 `tests/adapters_miles/test_w3b_formal_entry_vertical.py`（4 例，双 lane）：`test_fa_formal_entry_assembles_prepared_face_grader_profile_relay_and_orchestrator`——真实 `ensure_fa_started(args)`（miles 生产入口的启动引导）在 `RH2_EXECUTION_MODE=fa_formal` 下走通 prepared task face（attempt 绑定解析、评分材料已拆分）+ grader profile + relay + verify（`runtime_profile.json` / `startup_evidence.json`）+ `RolloutOrchestrator(fa_formal, profile, relay, digest, barrier, store)`，引擎实测版本 `7`，正常关停 ok；三条 typed 停止负例：`..._rejects_missing_prepared_artifacts_typed`、`..._rejects_version_contract_off_and_rolls_back_relay`（relay 已起又被回滚删掉）、`..._rejects_sandbox_verification_failure`。
- **T1 oracle**：`test_w1b_prepared_chain.py::test_w1b_bringup_builds_prepared_face_without_v1_loader` 末段"挡板文本必须先于任务面选择"→ 改为"挡板文本不再出现、任务面选择仍在"。
- F3 接缝（归集成者）：`BringupService.verified_router_workers`（`_run_startup_checks` 从 `startup_evidence.router_workers.urls` 填）→ 接 `MilesRouterWorkerClient.set_verified_workers(...)`（F3 commit `1ba4996f` 提供）。

### 12.7 测试证据（2026-09-04 实跑，HEAD `1ba4996f` + 本批未提交改动）

```
uv run pytest tests/ -q                                                     # 1740 passed, 310 skipped
uv run pytest tests/grading/test_w3b_grader_profile_docker.py -q            # 6 passed（真实容器）
uv run pytest tests/adapters/test_w3b_sandbox_docker.py -q                  # 14 passed（真实容器）
RH2_MILES_PATH=$REPO/reference/miles-rh2-integration uv run pytest tests/adapters_miles/ -q   # lane B: 664 passed, 0 skipped
bash scripts/miles_integration_lanes.sh    # 前置校验全部通过；lane A 354 passed / 310 skipped（manifest 仍 339/310 → 脚本红）
uv run ruff check src/repoharness2 tests experiments/s1_parity.py experiments/s1_7a_bringup/export_sample.py   # All checks passed!
```

计数归因：全仓 1704 → 1740（+36）= 本批新增：profile 单元 +10（P2-1/R2/F4/F2 脚本，含 3 条参数化行）、bringup F4 +5、grader 替身 +3、grader 真实容器 +3、fa_formal 纵切 +4、并行 F3 agent 的 `test_w10_multi_engine.py` +11。lane A 339→354 / lane B 649→664：+4 = 本批纵切（双 lane），+11 = F3（双 lane）；**manifest expected_counts 应同步为 lane A 354p/310s、lane B 664p/0s（集成者）**。本机 Docker 零残留（容器/网络无 `rh2-*`）。

### 12.8 协作协议五段收尾（本批）

**① 待拍板 T0**：无新增。codex 复核把本报告 §11 的两项"T0 候选"判为 false-positive T0（grader 非 root 已在 D2-2 批准——T2-e 用同一 grader profile 复验是数据资格实施；每 run 无状态 relay 是已批 allowlist 的实现组件）——接受该判定，不再列为待拍板；数据线仍需用同一 grader profile 复验最终题单（数据确定后）。

**② T1 决策及理由**：F2 权限方案取 sticky 目录 + root 0644 文件（§12.1 理由）；`.git` 归候选用户（无 reward 因果路径）；profile 下缺拆分脚本升 run-halt；F4 残留经 `report.residue` 上提而非让 step 失败（facts 保留为证据）；R2 pin 到 OCI index digest（多架构）；P2-4 六段追加到 `LIFECYCLE_SEGMENTS` 尾部（十三段顺序不变）。

**③ 临时挡板新增/命中/解除**：**解除** `bringup.py` 的 fa_formal 无条件挡板（F1）；无新增。

**④ 推翻或修正了哪些旧结论**：§1.2"候选执行用户 chown -R /testbed"→ 改为 official 文件/祖先目录 root 属主 + sticky；§4"`grader-chown-before-eval`"脚本 → `grader-protect-control-surface`（`scripts/sandbox_probes` 已重新 dump）；§11 两项 T0 候选 → 撤回；W3a 报告 §9 的 `test` 段含义在 profile 路径下改为"只计候选测试"。

**⑤ 测试/证据/账本状态**：§12.7；manifest expected_counts 由集成者同步；本机 Docker 零残留。

**本轮没有改变哪些已定案语义**：`contracts/` 全部 schema；W3a 评分正链/可信评分投影（`render_v2_eval_script` 文本逐字未变）；legacy（无 profile）grader 路径与 s1_compat；W5a 关停链步骤顺序与 `chain.py`；F3 归另一 agent 的 `engine_router_client.py` / `capture_wire.py`；`reference/`、`rh2/src/slime`、lanes manifest 与 patch 表。

## 13. codex Wave3 聚焦复核 §9.2（F2 残留 P1）修复（2026-09-04，append-only）

范围：只改 `grading/manager.py`、`adapters/slime/sandbox_profile.py` 的 grader 权限脚本、`adapters/slime/prepared_task_face.py` 的可信 setup 脚本渲染，以及对应测试与 `scripts/sandbox_probes` 的脚本副本。**未碰** `bringup.py` / `capture_wire.py` / `engine_router_client.py`（F3 归并行 agent）/ `contracts/` / `reference/` / `rh2/src/slime` / `generate.py`。工作树未 commit / 未 stash。

### 13.1 两个缺口（codex 复核属实）

1. `SWEGradingManager._run_eval()` 拿到 root 可信 setup 的结果后**完全不看退出码**，直接进权限布置并以候选 uid 跑测试。注入 `setup rc=17 / git apply failed` 后候选日志照样 PASS，产出 `outcome=resolved reward=1.0`——评分可能是在"没应用 official test_patch 的基线测试"上得出的。
2. 权限脚本遇到缺失或非普通文件的 official test 只写 `MISSING_FILES=...`，最后仍输出 `RH2_PROTECT_OK=1`；manager 既不看 `MISSING_FILES`，也不核对 `PROTECTED_FILES`。`PROTECTED_FILES=0`、`MISSING_FILES=tests/test_thing.py,` 仍能出 `reward=1.0`。

两条都是**已批 D2-3 不变量的实现缺口**，不改训练语义、不新增 reward 规则、无新 T0。

### 13.2 成功判据（自证标记 + manager 比对）

**为什么不给整段 setup 加 `set -e`**：official test_patch 可能新增测试文件，官方那条一次性 `git checkout <base> <全部路径>` 只要清单里有一个"base 里不存在"的路径就整条 pathspec 失败——用它当判据会把正常任务判成失败。所以把"恢复到基线"和"应用 official patch"拆成两个独立结果。

**可信 setup（`prepared_task_face.render_v2_trusted_setup_script` + `sandbox_profile.grader_trusted_setup_attest_lines`）**

- 恢复到基线：逐个 official test 文件，`git cat-file -e <base>:<path>` 命中才 `git checkout <base> -- <path>`，**checkout 失败即整段 `exit 3`**；base 里没有的路径跳过并记数（不是失败）。
- 应用 official test_patch：`git apply -v` 的返回码单独捕获进 `RH2_APPLY_RC`。
- 自证写进 **root 属主文件** `/rh2/rh2_trusted_setup_attest`（`GRADER_TRUSTED_SETUP_ATTEST_PATH`），同时打到标准输出留审计。**为什么不认标准输出里的自证行**：setup 会打印 `git -c core.fileMode=false diff <base>`，那份 diff 就是候选自己写的代码，候选只要在源码里放一行 `RH2_SETUP_OK=1` 就能伪造；自证文件在候选代码运行之前由 root 写出，候选没有任何写入口。
- 自证字段：`RH2_SETUP_APPLY_RC` / `RH2_SETUP_RESTORED` / `RH2_SETUP_EXPECTED_TEST_FILES`（渲染时写死的去重后清单长度）/ `RH2_SETUP_TEST_FILES`（在位普通文件数）/ `RH2_SETUP_ABSENT_TEST_FILES` / `RH2_SETUP_IRREGULAR_TEST_FILES`（存在但不是普通文件，例如 symlink）；三条判据（apply rc=0、irregular 为空、在位数 ≥ 1）全过才写 `RH2_SETUP_OK=1`，否则写 `RH2_SETUP_ERROR=<原因>` 并 `exit 3`。
- **manager 侧比对**（`_check_trusted_setup_attest`）：`setup.exit_code == 0` ∧ `RH2_SETUP_OK=1` ∧ `RH2_SETUP_APPLY_RC=0` ∧ `RH2_SETUP_EXPECTED_TEST_FILES == len(normalize_official_test_files(spec.hygiene.test_files))` ∧ 在位数 ≥ 1 ∧ 在位数 + 缺失数 == 期望总数 ∧ irregular 为空。任一不成立 → `GradingInfraError("grading_trusted_setup_failed:<原因码>...")`，**权限布置与候选测试都不启动**。

**权限布置（`grader_protect_control_surface_script`）**

- 三分支分类：普通文件 → 收回 root:root 0644 并计数；存在但非普通文件（symlink/目录）→ 进 `IRREGULAR_FILES`；不存在 → 进 `MISSING_FILES` 并记 `MISSING_FILES_COUNT`。
- 自证字段先落地（失败时也留证据）：`EXPECTED_FILES`（渲染时写死）/ `PROTECTED_FILES` / `PROTECTED_DIRS` / `MISSING_FILES` / `MISSING_FILES_COUNT` / `IRREGULAR_FILES` / `TESTBED_STAT`；`IRREGULAR_FILES` 非空、或 `PROTECTED + MISSING_N != EXPECTED` 时 `exit 5` 且**不输出** `RH2_PROTECT_OK=1`（原来 OK 是第一行，现在是最后一行）。
- **manager 侧比对**（`_check_control_surface_attest`）：`protect.exit_code == 0` ∧ `RH2_PROTECT_OK=1` ∧ `EXPECTED_FILES == 期望总数` ∧ `IRREGULAR_FILES` 为空 ∧ `PROTECTED_FILES == RH2_SETUP_TEST_FILES` ∧ `MISSING_FILES_COUNT == RH2_SETUP_ABSENT_TEST_FILES`。不达标 → `GradingInfraError("grading_control_surface_protect_failed:<原因码>...")`。
- manager 传给权限脚本的清单改成 `normalize_official_test_files(spec.hygiene.test_files)`（去重保序、非法路径 fail-closed），与算期望值用的是同一个函数。

**typed 处置**：两处都走既有 `GradingInfraError` 通道 → `outcome=failed_to_grade`、`failure_category=infra_failure`、`reward=None`（不是 `reward=0`）。没有新增 reward 规则、没有改 `contracts/`。

**偏离 codex 建议的一处（T1，理由）**：codex 写的是"`MISSING_FILES` 必须为空、`PROTECTED_FILES` 必须精确等于去重后的 official test 文件数"。直接照做会**新增系统性拒绝面**：`hygiene.test_files = patch_touched_paths(test_patch)` 取的是 `diff --git a/X b/Y` 两侧路径，因此 official test_patch **删除**或**改名**掉的测试文件也在清单里，这类正常任务跑完 setup 后本来就有文件不在位，"缺一个就拒"会把它们全判成不可评分（按协作协议这属于 T0 级的样本偏置面）。改成：缺失的**权威判据是"official `git apply` 成功"**——base 里存在的文件 checkout 失败即整段失败、apply 又必须成功，两条一起保证剩下的缺失只可能是 official patch 自己规定的；权限布置只需与可信 setup 数出的在位/缺失数**逐一对齐**。正常任务（patch 不删测试文件）下缺失数为 0，这两条自动退化成 codex 原话的形式。symlink/目录则**无条件拒**（保护住 symlink 本身不等于保护住被执行的测试）。

**新增的 run-halt（T1）**：profile 路径下 `hygiene.test_files` 为空 → `SandboxProfileViolation("grader_official_test_files_required")`。与既有 `grader_eval_split_required` 同类（environment adapter 侧系统性缺陷，不洗成成员损耗）；prepared 链本身已在构造评分材料时以 `v2_test_files_empty` 拒过，正常路径不可达。

**审计/计时**：`record.trusted_setup`（setup 自证事实）与 `record.control_surface`（权限自证事实）在判定**之前**就写进容器记账条目，失败时看得到卡在哪一条；`record.eval_log_partial` 保存 setup + 权限布置的原始输出，`grade()` 的 infra 分支用它给 `eval_log_ref` 落盘（候选测试从未启动时故障现场不丢）。`grader_trusted_setup` 计时段改由 `_run_eval` 在 `finally` 里记，被判据挡下的那次同样有计时（legacy 无 profile 路径恒 0.0，口径不变）。

### 13.3 反例测试（全部实跑通过）

真实容器（`tests/grading/test_w3b_grader_profile_docker.py`，+4；用 `RecordingDocker` 记录真实 docker CLI 调用，断言"以候选 uid 跑 eval 脚本的 exec 一次都没发生"——启动前探针也用候选 uid，按脚本形态区分）：

- `test_f2_official_test_patch_apply_failure_blocks_candidate_test`：official test_patch 真的打不上（上下文行不存在），而候选代码本来会让测试全过（`SRC_FIXED` → 正常路径 resolved/1.0）→ `failed_to_grade` / `reward=None` / 零候选测试 exec / 日志里没有 `>>>>> Start Test Output`，落盘日志含 `RH2_SETUP_ERROR=official_test_patch_apply_failed`，`control_surface is None`（权限布置根本没开始）。
- `test_f2_official_test_file_missing_after_setup_blocks_candidate_test`：setup 后唯一的 official test 文件不在位 → `no_official_test_file_present` → 同上。
- `test_f2_official_test_file_symlink_is_rejected_by_protect_step`：official test 文件被换成 symlink，且可信 setup **谎报**一切正常（手写自证文件绕过共享自证尾段）→ 真实权限脚本自己数出 `IRREGULAR_FILES=tests/test_thing.py,` 并 `exit 5` → 拒。
- `test_f2_protect_step_rejects_missing_official_test_file_it_was_told_to_protect`：setup 谎报"1 个在位"、实际文件不存在 → 权限脚本如实给出 `PROTECTED_FILES=0` / `MISSING_FILES=tests/test_thing.py,` 且自身判据通过（0+1==1）→ manager 与 setup 自证比对后 `protected_count_mismatch` 拒。**这条就是 codex 原样反例的生产路径版本。**

替身（`tests/grading/test_w3b_grader_profile_unit.py`，+7）：`test_f2_trusted_setup_nonzero_exit_blocks_candidate_test_and_is_typed_infra`（rc=17）、`test_f2_trusted_setup_attest_missing_blocks_candidate_test`（自证文件没写出）、`test_f2_trusted_setup_official_test_file_list_mismatch_blocks_candidate_test`、`test_f2_protect_reporting_zero_protected_and_missing_file_blocks_candidate_test`（codex 原样反例：脚本仍写 `RH2_PROTECT_OK=1`）、`test_f2_protect_reporting_symlink_official_test_file_blocks_candidate_test`、`test_f2_protect_expected_count_mismatch_blocks_candidate_test`、正例 `test_f2_official_test_patch_deleting_a_test_file_still_grades`（official patch 删掉清单里一个测试文件时照常评分——证明没新增系统性拒绝面）。

脚本文本（`tests/adapters/test_w3b_sandbox_profile.py`，+2）：`test_f2_protect_script_self_attests_coverage_before_declaring_ok`、`test_f2_trusted_setup_attest_lines_gate_apply_result_and_file_shape`。

既有 F2 正例全部原样通过（权限六路攻击 DENIED、A/Z import 副作用改不了后执行的测试、编译/缓存写入不误伤、resolved / tests_failed 正常语义）。

**T1 oracle 改动**：
- `tests/grading/grading_fixtures.py::make_trusted_setup_script` 从"一行 `git checkout`"改成"恢复（失败即 exit 3）→ 可选真跑 `git apply` → 共享自证尾段"，并新增 `test_files` / `test_patch` / `extra` 三个负例旋钮；fixture 与生产用**同一份**自证判据。
- A/Z 行为反例的 `make_trusted_setup_script` 现在必须传 `test_files=("tests/test_a.py", "tests/test_z.py")`（否则自证清单与 spec 的 `hygiene.test_files` 不符，按新判据即拒——这正是判据在起作用）。
- `test_grader_profile_resolved_with_candidate_code_run_as_nonroot_and_deny_all` 追加断言：`EXPECTED_FILES/MISSING_FILES_COUNT/IRREGULAR_FILES` 与 `record.trusted_setup` 各字段。
- `tests/sandbox_test_support.py::ProfileFakeState` 新增 `protect_facts_override` / `protect_exit_code` 旋钮，权限脚本替身输出改为按脚本里的 `EXPECTED=<n>` 生成完整自证字段。

### 13.4 测试证据（2026-09-04 实跑，工作树 = HEAD `52a4818b` + 本批改动 + 并行 F3 agent 未提交改动）

```
uv run pytest tests/grading tests/adapters/test_w3b_sandbox_docker.py tests/adapters/test_w3a_formal_grading_freeze.py -q   # 135 passed
RH2_MILES_PATH=$PWD/../reference/miles-rh2-integration uv run pytest tests/adapters_miles/test_w3b_formal_entry_vertical.py tests/adapters_miles/test_w1b_prepared_chain.py -q   # 15 passed
uv run pytest tests/ -q                       # 1759 passed, 310 skipped
uv run ruff check <本批改动文件>               # All checks passed!
```

全仓计数：本批新增 13 例（grader 真实容器 +4、grader 替身 +7、profile 脚本文本 +2），其余为并行 F3 agent 的改动。本机 Docker 零残留（`docker ps -a` 无 `rh2-*` 容器、无 `rh2-*` 网络）。`scripts/sandbox_probes/grader-protect-control-surface.sh` 已按 `dump-probes` 重新落盘（与包内文本逐字一致的既有断言通过）。

### 13.5 推翻或修正的旧结论 / 开放问题

- §12.1 "完整 eval_script 与两段拆分脚本**由同一组行构成**"在可信 setup 半段**不再成立**：profile 路径的 setup 脚本多了逐文件恢复循环、`RH2_APPLY_RC` 捕获与自证尾段。`render_v2_eval_script`（legacy 无 profile 路径执行的那份）与 `render_v2_candidate_test_script` **文本逐字未变**，W3a 冻结面与 s1_compat 不受影响。
- §12.1 "不达标 = `GradingInfraError("grading_control_surface_protect_failed")`"仍成立，但判据从"只看 `RH2_PROTECT_OK`"扩到 §13.2 的六条，并新增了对称的 setup 判据。
- **开放问题（本批不修，登记）**：候选测试命令是 `eval_cmd <hygiene.test_files 全部路径>`。若 official test_patch 删掉清单里的某个测试文件，该路径仍会被传给测试运行器（官方 swebench 脚本同样如此），可能让运行器报 usage error。本批的判据不会因此误判（缺失是合法的），但这类任务的**日志形态**是否被官方 parser 正确处理，需要在 T2-d/W3a 的真实镜像验证里覆盖。
