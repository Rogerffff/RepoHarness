# dask__dask-9378 独立交叉复核

结论：保留 `needs_review`、用途限 `development_diagnostic`。ones/zeros 的核心 mask equality 覆盖不足是静态实质疑点，优先于命名空间或可选参数争议；没有错误候选满分的当前运行证据。主审在 delta 中收窄 dtype/derived_from 主张有依据，我的封存初判也需要同样的条件性限定，原初判保持不改。

## 1. 独立阶段与本次阅读

本包三题 reviewer_initial 全部完成核 SHA 封存后收到明确 release，才读本题 public_read、主审 analysis/delta/card/record。history/refs精确列出的 L1_dask 与 dask_pilot 两份旧记录均先核 SHA 后全文读；没有沿它们的候选/实验/其它题链接扩读。初判已经全文读新增断言、ma.py/test_masked.py及 assert_eq/allclose 决定性 helper、gold和相关调用者，逐3 F2P/134 P2P身份和两侧原日志状态在初判附表。

本次补读 private/run_refs 指定两份 diagnostics、gold stage/projection，以及 P/base/dask/array/wrap.py:60–78、132–167、tests/test_creation.py:15–109，复读 utils.py:564–571、755–850。P=RUN/public/dask__dask-9378，V=RUN/private/dask__dask-9378。未读目标版本 NumPy 函数源码/实际签名或生成docstring，未导入/运行/联网取得它们。actual actor消息/答案可见性unknown；授权review私有暴露单列，不给solver。

## 2. 需求—测试双向核查

| 需求/断言 | 公开及源码依据 | 具体断言链 | 结论 |
|---|---|---|---|
| ones_like保留mask并产1 | 题面明示；ma+map_blocks公开建议 | test_like_funcs[ones_like]→assert_eq→allclose→np.ma.allclose(masked_equal=True) | shape/dtype/计算结果类型/可比值有约束，却无直接mask相等断言 |
| zeros_like保留mask并产0 | 同上 | test_like_funcs[zeros_like]同链 | 与ones同样的核心mask漏测疑点 |
| empty_like保留mask | 题面；empty数值不作确定性要求 | test_like_funcs[empty_like]仅比较getmaskarray | mask直接检查；返回本体dtype/type不直接保护，不能据mask结果推广 |
| ma新入口 | 题面末段明确建议 | getattr(da.ma,funcname) | 有公开依据；顶层-only完整修复的接受边界仍未执行，不能自动判误拒或强改题 |
| 分块惰性与常规行为 | Dask公开接口；asanyarray/map_blocks | 固定3×2输入，assert_eq允许NumPy或Dask输入 | 不直接要求res为Dask Array；eager返回亦可进入helper，不证明全shape、防硬编码或惰性 |

两常量分支最终不做mask数组逐元素比较是本base源码事实。对一个保持shape/dtype/MaskedArray类型及正确常量值、但all-False或过度屏蔽mask的输出，masked_equal=True可能让屏蔽位置不产生不等；静态推断足以指出 oracle 弱处，却不能替代实际错误候选的完整评分结果。empty分支直接getmaskarray比较应单列，不把它混成三分支都没检查mask。其它旧P2P确有显式getmaskarray断言（如test_masked.py:228周围），并不使新增ones/zeros自动继承该保护。

补充认可主审的eager返回缺口：assert_eq 的两边预处理可接受NumPy数组，类型比较发生在处理后；内部对Dask分支的chunks/graph检查不是入口必须Dask的断言。空分支只比较布尔mask，不能证明原结果dtype。134项相关原P2P可支持既有行为有限保留，不足以弥补新入口这两类遗漏。

Gold 三个包装用 asanyarray 与 map_blocks(np.ma.core.*_like)，默认mask保留路线合理；没有测试锁定物理实现，可用其它按块实现满足需求。对 dtype 等kwargs：map_blocks签名会消费dtype作为metadata、不会自然将其作为kernel dtype转发，这是静态机制；但题面是否承诺所有NumPy可选参数，不能由 `**kwargs` 推出。

## 3. 对 derived_from 的独立修正及文字分歧

utils.get_named_args只取显式POSITIONAL/POSITIONAL_OR_KEYWORD/KEYWORD_ONLY，排除*args/**kwargs；_derived_from比较原函数与wrapper显式参数后调用unsupported_arguments，inspect.signature抛ValueError时列表为空。因而“实际dtype必定被标成Not supported”需要该目标NumPy的可识别显式dtype签名与可匹配doc参数行，当前均未读。我的初判若读成无条件保证，应以本段收窄；主审delta与record的条件性版本成立。不能倒向另一个极端，把dtype机制直接当gold违反公开必须需求。保留支持范围unknown，不将它排在mask oracle之前。

旧“NumPy缺docstring就导入崩溃”可以直接反驳：_derived_from的doc is None明确变为空字符串；不需要靠历史pilot认可来推断。未证明所有可能依赖版本均安全。

对公开读稿保留一处措辞分歧：public_read称“不能把empty_like变成数值固定函数”若指必须检验未初始化值随机/不同，就越过公开可观察契约；同稿后段与主审均正确地不比较empty未初始化数值。已有creation测试也跳过empty数值，wrap的broadcast trick可传播单一未初始化值。应只要求公开必要属性/实现行为，不以“必须非固定数值”造硬断言；这不改变本次mask优先结论。

## 4. 八方面与原运行真实性/边界

目标/版本 base `8b95f983c232c1bd628e9cba0695d3ef229d290b` 与gold stage和公开源码对应。题面顶层mask复现与所引noop的ma入口缺失是不同证据：noop实际在getattr缺API处失败，不能称已重跑顶层复现。输入/环境方面没有actual actor消息、初始工作树、HEAD/status/diff原始RC与采集阶段、来源改动、忽略资产、UID/HOME/cwd/PATH、解释器与可写权限证据。最小masked array在内存生成不需外部数据或GPU，但未导出资产不等于环境缺失，历史安装也不证明actor可开发。

交付/可信评分方面，原gold patch字节hash与V/gold.patch吻合，stage git_apply、projection仅ma.py，ignored/unsupported为空；原diff和 `/testbed/dask/__init__.py` 导入观察支持本次gold生效。新读两份diagnostics均显示单文件apply RC0、restored/expected/present1、absent0、protected_files1。初判对17的保守unknown可在这个有限历史范围更新为pass；不是所有fixture/任意候选控制面安全结论。

原baseline01/w01-1账本严格只读11(noop)/12(gold)行，命令均 `pytest -n0 -rA --color=no dask/array/tests/test_masked.py`；Python3.10.14、pytest8.3.2，editable no-deps，安装RC0。noop912命令、1071–1104三个getattr缺API失败、1252/1253/1254分别ones/zeros/empty FAILED，1255汇总3 failed/134 passed；gold943命令、1237/1238/1239分别PASSED、1240汇总137 passed。三F2P与134P2P逐身份匹配，reference_missing/skipped为空，outside_segment0；并非本次新执行。

主审facts_ref的identity、policy/budget/raw resource、install/timing、report、projection、candidate、observations、cleanup、parser与原账本/diagnostics逐键一致。source image tag存在，expected digest `sha256:d59dc8d2aa23abc26c301754af4623f7bbad5d798713a6c5caa2d2113b6691b1`，actual image_id=null，不把expected说成实际ID；无派生维修镜像。历史UID54322/rh2grader、deny_all、cpus2、memory_bytes4294967296、pids512、deadline3600限定历史grader。raw mem_peak_mb noop287.969/gold261.359保留，不换成actor资源结论。runner pre/post一致、cleanup rm:ok；没有同状态重复运行，不证明一般稳定性。

测试有效性/覆盖/gold与回归已在表及参数段核查。无已证gold新增旧行为回归；mask遗漏是测试弱点，不是gold本身错误。暴露/用途维持check29 unknown与review usage分开、check40 unknown；静态合规不能排除误杀、漏检、抽样偏差。

## 5. 历史 delta 与结构化记录

L1的API缺失和三包装目标有据；“mask/shape硬编码不能通过”“要求chunking”等完备性主张超出断言，“逐参数可获部分reward”也未由获准评分源码验证。L1缺docstring风险被本base反驳。pilot已修正部分范围/运行解释，但未发现本次ones/zeros mask equality弱点；它的ready_for_probe、命名空间模型探针优先级不继承。两旧记录的跨题/候选/模型主张没有沿链接核验，保留未核。主审将mask诊断提高优先级、将自身dtype结论收窄均有独立源码支持，不能把历史认同数量当质量保证。

record13顶层字段、稀疏checks编号/合法状态/必备三字段、issues必备五字段均符合模板。25 issue是覆盖缺口，32 issue有明确静态oracle疑点而没有冒充mutation运行；17本次有有限新证据。6/9/23/24/27一般unknown与初判有限静态正证据可兼容。29 actual actor unknown与usage授权私有暴露分离，40unknown、quality_certified=false、revision_refs/additional_exclusions空合理。主审冻结时“未读reviewer/未收口”由协调者据本review收口，本人不改其前稿。

## 6. 唯一优先下一步

所需事实给任务二（Claude B）：私有CPU断言诊断保持shape/dtype/MaskedArray类型、ones/zeros正确常量值，只改变mask，与显式getmaskarray equality对照，保存exact命令/RC/各分支状态；区分“helper能漏放”与“完整错误候选实际获分”。本审查没有执行、修改评分或派发。该私有诊断不能认证actual actor资格；真实actor公开开发入口及输入/初态证据仍须另取得。未宣称必须先做全仓、所有反例或模型实验，亦无训练/正式评测批准。

## 封存与引用附录

本次仅新增此review.md；reviewer_initial保持原SHA。路径：

- B：`/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925`
- RUN：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925`

| 本题输入 | SHA256 |
|---|---|
| reviewer_initial.md | `6ee547743e16ad04237d35b918b85a45a4d11550f87ed6e5a7b07534f6ef4a2c` |
| public_read.md | `658d3b772f62362a282dea93c7788c7a521f716604c168b0b35828a2212f4758` |
| analysis_before_history.md | `60adde210415e69e3cfec504986bf5d5b747eaf5dbd32ea93a70d6d43b4bea3c` |
| old_findings_delta.md | `ae0a45d7293fb76a4d7503e2b649929c2bf6a3657ef4c00464072f0ee1252afe` |
| card.md | `f0b18e9308104289221c72a84620ffb92237f6dd9460542ac01e3509fc8016c8` |
| screening_record.json | `caeb89d120a6dea37a435b382e8168777fccab0d08543b8acde9209781679e28` |

历史只读refs.json中的sources；已先校验下列SHA后阅读：

- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-9378.json`，SHA256 `49439945d350b6b1fa60865297dffe5426fd4f1ffd9387a79d47b9c451ae47d0`。
- `/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/dask_pilot/records/dask__dask-9378.json`，SHA256 `2ebcee39e02a6d5456251ff3b7e034e987a9293826d4d66b359936aeb033d7c0`。

本题原运行精确引用（未读共享账本其它行）：

- noop：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl` 第11行；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_cbe4c60c.eval.log`。
- gold：`/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl` 第12行；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_36998202.eval.log`。

未进行项目执行/导入/测试、安装下载联网、容器SSH/GPU/模型实验；未改原题/测试/gold/评分/生产文件，未commit/push或派生子agent。未读原评分器实现、实际actor轨迹、完整仓库所有测试；细化实际已读范围以初判和本文列项为准。成本未获工具观测，不造token/金额/CPU耗时。
