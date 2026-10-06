# pydantic__pydantic-8793 — 独立 cross review

作者：e25_review_pack12_pydantic。root明确release后才新增阅读五份本题稿件与history/refs.json唯一原件。已封存reviewer_initial SHA256=`6226ba5486655b75ea8226c3706288ef0b9fb01248d12d7b835e7f680d119004`，重新核验未变。所有命令显式workdir=/Users/roger/Desktop/claude-code-verl-stage0h；本阶段只写review.md，未改初稿/主审/原题/测试/gold/评分，未执行项目/测试/网络/安装/容器/模型或派生agent。

复核结论：维持 needs_review / static_review、development_diagnostic。原例与三项新增测试有公开依据，gold 修复局部行为的原始证据成立；当前 actor 开发与实际可读写范围未知。主审技术结论可采用，但收口不要把 check4 的有限 pass 当成实际 actor 权限已验。未发现足以升级为“gold 已新增回归”的证据。

逐项交叉核对（P=本题 PUBLIC目录，源码路径相对P/base；Q=本题 PRIVATE；O=本题09-16历史JSON；H=09-19 run_refs 精确原件；R=本题OUTPUT）：

| 判断 | 独立核对/决定性证据 | 结果 |
| --- | --- | --- |
| create_model/bar、foo/bar/baz 必填 | 已封存 initial 的完整T及 fields.py:305–419；主审补引 models 文档动静等价和必填定义；public_read指出相同上游状态链 | 确认。两schema assert回到原例，三个is_required回到同一字段语义 |
| 基线缺陷与gold对应 | Q/gold.patch 全文；H noop:1077–1225：两warning-as-error、c.is_required False；gold状态原行1090–1092全部PASS | 确认局部因果，不从reward推断运行时全部正确 |
| 364项P2P均PASS | initial已逐ID机械对照；主审附录的ledger/log/hash及结构化runtime字段又逐个与原ledger核对 | 确认身份与状态；双方都没有通读364项正文 |
| 缺少runtime/复杂Annotated断言 | 新增五条assert只有schema/is_required；test_annotated与test_create_model不在实际单文件selector | 确认覆盖边界，不等于gold回归或证明某错误候选必过 |
| 只改is_required必定污染model_construct/默认schema | 本次补读P/base/pydantic/main.py:195–229及initial所读_generate_schema:1074–1078、wrap_default | 不支持旧全称推论。model_construct:221先判断not is_required才取默认值，schema构建也受同一门控。未运行替代补丁，不能宣称其完整正确或必过367项 |
| _attributes_set含Ellipsis就是gold不彻底 | P/base/pydantic/fields.py:180原本记录原参数；多Field再构造会规范化；initial完整G | 旧“gold_incomplete”没有已证错误行为，主审收窄正确。repr:558–582可能显示剩余default不等于自动增加内部状态评分要求 |
| 内部默认值与外层...优先级 | 主审与public_read指出fields文档:58–59“不支持内层default”与旧合并测试用Field(3)的差异；已补读文档 | 保留疑义，不臆造必须覆盖规则，也不为该疑义机械要求CPU |
| 原安装失败/CC缺依赖仍阻断 | O仅摘要引用早期日志；H修订配方安装RC0、目标确实执行且deny_all | 主审正确区分条件。O的原轨迹未授权追读，不称已证伪，也不当作当前actor实况 |

新增主动检查：读取P/base/tests/test_config.py:765–798，确认test_partial_creation_with_defer_build（:777–798）在测试内create_partial helper中调用FieldInfo.merge_field_infos(field, default=None)，然后断言原模型required=['a','b']、partial仅required=['b']。这给出真实default=None覆盖和原模型稳定性的具体公开旧约束；它没有进入本题H的tests/test_json_schema.py选择器。本次不运行它、不声称它base/gold通过。O把:788称为“另一个生产调用点（with_config/override_fields路径）”不准确：这里是测试局部helper，名称也不是with_config。主审delta没有清楚纠正这一小处，后续引用应使用真实函数名与测试作用域。它不改变唯一优先下一步。

对历史复述的审核：完整读取且重算O SHA256匹配授权refs。主审old_findings_delta对O的输入完整/泄漏零命中/ready_for_probe/20分钟都已按本轮证据收窄，不沿用旧资格或成本；对旧check26仅因未覆盖调用者即标issue也已改为check25覆盖风险、26 unknown。O所列其他题、R2/R3/R4、summary和轨迹没有跟随。本包9066基线确有同一七行字段归一化及三个旧测试，本次补读9066 fields.py:418–439确认；这只支持版本关联，不能证明正式split重复或actual actor泄漏。

字段与证据边界审核：

- screening_record.json具有恰好13个规定顶层字段；全部checks有status/evidence_refs/by，全部issues有category/scope/evidence_refs/proposed_action/status；编号在1–40内，未列项按not_checked。全部引用文件路径存在（只核存在性，没有扩读未授权内容）；analysis_sha256与当前封存analysis相符，runtime数字/镜像ID/scripts_digest/log SHA/test RC与本题两行原ledger相符。
- 3 unknown与23 pass分开；25 issue、26/27 unknown保留漏测与已证回归、局部正证据与完整性的区别；29 actual actor unknown与usage私有暴露分开；40 unknown正确，没有用封存合规冒充无漏检。additional_exclusions/revision_refs均空，disposition与intended_use及null成本合规。
- 主审check4=pass的note明确只说声明NON-TEST范围能容纳修复且历史投影源码，actual actor真实写权限未知。对计划提交范围可以采用这个有限正证据；对本轮完整check4问题，本review建议unknown，并明确保留上述正证据，避免消费方只看status误当actor权限通过。无需改封存主审稿，由协调者收口时处理。
- 本reviewer initial的6=pass只限历史修订grader，24=pass只限未发现内部算法约束。主审采用unknown防止被理解为当前工具链已验或普遍无误拒，我接受收口采用unknown；这是字段作用域变得更严格，不是发现反例，也不是意见人数投票。

八方面收口：公开目标/版本有直接依据；新增断言及关键helper完整核读；P2P只有明确风险段语义检查；合理替代方案未实测；gold与调用者有局部正证据但完整性未知；actor开发条件未知；历史候选投影/可信恢复有证据但非任意候选安全证明；用途及暴露仅限私有开发诊断。本轮没有新执行、没有新增隐藏要求或路径排除。

唯一优先下一步：任务二通过正式actor入口记录真实消息、HEAD/status/diff、解释器/工作区导入与写权限，运行公开create_model原例及缺bar/baz时的ValidationError；Python3.8使用公开旧测试已有typing_extensions.Annotated。base应仍呈目标错误，修复后应正确必填。该步骤解决实际开发事实缺口；不要求先全仓或先做is_required替代补丁实验。

新增获准阅读身份（SHA256，全文读取五份稿件；较大JSON输出截断处随后按键补读）：

- `public_read.md`：`822f04183cdc16ffedd25981386356b2dfce0673f324a11b8b24a978b60af741`
- `analysis_before_history.md`：`c12547018acb4df0b9c271c2ebc4a3da40648037ad9e37c2c0ce8020a591f793`
- `old_findings_delta.md`：`cfcda058d5a8119ed9dea86cba42ae45f187417d6ad6b3539aae672e2114dcac`
- `card.md`：`f513c84003c60e95fb471bb641468944ed2b58c78ad695bfc7655b801bb55370`
- `screening_record.json`：`b798364d092719e5c2771bd9339eee4da9b2ba6e5fdd23ab33a576c13a1f2321`
- 历史唯一原件 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8793.json`：`9d3f323be6432aa01c1a44e21e14d110669efc0890929b69581c2c5e4a2085f4`（本次重算一致）；未跟随其内其他题或历史汇总链接。

阅读边界：initial中的原始材料/完整新增断言/运行核对保持有效；本阶段补读源码区段已逐项列明。未扩大到全部P2P正文、core Rust实现、当前actor状态、模型消息或未授权质量材料。各项技术判断以原件为准，无runtime新增结论。

Reviewer收口记录（13顶层字段，checks稀疏；未列不代写主审结论）：

```json
{
  "task_id": "swe_gym_lite::pydantic__pydantic-8793",
  "task_revision": "upstream",
  "source_adapter_ref": {
    "source": "swe_gym_lite",
    "spec_vendor_id": "swegym_constants_242429c1",
    "source_refs": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8793/source_refs.json",
    "grading_bundle_ref": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8793/grading.json",
    "parser_version": "swegym_parsers@242429c1",
    "scope": "exported task and historical H19; current actor input unknown"
  },
  "recipe_ref": {
    "environment_record": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8793/environment_record.json",
    "run_refs": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8793/run_refs.json",
    "historical_derived_recipe": "pydantic-install-v1",
    "notes": "editable pip + candidate testing/testing-extra with offline wheelhouse; no audit modifications"
  },
  "code_snapshot_ref": {
    "base_commit": "832225b90672c68e2d4067bd0ffecf834d62b48b",
    "base_identity_ref": "runs/swegym_quality_expansion_20260925/public/pydantic__pydantic-8793/base_identity.json",
    "gold_sha256": "db816cd4802bd14e7428d09fff82141fdb3a2ee631a7fe3b809a12f701df273e",
    "test_patch_sha256": "9998aa0c19304a159da5642bc3df24a6ab3b9de129f8ac4f6bd71c2e140041a8",
    "historical_code_snapshot_ref": "runs/swegym_quality_expansion_20260925/private/pydantic__pydantic-8793/environment_record.json#/historical_code_snapshot",
    "archive_content_independently_read": false,
    "actual_actor_worktree": "unknown",
    "actual_actor_image_id": null
  },
  "facts_ref": {
    "sealed_initial": "/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/pydantic__pydantic-8793/reviewer_initial.md",
    "sealed_initial_sha256": "6226ba5486655b75ea8226c3706288ef0b9fb01248d12d7b835e7f680d119004",
    "main_read_hashes": {
      "public_read.md": "822f04183cdc16ffedd25981386356b2dfce0673f324a11b8b24a978b60af741",
      "analysis_before_history.md": "c12547018acb4df0b9c271c2ebc4a3da40648037ad9e37c2c0ce8020a591f793",
      "old_findings_delta.md": "cfcda058d5a8119ed9dea86cba42ae45f187417d6ad6b3539aae672e2114dcac",
      "card.md": "f513c84003c60e95fb471bb641468944ed2b58c78ad695bfc7655b801bb55370",
      "screening_record.json": "b798364d092719e5c2771bd9339eee4da9b2ba6e5fdd23ab33a576c13a1f2321"
    },
    "historical_exact_original": "docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_pydantic/records/pydantic__pydantic-8793.json",
    "historical_original_sha256": "9d3f323be6432aa01c1a44e21e14d110669efc0890929b69581c2c5e4a2085f4",
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
    }
  ],
  "file_rules": {
    "additional_exclusions": []
  },
  "revision_refs": [],
  "disposition": {
    "state": "needs_review",
    "scope": "static_review",
    "reason": "静态候选，actor开发条件及完整回归范围未验"
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
