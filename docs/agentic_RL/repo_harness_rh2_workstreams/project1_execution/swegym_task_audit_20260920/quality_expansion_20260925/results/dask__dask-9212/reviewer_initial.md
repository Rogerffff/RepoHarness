# dask__dask-9212 独立初判（封存前；2026-09-25）

审查者：e25_review_pack11_dask。结论为 needs_review / static_review：四类 Enum 的简单成员行为有清楚的公开依据和历史正反对照，适合受限开发诊断候选；不把两个 F2P 的通过当作完整确定性或防冲突保障。实际 actor 条件未知。

## 证据与阅读边界

P=`runs/swegym_quality_expansion_20260925/public/dask__dask-9212`，Q=同根`private/dask__dask-9212`，均相对 ROOT `/Users/roger/Desktop/claude-code-verl-stage0h`。已读公开题面、bundle/identity/environment_brief，Q test/gold全patch、grading/validation/source_refs/run_refs及环境信息；未读任何 public_read、主审稿、history、根汇总或别题结论。

完整读新增测试四参数和两断言；base.py:895–1080（tokenize/normalize_token和fallback），utils.py:544–607（完整Dispatch），test_base.py:1–115、200–480、580–740（函数、对象/协议、容器、dataclass等相关P2P），delayed.py:213–231、618–641（纯函数图键调用者）；custom-collections.rst:477–552、develop.rst:1–140、setup.cfg。103 P2P状态逐项核对，语义为风险抽查；test_base.py其余区段及所有下游仓库调用者未读，不以状态数量宣称语义覆盖。

原件 N/G 为 Q/run_refs 授权的 `runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-9212/{noop,gold}/eval_logs/evallog_replay-er19-compat_v2b-d_{5b76bc8e,0ae188c0}.eval.log`，分别1–925/1–919行；L0/L1为对应noop/gold目录ledger.jsonl第1行。日志hash与run_refs匹配。完整读gold recipe四份before/after脚本、recipe.json、image.json/build.log；candidate.patch与gold字节相等，projection/baseline/stage只读授权JSON指针，核attempt/HEAD/源码范围。历史配方中的原因文字只视为原因声明，没有扩读其引用的其他任务。

## 需求—断言双向表

| 公开需求/已有行为 | 断言/调用者 | 覆盖及局限 |
| --- | --- | --- |
| 同一个普通 Enum 成员重复 tokenize 应相等 | test_tokenize_enum[Enum] 的第一assert | F2P；直接复现公开MCVE；gold通过 |
| 不同成员应区分 | 四参数第二assert RED != BLUE | 从确定性图键的公开语义可推断，且非实现限制；仅1/2这对值 |
| Flag 也属于枚举 | test_tokenize_enum[Flag] | F2P；只具名单flag，未覆盖组合/零flag |
| IntEnum/IntFlag 保持稳定 | 对应两个新增参数 | P2P，base已由int dispatch走identity，不能说四项均检验新Enum handler |
| token按参数值形成稳定图键，不能系统性混淆语义不同对象 | docs custom-collections:482–503；delayed.call_function:618–641；test_tokenize_dataclass:438–455 | 新测试只构造一个局部Color，未测同名不同模块Enum、复杂value、跨进程稳定性；相关P2P不是Enum这些路径的替代 |
| 自定义对象可扩展tokenization | test_tokenize_method:374–394；Dispatch MRO | 普通对象P2P覆盖；Enum自定义__dask_tokenize__路径未测。文档已说明注册superclass会优先，因此不能将优先级变化自动判成违规 |

所有新增ID前缀 `dask/tests/test_base.py::test_tokenize_enum`：

| 后缀 | expected | noop → gold | 判断 |
| --- | --- | --- | --- |
| [Enum] | F2P | N633 FAILED → G662 PASSED | N743同成员重复token不等 |
| [Flag] | F2P | N636 FAILED → G665 PASSED | N760同成员重复token不等 |
| [IntEnum] | P2P | PASSED → PASSED | MRO先int，原已有稳定行为 |
| [IntFlag] | P2P | PASSED → PASSED | MRO先int，原已有稳定行为 |

## 八方面独立判断与具体疑点

1. **身份/输入**：base aa801de0f42716d977051f9abb9da2c9399da05c，公开/私有/历史绑定相符；gold hash 0e1750f45b3e53582caaa7ee078ec8f1a753742b48b4d1bc77a0bd6141114d56。真实actor消息及工作树仍unknown。题面本身给“Possible Implementation”，包含接近gold的实现是来源公开提示，不是本审查私料泄露；该片段import normalize_enum却使用normalize_token显然不完整，源码和完整MCVE足够定位，不要求照抄。
2. **规格/合理解**：明确最小目标为同成员稳定。返回类型/成员名/规范化value、注册Enum或在通用normalize路径等价处理，都可满足现有断言。具体digest无硬编码；未发现强制唯一实现。跨模块语义与任意value完整性须对照项目通用token规范，不能仅因gold使用三元组便指定三元组为规格。
3. **测试覆盖/漏测**：一个局部Color、RED=1/BLUE=2、同进程双调用。只返回成员名的弱修复也会满足新增断言，却混淆不同枚举类型同名成员。没有保证跨进程、复杂value、不同枚举类、Flag组合与自定义协议；这些是覆盖边界，不是全部都应立刻新增评分条件。
4. **gold正确性/完整性**：新增Enum注册使普通Enum/Flag绕开object的uuid fallback，静态原因与N/G结果相符。IntEnum/IntFlag优先int路径，并未使用新handler。具体结构冲突疑点：两个模块各自定义同名Color，RED=1、BLUE=2；两种RED不是同一个类型，却都规范为('Color','RED',1)。delayed(pure=True)若函数按枚举类型/模块返回不同结果，其任务名将相同，可能合并错误。可用 `Enum('Color', {'RED':1,'BLUE':2}, module='left')` 与 module='right' 构造，比较token及纯函数两结果。这是静态结构证据；未执行base/gold对照，check26仍unknown，不能称已观测gold回归。公开建议实现也有同一限制，因此记录为完整性/用途限定而非擅自改题。
5. **相关旧行为/协议**：normalize_object优先__dask_tokenize__，新的Enum registration会改变此路径；test_tokenize_method显示显式dispatch优先，文档提示registered superclass需要注册子类，所以不能简单将“未调用旧自定义方法”判为gold错误。e.value未经normalize_token，地址型/不稳定repr可能影响跨进程或重复稳定性；本题没有这类断言，也没有实测，不据此宣告所有Enum均失败。
6. **运行/评分**：两次原命令均 `pytest -n0 -rA --color=no dask/tests/test_base.py`；安装先离线 `python -m pip install --no-index --find-links=/opt/rh2/compat-wheels --no-deps pandas==1.4.4 numpy==1.24.4` 再 `python -m pip install --no-deps -e .`。安装RC都0，版本标记重复确认两pins。N918/922：2 failed、124 passed、3 skipped、RC1；G912/916：126 passed、3 skipped、RC0，均129 collected，2条scipy稀疏矩阵警告。3 skip为matplotlib缺失1、--runslow未开2；全部2 F2P与103 P2P在两原日志逐ID出现，没有expected skip/xfail/missing。账本num_parsed_tests=125不同于pytest126 passed；未审parser整体，不能混成同一计数口径，但全部本题expected已独立逐项对齐，无证据该差异影响本题分差。
7. **环境/条件版本**：historical grader UID54322，deny_all，cpus=2.0，memory_bytes=4294967296；源码import `/testbed/dask/__init__.py`，Python3.10、Dask2022.6.0+16.gaa801de0f.dirty。来源manifest 1ebd1560…ed60；compat_v2b实际image ID=5b69493366c23ca4871f1011097747345c49cb6c4f8408cac7fc6a8125fff122；image.json的base_id=974b8bd9…d982是本地base ID，不与manifest混用。build只COPY wheels，pins在安装脚本生效。scripts_digest=db692fb6…bb39；recipe改变依赖非题面/测试。N210–214恢复后的grader干净，G215只base.py改动；git show的dataframe patch是HEAD提交，不是未提交初态。实际actor准备后状态/资产/权限全部待验。修前cumproduct失败仅recipe reason声明，run_refs本轮授权对照是修后，不把未读取修前日志写成独立复验。
8. **用途/泄露/过程可靠性**：审查者已见hidden test/gold/原grader；不得给solver。真实actor可见私料/网络获取答案unknown。历史cleanup removed=true、runner_integrity_changed=false只支持该pair；不证明评分控制面不可绕过、采样无偏或真实模型已解。训练/模型成本未观测。

## 开发需要与唯一优先下一步

| 操作/资产 | 公开依据 | 已有适用证据 | actor缺口 | 最小公开命令/预期 |
| --- | --- | --- | --- | --- |
| Python Enum与工作区tokenize | user_prompt完整MCVE；base.py | 历史grader源码导入和目标断言 | 实际消息、解释器、UID/路径、工作树未知 | 打印sys.executable/dask.__file__并执行题面Color重复token断言；base应失败，修复应稳定 |
| 窄测试及可用依赖 | develop.rst:99–122，setup.cfg；test_base imports | compat_v2b下测试129收集 | actor NumPy/Pandas兼容pins、pytest/xdist及包权限 | `python -m pytest dask/tests/test_base.py -q -k 'tokenize or normalize'`；分别记录skip和目标失败，不要求全仓/slow全绿 |
| 可编辑非测试源并验证纯函数键 | public_hints；delayed公开pure API | 历史gold仅base.py | 交付权限及真实源码生效未观测 | 非测试source修改；必要临时公开复现无需私有测试 |

**唯一优先下一步**：任务二在拟交付actor入口记录真实环境并执行公开Color MCVE及窄token测试，确认该公开开发路径可用、base仍保留目标失败。当前最直接资格缺口是actor而非历史grader；上述同名不同模块Enum冲突保留为有依据的后续私有诊断疑点，不把未明确裁定的跨模块要求提前注入solver或评分。

## 结构记录（13个顶层字段；未列check视为not_checked）

```json
{
  "task_id": "swe_gym_lite::dask__dask-9212",
  "task_revision": "original",
  "source_adapter_ref": "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/source_refs.json",
  "recipe_ref": "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/run_refs.json",
  "code_snapshot_ref": "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/base_identity.json",
  "facts_ref": [
    "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/run_refs.json",
    "actor_environment_card.md"
  ],
  "checks": {
    "1": {
      "status": "pass",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/base_identity.json",
        "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/run_refs.json"
      ],
      "by": "e25_review_pack11_dask"
    },
    "2": {
      "status": "pass",
      "evidence_refs": [
        "需求—断言双向表",
        "运行/评分"
      ],
      "by": "e25_review_pack11_dask"
    },
    "3": {
      "status": "unknown",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/environment_brief.md"
      ],
      "by": "e25_review_pack11_dask"
    },
    "10": {
      "status": "unknown",
      "evidence_refs": [
        "开发需要与唯一优先下一步"
      ],
      "by": "e25_review_pack11_dask"
    },
    "18": {
      "status": "pass",
      "evidence_refs": [
        "运行/评分：仅历史授权pair和expected集合"
      ],
      "by": "e25_review_pack11_dask"
    },
    "19": {
      "status": "pass",
      "evidence_refs": [
        "逐个expected ID原日志对齐；不声明parser整体正确"
      ],
      "by": "e25_review_pack11_dask"
    },
    "20": {
      "status": "pass",
      "evidence_refs": [
        "原日志目标失败与安装RC记录"
      ],
      "by": "e25_review_pack11_dask"
    },
    "23": {
      "status": "pass",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/user_prompt.txt",
        "规格/合理解"
      ],
      "by": "e25_review_pack11_dask"
    },
    "24": {
      "status": "pass",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/test.patch",
        "仅已读断言范围"
      ],
      "by": "e25_review_pack11_dask"
    },
    "25": {
      "status": "issue",
      "evidence_refs": [
        "需求—断言双向表"
      ],
      "by": "e25_review_pack11_dask"
    },
    "26": {
      "status": "unknown",
      "evidence_refs": [
        "未运行的具体静态回归/结构冲突疑点"
      ],
      "by": "e25_review_pack11_dask"
    },
    "27": {
      "status": "unknown",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/gold.patch",
        "局部正证据成立，完整性未证"
      ],
      "by": "e25_review_pack11_dask"
    },
    "29": {
      "status": "unknown",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/environment_brief.md",
        "usage审查私有暴露不替代actor可见性"
      ],
      "by": "e25_review_pack11_dask"
    },
    "40": {
      "status": "unknown",
      "evidence_refs": [
        "抽查/封存不能证明无漏检误拒偏差"
      ],
      "by": "e25_review_pack11_dask"
    }
  },
  "issues": [
    {
      "category": "coverage",
      "scope": "static_review",
      "evidence_refs": [
        "需求—断言双向表",
        "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/test.patch"
      ],
      "proposed_action": "保留具体覆盖边界，按唯一下一步取决定性事实，不私改评分",
      "status": "open"
    },
    {
      "category": "actor_evidence",
      "scope": "actual_actor",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-9212/environment_brief.md"
      ],
      "proposed_action": "任务二采集真实入口、消息、工作树、权限和公开开发命令",
      "status": "open"
    },
    {
      "category": "gold_completeness",
      "scope": "static_hypothesis_not_executed",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/private/dask__dask-9212/gold.patch",
        "Gold/完整性疑点正文"
      ],
      "proposed_action": "保留对照诊断疑点，不冒写已证回归",
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
    "reason": "静态开发诊断候选；覆盖和gold完整性边界保留，actual actor未验"
  },
  "usage": {
    "intended_use": "development_diagnostic",
    "reviewer_exposure": [
      "本题gold",
      "本题隐藏测试",
      "run_refs授权原始grader日志/运行条件"
    ],
    "actual_actor_private_exposure": "unknown",
    "other_role_or_history_findings_read": false
  },
  "costs": {
    "tokens": null,
    "cost": null,
    "current_cpu_seconds": null
  }
}
```
