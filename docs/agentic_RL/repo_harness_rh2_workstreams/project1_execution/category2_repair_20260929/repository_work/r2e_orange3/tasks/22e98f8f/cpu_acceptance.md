# 22e98：最终CPU证据

2026-10-03。**CPU证据及非作者窄核已完成，固定单题GPU请求已提交；尚无本轮模型成绩。** [独立收据](independent_cpu_review_receipt.json)核40/40项，[实际prepared补收](prepared_artifact_receipt.json)与[提交回执](probe_submission_receipt.json)接续原作者收据；原收据生成时的待复核状态不回写。 本次仅修题面，评分内容没有改变。[机器可读收据](cpu_acceptance.json)包含精确SHA及忽略原件路径。

最终使用第五版冻结入口 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228…`。本题四个任务面与首版逐行相同，仍为064题面、23键；registry更新为v17／pins_v18不改变这道题的评分内容。

补建作业返回0，实际新镜像 `ad9d2a37…`，配方 `r2e_derive_v1+sysconfig_v1`，摘要 `e2e17bf…`与历史评分对照一致。21项镜像复核全部通过，sysconfig指向`/opt/py`且无旧私有前缀。前一镜像漏带sysconfig的错误与证据保存在[首轮收据](cpu_actor_v1_receipt.json)，不覆盖原件。

最终CC作业返回0、正常完成。实际agent UID/GID54321，`.venv` Python3.7.9、NumPy1.17.5，Orange及widget从工作树导入；HostConfig和cgroup实测2 CPU／4 GiB／512进程，无私有挂载，对外网络被拒绝。首HTTP包含完整新题面`f8701d3a…`，保存prompt `cbb5bef0…`，网关与桩消息一致，旧答案段不存在。

四条Bash检查中preflight／身份导入／公开helper分别返回0，helper为1passed；数字重复例的映射`[1,2,0,1,2]`不能还原输入，因此返回1，符合原缺陷。字符串例因前一断言停止而未执行，同文件完整回归也未执行。此结果不能叫模型失败，旧helper通过也不能叫修复通过。

原生FrozenPatch为空、冻结导出有效，完整轨迹保存；excluded缓存路径变化据实保留。actor、relay、network、gateway与stub均正常清理，残留为0。两次actor均为脚本端点，不是真实模型推理，合成tokens／cost不可当费用；本轮未运行正式grader。

复用历史正式noop0（22/23）、gold1（23/23）、DG0（20/23），逐参考、账本SHA、日志SHA、退出与清理见收据。隐藏测试树、expected及run_tests原文摘要不变，最终配方摘要一致，独立窄核允许限定复用。noop/gold逐测试raw eval当前缺本地原件，两份日志SHA仅按账本记录，未本轮复算；DG原文可逐键核验。新旧daemon image ID不同，复用依赖来源、材料、配方及当前实际环境证据，不声称完整镜像逐层相同；不为补档机械重跑该矩阵。grader准备预算沿已验1200秒；DG准备实际303.30秒。统一GPU入口须登记实际生效值，不能把本轮CPU的1200秒求解检查预算当成grader已执行的证据。

来源public_hints没有随CPU的spec.prompt交付。探针只附[当前中性公开说明](public_development_brief.md)，最终HTTP交付由执行者核对；不整体发送本目录或私有资产。模型、次数和求解预算沿`probe-wide-v1`。本题只用于题目／环境质量与基座难度调查，不授予训练或留出资格。
