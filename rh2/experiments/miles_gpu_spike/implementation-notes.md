# 租前终审 B1~B4 修复记录（2026-08-28）

规格权威：codex 租前终审复核（B1~B4 四条阻断 finding）。范围铁律：只修 B1~B4，
不扩展 F1/F2/F4/F5，rh2/src 核心零改动；miles 侧允许最小结构化事件 commit。

## 修复落点总览

- **miles 侧**（reference/miles-rh2-integration，分支 rh2-integration-v2）：
  新 commit `52040081a`（`[rh2-integration] structured G1 acceptance events +
  integration-tree identity assertion`），已按流程归档为
  `docs/.../miles_spike/patches/0004-*.patch` 并同步 manifest
  （expected_tree=`56ab24a5b...`，新表 `rh2_patches_g1`）。
- **rh2 侧**（未 commit）：`g1_acceptance.py` 全量重写 collect/扩展 judge、
  `launch.sh`（B3 runtime env + B4 preflight/post-run）、`thresholds.md`
  两个新判定键、`data/eval_smoke_prompts.jsonl`、新测试
  `tests/adapters_miles/test_g1_acceptance_events.py`、
  `scripts/miles_integration_lanes.sh` patch 表校验扩展、manifest 计数同步。

## 设计决策（T1，实现后报告）

1. **事件通道形态**：miles 新模块 `miles/utils/rh2_event_log.py`，按
   `MILES_RH2_EVENT_DIR` 门控 append 每进程一个 jsonl（未设即全 no-op，
   上游行为零变化）。事件写失败只告警一次不崩训练——证据缺失在 judge 端
   fail-closed 成 INCOMPLETE，这正是设计的失败面，训练不为证据 IO 抵命。
2. **applied 的独立事实**（B2）：`train_one_step` 只在真实
   `optimizer.step()` 成功后置 `optimizer_step_applied=True`，并同时输出
   Adam state `step` 计数与 scheduler `num_steps` 前后值；judge 用
   `optimizer_step_progress_consistent` 交叉验证（applied ⇔ Adam +1 且
   scheduler 前进）。NORMAL 枚举彻底退出 applied 判定。
3. **current_version 的独立事实**（B2）：`train_actor` 开头输出
   `train_rollout` 事件，取 `weight_updater.weight_version`（trainer 权威
   计数），staleness = 该值 − 逐 turn 最旧数值行为版本。
4. **消费与正控**（B2）：`train()` 逐 step 输出各 DP 分片消费的全局
   sample index（step 对分片是连续切分，动态均衡只在 step 区间内重排——
   已对 `get_data_iterator` 源码核实）；judge 新增
   `positive_control_must_be_consumed_by_applied_step`：正控组须全部样本被
   消费且 ≥1 样本落在 applied step。零方差组判定改用同一消费面。
5. **logprob 对拍来源**：trainer `compute_log_prob(store_prefix="")` 在
   top-p replay 下走 `use_rollout_sampling_mask=True`（support-renorm），与
   捕获侧 support-normalized behavior 同口径，因此对拍在 trainer 侧逐样本
   直接可算（`logprob_compare` 事件），不需要动 rh2/src 的 loss 模块。
6. **发布语义区分**：驱动侧补 `weight_publish_skipped` 显式事实——
   全 SKIPPED 区间"有意不发布"（版本保持=PASS）与"发布证据缺失"
   （INCOMPLETE）从此可区分。
7. **B3 钉死机制**：`$MILES_ROOT` 置 runtime `PYTHONPATH` 首位；launch
   preflight 用 miles 内同一函数 `miles_tree_digest()` 预计算树内容哈希，
   经 `RH2_EXPECTED_MILES_TREE_DIGEST` 下发；driver/trainer/rollout
   manager/sglang server 启动即自证，不一致 raise 停机（不等 post-run）。
   preflight 计算 digest 本身也证明目标树带 patch 0004（旧树立即红）。
8. **B4 eval 冒烟口径**：launch 增 `--eval-interval NUM_ROLLOUT` +
   1 prompt 冒烟数据（spike 数据首条，sha 预注册），末轮 train+publish 后由
   EvalDispatcher 走共享引擎 eval 路径一次，完成即出 `eval_smoke` 事件。
   这是对"worker 停止后 eval 冒烟"的解释：训练消费已结束、trainer 空闲后
   的 eval 路径冒烟；不是关掉 Ray job 之后再起新 job（那需要二次租期作业，
   不在最小闭环内）。已在 thresholds.md 检查表注明口径。
9. **B4 checkpoint reload 口径**：post-run 探针做"tracker + 迭代目录文件
   清单 digest + torch dist-ckpt `.metadata` 结构化反序列化"级别的 reload
   验证，然后删除。它验证 checkpoint 可读且结构完整，但不是完整 Megatron
   八卡 resume（那等于再跑一次训练作业）。`reload_mode` 字段如实记录口径。
10. **步内 metrics 聚合前移**：`aggregate_train_losses` 是 DP 集合通信，
    原来只在 NORMAL 分支执行；为了让 SKIPPED step 也有 dis_* 记账，聚合
    条件改为 `NORMAL or 事件开启`。outcome 全局一致（MAX 归约）且事件开关
    来自 runtime env（全 rank 一致），集合通信不会错位；NORMAL 路径数值与
    返回契约不变。

## 偏离说明

- 事件与 identity 断言合为一个 miles commit（0004）而不是拆两个：二者共享
  同一模块，拆分只会造成半个模块的中间态 patch。
- `--rollout-dumps`/`--train-log` 从 collect CLI 移除：routing tape 的
  shape/dtype/digest 改在 rollout manager 侧（numpy 在手）直接进事件，
  collect 不再依赖 torch。debug dumps 仍照常落盘，作旁证不作判定输入。

## 遗留 / 待现场校准

- dmon 吞吐、显存阈值仍是 thresholds.md 标注的机型校准位（数值校准，
  不是证据 schema 校准；schema 已无任何"首开机回填"项）。
- `resource_summary.throughput_tokens_per_sec` 取各 step 吞吐最大值作稳态
  代理（首步含预热）；如需改成"排除首 step 的均值"属阈值口径调整（T1）。

## 测试/账本状态

- lane A 138p/125s，lane B 263p/0s（manifest 已同步，含审计注记）；
- `tests/adapters/ + tests/contract_slime_async/` 321 passed 逐数不变；
- `g1_acceptance.py --self-test` PASS（代表性事件全链好例 PASS、9 类事件
  删除均 INCOMPLETE、B2 oracle 坏例与其余坏例逐一命中 FAIL）；
- launch preflight/dry-run 双 R3 模式通过（桩 asset）；坏 `RH2_REF_LOAD`
  preflight 即红（负例实测）；
- rh2 与 miles 改动文件 ruff 全过；`miles_integration_lanes.sh --checks-only`
  以新 expected_tree/patch 表通过。

---

# 租前完整审查 PR-P0-1~8 / PR-P1-1~2 修复记录（2026-08-28 第二轮）

规格权威：`docs/.../tmp/codex_miles_prerental_full_audit_20260828.md` §2/§3/§5。
范围铁律：§6 D1~D6（GPU 启动参数/实验编排）一律未动；未建监控框架/C3-C7
ledger/完整 resume；只修 evidence/oracle/launch 链路与 miles 事件发射层。
开工前逐条对照行号核实：**8 个 P0 + 2 个 P1 全部成立**（含 P0-2 的
torch.load 假红本机复现"Invalid magic number; corrupt file?"、P0-7 的 3/1
反例用真实 build_dp_schedule 复现）。

## 修复落点总览

- **miles 侧**（rh2-integration-v2）：新 commit `2fff41c95`
  （`[rh2-integration] close pre-rental audit evidence gaps in the event
  layer`），归档 `patches/0005-*.patch`，manifest 同步
  （expected_tree=`59a94d4c2...`、新表 `rh2_patches_prerental`、新字段
  `miles_source_tree_digest`）。内容：run_id 印章（P0-1）、
  `miles/utils/step_attribution.py` 真实 step 边界（P0-7）、
  replay fill/consume/exhausted 窄事件 + `consumption_snapshot` +
  `replay_sample_digests`（P0-5）、eval_smoke 带 weight_version（P0-3A）、
  `miles/utils/logprob_compare.py` loss_mask=1 口径 + length_mismatch 一等
  事实 + 训练 forward 透传 sample_indices（P0-8）、zero_signal_scan_seconds
  （P1-2）。
- **rh2 侧**（按指示未 commit）：`launch.sh`（P0-1 run 隔离 + run manifest +
  P0-4 manifest 双重钉死 + fail-closed 退出）、新 `postrun_probes.py`
  （P0-2/P0-3B，heredoc 探针拆出可测）、`g1_acceptance.py` 大改
  （collect 原子发布/run_id 校验/publish 三类事实/replay 记录/rank 记录/
  logprob 与 dis 逐样本事实；judge 新增 run_identity、
  weight_publish_conservation、queue_multiset_conservation、
  train_step_rank_coverage、logprob_alignment_and_coverage、
  positive_control_accepted_tokens、routing_replay_* 两键、shutdown 拆两键
  含 NOT_APPLICABLE 档、eval 改 post_train 绑定；self-test 新增 ~25 个
  审查反例负测试）、`thresholds.md` 键面同步、
  `src/repoharness2/adapters/miles/faithful_dis_loss.py` 逐样本
  sample_dis_accounting 事件、测试 5 个新文件 + 2 个文件扩展。

## 设计决策（T1，实现后报告）

1. **miles 侧一个 commit 而非多个**：全部改动同属"验收事件发射层"，单
   commit 便于 patch 归档与 manifest 单条目审计；上游 PR 候选时可再拆。
2. **NOT_APPLICABLE 判定档**（P0-3B）：s1_compat 的 finalization 检查新增
   第四档——不计 FAIL/MISSING、不影响总判定，但 verdict 里如实注明"此项
   不构成 F5 内存 pending draft 收口证据"。替代方案（直接删该检查）会丢掉
   fa_* 模式下 store 必须在场且空的判定面；冒充 PASS 则复刻审查批评的
   vacuous 零。
3. **探针拆成 postrun_probes.py**：heredoc 内逻辑无法被 pytest 覆盖，而
   本轮验收要求"每个假红/假绿反例都有对应负测试"。launch.sh 只保留接线。
4. **run root 语义**：`RH2_SPIKE_RUN_ROOT` 由"固定输出目录"改为"基目录"，
   run root = 基目录/run_id，已存在（哪怕为空）即拒绝。checkpoint 隔离由
   run root 唯一性自动获得（--load/--save 都在新 run root 内），未另设
   checkpoint 专用检查。
5. **replay 消费判定编码了 `--recompute-granularity full`**：backward pop
   数 == microbatch 数依赖"backward 重算触发 topk"（launch 钉死 full
   recompute；这也正是 Replay 类设 backward_index 的原因）。若下一轮改
   recompute 配置，此判定须随 thresholds 一起改——已在 §开放问题 登记。
6. **正控 accepted-token 归因走"组级事实"方案**（审查给的两选一）：由
   faithful_dis_loss 逐样本发 accepted/provenance 计数，judge 联结组与
   applied step；未采用"独占受控 step"方案（需改数据调度，超最小修复）。
7. **eval 绑定用 rollout_id + weight_version 双条件**，未加
   `--skip-eval-before-train`（审查明示留到下一轮启动配置讨论）。
8. **P1-1 选择改名**（`g1_sglang_engines_stable_across_steps`）而非补
   producer 事实：证据对象如实化成本最低；producer task 保温证据留待
   G3 生命周期实验设计轮一并定（若需要）。
9. **bash 3.2 多字节变量名坑**：`"$VAR"` 后紧跟中文标点在 macOS bash 3.2
   会被并入变量名（`set -u` 下 unbound）；launch.sh 相关位置统一
   `${VAR}`。桩环境实跑发现，属实现细节但记录以防回归。

## 偏离说明

- 无对审查 §2/§3 条款的语义偏离。§5 批次顺序按 1→5 实施，批 2 与批 3/4 的
  代码落点有交叉（同文件），提交粒度以文件为准而非批次。
- `queue_duplicate_sample_ids_max`/`unfinalized_deliveries_max` 两个旧阈值
  键被守恒/三态检查取代后删除（保留会成为无消费者的死配置；审查 §7 机械
  自检"新配置指认消费者"的反向应用）。

## 桩环境实跑证据（本机）

- `launch.sh preflight`：桩 asset 全绿；`RH2_MILES_ROOT` 指向 pin 树 →
  Ray 前红（P0-4 验收）；run root 复用 → Ray 前红且原目录零写入（P0-1）。
- `launch.sh run`（桩 ray/nvidia-smi/docker + 真 DCP checkpoint + 代表性
  事件）：全链 PASS、rc=0、postrun_status 全零。
- 审查头号反例复现：新 run 事件损坏 → collect rc=1、collected/ 未发布、
  judge INCOMPLETE、launch rc=1——"旧 PASS 洗绿新失败"结构性不可能
  （run root 唯一 + 原子发布双保险）。

## 开放问题

1. replay backward pop 判定与 recompute 配置耦合（上文 T1-5）：改
   `--recompute-granularity` 时 thresholds/judge 须同步，建议下一轮 GPU
   实验设计时把该耦合写进 D1 参数讨论。
2. `expected_dp_ranks=2`、`update_weights_interval=1` 是当前 6+2/TP1PP3
   拓扑的推导值，写在 thresholds 并标注"改拓扑必须同步改"；G2 换 4+4 时
   属 D2 议题。
3. 本机全仓回归有 15 个 docker daemon 依赖测试因本机 docker 未运行而
   skip（tests/grading/test_manager_docker.py，环境豁免非本轮引入）；租期
   机器上应回到 0 skip。

---

# 聚焦复核 3 残余 P0 oracle 缺口修复（codex_pr_p0_recheck，2026-08-28）

范围：只关闭复核文档的 finding 1/2/3（judge/collect 侧收紧），未触碰 miles
侧（生产 emitter 已逐 rank 携带 rank/dp_rank，无需补字段），未扩 §6。

## 核实结论（开工前逐条）

三个 finding 历史全部成立，且用红-绿流程二次证明：先落反例 fixture 与 11 个
负测试、对修复前 judge 实跑，其中 8 个如复核所述判 PASS（洗绿复现）；
`wrong_first_update_before`（bootstrap 在场时旧链检查可捕获）、
`all_skipped_but_update`（分支已有、只缺提交测试）、`missing_behavior_version`
（已有检查）3 个本就红，与复核定性一致。

## 设计决策（T1，实现后报告）

1. **finding 1 census 来源 = thresholds 声明**（新键
   `expected_trainer_global_ranks=6`，与 `expected_dp_ranks` 同纪律：改
   launch 拓扑必须同步改）。未采用"从事件自身归纳 census"——那正是复核
   否定的"只检查已出现事实"；事件文件整体丢失时只有外部声明能兜住。
   rank→dp 映射不做拓扑假设，只要求跨事件自洽 + dp 覆盖 0..D-1 +
   无预期外 rank（census 声明失真也红）。
2. **同 DP 副本 digest 一致性放在 source_linkage 检查**（digest 归属该
   检查语义），逐副本 multiset 相等替代 `setdefault` 取首条。
3. **finding 2 锚定实现为双向**：`update.version_before` ⇔ 本 interval
   trainer current（train_rollout 独立事实）；发布后版本 ⇔ 下一 interval
   trainer current；skip interval 同样锚定"版本保持"。bootstrap 有且唯一，
   缺 version_after 也是显式 problem。锚定只在事实在场时执行——版本事实
   缺失走既有 `weight_version_monotonic` 的 MISSING（总判定 INCOMPLETE，
   不会洗绿）。
4. **finding 3 逐项验证放在 judge**，collect 的 `behavior_version`（min
   数值折叠）字段保留：完整列表 `behavior_versions` 本就随 sample 落盘，
   judge 逐项验证（存在/可解析/<=current）后才用最旧版本算 staleness；
   折叠值仅剩展示与 logprob 同版本分组用途，不再单独承担判定。
5. **self-test fixture 拓扑升级为 6 global rank / dp=2**（train_step 与
   replay 事件都逐 rank 发），使 fixture 与 thresholds 声明的生产拓扑
   （TP1*PP3*CP1）一致——否则 census=6 与 2-rank fixture 自相矛盾。
   dp = rank % 2 是代表性映射并加注释（oracle 不假设 megatron 排序）。

## 负测试（每反例一个，fixture 与 --self-test 同源）

- finding 1：`replay_missing_rank`（少一个 rank 的全部 replay 事件）、
  `replay_missing_rank_step`（少某 rank 的一个 step 消费）、
  `replay_dp_digest_conflict`（同 DP 副本 digest 冲突）。
- finding 2：`drop_bootstrap`、`duplicate_bootstrap`、
  `wrong_first_update_before`、`next_rollout_current_mismatch`、
  `all_skipped_but_update`（补齐已有分支的提交测试）。
- finding 3：`mixed_future_behavior`（["1","99"]+current=1）、
  `nonnumeric_behavior_version`（数值+非数值混合）、
  `missing_behavior_version`（空列表，已有，纳入参数化提交测试）。

## 验证账本（本轮 fresh）

- `g1_acceptance.py --self-test` PASS（新增 10 反例检查全部命中）。
- 双 lane：A=167p/140s、B=307p/0s（manifest expected_counts 同步 +11/+11）。
- 321 硬验收：`tests/adapters + tests/contract_slime_async` = 321 passed 逐数不变。
- 全仓：默认 pin 1246p+155s（原 1235+155，+11）；integration base
  1386p+15s（原 1375+15，+11；15 skip 仍为本机 docker 未运行的环境豁免）。
- ruff 全仓过。rh2 侧未 commit；miles 两 checkout 零改动。

## 开放问题（本轮未扩大）

复核文档"触碰文件内其他问题/最小再验收"中不属于 3 finding 修复验收的项
仍开放：manifest 缺 `thresholds_sha256` 时 run_identity 仍 PASS（truthy
比较）、Ray rc1 独立负测试、launch 并发 run root TOCTOU、P0-7 生产
emitter seam、checkpoint tracker 未被探针消费（P1）。待下一轮拍板归属。

# 租前聚焦修复批：4 组 P0 + thresholds digest 顺手项（2026-08-28 第四轮）

规格权威：docs/.../tmp/租卡前claude.md（5 项清单）。开工前逐条对照源码核实，
5 项 finding **全部成立**（自证锚点：slime `trajectory.py` `to_sample()`
`index=base_sample.index` 且 canonicalize 强制叶 index==输入 index；
`sglang_engine.py` `_init_normal()` 只有 `use_rdt` 分支创建 SGLangServerActor，
broadcast 走 `launch_server_process` 子进程，`sglang_server` identity 永不发出；
`postrun_probes.py` 旧查询只有 `name=rh2-rollout`；`_judge_run_identity` 的
`if want_sha and ...` 缺失即跳过）。文中"非阻塞留下一轮"项（checkpoint tracker
iteration/TOCTOU/G3/拓扑参数）本批未动。

## 修复落点总览

- **miles 侧**（rh2-integration-v2）新 commit `0853f027b`（`[rh2-integration]
  leaf identity on the train wire + per-rank step facts + engine-actor
  identity`），归档 `patches/0006-*.patch`，manifest 同步
  （expected_tree=`ea012ae7b...`、miles_source_tree_digest=`1200dc3c...`、
  新表 `rh2_patches_focus`、lane 计数 A=186p/147s B=333p/0s）。
- **rh2 侧**（未 commit）：`g1_acceptance.py`（collect/judge/self-test 三面）、
  `thresholds.md`（identity 角色改 sglang_engine + 新键
  `g1_min_multileaf_fanout_runs` + 文档表）、`postrun_probes.py` +
  `launch.sh`（shutdown 探针 --run-id）、`adapters/slime/generate.py` 与
  `grading/manager.py`（容器 `rh2.run_id` owner label）、
  `faithful_dis_loss.py`（sample_dis_accounting 带 leaf_ordinal）、测试
  `test_g1_acceptance_events.py`(+15)/`test_postrun_probes.py`(+4)/
  `test_leaf_identity_wire.py`(新,6)/`test_logprob_compare_masked.py`(+1)/
  `tests/grading/test_manager_unit.py`(+1)/`test_faithful_dis_loss.py`(改)。

## 设计决策（T1，实现后报告）

1. **leaf 身份选薄 (sample_index, leaf_ordinal)，不改写 Sample.index**（规格
   给了两个可选方案）：ordinal = 该 agent run（run key = rollout_id，None 回退
   index——与 miles `rollout_ids` 列同一回退规则）在扁平样本顺序里的出现
   序号，由 `compute_leaf_ordinals` 单一实现供 train conversion 与
   rollout_group 证据两处调用（同函数+同顺序 = 两侧身份逐行一致的根据）。
   不改写 index 的原因：index 改写需要跨 generate 调用的全局编号协调，且会
   波及 miles 内所有 index 消费点；薄 ordinal 只加一列 wire
   （`leaf_ordinals`，VALUE_SPEC/dp 分片清单同步），rollout_id/group_index
   分组语义零改动。
2. **身份缺失 = MISSING（INCOMPLETE），不沿旧口径判**：judge 新增
   `leaf_identity` 检查消费 collect_report 的 `leaf_identity_missing` 清单；
   queue 守恒在身份缺失时也记 MISSING——纯 index 口径既会把合法 fan-out 判成
   重复消费（假红）又检不出同 leaf 双消费（假绿），两个方向都不可信。
3. **R3 联结升级为 leaf_id→digest 精确映射**：replay_fill 事件带行对齐
   `sample_indices`+`leaf_ordinals`；同 dp 副本映射必须相等、跨 dp 键不相交、
   并集 == rollout 侧逐 leaf 期望映射。fan-out 两叶 tape 对调（digest
   multiset 不变）由 `fanout_tape_swap` 反例钉死必红。
4. **fan-out 覆盖显式判定**：新阈值键 `g1_min_multileaf_fanout_runs=1`，
   check `g1_fanout_multileaf_coverage`——训练批须真实出现 ≥1 个多叶 run，
   全线性数据 FAIL。注意：launch 当前 `--disallowedTools Task` 关闭了
   subagent，fan-out 只能来自 context-compaction FORK；若真实租期 run 全程
   未触发 fork，该项会如实 FAIL——这是把 G1 数据形态要求显式化的预期行为，
   届时应调整数据/预算促发 fork，而不是回撤判定（开放问题，见下）。
5. **per-rank oracle 三检查落在新 collected 文件 `step_rank_records.jsonl`**：
   聚合面 `step_records.jsonl` 保留（原检查不动），per-rank census/链条/
   metrics 检查独立成 `train_step_global_rank_census`、
   `optimizer_state_continuity_per_rank`、`train_step_metrics_coverage` 三键。
   scheduler 精确步进需要每 step 的 num_rollouts——miles `train_step` 事件新增
   `num_rollouts` 字段（`opt_param_scheduler.step(increment=num_rollouts)` 的
   同源值）。metrics 一致性依据：`aggregate_train_losses` 在 effective_dp_cp
   组内 all-reduce，全部 pp-last rank 应携带同一份 metrics（collect 端
   `_consistent`、judge 端逐 rank dict 相等 + dp 覆盖 0..D-1）。
6. **sglang identity**：`SGLangEngine.init()` 在传输模式分派（external/
   normal、RDT/broadcast）之前 `assert_and_emit_identity("sglang_engine")`；
   RDT 专属 `sglang_server` 发射保留。thresholds 必需角色由 sglang_server 改
   为 sglang_engine（`identity_role_note` 记录未来切 RDT 时的增补规则）。
   未改传输模式。
7. **shutdown 探针**：三路 `docker ps`（rollout name / grading name /
   `label=rh2.run_id=<run_id>`）取并集去重；任一路失败 = docker_query_ok=false
   （P0-3B 语义在多查询下保持）。owner label 生产端：generate.py 与
   grading/manager.py 仅在 `MILES_RH2_RUN_ID` 在环境中时追加
   `--label rh2.run_id=...`——env 未设（全部现有单测/非 spike 链）docker 参数
   逐字节不变，这也是 321 基线与 grading 既有测试零改动的保证。
   `docker ps -a` 已退出未删容器按规格留 P1。
8. **thresholds digest 收紧**：`thresholds_sha256` 必须是 64 位十六进制且与
   judge 输入一致；缺失/空/非法 FAIL（三个反例 mutation）。

## 偏离说明

- 规格建议"最好用本 run 的 owner label"：已实现（而不只是 name 双查询），
  代价是 rh2/src 两个容器启动点各 +4 行 env 门控 label；因该改动条件触发、
  对非 spike 链零行为变化，按 T1 处理。
- `test_faithful_dis_loss.py` 既有 sample_dis_accounting 断言从两个不同
  index 改成同 index 双叶（oracle 改动，T1）：新断言严格更强（同 index 下
  仍须逐叶区分计数），旧形态被新形态蕴含。

## 开放问题（留用户/下一轮）

- 真实 G1 run 能否稳定触发 ≥1 次 fan-out（compaction fork）未经 GPU 验证；
  若首跑 FAIL `g1_fanout_multileaf_coverage`，处置应是调整 prompt/预算促发
  fork（或 owner 拍板暂调阈值并留痕），不是删判定。
- leaf_ordinal 依赖 conversion 与证据发射消费同一扁平顺序（同一 `data`
  list）；若未来 miles 改变 `_get_rollout_data` 的展平/重排位置，两处必须
  同步——已用 `test_rollout_group_event_uses_same_ordinal_rule` 源码锚点
  钉住接线，但语义上仍是单点假设。

## 验证账本（本轮）

- `g1_acceptance.py --self-test` PASS（新反例全部命中：leaf 4、per-rank 7、
  manifest digest 3；好例含双叶 fan-out）。
- lanes：A=186 passed/147 skipped（skip 全部 integration_base 豁免），
  B=333 passed/0 skipped，manifest 计数/树哈希/patch digest 同步。
- 全仓：默认 pin 1266 passed/162 skipped（原 1246/155，+20p/+7s）；
  integration base 1413 passed/15 skipped（原 1386/15，+27p）。
- `tests/adapters/ + tests/contract_slime_async/` = **321 passed 逐数不变**。
- ruff（rh2 全仓 + miles 改动文件）全过。

---

# V2 vendor refresh：per-token weight version spans 端到端（2026-08-31）

背景（adv_miles.md 反例）：sglang-miles（SGLANG_COMMIT=4e230c3d，模块
`python/sglang/srt/utils/weight_versions.py`）支持一条 /generate 跨多次权重
更新并返回逐 token 版本区间 `meta_info.weight_versions=[{version,start,end},
...]`；单数 `weight_version` 只是最后区间。只记单数会把 v10+v11 的 turn 记成
全 v11——`Sample.oldest_weight_version`（min）高估、`DefaultDataBuffer` 的
staleness=current-oldest 低报 1 个版本，可能把本应被 `--max-weight-staleness`
拒绝的组放进训练。

## wire 形态核实结论（以 sglang 源码为准，不以 adv_miles 转述为准）

gh api 拉取 sgl-project/sglang@4e230c3d 的 `weight_versions.py` +
`test/registered/unit/utils/test_weight_versions.py` +
`test/registered/rl/test_weight_version_spans.py` + `tokenizer_manager.py`
注入点核实：

- 键名 `weight_versions`（复数），每项 `{"version": str, "start": int,
  "end": int}`，半开区间按生成 token 位置计数；注入条件
  `recv_obj.weight_versions is not None`（旧引擎/未启用时**整键缺席**），
  `num_output_tokens=completion_tokens`。
- 合同不变式（上游单测逐条断言）：非空；`spans[0].start==0`；相邻
  `prev.end==cur.start` 且 `prev.version!=cur.version`（同版本必合并）；
  零输出恰一个 `{v,0,0}` 空区间；非零输出每区间 `start<end` 且末区间
  `end==生成 token 数`；版本可回归（v1→v2→v1），**不得假设单调**；
  `meta_info["weight_version"]==spans[-1].version`（单数=finalize 时刻值，
  与 FA-0 第 3 条收窄语义一致）。
- `--weight-version` 可为任意字符串（上游测试用 "base-v0"）；miles 场景为
  十进制计数器，judge 层保持 digit 校验。

## 落点

- `adapters/slime/generate.py`：`WeightVersionSpan` + `parse_weight_version_
  spans()`（fail-closed 全量校验，上述不变式逐条 + 单数交叉验证）；
  `TurnTape.weight_version_spans` + `weight_version_provenance` property
  （engine_spans / single_version_only）；hook 直调路径解析失败按既有 tape
  口径记 partial+mismatch（投影层拒收）；`backfill_leaf_sample` 把区间
  **全部**版本依序并入 `Sample.weight_versions`（oldest/min 修复主体），并
  在存在 spans 事实时挂 `LeafWeightVersionFacts` 附加属性。
- `adapters/slime/capture_wire.py`：wire 在 stage 前解析（F5 guard 区间内，
  引擎报了就必须合法——坏 spans 抛 SlimeBindingError，proxy 链 poison+
  abandon，直连链异常传播零暂存）；`PendingTurn.weight_version_spans`；
  commit 仅在场才传 hook kwarg（同 turn_support 模式）；registry
  `weight_versions[sid]` 按区间 extend（drain receipt / handshake 的
  weight_versions_seen 含全部版本，尾部仍是 finalize 值）。
- `adapters/miles/weight_version_facts.py`（新，纯 stdlib）：装配产物类型 +
  `rh2_weight_version_spans` 附加属性锚 + metadata payload 形态。
- `adapters/miles/canonicalize.py`：允许集扩 `rh2_weight_version_spans`，
  消费三闸 fail-closed（类型 / flat_versions 与 Sample.weight_versions
  两本账互检 / metadata 键双事实源拒绝），转
  `Sample.metadata["rh2_weight_version_spans"]`。
- 契约：`BackendHandshake.weight_versions_seen` 与 `WeightVersionsHandshake.
  weight_versions` **只填充语义不加字段**（description 注明 V2 起承载区间
  全部版本；FA-0 权威序列语义照旧）。staleness=current-min(seen) 与
  max_lag=max-min 自动修复，无代码改动。
- `faithful_dis_loss.py`：docstring 增交互确认——spans 只修 staleness/版本
  记账，不改 ratio（behavior logprob 逐 token 生成时刻已 faithful）；排查
  结论：rh2/miles 无任何按单版本的 DIS token/样本 gating（唯一版本准入 =
  buffer 组级 staleness；logprob_compare 的 same_version 只影响 parity 对拍
  分组，且低报修复后跨版本样本会被正确剔出对拍集）。
- miles 侧（commit 2f3786950，patch 0008 + manifest 同步）：
  `Sample.update_from_meta_info` 并入区间全部版本（miles 自有 rollout 路径
  同款低报修复，带连续性 assert）；`rollout_manager` rollout_group 事件新增
  per-sample `weight_version_spans` 列（读 metadata）。
- `g1_acceptance.py`：collect 落 `weight_version_spans` 行级列；新检查
  `weight_version_spans_coverage`（无新阈值键，纯语义）：记账列表与引擎
  一手区间证据逐项一致 + 区间结构合法 + token 覆盖与 logprob_compare 训练
  token 数交叉 + 有 mid-run 更新的 run 必须携带 spans 证据
  （single_version_only 仅在无更新窗口合法，bootstrap 豁免）；
  staleness_max_versions 逐项版本自动含区间全部版本（min over spans）。

## T1 决策（实现后报告）

1. **坏 spans 在 hook 直调路径记 partial 而非抛错**：wire 路径（生产链）
   fail-closed 抛错；hook 直调（探针/替身）与 sampling mask 同款记
   partial+mismatch——hook 的既有哲学是"只记录事实"，partial 记录被装配/
   投影双重拒绝，不产生第三种静默形态。
2. **结构化 spans 落 miles Sample.metadata 而非一等字段**：miles Sample 无
   spans 字段；staleness 语义修复完全由 `weight_versions` 本身承担（区间
   版本并入），metadata 只承载 G1/审计的 provenance 证据（metadata 不进
   训练 wire——P0-3 已证——但随 Sample 走完 buffer/rollout_manager，事件
   取证点在 wire 之前）。转换仍走附加属性+扩表 fail-closed（用户指定风格）。
3. **纯单数链不挂附加属性**：避免无 spans 的既有 321 面被迫 lazy import
   miles 包；per-turn provenance 在混合链里仍显式。
4. **judge 对 single_version_only 的合法窗口口径**＝run 内无 mid-run
   weight_update（publish updates 的 rollout_id 非 None 条目；bootstrap
   豁免）。有更新而全无 spans 证据 → FAIL（缺证据不算绿；pin-base 引擎或
   旧 emitter 的真实 run 会红——这正是"GPU 前必须吸收 spans 引擎"的强制）。
5. **相邻同版本区间判非法**：上游合并语义保证不出现；出现即证据被改写。
6. **registry 版本账按区间 extend**（去重不做）：保序保重复与既有逐轮
   append 语义一致，序列尾部仍是 finalize 时刻值。
7. **miles session/samples/merge.py 不修**（残余登记）：session 路径 spike
   不用；其 `strip_last_output_tokens` trim 发生在版本 append 之前，直接
   并入区间会把已被 trim 掉的尾段版本计入——需要按 sglang
   `truncate_weight_version_events` 语义做截断感知裁剪，超出"最小 commit"
   范围。若未来启用 session 模式必须先补。
8. **spans 总 token 与训练 token 的交叉校验**只在行有 logprob 对拍、无
   length_mismatch 且 masked>0 时强制——两个独立证据面的相等关系
   （入训轮生成 token 总数 == loss_mask=1 计数）；对拍缺失时由
   logprob_alignment 检查自己负责，不重复定罪。
9. **Outcome 的 turn_weight_versions 同步扩 spans**（generate.py 新
   `hook_turn_weight_versions()`，unsafe-artifact 两处 Outcome 记账改用
   它）：否则 `intra_execution_version_span`（max-min 派生互检，FA-0 第 2
   条）会与 Sample 侧同款低报；非 spans 链与旧
   `[r.weight_version for r in hook.records if r.weight_version]` 逐轮等价
   （record 与 tape 的单数同源同值，failed 轮两侧皆无）。

## 开放问题 / 待并行线程或后续

- thresholds.md 本轮由另一线程独占（只读）：`weight_version_spans_coverage`
  的"各键对应的检查"表格行待补（无阈值键，建议行文本见 dev 汇报）；判定
  逻辑不依赖该文档。
- 引擎自身漏报区间（该报多段只报一段）无法从事件层证伪——由 sglang 侧
  单测/GPU tests 覆盖（pin 的 SGLANG_COMMIT 已含）；judge detail 已写明
  该诚实边界。
- `_build_handshake` 的 staleness 修复未加专测（seen 内容由 backfill 测试
  锚定，current-min(seen) 数学由既有 handshake 测试覆盖）。

## 验证账本（本轮）

- 新测试：`tests/adapters_miles/test_weight_version_spans.py` 41 条
  （parse 正 6/负 18 参数化、hook 直调 3、Outcome 版本序列 helper 2、wire 3、
  backfill 4、canonicalize 5——含 adv_miles 反例的 oldest==10 端到端断言与
  低报 ledger_mismatch 红证明）。
- lanes：A=231 passed/147 skipped（190+41；skip 全 integration_base 豁免），
  B=378 passed/0 skipped（337+41），manifest 计数/expected_tree/
  miles_source_tree_digest/patch 0008 digest 全同步。
- `tests/adapters/ + tests/contract_slime_async/` = **321 passed 逐数不变**；
  全套非 miles 面 1080 passed/15 skipped 不变。
- `g1_acceptance.py --self-test` PASS；judge 红绿证明（独立复跑）：
  baseline PASS（含 8 样本跨更新多区间正向覆盖）；`span_understate`（低报）
  FAIL 且 **staleness_max_versions 同时保持绿**（低报静默的活证明——只有
  spans 一致性能抓）；`span_gap`/`span_overlap`/`span_out_of_bounds`/
  `spans_absent_with_update` 各自命中 FAIL；`no_update_no_spans` 的 spans
  检查 PASS（单版本合法窗口）。
- ruff 触及文件全过。rh2 侧未 commit（按任务要求）；miles 侧一个窄 commit
  2f3786950（patch 0008 存档 + manifest 更新）。

# V2/V3 收尾两小项：bringup 权重版本双端点探测 + thresholds.md spans 表行（2026-08-31）

## 核实结论（开工前，gh api 对钉死 commit 的一手核实）

- 钉死 `SGLANG_COMMIT=4e230c3d85cefdab5b65eeb6f6f87793a707a6fb`
  （sgl-project/sglang 的 sglang-miles 分支，v0.5.18 线；来源 =
  integration manifest `sglang_commit` / docker/Dockerfile:24）的
  `http_server.py` 真实路由：
  - `/get_weight_version`（含别名 `/weight_version`）**路由仍注册但 handler
    无条件抛 HTTPException(404 deprecated)**——比 V3 审计登记的"可能已更名"
    更确定：旧单端点探测对钉死引擎是必然 404，不是概率风险。
    `RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下 finalize 必 fail-closed 崩溃
    （单 engine 也炸）；bring-up 链则每次静默降级到历史观测。
  - `/model_info` 返回体含 `"weight_version"` 键 =
    `tokenizer_manager.config_value("weight_version")`（manager 持有的
    current，权重更新成功即推进——与旧端点同一事实源，无键名差异）。
- 引擎侧 v3 树 `sglang_engine.get_weight_version`（miles/backends/
  sglang_utils/sglang_engine.py:573-582）已是双端点探测，顺序**先
  `/model_info` 后 `/get_weight_version`**（先新后旧）。
- MilesRouter 是 catch-all 代理（miles/router/router.py:71
  `/{path:path}`），`/model_info` 经 router 可达引擎——探测走
  `sglang_url`（router 地址）无路由层阻塞。

## 落点

- `rh2/src/repoharness2/adapters/slime/bringup.py`
  `_latest_engine_version`：单端点 GET 改为
  `("/model_info", "/get_weight_version")` 双端点 fallback（顺序**对齐引擎
  侧**而非"先旧后新"——旧端点对钉死引擎必然 404，先旧只会每次 finalize 多
  烧一个死请求；注释写明 gh api 核实依据）；两端点全非 200 按末次响应
  raise_for_status，`RH2_REQUIRE_REAL_WEIGHT_VERSIONS=1` 下仍 fail-closed
  （错误消息注明双端点），bring-up 降级链（registry 最大观测 → 启动探针值）
  逐字不变；registry 交叉检查逐字不变。
- 新单测 `rh2/tests/adapters_miles/test_bringup_weight_version_probe.py`
  （4 条，真回环 HTTP server 而非 monkeypatch requests）：仅新端点（钉死
  引擎形态，且断言只发一次请求 = 顺序证据）/仅旧端点 fallback/双灭 +
  require_real=1 拒绝（断言两端点都真实试过）/双灭 + bring-up 降级语义
  锚定。红证明：stash 掉修复后 3/4 失败（降级测试双态皆绿，符合其"锚定
  不变语义"定位）。
- manifest `expected_counts`：lane A 231→235、lane B 378→382（+4，不触
  miles，双 base 均跑零 skip）。
- `thresholds.md`：补 `weight_version_spans_coverage` 表行（V2 开放项收口；
  无现成行文本落盘，按 g1_acceptance.py `_judge_weight_version_spans`
  实现写成：A/B 两分支判定 + 结构校验清单 + 交叉相等 + MISSING 档 + 诚实
  边界，证据来源两列齐）；拓扑限制登记里版本探测端点提法同步双端点。
- `router_targeting_audit.md`：§3 残余风险的更名登记项改写为**已收口**
  （保留核实事实与修复/测试锚点）；§1 调用点表、§3/§4 端点行、§5 前置
  2/7 的端点名与 bringup.py 行号锚点同步（§5 前置 2 的"逐 worker 全等
  断言"在多 engine 解锁前依旧开放，双端点落地不改变该项状态）。

## T1 决策（实现后报告）

1. **探测顺序取"对齐引擎侧"（先新后旧）而非任务给的另一选项"先旧后新"**：
   两者对三形态（仅新/仅旧/双灭）判定结果相同，但钉死引擎上旧端点必然
   404——先旧意味着每次 finalize 固定多一个死请求 + 引擎日志噪音，且与
   sglang_engine.get_weight_version 的顺序不一致（同一语义两处两个顺序，
   审计时要解释两遍）。
2. **连接级异常（如 ConnectionError）不做端点间 fallback**：同 host:port，
   第二个端点必然同样失败；引擎侧同款行为（requests.get 抛异常直接出
   循环）。失败处置仍由既有 except 分链路（正式 fail-closed / bring-up
   降级）承担。
3. **200 但缺 "weight_version" 键按整体探测失败处置（不试下一端点）**：
   与引擎侧 KeyError 直接传播同语义；对 rh2 落进既有 except 分支——正式链
   fail-closed，bring-up 降级，与修复前对坏 body 的行为一致。
4. **audit 文档登记项就地改写为已收口而不是删除**：核实出的事实
   （404 deprecated 而非移除）修正了登记时的预估，保留在案供租期镜像上
   复核对照。

## 验证账本（本轮）

- lane A（默认 pin base）：`tests/adapters_miles/` = 235 passed/147
  skipped；lane B（RH2_MILES_PATH=reference/miles-rh2-integration）=
  382 passed/0 skipped——均与更新后 manifest 逐数一致。
- `tests/adapters/ + tests/contract_slime_async/` = 321 passed 逐数不变。
- ruff 触及文件全过。未 commit（按任务要求）。

---

# vendor refresh 复核 P2 #1/#2/#5 收口（2026-08-31 第三轮）

规格权威：`codex_vendor_refresh_recheck.md`（复核终判 PASS_WITH_P2_RESIDUALS）
的 P2 #1/#2/#5 逐条验收条件；#3（零输出 judge 合同）/#4（hermetic 构建）本轮
明确不做，已另行登记。

## 修复落点

- **#1 rh2 侧**（`src/repoharness2/adapters/slime/generate.py`
  `parse_weight_version_spans`）：
  1. "键缺失"与 `weight_versions: null` 判然两分——只有键**不在场**才返回
     None 回退单数；键在场值为 null 抛 `weight_version_spans_null`
     fail-closed（pinned writer 只会不写键或写非空 list，null=账目损坏，
     不得洗成"旧引擎"）。
  2. span 的 version 必须是非空**字符串**：int/float 一律
     `weight_version_spans_version_not_string` 拒绝，删除原 int→str 宽容
     转换（writer 写入前显式 str 化，wire 上不存在数值版本）。原 reason
     code `version_unparsable` 更名 `version_not_string`（全仓无消费者，
     测试 oracle 同步——T1 登记见下）。
  3. 负例：parametrize 新增 null 行 + int 行；原正例
     `test_parse_int_version_coerced_to_str` 反转为负例。
- **#1 miles 侧**（integration tree 新 commit `63c7a94e7`，patch
  `0009-rh2-integration-validate-weight-version-spans-with-r.patch`，
  sha256 `f7ecf894…`；manifest 新表 `rh2_patches_spans_strict`、
  expected_tree=`a4b60c891…`、miles_source_tree_digest=`ef05b2ff…`）：
  `miles/utils/types.py` 的 spans 记账入口从 `if spans := get(...)` +
  assert 改为模块级纯函数 `_validated_weight_version_spans()`（ValueError
  真异常，`python -O` 不消失），补齐与 rh2 parser 同款结构不变式：null/空
  list/非 list/项非 dict/缺键/version 非字符串/边界非负 int(bool 拒)/首段
  0/连续无缝无重叠/相邻版本必不同/空段只许零输出唯一 [v,0,0)/单数
  weight_version 在场且等于末段。旧 walrus 真值判断会把 null 和 [] 静默落
  进单数回退分支——该洗绿口关死。负例 16 条 + 正例 4 条
  （`test_weight_version_spans.py` §6，integration_base 标记）。
- **#2 P11 覆写防护**（`launch.sh`）：新增 **P6b** custom_config.yaml 顶层
  键白名单——只放行现三个安全键的**精确钉死行**（与 P6 同形态），其余任何
  顶层行（P11 相关键、未知键、带引号键、`---`、重复白名单键等）一律
  preflight FAIL；同时"preflight 全部通过"从 FAIL 聚合点（原 :336）移到
  P11 (d) 之后输出——P11 也是 preflight 闭包，成功宣告不得先于它。
- **#5 文档漂移**：patches/README.md 头与表更新到 0001-0009（补 0008/0009
  行）；integration 树 `docs/developer/versions.md` 三处更新（build-arg 表
  SGLANG_IMAGE_TAG v0.5.16→v0.5.18、SGLANG_COMMIT/MEGATRON_COMMIT 空默认→
  0007 钉死值、"Bumping principle"段补本树有意偏离说明），并入 0009 miles
  commit；`router_targeting_audit.md` 5 处 capture_wire 行号校正
  （948-950→971-973、956-962→979-985、961-962→984-985×2、934-935→957-959×2）。

## T1 决策（实现后报告）

1. **reason code `version_unparsable` 更名 `version_not_string`**：语义从
   "解析不了"收紧为"必须是字符串"，旧名成为误导；全仓 grep 无生产消费者，
   仅测试 oracle 同步（float 1.5 行随迁）。
2. **versions.md 修正并入 0009 语义 commit 而非单独 patch 0010**：规格两
   选项皆许；单 commit 少一张 manifest patch 表与一次重建步骤，commit
   message 双列说明保持可审计。versions.md 第 140 行"Bumping principle"
   的"empty by default"陈述与钉死事实直接矛盾，超出规格点名的两行但属同
   一处漂移，一并修正。
3. **miles 侧不做 `end == 本次生成 token 数` 覆盖检查（诚实边界）**：
   `update_from_meta_info(self, args, meta_info)` 拿不到本次调用的生成
   token 数（`Sample.response_length` 是跨 partial-rollout 累计值；
   `meta_info["completion_tokens"]` 在 miles 自身消费里始终 `.get(...,0)`
   可缺省，且 spec-decode 下计数语义未经 pinned 源核证——错的强不变式会
   在 stock 路径制造假红）。结构不变式全量对齐，覆盖检查留在 rh2 parser
   （其有 `generated` 一手值）。改函数签名传入 token 数会扩大 vendored
   窗口（两处调用点+session 路径 TODO），不符"最小 commit"约束。
4. **P6b 用白名单而非 P11 键黑名单**：黑名单要枚举"拓扑/PD/qkv 类"的完整
   键面（arguments.py 数百键，漂移即漏）；白名单=现三个安全键的精确行，
   fail-closed 且与 test_gpu_spike_custom_config.py 的整 dict 断言同构。
   附带关死两个旁路：带引号键/`---` 等非常规顶层行（逐行兜底规则）与重复
   白名单键（yaml 取末次赋值的改值后门，awk 计数检出）。
5. **P6b 放 P6 区（fail 聚合）而非 P11 区（die）**：YAML 键面属启动闭包
   资产校验，与三键在场检查同源同形态；聚合报告让操作员一次看全所有
   preflight 违规。

## 临时挡板

- 无新增。本轮无 stub/skip/豁免类挡板；preflight 负例用临时注入 YAML 行
  实证后逐字节还原（diff 证明）。

## 验证账本（本轮）

- lanes 双 base 全绿：lane A = 236 passed/167 skipped、lane B = 403
  passed/0 skipped，与更新后 manifest expected_counts 逐数一致（+1 双 lane
  = parser 负例净增；+20 integration_base = miles stock §6）。
- `tests/adapters/ + tests/contract_slime_async/` = **321 passed 逐数不变**。
- `g1_acceptance.py --self-test` PASS。
- launch preflight 桩 asset 实跑：正例 preflight/dry-run 双绿（rc=0，
  "preflight 全部通过"输出于 P11 之后、dry-run 段之前）；负例 5 形态
  （use_miles_router:false / rollout_num_gpus / qkv_format / 
  prefill_num_servers / 重复 max_consecutive_zero_signal_steps 改值）全部
  rc=1、P6b FAIL 指名行号与内容、"全部通过"零出现；custom_config.yaml
  事后 diff 逐字节还原。
- ruff：rh2 generate.py + test_weight_version_spans.py、miles types.py
  全过；`bash -n launch.sh` 过；`miles_integration_lanes.sh --checks-only`
  以新 expected_tree/digest/8 张 patch 表通过。
- rh2 侧未 commit（按任务要求）；miles 侧一个 commit（63c7a94e7，
  patch 0009 已存档 + manifest 同步）。

---

# W10 多 engine 最小正确性（决策包 D2+B v2 B-5b，2026-09-04）

规格权威：`docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/decision_package_D2_B.md`
B-5a/B-5b、06 计划 §3 W10 行；完整报告
`docs/agentic_RL/repo_harness_rh2_workstreams/miles_spike/wave1/w10_report.md`。

## 本目录（未审实验文件）的改动

- `launch.sh`：`ROLLOUT_GPUS_PER_ENGINE="${RH2_SPIKE_ROLLOUT_GPUS_PER_ENGINE:-2}"`（原
  "覆盖位已作废设了即红 + per-engine := 全部 rollout 卡"删除）；P11(d) 改为正整数 / ≤ rollout
  卡数 / 整除 / engine 数 ≥ 1 四项合法性检查，删 `ENGINE_COUNT -eq 1`；P11(c) 与 dry-run 拓扑
  行去掉"钉死单 engine"措辞；文件头钉死组说明改为"engine 拓扑不再钉死"。
- `launch_args.md`：`--use-miles-router` 配套限制段与 `--rollout-num-gpus-per-engine` 条目、
  §4 (d) 改写为 W10 语义。
- `thresholds.md`："拓扑限制登记"改为"拓扑登记"（engine 数普通配置、matched comparison
  定首训 engine 数、`router_workers.count` 核对项、明确不做清单）。
- `router_targeting_audit.md`：新增 §0 状态表（§5 前置 1/2 已关闭，3/4/5 首版不做，6/7 待
  GPU），§3–§6 原文保留供对照。
- `g1_acceptance.py` / `postrun_probes.py` / `custom_config.yaml`：无 engine 数约束，未改。

## 与 rh2/src 的对应

- abort 广播：`src/repoharness2/adapters/slime/engine_router_client.py`（新）+ capture_wire
  `_abort_rid` 分支 + bringup `__init__` 接线 `registry.engine_abort`。
- 版本探测删除：bringup `_latest_engine_version` / `_registry_max_version` →
  `_observed_current_version`；startup_evidence 新增 `router_workers`。
- W4 接缝：bringup `staleness_threshold_mirror_from_args(args)` →
  `SlimeBindingConfig.staleness_threshold`。
- miles 侧（integration tree 工作树，未 commit，待存档 patch 0015）：
  `miles/utils/rh2_engine_versions.py`（新）+ `miles/ray/rollout/rollout_manager.py`
  `set_weight_version` 改 async 并逐台核对版本。

