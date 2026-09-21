# pandas-dev__pandas-51605 — B3 对照复审

**结论：同意 needs_review / static_review，用途 development_diagnostic；保留 gold 迭代器回归为首要问题。** 公开目标与新增空列表断言相符，历史 gold 13/13 通过有原始日志支持。但新增 `len(values)` 发生在旧 iterator→list 规范化之前，非空迭代器有静态回归证据，空迭代器仍漏修；当前测试没有保护这些行为。没有执行 CPU 反例，不把强静态推断写成已实测失败或已实测错误得分。

## 封存、放行及暴露

root 在 `2026-09-20T22:05:49.422998+00:00` 重算本包两份 initial 并封存，随后明确放行对照。本题 initial SHA256=`ce75440a9c77b4d8f9554f4ad94772c80292094aa1a27727115ab1fe22850de6`；50319 initial=`848e760cd05d0ecc1f3a18441bb41b36b364c6d565473e20ac89874007c664c1`。两份 initial 未改写。

放行后只读取自己两题的 public_read、analysis_before_history、old_findings_delta、card、screening_record，及各自 history/refs.json 指向的唯一旧单题记录；未追其它任务/聚合/附件。独立阶段已见本题 gold/test.patch/F2P/P2P，environment_record 的原 noop=0、gold=1 摘要，以及同包 50319 环境摘要；本阶段又见主审与历史结论，均为已暴露 reviewer。对照主审封存稿 SHA256=`9368249d288851e632e6bf46726c2180f424edea257a331c6e58c2110a40bef6`，所读 record SHA256=`3796b2ab999c6b37411d268e52b05f9e085b77b7cb17ac4160c6af46c92760de`。之后由 root 补结构，不代表这些读取时字节未曾存在。

路径：`ROOT=.`；`I3=ROOT/runs/swegym_quality_batch03_20260921_v1`；`P=I3/public/pandas-dev__pandas-51605/base`；`Q=I3/private/pandas-dev__pandas-51605`；`B=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01`；`W=B/workers/w06-1`。结果目录为 `ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/expansion/batch03/results/pandas-dev__pandas-51605`。

## 同意、补充与限缩

| 对照点 | 复审意见及依据 |
| --- | --- |
| 公开合同与输出类型 | 同意 public_read/主审。题面原三行输入需要三元素全 False；Index.isin 公共文档 P/pandas/core/indexes/base.py:6182–6213 明确 ndarray[bool]、与 self 等长。旧记录对“Index 还是 ndarray”的疑问可由公开文档消解，不能为题面口语而放宽到错误返回类型。 |
| 新测试及 helper | 同意。唯一 F2P 用两行 MultiIndex、values=[]，assert_numpy_array_equal 对比两个 False。独立阶段读 asserters.py:598–675；对照后补核 _check_isinstance:144–169、assert_class_equal:342–373、assert_attr_equal:376–412 及 missing.py:455–542。默认严格类、ndarray、shape/value 和 dtype；无内部算法、np.zeros、别名或拷贝要求。 |
| 合理非 gold 解、#24 | 保留本题 #24 的静态支持：测试只检外部合法行为。给 isin 内的 from_tuples 提供已知 names/层数，或保留输入验证并规范化迭代器后处理空值，都有合理源码路线，未实作也不宣布通过。直接全局改变 from_tuples([]) 无 names 时的异常会冲突公开构造器测试，应避免。 |
| 首要 gold 回归 | 与初稿、主审一致。P/pandas/core/indexes/multi.py:559–562 先检查 list-like，再将 iterator 转 list；原 isin:3748–3760 会走这里。gold 在此调用前直接 len(values)，非空 iter([(1,3)]) 不再能进入旧规范化路径，空 iterator 也未修；12 P2P 没有 iterator。代码顺序与对象协议构成强静态依据，真实 base/gold 值/异常仍待实验。 |
| 新增于独立初判的输入验证问题 | **采纳主审提出并补核源码。** P/pandas/_libs/lib.pyx:1150–1159 明确排除 str/bytes；旧 from_tuples:559–560 会拒绝它们。gold 的 len==0 提前返回会让 ''、b'' 绕过验证。这是可定位的次级静态回归；初稿虽读了 is_list_like，没有单列此点，不冒称独立先发现。未跑 CPU。 |
| 两行测试与公开三行例 | 初稿已记录长度硬编码缺口，主审给出了更具体的未执行错误候选：仅空 values 分支固定返回两个 False，其余沿原路径。现有 13 项可能放过它，而公开三行原例会违反等长要求；同意这是有公开依据的漏测线索。尚未构造/运行，不写“已获 reward1”；不能据此说无条件全 False 也会通过，P2P 明确检正匹配。 |
| #3 与语义检查项 | 同意 root 将 #3 改为 unknown：原 #3 查实际收到的消息，不是题意是否清楚。实际 actor 消息未捕获；公开合同的静态判断归 #23。#25 的 issue 可表述为明确未覆盖输入族，#26/#27 由上述静态 gold 回归支持；具体错误候选的实际分数仍未知。 |
| 调用者与旧建议 | 同意 delta 撤回“Series/DataFrame.isin 都走 MultiIndex.isin”的外推。已自行补读 series.py:5324–5327，走 algorithms.isin；frame.py:11168–11204 按 dict/Series/DataFrame/一般 list-like 分派，并非统一走本方法。独立查到的真实调用者是 generic.py:4582–4608 非唯一轴 drop 的布尔 mask 路径；历史本题命令没有验证它。 |
| 非默认 level | gold 仅在 level=None 分支增加空值判断，不能把“没改 level 路径”本身当回归。旧测试覆盖 level 索引、名字和错误；空 values+错误 level 未新增验收，但现有源码没有被该 shortcut 绕过的证据。 |
| 开发条件与成本 | 同意 .py 编辑在已有兼容扩展时不必为该编辑重编 .pyx；这不证明任意 actor 已有扩展。旧“99.4% 安装时间都可免、--no-deps 能免本体构建”缺证明，不能采纳。旧 829.6 秒或 20 分钟不作为当前重放/本轮审阅成本。 |

上述新增次级问题不改变唯一主实验。除 #3 的状态归属修正、费用/资源字段范围和对静态反例的限缩外，没有未解决的实质分歧；不撤回独立初判，也不沿用旧 ready_for_probe。

## 测试、原重放和评分层次

1 F2P 与全部 12 P2P 在独立阶段逐项核对：test_isin_nan；test_isin；test_isin_level_kwarg；test_isin_missing 的 NoneType/float0/NaTType/float1/NAType/Decimal 六个参数；missing_value 的 level=None/0/1 三个参数。fixtures 来自 conftest.py:369–374 与 tm.NULL_OBJECTS（_testing/__init__.py:181）。覆盖普通 tuple 成员、缺失值、候选 MultiIndex、空 self+非空 values、level 合法/非法输入；不含 empty/nonempty iterator、空 str/bytes，也不含题面原三行+[]。实际 13 nodes、13 parser keys、冻结 1+12 refs 一一对应，本题无可见的空白截断碰撞。

原入口确为 campaign.py → worker.py → ReplayGrader.replay_one。只选 B/jobs/w06-1.json 的本题 items[10]/items[11]（0-based）和 W/events.jsonl:21–24；没有把混题 job 整包运行方案当本题实验。原 config 校验 campaign/worker 的 hash 匹配；内部 harness 仅从 `ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz` extractfile 读取历史相关成员和调用链。没有 reference wrapper 或派生配方；未来采用冻结 CLI 作为单题入口，也不改变原运行入口的事实。

| 原观测 | noop | gold |
| --- | --- | --- |
| ledger | W/ledger.jsonl 第 11 行 | 第 12 行 |
| 日志 | W/eval_logs/evallog_replay-f216-baseline01-w_f5f8cb43.eval.log | 同目录 evallog_replay-f216-baseline01-w_bff5d554.eval.log |
| 完整测试命令 | :4708 pytest -rA --tb=long pandas/tests/indexes/multi/test_isin.py | :4726 同命令 |
| 实际测试与普通退出码 | :4722–4829 原 from_tuples TypeError；:4849 1 failed,12 passed；:4857 RC1 | :4755 F2P PASSED；:4756 13 passed；:4764 RC0 |
| 参考与 reward | F2P 0/1、P2P 12/12、reward0 | F2P 1/1、P2P 12/12、reward1 |
| 原资源字段 | install_seconds=693.328；test_seconds=5.79；mem_peak_mb=1081.07；resource_facts=null | install_seconds=719.751；test_seconds=4.552；mem_peak_mb=840.5；resource_facts=null |
| 实际安装证据 | :4683 built、:4693 installed | :4701 built、:4711 installed |

原日志 SHA256 分别为 `6ee0ffdfdb152cab009277b0377b16c59dbd444e87816906d15691ef5089f460`、`4509f3f18c8e18a24f6497cb88e7ab14070dc6ea5df8150423ff726c1c35f059`，已核；原 ledger 所选行 hash 也已核。不把 log 的 13 个执行节点、parser 键、reference 和 RC/reward 混成一项。RC 在冻结 harness 仅为诊断，得分取决于 parser/reference。安装末命令是卸载 pytest-qt，末命令 rc0 不能独立证明前面成功，本题用 built/installed 原行补证。mem_peak_mb 保持原字段，不擅换单位；没有本轮资源消耗测量。

历史评分为 rh2grader/54322、deny_all，机械应用补丁身份 agent/54321；这不等于正式 actor 曾使用工具完成开发。image_id_actual=null、resource_facts=null、env_qualification 缺失，预期 manifest 身份不得冒充实际镜像 ID。原包路径 /testbed/pandas/__init__.py、Python3.8.20/NumPy1.24.4 和安装观测只适用于原重放；当前可用性未知。official test_isin.py 精确恢复/保护；multi.py 可投影 included、ignored=[]，无额外排除依据。

## 历史与跨任务暴露的范围

唯一旧单题记录为 `ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_modin_pandas/records/pandas-dev__pandas-51605.json`。它已提空 generator 的 len 问题；当前独立审查补充非空 iterator 的旧行为回归，不能只把它写成新输入不支持。旧 gold 完整性 pass 与 ready_for_probe 不沿用；旧 raw hints 中的 first bad commit/PR 信息没有重新读取源交付，不能直接当当前 solver 实际暴露。当前 public_hints 存在也不能证明已渲染给 actor。

本题公开 P/pandas/_libs/tslibs/parsing.pyx:1009–1023 包含同包 50319 gold 的完整 _fill_token 核心及注释。独立阶段已发现，放行后再次核对。仅表述为“同包晚题公开源码含早题修复”，作为跨任务上下文隔离的具体线索；不证明 Git 祖先关系、重复任务或真实 solver 已见答案。不能让本次已暴露的审阅上下文继续承担 solver 角色。

root 已指出两份 record 共 7 个 issue 缺 category/scope/evidence_refs/proposed_action/status，最终由 root 补齐，并补 checks/disposition/usage 的审阅来源字段。本 reviewer 不代改，也不让 schema 修复冲淡已存在的语义结论。初稿保持封存，新增和限缩均在本文件记录。

## 唯一优先 CPU 实验（未来，未执行）

在新建重定位副本、固定冻结 baseline grader/profile 中，做一次 **base 与原 gold 的 iterator 行为对照**。对同一两行 MultiIndex 使用 []、iter([])、iter([(1,3)])，各调用新建 iterator，记录 bool ndarray 的值/dtype/shape 或异常及导入来源；同时核题面原三行 [] 例和原 13 节点的完整执行/解析键/RC/reward。主要判据是非空 iterator 在 base 正常匹配、gold 在新增 len 处 TypeError，空 iterator 在 gold 仍不满足 empty iterable 目标。历史 gold 13/13 只作现有参照，不代替新实验。

不强制另造两份修复候选，不先要求模型运行。实验依赖固定 grader 的有效导入/源码生效；正式 actor 身份、消息/工具和开发环境资格在未来模型开发前另验。空 str/bytes 验证与固定两元素错误候选属于次级后续，不与 iterator 主实验争优先。若实验确认，未来在 isin 内保留合法输入校验与 iterator 规范化，利用 self 已知层数处理空值，并补相应行为检查；保留 from_tuples([]) 直接无 names 的原错误合同，不缩窄 iterable 以迁就 gold。

原 /work prepared/manifest 与原 job 文件本轮未动；未来只能新建重定位、exact-task 副本和独立输出。本轮未执行项目/import/测试/安装/联网/Docker/SSH/付费模型/quota/reset，未改源/tests/gold/reference/reward/expected 或提交推送；只写两题 review.md，initial 不变。token/费用无观测为 null，最终仍为 needs_review / static_review / development_diagnostic。

