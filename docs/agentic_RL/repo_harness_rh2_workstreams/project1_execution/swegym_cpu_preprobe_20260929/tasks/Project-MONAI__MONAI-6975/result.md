# MONAI6975：最终 CPU 结果

2026-09-29。**原镜像 actor 可运行且复现 Dataset 忽略 lazy 策略；新恢复目录正式 noop／gold／丢弃dict输出候选为0／1／1。** 退化已执行正确lazy变换，却把Dataset返回图像替换为原图，正式参考仍给1，确认 **S1／T2b**。旧setup900失败保持infra／reward=null，未开始测试；本次恢复没有修改生产、镜像、参考或D6。

## 恢复范围与已验证行为

旧 `reserve6-v1` actor/private 已完整验收，新 `grading-setup1800-v1` 仅重做正式评分。[恢复approval](../../../../../../../runs/swegym_cpu_preprobe_20260929/monai6975_setup1800_approval_v1.json)为CPU29-R3，SHA `80e6cc063aabf2d0556bda60a89da47429691dc0155a436b71c2f5de2c240415`；其67件旧原件共589,018字节逐个大小/SHA与本地旧目录一致，新 `reused_evidence.json` 与approval内容相同。复用有明确材料约束，不把旧私有root执行算作新actor。

原actor为UID54321，Python3.8.20、NumPy1.24.4、Torch2.4.1+cu121、pytest8.3.3、NiBabel5.2.1，CUDA不可用，导入来自testbed。初态requirements-dev已有删除MetricsReloaded Git依赖的一行修改，已保留，不能称干净base或本次环境修复。公开旧Compose/Dataset测试实际56项通过。公开矩阵准确在Dataset True／None的lazy策略失败，无import/collection故障。

六行矩阵使用真实MetaTensor图像、两次Flipd：direct／Dataset × lazy=True／False／None。返回图像期望为双轴翻转的 `[[[11,10,9,8],[7,6,5,4],[3,2,1,0]]]`。

| 私有变体 | lazy策略 | 实际返回图像 | 原56项 |
| --- | --- | --- | --- |
| base | Dataset True／None被强制False | 六行图像正确 | 全通过 |
| gold | 六行正确 | 六行图像正确 | 全通过 |
| 丢弃dict输出 | 六行正确 | Dataset True返回未变换的0至11原图，其余五行正确 | 全通过 |

退化错误行实际wrapped `lazy.functional.resample` 调用1次，不能用日志或操作长度代替返回值验收。记录的调用数仅限被wrap函数，不是全后端总重采样次数规范。三组私有容器均UID0、准备/实际apply成功，整文件SHA已采；actor、私有容器及网络/relay/桩清理分别确认。详见[历史部分记录](result_partial.md)、[机器记录](result_partial.json)及[跨包行为复核](../../reviews/reserve6_monai_behavior_review.md)。内存Flip矩阵不等于重放题面完整NIfTI/RandAffine例子，也不证明GPU。

## 新正式评分与实际候选

三方实际执行同一冻结安装串：清除requirements-dev的MONAI Git依赖行、安装types-pkg-resources0.1.3/pytest、安装requirements-dev、`python setup.py develop`。安装均未跳过，无失败命令，RC0，Installed /testbed；版本 `1.2.0+116.g392c5c1b.dirty`，导入 `/testbed/monai/__init__.py`，runner digest前后相同。随后完整执行 `pytest -rA tests/test_compose.py tests/test_dataset.py`。

| 项目 | noop | gold | 丢弃dict输出 |
| --- | --- | --- | --- |
| reward／test RC | 0／1 | 1／0 | 1／0 |
| 4 F2P | 全失败 | 全通过 | 全通过 |
| 59 P2P | 全通过 | 全通过 | 全通过 |
| 实际pytest | 4失败59通过 | 63通过 | 63通过 |
| 安装／test秒数 | 11.828／17.545 | 12.152／18.034 | 12.011／17.658 |
| trusted setup秒数 | 584.637 | 577.499 | 572.303 |

三方各20 warnings，全部189个参考状态完整且唯一，无skip、缺失或段外状态。noop四项 `TestDatsesetWithLazy::test_dataset_lazy_with_logging_0` 至 `_3` 准确失败于日志断言：实际lazy False而应True；不是准备超时或安装错误。[root冻结parser](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/monai6975_setup1800_final_v1.json)与原件逐键核对一致。

noop冻结entries为空且无candidate.patch文件。gold／退化只投影 `monai/transforms/transform.py`，mode100644；实际patch与输入字节一致。完整frozen源码等于公开base逐hunk纯文本应用补丁，并等于私有apply后整文件SHA：gold21,532字节 `5d8ba724a4e09bdf533c1030e0891a9acfb00a98069ca6586533cddb4e369bb5`；退化21,696字节 `a8382325df5169732767963fa29553845514fe29b318ce60184bdcc12ddf369a`。gold把 `apply_transform` 默认lazy改为None；退化在此基础上执行变换后，对dict且Compose.lazy=True返回原data。未改测试或环境文件。

原manifest为 `0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`，原config ID `789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`，base `392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`；没有派生层。正式image_id_actual仍null，不能将镜像预检查冒充该字段的实测值；原manifest、预检查和frozen runtime提供绑定。所有完整eval.log SHA匹配ledger。

各candidate removed=true；从三份原driver尾部再核checked receipt，manager每次created=removed=1，containers_open/supply_open/cleanup_failures为空，final exit0，两层清理确认。[证据审计](evidence_audit.json)保留逐参考、实际安装、完整源码、日志、预算与原driver收口。[root传输对账](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/evidence_manifest_final3_v1.json)覆盖本恢复与两Conan共239件、3,529,295字节，全部一致；本题新目录占43件、1,296,949字节。[正式跨包独立复核](../../reviews/monai6975_setup1800_final_review.md)已完成原件检查及最终卡窄对齐，无新增阻断；非fresh盲审。

## 公开违例、修订设计与用途

[题面](../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/user_prompt.txt)本来就使用dict、Compose(lazy=True)和Dataset返回的out_2。[公开Dataset](../../../../../../../runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-6975/base/monai/data/dataset.py)说明取样时应用transform，其 `_transform` 返回apply_transform结果；base在本矩阵六行的图像也已正确。要求返回变换结果来自公开接口和既有行为，并非gold反推。

来源新增Dataset测试用 `data_from_keys(None,12,16)`，实际是Tensor；执行 `ds[0]` 后只对日志字符串作断言，未保存或核返回图像。新增 `test_dataset_lazy_on_call` 只创建数组，未调用Dataset或断言。旧dict形状测试的Compose默认lazy=False；因此63项虽然有日志、dict、形状和direct执行检查，却没有Dataset+dict+lazy=True的输出值检查。退化在这条公开核心路径的真实回归得1，构成确定误奖。

建议D6候选：在Dataset字典输入、lazy=True的确定性双Flip小图上直接核输出像素，并以direct及False／None作策略与值控制，保留真实lazy调用路径观测。gold已是该六行CPU范围的正对照；不把操作长度当重采样次数，不只加日志断言。该设计未实施、未改正式测试；版本化修订及正式三方复验仍待后续决定。

当前可用于环境/行为/奖励覆盖诊断，不进入无条件正确性比较、训练奖励或留出准入。若后续作受限比较，需事先固定统一语义验收、材料、预算及分母，不能以原reward单独判胜负。完整pip check、自主模型、题面/public_hints真实交付、GPU与训练资格仍未由本轮证明。

旧[setup900失败](failure_review_setup900.md)是control_surface_protect准备超时、测试未开始，外层“formal reference counts differ”为先查null参考计数的误分类。新配置只提高诊断setup到1800，test1800/whole3600不变（预算receipt的before300是冻结builder默认值，不是上一attempt的900）。2CPU/4GiB与权限/源码/安装/参考不变；运行并发也与旧批变化，不能把新setup约572至585秒归因于超时上调或单独调度。三方ledger peak均4096MiB，resource_facts=null。[root资源采样](../../../../../../../runs/swegym_cpu_preprobe_20260929/analysis/resource_final3_v1.json)按实际report容器匹配noop／gold／退化41／41／40样本，memory.events.max分别5411／5221／5280，采样未见OOM、oom_kill或PID拒绝。约15秒采样包含准备与测试，不证明全生命周期零事件；不称无内存压力，也不推定测试进程最低需4GiB。历史partial及旧失败原件保持不变。
