# dask__dask-7305 — history 前独立主审

主审：pack07_dask。needs_review / static_review；development_diagnostic。当前评分的主要区分项是小整数分界的特定集合，新增大整数测试在base已经通过且走快捷路径，不能验证题面的partition_quantiles端点。gold修正第一处整数插值有依据，完整性仍有限。

## 公开目标及需求—断言双向表

公开要求partition_quantiles对大整数取正确min/max，示例两个uint64端点为612509347682975743与616762138058293247，不能+1；set_index乱序分区症状是相关动机。原CSV未公开不阻断核心两元素复现。buffer overflow只是报告者猜想，不能当根因。标量min dtype变化是附带观察，未核完整归约链，不推定已由此gold解决。

| 需求/旧行为 | 公开依据 | 测试/断言和调用链 | 评价 |
|---|---|---|---|
| partition_quantiles精确大整数端点 | user_prompt直接调用；partitionquantiles.py:48–54 | 新test_set_index_interpolate_large_uint只调用d.set_index('x',npartitions=1)，断言npartitions==1与divisions集合等于两原整数 | 路径不足；没有直接调用/断言partition_quantiles输出 |
| 乱序最小值不落错分区 | user_prompt CSV例 | 新测试1输入分区=1输出分区，shuffle.py:522–530会用mins+[maxes[-1]]覆盖计算出的quantile divisions | 缺失；noop已PASSED，不能区分目标bug |
| 保留近似分位算法允许不同内部分界 | partitionquantiles.py:1–68明确无统计保证、端点职责明确 | 唯一F2P改test_set_index_interpolate集合{1,2,3,4}为{1,2,4}，仍要求3分区；浮点三个断言未变 | 小整数确切集合无充分公开规格；可能拒绝保留旧小整数算法而精确修大整数端点的合理解 |
| 非整数插值、小整数dtype | 旧test_set_index_interpolate/整数测试 | y首尾1/2，中间严格有序且在1–2；interpolate_int所有divisions是integer subtype | 有覆盖；不要求取消所有插值 |
| 时区/datetime/空分区/分类/普通set_index | 旧公开测试及下游边界职责 | timezone、datetime_precision[ns/us]、empty_partition、on_empty、categorical及test_set_index内容/范围断言 | 已风险抽查P2P；不是大整数多分区验证 |
| 直接输出Series dtype/name/quantile索引 | 公开两元素输出与接口 | 新set(divisions)不检查直接结果Series、顺序或dtype；也不compute最终DataFrame核行数/范围 | 缺失；附录的P2P身份通过不能填补 |

全部test.patch已核：一条旧集合断言被替换；新增函数构造uint64 DataFrame，from_pandas(df,1)，set_index(...,1)，仅两个断言，无新增helper/fixture。大整数测试属于P2P列表，不是F2P。唯一F2P noop在test_shuffle.py:614失败，原日志1511–1515明确left={1,2,3,4}、right={1,2,4}；gold通过。新大整数测试noop日志1597与gold1602均PASSED。这个原证据直接支持覆盖缺陷，并非从gold或历史标签推断。

## 完整 gold、helper 和调用者审查

完整gold仅percentiles_summary:413–419：整数也选nearest，删除linear后round/astype。数据来自df.values；categorical先转codes仍nearest；_percentile:13–34针对普通数值调用np.percentile。取最近已有整数样本避免第一阶段浮点插值丢低位，局部正确性有静态依据。partition_quantiles:431–483创建dtype任务、每分区摘要、合并树、process_val_weights后构造带原name的Series；Series._repartition_quantiles:3029–3033转发；shuffle.set_index:487–530同时计算quantiles/min/max，单分区快捷路径解释新测试假阴性；set_partition:605–634保留目标dtype并searchsorted，不能恢复已经损坏的数值。

全部partitionquantiles.py 1–483已读，包括sample_percentiles、percentiles_to_weights、merge_and_compress_summaries、process_val_weights与dtype_info。特别是process_val_weights:337–343在唯一值少于npartitions+1时仍np.interp，结果末尾381–382才astype回dtype；这仍可能把>2**53端点经浮点表示损坏。vals.tolist→np.array(vals)也未指定原dtype，对跨int64边界组合需谨慎。这是gold完整性具体静态风险，未运行第三方NumPy，不宣称已经穷举所有uint64或证实全部场景失败。它不是新gold所引入的已证回归，不能把check25/27混成26。

合理非gold可保留小整数原分界，单独精确保留/恢复整数端点、精确整数插值或针对有精度风险值使用离散选择。当前F2P硬编码改变小整数集合，可能误拒这种方案；没有执行完整替代补丁，因此称静态误拒风险而非已实测误杀。gold将内部近似分界改为{1,2,4}本身不必然是合理行为破坏：模块明确允许近似且空分区可能出现；不能只因为旧测试改了就断言gold数据丢失。未发现已证明的新gold内容回归，check26保持unknown。

相关P2P helper dataframe.assert_eq会同步compute，检查数据/名称/dtype、在known divisions条件检查每分区上下界，再Pandas比较；categorical测试自己检查分类排序。数据内容+边界比只看set(divisions)更强。已读的非大整数回归有局部正证据，不推广到未测大整数不足唯一值或auto重分区路径。shuffle.py:506另有np.interp，auto路径也未因本gold改变。

## 运行版本、可信恢复与局限

本题base=8663c6b7813fbdcaaa85d4fdde04ff42b1bb6ed0；baseline/stage指定指针吻合，gold candidate与gold.patch逐字节一致；投影只含partitionquantiles.py。原ledger仅w01-1第7/8行；不读该共享账本其它题。实际source tag与期望manifest digest在附录，actual image ID=null。Python3.8.19/pytest8.3.2来自原日志，安装python -m pip install --no-deps -e .成功，导入/testbed/dask。base源码导出不等于实际actor。

原selector运行完整test_shuffle.py：108 collected；noop1 failed/104 passed/3 skipped，gold105 passed/3 skipped；三项slow由conftest.py:36的--runslow门跳过，不属于expected中缺席。parser报告106项不同于108 collected，skip摘要合并三条为一条的日志格式可解释计数差异，但未完整重演parser，故只确认expected105项逐ID都有状态、reference_missing/skipped为空，不声称所有非expected身份完全可逆。F2P1及P2P104均逐ID核对。

grader日志准备阶段noop git status干净且真正git diff base为空，gold仅源码改动、diff为完整gold；git show是基线提交。测试文件base checkout及test patch apply成功，diagnostics trusted_setup恢复/保护成功，runner_integrity_changed=false。投影和恢复支持这个交付路径可行，不证明实际actor提交完整、输入未泄漏或控制面不可篡改。

## 开发需要与唯一下一步

| 操作/资产 | 公开依据 | 证据适用条件/缺口 | 最小未来公开验证（均未执行） |
|---|---|---|---|
| Python/NumPy/Pandas/Dask/pytest与本地源编辑 | setup.py、内存例 | 历史grader可安装、导入、测试；actual actor UID/PATH/解释器/权限/HEAD/status/初态unknown | 打印身份、依赖版本、dask.__file__、HEAD/status/diff，确认实际源码生效 |
| 直接核心复现 | 公开两元素uint64例 | 无CSV/外部资产/网络/GPU需要 | 原partition_quantiles(...,npartitions=1).compute()，用[int(x) for x in result]精确对比原整数，并核dtype/name/index |
| 受影响回归与集成 | test_shuffle旧公开测试，shuffle路由 | 本地shuffle临时资产权限actor待验 | pytest -q dask/dataframe/tests/test_shuffle.py -k 'set_index_interpolate or set_index_timezone or set_index_datetime_precision or set_index_empty_partition or set_index_on_empty or set_index_categorical'；独立精确检查乱序多分区上下界 |
| 合法源码交付 | public_hints与原projection | 非测试修改可承载修复；当前actor工具/消息未知 | git diff --stat/--name-only，保护测试由grader恢复，不把私有补丁带给solver |

唯一优先下一步：在私有隔离CPU中直接运行公开partition_quantiles例的base/gold对照，并把同一两值分别请求1与3个输出分区；精确比较首尾整数与dtype。它同时区分新测试捷径和未修的np.interp不足样本分支，可实质改变gold完整性判断。无须原CSV或全仓重跑。是否放宽小整数F2P是明确规格问题，保留为独立问题，不因唯一下一步而删去。

## 实读范围

完整本题公开包/封存public_read；private完整gold/test、grading expected全列表/validation，run_refs/source_refs/environment_record本题字段；中性五文件。源码：partitionquantiles.py:1–483完整；array/percentile.py:1–42；shuffle.py:460–555,580–645,1085–1105；core.py:3024–3036；dataframe/utils.py:703–891；test_shuffle.py:1–75,580–690,780–845；setup.py/setup.cfg/conftest.py。P2P语义实读test_set_index、interpolate_int、large_uint（patch）、timezone、datetime_precision两参数、empty_partition、on_empty、categorical、npartitions；其余仅身份/原日志状态机械对照。未读全部shuffle路由、全部P2P、第三方np.percentile/np.interp实现、标量归约链、完整全仓调用者或其他题材料。

## 原件身份、命令与逐测试附录

以下P=/runs/swegym_quality_expansion_20260925/public/dask__dask-7305/base（实际根为本文工作区）；private=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-7305。原路径均相对工作区 /Users/roger/Desktop/claude-code-verl-stage0h。

source tag=`xingyaoww/sweb.eval.x86_64.dask_s_dask-7305:latest`；期望manifest digest=`sha256:21fd7dd8a9a1511a02fa5c99403449c75547e2e110afee679b6c9c1569290b73`。

### noop

ledger `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl:7`；log `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_68132c2b.eval.log`，SHA256 `2a1d84d0210b2313b628b8d281e75bb9275b0f5b0059bdd61ea0aba71ff7bb42`（独立hash核对一致）。

- actual image ID：`null`
- derived recipe：`null`
- scripts digest：`"sha256:0fef197e41448182ea1210ca23c22518e969fad4adb52cbc817f40f22c945f12"`
- raw gold patch SHA：`null`
- projection included：`[]`
- install：`{"install_rc_last_command": 0, "install_seconds": 2.469, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 62.287}`
- resource原字段：`{"mem_peak_mb": 1161.25, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:1490 `+ pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py`
- log:1492 `platform linux -- Python 3.8.19, pytest-8.3.2, pluggy-1.5.0`
- log:1652 `SKIPPED [3] conftest.py:36: need --runslow option to run`
- log:1654 `======= 1 failed, 104 passed, 3 skipped, 2 warnings in 61.05s (0:01:01) ========`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate` | FAILED / 1653 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_on_empty` | PASSED / 1609 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate_int` | PASSED / 1596 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_timezone` | PASSED / 1598 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_datetime_precision[ns]` | PASSED / 1600 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_empty_partition` | PASSED / 1608 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_npartitions` | PASSED / 1599 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index` | PASSED / 1595 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_categorical` | PASSED / 1610 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_datetime_precision[us]` | PASSED / 1601 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate_large_uint` | PASSED / 1597 |

expected F2P=1、P2P=104；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 106, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

### gold

ledger `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/ledger.jsonl:8`；log `runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w01-1/eval_logs/evallog_replay-f216-baseline01-w_c9633225.eval.log`，SHA256 `2563d8e1675b4c92cb7ebe4baec366f3e618f5787eead73d869ed9864a7dc50b`（独立hash核对一致）。

- actual image ID：`null`
- derived recipe：`null`
- scripts digest：`"sha256:0fef197e41448182ea1210ca23c22518e969fad4adb52cbc817f40f22c945f12"`
- raw gold patch SHA：`"sha256:aa80a49b78eeabd0f7d4517ece79e894b75dcc2579f05f55d13d92ba6d1ed11d"`
- projection included：`["dask/dataframe/partitionquantiles.py"]`
- install：`{"install_rc_last_command": 0, "install_seconds": 2.482, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 63.547}`
- resource原字段：`{"mem_peak_mb": 1146.02, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:1511 `+ pytest -n0 -rA --color=no dask/dataframe/tests/test_shuffle.py`
- log:1513 `platform linux -- Python 3.8.19, pytest-8.3.2, pluggy-1.5.0`
- log:1657 `SKIPPED [3] conftest.py:36: need --runslow option to run`
- log:1658 `============ 105 passed, 3 skipped, 2 warnings in 62.48s (0:01:02) =============`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate` | PASSED / 1600 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_on_empty` | PASSED / 1614 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate_int` | PASSED / 1601 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_timezone` | PASSED / 1603 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_datetime_precision[ns]` | PASSED / 1605 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_empty_partition` | PASSED / 1613 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_npartitions` | PASSED / 1604 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index` | PASSED / 1599 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_categorical` | PASSED / 1615 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_datetime_precision[us]` | PASSED / 1606 |
| P2P | `dask/dataframe/tests/test_shuffle.py::test_set_index_interpolate_large_uint` | PASSED / 1602 |

expected F2P=1、P2P=104；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 106, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

## 审查边界与检查编号

实际actor消息（user/system/tool及hints是否交付）、实际初始工作树HEAD/status/diff、来源规定初改、忽略资产、UID/HOME/cwd/PATH、源码权限与包来源、资源与网络均unknown。历史grader恢复后的干净base不能替代这些事实。公开包没有导出某资产不证明镜像缺资产。grader的network=deny_all不证明actor网络相同；未发现最小功能需要外部服务。正式镜像构建供应网络与测试期网络分开。

原编号稀疏判断：1有base/patch/投影/原运行局部对应证据；2有源码根因与注明范围的noop；3 unknown（实际输入）；4/6/7/8/9/10/16/17/18/19/20/21按上文grader局部证据，actor部分unknown；23需求充分性与具体规格争议见正文，24非gold误拒、25漏测、26新增回归、27gold局部正确性/完整性分别论证；28不将自加样例强行写成来源要求。29 actual actor答案暴露unknown，不能因审查者已知gold改成actor泄漏；30未查实际网络取答案；31只核恢复/保护局部记录，非完整攻击审计；33/34/35/36真实模型和训练资格unknown；37仅注明原环境配方差异；38未重跑干净复验；39未跨题验证；40封存合规不能证明无漏检/误拒/抽样偏差。未列编号视为not_checked。

usage：本主审获授权看本题隐藏test.patch、gold.patch、expected、历史原noop/gold日志及本题public_read。未读history/旧质量记录、reviewer、根汇总、其他包；不能把本审查材料交给独立solver。additional_exclusions=[]；revision_refs=[]；无新CPU/模型或工具计费观测，costs相应为null。全文是诊断审查，非训练/正式评测批准。封存后不再改写，等待明确history release。
