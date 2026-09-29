# dask__dask-6801：旧发现逐项差异

收到root明确release后仅读取refs.json所列L1_dask本题记录，hash吻合；未沿旧记录链接读取raw hints、早期日志、仓库汇总、其它题或reviewer。以下“旧称”是二手历史主张，只有能由本次独立已读原件支持的部分才确认。

| 旧主张/位置 | 结论 | 决定性依据与范围 |
|---|---|---|
| checks1/4/17：base、源码gold、测试patch对应且无需额外排除 | 确认局部、收窄pass | 本次base_identity、完整两patch、candidate字节核对/投影和测试恢复支持；不覆盖实际actor交付。additional_exclusions=[] |
| check2：empty四F2P失败即证明题面重复调用缺陷 | 收窄 | 本次noop两True在read-parquet层查找IndexError，两False在to_delayed优化中DataFrame布尔ValueError；能证明构图测试失败，不能证明准确重复次数。静态因果链另有支持 |
| public_view：题面未要求返回Delayed | 纠正 | 公开base parquet/core.py:421–423明确compute=False返回dask.delayed；题面文字未说不等于公开规格缺失 |
| checks3/23/29：私有hints含修法、维护者判infer为预期行为 | 未核原hints；实际actor保持unknown | 只获准读旧记录转述，未读raw hints。公开schema文档430–431确实说明真实分区采样，但不明确承诺可重复多次；不能把旧私有裁定直接作为当前可见任务豁免。check3实际消息与23规格、29可见性分开 |
| check23：F2P是列投影结构，未直接验证调用次数 | 确认并细化 | test.patch+optimize.py完整核读：手动优化out图，强制read-parquet前缀/BlockwiseParquet/columns B；最后比较的还是读入ddf而非第二次写出结果 |
| check24：to_delayed(optimize_graph=False)替代方案倾向也过 | 保留未验证 | 与公开图复用方向一致，但未实现/执行；更一般低层图替代可能被结构条件拒绝，不把所有替代解认定必被拒 |
| check25/issues引擎覆盖：缺fastparquet导致72skip | 对本次引用条件过时；评分覆盖限制仍在 | compat_v3原命令离线安装fastparquet0.5.0，八个getitem参数实际运行，gold全通过；原expected仍仅四PyArrow F2P及169P2P。运行更多测试≠它们全进入评分 |
| checks6/11：pytest8、pandas内部API漂移导致恒失败、74skip与伪键 | 对当前pair过时，原早期数目未复核 | 本次Python3.8.15/pytest7.4.4/pandas1.1.5；gold363pass/1skip/7xfail，testRC0；noop8目标构图失败。旧parser早期10伪键未读取原status_map，不替它背书；本次expected逐ID均有对应 |
| check27：gold仅解决图重复，infer采样仍在 | 确认静态残留，次数未实测 | gold未改arrow.py:853–870，初始化仍.compute。当前通过分数不能证明完整满足公开目标 |
| check27次要：kwargs_pass修改调用方字典 | 纠正 | core.py:536用字典推导新建kwargs_pass，**kwargs也为函数局部kwargs；gold对该本地字典加fmd等不等于修改调用方传入dict。未见其它共享值被本次赋值修改 |
| check26 pass/给若干回归建议 | 收窄为unknown | 回归建议不是执行或无回归证明；本次另发现tokenize未含compression/backend/metadata等选项的静态碰撞风险，未实证文件回归。schema残留属于27而非26 |
| graph_size_pyarrow检查to_parquet图大小 | 纠正 | 旧测试2241–2253先写入再read_parquet，pickle测的是ddf2读取图；不是写图大小。test_to_parquet_with_get的完整次数/图形状旧解释未在本次阅读全文，不采纳 |
| check5包内唯一、全池关系/旧成本minutes25、训练资格 | 未核或不继承 | 不扩读prescan/其它题；旧人工耗时不是本次成本。静态建议needs_review/static_review而非沿用needs_repair生产标签；不先按gold层结构重写题意 |

读history后没有更改封存前稿的核心结论。新增的是上述旧错误/时效差异的明确处理；schema文档与旧维护者转述的区别保留。唯一优先下一步仍是公开例的私有base/gold分阶段计数对照（普通/infer、pyarrow、独立目录），用于确定直接行为和残留规模。没有新CPU、模型或评测资格证据。


封存初稿：[analysis_before_history.md](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_expansion_20260925/results/dask__dask-6801/analysis_before_history.md)（SHA256 `63f149eb941bb9e99be20f405e8c3c3fad1ee6e1ed968e4909bef6dc7e6a8216`）。

本次release后历史读取仅：

- [dask__dask-6801.json](/Users/roger/Desktop/claude-code-verl-stage0h/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dask/records/dask__dask-6801.json)；SHA256 `0bf09007a604f064fa216d43a69547c7c6779eeb4e72c139596a4dd1c13353f2`。
