# MONAI6975 setup1800 正式结果独立复核

2026-09-29。**原件复核完成：正式 noop/gold/退化为 0/1/1；支持 S1/T2b 实测误奖。** 先读公开要求/base及原始日志、候选、私有行为，再作此判定；未以题主最终卡或 root parser 摘要替代原件。仅本地静态读取与标准库核验，无远端/项目执行。最后的题主卡对齐与 root 归档状态见末段。

证据根：`runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-6975/`，旧 `reserve6-v1/` 保存 actor/private及准备失败；新 `grading-setup1800-v1/` 只运行三组正式评分。预发版本及预算审查见同目录 `monai6975_setup_recovery_review.md`。

## 误奖与公开要求的对应

冻结公开题面明确比较字典图像的 direct Compose 与 Dataset入口，要求 Dataset遵守 `lazy=True`。公开base `monai/data/dataset.py:67` 起说明取样时应用transform，`_transform` 返回 apply_transform结果；`monai/transforms/compose.py:185` 起明确 True/False/None策略；同文件字典转换与返回结果契约要求实际返回转换后的数据。因此，确定性内存图像/Flipd 控制有公开语义依据，不能只让日志看起来正确。

旧公开actor的6行矩阵显示：base像素均正确，但Dataset True/None实际强制effective=False；最终为指定目标断言失败，不是导入/设备/环境异常。UID54321、/testbed、目标base、CPU、实际源码路径完整；公开旧测56passed。原镜像初态 requirements-dev.txt 删除MetricsReloaded行及版本dirty如实保留。私有root三变体独立容器：base矩阵rc1、gold rc0、退化rc1，旧测均56passed、20warnings；root权限不等于actor权限。

退化在gold默认lazy=None修正上，先完整执行 `_apply_transform`，随后仅在data为dict且transform为Compose、lazy=True时返回原始data。旧私有 `degenerate_run/degenerate/lazy_value_matrix.out` 中 Dataset/True 的真实返回像素为0…11原顺序，预期是11…0；两个Flipd均收到effective=True，真实resample函数也执行过。其它5行像素/策略正确。决定性违例是实际返回图错，不是操作记录长度或某个唯一内部调用次数。gold六行全正确。

原参考新增Dataset测试使用 `data_from_keys(None,12,16)`，执行 `ds[0]` 却丢弃返回值，只断言日志字符串；`test_dataset_lazy_on_call` 仅构造数组。正式参考缺少本题字典图像返回值检查。该退化在正式得1，同时破坏公开核心行为，构成S1/T2b；私有检查没有被接入formal评分，D6仍未实施。

## 三方正式逐原件结果

| 候选 | reward / test rc | 原日志完整测试 | 安装秒 / rc | 测试段秒 | trusted setup秒 |
| --- | --- | --- | --- | --- | --- |
| noop | 0 / 1 | 4failed、59passed、20warnings | 11.828 / 0 | 17.545 | 584.636694 |
| gold | 1 / 0 | 63passed、20warnings | 12.152 / 0 | 18.034 | 577.498625 |
| 丢弃dict输出 | 1 / 0 | 63passed、20warnings | 12.011 / 0 | 17.658 | 572.302537 |

逐组从原日志提取并核对全部4 F2P+59 P2P的**189条逐名状态**，无缺失、额外、skip或xfail。noop精确失败 `TestDatsesetWithLazy::test_dataset_lazy_with_logging_0` 至 `_3`，均在test_dataset.py:127日志相等断言：实际eager/False日志不同于预期lazy/True；59旧参考通过。gold/退化全部参考通过。故noop是正常目标0，后两者是完整正式1，而非准备失败、超时或解析遗漏。

三组安装均实际执行requirements-dev的MONAI Git行过滤、`python -m pip install types-pkg-resources==0.1.3 pytest`、`pip install -r requirements-dev.txt`及`python setup.py develop`（Installed /testbed），完整install/test起止及RC标记各一份，没有安装失败命令。Python3.8.20/pytest8.3.3、/testbed模块导入；runner前后digest相同，未用修改测试/fixture取得分数。逐日志SHA与ledger一致：

- noop `dcc5c8830fdfe008cb14d640537870cf588d14d407539f7085192003b82b5155`。
- gold `dfe5e32d4782d65651b20b50569293c2e20fc3cf0d9b618356e090111814d1bc`。
- 退化 `994addbe8c02d6c9b1a408d1b7d6f946ec865a95fd69591ba8dcf3ecf0ef9d20`。

## 实际候选、身份与双层清理

三份 frozen_patch 均 materialized_head=`392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7`，runtime_image_digest=`sha256:0a529471d25c944c76e598474d7a665b20edc2ee95b1a2f30bf9c36fd8db6055`，excluded_pathset_changed=false。noop entries为空；gold和退化均只有regular/100644的 `monai/transforms/transform.py`，候选patch与输入逐字相同。冻结完整源码SHA：

- gold `5d8ba724a4e09bdf533c1030e0891a9acfb00a98069ca6586533cddb4e369bb5`；
- 退化 `a8382325df5169732767963fa29553845514fe29b318ce60184bdcc12ddf369a`。

上述SHA与旧private各自 `prep_5.out` 的实际SOURCE_SHA完全一致；公开base整文件SHA为 `1e39afa8d4464c4ef18ac3f1a05c654a213af65e4364fa194923faa92b156ee9`。因而正式误奖与私有返回图错误来自同一份完整候选源码，不只是补丁名相同。

新original_image.json、旧inspect和approval的ID均为 `sha256:789cb5d10d9b343a2e8b656581697a7127b56a0d467b1cc5b8779a79a0ff0727`，无派生层。**新旧formal ledger的image_id_actual仍null**；独立inspect与冻结runtime digest是另一路身份依据，不倒填该字段。新reused_evidence与approval结构相同，approval列旧67件589,018字节逐文件SHA重新核验通过。

三组candidate cleanup removed=true；原driver日志唯一footer与driver_close_checked.json结构完全一致：manager created=removed=1，containers_open/supply_open/cleanup_failures为空，outer cleanup_failures为空，halted/aborted=null，final exit0/grader_containers_open空/cleanup总数0。旧actor容器/stub rc0、label容器/网络及force残留空，旧private各自rm/query rc0且remaining空。新脚本只在最终实际runtime空检查后记录executed_pending_review；这不延伸为后续Conan执行期间宿主始终空。

## 预算、资源及用途边界

旧setup900 noop仍是 `grading_control_surface_protect_timeout_after_900s` 的infra，安装/测试/reward为空；旧实验先比较null参考数导致外层误报，旧双层清理实已完成。新预算审计三份均after1800、test_seconds_unchanged1800；whole3600/candidate900/cleanup120保持，2CPU/4GiB/UID54322/deny_all保持，actor/private未重做。本次setup实际约572–585秒，不能据此宣称“900秒必然不足”或“1800修好了根因”：并发、宿主负载及预算同时变化，未做单变量因果实验。

新三方mem_peak均4GiB，**resource_facts均null**；旧失败的OOM/PID事实不移植到新运行，也不把有限采样无事件扩成全生命周期证明。准备成本与17–18秒测试成本分列。

支持环境/评分诊断；模型比较只能在事先统一公开验收、同题/预算/分母和等标准语义审查下有条件使用，并保留原reward；不能用此次私有后检包装formal已修好。正式训练/holdout资格未解除。剩余为D6正式公开要求/参考修订与复验、完整NIfTI/RandAffine原例及更广调用者覆盖、模型/GPU入口预算；CPU deterministic成功不证明这些事项。已审确定性控制不冒充完整随机原例。

## 最终卡与归档对齐状态

原件判定后已读题主 `tasks/Project-MONAI__MONAI-6975/result.md` / `result.json`，分类、正式三方、旧失败分离、来源语义及用途边界均一致，无新增无证据主张或阻断。卡内独立复核及root回执待办可核销，由题主更新，不修改历史partial。

root `runs/swegym_cpu_preprobe_20260929/analysis/monai6975_setup1800_final_v1.json` 的三份report、逐名参考状态及日志SHA与本审原件逐键一致。`analysis/evidence_manifest_final3_v1.json` 共239件3,529,295字节verified=true、零差异；本题新目录子集43件1,296,949字节，已另核本地逐SHA匹配，旧67件复用另列而不混为新运行。`analysis/resource_final3_v1.json` 按真实report ID分别关联noop/gold/退化41/41/40个约15秒采样；峰值均4GiB，memory.events.max分别5411/5221/5280，采样中oom/oom_kill/PID拒绝均0。该证据显示达到内存上限的压力计数，但不证明最低测试内存或全程无事件；formal resource_facts仍保持null。
