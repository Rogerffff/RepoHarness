# Production Tracer 原始报告（2026-09-16）

结论：本轮新 P-A producer 有两处实质缺陷，均能通过现有报告、gate 与 admission。driver 已支持资格账本，因此当前可达；正式 actor 的资格来源尚未接入，actor 侧污染风险须标为条件可达，不能声称正式训练已被污染。另有因果关联反例交由 Training Semantics Reviewer 主报。本报告不重开 e1、P-B 或 S1 unsafe 通道决定。

审查对象是 HEAD `bac7659ea70cc07a3a8c872a29e7659a894afc5a` 加工作区未提交内容；实际读取文件的 SHA-256 见 [snapshot.json](snapshot.json)。未修改源码、维护测试、共享主文档或历史 evidence；未执行 SSH、Docker、GPU、模型 API。以下验证均为本机 CPU，Docker/模型输出使用仓内维护测试的既有替身。

## 1. 新 finding

### PR1 / P1：资源事实不可读仍被当作已排除资源终止

- **当前行为：** `manager._read_resource_facts()` 对读取失败返回 `None`；`_decide_execution_failure()` 随后把 `oom_kill_events=None` 折为 0、把 `container_oom_killed=None` 当 false，且缺少 `RH2_TEST_RC` 时 `signal_exit=False`。这些未知事实从未进入 `missing`，只要其它条件齐备就继续复证并产出 `candidate_execution_failed / 0.0`。
- **违反的不变量：** 实施计划 §8 F2 对这一窄全局失败分支规定，必要归因事实不足应保持未确定，不能冒充已证候选失败。此项不要求正常已有可信测试结果必须有内存指标，也不改变正常分数。
- **位置：** `rh2/src/repoharness2/grading/manager.py:2867–2897`、`:2944–2957`、`:2984–2999`。
- **证据：** [production_probe_result.json](production_probe_result.json) 的 `resource_unknown`：cgroup 与 Docker OOM 字段均为 null，报告仍为候选 0 分、`clean_grading.ok=true`、`KEEP_FULL`。`resource_and_rc_unknown` 再移除测试退出码，结论相同。正对照 `positive_control` 提供已知正常资源事实，负对照 `no_qualification_control` 得 infra / None / DROP_GROUP。
- **训练影响：** [group_transport_result.json](group_transport_result.json) 使用实际 `reference/miles-rh2-integration` HEAD `4c04f997b60fd08c36941d8715db06bfc0ed0543`。prepared registry → actor 编排 → manager → finalization → gate → canonicalize → `DefaultDataBuffer.put/get` → conversion 后，资源未知的候选 0 分与正常 1 分成员一起进入 `raw_reward=[1.0,0.0]`，两个 `loss_masks` 均非零。对照不注入资格时整组丢弃，`drop_admission_reward_scope_none=1`，没有 recycle。
- **可达性与分期：** `production_reachable` 于 `scripts/replay_grade.py run --qualification-ledger …`；正式 actor 是 `conditional_future`，条件为接入环境资格。属于本轮 producer 新增路径，应在继续依赖已归因 P-A 结果/接通 actor 资格前修正；不是 P0，也不是已有训练污染证据。资源观测失败的实际发生频率未知，未做真机 OOM 或 daemon 故障实验。当前 sidecar 能看到 null，但下游依然信任报告。
- **复现：** 从 `rh2/` 执行 `.venv/bin/python ../docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/batch4_scoring_20260910/implementation_review_20260916/production/production_probe.py`，及同目录的 `group_transport_probe.py`。
- **最小验收：** 同一候选/失败日志，在“资源正常已知、已证资源终止、必要资源事实未知”三组中分别得到候选 0、infra None、未确定 None；未知项具名进入诊断，不做候选归因复证；真实报告运输与组过滤保持相应去向。只限制 P-A 归因分支，不能扩成所有正常样本的额外内存闸门。无需新 owner、状态机或重试。

### PR2 / P1：内存编译复证仍会导入候选仓库中的 `json.py`

- **当前行为：** renderer 在工作目录下运行 `python -`，第一行 `import json, sys`。Python 可从当前仓库导入 `json.py`。候选模块会执行，能影响 `json.loads`、输出或 builtin；“不 import、不执行候选代码”的承诺不成立。新代码虽未再调用 `py_compile`，但仍保留了上轮 F3 指出的同类导入问题。
- **违反的不变量：** 实施计划 §8 F3 要求复证对源字节作内存编译，避免从仓库导入复证模块；不能把执行候选代码的输出当独立 SyntaxError 证明。本项不是要求解决 §9.6 的全部 stdout/运行器攻击，也没有扩大权限边界。
- **位置：** `rh2/src/repoharness2/grading/manager.py:1001–1035`，尤其 `:1013–1017`；`prepared_task_face.py:292–295` 直接复用此 renderer；`manager.py:2986–2999` 仅以 error_paths 非空接受证据。
- **证据：** `production_probe_result.json` 的 `compile_local_clean` / `compile_local_json_shadow` 实际运行 renderer 生成的 shell。合法 `src/thing.py` 在无遮蔽时只输出 OK；加入合法根 `json.py` 后，候选模块写出了无害 marker，证明被执行，同时打印伪 `RH2_COMPILE_ERROR=src/thing.py:SyntaxError:…`。脚本退出 0，合法目标随后仍编译成功并输出 OK。`json_shadow_transport` 把这个实际 stdout 送入正式编排与 manager，仍得候选 0 / clean gate / KEEP_FULL。
- **影响与分期：** 能把未证明的全局失败标成候选 0 分；合法同名模块若缺 `loads` 或导入抛错，也会让本应得到 0 分的语法失败变成无 reward。属于 P-A 新增复证器的局部回归，应在继续依赖该复证/接通 actor 资格前处理。普通仓库顶层同名模块的频率未知；恶意构造可稳定复现。driver 为 `production_reachable`，actor 为上述资格条件下的 `conditional_future`。当前 stdout/sidecar 有错伪混合信息，但没有独立校验。
- **复现：** 与 PR1 的 `production_probe.py` 相同。探针不改解释器、site-packages 或测试运行器，仅在临时仓库写两个合法 Python 文件。
- **最小验收：** 真实 SyntaxError 仍被识别；合法源码加缓存路径冲突保持干净；顶层 `json.py`、`py_compile.py` 等同名候选模块不会在复证时执行、不会制造伪错误或写 pyc。复证仍以候选 uid/HOME、同一目标解释器运行并受现有期限限制；不通过提权或新增长期服务修正。本轮未预设具体实现。

## 2. 生产入口、配置与所有权

| 路径 | 已核实的调用与事实 |
| --- | --- |
| 校准 driver | `scripts/replay_grade.py:49–68` 从 CLI 读 prepared/private、grader profile 与 `--qualification-ledger` → `load_context` → `ReplayGrader.replay_one:424` 构建 spec、注入本题资格 → 候选容器冻结、持久化、有界清理 → `SWEGradingManager.grade:1404`（`workspace=None`，输入只有 frozen delta，期限在提交时计算）→ 报告、日志与账本。CLI 整批 finally 调 `manager.close()`。driver 本身不训练。 |
| 正式 actor 任务面 | `BringupService._resolve_grading_spec:1760` → attempt registry → `PreparedTaskFace.grading_spec:433` 核派发、环境 digest、view revalidation → `build_grading_spec_from_host_view:298`。此真实入口未传 `env_qualification`。helper 参数与测试注入不等于 actor 已接线。 |
| 正式评分 | `generate._finalize` 中 `_grade:5222` 建立评分期限 → `bringup._grading_submit:1788` → 有界 `GradingQueue.submit/worker` → manager。队列 concurrency 来自 `RH2_FA_LIMIT_GRADING`，capacity=2×concurrency；manager 配置显式注入独立 grader profile。 |
| 报告至训练 | manager P-A 三路 → `GradingReport` → `generate._reward_input:4963` 逐值形成 RewardFacts → `governance.wrapper.finalize_rollout:133` / gate（`gate._dim_clean_grading:435` 按 outcome 判 infra）→ `generate.py:3615` 形成 Outcome → `derive_admission_payload` → miles `admit_group:361`。有效候选失败为 unresolved / reward 可用；infra 为 `grading_infra_failure` / reward 不可用。组层全员 KEEP_FULL 且非零方差才能消费。 |

所有权简图：driver 是单个 `asyncio.run` 进程，ReplayGrader 持候选容器与账本，manager 持 fresh grader 容器。正式运行中 actor/编排 loop 持 attempt、finalization 与评分队列；固定 queue worker 调 manager，manager 的 `_records`、P-A 诊断及清理仍由本次评分持有。模型 adapter 独立线程只负责 session/model-call 面，本轮没有向该线程引入 P-A 可变状态。容器内 root 执行 trusted setup/控制面布置，候选 uid 执行测试与 compile 复证；Docker CLI I/O 是外部边界。

## 3. 交接给主审的既有缺口与边界

- **正式资格来源：已承认、未完成。** actor 不注入资格，所以所有进入 P-A 全局失败钩子的正式样本均为未确定/None。`tests/adapters/test_batch4_pa_transport.py` 手动构造带资格的 task，不能作为正式配置真实性的证明。本轮 integration 探针也明确标注了实验注入，不冒充生产已接入。
- **派生镜像身份：主审已接收为上述资格缺口的 P2 补充。** `grading_image_identity:972–973` 用 `local_build:<image ref>`；`replay_grade:443–459` 已取得实际 `.Id`，但只送 baseline runtime identity。相同 tag 重建后旧资格仍可能有效，不能等同于“同一镜像 digest”。只做源码追踪，没有重建镜像实验；原 manifest digest 分支不受影响。
- **因果关联反例：由 Training Semantics Reviewer 主报。** 本组 `unrelated_local_failure` / `unrelated_error_transport` 提供独立运输证据：实际 pytest 因未修改测试的缺依赖报错，失败日志无候选 `src/unused.py`；未导入的 unused.py 有语法错误，最后仍候选 0 / KEEP_FULL。避免主报告重复计算 finding。
- **构建切片 F4：已登记尚未实施。** 段末安装码仍只作与资格基线的偏离判断，不能当实际构建命令的充分证明。
- **e1 §14.2 余项仍在源码：** `_records` 仍保留完整 `eval_log_partial`；派生 `.Id` inspect 仍在 row 建立前且不捕取消；取消账本 `log.partial=True` 仍硬编码。保持原 owner/gate，不把它们重复写成新回归。主审决定其与 e2 已跑事实如何收口。
- **安装/测试共预算：** candidate test exec 仍受同一 `spec.test_timeout_seconds`；安装+测试拆预算属于已登记 A2，未把建议 900+1800 秒描述为已实施。
- **已批准边界：** P-B 默认 glob 移除、S1 unsafe 永久拒绝/整组 DROP、P-A 参考全缺席走三路均按已定范围理解。stdout/conftest/安装后运行器攻击是 §9.6 已知待决策族，本报告没有代替用户裁定。

## 4. 验证与停止条件

本轮新增两个独立脚本，均退出 0。第一脚本 6 个完整编排案例，每条均恰好 1 次评分提交、1 条 receipt、grader 容器移除；本机 shell/pytest 对照用于验证证据本身。第二脚本比较两个 n=2 组：资格注入组 2/2 进入训练 conversion，无资格组 0/2 进入，均无 recycle。每个样本身份经 prepared registry/canonicalize/实际 buffer 对账；没有发起模型或 GPU 工作。

维护测试命令（从 `rh2/`）：

```sh
.venv/bin/python -m pytest -q tests/adapters/test_batch4_pa_transport.py tests/adapters/test_w1b_prepared_task_face_v2.py tests/adapters/test_replay_grade.py tests/grading/test_w3b_grader_profile_unit.py
```

新鲜结果：[maintenance_tests.txt](maintenance_tests.txt)，**72 passed，0 skipped，0 xfailed**。包含 profile setup/权限、取消日志、timeout、cleanup run-fatal、driver 写盘失败与清理、资格账本、P-A 正负与资源终止等已有用例。全通过不否定上面两个新反例。未重跑作者全套测试、e1、441 parser 语料或真实 Docker；queue full/restart/crash 没有因本轮代码而改变，未在本子任务重新注入，不作全系统韧性通过结论。

维度覆盖：A/G/D 以两入口、真实报告运输与 caller 配置核实；B 以有效 mask 和整组去向核实；E 对照指出维护测试未覆盖资源未知与仓库导入；F/H 核对 §8 F2/F3 和资格身份；L 核对期限、队列有界与已知全文保留；M 核对 sidecar/账本事实和取消遗留；N 固定 integration 树 HEAD 与本机解释器版本。C/I 将未接资格、F4、e1 余项分期，不新增授权闸门。J/K 不提纯风格意见，也不建议新状态机；本轮发现均落在已有 A/B/D/E/F/G/N 维度，无需修改审查标准。

停止条件：主审裁决 PR1/PR2 与语义 reviewer 的因果归因问题，之后只复核对应最小正反例和真实运输。正式 actor 资格入口及派生镜像身份另按既定流水线 owner/gate 收口。已通过的 P-B/P-C/P-D 与 e1 不因本报告重新开审。
