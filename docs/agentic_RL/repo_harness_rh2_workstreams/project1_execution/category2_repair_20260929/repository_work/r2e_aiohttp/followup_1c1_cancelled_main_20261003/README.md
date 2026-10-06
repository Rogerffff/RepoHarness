# 1c1：公开主任务取消的实际归因补证

2026-10-03。本包作业于05:56–06:01 UTC在cpu-a公平run槽1完成三个同输入对照、退出0，96文件原件已完整按SHA／大小归档。题主实测归因和一次非作者双角色核查均已完成并核收：原基线和完整Qwen清理正确，完整Coder在observer前留worker pending1、asyncgen和loop开放。原两个模型首轮各58/58、raw reward 1，以及原结果和闭合时点文件保留。本页不是训练资格或新评分结论。

本批13:24裁定要求核对一项具体风险：Coder 已完成且被取消的主任务在 `run_app` 的 `finally` 中调用 `Task.exception()`，可能抛出 `CancelledError`，使后续后台任务、异步生成器和事件循环清理被跳过。输入通过真实公开 `run_app(coroutine, loop=loop, handle_signals=False)` 到达该分支，不替换库函数、不读隐藏材料。后台任务已经进入 `try`，异步生成器保留强引用；主任务自身取消，公开 `_run_app` 在等待该 coroutine 时接收取消。

只比较同一个固定公开输入的三侧：原始基线、完整原 Coder FrozenPatch 的7条记录和完整原 Qwen FrozenPatch 的2条记录。Qwen 为同一输入的有效实现对照，不重新采样。先核对基线全部307个可评分文件、模式和排除路径集合，再应用全部候选条目并核对完整候选树；不只看HEAD，也不删除 `.coverage` 或候选辅助文件。

实测沿固定 R6 开发入口、实际 CC 2.1.205 桩和原正式演员装配执行。必须使用原GPU探针的精确00ad镜像、Python 3.9.21、UID 54321、2 CPU／4 GiB／512 pids。原 cpu-b 已销毁，本次使用现存 cpu-a 的公平 `cpu_slot.py` run 入口和已分配桩端口。精确镜像已由发布线程通过准备槽加载、核实为原ID/linux amd64。本包已通过run槽准入，不使用另一旧像或重建像冒充同环境。[有界控制器](bounded_controller.py)为这批串行作业设置1800秒运行和120秒清理等待，超时为基础设施/未完成证据，不直接判候选失败。

固定输入清单位于 `runs/category2_repair_20260929/r2e_aiohttp/followup_1c1_cancelled_main_20261003/inputs_v1/input_manifest.json`，SHA256 `921aebdb79dadef42c487e064b749de94a02242012c3cf05410e6f77f75a6517`。清单11个文件已在cpu-a按SHA256与大小全部核对，见同目录外的 `staging_readback_v1.json`。原[公开脚本](public_cancelled_main_probe.py) SHA256 `50c09f6ee8e303a1521dbfc958be4cbcc67055e82f493cd70cde3d8ca23b598e`；[支持请求](cpu_support_request_v1.json)字节不改。

判断依据是 `after_run_app_before_observer_cleanup`：caller异常、主任务done/cancelled、后台任务done/cancelled、异步生成器关闭、loop关闭、待处理任务数及清理事件。`CancelledError` 传播给调用者本身可以是三侧共同的预期结果，脚本rc0只表示完成观察。脚本之后的 observer cleanup 单独记录，不计入库的收尾成功。

若原始基线同样失败、环境不匹配或输入不能触发，不能归因成候选新增回归。只有实际对照成立并完成一次非作者有界审查，才另记候选语义失败与现有评分遗漏，提出窄P2P（原本应通过的公开行为仍须通过）断言建议。不会据此直接改原成绩、共享reward契约或发布新材料；也不重解、修剪候选或扩大旧矩阵来使候选得分。

当前依据：[实际结果](results_public_cancelled_main_20261003.json)、[非作者核收](review_acceptance_public_cancelled_main_20261003.json)、[窄P2P方案](assessment_and_p2p_proposal_20261003.md)。回归和58键遗漏已证实，旧binding题级阻断保持；本批窄方案已获裁定批准，后续[单P2P材料修订](../revision_1c1_cancelled_main_p2p_20261003/README.md)另留新版本与消费结果；本次归因不重跑，旧原件不回写。后续094/095已发布，五行CPU验证及非作者核收均完成，实际59键结果另见上述新版入口；本次归因原件保留不回写。
