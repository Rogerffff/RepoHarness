# pandas-dev__pandas-48106 — 独立初判，阶段一

审查日：2026-09-21。建议 `state=needs_review`、`scope=static_review`、`intended_use=development_diagnostic`。核心需求、gold 和新增测试相符；历史配方加参考绑定的 grader 对照可解释，但正式 actor 的环境消费和开发条件尚未验收，不能自动转成正式准入。本轮只读文件/JSON/hash/只读 Git，没有导入 pandas、运行测试、安装、容器、联网或模型，也未改 source/test/gold/reward。

路径缩写：`ROOT=.`；`I=ROOT/runs/swegym_quality_batch02_20260921_v2`；`B=I/public/pandas-dev__pandas-48106/base`；`P=I/private/pandas-dev__pandas-48106`；`R=ROOT/runs/env_recipe_repair_20260919/pandas_meta_v3`；`T=R/tasks/pandas-dev__pandas-48106`。

**阅读/暴露声明。**独立上下文未读任何 public_read、主审/其它 reviewer、card、screening_record、旧质量历史、B1/B2 聚合/manifest/assignments/method_adjustments/CPU 计划。一次读取完整授权原始包 `P/environment_record.json`，看到了其环境 summary/checks/observations、原运行结果及 history 字段中的三个环境批次/analysis 路径/roles 索引，不只是键名；未打开这些 history/analysis 指针。以下重要环境结论重新用 own run_refs 的原账本、日志、配方/镜像/资产/审计输出核实。有限暴露已向协调者报告；不称对原环境结果完全盲审。未读任何质量结论；三题初判全部保存后等待统一开放。

## 1. 公开需求、初态和材料

题面明确要求：向 `Series(["a", "b", "c"], dtype="category")` 的新标签 `3` 写数值 `0` 应得到 object dtype 的 `a,b,c,0`，不能抛内部 `type.__new__` 错误。base `pandas/core/indexing.py:2082–2130` 的 Series enlargement 调用 `maybe_promote`；`cast.py:575–705` 未处理 CategoricalDtype，整数 0 最终进入 `dtype.type(value)`（`_ensure_dtype_type:708–731`），与题面调用链一致。是否保留 category 对已在类别集中的值及 NA，可从 categorical 的验证逻辑、concat 语义与公开文档推导，不能把所有 enlargement 都机械转 object。

base `8b72297c8799725e98cb2c6aee664325b752194f`，tree `3c8a3b297944a7804b18fceafd7e710af22e729b`。公开/grading/validation JSON 与对应 S2 JSONL 第 152 行一致。test.patch SHA256 `aec2e587f0094d68a2679591548b601fec2a4c54af3ca5a0bfa6a29e65532be2`；gold.patch `cf099ba87549e41673503275a6e66263685a795770c42c373d1fd41554fed23d`。未重复全包 blob 审计。原 noop 的内部 TypeError 和 dtype 失败来自实际测试栈，支持初态确有问题。

公开 hints 的 non-test 修复限制对本题不构成业务入口冲突；cast.py 或 indexing.py 均为可提交源码。其 conda 已激活不是 actor 运行证明，旧“所有测试修改都恢复”的解释也不能替代当前精确路径机制。提示消息仅有静态渲染值，未核验本轮 CLI system message、自动附加消息或工具进程环境。

## 2. 双向需求—测试映射

官方 test.patch 只改 `pandas/tests/indexing/test_loc.py`：新增 CategoricalDtype 导入及四个测试函数，全部新增断言已读。全部 **16 F2P** 都属于 `TestLocWithMultiIndex`，实际输入却是普通 Series；类名不意味着只测 MultiIndex。

| 需求／旧行为 | 公开依据 | 全部新增断言及 F2P 参数 | 评价 |
| --- | --- | --- | --- |
| 新标签写入类别外数值应 object 扩容 | 题面精确原例 | `test_additional_element_to_categorical_series_loc`：写 0 后与 object Series 等值 | 直接覆盖原例；值、索引、dtype 均比较 |
| 已有类别值扩容保留类别 | Categorical `_validate_scalar`，concat_compat 同 dtype 保留；文档 categorical.rst:761–789 | `test_additional_categorical_element_loc`：新增 "a" 后与 category Series 等值 | 合理相邻旧行为，不要求特定 helper 实现 |
| 数值扩展类别可表示 NA，并与已有位置写 NA 一致 | 文档 categorical.rst:983–1008；categorical.py:1565–1590 接受合法 NA；Series enlargement 的 NA 分支 | `test_loc_set_nan_in_categorical_series[UInt8,UInt16,UInt32,UInt64,Int8,Int16,Int32,Int64,Float32,Float64]`：先 enlarge 到索引3，断言 dtype/内容；再把索引1设 nan，再次断言 | 10 F2P，两个断言均已核；不是只看第一个扩容结果 |
| 常见 NA 值在扩容/已有位置赋值间一致且维持类别 | 相同 categorical NA 约定 | `test_loc_consistency_series_enlarge_set_into[nan,na1,None,na3]` 对应 np.nan、pd.NA、None、pd.NaT：先比较两个路径，再与显式 category expected 比较 | 4 F2P；第二个断言防止两条路径同时错成 object 却相等 |
| 普通、混合、已有类别列、空 Series/非唯一索引扩容保持旧行为 | base `test_loc.py` | P2P 中 categorical partial-column、single-row、column-retains-dtype，empty-series/float/str-index、mixed-dtype append、nonunique-index expansion 等 | 相关正文已读；不是把 1020 个参考名都当已审完 |

fixture `pandas/conftest.py:1524–1541` 明确 8 种 nullable 整数及 2 种 nullable 浮点；无外部数据 fixture。`tm.assert_series_equal`（`_testing/asserters.py:865–885,1017–1030,1120–1130`）默认检查 dtype、索引、名称与 categorical categories/order，新增断言确实区分类别与 object。具体值都是内存内构造，没有远程资产或服务需求。

## 3. Gold、替代解和实际阅读范围

gold 在 `_maybe_promote` 的一般 NA/数值分支之前加 CategoricalDtype 分支：类别内值或 NA 保留 dtype，其它值返回 object；没有改变其它 dtype 分支。已读 maybe_promote 的缓存及非 scalar 分支、整个 `_maybe_promote` 与 `_ensure_dtype_type`、Series enlargement、`concat_compat:69–140`、categorical scalar validator；还查 `take_nd:60–107` 与 reshape:235–270 的调用约束，后两者对扩展数组有专门分派，不可把通用 maybe_promote 的调用数量当成 Categorical 必走的路径。

合理非 gold 路线是在 Series enlargement 中单独保留 Categorical 已有类别/NA、对新类别选 object；只要公开语义一致，官方断言不限定必须改 cast.py。自然部分实现“Categorical enlargement 全部转 object”会恢复题面 0，但其它 **15** 个 F2P 会拒绝；“给全部新值扩充 categories”则违反题面 object 结果并被原例断言拒绝。没有具体证据支持必须另造攻击样例或要求全仓测试才允许诊断。空 category、更多 scalar 种类、直接调用 maybe_promote 的非标准扩展 dtype 没有穷举，不补成已通过，也不把这些一般空白全部设硬门。

P2P 正文实际读范围：`test_loc.py:225–275` 的 7 个 Period/MultiIndex 参数及 KeyError helper、1158–1185 的 mixed append、1380–1425 的类别赋值、1815–1985 的相邻类别/扩容、2007–2046 的非唯一索引扩容；已读新增四函数全部与 fixture/helper。另读 `pandas/conftest.py:300–305` 的 ordered=True/False/None、555–652 的 indices_dict/index 及两种 MultiIndex 构造；index参数广泛不代表类别值扩容被所有这些旧测试保护。未逐字读完全部 1020 P2P 的参数及无关布尔、slice、时区、全部标量转换；未读全仓测试。公共 categorical 文档及相关源码支撑本题所需旧行为，不证明全部回归。

## 4. 实跑、冻结参考、解析绑定是三套集合

冻结 grading 仍是 **16 F2P + 1020 P2P**。历史命令整文件运行 `pytest -rA --tb=long pandas/tests/indexing/test_loc.py`，实际收集 **1045** 项。gold 为 1044 passed + 1 xfailed；noop 为 16 failed + 1028 passed + 1 xfailed。本人正文阅读集合见上节，不等于上述两个大集合。

只读取 `R/reference_bindings_v1.json` 的 `tasks[pandas-dev__pandas-48106]`。它把三个含空白/转义的冻结 P2P alias 映射到 `test_contains_raise_error_if_period_index_is_in_multi_index` 的七个完整 pytest node：2017 组2个（key5,6）、2019 组3个（key0,2,1）、2018 组2个（key4,3）。这不是把所有 1020 参考重建为完整 node，更不是新增七个评分项。

已读 `ROOT/rh2/experiments/env_recipe_repair_20260919/reference_bindings.py:14–71`：仅宿主冻结显式绑定；每个成员必须出现，出现任一 ERROR/FAILED 等按优先级使组失败；删除旧 alias 的碰撞结果后再合并，不允许缺失成员沿用旧 parser 末值。`parse_bound` 的 original/revised 是同一份本次 run 日志的两种解析审计结果，不是另一次执行。

两 run 的 `recipe/reference_bindings.json` 均与输入 own entry 相同；`recipe/pandas-dev__pandas-48106.reference.json` 的绑定也相同。两份 raw_node_states 的七节点均 PASSED，与原日志 gold:4990–4996、noop:5969–5975 一致。gold 原 parser 为 F2P16成功、P2P1017成功/3缺失、RESOLVED_NO；绑定后 P2P1020成功、RESOLVED_FULL。noop 前后 F2P均0成功，绑定只把相同三个 P2P缺失修复为成功。该结果说明参考身份修复被实际消费，不能说“因为全文件 rc0 所以自动 reward1”。

## 5. 原始环境输入及历史运行证据

`T/image.json` 与 build.log 显示 public digest `5300b53bb30e5b29f5425967f370e3a72c42b9bbffeb4c2fd1d3ba831716bdd5` 对应 base image ID `0e706113dce17d30fade5723a2a71c162afa253d777fd7fa139c5b89cf05c4b8`，派生 image ID `7fce0487dca32159e8480a7426e1f7cddeadeb60fd9687fb41617266f56c0ec7`。Dockerfile 只有 FROM + `COPY wheels/ /opt/rh2/compat-wheels/`；**镜像层没有安装这些 wheel**。assets_manifest 列 10 个固定 wheel，约17.5 MB，含 CPython3.8 的 fastparquet/Fiona 及 fsspec/s3fs/gcsfs、nbsphinx、build、pyproject-hooks 等。没有重下载或核对不在本地的 wheel 实体。

`T/preflight_pip_check.log` 记录离线安装后 `No broken requirements found`，并显示 root pip warning；这是准备/元数据 preflight，不能替代 grader 或 actor 身份验证。`R/recipes/pandas-dev__pandas-48106.json` 是安装输入，SHA256 `d9eaba74f519789b34cf94b74e755fa260eadba78d0951c504b97e5861b43aae`，与两个 run `recipe/recipe.json` 的 recipe_sha256 相符；每 run recipe 文件是审计输出，不能把路径倒过来当启动输入。

当前 wrapper `replay_with_install_recipe.py:23–40,62–81,100–118` 从 `--code-root` 导入 `src`、以输入 original_install 精确匹配再替换 eval/candidate_test 两脚本、从 `--bindings` 输入取 own entry 注入 parse_log。当前使用时 `--code-root` 应为 **ROOT/rh2**，不是 ROOT。`run_compat_cases.py:106–125` 由 plan 决定 code_root/recipe/bindings/derived-image。读取 plan **仅本题 entry** 得到历史 code_root `/work/env_recipe_repair_20260919/resources_v1/code/rh2`，bindings=true；不能凭 resources_v1 名称猜代码内容，也不能将当前 ROOT/rh2 字节认证成历史 runner。

原始 run 实际消费证据：before/after 四脚本各自把 vendor 原安装换成 `rh2_meta_install`，安装行从 `/opt/rh2/compat-wheels` 离线安装10个版本，再安装工作区 pandas、卸 pytest-qt、`python -I -m pip check`；两个原 eval log 记录这一完整顺序及成功标记，不仅是 COPY 或配方文本。

| 历史角色 | 精确原件 | 结果及关键依据 |
| --- | --- | --- |
| gold | `T/gold/ledger.jsonl:1`；`gold/eval_logs/evallog_replay-er19-pandas_meta__1160016c.eval.log` | 3107/3140 wheel安装，3143 editable install，3378–4875构建，4893–4894 pip check，4916收集1045；5541–5556全部16 F2P PASSED；6005为1044 passed/1 xfailed；test rc0，reward1 |
| noop | `T/noop/ledger.jsonl:1`；`noop/eval_logs/evallog_replay-er19-pandas_meta__67b00d26.eval.log` | 3085/3118 wheel安装，3121 editable install，3356–4853构建，4871–4872 pip check；5118/5541为原TypeError，其余为dtype差异；6968–6984列16 F2P失败和完整摘要；test rc1，reward0 |

日志 SHA 与 own run_refs 逐字匹配：gold `70ed347fc4d9589d3b0908b0f33919568acf08c6ab2c85b1bbd5cc19366475e9`；noop `588be0a87ea6cde725bf24d2b277b4737ca7fdd70762fa67976248af176798a9`。ledger 两次均用派生 image ID、rh2grader/54322、deny_all、2 CPU/4 GiB、可写 `/opt/miniconda3/envs/testbed`；pandas 入口 `/testbed/pandas/__init__.py`，版本 `1.5.0.dev0+1299.g8b72297c87.dirty`，runner digest 前后相同，cleanup removed=true。gold/noop 安装约708.967/708.235秒，内存峰值约1025.887/1033.613MiB。这些是历史真实 RH2 诊断，不是本轮重跑或 actor 数据。apply_user=agent/54321 不等于开发会话。

## 6. 开发条件、评分与恢复边界

| 操作/资产 | 公开依据及可用历史证据 | 当前缺口 |
| --- | --- | --- |
| 编辑并导入工作区的 cast/indexing | 公开 traceback；修复是 Python 分支，可正常源码提交 | actor 实际解释器、包入口/子模块来源、工作区修改是否被加载未实测 |
| pandas 基础扩展可导入 | base pyproject 要 Cython<3、setuptools/wheel；贡献文档要求先 build_ext / editable install；历史 run 确实 build_ext 并导入本地 pandas | 纯 Python 修复本身不强制重编扩展；若 actor 缺工作区可用扩展，需准备时提供或核可写编译路径，不能把 grader prefix 权限借给 actor |
| 兼容依赖及窄测试 | 本题目标无外部数据/服务；历史配方补齐已有包依赖元数据且离线通过整文件 | public image 不含这一安装副作用；派生镜像也只是装 wheel 文件，正式 face 尚无消费该 recipe/bindings 的证明 |
| 资源 | 历史2 CPU/4GiB运行与上述峰值；当前 rollout 默认相同数值，tmp1GiB/home256MiB | 历史约12分钟安装不等于 actor 必须重做，亦不保证有效 actor预算足够 |

当前 `rollout_spec_from_view` 取 public image，而 grading 诊断可以另取派生镜像；当前 actor 为 agent/54321，只明确 chown 工作区/home，grader 为54322并获 conda prefix 可写权。BASH_ENV 文件在 `/root` 且 hidden_paths 含 `/root`，真实 shell 的环境注入/PATH 仍待核，不据此单独断言故障。public_hints 不是这些事实的验收。

官方恢复文件只有 `pandas/tests/indexing/test_loc.py`；gold 的 cast.py 不被恢复，ledger included_paths 验证了该交付路径。当前 `test_globs=()`，非官方测试/fixture 不统一排除；无依据新增排除规则，`additional_exclusions=[]`。当前 RH2 trusted setup 恢复精确路径、应用官方 patch、控制文件及祖先权限；解释器/构建脚本/非官方 conftest 是另外的可执行面，不宣称全部防篡改。

当前 `scoring.py:190–272` 只解析 Start/End 内日志并对冻结参考评分。普通完整 pytest 的 rc1 或非参考失败不自动令 reward0；`manager.py:1197–1249,1314–1325` 另辨全局启动/收集故障。默认 prepared_task_face 的 parser 没有自动绑定本题3 alias，历史审计已显示原 parser 会缺3参考；当前默认路径若未另消费绑定，不能援引绑定后的历史 reward1。此处是代码推断加历史审计，未作本轮当前重放。

## 7. 关系、用途和唯一优先下一步

同批 53958、56849 的公开 base `pandas/core/dtypes/cast.py:626–631` / `634–639` 已含本题 gold 的相同 Categorical 分支，这是具体跨版本答案暴露关系，三题本身并非同一缺陷。只应在私有诊断中使用本报告，不能把 reviewer 跨版本阅读上下文交给公开 solver。

**唯一优先下一步（未来 CPU，未执行）：**在最终选定的正式 actor/public-image 路径下，以 agent/54321 用公开题面的数值扩容及一个类别内值/NA检查工作区导入和 Python 修改生效，同时记录 shell/PATH、包来源、是否需要并实际消费 v3 兼容资产/安装步骤。它区分“已有 grader 诊断可解释”与“actor 可正常开发”；无需无条件重做12分钟全构建或全仓测试。固定 grader 的语义试验可另用冻结 v3 输入、绑定和 current wrapper，但不以该试验替代 actor 条件。当前没有具体语义反例要求先强制改题；API边界未穷举如实保留。模型求解、成功率、token/费用未测，成本 null。

当前 ROOT HEAD `e3d120b55a62cca5985f688de8cdd481b12ea6be`；manager 未提交、experiments 目录未跟踪。当前源码 SHA256：wrapper `fc570d892f9189292e8502e8bb69351e723d56f340f71a8298455c58ab761dc9`；reference_bindings `088f6f24574d7d52b9dbe37060e4474802c2b74130f05a0702fde5b49be5f4cd`；run_compat_cases `15cb6eb1d4cbd2dafea96f75cf8040cb6fc7d35d8fdfef4f020d864b2f7b5d2e`；prepared_task_face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`。这些标识本次静态源码，未认证旧 run code_root 的字节。
