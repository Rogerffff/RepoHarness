# 首批SWE四题复核

2026-09-30 / Codex。独立子代理 `c3_first_swe_review` 核对原件并回传结论；根任务核对归档、抽验关键原件，整理本文件。子代理的额外调查已停止，没有重新执行项目或评分。固定云端提交：`0c074dc961231d2233a5624234a3606c239ecbcc`。

**Conan14177、Moto7584、Pydantic9066同意转第2类。Dask9378的mask漏检已证明，但唯一API目标仍未明确，整题暂留第3类。** 正式修订落地、开发条件和最终用途另行验收；本次不授予普通探针或训练资格。

本地快照根为`runs/category3_cloud_review_20260930/snapshot_0c074dc9/`；下文题目录均位于其中的`docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/`。实验候选与修订位于同快照`rh2/experiments/category3_cloud_20260929/`。

四题已有82条正式路径诊断账本：Conan27、Moto35、Dask10、Pydantic10。日志摘要、有效字段、安装/测试结束、逐参考状态和清理记录已核；根任务另对全批335条检查日志SHA及实际退出标记。没有把私有root实验当成actor开发条件，也没有重新跑这些账本。

## Conan14177：可交第2类，采用v2方向

原题明确给出`apply_conandata_patches(conanfile, verbose=False)`，并要求`verbose=True`逐个记录实际应用的补丁；目标没有必要再作为P5选择题。原验收存在未真正应用补丁也能通过的候选，gold本身也不满足新增公开API。

v2用实际文本补丁效果与输出行为区分候选；`pubcand`已经过独立核实，15个变体的诊断结果支持修法。原独立复核提出的具体阻断在v2有对应修订及聚焦核对。转2的依据是公开目标、缺陷和修法明确，不是“多数候选分数合理”。

第2类应完成：正式测试补丁/版本落地、已知正确与错误候选复验、actor公开开发操作核对。`test_single_patch_description`在base已通过，应按真实用途处理参考分组，不把它继续冒称新F2P行为。现D6尚不支持本题所需任意测试替换，云端本题已正确列为首片之外的能力。

证据：`conan-io__conan-14177/result.md:11–17,67–135,161`、`review.md`，实验目录`conan14177/`的修订与候选，以及本题`evidence/`原日志。

## Moto7584：可交第2类，不能按gold改写公开生命周期

原题逐步要求先成功订阅、删除端点、再次订阅报错。gold提前返回旧订阅，未修好该公开路径；它的私有注释不能推翻题面。原验收还可接受“application一律报错”和“对所有协议都校验端点”的实现，同时以额外异常正文拒绝按题面实现的修法。

v3保留公开异常最低要求，覆盖有效/已删除/从未存在的application端点及正常SQS协议；11个候选的正式路径诊断和既有独立复核支持转2。端点删除不自动取消订阅的公开材料，不能单独推出再次订阅必须成功；无需为了与gold一致要求用户改题目目标。

第2类应落实v3材料、保留生命周期与有效协议正例，验证替代正对照、gold和已知错误候选；实际actor依赖/公开验证仍需按将使用的环境核对。

证据：`getmoto__moto-7584/result.md:5–24,51–114`、独立`review.md`，实验目录`moto7584/`及本题`evidence/`。

## Pydantic9066：可交第2类，正对照已存在但范围不能夸大

gold修复IPv4默认值的schema输出，却让标准dataclass默认实例在`TypeAdapter(..., config=...)`抛出`type-adapter-config-unused`。base已有该行为，且`encode_default`负责字段默认值编码；后来上游修复是佐证，不是唯一公开依据。

`fallback`与`upstream271`在原材料和修订v1均为1；gold在新增dataclass回归检查中为0。两条不同路线及独立核实足以支持存在兼顾目标与兼容行为的正对照。已经记录的边缘差异不等于它们在所有API组合上等价。

第2类应固定所用正对照及范围，正式落地回归检查，保留不可序列化默认值原护栏，并记录新增断言实际所属参考组。更合适时把dataclass回归独立列P2P；不得只因先前把它嵌入F2P运行，就称其本身也是base失败的新目标。

证据：`pydantic__pydantic-9066/result.md:3–23,53–103`、`review.md`和实验目录`pydantic9066/`，本题`evidence/`。

## Dask9378：mask修法成立，ma API的排他要求尚未成立

原题首先用`da.ones_like(array)`与NumPy输出对比说明mask应保留；末段用“perhaps the simplest thing…”建议实现`dask.array.ma.ones_like`等函数。base公开`creation.py`的docstring还写有“same shape and type”，不能只取`out: ndarray`一行排除MaskedArray；MaskedArray本身也是ndarray子类。

独立核对形成四项关键证据：

1. 原mask断言会把缺mask或反转mask的候选判为通过，实际公开行为却错误；补显式mask比较方向成立。
2. 顶层修法不是凭空假设：`toplevel_only`已实测保留mask，并通过320个公开creation测试。
3. ma模块模式和`da.ma.average`的分工可以支持ma路线，但不能消除原题顶层例子对另一条路线的支持。
4. 作者`result.md:50–58`及复核把“顶层缺文档/旧测试”当作无公开依据；新功能请求本来就可能修改旧行为。复核初判用“同等依据”作为P5门槛，也不符合两种读法均有合理公开依据的规则。

因此不能仅用R-f把“建议新增ma API”改成“必须新增”，再以新公开读者认为清楚来认定该选择已经得到授权。先核原版本有无排他性API约定；若仍有两种合理读法，应明确任务版本目标。mask漏检技术工作可以保留，不必重跑已证反例，但整题不应按当前排他草案转2。

另需删除本题仍沿用的“原版存在确证漏判，但可事后语义审计做普通比较”用途。它与当前用户决定及统一标准页首不一致；特殊诊断用途另行说明，不能作为进入普通探针的例外。

证据：`dask__dask-9378/result.md:14,50–58,103–110`、`review.md`、`review_initial.md`，`dask9378/toplevel_only.patch`与本题`evidence/`的顶层/ma行为、原与修订评分、公开creation测试输出。上述为既有原件核对，不是本次新容器试验。
