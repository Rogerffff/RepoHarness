# Moto6114 修订版 CPU 验收

2026-10-03。题主：`SWE | Moto 题目修订`。修订版三臂为 **noop／gold／wrong_first = 0／1／0**；每臂完整执行原 1 F2P 和 34 P2P，安装、测试解析与两层清理均完成。新宿主 UID／激活／导入原件也已读回通过。最终非作者结果复核已通过，必要 CPU 准入条件已满足，可固定单题探针请求；模型、行为分析及最终用途尚未收口。

## 解决的问题与范围

原 F2P 仅检查 ARN 查询返回一条记录，已知错误候选返回第一个集群也得到 1。当前有效测试保持原节点与参考顺序，检查 ARN 查询返回的 Identifier、ARN 均对应请求集群，并检查名称查询定位同一对象；只比较稳定身份字段。原公开题面、安装命令、选择器和 34 条 P2P 不改；跨账号、地区及服务 ARN 的未约定行为不扩入目标。

| 对照 | 实际结果 | 决定性证据 |
| --- | --- | --- |
| noop | reward 0；1 F2P 失败，34 P2P 通过。 | 基线 ARN 查询产生 `DBClusterNotFoundFault`；未到新增身份断言。 |
| gold | reward 1；35 条全通过。 | 原 gold 补丁的 ARN 定位修法满足新增身份检查及所有原回归。 |
| wrong_first | reward 0；仅 1 F2P 失败，34 P2P 通过。 | 原 eval log 的 `test_rds_clusters.py:268` 实际比较 `cluster-id1` 与请求的 `cluster-id2`，在新增 Identifier 断言失败；数量检查已通过。后续 ARN 断言因首个失败未执行，不能分别记作失败。 |

三臂无缺失、跳过或未对账参考；原 `make init` 的两轮 editable 构建和安装完整成功，原 `pytest -n0 -rA tests/test_rds/test_rds_clusters.py` 完整结束。wrong_first 的测试退出码 1 表示正确拒绝，CLI 退出码 0 表示实验收口成功，两者分列。

## 固定消费及实际环境

- CPU 发布为 `cat2-cpu-r2e088-swe12-git-20261003-v1`，905 件，外部 manifest SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`；实际 `runtime_cpu_v2` 消费该冻结。
- 修订为 `moto6114-cluster-identity-v1`／`replace_test_patch_preserve_refs`；registry SHA `27e1b01dfec9aa2284e79fec753f70b62f6bd45462346483484f98785a59ae22`。有效测试补丁 SHA `fe211059864c661a557758f5c5ed4106016c767cbe98eaef4718733008a87d5f`；原补丁 SHA `32beadd88d5189dcab69b796980a93c464cb7b6f9d16bc8329d5da3e80571b61`。
- public／grading／environment digest 分别为 `sha256:6c8f45da003f8e8d1e065d1801afa4659c43cbb212e319a5d07a84922af5f0f2`／`sha256:e33ad739c3f8f9ebe4ba1210e7527b100fa6ff257131cad9f1f0a23653b01f3d`／`sha256:a791b087e4475a2a4f7d70183e7031a711e077091206e7826a3203cd32189f41`。材料身份为 `sha256:44bef90dc4148f74ad2b2e26e2c9d09e09b20993ae8c734c67d8df83e92c6309`。
- HEAD 保持 `f01709f9ba656e7cf4399bcd1a0a07fd134b0aec`。实际派生镜像为 `sha256:1d8dded2ee5bbe9275514fdc603116ac9f36da5e30c19b2d4ffcba4d4a9f27d5`；源镜像 manifest 为 `sha256:cb35f7e131f8e46c8a6865e8fb618c09032ce5ee27f1122f79010a7cfae8ef9a`。COPY-only Dockerfile、三个离线 wheel 的配方和二进制各自固定 SHA，不把 tag 或 CPU image ID 视作 GPU 已有镜像。
- 评分实际限额为 2 CPU、4 GiB、PID 512、shm 64 MiB；setup／apply／test = 300／120／1800 秒，candidate／whole grade／cleanup／image pull = 900／1800／120／1800 秒。候选补丁由 agent UID 54321 应用；grader UID 54322，网络关闭。

## 作业与原件

| 作业 | 范围与原件 | 收口 |
| --- | --- | --- |
| `moto6114-cpu-ffe3a2e97334` | v3 已完成 noop，43 件原件 SHA／长度匹配。之后导出 gold 的目录与结果目录重名，外层 rc1；gold／wrong_first 零执行。 | 已完成 noop 的 [独立复用窄核](../../reviews/moto6114_v4_entry_and_noop_reuse_non_author_20261003.md)接受复用；保留原 rc1，不机械重跑。 |
| `moto6114-cpu-0661259fc3d1` | v4 仅补 gold／wrong_first，rc0，59 件原件 SHA／长度匹配。入口清除 SWE 不支持的 R2E overlay，调用原 prepare／export-gold／run。 | 两臂 candidate 删除成功，manager 的容器／供应／失败清单为空；自有容器和网络查询均成功且为空。 |
| `moto6114-uid-83565d38db45` | 新宿主 network none 检查，rc0，5 件原件 SHA／长度匹配；12 次 Docker 调用全 rc0。 | 生产 sanitize／init／activation 成功；实际 UID/GID 54321、`/testbed`、conda testbed 解释器、本地 Moto/RDS 源码与 boto3/botocore 1.35.9 正确；实际镜像和限额相同，删除成功且容器／网络零残留。 |

原件都保存在 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`，各目录的 `transport_manifest.json` 逐文件记录 SHA／长度。gold／wrong_first 原 archive 已在远端形成；一次 SCP 中断后回收同一 archive，未改原件或重跑任务。独立于此的旧材料诊断、入口读回失败、暂停及槽忙 rc75 均保留，不计入新三臂的题目失败。

题主读回：[noop](../../reviews/moto6114_noop_owner_readback_20261003.json)、[gold／wrong_first](../../reviews/moto6114_gold_wrong_first_owner_readback_20261003.json)、[UID](../../reviews/moto6114_uid_owner_readback_20261003.json)。最终结果见 [非作者 CPU 原件窄核](../../reviews/moto6114_final_cpu_non_author_20261003.md)。历史证据不回写为当前结果。

## 公开操作复用与探针边界

历史三条真实 Claude Code 公开工具路径具有完整轨迹与 capture：身份检查 rc0、B 集群 ARN 的预期错误 rc1、原公开 `-k describe_db_cluster` 测试 4 通过／31 deselected。功能题面与公开材料未改；来源镜像、COPY-only 配方、SDK、CC 和资源限额的条件已逐项核对，新宿主实际 UID 检查补齐物理 derived image ID 变化后的证据。按 [历史公开 actor 独立复用核查](../../reviews/moto6114_public_actor_reuse_non_author_20261003.md)限定范围接续，不机械重跑同三条命令。

历史两个 legacy 检查标志仍为 false：解释器模板没有命中实际 `PY_CHECK` 输出，写拒绝未在那三条 CC 命令中测试；不能改写为历史工具通道已测。历史 devcheck 首请求为操作检查，未证明自主理解功能题面，也没有冻结导出；本次矩阵的 `candidate.kind=cc` 是 patch 输入枚举，不是真实 CC。**本记录不宣称新的 CC actor、模型试解或本题 fresh a2g 已运行。** 共享路径已由 5406 的真实 actor／原冻结工件 fresh 评分代表验证；6114 探针仍须新建实际 prepared、baseline 和原 FrozenPatch，再直接评分。

[public_dev_brief.md](public_dev_brief.md)仅补中性环境、解释器／导入检查、原安装与模拟 AWS 凭据，原公开 hints 逐字保留，功能要求仍来自原 issue。该说明未冒称已进入本次 CPU public bundle；由 GPU 执行者核实际首请求交付，不含私有断言、对照或答案。

通过必要 CPU 与独立核查后，只申请版本化基座诊断，不授予训练或留出资格。先按 `probe-wide-v1` 两模型各一次，核实际生效预算与全部轨迹，审候选语义和原评分，按整批进度接续必要重复采样。当前没有新模型结果；资源收口仍依赖模型、行为分析和可能修复完成。
