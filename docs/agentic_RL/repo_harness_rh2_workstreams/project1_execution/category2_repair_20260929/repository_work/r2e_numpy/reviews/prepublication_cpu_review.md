# NumPy d805：登记新版前的 CPU 证据独立核查

2026-10-03。核查者非候选／草案作者，沿用本包静态意见；本次只读下载证据、冻结源码与输入包，未 SSH、未调用 Docker、未重跑测试。只写本报告。

## 结论

**未发现阻止按当前材料登记新版的实质缺陷。** 原始证据支持：在本轮重建的 r2e-mr-056 父版上，hybrid 与 K-A5c 正式 reward 都为 1；在未登记的测试草案上，K-A5c 为 229 项通过，hybrid 和 K-A5b 各只有 `TestMaskedArray.test_str_repr` 失败，分别命中新阈值摘要和大 edgeitems 判据。结果与上一轮静态推导一致，K-A5c 可以继续作为新版正式验收的主正对照。

**草案三行不是新版正式评分。** 新材料尚未发布，不能把它们写成“新版正式 1／0／0”，也不据此授予 `probe_ready` 或训练资格。登记后的正式矩阵、材料／镜像身份和修订题面的实际交付仍须验收；本次没有新增测试要求。

## 身份与执行绑定

核查入口为本包 `cpu_prepublication_evidence.json`。原始目录：`runs/category2_repair_20260929/r2e_numpy/cpu_b_20261003/remote_evidence/`；下文 `D` 指其 `packages/r2e_numpy/diagnosis/parent-and-draft-v1/`。

- 冻结 release 的 `manifest.json` 重算为外部指定的 `282021962a92b510f077385660ac56acedcd7fac1d97e63db3baa98e4dcc057f`，794 个文件逐一与 size／SHA 清单一致。没有执行冻结代码。
- 本地上传归档 `draft-inputs-20261003-02.tar.gz` 的 27 个文件摘要逐一吻合；input manifest 为 `6c7a263d…`，wrapper 为 `db2ec638…`。归档中的 expected 与本包当前文件逐键一致，229 键全部预期 PASSED；草案全文逐字等于本包 `private/test_1.py`，摘要为 `09d0aa6d80f85d394fc0a7971e23de8dd43a79d817749f0246693f62898bf67a`。
- `D/input_binding.json` 与题级证据绑定一致；build facts 的摘要为 `2df7f6b8…`。本次实际父镜像为 `sha256:3f061f94abbe3bcf729c2e9b899378108136a36118bb317ecd76be9b09e67eb0`，配方为 `r2e_derive_v1+material_v2+sysconfig_v1`，仅含 r2e-mr-056。它是本轮重建身份，不冒称旧 v8 的 `c596cd48…` 镜像。
- build context 中父测试重算为 `14d78a1c…`；正式原日志恢复的 hidden tree 为 `71326af5…`、入口为 `8285765f…`，与 build facts 一致。三个草案容器的 `hidden_test_sha256.log` 均记录 `09d0aa6d…`，不是只根据草案文件名判断版本。
- 构建与诊断 job 的原始状态均记录 returncode=0，时间和命令与绑定吻合。wrapper 没有改候选、测试判据或正式 parser；私有 trial 显式固定父镜像，增加 2 CPU／4 GiB 限制、保存完整输出并检查测试摘要。它仍保留 trial 原有的 root 应用补丁、简化权限和不做评分基线重建的差别，这些已在证据中列明。

## 父版正式两行

分别核 `D/formal_parent/{hybrid,K-A5c}/` 的 ledger、完整 eval log、stage、projection、baseline manifest、frozen patch 和 candidate patch：

| 候选 | 原始评分结果 | 独立核实 |
| --- | --- | --- |
| hybrid | reward=1，229／229，resolved | 非空补丁由 agent/54321 以 git_apply 应用；仅投影 `numpy/ma/core.py`；无 stage_error；日志 test rc=0。 |
| K-A5c | reward=1，229／229，resolved | 同上；没有把 noop 或其它补丁当作正对照。 |

两份 ledger／eval log 的 SHA 与引用相符。独立从 Start／End 之间原始 pytest stdout 重取 229 个状态键，均与完整 expected 严格相等；没有 missing／extra／mismatch，也没有用段外结果凑数。原日志分别记录 `229 passed` 与 `RH2_TEST_RC=0`，不是仅采信 resolved 标签。

两份 baseline manifest 的 canonical SHA 与 frozen artifact 的锚一致；frozen artifact 重算 SHA 与 ledger／projection 一致。解码后的唯一源码文件逐字等于输入候选对公开初态的补丁应用结果，也等于保存的 candidate.patch 应用结果；baseline 中 core、arrayprint 和 testutils 摘要与指定公开初态吻合。ledger 记录完成评分基线重建，runner integrity 未变化。清理记录均为 `removed=true`、`rm:ok`；没有 stage／infra 错误。

这些是父版正式评分证据。ledger 中环境资格仍为 absent，不据这两行外推普通探针或训练准入。

## 草案三行：实际失败机制

核 `D/private_trials/draft-<候选>/` 的 `result.json`、`docker_calls.json`、`003.stdout.log`、`009.stdout.log`、实际测试摘要与删除输出。完整 result／stdout 的 SHA 与题级证据相符；独立重取 stdout 状态后，与 result 的 observed 逐键一致，均为 229 键、无 missing／extra。

| 候选 | 原始 pytest 结果 | 决定性断言 |
| --- | --- | --- |
| K-A5c | 229 passed，test rc=0 | `test_str_repr` 通过，因而两个新增断言都实际执行并通过。 |
| hybrid | 228 passed、1 failed，test rc=1 | `test_1.py:499`：n=3000／threshold=2000 应摘要。完整 AssertionError 中的 ACTUAL 经文本解码为 1500 个 token，保留索引 0–749 和 2250–2999，没有省略号，确实静默丢掉中间 1500 项。 |
| K-A5b | 228 passed、1 failed，test rc=1 | `test_1.py:511`：edgeitems=501 的 token 断言，ACTUAL=1002、DESIRED=1003。此前提高阈值的摘要断言已通过；失败与该补丁裁成首尾各 501 项、原 formatter 不插省略号的源码机制一致。 |

三行唯一差异键与声明一致，没有把补丁应用失败或测试未执行算作负例。应用原始输出均有 `Applied patch numpy/ma/core.py cleanly` 和 `RH2_APPLY_RC=0`；草案应用记录为一条增量成功。所有保存的 Docker 调用 returncode=0、stderr 为空；这里负例测试进程的真正 rc 由 `RH2_TEST_RC=1` 单独记录，外层 shell rc=0 不被误读为测试通过。

三个容器均有原始 `rm -f` 返回 0 与对应容器名输出。wrapper 还在删除后查询同名容器，只有查询成功且输出为空才接受并继续；诊断 job 完整返回 0，支持复查成功。该 ps 输出没有另存原始日志，证据强度限于原始删除记录加已绑定 wrapper 的完成控制流，不声称本次独立查询了远端实时状态。

hybrid 在第 499 行停止，不能说它也执行了第 511 行；K-A5b 命中第 511 行，才证明它已越过前一处。这不影响两个断言各自的区分力。

## 登记后接续及正对照边界

沿用 `publication_handoff.json`：合并替换本题已有 r2e-mr-056 的同目标条目，从原始来源重放，发布新的版本化测试全文与题面，保留旧文件／旧评分；不要在同一 target 再追加一条。

登记后按现有验收计划完成新版正式矩阵，并核正式恢复的材料摘要及决定性失败位置；新题面的实际 solver 消息交付仍待验。当前证据已解决新增反例是否真实有效、K-A5c 是否能通过完整草案的准备缺口，不需要为登记再造其它候选或扩展到二维、性能和共享平台。

K-A5c 的已验证范围是本轮一维打印实例与完整 229 键草案，不等于所有 dtype、子类、打印参数或性能都完整正确。旧 K-A5b 的父版通过记录继续保留；它不再是新版的主正对照。没有需要现在改动候选或判据的阻断项。
