# Dask包：根任务抽验

2026-09-25 / Codex B。**三题静态交付通过抽验：6626、7656保留受限开发候选，9378优先质量诊断。** 累计新增9题，6个受限候选、3个先诊断项；未取得实际actor或模型资格。继续首12题最后Pydantic包，储备20题仍待整批验收。

| 题目 | 核到的原件与结论 | 下一步边界 |
| --- | --- | --- |
| **6626** | 原题两种set_index顺序、gold的空categories修复、新K列及已有dtype断言对应。compat-v1两侧sparse已通过，noop一失败十五通过→gold十六通过，不能继续称旧环境恒失败。 | 公开两条用户流程仍缺实际actor验证；runner_integrity_changed两侧为true、配方确降pytest，但未核完整字节差异，保留限制，不据此断言候选篡改。 |
| **7656** | 新init=False字段无默认值，gold通过hasattr跳过缺失属性；重建仍以kwargs调用dataclass构造器。因此旧“gold总保留已有状态、按init过滤必丢post_init值”不成立。最终断言仅为嵌套a==3，没有完整状态比较。 | 支持公开Entry及嵌套delayed流程。题面已有修复提示，不能把结果解释为无提示独立定位能力；邻接状态语义未证，不冒称gold新增回归。 |
| **9378** | 新ones/zeros节点调用assert_eq；实际helper检查类型、shape、dtype/元数据后进入np.ma.allclose(masked_equal=True)，没有逐位mask比较。empty节点则明确比较getmaskarray。gold新增ma接口按块调用NumPy实现，未见同等证据证明gold本身漏mask。 | 支持只改变ones/zeros输出mask的私有窄诊断，同时保持MaskedArray类型与Dask包装。未实际运行错误候选；窄断言通过不等于完整RH2得分。empty未初始化值不能要求固定值或随机性。 |

六份原日志及选中账本与报告相符：7656为1fail/49pass/2xfail→50pass/2xfail，不能写成52项通过；9378为3fail/134pass→137pass，noop因新增ma接口不存在而失败，不是重新实测了题面顶层ones_like的mask行为。三题参考缺席均0。只核历史运行，没有执行项目、测试、容器或模型。

`derived_from`确按可识别的显式签名及doc参数行生成不支持提示，且本base对None doc已有处理；目标NumPy签名未读取，当前不认定实际dtype提示或任意kwargs兼容承诺。这不阻断本次mask诊断，也不另加通用接口实验。

过程抽验：五个角色的记录为Astra/high/fork_turns=none；九份封存稿摘要不变，后续材料release在各整包封存之后。原题/test/gold、决定性实现与原日志已核；协调者清除后稿跨题残句有归档。本结论是有限抽验，不证明完全无漏检、无误拒或OS隔离。

无需返工关键结论。任务二按[定向提案](pack03_followups.md)择取工作；原评分、题面和训练语义未变。详情见[协调报告](pack03_report.md)与逐题卡。
