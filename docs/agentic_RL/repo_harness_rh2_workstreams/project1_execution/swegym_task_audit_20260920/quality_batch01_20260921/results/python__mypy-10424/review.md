# python__mypy-10424 独立复核收口

2026-09-21；reviewer `/root/review_mypy10424`。协调者确认并登记初判后明确开放第二阶段，才读取本题主审产物和指定历史原件。**同意主审保持 `needs_review / static_review`，用途限定 `development_diagnostic`；不沿用旧 `needs_repair`，不宣布 `ready_for_probe`。** 当前有具体评分覆盖疑点和 actor 条件缺口，没有已执行的错误候选反例、合理解误拒或 gold 回归证据。

第一阶段 [reviewer_initial.md](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/reviewer_initial.md) 保持 SHA256 `f39224dfa856ec534e7267bb091c2a9830b709c22f902ed62c8508e36e4c4c7a`，未回写。主审历史前稿 `4982fdb617b3e2c4495c553bb373ad8fae0dfad809a16523520f673c2b086a37`、配方补记 `00c4d384547796fe587e997d1852e311d5ef68001e26883974a40cb22e6fd95d` 也与已登记散列一致。本轮只新写本文件；没有执行历史项目、mypy、pytest、安装、Docker、SSH 或模型。下文 CPU 命令全部是待执行方案。

## 决定性主张复核

| 主张 | 复核处理与原始依据 |
| --- | --- |
| 核心需求、F2P、gold 一致，题面可供正常开发 | 同意。题面 `is not M` 后早退，存活路径就是 `is M` 成立；[checker.py:4232](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/checker.py:4232) 交换否定比较的两侧映射，公开类对象文档允许 `Type[C]` 表示子类。因此正向分支期望不需要从 gold 注释倒推。 |
| 唯一 F2P 内有 5 条行为断言，不是单一分支或空运行 | 同意。完整 test.patch 对 `is`/`is not` 的四个分支和末尾汇合均要求 `Type[__main__.C]`。collector 独立切 case，默认 builtins/typing fixture，真实 build，整段输出比较的链条已在独立初判核完。[noop 日志:500](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/noop/eval_logs/evallog_replay-er19-iw1-python___bbc494ef.eval.log:500) 显示两条 `<nothing>` 与三条原已正确的类型；[gold 日志:497](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/eval_logs/evallog_replay-er19-iw1-python___6bca9f92.eval.log:497) 为同一 case PASS。 |
| 没有锁定 gold 的插入点或实现形状 | 同意至已查范围。类型输出格式来自公开 `reveal_type`；可在比较约束层限定类对象/元类的处理，或在共享 narrow 层修复。两者均应保留普通实例收窄。未运行非 gold 合理解，不能把此项理解成穷尽接受性证明。 |
| gold 可交付，未发现明确回归 | 同意至原例及已读旧行为。gold 只增加 TypeType 与元类 Instance 的保守分支；[meet.py:53](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/mypy/meet.py:53) 的非重叠、Union、Any、TypeType–TypeType 等前置处理保留；`is_metaclass()` 已在 base。原始 [gold 账本](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/ledger.jsonl:1) 投影仅 `mypy/meet.py`，无忽略。完整原例、泛型/联合/特殊元类边界与更宽回归未新跑。 |
| 普通类型比较没有参考保护，适合先做窄负对照 | 同意。F2P 五条全要求维持类型，不能约束 `Any → int` 和 `Union[int,str] → int` 必须继续发生；[公开旧测试:2594](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/public/python__mypy-10424/base/test-data/unit/check-isinstance.test:2594) 给出这两个确定的旧语义。主审和我均在读历史前独立提出关闭 `find_type_equals_check` 的候选。候选得分仍未知，不能直接写 RH2 假阳性已证实。 |
| 历史运行证明环境已修复 | 限定为指定派生 **grader** 的一次 noop/gold 对照。安装完成、目标断言实际执行、角色/资源/原始日志哈希可核；不证明正式 actor 消费派生镜像，也不证明所有内部模块均从源码导入、反复运行稳定或全仓测试通过。 |
| 源码-only 修复不受官方测试恢复限制 | 同意。test.patch 仅新增数据驱动测试；[gold 日志:231](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/gold/eval_logs/evallog_replay-er19-iw1-python___6bca9f92.eval.log:231) 只恢复对应 `.test` 文件。public_hints 的禁改测试指令不妨碍本题源码路线，但其“全部测试修改都永不计分”的解释仍不能当当前机制全貌。 |
| 文件同名足以定任务同族；无 `.git`/空旧 hints 足以定无泄漏 | 不同意这些历史推断，同意主审保留未知。未核其他题补丁/祖先关系，不以同模块制定拆分规则；静态导出不包含真实镜像全部文件、Git 状态和实际 CLI 消息。 |

对应主审 [analysis_before_history.md](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/analysis_before_history.md)、[recipe_before_history.md](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/recipe_before_history.md)、[old_findings_delta.md](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/old_findings_delta.md)、[card.md](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/card.md)、[screening_record.json](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/python__mypy-10424/screening_record.json) 的关键结论均有上述范围内的原件支持。

## 与历史记录的差异

第二阶段只读取 [history/refs.json](${REPO_ROOT}/runs/swegym_quality_batch01_20260921_v2/history/python__mypy-10424/refs.json) 指定的 [09-16 本题旧记录](${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_1/records/python__mypy-10424.json:1)，未沿旧记录的 dupidx、kcheck 等线索扩读其他任务或 acceptance。

- 旧记录 16、31 行把 `is M` if 期望称为“题面缺口”。这遗漏了原例早退后的逻辑条件；主审 `old_findings_delta` 对该归因的推翻正确。复杂元类的其他边界没有在题面穷尽，并不能反过来使这个直接等价分支成为隐藏需求。
- 旧记录 33、44、54 行断言全局 `return declared` 可以满分，并据此要求修订。它提出了合理静态攻击假设，但记录内没有候选运行；不能把预期 `RESOLVED_FULL` 写成观测。当前具体缺口是已读普通收窄旧语义未被选中，不是简单 `P2P=0`。主审改用影响范围更明确的比较入口候选，并要求通过冻结 reward 且损坏旧断言才确认，处理正确。
- 旧记录建议纳入多个整文件/目录。两个 Any/Union 正向旧 case 已能区分当前候选；无需以同文件为由扩大成全量 P2P。我的初判还列了两个 final case，它们是合理回归，但对本次首个可区分实验不是必需；本稿优先集收窄至主审的两个 case，初判不改。
- 旧记录“无 stage1”是当时记录范围；现在有 09-19 指定派生 grader 的原始失败/成功对照，不能继续写“本题从未有运行佐证”，也不能将新证据倒写成当时已有 stage1。
- 旧 `hints_text=0` 与当前公开 bundle 的 harness `public_hints` 不是可直接互换的字段；旧“无泄漏”只能降到所见输入未有明示答案。旧“无 fixture”需区分无显式覆盖与实际依赖默认 stub；“正文无 URL”也不替代安装阶段依赖审查。

没有发现主审遗漏的新高影响缺陷。与主审不存在须靠多数票解决的实质分歧；存在的是证据边界和最小实验范围的明确化。

## 独立性、额外核查与未覆盖项

独立初判已先行验证全部五断言、默认 fixture、runner、F2P、gold、原始账本/日志，并读普通正负类型比较、final、链式比较、`issubclass` 类对象收窄、`isinstance(x, type)` 旧测试，以及名称/成员/下标/union 方法调用的 binder 入口。另独立重算完整 base Git tree（1485 文件、12259324 字节），与公开身份 `195a4e235fdf7ff797e6b2e38178a99dd6edd651` 一致。不是只对旧 finding 勾选。

主审额外记录过 S2 第 183 行三个源 bundle 的对象比对；本 reviewer 未再次读取 source_refs 所指整批账本或对应行。本 reviewer 的独立材料结论限于本题 bundle、导出树、内嵌/单独补丁、hunk 和指定原始运行哈希一致，不冒领主审的 S2 行级操作。

第二阶段完整读了本题 public_read 和主审允许文件、历史 refs 指向的单一原件。screening_record 合并输出曾截断，随后按范围及 JSON 字段重读，核对了全部 40 个检查的状态/说明以及 issues、disposition、file_rules、usage、costs。`6/9/16/20` 的 pass 必须连同证据文字理解为历史 grader/已投影 gold 的范围；actor 的 `8/10/13` 与实际输入继续未知。`24/27` 是已查静态范围无具体冲突，非所有合理解/所有回归的保证。reviewer 字段和“尚待 reviewer”文字可由协调者收口更新，不能因此顺带把 actor、重建或抽样结果改成 pass；我未改主审文件。

八方面结论与冻结初判保持一致：公开目标/材料/断言/合法路线/交付边界有具体支持；回归充分性有待核的具体反例；actor 与实际消息未知；跨题关系、真实镜像泄漏、模型能力/成本未查。尚未证明没有其他漏测，也没有证据要求扩大本题为完整元类交集类型实现。

## 配方与镜像适用范围

历史对照的完整条件来自 [image.json](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/image.json:2)、[build.log](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-10424/build.log:15) 及两份 ledger:1：

| 字段 | 已核值与限制 |
| --- | --- |
| base commit | `4518b55663bc689646280a0ab2247c4a724bf3c0` |
| 原镜像内容身份 | `xingyaoww/sweb.eval.x86_64.python_s_mypy-10424@sha256:d1cfbdb0f70ccb1acbf0f412197a34d491b83dfdb50b09eb09b441e9032dae41`；base local ID `sha256:079d2d9feb30ced220f840379cb9bd647aa592e21a20701b3a430e894de580d6` |
| 派生镜像 | `sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08`；recipe `install-wave1:python__mypy-10424` |
| 层变更 | 只 COPY 三种固定 build wheels 并设置 `PIP_NO_INDEX=1`、`PIP_FIND_LINKS=/opt/rh2/build-wheels`；pins setuptools 75.1.0 / wheel 0.44.0 / packaging 24.1 |
| 既有初态差异 | 两日志都已有 `test-requirements.txt` 增加 `types-typing-extensions==3.7.3`；不能归因于这个 COPY 层，也不能在 CPU 对照中只给某一组保留它 |
| 历史 grader | `rh2grader/54322`，deny_all，2 CPU / 4 GiB；Python 3.9.19、pytest 6.1.2；scripts digest `7e77c7897cbefd592c00f2b8a9b5056c767a8a9e10a10c6636d4d0052b4373fa` |
| actor | 正式 profile 是 agent/54321；是否实际选用派生镜像、激活解释器/允许源码生效/有合适权限，均未运行核验 |

这三个 wheel **不是完整环境依赖锁**；日志显示 pytest、typed_ast 等大量需求来自保留的原镜像环境。把三个 wheel 复制进任意新环境不等于重建了本题已验条件。优先在 CPU 负责人已保留、核过 ID 的同一派生镜像上做对照；若需重建，使用原 base digest 和同版本 wheel 配方，记录新的 image ID，不能悄悄换 public `:latest`、只给 gold 使用修复镜像或把 tag 当不可变身份。未验证 layer/wheel 全部可见内容，也未执行独立重建。

## 有界 CPU 三组方案（全部未执行）

这是协调者统一 CPU 入口的执行规范，**不是本地静态包上的运行结果，也不是新建 actor 启动方式**。三组使用同一个 base、同一个固定派生镜像、同一 grader profile/安装与冻结评分参考；每组用独立新工作区，保留相同环境初态差异，不按顺序在同一脏工作树覆盖补丁。

| 组 | 普通源码输入 | 不变项 | 判别预期，不是事实 |
| --- | --- | --- | --- |
| base/noop | 无候选源码补丁 | 原官方 test.patch，由受信流程恢复/注入 | F2P 失败；旧 Any/Union 收窄通过 |
| gold | 本题 validation/gold.patch，SHA `0bc6c39bdd85a3ddd99913d868e153bcf3a3292f90ac35e577b4bcc2712bba23` | 同上 | F2P 与旧收窄均通过 |
| comparison_disabled | 只在 `find_type_equals_check` 的 docstring 后、原 `type_map = self.type_map` 前插入 `return {}, {}` | 同上，不改任何测试/helper/config | F2P 可能通过，但旧正分支保留 Any/Union 而失败 |

候选应使用下面这个完整源码差异；其旧 hunk 六行已仅用文本与 base 校验匹配，尚未写成补丁文件、应用或执行：

```diff
diff --git a/mypy/checker.py b/mypy/checker.py
--- a/mypy/checker.py
+++ b/mypy/checker.py
@@ -3966,6 +3966,7 @@
             expr_indices: The list of indices of expressions in ``node`` that are being
                 compared
         """
+        return {}, {}
         type_map = self.type_map
 
         def is_type_call(expr: CallExpr) -> bool:
```

**A. 三组标准 RH2 得分。** 下列 flags/候选输入形式来自已获准读取的 [run_install_wave1.py:54](${REPO_ROOT}/runs/env_recipe_repair_20260919/install_wave1/run_install_wave1.py:54)；保留原 grader 的 `pytest -n0 -rA -k testNarrowingUsingMetaclass`，不把下面额外旧测试偷偷并进 reward。

CPU 负责人须先把 `CPU_RH2_PYTHON`、`CPU_REPLAY_SCRIPT`、`CPU_PREPARED_SUMMARY` 设为**同一受信 CPU 部署**的实际绝对路径；`CPU_GOLD_DIR` 和 `CPU_MUTANT_DIR` 分别包含且仅用于本题的 `python__mypy-10424.gold.patch`（前者为原 gold，后者为上面的负对照，各自记录 SHA）；`CPU_OUTPUT` 是新输出目录。不能把本机材料路径当成远端路径，也不能假设这些变量或该 local image ID 当前已存在。这是显式部署前提，未检查当前 host。

```bash
: "${CPU_RH2_PYTHON:?set trusted RH2 Python absolute path}"
: "${CPU_REPLAY_SCRIPT:?set trusted replay_grade.py absolute path}"
: "${CPU_PREPARED_SUMMARY:?set matching prepared summary absolute path}"
: "${CPU_GOLD_DIR:?set original gold patch directory}"
: "${CPU_MUTANT_DIR:?set comparison-disabled patch directory}"
: "${CPU_OUTPUT:?set new output directory}"

task_image='sha256:362a2da70c5f90f6b7909ed92a8a8bceb9d9377cf822c0b170f45bc48f3e2a08'
task_recipe='install-wave1:python__mypy-10424'

task_replay_group() {
    local task_group="$1"
    local task_candidate="$2"
    mkdir -p "$CPU_OUTPUT/$task_group"
    "$CPU_RH2_PYTHON" "$CPU_REPLAY_SCRIPT" run \
      --prepared-summary "$CPU_PREPARED_SUMMARY" \
      --task-ids python__mypy-10424 \
      --candidate "$task_candidate" \
      --derived-image "$task_image" \
      --derived-image-recipe "$task_recipe" \
      --eval-log-dir "$CPU_OUTPUT/$task_group/eval_logs" \
      --artifacts-dir "$CPU_OUTPUT/$task_group/artifacts" \
      --ledger "$CPU_OUTPUT/$task_group/ledger.jsonl"
}

task_replay_group base noop
task_replay_group gold "gold-dir:$CPU_GOLD_DIR"
task_replay_group comparison_disabled "gold-dir:$CPU_MUTANT_DIR"
```

`gold-dir:` 是上述已读历史入口的补丁目录输入协议名，不代表其中补丁正确。负对照必须始终用 `comparison_disabled` 标记，并按 origin/patch SHA 识别；不能把可能由该协议写出的 `candidate.kind=gold` 当参考答案。此方案不声称已审阅当前所有 CLI/部署版本；若统一入口已升级，由负责人核对这些既有 flags 的兼容性及实际 scripts digest，另记执行条件。不能将运行入口错误当作本题语义结论。

**B. 每组相同的直接行为诊断。** 由统一 CPU 入口在与该组补丁一致的隔离 `/testbed` 中各执行一次下列命令，捕获 stdout/stderr/exit code 和输入补丁 SHA。不要复用已自动清理的 grader 容器；直接诊断和标准 RH2 的共同镜像/源码/依赖条件要能对应。B 的结果单列，不冒充 A 的 reward，也不交给未来 solver。

先记录实际来源；`.so` 或工作区外导入不能仅凭路径就判错，但必须核查候选源码确实生效：

```bash
cd /testbed
id
pwd
PYTHONPATH=/testbed python -c 'import os, sys; import mypy, mypy.checker, mypy.meet; print("HOME=" + str(os.environ.get("HOME"))); print("PATH=" + str(os.environ.get("PATH"))); print(sys.version); print(sys.executable); print(mypy.__file__); print(mypy.checker.__file__); print(mypy.meet.__file__)'
```

精确题面原例包含 `D`、`f(D)` 和 early return，用 mypy 静态检查，不能把含 `reveal_type` 的示例当普通 Python 程序执行：

```bash
cd /testbed
PYTHONPATH=/testbed python -m mypy --no-incremental --cache-dir=/dev/null -c 'from typing import Type

class M(type):
    pass

class C: pass
class D(C, metaclass=M): pass

def f(t: Type[C]) -> None:
    if type(t) is not M:
        return
    reveal_type(t)

f(D)
'
```

直接诊断工作区已由 CPU 入口注入冻结 test.patch 后，可准确定位 F2P 节点；若未注入，报“节点不存在”只是准备错误：

```bash
cd /testbed
PYTHONPATH=/testbed python -m pytest -n0 -rA \
  mypy/test/testcheck.py::TypeCheckSuite::testNarrowingUsingMetaclass
```

最小公开旧行为使用两个精确 pytest 节点，避免把 `.test` 数据文件误当 pytest 文件；已静态核验两 case 名各出现一次，且 `check-isinstance.test` 在该 suite 的收集列表中：

```bash
cd /testbed
PYTHONPATH=/testbed python -m pytest -n0 -rA \
  mypy/test/testcheck.py::TypeCheckSuite::testTypeEqualsCheckUsingIs \
  mypy/test/testcheck.py::TypeCheckSuite::testTypeEqualsNarrowingUnionWithElse
```

判定同时需要：A 的负对照实际 reward=1、参考无 missing/skipped、安装/收集成功，B 的该候选出现明确 Any/Union 正分支输出退化，而 base/gold 的同两个旧 case 通过。原例也应检查 reveal 内容和 `f(D)` 无新增类型错误，不能仅依据退出码。如果候选没过 F2P、gold 破坏旧行为、直接入口没有导入该候选，或任一组遭遇依赖/权限/收集故障，按相应日志重新归因，不宣布预设漏测已证实。

## 最终有界处置

保留原题和原评分版本，额外 exclusions 为空。先做上述单一有区分力的 CPU 实验，不先扩为全仓回归或改公开规格。若漏测被证实，独立评分修订可优先吸收原有 Any/Union 正向旧测试，并核 base/gold/合理替代解/错误候选；不能为保 gold 放宽要求，也不能只凭负对照得分就宣布全部任务用途无效。

即使 CPU 证实当前评分不足，本题仍可在补丁审读和旧行为复查伴随下用作探索性开发诊断；若要独立依赖 reward 统计修复质量，应先完成有依据的评分修订。任何模型探针之前还需核正式 actor 的实际 image/recipe 消费、UID/HOME/cwd、shell/PATH/解释器、相关模块来源、公共原例及公开测试、临时目录/依赖权限、真实消息与清理；这组 actor 验证不能由历史 grader 或上述直接诊断替代。静态初筛候选与运行已验准入保持分开。
