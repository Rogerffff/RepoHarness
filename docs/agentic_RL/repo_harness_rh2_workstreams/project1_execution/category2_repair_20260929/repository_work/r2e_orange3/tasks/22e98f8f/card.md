# orange3 22e98f8f：两模型首轮及独立语义复核完成

更新：2026-10-04。CPU及独立窄核已完成，原请求两模型首轮已returned并ack：Coder/Qwen3.6均正式1（23/23）、正常完成。原FrozenPatch、完整轨迹和逐参考结果已回收；[作者修法与行为分析](probe_analysis_20261003.md)和[非作者语义复核](../../reviews/orange22_first_probe_semantic_review_20261003.md)均完成，无必修项。两份逆置换修法符合公开语义，过程中的错误推断和自测限制保留；[当前首轮验收收据](probe_first_round_acceptance_20261003.json)接续封存分析中的生成时状态。当前首轮范围完成；GPU v2暂缓普通复采，不自动补至每模型3次，不能称稳定能力或训练资格。

`r2e-mr-064`删除直接实现答案、改正base映射描述，正文SHA `f8701d3a…`。复用[干净上下文阅读](../../../../reviews/orange22_public_reading.md)及[独立隔离修订核查](../../../../reviews/orange22_isolated_revision_review.md)。[existing_candidate.json](existing_candidate.json)是当时的冻结记录，其未发布状态不回写；实际接续见[版本绑定](cpu_release_binding.json)。

首版CPU发布material_v13／pins_v14包含064，新grading只更新修订号，隐藏测试、expected及run_tests内容不变；仍为23键。历史正式noop0（22/23）、gold1（23/23）、DG0（20/23）及清理获独立复核限定复用：noop/gold raw eval当前缺本地原件，日志SHA仅账本记录而非本轮复算；DG原文及逐键已核。这不是本轮重新评分，历史三者使用带sysconfig的配方。

[首轮CPU收据](cpu_actor_v1_receipt.json)：实际agent54321，`.venv` Python3.7.9、NumPy1.17.5和Orange工作树正确；公开helper 1passed，公开数值重复例失败符合原缺陷。字符串例未执行。完整空FrozenPatch与轨迹已保存，actor/网络/网关全部清理。CPU使用合成端点，未作模型推理、未运行grader；来源public_hints没有随CPU spec.prompt交付。

我本次构建漏带`--sysconfig-fix`，首镜像`29d371…`不能代替历史`+sysconfig_v1`／`e2e17bf…`的环境绑定。已保留原件并报告，改在第五版冻结入口补建；新prepared为本机重新生成，22e98四面字节与首版相同。[最终CPU证据](cpu_acceptance.md)与[实际prepared补收](prepared_artifact_receipt.json)已通过非作者核对；中性[公开说明](public_development_brief.md)已随固定单题请求绑定提交，见[提交回执](probe_submission_receipt.json)。新旧daemon image ID不同，复用依据来源digest、评分材料、配方和实际环境证据对齐，未比较所有旧镜像层。旧0／1／0不因题面-only机械重跑。

用途是题目与环境质量调查、附带基座难度观察；训练／留出资格未授予。grader准备预算沿历史1200秒，由统一执行者核实际生效；本轮`--no-grade`不能证明当前grader已运行该值。

[执行者接收回执](probe_intake_receipt.json)保留当时复核状态，不回写；当前已收齐两模型首轮，原执行与用途边界见新的作者分析和总回执。

2026-10-04当前采样政策：GPU最新v2覆盖优先已取代v1，Orange22两模型a2/a3明确暂缓，ordinary_repeat_dispatch_allowed=false；[最新政策收据](probe_repeat_deferred_receipt_20261004.json)与题级progress已同步。旧[计划接收](probe_repeat_plan_receipt_20261003.json)保留历史，不再当作当前在途/必做。两份有效首轮样本不重跑；未来抽样复采须按全批共同题组选择，并逐样分析实际材料/预算/采样/代码身份及完整候选/轨迹。
