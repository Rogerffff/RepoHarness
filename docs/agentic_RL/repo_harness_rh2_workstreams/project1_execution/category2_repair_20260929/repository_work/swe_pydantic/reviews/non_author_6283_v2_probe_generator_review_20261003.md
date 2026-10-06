# 6283 v2探针生成器：非作者静态窄核

日期：2026-10-03。结论：**生成器静态审查通过，无当前范围内决定性阻断**。接续表述属于复用已完成公开求解首臂、补真实安装/新版评分缺项的范围；它保留旧FP/baseline/原分和材料版本边界，不扩大Qwen采样，也不授予训练资格。本次未执行或导入生成器，没有创建snapshot/request或派发GPU。

我已读私有v1/v2材料、原Qwen轨迹与候选及旧CPU/GPU上下文，不是fresh公开读者。这里只用本地标准库读/hash/JSON/AST及源码差异；复用此前材料/runner/input审查与新CPU独立核收，不机械重核新498、旧GPU391或旧actor32原件，不运行SSH、Docker、安装、任务tests或模型。只写本报告MD/JSON。

## 源码与当前核收状态

生成器18143字节，SHA `b327ead21063678fe64061b1edfe4d50149ec8e258f41835ff779aea0d909b13`。完整读源码并对照旧 `generate_probe_request.py`（10134字节，SHA `6cdcff9c7d2100bd0330a18f69eb90a61c4e2539bb37eea6467e05315856f382`）。它限定6283、R19 v2四行，增加密封/发布/实际结果/旧actor/独立报告/题主acceptance及旧GPU接续绑定，无CPU、模型或外发执行逻辑。

任务下发时最终CPU报告和题主acceptance尚待；审查期间真实文件已到位。本次已全文读 `non_author_6283_v2_cpu_review_20261003.md`，读其关键JSON及实际 `6283_v2_cpu_owner_acceptance_v1.json`，并绑定字节/SHA。独立报告的job/source/manifest、cpu_review_passed、ordinary_gpu_probe_ready_within_review_scope、actor_reuse_accepted、reused_actor_job均与生成器要求匹配；题主accepted、job和review_json SHA也匹配。没有伪造缺失核收，亦没有因核收到位而越过“生成器不执行”的本次范围。

该报告已独立核498成员与真实四行41参考，实际reward0/1/0/0；题主另有498回读。这里只核索引/关键status及资格字段的连接，不把作者checks再当一份独立评分。新CPU通过与source actor有限复用是该实际报告的结论，不能由本静态审查代替；旧GPU原FP未补评分、actual58d actor未验、训练资格false等边界继续保留。

## R19材料及四行身份

R19 manifest固定 `2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e`；新formal input固定 `4d50c69969e883e48f919ac1221594d88665e409a720f67b9a16952c393b4640`，runner固定 `40b0460b70c2890a1eb3fbbf2474e10bee906125e3068868079370044d875805`。唯一job为 `pyd6283-formal-20261003033613-v2-b5f3a`，实际returncode0、error null及source/input/wrapper均吻合。

顺序严格noop/gold/validate_construct/qwen36_a1_pop_private，reward严格0/1/0/0；每行passed/checks为真。cleanup要求final0、manager containers_open/cleanup_failures空和末尾残留查询成功且空。实际budget300/120/1800保持，不能套用8316的R20 reset900。

v2 proposal密封manifest SHA `cf2a55de20e6ad8122308a096ce6892c70a6d35f8bb3d360e5d5949db8e6a23a`，15成员逐件大小/SHA再次匹配。密封时的pending/expected等是历史状态，不能回写成新实测。本次独立核四bundle、producer manifest及registry六件R19入口的发布manifest大小/SHA、唯一6283记录、public/grading canonical digest与env/spec join。

有效补丁SHA `30037d927f57145f7c0a80281e60861000183d10ae20e4bf10c03bcd8f5c7cde`、revision `pyd6283-behavior-v2`、E10资产/安装内容相连，参考为原1F/38P加1F/1P，总2F+39P=41。registry是运行注册格式，proposal是题主提案格式，核关键消费字段而不误称两份整体字典相同。此前已核旧40参考及新增唯一PrivateAttr普通行为节点的依据复用，不扩题或重审题义。

## 旧actor有限复用

生成器对旧input的七个unchanged keys逐字段比较，并固定旧job `pyd6283-actor-v1-20261002T173908Z-652bc`；检查公开交付、私有材料未活动、三命令匹配预期、清理及两份原result/attempt SHA。

**实际旧actor是基础镜像 `sha256:24e9c51fedb7dc930796362c90f72e8e7a9c47d9362fa72414c6c6ff8a1a2882`；新正式候选/grader是派生 `sha256:58d0c004cec144834a01dfc160c0f4caf427a9b31fd5ad95a60d03f6f3623226`。** 源码、snapshot与request都分别保存两者，没有把derived_id未变说成旧actor在58d上运行。它可按最终报告复用原source/base公开CC交付、导入、已有测试和可写开发路径；不是新R19首请求、58d actor安装、真实模型、fresh reader、full roles或typed租约验收。

独立报告实际解码首请求和私有隔离原件；本生成器只消费该已核复用结论。公开输入未变是复用理由，不是GPU真实首请求免验条件。GPU须再核实际公开首请求、授权image_override、服务/checkpoint、UID54321镜像/core/import/wheel可读性/E10开发及清理。

## 原Qwen首臂与新请求范围

旧safe_partial回执SHA `1200622f08a476f2bc2dc5da139a29fae355c1a29be1c859d2dbea013c07a4a3` 固定安全关闭，唯一执行臂为 `gpu1003-pydantic6283-qwen36-a1`；Coder和重复仍未执行。原FP canonical digest `sha256:1ac717446957b1463305cabaceb2e71f8a9b0685c8377f0659869820b8b829d5`、baseline canonical digest `sha256:5db8531800cd73bd1abe759a445e75cac7cefa12e88a3bd05bee1629e9e17998` 独立复算与回执相同，原轨迹也按原路径/SHA绑定。

原FP与baseline的task/public/base HEAD一致且与v2公开身份相同，原runtime image为 `sha256:a1009223bf2ad76bef2c9d16571a93f84bd9aef0c4722978c0f9b4158bb19e14`；baseline envdigest仍null。不得把新CPU或GPU镜像ID、v2 env/material身份静默写回这些旧artifact。历史install RC1与raw reward1保留；“original_model_a1_already_complete”只指求解采样及原候选已完成，不表示原安装、语义正确性、模型真实checkpoint或题目已验收。

新ID为 `swe-pydantic6283-behavior-v2-20261003`。continuation_plan明确：Qwen不新采样，只用**原完整FP**另记v2实际安装/41参考评分和PrivateAttr窄观察；Coder只开未执行的一次；重复不追加，仍按GPU原覆盖门槛另安排。它有旧request关联、safe_partial、原FP/baseline文件与canonical digest、原trajectory，符合有效首轮复用和补缺项范围。

新CPU的qwen源码等价负对照0不是对原GPU完整FP的补评分。原baseline运输/投影与不同实际GPU镜像的兼容必须由执行者窄核，缺共享consumer实现时关联发布支持；不能通过改FP metadata或换成CPU FP来冒称原FP重评分。换材料v2诊断单列，不覆盖旧40参考或原分。

通用model_budget仍列两个模型和每模型1次；**执行者必须明确消费continuation_plan，固定Qwen新增采样0次、Coder1次**。本次没有验证共享执行器机器支持该字段，不能按通用两模型循环重复采Qwen。该事项属于派发前执行者readback/兼容核收，不是当前静态生成器已具备的能力。GPU实际镜像ID仍为null，不能以CPU58d或Q12可读层证据代验本次真实GPU安装。

## 输出与未完成范围

全部材料、实际CPU/actor复用、最终报告、题主acceptance及旧GPU身份检查在两个exclusive open之前；首次输出open为第216行。源码只写新v2 acceptance目录的 `cpu_acceptance_snapshot_20261003_v2.json` 和 `probe_request_v2.json`，不属于密封15成员，也不改旧R7 snapshot/request、旧分或共享代码。存在输出时拒绝覆盖。完整request和snapshot文本先在内存生成；两文件连续exclusive保存，若后半I/O失败出现部分输出，不能认作合格请求。

64项本地材料断言及51件文件绑定通过。本次未执行生成器，当前两输出不存在。最终报告和题主核收现已到位；剩余是实际新输出全文/字节核收、GPU执行者对接续计划及镜像/consumer兼容的明确读回、原FP真正v2安装/评分、未执行Coder一次与相应完整轨迹/候选/用量/清理审阅。静态通过不证明GPU执行完成或训练资格。
