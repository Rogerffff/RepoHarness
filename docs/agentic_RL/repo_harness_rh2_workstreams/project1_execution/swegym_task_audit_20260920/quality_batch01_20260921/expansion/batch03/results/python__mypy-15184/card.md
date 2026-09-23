# python__mypy-15184

`needs_review / static_review`；人工建议为静态候选，公开原例待诊断；正式模型开发另待actor验收。base `13f35ad0915e70c2c299e2eb308968c86117132d`。目标是assert_type错误中同名类型用完整限定名，保留无歧义短名；协议等价性只是题面讨论。

| 需求/旧行为 | 官方验收 | 证据与边界 |
|---|---|---|
| 普通同名类消歧 | F2P1：array.array[int]/__main__.array | 原no-op短名失败，gold通过 |
| 嵌套同名类消歧 | F2P2：__main__.array.array | 原no-op失败，gold通过 |
| 无歧义保持简洁 | P2P3：array[int]/int | 两边都通过；仍属负向类型断言 |

八方面已查：精确材料；公开需求及源码约定；28行测试和全部fixture/helper链；合理替代；assert_type判定/返回/Literal/unchecked旧行为及格式化调用者；本题安装与开发需求；新增official文件、投影与计分；关系和暴露范围。未查全仓回归、原题CLI、真实actor、重复/并发、Git/资产泄漏、模型轨迹和成本。

原RH2的同一install_wave1条件下，选3节点、解析3键、冻结F2P2/P2P1，无missing/skipped；no-op 2失败1通过/reward0，gold3通过/rc0/reward1。日志证实requirements与editable安装成功。镜像仅COPY离线wheel和ENV，原spec保留；grader54322、apply54321不能证明正式actor。当前镜像可用性和wheel payload待准备。

gold只改失败文案并复用已有共同消歧，未改is_same_type或错误码。没有发现实证误拒。旧称__main__不可公开推知、只能走gold helper均被公开代码/旧测试推翻。原SupportsIndex案例可能因结构协议判定已不再触发错误，仍未实测；不能以旧评论转述作结论。泛型内部冲突和正向assert_type未入评分，保留覆盖限度。

唯一优先下一步：核本次诊断解释器、导入来源、配置和包内桩后，在base/gold做原题程序及既有testAssertType窄组对照，确认公开复现和成功/失败/返回语义。未执行。official仅新增check-assert-type-fail.test；restored=0正常、应用成功，additional_exclusions=[]。独立复核已完成，协调者已收束。详见[初稿](analysis_before_history.md)和[历史差分](old_findings_delta.md)；审查产物已见gold/私测/历史，不得交solver。

协调者收束：保留受限静态候选。封存公开初读C3和reviewer初判中的“原例必报错”预测已撤回：is_same_type采用双向proper-subtype，两份SupportsIndex方法结构相同；完整CLI仍未知。若base/gold都无诊断，记录该条件原例已不触发，一般同名名义类的真实缺陷仍成立。最终以[复核](review.md)的开放判据为准，封存稿保留过程。

独立证据与分歧见[最终复核](review.md)。后续1.4公开base含10174的关键修复排序，15184还含15139小写分支；仅证代码包含，未核完整Git谱系或实际solver可见性。
