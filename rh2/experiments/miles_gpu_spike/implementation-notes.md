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
