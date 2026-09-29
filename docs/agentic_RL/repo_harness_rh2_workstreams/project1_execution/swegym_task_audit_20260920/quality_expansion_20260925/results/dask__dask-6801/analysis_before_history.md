# dask__dask-6801 — history 前独立主审

主审：pack07_dask。初判为 needs_review / static_review，intended_use=development_diagnostic。公开目标与评分代理不等价；gold 仅处理共同图构造，未解决仍在初始化期间发生的 schema 采样。以下是静态证据和已授权 RH2 原日志，不是当前 actor 或新 CPU 结果。

## 公开目标、版本与双向映射

公开 issue 要求两个共享 delayed 调用各执行一次；联合写两个 DataFrame 不应翻倍，schema='infer' 也不应再额外执行。三个独立 compute 之间不承诺缓存；重试下 exactly-once 不是本题要求。meta 已显式提供，不能用 from_delayed 的普通结构采样解释全部问题。题面未指定引擎；auto 优先 fastparquet，schema 参数在那里被忽略。应显式区分 PyArrow schema 分支。原示例两次写同一目录有覆盖风险，但改变目录行为不是主要要求。

| 需求/合理旧行为 | 公开依据 | 断言、helper 与执行证据 | 判断 |
|---|---|---|---|
| 联合写入时共享上游不重复 | user_prompt 示例/期望；core.py:540–580；DataFrame core.py:1474–1497 | 四个 F2P 全是 test_getitem_optimization 的 PyArrow index/preserve_index 参数，均无调用计数 | 缺失：保留 BlockwiseParquet 不推出每个 delayed 只执行一次 |
| infer 不额外调用用户代码 | user_prompt 标题/最后一例 | 新测试没有 schema='infer'；旧 schema_inference 只写回并 assert_eq | 缺失；gold 未动 arrow.py:853–870 的分区 .compute() |
| 写回正确、可延迟写入、无 metadata 模式 | core.py 文档及旧测试 | to_parquet_lazy 两 scheduler；delayed_no_metadata；schema_inference；append_create | 有局部语义回归正证据，但无共享上游计数 |
| 保留读取列裁剪能力 | 旧 test_getitem_optimization；optimize.py:44–131 | 修改测试先写/read B，再建立第二次写出的 out.dask；选择 read-parquet 前缀层，要求 isinstance(BlockwiseParquet)、columns==['B']；最后仍比较 ddf.compute(optimize_graph=False) 与 ddf.compute() | 合理性能旧行为的结构代理；公开目标不足以要求某一种 HLG 层保留方式。最后断言计算的是读入 ddf，并没有计算 out 或读第二次写入结果 |
| compression/backend kwargs/append/index | to_parquet 公开参数 | 已读 compression/helper、kwargs、append/append_create、index 两参数 | 单独调用受保护；同时构图不同写选项的碰撞未覆盖 |

新/改测试完整核读：test.patch 加的两个目录、写入图、手动优化调用、层查找及全部后续原断言。engine fixture 为 fastparquet/pyarrow 两值并有版本/缺包 skip；index 使用一次随机 permutation，但内容固定 B 值并非计数数据。决定性 optimize_read_parquet_getitem 检查直接依赖是否单一 getitem Blockwise，改变读层 columns、meta、名称与依赖；不统计执行次数。BlockwiseParquet 构造保存 columns 并包装 ParquetSubgraph。DataFrame assert_eq 会计算并检查类型/名称/dtype、divisions 范围、Pandas 内容；本 F2P 末尾输入已是 Pandas，不能验证输出写入任务。

## Gold、调用者与非 gold 实现

完整 gold 仅改 parquet/core.py：导入 Delayed/HighLevelGraph/apply；删除函数内 delayed 导入；用 (df._name,d) 直接连写任务，所有参数通过 apply 字典传递；聚合 metadata 或 None 终结任务；HighLevelGraph.from_collections 保留 df 各层，再构造 Delayed，保留 compute/compute_kwargs。调用者 DataFrame.to_parquet:3982–3986 原样转发。HLG 单依赖路径复制原 layers/dependencies，确实避免 df.to_delayed 默认先分别优化。普通重复的因果修复有静态正证据，但未跑题面计数。

完整 Arrow initialize_write、write_partition、write_metadata 和 FastParquet 三写入方法核读：schema='infer' 且 object 列时仍逐分区采样 .compute()，在新 IO 图创建前执行。题面空 object 数据可能每个写调用扫描所有分区。gold 无缓存/共享采样节点，故不能将已通过 F2P 说成完整解决 infer 目标（check27 完整性 issue；这是残留而不是 check26 新增回归）。保留显式/复杂 schema 及旧采样语义也意味着不能擅自以 _meta_nonempty 代替真实 object 推断。

合理非 gold 方案包括局部以未预优化的图接入 delayed 写、或其它能复用上游的图构造；若最终图经不同合法优化成为低层图，可能功能和列裁剪都正确却没有 read-parquet/BlockwiseParquet 层，从而被当前结构断言拒绝。此为具体静态误拒风险，未执行替代解，不宣称已证明某一完整替代补丁通过所有旧行为。

另有 gold 新风险：tokenize 参数遗漏 engine、compression、write_metadata_file 和任意 backend kwargs，而写任务函数/参数依赖它们；同 df/path、不同选项可生成相同 name，HLG 合并的字典覆盖可能丢弃其中任务。用户同路径写入的期望冲突需界定，故此处不称已证实际文件回归；应保留为 check26 unknown/静态候选，不能用独立 compression P2P 通过消解。Delayed.optimize:464–467 仅 ensure_dict+cull，新测试手动调用 DataFrame 优化器也不证明普通执行会做同一列裁剪。

## 原运行与公平性

F2P 四项逐项身份/状态见附录；两 preserve_index=True 在 noop 分别于日志1175/1257找不到 read-parquet 层而 IndexError；两 False 于1200/1283构图提前优化，沿 to_delayed→HLG.cull→Blockwise._dict 触发 DataFrame truth-value ValueError（并非调用次数失败）。另外四个 fastparquet 参数也失败但不在 F2P。gold 八个参数通过。P2P 169 项均在同日志 PASSED，语义仅按下述范围抽查，不能把169当全功能覆盖。

历史 compat_v3 明确先从 /opt/rh2/compat-wheels 离线安装 pandas==1.1.5 fastparquet==0.5.0 pytest==7.4.4，再 python -m pip install --no-deps -e .；前后版本输出一致。candidate/eval before/after 脚本完整读过，差异是兼容安装，测试 patch/selector 未改；recipe 中的旧解释只是来源配置文字，不作为本次质量结论。image.json/build.log 表明加 wheels 层，保留 base layers。runner_integrity_changed=true 与安装变更同时出现，不据此称恶意篡改或完全无风险；私有安装配方不代表实际 actor 已预置。PyArrow 具体版本未见独立输出，不能由测试 pass 推断版本号。

## 开发、资产与合法交付

| 必要操作/资产 | 公开依据 | 现有条件与缺口 | 最小未来公开验证（未执行） |
|---|---|---|---|
| Python/Dask/Pandas/NumPy/fsspec 与 PyArrow；本地源码可编辑 | setup.py、API、题面 | 历史 grader 可 editable install 且导入 /testbed/dask；actual actor 全部 unknown | 打印 id、sys.executable、dask.__file__、依赖版本、git HEAD/status/diff；确认工作区来源与权限 |
| 本地可写临时目录及 parquet 编解码依赖 | /tmp/test 例、engine fixture | 历史 grader 创建临时输出成功；actor 权限/磁盘未验 | TemporaryDirectory 中按公开例建立两个独立目录，显式 pyarrow；同步调度计数构图前后及 compute 后 |
| 目标与兼容性窄验证 | 共享 delayed 例和旧测试 | 无需外部数据/网络/GPU；首次准备供应包与测试期离线分开 | 原例每次联合调用累计2次，普通/infer分开；pytest -q dask/dataframe/io/tests/test_parquet.py -k 'to_parquet_lazy or delayed_no_metadata or pyarrow_schema_inference' |
| 提交源文件、可信测试恢复 | public_hints；原投影与恢复日志 | 历史仅 core.py 被投影；测试由 grader checkout/apply，apply_rc=0 | 候选 git diff 限合理非测试源码；actor 实际输入/允许提交边界另取证 |

唯一优先下一步：在隔离私有 CPU 对照中按公开两 delayed 例记录普通/infer 的构图及 compute 分阶段调用计数（base/gold、独立输出目录、pyarrow），并据结果将直接计数纳入验收讨论。这一步可确定 gold 残留的实际规模，也会说明现有通过分数与目标的距离；不安排全仓或模型实验。

## 阅读范围与未覆盖

完整：本题 prompt/bundle/identity/environment_brief，private 两 patch，grading/validation 的任务字段及 expected 全列表，run_refs/source_refs/environment_record 的本题身份字段，本题封存 public_read，中性方法五文档。源码实读：parquet/core.py:118–165,368–644；arrow.py:800–1049；fastparquet.py:504–653；DataFrame core.py:1465–1505,3980–3990；optimize.py:1–131；highlevelgraph.py:360–449；delayed.py:1–45,450–520；base.py:205–250；dataframe/utils.py:698–886。测试实读 test_parquet.py:1–100,204–230,564–615,1080–1130,1400–1430,1480–1560,1808–1870,2240–2350；setup.py/setup.cfg/conftest.py。区段末尾跨入其它函数仅算部分阅读。

P2P语义抽查包括 delayed_no_metadata、schema_inference infer/complex（expected仅False参数）、to_parquet_lazy threads/processes、append_create、compression全部四值/partition_on、writing_kwargs、getitem_empty/multi、subgraph_getitem。其余 P2P 只核状态/身份，不声称读断言；手工 schema/时间序列 null 等在 public_read 可见但本主审未独立阅读全文，不以其覆盖作结论。未读完整低层融合、scheduler、第三方库、所有后端分区写 helper、全仓调用者或全部 fixture。原日志仅本题授权行/文件；git show 是基线提交，不是初态 diff。

## 原件身份、命令与逐测试附录

以下P=/runs/swegym_quality_expansion_20260925/public/dask__dask-6801/base（实际根为本文工作区）；private=/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/private/dask__dask-6801。原路径均相对工作区 /Users/roger/Desktop/claude-code-verl-stage0h。

source tag=`xingyaoww/sweb.eval.x86_64.dask_s_dask-6801:latest`；期望manifest digest=`sha256:b9dbc69abe704126d82a4b3b05b9da7237b430971e63b76e0688b5b52f1fbb9e`。

### gold

ledger `runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/gold/ledger.jsonl:1`；log `runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/gold/eval_logs/evallog_replay-er19-compat_v3-da_8671cb8c.eval.log`，SHA256 `3ff08305fa585658eece7eee40321ab261ef008697c80432522d5f138c7e5dfe`（独立hash核对一致）。

- actual image ID：`"sha256:83edfe0e19540a793fb328e5276e5531381b2b8ce48a6f6e2d7be9d6a950cc98"`
- derived recipe：`"compat_v3:dask__dask-6801"`
- scripts digest：`"sha256:068923e3885087f41db7d1c2e9948f9c4ec752cf2be7da54d825840c81d228e2"`
- raw gold patch SHA：`"sha256:4c7a12dfd989740a37dab9a77f86b3dec7e59f894d01447684e06e1145b5d185"`
- projection included：`["dask/dataframe/io/parquet/core.py"]`
- install：`{"install_rc_last_command": 0, "install_seconds": 9.367, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 0, "test_seconds": 68.163}`
- resource原字段：`{"mem_peak_mb": 857.246, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:1081 `+ pytest -n0 -rA --color=no dask/dataframe/io/tests/test_parquet.py`
- log:1083 `platform linux -- Python 3.8.15, pytest-7.4.4, pluggy-1.5.0`
- log:1483 `SKIPPED [1] dask/dataframe/io/tests/test_parquet.py:1949: ArrowEngine will only collect statistics for known index columns and/or filtered columns.`
- log:1484 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_empty[pyarrow-fastparquet-False] - fastparquet fails reading pyarrow written directories`
- log:1485 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_empty[pyarrow-fastparquet-True] - fastparquet fails reading pyarrow written directories`
- log:1486 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_ordering[pyarrow-fastparquet] - fastparquet fails reading pyarrow written directories`
- log:1487 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_roundtrip[fastparquet-df8-write_kwargs8-read_kwargs8] - Parquet doesn't support nanosecond precision`
- log:1488 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_roundtrip[pyarrow-df8-write_kwargs8-read_kwargs8] - Parquet doesn't support nanosecond precision`
- log:1489 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_read_from_fastparquet_parquetfile - No longer accept ParquetFile objects`
- log:1490 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_partitioned_preserve_index[pyarrow-fastparquet] - fastparquet fails reading pyarrow written directories`
- log:1491 `======= 363 passed, 1 skipped, 7 xfailed, 2 warnings in 67.23s (0:01:07) =======`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-index1-True]` | PASSED / 1418 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-None-True]` | PASSED / 1416 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-None-False]` | PASSED / 1417 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-index1-False]` | PASSED / 1419 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_kwargs[pyarrow]` | PASSED / 1323 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-snappy]` | PASSED / 1305 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_delayed_no_metadata[pyarrow-pyarrow]` | PASSED / 1137 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_subgraph_getitem` | PASSED / 1424 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-None]` | PASSED / 1311 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_pyarrow_schema_inference[pyarrow-infer-False]` | PASSED / 1262 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-gzip]` | PASSED / 1304 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-None]` | PASSED / 1303 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-default]` | PASSED / 1302 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_append_create[pyarrow]` | PASSED / 1185 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-gzip]` | PASSED / 1312 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-default]` | PASSED / 1310 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization_empty[pyarrow]` | PASSED / 1421 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_to_parquet_lazy[pyarrow-threads]` | PASSED / 1290 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-snappy]` | PASSED / 1313 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization_multi[pyarrow]` | PASSED / 1423 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_pyarrow_schema_inference[pyarrow-complex-False]` | PASSED / 1264 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_to_parquet_lazy[pyarrow-processes]` | PASSED / 1291 |

expected F2P=4、P2P=169；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 371, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_FULL"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

### noop

ledger `runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/noop/ledger.jsonl:1`；log `runs/env_recipe_repair_20260919/compat_v3/tasks/dask__dask-6801/noop/eval_logs/evallog_replay-er19-compat_v3-da_c2afc4d4.eval.log`，SHA256 `5fa8407dbdc91cec8871099e0a54b257ea10011de9caafa9723065e4ccba94f8`（独立hash核对一致）。

- actual image ID：`"sha256:83edfe0e19540a793fb328e5276e5531381b2b8ce48a6f6e2d7be9d6a950cc98"`
- derived recipe：`"compat_v3:dask__dask-6801"`
- scripts digest：`"sha256:068923e3885087f41db7d1c2e9948f9c4ec752cf2be7da54d825840c81d228e2"`
- raw gold patch SHA：`null`
- projection included：`[]`
- install：`{"install_rc_last_command": 0, "install_seconds": 9.498, "install_skipped": false, "log_partial": false, "markers_seen": ["RH2_INSTALL_RC", "RH2_TEST_RC", "RH2_TS_INSTALL_END", "RH2_TS_INSTALL_START", "RH2_TS_TEST_END", "RH2_TS_TEST_START"], "test_rc": 1, "test_seconds": 74.61}`
- resource原字段：`{"mem_peak_mb": 900.594, "mem_peak_unavailable_or_zero": false}`

原policy={"candidate_writable_prefixes": ["/opt/miniconda3/envs/testbed"], "cpus": 2.0, "grader_profile_digest": "sha256:1bb8e0cf80ce48b15401fdf79d18f4f4c08a5f01001d8b0756311c58de25c19a", "memory_bytes": 4294967296, "network": "deny_all", "pids_limit": 512, "profile_id": "rh2.grader_sandbox_profile.v1", "shm_bytes": 67108864, "tmpfs_bytes": 1073741824, "uid": 54322, "user": "rh2grader"}；原budgets={"candidate_stage_seconds": 900.0, "cleanup_seconds": 120.0, "grading_deadline_seconds": 3600.0, "image_pull_seconds": 1800.0}。不改资源字段名/单位。

原命令、平台和汇总：

- log:971 `+ pytest -n0 -rA --color=no dask/dataframe/io/tests/test_parquet.py`
- log:973 `platform linux -- Python 3.8.15, pytest-7.4.4, pluggy-1.5.0`
- log:1694 `SKIPPED [1] dask/dataframe/io/tests/test_parquet.py:1949: ArrowEngine will only collect statistics for known index columns and/or filtered columns.`
- log:1695 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_empty[pyarrow-fastparquet-False] - fastparquet fails reading pyarrow written directories`
- log:1696 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_empty[pyarrow-fastparquet-True] - fastparquet fails reading pyarrow written directories`
- log:1697 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_ordering[pyarrow-fastparquet] - fastparquet fails reading pyarrow written directories`
- log:1698 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_roundtrip[fastparquet-df8-write_kwargs8-read_kwargs8] - Parquet doesn't support nanosecond precision`
- log:1699 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_roundtrip[pyarrow-df8-write_kwargs8-read_kwargs8] - Parquet doesn't support nanosecond precision`
- log:1700 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_read_from_fastparquet_parquetfile - No longer accept ParquetFile objects`
- log:1701 `XFAIL dask/dataframe/io/tests/test_parquet.py::test_partitioned_preserve_index[pyarrow-fastparquet] - fastparquet fails reading pyarrow written directories`
- log:1710 `== 8 failed, 355 passed, 1 skipped, 7 xfailed, 2 warnings in 73.60s (0:01:13) ==`

逐F2P与已语义阅读的相关P2P身份（状态来自原日志；其余expected只机械核对）：

| 类别 | ID | 原状态/行 |
|---|---|---|
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-index1-True]` | FAILED / 1708 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-None-True]` | FAILED / 1706 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-None-False]` | FAILED / 1707 |
| F2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization[pyarrow-index1-False]` | FAILED / 1709 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_kwargs[pyarrow]` | PASSED / 1542 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-snappy]` | PASSED / 1524 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_delayed_no_metadata[pyarrow-pyarrow]` | PASSED / 1356 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_subgraph_getitem` | PASSED / 1635 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-None]` | PASSED / 1530 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_pyarrow_schema_inference[pyarrow-infer-False]` | PASSED / 1481 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-gzip]` | PASSED / 1523 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-None]` | PASSED / 1522 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_compression[pyarrow-default]` | PASSED / 1521 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_append_create[pyarrow]` | PASSED / 1404 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-gzip]` | PASSED / 1531 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-default]` | PASSED / 1529 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization_empty[pyarrow]` | PASSED / 1632 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_to_parquet_lazy[pyarrow-threads]` | PASSED / 1509 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_writing_parquet_with_partition_on_and_compression[pyarrow-snappy]` | PASSED / 1532 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_getitem_optimization_multi[pyarrow]` | PASSED / 1634 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_pyarrow_schema_inference[pyarrow-complex-False]` | PASSED / 1483 |
| P2P | `dask/dataframe/io/tests/test_parquet.py::test_to_parquet_lazy[pyarrow-processes]` | PASSED / 1510 |

expected F2P=4、P2P=169；所有P2P逐ID映射均PASSED，无缺席；这仅是身份与状态核对。原parser={"apply_ok": true, "num_parsed_outside_segment": 0, "num_parsed_tests": 371, "parser_source": "swegym_parsers@242429c1", "reference_missing": [], "reference_skipped": [], "resolution": "RESOLVED_NO"}；原cleanup={"detail": "", "removed": true, "steps": ["rm:ok"]}。

## 审查边界与检查编号

实际actor消息（user/system/tool及hints是否交付）、实际初始工作树HEAD/status/diff、来源规定初改、忽略资产、UID/HOME/cwd/PATH、源码权限与包来源、资源与网络均unknown。历史grader恢复后的干净base不能替代这些事实。公开包没有导出某资产不证明镜像缺资产。grader的network=deny_all不证明actor网络相同；未发现最小功能需要外部服务。正式镜像构建供应网络与测试期网络分开。

原编号稀疏判断：1有base/patch/投影/原运行局部对应证据；2有源码根因与注明范围的noop；3 unknown（实际输入）；4/6/7/8/9/10/16/17/18/19/20/21按上文grader局部证据，actor部分unknown；23需求充分性与具体规格争议见正文，24非gold误拒、25漏测、26新增回归、27gold局部正确性/完整性分别论证；28不将自加样例强行写成来源要求。29 actual actor答案暴露unknown，不能因审查者已知gold改成actor泄漏；30未查实际网络取答案；31只核恢复/保护局部记录，非完整攻击审计；33/34/35/36真实模型和训练资格unknown；37仅注明原环境配方差异；38未重跑干净复验；39未跨题验证；40封存合规不能证明无漏检/误拒/抽样偏差。未列编号视为not_checked。

usage：本主审获授权看本题隐藏test.patch、gold.patch、expected、历史原noop/gold日志及本题public_read。未读history/旧质量记录、reviewer、根汇总、其他包；不能把本审查材料交给独立solver。additional_exclusions=[]；revision_refs=[]；无新CPU/模型或工具计费观测，costs相应为null。全文是诊断审查，非训练/正式评测批准。封存后不再改写，等待明确history release。
