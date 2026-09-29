# B4 CPU 交接补审

结论：**最终三条方案未发现设计阻塞，可交接为按需选择的未来 CPU 诊断。** 每题只有一个主实验，候选数量与待区分问题相称，未把整批 CPU 通过或全面 actor 验收设为固定 grader 语义诊断的前置条件。此结论不表示 runtime 已就绪、候选已构造或实验已执行。

读取窗口：2026-09-20 22:55:42–22:56:44 UTC（本地次日 06:55–06:56）。首次队列仍含 Moto pending；末次已为 `reviewed_static_plans_complete`，三项均为 `reviewed_static_plan_not_executed`。收口仅改变 Moto 状态及复审说明，三项实验设计未变；三份最终 review 哈希均未变。最终 `expansion/batch04/cpu_queue.json` SHA256：`ce48b218c4e5efaf507be1964a973f34ca112067dbb5c9bb7cd0836b111e9604`。

| 题目 | 主实验与判据 | 交接结论 |
| --- | --- | --- |
| DVC 4185 | 同条件 base/gold 的两阶段本地工作流：重开 Repo 后分别核 false 的 status 与未变真值参数的不带 force commit；只附 start 改值这一正向控制。 | 两个公开症状保持独立，不把“false 不再 new”当成全部修复。不需要新候选。若 gold 仍触发未变参数确认，支持原满分未覆盖完整题意；若未触发则检查实际初态/调用链并修正预测。 |
| mypy 16869 | base/gold/一个经语义及导入校验的 Unpack 候选；原 `_Ts` 文件 CLI、公开名 `Ts` 与 `--include-private` 是同一实验的必要判别条件，最后保持原六项评分。 | crash 修复与默认 private 声明过滤分账；语法可解析还不足以证明类型参数语义、顺序和导入正确。只有合格候选因等价拼写被精确输出断言拒绝，才能确认误拒。不会额外要求候选修复 gold 也未处理的既有 private 过滤。 |
| Moto 6114 | gold 与一个仅在 ARN 分支返回首个集群的错误候选；创建两个真实对象，查询第二个的实际 ARN，独立核 Identifier/ARN，保持原 35 项评分。 | 两个变体足以区分身份与数量，无须另加 base 或第二反例。只有错误候选 reward=1 且目标身份失败才是新观测误收。合法、已存在、同账户同区域 ARN 即可；未知 ARN 边界不升级为契约。 |

入口和原件的有界核验：三题 gold/私有 grading/引用路径可定位；逐题 build plan 选项规范化哈希、归档成员哈希及所用 CLI 参数均与队列一致。读取了三个最终 card/review、必要公开入口源码和 DVC wrapper/recipe，未全面重审题目。

- **DVC：**使用 `dvc_install_v1c` 的归档代码与派生镜像，同时传原 `--recipe` 和完整 tasks-key `--bindings` 输入，所选 `tasks["iterative__dvc-4185"]` 单条绑定哈希相符；audit 输出不是输入。recipe 确有先离线安装 `networkx==2.3+rh2.1` 再安装 `.[all,tests]` 的路径。共享 `setup.py` Moto pin 从 `1.3.14.dev464` 到 `1.3.14` 须固定在两侧，不计入业务候选，也不能称 pristine base。若复用 launcher，`RH2_DVC_REPAIR_ROOT` 须显式指向已准备的 v1c 根目录，不能落回旧默认。
- **mypy / Moto：**均为 `install_wave1` 归档 baseline CLI，使用逐题实际派生镜像及 `install-wave1:<instance_id>` 身份；无 recipe/materials/bindings wrapper，也没有可套用的 `revised_install`。mypy 保持原 Python 3.12 条件和选择/并行命令，不另强制加 `-n0`。

实施提醒（不要求改封存稿或扩必测范围）：DVC 只需记录并拒绝确认的本地 hook，避免交互挂起且保存提示/调用次数；mypy 原文件命令走 `create_source_list`，不是 `-m/-p` 的 runtime import，候选使用现有导入设施仍须验证实际输出；Moto 应比较同对象身份或同一时刻按名称查询，不能拿创建时 `creating` 与查询时 `available` 的整包字典强行相等。

未完成的是未来执行准备：确认目标镜像/离线 payload、准备对应归档 Python runtime 和以 `rh2` 结尾的新 code-root、重定位历史 prepared/private 路径、构造并冻结 mypy/Moto 候选 diff/SHA、使用独立输出。构建审计不能冒充缺失 wheel/context，历史 grader 成功不能冒充当前 actor 消费。固定 grader 可先完成本题语义诊断，正式模型开发前再独立核 actor 消息、环境、导入及权限。

没有新增实质必修项。全程仅静态读取和元数据核验，只新增本报告；所有新实验仍为未执行。
