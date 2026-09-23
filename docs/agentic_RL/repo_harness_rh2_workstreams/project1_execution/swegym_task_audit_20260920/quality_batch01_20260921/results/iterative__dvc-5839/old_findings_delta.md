# iterative__dvc-5839：旧结论增量

前稿 analysis_before_history.md 已于开放历史前保存，SHA256=fdd4f5bf681fd17ab7bdc8ee733e32d8dd61c712da89fc4c1d3eee3dfbe8f911。本文件不修改前稿。2026-09-21 收到协调者单题放行后，读取 history/iterative__dvc-5839/refs.json 及其唯一引用：
${REPO_ROOT}/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_2/records/iterative__dvc-5839.json（下称 H）。

证据路径缩写沿前稿。没有跟随 H 的跨题 prescan、3677、4124 或旧全批汇总，也未执行 CPU 对照。

| 旧主张 | 处理 | 新的决定性证据及影响 |
| --- | --- | --- |
| base 漏传 precision，gold 一行且材料对应 | 确认至本题原件层；上游完整 PR 身份未另验 | P/base/dvc/command/metrics.py:92–98，Q/gold.patch:8；S2对应三份原行142与包相等；GL:194–206候选差异；NL:832–860失败位置 |
| 题目必须先回答科学记法的新语义，gold 不成立；8位下 mse 仍为0.0 | 推翻核心数值与语义结论 | 公开帮助 metrics.py:254–255 和旧 test_metrics_show_precision:303–333 都明确小数位语义。5.017257…×10^-9 保留8位为1×10^-8，gold沿既有 round 路径符合普通表示的例子。题面另一行0.001e-09是笔误，不据此判gold未修。仍未运行原CLI，数值结论是代码/算术推断 |
| 缺一个实参只能读代码发现属于公开材料不足 | 推翻不足推论 | 源码就是公开开发材料，入口及diff对照明确；正常定位根因不需要在题面给答案 |
| F2P mock 固定内部 helper 调用，但位置/关键字均可 | 确认 | test.patch:17–21、34–41；gold全位置参数在GL:663通过。必须保持调用点的限制真实存在，但尚无已执行的合法替代解误拒 |
| 把precision传进repo.metrics.show或事后处理table是当然正确替代解 | 未核实，不能拿来直接确认误拒 | repo/metrics/show.py:97–144返回原始数据；JSON共享读取，helper默认会再次round到5。底层舍入或事后改已舍入字符串未必保留精度和JSON。需要端到端证明合法，不能仅因改法不同就称正确 |
| F2P不渲染数字 | 确认但缩小措辞 | mock返回{}及空字符串；没有题面真实CLI输出断言。不是“所有show数字完全未保护” |
| helper把precision丢掉仍能满分；P2P仅diff precision | 推翻 | grading含test_metrics_show_precision；base test:303–333有默认、4、7三个精确数值断言；GL:675、NL:893都执行通过。修改helper忽略precision预计会违反这些P2P |
| 整文件绿证明json/markdown/precision回归均保护 | 部分确认 | 21 P2P和22项执行已逐ID核；show_json_diff实际调用_show_diff，非metrics show JSON端到端；Markdown也是helper默认。保护层级见前稿映射，不外推CLI全路径 |
| 同测试文件故与4124“同族同侧” | 推翻分类依据；具体祖先关系未核实 | 同文件不是同问题。H提到4124尾换行修复，本题utils/diff.py:103–105确有末尾换行，但未读4124原件，不能据此证明精确commit/派生关系或规定拆分 |
| install仍需网络、无依赖问题 | 对当前引用条件已过时/范围过宽 | dvc_install_v1c recipe.after安装实际extras；GL:387–389、600–623、NL:370–372、583–606在deny_all派生镜像用本地wheelhouse安装成功。此为grader配方已覆盖，真实actor消费仍未知 |
| parser伪键Could（同3677） | 旧条件未核实；当前未复现该现象 | 当前两日志逐ID对账与账本均22项、参考missing/skipped空、段外0；不读取其他题替证 |
| hints为空、没有泄漏 | 对原raw字段未核实；对当前face已过时/过强 | 当前public_bundle有明确public_hints；未见题面含修复代码不能证明真实镜像无未来答案、Git或缓存泄漏 |
| ready_for_probe | 改为本批静态约定needs_review/static_review | 真实actor、实际消息、公开复现未验；旧grader通过不代替。这不表示语义缺陷已确认，仍可作为范围明确的development_diagnostic候选 |

前稿新增的“命令层硬编码8”不同于 H 的“helper忽略precision”：前者保留helper原契约，所以其P2P预计仍通过。它是精确的漏测校准候选，但不是最自然的根因修复；公开默认5和参数n的描述已经明显排斥硬编码，不能从一个参数样本就推导常见合理解会被误判或题目必须阻塞。

因此收口保持该对照为唯一有疑点的窄CPU校准建议，同时明确它不构成强制阻断开发诊断的已证问题。最先需要补的是实际actor入口与公开CLI的默认/4/8数值对照；若执行同次评分校准，再纳入前稿规定的单行硬编码8候选，与base/gold共享输入/配方。没有新增任务修订、没有把测试要求抄进题面、没有已证误拒或假阳性。

