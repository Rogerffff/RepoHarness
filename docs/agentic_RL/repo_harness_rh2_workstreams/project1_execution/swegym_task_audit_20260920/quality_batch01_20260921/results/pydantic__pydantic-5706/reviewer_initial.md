# pydantic__pydantic-5706 — 独立初判（封存）

2026-09-21。角色：独立 reviewer；依次完成 8511、5706。未参与主审；两题初判封存前未读任何本包其他角色结论。仅静态读取和元数据核验；没有导入/运行历史项目、安装、Docker、SSH、模型或新反例。本记录 scope=static_review、usage=development_diagnostic，state 保留 needs_review。

**初判。** 评分明确选择“让 `Sequence[int]` 生成 array/integer schema，并让合法 JSON 数组验证成功”。这与公开仓库中 Sequence 接受列表、普通容器生成数组 schema 的行为相容，源码也提供了分开处理 JSON/Python 的现成机制；然而 issue 本身把 schema 报错说成“seems as a correct behavior”，并提出“validate_json should raise if model_json_schema raises”。这是应保留的修复方向歧义，不能读过隐藏测试后把成功支持说成题面唯一明确要求，也不能仅因该措辞就直接判坏题。现有测试确实区分了 noop/gold，但没有保护 Sequence 的 Python 容器保持/元素校验回归；gold 重新生成元素 schema 时绕过公共生成入口，存在嵌套及自定义元素的具体静态缺口。建议先做定点 CPU 对照，并在第二阶段核对公开读者对方向的独立解释。原题现在不应被记录为质量已通过或 actor 已可运行。

## 原件、身份和暴露

- 权威根 `R=${REPO_ROOT}`。
- `P=R/runs/swegym_quality_batch01_20260921_v2/public/pydantic__pydantic-5706`；`D=R/runs/swegym_quality_batch01_20260921_v2/private/pydantic__pydantic-5706`。
- `L=R/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5706`。
- 已读共用 reviewer 卡、quality_review_protocol_20260920.md、actor_environment_card.md、record_template.md；verification-before-completion 技能只用于输出文件核验。
- 已读 P 的全部顶层题面/环境/身份材料；D 的 test.patch、gold.patch、grading、validation、run_refs、source_refs，以及 environment_record 的环境元数据（已暴露 verified_environment_pair、gold/noop 结果及其条件）。未沿 analysis/history 引用读旧汇总。
- 已读指定 gold/noop 原日志的当前 base、候选 diff、安装、官方测试恢复、执行/失败/结果段；两份 ledger 第 1 行；gold recipe.json 和 eval_script.after.sh。对 environment_record 引用的两角色 5 个 recipe 文件逐项做散列核对，全符；只对上列指定 recipe 读了文本，其余文件仅散列。
- 未读 public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json、任何 review.md、质量 history、manifest、主计划、method_adjustments 或其他角色结论。
- 在本题前已读 8511 原始 public/private 并封存其 reviewer_initial.md；本题后段为核题间关系，又读取 8511 public/base/_generate_schema.py 的 _sequence_schema。该较新 base 已含 JSON/Python 分支实现，因此本 reviewer 不是纯公开 solver；不把这种暴露用于声称 5706 的原题解法显然。8511 初判未回写。
- 5706 base=`70e7e99ca1861ad71520cc8fcf1a2fb913abbc10`，tree=`cc191fc0e571a936cd3af5e6114c075d862f892f`；bundle/grading/base_identity commit 一致，两补丁与 JSON 字符串逐字一致，gold SHA256 与 validation 一致；两日志 SHA256 与 run_refs 一致。
- 用户报告 2.0a3/core0.25.0/Python3.10.11；评分基线是 2.0a4/core0.31.0/Python3.8，grading version 标签为 2.04。原始 noop 在指定基线的相同 IsInstanceSchema 路径失败，因此没有“问题已修复却错测另题”的证据。未重新计算整个导出树的 Git ID。

## 公开方向和需求—断言映射

公开主目标是修复 Sequence 在 JSON schema 与 JSON validation 之间的不一致。它有两种初读路线：支持 JSON 数组，或保留 schema 拒绝并对 JSON validation 作对应限制。前者有仓库语义支持，但 issue 的措辞没有直接选择前者。`BaseModel.model_validate_json`（base/pydantic/main.py:415–440）直接调用 core 的 validate_json，`model_json_schema` 则生成描述文档；二者在架构上没有“必须先能生成 JSON Schema 才允许验证”的门。不能据用户的猜测给所有类型加全局 schema 门。docs/usage/models.md:516 的“解析后传给 model_validate”是高层且有旧文档痕迹，精确调用应以源码为准。后续若修订题面，应只澄清 Sequence 的期望结果，不把 hidden test 的字段名/输出逐字抄入公开要求。

| 要求或合理旧行为 | 公开依据 | 验收断言/参考身份 | 覆盖与执行范围 |
| --- | --- | --- | --- |
| Sequence[int] 应获得 array、items integer 的 schema（评分选定的方向） | issue 的“不一致”；docs/usage/types/sequence_iterable.md:58–61 接受 list/tuple；schema_mappings.toml:43–61、86–92 对应普通容器；旧 tests/test_json_schema.py:522、628、2245 的容器 schema | 新 `test_sequence_schema[sequence_type1]` 中 `sequence_type=typing.Sequence`；完整 dict 等值断言：object/title Model、required field、properties.field title Field/type array/items integer | F2P 1。noop 在 model_json_schema 抛错；gold 通过。dict 等值还检查默认标题和 required，均是旧测试可见惯例；没有函数名/mock 顺序要求。 |
| 同上，用不同字段名；合法 JSON 数组应验证成功 | issue 原例数组 [1,2,3]；Model 的一般验证语义 | 新 `test_sequences_int_json_schema[sequence_type1]`：同类 schema 等值（字段 int_seq，标题 Int Seq），随后 `assert Model.model_validate_json('{"int_seq": [1, 2, 3]}')` | F2P 2。前半与第一测试大幅重复；后半确实调用 JSON validator，但只测 truthy，不比 `.int_seq` 内容/类型。noop 在前半即失败，不能称 noop 已执行 JSON 验证断言；gold 到达并通过后半。 |
| List[int] 原有 schema 和 JSON 路径保持 | 公开旧 list schema、类型系统与题面 int_list 对照 | 上两测试的 `[sequence_type0]`，sequence_type=typing.List，完全相同 schema/成功断言 | 两个都是 273 P2P 的成员，gold/noop 均通过。原例两个字段同时存在的模型未直接受测。 |
| 元素必须受 int 校验；返回数据应正确 | Sequence[int] 注解；旧 tests/test_types.py:2029–2144 的错误元素/位置断言 | 新测试只用已是 int 的 [1,2,3]，不检查返回值；test_types 不在 reference | **缺失。** 没有错误元素、数值字符串转换、空序列、非数组 JSON、strict 模式断言。不能用 schema.items 为 integer 证明实际 validation 检查了 int。 |
| Python Sequence 仍保留 list/tuple/deque 等语义，不接受 set/generator | _validators.py:46–74；tests/test_types.py:1876–1891、2010–2026、2029–2144 | 公开 `test_sequence_success`（list、tuple、range、deque、嵌套 Set/Tuple）、`test_sequence_generator_fails`、`test_sequence_fails` | **本题评分未覆盖。** 273 P2P 全部位于 test_json_schema.py；这些测试没有在所引用命令中运行。gold 静态保留原 python_schema/is_instance/sequence_validator；简单把 Sequence 换成 List 的候选可能通过评分却丢失 tuple 类型、接受 set/generator。未执行该候选。 |
| str/bytes 不作为带元素类型的 Sequence | docs/usage/types/sequence_iterable.md:67 起；_validators.py:55–62；tests/test_edge_cases.py:2480–2522 | 公开 `test_sequences_str` 对合法分段列表和错误 plain str/bytes 作精确验证 | 该文件不在评分/所引运行；旧测试还有 Python<3.9 skip，不能直接借 3.8 环境称这一分支已通过。源码可读，后续可用直接公开复现。 |
| 不同元素/自定义类型的 schema 钩子不应被无故绕过 | _generate_schema.py:194–234、312–328；tests/test_json_schema.py:2188–2216（MyPath/List[MyPath]）、2390–2460（自定义泛型）、3737–3755（Annotated CustomType） | 上述相关 P2P 实际通过；但没有 `Sequence[Path]`、`Sequence[List[int]]`、`Sequence[CustomType]` 组合 | **部分。** P2P 只保护原 List/独立类型，不能证明 gold 的 Sequence metadata 回调正确。下节保留具体静态疑点。 |
| 未参数化 Sequence/Any、嵌套/模型引用、serialization 模式 | _sequence_schema Any 分支；get_first_arg:1335–1342；TypeAdapter:75–76、275–276；已有容器/模式测试 | 抽查 `test_unparameterized_schema_generation`（List/Dict）、`test_list_sub_model`、`test_deque`、`test_iterable`、tuple schema；查 schema/validation 两路径 | 没有新增 Sequence[Any]/bare/嵌套/serialization 测试。gold 扩及 Any 是实现范围，不表示这些都通过。未逐行读全仓关联测试。 |

两个新增测试都是局部 BaseModel，参数化仅 `pytest.param(List)`、`pytest.param(Sequence)`，没有新增 fixture/helper、mock、随机数据、外部资源。已读 imports、test.patch 全部改动及 `tests/conftest.py:43–47` 的 autouse fixture（仅关错误 URL）。一个参数名写成字符串、另一个写成一元 tuple 是 pytest 的合法形式，原日志确实收集并执行了四个节点。所有新增/修改断言已在表内列出。

公开文档存在局部不一致：sequence_iterable.md:116–118 仍说 Sequence 可消耗 generator，而本版 `_sequence_schema` 的 isinstance 门与 `test_sequence_generator_fails` 明确拒绝。审查把保留当前具体源码/旧测试行为作为回归依据，未借旧文档单句扩大本题去改变 generator 规则。

## gold、合理替代实现与具体风险

gold 只改 `_sequence_schema`：为 JSON 使用带 item schema 的 list；Python 仍先检查 Sequence 并用 sequence_validator；再用 json_or_python_schema 组合。对 int 的核心路径，base 失败原因与 gold 修法对应，没有凭空更改公共 API 名称或错误消息。相关调用者已追到 BaseModel/core、TypeAdapter、GenerateJsonSchema.json_or_python_schema、metadata 回调、标准类型的 preparation 和 sequence_validator。

**G1（静态，待实验）：gold 的 JSON schema 回调重建元素时调用 `self._generate_schema(item_type)`，不是 `self.generate_schema(item_type)`。** 后者在194–234行先处理 prepare annotations、core schema hook，随后接上 JSON schema hook；前者直接进入330行的内部分派。标准 `Path` 的 schema 是 `_std_types_schema.py:403–452` 的 preparation 生成的；`List[int]` 经同文件581–600的 preparation。因此 `Sequence[Path]` / `Sequence[List[int]]` 的 validation 分支使用完整入口可以建立，但 gold 的 JSON schema 回调绕过该入口后将落到 unsupported 路径（Path 的无 origin 分支，或 List 的 origin=list 而不在 _sequence_schema 允许 origin 集的分支）。自定义类的 `__get_pydantic_core_schema__`/JSON hook 也有同类风险。这个结论由源码强烈支持，**未实际执行**；且 base 对 Sequence 的 JSON schema 本已失败，因此它是 gold 的支持范围缺口，不能写成“原来成功现在失败”的已证实回归，也未证明 Sequence[int] 题面必须扩到所有这些类型。

合理非 gold 路线可以保留现有 python_schema，只提供正确的 json_schema，并让 `GenerateJsonSchema.json_or_python_schema`（json_schema.py:567–571）自然使用已经生成的 JSON 分支。该公开源码已有适配入口，不需要重建 item schema 的额外 metadata 回调。此路线是本次静态审查提出，未编写/执行；随后看到 8511 较新 base 的同函数1364–1376也采用这种形状，只把它记为题间关系，不当成早期公开要求。

**T1（静态，待实验）：直接返回 list_schema 是简单、看似能修好原例的部分实现，但可能被现有评分接受而破坏 Sequence 的 Python 语义。** 测试只检查 int 数组的 schema/成功验证；相关旧 test_types 未纳入参考。另一种错误实现是 JSON 用无元素约束的 list，但 schema metadata 仍宣称整数；现有正例也不能鉴别。它们是具体负对照候选，未执行前不宣称 reward=1。

**S1（规格保留）：** 支持数组有充分工程动机，特别是 List/Iterable 的公开 schema 和现成 JSON/Python 分支；不过这并不自动证明 issue 那句 should raise 已被公开材料明确撤回。仅抛相同 schema 错误的修法会被两条 F2P 拒绝，是否算合理解取决于公开目标的解释。暂记方向歧义与潜在误拒，未把其升级成已实证误拒，也未为保住 gold 放宽标准。

## 八方面实际覆盖

| 方面 | 已读/核实 | 未查或不能断言 |
| --- | --- | --- |
| 公开需求 | 全题面、hints、环境说明；Sequence 文档、容器/schema旧例、BaseModel/TypeAdapter入口 | 方向歧义保留；未看公开角色分析。静态 prompt 非实际捕获消息。 |
| 材料与初始问题 | base/patch/json/hash一致性；noop两条schema失败；源路径是IsInstanceSchema | 未新跑原例；原JSON验证分支因首断言失败未被noop测试执行。用户旧版与本base不同但同症状仍存在。 |
| 测试与要求 | 全新增断言、两F2P及两List P2P；全部273参考ID到原日志状态逐项元数据核对；相关P2P测试体 | 未逐行审273项无关测试体；校验返回数据、错误元素、Python容器语义缺失。 |
| 误拒合理解 | schema dict既有接口惯例、非gold JSON/Python分支路线；issue文字的拒绝路线 | 没有已执行替代解；不能证明所有合理实现均接受；S1未决。 |
| 回归与gold | 全gold，生成入口/钩子、metadata handler、sequence_validator、Path/List准备、相关公开旧测试 | G1/T1待CPU；Any、递归model、多模式、约束/strict未全面检查或执行。 |
| 开发条件 | pyproject/Makefile、安装recipe、目标包/core/pytest imports及原日志 | actor镜像消费、PATH/激活/源码生效、权限仍未知；没有项目运行。 |
| 交付与评分边界 | test.patch仅改test_json_schema.py；gold仅改_generate_schema.py；ledger projection包含源文件；日志恢复官方测试 | 未审整条parser/隔离链和真实镜像资产。常规修复不要求修改测试或不可提交资产。 |
| 题间关系和用途 | 8511较新base同函数已包含JSON/Python分支修法；两题不同公开目标/文件 | 不是重复同问题；尚未查完整祖先/全题库，不能推断独立训练样本关系。reviewer见过两gold，非独立solver。 |

## 真实运行、冻结参考与静态判断分别记录

`L/gold/ledger.jsonl:1`、`L/noop/ledger.jsonl:1` 是 **2026-09-19 真实 RH2 评分重放**，本轮只重读。镜像是 `pydantic-install-v1` 本地派生 `sha256:ccecd4e5820e16d1bfefa35fc6d2ccef95be84d09037ad677815df5f0ac039f4`；public digest 是另一个身份，不可互换。policy 为 rh2grader/54322、deny_all、2 CPU/4 GiB，解释器前缀可写；candidate.apply_user 的 agent/54321 只说明补丁应用身份，不能当成正式 actor 工具会话验收。observations 记录 `/testbed/pydantic/__init__.py`、2.0a4；gold projection仅 `_generate_schema.py`，noop空，未忽略路径。

- gold 原日志 `evallog_replay-er19-pyd1-pydanti_2ce45489.eval.log:143` 为指定 base。153–1115 是 `git show` 展示该 base 提交自身的历史 diff，**不是额外候选修改或未来泄漏**；1116 才是相对 base 的工作树 diff。候选代码3503–3538与gold对应；3542–3552 的环境初态在pyproject添加pre-commit，另有pdm.lock改动。
- gold 3555–3594恢复并应用官方测试；3732–3768 editable install成功，core0.31.0来自testbed Python3.8；3815真实命令只跑tests/test_json_schema.py；4093–4096四个新增节点通过；4099–4108为277 passed/1 xfailed、rc0。
- noop 原日志 `evallog_replay-er19-pyd1-pydanti_d4a2811f.eval.log:3775` 同文件命令；4053–4058两List通过、两Sequence失败；4135/4213为`PydanticInvalidForJsonSchema: ... IsInstanceSchema (typing.Sequence)`；4228–4237为2 failed/275 passed/1 xfailed、rc1。
- 逐个reference核对：gold F2P2/2、P2P273/273；noop F2P0/2、P2P273/273，与ledger一致。冻结参考之外还有2个`test_callable_fallback_with_non_serializable_default` warning参数化节点通过、1个旧`test_get_pydantic_core_schema_calls` XFAIL；全文件实际执行结果与冻结参考数不应混称。上述计数来自原日志，不是新跑pytest。
- recipe为`pip install -e .`加候选pyproject的testing/testing-extra依赖；/opt/rh2/build-wheels提供安装材料。其成功是grader条件的证据，不证明actor能访问这些wheel/写解释器或正式face已消费此配方。

## 最小后续实验和开发需求

**唯一优先实验：同一版本的定点对照矩阵（全部未执行）。** 以base、gold、保留Python门但去掉冗余schema回调的合理替代解为三组；先跑公开原例（两个字段）、JSON合法/非法元素和实际字段值，再检查 `Sequence[List[int]]` / `Sequence[Path]` 的schema是否与相应List元素schema一致；补公开 `test_types.py -k 'sequence_success or sequence_fails or sequence_generator_fails'`。随后只对需要判断接受度的gold/替代解跑相同RH2 reference。预期此矩阵可区别“core JSON支持已修复”与“schema回调仍绕过元素处理”，并验证合理替代路线是否被误拒。若扩展组合的预期不在本题决定范围，明确限制作int诊断，不把扩展实验失败直接等同原题不可用。

T1若需要实证评分漏回归，再增加一个把Sequence直接替换为List schema的局部错误候选；其正常JSON/score与tuple/set/generator旧行为对照足以判别，不必批量造攻击。S1的意图歧义不能靠CPU裁定；第二阶段应核公开证据与公开读者初判，如需修订，只明确“支持JSON数组且保持Python Sequence行为”，保留原版与修订版区别。

| 开发操作/资产 | 公开依据 | 当前证据与缺口 | 最小确认及预期 |
| --- | --- | --- | --- |
| 找到修复入口并交付源码 | _generate_schema.py:471–473、826–845；json_schema.py:567–571 | 可静态定位；gold源文件在projection被消费 | actor读写/testbed源文件；实际包来源应指向/testbed，临时公开复现能观察源改动 |
| 导入模型/core和窄测工具 | pyproject.toml:60–65、93–107；测试 imports | grader使用Python3.8/core0.31.0/2.0a4；actor未知 | 实际agent shell打印身份、cwd、sys.executable、包/core版本和路径；原例应到达目标行为而非导入/激活错误 |
| 依赖与构建 | hatchling/hatch-fancy-pypi-readme；公开Makefile全组安装；修订recipe | 修复只需Python源码；已有core wheel足够，不需要修改或编译core | 准备时预置必要wheel/依赖；若actor须重装，核prefix权限及离线build依赖，不能假定可联网 |
| 公开验证路径 | 题面原例、旧test_types Sequence用例；TypeAdapter接口 | 评分只有schema文件；原例Python3.10.11与评分3.8不同 | 3.8重现时用typing.List[int]代替原例list[int]以保留语义；若要逐字复现原例需3.9+。不要把3.8的语法兼容问题误记为目标bug |
| 外部资产/服务和提交边界 | 原例仅类定义/JSON字符串；test patch只含本地测试 | 不需数据集、权重、网络服务；修复不要求改受恢复测试 | 公开复现可离线；提交_generate_schema.py或相关非测试源文件，无需写系统环境作为修复 |

两份初判全部封存之前未读其他角色结论；本份保存后不回写。等待协调者统一开放第二阶段后另写 review.md。
