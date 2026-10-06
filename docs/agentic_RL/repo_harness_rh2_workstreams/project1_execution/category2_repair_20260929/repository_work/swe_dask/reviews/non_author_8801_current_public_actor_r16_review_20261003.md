本轮只读复核通过：R16 v2 的来源准备和当前公开 actor 原件支持这两个阶段已完成，未发现范围内阻断。结论限定为固定来源、当前题面交付、非 root 公开命令、权限测试和清理；正式 29 行矩阵、实际 grader 身份、新鲜语义裁决及训练资格仍未验收。日期：2026-10-03；非作者复核：Codex。对应材料修订为 `dask8801-behavior-semantic-v7-compat1`。

两份运输清单都独立逐件核了 SHA、大小、唯一相对路径、非 symlink、无排除及实际文件集合完整性；清单文件本身不计入成员数。

| 实际阶段 | 原件与清单 | 成员数 / 字节 | 清单 SHA256 |
| --- | --- | --- | --- |
| 来源准备 `dask8801-source-image-cpu-c-20261003-v2` | [运输清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/image_preparation/dask8801-source-image-cpu-c-20261003-v2/remote/readback_manifest.json) | 21 / 16,163 | `15a95dd4077fc981a754a1253a30d4e45651b38eb0e68f0f29183f177de75bce` |
| 当前公开 actor `dask8801-current-public-cpu-c-20261003-v2` | [运输清单](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-current-public-cpu-c-20261003-v2/remote/readback_manifest.json) | 35 / 235,388 | `c7d5286f5115c26f5b6ae15efef5baba78943dcf2bf3752329b267c5960f6a9a` |

封存输入 `17b987e5cdcac007` 的 37 个普通文件共 130,694 B，归档成员与输入清单逐 SHA/大小相符，并与本机对应资产字节相同；未解包或改写原件。[v2 封存 payload](../../../../../../../../runs/category2_repair_20260929/swe_dask/batch_runs/dask-current-r16-cpu-c-20261003-v2/launch_payload.json) SHA 为 `a614e8973024a574ef8779d7c686fac9d13e8adca000abc4a25a39d3428f1119`，归档 SHA 为 `aa8c45e4c012ed02c12eeb6984d41c8b8bb8cb9fb137de8a6f2dcd994d70513e`。两阶段实际 config 与此 payload 精确相同；launch receipt 同时绑定 37 件、归档、serial 与 queue SHA。因此这里核的是实际使用的 v2 封存代码及配置。

发布 manifest 固定为 `f98eddad0c75df00e8e8352d52819d602a06d5e5ccb8d40feacb8c2658a2b80a`。本轮核了该 pin、11 个冻结 producer 文件的 SHA/大小，并实际进行纯本地受信修订 loader 重放；远端日志报告 1369 发布成员核验通过。本轮没有另扩审全部 1369 个成员或其它题。主要执行版本如下，完整 producer 列表与 188 条通过的读取/断言检查见 [JSON](non_author_8801_current_public_actor_r16_review_20261003.json)；此数字不是 CPU 测试条数。

| 绑定代码 | SHA256 |
| --- | --- |
| 来源准备 helper | `a7dccae809d0e81b15a8351f0b033ab398cca9ecb2848ba18c66c6336a3579f2` |
| 当前公开 actor helper | `761f0276831d64ca3af686512fc22d9d0b52f8fa74b073b1cda07d4647c85238` |
| 冻结修订 loader | `3db766c1e0ac64cb304fd5ba22809ee8b92878707b7e93c17fe593f8de0ccf48` |
| 冻结 devcheck | `75399297da458697ebcd17e6ca79aad90b56e4dbdda3214a4c70f82a4b389160` |
| 冻结 acceptance startup | `c67194f09e202c1cd1e83a3a1fbf5df7706952d2e542f97a4b2f3882604dc5d1` |

[来源步骤日志](../../../../../../../../runs/category2_repair_20260929/swe_dask/image_preparation/dask8801-source-image-cpu-c-20261003-v2/remote/build/status.json)实际显示 digest inspect 成功、别名 inspect 返回 1 且 stderr 为 `No such image`，随后只执行同来源 digest 到别名的 `docker tag`。没有 pull、build 或依赖安装步骤。前后 inspect 的配置 ID、RepoDigests 与 RootFS 层相同：来源 manifest digest 是 `sha256:21e77aea7025bad694a5c600ed6d4b372c80c83bc319fafa2fedb23d9ff48483`，镜像配置 ID 是 `sha256:695d2cc28e303a0224c1109fe245f7296c6290d480124fa4fd4cc2ad072124b1`。初始 HEAD 为 `9634da11a5a6e5eb64cf941d2088aabffe504adb`，porcelain 为空、命令返回 0；本 attempt 的两次清理查询返回 0，无残留。

两个 helper 都调用 `load_trusted_swe_revision_outputs`；冻结 prepare 也由受信修订入口生成任务面。实际重放得到公开 bundle digest `sha256:4410e2acd12b04f49f2f17967331573e54f3f22498980c3d612ce5a6ec27fdf2`；prepared rollout view 的全部公开字段与它相同，prepared manifest、公开文件、宿主 grading 文件 SHA 交叉相符。当前题面为 8,563 B、SHA `0b3ffb734d5e9f1eac09848d407b0f040913075359563f7717d5f3efb1ce166c`；原 7,784 B 前缀逐字节等于公开父 bundle，保留 162 处 CRLF。

[真实首条 request](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-current-public-cpu-c-20261003-v2/remote/run/actor/stub/requests/messages_000.json) SHA 为 `5f718f1440116d83f25dfd84c70274aba2e2e111419d6a559a151fb5b605ed1d`。其中只有一个 user message：标准日期 reminder 与实际公开 prompt 两个 text block。后者逐字节等于 `public_hints + "\n\n" + effective_statement`，共 9,284 B、SHA `52e24f3dca699764084f1555921669156e78a060872d8134b1bdc7a3030d3d3e`，含完整当前题面及全部 CRLF；不是只核 normalized 换行或旧前缀。prepared 的通用 prompt 模板与此显式 actor prompt 文案不同，但两者都含相同当前题面，实际 driver 传的是后者。

[prelaunch 原件](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-current-public-cpu-c-20261003-v2/remote/run/actor/prelaunch.json)的实际镜像 ID 同为 `695d2cc…`；运行时探针及 [公开 identity capture](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-current-public-cpu-c-20261003-v2/remote/run/actor/captures/identity_import.out)均观测 UID/GID 54321。2 CPU、4 GiB、swap 0、进程上限和激活环境证据相符；进程 CAPPRM/CAPEFF 为零、no-new-privileges 生效；可信初始化所需的容器 capability 边界集仍为 0x2f，外部和直连 upstream 被拒绝，仅 relay 可连。binds/mounts 均空；公开 rollout spec 的 `grading_spec=None`，其 payload 仅为该公开 bundle。宿主有独立 grading 文件，其 SHA 已核；它未通过 bind 交给 actor。实际四条请求也未出现私有测试、候选补丁、gold、judge 或 semantic 控制材料路径。冻结 producer 只由公开命令生成三次 Bash tool_use；独立重算的完整 stub script 与原件一致。

[逐命令原件](../../../../../../../../runs/category2_repair_20260929/swe_dask/cpu_diagnostics/dask8801-current-public-cpu-c-20261003-v2/remote/run/actor/attempt.json)与请求中的 tool result、完整 captures 对应，返回码依次为 `0 / 1 / 0`：

- 正常完整 `import dask` 指向原 `/testbed/dask/__init__.py`，解释器为 testbed Python 3.9.19。
- 字符串 YAML 在完整 `import dask` 链上真实返回 1，原始 `AttributeError: 'str' object has no attribute 'items'` 可见。
- 原公开 `dask/tests/test_config.py` 收集并通过 43 项，无跳过/失败；明细精确等于来源原 41 项 P2P 加 directory/file 两个已有公开权限分支。这两个分支确实 chmod 后断言结果；运行者是非 root，未用跳过替代。43 项公开 base 测试不等于正式补丁下 45 参考或 29 候选行验收。

实际使用 Claude Code 2.1.205，固定 tarball SHA 为 `sha256:d3dadfa9cde294ac82c755eb6d889291228849180bac5d677ad1a4027aca1bc4`。四次请求分别消费三条预写命令和结束文本；trajectory 有四次 message_start、一个 result，daemon exec 退出 0、日志完整。这是 scripted stub，没有基座模型推理。运行后跟踪工作区仍干净、agent 进程为零；容器/网络/relay/stub 清理无失败，最终标签查询无残留。

原件中的 `interpreter_in_tool_result=false` 和 `bashenv_denied_for_agent=false` 保持原值。两者来自旧通用检查对专用输出 marker 的要求，本公开清单没有这些 marker；本轮使用直接 interpreter capture 和实际 activation/prelaunch 探针，不把全部旧 checks 宣称通过。`launch_facts.launched=null` 同样保留未知，启动事实来自请求和 exec 原件。mtime 记录有 33 个较新条目，展示样本主要是 pycache/父目录；不据零 porcelain 宣称零文件写入，也不把未展示的全部条目分类。

[作者固定记录](../tasks/dask__dask-8801/current_public_source_actor_readback_r16_20261003.json) SHA `a893ae7263608d11a0509bad86fd1b3a963b1efe24c959a2968276a7d5b67e7f` 已绑定，但上述结论独立由运输原件、封存输入和 producer 得出。本轮只在本机读取、hash、解析并重算必要纯函数；未运行 SSH、Docker、CPU、网络、语义服务，也未改作者/封存/CPU 原件。语义 expected、bindings_private、calibration/heldout verdict 文件未读。实际正式 grader 的配置 ID 保留未审；sealed formal config 的预期 `695d2cc…` 不能替代它的运行证据。没有等待正式矩阵，也没有授予自动 reward、公开对外交付或 GPU 训练资格。

