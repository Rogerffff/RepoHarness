# Dask 8801 R16 新作业接线独立窄核

2026-10-03。最终适用版本为本机封存、尚未派发的 `dask-current-r16-cpu-c-20261003-v2`，不是旧 v1 计划或仅按工作区代码推定的版本。

**公开题面 loader、固定来源镜像准备与 v2 依赖计划的有限核查通过，当前范围内没有剩余阻断。** 本次先复现旧 v1 的取消误报，题主修正并另存 v2 后，同一反例已核销。最终 86 项实际本机检查通过。检查没有运行 Docker、SSH、CPU 作业、Claude Code 或模型，也没有读取真实 `messages_000` 回执；不能据此称本次公开交付、正式行为／语义验收或训练已完成。

只修改本报告和[同名 JSON](non_author_8801_r16_dispatch_adapter_review_20261003.json)。工具条件检查使用本机 `rh2/.venv/bin/python`，将 subprocess 和 socket 对象完整替换成内存检查夹具，临时输出均在临时目录中清理；没有创建真实镜像、容器、网络连接或派发子作业。旧 prepare、public actor、source wrapper 和发布材料均未修改。未派子代理，没有重新裁决候选语义。

## 发现并核销的旧 v1 问题

[旧 v1 本地封存 payload](../../../../../../../../runs/category2_repair_20260929/swe_dask/batch_runs/dask-current-r16-cpu-c-20261003-v1/launch_payload.json)的 serial SHA 为 `a9b327b8…1112e`。用其原字符串编译运行，而非重建作者预期逻辑：第 4 个假子进程的 `wait()` 内调用已登记的 SIGTERM handler，随后返回 0。旧代码实际记录 `signal_received: 15`，仍返回 0 并写 `status: complete`。原因是完成判据只看作业数量及退出码，没有排除已取消状态。

题主保留旧 v1，并以 `not_dispatched_review_issue.json` 标明未派发；本核读取了该原件。新版另起 v2 计划和各 stage ID，没有回写旧 payload。v2 sealed serial 加入：

```python
complete = not cancelled and len(codes) == len(plan["configs"]) and all(code == 0 for code in codes)
```

对 v2 原字符串重放相同反例，实际返回 **130**，状态为 `partial_or_interrupted_needs_readback`，保留 `signal_received: 15` 和全部 4 个已等待的作业记录。此缺口在当前 v2 已核销。JSON 分开保存旧问题及当前检查，不将旧 v1 静默标成通过。

## 当前公开题面确实来自修订输出

本核实际调用冻结 R16 的 `load_trusted_swe_revision_outputs`，仅读本机发布文件。选出的 8801 公开对象为：

| 字段 | 实际结果 |
| --- | --- |
| 修订题面 | 8,563 字节；SHA `0b3ffb734d5e9f1eac09848d407b0f040913075359563f7717d5f3efb1ce166c` |
| 原题面前缀 | 7,784 字节，逐字节精确相同 |
| CRLF | 原 162 个全部保留 |
| 公开 bundle digest | `sha256:4410e2acd12b04f49f2f17967331573e54f3f22498980c3d612ce5a6ec27fdf2` |
| 来源镜像 manifest | `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483` |
| base commit | `9634da11a5a6e5eb64cf941d2088aabffe504adb` |

同一 trusted 对象的原始 source 公开题面只有 7,784 字节。这印证旧 `load_trusted_ingest_outputs` 不能用于本次修订题面交付。两个新 helper 都明确导入修订 loader；新 actor 还要求其题面编码字节等于输入快照的 `effective_statement.txt`，并核传入 SHA，旧题面不能通过这一层。

当前 prompt 为 `public_hints + "\n\n" + problem_statement`。内存检查确认这串 UTF-8 字节被原样写入 prompt 文件并传给 devcheck 的 `--prompt`。检查夹具写入模拟的第一条 user message：完整原字节通过；只有换行归一化版本、只有旧 7,784 字节题面均使 helper 停止。源码随后读取 `actor/stub/requests/messages_000.json`，要求 user 文本包含完整、未经换行归一化的当前题面；归一化比较仅为附加记录，不能代替 exact 断言。

这些检查证明**当前断言和传参接线能够区分新旧题面及 CRLF 丢失**。模拟消息不是真实 Claude Code 请求；实际新 CPU 作业仍须拿到真实首条请求及 SHA 才能确认公开交付。

公开命令快照只有三条：源码／导入身份、公开字符串配置导入复现、原公开 config 回归。没有加入私有 effective test、候选、gold、矩阵或语义材料。冻结 devcheck 将 prompt 原样交给 driver；其 actor spec 来自 rollout public view。宿主 prepare 会产生私有目录并在宿主加载 context，但 actor 启动的 Docker 参数无私有 bind mount，driver 接收公开 prompt、公开命令和环境激活材料。本核只追踪这些相关冻结依赖，没有扩审整个共享 harness。

## 来源 digest、别名和干净 base

当前新 prepare helper 为 `a7dccae8…579f2`，包括“允许 No such image 返回之前先检查取消”的修正。以下全用内存 Docker 输出检查夹具重放：

| 条件 | helper 实际行为 |
| --- | --- |
| 固定 digest 已缓存，`latest` 别名缺失 | 不 pull；只创建同一固定来源的缺失别名，然后重新 inspect |
| digest 与别名均已正确存在 | 不 pull、不 tag |
| digest 确实缺失 | 按固定 manifest pull，再 inspect 并补缺失别名 |
| 已有别名指向错误 image ID | 停止；没有 tag 覆盖，也未进入 checkout probe |
| inspect 返回服务错误，而非明确 No such image | 停止；没有把服务错误当成 digest 不存在再 pull |
| checkout 输出存在修改项 | 停止，不能产出“干净 base”成功状态 |
| 缺 digest 的 inspect 等待期间收到取消 | 停止；不进入 pull／tag |

inspect 同时核唯一返回项、预期 image ID 和 RepoDigests 中的固定 manifest。checkout probe 要求 HEAD、空 porcelain 和查询成功的确切输出。v2 的 prepare 和 formal 配置都绑定原来源 ID：

```text
sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1
```

actor 读取 prepare 的成功状态和 image 回执，核相同 base、公开 digest、无 dependency_changes、固定 manifest、干净初态，再以该 image ID 启动。正式镜像的实际存在与干净状态尚未在本核由 Docker 验证；上述结果只覆盖代码的判断条件及封存参数。

## 封存 v2 的依赖与槽位边界

本核直接读取 v2 `plan.json` 与 `launch_payload.json`，计划内容精确相同；编译运行的是 payload 中的 sealed serial 字符串。37 件作业输入快照的 tar 成员集合、逐项 SHA 与大小均匹配声明。v1 与 v2 的 gzip archive SHA 不同，当前 v2 值正确；不能把压缩容器字节变化称作成员内容变化。

| 次序 | stage | 封存 mode | 失败处理 |
| --- | --- | --- | --- |
| 1 | 7138 固定镜像导出 | prepare | 独立步骤的一般失败允许继续；75／130 或取消立即停止 |
| 2 | 8801 固定来源镜像准备 | prepare | 任意非零停止 |
| 3 | 8801 当前公开 actor | run | 任意非零停止 |
| 4 | 8801 的 29 行 formal 矩阵 | run | 任意非零保持未完成 |

四个配置均调用共同 `cpu_slot.py`，queue 固定传 `--package swe_dask`，并对完整子命令执行前景 `wait()`。serial 同时只等待一个 queue；没有同时启动多个 stage。prepare 输出路径精确接到 actor 的 image-readback；actor 与 formal 使用相同 37 件快照，三个 8801 stage 使用同一 R16 manifest；prepare／actor 题面 SHA、prepare／formal 原来源 ID 和 formal 的 300 秒 setup 约束均匹配。

队列先等待旧 v2 来源矩阵 batch 达到终止状态；此前不调用 Popen／cpu_slot。用模拟时钟重放前批一直运行的条件，120 次、每次 120 秒的上限后返回 75，启动作业数为 0。每个槽队列另设 15 次尝试、120 秒退让。一般非零、75／130、prepare 和 actor 失败、独立首步失败及最终取消的条件均按上表核过。

这些证据确认本轮**封存的调用顺序、参数和前景等待**。payload 只给公共 cpu_slot 的路径，本核没有核远端控制脚本实际字节、锁实况或运行时资源占用；不冒称已经实际持槽或完成清理。

## 适用身份及剩余范围

| 原件／代码 | 当前 SHA-256 |
| --- | --- |
| 冻结 R16 manifest | `f98eddad0c75df00e8e8352d52819d602a06d5e5ccb8d40feacb8c2658a2b80a` |
| 来源 prepare helper | `a7dccae809d0e81b15a8351f0b033ab398cca9ecb2848ba18c66c6336a3579f2` |
| 当前公开 actor helper | `761f0276831d64ca3af686512fc22d9d0b52f8fa74b073b1cda07d4647c85238` |
| v2 sealed serial | `4bd4e31a05d39f7348142f9168a142496d5c91f50b6d84cb11673b4be8d04fe5` |
| sealed queue | `b78f5a14382f9d2ca165fe2613d933b55397bfe9edcea856fc7f425e890dd942` |
| v2 plan | `b612ed09b7aae0cea4738b9138deb2a90c0279c566af96e85e810a56f49f8b06` |
| v2 payload | `a614e8973024a574ef8779d7c686fac9d13e8adca000abc4a25a39d3428f1119` |
| v2 输入 archive | `aa8c45e4c012ed02c12eeb6984d41c8b8bb8cb9fb137de8a6f2dcd994d70513e` |

输入 snapshot ID 为 `17b987e5cdcac007`。本轮没有重复验收作者已核的全部 1,369 个 release 文件、49 件发布输入或 trusted 48／216；只核 manifest 身份、直接相关冻结代码、实际 8801 修订 loader 结果、37 件本次作业快照与封存接线。`binding_intake` 的 2F／43P、300／120／1800 和 env qualification 为 null 已核其原件，但没有实际评分。

后续实际 CPU 回执仍需证明固定来源镜像、真实公开首条请求、正式 29 行执行、身份及清理；语义裁决与用途准入继续按原范围另核。本报告不授予自动 reward、探针或训练资格，也没有因检查结果新增审批。
