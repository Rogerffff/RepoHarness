# pydantic__pydantic-9066 reviewer initial — 2026-09-25

审查者：e25_review_pack12_pydantic。阶段：initial；尚未读取 public_read、主审稿、history/旧质量结论、根汇总或其他题。只执行静态文件读取、stdlib JSON/AST/hash；未执行/导入项目、测试、安装、网络、容器、SSH 或模型；未派生 agent。

证据简称：P=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066`；Q=`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066`；B=`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925`。源码行号均相对于 P/base；T=Q/test.patch，G=Q/gold.patch。

独立初判：公开 IPvAnyAddress 默认值问题与两项新测试匹配，gold 有目标修复的历史正证据；但它把所有无 __pydantic_serializer__ 的默认值都交给带 config 的 TypeAdapter，普通 stdlib dataclass 默认实例存在具体的未验证异常路径。保留 needs_review，优先作该小范围 base/gold 对照，不能以 367 项 P2P 全通过宣告完整无回归。

题面标题“IPv4Address not parsed”容易被误读为字段输入验证；正文实际是 model_json_schema() 报 non-serializable-default 并丢弃默认值。合理目标是将 IPv4 默认对象编码为 JSON 字符串并保留 default；IPv6 是 IPvAnyAddress 同一公开 API 的合理延伸。题面报告 2.6.2/core 2.16.3/Python 3.11，材料为 2.7 开发基线，历史 grader Python 3.8/core 2.16.3。

需求—断言双向表（T=test.patch；G=gold.patch；测试均位于 tests/test_json_schema.py）：

| 公开需求/既有合理行为 | 决定性断言/测试 | 覆盖及边界 |
| --- | --- | --- |
| IPv4 默认值可进入 JSON schema，类型格式保持 | F2P test_default_value_encoding[IPvAnyAddress-default_value0-expected_schema0]：完整 schema 默认 '127.0.0.1'，format ipvanyaddress，title/type 保留，无 required | 直接覆盖正文；未单独 assert warnings，但 pytest filterwarnings=error 会捕获目标 warning |
| IPvAnyAddress 的 IPv6 默认同样正确 | F2P test_default_value_encoding[IPvAnyAddress-default_value1-expected_schema1]：default='::1' 的完整 schema | API 对称扩展合理；非隐藏特定内部实现要求 |
| 无默认时的 IP schema 不变 | P2P test_ipv4address_type/test_ipv6address_type/test_ipvanyaddress_type:1106–1142 | 检查格式、type、required；不检查默认值 |
| 已有不可编码值仍 warning/省略，schema 继续生成 | P2P callable 与 non_serializable_default:1223–1391（其中辅助分支全读） | 避免所有值盲目 str；未覆盖 TypeAdapter 抛 PydanticUserError 的新路径 |
| list/dict/enum/model 默认值及内嵌别名保持 | P2P test_list_default 至 test_model_default:1644–1724；test_nested_default_json_schema:4465–4489 | 已读具体断言；不代表任何容器类型/子类/任意实例都覆盖 |
| bytes/timedelta 的配置生效 | P2P model/dataclass/TypedDict default tests:1727–1852 | 实际默认值是 bytes 或 timedelta；这些“dataclass”测试不是 dataclass 实例作为另一个字段的默认值 |
| namedtuple 默认值保持数组 | P2P test_namedtuple_default:3264–3286 | 已读并核日志 PASSED；不覆盖 stdlib dataclass 默认实例 |
| stdlib dataclass 被模型支持 | base docs/concepts/dataclasses.md:242–264；test_nested_python_dataclasses:4232–4267 | 支持类型与普通嵌套 schema，有明确合理行为来源；无默认实例的测试不能检验本次疑点 |

八方面复核：

1. 题意：不是要求新解析 IPv4 验证器；公开例子已经构造了地址。保留 default 且不发目标 warning 即可。测试 schema 等值要求正常格式，未见超出公开意图的结构限制。
2. 断言/helper：完整读 T：一个参数化测试、IPv4/IPv6 两组常量期望、一条完整 schema assert，没有私有 helper/fixture。读 json_schema.py default_schema:995–1026、encode_default:1985–2001、_config:301–303，以及 TypeAdapter.__init__:152–220、dump_python:320–347、_type_has_config:101–107。IP serializer 在 _std_types_schema.py:582–602 明确使用 to_string_ser_schema。
3. 漏测/误拒：仅两个固定地址，不能证明其他地址、直接 IPv4Address 注解、容器里的 IP、runtime validate/dump、其他默认类型。IP 专门处理/通用序列化修复都是合理非 gold 路线；测试不强制 TypeAdapter。扩展到任意未知对象 str 会与旧 non_serializable_default 断言冲突，这是有意义的回归约束。未发现当前测试误拒正确公开解的具体实例。
4. Gold/相关调用者：完整 G 只改 json_schema.py import 和 encode_default。已有 serializer 的对象保持旧 to_jsonable_python 路线，其余按 type(dft) 构造 TypeAdapter(...,config=config.config_dict)，dump_python(mode='json') 再转换；PydanticSchemaGenerationError 被改成 PydanticSerializationError，供 default_schema 发 warning。目标地址有 string serializer，历史 F2P 通过支持局部正确。
5. 具体回归疑点：stdlib dataclass 实例通常没有 __pydantic_serializer__，而 TypeAdapter 的 _type_has_config 对任何 is_dataclass(type) 为 True；只要 config 非 None（ConfigWrapper.prepare_config(None) 返回空 ConfigDict，见 _config.py:268–286），__init__:197–204 就抛 PydanticUserError(code='type-adapter-config-unused')。G 只 catch PydanticSchemaGenerationError，调用者又只 catch PydanticSerializationError，故该异常很可能外泄。读 _generate_schema.py:1474–1568：普通 dataclass 分支 collect 字段并返回定义引用，未在此为类设置 serializer；因此不能凭文档“自动转换”一句认定 guard 必然避开。尚未运行 base/gold、未读取 core 实现，不能把这个静态强疑点记为已证 gold 新增回归；check26 保持 unknown。目标测试/P2P 都没有覆盖这个交叉情形，因此 check25 可记录 coverage issue。
6. 原运行/评分：下方原件对照逐 ID 确认两个 F2P FAILED→PASSED，367 个 expected P2P 在两个角色均 PASSED。参考状态未跳过、不缺失；本题全文件实际 384 项有一 skip 一 xfail，不以“全绿”替代真实状态。P2P 大集合仅按表中高风险区段语义复核。
7. 开发环境/边界：需要 pydantic 可编辑工作区、core 2.16.3、typing_extensions、pytest 与配置要求的 benchmark 插件；本题公开流程无需网络服务/数据集/权重。历史安装+import 仅对 rh2grader 有效，actual actor 初态/权限/消息及工具条件 unknown。审查者已接触 gold、隐藏测试和历史运行原件，不能传给独立 solver；没有以共享工作区冒充 OS 隔离。
8. 适用性：公开目标规模适合诊断，但 gold 普适性有具体未解问题。未验证模型工作流、解题成功、训练价值、重复性或任意候选控制面攻击。封存规范不能证明筛查无遗漏/误拒/抽样偏差。

唯一优先下一步：交任务二在隔离私有 base/gold 环境，通过公开 BaseModel.model_json_schema API 对照一个 stdlib dataclass 默认实例，记录返回 schema、warnings、异常类型/栈、RC、代码导入来源及同条件差异。构造 `@dataclasses.dataclass class D: x:int`，`class M(BaseModel): d:D = D(1)`；预期合理行为是产生 d 的 default={'x':1}。若 base 成功且 gold 抛 type-adapter-config-unused，就可把疑点提升为已证 gold 回归；若两者表现相同或类型已带 serializer，按事实收窄/撤销。这个具体 CPU 对照会改变判断，不需要全仓或额外模型探针。本 reviewer 没有执行该代码。

开发需求表：

| 操作/资产 | 公开依据 | 已有证据适用于谁 | 缺口/最小命令及预期 |
| --- | --- | --- | --- |
| 导入实际工作区代码 | 题面 BaseModel + IPvAnyAddress | 历史 grader /testbed/pydantic/__init__.py | actual actor 解释器/包来源、HEAD/status/diff/可写权限待核 |
| 公开 IP 复现 | user_prompt 全例 | 2 项 F2P 历史等价实现 | `python` 执行原例；base warning+缺 default，修后字符串 default 且无目标 warning |
| dataclass 交叉默认值 | 公开 dataclass 支持 + 本题默认值编码接口 | 仅静态调用链 | 上述唯一优先私有 base/gold 对照；不能把探针/gold 送 solver |
| 旧默认值窄测试 | base test_json_schema.py 所列 P2P | 历史文件执行已通过 | actor 可用性验证时可选 `python -m pytest tests/test_json_schema.py -k 'default or ipv'`，不可只 collect-only |

原运行证据与版本：

- base_commit `a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7`；公开 source tag `xingyaoww/sweb.eval.x86_64.pydantic_s_pydantic-9066:latest`；expected source manifest `sha256:36a2143540442ceb905593fb572866b891c7acede914eda0db2ee86781fddc31`。source image 历史 inventory ID `sha256:5a05759a5549cc7d65c471fb5d57d8fc554485b6c178a389a1fd373111ff3f4d` 仅为 Q/environment_record.json 转录；当前 actor image ID=null。
- 原安装命令 `export PATH="$HOME/.local/bin:$PATH"; pdm add pre-commit; make install;` 被 pydantic-install-v1 改为 `python -m pip install -e .` 后按 pyproject testing/testing-extra 生成 requirements，再 `python -m pip install -r /tmp/rh2-envrepair-testing-reqs.txt`。已读两角色配方差异、gold after 全文、build.log/image.json；派生镜像保留基础层并加 build-wheels，设置 PIP_NO_INDEX=1/PIP_FIND_LINKS。原 make 路径本次未重跑，不能推断当前已修好。
- 两角色日志均先 source activate、conda activate testbed；测试命令均为 `pytest -rA --tb=short -vv -o console_output_style=classic --no-header tests/test_json_schema.py`。运行安装后导入 /testbed/pydantic/__init__.py、版本 2.7.0a1；Python 3.8 site-packages/pytest 7.4.4。无安装失败；目标 warning 因公开 pytest filterwarnings=error 成为测试失败。
- gold: `runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/ledger.jsonl:1`；原日志 `runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_3ef85fd4.eval.log:1–1118`。安装 RC=0，test RC=0；F2P=2/2，P2P失败=0/367。actual derived image `sha256:b12b48fbea360dc19ca0537495ef0b5d3e9a33f62712e561f570f5a63b84b5a1`，scripts_digest `sha256:648caee82a20dab8ac54120d955b4200fd0270fc33aecd4196c2555265ffefe2`。
- noop: `runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/ledger.jsonl:1`；原日志 `runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_a93f65ea.eval.log:1–1237`。安装 RC=0，test RC=1；F2P=0/2，P2P失败=0/367。actual derived image `sha256:b12b48fbea360dc19ca0537495ef0b5d3e9a33f62712e561f570f5a63b84b5a1`，scripts_digest `sha256:648caee82a20dab8ac54120d955b4200fd0270fc33aecd4196c2555265ffefe2`。
- 逐 ID 机械匹配 F2P/P2P 到原日志终态，没有 missing/skip 的 expected 项。本题实际 384 collected：noop 380 passed+2 failed，gold 382 passed；各角色还各有 test_literal_types SKIPPED（Python 3.8 ListEnum）及 test_get_pydantic_core_schema_calls XFAIL（重复调用 hook），无 XPASS。parser 记录 376 个身份，与 pytest 展开数不同；expected 身份全部定位已核，不将 parsed 数当全覆盖证明。
- no-op 原日志:1065–1211：IPv4 和 IPv6 测试分别在 encode_default 序列化未知类型后由 warning 异常失败；不是地址输入验证失败。gold:1108–1115 记录最终 382 passed/RC0。
- 历史 `git status` 位于各日志:132–140，noop 在测试恢复前已有 pdm.lock、pyproject.toml 改动。已核 diff 内容：pyproject 加 pre-commit>=3.5.0，lock 升 4.5.0、改 targets/hash，新增 cfgv/distlib/identify/nodeenv/pre-commit/virtualenv 与依赖约束；lock 只做元数据风险抽查，未逐 wheel hash 语义审计。`git show` 后的 HISTORY.md（8793）或 docs/concepts/models.md（9066）是基线提交展示，不能当成未提交改动。actual actor 准备后 status/diff/忽略资产仍 unknown。
- 已按 run_refs 指针核 baseline.task_base_commit/materialized_head、stage.head/apply_method、projection physical attempt/frozen digest/included paths：noop 无候选路径，gold 分别只有 pydantic/fields.py 或 pydantic/json_schema.py；gold 原 patch SHA 与 Q/validation 对应。每个原 ledger/log/diagnostics SHA256 已重新计算匹配引用。测试还原+patch apply RC0；diagnostics RH2_SETUP_OK=1、RH2_PROTECT_OK=1、runner_integrity_changed=false，cleanup removed=true。控制面抗攻击/任意候选完整交付未独立证明。
- 历史角色 rh2grader UID54322，candidate apply 标 agent/54321；network=deny_all、cpus=2.0、memory_bytes=4294967296、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824；不换算未核资源单位。source snapshot 和 archive 仅使用 Q/environment_record 转录的定位/digest，未读 archive 内容、不以其证明当前实现相同。共享入口仅读取授权 run_pydantic.py:10,43–45 与 replay_with_install_recipe.py:14–17,96；未跟随 prepared-summary 扩读。

阅读完整性：全部公开题面、bundle/base_identity/environment_brief；Q 的 source_refs/grading/validation/test/gold/run_refs/environment_record；完整新增断言及上述调用链；原件阅读范围如上。两次较大工具输出发生截断，决定性 patch、失败尾段、配方、P2P 风险段已用较小读取补齐。未通读 tests/test_json_schema.py 其余区段；不宣称 364/367 项 P2P 语义全部阅读。未读其他测试全仓、core Rust 实现、actual actor 或历史质量结论。

结构化静态记录（13 个顶层字段；未列 checks 为 not_checked）：

```json
{
  "task_id": "pydantic__pydantic-9066",
  "task_revision": {
    "base_commit": "a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7",
    "gold_sha256": "5bb189597da2acc269a026b887b1e7d4152c6fe24f60d253ce3c9fb309757fa4",
    "test_patch_sha256": "762cd93f859d6ef4f79b233e7b0e3019a8ccd9b417f13301467180b1082f6222"
  },
  "source_adapter_ref": {
    "schema": "rh2.private_grading_bundle.v2",
    "vendor": "swegym_constants_242429c1",
    "refs": [
      "Q/source_refs.json",
      "Q/grading.json"
    ]
  },
  "recipe_ref": [
    "Q/run_refs.json#/0/recipe_and_override_originals",
    "Q/run_refs.json#/1/recipe_and_override_originals"
  ],
  "code_snapshot_ref": [
    "P/base_identity.json",
    "Q/environment_record.json#/historical_code_snapshot (locator only)"
  ],
  "facts_ref": [
    "runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/ledger.jsonl:1",
    "runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/ledger.jsonl:1",
    "runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_3ef85fd4.eval.log",
    "runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-9066/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_a93f65ea.eval.log"
  ],
  "checks": {
    "1": {
      "status": "pass",
      "evidence_refs": [
        "P/base_identity.json；Q/validation.json、grading.json、run_refs.json：静态包及本题历史绑定相符；当前 actor 版本仍未知"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "2": {
      "status": "pass",
      "evidence_refs": [
        "G；原 noop.log 目标失败段：对应历史 base 确含目标错误"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "3": {
      "status": "unknown",
      "evidence_refs": [
        "P/environment_brief.md：仅计划 prompt；实际消息未获"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "4": {
      "status": "unknown",
      "evidence_refs": [
        "P/public_bundle.json：声明 bash/edit 和非测试提交；实际权限未获"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "6": {
      "status": "pass",
      "evidence_refs": [
        "历史 recipe/image/build/ledger：匹配依赖在该配方下可恢复；仅历史 grader"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "7": {
      "status": "unknown",
      "evidence_refs": [
        "P/pyproject.toml；本题无额外服务需求，actual actor 资产未验"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "8": {
      "status": "unknown",
      "evidence_refs": [
        "历史 rh2grader 非 actor"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "9": {
      "status": "pass",
      "evidence_refs": [
        "历史 ledger observations + projection/stage：目标源码及gold绑定局部证据"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "10": {
      "status": "unknown",
      "evidence_refs": [
        "开发需求表；actor shell/权限未验"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "18": {
      "status": "pass",
      "evidence_refs": [
        "本题两角色日志及逐 expected 身份映射；范围限本文件"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "19": {
      "status": "pass",
      "evidence_refs": [
        "Q/grading.json + 原日志：全部 expected 对应，skip/xfail不在expected"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "20": {
      "status": "pass",
      "evidence_refs": [
        "noop目标失败与gold通过同配方对照"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "21": {
      "status": "pass",
      "evidence_refs": [
        "原日志失败栈、安装RC和testRC分开；无重试隐藏"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "23": {
      "status": "pass",
      "evidence_refs": [
        "P/user_prompt.txt 与需求—断言表：公开目标可推断"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "24": {
      "status": "pass",
      "evidence_refs": [
        "T：只查公共schema/is_required，不绑定内部方案"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "25": {
      "status": "issue",
      "evidence_refs": [
        "需求—断言表及漏测讨论：有限断言不能验证所有runtime/其他默认类型"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "26": {
      "status": "unknown",
      "evidence_refs": [
        "G与相关调用者静态复核；未做新base/gold回归对照"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "27": {
      "status": "unknown",
      "evidence_refs": [
        "目标修复有局部静态/历史正证据，完整性未证"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "28": {
      "status": "pass",
      "evidence_refs": [
        "只将公开/既有行为用作诊断，不私设正式评分要求"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "29": {
      "status": "unknown",
      "evidence_refs": [
        "actual actor可见内容未知；审查私有暴露另见usage"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "31": {
      "status": "unknown",
      "evidence_refs": [
        "diagnostics保护/runner digest仅局部证据，未做任意候选攻击审计"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "33": {
      "status": "unknown",
      "evidence_refs": [
        "无真实CC工作流事实"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "35": {
      "status": "unknown",
      "evidence_refs": [
        "无真实模型已通过解"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "37": {
      "status": "pass",
      "evidence_refs": [
        "已读before/after安装差异；历史修改是依赖安装路径，test patch不变"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "38": {
      "status": "unknown",
      "evidence_refs": [
        "配方可追溯但本轮未干净复验"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "40": {
      "status": "unknown",
      "evidence_refs": [
        "独立阶段封存与风险抽样不证明无漏检/误拒/偏差"
      ],
      "by": "e25_review_pack12_pydantic"
    }
  },
  "issues": [
    {
      "category": "actor_evidence_gap",
      "scope": "current actor messages/worktree/permissions/development",
      "evidence_refs": [
        "P/environment_brief.md",
        "Q/environment_record.json",
        "开发需求表"
      ],
      "proposed_action": "任务二按正式入口核对实际消息、工作树、权限和公开复现；不以历史grader代替",
      "status": "open"
    },
    {
      "category": "coverage_gap",
      "scope": "tests and gold completeness",
      "evidence_refs": [
        "T",
        "需求—断言表",
        "G与调用链"
      ],
      "proposed_action": "优先以stdlib dataclass默认实例作私有base/gold API对照，确认或撤销TypeAdapter配置异常疑点",
      "status": "open"
    }
  ],
  "file_rules": {
    "additional_exclusions": []
  },
  "revision_refs": [],
  "disposition": {
    "state": "needs_review",
    "scope": "static_review",
    "reason": "目标修复成立但gold的stdlib dataclass默认编码有具体静态疑点；actor未验"
  },
  "usage": {
    "intended_use": "development_diagnostic",
    "reviewer_private_exposure": [
      "本题gold/隐藏测试/expected",
      "本题run_refs授权历史noop/gold原件"
    ],
    "other_quality_conclusions_read": false,
    "actual_actor_exposure": "unknown",
    "solver_input_allowed": false
  },
  "costs": {
    "tokens": null,
    "money": null,
    "current_cpu_seconds": null
  }
}
```
