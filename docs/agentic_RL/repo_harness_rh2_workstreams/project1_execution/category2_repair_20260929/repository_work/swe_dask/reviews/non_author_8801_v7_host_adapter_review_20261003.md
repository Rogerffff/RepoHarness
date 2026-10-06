# Dask 8801 v7 宿主接线独立窄核

2026-10-03。范围仅为 `judge_job_from_formal_log.py`、`validate_semantic_verdicts.py`、五项合成管线检查原件及 revision 新增宿主元数据。最终按[假值兼容前的固定归档](../tasks/dask__dask-8801/history/dask8801-v7-before-falsy-compatibility_20261003/manifest.json)收口，宿主代码为 `99bb626d…f8d54`／`4880feba…e196b`，revision 为 `f18d5bc4…3f8e5`。未重审已通过的内联采集、补丁或 P2P；未读取留出标签、实际裁决输入／输出或控制校准结果。允许的本机格式检查只创建合成文件，不调用裁决者、CPU 作业、SSH 或网络。

**四类已复现的接线问题均已由题主修复，归档版本的有限复核未再现这些阻断。** 缓存绑定、盲输入隔离、宿主缺证、缺少裁决输出和 uncertain 的诊断侧处置已用 Python 3.9.6 合成文件验证。可以核销该固定旧版的宿主接线代码阻断；**不证明正在修改的假值双分支新版已经通过**，也不代表正式 CPU 或实际候选语义验收完成。

本审查未参与作者修改，写入范围只有本报告及同名 JSON；本机临时文件随检查清理，关闭 bytecode 写入。此前已接触 gold，不能充当新鲜语义裁决者。父线程关于已完成控制校准、逐 ID／引用验收的声明属于交接与元数据，本核没有读取或独立核销那些结果。

## 已核接线与授权范围

[归档 adapter](../tasks/dask__dask-8801/history/dask8801-v7-before-falsy-compatibility_20261003/judge_job_from_formal_log.py)接收单候选正式账本和日志，核材料身份、`agent/54321`、参考缺席数、安装、测试片段、日志 SHA 和清理，然后只从测试片段构建诊断裁决输入。行为分 0 与未完成执行分别处理；行为分 1 必须继续采集和语义步骤，不能直接当公开诊断目标通过。

缓存键按以下六项内容计算，13 个合成输入的 payload SHA、cache key 及不透明 ID 都与公式精确相符：

```text
SHA256([formal_material_identity, ledger_sha256, eval_log_sha256,
        judge_config_sha256, judge_prompt_sha256, payload_sha256])
```

相同字节证据、相同身份的新输出目录得到相同键。单独改变正式材料、账本 `run_id`、配置、提示，或日志／payload，键均变化。运行通过账本及日志 SHA 绑定；键不是仅按候选名缓存。配置中的 prompt SHA 还与实际 prompt 文件核对。

`judge_inputs.json` 只含 schema 和输入列表，每项只有不透明 `id` 与 `semantic_judge_input`。合成账本内的候选名、gold 标签、补丁 SHA 未进入盲输入；补丁 SHA 与 case／ID 对应关系留在 `private_run_binding.json`。此处验证的是宿主不附加这些身份；不会把诊断文本本身作为可以执行的指令。

输出只有诊断 job／outcome，不新增训练 reward。`automatic_training_reward_authorized` 为 false；`raw_behavior_score` 保留账本原行为分，不是把语义步骤转成 0／1。完整 13 ID 的合成结果中一项 uncertain，其余格式合格时，最终为 `needs_review`、保留全部 13 项及原行为分 1。缺少裁决输出同样为 `needs_review`，不丢样本。保存原配置字节的 SHA 不等于证明后端模型版本和 effort 完全固定；revision 已披露继承本地配置而后端精确快照不可得的限制。

## 复现问题及修复记录

以下是合成格式检查，不是对任何真实候选的语义重新评分。

| 问题 | 初版具体触发 | 修复要求与复核状态 |
| --- | --- | --- |
| 宿主缺失／损坏文件没有保存缺证状态 | adapter `006491b0…c5f1a`：prepare 缺 ledger 抛 `FileNotFoundError`、坏 JSON 抛 `JSONDecodeError`；finish 缺 `judge_inputs.json` 抛 `FileNotFoundError`，均未留下约定的状态原件 | 已核销。最终缺 ledger、坏 JSON、缺输入文件、job 为 `[]`／null／字符串及 awaiting 必要字段缺失均保存 `needs_evidence`。中间版 `7cf973a2…b8af8` 的顶层型别遗漏也已修复 |
| 测试片段只核计数，不核先后 | 日志仅一份 End、一份 Start，但 End 在前、Start 后放完整 13 封包，初版仍进入 `awaiting_independent_semantic_judge` | 已核销。最终核 Start 早于 End；同一反例返回并保存 `needs_evidence` |
| 裁决输入格式缺失触发异常 | validator `bb85fdc0…4a992`：输入项有 ID 却无 `semantic_judge_input` 抛 `KeyError`；中间版的总输入集合为 null 仍抛 `TypeError` | 已核销。缺 payload、总集为 null／空列表／对象均 `needs_evidence`；不当作裁决 fail |
| 裁决结构自相矛盾被接受 | verdict 为 pass，三项引用均可在可见诊断找到，但 `contradiction_evidence` 非空；初版 validator 返回 complete | 已核销。最终返回 `needs_review`；只核结果结构，不重判自然语言内容 |

初版五项合成检查绑定 adapter SHA `006491b0d73fd61121be52662764fe7cc33c7ee9527d4adea02aeb4f221c5f1a` 与 validator SHA `bb85fdc0016f8ce4a4e0476595e2f01dadd286df1d4f9dd9fad098a017f4a992`。这些是原件所属版本；不能因本轮修改而将旧五项检查静默称为新代码已经验证。最终新增独立格式检查与版本绑定记录在同名 JSON。

最终还核过：错误材料身份、未完成执行返回 `needs_evidence`；完整已观察行为失败单独为 `fail_behavior`；缺少输出 ID、重复 ID、引用不在可见诊断和 pass 自报矛盾证据均 `needs_review`。完整输入里的 uncertain 是合法裁决值，格式校验可为 complete，但综合诊断仍为 `needs_review`，不会误写成通过。

## 本报告不替代的验收

这里只核宿主接口及格式状态，未核正式 CPU 账本实物、真实 Dask 导入、参考测试或清理。本机合成账本中的完成字段是测试构造的数据，不是实际正式作业完成证据。发布后须以正式材料身份和实际回执调用 adapter；只匹配传入身份的功能不能替代外层确认该身份来自受信发布。

没有复裁已知／留出控制或验证实际模型输出语义；最终候选仍需新鲜裁决及逐 ID、引用与状态闭环。没有审核共享 grader 的全部安全面，也不把诊断通过推广成自动训练 reward、GPU 或训练资格。此前采集报告及测试／补丁绑定继续按其原范围复用。

## 最终版本

| 宿主代码 | SHA-256 |
| --- | --- |
| `judge_job_from_formal_log.py` | `99bb626dcc0ee12ea9d0b3447efbfd6774c9f751b64d64c32e5e38a4603f8d54` |
| `validate_semantic_verdicts.py` | `4880feba7ace4e133475a8ceeb4d3b23b7d38fff764065e5d69bb59baa1e196b` |

归档 revision 元数据与初版检查原件的独立 SHA、有限检查结果见[同名 JSON](non_author_8801_v7_host_adapter_review_20261003.json)。未改前一份采集审查报告；新版增量复核另行接续。
