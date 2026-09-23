# 09-19 链路修复：Production Tracer 有界复核

审查基线：`bac7659ea70cc07a3a8c872a29e7659a894afc5a` 加 2026-09-19 未提交实现。复核期间六个关键源码文件摘要未变，见 [production_probe_result.json](production_probe_result.json) 的 `source_sha256`。

**本切片没有新增当前阻塞项。** 日志全文释放、两处取消账本、正式 grader 的 `--init` 参数接线已闭合；派生镜像在两次评分之间同 tag 重建时，旧资格已失效。R5 的构造器到 manager 运输已接通，正式配置加载仍是作者已披露的流水线待办，不能标为完整闭合。运行途中同名 tag 被重指只登记为非阻塞条件性残余。

本报告不复审 P-A 因果/训练语义、P-C/P-D 或反作弊政策。环境资格已由用户确认；真实记录待流水线产出，不新增 T0 或审批。没有 SSH、真实 Docker、GPU、HTTP/API 调用；未改生产源码、维护测试或共享文档。

## 证据及边界

- [窄回归](pytest.log)：**29 passed，9.49 秒**。完整 `tests/adapters/test_replay_grade.py`，grader profile 参数、setup/candidate 顺序、两种取消日志、初始化失败清理、scope 无法终止与关闭预算、创建期取消等必要生命周期回归；均为 CPU 替身。
- [独立探针](probe_production.py) / [执行输出](probe.log) / [结构化结果](production_probe_result.json)：真实 `prepare_for_replay` 产物、真实 host-private/manifest 读取和 digest 检查、真实 attempt registry、真实 `GradingQueue` 与 frozen-delta `SWEGradingManager`。Docker 使用维护 fixture 的替身；日志 parser 使用当前真实实现。
- 为遵守本切片禁止 API 的边界，actor 探针从 `BringupService` 原文件抽取并执行 **原 AST** 的 `PreparedTaskFace.load` 调用、`_resolve_grading_spec` 和 `_grading_submit`；没有启动整个 actor、adapter HTTP 服务或模型。探针明确区分正式默认路径与构造器注入正例，不把手工注入说成配置已接通。
- `runtime/` 与 `pytest_tmp/` 是当前探针临时产物，包含日志和 ledger，未作为新增提交材料；摘要与结论在上述 JSON 中。可从仓库 `rh2/` 运行 `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/chainfix_review_20260919/production/probe_production.py` 重建。

## 真实调用链与旧问题闭合范围

正式配置为 `RH2_EXECUTION_MODE=fa_formal` 加 `RH2_PREPARED_TASKS_DIR`、manifest SHA、host grading path/SHA。`bringup.py:1140` 调用 `PreparedTaskFace.load()`；`prepared_task_face.py:407–417` 读取三份产物后调用构造器。`bringup.py:1760–1766` 按本次 attempt 的 authoritative registry 取 `grading_spec()`，`generate.py:2756–2759` 对单个 attempt 缓存同一 spec，`generate.py:5245–5252` 原样交给 `BringupService._grading_submit()`，后者 `bringup.py:1807–1810` 交给 queue→manager。默认评分并发仍来自 `RH2_FA_LIMIT_GRADING`（默认 4），队列为其两倍；本修复未增加 owner 或 retry。

| 原问题 | 本轮核实结果 | 证据 |
| --- | --- | --- |
| R5 构造器→评分材料运输 | 已接。`PreparedTaskFace(..., qualifications=)` 按 task_id 保存在 host 侧，`grading_spec()` 472 行传给 helper；不进入 rollout task public spec。probe 从真实 driver/manager 写出的 CPU noop ledger 用 `load_env_qualifications` 取得资格，构造器注入后，经原 resolver→submit→真实 queue/frozen manager，spec 与 sidecar 都为 `ok:<source>`，正常分数仍为 1。 | `constructor_transport_positive`；不等于完整 actor 配置已接。 |
| R5 正式配置→构造器入口 | **部分闭合，已披露待办**。`load()` 无资格参数，bringup 六个 load 参数也无资格来源；probe 的原 actor load→实际 caller 得到 spec/sidecar 均 `absent`。 | `formal_default`；下节 P-1。 |
| 派生 tag 重建沿用旧资格 | 原反例已闭合。`replay_grade.py:481–486` 将 inspect 的 `.Id` 传给 `image_local_build_id`；`grading_image_identity` 使用该 ID。正常 ID A→资格 ok；同 tag 在新一次 inspect 前改成 ID B→`image_identity_mismatch`。 | `stable` / `rebuilt_before_inspect`。 |
| 评分收口后保留全文 | 已闭合。`manager.py:1822–1833` 在容器 scope 清理的内部 `finally` 清空 `record.eval_log_partial`，不删引用/候选事实。独立 probe 两条各 1,049,933 字节日志已持久化，`_records` 中无 sentinel 全文，report 和解析计数保留。取消路径亦清空。 | `formal_default` / `constructor_transport_positive` / `cancel_post_observation`。 |
| 派生 inspect 期间取消缺 ledger | 已闭合。row 先建，`replay_grade.py:473–476` 落 `cancelled:derived_image_inspect` 后原样传播。probe 用事件准确停在 inspect，仅 1 条 ledger，0 次容器创建。 | `cancel_derived_inspect`；维护原反例亦通过。 |
| 后观测取消把完整日志误标 partial | 已闭合。`replay_grade.py:623–625` 取现有候选事实。probe 用事件停在 post observation，完整日志摘要与账本一致，`partial=false`，仅 1 条账本且原样传播取消；manager 容器已清理、全文已释放。候选 exec 期间取消的 partial=true 旧行为由维护回归覆盖。 | `cancel_post_observation`，`pytest.log`。 |
| grader `--init` | 参数接线已闭合。正式 profile 从 `sandbox_profile.py:582` 带 `--init`，manager `_start_container()` 2018 行使用该 profile；probe 经原 caller/queue 到 manager 的全部 grader run 都含 `--init`。仍为 root 的 init/sleep 容器主进程，测试经现有 candidate uid exec；租约登记、scope 有界终止和 fatal 通道未另建分支。 | `all_container_runs_have_init=true`；生命周期 CPU 回归通过。孤儿实际回收/dvc 真机改善由主审远端证据裁决，本切片不声称已实测。 |

## P-1：R5 正式资格加载仍未实现（既有披露，非新增阻塞）

**可达性：** `production_reachable`，上述真实正式入口必走 `PreparedTaskFace.load()`；该函数不会消费资格。负样本遗漏发生在之后的 P-A 全局失败分支，不能把“现在安全地 absent”当成正式功能完成。当前 CPU 正常测试在 absent 下仍为 1，未观察到正常结果被本接线改坏。

**处置：** `deferred_with_owner_and_gate`。owner 沿用 Claude 的评分接线与流水线实施者；在项目宣称正式 P-A 已启用之前，用真实记录接通并验收。用户已确认环境资格，不重开决定、不阻碍当前环境处理。

**最小修法与验收：** 复用现有 host-private/题包身份绑定，把流水线冻结的每题资格通过 loader→构造器传入；无需让 actor 临时扫描所有历史 ledger。验收从真实启动配置提供产物，走 load/resolver/queue/manager，匹配记录为 ok、镜像或脚本变化为 mismatch、缺席保持 absent；另加带有效资格的真实 startup/collection 负例运输。已有构造器正例可以保留，但不能独自核销加载点。

**方案五问：** ①旧正式入口确实无来源；②上述接线恢复本来缺失的负样本资格，不是新增拒绝分类；③无需新增 owner、状态机、retry 或 fallback；④fail-stop 会停止本可正常评分的任务，删除 P-A 则丢失已批负样本能力，当前先延后接线即可；⑤正常测试不变，只有已批准 P-A 且资格有效的全局候选失败由未确定进入负样本。代码和 CPU 接线验收成本低，真实环境资格记录产出成本不由此虚估。

## P-2：inspect 之后同名 tag 被重指（条件性残余，非当前 P1）

**反例：** driver inspect 返回 ID A 后，外部将同 tag 指向 ID B。当前 `replay_grade.py:483` 只设置资格 ID，`spec.image` 仍是 tag，候选容器 `replay_grade.py:304–305` 也从 ctx 取 tag；manager run 同样用 `spec.image`，`manager.py:2273–2274` 对 local_build 跳过实际容器镜像检查。探针模拟这个合法 Docker 外部事件，两个 run 都使用 B，ledger/sidecar 仍记录 A 且旧资格 ok。它只证明身份窗口，没有伪造无效内部对象，也没有证明实际训练误归因。

**可达性与处置：** `conditional_future`：若后续流水线允许评分期间并发重建/重指同名 tag。当前作业没有实际发生或计划这种变更的证据，不能仅据替身将它升级当前阻塞。建议 `no_fix_accept_residual_risk` 于本轮；并行镜像构建若成为正式能力，再由原 driver owner 收口。

**最小修法与验收：** 如要支持该并发能力，候选容器与 grader 都直接使用已经解析的 immutable image ID，原 tag 仅作观测记录；无需额外 owner、锁、监控或恢复协议。同 tag 在 inspect 前重建仍使旧资格失效；在 inspect 后重指则两个容器继续使用 A，或按明确的身份检查拒绝错配。CPU 一个双时间点对照即可核实接线；不要求重跑全题或真实 OOM/GPU 矩阵。

**方案五问：** ①旧入口存在同一 tag 窗口，原“下次评分前同 tag 重建”的已知反例本次已修；②pin 两次 run 的 ID 解决根因；③新增 owner/state/retry/fallback 均为 0；④当前接受运行期 tag 不变即可延期；未来若支持并发重指，局部 pin 比整进程 fail-stop 更小；⑤无并发重指时评分及训练分布不变，仅使日志身份与实际镜像一致。成本低，但本轮没有为它延迟主线的证据。

## 停止条件

本切片已足够结束：五项收口与派生资格常规失效正反例通过，正式加载缺口按已披露流水线边界保留；仅登记运行期重指 tag 残余。不扩成整个 actor、全部镜像或反作弊审计，不要求重跑已对上的全题库。主审只需结合其它切片与其负责的远端证据裁决整批。
