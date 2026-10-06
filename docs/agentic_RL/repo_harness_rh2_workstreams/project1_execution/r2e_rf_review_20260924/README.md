# R2E R-f 真机对账独立复核（2026-09-24）

**结论：R-f 通过本轮限定验收，可以结束本轮评分接线验收、转入环境流水线与正式 actor 接入。** 没有发现推翻本批判分的 P0/P1。原始 96 次运行完整，94/96 与参考逐键相同；唯一不同任务 numpy `2f4a9650` 的资源问题已由单题诊断说明。不能把该题在默认资源下的 gold=0 当作有效训练负例，也不能把本报告解释为 48 题均已获得环境资格。

本轮保留三个非阻塞更正：numpy 资源下界文案、镜像 ID 变化原因、对账工具的 M3 自核范围；另有 pandas 退出码等小修。它们不要求重跑 48 题、不需要新 T0。远端只读检查已确认无残留容器；证据和运行输入快照均在本机，从本次验收需要看可以释放机器，实际终止仍由用户或其授权执行者操作。

## 1. 独立验证范围与结果

主审检查镜像、快照、共享初始化差异、耗时和现场事实；两个独立上下文分别核原始评分证据与旧 F1/F2 工具修复。全部生产代码、维护测试与原始运行证据保持不变。

| 验证面 | 证据与本轮结果 |
| --- | --- |
| 原始账本完整性 | 全池 noop 48、gold 48，题目集合与可信输入一致，无重复/缺题；另核代表题 12、numpy 放宽资源 2、最终错误对照 3，合计 **113 行**。本地化的 10 份账本副本只改日志/sidecar 引用，未改变结果 |
| 来源规则独立重算 | 从固定 vendored 上游源码 AST 提取纯函数，未依赖 RH2 parser 或 `reconcile.agree`；重读 **336 份参考日志**，核 M3 的 96 行及旧参考账本 144 行的日志摘要和 reward。无账本矛盾 |
| 全池结果 | noop **48 个 0**；gold **45 个 1、3 个 0**。coveragepy `016af5f6`、datalad `58ba5165` 的两个 0 与已知来源结果一致；numpy 的一题新分歧如下。正常 96 行均无 stage_error、infra、partial 日志，runner 摘要前后一致 |
| 逐键状态 | 全池 **94/96 一致**；两条差异均是 numpy `2f4a9650` 的 `TestSavezLoad.test_big_arrays`：本批 FAILED、参考 PASSED。代表题 **12/12**、numpy 放宽资源重跑 **2/2** 一致 |
| P-A 与超时 | coveragepy 的语法错误候选，有同镜像/脚本/资源条件的临时资格 → `candidate_execution_failed/0`；无资格 → `test_log_parse_failed/None`；文件末尾 sleep → `grading_deadline_exhausted/None`、partial 日志、候选段未完成。日志位置与编译复证均为 `coverage/inorout.py:466`。资格来自本批 noop，参考完整，并非要求 gold 得 1 |
| 派生镜像 | 48 份 facts、覆盖表和 bundle 互核；对保存的 base/derived 文件清单重新执行六类完整性比较，**48/48 通过**；HEAD、隐藏测试树与 runner 摘要正确。全池 96 次实际 image ID 与最终覆盖表一致 |
| 工具与当前树 | 旧 F1 状态混淆及 F2 同目录写覆盖关闭，runbook 原三处已改。工具维护 **3 passed**；主审在当前树复跑 R2E adapter 相关 **25 passed**、miles 组级 **2 passed**。未重新跑全量套件或新容器 |
| 远端现场 | 用户给 SSH 后只读核验：x86_64、388 文件 `sha256sum --quiet -c` 退出 0，`docker ps -a` 为空；根盘 193 GiB，已用 128 GiB、可用 46 GiB。现场 image descriptor 见 §3 |

证据：[独立逐行核验摘要](evidence_agent/summary.json)、[逐行结果](evidence_agent/row_results.json)、[P-A producer 对照](evidence_agent/contrast_producers.json)、[工具审查](tools_agent/README.md)、[主审镜像/快照/耗时](provenance_results.json)、[远端只读事实](remote_facts_20260924.json)。

## 2. numpy：已定位资源差异，撤回“3 GiB 足够”的写法

**P2 文档/后续配方问题**，位置：`r2e_grading_wiring_20260920/runbook_rf.md:91`。

实际对照只支持两组条件：

| grader 资源 | noop | gold | 含义 |
| --- | --- | --- | --- |
| `/tmp=1 GiB`、内存 `4 GiB` | 0，140/142 | 0，141/142 | `test_big_arrays` 报无法写入 2,147,583,648 字节；这是已知环境假阴性 |
| `/tmp=6 GiB`、内存 `12 GiB` | 0，141/142 | 1，142/142 | 与参考逐键一致；两项资源同时变化，尚未测最小充分配置 |

不能把“单个数组约 2 GiB”换算成“3 GiB 的 /tmp 就够”：该版本 `_savez` 先写临时 `.npy`，再复制进 `ZIP_STORED` 的 `.npz`，临时文件在复制结束后才删除。源码推断两个副本的有效载荷合计已经略大于 4 GiB，另有格式和运行开销；这不是新做的 3 GiB 实测。修后运行记录的内存峰值也约 4.3 GiB。

建议将 runbook 改为**已验证配置 6 GiB / 12 GiB，最小配置待流水线测量**。按用户既有决定将此题的 tmpfs 与内存配方登记到环境流水线，不改全局默认值、不加自动把磁盘错误改判 infra 的新规则。进入有效训练池前先处理此配置；环境资格要绑定实际采用的条件。[源码与 profile 证据](evidence_agent/numpy_source_and_profiles.json)。

## 3. 镜像身份：本次观察成立，原因解释需要更正

**P2 文案问题**，位置：实施计划 R-f 段“重建即换 image ID”及 runbook §7。

Claude 正确记录了本次六张代表镜像重建后 `.Id` 改变、旧覆盖表被拒的事实；但“config 的 created 每次改变，因此重建一定换 ID”的解释与原始 build.log 相反。

- 六题两次构建的 **`exporting config sha256:…` 均未变化**。
- 改变的是 `exporting attestation manifest` 与 `exporting manifest list`，覆盖表中的旧/新 ID 分别等于旧/新 manifest list 摘要。
- 现场 `docker image inspect` 的 `Descriptor.mediaType` 是 `application/vnd.oci.image.index.v1+json`；`.Id` 与这个 OCI index 的 digest 相同。旧 index 现场已不可 inspect，故不冒称取得其旧 `Created` 字段；config 字节身份不变由两次 build.log 的同一摘要证明。

以 coveragepy 为例，两次 config 都是 `sha256:fd67cac710e0281d003573ae302e3a0dcbc79bc2891d60dc4a9a222ab1257883`，index 则从 `36ef6054…` 变为 `2020169d…`。不要把此构建器/存储模式的一次行为写成所有 Docker 重建的规律。

**运行规则不用改**：始终以目标机器实际 inspect 结果绑定覆盖表及临时资格；tag 重指、身份变化后重新核对。当前按 ID 启动和旧身份拒绝保持正确。[六题构建摘要](provenance_results.json)、[现场 descriptor](remote_identity_20260924.json)。本轮不建议新增稳定 ID 算法或放宽资格匹配。

## 4. 工具收尾与小文案

旧 F1/F2 已关闭。一个**非阻塞 P2** 留给 Claude：`reconcile_r2e.py:77–86` 用全部 M3 加 `--old-root` 日志的 reward 集合核对 M3 账本。若 M3 自己的账本/日志都为 0，而旧来源为 1，当前会误报“M3 账本与其日志矛盾”；若账本 reward 全为 null，则可能因空集合 `all(...)` 被标为 True。应只用对应 M3 日志自核 M3 账本，跨来源差异另列，没有有效 reward 则未知。当前固定语料未触发，独立重算也确认本批无真实账本矛盾；**不影响 94/96 的验收结论**。[真实 CLI 反例与修法](tools_agent/README.md#2-p2参考账本互核混用了不同来源的参考日志)。

其余顺手修正文案/维护即可：

- 代表题表 pandas `19c5eea5` gold 的 `rc=0` 应为 **rc=1**，仍然 155/155、reward=1。这正说明 R2E expected-map 可以期望 ERROR，退出码非零不等于判分失败。
- runbook §4 的总体一致应写三条件，补“观测状态映射逐键相同”；实现已做到。
- 92 分钟、两进程、各 48 次，对应每个进程平均约 **1.9 分钟/次尝试**；若把 noop+gold 算一题的累计 worker 时间则约 3.8 分钟。原“3.5 min/题/进程”单位混淆，勿用于后续容量估算。
- 可信 setup 占 grader 时间的主要结论成立：按仓库中位约 59%–90%，orange3 的 grader 总时长中位约 153 秒、setup 136 秒。当前计时是整个 setup 段，不能直接等同于孤立测得的 chown 耗时，也未证明严格线性关系。
- 锁元数据写入失败可遗留空 `.build.lock`，仅为低优先维护注；可将说明写入纳入既有 finally，无需新增锁恢复系统，不阻塞本轮。

## 5. 代码版本与集成边界

本批远端运行的是给定的 **388 项快照**，并非当前 `9379af1d` 之后的所有公共链路实现。当前有 20 个文件与快照不同：19 项可精确从 `d4a11940` 取回；一个组级测试含当时 R2E 的 fx 参数，逆转随后 A 新增的两个 driver 可选参数后摘要匹配。R2E 的评分、parser、driver 与两份验收工具仍与运行快照一致。

主审已把 388 项逐字节按原摘要重建并归档到本机 `runs/r2e_rf_review_20260924/verified_input_snapshot.tar.gz`，归档后再读一遍逐文件验证。归档 SHA-256：`955c371e3fc6427e386ea0cf3485af7ecd75987aebf97d700ac8206fef57d7e7`。这份归档只保存本地运行输入，不改工作树或历史 evidence，不代表把敏感资产/镜像上传远端仓库。

A 后续的解释器注入和宿主日志收集不纳入本次真实运行通过声明；当前相关 CPU 维护测试已过。正式 R2E actor 还需将冻结后的派生环境身份送入任务面，声明 `.venv` 激活脚本/解释器前缀，并经真实 CC 子 shell 求解验证。按共享初始化的实际变化先做少量冷镜像对照，再决定是否扩大，不机械重跑全部 48 题。

## 6. 收口与下一步

1. **R-f 可以收口**：本批完成了真实 RH2 固定补丁/来源规则对账与纯 pytest 的 P-A/超时对照。numpy 的默认资源缺口作为明确后续项保留，结果不合并改写为“默认条件 46/48”。
2. **Claude 做窄收尾**：更正 §2–§4 中的文案及 M3 自核范围；不改变评分语义、题目、expected、全局资源默认或训练准入。
3. **B 线流水线**：numpy 的资源配方与两个既知来源缺陷进入按题处理，形成实际环境资格；再做题目质量、反作弊和模型任务价值判断。本次临时资格只服务机制验证。
4. **正式 actor 接入**：派生镜像/题包身份与 `.venv` 开发条件接好后，选少量任务经真实 harness 验证；不把 driver 的 `--image-overlays` 当成 actor 已经接通。
5. **机器**：现场无残留容器，原始证据已回传且输入快照可重建。当前剩余工作不要求继续占用这台机器，建议结束租用；本次审查没有执行终止操作。

审查矩阵 A–N 的适用性：正确性、错误归因、并发工具、来源依据、反例/回归、producer 运输、版本与成本均有上述证据；算法/loss、模型训练质量、真实 actor、安全对抗完备性不在本批新增范围。沿已有批准边界分期，不新增门槛。生产代码未改、未提交或推送。
