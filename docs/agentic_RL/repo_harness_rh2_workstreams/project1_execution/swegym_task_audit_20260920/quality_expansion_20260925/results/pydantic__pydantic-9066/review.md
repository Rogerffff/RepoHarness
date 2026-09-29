# pydantic__pydantic-9066 — 独立 cross review

作者：e25_review_pack12_pydantic。root明确release后才新增阅读五份本题稿件与history/refs.json唯一原件。已封存reviewer_initial SHA256=`c977d814d44788bcbdd82fc76d9e9fd5e34c680c5065251c017340e8e4c7b669`，重新核验未变。所有命令显式workdir=/Users/roger/Desktop/claude-code-verl-stage0h；本阶段只写review.md，未改初稿/主审/原题/测试/gold/评分，未执行项目/测试/网络/安装/容器/模型或派生agent。

复核结论：维持 needs_review / static_review、development_diagnostic。IP默认值目标、两F2P与历史局部修复证据成立；标准库dataclass实例默认值触发TypeAdapter配置异常的链仍是具体静态疑点，未获得新的base/gold执行证据。主审对主要旧结论的纠正成立，可采用其技术判断及唯一优先CPU对照；actual actor资格仍unknown。

逐项交叉核对（P=本题PUBLIC目录，源码路径相对P/base；Q=本题PRIVATE；O=本题09-16历史JSON；H=09-19 run_refs精确原件；R=本题OUTPUT）：

| 判断 | 决定性证据及复核 | 结果 |
| --- | --- | --- |
| 真正目标是schema默认值而非IP输入解析 | user_prompt原例；public_read对应networks已有validator/serializer；initial完整T及default_schema调用链 | 确认。IPv6可由IPvAnyAddress的公开范围推出 |
| 两F2P覆盖默认字符串、format/title/type且不再报目标warning | T两个参数化完整schema；pyproject filterwarnings=error；H noop:1065–1211目标栈；gold:1101–1102 PASS | 确认。没有单独warning assert不等于没有该约束 |
| 367 P2P回归护栏 | initial已读默认值/配置/错误回退风险段；全expected逐ID核状态；本次结构化runtime值再与原ledger匹配 | 确认局部正证据。不把数字当语义全覆盖 |
| gold每个默认值都构造TypeAdapter | G的hasattr(__pydantic_serializer__)短路 | O量词错误，主审纠正成立。构建开销未测，不称性能回归 |
| gold将原warning普遍升级为异常 | G只把schema-generation error转serialization error；P/base/pydantic/json_schema.py:1011–1019捕获后仍warning/省略 | O一般性主张不成立，主审纠正正确；不能混同pytest warning-as-error或另一种未捕获PydanticUserError |
| 新except路径完全零覆盖 | 本次补读_generate_schema.py:386–407,740–833、_typing_extra.py:74–85；旧test_non_serializable_default含lambda，H对应PASS | 不支持“零覆盖”的绝对结论。type(lambda)是function类，非Callable特殊类型/函数实例分支，静态推导走unknown-type schema并触发新except；没有动态插桩，不能声称已测分支覆盖率 |
| object()可作为不能生成schema的反例 | P/base/pydantic/_internal/_generate_schema.py:768–769对object返回any_schema | 旧建议不适合检验该except。公开model_json_schema也不应直接按内部PydanticSerializationError验收 |
| IP类别专门处理是错误硬编码，应新增非IP类型要求 | 公开问题要求IP默认值；T没有内部方案限制 | 主审纠正成立。按IP类型正确处理是合理路线；写死测试字面量/字段名才是明显不完整。不能只为迫使采用gold通用方案扩规格 |
| dataclass默认实例疑点 | initial已完整读TypeAdapter配置判定、default_schema、ConfigWrapper和标准dataclass schema路径；本次补核异常类关系errors.py:87及:131 | 维持未证状态。PydanticSchemaGenerationError是PydanticUserError子类；catch子类不能捕获直接PydanticUserError。空config仍非None，普通dataclass无serializer的分支可能抛type-adapter-config-unused |
| 已有dataclass测试能排除该异常 | 已读dataclass_default_bytes/timedelta实际默认值为原生bytes/timedelta；nested_python_dataclasses无默认实例；BaseModel defaults有serializer | 不能排除，主审区分正确；尚不能据静态路径判定base成功/gold失败 |

历史复述审核：O SHA256已重算匹配授权refs，完整阅读了唯一获准原件。主审delta正确将旧安装RC2限定为早期未重读条件，而H的离线wheelhouse+修订pip安装两次RC0是真实已核运行；不能拿H替当前actor。O对6126行重叠的叙述没有对应获准跨题原件，本次未访问该题，主审保持“旧主张未核”是正确处理；行重叠本身不等于actual actor得到私有答案。旧R4/泄漏扫描/15分钟/ready_for_probe未沿用，正确。双方已有同一个dataclass疑点只是独立静态复核一致，不增加runtime证据等级。

主动找遗漏与本次范围：补读了function类/Callable分支与object分支，以核对主审对O“except零覆盖”的纠正，而非仅凭主审复述同意。没有发现新的必须补评分的非IP需求。initial已读test_namedtuple_default:3264–3286，它补充了一个合法无serializer类型的已有护栏，但仍不解决dataclass的特殊config限制。H的全文件完成与P2P通过不能推断每个新分支或所有容器默认值都已覆盖。直接IP注解、其他地址值、容器中的IP、field serializer/default_factory仍是范围边界，不机械把所有边界升格为失败。

字段与证据审核：

- screening_record.json恰有13个规定顶层字段；所有checks的status/evidence_refs/by和issues的五个必需键齐全；编号合法稀疏。全部引用文件路径存在（仅存在性核验，未扩大内容阅读）；analysis_sha256匹配封存主审初判。runtime两行中的F2P/P2P、test RC、实际历史派生镜像ID、scripts_digest与log SHA均和原ledger相符。source expected digest与actual derived ID分列，actual_actor_image_id=null正确。
- 3 unknown与23 pass、25 issue与26 unknown、27局部正证据/完整性unknown、29实际泄漏与usage审查暴露、40 unknown均未混淆。potential_gold_regression的status=unconfirmed/evidence_level=static明确；没有把CPU建议写成结果。additional_exclusions=[]、revision_refs=[]、needs_review/static_review、development_diagnostic及null成本合规。
- check4=pass的note仅证明声明NON-TEST边界及H源码投影，且承认actual actor权限未知。建议协调者最终整体check4采用unknown并保留声明范围有正证据；不要把状态单独投射为actor已获合法读写范围。本review未修改主审文件。
- initial的6=pass只限历史可恢复配方，24=pass只限静态未见算法约束。接受主审收口使用unknown以限定当前资格及未验证误拒范围，保留对应局部正证据。不是发现非gold方案失败，也不是以相同意见数量决策。

八方面结论完整保留：公开规格和版本可追溯；两新增断言/关键helper完整读取；风险P2P范围明确；非gold合法路线不被按内部算法否决；gold有具体未证回归路径；真实actor环境仍未知；历史可信测试恢复/源码投影成立但不等于任意候选控制面无漏洞；审查仅限私有开发诊断，不能宣告训练或正式评测资格。

唯一优先下一步：由任务二在隔离私有、同配方的base/gold环境构造stdlib `@dataclasses.dataclass class D: x:int`、`class M(BaseModel): d:D=D(1)`，调用公共M.model_json_schema，并用题面IPv4例作目标控制。记录代码来源、镜像/HEAD/初态、warning、schema默认值、异常类型/code和RC。只有base可用而gold因type-adapter-config-unused失败，才可把26提升为已证新增回归；若两者相同或对象已带serializer，应收窄/撤销推断。无需全仓或GPU，私有对照成功也不替代actor开发条件。

新增获准阅读身份（SHA256，全文读取五份稿件；较大JSON输出截断处随后按键补读）：

- `public_read.md`：`88a4ba0c85512c6e6e722ab7f6e732ea804ee349aa9444abdfb717bdf1e06b83`
- `analysis_before_history.md`：`212281deb809c58b20d14d57dbc104c7710d07612cace57d37dc13d25e1fa305`
- `old_findings_delta.md`：`95180356beb9b2417367645cacd11a0f9df8a0584494f3a2605be90552d13189`
- `card.md`：`05e05f1a1b5fc68b464c37cf40d3ee23aa9b3a88855046d91b888c3d4c7df8ba`
- `screening_record.json`：`399000d953993c14d27a0595122c7b802bc7b6ade400a2732072f6d939f839e7`
- 历史唯一原件 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-9066.json`：`14510c774ad525bdb17c054d9555b438572bde42f6e221464b2c0c22f8bc5713`（本次重算一致）；未跟随其内其他题或历史汇总链接。

阅读边界：initial中的原始材料/完整新增断言/运行核对保持有效；本阶段补读源码区段已逐项列明。未扩大到全部P2P正文、core Rust实现、当前actor状态、模型消息或未授权质量材料。各项技术判断以原件为准，无runtime新增结论。

Reviewer收口记录（13顶层字段，checks稀疏；未列不代写主审结论）：

```json
{
  "task_id": "swe_gym_lite::pydantic__pydantic-9066",
  "task_revision": "upstream",
  "source_adapter_ref": {
    "source": "swe_gym_lite",
    "spec_vendor_id": "swegym_constants_242429c1",
    "source_refs": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066/source_refs.json",
    "grading_bundle_ref": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066/grading.json",
    "parser_version": "swegym_parsers@242429c1",
    "scope": "exported task and historical H19; current actor input unknown"
  },
  "recipe_ref": {
    "environment_record": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066/environment_record.json",
    "run_refs": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066/run_refs.json",
    "historical_derived_recipe": "pydantic-install-v1",
    "notes": "editable pip + candidate testing/testing-extra with offline wheelhouse; no audit modifications"
  },
  "code_snapshot_ref": {
    "base_commit": "a3b7214a1d6ac8e32c29e9d4436ea6a9e253ead7",
    "base_identity_ref": "runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-9066/base_identity.json",
    "gold_sha256": "5bb189597da2acc269a026b887b1e7d4152c6fe24f60d253ce3c9fb309757fa4",
    "test_patch_sha256": "762cd93f859d6ef4f79b233e7b0e3019a8ccd9b417f13301467180b1082f6222",
    "historical_code_snapshot_ref": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-9066/environment_record.json#/historical_code_snapshot",
    "archive_content_independently_read": false,
    "actual_actor_worktree": "unknown",
    "actual_actor_image_id": null
  },
  "facts_ref": {
    "sealed_initial": "/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-9066/reviewer_initial.md",
    "sealed_initial_sha256": "c977d814d44788bcbdd82fc76d9e9fd5e34c680c5065251c017340e8e4c7b669",
    "main_read_hashes": {
      "public_read.md": "88a4ba0c85512c6e6e722ab7f6e732ea804ee349aa9444abdfb717bdf1e06b83",
      "analysis_before_history.md": "212281deb809c58b20d14d57dbc104c7710d07612cace57d37dc13d25e1fa305",
      "old_findings_delta.md": "95180356beb9b2417367645cacd11a0f9df8a0584494f3a2605be90552d13189",
      "card.md": "05e05f1a1b5fc68b464c37cf40d3ee23aa9b3a88855046d91b888c3d4c7df8ba",
      "screening_record.json": "399000d953993c14d27a0595122c7b802bc7b6ade400a2732072f6d939f839e7"
    },
    "historical_exact_original": "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-9066.json",
    "historical_original_sha256": "14510c774ad525bdb17c054d9555b438572bde42f6e221464b2c0c22f8bc5713",
    "new_execution": false
  },
  "checks": {
    "3": {
      "status": "unknown",
      "evidence_refs": [
        "P/environment_brief.md"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "4": {
      "status": "unknown",
      "evidence_refs": [
        "P/public_bundle.json；主审check4 note：声明范围有正证据，actual actor权限未知"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "6": {
      "status": "unknown",
      "evidence_refs": [
        "Q/run_refs.json：历史配方局部成功；当前actor未验"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "18": {
      "status": "pass",
      "evidence_refs": [
        "Q/run_refs.json；initial逐项历史执行核对"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "19": {
      "status": "pass",
      "evidence_refs": [
        "Q/grading.json；原ledger/log全部expected对应，仅所引运行"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "23": {
      "status": "pass",
      "evidence_refs": [
        "需求—断言双向表；P/user_prompt.txt；T"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "24": {
      "status": "unknown",
      "evidence_refs": [
        "T未见算法限定；无替代解运行，普遍误拒未证"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "25": {
      "status": "issue",
      "evidence_refs": [
        "initial需求—断言表；本review具体边界"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "26": {
      "status": "unknown",
      "evidence_refs": [
        "G与调用者；没有新增base/gold回归执行证据"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "27": {
      "status": "unknown",
      "evidence_refs": [
        "原H目标通过的局部正证据；完整性未知"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "28": {
      "status": "pass",
      "evidence_refs": [
        "本review旧结论纠正；未扩生产规格"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "29": {
      "status": "unknown",
      "evidence_refs": [
        "P/environment_brief.md；授权暴露见usage"
      ],
      "by": "e25_review_pack12_pydantic"
    },
    "40": {
      "status": "unknown",
      "evidence_refs": [
        "风险抽样与未运行边界；不由封存推无漏检"
      ],
      "by": "e25_review_pack12_pydantic"
    }
  },
  "issues": [
    {
      "category": "actor_evidence_gap",
      "scope": "actual actor environment and check4 status scope",
      "evidence_refs": [
        "主审screening_record.json#/checks/4",
        "P/environment_brief.md"
      ],
      "proposed_action": "收口保留actual actor unknown；通过任务二真实入口核验",
      "status": "open"
    },
    {
      "category": "coverage_gap",
      "scope": "target and relevant regressions",
      "evidence_refs": [
        "reviewer_initial.md需求—断言表",
        "本review交叉核对表"
      ],
      "proposed_action": "保留具体未覆盖范围，不能用P2P数量替代语义覆盖或判gold已回归",
      "status": "open"
    },
    {
      "category": "potential_gold_regression",
      "scope": "stdlib dataclass default instance",
      "evidence_refs": [
        "G",
        "P/base/pydantic/type_adapter.py:197",
        "P/base/pydantic/json_schema.py:1011"
      ],
      "proposed_action": "唯一优先私有base/gold公共API对照，带原IP例控制",
      "status": "unconfirmed"
    }
  ],
  "file_rules": {
    "additional_exclusions": []
  },
  "revision_refs": [],
  "disposition": {
    "state": "needs_review",
    "scope": "static_review",
    "reason": "IP局部修复成立，stdlib dataclass配置异常疑点未证，actor条件未知"
  },
  "usage": {
    "intended_use": "development_diagnostic",
    "private_exposure": [
      "本包获准gold/隐藏测试/expected/历史run原件",
      "release后本题五稿及唯一历史JSON"
    ],
    "actual_actor_exposure": "unknown",
    "solver_eligible_material": false,
    "cross_review_release": "explicit root message after initial sealing"
  },
  "costs": {
    "tokens": null,
    "money": null,
    "current_cpu_seconds": null
  }
}
```
