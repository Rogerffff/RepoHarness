# dask__dask-7656 独立初判（封存前）

2026-09-25；fresh reviewer；static_review / needs_review。狭义“未设置值的 init=False 字段通过 delayed 参数/对象遍历”有公开充分需求和历史分差，可作为受限开发诊断候选。不能扩大成所有 dataclass/init=False 用法已完整修复；有未测旧 sibling 路径与已设值字段重建边界。

## 1. 身份、输入与版本

base=`07d5ad0ab1bc8903554b37453f02cc8024460f2a`，public/base_identity 428跟踪条目，包内 public/grading 源码版本相符；基线 version2021.04 与用户报障2021.03.0分别保留。原 run_refs 指定 gold candidate.patch 与本包 gold 完全相同、哈希匹配。导出 identity 中 blob/path/mode 核验是已有材料记录，未再逐 blob 复核。

题面原例 `Entry.primary_key=field(init=False,repr=False)` 无 default，other_field=4；期望 delayed(fun)(e).compute 不在 getattr(primary_key) 报错，公开 workaround 也解释未初始化字段。此 hack 是题面自带公开信息，不是 reviewer 泄漏私有答案。它使用旧 compatibility.dataclass_fields，当前 base 已直接 import dataclasses.fields；照搬 monkeypatch 路线不一定适用此基线，但根因容易由代码推断。actual actor 完整消息、hints/system/tool呈现、初始工作树/来源改动/忽略资产/权限 unknown。

## 2. 根因与相关调用者

`dask/delayed.py:110–115` 的 unpack_collections 无条件 getattr 每个 dataclass field；无 default 的 init=False 字段并不存在，遍历阶段即异常。`delayed:432–433` 和 `call_function:609–615` 都走它，字典/列表/元组/集合/切片递归保持 collection 依赖。`to_task_dask:188–193` 存在同分支，但 :155–159 已声明 deprecated。

另有 `dask/base.py:424–436` 的公共 compute/persist 对象 repack 路径，同样无条件 getattr，gold 未改。该路径与“以 dataclass 作为 delayed 参数”不同；不应把其残留归作新回归，也不能从 delayed F2P 通过推导它已修复。

## 3. 需求—断言双向表（完整补丁）

| 需求/行为 | 公开依据 | 具体断言/路径 | 覆盖 |
| --- | --- | --- | --- |
| 未初始化 init=False 不触发 AttributeError | 题面 primary_key | test_delayed_with_dataclass 唯一改动：make_dataclass 的字段增加 b=field(init=False)；dask.delayed({'a': ADataClass(a=literal)}) 触发遍历 | 直接；原 noop 在 delayed.py:112 因 b不存在失败 |
| 保留其它字段并计算嵌套 Delayed 值 | 旧 dataclass 支持、题面 other_field | literal=dask.delayed(3)，return_nested 返回 obj['a'].a，唯一终点 assert final.compute()==3 | 确实测试递归执行，不只是构图无异常；不能简单把整个 dataclass当常量或丢全部字段 |
| 题面装饰器 fun(e) 参数路径 | 原例 | 新测走 delayed(字典对象)，不是原例装饰器 | 共用 unpack_collections，源码支持；缺直接用户流程断言 |
| deprecated to_task_dask 的未初始化字段 | 既有同类分支 | test_to_task_dask P2P覆盖 list/tuple/dict/slice/namedtuple/custom collection，未含 dataclass | gold第二处修改没有目标断言；只改第一处也可能得分 |
| 已设值 init=False、default/default_factory、post_init与字段保留 | 题名概括较宽；原例只无值字段 | 无断言；构造仍 `(apply,typ,(),dict(args))` | 范围边界/漏测，不能据广义标题声称全支持 |
| compute(dataclass含Delayed) 等 base.unpack_collections | 公开 Dask collection 遍历机制 | 本题测试无覆盖 | 相关既有缺陷候选，须与狭义目标分开 |

反向看唯一 test patch 没加实现、异常文本、函数名要求；只增加能重现本题的缺失字段。F2P 所有语句/最终断言和其 helper 已完整阅读。相关 P2P：test_to_task_dask、delayed、lists/literates/iterators/kwargs/traverse_false、custom_delayed、array/bag组合、pickle/cloudpickle 均保护递归图、类型、依赖和序列化的一部分；没有保护 init=False 已存在字段。

## 4. gold、非 gold、误拒、漏测与回归

gold 在两个遍历分支过滤 `hasattr(expr,f.name)`，缺失字段跳过，有值字段继续递归；保留原构造策略，因此对原例和新增测试静态合理。合法非gold可用有针对性的安全 getattr、共享字段提取 helper 或只排除不存在的非init字段，不必复制 hasattr写法；测试无明显强制唯一实现。

限制 A：当 init=False 字段带 default/default_factory 或后来赋值时，hasattr为真，args仍把该字段传入 `typ(**args)`；标准 dataclass 自动 __init__ 不接收它，预计 TypeError。base也有同样问题，所以是未解决的旧范围，不是已证 gold新增回归。若方案一律丢 init=False 字段，可避构造异常但丢用户赋值/潜在依赖；本题新增断言无法区分。这说明不能把本题通过标成“全部init=False正确”，但是否强制新增全面支持应由公开需求边界决定，不能审查者悄悄加题。

限制 B：base.py独立遍历仍会 getattr缺失字段；把 dataclass直接交 `dask.compute` 且内部含 Delayed，与把它作为 delayed函数参数的能力分离。限制 C：to_task_dask改动没新增目标覆盖，可能漏放只修一处的实现。property自定义 getattr副作用、dataclass类对象、frozen/slots等未测；这里不把全部可能性列成准入阻断。未发现窄核心测试误拒正常递归修复；本轮未跑反例或回归。

## 5. 原运行条件与失败位置

只核 `runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-7656/{noop,gold}/ledger.jsonl:1` 与 run_refs 精确日志、recipe脚本、build/image、candidate。before/after显示恢复并打本题可信test patch；安装修订设 `SETUPTOOLS_USE_DISTUTILS=stdlib`、从 `/opt/rh2/compat-wheels` 用 no-index/no-deps安装 pandas==1.3.5、再 `python -m pip install --no-deps -e .`，未修改源码/gold或测试定义。recipe自述原因已读，但本 reviewer未核更早修前运行，不把自述当已实测失败复现。

实际派生 image=`sha256:14ab8b60db7da42443922a149ee73e099a41ce8e6362a8bf8df0158d775043d4`，source expected=`sha256:27d11a070a6af9472f390a39258cfafd3ddcd0a768963a4bc903c797c9d7b601`，COPY wheels保留base层的构建原件已读。命令 `pytest -n0 -rA --color=no dask/tests/test_delayed.py`；noop :587–594 为 Python3.9.19/pytest8.3.2、52 collected；:661–693 在 test :108 构图、delayed.py:112 getattr b 失败；:758 为 1 failed/49 passed/2 xfailed。gold :622–629 同条件52 collected，:747为50 passed/2 xfailed，F2P在:697 PASSED。两个 xfail 是旧 pickle[f1/f2]的 #3369，不能计作新故障或普通 pass。

账本 F2P0/1→1/1、48P2P无失败，逐ID对日志附后；parser52条、无段外解析、reference_missing/skipped为空、install rc0、test rc1/0、导入 /testbed/dask/__init__.py，cleanup removed/rm:ok。历史 rh2grader UID54322，network deny_all，cpus2.0、memory_bytes4294967296、pids512、deadline3600s；mem_peak_mb 原值 noop317.363/gold296.164，不推断单位实现。runner digest前后一致。历史noop的git status clean在可信test patch应用前，gold仅显示目标源码改动；git show基线提交不算初态diff。无 actual actor资格、重复评分或当前修复复验结论。

## 6. 开发需求和最小事实请求

| 操作/资产 | 公开依据 | 已有证据适用范围 | 未知 | 最小公开验证与预期 |
| --- | --- | --- | --- | --- |
| Python标准dataclasses与本工作区dask | 原题 imports；setup.py要求Python>=3.7 | 历史grader Python3.9.19/import路径 | actor激活/解释器/UID/cwd/PATH/权限 | 实际CC shell打印解释器、dask.__file__、dataclasses来源、初态status/diff并执行原例 |
| delayed构图与compute | 题面 fun(e) | 历史同helper隐藏F2P可区分 | actual actor原例未验 | 题面不带hack原例：base预计构图AttributeError，修后得到字符串；增加公开自然的 other_field读取可确认字段保持 |
| 窄pytest/editable install | develop.rst:96–110；已有test_delayed | 历史compat_v2b可运行 | actor pandas/pytest/toolz等依赖及写权限 | `python -m pytest -q dask/tests/test_delayed.py`，核实际执行而非skip/collect-only；`pip -e`仅在需要时按公开供应策略 |
| 本地数据与服务 | 纯内存dataclass+本地调度 | 无题面外部fixture/模型/服务需求 | actor资源/临时写权限未验 | 同流程记录逐命令退出码；不强制分布式集群或全仓绿 |

优先事实是 actual actor 执行原题 fun(e) 并证明候选代码生效。另保留有区分力的私有诊断需求：无值init=False对照有值init=False、delayed参数对照直接compute容器，分别定位已修/既有范围。交由任务二决定执行，本角色不运行或派发。

## 7. 可信提交与隔离边界

公开计划限制非测试文件；历史投影包含 dask/delayed.py，ignored/unsupported为空、可信测试恢复并成功应用，支持此类源码diff正常交付。真实solver的可写范围、用户级安装能力、评分控制面不可写性和真实CC交付unknown；没有因为gold reward1就证明任意解完整/诚实。

## 8. 用途、检查编号与阅读清单

usage.intended_use=development_diagnostic，reviewer看过本题私有gold/test/grading/validation、run_refs/environment_record/source_refs、原candidate与历史noop/gold，仅用于审查，不进入独立solver。29 actual actor答案暴露=unknown；题面自带hack单独归为公开输入，不能因有修复提示就错记私有泄漏。30网络答案可得性未核。

建议编号：1/2 pass 仅静态包/历史目标缺陷；3/4/7/8/10/13/14/15/29 unknown；6/9/16/17/18/19/20/21 pass 仅引用历史角色命令；23 pass窄原例、广义init=False边界保留；24 pass仅所读断言不强制算法；25 issue sibling/to_task/有值字段未覆盖；26 unknown（无新回归实证）；27 pass仅窄目标，不能写完整dataclass支持；28 pass未新增评分要求；33/35/36 unknown；37 pass仅本题环境配方；38unknown当前复验；39not_checked；40unknown。流程合规不证明漏检/误杀/抽样偏差不存在，其他未列not_checked。

已完整读gold/test补丁和F2P全部，delayed.py:1–215、415–452、597–633、base.py:392–442，相关P2P上述函数完整正文、Tuple helper、utils.py:32–36 apply、pickle参数标注；其它48P2P逐ID历史状态全核，非相关函数未声称逐体完整审读。README/CONTRIBUTING全文、setup/develop/config相关段；原ledger只本题行、日志的环境/安装/失败/测试摘要/所有expected状态，recipe before/after/build/image/candidate哈希。未读任何public_read/主审/其他reviewer/历史质量结论，全仓其余文件和actor实态未读。未执行项目、导入、测试、联网、模型、子agent。封存后不改，等明确cross_review release。

## 附录：逐 expected ID 原日志对拍（历史，不是本轮重跑）
- gold ledger：`runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-7656/gold/ledger.jsonl:1`；选中行SHA匹配=True。log：`runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-7656/gold/eval_logs/evallog_replay-er19-compat_v2b-d_874cd6d9.eval.log`；全log SHA匹配=True。
- noop ledger：`runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-7656/noop/ledger.jsonl:1`；选中行SHA匹配=True。log：`runs/env_recipe_repair_20260919/compat_v2b/tasks/dask__dask-7656/noop/eval_logs/evallog_replay-er19-compat_v2b-d_065f8159.eval.log`；全log SHA匹配=True。

| 集合 | expected ID | noop日志状态@行 | gold日志状态@行 |
| --- | --- | --- | --- |
| F2P | `dask/tests/test_delayed.py::test_delayed_with_dataclass` | FAILED @757 | PASSED @697 |
| P2P | `dask/tests/test_delayed.py::test_pickle[f0]` | PASSED @749 | PASSED @739 |
| P2P | `dask/tests/test_delayed.py::test_finalize_name` | PASSED @744 | PASSED @734 |
| P2P | `dask/tests/test_delayed.py::test_literates` | PASSED @718 | PASSED @708 |
| P2P | `dask/tests/test_delayed.py::test_keys_from_array` | PASSED @745 | PASSED @735 |
| P2P | `dask/tests/test_delayed.py::test_attributes` | PASSED @710 | PASSED @700 |
| P2P | `dask/tests/test_delayed.py::test_delayed_decorator_on_method` | PASSED @746 | PASSED @736 |
| P2P | `dask/tests/test_delayed.py::test_cloudpickle[f1]` | PASSED @751 | PASSED @741 |
| P2P | `dask/tests/test_delayed.py::test_pure` | PASSED @723 | PASSED @713 |
| P2P | `dask/tests/test_delayed.py::test_common_subexpressions` | PASSED @715 | PASSED @705 |
| P2P | `dask/tests/test_delayed.py::test_nout_with_tasks[x4]` | PASSED @730 | PASSED @720 |
| P2P | `dask/tests/test_delayed.py::test_delayed_errors` | PASSED @714 | PASSED @704 |
| P2P | `dask/tests/test_delayed.py::test_lists` | PASSED @717 | PASSED @707 |
| P2P | `dask/tests/test_delayed.py::test_delayed` | PASSED @707 | PASSED @696 |
| P2P | `dask/tests/test_delayed.py::test_custom_delayed` | PASSED @732 | PASSED @722 |
| P2P | `dask/tests/test_delayed.py::test_delayed_name_on_call` | PASSED @739 | PASSED @729 |
| P2P | `dask/tests/test_delayed.py::test_iterators` | PASSED @721 | PASSED @711 |
| P2P | `dask/tests/test_delayed.py::test_literates_keys` | PASSED @719 | PASSED @709 |
| P2P | `dask/tests/test_delayed.py::test_cloudpickle[f0]` | PASSED @750 | PASSED @740 |
| P2P | `dask/tests/test_delayed.py::test_dask_layers` | PASSED @753 | PASSED @743 |
| P2P | `dask/tests/test_delayed.py::test_name_consistent_across_instances` | PASSED @741 | PASSED @731 |
| P2P | `dask/tests/test_delayed.py::test_nout` | PASSED @725 | PASSED @715 |
| P2P | `dask/tests/test_delayed.py::test_sensitive_to_partials` | PASSED @742 | PASSED @732 |
| P2P | `dask/tests/test_delayed.py::test_kwargs` | PASSED @731 | PASSED @721 |
| P2P | `dask/tests/test_delayed.py::test_attribute_of_attribute` | PASSED @747 | PASSED @737 |
| P2P | `dask/tests/test_delayed.py::test_delayed_compute_forward_kwargs` | PASSED @736 | PASSED @726 |
| P2P | `dask/tests/test_delayed.py::test_callable_obj` | PASSED @740 | PASSED @730 |
| P2P | `dask/tests/test_delayed.py::test_lists_are_concrete` | PASSED @720 | PASSED @710 |
| P2P | `dask/tests/test_delayed.py::test_to_task_dask` | PASSED @706 | PASSED @695 |
| P2P | `dask/tests/test_delayed.py::test_nout_with_tasks[x2]` | PASSED @728 | PASSED @718 |
| P2P | `dask/tests/test_delayed.py::test_delayed_visualise_warn` | PASSED @713 | PASSED @703 |
| P2P | `dask/tests/test_delayed.py::test_methods` | PASSED @709 | PASSED @699 |
| P2P | `dask/tests/test_delayed.py::test_method_getattr_call_same_task` | PASSED @711 | PASSED @701 |
| P2P | `dask/tests/test_delayed.py::test_delayed_method_descriptor` | PASSED @737 | PASSED @727 |
| P2P | `dask/tests/test_delayed.py::test_cloudpickle[f2]` | PASSED @752 | PASSED @742 |
| P2P | `dask/tests/test_delayed.py::test_nout_with_tasks[x0]` | PASSED @726 | PASSED @716 |
| P2P | `dask/tests/test_delayed.py::test_nout_with_tasks[x3]` | PASSED @729 | PASSED @719 |
| P2P | `dask/tests/test_delayed.py::test_delayed_callable` | PASSED @738 | PASSED @728 |
| P2P | `dask/tests/test_delayed.py::test_delayed_name` | PASSED @743 | PASSED @733 |
| P2P | `dask/tests/test_delayed.py::test_np_dtype_of_delayed` | PASSED @712 | PASSED @702 |
| P2P | `dask/tests/test_delayed.py::test_delayed_picklable` | PASSED @735 | PASSED @725 |
| P2P | `dask/tests/test_delayed.py::test_delayed_optimize` | PASSED @716 | PASSED @706 |
| P2P | `dask/tests/test_delayed.py::test_traverse_false` | PASSED @722 | PASSED @712 |
| P2P | `dask/tests/test_delayed.py::test_nout_with_tasks[x1]` | PASSED @727 | PASSED @717 |
| P2P | `dask/tests/test_delayed.py::test_array_bag_delayed` | PASSED @734 | PASSED @724 |
| P2P | `dask/tests/test_delayed.py::test_operators` | PASSED @708 | PASSED @698 |
| P2P | `dask/tests/test_delayed.py::test_dask_layers_to_delayed` | PASSED @754 | PASSED @744 |
| P2P | `dask/tests/test_delayed.py::test_pure_global_setting` | PASSED @724 | PASSED @714 |
| P2P | `dask/tests/test_delayed.py::test_array_delayed` | PASSED @733 | PASSED @723 |
