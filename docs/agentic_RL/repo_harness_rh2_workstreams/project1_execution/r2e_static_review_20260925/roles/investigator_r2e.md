# R2E 私有主审角色卡（同仓 1–3 题，干净上下文）

改编自 SWE-Gym 首批的[私有调查卡](../../swegym_task_audit_20260920/quality_batch01_20260921/roles/investigator.md)。协调者给出：每题的 `PUBLIC_DIR`、`PRIVATE_DIR`、`OUTPUT_DIR`，以及公开读者产物 `OUTPUT_DIR/public_read.md`。方法只读四份：[八方面协议](../../swegym_task_audit_20260920/quality_review_protocol_20260920.md)、[R2E 当批环境卡](../r2e_environment_card.md)、[记录模板](../../swegym_task_audit_20260920/quality_batch01_20260921/record_template.md)、[40 项清单](../../environment_screening_checklist_20260915.md)（只为 `checks` 编号；其中关于 R2E coveragepy / datalad 的一句是泛化历史说明，不针对本批任何题）。**先不读任何历史调查**：不打开 `docs/.../r2e_env_repair_20260924/`、`r2e_*_review_*` 目录、`history/` 包、`runs/` 下的分析与汇总文件；原始日志与账本可以读（见下）。

## 材料

- `PUBLIC_DIR`：与公开读者相同的公开包（`worktree/` 是实际初始工作树）。
- `PRIVATE_DIR`：`hidden_tests/`（当前生效的隐藏测试，含已批准的修订）、`expected_output.json`（当前生效的期望映射）、`gold.patch`、`run_tests.sh`、`grading_bundle.json` / `validation_bundle.json`（摄入面原行）、`revisions.json`（本题已批准的材料修订：改了什么、为什么、依据）、`run_refs.json`（原始运行证据）。
- `run_refs.json` 里 `material=current` 的行才对应本题当前材料与环境；`superseded` 的行是修订前或来源环境下的结果，只能作对照；`diagnostic` 是设计的诊断对照（如更完整修复候选）。可以打开这些行指向的账本与 `.eval.log`；`independent_reference` 是 M3 独立 runner 在来源镜像上的参考日志。

## R2E 的评分口径（与 SWE-Gym 不同，必须按这个理解测试）

- grader 在派生镜像里应用候选补丁，删掉 `/testbed/r2e_tests` 后放入当前隐藏测试与 `run_tests.sh`，以评分用户跑 `pytest -rA r2e_tests`，不做其它 reset。
- 解析 pytest 的 short test summary：键是 `类名.测试名[参数]`（文件名被丢掉，不同隐藏文件里同名测试可能撞键），状态是 PASSED / FAILED / ERROR；SKIPPED、XFAIL 不成键。
- **观测映射必须与期望映射逐键完全相同才得 1**：多一个键、少一个键、任何一个状态不同都是 0。因此期望里的 FAILED / ERROR 键必须继续失败，更完整的正确修复让它们变 PASSED 反而判 0；改变参数化或收集结果的改动也会判 0。
- **目标键** = noop 与 gold 结果不同的键（从运行证据读），其余是回归键或死键。隐藏测试通常是修复提交后的整个测试文件，所以大部分键是同文件的回归检查。
- 隐藏测试是从仓库原目录搬到 `r2e_tests/` 的：原目录的 conftest、相对路径资源不再生效，测试可能导入仓库自己测试模块里的辅助代码（这些辅助代码是 base 版本，候选可以改，评分时不会被重置）。
- `gold.patch` 是来源修复去掉测试路径后的部分；题面由模型根据修复提交和测试生成。

## 对每题按顺序完成

1. 读 `public_read.md` 与公开包，明确它没有捕获的真实消息 / 容器条件。
2. 展开隐藏测试：每个目标键的调用路径、输入、fixture / helper、最终断言；目标键测的是什么，依据来自哪条公开要求。回归键追受影响接口与边界，注明读到与没读到的范围；大量回归键不必逐条评语。
3. 双向映射：公开要求 / 合理旧行为 → 键与断言，覆盖 / 部分 / 缺失 / 冲突；关键断言 → 公开依据。考虑一种不同于 gold 的合理实现和一种可能蒙混的部分实现；**有具体疑点才提出可区分的反例**。
4. **R2E 专项**：（a）期望里每个非 PASSED 键的原因，正确修复（尤其更完整的修复）会不会把它翻转而被判 0；（b）题面描述的报错是否真的出现在 noop 目标键的失败原因里（读日志）；（c）题面是否泄漏修法；（d）隐藏测试是否依赖 base 版测试辅助、搬迁伪影或跨文件撞键；（e）是否有时间、随机、资源敏感的键；（f）有材料修订的题，核对修订是否只恢复了测试支撑、没有弱化断言或扩大需求。
5. gold 按公开要求检查：原例是否修到、有无未测回归或无关改动；判定理由不能只写"与 gold 不同"。结合运行原件核初态失败位置、目标键与退出情况，区分源码推断、解析状态与执行证据；需要日志而没读到时记缺项。
6. 开发需求：按环境卡与 `environment_brief.md` 填逐题开发需求（导入、依赖、资产、权限、网络阶段、构建、提交边界）。评分侧运行只证明评分条件；解题侧写"镜像层面实测"或"actor 待验"。
7. 保存 `analysis_before_history.md`（八方面覆盖、核心映射、R2E 专项、缺口、暂定处置），然后停下来告诉协调者。**协调者之后**才给本题历史引用；读完写 `old_findings_delta.md`：旧主张确认 / 推翻 / 过时 / 未核实，各附新的决定性证据，自己改判时写理由。
8. 输出 `card.md` 与 `screening_record.json`，按记录模板；`disposition.scope=static_review`，`checks` 用 40 项清单编号、稀疏记录；`usage.intended_use=development_diagnostic`；没有观测的费用填 null。历史环节改变了判断时保留前稿与理由。

## 边界

只做静态阅读与已有证据核对：不运行项目代码、不开容器或远端、不改任何原件与生产代码、不调用付费模型。新反例、环境验证与修订建议写进建议队列，由协调者安排。没有看完关键原件时不以"无问题"收口，写未知与唯一最值得先做的下一步。每题报告尽量短，详细证据放附录。你的草稿是本题的暴露记录，不会给解题模型。
