# 执行记录

## 2026-09-29：材料核对与首批启动

- 冻结起点41题（SWE28／R2E13）；三个GPT-6 Astra／xhigh子任务分别整理R2E续接、D6入口方案、SWE材料。逐题清单已完成；没有新题转入第1类。
- 主线程核对D6明确授权边界、mypy实际选择器及保护文件范围。提交[首片决定](d6/decision_request.md)，未实施SWE正式机制。
- 两道mypy在09-25用原镜像导致的离线安装失败，已有09-19 `install_wave1`修复。新包固定原digest、两套配方和11个wheel的历史SHA，合计2,413,682字节。只准备镜像，不把镜像准备当安装或评分通过。
- SWE机只读检查无现存容器；新目录部署镜像准备。v1因把本地image ID作为`FROM`参数而被BuildKit解释为registry名称，构建失败；实际无遗留容器，失败日志保留。v2改用已核的固定`repo@digest`，增加派生层继承检查，经[独立窄复核](reviews/image_preparation_review.md)后在新目录／标签继续。旧脚本与结果未覆盖。
- v2两题镜像均已准备完成，11个wheel与固定来源清单一致，base身份及派生层继承已核，实际无残留容器。新image分别为10424 `64472be3…`、17071 `0111b5f8…`；新ID独立登记，不冒作09-19旧ID。完整检查在`runs/category2_repair_20260929/image_preparation_result.json`，远端证据已回传；候选安装和评分尚未执行。
- aiohttp4075七份正式完整日志与136键映射已独立重算，评分修订验收通过；错误公开复现仍必须修，因此不转类。三个expected FAILED键依据离线纯Python范围分别解释，没有擅自改为全PASS或删键，见[专项记录](r2e/aiohttp4075_acceptance.md)。
- orange3 22e98的独立公开包1573项摘要经主线程核对；fresh读者只读公开包，给出一般输入的需求解释，未见实现答案，见[公开阅读](reviews/orange22_public_reading.md)。读者看到包中`run_tests.sh`来源文字，但未打开脚本或私有内容，已披露边界。
- orange3 R-f已在`runs/category2_repair_20260929/frozen_r2e_statement_v1/`独立快照构造材料候选v12、pins v13；共享v11保持原样。首次维护检查因快照漏带SWE pins／构建配方文件而有10项失败；补齐真实原件并记录SHA，未改测试，四文件复跑 **73 passed**。这是本次快照准备遗漏，不是题目或生产评分缺陷。
- 隔离R2E版本还须独立核材料变化、当前consumer交付和机器条件；维护测试通过不等于实际CC已经接收新题面。新材料、运行和失败记录均在`runs/category2_repair_20260929/`，未提交或推送。
- 后续[隔离修订独立复核](reviews/orange22_isolated_revision_review.md)已通过：48行中仅本题题面及关联摘要／修订号变化，其余47题逐行字节一致，评分正文、expected、隐藏树、入口与validation不变。主线程已补存复跑的command／cwd／returncode及日志SHA，见`r2e/orange22_rf_v1/tests_after_material_completion_result.json`。当前仍未完成实际CC消息交付与共用入口切换，因此不转第1类。

## 2026-09-29：D6正式机制授权与实施

用户明确批准实现SWE正式评分材料修订机制，先用mypy10424、17071验证，通过后逐步用于其他需修订题。当前分工：入库agent负责类型、登记与可信重放；消费agent负责controller/prepared与共同脚本；root负责材料资格、诊断和真实CPU验收。首片不改变原题面、原测试补丁、奖励算法或网络边界。最终另由非作者复核，六次正式评分尚未运行。
