# pandas-dev__pandas-51605 — 独立复核初判（封存版）

2026-09-21。角色：fresh B3 reviewer；本包 50319、51605 两题，先读原件形成独立判断。状态 **needs_review / static_review**；用途 **development_diagnostic**。本文件封存后不回写，主审/公开/旧结论比较另写 review.md。

**独立结论：公开要求清楚，新增空列表测试有效，但 gold 有强静态证据支持的迭代器回归，且漏测同属题目“empty iterable”的空迭代器。应先做 base/gold 窄回归实验，再决定测试/gold 修订。** gold 在 `level is None` 入口直接 `len(values)`；原代码先交给 `MultiIndex.from_tuples`，后者明确将 iterator 转成 list。非空 generator/zip/iterator 原来可以规范化，现在在到达该代码前就会 TypeError。现有全部 1 F2P+12 P2P 不含这些输入，原 gold reward=1 不证明无回归。

## 阅读、暴露与材料身份

仅共用四份方法卡、自己的 I3 public/private 原件、inventory common/baseline01/reference_v1 与两题 exact-id 项、精确指向的原运行材料和相关历史代码；没有读 public_read、主审稿、delta/card/record、独立 history/旧质量报告、B3 assignments/聚合、其它题结论或 analysis_reference 目标。

**已见暴露：** gold、test.patch、完整 F2P/P2P；本题 environment_record.json 只有 `baseline_pair_no_known_environment_issue` 与“original noop=0、gold=1、RC=0、无新质量/稳定性认证”摘要，已读，未追 scope_reconciliation 结论文件。本包 50319 的环境原件内附 gold/noop/安装摘要也已看到。摘要仅作为需核实材料，后续直接读原 ledger/log。不是公开盲读。

静态 stdlib JSON/hash 与 tarfile.extractfile；没有项目 import/执行、测试、安装、下载/联网、Docker、SSH、模型/quota/reset 或提交推送；没有改源/tests/gold/reference/reward/expected。

路径缩写：`ROOT=.`；`I3=ROOT/runs/swegym_quality_batch03_20260921_v1`；`P=I3/public/pandas-dev__pandas-51605/base`；`Q=I3/private/pandas-dev__pandas-51605`；`B=ROOT/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01`。下列相对引用均以此为准。

base `b070d87f118709f7493dfd065a17ed506c93b59a`，tree `a3d714b05bc870106b35b3bff6f00d7c551b7460`。source_refs 原 ingest public/grading/validation 第 154 行、导出文件 SHA 全核一致；test.patch 等于 grading.test_patch；gold 等于原 replay/gold candidate，SHA `3e268d05a6a97e89e8b031091642842ca0a7ac6768a6e04bde63b7be5b179f22`。stdlib Git blob hash 核得源码 old blob `92cb7b5fd5f4714f86966efbedc5340ba09f8f31`、测试 old blob `bf003019d538761d7384cad0b105f106d2c9b124`，均匹配补丁 index。

## 八方面与需求—断言双向映射

| 方面 | 已查事实、结论及边界 |
| --- | --- |
| 公开需求 | 全读题面、public_bundle/user_prompt。MultiIndex.isin([]) 应给与索引等长的全 False 结果，原例 3 行。题面口语称“Index”，但继承的 Index.isin 文档（core/indexes/base.py:6182–6213）明确返回 np.ndarray[bool]，因此严格数组/布尔 dtype 断言有公开依据，不构成误拒。标题与 list-like API 范围不只 Python list。 |
| 材料与初态 | core/indexes/multi.py:3748–3760 在 level=None 时把非 MultiIndex values 送入 from_tuples；:578–580 在没有 names 的空 tuples 上抛“Cannot infer number of levels from empty list”。原 noop 栈在相同路径，题面/base/补丁对应，版本号 issue 2.0.x 与材料 version 2.1 是开发序列，不足以判错配。 |
| 测试测到要求 | 全读 test_isin.py 87 行、test.patch 新用例和 helper。新 F2P test_isin_empty 用 2 行 2 层整数 MultiIndex，isin([])，assert_numpy_array_equal 对比 np.array([False,False])，覆盖报错路径与返回值/长度/dtype。helper asserters.py:598–675 验类、ndarray、形状/值与默认 check_dtype=True。没有业务源码混入 test.patch。 |
| 误拒合理解 | 新测试无内部 helper 名、调用顺序或 Mock 限制。合法非 gold 路线可给 from_tuples(values, names=self.names) 提供已知层数，让其已有 iterator 规范化处理输入；或只在合适规范化后判断空值。仅为静态候选，不声称已过。不能把全局 from_tuples([]) 改成随意单层空索引：公开 test_constructors.py:353–356 仍要求无 names 时报错。 |
| 回归/gold | 全读 MultiIndex.isin、from_tuples:516–595、继承 API 文档；lib.pyx:1099–1160 的 is_list_like 明确允许 __iter__，排除 string 等；公开 constructor iterator 测试 :367–375 使用 zip。gold 在规范化前 len(values)，非空 iterator/generator/zip 新增 TypeError，空 iterator 也未修。被读取的 12 个 P2P 无 iterator；未执行，故回归影响以强静态推断记录。 |
| 开发条件 | Python 源入口可定位；既有 pandas C 扩展及 NumPy/dateutil/pytest/hypothesis 仍是导入/测试前提。gold 只改 .py，若工作区已有兼容扩展，函数编辑无需因本变更重编 Cython；历史 grader 仍按 vendor 做了全 editable build。正式 actor 来源/PATH/依赖未验。 |
| 交付/评分 | gold 源 multi.py included，ignored=[]。官方仅恢复/保护 test_isin.py；无额外排除证据，无需写环境外文件。公共 hints 的“所有测试修改永不计分”不是 frozen 实际 general 规则，但合理源修复本题无需改测试。 |
| 关系/用途 | 本题 base parsing.pyx:1009–1023 已包含本包 50319 的 gold token 判断，属于具体跨版本答案暴露线索；本题自身修 MultiIndex，不能据同仓归为同题。不得把本审阅上下文作为 solver，不能静态推断成功率或学习价值。 |

| 需求或合理旧行为 | 公开依据 | 测试与关键断言 | 覆盖/问题 |
| --- | --- | --- | --- |
| 空列表得到与索引等长的全 False bool ndarray | issue 原例；Index.isin 文档 | 新 test_isin_empty → [False,False] | 覆盖；2 行替代 3 行没有语义冲突，但硬编码长度仍可能漏测，未构造候选。 |
| 一般空 iterable，包括空 iterator | 标题“empty iterable”；list-like、from_tuples 的 iterator 规范化 | 无 empty iterator/zip/generator 断言 | 缺失；gold len 不能处理 unsized iterable。 |
| 非空 iterator 保持 tuple 成员查询 | multi.py:559–563；lib.pyx:1150–1159；公开 constructor zip 测试 | 全 12 个 P2P 只有 list/MultiIndex 输入 | gold 新增回归，未被本题评分保护。 |
| 非空 list 成员判断、空 self 返回 bool 空数组 | test_isin.py:25–37 | test_isin，期望 [F,F,T,T]；空 self 长度=0 且 dtype=np.bool_ | P2P 覆盖；同时空 self+空 values、更多层数未增测。 |
| NaN/null 值匹配与不匹配 | :8–22、75–87 | test_isin_nan；test_isin_missing 六参数；missing_value 三参数 | 所有对应 P2P 已查；不同空值语义无明显新冲突。 |
| level 非默认值和错误级别 | :40–72；Index.isin 文档 | test_isin_level_kwarg：0/-2、1/-1、A/B；越界/浮点/未知名异常 | P2P 覆盖；gold 位于 level=None 分支，静态不改这些路径。空 values+指定 level 没有新用例。 |
| 公共调用者依赖 membership mask | core/generic.py:4582–4608 非唯一轴 drop 路径 | 评分只 test_isin.py，不跑 drop 端到端 | 已追调用位置，不能把单文件成功扩大为全部调用者回归已验。 |

P2P 共 12 个键已全部核：test_isin_nan；test_isin；test_isin_level_kwarg；test_isin_missing 的 NoneType/float0/NaTType/float1/NAType/Decimal 六 node；test_isin_multi_index_with_missing_value 的 level=None/0/1 三 node。conftest.py:369–374 的 nulls_fixture 使用 tm.NULL_OBJECTS；_testing/__init__.py:181 为 [None,np.nan,pd.NaT,float("nan"),pd.NA,Decimal("NaN")]。新增测试没有 fixture 或额外隐含 mock。13 个完整 pytest node 与 13 个 parser 键、1+12 个冻结参考一一对应，没有本次可见的空白截断碰撞。

## 决定性静态反例与非 gold 路线

以下仅是未来实验输入，没有运行：

```python
midx = pd.MultiIndex.from_arrays([[1, 2], [3, 4]])
midx.isin(iter([(1, 3)]))     # 公开语义应 [True, False]；base 可进入 from_tuples 的 list 化
midx.isin(iter([]))           # 应 [False, False]；gold 在 len(iterator) 处仍抛错
midx.isin(zip([1], [3]))      # 同一类已有支持的非空 unsized iterator
```

非空 iterator 是更有区分力的回归对照：base 先转 list 后正常建索引；gold 的新增 len 发生在这之前，不依赖猜测内部索引算法。空 iterator 则同时揭示目标覆盖不完整。返回类型、顺序和 ndarray bool 长度都有公开依据。没有把“所有 iterable 的所有可能协议”当无限新增需求，也不要求全仓穷举。

可行替代路线是利用 self 的已知 levels/names 为 from_tuples 空构造提供信息，或先保留其合法输入校验及 iterator 规范化、再处理空值；不要求采用 gold 的 np.zeros 分支。是否改变不匹配层数/特殊 iterable 的异常范围尚须窄验证，未宣称此替代路线必过。

## 原 baseline01 调用和运行事实

原运行是 **campaign.py → worker.py → ReplayGrader.replay_one**，没有 reference wrapper 或 install recipe。已核 ROOT/rh2/experiments/full216_diagnostic_20260919/campaign.py:145–153、186–200 与 worker.py:65–107；文件 hash 分别 `37e3fb31733278dbe80970706f5615a9f158442a78dcd4c94e97f51cc9bbebce`、`b5584d5266515ecb64cdb4d46715de0a1696d80c80b4ef575ed2c8b347046207`，等于 B/config.json 记录。仅选择 B/jobs/w06-1.json **items[10]、items[11]（0-based）** 本题 noop/gold，以及 B/workers/w06-1/events.jsonl:21–24；未读/打印其它 job。未来必须新建 exact-task jobs，不能直接运行混题原 job 文件。

下列 log 均位于 B/workers/w06-1/eval_logs/；ledger 为 B/workers/w06-1/ledger.jsonl：

| 角色 | ledger 行、完整测试证据 | 评分 | 原安装/资源字段 |
| --- | --- | --- | --- |
| noop | 第 11 行；evallog_replay-f216-baseline01-w_f5f8cb43.eval.log:4708 命令，:4722–4829 test_isin_empty/from_tuples 抛题面异常；:4849 **1 failed,12 passed**；:4857 RH2_TEST_RC=1 | F2P 0/1、P2P 12/12、reward 0、tests_failed | install_seconds=693.328；mem_peak_mb=1081.07；resource_facts=null |
| gold | 第 12 行；evallog_replay-f216-baseline01-w_bff5d554.eval.log:4726 命令；:4755 test_isin_empty PASSED；:4756 **13 passed**；:4764 RC=0 | F2P 1/1、P2P 12/12、reward 1、resolved | install_seconds=719.751；mem_peak_mb=840.5；resource_facts=null |

命令均 `pytest -rA --tb=long pandas/tests/indexes/multi/test_isin.py`；原日志与 run_refs 的 SHA、所选 ledger 行去换行 SHA 均复算相同。两次日志完整、parsed_outside_segment=0、reference_missing=[]、reference_skipped=[]。评分只说明以上引用集通过，不包括 iterator 路线。

原 noop 日志:2979–2982、:4683/4693；gold :2997–3000、:4701/4711 分别记录 numpy<2、editable build 和 Successfully built/installed pandas。Python 3.8.20，NumPy 1.24.4；包路径观测 /testbed/pandas/__init__.py，版本 2.1.0.dev0+44.gb070d87f11.dirty。RH2_INSTALL_RC=0 来自最后的 `pip uninstall pytest-qt -y`（noop:4694、gold:4712），**不能独立代表前面的 build 成功**；本题有成功安装原行补证。完整测试 RC 与 reward 分开，冻结 harness 的 RC 是诊断，不是直接评分闸门。

## 身份、冻结 harness 与交付边界

- manifest tasks[153] canonical SHA `4ebbdf4a25dc4b17b3afaca30b734c3eaffc6800189ec58772398e0896bae01a`；原 host_grading_views.jsonl:154 原行 SHA `812146b5a069c4dc64874ee4a50a5baa32cca5179ee74318f707375cfadc88e7`，grading 内容等于 Q/grading.json。
- 原 image_ref xingyaoww/sweb.eval.x86_64.pandas-dev_s_pandas-51605:latest；expected/identity `sha256:030bdab9144f93f67be2152375db00d2d8de10afbcfec2ddf509a8ff9cb5eccd`；**image_id_actual=null**，不是已捕获真实 image ID。image_local_build=false、derived_image_recipe=null。scripts_digest `sha256:ae72ae6c39ae543786f3902d0df7009385b4eb7a906882e804c4d2b4f43a527f`。
- 内部 harness 只从 ROOT/runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz extractfile 只读相关成员。ReplayGrader SHA `b8f1fbe2f37032e52b496f2eb9296c8a647a3072af2b7def600809544c9999fb`，prepared_task_face SHA `3a3d7bcab18e8a83f99104180e065ed32d8ecbce5d1bd4aaa7f8bd72b001aa27`；追 spec_vendor/test directives、scoring、swegym_parsers、manager 与 trusted_projection。归档 scripts/replay_grade.py 可作未来单题相同 driver 入口，不冒称原进程由该 CLI 启动。
- grader 为 rh2grader/54322，candidate_writable_prefixes=["/opt/miniconda3/envs/testbed"]，network=deny_all，cpus=2.0，memory_bytes=4294967296，pids_limit=512，shm_bytes=67108864，tmpfs_bytes=1073741824。apply_user=agent/54321 是机械补丁应用身份，**不等于正式 actor 已实际开发/验证**。默认预算秒数 candidate=900、cleanup=120、grading=3600、image pull=1800；env_qualification=absent。
- 两次 trusted_setup 恢复/应用 1 个 official 文件，control_surface 保护 1 文件成功；projection 对 gold 仅 included pandas/core/indexes/multi.py，ignored=[]；cleanup.removed=true。冻结 prepared_task_face.py:306–331 的 test_globs=()，official test 文件仍精确恢复/保护；不按所有 tests 目录一律排除，更不能用公共提示的简化说法替代代码。
- 原 summary 仍指 /work/full216_20260919/replay/{prepared,private}，目标机可用性未知。未来需新重定位 summary/manifest、独立输出和 jobs，保留原件；本轮未改写 prepared/work 文件。没有新模型测试或新 CPU 重跑。

## 逐题开发条件与缺口

| 必需操作/资产 | 公开依据 | 现有证据/适用范围 | 待验条件 | 未来最小验证 |
| --- | --- | --- | --- | --- |
| 定位 Python 实现、导入当前工作区 | issue MultiIndex；core/indexes/multi.py:3748 | base 完整；历史 grader 路径正确 | 正式 agent PATH/Python、MultiIndex 来源与镜像初态 | 实际 agent shell 记录身份/cwd/解释器和 pandas 来源，再运行原三行 DataFrame 示例。 |
| pandas 编译扩展与核心依赖 | pyproject.toml:1–9、24–30；公开构建文档 :207–228 | 历史 editable build 成功；本次 source 修改为 .py | actor 预装兼容扩展/NumPy/dateutil；必要时可写 build 路径 | 能导入则本修改不需重编 .pyx；缺扩展时准备阶段按公开构建入口解决并核来源。 |
| narrow pytest 及 fixture 依赖 | test_isin imports；pandas/conftest.py:39–49 的 hypothesis/dateutil/pytest/pytz | 原 13 节点都实际执行 | actor 是否有同类依赖与可写临时目录 | `python -m pytest -q pandas/tests/indexes/multi/test_isin.py`；配合原例/迭代器脚本，不跑全仓。 |
| 资产/服务/网络 | 数据全在题面或测试内构造 | 无下载数据、权重或运行时服务需要；grader deny_all 成功 | 环境缺包时需准备阶段固定依赖 | 不把公网访问作为本题业务前提。 |
| 提交与投影 | source 修复及 test_patch 文件集合 | multi.py 可投影，官方测试恢复；无系统文件写入要求 | 正式消息是否包含 public_hints，模型工具实际行为未知 | 验证仅源改动进入评分；不交付编译产物或改 hidden tests。 |

actor 的开发可用性需在模型探针前补齐；固定 grader 的迭代器语义诊断可以独立推进，不自动要求先跑正式 actor/模型全链。

## 唯一优先后续实验（未执行）

使用新重定位、相同冻结 baseline grader 条件，在 **base 与原 gold** 上对照原题空 list、`iter([])`、`iter([(1,3)])`（可用 zip 同类代表）三个窄输入，记录结果值、dtype/shape、异常与实际导入路径；同时保留原 13 节点的 RC、解析键和 score 对账。关键区分是“非空 iterator base 正常而 gold 在 len 处 TypeError”，以及“空 iterator gold 仍不满足题面”。原 gold 的 13/13 已有历史证据；新的 CPU 对照不能冒称已经完成。

若证实，未来只补 empty/nonempty unsized iterable 的回归覆盖，并修订候选/gold 的规范化顺序或已知层数空构造；保留原 gold/test 版本和触发反例，不为了保 gold 缩窄“iterable”定义。本轮仅列建议，没有创建修改版补丁/测试，没有改评分口径。当前不填 pass、不称 ready_for_probe；费用/token 未观测为 null；列出的安装/内存是历史原字段值，没有改单位。

