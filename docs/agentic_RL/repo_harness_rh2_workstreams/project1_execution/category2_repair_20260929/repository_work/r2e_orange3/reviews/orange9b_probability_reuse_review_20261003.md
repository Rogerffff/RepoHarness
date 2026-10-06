# Orange9b54：旧概率校准复用范围独立审查（2026-10-03）

本次旧概率校准的结果及其证据边界可复用；窄核完成并独立封存。它支持旧版本、全量 iris 数据上区分默认 OvR 与显式 multinomial，并校准 `rtol=1e-5 / atol=1e-7`。它不替代最终 R9 十方矩阵、新公开 CC 或题级 CPU 验收。本题最终 CPU、GPU 准入和模型能力结论仍为空。

只读已有真实原件，不跑 CPU、候选、模型、新测试或 fresh reader，不重做静态/共用101。只新增本报告与同名 JSON；后续完整 CPU 报告引用它，不回写本阶段报告。

[旧概率收据](../tasks/9b5494e2/probability_precheck_v2.json)（SHA `1c643c35bdc9…`）；[45 文件捕获清单](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/cpu-c_20261003/orange9b_envonly_actor/capture_inventory.json)；[完整实际 trajectory](../../../../../../../../runs/category2_repair_20260929/repository_work/r2e_orange3/cpu-c_20261003/orange9b_envonly_actor/attempt/trajectory.jsonl)；[结构化核查](orange9b_probability_reuse_review_20261003.json).

## 原件和实际数值

45 份已捕获 actor/trusted 原件大小与 SHA 全部独立核对一致，另核旧 builder 的6份已捕获文件 SHA 一致。收据所引文件 SHA 一致。旧清单排除了 secret keys 与 baseline.tar 等大包；运输归档 SHA 只是清单记录，未在本次另核归档本体，也不声称全工作树字节核验。

实际 CC 2.1.205 由确定性端点给出固定命令，以 uid54321、`/testbed/.venv/bin/python` 完成七次 Bash、七份完整结果及八次HTTP请求，ran/completed、harness exit0。gateway 与 stub 全八次模型可见 messages 一致，首请求与实际 prompt 逐字一致。用量为合成端点记录，不是模型成本或模型能力。

完整工具结果给出 Python3.7.9、NumPy1.17.5、SciPy1.5.4、sklearn0.22.2.post1。三次比较命令逐字相同：`Table("iris")` 全150行；Orange 默认 learner 与显式 `multi_class="multinomial"` 分别拟合，再比较两个 `Model.Probs` 的150×3矩阵，实际执行 `np.max(np.abs(a-b))` 和 `np.allclose`。

| 来源 | 结果行 / tool ID | 默认策略 | 最大概率差 | allclose |
| --- | --- | --- | ---: | --- |
| base | 30 / toolu_832d905ded95c9af | auto / lbfgs / l2 | 0 | true |
| gold | 48 / toolu_2466748480e49064 | auto / lbfgs / l2 | 0 | true |
| G1 | 66 / toolu_b207d9838ad52c07 | ovr / lbfgs / l2 | 0.38716698009532013 | false |

容差实际为 `rtol=1e-5 / atol=1e-7`。G1 的工具 rc0 与 is_error=false 表示诊断完成；它打印 relation_holds=false，不能把退出0写成概率关系通过。这只校准记录条件下的关系，不能证明所有数据、合理解或solver/penalty组合，也不能推定最终sysconfig环境数值等价。

## 补丁、源码与最后私有工件

apply_gold（命令35、结果39）与apply_G1（命令53、结果57）均先 restore HEAD 再应用各自 payload，并运行 git apply --check。两份实际payload SHA 分别为 `162ad8b40ffa…`、`00ba0b7c7801…`，不是在gold上累积G1。

实际拟合进程加载 `/testbed/Orange/classification/logistic_regression.py`，三份源码 SHA 为base `ad54fe8199ca…`、gold `65ec3be63c07…`、G1 `66a2c506be07…`。独立从原生G1字节和实际payload在内存逆向还原base，再正向还原gold/G1；得到的三份SHA与实际拟合输出一致，未执行补丁或候选。

最后仅原生导出G1单模块修改，decoded字节SHA `66a2c506be07…` 与实际加载源码一致；baseline canonical digest `40d1ef1ecc07…`、FrozenPatch digest `46eb6600aa58…` 独立重算相符。render1397字节、SHA `91c79e900583…`，内存逐hunk还原也等于原生G1。baseline.tar本次未捕获，未做完整tar往返验收。

classification为projectable、unsafe=false，excluded_pathset_changed=true保留；不宣称所有工作树路径不变。这个最后G1是私有校准控制工件，没有模型候选或正式评分意义。

## 资源、清理及旧拒绝

原prelaunch实际inspect记录2CPU、4GiB、512pids、memoryswap=memory、无bind；实际cgroup2为CPU `200000 100000`、memory `4294967296`、swap `0`、pids `512`，agent网络探针拒绝指定禁止入口及直接upstream。这里只证明启动前快照，不能推广为全程资源观测。

原attempt/summary确认actor删除成功、containers/networks无残留、cleanup failure空；gateway revoked/drained、active_requests0，两个endpoint stopped rc均0。清理属于该已完成旧校准attempt，不借给最终R9作业。

更早完整配方 `caa2db015bcc…` 的attempt在consumer构造任务面前因当时recipe未批准被拒绝：原attempt stages空、PreparedTasksError、无CC工具、拟合或正式评分，清理残留为空，端点停止。它不计完成校准样本，也不是模型或题目测试失败。不能用builder完整性通过替代consumer批准。

## 可复用范围与待补项

实际旧输入只有r2e-mr-020，image `481eb85bc5e4…`、完整env_v2 recipe `5122771965c2…`，没有sysconfig，未用新hidden092。当前固定R9元数据为020+092、full recipe `050316e44910…` / base `7e1710aebfb2…`、image `08470256e1bd…`；旧概率结果只能作为历史校准依据，不能单独核销这个最终组合环境。

旧host reference与最终绑定的expected SHA `cd034086c160…` 一致，13键含两个既有expected FAILED：`test_learner_scorer` 和 `test_learner_scorer_multiclass`。后续验收应逐状态匹配13键，成功不等于全pytest通过；pytest rc非0也不能单独判infra。

[已封public brief事实窄核](orange4014_9b_public_briefs_review_20261003.md)复用，9b brief SHA `33d7e34f091c…` 未变。公开test_probability实际是penalty=l1、iris前100行；它不同于这里默认L2/full150的校准。建议selector不能包装成已跑命令，新公开CC的base可出现1fail1pass和L1 fit ValueError，应读取完整工具结果、失败位置与源码身份，不能预设RC0，也不能据旧step ID `public_default_regression` 宣称全default回归。

下一阶段仍需最终十方原件和新公开CC原件，核完整reference、目标失败、预算、原生应用/加载、日志SHA、实际交付、资源与清理。当前窄核没有发现需要修改校准收据的事实错误；最终CPU报告将引用本报告另行完成。本阶段不持续轮询、不追加实验。
