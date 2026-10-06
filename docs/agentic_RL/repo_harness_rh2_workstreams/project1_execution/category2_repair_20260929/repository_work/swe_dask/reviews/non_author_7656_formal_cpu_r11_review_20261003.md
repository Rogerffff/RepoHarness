# 7656 R11 正式 CPU 增量非作者核查

2026-10-03。**固定 R11 正式评分矩阵验收通过：noop / gold / wrong_result_type / opaque 的实际 reward 为 0 / 1 / 0 / 0。** 四行各有 1F + 48P、49 个完整参考；48P 均实际 PASSED，未见缺席、跳过或 P2P 失败。未发现妨碍复用这一版本评分侧资格的具体阻断。结论不包含实际 actor 求解、GPU 探针结果或 typed 正式训练 actor 支持。

本次只补真实正式 CPU 评分证据，复用既有题面和测试静态审查，不改原报告。核查者未参与本轮作者修改、CPU运行或发布；此前已接触 gold 与私有报告，属于非作者证据核查，**不是公开盲审**。未 SSH、重跑 CPU、新 Docker 或网络调用，未读取 8801 当前新材料/标签；只写本报告和同名 JSON。

## 原件与固定版本

[固定输入报告](../tasks/dask__dask-7656/formal_cpu_readback_r11_20261003.json) SHA256 `c797ac322d6771023a74b22b0a844ffa8f3234281254bbd92b8226c8358a557d`；[实际 readback 清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-formal-cpu-c-20261003-v1/remote/readback_manifest.json) SHA256 `3abf25308efe4aa6e014c72698b93302fd5cb66fe360314ac47c8c089c9de302`。逐文件核实 **57 / 57** 的 SHA 与大小，共 **819881 字节**，零不符、无排除项。JSON 保留逐件清单及每行 ledger/eval/diagnostics/候选/导出物绑定。

[发布回执](../../../../../../../../runs/category2_repair_20260929/publication_cpu_takeover_20261003/r11/dask7656_publication_receipt.json)绑定 release `cat2-cpu-r2e089092-swe17-dask-conan-20261003-v1`，manifest SHA256 `bf1d0e8a279f996a7737de775c9a30abf3401dc34840ef54bf7e56b754991bb9`；回执未声称发布方完成本轮题级 CPU。实际 [run/status](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-formal-cpu-c-20261003-v1/remote/run/status.json) 六步 verify/prepare/四行 grade 全部退出0，结束状态为 `formal_matrix_complete_independent_review_pending`。退出0仅是 driver 收口；reward 与失败原因另核实际测试段。

本机核25份相关 release 代码/材料的字节与 manifest 一致，另核 `verify_release.py` 摘要；远端本轮 verify 原件报告980份文件验证通过，未用局部核查冒称本机重新核全部 release。当前7656 revision SHA256 `0b70310018821b5cff83d81a89bcfdca820a198b85c94d246ed91e37500cfcd3` 与 matrix SHA256 `5da46b2ddb0407b61492c546a323a12b6b55f6417b48fd91044ff83a3a856f8f` 均吻合本轮运行绑定。

## 实际矩阵与断言

| 候选 | reward | F2P | P2P | 测试退出 | 实际原因与边界 |
| --- | ---: | ---: | ---: | ---: | --- |
| noop | 0 | 0/1 | 48/48 | 1 | 构造 `with_class` 时读取缺失的 `b`，抛 `AttributeError`；类型/值断言和默认值分支未跑。 |
| gold | 1 | 1/1 | 48/48 | 0 | 完整 F2P 通过，包含显式 Delayed 与默认值两个同步 compute 分支。 |
| wrong_result_type | 0 | 0/1 | 48/48 | 1 | `return_nested` 的新增 `isinstance` 断言实际失败：收到 `namespace(a=3)`；值断言和默认值分支未跑。 |
| opaque | 0 | 0/1 | 48/48 | 1 | 类型断言通过，但字段仍是 Delayed；在 `assert obj["a"].a == 3` 内转换比较结果的真值时抛 `TypeError`，不是数值比较得到False；默认值分支未跑。 |

直接从四份 eval 的唯一 Start/End 区间逐参考读取状态，与 ledger 分区一致；不存在区间外解析或未核的参考。模块实际收集52项：gold 为50 passed/2 xfailed；其余为1 failed/49 passed/2 xfailed。额外通过的 `test_check_meta_flag` 和两个 XFAIL pickle 节点均未进入原1F48P参考，**没有把 XFAIL 冒充成48P通过**。

三份补丁原件均与 matrix SHA 相符；frozen patch 的规范摘要本机重算吻合 ledger/projection，所有非空导出只含 `dask/delayed.py`，无测试/fixture修改，noop 导出为空。`candidate.kind=cc` 是 patch 输入标签，本轮未启动 Claude Code 或 LLM。

## 实际消费、身份、安装与清理

[host grading原件](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-formal-cpu-c-20261003-v1/remote/run/private/host_grading_views.jsonl) 内的有效补丁正文 SHA256 `d3b711c9eb53cbdb6477314eae82f3ae5ca49e5c052a352c7da3959289c287db` 等于作者与 release 的新补丁，参考仍为原1F48P；实际失败栈显示新默认字段定义和类型/值断言，受信 setup 恢复测试文件、base SHA验证、补丁应用均成功。没有拿旧测试的历史reward代替本轮。

本机通过冻结 release 的模型和纯渲染/摘要函数重算，未执行渲染 shell：grading bundle `sha256:f8a8a49e3ebf538982c8af57b9544186502c8b8ce9a5a5e257d9a41f29ced8c6`、environment package `sha256:fd2310ca4c525c7e7e03a19e21d644ac716724759391317517b5db95360813b1`、materials identity `sha256:d7a8f86cd375efc81608438799cd8eee7c8b96772b78fbe85c366fc57de859ed`、scripts digest `sha256:88333443f1861b2e4f412f084e8138a4e6354e1110266f951916eda774ba6661` 全吻合 [formal binding](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask7656-formal-cpu-c-20261003-v1/remote/run/formal_binding.json) 与四份 ledger。host JSON SHA `c57f…f4e0f` 按 driver 明确的默认ASCII转义序列化重算吻合；通用 canonical digest 使用不转义中文，属于不同编码，不能混用。prepared manifest/公开 rollout/私有 grading 的文件SHA链也逐件吻合。

实际 grader 固定为 `sha256:50bca237706aed5413899f7fec2123e9933de56293e8ed8169938c86a9e0559b`，recipe 为 `dask7656-e11-pandas135-stdlib-v1`，setup预算900秒。E11原正文 SHA `26cb808ebe8177028372a351c4704332a3d02e1aa34e3b8a170eb7f0b92047be` 保持；外层新增 `PIP_NO_INDEX/PIP_FIND_LINKS` 离线环境。日志真实执行 stdlib distutils 前导、离线 pandas1.3.5 wheel安装和原 `python -m pip install --no-deps -e .`，安装前后兼容版本均1.3.5，全部安装rc0、无失败命令、未跳过。测试实际为 Linux Python3.9.19/pytest8.3.2，四段标记顺序正确且完整，pytest rc为1/0/1/1，外层shell exec rc0没有覆盖失败。

root 权限用于受信 materialize/sanitize/基线重建、测试文件恢复/补丁应用、wheel SHA和权限布置；补丁写入/应用由 `agent/54321`，评分安装/测试由 `54322`。54321凭账本和固定 release 中 `agent_ws(user=agent_uid)` 执行路径核实，本轮没有单独 `id -u` 输出；54322还由隔离解释器前置 probe 的实际 `geteuid()==54322` 断言和 wheel字节验证成功输出证实。不能把 root受信setup写成正式reward来自旧root私有诊断，或当作actor验证。

四份 ledger均记录 cleanup `removed=true`、`rm:ok`；四份 grade日志的 manager_close均为 created1/removed1、无open container/supply/cleanup failure，final_status退出0。候选容器移除的固定代码路径及grade最终cleanup_failures为空可追溯；未实时查询远端Docker。评分policy记录2 CPU/4GiB、断网、PIDs512；观察峰值分别3458.445/1989.586/1961.672/1976.297MB。资源数值是本轮账本观测，不扩为其他输入资源保证。

## 接探针所需边界

本矩阵可作为该材料身份的**正式评分侧资格证据**，无需因探针换执行者重跑全部静态审查。`env_qualification=absent` 原样保留；四行都是参考完整的正常测试结果，无infra失败，不据此自动生成训练准入。

R11 rollout仍为来源 actor。父线程已交接发布/GPU确认的现有诊断入口：固定 `sha256:118f47f67994e4d4df700f427404c7620cd2c9eedf3b818f0e8b21d3276babe3` 可通过 `image_override` 使用；本审查未核新的实际GPU部署或actor作业，不要求为已有诊断接法重建 typed actor。

后续实际探针仍须留证：①部署代码、公开输入/profile、实际actor镜像inspect与override生效、非root UID、首请求/工具执行和模型轨迹；②模型候选 frozen patch 与本矩阵 grader/E11/有效测试/材料身份对齐，实际评分/参考状态/reward运输和清理回执。若以后声明正式训练actor支持，再核被正式消费的typed镜像/激活/环境身份及相应实现、部署与准入；诊断override不等于其已实现。旧actor43或公开stub均未充作本轮actor/LLM证明。

此次独立核查未发现需回退R11评分矩阵的具体阻断；有效范围限定四个候选和固定材料/consumer/镜像/脚本，不穷举所有合理dataclass修法。完整身份、逐文件SHA及逐行参考状态见[同名JSON](non_author_7656_formal_cpu_r11_review_20261003.json)。
