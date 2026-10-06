# Conan 13230 当前题卡

2026-10-03。**正式R11 CPU及两份非作者核查完成；Qwen3.6／Coder首轮两模型均raw1，分别37参考全过。两份七维分析、语义／执行独立核查已采纳，总回执已ACK并清活动指针，本题配置诊断首轮收口。** 当前无材料阻断，稳定性、真实交叉编译及训练资格尚未建立，详见[当前配对结论](probe_pair_analysis_20261003.md)。

目标是 Macos build／Linux host 的最终 CFLAGS 不含 Apple flags。修订保留原 Android F2P 和 34 个 P2P，新增 Linux 无 SDK／SDK 哨兵两节点。正式完整候选 noop／gold／Android-only 的 reward 为 0／1／0；每方精确核销 37 个参考，共 111 个状态，没有缺席或跳过。

验收覆盖固定发布材料的 prepare、整份候选到 FrozenPatch 及可信投影、实际安装与测试、评分器关闭和两层清理。55 件原件 SHA／大小一致，两份独立报告无当前 CPU 阻断。完整资源事实未逐容器留存，不将声明配额记作 CPU 容量实测。见 [CPU 验收及根审处置](cpu_acceptance_r11_20261003_v1.json)。

公开原基线actor的34项回归和真实配置生成命令按相同source／vendor范围复用。[solver brief v2](solver_brief_20261003_v2.md)说明Linux SDK诊断前置并限定配置用途，干净读者与增量复核保持。两模型各自实际首gateway已核完整原issue＋brief交付；模型轨迹另有原件，旧scripted actor不是其替代证据。

[固定请求](probe_request_20261003_r11_v1.json)的原SHA与两模型各一次预算保持。[Qwen3.6首次分析](probe_qwen36_a1_analysis_20261003.md)和[Coder首次分析](probe_coder_a1_analysis_20261003.md)分别记录完整输入／候选／投影、根因、定位、工具、并行、验证、效率与结束边界。Qwen测试新增保留FP但被可信投影剔除；Coder两开发脚本全保留投影，正式37参考不执行它们。两者生产均改为host侧Apple判断，没有评分绕过。Coder native自测无行为断言、打印型复现和functional失败／skip的证明边界记两项非阻断P2，不扩大为全仓回归或真实编译通过。

两臂材料、实际470b镜像、完整baseline、公开prompt、37参考和预算一致；实际runtime为code5／code7，完整代码树不同，差异已披露，不用单次39.548／51.047秒作模型排名。原回执部分旧状态／参考数量文字与当前事实不符，已按原日志和当前总账另记，原件保持。当前本题无CPU／已授权GPU续跑待办，继续同仓其余题覆盖，普通追加采样暂缓；整体资源操作服从对应负责线程的现行授权。[结果清单](result_manifest.json)保存当前核收及证据，旧首臂报告的待回状态为历史快照。
