# dask__dask-6626 独立初判（封存前）

2026-09-25；fresh reviewer；static_review / needs_review。建议作为“空分类列元数据一致性”的受限开发诊断候选，待 actual actor 公开复现证据。未发现必须淘汰题目的静态矛盾，但评分没有直接验证题面 set_index 两条完整用户路径，不等于完整行为资格。

## 1. 身份、公开输入与初态

public/base_identity.json 的 base 为 `56cd4597630feb1b01501c16d52aa862dd257a83`，408 个 Git 跟踪条目，静态导出记录称 blobs/path/mode 已核；本 reviewer 未再次逐 blob 对拍。public_bundle、grading.base_commit、gold hunk 所在源码相符；私有原运行 gold candidate.patch 与本包 gold.patch 字节相同且 SHA 对应 run_refs。version=2.25 与题面用户报告 2.19 是任务基线与报障版本之别，不能混为当时运行依赖。

题面完整给出 Pandas 数据、空 category 列 col1、有值 col2、两种 set_index 顺序和预期空 categories；目标可公开推断。计划 public_hints 要求改非测试源码、允许窄测试。actual actor 用户消息/system message、public_hints 实際交付、HEAD/status/diff、准备前后初态与忽略资产均 unknown。历史 noop 日志的 working tree clean 是历史 grader、可信测试应用前状态，不能代替 actual actor；git show 是基线提交内容，不是未提交变更。

## 2. 公开目标与根因/调用链

`dask/dataframe/utils.py:543–559` 中 `_nonempty_series` 遇空 categories 时用 `_nonempty_index` 造假样本，object Index 的值为 a,b（:411–412），随后 categories=None 允许 Pandas 推导新类别。`meta_nonempty_dataframe:388–401` 按 dtype 复用这些 Series，故污染列元数据。`core.py:348–350,5150–5156,5204–5206` 将假非空数据用于 map_partitions 的元数据推断。题例单调分区在 `shuffle.py:112–119` 进入 set_sorted_index 后再 map_partitions(sort_index)，后者未显式指定 meta，能把假类别传播回来。这是从源码可追溯的原因，不是本轮运行证明。

`docs/source/dataframe-design.rst:17–53` 公开说明 _meta 的 dtype/名称保持、_meta_nonempty 假数据推断及显式 meta 路径；因此修元数据辅助函数合理。`set_partition` 的 assign/shuffle 元数据路径也会受相同 helper 影响，不能只考虑两个字符的显示修补。

## 3. 需求—断言双向表（全部改动）

| 需求/旧行为 | 公开依据 | 断言及 helper | 判定 |
| --- | --- | --- | --- |
| 空 category 列不能新增类别 | 原例 col1，设计文档元数据契约 | test_meta_nonempty 新增 K=Categorical([None]*3)，纳入 columns；既有整表 dtype equality 也新增覆盖 K；新增 len(K.cat.categories)==0 | 直接覆盖 helper；历史 noop 实际先失败于 dtype equality，未到新增 len 断言 |
| 不破坏普通/已有/unknown 类别与其它 dtype | 同表 col2 + 既有元数据设计 | 同一 F2P 内 A=Alice/Bob/Carol、J=UNKNOWN_CATEGORIES；B/C/I 为 foo、D float32/E int32、F/G timestamp 时区、H timedelta；最后 A Series dtype 与整列相等 | 全部既有断言已读；保护非空分支及 dtype，但不测 col2 的完整 set_index |
| set_index 后 .cat.categories 与 compute 类别一致，两种顺序一致 | 题面核心用户行为 | 无新断言调用 dd.from_pandas(...).set_index 或 compute | 缺少端到端断言；helper 修好支持此路径是静态推断 |
| 空类别不同底层 Index 类型、ordered/name 保留 | 既有 test_meta_nonempty_empty_categories | O/f8/M8[ns]，Index 与 Series 类型、ordered/name；Series 仅 assert dtype=='category' | 相关 P2P 部分覆盖；不要求空集合数量，也不比较真正 categorical dtype 完全相等 |
| 重复列、普通 Index、多层 Index、unknown 分类、错误信息 | 既有测试 | test_meta_duplicated，meta_nonempty_index/uint64index/scalar，make_meta，check_meta，raise_on_meta_error 等 | 相关旧行为防护；不能替代空类别用户路径 |

反向看，新增 fixture/列顺序变动/新增 len 断言均服务空分类元数据要求，没有要求使用 gold 的切片写法。F2P 内那些具体假值断言是既有辅助函数契约，不是此次新增风格约束。

## 4. gold、合法非 gold、误拒与漏测/回归

gold 仅把空分类 Series 分支的 cats=None 改成 `s.cat.categories[:0]`，保留底层 Index 类型与 ordered；假样本不属于空 categories，预计转成缺失值，消除 dtype 漂移。合理替代可用保留原 dtype 的 Categorical 构造或合适的全缺失 codes；测试没有强迫这行源码。仅给 set_index 路径传入显式正确 meta 的局部修复可能满足原例却未修 helper、从而被 F2P 拒绝；公开设计支持通用元数据一致性，因此这是需界定“只修原例/修通用契约”的范围风险，尚不能断言测试误杀所有合法局部解。

漏测：可只对 object 空分类或只对 K 列处理而通过；未直接测试有序/数值/日期空 categories 的集合仍为空，P2P 只核类型不够。`_nonempty_index` 的空 CategoricalIndex 分支 :445–452 仍会构造新类别；这是未修改的相关旧行为，不是已证 gold 新回归，也不能直接扩成题面要求索引全部修复。对一般 map_partitions/dropna/groupby 全仓传播未运行、未穷举。不能据无 P2P 失败声称 26 全通过。

## 5. 历史真实 RH2 证据与原命令

仅使用 private/run_refs 指定的 `runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/{noop,gold}/ledger.jsonl:1` 和对应原日志。安装脚本 before/after 与 eval_script 全文已读：source conda，activate testbed，cd /testbed；恢复本题测试文件、应用与本包相同 test patch；离线从 `/opt/rh2/compat-wheels` 安装 pytest==7.4.4，随后 `python -m pip install --no-deps -e .`。构建原件仅 COPY wheels 保留 base layers，实际派生 image ID 为 `sha256:9776743c862cf253a473d545325b5975b3cab8f098028b4dfbe5bc0622e0b8d0`，不等同 source expected digest `sha256:a182a6a7383561f7b7a078585259c6314e60504235b4d86cf00f4fd15ef69503`。

原命令 `pytest -n0 -rA --color=no dask/dataframe/tests/test_utils_dataframe.py`；noop 日志 :454–492 为 Python3.8.19/pytest7.4.4、16 collected，目标在 patched test :142 的 dtype equality 失败，K False；:534 为 1 failed/15 passed。gold 日志 :472–522 为同命令 16 passed。两账本 F2P=0/1→1/1，14 P2P 均无失败、reference_missing/skipped=[]、num_parsed_outside_segment=0。逐 ID 与日志状态对拍见附录；额外 test_nonempty_series_sparse 不在14 P2P但实际也执行。

该额外测试使用 pytest.warns(None)，源码与修后日志可解释 pin pytest7 的兼容目标；未读修前失败日志，不能声称本 reviewer 已核原 pin 前失败原因。runner_integrity_changed=true 出现在双方，且有授权 recipe 修改证据；未把它当成候选污染或无害性的全面证明。账本记录安装 rc=0、test rc=1/0、/testbed/dask/__init__.py 导入、UID54322 rh2grader、network deny_all、cpus2.0、memory_bytes4294967296、pids512、截止3600s、cleanup removed/rm:ok。mem_peak_mb 原值 noop468.746/gold286.508，不推断单位实现。只有一次各候选，没有重复稳定性证据。

## 6. actor 开发需求（只提事实需求，不执行）

| 操作/资产 | 公开依据 | 已有证据适用谁 | 缺口 | 最小公开验证与预期 |
| --- | --- | --- | --- | --- |
| Python+Dask DataFrame/Pandas/NumPy、工作区 import | 题面 imports；setup.py DataFrame extras | 历史 grader 可 editable install/import | actual actor 解释器/版本/源码来源/权限 unknown | 实际 shell 打印 sys.executable、dask.__file__，保存 UID/HOME/cwd/PATH 和版本；应导入本候选工作区 |
| 执行题面两段公开流程 | 原题完整例子 | 历史只跑 helper 测试文件 | actor 原例与修改生效未验 | 原例对照：base 暴露 col1 元数据/计算差异；修后两种顺序的类别都空、col2保持 A；不得要求 base 全绿 |
| 窄测试及安装 | develop.rst:89–104、既有 utils 测试 | 历史 pytest7.4.4 可执行 | actor pytest兼容、可写env、pip供应路径 unknown | `python -m pytest -q dask/dataframe/tests/test_utils_dataframe.py`，检查实际收集和逐失败位置 |
| 本地数据/调度 | 题面内存数据与 shuffle 分支 | 无外部数据文件/服务的显式需求 | actor tmpdir写权限、资源尚未实测 | 运行同公开流程，按环境卡采集；不需先安装全套文档/分布式服务 |

优先需要 actual actor 两条原例完整执行并保留初态/解释器/import/退出码；由任务二获取，不在本角色执行或派发。忽略资产未导出不等于缺资产，当前未知不是必然阻断。

## 7. 提交与评分可信范围

历史 gold 投影只有 dask/dataframe/utils.py，无 ignored/unsupported paths；私有脚本恢复测试后应用可信 test patch，原 candidate 字节与 gold 相同。现有记录支持这一历史普通源码差分的交付，不证明任意候选无法改评分控制面、所有文件类型都可提交或真实 CC 完成任务。当前 actor 可写路径/提交边界仍待采集。不能据 scorer reward=1 推导诚实完整解或训练资格。

## 8. 用途、暴露、编号与实际阅读

usage.intended_use=development_diagnostic。本 reviewer 获授权见本题 gold、test patch、grading、validation、run_refs/source_refs/environment_record、原 gold candidate 和 noop/gold 日志；不送给独立 solver。这类 reviewer 私有暴露记录在 usage。29（actual actor 答案暴露）=unknown；30 网络答案可得性、31控制面完整性、33真实CC、35真实解完整性、36训练适配均未证。

编号建议：1 pass 仅静态包/引用匹配；2 pass 仅源码和历史目标失败；3/4/7/8/10/13/14/15/29 unknown（actor/稳定性）；6/9/16/17/18/19/20/21 pass 仅上述历史角色和命令；23 pass（目标可推断）；24 unknown（局部实现范围）；25 issue（端到端与空类别变体缺口）；26 unknown（无新增回归证明）；27 pass 仅目标分支静态合理/历史窄测试；28 pass 本次未加评分要求；37 pass 仅本题配方安装变更；38 unknown 当前复验；39 not_checked；40 unknown。40流程守规不能证明无漏检、误杀或样本偏差；其它未列 not_checked。

实际完整读了所有 gold/test diff、F2P 函数所有断言、test_utils_dataframe.py 全文件及 utils.py 决定分支、上述 core/shuffle 调用者和 dataframe-design 元数据部分；README/CONTRIBUTING 全文，setup/develop/配置相关段落。run_refs 引用原 ledger 精确本题行、日志安装/初态/执行/失败/summary及逐expected状态；recipe/build/image原件、candidate hash 已核。未读全仓所有源码/测试、修前未引用实验、actual actor材料、评分器实现快照内容、任何 public_read/主审/其他reviewer/旧质量结论；未进行项目执行、导入、测试、联网或子agent。源码检索输出有过截断，关键段落均分段补读，未把未呈现内容记为已人工审阅。独立初判封存后不改，等待 cross_review release。

## 附录：逐 expected ID 原日志对拍（历史，不是本轮重跑）
- gold ledger：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/gold/ledger.jsonl:1`；选中行SHA匹配=True。log：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/gold/eval_logs/evallog_replay-er19-cv1-dask__da_1ff4e1b3.eval.log`；全log SHA匹配=True。
- noop ledger：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/noop/ledger.jsonl:1`；选中行SHA匹配=True。log：`runs/env_recipe_repair_20260919/compat_v1/tasks/dask__dask-6626/noop/eval_logs/evallog_replay-er19-cv1-dask__da_0b698030.eval.log`；全log SHA匹配=True。

| 集合 | expected ID | noop日志状态@行 | gold日志状态@行 |
| --- | --- | --- | --- |
| F2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty` | FAILED @533 | PASSED @508 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_is_dataframe_like[False]` | PASSED @530 | PASSED @519 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty_scalar` | PASSED @524 | PASSED @513 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_duplicated` | PASSED @520 | PASSED @509 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_apply_and_enforce_message` | PASSED @531 | PASSED @520 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_check_matching_columns_raises_appropriate_errors` | PASSED @527 | PASSED @516 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_raise_on_meta_error` | PASSED @525 | PASSED @514 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty_index` | PASSED @522 | PASSED @511 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_check_meta` | PASSED @526 | PASSED @515 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_make_meta` | PASSED @519 | PASSED @507 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty_empty_categories` | PASSED @521 | PASSED @510 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_shard_df_on_index` | PASSED @518 | PASSED @506 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_check_meta_typename` | PASSED @528 | PASSED @517 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_is_dataframe_like[True]` | PASSED @529 | PASSED @518 |
| P2P | `dask/dataframe/tests/test_utils_dataframe.py::test_meta_nonempty_uint64index` | PASSED @523 | PASSED @512 |
