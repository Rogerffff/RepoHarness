# Pydantic 三题 CPU 接续脚本窄审

日期：2026-09-29。结论：本次静态核对未发现阻止按当前方案启动的正常路径问题。尚未执行，不能据此认定题目通过或环境合格。

这是跨包独立核验：审查者未编写 `pydantic_followups.py`，复用当前批次上下文及既有静态材料，不是新的全套盲审；不构成 OS 隔离证明。范围仅实际 CLI/字段、输入和输出判据、失败归因、公开/私有身份与清理。未执行远端、容器或历史项目。

## 核对依据与结果

- 脚本：`rh2/experiments/swegym_cpu_preprobe_20260929/pydantic_followups.py`，SHA256 `ba6358b80405da3878b7c0ad6fb0a39be4fd74dff3b2997ed140f32882734105`。对应三个题的 `runs/swegym_cpu_preprobe_20260929/task_inputs/` 中命令、补丁、镜像计划、安装配方及 manifest 已核对；manifest 指向的字节均相符，私有 gold 与本批正式 gold 副本相符。
- 对照实际 `frozen_code_v1/rh2` 的 devcheck、安装 wrapper、replay_grade 和 sandbox_profile，四个固定摘要相符。CLI 参数可达；当前供应关闭时 wrapper 替换实际候选安装段有效。正式 ledger 的 `test.segment_completed` 是当前冻结入口真实产出的字段，不能用旧 ledger 缺少此字段推断脚本有误。`post_observation_append` 被 wrapper 接受，新增 core 身份打印不改安装或评分。
- 三题 core 版本分别为 0.27.0、0.42.0、0.31.0；参考总数分别为 1/127、1/38、2/273，与对应既有记录一致。不可变 base digest 与 image config ID 分别检查，公开 actor 使用原镜像，私有行为使用同一 base，正式 grader 使用仅附加 wheelhouse 的派生镜像及离线配方。
- 对脚本做 AST 语法检查，对各题公开命令及额外私有命令做 `bash -n`，均通过。这些检查不执行项目代码，也不代替运行证据。

## exact marker 与变体语义

| 题目 | 实际公开/私有命令与脚本判据 | 结论 |
| --- | --- | --- |
| 5662 | `COMPARISONS` 六项字典在断言前输出；base 六项 false，gold 仅 ANY 和真 matcher 为 true，any_only 仅 ANY 为 true，all_nonmodels_equal 全 true。前三种失败使用明确 delegation marker，全相等候选先在 dict/object 断言失败，因此使用 AssertionError。既有 equality 测试仅全相等候选预期失败。 | 输出和断言顺序匹配；gold 的 rc=0 同时要求 matcher 调用断言完成。 |
| 6283 | base 原例要求 `PUBLIC_ROOT_CONSTRUCTION_EQUALITY_FAILED`，gold/validate_construct 要求 `ROOT_EQUAL True`。额外不验证控制对 validate_construct 要求 ValidationError/int_parsing，其余要求成功 marker。原 RootModel 测试会检出错误候选将 model_construct 变成验证构造；共享 BaseModel construct 测试仍要求通过。 | 目标修复与不应验证的回归控制分开，未将 base 的原例失败条件套用 gold。 |
| 5706 | 原题双症状命令准确检查 schema 和 JSON 的错误类别并输出 `BASE_BOTH_PUBLIC_SYMPTOMS_CONFIRMED`；私有 gold 和 sequence_list 明确排除此 base-only 命令。回归命令要求完成 marker；错误候选进一步要求 tuple、range、deque 三个已定位失败标识。 | base-only 控制使用范围正确；gold 只运行适用的回归项。此结果不解除支持/拒绝目标歧义或 P5 限制。 |

## 失败、边界与清理

actor 检查 prelaunch、activation、完整日志、命令 ID 顺序、捕获大小、具体 rc 和内容，不把 `all_match_expect` 当作语义证明。私有行为先执行身份/导入及 pytest collection，再在单个 matrix 内逐命令核判据；rc=2、124、导入/收集导致缺少目标 marker 等情况会停止本题，不会被 helper 整体 rc=0 掩盖。正式 noop/gold 的 reward 对照、安装/test 收口、参考缺席、apply 状态和清理均有检查，错误候选的正式 reward 留作结果审阅。

公开 actor 只接收 public_commands；gold、错误候选和额外 nonvalidation 留在私有运行。私有容器是 root 诊断，不证明 actor 权限；最终 `executed_pending_review` 也不表示训练准入。实际 CC 收到完整题面/public_hints 的证据仍需另验，脚本已显式保留该限制。

TERM/INT 触发父脚本转发子进程组，给予下游 finally 清理时间；正常完成逐项核对 actor/private/grader 清理。强杀分支标记 cleanup_unconfirmed 并停止，不能推断容器已清净。重复信号或主机中断后的残留仍由 root 核验；这不是当前正常路径的新闸门。

后续仅需读回实际输出，若发生与预测不同的 target/test 结果，应按新证据归因，不应修改判据来强行得到完成状态。
