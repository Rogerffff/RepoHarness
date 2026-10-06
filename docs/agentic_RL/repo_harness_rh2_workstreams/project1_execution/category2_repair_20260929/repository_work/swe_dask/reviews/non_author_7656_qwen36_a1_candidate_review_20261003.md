# Dask7656 Qwen3.6 首候选非作者独立审查

2026-10-03。结论：**当前题目语义通过，未发现源码或有效测试的新增阻断项；公开运行说明范围保留一项 `needs_alignment`。** 原正式 reward=1 保留。该结论只属于 `gpu1003-dask7656-qwen36-a1`、`dask7656-dataclass-argument-v1`，不授通用 dataclass 正确性、稳定能力或训练资格。

本轮按题主授权只读审查。未重跑模型、CPU、控制矩阵、容器或SSH；未改封存输入、总账、题卡或共享文件。额外对比只涉及同题Coder既有封存prompt和接口。审查者未参与该候选或有效测试编写。

## 实际补丁为什么符合当前目标

公开issue要求：未初始化且不存在的 `init=False` 字段，不阻止 dataclass 作为 delayed 输入。现有修订还要求被调用函数实际收到原 dataclass 类、字段值正确、嵌套 Delayed 已求值，并检查普通默认字段对象；不新增已存在 `init=False` 字段的状态恢复要求。

实际FP源码仅改 `unpack_collections` 的112行和弃用 `to_task_dask` 的190行：字段列表增加 `if f.init or hasattr(expr, f.name)`。缺失 `init=False` 字段被跳过，避免 `getattr` 的原失败；普通初始化字段仍递归求值、合并子图，并经原有 `apply(typ, (), dict(args))` 重建原类。没有固定返回值、替换参数类型或关闭嵌套求值。正常路径由 `delayed` 的433行及 `call_function` 的609/613行进入该处理。

该谓词直接来自公开issue的workaround，是公开线索，不是私有gold泄漏。gold采用 `hasattr` 过滤所有缺失属性，本候选保留 `init=True` 字段的 `getattr`；人为删除普通初始化字段的处理不属于本轮批准范围，不能因与gold不逐字一致就拒绝该候选。

已存在 `init=False` 默认/手设/`__post_init__` 字段仍被放进构造kwargs，标准dataclass构造器可报 `unexpected keyword argument`。原base已有相同重建方式；本审查从源码判断它是未修旧缺口，未重跑反例，没有证据把它升为本轮新回归。

## 轨迹与验证

| 环节 | 实际证据及结论 |
| --- | --- |
| 定位 | 轨迹15–47行：按题面旧名称 `dataclass_fields` 搜索无结果，拓宽至dataclass后找到实际 `fields` 导入和两条分支。 |
| 修复 | 131/145行两次源码编辑均有行为变化；随后163–181行读回核对。没有无效重复编辑。 |
| 自检 | 195–199行原例返回 `Hack works`；213–217行原单测试1PASS；添加新测试后259–263行两项2PASS。未运行修复前失败对照。 |
| 纠错 | 277–281行 `--timeout=60` 不受支持，实际pytest没有执行。模型识别并去掉参数；291–295行完整test_delayed.py结果为51PASS、2XFAIL。管道到head导致工具错误标记为false，不能把前一条命令记作成功验证。 |
| 最终说明 | 305/309行准确列出两处过滤与新增测试。`All tests pass`只能指已跑的单文件范围；不等于全仓、所有Python版本或通用dataclass兼容。 |

Qwen本臂20个模型请求、19个工具调用（9 Bash、7 Read、3 Edit），输出3220 tokens。solve_seconds=27.802，CC本体24.36秒；评分384.38秒，其中trusted setup365.008574秒。求解与评分成本分列，不把setup计入模型推理速度。

正式原日志与冻结私有参考交叉核对：**1/1 F2P、48/48 P2P均PASS，无参考缺席/跳过**。完整测试文件52项：50PASS、2个非参考XFAIL，另1个非参考PASS为 `test_check_meta_flag`。这是原评分证据读回，不是本次重新运行。

## 测试编辑、评分污染与说明范围

Qwen实际FP有两个条目：`dask/delayed.py`和`dask/tests/test_delayed.py`，后者只增加未初始化字段回归测试。[评分投影](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-dask7656-qwen36-a1/grading/projection.json)只纳入源码；原评分日志318–334行证明正式测试从base恢复、SHA核对后应用固定有效测试patch，新测试没有进入正式log。未发现修改评分、测试控制、伪造stdout或访问私有题材的证据。原issue/workaround提供的是公开线索。

### A1：`needs_alignment`，不定为新共享bug或模型违令

冻结公开面含以下完整6行 `public_hints`：

```text
You are a software engineer fixing a real GitHub issue in the repository checked out at /testbed (your bash tool already runs there).
- The project's Python environment is a pre-activated conda env named `testbed`: `python`, `pip` and the repo's test tools already point at it.
- Explore the code, find the root cause, and edit NON-TEST source files to fix the issue.
- Do NOT modify test files: grading resets the test files to their original state before running the official test suite, so test edits never count.
- You may run tests to verify your fix, but keep runs narrow (a single test file or module) to save time.
- When you are confident the fix is complete, reply with a short summary and stop calling tools.
```

这些是RH2 `bundles.PUBLIC_SYSTEM_HINTS`生成的通用运行规则，**不是source issue原文**。当前原公开题面中的目标、例子和workaround已完整交付。

Qwen全部20份、Coder全部34份实际请求的 `body.system/messages`均没有上述6行。两臂的 `attempt/prompt.txt` 同为3199字节，SHA=`aaadede8cfa6a5dc0be3e9ae673951e5ed1f0067206c03ddeb90ce89dcb1d7ef`。两臂均沿用冻结code7/code8 `resolve_public_delivery` 的 `unchanged`：不追加说明，直接传 `spec.prompt`；`render_user_prompt`只渲染repo/base/issue。历史 `SweSmokeTask.system_prompt`另行承接旧hints，不代表此次普通诊断入口也消费它。

原封存probe的约定为：

> mode=unchanged；basis：原题面/hints准确且已在CPU实际首请求交付；executor须保持公开prompt字节和有效中性环境激活，拒绝任何私有调查材料

[现行统一决定](../../../../ordinary_probe_20260929/gpu_coordination_decisions_20261002.md)第52行明确不要机械追加全部旧 `public_hints`，应交付当前有效中性说明，并先纠正过时测试恢复描述。因而**字段存在不构成必须逐字送达的充分依据**。真实事实是两臂均保留prepared prompt；题主basis把题面/hints并称，与固定接口实际交付范围有歧义。

本项是沿用固定接口后新识别的措辞/验收范围问题，适用义务尚需对齐，不是已证Qwen新回归，也不能直接归为已知限制已核销。建议题主与GPU明确7656为何选 `unchanged`、哪些中性说明有效且需送达；若未来追加，保留新的说明版本和最终请求证据。此次原分、输入、源码接受范围均保留。本审查不发其它线程消息。

因此，**不能把本次新增测试判作违反模型已收到的禁止令**；也不能因公开bundle身份相同就声称全部hints实际送达。测试编辑已被评分排除，当前没有评分污染证据。

## 证据边界与原件身份

本审查逐文件重算Qwen封存148项的SHA及字节，总13,107,604 bytes，全部匹配；仅指定源码、轨迹、测试、交付和评分原件作内容审查，不声称148项全做语义审查。FP源码内容SHA为 `bf2c408907dbe65c66ef46d771b4aeea97071ba2ead760e75c5369e4f8fc3540`，测试内容SHA为 `d4e01dc9655cfdf27fcbb35019ec558ab019c008ba8bdd09a3596df0317506c1`。

| 原件 | 实际SHA256 |
| --- | --- |
| [Qwen sync回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/sync_receipt_v4.json) | `b5f8ee656b8995a0f506b6704d17c409d6f44970ab1b7e7786d2fdc0b1f6d0fa` |
| [Qwen执行回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/gpu1003-dask7656-qwen36-a1_execution_receipt_v1/execution_receipt.json) | `c69be4cd4072c1af00bb6711cae0d9471a3afe72a4181e6f51570e19d5cbc3c1` |
| [双模型回执](../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/probe-swe-dask-7656-20261003-v1_pair_execution_receipt_v1.json) | `58f49c8875e217bde6e7d912252312a1b289167007a99d9479ef8a0593230de5` |
| [冻结公开面：完整hints](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/prepared_conan11594_dask7656_code7_v1/dask7656/prepared/rollout_task_views.jsonl) | `771b5593b3650032b9a278fdd81578ab1e91e344c27d505ce9bf1538e90afe29` |
| [冻结原probe：public_delivery约定](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/prepared_conan11594_dask7656_code7_v1/dask7656/host_evidence/request.json) | `adb01532eeb93df7dab561a4f9a034cf023fce4ac3ce9c2571e66412ef133435` |
| [Qwen实际20请求](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/services_qwen_code8_v1/qwen36/gateway/first10-v1/gpu1003-dask7656-qwen36-a1/requests.jsonl) | `bfaea85f74946e030619de1a46a660781a2351532879d1c262df9a2d3957e4d4` |
| [Coder实际34请求：同题范围对比](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/services_v15/coder/gateway/gpu1003-dask7656-coder-a1/requests.jsonl) | `715a8331b269cf6813e7606cec8ebd97ff12e98123e7328706fe89fae30040d4` |
| [Coder原封存manifest](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/gpu1003-dask7656-coder-a1_closed_manifest_v1.json) | `1a379e1e4e1398b4bf4da2eee4641714f7a5e76c6e360c3d32be02b94da419cd` |
| [Qwen实际FP](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-dask7656-qwen36-a1/attempt/frozen/frozen_patch.json) | `bbe632d66f7757070f2ac81cc70d070bbd45d00090dee4459b9980aeb4d8e38e` |
| [Qwen正式原log](../../../../../../../../runs/ordinary_gpu_probe_20261002/closed_snapshots/gpu1003-dask7656-qwen36-a1/queue_qwen_first10_v1/results/gpu1003-dask7656-qwen36-a1/grading/eval_logs/evallog_gpu1003-dask7656-qwen36-_95166d70.eval.log) | `9f63afd62c8433d2fa2d6b466cb3ed091e4dbc9810ee3b5816e29c5a3fc419b9` |

Qwen20请求逐记录SHA、完整读取文件清单/字节、封存148项的机械核对清单，以及冻结code7/code8来源核对见[结构化报告](non_author_7656_qwen36_a1_candidate_review_20261003.json)。逐请求SHA按原JSONL行UTF-8字节计算，不含末尾换行。

不作新判定的范围：弃用 `to_task_dask` 的dataclass分支未单独执行；已存在 `init=False`字段/所有 `__post_init__`情形未验证；没有新增CPU矩阵；单个Qwen样本不证稳定能力；资源32次采样间隙未知、env qualification absent，未重验GPU内存权重或正式训练typed actor。双模型各首轮已执行属于执行事实；code7/code8差异及原分保持，不自动变成题目全收口或训练准入。
