# 共用发布维护暂停点

记录：2026-10-03 03:07 SGT。总协调转达用户暂停要求后，已停止新增实现、合并、封包、部署请求和常规消息转发。等待用户明确恢复。本线程没有远端作业、容器或待清理资源；三个本地子 agent 均已安全停止，无在途命令或维护进程。

## 本线程职责

- 维护有明确输入的共用材料消费者、必要维护检查和不可变发布；当前暂停。
- 仓库题主持续负责各题调查、CPU验证、非作者结果复核及模型结果；本线程不做每题重复终审或代转常规进度。
- “梳理分类二处理背景”统一人员、CPU/GPU槽及暂停恢复；不另建SWE协调树，不由本线程调度15仓。

## 已发布边界

[发布记录](publication_20261003.md)列出九个已封版本。最后版本在暂停通知之前已经完成：

- 第八版 `cat2-cpu-r2e088-swe13-git-20261003-v1`：923成员，manifest `95ff56085fc2ccf6857829f960c23195a3dd332cfecabe8fe6b3f0c3817ebd08`；协调已确认cpu-a只读部署。增加Moto5134，题级三臂不由本线程验收。
- 第九版 `cat2-cpu-r2e089092-swe13-git-20261003-v1`：929成员，manifest `694a1cd364a4bc3348069bd9dd362c4432fbd25339b192d149a2f29d9a709230`；本地封包、101维护/3prepare/264消费范围检查通过，暂停前已发给协调和Orange。**本线程尚未收到部署完成事实，不因旧消息继续派发。** 本地目录 `runs/category2_repair_20260929/releases_20261003/r2e_089_092_swe13_git_candidate_v1/`，code-root为`repo/`。

第九版仅新增Orange089–092，三题expected/runner/gold保持；9b54新hidden+SciPy配方固定。全部发布不可热改。本地检查不表示新宿主CPU或模型验收。

## 未发布与子 agent

独占草案均在 `runs/category2_repair_20260929/release_work_20261003/`，不得直接分发运行，也不为暂停赶封包。

| 子 agent／目录 | 已保存和当前边界 | 恢复后下一步 |
| --- | --- | --- |
| `aiohttp_material_narrow_review_1003`／`mypy15184_consumer_v1` | 已停止。最终34本题维护、434兼容维护（含34）、1题prepare通过；`CHECKPOINT.md` SHA `b6a5176838d66c97431da696660d12fc48e8b0bbd3e8340df993aec95e3cf7e1`。最后去重守卫后旧264消费差异/文件摘要/最小diff尚未刷新，不可据此封包。 | 读该候选检查点，按最新已封版独立窄核与合并。 |
| `monai_material_narrow_review_1003`／`dask7656_consumer_v1` | Dask已固定交付，`HANDOFF.md`可读；生产4文件、264仅7656变，512不同维护分批通过。DVC缺陷仅保存`dvc5839_preflight_fix_v1/CHECKPOINT.md`分析，未复制R8、实现或起维护；已停止，无后台作业。 | Dask保留冻结；DVC只恢复所需公共修复，不重复Dask实验。 |
| `pandas_material_narrow_review_1003`／`pandas48106_consumer_v1` | 已停止、无在途维护；`CHECKPOINT.md` SHA `40a8e190b2604e085ac09a975a9ca13a6c71db7ab615b37fb1eba2294be83de1`。root降UID已移除，修正后未重验；82/105通过均属修正前版本。尚缺共同candidate预检入口，不能称运行就绪。 | 以最终检查点为准接预检入口，再验证受影响部分；不把修正前测试套到新字节。 |

## 已知阻断与唯一必要对口

**DVC5839发布版R7起的候选身份预检存在实现错误。** root trusted_setup内`setgroups/setgid/setuid`被正式cap契约拒绝；首noop尚未install/test，保留infra/None与双层清理，后续三臂已停。题主随后用原profile的`docker exec --user 54322:54322`核四wheel实际可读、SHA匹配，探针清理完成。原件 `runs/category2_repair_20260929/repository_work/swe_dvc/formal_evidence/dvc5839-r7-uid-probe-20261003-001/uid_probe.json`，SHA `0cc4ec2959f8a40abfe7eced1effed752c5aac0ade800b3bd724c633194e1c00`。

恢复后优先设计并验证由Docker以候选身份执行固定读取检查的最小入口，不加cap，不把失败给0，不热改R7/R8/R9。Pandas草案不能复制root内降UID方式。对口：总协调决定恢复/安排机器，DVC题主提供已有原件与定点CPU，发布维护者处理共用消费者。尚未授权恢复前均不执行。

其余已收到的题级CPU进度保留在各仓记录，由协调按需读取；本线程停止转发、确认链和逐题重复核查。
