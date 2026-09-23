# 预算终止闭环：错误来源与停止分类窄审查

日期：2026-09-09。角色：Production Tracer。范围：Owner Brief §6 四项、批 A 的错误分类、批 D 的 grader 停止结果；不审预算时钟，不改源码、不提交。核对对象为当前工作区；收口时主仓库 HEAD 为 `297f1f59`。

**结论：支持正式执行链中的四项改为 FATAL，但 Brief 需先做三处窄修正：typed 码不能自动代表已归因的 task-local 故障；两条已经映射的 capture 账实矛盾不能照旧 ABORTED；最终停止仍未知不能只记普通 grading infra。它们均可按已有 D1/A4 落实，无须再开一轮 T0。** 旧测试只能证明旧实现行为，不能覆盖后续 owner 定案。

## 1. 四项的真实来源与限定范围

| 项目 | 当前来源与生产可达性 | 判断与例外 |
|---|---|---|
| `fa_identity_incomplete_in_formal_mode` | `adapters/miles/generate_fn.py:144–150` 在调用编排前铸造身份；`identity.py:248–255` 将完整六字段写回输入。`adapters/slime/generate.py:2654–2666` 是非 `s1_compat` 路径的残缺身份守卫。正确正式入口本来不会触发；触发意味着绕过入口、接线或身份损坏。未在真实作业观察到此故障。 | **支持 FATAL，已有 D1。** 不再伪造一个身份不足的 ABORTED 成员。`s1_compat` 本来豁免，保持不变；错误名称虽然含 formal，现有守卫也覆盖 `fa_audit_only`，实施时应明确模式范围，不借机改兼容路径。 |
| finalize 前逃出的 `ValidationError` | `generate.py:3849` 的 `SandboxLease`、`:4009` 的 `WorkspaceHandle`、`:2709–2721` 的 launch/proxy 契约、`:2852` 的 drain receipt 等均由控制面事实构造；当前 `:3456–3467` 仅因阶段较早就转 ABORTED。 | **支持当前 generate/adapter 执行链内的 FATAL，已有 D1/06 §2。** 它未必每次都是“内部代码 bug”，也可能是必需配置或外部事实不合法；共同点是尚未被证明为可恢复的局部故障。不是全仓所有 Pydantic 错误一律 fatal。候选测试/工具输出中的错误文本不属于此入口；可选 telemetry 内已自行消化的校验失败也不扩大（如 `generate.py:2006`）。 |
| `frozen_artifact_persist_failed` | `generate.py:3187–3207` 的 `put_artifact_bodies` 失败；可能是文件系统 I/O、权限/空间问题，也可能是被宽泛 `except Exception` 包住的内部异常。`FinalizationStoreConflict` 已另走 FATAL。 | **支持 FATAL，A4 明文已经覆盖 patch 持久化失败。** `06` 的 A4（`:42`）与 W3a（`:142`）明确要求核心记录失败不交付、停 run、仍清理，取代旧 B5 失败表的 artifact 持久化失败 missing 分支。不要同时扩大为所有 exporter task-local 读取故障必然 fatal。 |
| `sampling_mask_tape_missing_in_assembly` | `generate.py:2951–2965`：会话已请求 `return_sampling_mask`，叶链引用的 TurnTape 却无支持集。真实 wire 在 `capture_wire.py:1198–1213` 先解析，再由 `:727–741` commit 给 hook；hook 在 `generate.py:875–908,979–990` 落 tape。正常生产链不会把合法缺失送到此守卫；触发说明支持集事实丢失或路径不一致。 | **支持该装配守卫 FATAL，已有 D1 的 mask/引用一致性原则。** `top_p=1` 或未开启 mask 的会话不走此检查。引擎 abort 且零输出的合法豁免返回空 `TurnSupport`，不是 `None`（`sampling_mask_assembly.py:247–252`），不应改成 fatal。只改此守卫不等于已覆盖 wire 上游全部错误来源。 |

四项 FATAL 都应保留原始异常及 stage，先通知停止，再继续 session/scope/container 清理；不能只换 exception 名称后仍让 miles 收到 ABORTED。

## 2. F1：批 A 的 typed 白名单仍会掩盖配置、完整性和内部错误

- **行为/位置**：Brief `README.md:36–37` 将 materialize 的整批 typed 码与 CLI 引导 `RuntimeError` 统一保留为 ABORTED。
- **违反的不变量**：06 `:116,182–194` 只允许“已归因且未形成 present 的 task-local 故障”进入 ABORTED；typed 只代表有名称，不证明根因或作用域。
- **证据**：`rollout_testbed_lineage_failed`（`generate.py:3934–3943`）同时覆盖探针命令失败与“命令成功、基线血缘错误”；`rollout_image_digest_mismatch`（`:4136–4144`）同时覆盖查询失败、空/非法结果与真实 digest 漂移。`ClaudeCodeDriver._install_native_cli` 的版本不匹配明确抛 `RuntimeError`（`bringup.py:324–332`）；批 A 若将整段引导的 RuntimeError 包为 `harness_bootstrap_failed`，会把版本画像失效改名后继续丢组。
- **影响/可达性**：`production_reachable`。真实 `Rh2MilesGenerateFn → rh2_custom_generate → _generate_attempt → materialize / ClaudeCodeDriver.run` 可到达这些来源；错误发生在模型取得写权前，不能解释为模型策略失败。若只影响部分镜像，持续丢该类任务也未必触发 no-progress。
- **复现**：小 CPU 反例使用真实 `evaluate_probe` / `_verify_rollout_image_digest` 和 Docker 结果替身，证明 exit=0 的错误血缘与真正 digest 漂移都进入当前失败判据，见 §5。
- **分期/验收**：批 A 开工前修表。保留真正局部、已识别的服务/传输/容器运行故障 ABORTED；配置不合、完整性矛盾及尚未归因异常按既有原则 FATAL。对一个混合原因码，应在真实抛出点区分来源，不能只补一个大白名单，也不能反向把所有 materialize 非零退出都定成结构损坏。至少覆盖“错误 CLI 版本”“成功查询但 digest 不符”“已识别局部运行故障”三个不同结果。

## 3. F2：两条“已映射 capture 族”正是 I05 已要求补齐的漏网分支

- **行为/位置**：Brief `README.md:39` 写“已映射 capture 族码不变”；`outcome_producer.py:61–62` 已将 `leaf_facts_length_mismatch`、`capture_record_unknown_in_backfill` 映射为 `capture_incomplete`，随后 `generate.py:3534–3579` 返回 ABORTED。
- **不变量/证据**：`generate.py:2896–2912` 分别是“我方树侧事实条数与叶链数不相等”和“叶链引用的记录不存在”。第二组 `batch2_failures_20260908/README.md:13,25–32` 已将这类事实/引用矛盾列为现有 D1 的 FATAL，不能用是否已经在表中代替来源分类。
- **影响/可达性**：`production_reachable`，但本轮未做真实作业复现。真实叶链装配入口具备这两条守卫；若分支轨迹才触发，ABORTED 丢组会掩盖接线错误并选择性排除这类轨迹。
- **复现/分期/验收**：批 A 即处理；用真实装配入口配一条已知错配引用或长度事实，断言 typed FATAL、原始证据留存、没有返回 ABORTED、清理继续。不能只把两处裸 RuntimeError 测试换成 typed 故障后宣称 I05 已闭合；其它合法 capture 不完整原因不因此一律改 fatal。

## 4. F3：grader 最终停止未知必须进入 fatal 通道，同时保留已安全停止的例外

- **行为/位置**：Brief `README.md:74` 在 rm 失败或容器仍在时，只将 `container_stop_unconfirmed` 加进 `cleanup_failures` / `infra_failure_detail`。当前 `manager.py:1214–1243` 把普通 `GradingInfraError` 返回为 `failed_to_grade`；`:1410–1424` 清理不确认停止，且 `_container_running` 将 inspect 失败压成 `False`。
- **违反的不变量/证据**：06 A4 `:42` 与 A5-c `:62` 已定 execution scope 无法终止为 run-fatal；第一组 `batch1_budget_20260908/README.md:83` 已明确直接落实，不让 owner 重选。评分超时且安全收口才可保留为普通 grading infra / DROP。
- **影响/可达性**：`production_reachable`。路径为正式 `_finalize._grade → grading queue → manager.grade → _exec_bash_checked timeout → finally _remove_container`；若测试进程仍运行或 Docker 状态不可知，普通 failed_to_grade 会让后续任务继续占用资源。
- **复现**：计划中的 FakeDocker timeout/rm/inspect 即足以验证异常传播，无需再跑 GPU。必须区分“rm 首次失败、后续已安全停止”与“有界收口结束仍 running/unknown”。
- **分期/验收**：批 D 修正。后者沿既有致命基础设施错误通道向编排/关停传播，继续做有界清理，不能只附加文本。检查失败不是“容器不存在”；已明确停止也不等于已删除。第一次 rm 非零不自动 fatal，随后确认安全停止/移除时保留真实诊断；不能推翻 I13 对中间等待超时但最终安全收口的已批例外。验收应有 running、unknown、安全停止三种结果及主调用链是否停止的断言。

## 5. 本轮验证与停止条件

只读核对了以上来源与既有决策，未执行 Docker/GPU、未修改实现或旧测试。一次临时 CPU 探针运行 `uv run --no-sync python`，实际输出：

```text
probe_transport_succeeded_but_lineage_invalid: True False
digest_check_collapses_query_failure: 1 False
successful_inspect_real_mismatch_reason: rollout_image_digest_mismatch
```

此前合并探针尝试导入 mask 模块时因当前解释器未配置 `miles` 路径而中止；未安装依赖。随后缩小探针为不需要 miles 的上述三项并成功退出。mask 零输出例外来自源代码核对，不冒充运行验证。

停止条件已满足：四项来源与例外已核对，批 A 与批 D 所需窄修正已交主审。不要求重审全仓、不增加通用分类平台、不扩大 T0。主审独立裁决后即可把收窄后的 Brief 交 Claude 实施。
