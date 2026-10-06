# 8567：九行联合CPU验收通过，固定探针已提交

2026-10-03。**原已验两行＋新七行及公开actor获[组合非作者核查](../../reviews/non_author_8567_combined_cpu_review_20261003.md)通过，固定双模型首轮探针已实际提交。** R14 正式 job `pyd8567-formal-20261003001737-r14-b631d` 的 noop／gold 两行各 162 参考实际 0 分，已获[非作者部分CPU窄核](../../reviews/non_author_8567_partial_cpu_review_20261003.md)通过，可保留原 job 归属直接复用。第三行 c3_reorder 在安装／测试之前的控制面保护调用0099超时300.071秒，原结果为 `infra_failure/reward=null`；它没有候选行为评分，不能改作模型0分。

375件原始证据及归档tar、458项完整baseline、三候选源码／FrozenPatch运输已核。前两行安装退出0、实际UID54322／Python3.8.19／core2.15.0及受保护有效测试身份通过；c3没有测试阶段导入／版本审计。三候选与三grader实际删除成功，归档时本run容器／网络为空。外层“收尾异常或存在残留”掩盖首个“真实测试标记缺失”异常，不证明清理残留。

noop两个F2P失败、160项P2P通过。gold两个F2P和新增两个P2P失败、原158项P2P通过；这些是完整执行后的普通行为失败，不因它是历史gold而改判infra。两份正对照的既有语义意见保留；它们的新正式全参考结果见下文，不改变旧失败轮c3的null。

新的[七行补验输入](../../cpu_acceptance_20261003/8567_resume_v1/README.md)只删除已验收的noop／gold，runner字节、剩余候选字段和顺序、材料、安装、精确镜像、资源及预算全部不变，[非作者输入窄核](../../reviews/non_author_8567_resume_input_review_20261003.md)已通过。四个输入成员和单独的运输清单已上传新的 `formal_8567_resume_v1`，逐件大小／SHA及初始精确集合通过；上传当时没有派发候选或Docker工作；随后实际补验另立新job。旧 `formal_v2`、原失败轮和null结果不覆盖。

共享CPU支持 `swe-pydantic8567-control-protect-timeout-support-v1-20261003` 已返回并核收/ack：一次同镜像、同资源和原300秒的保护-only诊断149.041秒完成，主要为解释器目录chown约145秒；63件绑定原件及自有清理通过。去掉诊断观察边界后保护正文逐字等于原脚本；诊断setup只保留restore/apply/attest而省略激活/显示，不能冒作完整评分链恢复或解释旧超时根因。此支持回执仅支持有界接续；题级普通探针准备随后依据完整九行及actor组合验收通过。[核收原件](../../coordination_20261003/8567_shared_cpu_recovery_readback_v1.json)固定范围。新七行job `pyd8567-formal-20261003013213-r14s1-a8dbf` 于01:32:16 UTC入cpu-a slot1，原noop/gold不重跑；于02:00:39 UTC自然结束rc0。928原件绑定及归档tar已核收，七行各162参考完整，实际UID54322/Python3.8/core2.15.0、候选源/import、受保护测试、安装步和运输自动核对通过，自有容器/网络查空。新运行成功不解释旧超时根因。公开actor首派`pyd8567-actor-20261003020327-r14-f200e`返回75/All CPU slots busy，未入槽、无题目执行；之后公开actor新job `pyd8567-actor-20261003020814-r14-e919a` 实际入槽并结束rc0，32原件核收；实际UID54321/Python3.8/core2.15.0、源码导入与可写性断言、原公开示例预期失败及已有节点1 passed通过。首消息保持原公开字节（含CRLF），420个解码请求字符串未见私有材料。组合独立核查已通过；8316随后五行完成后再遇同阶段保护超时，另按共享CPU支持接续；不撤销本题已完成的CPU核查。

| 实际正式行 | 本次采用的job | reward | 关键参考结果 |
| --- | --- | ---: | --- |
| noop／gold | 原失败轮的已完成两行 | 0／0 | noop两个F失败；gold两个F和新增两个P失败，原P全部保留。 |
| c3_reorder／ok_post_attach | 新七行补验 | 1／1 | 全部162参考通过，两种修法均可接受。 |
| upstream261 | 新七行补验 | 0 | 原F修复，新增F及两个P失败。 |
| bad_nonvalidators_after_pv／rv_ser_to_end | 新七行补验 | 0／0 | 原F失败，新增F/P通过；其余参考无额外失败。 |
| c3_serpass／n_python_only | 新七行补验 | 0／0 | 两个F和新增两个P失败，其余参考无额外失败。 |

[题主七行核收](../../coordination_20261003/8567_new_seven_formal_owner_readback_v1.json)保留逐行参考及实际源码身份。旧失败轮的c3没有评分，不能将本表新c3的1分回写给它。

[固定探针输入](probe_request.json)及[CPU快照](cpu_acceptance_snapshot_20261003.json)已生成，1364条本地路径SHA绑定核对通过；请求 `swe-pydantic8567-behavior-v1-20261003` 已落账并实际通知GPU执行者。当前CPU准备仅支持版本固定普通探针，GPU实际镜像/wheel安装、当时模型checkpoint、两模型完整轨迹与评分仍待，不授予训练资格。逐行原件仍见[四题CPU账本](../../cpu_acceptance_20261003/remaining/results.json)，输入、审查及实际上传读回见[协调记录](../../coordination_20261003/)。baseline环境锚null、非参考含空格参数解析缺口及控制桩／typed训练边界继续保留。
