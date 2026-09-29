# MONAI2446 跨包独立复核（完整 CPU 结果）

2026-09-29。复用本批运行工具与审查上下文的跨包独立核验，不是重新盲审。本次先读公开原件、base 源码和精确命令，再读 actor/private/noop 原件，最后才读题主 result_partial；只做本地文本、JSON、SHA256 和补丁文本重建，没有运行项目、容器或远端。写入范围仅本文件。

**NiBabel 开发条件修复有效；正式 noop=0、gold=1、degenerate_array_no_shuffle=1。退化实际取消数组列表的内部 shuffle 和对应缓存顺序，违背公开题面，却通过全部正式测试，确立 S1 评分覆盖缺陷。候选冻结源码、实际安装、逐参考结果、完整测试收口与清理均已核实；本轮 CPU 结果不构成模型或训练资格。**

## 公开依据与命令

公开 [user_prompt.txt](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-2446/user_prompt.txt) 明确说 “It should only shuffle the datalist in the SmartCacheDataset.” 原例为五个 ndarray 的 list、shuffle=True、cache_rate=.5、replace_rate=.4。因此既要保留调用者顺序，也要保留内部 shuffle；单纯跳过数组列表 shuffle 不是允许的修法。

公开 base 的 [dataset.py](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-2446/base/monai/data/dataset.py) 第 664–665 行说明 shuffle 与默认 seed=0；第 681–685 行先 randomize 后交 CacheDataset，第 712–716 行调用 self.R.shuffle。旧 [test_smartcachedataset.py](../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-2446/base/tests/test_smartcachedataset.py) 的 test_shuffle 还验证 seed=123 下字典列表的既定缓存内容。内部数组列表顺序并非从 gold 新增的断言推导。

[public_commands.json](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-2446/public_commands.json) 的四条命令与两轮 attempt.commands 完全相等：identity/import、NiBabel 版本、public_smartcache、`python -m pytest -rA tests/test_smartcachedataset.py`。public_smartcache 对 shuffle=True/False 都先输出 caller/internal/cache 三组事实，再断言输入保持、内部顺序、前两项缓存。默认 seed 的预期由公开 base 的 RandomState 行为给出。此处只检查序列顺序，不增加深复制、元素隔离或任意 transform 的要求。

## 开发条件与 actor 原件

原件目录：[mixed-v1](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1)。两轮 actor 均为 CC 2.1.205、uid 54321、Python 3.8.20/testbed、base `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`，从 `/testbed/monai/__init__.py` 导入。numpy 1.24.4、torch 1.13.1、parameterized 0.9.0、pytest 8.3.3 可用，工作区与 /tmp 可写。prelaunch/activation 无 violation；每轮 4 个 Bash 调用、5 次消息、完整 result，四条命令的完整 capture 可读，没有把 timeout/nonzero 泛当成功。

| 观察 | 原 actor | 修订 actor |
| --- | --- | --- |
| NiBabel | 5.2.1，版本断言失败 | 4.0.2，断言通过 |
| 旧公开模块 | 5 failed / 2 passed | 7 passed / 20 warnings |
| shuffle=True | caller 被改成 2,0,1,3,4；internal/cache 正确 | 同一目标错误准确保留 |
| shuffle=False | caller/internal/cache 均正确 | 同左 |

原五个 shape 失败均在 `Nifti1Image(np.random.randint(...), ...)` 的 int64 构造处，是 NiBabel 5.2.1 的兼容性错误；4.0.2 将该处变为 warning。修订 actor 的 all_match_expect=true 只表示预期 base 缺陷与开发检查均达到，不表示题目已修复。原版本断言失败本身不是开发缺口的唯一依据，五个真实旧测失败才提供了具体影响。

[build_dependencies.log](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/build_dependencies.log) 明确由 immutable manifest `cca2571758f276aa5d82fcb372b523e2201cd10be150776badceaaa04defad6a` 构建，卸载 5.2.1 并安装 4.0.2，生成 image `e463edf9eddf29d59db779a0ecc3d2ab009f8f63885dc26425c938d4059b6220`。Dockerfile 只加 wheel 与预装依赖；不把这称为历史 COPY-only 镜像字节复原。本地没有 wheel 原始字节，本复核没有独立重算 wheel SHA。下载容器、actor 容器、网络、relay、stub 均已有正常清理记录；actor 结束源码 git status 为零改动。

这是真实 actor 权限下的脚本化开发检查，调用由 stub 指定，不证明模型自主解题、正式题面交付或训练资格。私有 root 行为不代替 actor 证据，prelaunch 成功也不宣传完整 OS 隔离。全环境 pip check 未执行，不能宣称所有依赖健康。

## 私有变体与实际源码

[private_behavior/summary.json](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/private_behavior/summary.json) 及各 prep/public_smartcache.out 显示三变体均在同一派生镜像、uid 0、相同 base 上运行。每个变体先核源码；gold/退化经 apply-check、apply、应用后 SHA 校验，所有准备 rc=0。本地独立按公开 base 和补丁逐行重建文本，得到下表哈希，与实际 prep_2/prep_5 输出吻合；没有只凭候选标签判断。

| 变体 | patch SHA256 | 实际 dataset.py SHA256 |
| --- | --- | --- |
| base | 无 | 22f52cd44c1b8bc2afac1111aa6824e4c563920a631c3336984a910bd264299a |
| gold | 0c0e9e07a3d8195c75cebdac933cb628fef3425e2721f99087fea2ced6fc9f1a | f29bf46a6bc40e9d4e09ac1e94e46513fcec160c860ca87cbe6633f01b4e301b |
| degenerate_array_no_shuffle | 91bcb98b33149e93606f2e42d48de5a08fd735a4e4e1c54da0f84d04933024e0 | 1653727e6f823ad96967d6f717d8a49db05b2f136e782a4f3df73f16c1ea811b |

Gold 在 shuffle 前浅复制 data；退化对非空且首元素 ndarray 的 list 跳过 randomize，其余仍用旧实现。行为输出完整：

| shuffle=True | caller 保持 | internal | cache | rc |
| --- | --- | --- | --- | --- |
| base | 否 | 2,0,1,3,4（正确） | 2,0（正确） | 1，目标断言 |
| gold | 是 | 2,0,1,3,4（正确） | 2,0（正确） | 0 |
| 退化 | 是 | 0,1,2,3,4（错误） | 0,1（错误） | 1，目标断言 |

三者 shuffle=False 的三项均正确。循环先完成两种模式再统一 assert，因此此处没有未到达第二分支的问题。无超时、导入或 collection 失败；逐容器 rm/query 为 0、remaining=[]。私有只执行这一行为命令，没有记录 gold/退化旧公开模块通过，更未覆盖完整 SmartCache 生命周期或其他数据类型。

## 正式三方结果与保留边界

[noop ledger](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/grade_noop/ledger.jsonl) 与完整 install/test 输出一致。无候选改动，apply_ok=true，安装实际执行而非 skipped；NiBabel 安装前后均 4.0.2，旧安装链完成 `python setup.py develop`、从 /testbed 加载，install rc=0、无 failed-command marker。供应关闭；两段脚本的实际 candidate_test_script 包含修订配方与原 pytest 命令。

测试完整收口为 1 failed / 7 passed / 20 warnings；唯一失败 test_datalist 比较 caller 与 backup，恰为原题缺陷。ledger 为 reward=0、F2P 0/1、P2P 无失败/2、reference_missing/skipped=[]，不是基础设施、导入或安装失败。noop 原始 eval log SHA256 独立重算为 `12ebd9f13dace2a6366f2f93f6a3ea9bf072f80377e657813dd25acd336fb0a5`，与 ledger 一致。runner digest 前后一致；容器 removed=true，manager_close created=removed=1、open=[]、cleanup_failures=[]、final_status exit_code=0。

CPU 准备阶段在本批统一 900 秒上限内用 374.779 秒；这不表示旧 300 秒条件通过。noop mem_peak_mb=4096.0、resource_facts=null：单独的峰值不能证明 OOM，也不能证明完整零事件。root 补充只读核验宿主 15 秒采样：27 个对应评分容器样本，memory.peak=4294967296、memory.events.max 末值 1650，说明内存上限被触及、发生限额回收压力；采样范围内 oom/oom_kill=0、pids.events.max=0。本段资源样本依据 root 已完成核验，本审查未重新解析宿主采样；不能写“无内存压力”，也不能当作 OOM 或模型失败。gold 与退化也都记录 mem_peak_mb=4096.0、resource_facts=null；其准备耗时分别 524.216、461.583 秒，均在相同 900 秒上限内完成。此前 noop 的 27 个资源样本不能自动外推为另外两容器的逐事件统计；三方完成安装与测试的事实，也不能包装为无内存压力。

## gold／退化终态补核

[status.json](../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-2446/mixed-v1/status.json) 已有 finished_at，三次正式步骤都 rc=0；其原始 status 字段为 `executed_pending_review`，不是作业仍在运行。本次补核完成独立审查，不回改原始状态。

Gold 与退化的 candidate.patch 分别与输入 gold.patch、degenerate_array_no_shuffle.patch **逐字节相等**；再次独立按公开 base 应用补丁文本，解码各 frozen_patch.json 的 content_b64，比较整个 dataset.py：gold 49,702 bytes、退化 49,686 bytes，全部相等，SHA 即上表实际源码 SHA。两份 frozen entries 和 projection 都只有 monai/data/dataset.py，mode=100644，excluded_pathset_changed=false；materialized_head、runtime image 和 baseline/public bundle digest 相同。stage 至 projection 无异常、apply_method=git_apply，ledger apply_ok=true；没有候选测试或 fixture 改动。该核验覆盖冻结文件的全量字节。

三方实际使用同一历史安装修订配方和原 `pytest -rA tests/test_smartcachedataset.py`。Gold/退化日志从安装开始到测试结束均完整读回：NiBabel 前后 4.0.2，requirements 安装和 `python setup.py develop` 完成，Installed /testbed；没有 install_failed_commands、导入或 collection failure。Gold 安装 9.992 秒、测试段 7.924 秒；退化 7.909 秒、8.078 秒；install rc 和 test rc 均为 0，candidate segment 与 test segment 均 completed=true。两者 `8 passed, 20 warnings` 的 pytest 内部耗时分别 6.98、7.05 秒。日志中的 deprecated/np.bool/int64 警告未转化成失败。

以下三个完整 nodeid 的公共前缀均为 `tests/test_smartcachedataset.py::TestSmartCacheDataset::`。对 root 的 [冻结 parser 重放](../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai2446_final_v1.json) 逐键核原始日志，不只看汇总 reward；三方共 9 个参考状态全部匹配：

| 参考或结果 | noop | gold | 退化 |
| --- | --- | --- | --- |
| F2P test_datalist | FAILED | PASSED | PASSED |
| P2P test_shuffle | PASSED | PASSED | PASSED |
| P2P test_update_cache | PASSED | PASSED | PASSED |
| 正式 reward | 0 | 1 | 1 |
| 完整模块 | 1 failed / 7 passed | 8 passed | 8 passed |
| test rc | 1 | 0 | 0 |

各方 reference_missing/skipped=[]、num_parsed_outside_segment=0；另五个 test_shape_0 至 _4 也均通过，没有参考外失败。三份日志 SHA 都重新计算并匹配 ledger；gold 为 `a7004961404ebec652a3797d0f7977246a4b880ce44af6679400b5d2339bd905`，退化为 `13422cbab784ecb6a87a48af600ec4ad2a1b08a7ceb0fa349e2d5a3c980ed239`。runner digest 三方均前后一致；供应 null。每次 ledger removed=true；各 driver_close_checked 均 created=removed=1、containers_open/supply_open/cleanup_failures=[]、无 halted/aborted，final_status exit_code=0。所有正常退出都伴随完整测试，而非仅 wrapper rc=0。

## 误奖范围、可复用修订与剩余事项

误奖是**正式断言覆盖不足**，不是 parser 漏读失败：新增 test_datalist 仅保留调用者 list 的比较，没检查内部顺序；已有 test_shuffle 用字典列表，退化仅对 ndarray 列表跳过 shuffle，故它继续通过字典旧测。已证明的违反范围就是原题五个 ndarray 列表在 shuffle=True/default seed=0 时，内部仍为 0,1,2,3,4，缓存仍为 0,1；不是任意数据或所有 seed 上的完整结论。私有同源码 gold 能同时保留 caller 和内部 shuffle，排除了以“公开要求彼此冲突”解释退化的可能。

已有 [public_smartcache 命令](../../../../../../runs/swegym_cpu_preprobe_20260929/task_inputs/Project-MONAI__MONAI-2446/public_commands.json) 可直接作为最小验收草案复用：原题 ndarray list 下 caller 顺序保持、内部按默认 seed shuffle、cache 与内部前两项一致，并用 shuffle=False 保留既有不打乱控制。原题支持前两项，base 缓存构造/seed 契约支持 cache 和 False 控制；现有 base/gold/退化对照已经分别得到失败/通过/失败。无需从 gold 新增需求，不扩大到深复制、所有 transform 或完整生命周期。本轮没有改正式测试或评分；后续接入仍依赖共同 D6 实施。

题主 [result_partial.md](../tasks/Project-MONAI__MONAI-2446/result_partial.md) 的 actor/private 内容已于首轮最后读取且与本复核一致；其“正式在途、独立复核未做”是较早快照。本次先直接收束独立结果，题主完整题卡稍后据此对齐，未把题主未完成更新当成运行失败。当前任务适合作为环境修复和 S1 覆盖诊断案例；原评分未修前不作为无条件训练合格题。保留全环境 pip check 未做、wheel 字节未本地重算、正式题面交付／自主模型行为未验、CPU 资源压力以及 D6／模型／训练条件未完成的边界。
