# Moto5134受信材料增量与第八版

2026-10-03。只新增Moto5134的mixed-list兼容P2P。作者独立候选先完成，主维护者阅读完整生产差异、固定双文件材料与维护测试后合入R7。第八版 `cat2-cpu-r2e088-swe13-git-20261003-v1` 已封包，923成员，manifest SHA `95ff56085fc2ccf6857829f960c23195a3dd332cfecabe8fe6b3f0c3817ebd08`。它仍是新正式CPU材料候选，不提前给出新三臂reward。

## 实际修订

原2F／12P、公开题包、命令和安装不变，完整有效补丁保留 `test_event_pattern.py` 与 `test_events_integration.py` 的原补丁，追加已有公开兼容行为mixed-list的唯一P2P，最终2F／13P。15是评分参考数，18是下一轮项目collection预期，不是本地维护实际运行数。

作者输入来自 `runs/ordinary_gpu_probe_20261002/diagnostic_inputs/moto5134_d6_revision_v1_review/`。REVIEW SHA `b7d9cc2a6c90b3e9393d3fe24545a211e03cd05ca878e73643a7033e6593d7a5`，有效补丁 SHA `caaf39d27912117e28a9fc5c855712fd8362b553fccdde0d44a0831f36a9f008`。独立候选报告与282维护（含22本题）保留在 `release_work_20261003/moto5134_consumer_v1/`。

生产仅改 `envpack/bundles_v2.py` 与 `envpack/swe_material_revisions.py`。单题Literal锁定来源、仓库、base、原公私digest、原／有效patch、两个文件与各自base SHA、顺序及唯一新增节点。固定registry与实际原／有效patch、base资产逐字核对，不扩大旧单文件修订。复用既有context、受信恢复、候选测试修改剥离和原参考分区；不改parser、scorer、manager、预算或安全配置。

## 合并验证

三新增类型的AST与作者候选相同，R7既有类型AST保留，只有承载新增类型的两个union／validator扩展；PreparedTaskFace、spec_vendor、评分context、manager、Git四文件及builder保持R7字节。所有R2E文件及旧十二题实际消费身份保持。

实际组合维护484不同用例分批通过：471通过／13个fixture重复copy错误；修复该fixture后，其模块34通过，覆盖13个错误。保留原错误日志，不称一次整套全绿。作者282维护与此组合检查有重叠，不能相加。

default prepare单题成功。组合代码实际消费264题，仅Moto5134改变，另263项不变。SWE13 producer manifest SHA `3ca6820dbd25bc890144234b5bf285d4c233eea0bf6f9a827500df90358eef06`；923成员及trusted48／216核验通过。发布脚本首次把replay prepare的`task_ids`误按`task_count`读取，在创建输出前失败，修正检查字段后发布；未因此改生产。

证据：`releases_20261003/r2e_088_swe13_git_candidate_v1/checks/`；合并与原失败日志：`release_work_20261003/moto5134_combined_swe13_v1/`。本轮未SSH、Docker或执行Moto测试。

## 下一步与责任

题主仍为“负责处理第一类的模型探针”，不是Moto六题负责人。实际CPU需用新材料执行noop、原gold、原a3工件三方，预期0／1／0，并核15参考、安装、完整test退出/footer、两层清理及新材料身份。默认来源镜像与GPU历史actor/grader镜像必须按固定SDK/overlay明确关联，不能混称同一镜像。

旧FrozenPatch不改绑，原账本保留。新评分记录本次材料／代码身份和原工件来源，不能覆盖历史。无需统一切换其他仓库；R7在途继续原版。CPU及非作者验收后再由题主决定相应GPU接续。
