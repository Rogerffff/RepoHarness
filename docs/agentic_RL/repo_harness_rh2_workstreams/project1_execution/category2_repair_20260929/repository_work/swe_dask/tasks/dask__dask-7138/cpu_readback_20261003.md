# Dask7138：array-like 与关键字兼容的实际 CPU 读回

2026-10-03，题主执行并读回。**真实公开 actor 和三份私有对照符合预期：兼容修法通过，noop 与原 gold 被拒。** 修订材料尚未正式发布评分，实际结果仍需非作者核查；本文是作者运行报告。

输入快照 `171ae9861a465328` 的 19 个文件逐 SHA 核实。修订补丁 SHA 为 `2f3c5c539816149a06b6c460b5d79d6b3223f452cd5862bcdbac41faf76bc44a`，参考为 1 F2P + 469 P2P，包含原 468 P2P 和新增的 `test_ravel_keyword_array`。

## 镜像与执行版本

找回历史 pytest7.4.4 Dockerfile，固定原镜像 manifest `sha256:91df52cb66bb64003ecf4721832eae373c701536aa3dcb85ddc7d9e0ea757736`。实际 base ID `sha256:8da379ba385fb50070429c697a92cdb5673b8475b0b48a7da7e8642cc99eef3e` 与历史一致。新构建沿用历史版本 pin，但采用冻结共用 builder 的 copy-only grader 与安装 wheel 的 actor 配方，**不是逐层复刻历史 Dockerfile**，故本轮重新验证实际行为。

`dask7138-images-cpu-c-20261003-v1-q01` 构建完成。grader ID 为 `sha256:625b404c6c1c40da31df4edfea6052a10fbd30b7fb49d58072b6ee2b215fab13`，actor ID 为 `sha256:fdd298b61309ae2df4cb9f528351526b7b3817c42fc34f47f98152a92a520881`；基础层保留，pytest7.4.4 wheel SHA 为 `b090cdf5ed60bf4c45261be03239c2c1c22df034fbffe691abe93cd80cea01d8`。原历史 wheel 未记录 SHA，不声称 wheel 字节等同历史。actor 的 `pip check` 仍报 distributed、zarr 和 chest 的历史冲突，不声明全环境兼容。

镜像和后续运行绑定第五版 `cat2-cpu-r2e078079-swe7-git-20261003-v1`，manifest SHA `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，使用 `runtime_cpu_v2`。这版含已审 Git 修复，但没有登记本题新测试。本包运行 helper SHA 为 `c05891aaa9bffb879092652d049b38845091b16b0db9f09bd283ca9a8e077eea`，调用冻结 prepare、devcheck 与 private_behavior。

## 原公开 actor

作业 `dask7138-diagnostic-cpu-c-20261003-v1-q01` 返回资源忙 75，未执行题目；q02 获统一 run 槽完成。真实 Claude Code 2.1.205 使用脚本桩，**没有基座模型推理**。UID54321、2 CPU / 4 GiB、512 进程上限、无 swap、无宿主挂载；HEAD 为 `9bb586a6b8fac1983b7cea3ab399719f93dbbb29`，初态干净。

实际首条请求包含原 public_hints 和原题面，problem_statement 字节一致。身份/导入确认 `/testbed/dask`、Python3.8.15、NumPy1.17.5、pytest7.4.4。四个公开命令均执行：原 list 例子 rc1，实际为缺少 `reshape` 的 AttributeError；旧 `array=` 调用 rc0；原公开 routines 模块 560 passed、92 warnings。未向 actor 提供本包私有新测试或候选。

启动前与激活检查通过，activation 写权限被拒；harness rc0、日志完整，容器、网络和桩清理无残留。泛用报告两个固定标记检查为 false，因为本题命令未打印相应标记；实际身份、激活和权限由对应原件确认，不把固定标记说成通过。

## 三份私有对照

每份使用独立干净 root 容器，候选和新测试分别应用，执行完整 `test_routines.py`。只解析 Start/End 标记之间的输出，逐 ID 核 470 个参考。下表为私有测试行为，**不是正式 reward**。

| 候选 | 私有行为 | pytest | 区分证据 |
| --- | --- | --- | --- |
| noop | 拒绝 | 1 failed、561 passed、92 warnings | F2P 的 array-like 转换失败，469 P2P 全通过 |
| compatible_ravel | 接受 | 562 passed、92 warnings | 新旧输入、实际结果类型及关键字兼容通过，470 参考全通过 |
| gold | 拒绝 | 1 failed、561 passed、92 warnings | F2P 通过；只在新增关键字 P2P 报 `ravel() got an unexpected keyword argument 'array'` |

全部候选的原 468 P2P 均 PASSED；没有缺席参考或未执行命令。gold 的失败不是泛用环境问题，也不是原 F2P 误拒。每份容器移除和查询 rc0，无残留。本轮没有添加零拷贝等新的目标。

## 证据与剩余

忽略证据根 `runs/category2_repair_20260929/swe_dask/` 下，镜像目录 `image_preparation/dask7138-cpu-c-20261003-v1/remote/` 有 19 份文本证据、54958 字节；实际诊断目录 `cpu_diagnostics/dask7138-cpu-c-20261003-v1/remote/` 有 60 文件、548676 字节。每份已核 SHA 和大小，分别有 `readback_manifest.json`。完整参考状态在 `run/status.json`，真实 actor 在 `run/actor/`，私有完整输出在 `run/private/<candidate>/<candidate>/revised_test_file.out`。

材料[非作者静态窄核](../../reviews/non_author_7656_9378_7138_material_review_20261003.md)已通过，范围不含这些实际结果。继续由共用发布者登记固定补丁及新增 P2P，正式核 0/1/0 和逐参考状态，完成结果非作者核查后提交 GPU。题面保留既有公开修法提示，后续探针须注明引导属性；正式分数继续为 null。
