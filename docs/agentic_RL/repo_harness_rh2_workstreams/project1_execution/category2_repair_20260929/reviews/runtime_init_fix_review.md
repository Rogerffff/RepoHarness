# Git 初态一致性候选独立审查

2026-09-29。**候选代码未发现阻塞，可独立封板并执行两题原 actor 工件直评。F1 尚未关闭：必须取得完整 baseline 重建真正通过的真实证据，随后复验新 replay 的两题 noop／gold／C1 矩阵。** 本报告审代码与本地故障模型，不把本地 Git fixture 或 FakeDocker 通过写成真实镜像验收。

审查对象为 `runs/category2_repair_20260929/runtime_init_consistency_v1/code_v1`，比较来源为 `frozen_d6_v1/code_v1`。先读实际 diff、生产调用和测试，再核作者 README／测试记录。未修改候选或共享生产源，未使用远端、Docker、模型或提交。旧真实反例保留在 [F1 原件复核](d6_actor_to_grader_failure_review.md)。

后续进展：两题原 actor 工件在新封板下的直评已于同日独立复核通过，完整 baseline 逐字段相等、真实 noop 测试与清理完成；详见 [v2 原始证据审查](d6_actor_to_grader_v2_evidence_review.md)。当前尚待新 replay 六行矩阵，该进展不修改下面的代码审查范围或历史验证事实。

## 版本与实际改动

| 文件 | 独立重算候选 SHA-256 |
| --- | --- |
| `rh2/src/repoharness2/grading/manager.py` | `b6b10f98bf0e1a7bbe4774ac705ece6bb2746da2b1ac4f20394673293f24bbb0` |
| `rh2/src/repoharness2/adapters/slime/replay_grade.py` | `3bd574eed3da9372b8640eac48d5da0b1141375c21b6e492de822d494443ef66` |
| `rh2/tests/adapters/test_replay_grade.py` | `e5ef21e2cb6ac21f8b583d407e81c37a66c30ec5615a1501b4a537e72cd25af5` |
| `rh2/tests/adapters/test_pristine_git_initialization.py` | `bea5d1b56628f43eb207f575ea0e51e351f01219a46a7adc8e6b361a3a9e39bb` |

四项均匹配候选清单。独立逐字节确认 actor `generate.py`、共用 `sandbox_profile.py` 和 `contracts/baseline_manifest.py` 与旧冻结树相同。没有修改 baseline schema、canonical digest、排除区摘要、HEAD／完整 manifest 比较、原材料或 reward 语义。

实际补齐的调用链：

```text
actor（未改）：materialize probe → sanitize → trusted init/chown → baseline → CC
replay：       materialize probe → sanitize → trusted init/chown → baseline → candidate → frozen
profile grader：clone（如需要）→ probe → sanitize → full baseline equality → candidate → test
```

replay 的位置在 `replay_grade.py:347` 起，grader 位于 `manager.py:2917` 起。两处均直接调用已有 `git_sanitize_script` 和 `git_sanitize_violations`；没有另写一份 refs/repack/prune 逻辑。它们还要求 sanitizer 报告的 HEAD_BEFORE 与 HEAD_AFTER 都等于刚通过血缘 probe 的 HEAD，避免“前后同错”通过。清理时尚未写入候选字节，也未执行候选代码；replay 在清理后才 chown，避免后产生的 pack 留为 root 属主。

## 失败边界与证据

- **受信执行与输入**：新调用采用既有 `TRUSTED_ROOT_EXEC_PREFIX`，绝对 env/bash、清继承环境、系统 PATH、HOME=/root，未新增任意 shell 选择或模型控制输入。manager 的按需 import 避免包初始化循环。
- **原 actor 的环境差异保留**：actor 既有 `run_git_sanitize` 继承镜像 ENV，新 replay/grader 清环境。相同脚本和 HOME 不能证明镜像 GIT_*、PATH、BASH_ENV 全等；真实两题原工件直评是当前镜像的闭环，不能用本机三份 Git fixture 替代。
- **deadline／取消**：replay sanitizer 使用 profile 的已有预算并被整个候选阶段预算包围；grader 使用 reset 预算并经 `_exec_bash_checked` 与共同 deadline 取小。失败后走原 owner 的有界容器清理，不新增重试循环。新 14 项及独立 manager 取消探针确认取消传播、候选未执行、容器移除和阶段证据保留。
- **已交付输出**：grader 在 `_exec_bash_checked` 的 on_delivered 同步回调中先保存 facts／exit／原输出，再进入可能被取消的容器状态查询；取消侧车能引用已完成的输出。replay 将阶段 facts 与耗时写入 stage.json／ledger。超时或传输错误不被构造成 reward=0。
- **严格比较未削弱**：`_verify_baseline_rebuild` 保持完整摘要硬比较。新增测试在 sanitizer 成功后注入 `.git/unexpected`，仍真实到达 `BaselineIntegrityError('baseline_digest_mismatch')`，且没有执行候选或评分。
- **clone**：先 clone/checkout，再 probe/sanitize，未对不存在的工作树提前清理。此顺序测试只证明执行顺序；不保证任意 clone 的 `.git` 路径与 image-embedded actor 相同，完整比较继续拒绝这种不一致。

原有单事件循环／单 manager owner 不变；grader record 由评分调用写入，replay stage 由该次 replay 写入，取消路径仍在同一 owner 的 finally 收口。增加的事实字段只进入内部诊断，没有并行共享的新状态。

## 本地验证与范围

独立实际运行（候选 `code_v1/rh2` 为工作目录）：

```text
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 <项目.venv>/bin/python -m pytest -q -p no:cacheprovider tests/adapters/test_pristine_git_initialization.py
14 passed in 3.19s
```

先核 `repoharness2.grading.manager.__file__` 指向候选树，后跑上述测试。14 项覆盖两端顺序、安全执行前缀、clone、错误自证／错误 HEAD／执行异常／timeout、双端取消、排除区硬拒绝。另做只作用于本地 FakeDocker 的 manager sanitizer 取消探针，确认不进 census/apply、记录移除、close 无开放资源。

审查者第一次 pytest 调用漏设 PYTHONPATH，项目 editable 安装加载了共享旧源码，造成 12 失败和等待 sanitizer 的测试挂起；确认 import 来源后只中断自己的进程，再按上述正确命令运行。该次无效调用不计为候选缺陷，也不计通过。未用改测试期望或 skip 获得通过。

作者的相关四文件测试记录为 **126 passed / 11.75s**，ruff 通过；已读原日志，但独立未机械重跑这 126 项。作者本地 Git fixture 在受控 HOME／同一系统 Git 下得到三份相同路径摘要；其范围仅为本机原型，不覆盖真实镜像环境、UID 或正式 actor 工件。

## 非阻塞兼容边界：ReplayGrader 与无 profile manager

新 replay 总执行 sanitizer，而 `manager.py:2917` 只对配置了 sandbox profile 的 manager 执行。`ReplayGrader.__init__:303` 目前不拒绝无 profile manager 的组合。对于清理会改变 `.git` 路径的镜像，该直接 API 组合仍可能在 baseline 重建失败；这不能写成“所有旧 replay 调用保持兼容”。

本片实际使用范围不受影响：仓内 src/scripts 的唯一 `ReplayGrader` 构造在 `rh2/scripts/replay_grade.py:67/73`，显式给 manager 传 grader profile；D6 CPU 与原工件直评也明确传相同 profile。无 profile manager 单独使用的旧行为未改。新增 replay 顺序测试故意使用无 profile FakeDocker manager，只能证明候选侧顺序，fake 的恒定 census 不能证明该组合真实可评分。

**分期**：当前两题验收非阻塞，root 在交付范围明确排除上述混配。未来若要向直接 API 调用方承诺支持，应单独选择入口明确拒绝，或审查其初始化接线；不能通过忽略 `.git`、替换 baseline 或本片临时扩大无 profile 行为来处理。本报告不要求为这个范围外组合新增用户审批。

## A–N 覆盖与未收口

| 维度 | 本次依据与结论 |
| --- | --- |
| A／G | 两端实际生产调用＋HEAD 自证＋错误/timeout/cancel 分支；本地通过，真实接缝仍待验。 |
| B／F | 无评分/训练语义变化；初始化失败仍为基础设施失败且 reward=None，不能混作普通负样本。 |
| C／I | 既有 F1 继续阻塞首片整体核销；root 持有原 actor 直评与新 replay 矩阵的验收项。 |
| D／H | 同一 sanitizer 源，manager/replay owner 不变；正式 profile 消费点明确。 |
| E | 独立确认候选 import，14 个测试真进新增分支；明确 fake census 不证明镜像相等。 |
| J／K | 两处只承担生命周期接线/阶段证据，没有分叉 Git 清理算法；无新增配置语义。 |
| L | 多了一次 repack/prune，使用现有阶段与整体时限；实际耗时必须由真机记录，尚无容量结论。 |
| M | 阶段、script SHA、HEAD、自证、耗时及原始输出可追溯，取消保留侧车；真实证据不能只读自动 review。 |
| N | actor/contract/原工件未变；ENV 差异、clone 与无 profile API 的验证边界明确保留。 |

F1 关闭条件：两题原 baseline/frozen/projection 字节不改，当前材料与脚本／预算不改，新版 manager 真正完成 baseline 严格比较，随后完整安装与逐参考测试得到原 noop 的正常 0 分且清理完成。新 replay 还需原两题的 noop／gold／C1 三方结果与新增参考约束保持。该条件未满足前，旧六行材料矩阵和 actor 公开子链的已验证事实继续保留，但不宣称首片整体完成或转类。
