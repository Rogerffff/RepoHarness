# v0.1.1 发布面逐项覆盖表

整理：2026-09-29。主结论见 [README](README.md)。本表为相关性与采用方式盘点，**不是每个发布项都做了运行验证**；最后一列标明实际证据层级。实现建议均未自动批准。

范围：详细清单 122 条、15 类，另列 3 项高亮模型。输入来自固定 tag 对应 release；Git 祖先核对和 PR 对照保存于 `runs/miles_v0_1_1_review_20260929/release_pr_ancestry.json`。重构系列中多个 PR 共用一条，数量不能与 442 个 Git 提交相加。

## 训练与算法

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 1 · [#2200](https://github.com/radixark/miles/pull/2200)、[#2595](https://github.com/radixark/miles/pull/2595)、[#3354](https://github.com/radixark/miles/pull/3354) | 部分已具备 | 已有支持集原语与运输；#3354 新入口不能替代 custom loss 的 0001。 | 训练原函数/源码 |
| 2 · [#2825](https://github.com/radixark/miles/pull/2825) | 条件使用 | 现有 spike 未启用 true_on_policy_mode；分块不消除 full-vocab gather。 | 训练原函数/源码 |
| 3 · [#2764](https://github.com/radixark/miles/pull/2764) | 条件适配 | 新版 custom_loss 的训练 logits 仍转 FP32；实际显存值得时单独适配。 | 训练原函数/源码 |
| 4 · [#2818](https://github.com/radixark/miles/pull/2818) | 后置/迁移 | 当前不是 SFT；与 #2764 合看，不照搬显存收益。 | 训练源码 |
| 5 · [#2878](https://github.com/radixark/miles/pull/2878) | 后置 | 当前 GRPO 无 critic；选 PPO 时再核 bridge critic。 | 适用性筛选 |
| 6 · [#2891](https://github.com/radixark/miles/pull/2891) | 后置 | 当前没有 shared actor-critic PPO 或 indep-DP 组合。 | 适用性筛选 |
| 7 · [#3125](https://github.com/radixark/miles/pull/3125) | 优先窄回移 | 真实 PP stage 判定；当前效率档非末级的无用优势计算已复现。 | 训练原函数/源码 |
| 8 · [#3091](https://github.com/radixark/miles/pull/3091) | 条件使用 | 修改 reset optimizer state 按优化器类型的实现；恢复不能误把 reset 当正常 resume。 | 改动范围/源码 |
| 9 · [#3083](https://github.com/radixark/miles/pull/3083) | 后置 | 改动实际在 lora_utils 的保存，不能由标题推为当前全参保存 bug。 | 改动范围 |
| 10 · [#2682](https://github.com/radixark/miles/pull/2682) | 已具备 | 已在当前 base；不替代 RH2 版本状态与 I22 编号匹配。 | Git 祖先/运行时源码 |
| 11 · [#3211](https://github.com/radixark/miles/pull/3211) | 后置 | 当前未启用 MTP；未来开启时与 bridge、梯度传播一起核。 | 适用性筛选 |
| 12 · [#3219](https://github.com/radixark/miles/pull/3219) | 后置 | 当前未启用 MTP；未来开 CP+MTP 时核 token/mask 切片。 | 适用性筛选 |
| 13 · [#3655](https://github.com/radixark/miles/pull/3655) | 参考/条件适配 | 只作用默认 policy_loss；RH2 效率档的同版本对拍仍不可用。 | 训练源码 |
| 14 · [#3172](https://github.com/radixark/miles/pull/3172) | 后置 | debug-train-only 快照 eval 不等于现 I21 独立 eval-only。 | 运行时源码 |
| 15 · [#3182](https://github.com/radixark/miles/pull/3182) | 条件使用 | 同步/colocate 最后轮 handoff 优化；当前 train_async 不直接受益。 | 路径/适用性筛选 |
| 16 · [#3615](https://github.com/radixark/miles/pull/3615) | 条件使用 | 与 #3182 配套，最后 eval 前仍需正确切回引擎。 | 路径/适用性筛选 |

## Rollout 与 session

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 17 · [#3258](https://github.com/radixark/miles/pull/3258)、[#3301](https://github.com/radixark/miles/pull/3301)、[#3264](https://github.com/radixark/miles/pull/3264)、[#3302](https://github.com/radixark/miles/pull/3302)、[#3311](https://github.com/radixark/miles/pull/3311)、[#3249](https://github.com/radixark/miles/pull/3249) | 迁移参考 | 请求规则、渲染、commit 先后次序值得复用；不能删 RH2 身份和实际参数证据。 | session 源码 |
| 18 · [#2358](https://github.com/radixark/miles/pull/2358) | 不可直接替换 | 真实 CC 请求带该入口拒绝的 thinking/output_config；见 S1。 | 真实语料+原函数 |
| 19 · [#3114](https://github.com/radixark/miles/pull/3114) | 条件使用 | 仅改可选 Anthropic helper 缺失时兼容；不解决 S1 请求特征限制。 | session 源码 |
| 20 · [#2302](https://github.com/radixark/miles/pull/2302) | 后置 | Inkling raw completion 路径非当前 CC/RH2 入口。 | 适用性筛选 |
| 21 · [#2774](https://github.com/radixark/miles/pull/2774) | 迁移必查 | session worker 数与端口独立；保留 RH2 时无需额外启动。 | 启动源码/说明 |
| 22 · [#2851](https://github.com/radixark/miles/pull/2851) | 条件使用 | 跨宿主 session 暴露地址只在采用 native session 时使用。 | 适用性筛选 |
| 23 · [#2834](https://github.com/radixark/miles/pull/2834) | I18 材料 | 非 retract 增量 R3；不能替代异步行为路由来源决定。 | session/训练源码 |
| 24 · [#3323](https://github.com/radixark/miles/pull/3323) | 局部参考 | eval 关闭路由/采样 replay 不会自动作用当前 RH2 入口。 | session 源码 |
| 25 · [#3337](https://github.com/radixark/miles/pull/3337) | 局部参考 | HTTP 200 下 backend abort 不 commit；不能替代 RH2 交付/停止确认。 | session 源码 |
| 26 · [#3339](https://github.com/radixark/miles/pull/3339) | 局部参考 | 只把不可变 payload 的客户端解码移出 loop；E3 后先看剩余瓶颈。 | 源码/PR 原说明 |
| 27 · [#3585](https://github.com/radixark/miles/pull/3585) | 迁移参考 | 会话创建时设置 sampling defaults；实际入口仍须保留当前已定采样合同。 | session 源码 |
| 28 · [#3657](https://github.com/radixark/miles/pull/3657) | 迁移需改默认 | 相同 prompt 较早真实输出被 picker 丢弃；identity picker 可保留。 | 上游/RH2 直接对照 |
| 29 · [#2759](https://github.com/radixark/miles/pull/2759) | 条件选择 | Qwen3.5/3.6 TITO 会改变未来输入；不是 I01 B 的等价性能补丁。 | session 源码 |
| 30 · [#2760](https://github.com/radixark/miles/pull/2760) | 模型选择后 | Qwen3.8 tokenizer 只在相应模型/harness 选择后接；未验证该模型。 | 适用性筛选 |
| 31 · [#3087](https://github.com/radixark/miles/pull/3087) | 模型选择后 | GLM 模板扩展不自动改变当前模型或支持 CC 全请求面。 | 适用性筛选 |
| 32 · [#2814](https://github.com/radixark/miles/pull/2814) | 迁移必查 | 新增 missing-reward 丢组需保留 RH2 归因与分母；不能先吞自洽错误。 | buffer 源码 |
| 33 · [#2743](https://github.com/radixark/miles/pull/2743) | 迁移参考 | 非数值 reward 不纳 episode 平均；不能据此把基础设施失败记零。 | metrics 源码 |
| 34 · [#3319](https://github.com/radixark/miles/pull/3319) | 条件窄回移 | 先核单组取消的真实来源；不得吞整体关停/未知错误。 | 运行时源码 |
| 35 · [#3343](https://github.com/radixark/miles/pull/3343) | 关键顺序已具备 | 0014 已有 fully-async JIT drain；其余版本/无进展合同未由上游替代。 | driver 原函数/源码 |
| 36 · [#3587](https://github.com/radixark/miles/pull/3587) | 迁移必查 | rollout path 与 fully-async 模式选择需同一最终配置；不直接复用旧命令。 | 适用性筛选 |
| 37 · [#3600](https://github.com/radixark/miles/pull/3600) | 后置 | 当前纯文本 coding；图文混合数据加载不是近期缺口。 | 适用性筛选 |

## Harness 与环境接口

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 38 · [#2805](https://github.com/radixark/miles/pull/2805) | 局部参考 | 共享 agent-function 参数层可减少未来 harness 胶水；现用自定义 generate。 | session 源码 |
| 39 · [#2806](https://github.com/radixark/miles/pull/2806) | B 线参考 | in-process Harbor Trial 可以参考；示例 generic failure→0 与 RH2 不同。 | session/Harbor 源码 |
| 40 · [#2836](https://github.com/radixark/miles/pull/2836) | B 线参考 | 适合 terminal 补充路线的启动例；不是当前 SWE 链替换。 | 示例/适用性 |
| 41 · [#3341](https://github.com/radixark/miles/pull/3341) | 后置 | 当前本地 Docker，不是 Modal provider。 | 适用性筛选 |
| 42 · [#3345](https://github.com/radixark/miles/pull/3345) | 后置 | 采用 Harbor 后复用资源参数运输，仍需目标环境对账。 | 适用性筛选 |
| 43 · [#3215](https://github.com/radixark/miles/pull/3215) | 不可照搬清扫 | Daytona 默认 orphan 回收不授权恢复 RH2 跨 manager 按年龄清理。 | 改动范围/适用性 |
| 44 · [#2741](https://github.com/radixark/miles/pull/2741) | B/I19 参考 | 多段压缩训练结构可借鉴；不证明 CC 的计数/400/摘要路径。 | session/示例源码 |
| 45 · [#3658](https://github.com/radixark/miles/pull/3658) | 后置 | Workplace Assistant 非当前 coding 主任务。 | 适用性筛选 |
| 46 · [#2677](https://github.com/radixark/miles/pull/2677) | 基线已有 | OpenEnv 结束原因功能已在 base；当前使用 RH2 终止事实。 | Git 祖先 |
| 47 · [#2809](https://github.com/radixark/miles/pull/2809) | 后置 | 只有选择 OpenEnv E2B 时才需 SDK floor。 | 适用性筛选 |
| 48 · [#2811](https://github.com/radixark/miles/pull/2811) | 后置 | 只有接 OpenEnv Terminal-Bench 环境时核版本合同。 | 适用性筛选 |
| 49 · [#2863](https://github.com/radixark/miles/pull/2863) | 后置 | OpenEnv TB2 server 的依赖 pin，当前入口不使用。 | 适用性筛选 |
| 50 · [#3084](https://github.com/radixark/miles/pull/3084) | 后置 | 未来选 verifiers 时匹配 renderer 版本；无需给当前链增依赖。 | 适用性筛选 |
| 51 · [#2748](https://github.com/radixark/miles/pull/2748) | 局部参考 | 多 session 全部 flush 的 owner 原则有用；示例 swe-agent 非当前 CC 入口。 | 适用性筛选 |

## LoRA 与多租户

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 52 · [#2839](https://github.com/radixark/miles/pull/2839)、[#2840](https://github.com/radixark/miles/pull/2840)、[#2841](https://github.com/radixark/miles/pull/2841)、[#2842](https://github.com/radixark/miles/pull/2842)、[#2843](https://github.com/radixark/miles/pull/2843)、[#2844](https://github.com/radixark/miles/pull/2844)、[#2845](https://github.com/radixark/miles/pull/2845)、[#2849](https://github.com/radixark/miles/pull/2849) | 后置 | 当前全参单作业，不建多租户 Tinker 服务。 | 源码存在/适用性 |
| 53 · [#3318](https://github.com/radixark/miles/pull/3318) | 后置 | 选择 LoRA 时才核 target 模块组映射。 | 适用性筛选 |
| 54 · [#3584](https://github.com/radixark/miles/pull/3584) | 后置 | 多 LoRA 正确性及依赖配套需一起用；当前未采用。 | 适用性筛选 |
| 55 · [#3656](https://github.com/radixark/miles/pull/3656) | 后置 | Tinker launcher 清理与 RH2 manager 关停不是同一 owner。 | 适用性筛选 |
| 56 · [#3194](https://github.com/radixark/miles/pull/3194) | 后置 | 单 LoRA 的 dtype/load/barrier 配套；不代表当前全参收益。 | 适用性筛选 |
| 57 · [#3089](https://github.com/radixark/miles/pull/3089) | 后置 | colocate+LoRA 的重复 CPU 备份，当前未经过。 | 适用性筛选 |
| 58 · [#3147](https://github.com/radixark/miles/pull/3147) | 后置 | LoRA 发布时显存约束仅在相关模式启用。 | 适用性筛选 |
| 59 · [#2869](https://github.com/radixark/miles/pull/2869) | 后置 | LoRA critic bridge 配置，当前无消费者。 | 适用性筛选 |
| 60 · [#3245](https://github.com/radixark/miles/pull/3245) | 后置 | LoRA 恢复 optimizer 选择需保留；当前为全参。 | 适用性筛选 |

## 权重发布

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 61 · [#2502](https://github.com/radixark/miles/pull/2502) | 迁移必接 | 版本需由新 TrainerController 返回并传到 RolloutExecutor；保留全引擎收敛。 | 运行时源码 |
| 62 · [#2500](https://github.com/radixark/miles/pull/2500) | 条件使用 | disk-delta 选用时须同步 baseline reload；当前不为此换传输。 | 适用性筛选 |
| 63 · [#2692](https://github.com/radixark/miles/pull/2692) | 条件使用 | disk-delta 布局约束；本轮未运行该协议。 | 改动范围 |
| 64 · [#3128](https://github.com/radixark/miles/pull/3128) | 条件使用 | offloaded actor 的发布来源需正确；当前训推分离无该 offload 配方。 | 改动范围/路径 |
| 65 · [#3129](https://github.com/radixark/miles/pull/3129) | 条件使用 | 与 offload 发布配套的连接分配保护；非当前默认收益。 | 改动范围/路径 |

## 低精度

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 66 · [#2864](https://github.com/radixark/miles/pull/2864) | 后置 | 选择 NVFP4/QAT 和适配硬件后再用 fused kernel。 | 适用性筛选 |
| 67 · [#2855](https://github.com/radixark/miles/pull/2855) | 后置 | 专家量化范围属于量化配方；当前 BF16。 | 适用性筛选 |
| 68 · [#3638](https://github.com/radixark/miles/pull/3638) | 后置 | 主 decoder 的量化过滤与所选模型绑定。 | 适用性筛选 |
| 69 · [#3217](https://github.com/radixark/miles/pull/3217) | 后置 | NVFP4 发布成本与特定表示绑定；不外推 BF16。 | 适用性筛选 |

## 内存与卸载

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 70 · [#2781](https://github.com/radixark/miles/pull/2781) | 条件使用 | colocate 把峰值位置从 host 转到 GPU；当前 train_async 不走。 | 训练/运行时源码 |
| 71 · [#3100](https://github.com/radixark/miles/pull/3100) | 后置 | 上述 colocate + LoRA 配套。 | 训练源码 |
| 72 · [#2739](https://github.com/radixark/miles/pull/2739) | 后置 | 当前 Adam；不为 offload 特性而改 Muon 算法。 | 训练源码 |
| 73 · [#2653](https://github.com/radixark/miles/pull/2653) | 容量需要时 | Adam NVMe 流式初始化可复用；先量 host 峰值与 I/O。 | 训练源码 |
| 74 · [#2142](https://github.com/radixark/miles/pull/2142) | 后置 | TE 量化缓存 + offload 才有收益，CUDA graph 还有约束。 | 训练源码 |

## 模型支持

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 75 · [#2706](https://github.com/radixark/miles/pull/2706) | 模型选择后 | DeepSeek-V4 的训练后端选择应随整栈与硬件验收。 | 适用性筛选 |
| 76 · [#2038](https://github.com/radixark/miles/pull/2038) | 模型选择后 | DeepSeek-V4 packing/CP 不是当前 Qwen 通用增益。 | 适用性筛选 |
| 77 · [#2717](https://github.com/radixark/miles/pull/2717) | 基线已有 | DeepSeek-V4-0731 转换已在 base；选模型后仍需真加载验收。 | Git 祖先 |
| 78 · [#3163](https://github.com/radixark/miles/pull/3163) | 模型选择后 | Nemotron-H 权重映射修复，只在选择该模型时使用。 | 适用性筛选 |
| 79 · [#3164](https://github.com/radixark/miles/pull/3164) | 模型选择后 | Nemotron-H 无 MTP 的 forward 修复。 | 适用性筛选 |
| 80 · [#2716](https://github.com/radixark/miles/pull/2716) | 基线已有 | MLA RoPE 配置修复已经在 base；不重复回移。 | Git 祖先 |
| 81 · [#3653](https://github.com/radixark/miles/pull/3653) | 转换需要时 | 实际转换 checkpoint 时核 ETP/PP 自动推导，非当前所有作业必需。 | 适用性筛选 |

## 启动与配置

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 82 · [#2738](https://github.com/radixark/miles/pull/2738) | 新作业参考 | 自动识别硬件可复用，但不替代并发/显存测量和正式参数决定。 | 改动源码 |
| 83 · [#2885](https://github.com/radixark/miles/pull/2885) | 迁移复用 | 端口真实 owner 的检查放新 worker 启动层；不另建 RH2 分配服务。 | 改动源码 |
| 84 · [#3581](https://github.com/radixark/miles/pull/3581) | 迁移配套 | SGLang ServerArgs 类型随 0.5.20 栈一起核。 | 适用性筛选 |
| 85 · [#3141](https://github.com/radixark/miles/pull/3141) | 条件使用 | 默认 policy debug dump 的 TP 去重；RH2 custom loss 不直接调用。 | 改动源码 |

## 观测与展示

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 86 · [#2598](https://github.com/radixark/miles/pull/2598) | 后置 | 当前未开 speculative decoding；未来开时计数需同时换。 | 适用性筛选 |
| 87 · [#2710](https://github.com/radixark/miles/pull/2710) | 已具备 | 当前基线就是此压缩统计提交。 | Git/metrics 源码 |
| 88 · [#2765](https://github.com/radixark/miles/pull/2765) | 局部复用候选 | 按 execution 聚合多行长度，与 I01/I20 共用来源和分母。 | metrics 源码 |
| 89 · [#2778](https://github.com/radixark/miles/pull/2778) | 条件使用 | 旧多 adapter 的 reward 统计域修正；当前单模型不直接获益。 | 改动源码 |
| 90 · [#3115](https://github.com/radixark/miles/pull/3115) | 观测候选 | 完整 response 的重复检测可能有用，但需明确多行 masked 区域的口径。 | 适用性筛选 |
| 91 · [#3334](https://github.com/radixark/miles/pull/3334) | 优先窄回移 | 先修 consumed 统计位置；结构化 token 加权指标另做字段映射。 | buffer 源码 |
| 92 · [#2696](https://github.com/radixark/miles/pull/2696) | 基线已有/后置 | AMD 遥测已在 base；当前设备若非 AMD 无消费者。 | Git 祖先 |
| 93 · [#3239](https://github.com/radixark/miles/pull/3239) | 后置 | 当前不含图像轨迹；不为发布项建设多模态 UI。 | 适用性筛选 |
| 94 · [#2881](https://github.com/radixark/miles/pull/2881) | 局部复用候选 | 离线多叶 viewer 值得借用，须对齐 RH2 leaf identity 和 dump。 | 改动源码 |

## AMD / ROCm

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 95 · [#2854](https://github.com/radixark/miles/pull/2854) | 设备选择后 | ROCm10 MI35X 镜像只对相应设备有用。 | 适用性筛选 |
| 96 · [#3326](https://github.com/radixark/miles/pull/3326) | 设备选择后 | ROCm7.2.4 镜像只对相应设备有用。 | 适用性筛选 |
| 97 · [#3183](https://github.com/radixark/miles/pull/3183) | 设备/配方选择后 | AMD Qwen LoRA 例不等于当前全参八卡验收。 | 适用性筛选 |
| 98 · [#2660](https://github.com/radixark/miles/pull/2660) | 基线已有 | ROCm wheels 文档/版本选择已在 base。 | Git 祖先 |

## 架构重构

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 99 · [#1837](https://github.com/radixark/miles/issues/1837)、[#1842](https://github.com/radixark/miles/pull/1842)、[#1843](https://github.com/radixark/miles/pull/1843)、[#1861](https://github.com/radixark/miles/pull/1861)、[#1985](https://github.com/radixark/miles/pull/1985)、[#2051](https://github.com/radixark/miles/pull/2051)、[#2054](https://github.com/radixark/miles/pull/2054)、[#2063](https://github.com/radixark/miles/pull/2063)、[#2154](https://github.com/radixark/miles/pull/2154)、[#2161](https://github.com/radixark/miles/pull/2161)、[#2176](https://github.com/radixark/miles/pull/2176) | 整栈迁移 | 不是简单类改名；RH2 owner、异常、发布与恢复合同要重接。 | 运行时原函数/源码 |
| 100 · [#1942](https://github.com/radixark/miles/pull/1942)、[#1943](https://github.com/radixark/miles/pull/1943)、[#1944](https://github.com/radixark/miles/pull/1944)、[#1945](https://github.com/radixark/miles/pull/1945)、[#1946](https://github.com/radixark/miles/pull/1946)、[#1947](https://github.com/radixark/miles/pull/1947)、[#1948](https://github.com/radixark/miles/pull/1948)、[#1949](https://github.com/radixark/miles/pull/1949)、[#1950](https://github.com/radixark/miles/pull/1950)、[#1951](https://github.com/radixark/miles/pull/1951)、[#1952](https://github.com/radixark/miles/pull/1952) | 整栈迁移 | 复用 RPC/worker 层，避免 RH2 重造；本轮未逐项验证 RPC 协议。 | 运行时路径/部分源码 |
| 101 · [#2740](https://github.com/radixark/miles/pull/2740)、[#2745](https://github.com/radixark/miles/pull/2745)、[#2746](https://github.com/radixark/miles/pull/2746)、[#2747](https://github.com/radixark/miles/pull/2747)、[#2751](https://github.com/radixark/miles/pull/2751)、[#2752](https://github.com/radixark/miles/pull/2752)、[#2753](https://github.com/radixark/miles/pull/2753)、[#2754](https://github.com/radixark/miles/pull/2754)、[#2756](https://github.com/radixark/miles/pull/2756) | 整栈迁移 | 复用统一 WeightUpdater，保留 dirty/all-engine/cold-resume 合同。 | 运行时源码 |
| 102 · [#3198](https://github.com/radixark/miles/pull/3198) | 整栈迁移 | 统一 snapshot/checkpoint 写入；旧目录覆盖删除需运行方案处理。 | 运行时源码/发布契约 |
| 103 · [#3342](https://github.com/radixark/miles/pull/3342) | 条件使用 | HF 导出与 native 保存重叠的收益随 checkpoint 阶段测量。 | 路径/适用性筛选 |

## 文档

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 104 · [#2650](https://github.com/radixark/miles/pull/2650) | 基线已有 | 大模型 recipe 文档已在 base，不意味着目标设备能跑。 | Git 祖先 |
| 105 · [#2535](https://github.com/radixark/miles/pull/2535) | 基线已有 | Mooncake 数据传输与文档已在 base；有瓶颈再启用。 | Git/源码 |
| 106 · [#3213](https://github.com/radixark/miles/pull/3213)、[#3214](https://github.com/radixark/miles/pull/3214)、[#2837](https://github.com/radixark/miles/pull/2837) | B 线参考 | 未来 sandbox provider 接入有用，当前不替换本地 Docker 边界。 | 示例/适用性 |
| 107 · [#3209](https://github.com/radixark/miles/pull/3209)、[#3313](https://github.com/radixark/miles/pull/3313) | 设备选择后 | AMD 指南随设备选择使用。 | 适用性筛选 |
| 108 · [#2651](https://github.com/radixark/miles/pull/2651) | 基线已有 | 旧路径文档修正已在 base；新版 versions/FT 页仍有过时说明。 | Git/文档核对 |
| 109 · [#2606](https://github.com/radixark/miles/pull/2606)、[#2655](https://github.com/radixark/miles/pull/2655)、[#2657](https://github.com/radixark/miles/pull/2657) | 基线已有 | 入口文档刷新不作为项目新增功能。 | Git 祖先 |

## 依赖

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 110 · [#2714](https://github.com/radixark/miles/pull/2714)、[#3124](https://github.com/radixark/miles/pull/3124)、[#3321](https://github.com/radixark/miles/pull/3321) | 部分已有/整栈迁移 | 0.5.18 已选入；新 0.5.20 与最终 pin 需整体验收。 | Docker/lock/Git |
| 111 · [#2673](https://github.com/radixark/miles/pull/2673)、[#2734](https://github.com/radixark/miles/pull/2734) | 部分已有/整栈迁移 | 相关分支调整已在 base；具体新 Megatron lock 不同。 | Docker/lock/Git |
| 112 · [#2872](https://github.com/radixark/miles/pull/2872)、[#3336](https://github.com/radixark/miles/pull/3336)、[#3584](https://github.com/radixark/miles/pull/3584) | 整栈迁移 | Bridge 新 pin 与转换/恢复/训练一起核。 | Docker/lock |
| 113 · [#2790](https://github.com/radixark/miles/pull/2790) | 已选入 | FLA 0.5.2 已提前接入；新版其它 patch 仍需匹配。 | Docker/Git |
| 114 · [#3309](https://github.com/radixark/miles/pull/3309) | 整栈迁移 | TileLang 0.1.14 应与模型/kernel 依赖成套。 | Docker/lock |
| 115 · [#3296](https://github.com/radixark/miles/pull/3296) | 整栈迁移 | cudnn-frontend 1.28 与新镜像一起核。 | Docker/lock |
| 116 · [#2670](https://github.com/radixark/miles/pull/2670)、[#3192](https://github.com/radixark/miles/pull/3192) | 部分已有/整栈迁移 | 旧 TMS 修复已在 base；新版 TMS pin 是增量。 | Docker/lock/Git |

## 不兼容变化

| 序号 / 上游项 | 项目处理建议 | 判断理由 | 核对层级 |
| --- | --- | --- | --- |
| 117 · [#3703](https://github.com/radixark/miles/pull/3703) | 迁移必查 | 版本化 release 仅 CUDA13；当前 Docker 默认本已 CUDA13。 | 构建/发布契约 |
| 118 · [#1996](https://github.com/radixark/miles/pull/1996) | 迁移必查 | 外部 router 模式删除；单模型仍回填旧地址字段，现 RH2 读取可承接。 | 运行时/启动源码 |
| 119 · [#2053](https://github.com/radixark/miles/pull/2053)、[#2774](https://github.com/radixark/miles/pull/2774) | 迁移必查 | session worker 数与 base port 不再共用参数含义。 | 启动源码/说明 |
| 120 · [#1971](https://github.com/radixark/miles/pull/1971)、[#2897](https://github.com/radixark/miles/pull/2897) | 迁移必查 | control API 改名与默认监听地址变化；按实际远控需求接。 | 运行时/启动源码 |
| 121 · [#2839](https://github.com/radixark/miles/pull/2839)、[#2845](https://github.com/radixark/miles/pull/2845) | 条件不兼容 | 移除 LoRA v1；本项目未用，但不能将旧多 adapter 命令迁入。 | 发布契约/源码 |
| 122 · [#3198](https://github.com/radixark/miles/pull/3198) | 迁移必查 | 覆盖先删旧 checkpoint；唯一新目录保护上一可恢复点。 | 写入契约 |

## 高亮模型补充

| 上游项 | 项目判断 | 核对范围 |
| --- | --- | --- |
| [Kimi-K3 #1825](https://github.com/radixark/miles/pull/1825) | 若选作训练模型，再采用同一镜像/转换/LoRA 配套；不是当前必须上此模型 | 发布能力与适用性，未跑模型 |
| [Qwen3.8-Flash-Next #2777](https://github.com/radixark/miles/pull/2777) | 新 hybrid MoE 支持可减少自接模型成本；依赖与硬件规模须另核 | 发布能力与适用性，未跑模型 |
| [GLM-5.3-Flash #2786](https://github.com/radixark/miles/pull/2786) | 同上；R3/backend 条件不能泛化到当前 Qwen 或 I18 | 发布能力与适用性，未跑模型 |

## 未列入发布条目但主链必须核对的接缝

运行时审查还追了新版版本发布频率检查（#2470）、快照 eval skip 处理（#2823）、旧引擎与 manager 文件迁移，训练审查核对 Sample 版本结构与 custom loss caller。这些在主报告和子报告中记录，未为了凑发布覆盖数加进本表。
