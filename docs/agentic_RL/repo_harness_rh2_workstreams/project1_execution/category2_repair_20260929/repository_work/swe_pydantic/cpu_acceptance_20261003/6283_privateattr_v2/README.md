# 6283 v2：真实依赖下的私有属性保护验收

2026-10-03。R19 `cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1` 的实际发布、CPU-a部署与1476成员SHA／48+216可信回读已[核收](../../coordination_20261003/6283_v2_r19_publication_owner_readback_v1.json)。固定四候选已在CPU-a实际完成，奖励0／1／0／0；每行41个正式参考结果符合预期，全部安装RC0。题主已核498件原件及最终清理，见[实际读回](../../coordination_20261003/6283_v2_formal_owner_readback_v1.json)；[非作者实际核查](../../reviews/non_author_6283_v2_cpu_review_20261003.md)通过并由题主核收。[固定v2探针](probe_request_v2.json)已生成、核收并提交，实际通知已登记。 原Qwen完整FP已在code_v8/v2实际补评分并[核收](../../model_audits_20261003/6283_original_fp_v2_regrade_acceptance.md)：安装RC0，原40参考全通过，新增PrivateAttr P2P抛TypeError，正式奖励0，没有新模型样本；新Coder首臂及版本续作随后已[完整核收](../../model_audits_20261003/6283_coder_v2_continuation_acceptance.md)：安装／测试RC0、41参考全过，合法PrivateAttr保留；附带失败调试文件另记。本次returned已ACK、清活动指针，跨求解环境不比较模型，重复及用途资格待。

本版保留旧40参考，新增 `test_root_model_construct_preserves_private_default` 为P2P（原行为须继续通过），共2个F2P和39个P2P。新节点验证可信 `RootModel.model_construct` 仍保留公开 `PrivateAttr(default='abc')` 默认值，避免原Qwen候选无条件删除合法私有状态后得到错误奖励。原公开输入、base、Python/core、八个公开wheel和安装配方保持；旧Qwen raw1、安装RC1、旧FP及安全partial回执不回写。

| 新CPU候选 | 实际奖励 | 已观察的真实依赖行为 |
| --- | ---: | --- |
| noop | 0 | 普通与可信构造均读到 `abc`；新增P2P通过，原两个F2P失败。 |
| gold | 1 | 普通与可信构造均读到 `abc`；全41参考通过。 |
| validate_construct | 0 | 新私有属性保护通过，但原可信构造语义参考失败。 |
| qwen36_a1_pop_private | 0 | 普通构造仍读到 `abc`；可信构造读取私有默认值产生 `TypeError`，新增P2P失败，原40参考通过。 |

补充观察与正式pytest结果分别记录，不能互相代替。原Qwen源码等价负对照在新CPU材料下运行，不是原GPU FrozenPatch重评分。若实际依赖行为或参考状态与预期不同，保留实际原件并停下分析，不把异常改判为预期结果。

实际回执核收后已生成不可覆盖的固定输入，并完成新的consumer本地prepare及41参考／补丁／安装／actor-host spec身份核对，见[题主读回](../../coordination_20261003/6283_v2_local_prepare_owner_readback_v1.json)。[实际固定输入独立核查](../../reviews/non_author_6283_v2_input_review_20261003.md)已通过；10个载荷文件加清单已上传，远端精确成员集、大小及SHA读回通过，记录在`runs/.../cpu_preparation_20261003/6283_v2_upload_owner_readback_v1.json`。这些操作未执行Docker或题目测试。

原广域hold已按[非作者范围核查](../../reviews/non_author_6283_cpu_hold_scope_20261003.md)和[题主范围处置](../../coordination_20261003/cpu_hold_scope_disposition_v1.json)原字节归档。6283使用R19及原300秒预算，不以8316的900秒结果替代本题证据，也不要求另一题成功后才运行。唯一作业`pyd6283-formal-20261003033613-v2-b5f3a`于03:36:16 UTC在CPU-a slot1开始，03:48:52 UTC自然结束RC0；四次实际控制面保护分别132.983／120.217／128.154／184.567秒。140个Docker调用均RC0，manager四建四删，最终容器／网络查询RC0且为空。本轮成功不能证明共享I/O问题永久消失；若出现新infra或清理未知，立即建立新hold并停止新派发。

旧公开actor在原公开字节、base、source镜像与core相同的范围内，经非作者核查原件后有限复用；它使用24e9… source镜像，不是新58d0…派生grader的actor实测。新材料spec、CPU安装与全41参考已经另验；新GPU Coder的实际540e镜像、UID54321、安装RC0、公开首HTTP和41参考已另获[独立执行核查](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/pydantic6283_v2_coder_a1_execution_review_v1.md)及题主核收；这不把旧CPU actor改写为新CPU grader actor实测。本版请求`swe-pydantic6283-behavior-v2-20261003`已通过CLI提交并[实际通知](../../coordination_20261003/6283_v2_probe_send_receipt_20261003.json)：Qwen新采样0，仅原FrozenPatch独立v2补评分；Coder补未执行首臂1。两版实际评分分别记录，不覆盖旧R7、旧raw1或原FP。生成器[静态核查](../../reviews/non_author_6283_v2_probe_generator_review_20261003.md)及[生成结果核收](../../coordination_20261003/6283_v2_generated_probe_owner_readback_v1.json)通过时只确认输入；随后指定两项GPU操作已实际完成并由题主核收。这些步骤不授予训练资格。

