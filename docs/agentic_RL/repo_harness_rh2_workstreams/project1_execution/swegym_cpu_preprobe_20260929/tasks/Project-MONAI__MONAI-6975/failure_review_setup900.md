# MONAI6975：setup900 准备失败复核

2026-09-29，依据05:35 SGT本地同步原件，只读复核。**本轮正式 noop 是基础设施准备失败，reward=null；没有运行安装或测试，不能记为任务0、金标失败或参考失配。** 原 actor/private 三组证据继续有效，正式 gold/退化在本轮未派发。[机器核对](failure_review_setup900.json)；[原始运行](../../../../../../../runs/swegym_cpu_preprobe_20260929/remote/results/Project-MONAI__MONAI-6975/reserve6-v1)。

原 ledger 的 `outcome=failed_to_grade`、`failure_category=infra_failure`、`infra_failure_detail=grading_control_surface_protect_timeout_after_900s`；F2P/P2P计数、install、test、observations均null，正式参考还未被测试。trusted_setup阶段合计901.136589秒，delta_apply0.191889秒、baseline_rebuild0.810293秒。来源两个测试文件恢复并apply成功，可信自证为`RH2_SETUP_OK=1`；失败发生在随后control_surface保护阶段，其完成自证为null。完整日志18,091 B的SHA为`0209d74891d2ec022d7e78ac90ef597e7fc7f67b933c0538bcb07956c866958d`，与ledger一致；没有install或test起始标记。`log.partial=false`只说明已产生日志已收集，不能据此称完整评分已执行。

冻结manager在可信测试准备与自证后调用保护脚本，使用env_reset_timeout_seconds；保护成功后才进入候选安装/测试。本次phase/error与这个顺序一致。不能由现有日志进一步确定递归保护卡住的具体文件或唯一本体原因；overlay copy-up／文件缓存压力是已有宿主诊断支持的方向，本记录不将其当作已证明的唯一原因。ledger peak=4096 MiB，同时resource_facts记录container_oom_killed=false、oom_kill_events=0、pids_events_max=0；这不支持“OOM导致失败”，也不代表测试进程需要4GiB或全生命周期无资源压力。

候选stage已完成noop投影：base HEAD为392c5c1b860c0f0cfd0aa14e9d4b342c8b5ef5e7，frozen entries空、excluded=false、stage_error=null。准备前original_alias把已验证immutable manifest `0a529471…db6055`对应的image ID `789cb5d1…ff0727`设为冻结入口本地别名，没有构建新层。失败ledger的image_id_actual仍null，不能假写安装后镜像/导入观察已完成；原alias、固定manifest和已完成actor/private身份另有证据。

## 清理与外层误报

候选ledger的cleanup为removed=true、`rm:ok`、detail空；原 `grade_noop.log` 最后JSON的manager_close为created_total=removed_total=1，containers_open、supply_open、cleanup_failures均空，halted/aborted为空，final_status.exit_code=0。该exit0是driver完成记录和收口，不是测试通过。两层清理在原件中均确认。

实验脚本 `monai_reserve_followups_v1.py:213`先要求参考总数匹配，下一步才检查infra/reward；本次计数为null，于是外层留下 `formal reference counts differ`。它使诊断标签错误，但安全停止了本题，未继续gold/退化。后置的`driver_close_checked.json`也因此未写出；本复核直接读取原driver尾JSON确认清理，不能把receipt缺失误认为容器必然残留。旧status、日志和冻结脚本不回写。

## 下一次独立诊断的边界

对root拟议的复验无关键反对：在4583全部收口后，6975单独用新输出目录将准备预算900→1800秒；保持test1800秒、whole3600秒、原镜像、code_v1、依赖配方、源码/参考/私有材料和权限不变。这是有真实准备超时依据的CPU诊断，尚未执行，不保证1800秒足够。whole期限仍独立约束全流程，准备/测试两项上限相加不意味着两项都能用满并另获额外时间。

新诊断应先独立收取并确认candidate/manager清理，再按infra判据解释结果，参考数量仅对实际测试完成的结果判断；任何准备/清理未知都停本题。无须重跑已完整的actor/private：两者使用相同原镜像/base/目标源文件，私有root不冒充actor，已由[跨包行为复核](../../reviews/reserve6_monai_behavior_review.md)核对。新正式结果仍须核安装、完整日志、逐参考、gold/退化实际整文件和两层清理，才能给最终题级结论。D6未实施，本失败及拟复验均不授予比较、训练或留出资格。
