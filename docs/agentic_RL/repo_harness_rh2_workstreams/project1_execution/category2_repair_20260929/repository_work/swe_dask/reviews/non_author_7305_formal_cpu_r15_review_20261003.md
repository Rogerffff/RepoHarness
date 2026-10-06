**Dask7305：正式 R15/source050 v2 CPU 非作者验收**

2026-10-03。结论：本轮完整 17 行正式 CPU 矩阵验收通过，未发现所核范围的阻断。实际仅 `gold_full_auto=1`，其余 16 行均为 0，与冻结矩阵一致。每行 105 项正式参考均有 PASSED/FAILED，共独立核对 1785 个参考状态；`first_last` 恰有两项已知旧 P 失败，其余 16 行的 104P 全部通过。本结论是正式 CPU 评分证据，未授 GPU 部署或训练资格，也未证明真实模型推理已运行。已有授权的后续首轮不因本报告新增审批闸门。

我是非作者核查者，没有修改或运行作者候选、测试或远程作业；已接触私有 gold 和作者报告，不能视为公开盲审。本次只在本机读取原件，做 SHA/大小重算、冻结 consumer 的模型纯构造与摘要复算、内存中补丁正反应用及原日志解析，没有 SSH、Docker、CPU 实验或模型推理。仅新增本报告与同名 JSON；[此前材料和历史 CPU 审查](non_author_cpu_and_7305_review_20261003.md)保留原范围。

**原件和运输绑定。** [terminal 清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7305-formal-cpu-c-20261003-v2/remote/readback_manifest.json) SHA 为 `b064f565b004b30464b7dbfa798a72816e258a9dad357581daac2d832d2cfa51`；186 成员、4,616,690 字节，全部大小/SHA 匹配、无排除。[固定作者读回](../tasks/dask__dask-7305/formal_cpu_readback_r15_20261003.json) SHA 为 `547ecdfa3414096ac6800a923e81c21c1407b2be4f108d4aa404e2626c4c2418`。没有用作者汇总替代原日志：各行从唯一 Start/End 测试区间独立解析，再与 state、ledger、固定读回逐 ID 对账。

另外复用了 `finalize_8801_formal_behavior_r16_20261003.py` 的 7d31 固定字节中四个只读运输函数：`sha/read/closed_raw_path/verified_readback_manifest`。工具 SHA 为 `7d31edc355114a86266f94cefc0d320327928c5e9e600719c8c03e1a63f8af4b`。只抽取这些函数并将输入绑定到 7305，没有执行其 8801 main、读取 8801 标签或裁决、修改 R15 finalizer。本次消费的 95 份原件全部在清单内；路径封闭、无符号链接跳转，各候选的 run_id、ledger 路径/SHA、log 路径/SHA、105 项参考及清理记录均匹配。32 份所用冻结题目/producer/consumer/契约资产也逐 SHA/大小匹配 release；同名 JSON 保存逐资产和逐行绑定。

**实际逐行结果。** 下表只列实际首个 F2P 失败分支；负对照提前失败时，后续 nested 断言没有执行，不能按矩阵“reason”猜其本轮失败原因。每行模块都是 108 个用例，另有 3 个既有 slow 测试因未传 `--runslow` 跳过，均不在 105 个正式参考中；不能说整个模块无跳过，也不能将这 3 项写成正式缺参考。

| 候选 | 实际分 | F 通过 | P 通过 | 实际结果和范围 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | 104/104 | 题面 uint64，1 输入／1 输出：量化最小值 +1。 |
| gold_full_auto | 1 | 1/1 | 104/104 | 105 项正式参考全部通过，包括新 auto 行归属控制。 |
| gold | 0 | 0/1 | 104/104 | 题面 uint64，1 输入／3 输出：量化最小值 +1；未到后续控制。 |
| gold_full | 0 | 0/1 | 104/104 | 七组显式分区控制已过；auto 最小分界 +1。 |
| exact_full | 0 | 0/1 | 104/104 | 七组显式分区控制已过；auto 最小分界 +1。 |
| higher_full | 0 | 0/1 | 104/104 | 七组显式分区控制已过；auto 最小分界 +1。 |
| nearest_via_float | 0 | 0/1 | 104/104 | 题面 uint64，1／1：量化最小值 +1。 |
| clip_partition | 0 | 0/1 | 104/104 | 题面 uint64，1／1：量化最小值 +1。 |
| uint_only | 0 | 0/1 | 104/104 | 题面 uint64，1／3 已失败；本轮尚未到 signed 分支。 |
| k1_only | 0 | 0/1 | 104/104 | 题面 uint64，1／3：量化最小值 +1。 |
| first_last | 0 | 0/1 | 102/104 | 题面 uint64，1／3 失败；另有两项已知旧 P 失败。 |
| gold_pin_only | 0 | 0/1 | 104/104 | 前四组已过；跨 2**63 的 uint64，4／4：量化最小值 +1。 |
| gold_typed_only | 0 | 0/1 | 104/104 | 题面 uint64，1／3：量化最小值 +1。 |
| rv_pin_noclip | 0 | 0/1 | 104/104 | 相邻大 uint64，3／5：最大值 612509347682975872 超过 612509347682975844。 |
| rv_interp_pin_noclip | 0 | 0/1 | 104/104 | 相邻大 uint64，3／5：量化分界无序；第 1 位 612509347682975872 ≠ 612509347682975844。 |
| rv_maxonly_threshold | 0 | 0/1 | 104/104 | 全负 int64，4／4：最小值 −612509347683174144 ≠ −612509347683174146。 |
| rv_k_le4 | 0 | 0/1 | 104/104 | 相邻大 uint64，3／5：最小值 612509347682975872 ≠ 612509347682975842。 |

`first_last` 的旧 P 失败仅为 `test_set_index` 和 `test_empty_partitions`，两处均在末分区索引最大值不得超过最后分界的断言失败。它实际是 3 failed/102 passed/3 skipped；正对照为 105 passed/3 skipped；其余负对照均为 1 failed/104 passed/3 skipped。全部模块有 2 warnings，原件照实保留。源 gold、`uint_only` 等虽有其他已知残缺，本轮实际尚未到那些分支。`gold_pin_only` 已通过前四组，再在跨 `2**63` 的 uint64 组失败；同样的 +1 数字不是同一个已执行分支。

四份原先只有 F2P 定向结果的控制 `rv_pin_noclip/rv_interp_pin_noclip/rv_maxonly_threshold/rv_k_le4`，本次均真正执行了完整模块，104P 全部通过，F 分别触发越过最大端点、非单调分界、全负大整数最小端点偏移和 5 输出分区的阈值错解。此次完整 P2P 补齐单独记在新原件中，没有回写历史 4 份定向结果。

**公开依据、auto 和正对照。** 冻结公开问题未改变，明确要求大整数分位数保持正确 min/max，并指出乱序输入、最小值靠后时 `set_index` 的行归属错误。当前测试保留 v2 七组，新增 1000 个乱序大 uint64、最小值置末尾、4 输入分区的 auto 实例。auto 只传给支持它的 `set_index`，没有传给只接受整数分区数的 `partition_quantiles`。量化分支核整数 dtype、精确端点与非降分界；`set_index` 用 Python int 比较端点、每个非空分区区间与汇总索引值，避免 uint64/float64 提升掩盖 +1。

测试没有规定 gold 的内部量化值、auto 输出分区数或修复实现。小整数原测试从锁定内部集合改为精确两端、整数/排序与数据等价，合理整数近似内部分界可以通过。`gold_full_auto` 的两份非测试源码正文与实际 FrozenPatch 一致：整数摘要保持 dtype、分区量化 nearest、唯一值不足时钉精确端点并夹紧近似内值；新增整数 auto 从精确摘要选取分界，非整数仍走原逻辑。它完整执行七组及 auto 的端点、归属、行保留断言并通过 105 参考。这是对已测试公开语义的正对照，有限输入范围不证明穷尽正确性。源 gold 的名字不替代实际正确性；其本轮为 0。

**consumer、材料和执行身份。** 固定 R15 为 `cat2-cpu-r2e089092-swe39-dask-monai-20261003-v1`，release manifest SHA `2b788d1ce84228a27894e04886ade347e91993f48ddc9bdeeb8f92de4aa92917`。从冻结 producer、registry 构造的 public/private/environment 与实际 prepared 原件一致；registry 为 `sha256:23b2c30e3f4bbd9d0a6569d25fd948f836f1a7a4521e0e104b62a4c6fdb5277d`。源 1F/104P 被完整保留，`added_pass_to_pass=[]`；large_uint 是原源评分 patch 的 P，不能说成本轮新加的 P。实际 base 和 17 份 baseline/FrozenPatch 均为 `8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0`。每个 baseline 有 428 条对象记录；候选全量源码与计划 patch 在内存正反应用后，逐路径内容摘要回到该 baseline。noop 没有投影条目，其余候选未触碰测试或 conftest。

材料身份为 `sha256:14a6817b0bc1bebdd6a9cb344270e1ab66ba0d2f6d00ca6bf3e777a97e526739`，grading bundle 为 `sha256:07899b813de68a224798adc57f3323f2f582ce99369ea5de60b3330a87faae8c`，environment 为 `sha256:cda3770ed36db3f37f42a14ebb4d7bda1833cc05474d17fc88ef688457b904db`。实际脚本摘要逐行等于冻结 consumer 复算的 `sha256:f5d18ea25690356ea6a30217bcf8cbef090405cd579a7164c0786a905624e900`。保留 source/vendor setup 300 秒，安装 `python -m pip install --no-deps -e .`，正式测试 `pytest -n0 -rA  --color=no dask/dataframe/tests/test_shuffle.py`；没有新 prerequisite 配方。17 份可信 setup 均记有效测试 patch 应用 rc0、1 个评分测试文件保护成功。root 做受信 setup/权限布置；候选补丁按冻结 replay 的 numeric UID54321 exec，安装和测试按冻结 manager 的 numeric UID54322 exec，不能把 root setup 说成非root运行。

本轮候选 UID54321 和评分 UID54322 的依据是实际 ledger 的 `apply_user=agent/54321`、评分 policy 及上述固定代码路径。读回没有每行新 `id -u` 原始输出；`RH2_OBS_PREFIX_OWNER_PRE=54322` 是候选侧诊断，不能独立当作可信进程 UID 证明。各行 `runner_integrity_changed=false` 只对应其采集摘要前后相同，不推广成共享 runner 的完整安全证明。

**来源镜像和资源边界。** c58d4ad6fd35eab8 输入快照的 28 个成员均匹配，归档 SHA `891fcaa7f11730934d7a8dd78293f52998fc250020a715e4a97e3f3b7147bcf5`。本轮实际 command 使用快照内旧相对名 `tools/cpu_formal_matrix.py`，字节 SHA 为 `05080362f74eeba0cfacee4a51c2002a1806d2a387ee571bfb69ca695140e962`，与当前独立 `tools/cpu_formal_matrix_source_identity_v2.py` 相同。工作区旧路径仍是 `208430d5b5a87121c8473cb209858f95089e2716613325919028dcfa9d55c85d`，没有称旧 208 已修复。本次 v2 确实运行了 050 的 source 分支并完成 17 行。

初始 `source_image_inspect.json` 的 config Id 是 `sha256:b4f186ca0a0139f4287b9203a666b9fd009af079ddad700bb2bf8019aede8b99`，RepoDigests 含来源 manifest `sha256:21fd7dd8a9a1511a02fa5c99403449c75547e2e110afee679b6c9c1569290b73`。17 行 `ledger.image_id_actual=null` 原样保留。冻结 manager 在每个来源评分容器启动后读取运行容器的 `.Image`，再校验该实际 Id 的 RepoDigests，缺失/不匹配会报 infra；本轮完整评分且无 infra 支持该强制路径已经通过。读回没有单独保存每个运行容器的 inspect 原始输出，初始 config inspect 不能冒称它们各自的 config ID。

17 行安装 rc0、无失败安装命令、完整日志；测试 rc 仅正对照为 0，其他为真实断言失败的 1，candidate exec 与 test exec 均正常交付。无基础设施失败，逐行清理 `removed=true, steps=[rm:ok]`。policy 是 2 CPU/4GiB/PIDs512，`resource_facts=null`；测试 phase 114.97–137.47 秒，trusted setup phase 149.06–229.33 秒。内存峰值诊断 3070.484–4096 MiB；noop 4096 MiB 不等同 OOM，实际断言退出和完整原件没有给出 OOM/infra。未把历史 actor 的实测 cgroup 填作本轮 grader 的新探针。

**历史 actor 与未完成范围。** 复核旧公开 actor 清单中 20 份相关原件 SHA/大小：真实非root CC2.1.205 的首请求含原公开题面和 hints，使用同一来源 config/base；公开身份导入 rc0，题面 quantiles rc1（两端 +1），原公开 shuffle 模块 rc0/104 passed/3 skipped/2 warnings。旧 prelaunch 与 activation 原件实测 UID54321、2 CPU/4GiB/PIDs512、禁 swap、activation 写拒绝；实际脚本桩有 4 请求、3 Bash 工具结果，harness returned/rc0，容器/网络/relay/stub 清理无残留。attempt SHA `f94d07e5c0b8347eb840081d09e1c91ea09fb8276dc58ded88129a4806c26870`，首请求 SHA `fd891a9fdc1744c6ea38ab18d5564c924426b183b187f1ac96c1479c490bedfd`。两个通用旧摘要字段仍为 false，实际探针和输出按原范围读取，未静默改旧记录。

这份旧 actor 是 API 脚本桩，没有模型推理；它支持同源公开可运行性，不能等同本次正式评分 actor、新 GPU 部署或 typed 训练 actor。后续实际 GPU 镜像/激活/首请求、模型轨迹及评分接续原件仍未由本轮交付，不泛化成新准入条件。本轮模型首轮尚未发生。

可变 `results.json` 现已分开旧 v1 的“仅首 noop 后因来源 ID 断言中止”和当前 v2 完整矩阵：v1 的 `full_matrix_score_observed=false`，v2 为 true。固定作者读回和 terminal 原件仍是本报告绑定的 v2；这项行政纠正关闭了误标范围，未把旧 v1 当成新完整结果验收。

**关键版本绑定。**

| 材料 | SHA256 |
| --- | --- |
| revision.json | `b65bf0af180aa373cc663b401d357dbe51d61036a8f065aabfd1ebde95108270` |
| acceptance_matrix.json | `de3250c854bb6a5b335812070034eeb0261612344876cba6baca9d84241f1c88` |
| effective_test.patch | `4c63d384f1c62eaa019c12bc70ae8b0cab0d7595e719edcc1d5e878feb86c127` |
| effective_test.py | `025b72244c757ab5ea353ff8bfcfb081ecde9987ccfcde67638f65b2058c58b5` |
| gold_full_auto.patch | `1a249962f60580a4340d6f92a45b414475c0eca86655715abb70229a366b5994` |

逐行 ledger/eval/baseline/FrozenPatch SHA、实际失败源码行、105 参考的共享 ID 与状态重建规则、32 份 release 资产、95 份消费路径及历史 20 原件见同名 JSON。本次结论只绑定上述固定字节和 terminal v2 原件。

