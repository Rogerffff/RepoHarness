# Dask8801 原环境与原公开 actor 读回

2026-10-03。**原digest镜像、干净源码、非root公开开发环境与问题复现已确认；原config模块43项通过，包含目录/文件权限两项。这里只核原公开材料，不采用v6新原因规则、不授予正式reward或探针资格。**

镜像准备 `dask8801-cpu-c-20261003-v3` 的前两次退出75、未执行；q03完成。原镜像ID `sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`，原manifest digest `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`；HEAD `9634da11a5a6e5eb64cf941d2088aabffe504adb`、初态worktree干净，无依赖改动。准备23文件/15600字节，清单SHA `f37ec4e8fd96f3a58d16588674f1d047524fc53d2ced044eaba82c74dbffa3d3`。

公开actor `dask8801-public-cpu-c-20261003-v1-q01`完整结束。冻结第五版source manifest `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，runtime_cpu_v2；不是后续新材料版本。输入快照 `dc2ddc6547e906a6` 只含原public字节、公开命令及冻结helper，三个文件逐SHA确认，不含私有测试或候选。

| 公开命令 | 实际结果 | 说明 |
| --- | --- | --- |
| identity_import | rc0 | UID54321；Python3.9.19/PyYAML6.0.2/pytest8.3.2，实际Dask从/testbed导入 |
| issue_public_import_scalar | rc1 | 新进程读str配置，原堆栈准确复现为AttributeError: str没有items；不是安装/收集失败 |
| public_config_regression | rc0，43 passed | 原公开config模块，含directory/file权限测试，无新增skip |

真实CC2.1.205配脚本桩，无模型推理。首请求逐字交付原题面，SHA `66427f43d5ecf32b2840f2717e5a30adebd93af9c504587a142a5663de9db2be`。prelaunch通过：2CPU/4GiB/swap0/pids512、无bind mount、activation写入DENIED。泛用interpreter_in_tool_result和bashenv_denied_for_agent仍为false，因为命令没有打印该检查器固定标记；实际身份/解释器/权限由原件证明，不把false改写为通过。

harness rc0、日志完整。三命令均实际执行且符合预期；容器rm、stub rc0，容器/网络/relay无残留。公开运行37文件/214071字节已逐SHA回收，清单SHA `7ddfbabae95da9b46143f5c06073bfca3f6ae044eadd2ca88b7e507f2182c7a5`。原件在 `runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-public-cpu-c-20261003-v1/remote/`，身份/首请求/捕获及清理见run/status.json、run/actor/attempt.json和run/actor/captures/。

原因规则的[独立设计窄核](../../reviews/non_author_8801_reason_oracle_20261003.md)确认v6仍误接受“文件不存在”错解；两候选的24份[实际可见原因封包](reason_pair_evidence_20261003.json)仅为本地隔离API采集，全部语义verdict为空，没有运行新判定器。新的原因评分机制/公开契约待用户决定。新题面公开读者、修订的完整Dask导入和可信非root正式评分尚未完成；这份原环境证据不能核销这些事项。
