# Pydantic 8567：两 job 合并探针请求生成器静态窄核

2026-10-03。**静态差异核查通过，未见本轮合并逻辑新增阻断。** 入口保留旧失败轮身份与两行原分，要求新七行完整成功、实际公开 actor、所有归档原件 SHA／大小和联合非作者报告；输出将两个 job 分开保存，明确新正式 job 只含七行。此次没有运行 helper 或生成请求／snapshot，未核新的实际 CPU／actor 原件，**不标记 8567 全题 CPU 或普通 GPU 就绪，不授予训练资格**。

对象：`runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/generate_8567_combined_probe_request_v1.py`，15422 字节、SHA `14207ee4e1aacb11357d523055909cc02d1653833ca6ba10202260c0e8c02a27`。基础入口 `generate_remaining_probe_request.py` SHA `32aae90391498b29d1064674e37e419100f5d310e81e9acc76197f17c959573d`。只读并作标准库 diff、AST／源码核对，复用原入口、[失败轮核查](non_author_8567_partial_cpu_review_20261003.md)、[七行输入核查](non_author_8567_resume_input_review_20261003.md)和既有 R14 材料／runner 意见，不扩大为公共生成器标准。审查者非本 helper／材料／结果作者，已见私有上下文，不是 fresh 公开读者。只写本报告和[同名 JSON](non_author_8567_combined_probe_generator_static_review_20261003.json)，没有 SSH、Docker、模型、安装、项目代码或 helper 执行。

## 合并前的真实身份与资格要求

新 `attempt(..., partial=True)` 分支只接受旧 job `pyd8567-formal-20261003001737-r14-b631d`：`returncode=1`、`status=stopped_needs_analysis`、非空 error、旧 namespace `formal_v2`。原 returncode／error 没有改成成功；旧原件清单仍逐件检查实际 SHA／大小。旧部分报告必须确认两行可复用、c3 reward 为 null、不是模型 0、清理零残留；旧 rows 必须严格为 `noop/gold`。

新正式 attempt 仍必须 `returncode=0/error=None`、成功矩阵状态，namespace 固定为 `formal_8567_resume_v1`，输入 SHA `cce81e77a4122786ed78f8134d79fab11e7c46e4b851c80308c393076b3c3845`；旧输入 SHA 固定为 `bea70edd55d2a316b5d92fde1a3a894e9c79363a168e2cd92c7de2d40b83ac1b`。两个 wrapper 都必须为 `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5`。两个 attempt 及 actor 必须指向相同 release／manifest，且其证据清单中的每个文件都经过实际长度／SHA 检查；不能用正在运行的一行成功代替完整七行归档。

合并结果只取旧 `noop/gold` 加新七行，并为每行附其实际 job。完整九行顺序必须等于原固定候选顺序：`noop/gold/c3_reorder/upstream261/ok_post_attach/bad_nonvalidators_after_pv/c3_serpass/rv_ser_to_end/n_python_only`，预期 `0/0/1/0/1/0/0/0/0`。新 attempt 自身严格等于原列表后七行；所有合并行必须 passed 且 checks 全真，原 reward 与对应预期相等。旧 c3 没有被加入合并行或移记到新 job，它仍由旧失败原件／部分意见保留；新 c3 来自新 job。原 gold 的实际 0 分也不会被改写。

两份原 `status.json` 的 **完整 spec 必须相等**，新 job final status 必须退出 0。这会绑定材料、参考分区、安装、脚本、hygiene 和 spec 预算等实际保存字段；不是仅比较名字。与旧输入核查相同，资源／保护上限没有在该 helper 改动。

实际 actor 必须归档成功，原件 SHA／大小检查仍适用，diagnostic 中 `actual_public_delivery=True/new_test_material_active=False`，实际 image／2 CPU／4 GiB 与登记值相符，收尾残留为空。上述自动条件仍需未来联合非作者阅读完整首 prompt、三命令、数据流、导入／源码、资源和清理原件，不取代 CPU／公开 actor 独立验收。

## 联合报告与输出不混记

未来实际联合 MD／JSON 必须来自真正完成的原件审查；helper 的 JSON 断言要求如下。当前部分意见为 `cpu_review_passed=False`，不能冒用它生成请求：

| 字段 | 必须满足 |
| --- | --- |
| `job/actor_job` | 新七行 job／实际归档 actor job，与参数相等 |
| `reused_formal_job` | 旧失败 job |
| `formal_jobs` | `[旧 job, 新 job]`，原顺序 |
| `combined_candidate_order` | 原九行完整顺序 |
| `old_c3_infra_null_preserved` | 严格 True |
| `cpu_review_passed` | 严格 True，由实际联合验收给出 |
| `ordinary_gpu_probe_ready_within_review_scope` | 严格 True，由实际 CPU＋actor 验收给出 |
| `source_release/manifest_sha256` | 同一固定 R14 身份 |

snapshot 分别保留原始 `formal_attempt`（新七行）与 `reused_partial_formal_attempt`（旧失败轮）整份对象，包含各自 input／wrapper SHA、evidence、状态、error 和 cleanup；另存带 job 的九行合并结果、旧部分意见、新联合意见和 actor。没有把旧失败轮伪称九行完整通过。请求的 `formal_job_scope='new seven rows only'`，另外显式列 `formal_jobs/reused_partial_formal_job/reused_partial_status`；清理对象按 `new_seven_row_job/original_reused_partial_job` 分开。旧 final status 4 与零残留可同时原样保存，不被新成功清理覆盖。

唯二写入路径是本题的新 `cpu_acceptance_snapshot_20261003.json` 与 `probe_request.json`；源码先断言两者均不存在，此次读取时确实都不存在。没有写原 results、旧 status／report、输入、失败工件或材料。该私有入口只生成本地固定请求，不提交、不派发；运行前仍需题主已读完整联合意见。此次静态核查不创建这些实际文件。

## GPU 身份与已有缺口的准确范围

新回执要求明确：每个模型记录当时**实际服务 checkpoint 与任务请求绑定**，模型别名不能代替实际身份；同时保留完整轨迹、公开首消息、baseline／FrozenPatch／diff、原评分、逐参考、完整日志、预算用量、终止和清理。

新增引用为 `coordination_20261003/q12_pydantic_wheel_readability_v3_owner_readback_v1.json`。读取其范围字段可确认，它只涉及 5662／6283 两题 GPU 公开 wheel 权限层，`install_or_grade_or_model_run=false`，原 FP 安装／评分补验仍待，本题 8567 GPU 镜像仍须单独验。helper 的 followup 文案与此相符；`gpu_actual_image_id` 保持 null，不能把 CPU image ID 或可读层核收当 GPU 实测安装。新 8567 的固定 COPY 上下文、八个公开 wheel URL／SHA、UID 54321／54322 可读性及实际 actor／grader 镜像仍由 GPU 执行者验证，不能继承旧 0600 问题。

公开输入仍保持原题面／hints，私有测试和 gold 不交 solver；CPU actor 仍是固定控制桩，GPU 须重新核实际首消息。共享 parser 对非参考带空格 ID 的截断、专门 BASH_ENV 写拒绝未测、baseline 环境锚 null、精确诊断 override 与正式 typed 训练 actor 租约的区别，以及旧候选语义边界继续保留。该 helper 没有修复、核销或扩充这些范围。

父线程已告知共享保护-only回执核收、七行作业派发。本报告不重做该恢复核收，不以其代替实际七行／actor验收；也不据当前单行进展签发资格。**通过范围仅是新的合并／绑定／请求文案静态差异。** 全部七行自然完成并归档、公开 actor 和全部原件核对、题主读联合非作者意见之后，才满足本入口预期；未完成条件原样保留。
