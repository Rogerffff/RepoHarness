# Scrapy 恢复检查点

2026-10-03，Asia/Singapore。用户已批准三方协作、总账工具与路由迁移，并恢复实验。依据为[现行协作流程](../../coordination_workflow_20261003.md)及[迁移恢复记录](../../coordination_resume_20261003.md)。[旧暂停点](pause_checkpoint_20261003.md)保留原件。

## 当前接续位置

- 本包仍只负责`r2e_gym_subset::scrapy__a95a338eeada7275a5289cf036136610ebaf07eb`，材料为rev4／066、067。正式8候选、R5真实CC加桩开发检查、警告观测及非作者CPU核查已完成，无已知题级CPU阻断；证据复用，不因迁移重跑。
- 原探针请求`r2e-scrapy-a95a-cpu-rev4-20261003`保留。原请求与GPU冻结副本逐字相同，SHA为`2e351e520c216977d88529b1725a2af0f609a2ede7423a425c0740b2284965a0`；总账材料版本为`binding-sha256:21c3005ea2ce12591aa8a029b868730fa1ed9d865f9cf96898cc9292017d77dd`。
- 本次读到请求为`queued`，未领取、无模型job及总回执；GPU原登记为`received_intake_review_pending_not_dispatched`。这只证明接收登记，不证明GPU准入或运行通过。
- 本题没有CPU、子agent或后台重试在途；本次接续不需要新增CPU实验。CPU资源文档仍保留派发暂停门，由发布线程维护，本题恢复记录不解除该门。

## 下一步与交接

题主先通过[总账工具](../../task_board_usage_20261003.md)更新本题progress，再定向向GPU线程发送原请求ID与[总账路径](../../repository_work_packages_20261002.json)，发送回执记录在本包[交接记录](probe_handoff_20261003.json)。迁移请求没有通知事件，不伪造旧事件或发送成功时间，也不创建重复请求。GPU继续负责输入核验、固定版本准备、单卡队列及两款模型各首次运行，直接向本线程返回总回执。

收到总回执后先核实际版本、完整轨迹、候选与原评分，区分运输正确性和语义正确性；再用工具`ack`及`update-task`收回交接并写下一步。若发现任务缺陷，记录对应材料版本阻断，保留原评分。环境验收或探针结果都不自动授予训练／heldout资格。
