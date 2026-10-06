# Scrapy暂停检查点

2026-10-03（Asia/Singapore）。按用户最新要求暂停，等待用户明确恢复；不新增任务、重试、发布、部署或跨线程通知。

## 已停状态

- 本包没有在途CPU作业或需要清理的自有资源。最近作业`scrapy-a95a-dev-b-20261002T183830Z`已自然完成，包装器状态finished／returncode=0；正式矩阵、CC actor、relay／network／stub及两个私有观测的清理证据均已保存。
- 非作者子agent`/root/scrapy_cpu_review`已完成最终报告；未起新agent或下一轮。
- `dispatch_cpu_dev.py`仅按次手动调用，`fetch_cpu_dev.py`仅回收原件；无自动重试循环、后台派发或自动化。已核本地没有这两份脚本的活动进程，停止后续调用。
- 既有GPU请求保留冻结状态，由统一执行者负责安全停派。最近收到的确认是已核请求摘要并登记、未派模型；本轮未再轮询或操作GPU队列，不将旧确认冒充暂停时的新状态。

## 固定版本与证据

- 当前材料rev4／`r2e-mr-066`、`r2e-mr-067`。最新准备与actor绑定R5：`cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest`80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，宿主runtime_cpu_v2。
- 已完成的8候选正式矩阵保留R4绑定：manifest`621e73660ea5685b9a77c353e7f4f3664d7eefa073aed8454bae1ae3e32f388f`。本题public／grading bundle与066／067在两版相同，未改绑旧FrozenPatch或重写旧尝试。
- 当前阅读入口：[preparation.md](preparation.md)。CPU结果：[验收报告](cpu_acceptance_20261003.md)、[机器记录](cpu_acceptance.json)、[非作者核查](review_cpu_acceptance_20261003.md)。最近原件：`runs/category2_repair_20260929/r2e_scrapy_cpu_20261003/scrapy-a95a-dev-b-20261002T183830Z/remote_evidence`；56份文件逐SHA核回，无省略，源chmod／mtime未复制，不作为运行输入。
- 已提交请求：[probe_request.json](probe_request.json)，SHA `sha256:2e351e520c216977d88529b1725a2af0f609a2ede7423a425c0740b2284965a0`；[交接记录](probe_handoff_20261003.json)。请求文件和唯一队列保持原件，没有新增请求或修改其绑定。

## 恢复后的唯一下一步

**用户明确恢复并重新确认分工后，仅与统一GPU执行者核一次既有请求／在途状态。** 若已有回执，先审原轨迹、候选与评分；若仍未派发，由执行者按重定分工接续。不得另建重复尝试、因旧消息自动恢复或机械重跑CPU矩阵。

当前CPU材料及开发验收无阻断；真正未完成的是GPU宿主核验／队列准入和两款模型各首次结果的题主语义审计。现在的停止条件是用户明确暂停，恢复不以旧线程消息或资源空闲作为授权。
