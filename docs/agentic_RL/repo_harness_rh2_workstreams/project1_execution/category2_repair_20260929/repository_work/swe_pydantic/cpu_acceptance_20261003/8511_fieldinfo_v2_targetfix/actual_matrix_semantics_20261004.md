# 8511 R27正式CPU实际结果：177参考

2026-10-04（Asia/Singapore）。唯一作业`pyd8511-formal-20261003175031-v27-dc821`已自然结束RC0，题主完成526原件SHA/大小读回和实际语义核对；**非作者实际CPU验收已通过、题主528原件/报告及11支持绑定核收；原完整GPU FrozenPatch新版补评分尚未执行，模型新采样0。**

| 候选 | 奖励 | F2P通过 | P2P失败 | 实际结果 |
| --- | --- | --- | --- | --- |
| noop | 0 | 0/1 | 0/176 | 原repr缺陷仍失败；新增四项合法字段行为保持通过。 |
| gold | 0 | 1/1 | 4/176 | 修复repr，但三个旧继承保护及新增继承factory保护失败，不能因来源gold认定正确。 |
| narrow | 1 | 1/1 | 0/176 | 全部177正式参考通过，合法字段行为和原有继承保护保持。 |
| qwen_original | 0 | 1/1 | 4/176 | 原173参考通过；新增default_factory、继承factory、gt和alias四项全失败。 |

四份实际日志都把177参考逐ID记录为PASSED或FAILED，参考分区missing/skipped/unaccounted为空。pytest另外有11个非正式参考skip；来源parser184个唯一键不是正式参考数，不能称全项目测试通过。Qwen实际错误是factory字段x变成required、继承factory同样丢失、x=0未触发ValidationError、y='2'仍留下x=1；与先前独立直接诊断一致。gold用getattr取得父类__annotations__并把Field挂到缺少本地注解的子类，导致标准库报“field but has no type annotation”；这也是新增继承factory失败的具体原因。

实际R27 source/manifest、固定输入/runner、新effective test、E10安装、df6c镜像、Python3.8.19/core2.14.5、/testbed源码导入、UID54322以及私有测试root所有/不可写均核到原件。每行安装RC0；测试RC依次1/1/0/1。资源保持2CPU/4GiB/pids512/deny_all；四次保护实际耗时137.095/129.301/133.811/135.449秒，原300秒预算没有放大。四份baseline各452成员，CPU FP为空或单条生产delta，候选源码投影一致；实际走同镜像baseline一致分支，不是原GPU baseline.tar重建。源码等价CPU运输仍不替代原完整GPU FP补评分。

148个Docker调用保存完整stdout/stderr，所有调用RC0（项目测试失败码由封闭评分脚本记录）；四行候选removed，各grader已移除，manager创建/移除4/4、open/cleanup_failures空。最后精确run标签container/network查询为空，shared CPU slot finished/returncode0。此作业为普通SSH前台slot，不套用先前systemd诊断的PID1服务事件。

原R26 false报告/命令hold、旧R14材料覆盖缺口、旧173/raw1/完整FP均保持历史原件。本页只描述此次实际CPU验收，不能据此授训练/留出资格；后续仅用原完整FP另作新版本评分。

- [题主526原件读回](../../coordination_20261003/8511_v2_targetfix_formal_owner_readback_v1_20261004.json)，SHA `5874c7da2073871f59e4e7eaa90e558bead2a1be105ba5672b627c371169548b`。
- [本次结果与完整本地原件路径](results.json)，原始归档SHA `5f7891378fcb969f4b406bac82365a38f23ed0c87e0bcadf38c3c4c9c8b5c1d0`。
- [独立固定输入delta](../../reviews/non_author_8511_v2_targetfix_input_review_20261004.md)已通过，[实际CPU独立报告](../../reviews/non_author_8511_v2_targetfix_cpu_review_20261004.md)已通过，CPU前置完成；[验收快照](cpu_acceptance_snapshot_20261004_v2.json)及[原完整FP-only请求](probe_request_v2_fp_regrade.json)已新建，请求已非作者终版核收并提交GPU队列/实际通知；原完整FP新版实际评分仍待。
