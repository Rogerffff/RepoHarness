# 分类3云端第二批：方法与续接独立审查

审查日期：2026-09-30。对象固定为 commit `0c074dc961231d2233a5624234a3606c239ecbcc` 的只读快照；不是用户摘要 `382b9c3`，两者之间有 1314 个文件变更。本审查只读文本、补丁、JSON 和已有日志，没有联网、SSH、运行项目、启动容器或重新评分。独立性限制：任务说明和批次 README 已转述主要主张；我随后直接核对原测试、gold、修订测试、候选与原始输出，未把作者结论当作验收依据。

**结论：工作方向合理，第二批已经取得可复用的具体诊断；应先校准状态、分类边界与验收方法，再继续原建议顺序。** 不需要全批推倒重做，也不能沿用 README 中“修订评分未归档、6题均未恢复”的暂停快照。前三题的新评分已在固定版本里；dask-7305 的新独立探针则推翻了“v1 已挡住已知错误解”的充分性。

分类3转分类2的条件是**问题、公开目标和窄修法已经明确，并能交接剩余事项**。正式修订材料入库、最终版本复验、聚焦审查和 actor 开发条件可由分类2承接。转2不等于修订已验收、环境完整、可以训练。本报告没有翻转题目资格或训练闸门。

## 1. 四道重点题

| 题目 | 固定快照里的可靠结论 | 具体剩余事项与转2条件 |
| --- | --- | --- |
| dask-7305 | 原测试没有有效保护大整数精确端点，并误拒合理内部分界。原7次、v1正式15次都已有证据。新增独立私有模拟证明 v1 放过3个同类错误候选；v2 draft 已针对它们补两类实例 | **建议转2**：当前目标、两个新增失效机制、v2窄补法与正对照核心范围均已清楚。交接时同步旧结论和D4核实记录；v2正式入库评分与聚焦复核列入分类2，不要求在分类3修到全绿 |
| conan-13403 | 原 mock 同时误拒正确 cwd 实现和放过不进入上下文的实现。v2 的吞错漏判与异常文案误拒在 v3 中修正；v3正式29次：gold和8个合理实现为1，noop及19个错误／边界候选为0 | 可以带明确余项转2。分类2承接 v3 聚焦复核、D6落地及最终版本复验；GNU工具链端到端和 actor 条件仍未验，不能据此授予训练资格 |
| pydantic-8567 | 原测试没有检查题面 JSON 输出及若干相关行为；gold破坏未知类型的PlainValidator。两份替代正对照已由原独立复核核实。v3正式17次已拒 `rv_pv_first` 并保留合理实现 | 可以带明确余项转2。分类2承接 v3 聚焦复核、D6落地、固定等效派生配方与actor核对；保留正对照范围差异，不能将“upstream261/c3_reorder合理”解释成全API等价 |
| dask-8801 | 原版T1已被措辞／引号2×2实验拆开证明；v4正式23次纠正原误判。root无关的OSError实例解决原阻断；P5第一分支有当前旧行为依据 | **建议转2**：目标足够明确，残余T1与已知类型子集漏判作为明确修复清单带入2；不能宣称v4修订验收完成。分类2承接窄修、最终复验及R-f新公开读者验收；若发现“报错／跳过”两种目标都有合理公开依据，才需要目标选择，并不要求两边依据等强 |

### dask-7305：新增证据使“只差复核”的旧安排失效

直接依据：[原测试与gold](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/dask__dask-7305/evidence/orig_test.patch)、[v1修订](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/dask7305/revised_test_v1.patch)、[私有模拟逐项结果](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/dask7305/review/out/grade/results.jsonl)、[v2草案](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/dask7305/review/revised_test_v2_draft.patch)。复核驱动明示其为root、断网的**私有模拟评分**，没有经过正式 `replay_grade.py`，不能把这里的1写成正式reward。

- `rv_pin_noclip`、`rv_interp_pin_noclip`、`rv_maxonly_threshold` 在 v1 私有模拟均为1，在 v2 draft 均为0；F2P执行，104个P2P均无失败。
- 前两者在“少量相邻大uint64、float舍入越过最大值”的实例分别破坏最大端点或有序性；后者只看正最大值阈值，在全负大int64上仍丢精度，`neg_int64` 的set_index还丢1行。这些是已有目标的实例，修订仅补相邻值与全负值，不要求再穷举全部类型。
- `gold_full`、`exact_full`、`higher_full` 在独立矩阵42个带 `ok` 的检查均通过，在 v1/v2 draft 私有模拟均为1；原内部分界分别允许 `[1,1,2,4]` 与 `[1,2,3,4]`，支持R-b放宽。矩阵另有小整数观察和扩展dtype失败记录；不能写成“44个场景全通过”。
- 三份正对照在 `process_val_weights` 中保持整数dtype，唯一值不足时用精确端点并夹住内部分界；`exact_full` 在摘要阶段保留精确端点，`higher_full` 采用离散取值。本次独立读补丁及归档探针，认为三者在公开要求的numpy大整数范围内可以作为合理正对照；扩展dtype与auto路径不在这项肯定结论内。任务目录却只有 [review_initial.md](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/dask__dask-7305/review_initial.md)，没有总结这些新结果的最终review；交2时应补成D4核实记录，不能继续写“独立复核尚未开始”。本次没有新跑候选，不把这些私有探针升级为正式修订验收。

**停止条件**：已有证据足以明确两种新增失效机制、v2窄补法、三份正对照核心范围与未查范围，建议转2。未见仍需留在分类3消解的目标选择；总结记录、正式v2与actor的验证由分类2承接，不因记录未汇总或v2未正式运行而新增转类门槛。

### conan-13403：替身校准有效，正式链仍未证明真实工具链

[v3完整测试](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/conan13403/revised_autotools_test_v3.py) 的 `run` 明确模拟 `ignore_errors=False` 抛错／`True` 返回非零，修正了v2把该参数吞进 `**kwargs` 后忽略的错误；失败检查接受原异常链和“返回失败码后报错”两种实现。它还从非build目录发起调用，区分“恢复调用者目录”与“总回build目录”。[旧独立复核](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/conan-io__conan-13403/review.md)及[v3逐项失败原因](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/conan-io__conan-13403/evidence/rerun_0930/formal_revised_v3/failure_reasons.txt)支持三处变化均针对已知问题。

这里的R-e只把目录切换改为真实目录行为，命令仍由记录器代替。因此“正式29次符合预期”证明正式判分采用该测试并区分这些候选，**没有证明真正运行autoreconf并生成configure**。作者已写明镜像无GNU工具链，未查清单诚实。位置参数顺序的gold回归未发现仓内常用调用，继续登记S2有依据；不应为保位置调用而把题面所有合理签名重新限定。

**停止条件**：29条新版结果与v3测试已经回答原阻断。聚焦复核只查替身真实性、失败传播、目录恢复和公开约束，不再把新增所有反例类别作为必跑清单。未查GNU工具链和actor条件交分类2安排。

### pydantic-8567：正对照可以不同，但必须携带差异范围

[原测试](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/pydantic8567/original_test.patch)只查输出是字符串；[v3](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/pydantic8567/revised_test_v3.patch)补精确Python/JSON、TypeAdapter、非示例模式、未知类型与PlainValidator短路。新加入的 `AfterValidator(lambda v: 1 / 0)` 是决定性故障注入：若原本被PlainValidator取代的验证器被重排到外层，它就实际执行并失败。v3账本中 `rv_pv_first` 为0、158个P2P无失败，gold仍只在未知类型断言失败，正对照与 `rv_condwrap` 为1；这些符合旧复核的修法，不是只比对总通过数。

[原独立复核§2](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/pydantic__pydantic-8567/review.md)实测并核实了两份正对照，也记录未知类型加serializer、未定义前向引用、源类型自带serializer等差异。保留这些范围记录是必要的。上游正式版只能作为佐证，不能仅凭“上游也是这样”把核心遗漏降成T3；另一方面，也不能把所有组合都扩进本轮测试。现有明确边缘／范围外项可继续登记，按用途限制解释。

**停止条件**：原阻断在v3已被决定性断言和正式链修正，可以转2；最终聚焦审查和资格确认仍未完成。本次没有复跑作者全量测试，相关宽覆盖只作为已归档历史证据。

### dask-8801：身份校准通过，仍须处置已承认的漏判与误拒

[当前结果页](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/dask__dask-8801/result.md)的09-30头部与23条v4正式账本相符。v4用配置目录里的 `c.yaml` 子目录触发OSError，避免把root不受chmod限制误判成候选错误。root运行gold的完整pytest日志仍是**2 failed、43 passed**，失败是原权限测试；两项F2P和41个P2P参考键通过。正确表述是“按参考名单结果一致”，不能写“root下测试全绿”。

两个需要在最终修订验收前明确处置的问题：

1. **已知类型子集漏判（建议按S1核，不接受仅凭构造不自然降T3）。** 当前结果页:310/319已承认 `rv_enum_types` 在v4私有模拟为1；[候选](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/dask8801/rv_enum_types.patch):24只拒list/str/int，[新行为输出](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/dask__dask-8801/evidence/rerun_0930/semantic_v4/rv_enum_types/b1_behavior.out)中 `fresh_import.bad_float_file_direct` 仍报 `AttributeError: 'float' object has no attribute 'items'`，不点名文件。这是“非mapping在读取处给可用诊断”的同一要求，与list/str/int的区别只是YAML基本类型；人工构造本身不能降低D1严格版严重度。本例尚无正式ledger，因此不能写“正式误放已证实”，但已足以交接窄修：加一个 `1.5` 实例并让已知候选为0，或提供足以证明属于罕见路径的公开证据再裁决。
2. **残余T1不是完成验收。** [v4补丁](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/rh2/experiments/category3_cloud_20260929/dask8801/revised_test_v4.patch):80仍按 `dict/mapping/key/type_name` 词表判断原因，结果页:321直接承认“expected an object／got a sequence”会被拒。增加一个词修好已知 `rv_kv_pairs` 有价值，但不能把词表扩充当作语义判据已经解决。先列明允许的行为与诊断最低内容，避免重新要求特定英文同义词；保留文件点名、实际失败、解析错误可见及已知错误仍拒这几项。由分类2用一个代表性合理措辞检查修法，不要求穷举同义词。

这两项的影响是新版可能误奖或误拒合理求解，建议分期为**最终修订验收／训练资格前处理**，不阻止带明确修法转2。可复核方式是阅读上述补丁和JSON，最终验收需在有效grader身份下验证。P5第一分支当前依据为base内容错误本就阻止加载，而OSError被单独跳过；我同意此为R-f已有依据补明，尚须新公开读者验收。没有必要现在再把A/B/C列为用户必选题。

## 2. 其余六题：未完成，但已经不都是“没有证据”

| 题目 | 当前真实状态 | 下一步与转2条件 |
| --- | --- | --- |
| moto-6185 | 结果页仍说无evidence；实际已有私有矩阵、原/v2/v2s模拟、全套DynamoDB输出和派生记录。正式评分表仍空，快照没有该题正式ledger | 先恢复“私有已核／正式未核”的状态。复用现有矩阵，独立核明主键名M等边缘项是否确应S2，决定v2或v2s窄范围并核实正对照；达到问题/目标/修法明确即可转2。若正式分数会改变分类判定，再补关键候选，不能将全部私有输出判作丢失重跑 |
| pydantic-8316 | 结果页说无evidence、只有13候选/v1；实际已有21条原材料正式ledger、gold/派生证据及v2草案。已知 `lead_only/first_only/acr3` 等原版为1，noop0/gold1；没有归档新版正式评分或完整私有矩阵 | 写清缩写修复一般目标与旧数字边界。v2只补两读法共同成立的 `base64URLEncode`、下划线与末尾缩写，不强行决定A1如何拆；对v2 reason中“已通过”的未归档陈述不作已验证事实。完成原版漏判诊断及v2修法说明、独立核对即可交2，最终新版评分由2承接 |
| dask-8597 | 未见本批新增任务目录／实验材料，README“未开始”仍与快照相符 | 复用历史环境，按split具体工作项先核目标、原断言和代表性部分修复；疑点消除可申请1，问题/窄补法明确可转2。不能从无新证据推导质量差 |
| dask-9212 | 同上 | 对pure delayed token的具体疑点做决定性对照并解释公开正确行为；目标和修法明确后转2，不增加与该机制无关的反例家族 |
| coveragepy f5eb | 已有[09-30原件初判](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/coveragepy__f5eb5f2159180db8cf0a1cf8b34bc96f1140dc96/initial_judgment.md)和rb2/rc2候选/草案；没有结论页、评分输出或最终独立审查 | 初判认为totals是唯一目标，文件summary额外合理字段属于R-b，不是两种相反目标。该判断有原件理由但仍是提议，应对照既有P5历史并给语义解释，核多文件总数、可选字段出现时值正确；形成可审查的目标/修法后交2。不得把“新初判”写成用户已批准或正式修订已落地 |
| pillow a682 | 已有公开环境brief和[盲读公开稿](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90/public_read.md)，封存时未运行；其后5条公开命令已实际执行并归档。题面TypeError已复现，GIF公开测试92过/2因Netpbm缺失跳过，convert测试27过；没有作者私有评分诊断／修订验收 | 复用已执行公开复现和边界探针，再查核心需求—隐藏断言关系，核合理修法及正负对照。保留R7关键字元组、R8警告等未约定范围；达到问题/目标/窄修法明确后转2，不重跑已有公开命令 |

这些新证据说明续接取得进展，**不说明六题已经完成**。原暂停记述应保留为历史，当前状态追加纠正；更新README当前总表，避免继续按旧“全部丢失”安排昂贵重跑。

Pillow的[后续devcheck结果](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/tasks/pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90/evidence/devcheck/results.json)与逐条stdout已核：调色板可分配的小图保存后保留透明度索引255；两帧路径成功且无透明度；真实tRNS PNG成功并保留索引59。这里证明公开初态和回归参照，不证明gold或新候选已经修好。`public_read.md`中的“未运行”是封存时事实，不应据此抹去后续CPU执行。

## 3. 共同反馈与建议顺序

1. **先更新证据驱动的续接表。** 记录每题材料版本、作者诊断、独立复核、正式/私有结果、修订落地与actor核对各自状态。只维护一个当前入口；把“未归档”的历史陈述与09-30恢复范围分清。已有输出不重跑，不从中间证据推最终资格。
2. **把候选类别改成排查提示。** [作者须知§2](https://github.com/Rogerffff/RepoHarness/blob/0c074dc961231d2233a5624234a3606c239ecbcc/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/category3_diagnosis_20260929/batch2_author_brief.md):29默认“每类至少想一个”比统一标准§7.1“仅实验会改变处置才跑、每个问题优先一个代表候选”更宽。按本题机制选择：精度题重点舍入/分支/范围，配置题重点输入类型/加载入口/诊断，目录题重点真实cwd/恢复/失败；不为凑全五类扩大每题范围。dask-7305作者说明“没有异常可吞”是正确裁剪。
3. **首次修订就核替身真实语义和误拒。** 从真实API列调用签名、返回值和异常方式，再写替身；R-b后重新审查有无引入文案、异常身份或顺序约束。代表性合理替代实现用于查过约束，真实错误效果用于查漏判，不将“总分符合预期”代替失败位置证据。
4. **采用已知范围的停止条件。** 新反例要先说明公开违例、路径常用程度和改变处置的价值；不把“还能造反例”当无限继续理由。已有复核阻断修正后只做一次聚焦检查；仍有真实目标分歧、且无便宜辨别证据时暂挂，继续其它题。
5. **顺序先小幅调整。** 先把conan-13403/pydantic-8567的已明确修法和余项交分类2；同时把dask-7305新发现收为v2交接，并给dask-8801两项残余问题明确处置。随后复用moto-6185与pydantic-8316已恢复证据，完成其作者判断；再完成已启动的coverage/pillow和两题尚未开始的dask。无需先启动其余49题，也不必先把第二批所有最终修订评分跑完才转2。

审查适用面：A/E/G/F/H/I/N为主，分别核行为、测试有效性、实际评分入口、规则一致性、证据版本、分期及API/依赖。B/C仅审题目reward和资格的口径，本次没有改变训练样本或闸门。D/J/K只检查共享文件与方法维护成本。L只据已有资源限制安排续接，没有测吞吐；M核账本可诊断范围。未审运行时并发、安全实现、真实模型能力或训前总审计，本报告不能代替那些级别的验收。
