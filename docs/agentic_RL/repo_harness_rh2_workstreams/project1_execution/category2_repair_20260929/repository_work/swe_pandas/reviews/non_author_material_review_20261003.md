# Pandas 两题非作者材料窄核

2026-10-03。审查者未参与本包材料生成。本次结论为：**未发现阻断当前材料准备的具体问题；可进入已登记的 CPU 验收。** 这不是 fresh 运行、正式评分接线验收、actor 资格或训练准入。两题当前仍属分类二。

范围仅为本包 `preparation.md`、两题修订单/绑定/测试及候选草案、所指公开 base 和必要旧证据；不重做全题质量审查，不扩展候选数量。适用重点为参考身份、测试接受范围、版本一致性与证据边界；运行、成本与正式消费路径仅核对待办，不声称已验。

## 48106：绑定与成员保留成立

- `revision_draft.json` 的 F2P 前后均为 16 项，P2P 前后均为 1020 项；前后数组与所指原 `grading.json` **逐项相等**，不是只比较长度。测试补丁及公开 base 测试副本与来源字节相等。
- `reference_bindings_draft.json` 原三组 Period 的键、成员与顺序均保留，共七个成员。新增两组 tz 分别为标量/列表列选择的两个成员，以及 DataFrame/Series × 两种切片终点的四个成员。对 gold/noop 的各自唯一测试输出段独立提取完整摘要，新增每组的成员集合与日志该别名下的全部完整节点严格相等；总五组十三个绑定成员在两份日志中各仅有一个 PASSED 摘要。结合公开 `test_loc.py` 的相应参数与正文，未见成员丢失、跨组混入或错绑。
- 已引用的诊断绑定函数按完整 nodeid 匹配，任一成员缺席则不生成组状态；消费时先删除旧别名再更新，不能回退到旧别名末值。所有成员的状态并集按 `ERROR > FAILED > SKIPPED > XFAIL > PASSED` 聚合，因此任一非 PASS 不会被同组 PASS 覆盖，行序不影响该优先级。这是当前软件语义静态核对，**不是正式 manager 的全局会话/评分验证**。XFAIL 的评分分桶仍须沿既有 SWE 规则，不据此新增 reward 规则。
- 旧两组 tz 的六成员在保存日志中全部通过，只证明存在身份合并和本次绑定完整；不能称旧运行已误奖。原 noop0/gold1 结论不改写。

证据：[绑定草案](../tasks/pandas-dev__pandas-48106/reference_bindings_draft.json)、[修订单](../tasks/pandas-dev__pandas-48106/revision_draft.json)、[公开测试](../tasks/pandas-dev__pandas-48106/public_tests/pandas/tests/indexing/test_loc.py)、既有 [独立复核](../../../../swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch02/results/pandas-dev__pandas-48106/review.md)。原日志精确路径及摘要留在修订单引用与本包离线检查，不改写历史原件。

## 50319：接受公开允许的 None，保留旧回归约束

- 公开 bundle 的原题面明确允许返回 `None` 或猜中格式，要求不抛错误；公开 base `parsing.pyx` 的 `guess_datetime_format` 返回契约也为格式字符串或 None。公开 `datetimes.py` 的 `_guess_datetime_format_for_array` 与上层转换路径明确承载 None 后逐项解析。因此接受合理 None 路线有公开依据，无需把 gold 的内部正则或唯一格式字符串作为验收条件。
- 有效测试补丁从公开 base 构造。我在临时副本独立执行 `git apply --check --whitespace=error` 及纯静态应用，并解析 AST：移除唯一新增函数后，整个模块 AST 与 base 相等。原成功格式、dayfirst、非法输入、wrong-type 和其它测试均原样保留；原新增单例不再作为旧成功格式参数残留。
- 原唯一 F2P 被 `reported` 与 `another-dot-date` 两个稳定 ID 替换。109 项 P2P 前后与来源数组逐项相等；旧反斜杠绑定保留，新增两个空白截断别名的 2/4 完整成员与两份旧日志集合严格相等，且各成员仅有一个 PASSED 摘要。
- 新断言显式使用 `is not None`：None 被接纳；其它值必须为字符串，且 `datetime.strptime` 的完整结果必须等于预期年月日、时分秒及微秒。两样例改变日期和时间，第二例使用非零六位小数秒，仍在相同点分日期问题范围内。它能静态排除布尔值、数字、空字符串、无法解析的格式和解析为错误日期/时间的格式；固定错误格式不能仅凭“返回字符串”通过。原样例仍被完整验收，只把不公开承诺的精确格式要求改为正确结果要求。
- 恒 None 候选即使满足新两节点，也违背原有非 None 成功格式及 dayfirst 等 P2P 的相等断言；这些断言未放宽。局部 `_fill_token` 的 `ValueError → None` 候选不吞整个函数异常，不限制题面字面值；仅示例候选和无效格式候选分别对应第二节点及字符串语义断言。五份候选补丁在公开 base 临时副本均通过静态应用，gold 副本与原 gold 字节相等。**这只确认候选可应用及断言方向；没有证明候选编译成功、运行得分或回归通过。**

证据：[有效测试补丁](../tasks/pandas-dev__pandas-50319/test_patch_draft.patch)、[修订单](../tasks/pandas-dev__pandas-50319/revision_draft.json)、[绑定草案](../tasks/pandas-dev__pandas-50319/reference_bindings_draft.json)、[候选](../tasks/pandas-dev__pandas-50319/candidates/)、[私有调用者检查](../tasks/pandas-dev__pandas-50319/check_runtime_contract.py)、既有 [独立复核](../../../../swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/pandas-dev__pandas-50319/review.md)。公开题面与 base 源码以修订单所指版本为准，本轮未另取线上变动版本。

## 核验身份、剩余事项与停止条件

本包 manifest 的 17 个文件引用摘要全部重算一致；两题修订单所指原件/草案文件摘要，以及原 grading/public 的 canonical digest 全部一致；离线检查引用的 parser 和诊断 binding 当前字节也与其记录一致。作者的 64 个合成状态控制、14 个返回值控制只作为作者软件控制阅读，本轮未把它们冒称独立实际测试。

待 CPU 的工作保持原准备入口安排：48106 核新宿主身份、完整绑定的正式消费与 noop/gold；50319 先实际重编译并以新进程核源码/扩展加载，证实局部 None 路线旧行为和调用者回退，再做新材料的正式节点收集与已列正负对照。有效补丁须**替换**原测试补丁，在 base 上生成正确官方测试；不能在已应用原补丁的测试文件上简单叠加而保留旧精确格式断言。正式登记、选择/保护/恢复/解析及材料身份一致性尚未验收，诊断 wrapper 不作为这项验收的替代。

停止条件：本次材料窄核到此结束；仅在正式接线/CPU 原始结果带来具体矛盾，或本次所核文件身份变化时复核相应差异。不因尚未穷尽其它日期语法或全部旧测试而增加本轮候选、启动全题审查或升级训练资格。

本轮只执行文件读取、stdlib JSON/hash/AST 分析与临时副本 `git apply` 静态检查；没有运行准备生成器、导入 pandas/项目模块、执行测试、编译 Cython、安装、下载、SSH、容器或模型。没有新 reward，也没有已发生的 None 误拒证据。唯一新增文件为本审查记录；创建使用排他写入，未覆盖作者或他人文件。
