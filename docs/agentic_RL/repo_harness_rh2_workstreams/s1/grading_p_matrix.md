# S1-4 P1~P11 对照表（SWEGradingManager 最小版）

来源清单：设计文档 2 §5.2 "SWEGradingManager 必须处理的工程坑"
（`docs/harness_improve/repo_harness_design_doc2_verifiers_based.md`，P1~P11）。
本表逐条给出：S1-4 的实现落点、真实测试路径、以及显式豁免（豁免必须写明
"为什么现在测不了 + 递延到哪一站"）。

代码：`rh2/src/repoharness2/grading/manager.py`（prepare/grade/gc + startup 清扫）、
`rh2/src/repoharness2/grading/queue.py`（有界队列 + 反压事件）。
测试：`rh2/tests/grading/`（53 个用例 = 42 个无 docker + 11 个 `-m docker` 真容器）。

状态图例：**测** = 有真实测试；**测(部分)** = 核心行为已测、其余面豁免；**豁免** = 全部递延。

| #   | 坑                     | 状态   | 实现落点（manager.py / queue.py）                                                                                                                                                                      | 测试路径                                                                                                                                                                                                                                                                                          | 豁免部分与递延站点                                                                                                                                        |
| --- | ---------------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| P1  | 泄漏回收与故障域隔离   | 测     | 容器 label 记账（`rh2.grading.owner/.trajectory/.created_at_epoch`）+ 名前缀 `rh2-grading-`；`grade()` finally 必删；`gc(trace \| ttl \| 全量)`；`startup()` 按 label 清扫"外来且超龄"容器（默认 3600s 门槛防误杀并行 worker）；rm 失败写 `cleanup_failures`（Q8 留痕）；评分容器崩溃 → infra 报告照常返回（trace 不丢）；单条评分异常不炸队列 | docker：`test_orphan_sweep_real`（真孤儿清掉、年轻外来容器幸存）、`test_killed_grading_container_real`（容器被杀 trace 不丢）、全部 docker 用例结尾 `_assert_no_leftover_containers`；unit：`test_startup_sweep_age_and_ownership_rules`、`test_gc_by_trace_and_ttl`、`test_cleanup_failure_is_recorded_not_swallowed`；queue：`test_single_failure_does_not_kill_queue` | evict-and-reschedule 到**健康节点**重评是多节点语义 → S5（单机 S1 无节点池；infra 报告即上层重试信号）                                                     |
| P2  | 资源翻倍               | 测(部分) | `prepare()` fire-and-forget（立刻返回 Task）+ 有界信号量（`prepare_concurrency` 默认 2）；prewarm 默认关闭（S1 只做镜像预拉取，不预起容器）                                                                                                  | unit：`test_prepare_is_bounded_and_fire_and_forget`（6 个并发 prepare，实测最大并发拉取 ≤2）                                                                                                                                                                                             | "16 rollouts 高峰并发容器翻倍"的规模效应需真实负载 → S1-7a/S2 用 F5 埋点数字复核                                                                    |
| P3  | 超时账目               | 测     | manager 内部**分段** timeout（env_reset / patch_write / patch_apply / eval_write / test 各段独立 `wait_for`，spec 可配）；超时原因写 `infra_failure_detail`（如 `grading_test_timeout_after_3s`）                                                | docker：`test_segment_timeout_real`（eval sleep 300 + test_timeout=3s → infra_failure + 超时段写明）                                                                                                                                                                                     | 与 verifiers `Rollout.scoring_timeout` 的"宽外层 + 严内层"关系在 S1-6 绑定时接线（grading 库层零 verifiers 依赖，本层无从测）                             |
| P4  | 失败归因三分与组修复   | 测(部分) | 三分归因决策树（见 manager.py 模块 docstring）；infra 族强制 reward=None 的双保险：manager 的 infra 分支**签名里没有 reward 参数**（想塞也没有代码路径）+ contracts schema 校验器拒收 infra+reward                                                                | docker：`test_killed_grading_container_real`（真杀容器 → infra_failure + reward=None）；unit：`test_killed_container_is_infra_failure`、`test_dead_workspace_is_infra_failure`、`test_p4_schema_lock_infra_with_reward_is_unrepresentable`；另有 contracts 层既有互锁用例（tests/contracts/test_grading.py）              | 组修复信号（GLM-5 规则、组装配前对后端可见）不归 manager：GroupSignal 契约在 handshake.py（S1-1），产出与消费在 S1-5 gate / S1-6 绑定                        |
| P5  | prepare/grade 竞态     | 测     | grade 不依赖 prepare（自带冷启动 `_ensure_image`）；per-image asyncio 锁去重（prepare 在途时 grade 等锁复用结果，全程只拉一次）；prepare 失败只记 `prepare_failures`，不污染缓存                                                                          | unit：`test_grade_cold_start_without_prepare_and_pull_cached`、`test_prepare_grade_race_pulls_image_once`（竞态下 pull_count==1）、`test_prepare_failure_does_not_poison_grade`（失败后 grade 自行重拉成功）                                                                                        | —                                                                                                                                              |
| P6  | 共享 snapshot 只读     | 测     | clone 模式：宿主快照以 `:ro` 挂载进容器（docker run --volume …:ro），评分只在容器私有的 /testbed clone 副本上进行                                                                                                                        | docker：`test_snapshot_readonly_real`（容器内写快照探针得 SNAPSHOT_WRITE_DENIED + 宿主目录前后内容 digest 不变 + 评分不受影响）                                                                                                                                                              | 真实 SWE 形态走 image_embedded（官方镜像自带 /testbed，容器层天然 copy-on-write，fresh 容器即隔离）；prepared snapshot volume 优化按设计文档 5.2 定案第 5 条留环境生产期（S2+） |
| P7  | 接口 backend-neutral   | 测(部分) | docker 通道是构造参数 `DockerRunner`（FakeDocker 注入即证明可替换）；per-worker 实例零共享（run_id/记账/租约各自独立）                                                                                                                     | unit：`test_backend_injection_and_instance_isolation`（两实例通道完全隔离 + 默认通道 = 真 docker CLI）                                                                                                                                                                                      | 跨进程统一池化 / 独立弹性评分池 / serverless 后端 → S5（设计原文即如此分期）                                                                          |
| P8  | 重试互动               | 测(部分) | 容器 per-grade 一次性（名字含随机 nonce），同 trajectory_id 重评也绝不复用；旧容器靠记账 gc/TTL 回收                                                                                                                                    | unit：`test_no_container_reuse_across_grades`（同 trace 两评 → 两个容器、全部回收）、`test_gc_by_trace_and_ttl`                                                                                                                                                                             | verifiers `run_with_retry`（新 trace_id）的真集成在 S1-6/S1-8 验（本层无 verifiers）                                                                   |
| P9  | 评分环境同等隔离       | 测(部分) | 网络策略唯一来源 = `SandboxLease(purpose=grading)`，schema 层锁死 deny_all（想开网得先改契约），docker 参数由租约推导出 `--network none`；评分私有材料（eval 脚本/cleaned patch）只写入评分容器——manager 根本不持有 rollout 容器句柄                                          | docker：`test_grading_network_isolated_real`（容器内 /dev/tcp 出网实测 NET_BLOCKED + 租约 evidence）；unit：`test_grade_resolved_end_to_end` 断言 docker run 参数含 `--network none`；contracts 层：purpose=grading + 非 deny_all 不可表示（tests/contracts/test_sandbox.py 既有）                             | 非 root / cap-drop / seccomp 等 5.1 硬化随 S2 安全 Runtime 统一做（S1 评分容器 run_as_user=root，租约如实记录）；prewarm 防泄漏约束豁免（prewarm 未启用容器预热）    |
| P10 | 镜像并发拉取分档       | 测(部分) | 第一档（预拉取）：`prepare()`/`_ensure_image` 镜像缓存 + per-image 锁；`image_pull_seconds` 计时（本地命中记 0.0）                                                                                                                  | unit：`test_grade_cold_start_without_prepare_and_pull_cached`（第二次评分零拉取）、`test_prepare_grade_race_pulls_image_once`；docker：`test_grade_resolved_real` 断言 image_pull_seconds==0.0                                                                                                | 第二档 registry mirror / 分布式镜像缓存是多节点规模问题 → S5                                                                                        |
| P11 | 评分队列反压           | 测     | `GradingQueue` 有界（**并发 4 / 队列 8 默认，可配置**，F5 用户版）；打满策略 = block_submitter（阻塞提交方 = 反压 rollout 准入）；每次打满产出 `BackpressureEvent`（reason_code=`grading_backpressure_queue_full` 可直接进 EligibilityReport.reason_codes）；排队等待从 submit 起计时进 `GradingTimingRecord.queue_wait_seconds`，`backpressure_triggered` 旗标随报告落盘 | queue：`test_f5_defaults_and_configurability`（默认 4/8 + 参数校验）、`test_queue_full_emits_backpressure_event`（打满 → 事件字段全断言 + 旗标传导）、`test_concurrency_is_bounded`、`test_queue_wait_seconds_measured_from_submit`、`test_queue_with_real_manager_fake_docker_propagates_facts`（整链传导进真 GradingReport.timings） | 积压超阈值的另两种策略（defer 评分 / 降级 audit_only）留 S2+ 按实测数据选型；S1 取最保守的阻塞策略，事实字段已齐                                              |

## 故障注入四类（任务验收项）实测结果

| 注入                       | 期望                                             | 结果 | 用例                                                                 |
| -------------------------- | ------------------------------------------------ | ---- | -------------------------------------------------------------------- |
| 杀评分容器（eval 段 rm -f） | infra_failure，reward=None，trace 不丢           | 通过 | docker `test_killed_grading_container_real`（+ unit 桩版）           |
| 篡改测试文件               | hygiene 降级 rejected_test_tampering，封顶 unresolved（即使剥离后测试全过，f2p_pass=1 仍 reward=0） | 通过 | docker `test_tampered_tests_downgraded_real`（+ unit/hygiene 各一版） |
| 日志不可解析（标记在、内容垃圾） | test_log_parse_failed（infra 族），reward=None   | 通过 | docker `test_unparseable_log_real`（+ unit 三个变体：零测试/缺标记/parser 异常） |
| 队列打满                   | BackpressureEvent 产出 + 阻塞提交方 + 旗标进 timings | 通过 | queue `test_queue_full_emits_backpressure_event`（纯 asyncio，无需 docker） |

附加污染注入（A7 条 4）：grader-only 路径未跟踪新文件 → `rejected_forbidden_contamination`
（docker `test_contamination_downgraded_real`）。

## 本机验收证据（2026-07-07，darwin arm64，docker 29.4.1）

- 行为验证镜像：`rh2-s14-grading-fixture:v1`（python:3.12-slim + git，本机构建，
  `Architecture=arm64`，Id `sha256:7a5be9fe66ee…`）——**未拉取任何 x86 SWE 官方镜像（U-D）**。
- 全套：`cd rh2 && uv run pytest -q` → **399 passed**（含本任务新增 53、并行 S1-3 的 32）。
- docker 标记单跑（留证）：

```text
$ uv run pytest -m docker -v
tests/grading/test_manager_docker.py::test_grade_resolved_real PASSED    [  9%]
tests/grading/test_manager_docker.py::test_grade_tests_failed_real PASSED [ 18%]
tests/grading/test_manager_docker.py::test_grade_patch_apply_failed_real PASSED [ 27%]
tests/grading/test_manager_docker.py::test_tampered_tests_downgraded_real PASSED [ 36%]
tests/grading/test_manager_docker.py::test_contamination_downgraded_real PASSED [ 45%]
tests/grading/test_manager_docker.py::test_unparseable_log_real PASSED   [ 54%]
tests/grading/test_manager_docker.py::test_killed_grading_container_real PASSED [ 63%]
tests/grading/test_manager_docker.py::test_segment_timeout_real PASSED   [ 72%]
tests/grading/test_manager_docker.py::test_orphan_sweep_real PASSED      [ 81%]
tests/grading/test_manager_docker.py::test_snapshot_readonly_real PASSED [ 90%]
tests/grading/test_manager_docker.py::test_grading_network_isolated_real PASSED [100%]
===================== 11 passed, 388 deselected in 11.92s ======================
```

- 跑完后宿主零残留：`docker ps -a --filter label=rh2.grading.owner` 为空。
- F5 计时实测样本（fixture resolved 一次）：image_pull=0.00s、env_reset=0.25s、
  prep=0.13s、test=0.17s、total=1.08s、container_peak_memory=13.06MB
  （cgroup v2 `memory.peak` 在 Docker Desktop VM 内可读）。

## 8 题真实 SWE 评分回归（递延声明）

远程 GPU/x86 实例仍关机（与 S1-2 远程回归同因，见 implementation-notes S1-2 条目），
"8 题经 manager 评分与 S0-7 结果一致"的真实回归**递延到 S1-7a 前与 S1-2 的远程
回归同批执行**。本机已钉住的等价面：

1. `build_swe_grading_spec` 对冻结 bundle 的接线单测（镜像/base_commit/eval 脚本/
   官方测试文件名单/parse_log 绑定，`test_build_swe_grading_spec_wiring` +
   `test_swe_spec_parse_log_binds_private_bundle`）；
2. 官方 parser 对 8 题 428KB 真实日志的回归（S1-2 已入库，
   `tests/envpack/test_scoring_regression.py`）；
3. manager 全链路行为（本页 fixture 全套）。

远程回归判据：8 题走 `image_embedded` 模式（官方镜像自带 /testbed@base，血缘核验），
逐题对照 S0-7 的 resolution/apply_ok/reward。
