# Dask7656：检查 delayed 函数实际收到的 dataclass

2026-10-03。R11 已正式消费修订，四候选正式 CPU 评分完成；独立核查通过，Coder及Qwen3.6两模型首轮均完整评分、题主轨迹及非作者语义核通过当前目标，双模型回执已核收。base：`07d5ad0ab1bc8903554b37453f02cc8024460f2a`。

本题要求未初始化的 `init=False` 字段不妨碍 dataclass 作为 delayed 输入。原代码以原类重建参数，既有测试要求嵌套 Delayed 求值。09-29 已证 `wrong_result_type` 把实际参数改成 `SimpleNamespace`，最终属性值仍正确，原正式参考却给 1；这不是最终字符串错误，也不能推断未执行的分支失败。

本轮只增强既有 `test_delayed_with_dataclass`：在被调用函数内检查原 dataclass 类型和字段值，保留嵌套求值，另检查同类默认字段对象。参考仍为 1 F2P、48 P2P，题面不变。不新增 `post_init` 或已存在 `init=False` 字段状态恢复要求。

| 候选 | 原正式分 | R11 新版本实测 |
| --- | --- | --- |
| noop | 0 | 0 |
| gold | 1 | 1 |
| wrong_result_type | 1 | 0：实际参数类型断言 |
| opaque | 0 | 0：嵌套求值控制 |

历史完整 actor/私有/正式证据及独立核查继续引用。配方是 pandas1.3.5 加 stdlib distutils；trusted setup 用已证需要的 900 秒。300 秒超时在测试前发生，reward 为 null，不能计作 noop=0。宿主变化至少补身份、源码和关键导入；公开 actor 的实际首请求已确认原题面/hints；它使用 CC 控制桩，未跑真实模型。

原受信身份、新补丁及四候选离线应用/语法已核。[材料非作者窄核](../../reviews/non_author_7656_9378_7138_material_review_20261003.md)无静态阻断。[本轮 CPU 读回](cpu_readback_20261003.md)已确认真实非 root CC actor、原题面实际交付和四候选私有测试行为：gold 接受，noop、类型错解和不求值错解拒绝；每份均有全部 49 个参考，48 P2P 通过。它们不是新材料正式 reward。镜像仍有历史依赖冲突，只确认本题实测路径可用。

固定输入见 [revision.json](revision.json)、[acceptance_matrix.json](acceptance_matrix.json) 和 [cpu_acceptance_plan.json](cpu_acceptance_plan.json)，当前结果见 [results.json](results.json)。历史实测见 [09-29 结果](../../../../../swegym_cpu_preprobe_20260929/tasks/dask__dask-7656/result.md)。[R11 正式 CPU 读回](formal_cpu_readback_r11_20261003.json)已确认 0/1/0/0；每项49参考完整、48P全部通过，候选UID54321/评分UID54322、安装和测试完整、清理完成。57份原件已按SHA回收。[R11独立窄核](../../reviews/non_author_7656_formal_cpu_r11_review_20261003.md)已完成：57份原件SHA/字节、正式材料与配方、逐项参考、非root边界和清理均核实。R11评分镜像50bca固定，正式训练actor接法仍未实现；当前已授权基座诊断可用GPU既有固定image_override消费已验证118f47 actor，保留原source/public/environment身份并明确诊断差异。探针前仍由执行者验证GPU实际镜像、recipe和consumer版本，不把CPU image ID当成GPU已部署。

当前[首轮探针请求](probe_request.json)固定原R11输入与预算引用。GPU需先获得同ID镜像；已在CPU-c的统一prepare槽成功导出actor118f47/grader50bca，两配置ID保留；归档2,017,843,609 bytes、SHA及13份导出记录已核验并直接交给GPU线程。GPU实际回执已核归档SHA、docker load成功及精确actor118f47/grader50bca配置ID（linux/amd64）；[原件](../../../../../../../../../runs/ordinary_gpu_probe_20261002/migration_20261003/dask7656_actual_fixed_image_load_v1.json) SHA为 `a479715d3868aa982db040ef9f766c9199a6170efe37f831ba3889f754f308cd`。执行者确认本题不再依赖CPU-c源归档。当前实际首Coder `gpu1003-dask7656-coder-a1` 已完成，实际actor UID54321/评分UID54322及离线pandas/工作树安装、逐参考和清理经[执行独立核查](../../../../../../../../../runs/ordinary_gpu_probe_20261002/reviews/dask7656_coder_a1_execution_review_v1.json)验证。

[首Coder题主轨迹分析](model_probe_coder_a1_analysis_20261003.md)及[候选非作者窄核](../../reviews/non_author_7656_coder_a1_candidate_review_20261003.md)确认当前目标通过：1F48P均过、原reward1，完整日志50PASS+2非参考XFAIL。保留原类和嵌套求值；已存在的init=False默认/手设字段仍重建失败，属于未修原有缺口且当前明确不新增该要求，没有已证新回归。模型最后泛称全面兼容超出证据；第二次源码编辑无行为改变，已作为验证表述问题记录。求解62.669秒、34模型响应、33工具、输出6698token；评分387.646秒/准备366.715秒单列。该Coder点时分析封存不回写；现在Qwen首轮也已回齐并分析，双模型回执已returned／题主ack。本题无新CPU复修；后续重复依全局覆盖规则，当前不追加，不授稳定能力或训练资格。

[Qwen及双模型首轮分析](model_probe_qwen36_a1_analysis_20261003.md)确认Qwen当前目标通过：两入口跳过未初始化init=False字段，原类／字段／嵌套求值保持；49参考过，正式50PASS／2非参考XFAIL。模型新增公开测试被评分投影排除，不能当私有评分污染；--timeout参数错误已纠正。148原件13,107,604B、31回执引用和3Edit重放均核，非作者报告的点时说明待对齐已由GPU澄清：unchanged只保留prepared spec.prompt原字节。两臂实际同SHA／3199B，旧通用public_hints未交；原CPU控制桩范围与真实GPU输入分开，不把未收到的禁止测试编辑提示当违令。当前描述更正，原probe／原分／轨迹保留。Qwen求解27.802s／20响应／19工具／3220输出，评分384.38s／准备365.008574s分列；两模型各一次通过不证明稳定能力或训练资格。
