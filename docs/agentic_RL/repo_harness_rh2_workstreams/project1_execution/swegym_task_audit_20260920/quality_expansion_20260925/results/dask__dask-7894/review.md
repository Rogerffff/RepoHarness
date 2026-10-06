# dask__dask-7894 独立交叉复核

审查者：e25_review_pack11_dask；2026-09-25。root明确cross_review release后形成。封存初判SHA256 `3e60894bcc3a639629ab16d29d13160931eac98fc5761559b60bf4c8c1b288cd`，保持不变。

**维持 needs_review / static_review、development_diagnostic。** 主审对核心需求、全部新增断言、boundary漏测、历史noop/gold及actor未知的判断有原件支持。补充一项比笼统“new_axis邻近边界”更具体的静态回归路径；当前未运行，不能升级为已观测gold回归。唯一优先下一步与主审有实质差异，见末节。

## 读取与原件复核范围

本轮新增读取仅本题public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json，以及 `runs/swegym_quality_expansion_20260925/history/dask__dask-7894/refs.json` 授权的L1和Pilot两份本题记录。历史原件SHA分别为 `de6c82fd4fbd0b0f8e760330de5f17de22acf2e8805ac364f363613e3db5f053`、`63ac5e27701b0d425882afc4db73180e77bdafcfdf06c10649aa5d1fb52ec756`，均核对一致；只读旧文内主张，不跟随其候选、跨题或其他日志链接。第一阶段原件阅读范围见reviewer_initial.md。本轮另在本题public/base/dask/array/core.py定位轴/尺寸处理；定向读取3350–3420无决定性新证据，不用作回归断言。

本文源代码简称均指本题 `runs/swegym_quality_expansion_20260925/public/dask__dask-7894/base`。原日志及账本依第一阶段run_refs精确授权：w01-3/ledger.jsonl第7/8行、`_ef6aaeb0.eval.log`和`_81567ca7.eval.log`。本轮把主审screening_record.facts_ref中的candidate、projection、install、test、observations、expected_report、parser_diagnostics、cleanup逐字段与两行原账本机械比较，全部一致。没有执行或导入项目、测试、安装、网络、容器或模型，也未改任何既存稿件/题目。

## 技术复核与需求—断言覆盖

| 项目 | 对主审判断的复核 | 证据与限制 |
| --- | --- | --- |
| 删除后depth轴映射 | 确认 | overlap.py:691–699将map_blocks输出交给trim；core.py:685–686删轴，trim_internal:103–120与_trim:142–168仍按输出轴号读输入字典。七参数完整断言均比较实际均值数组 |
| boundary映射漏测 | 确认，属于check25 | 新边界0/reflect/nearest在trim端都属于非none。只有depth重映射的候选不会被七新增例区别；实际完整expected接受仍未执行该半修复 |
| 新增参数分组 | 确认 | (0,)、(1,)、(0,1)、(2,0)、标量1为5 F2P；(2,)、(1,2)为2新增P2P。不能把后两者当作boundary混合分支保护 |
| 数值与元数据 | 主审补充成立 | 新y先compute，numpy assertion不检查懒对象chunks/shape；旧assert_eq可能检查这些，但不能迁移成新增降维路径已验证。无具体“元数据错却通过”实测候选，issue保持覆盖边界 |
| 合理非gold实现/误拒 | 确认未锁实现 | 无helper名、patch字节或精确图要求；抽helper/统一轴变换可表达合法解。但没执行替代候选，不能证明普遍无误拒。主审check24=unknown比我的初判“pass限已读断言”更保守；交叉复核采用unknown并保留局部无锁定正证据 |
| no-drop/trim=False/零depth/多数组 | 确认局部正证据 | 对应旧测试和原分支已查；主审和我均明确P2P语义抽查，不以全部75个pass宣称交互穷尽 |
| 版本、执行与交付 | 确认 | exact base bf4bc7dd8dc96021b171e0941abde7a5f60ce89f，gold字节绑定；安装RC0/0，原选择 `pytest -n0 -rA --color=no dask/array/tests/test_overlap.py`，noop5失败75通过/RC1，gold80通过/RC0，无skip/xfail；actual image ID=null，不能用manifest替代 |
| actual actor与用途 | 确认unknown | 历史grader源码导入、干净noop或gold源码diff不是当前actor准备后工作树；git show只是HEAD正文。真实消息、权限、资产、解释器与资源待验；不批准训练/正式评测 |

主审analysis第58行“测试要求不同成员数值相等”是措辞错误；old_findings_delta末段已明确应读作每个参数各自与其均值参考相等。新增测试不存在跨“成员”相等断言。无需改封存稿，但后续摘录不能传播原错句。

## 新增具体发现与分歧

**R1 / static_regression_path / check26 unknown、check27完整性unknown。** 保留我在history释放前独立构造的组合：

```python
x = da.ones((5, 10), chunks=(5, 5))
y = da.map_overlap(
    lambda a: a.mean(0)[None, :], x,
    depth=(0, 1), boundary="reflect",
    drop_axis=0, new_axis=0, dtype=float,
)
# 用户语义预期：y.compute() 与 x.mean(0)[None, :].compute() 相同，shape=(1,10)
```

core.py:477–481明确先drop后new，:685–699实施。这个例子先删除原轴0，再在输出0插入长1新轴，保留原轴1位于输出1。base的trim深度{0:0,1:1}恰好仍与该输出对应；gold删除旧轴0后按kept_axes重新编号为{0:1}，没有将新增轴计入。由trim_internal:108–112可静态推出它会对新轴的长1扣2，并对真正需裁剪的输出轴1取默认0；_trim对新轴执行slice(1,-1)。这比“任意new_axis没支持”更具体，涉及可能破坏原先可用的输入。**已证的是映射/切片静态差异；尚未取得base返回正确、gold异常或错误数组的实际运行结果。** 不虚构异常类型、具体报错阶段或gold实测shape。

因此不能直接沿Pilot的“new_axis不是题意新增要求”抹去R1；那句话合理排除了要求实现任意新轴功能，却不能自动豁免保留既有合理行为。反过来也不能只凭邻近API文档就拒绝gold；需最小base/gold对照消解。

**R2 / coverage_gap / check25 issue。** 主审I1的确定性arange例与预测成立：depth=(0,2)、boundary=(reflect,none)、drop_axis=0；只映射depth时错误裁外沿，静态预测10→6。这是公开题意直接要求的boundary漏测，不是gold本身boundary错误。主审选原测试加此例做三候选对照能验证实际漏接收，是有价值的后续；本review只将其排在R1之后，不删除问题。

## 历史复述核验

L1确实写过“depth-only会失败”“kwargs.pop修改调用者字典”“ready_for_probe/判别力最好”和建议20次随机重复。Pilot已反驳前两项、收窄ready并保留随机稳定性未知；主审delta忠实区分这些版本，没有把旧标签当新事实。**kwargs由函数的`**kwargs`收集成局部映射，pop不删调用者展开字典键**，应明确退役旧副作用问题。

对old checks3/29收窄为actual actor unknown正确；L1的跨14题唯一性及DeepSeek完整通过本次未获原件，delta不继承也正确。无seed是事实，不等于已证reward抖动，主审不机械20次重跑合理。没有新历史运行能把R1或R2升级为实测。

## 结构字段与边界

screening_record具有规定13顶层字段，所列check均有status/evidence_refs/by，issues均有category/scope/evidence_refs/proposed_action/status；编号与中性1–40索引对应。检查3与23分开、25与26分开、27局部正证据与完整性分开、29实际actor与usage私有暴露分开、40=unknown；additional_exclusions=[]、revision_refs=[]、成本null、needs_review/static_review及development_diagnostic符合边界。

需要由协调者在自己的最终收口反映的新增信息仅R1及本次优先级分歧。主审card/record里的reviewer未读是生成时事实，不是结构错误；本review不擅自改写。check26继续unknown，建议其说明中从笼统new_axis邻近边界增加上面可核对的映射路径。

## 唯一优先下一步与交付结论

**优先任务二私有CPU的R1最小base/gold对照**，固定上述相同公开API例，记录源码来源、lazy shape/chunks、compute数组或异常及逐命令RC；同一同步本地调度条件即可，不需全仓、网络、GPU或模型。若base正确/gold错误，才形成明确的用户结果新增回归证据；若base也失败，则撤回“新增回归”方向并回到主审R2漏接收对照。这比先重复确认核心MCVE或仅泛查actor更能改变当前check26/27判断。

这与主审优先depth-only对照属于明确保留的排序分歧，不以人数裁决。两项都不能注入独立solver私有提示。actor环境捕获仍是共用验证要求，不能由本私有对照替代。当前未执行、未派发下一步；仅新增本review，初判及主审稿SHA不变。
