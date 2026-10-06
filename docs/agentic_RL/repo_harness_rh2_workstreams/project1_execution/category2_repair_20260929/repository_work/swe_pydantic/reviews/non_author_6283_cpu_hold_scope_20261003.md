# 6283 自有 CPU 暂停影响范围：非作者只读窄核

核查日期：2026-10-03。范围是现有自有 CPU 暂停对一次 R19 四行正式实验的具体影响，不是新 CPU 结果验收。本审查已接触旧 CPU、私有材料、固定输入及保护代码；不是 fresh 公开读者。

现有证据支持在原精确镜像、资源、保护方式和 300 秒 reset 预算下开展一次 R19 四行正式实验。未发现必须等待 8316 在 R20 下实际成功的技术依据；该条件不是原暂停理由写明的要求，也不能用 8316 的 900 秒成功证明 6283 的 300 秒足够。当前仍有实际执行阻塞：原 cpu_infra_hold.json 保持，派发 guard 会在远端命令前返回 75。本次审查不解除暂停、不派发作业、不宣布 CPU 已恢复。

## 暂停的事实与当前边界

[原暂停文件](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/cpu_infra_hold.json) 的 434 字节及 SHA-256 仍为 ce3b1b2581109b955261c5da6d689df0dd219ffd6f5f34e03714710e19160f5b。原因为“8316第六候选正式作业异常自然停止，待归档实际首因及共享CPU支持核收；本包不派发新CPU，不自动重试或改300秒保护”，范围是新的自有 CPU 派发，既有 GPU 探针不受该文件影响。

[8316 部分结果非作者审查](non_author_8316_partial_cpu_review_20261003.md) 已验 759 原件，记录首个真实失败是第六行 control_surface_protect 超过 300 秒；安装/测试未启动，reward=null，不是模型 0 分。五行可复用且本 run 清理零残留。完整底层慢因（共享负载、I/O 等）仍未确定，不能把已归档失败阶段写成主机故障根因已解决。

[R20 支持题主核收](../coordination_20261003/8316_r20_support_owner_readback_v1.json) 及本轮所核六项绑定原件证明版本化支持已发布、cpu-a 部署读回和 prepare/replay 连接已核收。回执明确 actual_task_cpu_recovery_verified=false、6283_hold_released=false。其唯一 reset 改动适用于精确匹配的 8316、DVC9395：300→900；6283 不在政策的两个 task/revision/grading/patch/exactgrader identity 条件内。R20 snapshot 的 6283 reset 仍为 300。

原暂停所待的实际失败归档和共享支持核收已具备，可据此重新判断本包暂停的适用范围；它们不自动解除文件或证明实际恢复。R20 的 6283 snapshot 是默认 source 消费口径，也不是 R19 显式 58d derived 镜像的运行验收。当前 [6283 派发代码](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/dispatch_6283_v2.py) 仍检查 cpu_sequence_hold.json / cpu_infra_hold.json；前者不存在，后者存在，命中后 sys.exit(75)。题主需先针对本包处置并留证现有暂停范围，保持正常 cpu_slot 入口；本审查不建议绕过 guard。

## 6283 自身已有的可比较运行

复用 [旧 R7 完整 CPU 非作者审查](non_author_6283_cpu_review_20261003.md)，没有重新机械复核其全部 375 原件。本轮独立读取 [真实 status](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/remote_evidence/packages/swe_pydantic/formal_v1/outputs/pyd6283-formal-20261002185959-dbe65/status.json)、槽 status、选定 call.json/完整 stdout，重新计算阶段耗时、核实际镜像/资源与清理。旧 job 为 pyd6283-formal-20261002185959-dbe65，R7 manifest f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b；cpu-a 自然返回 0，noop/gold/validate_construct 实际 0/1/0，40 参考完整判分，完整 wall time 514.250 秒，本 run 零残留。

| 调用 | 实际阶段 | 秒 | 退出 |
| --- | --- | ---: | ---: |
| 0025 | grader control_surface_protect | 133.886 | 0 |
| 0060 | grader control_surface_protect | 122.161 | 0 |
| 0095 | grader control_surface_protect | 113.588 | 0 |
| 0008 | candidate rollout_trusted_init | 4.472 | 0 |
| 0039 | candidate rollout_trusted_init | 2.547 | 0 |
| 0074 | candidate rollout_trusted_init | 2.752 | 0 |

三次慢调用具有相同保护正文 SHA-256 c9ad9d3ff2672bc99123bf9e20afb6d9d2bc0cb6e8980ac96dba8c42c4e5e799，完整 stdout 都有 RH2_PROTECT_OK=1。后三次短调用是候选可信初始化，正文和职责不同；不能拿其 2–4 秒作为 grader 保护耗时。旧整 job 的 514 秒跨多个阶段，也不是单次 reset 超过 300 秒。

旧六次 candidate/grader docker run 实际镜像都为 sha256:58d0c004cec144834a01dfc160c0f4caf427a9b31fd5ad95a60d03f6f3623226，network=none、2 CPU、4,294,967,296 字节内存、pids=512。精确 Python 3.8.19 / core 0.42.0、安装/源码导入、完整 baseline/FrozenPatch 和原结果审查沿用已核原件；本轮没有重跑。此证据是 6283 在自身镜像和原预算下的三次真实成功样本，不是现在的 CPU 槽空闲、负载或未来耗时保证。

## R19 固定输入与旧运行的连接

复用 [R19 实际固定输入审查](non_author_6283_v2_input_review_20261003.md) 并本轮再核输入/runner SHA、JSON 身份、脚本字节与选定冻结代码。source_release=cat2-cpu-r2e093-swe40-pyd6283-moto6114-20261003-v1；manifest=2cfdd9b4f1134c0915346b727b729665482c4c1121b550764833f16f2982402e。formal_inputs SHA=4d50c69969e883e48f919ac1221594d88665e409a720f67b9a16952c393b4640；runner SHA=40b0460b70c2890a1eb3fbbf2474e10bee906125e3068868079370044d875805。

四行按 noop、gold、validate_construct、qwen36_a1_pop_private 固定顺序；每行 41 参考（2 F2P、39 P2P）。旧两条 F2P 与旧 38 条 P2P 顺序完全保留，只新增 test_root_model_construct_preserves_private_default。0/1/0/0 是固定预期，尚未实际观察。新增 qwen 负对照和三模块源码审计范围不是已执行事实；旧 GPU FrozenPatch/原分没有在此重评分。

base commit a29286609e79c79b2ecd71bc7272eea43ed9fccd、公开 digest sha256:d2d8b998296f14d164a024519603119def49bbc9ba84fad05b7a5c0eebceddc5、base/derived ID、core、完整安装 recipe/asset 和受保护 test_file 与旧 R7 相同。local_prepare spec 的 hygiene 完全一致；reset/apply/test 仍为 300/120/1800 秒。runner 资源仍为 2 CPU/4 GiB，保护 profile 保持同一 UID/目录/受保护测试边界。

“脚本全部相同”需要限定：五份 candidate test/install/after-install/pre/post-observation 脚本逐字一致；eval_script 和 trusted_setup_script 随私有 effective_test.patch 变化。独立将新内嵌完整 patch 换回旧 patch 后，两份脚本分别与旧脚本全字节一致，未见其它机制变化。R7/R19/R20 的 sandbox_profile.py 全字节同 SHA 313bfd7691c5dca775aa0e9992f13561e20936f062ddfa3d269892b6bf4895ee；R7/R19 manager 中保护调用的 AST 和实参相同，timeout 取 spec.env_reset_timeout_seconds。整个 manager 文件并非全字节相同，不能据局部连接宣称整个版本无差异；既有 R19 runner/材料静态审查沿用。

[R19 上传题主核收](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/6283_v2_upload_owner_readback_v1.json) 和 [实际远端读回归档](../../../../../../../../runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/6283_v2_upload_verified_remote_v1.json) 已连接 10 payload、精确成员/大小/SHA、formal_6283_privateattr_v2 namespace，tar SHA e4cfa59f7e3a74219ecc42eedf57c65ad2247ed8bce708123add218bd4825f86。读回本身未调用 Docker，题主回执 cpu_dispatched=false、own_cpu_hold_kept=true。旧输入审查当时的“上传待完成”是历史状态；本报告按新读回记为已完成运输核收，不回写旧审查。

## 是否支持一次原预算实验

本范围内没有发现需要把 8316 R20 实际成功设为 6283 前置条件的具体契约或技术证据。两题的精确 grader 镜像/材料不同，8316 获批的是 900 秒精确例外；该成功即使发生，也不能验证 6283 的 300 秒上限。6283 有自己在相同精确镜像/保护/资源下的成功原件，R19 的相关运行机制保持，新增内容主要是私有 P2P 和固定负对照；因此支持题主针对现有 hold 作范围处置后，经正常 cpu_slot 开展一次原 300 秒四行实验。

这个判断只支持收集新事实。共享 CPU 慢因仍未知；三次旧保护耗时不覆盖当前负载、第四行或新 PrivateAttr 行为，新保护仍可能超时。首个新 infra 或清理未知即停止，保全 call/report/slot 与 null 原分并回公共支持；不得循环重试、继续提高预算、把 infra 写成模型 0 分或沿用未完成的清理推断。暂停文件、300 秒限制和共享安全机制本轮均未改动。

## 验证范围与明确未完成项

使用本地标准库 JSON、SHA-256、AST 和字节比较；复用已核旧 CPU 全原件、8316 部分结果、R19 材料/runner/固定输入及发布支持证据，只重核有关身份和阶段。没有 SSH/Docker/安装/pytest/模型/作者 helper 执行，没有新的实机资源采样或 CPU 派发。本次只写本 MD 与同名 JSON。

本范围判断通过；当前执行阻塞仍是未处置的自有 hold。新四行 41 参考、实际 PrivateAttr、容器安装/导入、候选 FrozenPatch 与完整 baseline 运输及清理尚无新结果，本报告的 CPU 验收/派发 ready、GPU ready、实际恢复、训练资格均为 false。不要求换公开读者：公开输入未改，旧 actor 控制桩边界可按身份复用，但它不是模型求解或新私有行为证据。
