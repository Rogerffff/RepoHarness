# Pillow 暂停检查点

**历史记录：后续已获用户批准按三方流程恢复。当前状态见[准备入口](preparation.md)，以下保留暂停时事实与要求。**

2026-10-03。按“梳理分类二处理背景”线程转达的用户暂停要求保存；等待用户明确恢复。停止新增任务、派发、轮询重试、发布部署及常规跨线程广播，不因旧消息接续工作。

## 当前安全状态

- 本线程已停新增工作。三题必要 CPU 运行及非作者结果复核全部完成；本包 CPU 作业均已自然结束、退出和清理正常，槽已释放。没有本线程持有的后台派发器、自动重试器或 GPU 进程。
- 本地子 agent `pillow_cpu_review` 已保存原唯一报告并停止接续，无远端／容器／模型作业。保存前已完成三题 CPU 与两份 `2d01` 模型现有结果窄核，均为限定范围 PASS；不将暂停后的未核边界改为通过。最终报告 SHA 为 `2062c940…`，同字节快照保存在 `review_snapshots/2d01_model_results_review_v1.md`（相对于本包忽略原件根目录）。checkpoint 权重身份、长窗口／最大输出全链生效和 Coder 排除面变化的具体路径仍保留本仓未核边界，执行者另有独立执行报告。
- `3a61`、`a682` 请求已由统一 GPU 执行者接收登记，最近回执确认两题尚未发模型，需下一入口冻结支持已审 `unchanged` 交付。请求原件保留，不新增或自行派发；队列和 GPU 暂停由执行者维护，本线程没有 GPU 控制权。

## 固定版本和证据入口

- `2d01` CPU 保持首版 release，manifest `28202196…`，材料 `063`、隐藏树 `bd62b707…`。两模型各一次均返回 60/62、reward 0；题主原日志定位为只保留标签、漏修原有 1／L 图像往返。执行者双模型复核已回传，本仓两份现有结果窄核也已保存为 PASS；结果可消费不等于模型修复通过。入口路径／SHA 记录错配保留正确两对，不重跑模型。见 [CPU 记录](cpu_2d01_acceptance_v1.json)、[Qwen 题主核查](model_audit_2d01_qwen36_a1_v1.json)、[Coder 题主核查](model_audit_2d01_coder_a1_v1.json)、[执行回执](gpu_execution_receipt_2d01_v1.json)及 [非作者唯一报告](reviews/non_author_cpu_results_20261003.md)。
- 另外两题评分／actor 固定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest `80ee228d…`；镜像复用第四版已验 builder（manifest `621e7366…`），Pillow 材料和 builder 字节不变。`3a61` 材料 `070/071`，18 方／74 键，6 正 12 负；原 C1 为正、原 gold 为负。`a682` 材料 `072`，16 方／93 键，3 正 13 负。两题 CPU 与非作者结果核查都 PASS。见 [3a61 CPU](cpu_3a61_acceptance_v1.json)、[a682 CPU](cpu_a682_acceptance_v1.json)。
- 冻结请求：[3a61](probe_request_3a61_v1.json)，SHA `122ee4b4…`；[a682](probe_request_a682_v1.json)，SHA `b6140994…`。接收状态分别保存在 [3a61 回执](gpu_intake_receipt_3a61_v1.json)、[a682 回执](gpu_intake_receipt_a682_v1.json)。接收不等于入队或已发模型。
- 原件根目录：`runs/category2_repair_20260929/r2e_pillow_cpu_b_20261003/`，含不可变 CPU 原件清单、重解析记录和非作者快照；GPU 原件分别在 `runs/ordinary_gpu_probe_20261002/remote/queue_v5/results/gpu1003-pillow2d01-qwen36-a1/`、`queue_v7/results/gpu1003-pillow2d01-coder-a1/`。连接凭据未写入本记录。

## 恢复后的唯一下一步

用户明确恢复并重新确认分工后，按新分工只读统一 GPU 执行者保存的两道新题接收／入口冻结状态，确定是否接续已有冻结请求；不重新跑 CPU／`2d01` 模型。真正外部等待项是新入口冻结、实际 GPU 镜像／公开交付核验及派发。`2d01` 现有双首轮结果已收口，既有 P4 和用途边界保留，不自动轮询或催发。

普通诊断、模型执行、题目修订验收和训练／留出资格仍分别记录；此次暂停不改变任何旧结果或用途资格。
