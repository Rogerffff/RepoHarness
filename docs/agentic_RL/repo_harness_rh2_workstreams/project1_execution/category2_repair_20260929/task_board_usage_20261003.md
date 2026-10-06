# 总账工具：最小用法

2026-10-03。入口 `rh2/scripts/category2_task_board.py`，仅Python标准库，适用于本机macOS和Linux。工具只更新JSON，不启动实验、不发送消息、不解除CPU/GPU暂停。各线程直接通信，GPU原账本仍是实际运行事实来源。

## 每次先读自己的待办

在仓库根执行，`THREAD_ID`填写自己的登记线程ID：

```bash
python3 rh2/scripts/category2_task_board.py --board docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category2_repair_20260929/repository_work_packages_20261002.json --actor THREAD_ID todo
```

`show --task swe_gym_lite::python__mypy-15184`读一题；`show --request REQUEST_ID`读一个请求。R2E键使用`r2e_gym_subset::完整instance_id`。每次修改从刚读到的目标记录取`revision`，传`--expect N`；不拿全总账版本判断某题是否过期。

## 写入动作

所有命令沿用上面的`--board`和`--actor`，JSON参数先保存到小文件，再用`--data 文件`传入；不用手动改共享JSON。

| 动作 | 参数与最小输入 | 谁执行 |
| --- | --- | --- |
| `update-task` | `--task KEY --expect N --data 文件`；只允许progress里的材料、阶段、检查点、下一步、阻塞/受影响版本和活动请求字段 | 题主 |
| `submit` | `--request ID --data 文件`；正常题主交接另加`--task-expect N` | 题主；GPU也可提兼容publish |
| `claim` | `--request ID --expect N`；已领取返回`changed:false`，须接续已有作业，不能再启动一遍 | 接收方 |
| `needs-input` | 请求和版本；输入为回执路径/SHA、缺项摘要、`safe_closed:true`（已有执行已安全停妥） | 接收方 |
| `supplement` | 请求和版本；`supplement_ref`、`supplement_sha256`，只补说明，不改原输入；材料字节变化另建新请求 | 发起方 |
| `receipt` | 请求和版本；`receipt_ref`、`receipt_sha256`、可选`summary`、`safe_closed:true` | 接收方 |
| `cancel` | 请求和版本；`reason`。只登记意图，不结束作业或释放活动交接 | 发起方 |
| `confirm-cancel` | 请求和版本；安全收尾回执路径/SHA及`safe_closed:true`，实际无在途后才执行 | 接收方 |
| `ack` | 请求和版本；标记已读结束回执，消除该请求的未核收待办 | 发起方 |
| `notice` | 请求、版本和`--event EVENT_ID`；`delivery_ref`为真实发送成功的消息ID或工具回执位置 | 该事件发送方 |
| `correct-summary` | 已结束请求和版本；`summary`、`correction_ref`、`correction_sha256`，引用事实更正说明并保留旧摘要 | 原请求接收方 |

正常题目交接结束后，题主先对请求执行`ack`，再用`update-task`把`active_request_id`设为null并写下一步。两步都要做：只清指针仍会留下未核收待办，只`ack`仍保留活动交接。独立支持或兼容请求没有题目活动指针，只需`ack`。这些动作不会自动清空`blocker`或`blocked_material_versions`；`ack`只标已读，不代表题目验收通过。

已结束回执的展示摘要有笔误时，由原接收方执行`correct-summary`；工具保留原摘要和更正依据，只修改摘要及本记录的版本、更新时间。状态、原回执路径/SHA、原通知和题主阻断保持，不重新派发实验，也不生成额外普通通知。真正的评分证据或材料需要更改时不能用此动作代替。

正常提交文件例：

```json
{"kind":"publish","task_key":"swe_gym_lite::python__mypy-15184","material_version":"nested-v2","input_ref":"仓库相对路径/material_manifest.json","input_sha256":"64位小写SHA256"}
```

`cpu_support`须说明`scope`（如主机/组件），可不设单一task_key，并加`affected_tasks`、`related_request_ids`。GPU兼容publish直接回GPU。两者不占题主的正常活动交接。同因故障先查询并关联现有请求，不重复建单。

提交后读取返回的`notices`事件，发送一次“请求ID＋总账路径”给登记接收方；发送成功后才用`notice`登记。发送失败保留`sent_at:null`，下次`todo`会列出。允许重复提醒；同请求ID同身份/输入重复提交不新增，输入变化拒绝覆写。无需回复“收到”。

## 写入保证与限制

锁定独立`.lock`文件，锁内重读总账，核目标记录revision后原子替换JSON；保留其它题和未涉及字段。锁文件本身不表示有作业，不要手删来解除锁。版本冲突返回退出2：重新读目标，理解对方变更后再提交，不盲目增加revision。`show`/`todo`也使用同一读锁。

角色从`coordination.shared_publication_owner_thread_id`、`probe_executor_thread_id`及各group.owner_thread_id取得；可加`read_only_observer_thread_ids`供巡检只读。历史coordinator不自动取得写权限。`--actor`是合作式字段归属声明，不是系统认证，也不能抵御本来就能直接写文件的用户。

工具在提交/首次领取时核输入文件SHA，回执和补充也核实际文件。`safe_closed`仍须执行者根据真实作业和清理证据填写，工具不能代替远端检查。GPU在真正派发前仍要读题主当前阻断与运行控制；本工具不是运行闸门。

## 迁移接口

保留原`groups/tasks/coordination`及历史字段；顶层`requests`是按ID索引的对象。请求ID及原输入SHA保留，迁移不要创建虚构通知。每题progress及每个请求使用独立整数revision（首次0）；输入不可变字段为kind/task_key/scope/affected_tasks/related_request_ids/material_version/input_ref/input_sha256。请求路由从登记角色填入，历史任务实际状态逐项映射。

当前维护检查：18项通过，包括真实两进程不同题无丢失、同题旧版本冲突、原子替换故障不毁旧账、越权字段/角色拒绝、取消先收口、输入漂移/受阻版本拒绝、提醒幂等和只读巡检。ruff通过。实际总账由一次性迁移者单独写入，本工具测试仅用临时文件。

摘要勘误入口补充后，相关维护检查为24项通过、ruff通过：验证非接收方／活动请求／越权字段／证据漂移／旧版本被拒，并核对更正前后原回执、通知、其它题与阻断逐字段保持。检查仍仅用临时文件，不修改正式总账。
