# Dask8801 同原补丁 CPU 行为与诊断结果

2026-10-03。原 Coder 补丁在新 CPU 作业的 **45 项参考全部通过，行为分 1**；本次运行绑定的新鲜独立语义裁决为 **19 pass／4 fail／0 uncertain，完整诊断目标失败**。四个失败是损坏 YAML 的两 fixture ×目录／文件入口：真实解析原因有显示，但文件仅显示 `<unicode string>`，没有指明坏文件。非映射类型诊断和完整 import 例通过。题目材料没有发现需要修订的新缺陷；原 GPU 的 prepare300 infra None 保留。

只将准备上限改为900，复用原 FP／baseline／code8／R16 材料／来源镜像和完整五脚本，不套7305五键。实际 source manifest21e77、image695d、UID54322、2CPU／4GiB／pids512／断网、single-shell／supply=None均核过。安装2.274s／rc0，测试2.239s／rc0，trusted setup134.698491s。该准备耗时低于原300，不能声称900是唯一因果或GPU时延已验。

41份原件353,509B逐SHA闭合；38次资源采样、PID峰34／max0、内存峰2,047,328,256B／全部memory events0／无OOM。原diag resource_facts=null与独立资源读回分开，runner变化false。自有容器0、manager创建／移除1／1、统一槽结束、1581固定成员末次核不变。本次无新模型调用／样本，没有重跑59控制或复用420裁决。

环境[非作者验收](../../reviews/non_author_8801_original_fp_CPU_environment_recovery_review_20261003.md)需同时读[封包计数更正](../../reviews/non_author_8801_CPU_recovery_capture_count_correction_20261003.md)：主JSON统计前缀误用导致compat写0，实际固定前缀计数为10，原件没有覆盖。新[诊断运行绑定窄核](../../reviews/non_author_8801_original_FP_actual_diagnostic_binding_review_20261003.md)独立复算23匿名payload／ID／缓存键、引用和实际fresh编排，未代判自然语言。精确裁决后端／effort仍未暴露，禁读声明不是密码学认证。

[固定JSON](coder_original_FP_CPU_recovery_readback_20261003.json)链接全部原件、实际裁决与身份；[原候选分析](model_probe_coder_a1_analysis_20261003.md)保留点时记录。[独立共享consumer支持](../../publication_requests/support-swe-dask8801-setup900-20261003-v1.json)已入账并直接交发布，回执核后供缺失Qwen首轮使用。题主CPU作业与本次依赖关闭，源文件／实例保留，整机处置由发布合并其他依赖。没有自动训练reward或训练资格；原probe仍claimed，未按双模型完成ack。
