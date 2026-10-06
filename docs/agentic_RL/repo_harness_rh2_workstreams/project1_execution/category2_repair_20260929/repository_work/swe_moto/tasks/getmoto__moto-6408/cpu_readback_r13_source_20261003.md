# Moto6408：R13 原镜像三臂读回，安装未通过

2026-10-03。作业 `moto6408-cpu-1efc480be0d1` 正常结束，73 件回收原件逐 SHA256／长度核对一致。**原始奖励为 noop 0／gold 1／reorder_only 0，但三臂安装均失败，不能据此验收 CPU 或提交普通模型探针。** 独立结果核查尚未完成。

| 候选 | 安装实际退出 | pytest 实际退出 | 收集／解析 | 原始奖励 | 失败依据 |
| --- | ---: | ---: | --- | ---: | --- |
| noop | 2 | 1 | 96／96 | 0 | 目标节点第 630 行：按标签读取的 manifest 不一致。 |
| gold | 2 | 0 | 96／96 | 1 | 96 个参考均通过。 |
| reorder_only | 2 | 1 | 96／96 | 0 | 同一目标节点第 635 行：`assert 2 == 1`，移位后旧镜像仍占有标签。 |

三臂的 95 个 P2P 全通过，无缺失、跳过或 parser 合键。两组负对照只有 `tests/test_ecr/test_ecr_boto3.py::test_multiple_tags__ensure_tags_exist_only_on_one_image` 失败；其失败位置不同，说明排序反例进入了新增所有权检查。这里没有执行旧 R5 材料，旧材料对 reorder_only 的得分仍未知，也不能断言本次已证明旧材料误判。

`make init` 的 PEP517 隔离构建均报告离线找不到 `setuptools>=40.6.0`，最终 `RH2_INSTALL_RC=2`。测试使用镜像中已有 SDK 继续运行，安装／测试是不同的事实。正式 marker、逐参考、可信测试恢复和候选移除记录完整；作业 footer 与最终本作业容器／网络查询为空。安装失败保留为环境阻断，原分数保留为观察。

实际镜像 `sha256:a0071858b0bb3a9c316e3c75dd49e9a3a2f8136f7bb4213e1210b44b7de2e689` 与 R13 注册和源镜像读回相同；固定有效 patch、参考分区、脚本和材料身份均匹配。外层诊断 deadline 1800 秒，原安装／apply／测试预算 300／120／1800 秒。安装段约 9 秒、测试段约 13 秒，不能把整个作业时长归因于 CPU 测试。

后续拟仅给本题加历史三件离线构建 wheel 的 COPY 层，目录 0755、文件 0644，逐文件 SHA 不变；需要新环境登记、实际镜像读回及实际 agent UID 可读验证。原公共项目层、测试、参考与预算保留。新环境交付后再复验相关三臂和 UID；本次原镜像证据不改绑。UID 作业 `moto6408-uid-53e556c49aca` 返回 75，未开始；三件工具已运输，不表示 UID 检查通过。

证据位于 `runs/category2_repair_20260929/moto_cpu_20261003/moto6408-cpu-1efc480be0d1_evidence/`。归档 SHA256 `a5f97320b0eaa0e2b023bb8553c019e12fd593086cff1185de69762e779cff75`；运输 manifest `dc68af38af0a40043ddf46e8b4cbd2a825e2041add8dc5748bd582d331f07c1c`。三份日志 SHA256 为 noop `f371b115f631e6262c4e6628aef815bc9a3c36873ff5474e36eae89e2f49c7f9`、gold `9a899a6f691ddb5496b59317d0cc214716e1661ee727f44c0e7acf0dd3e9ca32`、reorder_only `36ba4db403bd62f38c422fbf6b9eec334c97109363d84ce538394b7bd35ec94c`。

本地派生读回为同目录上一级 `moto6408-cpu-1efc480be0d1_author_raw_readback_v2.json`。v1 曾把 pytest 1 与正常 docker exec 包装退出 0 比较，错误标记两组负对照测试未完成；v2 改为核包装退出 0、pytest 0／1、实际 marker 一致及完整段落。原 v1 和运行原件保留，修正不改变安装失败或原奖励。
