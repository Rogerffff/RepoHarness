# dask__dask-7894 独立初判（封存前；2026-09-25）

审查者：e25_review_pack11_dask。结论为 needs_review / static_review：公开目标清楚，历史 noop/gold 的差异确实落在目标断言；可保留开发诊断候选，但 boundary 映射的验收有明确盲点，drop_axis 与 new_axis 组合有需要对照验证的 gold 回归疑点。不批准 ready_for_probe、训练或正式评测。

## 证据与阅读边界

以下 P 指 `runs/swegym_quality_expansion_20260925/public/dask__dask-7894`，Q 指同根 `private/dask__dask-7894`，路径均相对固定 ROOT `/Users/roger/Desktop/claude-code-verl-stage0h`。
已读公开 user_prompt、public_bundle、base_identity、environment_brief；Q 的全部新增 test.patch、全部 gold.patch、grading/validation/source_refs/run_refs，以及 environment_record 的本题环境信息。未读任何 public_read、主审稿、history、根汇总或其他题结论。

源码阅读：P/base/dask/array/overlap.py:1–180、436–752（完整 map_overlap、trim_internal、_trim、coerce helper）；core.py:455–590、640–760、760–845（map_blocks 参数、轴变换及 block_info）；test_overlap.py:1–535（直接相关旧断言与全部新增断言上下文）；test_array_core.py:3065–3126（drop/new 组合）；docs/source/develop.rst:1–140、setup.cfg。test_overlap.py:536 以后主要为窗口/重分块测试，本次未逐断言语义读完，75 P2P 的状态逐个核过但不得称为75项语义穷尽。

原件 L0/L1 为 Q/run_refs.json 指定的 `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-3/ledger.jsonl` 第7/8行。N/G 为同目录 eval_logs/evallog_replay-f216-baseline01-w_ef6aaeb0.eval.log（1–1090）和 evallog_replay-f216-baseline01-w_81567ca7.eval.log（1–867）。按授权选择器读命令、初态、目标失败、执行状态与总结；每个 expected ID 对齐两份原日志，日志 SHA 与 run_refs 匹配。candidate.patch 与 Q/gold.patch 字节相等；projection/baseline/stage 只读授权 JSON 指针，核对实际 attempt、HEAD、包含源码路径，未扩读 baseline 文件清单。

## 需求—断言双向表

| 公开需求/旧行为 | 决定性断言或调用者 | 状态与执行依据 |
| --- | --- | --- |
| 非均匀 depth 在 drop_axis 后须随保留轴重编号，结果保持正确长度和值 | 新 test_map_overlap_trim_using_drop_axis_and_different_depths；_mean 同时作用于原 dask array 和 overlap 后块，最后 numpy assert_array_almost_equal | 7 参数全部读；F2P 与 P2P 如下；无内部实现/精确图键限制 |
| boundary 同样要删除被丢轴并重编号 | 同一新测试给 (0, reflect, nearest) | 部分：三者在 trim_internal/_trim 都走 boundary != none 的相同 trim 分支。因此只修 depth、不修 boundary 的不完整解可通过全部新增例；旧 none 边界测试未与 drop 组合 |
| drop_axis 支持标量和 iterable、非排序多轴 | (0,), (1,), (2,), (0,1), (1,2), (2,0), 1 | 七参数覆盖；dropped 轴深度全部置0，避免 mean 被重复边界污染；不是暗中要求 drop 轴深度永远为0 |
| 原有 trim=False、多数组、零深度及边界行为 | test_map_overlap、multiarray/defaults/different_depths/block_broadcast/variadic、no_depth、trim_is_false 等，test_overlap.py:276–485 | 相关旧断言已读；历史全75 P2P pass，但无 trim=True+drop+new 组合 |
| map_blocks 的 new_axis 在 drop_axis 之后添加；map_overlap 转交该 kwargs | core.py:477–481、685–699；test_array_core.py:3107–3126 | 公开已存在语义；新增测试缺失，gold 未插入新轴对应零 depth，详见疑点 |

参数逐一映射（前缀均为 dask/array/tests/test_overlap.py::test_map_overlap_trim_using_drop_axis_and_different_depths）：

| ID 后缀 | drop_axis | expected 类别 | noop → gold |
| --- | --- | --- | --- |
| [drop_axis0] | (0,) | F2P | FAILED N675 → PASSED G711 |
| [drop_axis1] | (1,) | F2P | FAILED N676 → PASSED G712 |
| [drop_axis2] | (2,) | P2P | PASSED → PASSED G713 |
| [drop_axis3] | (0,1) | F2P | FAILED N678 → PASSED G714 |
| [drop_axis4] | (1,2) | P2P | PASSED → PASSED G715 |
| [drop_axis5] | (2,0) | F2P | FAILED N680 → PASSED G716 |
| [1] | 1 | F2P | FAILED N681 → PASSED G717 |

N774/826/878/929/981 分别报告 shape (10,8)→(22,4)、(5,8)→(5,16)、(8,)→(16,)、(10,)→(22,)、(5,8)→(5,16) 不符。其余两种丢末轴时保留轴编号本来未错，合理归为 P2P。

## Gold、合理替代与八方面判断

1. **身份/输入**：公开与私有 base 都是 bf4bc7dd8dc96021b171e0941abde7a5f60ce89f；gold SHA a9c18255a00d60d785d7bb9cd1cb459503261d5cf669d0bf028db8ce3cbb8f1c。source 引用与实际 candidate 绑定相符。真实 actor 输入另为 unknown，静态模板不等于实交消息。
2. **公开规格**：MCVE 和文字均给出预期；版本串“2012.7.0”不用于覆盖真实 base 身份。合理解可在 map_overlap 内规范化、在 helper 传递显式轴映射，或以等价方式修剪，不必复制 gold 的 Number/字典构造。
3. **验收覆盖/误拒**：新增断言验证用户结果，无已发现的实现锁定。boundary='none' 漏测是直接对应题意的覆盖问题，不是 gold 已经做错 boundary 的证据。随机数据无固定种子，历史仅一对运行，重复稳定性未知；shape 缺陷本身不依赖特定随机值。
4. **gold/回归**：gold 删除 dropped 轴并顺次重编号，对七例有静态和历史运行正证据。其完整性不能由5/5推出。具体静态回归疑点：`x=da.ones((5,10),chunks=(5,5)); y=da.map_overlap(lambda a:a.mean(0)[None,:],x,depth=(0,1),boundary='reflect',drop_axis=0,new_axis=0,dtype=float)`。base 的 trim 仍用 {0:0,1:1}，正好匹配输出新轴0/原轴1；gold 改成 {0:1}，会从新轴长1两侧各剪1，而原轴1不剪。预期与 `x.mean(0)[None,:]` 相同 shape=(1,10)，gold 预计异常/错误形状。未运行，check26 仍 unknown，不能写“已证 gold 回归”。负 drop_axis 不列为此题已证缺陷，因为本版本 map_blocks 也未规范化负轴。
5. **相关旧行为**：trim=False 早返回、不含 drop 的调用保持原路线；多数组选最大 rank、同 rank 取首个的既有规则不变。new_axis 与混合 none 边界的组合未被所选 P2P语义覆盖。
6. **运行/评分**：N617 是 `python -m pip install --no-deps -e .`，N641 是 `pytest -n0 -rA --color=no dask/array/tests/test_overlap.py`；gold同命令。安装 RC 都0；N1083/1087为5 failed/75 passed、test RC1，G860/864为80 passed、RC0。无 skip/xfail，全部5 F2P和75 P2P实际出现；runner parser swegym_parsers@242429c1、grader swebench-4.1.0。L0/L1 未见参考缺失、控制脚本变更；cleanup removed=true。不能从单一成功证明全部控制面安全。
7. **环境/开发**：历史 grader UID54322、deny_all、cpus=2.0、memory_bytes=4294967296；source import `/testbed/dask/__init__.py`。历史 Python3.9，包版本2021.07.0+3.gbf4bc7dd8.dirty。N210–214干净状态是在该 grader candidate恢复后的检查；G215改动为 overlap.py。git show 的 configuration.rst 是HEAD提交内容，不是初态未提交差异。原tag见public_bundle，expected manifest e66d08cf…236a，actual image ID=null；scripts_digest=57eda7b3…03a8。实际 actor 的准备后 HEAD/status/diff/忽略资产/权限/PATH/解释器仍未知。
8. **用途/泄露/流程**：本审查见 gold、隐藏测试和 grader原件，不能进入solver环境；实际 actor是否见过私料未知，check29不等于审查自身暴露。没有真实模型证据，不能判能力、成本、训练适配或已解质量；封存步骤不能证明无漏检/偏差。

## 开发需求与唯一优先下一步

| 操作/资产 | 公开依据 | 已有适用证据 | actor缺口 | 最小公开验证及预期 |
| --- | --- | --- | --- | --- |
| Python、NumPy、Dask源码可导入 | 公开MCVE；overlap模块import；develop.rst:93–119 | 历史grader editable install和源码路径 | 实际解释器/UID/工作树/可写范围 | 打印 sys.executable/dask.__file__，运行公开MCVE；base应表现原目标shape失败，修复后正确 |
| 本地数组执行与窄测试 | test_overlap.py，无外部数据/服务需求 | 历史目标文件80项执行 | actor pytest/xdist依赖及实际收集 | `python -m pytest dask/array/tests/test_overlap.py -q`；以base已有测试为准，不要求隐藏新增测试可见 |
| 可编辑非测试源码并交付 | public_hints | 历史candidate含 overlap.py | 实交hints与权限未观测 | 保存实际来源初态，不以reset消除来源改动；源码变更需真实生效 |

**唯一优先下一步**：交任务二在同条件 base/gold 私有对照中验证上述 drop_axis=0+new_axis=0 的公开API例，保存 `.shape/.chunks`、compute结果/异常与每命令RC。这一事实可把“疑似新增回归”升级或撤回；同时仍须走共用actor身份采集，不由grader成功推资格。本 reviewer 不执行命令。

## 结构记录（13个顶层字段；未列check视为not_checked）

```json
{
  "task_id": "swe_gym_lite::dask__dask-7894",
  "task_revision": "original",
  "source_adapter_ref": "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/source_refs.json",
  "recipe_ref": "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/run_refs.json",
  "code_snapshot_ref": "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/base_identity.json",
  "facts_ref": [
    "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/run_refs.json",
    "actor_environment_card.md"
  ],
  "checks": {
    "1": {
      "status": "pass",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/base_identity.json",
        "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/run_refs.json"
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
        "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/environment_brief.md"
      ],
      "by": "e25_review_pack11_dask"
    },
    "10": {
      "status": "unknown",
      "evidence_refs": [
        "开发需求与唯一优先下一步"
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
        "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/user_prompt.txt",
        "公开规格"
      ],
      "by": "e25_review_pack11_dask"
    },
    "24": {
      "status": "pass",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/test.patch",
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
        "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/gold.patch",
        "局部正证据成立，完整性未证"
      ],
      "by": "e25_review_pack11_dask"
    },
    "29": {
      "status": "unknown",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/environment_brief.md",
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
        "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/test.patch"
      ],
      "proposed_action": "保留具体覆盖边界，按唯一下一步取决定性事实，不私改评分",
      "status": "open"
    },
    {
      "category": "actor_evidence",
      "scope": "actual_actor",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/public/dask__dask-7894/environment_brief.md"
      ],
      "proposed_action": "任务二采集真实入口、消息、工作树、权限和公开开发命令",
      "status": "open"
    },
    {
      "category": "gold_completeness",
      "scope": "static_hypothesis_not_executed",
      "evidence_refs": [
        "runs/swegym_quality_expansion_20260925/private/dask__dask-7894/gold.patch",
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
