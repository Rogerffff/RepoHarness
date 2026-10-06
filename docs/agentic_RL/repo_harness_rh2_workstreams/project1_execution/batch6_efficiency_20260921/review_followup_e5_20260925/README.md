# R1–R6 修复与 E5 实施聚焦复核

2026-09-25，Codex。复核 `ee0ae702`（#5 / E1）、`0ef2e617`（网络 / E2-E4 设计修订）、`6526839f`（E5 无 GPU 部分）。主仓库 HEAD `6526839f63e71915c055309f309ec14081668d21`；miles fork `275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`。B 的任务、评分、manifest 等未提交改动只读，未代为修改或提交。

**结论：#5 R1/R2、E1 R3 可以收口；网络 R4 和 R5 的宿主控制方向已修正，补下述测试段前导即可按已批方案实施；E4 R6 的 Brief 通过。E5 配置 / CPU 等价 / G1 三态主干通过，但评分速率有一项生产接线遗漏 EF1 / P2，需要本片补齐。** 没有新的 T0。

| 对象 | 裁定与边界 |
| --- | --- |
| #5 R1：字面 EOS | accepted / fixed：由真实 capture wire 发布末尾采样 ID 事实；不是探针手工发布事实后只测 parser |
| #5 R2：悬空调用 | accepted / fixed：旧的正文误报与“有效调用后跟悬空片段”漏报均改判；只接受已声明的窄语法覆盖，不宣称完整坏调用检测 |
| E1 R3：初始化观测 | accepted / fixed：正常和初始化后的真实期限取消都经过编排与 audit writer，已执行阶段保留、未执行阶段缺席 |
| 网络 R4：root pip | accepted / fixed in design：候选 UID 与现有 I1 入口对齐；尚未实现联网，不称运行验证通过 |
| 网络 R5：放行与收口 | 宿主断网核对后起第二 exec、三个终点、共享期限的方向接受；NS1 补测试 shell 的可信前导与实际 parser 验收 |
| E4 R6：记录退役 | accepted / fixed in design：完成顺序、GC 快照、leases、无日志启动失败、内存范围均已写清；实现后按已列反例验收 |
| E5 | 配置与计算路径证据通过；EF1 修掉“缺评分 producer 却报零”的观测错误后收口本机部分；GPU F1–F8 保留 |

## 1. EF1 — P2：正式 miles 路径没有评分摘要，收尾行却让报告显示有效评分为 0

**当前行为与位置。** [launch.sh](../../../../../../rh2/experiments/miles_gpu_spike/launch.sh) 第 445 行配置 `Rh2MilesGenerateFn`；[generate_fn.py](../../../../../../rh2/src/repoharness2/adapters/miles/generate_fn.py) 第 214 行直接调用 `rh2_custom_generate`。带 `grading` 的 `record_event` 仍只由旧 [bringup.generate](../../../../../../rh2/src/repoharness2/adapters/slime/bringup.py) 第 3074 行调用。正式路径关停时仍会向同一文件写入 `shutdown_started/completed`。

新 [run_report.py](../../../../../../rh2/src/repoharness2/adapters/miles/run_report.py) 第 1006–1018 行只判断 `if bringup`，随后将没有的 `resolved/trusted_zero` 计数取默认 0。因此运行中没有文件时是未知，出现两条关停行后反而变成有效评分 `0 / 小时`，并且没有缺评分证据的 reason。

**证据与可达性。** `production_reachable`。读取完整生产入口，执行真实 `Rh2MilesGenerateFn` 类体、旧包装正控、真实事件 writer 与报告函数；昂贵 rollout、身份 / canonicalize 为明确替身，时间窗人为设为一小时。不是实际模型成功率或机器吞吐测量。

| 探针形态 | 调用评分摘要 writer | 报告有效评分 |
| --- | ---: | --- |
| 正式 miles 包装，两次返回 reward 1 / 0，尚无关停行 | 0 | `None` |
| 同上，加真实关停 writer 写出的两行 | 0 | count=0、每小时=0、每 GPU 小时=0，reasons 为空 |
| 旧包装正控，真实评分 writer、同样两个结果 | 2 | resolved=1、可信零分=1、total=2 |

[探针](tracer_production_grading_probe.py) / [结果](tracer_production_grading_probe.json)；主审在 [main_grading_recheck/](main_grading_recheck/) 独立复跑一致，并额外输入有效评分行验证总数为 2。

**违反的不变量 / 影响。** E5 已批准“缺观测不是零”；该路径让新指标系统性失真，无法用它判断评分吞吐。它不把训练 reward 改成零，也不改变当前 loss / 组准入；故为 P2，不上升为训练语义 P1。旧 reward facet 也依赖该 producer，应共用修复，而不是另造第二个评分数据源。

**建议修法与分期。** 本轮 E5 收口前修，不等 GPU：通过真正会被每次 execution 调用的审计出口保存评分摘要，再让报告按明确 execution / attempt 身份和 train/eval 平面聚合；可扩现有 audit writer，无需新日志平台。不要直接照搬旧 `service.record_event` 对 session 的查找和全列表扫描。无评分记录时保持未知，即使同文件已有 shutdown 行也不能填 0；有部分评分记录时说明覆盖量，不把部分观察当完整总体。若暂不接 producer，应将该指标明确标为未采集，而非宣称 E5 已提供有效评分速率。

**最小验收。** 走实际 miles 包装 / 编排出口完成一个成功评分、一个可信零分，以及一个 infra 无 reward；再补 eval attempt 和只有 shutdown 行的输入。前两者计入，infra/eval 分列，生命周期行不创造零分或评分分母。重评分、多训练行不得把同一次有效评分重复计数。无需全池或 GPU。

## 2. NS1 — P2 设计补充：第二个 exec 必须保留来源脚本的 shell 前导

**位置与范围。** [网络 Brief §4.2](../network_supply_brief_20260924.md) 第 63–67 行携带 exported 变量、函数、cwd 后直接执行测试尾部，并声称 Start/End 标记与 parser 不变。`export -p / declare -f / pwd` 不携带来源 shell 的 `set -xo pipefail`。当前 SWE 的官方标记是冒号命令 `: '>>>>> Start Test Output'` / `: '>>>>> End Test Output'`，依赖 xtrace 才进入日志。

**证据。** `conditional_future`，联网分段尚未实施。用真实 `getmoto__moto-6913` bundle → 当前 renderer → 两段本机 Bash → 真 `spec.parse_log` / `manager._parse_eval_log`；只把真正的测试命令替换成确定性 PASSED 文本，没有运行任务或 Docker 网络。

| 形态 | Start/End 标记 | 解析 |
| --- | --- | --- |
| 原单 shell 正控 | 齐全 | 18 项，manager 接受 |
| 只携带 export / function / cwd | 全缺 | 0 项，`test_log_parse_failed / official_bad_codes_after_successful_replay` |
| 第二段显式恢复来源 `set -xo pipefail` | 齐全 | 18 项，manager 接受 |

[探针](falsifier_two_exec_markers.py) / [结果](falsifier_two_exec_markers.json)；主审[独立复跑](main_marker_recheck/falsifier_two_exec_markers.json)一致。这不是当前离线评分回归，也不需要通用 shell 序列化。

**实施约束与最小验收。** 测试 exec 保留该来源 renderer 的可信前导，不照搬作者 Bash 夹具的 `set -u`（此前 pandas 激活钩子已证明不兼容）。将真实 renderer / parser 的上面对照列入分段验收即可；cwd 用 `cd` 恢复，不是字面 `source` 三个文件。新 HOME 下先建状态目录；区分安装命令非零但原 shell 继续、shell 提前退出和状态写入失败，沿用既有 P-A 归因，不由携带文件或 marker 重新定义 reward。携带的脚本按候选 UID 执行，只是候选状态，不作为可信完成证明。

保留已列三终点：安装未完成、撤网失败、取消 / 期限到点时不得意外启动第二 exec；安装 / 撤网 / 测试消费同一剩余预算。R2E 无安装段做一项正控。Brief 的旧“单 shell / root 放行文件 / 轮询”词句同步删掉，避免实施者照旧段落写回去。

**开工边界。** 1A+2A 与继续推进已经获批，上述具体接线不需要用户再批准“允许实现 grader 联网”。补入 NS1 后即可按片实施；正式作业启用、实际政策与运行配置仍按原约定另行安排。本轮没有启用网络。

## 3. 已通过的修复证据

### #5：真实 capture wire，而非辅助 publisher 替身

[主审探针](probe_parse_capture.py)使用本地已有 Qwen3.6 tokenizer，真实 RH2 HTTP adapter、真实 capture wire、真实解析与轨迹记录；只有引擎按请求返回固定 ID。六个 session 并发交错：真实 EOS、普通 token 拼出的 EOS 字面量、正文提到标签、完整调用后跟悬空片段、单独悬空片段、正常工具调用。

[结果](probe_parse_capture.json)：旧的三个反例全部改判；采样 ID 与 logprob 原样，六条捕获各 commit 一次、无 pending / draft 残留，`eos_fact_missing=0`。因此 R1/R2 的停止条件满足。未重新测模型发生率、真实 CC 行为或多模型 adapter；仍按现有单服务 tokenizer 归属与已声明窄语法支持。

### E1：正常与期限取消均到最终 JSON

[主审探针](probe_e1_transport.py)走真实编排与 audit writer，资源和模型为已有测试替身。[结果](probe_e1_transport.json)：正常结束保留 bootstrap / launch；bootstrap 完成后期限取消保留 bootstrap、launch 缺席，harness exit=-1、hit_by=harness_outer。缺失阶段不补零。复用分支移除 `git config --system --add` 接受，R3 收口，不再扩查整条启动链。

### E4：R6 的具体退役约束足够进入实现

完成顺序、GC 快照 / 遍历后裁剪、活动与未确认删除记录保留、leases 随记录退役、无日志启动失败例外、累计数与有限历史分开、内存平台期限定在容器历史，均已写清。现有 B 串行消费者不需要新 ack 协议。E2 §1.5 第 3 项残留“等 §1.3 T0 决定”，与修订后的权限归类矛盾，删除旧文案即可；root 的可信 PATH 修复继续与 B E09 顺序落地。

## 4. E5 已验证的主干与剩余边界

- `launch.sh` 仍默认诊断，效率只追加 `--use-rollout-logprobs`；P12 是新增的配方兼容检查，不是训练样本准入闸。应按此准确报告“挡板变动”，不能让“无新增挡板”掩盖确实新增了配置拒绝。
- 对照当前 miles actor / model / train_async：额外 forward 条件、路由 fill / train_step / exhausted、训练与发布的时间线字段相符。G1 效率档最多 NOT_APPLICABLE，不借缺对拍取得 PASS；诊断缺对拍仍缺证据、效率出现对拍仍报矛盾。
- 原样加载作者 CPU 等价脚本，只把 `OUT_DIR` 指向[本轮目录](cpu_equivalence/)重跑，历史证据未回写。结果 `all_checks_pass=true`：真实 fork 函数体、两步、末级 / 非末级 PP 的受测 loss / 梯度 / 参数与 replay 消费相同；额外 forward 毒化不改变训练量；两份 dry-run 参数表只差一个开关。模型 / 优化器 / 分布式 / GPU 与 router 内部状态仍是明确替身边界，不能把它当八卡验收。
- `startup_evidence.json` 的进程内 final args 已写；当前 report / judge 仍只读 `run_manifest.json`。这是当前支持入口范围，未来正式 launcher 必须接同一证据；此处没有报告“两个 source 当前必冲突”或新增强制启动器。
- 效率档 judge / launch 非零退出已明示，暂不另挡本片；写正式作业入口时应区分“G1 不适用”和作业失败。首轮完整 G1 仍诊断档，GPU F1–F8、I18、心跳、逐阶段显存和采样器按原分期。
- 复杂度提醒（非阻塞）：不再把纯观测不足一概扩成配置拒绝。例如 `save_debug_train_data` 本身只是保存现有数据，少了诊断 `log_probs` 列应明确其能力，不代表 faithful DIS 不可训练。新增配方时优先核真实消费者，避免继续堆 YAML 关键词扫描和独立参数镜像。

## 5. 验证、修改范围与停止条件

- #5 / E1 / 既有启动收集四个维护测试文件：**96 passed**，含本机 Docker 用例。
- 集成 fork 下 E5 三文件与 I21 bringup 纵切：**67 passed**。未跑全库或完整双 lane，不引用共享树 manifest 的总数作为本轮证据。
- `python3 rh2/experiments/miles_gpu_spike/g1_acceptance.py --self-test`：PASS；相关源码及本轮探针用 `rh2/pyproject.toml` 的 ruff E9/F 检查通过。源码 diff whitespace 检查通过。
- 生产可达性核查按审查标准 §10.4 用一对 tracer / falsifier，主审独立复跑关键反例并裁决。A / D / E / F / G / H / I / J / K / L / M / N 见各节；B/C 只核本批未改 reward / mask / 组准入，P12 的配置拒绝如上报告，不扩成算法审计。
- 本轮只新增审查 / 探针工件、各 Brief 的回链及共享账本追加；不改生产实现、运行配置、维护测试 oracle、fork 或 B 在制品，未提交 / push、登录机器、发跨任务消息或启用网络。
- **停止条件**：#5 / E1 不再反复展开；E4 按 Brief 实施。E5 补 EF1 的实际评分运输及缺证据反例后收口本机部分。网络将 NS1 写进实现与验收即可继续，不再为已批政策增加用户确认。真实训练数值、路由与性能继续留既定 GPU 作业。
