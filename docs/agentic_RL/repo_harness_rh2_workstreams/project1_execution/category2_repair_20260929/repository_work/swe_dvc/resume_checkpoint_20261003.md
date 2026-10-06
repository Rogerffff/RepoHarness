# DVC 恢复接续记录

2026-10-03。用户已批准三方流程、工具／路由迁移及继续实验，总协调的统一恢复通知替代行政暂停。已读新协作规则、本仓 `todo` 与 CPU 资源门控；发布线程04:32 SGT已解除三机派发门。5839题级缺陷阻断保持，本仓未修改control/setup。旧暂停原件不回写。

四题 progress 已由更新工具补齐当前材料版本、阶段、检查点和下一步；5839 的 R7／R8／R9 缺陷阻断保留。请求使用下列固定输入，已经落账、定向合并通知发布线程并登记真实发送回执：

| 请求 | 固定输入 | 接续内容 |
| --- | --- | --- |
| `dvc5839-uid-preflight-support-20261003-v1` | [共享修复输入](requests/dvc5839_cpu_support_v1.json) | 同一 UID 预检缺陷及实际原件；请求新冻结修复、CPU-a 部署、官方入口 |
| `dvc6954-publish-dvc6954-behavior-v1-draft-20261003-v1` | [6954发布输入](requests/dvc6954_publish_v1_input.json) | 13精确绑定、absent 文件保护、功能选择器；正式应用须核新增测试完整字节 |
| `dvc4166-publish-dvc4166-behavior-v2-draft-20261003-v1` | [4166发布输入](requests/dvc4166_publish_v2_input.json) | v2完整补丁、一对二绑定、3F／60P及确切兼容 wheel |
| `dvc9395-publish-dvc9395-behavior-v2-draft-20261003-v1` | [9395发布输入](requests/dvc9395_publish_v2_input.json) | v2完整补丁、3F／37P；正确对照为 c3_frozenfix，原 gold 应被拒绝 |

工具和通知记录在 `runs/category2_repair_20260929/repository_work/swe_dvc/board_actions_20261003/` 与 [发送回执](requests/handoff_delivery_20261003_v1.json)。实际状态从总账 `todo/show` 读取；普通进度不抄送协调线程。四项交接无需再次确认，输入发生变化则新建请求。

没有自动重试或本仓 GPU 请求。已有非作者子agent按原授权补核公开actor入口，未新建管理线程。5839的唯一优先运行步骤仍是：共享修复和 CPU-a 部署回执交付后，从新版本另建 prepared，先执行正式noop，确认实际安装和测试可达，再做gold／固定8、actor及非作者结果读回。等待时继续其它题独占工作，不重复已有私测，不用旧私测授予正式资格。

本地已准备 [public_actor_check.py](public_actor_check.py) 和5839的 [公开命令清单](tasks/iterative__dvc-5839/public_actor_commands_v1.json)，仅完成语法与公开输入来源核对，尚未运行。入口继承交付版本的真实 CC／relay／预启动／清理路径，独立镜像初态容器也使用原2CPU／4GiB／PID512 profile；真实首请求须包含逐字题面与已固定开发说明，四条命令只核实际身份、激活保护、两条已存在公开测试和CLI帮助。实际配置必须等新冻结交付后绑定 code／prepared／image SHA，不能把本地入口准备当作 actor 验收。

6954公开actor输入已准备，job `dvc6954-public-actor-20261003-v1-001` 和 `dvc6954-public-actor-20261003-v1-002` 两次领取槽忙返回75，未获准入，容器和模型请求均为0。两次记录为 `runs/category2_repair_20260929/repository_work/swe_dvc/public6954_r5_v1_admission_001.json`、`public6954_r5_v1_admission_002.json`；下次使用新job后缀003，不复用旧ID，不高频轮询。本次固定R5 `cat2-cpu-r2e078079-swe7-git-20261003-v1`（已部署公共Git修复）、新prepared summary SHA `f84b0049f0842372c679b110e8bd41c5aa45396be27b5b6ed8e5d7d5140f7482`、公开bundle `9186b41928accff7f5b576f240163c6c87c013cc9cfb219fa8a42571b3d526fb` 和已准备依赖image `083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`。只执行 [6954公开命令](tasks/iterative__dvc-6954/public_actor_commands_v1.json)，不消费尚未发布的私有修订或授予正式reward。独立入口／输入在 `packages/swe_dvc/public6954_r5_v1/`；实际执行后保存真实首请求、逐命令结果及清理，不因收到发布回执热换在途版本。

第三次 `dvc6954-public-actor-20261003-v1-003` 已于20:49:32 UTC获slot0，作业状态为running；没有启动其它Docker实验。4166／9395的公开命令和独立R5输入正在做不涉及Docker的prepare，均未执行actor。今晚各题GPU结果按更新后的[行为分析要求](../../overnight_watch_20261003.md)收齐定位、工具／并行、验证与效率证据；当前仍需CPU与GPU。
