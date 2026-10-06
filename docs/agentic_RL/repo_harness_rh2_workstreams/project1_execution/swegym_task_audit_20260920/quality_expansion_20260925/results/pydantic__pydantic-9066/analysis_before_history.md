# pydantic__pydantic-9066 — 历史解封前独立分析

初判：题面真正观察到的是 JSON Schema 默认值编码，不是 IP 输入校验。IPv4/IPv6 两项新增断言有公开依据，H noop/gold 对照成立；但 gold 改了通用默认值编码，标准 dataclass 实例默认值存在具体静态异常链，现有 P2P 未针对覆盖。保留 needs_review；不将静态疑点冒称已执行回归，也不以 gold 通过等同完整正确。

## 审查边界与证据等级

作者/by：main_pack12_pydantic（私有主审）。所有命令显式 workdir=/Users/roger/Desktop/claude-code-verl-stage0h。完整读取指定派发卡、investigator、record_template、check_number_reference、actor_environment_card、actor_development_validation 方法文件。仅访问本包两题 PUBLIC/PRIVATE、各自封存 public_read.md 和 run_refs/environment_record 精确授权原件；没有读取 history、reviewer、旧质量结论、其他包或根汇总。没有执行/导入项目、测试、安装、网络、容器、SSH、GPU、模型或子 agent；只做文件、JSON/hash 和静态源码阅读。前稿保存后不再改写，等待 root 明确 history release。

下文 P=本题 public 目录，Q=本题 private 目录；源码/旧测试行号相对 P/base，patch 行号相对 Q。原日志使用本题 run_refs 中的精确路径，末尾运行附录给出身份与行号。S=静态直接证据/推断；H=授权历史真实 RH2 原件；A=当前 actor，尚无观测。H 不替代 A。

## 1. 公开目标、版本与初态

P/user_prompt:3–30 中 IPvAnyAddress 字段默认 IPv4Address('127.0.0.1') 在 model_json_schema() 触发 non-serializable-default 并省略 default。合理目标是正常生成 schema，default='127.0.0.1'，保留 type=string、format=ipvanyaddress、标题、非 required，并不再因该值告警。字符串预期来自 networks.py:511–575 的现有 IP serializer 和 tests/test_networks_ipaddress.py:352–363，不是凭标题扩张。IPv6 是同一 IPvAnyAddress 已承诺支持的相邻情况。

base_commit=a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7，tree=77943505872ef44e237e874ea1d3770f96c16959，482 跟踪条目；静态导出声明没有 gitlinks/LFS/软链缺口，未重验全部 blob。Q/grading 和 validation 的 patch 分别与 test.patch/gold.patch 逐字一致。报告者 Python3.11.5/macOS/core2.16.3 与历史 grader Python3.8/Linux 是不同条件；pyproject:47–52 允许 >=3.8 且固定 core2.16.3。

原 noop log :132–140 的 status 显示 pdm.lock、pyproject.toml 已修改；:141 git show 是提交展示，:163 起才是实际相对base diff。pyproject :392–403 增 pre-commit>=3.5.0；pdm.lock :164–391 从4.4.1变4.5.0、加入metadata.targets/pre-commit及依赖/兼容标记。H baseline HEAD 对应base，不代表工作树无改动。实际actor消息、HEAD/status/diff RC/阶段、来源规定初态、忽略资产及准备后状态仍 unknown。

## 2. 根因链、全部 gold 改动和回归疑点

json_schema.py:988–1026 的 default_schema 从 core schema 取 default，调用 encode_default；只捕获 PydanticSerializationError 并发题面告警，$ref 默认值用 allOf 包装。:1985–2001 直接 to_jsonable_python(dft, timedelta_mode=..., bytes_mode=...)，没有字段 serializer 信息。networks.py:563–575、_std_types_schema.py:582–665 明确有地址/网络/接口 to_string serializer。原 H 失败回溯直接在 encode_default 遇 IPv4/IPv6未知类型，支持该因果定位。

gold 全文已读：新增 PydanticSchemaGenerationError import；encode_default 局部导入 TypeAdapter；有 __pydantic_serializer__ 的实例保持原值，否则 TypeAdapter(type(dft), config=config.config_dict).dump_python(dft, mode='json')；只将 PydanticSchemaGenerationError 转成 PydanticSerializationError，最后仍 to_jsonable_python。改动仅 json_schema.py，无测试/控制面修改。TypeAdapter 是按实际默认值类型编码，不先按字段注解validate_default，因此可保留 ByteSize('1MB')测试期待的原默认表示；有自身serializer的 BaseModel/Pydantic dataclass 避免config冲突。

具体未证回归候选：标准库 @dataclasses.dataclass 的 D(x=1) 默认实例一般无 __pydantic_serializer__，gold 会进入 TypeAdapter(D, config={...})。type_adapter.py:101–107 的 _type_has_config 将任意 dataclass 标为有配置，:193–204 在 config is not None 时抛 PydanticUserError(code='type-adapter-config-unused')；_config.py:87–91,268–286 说明空配置也是 dict 而非 None。gold只捕获另一个异常类，default_schema也不会接住此PydanticUserError。_generate_schema.py:1474–1564 的标准dataclass schema路径生成定义但未为原D安装serializer，故绕过分支不是明显可依赖的保护。

该链是具体静态风险，尚无本轮执行或已核H证明 base 同例成功、gold失败，check26 保持 unknown。已读 test_nested_python_dataclasses(:4232–4267) 只测无默认值的嵌套 schema；test_dataclass_default_bytes/timedelta 的默认值实际是 bytes/timedelta；test_model_default 与 test_nested_default_json_schema 使用有serializer的BaseModel。这些 P2P 全过不能排除 D实例默认值异常。只要该对照证实，gold完整性应下调，而非把原IP题目标定为不可解。

其他边界：列表/字典中嵌套 IP 默认值未保证被 TypeAdapter(list/dict)逐叶子识别；字段自定义serializer、用户类型、tuple/子类、注解与实际值不同、两种mode、default_factory未调用等不由两项F2P穷尽。它们是覆盖界限，除上述dataclass疑点外，本轮没有足够证据逐项定为新回归。gold使用实际类型是实现选择，不能反推公开规格必须采用TypeAdapter。

## 3. 需求—断言双向表、helper 与合理替代解

完整读 test.patch：新增一个参数化函数，两组 IPvAnyAddress/IPv4Address或IPv6Address/expected_schema，函数内声明 BaseModel 后一次 schema==expected_schema。无新增fixture、无网络/Mock/helper。现有 imports(:1–106)提供 IPv 类型、BaseModel、pytest；conftest:46–50 autouse仅设置错误URL省略，pyproject:156–172使warning变error、xfail严格。故即使没有显式“无警告”assert，原目标告警会使新增测试失败。

| 公开要求/合理旧行为 | 依据 | 测试ID/决定性断言 | 覆盖及证据 |
|---|---|---|---|
| IPv4默认值进入schema且不再因不可编码告警 | 原例；IP旧序列化 | test_default_value_encoding[IPvAnyAddress-default_value0-expected_schema0]：default='127.0.0.1'、format/title/type、无required | S直接；H FAIL→PASS |
| IPv6同类默认值支持 | IPvAnyAddress公开支持v4/v6；networks.py、ipaddress旧测试 | test_default_value_encoding[IPvAnyAddress-default_value1-expected_schema1]：default='::1'及同结构 | S合理扩展；H FAIL→PASS |
| 无默认地址/网络/接口仍有原format与required | test_json_schema:1106–1220 | P2P ipv4/ipv6/ipvany address/interface/network 类型函数 | S/H旧行为覆盖；不是默认值泛化证明 |
| 真正不可序列化值继续省略并告警 | default_schema；旧test_non_serializable_default | 两参数：lambda与含lambda字典，warnings匹配、properties、required缺省 | S/H覆盖特定回退；不能整体禁警告或任意str() |
| 原默认值不被按字段校验改变 | test_byte_size_type:1296–1337 | ByteSize字段默认'1MB'，validation/serialization都保留该字符串 | S/H覆盖该旧行为 |
| bytes/timedelta编码配置、嵌套模型及$ref保持 | test_json_schema:1697–1852,4465–4489 | model/dataclass/typeddict default_bytes/default_timedelta；model_default、nested_default_json_schema | S/H针对配置和有serializer对象；未覆盖标准dataclass对象默认值 |
| 标准dataclass实例默认值不应使整个schema生成崩溃 | 既有dataclass支持、default_schema通用回退；具体异常链见上 | 无针对F2P/P2P断言；nested_python_dataclasses不含默认实例 | S有具体风险，H未测，需base/gold窄对照 |
| 有效IP输入/非法IP拒绝/JSON字符串输出不变 | tests/test_networks_ipaddress:11–43,194–223,352–363 | test_ipaddress_success/fails、ipvany_serialization | S已读；该模块不在H实际selector |
| 模式与IP容器/自定义serializer | 默认validation文档:255–302；serializer现有机制 | 新增仅default validation；无针对容器IP/default_factory断言 | 覆盖部分/缺失，未凭直觉增加强制评分要求 |

反向看，新增隐藏IPv6要求可从IPvAnyAddress公开范围推出，无只在gold中才出现的私有算法要求；完整dict是该项目既有测试风格。支持局部IP默认编码、复用已有serializer或完善通用默认编码等非gold实现，只要保留公开旧行为都应有机会通过；未执行替代解，不声明普遍无误拒。仅支持IPv4的修复会被IPv6拒绝，这不是无依据扩张；任意str()所有对象或吞掉所有warning会违背已读P2P。对当前两IP值写死的错误实现仍可能过，F2P通过不证明完整支持所有IP值，记check25。

P2P共367个expected身份全部机械对齐原日志为PASSED；语义阅读明确是风险抽查：上述IP无默认、ByteSize、不可序列化两参数、list/dict/enum默认、model/nested default、model/dataclass/typeddict bytes/timedelta与nested_python_dataclasses。剩余P2P只核状态未逐断言阅读；tests/test_networks_ipaddress相关公开测试未在H执行。不以367个状态代表367项语义审计。

## 4. 开发条件、交付恢复与暴露

| 需要操作/资产 | 公开依据 | H条件 / A缺口 | 最小后续公开验证（均未执行） |
|---|---|---|---|
| 输入、真实工作树与权限 | P/user_prompt/public_hints/environment_brief | 计划输入与base；H有预存依赖改动；A unknown | 捕获实际消息，pwd/git rev-parse HEAD/git status --porcelain=v1/git diff并记录RC/阶段 |
| 对应Python/core和本地源码 | pyproject:47–52；题面 | H editable安装/core2.16.3/Python3.8；A PATH/激活/导入未知 | python -c 打印sys.executable、pydantic.__file__、core.__version__，确认actor checkout |
| 公开IP默认值API | 原例与标准IP序列化 | H两隐藏变体通过；A未执行 | python - 内联原例，warnings.simplefilter('error', PydanticJsonSchemaWarning)，assert default字符串；validation为原始模式，serialization作相邻回归 |
| 旧schema边界与工具 | 已读test_json_schema及pyproject benchmark | H单模块可收集执行；A插件、缓存/临时写权限未知 | python -m pytest -q tests/test_json_schema.py -k 'ipv or non_serializable_default or byte_size_type or model_default_timedelta or model_default_bytes' |
| IP输入校验/序列化 | test_networks_ipaddress | H未选择此模块 | python -m pytest -q tests/test_networks_ipaddress.py -k 'ipaddress_success or ipaddress_fails or ipvany_serialization' |
| 安装、资产与服务 | testing/testing-extra、纯本地schema代码 | H本地wheelhouse+deny_all成功；A位置权限未知 | 依赖准备完后原例无需网络/GPU/模型权重；在actor检查必要导入/临时目录，不因静态导出缺某目录推断镜像缺资产 |
| 合法交付与可信测试 | public_hints要求NON-TEST；原recipe/projection | H只投影json_schema.py，重置/apply测试RC0 | 按实际初态导出源码改动，不提交私有/测试/原始准备差异作为解答 |

已读 eval_script.after.sh 的可信测试checkout+apply过程；diagnostics与log的SETUP_APPLY_RC=0、RESTORED=1、EXPECTED=1、ABSENT=0、PROTECT_OK=1，支持对应H运行恢复了该唯一测试文件。candidate投影仅json_schema.py且hash等于gold。历史pip配方消费候选安装元数据，去除了原pdm add pre-commit; make install开发全套操作；来源镜像增wheelhouse，PIP_NO_INDEX=1。修订的是环境入口，不是IP规格或测试断言，适用性仅限H，不能宣告当前actor修好。

actual actor可见材料/工具网络泄露为unknown，检查29不能用审查流程合规替代。审查者已接触gold、hidden、expected、H与public_read，usage.intended_use=development_diagnostic，禁止输入独立solver。此base的fields.py:422–435和tests/test_json_schema:5941–5997已包含8793的字段修复/三断言，所以两题有关联的版本历史；本题gold和目标仍是另一个默认编码问题，不能视同重复任务，也未核其他评测集合交叠。

## 5. 初判检查、问题和唯一优先下一步

| check | status | evidence_refs / 边界 | by |
|---|---|---|---|
| 1,2 | pass | P/base_identity，Q patch相等，H候选binding、逐IP F2P，限定材料/H | main_pack12_pydantic |
| 3,8,10,33 | unknown | 实际消息/初态/actor执行未取得 | main_pack12_pydantic |
| 4,16,17,18,19,20,21 | pass | NON-TEST计划边界；H投影/恢复/真实选择器/RC和expected对应，仅H范围 | main_pack12_pydantic |
| 6,7,11,13 | unknown | H局部安装/资源成功；A仍待核 | main_pack12_pydantic |
| 23 | pass | IPv4原例及IPvAnyAddress公开IPv6语义；非运行时解析新规格 | main_pack12_pydantic |
| 24 | unknown | 未见强制TypeAdapter实现；合理替代解未执行 | main_pack12_pydantic |
| 25 | issue | 新增仅两IP默认值；普通dataclass默认实例未被相关P2P覆盖 | main_pack12_pydantic |
| 26 | unknown | gold→TypeAdapter配置冲突静态链明确；base/gold同例运行未核，未称已证回归 | main_pack12_pydantic |
| 27 | unknown | H证明IP局部修复，不能排除通用编码风险 | main_pack12_pydantic |
| 28 | pass | 具体dataclass疑点是旧行为回归检查，未成为新生产要求 | main_pack12_pydantic |
| 29,30,31,35,36,38,39,40 | unknown | actor泄露/控制面、真实解/适用阶段/复验与完整筛查偏差无充分证据 | main_pack12_pydantic |

未列项为not_checked。issues：①category=coverage，scope=通用默认编码，evidence_refs=gold及双向表，proposed_action=以相关旧行为审查解答，status=open；②category=potential_gold_regression，scope=标准dataclass默认实例，evidence_refs=type_adapter:101–107,193–204/_config:268–286/default_schema:1011–1019，proposed_action=下述同条件窄对照，status=unconfirmed；③category=actor_environment_unknown，scope=真实actor，evidence_refs=P/environment_brief，proposed_action=任务二取得真实输入/工作树/开发命令证据，status=open。

唯一优先下一步：由任务二在隔离私有CPU环境，对同base与gold各跑一个公开API组合：标准库 @dataclasses.dataclass 的 D(x:int)，BaseModel M 含 d:D=D(1)，调用 M.model_json_schema()，记录是否有 default={'x':1}、warning、异常类型/code；并保留题面IPv4例作目标控制。该对照若base正常而gold抛type-adapter-config-unused，即把check26从unknown变为已证回归；若二者均可用，需收窄/撤销当前静态路径假设。无需全仓、GPU或模型实验。本轮只提出，不执行、不修改测试/gold/评分；私有容器不能交solver。

disposition={state:needs_review,scope:static_review}，reason=IP局部对照成立但通用默认编码疑点及actor条件未核；additional_exclusions=[]、revision_refs=[]；本轮token/费用/CPU成本为null。

## 运行原件附录（逐题独立，非旧质量结论）

### gold

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_3ef85fd4.eval.log`，SHA256=af642065b1e9a5f3d2ab4b028d453f626c7c8c3bbc3ebcb33d5e3b5b47980d1b（与run_refs一致）。
- run_id=er19-pyd1-pydantic__pydantic-9066-gold；开始=2026-09-19T06:43:29.311742+00:00；base/HEAD从精确baseline/stage指针核对。candidate={'apply_method': 'git_apply', 'apply_stderr_tail': None, 'apply_user': 'agent/54321', 'kind': 'gold', 'origin': '/work/full216_20260919/replay/gold/pydantic__pydantic-9066.gold.patch', 'patch_sha256': 'sha256:5bb189597da2acc269a026b887b1e7d4152c6fe24f60d253ce3c9fb309757fa4'}；projection={'frozen_patch_digest': 'sha256:43ba2f555cc80ec35f4935d8fda5fa9e7115df5b453f07ea932b93ab3269313d', 'ignored_paths': [], 'included_paths': ['pydantic/json_schema.py'], 'unsupported_shape_reasons': []}。
- 原始命令：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`；install={'install_rc_last_command': 0, 'install_seconds': 4.887, 'install_skipped': False, 'log_partial': False, 'markers_seen': ['RH2_INSTALL_RC', 'RH2_TEST_RC', 'RH2_TS_INSTALL_END', 'RH2_TS_INSTALL_START', 'RH2_TS_TEST_END', 'RH2_TS_TEST_START'], 'test_rc': 0, 'test_seconds': 7.231}；report={'execution_failure_evidence': [], 'execution_failure_stage': None, 'f2p_pass': 2, 'f2p_total': 2, 'failure_category': None, 'grader_version': 'swebench-4.1.0+swegym_parsers@242429c1', 'grading_semantics': 'swe_f2p_p2p', 'infra_failure_detail': None, 'outcome': 'resolved', 'p2p_fail': 0, 'p2p_total': 367, 'report_id': 'rpt_grading_3ef85fd4', 'reward': 1.0}；verdict={'apply_ok': True, 'num_parsed_outside_segment': 0, 'num_parsed_tests': 376, 'parser_source': 'swegym_parsers@242429c1', 'reference_missing': [], 'reference_skipped': [], 'resolution': 'RESOLVED_FULL'}。
- 实际逐行识别384个pytest状态身份；expected P2P 367项全部PASSED，未发现expected缺席/跳过。此机械状态核对不替代断言语义阅读。
- F2P `tests/test_json_schema.py::test_default_value_encoding[IPvAnyAddress-default_value1-expected_schema1]`：('PASSED', 1102)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_default_value_encoding[IPvAnyAddress-default_value0-expected_schema0]`：('PASSED', 1101)（状态、log行号）。
- 非通过的预期标记：[('tests/test_json_schema.py::test_literal_types', ('SKIPPED', 959)), ('tests/test_json_schema.py::test_get_pydantic_core_schema_calls', ('XFAIL', 1028))]；这些不在F2P/P2P expected内。
- source manifest expected=sha256:36a2143540442ceb905593fb572866b891c7acede914eda0db2ee86781fddc31；实际历史derived image ID=sha256:b12b48fbea360dc19ca0537495ef0b5d3e9a33f62712e561f570f5a63b84b5a1；derived recipe=pydantic-install-v1；scripts_digest=sha256:648caee82a20dab8ac54120d955b4200fd0270fc33aecd4196c2555265ffefe2；实际当前actor image ID=null。
- 原policy={'candidate_writable_prefixes': ['/opt/miniconda3/envs/testbed'], 'cpus': 2.0, 'grader_profile_digest': 'sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a', 'memory_bytes': 4294967296, 'network': 'deny_all', 'pids_limit': 512, 'profile_id': 'rh2.grader_sandbox_profile.v1', 'shm_bytes': 67108864, 'tmpfs_bytes': 1073741824, 'uid': 54322, 'user': 'rh2grader'}；budgets={'candidate_stage_seconds': 900.0, 'cleanup_seconds': 120.0, 'grading_deadline_seconds': 3600.0, 'image_pull_seconds': 1800.0}；resource原字段={'mem_peak_mb': 186.027, 'mem_peak_unavailable_or_zero': False}（不推断单位）；cleanup={'detail': '', 'removed': True, 'steps': ['rm:ok']}；observations={'RH2_OBS_IMPORT_PATH': '/testbed/pydantic/__init__.py', 'RH2_OBS_INSTALL_PROBE': 'absent', 'RH2_OBS_INSTALL_PROBE_PRE': 'absent', 'RH2_OBS_PKG_VERSION': '2.7.0a1', 'RH2_OBS_PREFIX_OWNER_PRE': '54322', 'RH2_OBS_RUNNER_DIGEST': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809', 'RH2_OBS_RUNNER_DIGEST_PRE': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809'}。

### noop

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_a93f65ea.eval.log`，SHA256=74b278392a27f141b56e0c94d117fb6c230c5a82680e947fd7b2b9139bb4bf8f（与run_refs一致）。
- run_id=er19-pyd1-pydantic__pydantic-9066-noop；开始=2026-09-19T06:42:57.240869+00:00；base/HEAD从精确baseline/stage指针核对。candidate={'apply_method': 'noop', 'apply_stderr_tail': None, 'apply_user': 'agent/54321', 'kind': 'noop', 'origin': 'noop', 'patch_sha256': None}；projection={'frozen_patch_digest': 'sha256:affd4998b4449a5b525cccc506126766fee3b09f06f1dc20c99ad0b1cd0fb183', 'ignored_paths': [], 'included_paths': [], 'unsupported_shape_reasons': []}。
- 原始命令：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`；install={'install_rc_last_command': 0, 'install_seconds': 4.834, 'install_skipped': False, 'log_partial': False, 'markers_seen': ['RH2_INSTALL_RC', 'RH2_TEST_RC', 'RH2_TS_INSTALL_END', 'RH2_TS_INSTALL_START', 'RH2_TS_TEST_END', 'RH2_TS_TEST_START'], 'test_rc': 1, 'test_seconds': 9.033}；report={'execution_failure_evidence': [], 'execution_failure_stage': None, 'f2p_pass': 0, 'f2p_total': 2, 'failure_category': 'tests_failed', 'grader_version': 'swebench-4.1.0+swegym_parsers@242429c1', 'grading_semantics': 'swe_f2p_p2p', 'infra_failure_detail': None, 'outcome': 'unresolved', 'p2p_fail': 0, 'p2p_total': 367, 'report_id': 'rpt_grading_a93f65ea', 'reward': 0.0}；verdict={'apply_ok': True, 'num_parsed_outside_segment': 0, 'num_parsed_tests': 376, 'parser_source': 'swegym_parsers@242429c1', 'reference_missing': [], 'reference_skipped': [], 'resolution': 'RESOLVED_NO'}。
- 实际逐行识别384个pytest状态身份；expected P2P 367项全部PASSED，未发现expected缺席/跳过。此机械状态核对不替代断言语义阅读。
- F2P `tests/test_json_schema.py::test_default_value_encoding[IPvAnyAddress-default_value1-expected_schema1]`：('FAILED', 1067)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_default_value_encoding[IPvAnyAddress-default_value0-expected_schema0]`：('FAILED', 1065)（状态、log行号）。
- 非通过的预期标记：[('tests/test_json_schema.py::test_literal_types', ('SKIPPED', 923)), ('tests/test_json_schema.py::test_get_pydantic_core_schema_calls', ('XFAIL', 992))]；这些不在F2P/P2P expected内。
- source manifest expected=sha256:36a2143540442ceb905593fb572866b891c7acede914eda0db2ee86781fddc31；实际历史derived image ID=sha256:b12b48fbea360dc19ca0537495ef0b5d3e9a33f62712e561f570f5a63b84b5a1；derived recipe=pydantic-install-v1；scripts_digest=sha256:648caee82a20dab8ac54120d955b4200fd0270fc33aecd4196c2555265ffefe2；实际当前actor image ID=null。
- 原policy={'candidate_writable_prefixes': ['/opt/miniconda3/envs/testbed'], 'cpus': 2.0, 'grader_profile_digest': 'sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a', 'memory_bytes': 4294967296, 'network': 'deny_all', 'pids_limit': 512, 'profile_id': 'rh2.grader_sandbox_profile.v1', 'shm_bytes': 67108864, 'tmpfs_bytes': 1073741824, 'uid': 54322, 'user': 'rh2grader'}；budgets={'candidate_stage_seconds': 900.0, 'cleanup_seconds': 120.0, 'grading_deadline_seconds': 3600.0, 'image_pull_seconds': 1800.0}；resource原字段={'mem_peak_mb': 233.578, 'mem_peak_unavailable_or_zero': False}（不推断单位）；cleanup={'detail': '', 'removed': True, 'steps': ['rm:ok']}；observations={'RH2_OBS_IMPORT_PATH': '/testbed/pydantic/__init__.py', 'RH2_OBS_INSTALL_PROBE': 'absent', 'RH2_OBS_INSTALL_PROBE_PRE': 'absent', 'RH2_OBS_PKG_VERSION': '2.7.0a1', 'RH2_OBS_PREFIX_OWNER_PRE': '54322', 'RH2_OBS_RUNNER_DIGEST': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809', 'RH2_OBS_RUNNER_DIGEST_PRE': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809'}。

原raw状态总数与ledger num_parsed_tests存在8项差值；未完整重读parser源解释这8项，但独立按verbose原行精确ID核对覆盖了所有expected，不能称expected缺失。不能用原总分覆盖目标失败；所有F2P失败均已检查异常或is_required断言位置。H只含单次noop与gold，不证明可重复性/模型能力。

## 实际阅读范围与未读范围

完整：本题计划prompt/public_bundle/base_identity/environment_brief/public_read、gold/test patch及grading/validation身份/expected/patch、run_refs/source_refs；environment_record定向读取身份、原运行和inventory定位。早期长JSON显示截断后按键核读，不称全部嵌套语义已审。

源码：json_schema.py:980–1046,1980–2018；type_adapter.py:95–113,144–240,298–350；networks.py:511–575；_std_types_schema.py:570–672；_generate_schema.py:1470–1566；_config.py:35–68,85–102,264–295；fields.py:400–439（确认本base已有字段修复）。旧测试：test_json_schema.py:1–106,1106–1220,1296–1368,1644–1766,1770–1857,4232–4278,4465–4505,5936–5997；test_networks_ipaddress.py:11–43,194–223,352–363；conftest.py:1–90并检索autouse。配置pyproject:44–71,99–135,155–181；docs/concepts/json_schema.md:254–303。test_dataclasses.py仅符号检索未读相应断言，不能算回归覆盖；未完整读其余tests。

原件：两run选定ledger第1行、diagnostics；candidate_test_script.after.sh与recipe.json全文、gold eval_script.after.sh全文；image.json全文；candidate.patch hash/内容比较；projection/baseline/stage只读授权指针。日志全许可区间机械核所有expected，人工读激活/安装/恢复/目标trace/收尾及初始diff语义改动；锁文件wheel hashes和未变context不算语义检查。image_inventory核身份/Python/packages与文件定位。未读冻结源码archive/完整manager/parser、未读项目HISTORY、未读history/reviewer或其他包/根结果。未重验实际actor工作树、工具权限、网络、资产或资源。
