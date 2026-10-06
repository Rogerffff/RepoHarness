# Moto5960 原镜像 noop 原件与离线供应发布材料：非作者窄核

2026-10-03。结论：**原镜像 noop 的 raw0 和完整测试失败观察成立，但 `make init` 实际退出 2，当前 CPU 未验收。新离线供应材料未发现提交发布前的静态阻断。** 本次只运行过 noop；gold 和 omit_keys_only 没有执行，不能预报它们的实际得分。旧 R5 反例得分仍未知。

本报告仅独立读回本题运输原件并核对供应材料，不重复项目级测试语义审查。我已接触私有评分参考、gold 输入和构造反例，不是公开盲读 solver。使用标准库读取、JSON、hash、tar／wheel ZIP 元数据以及原消费者源码文本；没有执行项目、SDK、CPU、Docker、远端、模型或作者读回脚本。只新增本报告，不修改原件、题主材料、发布输入、固定报告或历史得分。

## 运输身份、实际范围与原始结果

证据根为 `runs/category2_repair_20260929/moto_cpu_20261003/moto5960-cpu-6a6dd8d309c3_evidence/`。独立逐文件核对 transport manifest 的 **45 件／663935B**，SHA256 与长度全部匹配；目录文件集合也与 manifest 加其自身一致。压缩包的全部原件成员与本地文件逐字相同：

| 运输输入 | 实读字节 | SHA256 |
| --- | ---: | --- |
| `moto5960-cpu-6a6dd8d309c3.transport.tar.gz` | 122667 | `b80edd66cfb9b7695ce215be57f0f69869177131125854236aa95747a8ebe14c` |
| `transport_manifest.json` | 7333 | `8ae5b4af9c8ad27056637c985e1b8817b2c41bf436905e3d1d62484b8ccb9755` |
| 同级 transport receipt | 553 | `94a5425b32e8ce53c7295a2c31652b44396733e06f9d26f756bb80245eb5dcc4` |
| 唯一 `.eval.log` | 49370 | `5b45ececd156bcada1f8120b8e4741f75d905e3ed1c9c87523b8a4540e5780ce` |

job status、scope、CLI 命令、唯一 ledger、completed_controls 和 result 相互一致：固定 R13 作业 `moto5960-cpu-6a6dd8d309c3` 使用 matrix v2，`--controls noop`，只完成一个 noop。入槽后实际运行，不是返回 75 的未开始状态。job、verify-release、image-inspect、prepare、export-gold、run-noop 的记录返回码均为 0。export-gold 只导出了 593B gold patch；没有 `run_gold` 或 omit 执行目录／ledger，不能把导出当执行。

唯一正式 report 是 `outcome=unresolved`、`failure_category=tests_failed`、`reward=0.0`，`stage_error=null`；F2P 通过 0／3，P2P 失败 0／155。这是原评分器产生的正常负分观察，没有改成 `failed_to_grade`，也没有因为安装失败回写其 raw reward。matrix v2 的“所选控制臂完成”状态只说明流程结束，`formal_cpu_accepted=false` 保留。

## 159 个原始测试项与 158 个 parser key

独立读取完整 log，按原 manager 的正式 Start／End Test Output 标记取段，核对原 R13 `swegym_parsers.py` 的 getmoto 映射：`parse_log_pytest` 以摘要行 `line.split()[1]` 作为 key。未导入或执行该 parser；在标准库读回中分别保留完整原始行和按这个已读源码规则形成的 key。

pytest 实际 `collected 159 items`，短摘要原始 159 行为 **156 PASSED／3 FAILED**；parser 形成 **158 个唯一 key，155 PASSED／3 FAILED**。唯一合键来自原参数名里的空格，两条完整原始节点分别为：

- `tests/test_dynamodb/test_dynamodb.py::test_set_attribute_is_dropped_if_empty_after_update_expression[use attribute name]`，实际 `PASSED`。
- `tests/test_dynamodb/test_dynamodb.py::test_set_attribute_is_dropped_if_empty_after_update_expression[use expression attribute name]`，实际 `PASSED`。

它们均映射到原 P2P 的 `tests/test_dynamodb/test_dynamodb.py::test_set_attribute_is_dropped_if_empty_after_update_expression[use`。两条状态一致，所以本次不存在一次通过覆盖另一次失败的误判。没有修改 parser、参数名或参考节点；不能仅凭总 parsed 数判断原始参数项已覆盖。

逐个比较 runtime／prepared 的参考分区与原日志状态，158 个唯一参考全部有结果，三组无重复、无缺失、无 skip、无未解释 key，ledger 与 diagnostics 的分区结果也一致：

| 原固定分区 | 引用数 | 实际状态 |
| --- | ---: | --- |
| original_f2p | 2 | 2 FAILED |
| added_f2p | 1 | 1 FAILED |
| original_p2p | 155 | 155 PASSED；其中一个 key 对应上述两条真实 PASSED 参数项 |

三个失败名称和原件中的实际断言分别为：`test_gsi_projection_type_include` 多出 `nonProjectedAttribute`；`test_lsi_projection_type_keys_only` 多出 `someAttribute`；新增 `test_gsi_scan_projection_keys_only_all_items` 的实际 item 仍含 `payload: alpha/beta`，与只含表／索引键的期望比较失败。它们有真实 pytest 失败体及 FAILED 摘要，不能说成收集失败或缺参考；本次仅确认实际观察，不重新裁定断言语义。

## 安装阻断、执行退出码和清理

log 399–432 行有真实 `make init` 调用、PEP517 隔离构建失败、DNS 重试及 `No matching distribution found for setuptools>=40.6.0`，随后 `make` 错误和独立 `RH2_INSTALL_CMD_FAILED=2 make init`、`RH2_INSTALL_RC=2`。安装并非跳过，安装时间 marker 完整，对应 9.047 秒。原公开 base 的 `pyproject.toml` 直接要求 `setuptools >= 40.6.0`；Makefile 的 init 先 `pip install -e .`，再安装 `requirements-dev.txt`。本次在第一项失败，不能说完整 init 已成功或第二项依赖已验。

候选包装 shell 随后实际运行 `pytest -n0 -rA tests/test_dynamodb/test_dynamodb.py`；正式测试段与时间 marker 完整，`RH2_TEST_RC=1` 与 3 failed／156 passed 的 pytest 摘要一致，记录测试时间 22.480 秒。**包装 exec 的 0 与 pytest 的 1 是不同层级**：shell 保留安装／测试返回码用于原评分解析，其最后命令完成为 0 不会把安装或测试变为成功。镜像已有 Python／SDK 使测试继续产生结果，也不能抵消 init2 的环境阻断。

可信 setup 日志实际从 base 恢复测试文件，核 base SHA `ca1defac3011d78ae2c19e8487298d3dec47571e3a94429f5dc98caa4d63c885`，有效 patch 应用 clean；`RH2_SETUP_APPLY_RC=0`、`RESTORED=1`、预期／实际文件各 1、absent 0、irregular 空、`RH2_SETUP_OK=1` 与 diagnostics 一致。控制面记录 `RH2_PROTECT_OK=1`、保护目录 3／文件 1、缺失 0、无 irregular；候选前后 runner digest 同为 `10a0308d887b21b702e28790379e06bfdbede40a5d5d04684757372d4d86f96c`，`runner_integrity_changed=false`。noop stage 与 grader sanitize 均保持 HEAD 为本题 base，exit0、无 violations；noop FrozenPatch entries 和 projection included paths 均为空。

ledger 的 grader policy 为 2CPU、4GiB、PID512、shm64MiB、tmpfs1GiB、deny_all，grader UID54322／rh2grader。该范围证据是固定 profile／policy 及原运行记录，本件没有额外 actual HostConfig 资源原件（`resource_facts=null`）；不伪称已独立 inspect 所有资源。它也不是 UID54321 的公开 agent 操作证据。

候选清理 `removed=true`、`steps=["rm:ok"]`。真实 CLI footer 的 manager 层 containers_created_total=1、removed_total=1，containers_open／supply_open／cleanup_failures 都为空，final_status exit0／reason ok、grader_containers_open 空。matrix 原脚本查询仅按 `label=rh2.run_id=moto5960-cpu-6a6dd8d309c3-noop` 读取自有 containers 和 networks；`residual_noop.json` 两次查询均 returncode0，stdout／stderr 空。查询成功和零残留分别有证据，没有把查询失败当空结果，也没有扩大到共享对象清理。

## 本题 source、消费者与旧身份

source 身份独立取自本题真实 `image5960_source_receipt.json` 和本 job `image_inspect.stdout`，并与 R13 冻结 environment recipe、prepared／runtime、ledger／noop FrozenPatch 核对：

| 身份 | 固定值 |
| --- | --- |
| base | `d1e3f50756fdaaea498e8e47d5dcd56686e6ecdf` |
| source ConfigID | `sha256:c67dbd356fcaa937ebff4b3fe0d78e4ea78211888233a4e5f07da95eddfe079d` |
| source manifest | `sha256:4b71766331736b51bd74bb86cdb5e4e21040a7816e01fbb5d914526d33ef8944` |
| public bundle digest | `sha256:a09554119b86752f15f8b2fa12eb31a559e92dc28b3334565e8b94ae50862336` |
| 原环境 digest | `sha256:b2196e4ede419b3a4d7e9d31ffffdd0d9f5b482061be3505b8b07cb06ac292d6` |
| 原 grading bundle digest | `sha256:1d59b3e30499d16fcc0291b69d5a7a4c297d84bab9ae06f22456f7031aadd3d5` |
| 原 materials identity | `sha256:7311f6778339f92f416fe6f5a45c90732d7254233e95dbfd04a433f066260b5a` |
| 有效 test patch | 2571B／`b9a656bde376f6fefa3dd33b16dad74704b50213795b3c52dfcecfa3c57c296e` |

本题 source receipt 为 765B／`82d4fe2eb121b740aac543d1319ad1c92bc92792d535365deb50b9ef12d8d68f`，成功 pull 和 source manifest 指向上述 ConfigID。实际 image inspect 含相同 RepoDigest、13 层、amd64／linux。这里没有借用 6408 的 source ConfigID。

R13 发布 manifest 实读 SHA `3fad18daff8db219294e10cbf08d4424d68cf7000d008bb983cba4bdc427b641`；本题冻结 registry 为 `24e502bd738d60eee73ccac1a4c859551f59385f30950f6b60518728f664ab89`，recipe 只登记本题原 source／receipt。实际 CLI `--derived-image` 传上述 source ConfigID，`--derived-image-recipe moto5960-fixed-environment-v1` 走既有 exact local override 诊断路径。ledger 因此显示 `image_local_build=true`／`local_build:<ConfigID>`、expected digest null；这并不是已经生成新的 COPY 供应镜像。public face 与实际 consumer 原始 image 仍为本题 source tag，overlay null、qualification absent，actor 未执行。

实读 `consumer_readback_before_checks.json` 与固定 matrix v2 本题 `expected_runtime.json` 整体一致，包括五份脚本 SHA、base、材料／环境 digest、3F155P、install／test 命令和原 revision context。prepared manifest 的公开／私有文件摘要与实物一致；private view 的有效 test patch 字节等于固定 patch。ledger 和 diagnostics 的 revision／registry／材料身份及分区一致，scripts_digest 同为 `sha256:f75391fc7b665f2fc8246c63163a58127899ab28dadb8378842f94edfeba39d6`。这些是原消费者字节绑定和实际执行记录核对，不是重新执行消费者。

原预算记录保持 setup300／apply120／test1800 秒，candidate stage900、whole grading1800、cleanup120、image pull1800 秒；新输入 `original_budgets` 与相应 runtime 记录一致。未执行的 omit patch 仍为 712B／`5ddf1b01fdf43ecf0bc1a18e6d20908ff20ae70737d01ea00324f3a52fb1c734`，匹配固定控制输入；其旧 R5 分数不能由本次 R13 noop 推断。

作者 `read_r13_matrix_raw_v2.py` 仅作为文本核对（6809B／`4ce24ba3ce82ae0a6383d247eee41d56e44c8cd33adda7a892c999c07ecdc8f6`），没有执行。作者读回 JSON（52614B／`f73199a546f6e926cb1637def73aca120e56e7dc2b8c5b93e99c8681a2f58ac0`）的全部逐参考状态、两条合键原行、失败行、report／test／install 与独立读回相符，`install_complete=false` 也正确。作者报告（2882B／`4dd53803f95fee119df376279a7b6f57c1014cbee8ee958508c9ec9417de59d7`）没有把 noop／包装退出0写成 CPU 通过。

## 新离线供应材料可提交，交付与运行仍待验证

新请求为 `publication_requests/swe-moto5960-offline-env-publish-20261003-v1/`：input 为 23922B／`de6510d19c7c6aab880640d08f404f22a04890fd0725c20354673fbc29988123`，Dockerfile 为 126B／`352caaf2eae8dc6fdb3291e9afaf85281a0b0199d6b3ee091d9e3d3247d44993`，wheel manifest 为 477B／`660fa7aa83d8c3cedeb5e188ef7a4de0621e6011a37be48958813a6c50425a55`。输入中的 10 个直接 path／SHA／bytes pin 均与实物相符，三件历史 wheel 另外逐件核对：

| wheel | 字节 | SHA256 |
| --- | ---: | --- |
| packaging 24.1 | 53985 | `5b8f2217dbdbd2f7f384c41c628544e6d52f2d0f53c6d0c3ea61aa5d1d7ff124` |
| wheel 0.43.0 | 65775 | `55c570405f142630c6b9f72fe09d9b67cf1477fcf543ae5b8dcb1f5b7377da81` |
| setuptools 72.1.0 | 2337965 | `5a03e1860cf56bb6ef48ce186b0e557fdba433237481a9a625176c2831be15d1` |

三件实物来自固定历史 `install_wave1_inputs_v1/wheels/`，manifest 的名称、顺序、摘要、字节数与请求一致。文件实读 mode0644、wheel 目录0755；ZIP 元数据分别吻合版本且 Requires-Python≥3.8，与原件 Python3.12.4 没有静态版本矛盾。setuptools72.1.0 覆盖本次已经暴露的 ≥40.6.0 需求，但三件 wheel 不能静态证明完整项目安装或全部开发依赖已经满足。

Dockerfile 只有 `ARG BASE_IMAGE`、`FROM ${BASE_IMAGE}`、`COPY wheels/ /opt/rh2/build-wheels/` 和 `ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`；没有 RUN、联网 build 命令、项目层写入或预安装项目依赖结果。请求指定本题 source manifest／ConfigID作为来源，要求 source 层是新镜像层完整前缀，并把实际 derived ID 保留为 null，等待真实构建登记。原公开 source、base、有效 test patch、三个 F2P／155P 顺序、make init、测试命令、预算均与本轮消费者一致；新环境 digest、registry／消费者和实际镜像身份应显式另登记，不能复用旧 R13 identity 冒充新供应条件。

0755目录／0644文件和 root:root 的交付策略、复制前归一化、输入及实际容器 stat、实际 UID／GID54321 读取各 wheel SHA 均已写入 `required_delivery`。本地 mode 支持该计划；本次没有新镜像原件，不能据此断言容器内归属、父目录可遍历或 UID54321 已读到正确字节。需要交付记录实际 derived ID／环境绑定、source13层前缀、wheel bytes／mode／实际 stat 和 agent UID54321 读取证据，再 fresh prepare 核 3F155P 与命令，实际完整运行原 make init。若出现新的依赖缺件，保留原失败并按具体证据处理，不能预告三 wheel 已解决全部安装。

请求明确 `formal_cpu_accepted=false`、无新模型运行、不静默改绑旧 probe／FrozenPatch／material。以后该 COPY-only 镜像用于 actor／grader exact 诊断也须分别记录条件；本报告不授予 typed actor 或训练资格。后续 gold／omit、UID、公开操作和整题验收仍未完成，均按题主已有计划执行。本报告没有新增审批闸门。
