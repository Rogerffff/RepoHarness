# getmoto__moto-7584：独立二阶段复核

**建议：原版不列为用于解释 solver 修复能力的“受限静态候选”；仅保留为已知规范冲突的 CPU 诊断对象。** 状态为 `needs_review / static_review`，用途 `development_diagnostic`。这里不是因未做新 CPU、未覆盖所有边界或 actor 未验而拒绝候选资格，而是公开原例与 gold 控制流直接冲突，同时静态预计精确消息断言会拒绝一种公开一致的实现。限定用途不能使这个 reward 自动成为公开目标完成度的可靠指标。

本稿在三题 reviewer_initial 全部由协调者封存、统一开放后写成。独立初稿 SHA256 为 `36935247d795d340d7f32d8e732d36d164ef8a83ba3d22bb51bde99ef0b2ad3b`，未回写。对照了本题 public_read、analysis_before_history、old_findings_delta、card、screening_record，以及 history/refs 精确指向的 L1_moto_3 本题记录；未用多数意见裁决规范。主审的两项核心疑点与独立初稿一致，本稿将用途限制说得更明确。

本文 ROOT 为 `${REPO_ROOT}`；PUB/PRI 为 ROOT 下 `runs/swegym_quality_batch02_20260921_v2/{public,private}/getmoto__moto-7584`；E 为 `runs/env_recipe_repair_20260919/install_wave1/tasks/getmoto__moto-7584`；S1 为 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-7584/gold/offline/a1`。下列源码均从 PUB/base 起算，完整第一阶段八方面证据保留在 reviewer_initial.md。

## 决定性主张及分歧

| 主张 | 独立复核及证据层级 |
| --- | --- |
| 公开原例没有规定删除 endpoint 后既有订阅怎么办 | **不成立。** PUB/user_prompt.txt:23–39 明确先成功 Subscribe、删除 endpoint、再以同参 Subscribe，末次应报错。它不是审查者新增的边界。旧记录 public_view 及“重订应返回旧订阅”的回归建议均与此冲突。 |
| gold 正确修复题面，查重前校验反而是不完整解 | **不成立，静态控制流明确。** base moto/sns/models.py:514–517 先返回 _find_subscription 结果；:538–548 按 topic/endpoint/protocol 找旧订阅；:714–718 删除时只移除 endpoint。PRI/gold.patch:5–18 把存在性检查插在提前返回之后，因此沿题面原序列仍会返回旧订阅。当前历史 gold reward1 只证明冻结验收通过；未执行题面原序列，不能写成实际复现已失败。 |
| 新 F2P 覆盖完整题面流程 | **不成立。** PRI/test.patch:15–38 创建 endpoint 和 topic 后直接删除 endpoint，缺少第一次成功 Subscribe；测试验的是“无旧订阅的缺失 endpoint”。名字虽叫 publish，正文只调用 Subscribe。测试名误导本身不构成坏题，遗漏题面前置状态才是这里的决定性差异。 |
| 公开消息与 F2P 精确消息兼容 | **不成立。** prompt:4 为 `...endpoint {endpoint_arn}`，patch:41–44 要 `...endpoint arn{endpoint_arn}`；models.py:347 生成的 ARN 已含 `arn:`，因此后一项实际有 `arnarn:`。按公开消息写异常、且在查重前检查 endpoint 的实现，静态预计完成公开流程，却在该精确字符串断言被拒。该替代尚未写入或执行。 |
| 旧报告称 AWS 实际报文有额外 arn、既有订阅应暂时保留，可因此覆盖公开原例 | **不能采纳为规范裁决。** 这来自 gold 注释及 aws_verified 标记；本轮原日志走本地 mock，未验证云服务事实。保留其来源，不把注释当作独立 AWS 证据，也不以评论较新或多个报告同意改变公开要求。若未来决定采用另一规范，需明确修订题面/验收版本；本轮不改任何材料。 |
| 19 个 P2P 间接覆盖正常 application Subscribe | **不成立。** 第一阶段逐体读完整个旧 test_application_boto3.py 和新 F2P；P2P 包含 endpoint 生命周期、直接 publish、SMS 属性，未执行正常 application Subscribe。额外已读公开 test_subscriptions_boto3.py 的 SMS、重复 SQS、HTTP 正例，不在此次参考集。第二阶段再核 models.py:128–145 的 CloudFormation Topic 创建也调用同一 backend.subscribe；未声称 CFN 测试运行。 |

合理解仍有实现自由度：在 backend 的幂等查重之前校验 application endpoint，或在 response 层执行相同前置条件并保留其它协议行为，都不必照抄 gold。公开题面还要求存在 endpoint 时正常订阅；冻结集合缺少该正例。初稿中“拒绝所有 application 订阅可能过该集合”仅是静态覆盖风险，没有实施候选，不作为第二个优先实验，也不能掩盖现有 gold 已体现的自然部分实现。

## 历史事实与当前环境证据

亲读旧 L1_moto_3/records/getmoto__moto-7584.json 后，沿其精确 S1 目录核 eval.sh 的安装/恢复/测试入口、test_output.txt:390–422,432–482，以及 patch.diff 与当前 gold 的字节对应。旧 gold patch SHA256 为 `4259577987a8f90d16046a73060c2d3f5b3c8a7d19ace77c2a7b1c6104e7bbea`，与 PRI/gold.patch 相同。这是局部原件对应，不是重新全包检查。

S1 确实发生 setuptools>=40.6.0 离线构建依赖获取失败、make init rc2，脚本仍继续，随后 20 passed/test rc0。旧报告分别引用这些事实可以成立，但“20 通过”不能单独证明当时安装健康。第一阶段已亲读 E 的 image/build、通用构建入口及两角色账本/原日志：离线构建工具 wheel 被提供，make init 实际完成；gold 20 passed/reward1，noop 19 passed 加目标 F2P failed/reward0，均 install rc0。这是 09-19 已执行的派生 grader 诊断，本轮没有重跑，也没有把 COPY wheel 当成安装成功证据。

该派生 grader 为 UID54322、deny_all、2 CPU/4GiB，解释器前缀可写，源导入指向 /testbed/moto/__init__.py。candidate.apply_user=54321 只是应用补丁的用户。正式 rollout_spec_from_view 仍取 public image/digest；actor UID54321 的实际消息、工具 shell、PATH/激活、依赖、源码编辑生效及安装权限尚未验。旧 root pip 警告、当前 grader 成功、预激活文字都不能补齐这一层。

sns_aws_verified 的开关事实需准确保留：旧记录本身也承认默认 false。tests/test_sns/__init__.py:22–47 只有显式在线开关才取真实 SSM/Firebase 资产；默认 mock 使用假 key，现有日志有 mock_api_key。本题最小开发没有必需真实 AWS/秘密资产的证据。旧 finally/topic_arn 风险是可能遮蔽前置创建异常的静态测试卫生问题，当前完整日志没有触发；不据此新增准入规则或排除路径。

## 恢复、关系和暴露

当前 ROOT/rh2 的 prepared_task_face.py:312–335 按 test.patch 精确恢复 `tests/test_sns/test_application_boto3.py`，`test_globs=()`；gold 的业务 models.py 可投影交付，额外排除保持空。tests/test_sns/__init__.py 不因位于 tests 下而自动恢复，装饰器篡改可影响评分是已记录的静态控制面风险；未运行利用，且其不是遵守公开指令的合理解。manager 对全局失败另分类，普通完成的非引用 pytest rc1 不自动等于 reward0。

主审将跨题关系保留 unknown 是其阅读范围内合理的限制；本 reviewer 另有第一阶段已核的指定三题原件证据：7584 的公开 base 含 5134 的 EventPattern 缺失标记方案和 5752 的 SSM 标签列表匹配方案（events/models.py:40,888,917；ssm/models.py:1872 起）。这属于后续版本包含先前答案的暴露关系，不代表三题是同一问题或自动污染。旧 6355 反向 apply 声明无本轮已读的精确实验原件，不据它强制分组，也未越界读取该题。

本 reviewer 已私有阅读三题 gold、隐藏测试、真实历史原件；第二阶段才读获准主审和旧记录。旧 raw hints 的“仅复现”主张没有进一步精确原件核实；当前 public_hints 是操作说明，实际 actor 的 Git/缓存/挂载/模型消息可见面仍未知。公开导出不含 .git 不等于运行无泄漏，本稿不能作为独立 solver 轨迹或模型能力证据。

## 唯一下一步及最终建议

**只优先一组冻结 grader 条件下的离线 CPU 语义对照**：base、已有 gold，以及一份“先验证 endpoint、使用公开消息”的源码候选，分别执行完整公开先订阅→删除→重订序列与未修改的官方参考集；记录调用结果、异常全文、首个失败断言和原 reward。此实验同时定位“公开原例仍未修却得1”和“公开行为修好却因消息得0”的静态预测，不另建作弊补丁，不调用 live AWS，不先改 oracle。CPU 结果只能验证分支/拒绝原因，不能替代规范选择。

独立初稿的核心判断保持；历史增加了 S1 安装失败的直接证据，并纠正旧报告关于 gold 位置、成功订阅覆盖及云服务事实的过度判断。主审的 needs_review/static_review 与两项疑点获支持，但应明确：**原版只适合已知争议的 development_diagnostic，暂不进入可解释 solver 能力的受限静态候选集。** actor 启用核验是任何后续模型工作另一个必要条件，当前不列第二个优先实验；无新 CPU、无模型运行、无费用/稳定性结论，未改封存稿或他人产物。
