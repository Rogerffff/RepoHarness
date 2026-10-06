# Orange3 暂停检查点

2026-10-03。按总协调转达的用户暂停要求，本线程已停止新增执行，等待用户明确恢复。收到更早的发布、部署或排队消息不自动接续。

## 安全位置

- 本包没有在途CPU作业或子agent。最近的 `orange9b-envonly-derived-c-20261003-v4` 与 `orange9b-envonly-actor-c-20261003-v1` 均返回0，原件已回收，actor／网络／网关／桩清理已核。
- 本线程没有自动重试器或后台派发。此前75重试均为逐次手动申请，已停止；不再申请下一槽、启动矩阵、发布／部署或发送常规跨线程通知。
- 本轮第九版仅做本地只读核对和发出部署请求；未在该版执行trusted prepare、镜像构建、正式矩阵或CC。暂停消息到达时没有未完成的本地编辑单元。
- Orange22固定GPU请求留在原队列。执行状态由统一执行者管理，本线程不新增请求、不改绑旧工件、不自行改队列或取消其在途作业。

## 固定版本与证据

- Orange22：064材料、第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`。CPU验收及非作者窄核完成；[固定请求](probe_request.json) SHA256 `f39b8e2ba9144c2750fab673fda3e673f47b8a3282f1308067ef60246a0fe9bb`。[提交回执](tasks/22e98f8f/probe_submission_receipt.json)、[接收回执](tasks/22e98f8f/probe_intake_receipt.json)保留已提交、执行者收到并复核中的实际状态；本线程尚未收到模型结果。
- Orange9b54：原020／第五版／完整已批准env_v2的私有概率校准完成。[校准收据](tasks/9b5494e2/probability_precheck_v2.json) SHA256 `1c643c35bdc9c94d0ee5a060da0773adfe7ab31932a37e0e033954bf18d34180`，base/gold差0，G1差0.38716698009532013；不使用新hidden，不代表正式评分或最终sysconfig组合验收。旧consumer拒绝与75原件保留。
- 余三题已收到共用发布者第九版封版通知：`cat2-cpu-r2e089092-swe13-git-20261003-v1`，本地 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe13_git_candidate_v1/`，源码根 `repo/`，929文件，外部manifest SHA256 `694a1cd364a4bc3348069bd9dd362c4432fbd25339b192d149a2f29d9a709230`已本地实算匹配。材料089合并替代4014的active057；50f6公开090／隐藏091；9b54隐藏092。发布者登记9b54 base配方 `7e1710…`、含sysconfig完整配方 `050316…`。本线程尚未完成该版题级材料／consumer／配方核对，也未确认cpu-c部署。
- 26个新版正式候选的observed仍为空。固定草案、旧作者收据、独立报告及Orange22请求没有因本次暂停改写。[工作入口](preparation.md)与[CPU记录](cpu_preparation.md)停留在暂停前已完成事实；本检查点优先表示当前是否继续工作。

## 恢复后的唯一下一步

用户重新确认分工并明确恢复后，先核对cpu-c第九版的部署回执、929成员与可信读回，以及本包三题的实际材料／consumer／配方绑定；核对完成后才按原槽规则接续新矩阵和必要CC检查。

当前阻塞项是用户暂停及待确认的第九版cpu-c部署／题级绑定，不是材料草案待终审。没有新的用户审批要求；恢复前不轮询部署、重试作业或转发旧消息。
