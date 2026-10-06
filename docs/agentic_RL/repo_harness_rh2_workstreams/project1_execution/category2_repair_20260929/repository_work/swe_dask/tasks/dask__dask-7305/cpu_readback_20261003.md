# Dask7305：CPU 私有对照与 auto 修补

2026-10-03，题主执行并逐 SHA 读回。**原公开 actor、13份完整模块私有对照和4份F2P定向对照完成：扩展正对照通过，其余候选被拒绝。** 正式材料评分与非作者核查未完成；本文是作者运行报告，不授予探针或训练资格。全部在途作业已自然收尾，随后按总协调转达的用户要求安全暂停。

## 固定输入与原公开 actor

原 manifest `sha256:21fd7dd8a9a1511a02fa5c99403449c75547e2e110afee679b6c9c1569290b73` 拉取并核实实际 ID `sha256:b4f186ca0a0139f4287b9203a666b9fd009af079ddad700bb2bf8019aede8b99`，HEAD 为 `8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0`，初态干净，不改依赖。25 文件快照 `6ed3228ad3615384` 逐 SHA 一致，实际作业绑定初始13行矩阵，不热改为后来追加的17行。

镜像准备及运行使用第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，解释器为 `runtime_cpu_v2`。该 source 包含已审 Git 修复，但没有正式登记本题新测试。修订补丁 SHA 为 `4c63d384f1c62eaa019c12bc70ae8b0cab0d7595e719edcc1d5e878feb86c127`，1 F2P + 104 P2P 的编号不变。

公开 actor 作业使用真实 Claude Code 2.1.205 和脚本桩，**没有基座模型推理**。实际 UID54321、2 CPU / 4 GiB、512进程上限、无 swap、无宿主挂载；启动前和激活检查通过，activation写权限被拒，日志完整且容器/网络/桩无残留。原 hints 和题面均在实际首条请求中核到，首请求 SHA 为 `fd891a9fdc1744c6ea38ab18d5564c924426b183b187f1ac96c1479c490bedfd`。

身份和导入确认 `/testbed/dask`、Python3.8.19、NumPy1.20.3、pandas1.2.5、pytest8.3.2。原题面 MCVE 的实际两端为 `612509347682975744`、`616762138058293248`，各比正确值大1；用 Python int 比较后 rc1。原公开 shuffle 模块 104 passed、3 skipped、2 warnings；三个 slow 测试按原 `--runslow` 规则跳过，不属于104个参考，未新增 skip。

## 首六份完整私有对照

每份独立干净 root 容器中分别应用候选和新测试，完整执行 `test_shuffle.py`。全部105参考有实际状态，各自104 P2P均 PASSED，缺席为0、移除和查询rc0、无残留。下表是私有测试行为，**不是正式 reward**。

| 候选 | 新测试私有行为 | pytest（另有3 skipped、2 warnings） | 实际失败点／接受范围 |
| --- | --- | --- | --- |
| noop | 拒绝 | 1 failed、104 passed | 题面原例的 `partition_quantiles` 最小值大1 |
| gold_full_auto | 接受 | 105 passed | 全部v2控制及新增auto端点、行总量和区间归属通过 |
| gold | 拒绝 | 1 failed、104 passed | 原例请求3个输出分区时仍最小值大1，先于auto失败 |
| gold_full | 拒绝 | 1 failed、104 passed | 前七组通过；auto分界首端为…744，而真实最小值为…743 |
| exact_full | 拒绝 | 1 failed、104 passed | 同一新增auto实例，前七组通过 |
| higher_full | 拒绝 | 1 failed、104 passed | 同一新增auto实例，前七组通过 |

旧三份的历史独立资格只覆盖显式分区，不能继承为本轮 auto 正对照。新 `gold_full_auto` 在整数 auto 分支从精确摘要取分界，非整数分支保持原插值。当前结果证明本轮实例与原参考回归通过，还需非作者核修法合理性及正式身份评分。

## 已知候选接续与范围

初始13行漏掉了原v1曾放过的四份候选：`rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_maxonly_threshold`、`rv_k_le4`。它们分别触发相邻整数的两处不夹紧、全负int64和值域/分区数阈值，不能用早在前面失败的候选证明这些v2分支有效。当前 [acceptance_matrix.json](acceptance_matrix.json) 已补为17行；[初始13行原件](acceptance_matrix_initial13_20261003.json)和已完成快照保持不变，四份追加补丁可应用且AST通过。

28文件新快照 `1e59b10771f52f51` 在cpu-c逐SHA核实；给Orange完成镜像准备及公开actor机会后，剩余作业 `dask7305-remaining-cpu-c-20261003-v1-q02` 经原统一run槽自然完成、退出0。它复用同版本原公开actor，不重复运行actor或构建镜像。

剩余七份完整模块均被拒绝，各有105参考状态、缺席0。`nearest_via_float`、`clip_partition`、`uint_only`、`k1_only`、`gold_pin_only`、`gold_typed_only`各1 failed/104 passed/3 skipped；前四份及`gold_typed_only`先在题面原例的端点偏差失败，`gold_pin_only`则通过前四组控制，随后在跨2**63的uint64组失败。两处虽均表现为最小值大1，不能据同一错误数字混为同一分支。`first_last`为3 failed/102 passed/3 skipped，除该F2P外，只失败已登记的旧P2P `test_set_index`、`test_empty_partitions`，没有额外回归。

四份F2P定向对照也实际失败：`rv_pin_noclip`在相邻整数的最大值越界；`rv_interp_pin_noclip`在同组相邻整数的摘要排序失败；`rv_maxonly_threshold`在全负int64最小值偏差失败；`rv_k_le4`在5个输出分区的相邻整数端点失败。每份只有1项实际F2P状态，**104 P2P未执行**，不能以此替代17行完整正式评分。11份均清理rc0、查询rc0、无残留，正式reward继续为null。

## 原件与后续

忽略证据根 `runs/category2_repair_20260929/swe_dask/`：镜像 `image_preparation/dask7305-cpu-c-20261003-v1/remote/` 共18文件、11934字节；实际诊断 `cpu_diagnostics/dask7305-cpu-c-20261003-v1/remote/` 共77文件、344778字节。全部逐 SHA/大小下载，并有 `readback_manifest.json`。完整状态在 `run/status.json`，公开实际结果在 `run/actor/`，各私有原文在 `run/private/<candidate>/<candidate>/revised_test_file.out`。

剩余对照的原件在 `cpu_diagnostics/dask7305-remaining-cpu-c-20261003-v1/remote/`，共89文件、277502字节，逐SHA/大小下载；读回清单SHA为 `9a464cc0eab7afad4cf709b6168215d39c18aef577e57785081c5ed88114f461`。[结果清单](results.json)分别记录首六份与后十一份，保留两份输入快照和不同执行范围。

旧暂停回执见[暂停记录](../../pause_checkpoint_20261003.md)；现按三方流程恢复材料核查，CPU实际派发门待发布方解除。非作者指出的摘要滞后及`gold_pin_only`失败分支过宽已按原件订正，旧CPU输出不改。仍须完成非作者核v3修法及v2聚焦断言、共用正式发布和17行正式矩阵，之后才能提交统一GPU队列。
