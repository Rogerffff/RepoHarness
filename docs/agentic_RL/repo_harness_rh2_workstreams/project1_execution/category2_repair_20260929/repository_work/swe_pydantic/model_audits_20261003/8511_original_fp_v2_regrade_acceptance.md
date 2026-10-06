# 8511：原完整Qwen候选在177参考下的补评分核收

2026-10-04（Asia/Singapore）。**原完整FP已在cpu-a/R27实际重评：旧173参考全部通过，新增四项全部失败，正式奖励0，属于代码回归；本次固定请求已returned并ACK，活动指针已清。** 没有新增模型采样或候选导出。原173参考的奖励1、原轨迹、FP、baseline和历史失败记录保持。

新作业为`pyd8511-fp-r27-20261003T190211Z-v1`，实际运行19:02:14Z至19:05:14Z；请求`swe-pydantic8511-behavior-v2-fp-regrade-20261004`在19:24:29Z ACK/revision5，题目progress revision25、phase=probe、active=null。这里关闭的是本次修订及补评分交接，不宣告训练资格、留出资格或稳定成功率。

## 原候选为什么从旧版1分变为新版0分

候选通过只遍历本地注解修复公开repr行为和旧继承护栏，但把`FieldInfo`转成stdlib `field`时仅保留默认值，丢失`default_factory`和验证元数据。新增四项都检验base既有行为，应为P2P（修复前后均应通过），并未新增题外功能要求。

| 新增参考 | 实际失败 | 结论 |
| --- | --- | --- |
| 隐藏字段默认工厂 | 无参构造出现`x Field required` | 默认工厂丢失 |
| 继承的隐藏字段默认工厂 | 子类无参构造出现同一缺字段错误 | 继承时也丢失工厂 |
| 隐藏字段`gt`约束 | `x=0`没有抛出`ValidationError` | 验证约束丢失 |
| 隐藏字段别名 | `Aliased(y='2').x`实际为1，预期2 | 别名丢失，退回默认值 |

实际评分为F2P 1/1通过，P2P 172/176通过；缺失、评分参考skip和未计入终态均0。完整测试文件188项为173通过、4失败、11跳过；11个跳过项均在177评分参考之外。官方parser识别184项不能当作参考分母或完整文件总数。

安装RC0、测试RC1、外层执行RC0，日志完整。正式report为`unresolved/tests_failed/reward=0`，execution failure与infra字段为空。原Qwen当前不满足完整修复；旧173通过的事实仍有效，新材料准确补上该覆盖缺口。原Coder在旧继承护栏下的0分维持，不追加Coder求解。

## 完整FP与评分环境的身份

使用原作业`gpu1003-pyd8511-qwen36-a1`的完整FP、baseline manifest和tar原字节，不用源码重构工件替代。FP canonical为`sha256:4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`，baseline canonical为`sha256:40135f281c216e76a04de6772eaaadcdfd0b46d949e98c5164f29cba2f454e45`；原`excluded_pathset_changed=true`和baseline environment digest=null保持。实际运输stdin与原`content_b64`解码字节完全相同。

正式manager在应用FP前重建完整452项baseline，实际HEAD、路径、类型、mode、内容摘要及25项排除路径集与原manifest一致，重新计算canonical digest相同。R27仅修私有v2的测试文件选择，实际三个评分脚本均使用`tests/test_dataclasses.py`；新grading identity独立绑定，不重写原baseline。

实际镜像为既有`df6c3aff…`，Python3.8.19/core2.14.5、UID54322，导入`/testbed`中的原候选；实际测试SHA为`3caba437…`，root所有且对候选不可写。CPU限制2核、内存4GiB、PID512，runner保护摘要前后不变。资源证据含限制与峰值记录，`resource_facts=null`；没有连续采样或末尾memory/pids事件，不能补写未观察到的资源事实。本次由cpu-a执行评分，不证明GPU机器、模型服务或权重准备状态。

## 控制矩阵与清理证据

此前同R27正式四候选矩阵及非作者验收已经通过，各行177参考齐全：

| 控制 | 奖励 | 区分依据 |
| --- | --- | --- |
| noop | 0 | 原repr F2P失败，新增四P2P通过 |
| gold | 0 | 三项旧继承护栏加新继承factory失败，不能作为正对照 |
| narrow | 1 | 全177参考通过，保留合法字段行为 |
| 原Qwen源码 | 0 | 旧173通过、新四项失败 |

本次完整FP实际结果与源码负对照一致，但保留独立作业、原完整运输和原baseline验证，不将此前源码对照冒作完整FP评分。原四候选CPU验收快照保留当时“完整FP尚未重评”的范围，不回写历史。

本次109件原件共435,098字节，成员集、大小及SHA全部吻合。28次Docker调用均结束RC0；一个评分容器实际创建并删除，manager close与slot/systemd终态0，末尾独占`rh2.run_id`标签的容器和网络查询成功且空。独立事后25项检查全通过，题主另核143个绑定和221项事实（含177个参考的原日志终态）。

最终runner预检报告的`as_of=19:02:51Z`晚于`dispatch=19:02:11Z`及slot开始。后续[时间线读回](../coordination_20261003/8511_original_full_FP_v2_preflight_chronology_owner_readback_v1_20261004.json)独立核实非作者`send_message`调用19:01:49.303Z及返回19:01:49.528Z均在派发前；发布方明确记录收到固定c629 runner通过通知后派发。会话消息参数加密，题主未独立读回明文或发布方接收UTC。因此准确范围是“前置核查通知后派发、书面报告事后落盘、实际25项事后验收”，不能称书面报告已在派发前封存；没有追加实验。本次技术运输、真实终态和题主语义验收范围已成立。

## 证据入口

- [题主完整原件与语义读回](../coordination_20261003/8511_original_full_FP_v2_regrade_technical_owner_readback_v1_20261004.json)：143绑定；原始报告、日志、baseline census、FP stdin、独立报告逐一SHA核实。
- [实际ACK记录](../coordination_20261003/8511_original_full_FP_v2_request_ACK_actual_v1_20261004.json)：固定请求输入与技术receipt保持，CLI实际返回revision5。
- [此前177四候选实际矩阵](../cpu_acceptance_20261003/8511_fieldinfo_v2_targetfix/actual_matrix_semantics_20261004.md)及[非作者验收](../reviews/non_author_8511_v2_targetfix_cpu_review_20261004.md)。
- [原Qwen首次核收](8511_qwen_first_arm_and_pair_acceptance.md)：旧173/raw1和原模型来源、轨迹分析；本次复用既有轨迹，不改变求解环境或重跑模型。

技术回执与原件位于仓库`runs/category2_repair_20260929/pyd8511_original_FP_regrade_20261004/`：`technical_receipt_v1.json` SHA `69be8cee…`；`non_author_actual_readback_v1.json` SHA `a2f9ba08…`。完整路径、大小和SHA均在题主读回证书中固定。
