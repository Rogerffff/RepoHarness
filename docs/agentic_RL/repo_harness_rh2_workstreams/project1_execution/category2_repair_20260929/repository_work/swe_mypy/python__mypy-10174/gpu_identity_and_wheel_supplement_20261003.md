# 10174：模型来源与GPU权限层补证

2026-10-03 09:27（Asia/Singapore）。题主只读核查已完成，未运行CPU、模型或项目代码。[冻结回读](gpu_identity_and_wheel_supplement_20261003.json) SHA `4a6630f407cde6f31e23eeb1cbd1f7076d2a74985ec4a5817fbe9470af972989`，绑定82件原件，115项核查通过。当前CPU条件不变；新GPU权限层已实测，原候选在该层的安装/重评分及未运行Coder仍待GPU执行者返回。

## 10174首臂的有限模型归因

GPU方的[Q12根审收口](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q12_retrospective_checkpoint_request_binding_root_accept_v1.json) SHA `cd603e4e2573da19be61c80520468dbfb62c74eb4d5af117e98358c17eac4eb2`与[非作者核查](../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/q12_retrospective_checkpoint_request_binding_non_author_review_v1.json)相符。题主重算其29件原件SHA/大小，复用非作者13项身份核查；本次只对mypy10174解释逐请求结果，不为另两道Pydantic题签收。

作业`gpu1003-mypy10174-qwen36-a1`时间为22:55:13.199600–23:00:26.914552 UTC。87条实际网关请求将`slime-actor`转发为`Qwen3.6-35B-A3B`；87条adapter生成均带本job SID，固定和实际端点均为`http://127.0.0.1:30001`。同时间窗后端日志有87次`POST /generate`成功完成，原件第299–385行；与adapter完成时间最大差6.135毫秒。

历史实际启动读回、事后同一engine容器/启动时间/restart0、只读`/model`挂载及HTTP字段支持运营来源归因。模型仓库为`Qwen/Qwen3.6-35B-A3B`，下载manifest revision为`995ad96eacd98c81ed38be0c5b274b04031597b0`；后端dtype为bfloat16、context196608。

这不是逐作业当时保存的checkpoint快照。旧turn没有后端engine ID，日志时间对应不构成逐请求签名；HTTP revision/model_checksum均null，精确revision来自下载与挂载来源。没有重新hash约71.9GB权重，也没有GPU内存密码学证明；容器只读挂载不证明宿主路径不可变。旧`config_only=true`、运行核验false和`checkpoint_identity_verified=false`保持原样。15184的Q13逐请求链未由此报告核查，不能借用本题归因。

## GPU权限层实际核查

旧镜像`32f313c82fd4…`通过本次自有alias固定，实际新镜像为`sha256:80418df01e0544855bbba9d858a53e45089320ed650bc4b1eb05e91bbf33880f`。题主核[本题原件目录](../../../../../../../../runs/ordinary_gpu_probe_20261002/remote/public_wheel_modes_repair_v3/mypy10174/image_readback.json)及command001–040：实际构建RC0，network none、pull=false，Config完全相同、旧14层全保留，只追加1层。

完整`/testbed`清单1663条（含`.git`与目录）逐项不变。三wheel的内容SHA、大小和uid/gid不变；权限从0600改为0644，wheel目录0755。受限、只读、无网络容器中的UID54321和54322均实际完整读取全部三wheel并重算相同SHA，真实进程退出0。四个census/reader容器均创建、退出、移除并确认不存在；本轮自有label清理检查为空。

这份修复原件明确`install_grade_model_executed=false`。它只证明权限层和内容不变性，不能据此写新GPU安装/评分/actor/模型运行完成。旧GPU安装RC1、raw1、原FP和旧验收JSON不回写；CPU r16窄补证仍单列。GPU方正在核同原FP、完整基线和投影在新层上的实际重评分，并安全接续原请求的未运行臂；题主不重复提交或ack部分结果。

当前无新增修题或CPU依赖，训练、留出资格及同条件稳定性均未增加。实际权限层本次由题主回读原件；复用的GPU权限脚本非作者审查是静态范围，不冒称新的非作者动态验收。
