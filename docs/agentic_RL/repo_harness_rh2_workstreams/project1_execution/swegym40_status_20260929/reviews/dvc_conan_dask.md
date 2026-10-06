# 原SWE-Gym 40题：DVC/Conan/Dask 14题现状复核

2026-09-29。复用历史上下文的本地证据复核，不是重新盲审；未执行远端、项目或模型，未改原题卡。逐题结构化证据与真实路径见[dvc_conan_dask.json](dvc_conan_dask.json)。

**本包6题属于旧19个有条件比较候选，另8题仍待语义/开发诊断；4题有09-22模型尝试。旧19不是训练名单。** 8道旧诊断题在固定scope和任务二目录中未找到新增actor/CPU结果：Conan14177、Dask8801、DVC9395/3620/3576/3665/4785/4185。其历史grader曾运行，静态疑点仍未升级成新实证。

| 题目 | 最新有证据的状态 | 当前用途与残留 |
| --- | --- | --- |
| conan-io__conan-15422 | 正式actor已验；有模型证据 | 条件比较；12个正式1中已实测3条遗漏公开需求（DS a1多配置、Coder a1/a3默认jobs），Q36 a2另有schema4/最低CMake3.25兼容风险。原卡5条gold差异包含DS a4，T0已明确其生成器范围差异不算错。 |
| conan-io__conan-14177 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；公开接口与gold/测试的结构性冲突已由源码＋历史gold13/13接受确认；不等于显式verbose调用已实跑。 |
| dask__dask-8597 | 正式actor已验；有模型证据 | 条件比较；派生镜像pip check仍有distributed2024.8.0要求dask2024.8.0与本题旧dask冲突；本地数组命令已验，不泛称环境全健康。 |
| dask__dask-8801 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；原参考确实锁文案/异常形态，当前公开依据不足以唯一化；不把局部拒绝升级为完整正常解实测误拒。 |
| iterative__dvc-5839 | 正式actor已验；有模型证据 | 条件比较；硬编码8官方评分未执行；标量float既有不舍入不算新gold缺陷。 |
| iterative__dvc-4166 | 正式actor已验；无本轮模型证据 | 条件比较；pathspec版本改变题目语义，未来必须保持actor0.8.1与grader一致。 |
| iterative__dvc-1681 | 正式actor已验；无本轮模型证据 | 条件比较；题面原例依赖旧版产物及大文件，本轮无法原样重跑；已有公开替代复现，不等于题无效。 |
| iterative__dvc-6954 | 正式actor已验；有模型证据 | 条件比较；正常负数工作流已补验；int-only退化未评分，非法输入不新增必修要求。 |
| iterative__dvc-9395 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；pull+dry文件快照与dry=False正控、无remote对照尚未跑；actor未验证。 |
| iterative__dvc-3620 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；数据丢失退化的正式校准、非空文本链接断开/写入不改缓存未跑；symlink-only不能单凭CPU决定hardlink规格。 |
| iterative__dvc-3576 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；base/gold/命令层替代解的CLI输出与正式分数未对照；真实Git/JSON路径和actor未知。 |
| iterative__dvc-3665 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；验收强制内部helper及Windows行为未受当前Linux测试直接保护，是已确认结构性限制，尚无动态误拒/漏收。 |
| iterative__dvc-4785 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；异常类型解释有公开争议：题面提raise_for_status，现有CLI用DVC异常；不等于任意Requests路线都合法或已误拒。 |
| iterative__dvc-4185 | 仅历史grader＋静态；无本轮模型证据 | 暂作诊断/needs_review；base/gold重新加载后的status与不带force commit双症状尚未跑，不能写gold已实测漏修。 |

最重要的更新：

- Conan15422 的CLI/CMake和G1 noexec已修，功能选择组10通过，不继续列环境未修。原模型12/12得1并不证明全部语义正确：3条公开需求遗漏及1条schema兼容风险仍在；DS a4的纯生成器差异按T0不判错。比较使用预登记事后审计，训练因S1不准入。
- Dask8597的pytest7.4.4、DVC5839的pathspec0.8.1、DVC6954的pygit2 1.14.1、DVC4166的pathspec/networkx兼容均有正式actor复验。Dask仍有distributed依赖冲突；DVC4166必须保持匹配语义版本，并保留setup.py初态。
- DVC1681可用原镜像与公开替代复现，原题例不能原样重跑的限制保留；不能把需自造复现误写成坏题。
- DVC5839后续CLI矩阵支持10个成功候选；两个失败确属小数位改成有效数字。DVC6954后续已覆盖正常负int/float/nested、lock与更新；非法坏行gold CLI有shell引号错误，这是无效观察、不是DVC本体缺陷，不能据该条rc255判断gold语义，且T0本就不要求这些非法表达式。
- 旧静态CPU方案不机械变比较闸门：例如Dask split=True退化、DVC5839硬编码8、DVC1681内部规范化路线仍未执行；需要时做窄校准，而不是重跑全部题。训练正面覆盖与留出隔离另按标准§2/10判断。

root本轮只读机器核查回传：原6个actor派生镜像当前均不在机器，本包涉及5个。下次派发需按已验配方重建并核身份，这属于准备条件，不否定09-25历史实证。本review未远端核机器。

本次只登记下一步，未取得新实验或评分修订授权；机器是否开启不改变本地证据的证明范围。
