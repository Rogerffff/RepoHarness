# Moto7584：当前普通 CPU 诊断验收

2026-10-03。固定R13、修订 `moto7584-endpoint-v3` 的普通CPU诊断验收通过；[最终非作者原件核查](../../reviews/moto7584_final_cpu_non_author_20261003.md) SHA `71a98fb8fe87325dbcde67d86460a4b542c774c6ca5f6372c162a98045add6bd`。不授予训练或留出资格。

十一臂同条件完成：noop与八负raw0，stmt和stmt_arnmsg两正raw1；原gold已知不完整，属于八负之一。每臂make init0，正式评分20项唯一参考、1F／19P完整，没有缺失、跳过或合键；pytest退出与完整trace逐项核对，不能把wrapper0当pytest0。实际冻结的单源码entry与各固定控制patch严格apply后的字节相同。候选、manager与自有标签容器/网络两层清理完整。

实际UID/GID54321、testbed解释器/工作区SNS模块和SDK1.35.9、2CPU/4GiB/PID512/shm64MiB及激活通过。真实CC2.1.205配确定性stub执行原四公开操作：A解释器/导入成功；B仅在原公开脚本末尾准确复现已删除endpoint被接受；C1/C2各原19项通过。实际公开prompt进入首真实请求，完整trajectory和容器、relay、网络、stub收尾齐全。

两个旧检测flag仍false：本清单不输出旧RH2_SYS_EXECUTABLE或RH2_BASHENV_WRITE标记，完整A及prelaunch提供对应实际事实；未改原flag。公开pytest -q只有原命令及19项总数，未虚构逐节点名单。actor依据实际DevRunner生命周期工件，未另运输全Docker调用。真实CC公开操作没有模型自主求解、FrozenPatch export或a2g；人工矩阵的冻结补丁不能冒充solver补丁。

source manifest `sha256:3b263c0c4745d890400b7beaf08c10b5413f86ae7983dd4bf14d93e43cd2fbf9`，CPU actor诊断与grader实际COPY-only image `sha256:990e0e91a190f85426e6900828cf758c30f389c927f6c1d0cd1ed8c68b902f96`。原public face保留；已有明确诊断override供普通探针使用，typed训练租约未接线。GPU需核自己的镜像、代码和实际公开请求，产生新baseline/FrozenPatch，不重绑CPU工件。

原件：`moto7584-cpu-a9dd947080c8`（noop）、`moto7584-cpu-0121b210ce7a`（其余10臂）、`moto7584-uid-ef396ea52123`、`moto7584-actor-a50e7789d81a`，均在 `runs/category2_repair_20260929/moto_cpu_20261003/<job>_evidence/`。SSH255与首次slot75按历史原样保留，四个实际闭合job均parent0；无机械重跑。
