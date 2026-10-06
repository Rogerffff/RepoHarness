# 8511 四项字段保留：实际 CPU 读回

2026-10-03。题主已核实际输入、38 个命令及 154 件证据绑定，[非作者实际核查](../../reviews/non_author_8511_fieldinfo_retention_v3_cpu_review_20261003.md)通过，其148项实际成员绑定也已题主逐件核收。原始代码和既有 narrow 各四项通过，原 Qwen 四项失败；这是既有行为回归的运行实证。通过范围仅直接行为诊断，177 项正式评分尚未执行。

| 检查 | 原始代码 | narrow | 原 Qwen |
| --- | --- | --- | --- |
| 隐藏字段默认工厂产生独立空列表 | 通过 | 通过 | 字段被当作必填，ValidationError |
| 无本地注解的子类继承同一默认工厂 | 通过 | 通过 | 字段被当作必填，ValidationError |
| 隐藏字段 `gt=0` 接受字符串 2、拒绝显式 0 | 通过 | 通过 | 0 被错误接受 |
| 隐藏字段通过别名 `y='2'` 得到 `x=2` | 通过 | 通过 | 别名被忽略，仍为默认值 1 |

实际作业为 `pyd8511-retention-20261003T153716Z-v3`，15:37:16–15:37:27 UTC 自然结束；统一 run 槽 returncode0，实际 PID1 日志记录正常结束。镜像为 `sha256:df6c3affb7ea6fd826f44863ec92926f7b52558dd0f1b42e05f97aec9fe8ca68`，完整基线绑定 base `e4fa099d5adde70acc80238ff810c87a5cec7ebf`；原 Qwen FP 为 `sha256:4c305765cca042e14a8b79ebafa304394739f982b0eb68a471a47efbf92b3da1`。四项检查本身不执行 repr 断言，避免把原 F2P 缺陷误当作新增 P2P 的前置要求。

每个容器独立恢复原 452 个完整源码成员，仅候选 `pydantic/dataclasses.py` 有预定差异；内容 SHA 与执行位在行为检查前后均一致。实际使用 Python 3.8.19、core 2.14.5、Pydantic 2.6.0a1，导入 `/testbed/pydantic/__init__.py`。行为命令运行 UID54321，实际 effective／permitted／inherited／ambient capabilities 均为 0，NoNewPrivs1。root 只用于自有容器恢复，授予 CHOWN／DAC_OVERRIDE；这不是完整 RH2 actor 租约或训练权限证明。

三容器实际均断网、无宿主挂载，限 2 CPU／4 GiB／512 PID；每个有 5 个约 0.5 秒间隔的资源点，未采到的瞬间保持未知。所观测 cgroup memory.peak 最大分别为 36,175,872／36,225,024／36,360,192 字节，观测 pids.peak 各 8，采样 OOM 计数均 0。各自精确 CID 的删除命令及查询退出 0、查询为空，整作业标签查询退出 0 且为空，没有自有残留。

v1／v2 均在 baseline 身份比较前后停止，没有执行任何行为检查。v2 证明仅五个执行位在自有恢复器中丢失，452 内容 SHA 全部一致。v3 由文件所有者 UID54321 恢复冻结 Git mode，保留完整身份断言与原时间／资源上限；前两次失败原件和 hold 原字节保留。tar 先 chown 后 chmod、root 缺 FOWNER 的原因只是机制推断，不写成内核实测结论。

原件：[归档与同步回执](../../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/8511_retention_original_evidence_v3_sync_receipt.json)、[题主逐件读回](../../coordination_20261003/8511_fieldinfo_retention_v3_owner_readback_v1.json)。归档 SHA 为 `6ff4a4b36934ebf661a761213fbd99280105c9c6ed867dbd12a0969d654bf177`，3,195,457 字节；148 件实际文件逐项与归档一致。直接行为结果不能替代新增 177 参考下的 pytest 收集、正式评分运输、安装、完整正负对照及非作者验收，也不改变旧 173 项 raw1。
