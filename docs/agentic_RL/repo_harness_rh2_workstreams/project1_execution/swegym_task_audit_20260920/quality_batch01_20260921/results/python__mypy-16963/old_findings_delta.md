# python__mypy-16963：旧结论增量

协调者明确放行后读取 history/python__mypy-16963/refs.json 及其唯一引用 `R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_mypy_2/records/python__mypy-16963.json`（H），R=`.`。未扩读其它题/其它角色，前稿 SHA256 `faa88f06bce3ae6bcf9cf449cfda359c3988ba52fc2867f28d55b4e95048a6cf` 保持不变。

| 旧主张 | 处理 | 新决定性依据 |
| --- | --- | --- |
| Type[TD] base 缺分支、helper已存在、材料对应 | 确认并补强 | checkexpr:1818–1860/949–956，S2第210行逐对象核对；09-19原noop四次Cannot instantiate与gold完整case PASS。 |
| 三种非法参数检查不能从题面推出，几乎只能复用gold helper | 推翻“无法公开推知”；诊断格式问题另留 | 公开check-typeddict:47–75已有同三类误用及字段类型错误，docs构造器语义支持延伸。helper复用不是行为唯一途径。区别是直接TD路径的诊断文本不同于新增F2P的callable文案；语义拒绝合理不等于精确措辞唯一合理，替代实现仍未执行。 |
| 单纯删 unsupported_type_type 兜底即预期满分 | 推翻所述单独候选；更窄条件下可有回归风险 | 删除报错仍返回Any，三类非法调用不会产生F2P要求的三条诊断，整数组比较将失败。若先正确实现TD分支再额外删兜底，才有可能保留F2P并破坏Type[Tuple]旧错误；H没有该组合候选运行。前稿另提出保签名却返回Any的漏测路线，因F2P只reveal输入而不看结果。 |
| P2P=0、正反两侧都有；应补整个TD文件 | 确认计数和内部保护；不自动采用全文件修订 | 当前日志确实只1 item。缺口须落到结果精度、公开原例或具体旧Type行为，零P2P不自动判坏或授权改变reward。先完成前稿唯一原例对照，扩展测试按具体结果选择。 |
| gold没覆盖原五条错误，例如Union赋值“明显另一bug” | 未核实，纠正依据 | gold补丁短不能推出输出仍错；base的Callable→Type与Type Union语义已支持相关兼容。H也说原五错来自0.910，自己未运行base；不能同时把旧错误当当前gold失败证据。Boat join是新的具体源码疑点，但也未运行。 |
| 旧raw hints在1.7.1更新为三条错误，题面应替换/收窄 | 历史暴露，当前输入缺证；不按旧摘要改题 | 当前public bundle里public_hints是harness操作说明，不是H提及的689字符issue评论。H未给可定位原始hints路径，本轮未读其原件；实际CC消息也未捕获。公开读者已独立识别版本差异和Boat范围歧义；优先base/gold完整原例，之后才决定是否需要说明，而非先收窄题目保gold。 |
| 无任何运行/安装证据 | 过时于09-19派生grader条件 | 本题image/build、G/N ledger:1与日志已读：固定八个wheel离线安装成功、真实断言分差、精确节点无缺席。actor仍未验。 |
| 无-n0会并行，需统一修 | 确认实际并行，不确认当前假失败 | 原日志两次11 workers [1 item]，峰值约821/836MiB、无OOM与收集失败；默认-nauto确有开销。公开开发建议-n0，但未做并行对照，不把资源口径当语义缺陷。 |
| 16963修复commit等于16966 base，应同侧 | 未核实，留协调者关系审查 | H没有给具体修复SHA或可定位独立证据，仅转引其它角色；未读16966。该主张比“同文件”具体，但仍不能当本题已确认事实。 |
| 将mypy/test/*和test-data/*统一排除/保护 | 不采用旧建议，边界仍未知 | 当前本题原始restore只覆盖check-typeddict.test，gold源文件可投影。gold没有触碰某目录不能证明所有合法解也不需它；共用当前规则不使用默认测试名通配。未执行helper攻击，不把历史行号或提议当现已证漏洞；additional_exclusions仍空。 |
| 无泄漏、纯离线、无外部依赖 | 限定范围 | 题面无答案链接只证明题面所见；真实镜像/Git/网络未验。case无在线服务但有repo fixtures和测试依赖，派生配方将安装包预置，不等于无需准备或actor已可用。 |

旧记录未提供新决定性执行证据，最终保持前稿的needs_review/static_review与完整原例优先对照。追加保留diagnostic-route、return-Any与optional-key静态线索，尚无已证实误拒/假阳性或gold回归。旧27分钟不填成本；未改原题、测试、参考或前稿。
