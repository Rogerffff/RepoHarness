# Moto6408 原镜像 CPU 原件与离线供应发布输入非作者窄核

2026-10-03。结论分为三项：**原镜像三臂真实评分观察为 0/1/0，运输、测试参考与清理原件相符；三次 `make init` 均退出 2，环境阻断未解除，不能验收 CPU 或据此提交普通模型探针；固定 COPY-only 供应请求没有发现提交发布前的静态阻断，可提交发布。** 新镜像尚未构建/登记/部署验收，权限和安装修复不能写成已经通过。

## 范围和固定输入

独立读取以下本地原件：`publication_requests/swe-moto6408-offline-env-publish-20261003-v1/` 的 input、Dockerfile、wheel manifest 及其逐项固定来源；`runs/category2_repair_20260929/moto_cpu_20261003/moto6408-cpu-1efc480be0d1_evidence/` 的 73 件原件及 transport manifest；作者 `read_r13_matrix_raw_v2.py`、`moto6408-cpu-1efc480be0d1_author_raw_readback_v2.json` 和题级 CPU 报告；固定 R13 parser、候选 exec/安装分段的相关源码。只使用标准库读取、哈希、JSON/文本/ZIP metadata 和独立逐参考核对，不导入或执行作者脚本、RH2、SDK、项目测试、Docker、远端、CPU 或模型。不修改原件、共享记录、工具、旧报告或请求，仅新增本报告。

审查者已接触私有材料与反例，非盲 solver；本次不重复题级测试断言语义审查。已有 R13 工具报告的其他静态项按原范围复用。本题这次是 R13 修订测试在原 source 物理镜像上的诊断，不是旧 R5 原材料评分，不推断旧 R5 的 `reorder_only` 分数。

| 固定发布文件 | SHA256 | 字节数 |
| --- | --- | ---: |
| `input.json` | `308faa9b858d685694985007c6bb95acdfc80a36ec9d68ad2d54082dd1cd459a` | 17529 |
| `Dockerfile` | `352caaf2eae8dc6fdb3291e9afaf85281a0b0199d6b3ee091d9e3d3247d44993` | 126 |
| `wheel_manifest.json` | `660fa7aa83d8c3cedeb5e188ef7a4de0621e6011a37be48958813a6c50425a55` | 477 |

input 中 12 项带 path/SHA/bytes 的直接来源均独立读取匹配，含上一发布输入、source receipt、作者报告/读回、transport receipt、三份真实日志、Dockerfile、wheel manifest、effective patch 和 source public。上一固定发布 input 为 `b25ce17edd9ea26fe717cdc6e84774651fb74490c9fafec17b5fae2c08f41928` / 29504B；本次没有覆写它。

## 73 件 CPU 原件身份与实际三臂

transport manifest SHA 为 `dc68af38af0a40043ddf46e8b4cbd2a825e2041add8dc5748bd582d331f07c1c`。独立核其全部 73 个普通、非符号链接文件的 SHA/bytes，合计 1893519B；目录文件集合恰为这 73 件加 manifest，无缺失或额外结果件。运输 archive 实际 SHA/bytes 为 `a5f97320b0eaa0e2b023bb8553c019e12fd593086cff1185de69762e779cff75` / 368277B，与 receipt 相符。没有仅接受 `all_sha256_and_length_match=true`。

原作业 `moto6408-cpu-1efc480be0d1` 使用固定 `moto_four_r13_matrix_v1` manifest `a72d5d57e6c85f12105642ac1ef91e1aa18e618afb39ddd93133184850b7ef99`，selected controls 为 noop/gold/reorder_only，job、三个原 CLI 和整体正常退出均为 0。输出仍明示 `formal_cpu_accepted=False`、`actor_executed=False`、model attempts 0；这些退出码不能替代安装成功。

| 臂 | 安装 marker / make init | 包装 exec / pytest RC | 收集与解析 | 原 1F / 95P 状态 | 原始 reward |
| --- | ---: | --- | --- | --- | ---: |
| noop | 2 | 0 / 1 | 96 / 96 | F 失败；95P 全通过 | 0 |
| gold | 2 | 0 / 0 | 96 / 96 | F 通过；95P 全通过 | 1 |
| reorder_only | 2 | 0 / 1 | 96 / 96 | F 失败；95P 全通过 | 0 |

三份真实 eval log SHA/bytes 分别为：noop `f371b115f631e6262c4e6628aef815bc9a3c36873ff5474e36eae89e2f49c7f9` / 35565B；gold `9a899a6f691ddb5496b59317d0cc214716e1661ee727f44c0e7acf0dd3e9ca32` / 34077B；reorder_only `36ba4db403bd62f38c422fbf6b9eec334c97109363d84ce538394b7bd35ec94c` / 35950B。各自还与 ledger 的 log SHA 相符。

没有调用项目 parser；仅读原固定 `swegym_parsers.py:44–56` 的 getmoto 摘要映射规则，再独立读取官方 Start/End Test Output 段内的状态行。每臂恰有 96 个 raw summary 行和 96 个唯一 key，无重复合键；键集合恰为固定原 1F/95P 全集，每个参考都被核对，不是仅看总 passed 数。ledger/diagnostics 的 reference_missing、reference_skipped 均为空，segment 外解析计数为 0。与作者 v2 的完整 `reference_statuses` 逐项相同。

两组负臂唯一失败节点均为 `tests/test_ecr/test_ecr_boto3.py::test_multiple_tags__ensure_tags_exist_only_on_one_image`。noop 原 log:605 定位测试文件第 630 行的 manifest 相等断言失败；reorder_only 原 log:621–624 显示 `assert 2 == 1`，定位第 635 行；gold 的全部 96 项状态为 PASSED。这里只报告已执行分支与断言结果，不重新论证题级断言语义或从该观察推断旧评分误判。

三个 ledger 均 stage_error 空，report 为正常 resolved/unresolved、None/tests_failed、reward1/0 的来源语义结果，F2P/P2P 分母分别 1/95。这次没有出现此前 v1 窄核指出的 failed_to_grade/null reward 继续后臂路径；同时，新增正常 report guard 本身也不能证明安装通过。安装错误仍必须读原 install 段。

## 安装阻断及作者 v2 的退出码修正

三份 log 的 PEP517 build dependencies 子进程均尝试取 `setuptools>=40.6.0`，在隔离/断网环境中 DNS 重试后报告无匹配分发；随后 make 返回 2。三个独立无 xtrace 前缀 marker 均为 `RH2_INSTALL_RC=2`，`RH2_INSTALL_CMD_FAILED=2 make init` 也在场。ledger 的 `install_failed_commands=[{'cmd':'make init','rc':2}]`、last command RC=2、`install_skipped=False`、`log_partial=False`；安装段完整结束约 9.206/9.114/9.161 秒，**完整结束不等于安装成功**。测试继续使用镜像已有环境，约 12.724/13.318/13.864 秒，不能将测试可运行改写为依赖安装成功。

实际测试 marker 分别 `RH2_TEST_RC=1/0/1`，与 ledger 的 pytest RC 一致；候选 shell/docker exec 包装退出均为 0，segment completed true。固定 manager 的候选 exec 路径按候选身份执行脚本并保留独立 install/test marker，不能要求包装 exec RC 与 pytest RC 相等。原 CLI 正常 footer 的 exit 0 同样只回答入口/清理收口。

实际读取的作者 `read_r13_matrix_raw_v2.py` SHA 为 `4ce24ba3ce82ae0a6383d247eee41d56e44c8cd33adda7a892c999c07ecdc8f6` / 6809B；其 v2 JSON 为 `53861222293fdc99d7d7c335860867044e32fd69235aef12ae74a3203e874241` / 89906B。v2 的 `test_complete` 条件正确分开 wrapper=0、pytest∈{0,1}、唯一实际 marker、完整段落；`install_complete` 还要求无失败命令且 last RC=0。独立核得到三臂 `test_complete=True`、`install_complete=False`，与作者 v2 一致，report/install/test 和逐参考读回亦相同。没有执行该脚本或将其布尔值直接当独立结论。原 v1 的包装/pytest 混比修正不改变安装失败和原 reward；原文件与运行原件保留。

## 材料、来源镜像和清理

原 source receipt `cd618f417622ff8d40a51d434f7f1dc40c60d403828d44fc83f5b6dbf325d86d` / 765B，与 transport 中 image inspect 的物理 ID、RepoDigests、linux/amd64 相符：source manifest 为 `sha256:db52bf5253616c8662863703accf3ad9e5c20e809e63f2e5829b48fb1212f8a4`，actual Config ID 为 `sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689`，source RootFS 13 层。三臂原 run 确实通过 R13 既有 `--derived-image <source Config ID>` / registered recipe `moto6408-fixed-environment-v1` 诊断入口，ledger local_build/actual ID 是该路径的记录，物理镜像仍是 source；没有已有 COPY-only 派生镜像可供本次冒用。

runtime inputs 全部固定 expected 项与原 R13 工具 expected 相等。source public 文件实际 SHA `d195f0b824555d8340301d17fa9c145e1bc82d3033a1399220e115ba87326fc2` / 3027B，独立 canonical digest 为 `sha256:614eff48270224a61e540333a4588303eae4f76e5d3e259e894e78db7e16ba71`，base 为 `1dfbeed5a72a4bd57361e44441d0d06af6a2e58a`。固定 effective test patch `00546841fca20f0b6b781fb49124370d0dab60bf99fdcd01e55aa947b4b65365` / 2977B 未变；原 test patch 2001B、原 grading 文件、原 base identity、gold 993B 与 reorder_only 290B 的既有 pin 也匹配。原 grading 的完整 fail_to_pass/pass_to_pass 列表、旧发布输入、R13 expected context 和本次发布 preserved partitions 全部相同，仍为 1F/95P。

ledger 与 diagnostics 的脚本 digest 一致，并绑定既定 runtime script SHA；trusted setup 原件均 restored=1、apply RC=0、absent test files=0、irregular 空、setup OK=1。git sanitize HEAD 前后均为该 base、RH2_GIT_SANITIZE_OK=1，runner_integrity_changed false。固定 install/test 仍是 `make init` / `pytest -n0 -rA tests/test_ecr/test_ecr_boto3.py`。spec 预算 setup/apply/test=300/120/1800 秒，CLI candidate/outer/cleanup/image-pull=900/1800/120/1800 秒；外层 1800 是原本明确选用的诊断期限，不冒称原 CLI 默认 3600。

每臂候选 cleanup removed=true，rm:ok；最后原 CLI footer rows=1、halted/aborted 空、manager containers_open/supply_open/cleanup_failures 全空、manager created/removed 均为 1、final exit=0。之后按该臂独立 run_id 查询的自有容器和网络都实际 query RC=0 且 stdout/stderr 空，没有把查询失败当零残留。`reorder_only` 的候选 kind=`cc` 是原 patch 输入枚举，不是执行了真实 CC。

## COPY-only 供应材料是否可提交

Dockerfile 全文仅为 ARG/FROM、`COPY wheels/ /opt/rh2/build-wheels/` 和 `ENV PIP_NO_INDEX=1 PIP_FIND_LINKS=/opt/rh2/build-wheels`。没有 RUN、下载、项目源码覆盖或预先 pip 安装；BASE_IMAGE 参数需在发布构建时固定到上述 source，而不是任意 latest。input 明确要求完整 source 层作为新镜像层前缀，实际 derived ID 当前为 null，登记新配方 `moto6408-offline-build-wheels-copy-only-v1`、新环境/consumer 和实际 ID，不继续冒用旧 R13 actual ID 或旧环境摘要。发布输入引用旧 context 的字段名为 `grading_context_before`，没有声称新环境身份仍与旧 digest 相同。

三件历史 wheel 的本地普通文件独立 SHA/bytes 与新 wheel manifest、input 和历史 `install_wave1_inputs_v1/wheel_manifest.json` 全部相同：

| wheel | SHA256 | 字节数 |
| --- | --- | ---: |
| `packaging-24.1-py3-none-any.whl` | `5b8f2217dbdbd2f7f384c41c628544e6d52f2d0f53c6d0c3ea61aa5d1d7ff124` | 53985 |
| `wheel-0.43.0-py3-none-any.whl` | `55c570405f142630c6b9f72fe09d9b67cf1477fcf543ae5b8dcb1f5b7377da81` | 65775 |
| `setuptools-72.1.0-py3-none-any.whl` | `5a03e1860cf56bb6ef48ce186b0e557fdba433237481a9a625176c2831be15d1` | 2337965 |

ZIP METADATA 的名称/版本与文件名相符；setuptools72.1.0 满足原安装明确缺少的 `>=40.6.0` 下限，三件 wheel 的 Requires-Python 均为 >=3.8。这里只证明供应字节及其针对已见缺件的合理性，**不能静态保证 make init 后续所有依赖步骤一定通过**。发布端仍需按本请求构造仅含这三件的 wheels build context，不用更换项目依赖版本或执行项目安装来制作镜像。

本地历史 wheels 目录实际模式为 0755、三文件为 0644。请求同时明确发布前规范目录0755/文件0644/root:root，并记录 input stat、actual container stat 和 UID/GID54321 的实际读取 SHA；这套权限使非属主 UID 能遍历供应目录、读取文件，避免以 root 可读代替 agent 可读。Dockerfile 本身没有 chmod，故它依赖请求已明确的上下文规范化步骤；本地 mode 符合不能替代新镜像的实际 stat/UID 交付证据。candidate exec 原 manager 路径以候选 UID 执行并继承镜像 ENV，非默认 env-i 的 root 维护路径，未发现新 PIP ENV 在原候选安装入口必然被清除的静态冲突。

现有 UID invocation `moto6408-uid-53e556c49aca` 的本地 exit 原件仅记录 SSH command RC=75，没有完成的 UID 结果或 wheel 读取证据；按任务交接这是未入槽/未开始，不能作环境失败样本或 UID 通过。当前 CPU apply_user 中的 agent/54321 也不能替代新供应镜像的专门 UID/GID 读取验收。

## 阻断与验证边界

提交发布前没有发现 pin 不符、遗漏三件 wheel、非法项目改动、旧材料/环境身份冒用或权限交付要求缺失这类静态阻断。**原 source 环境的安装失败仍是明确阻断，不能用 raw reward、CLI rc0、既有镜像能跑测试或尚未开始的 UID 消去。** 本报告允许提交这个环境供应请求，不声称它已经完成发布或修复环境。

后续应完成 input 已列明的交付与局部复验：固定 source 构建及层前缀、新 derived ID 与环境/consumer 登记、fresh prepare 保留 public/base/effective patch/1F95P/命令/预算，实际 UID54321 的 stat/读取 SHA，再按题主原计划复验 make init 三臂及公开开发操作。actual actor image_override 与 grader 诊断镜像分别记清；公共 source face、旧 probe/FrozenPatch/material 与旧 CPU 失败原件不改绑，不授予 typed actor 或训练租约资格，也不据6408的已见缺件自动改5960或其他未运行题。这里没有增加原请求之外的审批或扩大控制臂。
