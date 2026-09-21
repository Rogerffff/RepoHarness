# conan-io__conan-15422

目标：在 base `f08b9924` 生成的 CMake build preset 中写入 jobs，使安装后的外部 CMake 可按配置并行。建议 **needs_review / static_review：开发诊断候选，actor 待验**。原镜像 noop 在 jobs 断言处 KeyError；gold 整文件 41 passed、3 个非参考平台 skip，命令退出 0，F2P=1/1、P2P=40/40。

| 需求/旧行为 | 公开依据 | 验收 | 覆盖 |
| --- | --- | --- | --- |
| 显式 jobs 传入生成 JSON | 题面 JSON；cpu.py:8–28 | test_presets_njobs：值 42 | 单值、首次安装 |
| CPU 默认与其它配置值 | 同 helper 契约 | 无 jobs 默认断言 | 缺失 |
| 多配置追加、名称/用户文件保护 | presets.py；旧公开测试 | singleconfig、multiconfig、用户预设相关 P2P | 结构受保护；追加条目 jobs 未测 |

八方面已查：公开包与 S2/base 对应；原始失败与 gold 日志；新增测试完整调用/Mock/断言；非 gold 合理路线；相关 P2P 与 gold 两条生成路径；导入、临时写入、网络及编译需求；官方恢复与源码投影；用途及暴露范围。未查：全部无关 P2P 语义、跨生成器实际构建、真实 actor/消息/镜像资产、与旧记录14296的具体派生关系。

核心限制：只在显式配置时写 jobs 的部分实现静态上可能满分，默认安装仍漏修；尚无该候选实跑。gold 的 helper 已在 base 交付，无无关改动；无条件跨生成器写 jobs 与既有 NMake/Visual 并行策略的兼容性待核，未证明 gold 错误。旧“CPU 默认随机器变化即不稳定”归因不成立。没有锁定 gold 内部形状的证据。

随后14177原件调查确认：本题公开base的patches.py已含14177 gold关键日志行为；应登记跨题参考暴露，非重复需求。见14177历史前分析；本题前稿未改。

唯一优先下一步：真实 actor 中检查解释器/包来源后，以公开最小 recipe 比较显式 2/7、未配置和多配置追加，并用条件写 jobs 的 CPU 负对照检验漏收。评分原镜像已有成功记录，无已知需修环境项；它不等于 actor 已验。独立 reviewer 同意有限候选处置；复核见 [review.md](review.md)。None/未配置会回退 CPU 默认，0/负数及后端语义仍待验。

完整映射、运行原件与范围见 [历史前分析](analysis_before_history.md)；历史变化见 [对照增量](old_findings_delta.md)。主审已见 gold/隐藏测试/旧调查，不得充当独立 solver。
