# pydantic__pydantic-8567 独立初判

结论：保留 needs_review/static_review。目标和 F2P 方向相符，但断言仅查 Python dump 字符串类型，未核公开 JSON 结果和值；gold 无条件重入内层 schema 的更广影响有明确静态风险，需目的明确的回归事实后再收口。

本稿为 fresh 独立 reviewer 在未读 public_read、主审、其它角色、旧质量结论和根汇总时形成的初判。全程只做静态文件、JSON、AST、hash 检查，未执行/导入项目、测试、安装、网络或容器操作。已读 roles/reviewer.md、record_template.md、actor_environment_card.md、check_number_reference.md、actor_development_validation.md。引用 P=本题 public 目录， V=本题 private 目录， L=run_refs.json 精确指定的原日志；下述 base 行号均指 P/base。包内其它两题仅用于共同方法理解，不作为本题事实证据。

实际 actor 初始 HEAD、porcelain status 输出/退出码/采集阶段、来源初始改动、忽略资产及准备后状态、消息、UID/HOME/cwd/PATH、解释器和文件权限全部 unknown。public/base 是固定 Git blobs；没有 .git 的静态导出不证明 actor 缺件。user_prompt 是计划输入，public_hints 是否实际交付未知。历史 grader 的 source import、安装和成功测试不是当前 actor 开发资格。

### 1. 公开目标与版本

base=8060fa1cff965850e5e08a67ca73d5272dcdcf9f，源码2.6.0a1，题面运行报告2.5.3。要求 Annotated bool 中 PlainSerializer 放在 PlainValidator 前后均生效，公开 model_dump_json 原例应 x="0"、y="1"。源码 functional_validators.py:129–162 的 PlainValidator 直接返回plain core schema，不调用handler；functional_serializers.py:18–56会先handler然后写serialization。_generate_schema.py:1693–1738,1805–1825逐metadata包装，因后面的plain validator截断内层生成，前置serializer丢失。已读这些完整决定性方法。

合理非gold路线：保留内层serialization或在生成Annotated schema时组合两类metadata；无须采用gold的wrap passthrough方式，须同时保留plain验证“替代内层验证”的语义和serializer自身when_used。

### 2. 完整 test patch/helper 与双向表

已完整读新增 import PlainSerializer 和 test_plain_validator_plain_serializer；F2P只有该函数。ser_type=str、serializer=lambda x: str(int(x))、validator=lambda x: bool(int(x))、两条字段的metadata逆序、Blah(foo='0',bar='1')及model_dump均已读。全部新增assert正好两条 isinstance；无外部fixture。

| 需求/旧行为 | 公开依据 | assert/反向约束 | 覆盖 |
|---|---|---|---|
| 两种顺序serializer均生效 | 题面 BRight/BWrong | isinstance(data['foo'],str) 与 bar | 覆盖Python dump类型这一必要表象 |
| 正确值0→"0"，1→"1" | 公开serializer函数和示例 | 无值相等assert；无调用跟踪 | 缺失，任意字符串/丢转换亦能满足 |
| JSON dump正确 | 题面model_dump_json | 新测仅model_dump()默认Python mode | 缺失；Python通过不能代替JSON |
| plain validator无info及with-info | 已有API/functional_validators分支 | F2P仅no-info；P2P plain/info测试只查validation | 组合serialization的with-info分支未测 |
| 保留plain替代内层validation | docs/concepts/validators.md:60–70 | P2P plain中x=-1→0及field_name；不检测unsupported inner schema | 部分，有回归空隙 |
| serializer when_used/不同返回类型/嵌套 | functional_serializers.py:18–30公开API | F2P only always,str,bool,单层 | 未覆盖，不据此另加题面要求但需关注受影响旧行为 |

测试不要求特定函数内部实现；foo对照能防“所有serialization都丢失”，但两个isinstance不能证明相同用户结果。

### 3. P2P实读、gold与旧行为风险

已完整读 tests/test_validators.py 内 P2P 主体 test_annotated_validator_plain:81–89（with-info），test_annotated_validator_nested:123–147（AfterValidator，不能充作plain嵌套覆盖），test_annotated_validator_runs_before_field_validators:150–161（也是AfterValidator），test_annotated_validator_typing_cache:164–181（四个param，含PlainValidator），test_plain_validator_field_name:2711–2718，及决定性foobar_validate helper:2616–2620（返回dict并复制info.data）。其余P2P主体未逐读，只对账全部expected nodeid与原状态行；未将158数量冒充受影响覆盖。搜索到 test_annotated.py 自定义core plain位置但未深入全文，不计已读覆盖；未读全test_serialize.py。

gold完整读：在 PlainValidator.__get_pydantic_core_schema__ 首先 handler(source_type)，再创建 passthrough wrap serializer，传给with-info/no-info两条plain返回路径。目标方向合理，验证仍走plain，不等于运行了内层validator。然而无条件handler新增“内层必须可生成schema”的前置条件。_generate_schema.py:396–405明示未知类型抛PydanticSchemaGenerationError，842–851在无arbitrary_types_allowed时到该分支；旧plain可根本不进入该路径。

具体静态风险例：自定义普通类Custom，无core schema；Annotated[Custom, PlainValidator(lambda v: Custom())]。旧plain的替代逻辑不需Custom schema，gold会先handler(Custom)触发unknown type错误。这是有源码路径支撑的待验证回归，不写成已运行/已证gold失败；是否为必须支持的合理旧用法应结合“替代内层逻辑”文档与同条件base/gold对照裁定。没有要求solver修复未公开的新功能，也不把审查假设提升成测试定义。

### 4. 原运行与实际状态边界

历史noop日志1500原pytest命令执行tests/test_validators.py，1502收集165项；1668 F2P failed，1672–1675在bar isinstance断言报 isinstance(True,str)==False；foo已过。gold1525同命令、1693 F2P passed。noop164 passed/1 failed、gold165 passed；P2P期望158项逐名均有PASSED。

历史noop132–140 status含pdm.lock及pyproject.toml修改，1216–1226 pyproject diff增加pre-commit>=3.5.0，987–1215 lock差异仅定位未全文核语义；这不能被clean静态base覆盖。gold1217–1237源码diff对应gold。dependency要求core2.15.0来自base pyproject，不能拿题面旧2.14.6当运行绑定。

### 5. 最有价值后续事实

优先请任务二将公开JSON原例通过实际actor shell跑通并记录base目标差异、工作区导入与初态；私有同条件可验证Custom+PlainValidator base/gold类构造差异，并说明其是否阻断合理旧行为。这两类事实分别裁定开发可用性与gold回归，不能用历史评分替代。漏测可另用有目的的诊断检验只保证str而值错/JSON未修的候选，但没有运行反例前只称静态可漏测性质。未执行或派发实验。

### 6. 开发操作/资产/权限

| 操作/资产 | 公开依据 | 适用证据与缺口 | 最小公开验证/预期 |
|---|---|---|---|
| 工作区Python、pydantic、core2.15.0 | pyproject:1–3,64–68；公开原例 | 历史grader2.6.0a1editable import成功；actor激活/ABI/路径未知 | 打印解释器、包来源、core版本，确认工作区源码生效 |
| 公共序列化行为 | 题面完整可执行例 | 本地模型/Annotated，无外部服务权重资产需求；包供应权限未验 | 执行公开model_dump_json例；base y为true为目标现象，修复期望y="1" |
| 窄开发回归 | test_validators.py及配置testing | 历史测试成功；actual actor pytest/依赖未验 | pytest tests/test_validators.py -k 'annotated_validator_plain or plain_validator_field_name or annotated_validator_typing_cache'，要求实际执行 |
| 安装与候选交付 | Makefile install、public_hints | hatchling、core wheel与actor源码/环境权限未知；历史wheel库不是actor资产证明 | 保存准备后status/退出码/diff，依实际初态交付非测试源码；必要editable安装需确认供应及写权限 |

### 7. 编号、使用与暴露

| checks | status | 证据/边界（by=fresh reviewer） |
|---|---|---|
| 1,2 | pass | 固定base与该历史noop目标机制 |
| 3,4,6,7,8,10,11,29,33 | unknown | 实际actor消息、初态、资产权限/开发路径未验 |
| 18,19,20,21 | pass | 限该历史选择器、expected逐名状态及bar失败位置 |
| 23,24 | pass | 需求明确且测试无实现方式约束 |
| 25 | issue | 仅str类型、没有JSON和值断言 |
| 26,27 | unknown | gold目标成立的历史证据；unsupported内层schema回归为静态风险待证 |
| 40 | unknown | 封存和抽查不能证明无漏检误杀/抽样偏差 |

其它not_checked。usage.intended_use=development_diagnostic，已暴露本包三题gold、隐藏测试、私有grader/candidate引用；未见其它角色/旧质量结论或模型答案。这是reviewer暴露，不自动判actor check29。不是训练/正式评测/ready_for_probe批准，token和费用未知。


### 原运行核对与交付恢复范围

- gold: `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8567/gold/ledger.jsonl:1`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8567/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_58053e09.eval.log`。历史 pydantic-install-v1、rh2grader UID 54322、deny_all 网络；image ID `sha256:6e5e6703c2e9393f60ffd10ef81454d87bfabd987f542ffe6f58d3771bc41a65`。install rc=0，test rc=0；F2P 1/1，P2P fail 0/158。只描述该历史执行。
- noop: `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8567/noop/ledger.jsonl:1`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8567/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_fe374a47.eval.log`。历史 pydantic-install-v1、rh2grader UID 54322、deny_all 网络；image ID `sha256:6e5e6703c2e9393f60ffd10ef81454d87bfabd987f542ffe6f58d3771bc41a65`。install rc=0，test rc=1；F2P 0/1，P2P fail 0/158。只描述该历史执行。
已用 stdlib 对账所有 expected F2P/P2P nodeid 与日志状态行：两次所有 P2P 均有 PASSED，无 expected 缺失；原账本 parser reference_missing/reference_skipped 为空、outside segment 为 0。不是将总分代替断言审查。已核 ledger/log SHA 与 run_refs 一致，gold candidate.patch 与本题 gold.patch 字节一致；stage HEAD 和 projection included_entry_paths 与本题源码修改对应。源码 diff 出现在 grader 日志；观察字段 import=/testbed/pydantic/__init__.py。

已读 after candidate/eval 脚本：conda testbed、/testbed、editable pip 安装及 testing/testing-extra 依赖、固定测试文件恢复后施加 test patch，再执行指定文件。实际日志含 checkout 与 Applied patch cleanly；账本 cleanup.removed=true。恢复、projection、runner digest 证据仅限该历史正常候选；没有穷举恶意评分控制面或并发/重复一致性，也未独立核实现行 parser 源码、完整 baseline manifest 和全部原 recipe before/build 内容。

初判到此封存，等待明确 cross_review release；不以封存本身作为check40通过证据。
