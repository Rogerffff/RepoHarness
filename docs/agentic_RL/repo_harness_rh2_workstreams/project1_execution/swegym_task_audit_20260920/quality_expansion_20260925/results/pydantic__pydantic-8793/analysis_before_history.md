# pydantic__pydantic-8793 — 历史解封前独立分析

初判：公开核心目标明确，新增断言具有公开依据，原始 noop/gold 对照来自目标行为；可以作为开发诊断静态候选。实际 actor 输入、初态和开发工具链均 unknown，不能宣布运行资格。测试未穷尽 FieldInfo 的覆盖优先级与运行时缺值语义，未证 gold 新增回归，也未证明所有合理实现都不会误拒。

## 审查边界与证据等级

作者/by：main_pack12_pydantic（私有主审）。所有命令显式 workdir=/Users/roger/Desktop/claude-code-verl-stage0h。完整读取指定派发卡、investigator、record_template、check_number_reference、actor_environment_card、actor_development_validation 方法文件。仅访问本包两题 PUBLIC/PRIVATE、各自封存 public_read.md 和 run_refs/environment_record 精确授权原件；没有读取 history、reviewer、旧质量结论、其他包或根汇总。没有执行/导入项目、测试、安装、网络、容器、SSH、GPU、模型或子 agent；只做文件、JSON/hash 和静态源码阅读。前稿保存后不再改写，等待 root 明确 history release。

下文 P=本题 public 目录，Q=本题 private 目录；源码/旧测试行号相对 P/base，patch 行号相对 Q。原日志使用本题 run_refs 中的精确路径，末尾运行附录给出身份与行号。S=静态直接证据/推断；H=授权历史真实 RH2 原件；A=当前 actor，尚无观测。H 不替代 A。

## 1. 公开目标、版本与真实初态

题面要求 create_model 的 foo=(int, ...)、bar=(Annotated[int, Field(description=...)], ...)、baz=(Annotated[int, Field(..., description=...)], ...) 在 model_json_schema() 中得到 required=['foo','bar','baz']，类型、标题、描述保留。docs/concepts/models.md:1041–1066 将动态/静态模型等同，:1320–1345 明确 Ellipsis/Field(...) 的必填意义；fields.md:6–59 则要求真实 default/default_factory 语义不被破坏。题目不是指定某个内部算法。

P/base_identity.json 的 base_commit=832225b90672c68e2d4067bd0ffecf834d62b48b，tree=11e57c7275fdd5baa73461a82eeee828ea47e522，467 个跟踪条目；无导出的 gitlinks/LFS/软链缺口。此为静态导出声明，未重验全部 blob。Q/grading.json、validation.json 的 task/base 对应；其中 test_patch/golden_patch 与分离 patch 文件逐字比较一致。报告者 Python 3.11.7/core 2.16.2 与来源 grading.python_version=3.8 要分开；旧测试用 typing_extensions.Annotated，公开原例在 Python 3.8 直接从 typing 导入 Annotated 不兼容，后续公开等价复现需使用旧测试已使用的兼容导入，不能把这一导入差异当目标 bug。

历史 noop 日志 :132–140 的 git status 显示 pdm.lock、pyproject.toml 已修改；:141 的 git show 是基线提交展示，不是未提交 diff。真正 diff 从 :167 开始，pyproject :401–412 添加 pre-commit>=3.5.0；pdm.lock 升为 4.5.0、加入 metadata.targets、pre-commit 及 cfgv/distlib/identify/nodeenv/virtualenv、兼容依赖标记等（详见原件 :168–400）。这不是实际 actor 初态快照。原始来源规定改动、实际模型消息、准备后 status 的 RC/采集阶段、忽略资产均仍 unknown；不得把导出称为实际干净环境。

## 2. 根因链、gold 全部改动与调用者

fields.py:174–214 构造函数把 Ellipsis 归一为 PydanticUndefined，并检查 default/default_factory 冲突；:305–385 的 from_annotated_attribute 将外层 default 传入 merge_field_infos。:396–419 会展平 FieldInfo，单元素路径 copy 后直接 setattr，故外层 ... 留成真实 default=Ellipsis。main.py:1454–1497 与 _internal/_fields.py:200–237 把动态模型 tuple 输入送到同一条类字段路径。

is_required(:513–519) 要求 default is PydanticUndefined 且无工厂；_generate_schema.py:1074–1078,2067–2086 对非必填字段包 default core schema；json_schema.py:1435–1442,1467–1490 将 default schema 视为非必填，再由 :1244–1267 汇集 required。该静态链解释 foo 与 bar/baz 的差异；H 中前两项因 warning-as-error 在编码 Ellipsis 处失败，第三项 is_required 为 False，给出独立运行支持。

已读 gold 全部 7 行新增：仅改 fields.py 单 FieldInfo 合并路径；保留 copy 和 _attributes_set.update(overrides)，pop default，将 Ellipsis 转为 Undefined；只有实际非 Undefined 默认值才写回，其他 overrides 仍 setattr。它修复无内层默认值的题面路径，并保留数值/None 等真实 override。没有修改 JSON Schema、测试或评分。from_annotation、普通类、动态类及 dataclass 分支均会消费合并结果；通用影响不能只按 JSON 输出评估。

边界：若单 FieldInfo 原有 default=5，外层 ... 会在 gold 下保留 5，而多 FieldInfo 构造路径可能清空它；_attributes_set 仍记录 ...。公开 fields.md:58–59 说 Annotated 内 Field.default 不支持，但 test_merge_field_infos_type_adapter/model 明确使用 Field(3)，所以这有公开表述与既有测试之间的歧义，不能武断要求其中一种优先级。该组合新增测试未覆盖，记为规格/完整性待澄清，不称已证 gold 回归。浅 copy 后共享 _attributes_set 的已有行为也非本次新增，未做完整复用污染证明。

## 3. 需求—断言双向表与实际选择

新增 patch 完整读完：两处仅重排 import，无语义新增；三函数共 5 个 assert，无自定义 fixture/helper，使用标准 create_model/BaseModel/Field/Annotated（typing_extensions）与公共 model_json_schema/is_required。conftest:46–50 autouse 只禁错误 URL；pyproject:155–171 配置所有警告为错误、xfail_strict=true 与 benchmark 插件选项。

| 公开要求/合理旧行为 | 依据 | 测试 ID / 决定性断言 | 覆盖及强度 |
|---|---|---|---|
| 单 Annotated Field + 外层 ... 为必填，描述/整数类型保留 | 原例 bar、models 文档 | test_json_schema_annotated_with_field：完整 dict，required=['bar']，无 default | S 完整对应；H noop FAIL→gold PASS |
| foo/bar/baz 均必填，顺序及全部元数据保留 | 原例明确预期 | test_required_fields_in_annotated_with_create_model：完整 dict，required=['foo','bar','baz'] | S 完整对应；H FAIL→PASS |
| 等价普通类无默认字段仍必填，未知 Annotated 元数据不改变必填 | 动静等价文档；fields.py 共用路径 | test_required_fields_in_annotated_with_basemodel：a、b、c 三次 is_required() | S 合理扩展；H 仅 c 实际失败→PASS |
| 真 default、default_factory 可省略且元数据/alias/约束保留 | fields 文档；test_annotated:17–176、261–306、320–345 | P2P test_list_default、test_dict_default、test_model_default、test_nested_default_json_schema；相关 test_annotated 不在本题实际 selector | S/P2P 部分；Annotated 工厂与真实 override 未由新增测试针对 |
| 序列化 defaults_required 配置仍独立有效 | json_schema.field_is_required；旧测试 :5749–5761 | P2P test_json_schema_serialization_defaults_required | S/H 覆盖配置常规路径，不覆盖 Annotated 全组合 |
| 缺失必填值运行时应报 missing，有效输入仍接受 | required 语义；test_create_model_usage、test_annotated_instance_exceptions | 新增仅 schema/is_required；本题 selector 不含上述两个测试模块 | S 缺少目标运行时断言，不能由三个新增测试证明 validator 行为完整 |
| 内层真实 default 遇外层 ...、复用 FieldInfo | 文档/旧测试表述有差异；共享元数据机制 | 无针对新增断言；多 Field ordering 旧测试在别模块 | S 未定规格/覆盖空白，不升级为 gold 已破坏旧行为 |

反向检查：三项 hidden 断言均能回到原例、公开必填定义或动静等价；没有要求 patch 文件、内部 helper 调用次数或特定代码形状。完整 dict 会固定表面 schema 结构和 required 顺序，顺序虽不影响 JSON Schema 集合语义，但题面给出同样有序预期且既有 API 保持声明顺序；未见足以否决本题的误拒证据。合理非 gold 路线可在 FieldInfo 归一化/字段构建处实现相同公开行为，不必复制 gold；未实际执行替代解。只改 schema required 而不修字段状态会被第三项拒绝，有合理依据；仅修固定 bar/baz 名称可能被单 bar 与普通类发现，仍不能证明任意硬编码都被拦截。

P2P 语义阅读为风险抽样，不是 364 项全文：实际读了 test_json_schema 的 test_list_default、enum_str/int_default、dict_default、model_default、subfield_field_info、nested_default_json_schema、json_schema_serialization_defaults_required；全部 expected ID 的原日志状态另做机械对齐均 PASSED。其余 P2P 仅核身份/状态，未阅读全部断言。test_annotated.py 与 test_create_model.py 是重要公开旧行为依据，但没有进入实际 tests/test_json_schema.py 选择器。漏测属 check25，不等于 check26 已证回归。

## 4. 开发条件、合法交付、可信恢复与暴露

| 操作/资产 | 公开依据 | 已有条件证据/缺口 | 后续最小公开命令及预期（本轮未执行） |
|---|---|---|---|
| 真正 actor 输入、源码与初态 | P/user_prompt:1、public_hints、environment_brief | 只有计划消息/静态 base；历史 grader 有初始依赖改动 | 捕获消息；pwd、git rev-parse HEAD、git status --porcelain=v1、git diff；记录命令 RC 与准备前后阶段 |
| Python/依赖/源码生效 | pyproject:65–70、旧测试兼容 Annotated | H Python3.8/core2.16.2、editable /testbed；A 解释器/PATH/源码位置未知 | python -c 打印 sys.executable、pydantic.__file__、core.__version__；确认 actor checkout/core2.16.2 |
| 原例用户 API、必填与元数据 | 原例；fields/模型文档 | H 覆盖隐藏变体；A 无证据 | python - 内联原例（3.8 用 typing_extensions.Annotated），assert required，检查模型缺值 ValidationError；修前目标失败、修后通过 |
| 默认值/工厂及动静一致窄测试 | test_annotated、test_create_model | H 只跑 json_schema；A pytest/插件/临时文件权限未核 | python -m pytest -q tests/test_annotated.py；另单独 tests/test_create_model.py，预期相邻旧行为保留 |
| 安装/资产/网络 | pyproject testing/testing-extra、conftest 临时模块 | H wheelhouse+deny_all 下安装成功；A wheelhouse/可写前缀未知 | 实际 actor 窄测试确认 imports、缓存/临时目录可写；依赖预备后原例无需联网、GPU或模型权重 |
| 源码交付/可信测试 | public_hints NON-TEST；Q patch与原 recipe | H 仅 fields.py 投影，恢复 tests/test_json_schema.py，apply RC0 | 候选相对真实初态导出源码 diff；不将现有 pdm.lock/pyproject 变更错当 solver 补丁 |

H 的 eval_script 先 checkout 该 base 的 tests/test_json_schema.py 再 apply test.patch；原 diagnostics RH2_SETUP_APPLY_RC=0、RESTORED=1、EXPECTED_TEST_FILES=1、ABSENT=0、PROTECT_OK=1，candidate 无测试路径。仅支持该原对照的恢复/投影；未完整审计当前 manager、恶意候选控制面或当前 actor 权限。原 install 从 pdm add pre-commit; make install 改为 editable pip + 候选 testing/testing-extra 元数据，未改题目行为断言，不能把旧安装配方的所有问题视为仍存在，也不推导 A 已修。

审查者已见本题 gold、隐藏测试、expected、授权 H 原件及 public_read，因此 usage.intended_use=development_diagnostic，材料不能提供给独立 solver。check29 的 actual actor 泄露仍 unknown；网络是否可取得未来答案未查。与 9066 的关系：后者本题允许 base 中已有这三项测试和相同字段修复，是后续版本依赖关系，非同一目标或同一 gold；不得据此推断其他池重叠、去重或正式划分资格。

## 5. 初判检查、问题与唯一优先下一步

| check | status | evidence_refs / 边界 | by |
|---|---|---|---|
| 1,2 | pass | P/base_identity、Q patches/expected、H binding/逐F2P，仅材料与原运行范围 | main_pack12_pydantic |
| 3,8,10,33 | unknown | P/environment_brief；A消息/权限/开发入口未捕获 | main_pack12_pydantic |
| 4,16,17,18,19,20,21 | pass | NON-TEST计划范围；H单源码投影、可信恢复、目标RC和expected对齐；只限所引用H | main_pack12_pydantic |
| 6,7,11,13 | unknown | H修订配方成功是局部证据，A依赖/资产/资源仍未知 | main_pack12_pydantic |
| 23 | pass | 原例与必填定义一致；内外default组合歧义保留 | main_pack12_pydantic |
| 24 | unknown | S未见强制gold路径；未执行替代解，不保证普遍无误拒 | main_pack12_pydantic |
| 25 | issue | 目标运行时缺值、Annotated默认值/工厂组合无针对隐藏覆盖 | main_pack12_pydantic |
| 26 | unknown | 无本轮/已核H反例证明gold新回归 | main_pack12_pydantic |
| 27 | unknown | 题面局部S/H正证据充分，完整性未证明 | main_pack12_pydantic |
| 28 | pass | 建议区分公开要求与审查风险；未增生产要求 | main_pack12_pydantic |
| 29,30,31,35,36,38,39,40 | unknown | actor暴露/控制面、真实解、适用性、复验及跨题影响/漏检偏差均未证毕 | main_pack12_pydantic |

未列编号为 not_checked。issues：① category=coverage，scope=目标运行时及FieldInfo边界，evidence_refs=上述双向表，proposed_action=后续解答审查保留公开旧行为，不凭F2P全过认定完整，status=open；② category=actor_environment_unknown，scope=实际actor，evidence_refs=P/environment_brief及H/A区分，proposed_action=取得实际开发证据，status=open。default覆盖歧义是①的具体限制，不另造不可解结论。

唯一优先下一步：由任务二在正式 actor 身份核验原例公共 API（含缺值校验）的导入/运行与实际初态；该步骤能改变“仅H可运行、A未知”的当前判断。内层 Field(5)+... 缺乏明确一致规格，现阶段不为它机械追加CPU；保留语义疑义供后续解释。disposition={state:needs_review, scope:static_review}，reason=静态候选待actor验证、有限覆盖；additional_exclusions=[]，revision_refs=[]；token/费用/本轮CPU成本均 null。

## 运行原件附录（逐题独立，非旧质量结论）

### gold

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8793/gold/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8793/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_cec5f167.eval.log`，SHA256=176d846e9cb287423e9215e277bde6fb1ca645c63591389193b9c5df64f70634（与run_refs一致）。
- run_id=er19-pyd1-pydantic__pydantic-8793-gold；开始=2026-09-19T06:41:19.816042+00:00；base/HEAD从精确baseline/stage指针核对。candidate={'apply_method': 'git_apply', 'apply_stderr_tail': None, 'apply_user': 'agent/54321', 'kind': 'gold', 'origin': '/work/full216_20260919/replay/gold/pydantic__pydantic-8793.gold.patch', 'patch_sha256': 'sha256:db816cd4802bd14e7428d09fff82141fdb3a2ee631a7fe3b809a12f701df273e'}；projection={'frozen_patch_digest': 'sha256:e22994e0ef14da4c5a2a3a761762f4a304318452c1733726807fc905b003edc0', 'ignored_paths': [], 'included_paths': ['pydantic/fields.py'], 'unsupported_shape_reasons': []}。
- 原始命令：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`；install={'install_rc_last_command': 0, 'install_seconds': 4.678, 'install_skipped': False, 'log_partial': False, 'markers_seen': ['RH2_INSTALL_RC', 'RH2_TEST_RC', 'RH2_TS_INSTALL_END', 'RH2_TS_INSTALL_START', 'RH2_TS_TEST_END', 'RH2_TS_TEST_START'], 'test_rc': 0, 'test_seconds': 7.26}；report={'execution_failure_evidence': [], 'execution_failure_stage': None, 'f2p_pass': 3, 'f2p_total': 3, 'failure_category': None, 'grader_version': 'swebench-4.1.0+swegym_parsers@242429c1', 'grading_semantics': 'swe_f2p_p2p', 'infra_failure_detail': None, 'outcome': 'resolved', 'p2p_fail': 0, 'p2p_total': 364, 'report_id': 'rpt_grading_cec5f167', 'reward': 1.0}；verdict={'apply_ok': True, 'num_parsed_outside_segment': 0, 'num_parsed_tests': 374, 'parser_source': 'swegym_parsers@242429c1', 'reference_missing': [], 'reference_skipped': [], 'resolution': 'RESOLVED_FULL'}。
- 实际逐行识别382个pytest状态身份；expected P2P 364项全部PASSED，未发现expected缺席/跳过。此机械状态核对不替代断言语义阅读。
- F2P `tests/test_json_schema.py::test_required_fields_in_annotated_with_create_model`：('PASSED', 1091)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_json_schema_annotated_with_field`：('PASSED', 1090)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_required_fields_in_annotated_with_basemodel`：('PASSED', 1092)（状态、log行号）。
- 非通过的预期标记：[('tests/test_json_schema.py::test_literal_types', ('SKIPPED', 951)), ('tests/test_json_schema.py::test_get_pydantic_core_schema_calls', ('XFAIL', 1020))]；这些不在F2P/P2P expected内。
- source manifest expected=sha256:bdd9a2ddbca3a265f115d7f704eff78d39282f38d5be34bb8e338b717cc41b5c；实际历史derived image ID=sha256:3ed9b0685fbbd4dbbefcee77ac6c80f3f58b41d8e0722f54bc58c98267c5b0ed；derived recipe=pydantic-install-v1；scripts_digest=sha256:d035288b46cb26f6bf90cd1dda959bb9ee44bc10a92edb4887f372f8b9542506；实际当前actor image ID=null。
- 原policy={'candidate_writable_prefixes': ['/opt/miniconda3/envs/testbed'], 'cpus': 2.0, 'grader_profile_digest': 'sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a', 'memory_bytes': 4294967296, 'network': 'deny_all', 'pids_limit': 512, 'profile_id': 'rh2.grader_sandbox_profile.v1', 'shm_bytes': 67108864, 'tmpfs_bytes': 1073741824, 'uid': 54322, 'user': 'rh2grader'}；budgets={'candidate_stage_seconds': 900.0, 'cleanup_seconds': 120.0, 'grading_deadline_seconds': 3600.0, 'image_pull_seconds': 1800.0}；resource原字段={'mem_peak_mb': 201.805, 'mem_peak_unavailable_or_zero': False}（不推断单位）；cleanup={'detail': '', 'removed': True, 'steps': ['rm:ok']}；observations={'RH2_OBS_IMPORT_PATH': '/testbed/pydantic/__init__.py', 'RH2_OBS_INSTALL_PROBE': 'absent', 'RH2_OBS_INSTALL_PROBE_PRE': 'absent', 'RH2_OBS_PKG_VERSION': '2.7.0a1', 'RH2_OBS_PREFIX_OWNER_PRE': '54322', 'RH2_OBS_RUNNER_DIGEST': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809', 'RH2_OBS_RUNNER_DIGEST_PRE': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809'}。

### noop

- ledger：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8793/noop/ledger.jsonl:1`；log：`runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-8793/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_8fa63264.eval.log`，SHA256=a4973021409fca874461057e2274d9cd8b15150cf1bcc08b2e558b612599c8a5（与run_refs一致）。
- run_id=er19-pyd1-pydantic__pydantic-8793-noop；开始=2026-09-19T06:40:47.418700+00:00；base/HEAD从精确baseline/stage指针核对。candidate={'apply_method': 'noop', 'apply_stderr_tail': None, 'apply_user': 'agent/54321', 'kind': 'noop', 'origin': 'noop', 'patch_sha256': None}；projection={'frozen_patch_digest': 'sha256:e6beea038dfb08445559010ef737829bebeffdb53b0cb59003e976ae40f558f3', 'ignored_paths': [], 'included_paths': [], 'unsupported_shape_reasons': []}。
- 原始命令：`pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`；install={'install_rc_last_command': 0, 'install_seconds': 4.987, 'install_skipped': False, 'log_partial': False, 'markers_seen': ['RH2_INSTALL_RC', 'RH2_TEST_RC', 'RH2_TS_INSTALL_END', 'RH2_TS_INSTALL_START', 'RH2_TS_TEST_END', 'RH2_TS_TEST_START'], 'test_rc': 1, 'test_seconds': 8.293}；report={'execution_failure_evidence': [], 'execution_failure_stage': None, 'f2p_pass': 0, 'f2p_total': 3, 'failure_category': 'tests_failed', 'grader_version': 'swebench-4.1.0+swegym_parsers@242429c1', 'grading_semantics': 'swe_f2p_p2p', 'infra_failure_detail': None, 'outcome': 'unresolved', 'p2p_fail': 0, 'p2p_total': 364, 'report_id': 'rpt_grading_8fa63264', 'reward': 0.0}；verdict={'apply_ok': True, 'num_parsed_outside_segment': 0, 'num_parsed_tests': 374, 'parser_source': 'swegym_parsers@242429c1', 'reference_missing': [], 'reference_skipped': [], 'resolution': 'RESOLVED_NO'}。
- 实际逐行识别382个pytest状态身份；expected P2P 364项全部PASSED，未发现expected缺席/跳过。此机械状态核对不替代断言语义阅读。
- F2P `tests/test_json_schema.py::test_required_fields_in_annotated_with_create_model`：('FAILED', 1073)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_json_schema_annotated_with_field`：('FAILED', 1071)（状态、log行号）。
- F2P `tests/test_json_schema.py::test_required_fields_in_annotated_with_basemodel`：('FAILED', 1075)（状态、log行号）。
- 非通过的预期标记：[('tests/test_json_schema.py::test_literal_types', ('SKIPPED', 932)), ('tests/test_json_schema.py::test_get_pydantic_core_schema_calls', ('XFAIL', 1001))]；这些不在F2P/P2P expected内。
- source manifest expected=sha256:bdd9a2ddbca3a265f115d7f704eff78d39282f38d5be34bb8e338b717cc41b5c；实际历史derived image ID=sha256:3ed9b0685fbbd4dbbefcee77ac6c80f3f58b41d8e0722f54bc58c98267c5b0ed；derived recipe=pydantic-install-v1；scripts_digest=sha256:d035288b46cb26f6bf90cd1dda959bb9ee44bc10a92edb4887f372f8b9542506；实际当前actor image ID=null。
- 原policy={'candidate_writable_prefixes': ['/opt/miniconda3/envs/testbed'], 'cpus': 2.0, 'grader_profile_digest': 'sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a', 'memory_bytes': 4294967296, 'network': 'deny_all', 'pids_limit': 512, 'profile_id': 'rh2.grader_sandbox_profile.v1', 'shm_bytes': 67108864, 'tmpfs_bytes': 1073741824, 'uid': 54322, 'user': 'rh2grader'}；budgets={'candidate_stage_seconds': 900.0, 'cleanup_seconds': 120.0, 'grading_deadline_seconds': 3600.0, 'image_pull_seconds': 1800.0}；resource原字段={'mem_peak_mb': 228.887, 'mem_peak_unavailable_or_zero': False}（不推断单位）；cleanup={'detail': '', 'removed': True, 'steps': ['rm:ok']}；observations={'RH2_OBS_IMPORT_PATH': '/testbed/pydantic/__init__.py', 'RH2_OBS_INSTALL_PROBE': 'absent', 'RH2_OBS_INSTALL_PROBE_PRE': 'absent', 'RH2_OBS_PKG_VERSION': '2.7.0a1', 'RH2_OBS_PREFIX_OWNER_PRE': '54322', 'RH2_OBS_RUNNER_DIGEST': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809', 'RH2_OBS_RUNNER_DIGEST_PRE': 'd5eb18bb38fd14ad32a6fa0b27231b03753e9c31921a29f55abea680d363d809'}。

原raw状态总数与ledger num_parsed_tests存在8项差值；未完整重读parser源解释这8项，但独立按verbose原行精确ID核对覆盖了所有expected，不能称expected缺失。不能用原总分覆盖目标失败；所有F2P失败均已检查异常或is_required断言位置。H只含单次noop与gold，不证明可重复性/模型能力。

## 实际阅读范围与未读范围

完整：本题计划prompt、public_bundle、base_identity、environment_brief、public_read；Q gold/test patch、grading/validation的身份/expected/patch、run_refs/source_refs，environment_record的身份/运行引用；中性方法卡。较大的JSON早期显示曾截断，之后逐键定向核读，不把未显示字段宣称为语义阅读。

源码实际区段：fields.py:155–215,245–435,500–525；main.py:1440–1501；_internal/_fields.py:190–240；_generate_schema.py:1064–1088,2067–2100；json_schema.py:1244–1278,1426–1494。旧测试：test_annotated.py:1–180,250–345；test_create_model.py:20–48,267–297；test_json_schema.py:1659–1742,2659–2694,4474–4504,5748–5778；conftest.py:1–90。文档：fields.md:1–60，models.md:1041–1066,1320–1345。配置pyproject:44–71,99–135,155–181。全部新断言在Q/test.patch完整读。

原件：两run ledger选定第1行，diagnostics；各candidate_test_script.after.sh与recipe.json全文；gold eval_script.after.sh全文；image.json全文；candidate.patch hash/原件比较；projection/baseline/stage只读授权指针。日志按run_refs本题完整许可区间做状态扫描，人工阅读激活、安装、可信恢复、目标失败和收尾；初始diff读语义变更，wheel文件hash/大量未变context不作语义审计。image_inventory只核身份、Python、packages及pyproject定位。没有解包/读取冻结源码archive、没有读取完整manager/parser、全部P2P正文、项目HISTORY、锁文件全本、未授权历史。source_refs定位不等于读取共享汇总。
