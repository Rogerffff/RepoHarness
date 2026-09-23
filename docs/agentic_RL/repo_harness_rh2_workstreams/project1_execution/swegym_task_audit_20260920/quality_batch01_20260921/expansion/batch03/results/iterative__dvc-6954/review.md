# iterative__dvc-6954 独立最终复核

**结论：同意保留为静态开发诊断候选，状态仍为 `needs_review` / `static_review`，用途 `development_diagnostic`。未发现应先强制修订题面或测试的证据。** 唯一优先实验改采主审的正式 actor 公开 repro/lock 流程并加同形 `-0.5`；初判的负 int-only 部分候选降序，不再列为并行必做项。

初判 SHA256=`cbcd0c282984dd4a574e4570d5f75bad2611d41f907a02c0a2e2639ab0b68ab2`，保持不变。

复核保存时间：UTC 2026-09-20T21:40:54.057106+00:00；SGT 2026-09-21T05:40:54.057106+08:00。

权威 ROOT=`${REPO_ROOT}`。下文 P=`runs/swegym_quality_batch03_20260921_v1/public/本题`，V=同批 `private/本题`，R=`runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/本题`，E=`runs/env_recipe_repair_20260919/dvc_install_v1c`；均相对 ROOT，日志短后缀唯一对应本题 run_refs。

本 reviewer 先独立完成整包三份初判。协调者于 UTC 2026-09-20T21:34:52.575948+00:00（SGT 2026-09-21 05:34:52.575948+08:00）核哈希封存并明确开放后，才读取三题 public_read、analysis_before_history、old_findings_delta、card、screening_record 和各题 history/refs 唯一指向的旧记录。未回写初判，未读旧聚合/相邻题。environment_record 在独立阶段已带历史结果摘要，故独立性是未接触主审和历史质量结论，不是无结果暴露盲审。

本轮只做静态文件与 stdlib 文本/哈希核对；没有项目导入、执行、测试、安装、联网、Docker、模型或新 CPU 实验。重读历史日志不称重跑。所有后续实验和修订均为建议、未执行。未修改题面、源码、测试、gold、参考、reward 或配方；只新增本文件。


## 主审决定性主张的逐项核对

| 方面 | 最终处置与原件依据 |
| --- | --- |
| 公开目标与合理实现 | 同意。prompt 的负数 Python 参数需进入 run/repro；`_py.py:89–181` 静态赋值提取拒绝 UnaryOp，`param.py:116–138` 缺键成为 MissingParams。合理修复可保留旧 helper 并支持安全数值 USub，不必采用 gold 的 ast.literal_eval。普通负 float 合理属于数字参数范围；任意算术、执行函数或所有连续符号不自动成为硬要求。 |
| 完整 test.patch、F2P/P2P、helper | 独立初判已完整核 45 行新增文件和 13 个参数化用例，无自定义 helper/Mock。1 F2P 仅检查 `UNARY_OP = -1`；12 P2P 保护 BOOL/INT/FLOAT/STR/DICT/LIST/SET/TUPLE/NONE、class/self 与忽略 CONSTRUCTOR/SUM。返回值断言不锁 gold 实现。 |
| 覆盖与公开旧行为 | 同意主审限度。负 float、容器/注解等已有位置的负值、CLI/lock/update 未直接冻结。公开 `tests/unit/dependency/test_params.py:114–176` 和 `_py.py` 支持保留既有静态边界；“测试文件新建所以不算旧行为回归”和“必须补题面才可拒绝任意 eval”均不成立。 |
| gold 与调用者 | 同意局部静态成立，不能升级全面通过。gold 只改 `_py.py` 的值读取与 helper；已追 LOADERS → ParamsDependency → stage/lock 及 MODIFIERS → experiments 更新。复核另直接检查 `param.py:64–84,91–138`、`stage/serialize.py:109–125,175–187`，确认值比较、参数值与 lock 的关联。13 项通过不等于这些调用链已实际运行。 |
| 原件版本、初态和真实日志 | 主审解释成立。base=`28dd39a1a0d710585ff21bf66199208b1b83cbde`；noop `...9b69e9e3.eval.log:132–136` 是 clean，:213 后没有 base diff。前面的 exp diff 来自 git show 本次 base，不能当未来修复泄漏。gold `...888e8b72:685–715` 为 13 passed/RC0；noop :630–700 为 12 passed、负整数一项失败/RC1。独立核原失败是 `{}` 对 `{'UNARY_OP': -1}`。 |
| 开发条件 | 同意仅固定 grader 已验。E/recipes/本题.json 由 wrapper:61–86 消费；逐 run recipe 为审计输出。原 gold :650–670/noop :595–615 显示真实离线 editable 安装 RC0，导入 `/testbed/dvc/__init__.py`；COPY wheels 不是证明。正式 actor 的镜像、配方、UID/PATH、prefix/工作区/临时目录可写、CLI 与消息仍未知。 |
| 投影、官方恢复、评分 | 同意，不能按名称扩大排除。历史 dvc.tar.gz 中 prepared_task_face、trusted_projection、spec_vendor、scoring/parser 的精确身份与范围见初判；未用当前 ROOT/rh2。test_globs=()；唯一官方路径为新 `tests/unit/utils/serialize/test_python.py`，restored=0、apply_rc=0、expected=1；gold 投影仅 `_py.py`。执行13、解析13、冻结1+12各自对账，本次截断键均唯一且无缺失。一般 pytest RC1 不自动触发 reward0。 |
| 暴露、用途、跨题关系 | 三题 gold/隐藏测试、旧记录均已暴露，不能再承担 solver。正式 actor 可见 Git/镜像/缓存未验；无模型成功率/费用结论。跨题代码关系补证如下，未以同仓直接认定重复。 |

## 历史主张与新增关系

精确旧记录为 `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-6954.json`。同意主审对“必须补 literal-only 题面”“新 P2P 不是旧行为”“12 P2P 足以防部分实现”的纠正；当前原件不能支持这些旧推断。当前无截断 ID 碰撞，不能据旧风险自动重写参考。新离线安装事实也不能倒推旧 stage1 或正式 actor 已通过；不沿用 ready_for_probe 和旧估时。旧上游 commit 一致、全包无同路径即无关系等外推未验证。

整包原件有一个实际代码关系：3665 gold 的 `_to_relpath`/`partial` 保存链，在 4785 public base `dvc/config.py:385–399` 可见相同核心逻辑；6954 public base `dvc/config.py:230–250` 仍有该 helper/保存接线，但只在相对分支做 `localfs.path.as_posix`，绝对路径原样返回。因此三题不是同一缺陷，亦不能把更晚 base 当完全独立于早题实现的材料。当前只证明文本与核心逻辑关系，未核完整 Git 谱系，不要求自动合并或跨题更改划分。6954 HTTP 已迁移到 `dvc/fs/http.py`，没有据此断言完整保留 4785 gold。

## 下一实验与初判的变化

初判优先构造“仅支持负 int”的部分修复，以证明 reward 对负 float 的遗漏。这个候选确有具体静态依据，但新增信息集中在已知的测试输入缺口；它不能先解决正式 actor 是否能开发/运行题面链路的问题。主审建议的公开行为检查同时触及未验的 actor 入口、ParamsDependency、lock、值不变与变更检测，并包含同形负 float，因此本轮采纳其优先级。

**唯一优先实验（建议，未执行）：** 在明确身份、解释器/源码导入和固定资产的正式 actor 条件中，对同一源码状态跑公开 `-1` 的 repro → 记录实际参数 lock 值 → 不变时跳过 → 改值后重跑，再将同形参数换为 `-0.5` 重复该流程；记录候选身份和每一步结果，环境失败与语义失败分开。不向干净 solver 提供本审查私有信息。该实验成功只支持所测公开通路，不能证明冻结评分拒绝所有部分解；int-only 漏测路线保留为未验证线索，必要时另立后续版本化实验。

**剩余分歧：** 核心结论无未解决冲突；下一实验顺序已调整。gold 扩大字面量范围对 `_dump` 的边界、未测位置和正式 actor 条件仍未知。没有由静态候选升级为正式训练/评测准入，也没有新增排除或 reward 变更。
