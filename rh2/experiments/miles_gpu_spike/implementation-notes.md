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
