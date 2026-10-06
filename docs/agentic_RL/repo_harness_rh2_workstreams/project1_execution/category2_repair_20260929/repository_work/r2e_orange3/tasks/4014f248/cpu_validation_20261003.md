# Orange4014：当前CPU验收

2026-10-03。**R9/089最终八方已经完整核对，实际CC重编/原生冻结/新grader也已完整核对，[独立CPU终审](../../reviews/orange4014_r9_cpu_review_20261003.md)已通过、无必修项，固定[单题请求](probe_request.json)已登记并实际送达GPU。** 原057全部断言保留，新增小量级分箱断言已实际拒绝舍入错修。

| 对照 | 正式reward | 参考匹配 | 原始失败位置/含义 |
| --- | ---: | ---: | --- |
| noop | 0 | 26/27 | test_1.py:55，实际重复阈值触发low<high断言 |
| gold | 1 | 27/27 | 正确修复通过 |
| C1 | 1 | 27/27 | 另一合理处理位置通过 |
| DG | 0 | 26/27 | 第80行，0与近邻值合到同一区间 |
| C3 | 0 | 26/27 | 第90行，小量级数据75/100分箱不匹配，实际全落区间1 |
| C4 | 0 | 26/27 | 第64行，未覆盖另一分支，重复阈值仍断言失败 |
| pyx_build | 1 | 27/27 | 固定已有源码+二进制工件通过 |
| pyx_only | 0 | 26/27 | 第55行，源码编辑没有改变旧扩展行为 |

8方均完整TEST段/解析，27参考键无missing、reference skip或额外键；expected映射不变。实际before300/after1200/test1800，footer/清理均核，无基础设施评分异常。235份原件逐文件大小/SHA已回收核对；8方的candidate/grader共16容器均有有限HostConfig/cgroup观察，实际2CPU/4GiB/512、swap0、network none。并非全程资源抓取，ledger.resource_facts仍为空。

C4两个删除阶段观察为removing/PID0/exit137/OOMKilled=false，candidate发生于进入grader前、grader发生于完整测试结束后的删除；其cgroup已不可读。不能把删除态137称为测试OOM，也不能由有限样本推断全程无OOM/节流。评分加载字段只证明Orange包来自/testbed；没有单独记录grader扩展__file__/SHA，原生工件消费须结合下述实际CC/roundtrip与pyx_only反例。

实际CC v2沿同镜像330716…和批准配方9cd596…完成六个固定Bash步骤：查看旧扩展、改pyx、实际inplace重编、检查新扩展导入路径、复现公开m4/m5近邻例，原冻结工件交全新grader得到正式1（27/27），原TEST段27键完整、test rc0、准备1200秒、清理完成。旧扩展9ee458…实际重编为f1d05c…，actor新进程导入路径正确；5项源码/二进制冻结及transport372f498…与实际baseline逐字核，往返身份/entries/digest全部一致。91份原件回收并核SHA。构建脚本保留实际BUILD_RC/full output，源码/二进制/渲染/roundtrip另核，不能仅因工具rc0宣布成功。它是固定endpoint CPU诊断，不是模型解题。

私有CC v1在启动前因live legacy_gitdiff_compare=true被R9入口拒绝，0工具/0评分，作业1；12份原件保留。v2只删除这个已禁用诊断选项，六个步骤逐字相等，不改R9源码、消费者、评分或CPU控制；启动前已读回旧作业结束、own label/网络无残留、端口空闲、正确prepared SHA。失败attempt不计正式对照或模型样本。

[八方结果收据](cpu_matrix_result_20261003.json)、[实际CC及全新grader收据](cpu_actor_result_20261003.json)、[完整原件manifest](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_matrix_complete_v1/readback_manifest.json)、[逐断言/资源核对](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_matrix_failure_resource_author_check.json)、[前置拒绝原件](../../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/resume_20261003/r9_4014_actor_failed_v1_author_receipt.json)。

中性[公开开发说明](public_development_brief.md)已完成[独立事实/可见边界窄核](../../reviews/orange4014_9b_public_briefs_review_20261003.md)，本轮未交付该brief，须GPU实际交付/readback。当前用途限诊断，正式八方不等于GPU准入、模型结果、训练或留出资格；[当前CPU验收](cpu_acceptance.json)及[独立接收回执](independent_cpu_review_receipt.json)已封；[探针提交回执](probe_submission_receipt.json)区分已交付请求与尚待执行者准入/模型结果。
