# 5662／6283正式CPU验收

2026-10-03。新材料已随第七版 `cat2-cpu-r2e088-swe12-git-20261003-v1` 封包，外部manifest SHA为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。总协调已确认cpu-a／cpu-c只读部署，905成员及48 R2E／216 SWE可信读回通过。本包只在cpu-a运行，使用 `runtime_cpu_v2`，每题新job／prepared／FrozenPatch身份；已有公开actor与镜像证据按版本复用。

[固定输入](formal_inputs.json)引用已审修订单的原／新参考、完整有效补丁、各题E10安装资产、按题core与实际派生镜像。5662为2F／127P、core0.27.0；6283为2F／38P、core0.42.0。两题安装文本SHA相同也不合并镜像或安装资产。原公开题面、public_hints和vendor测试命令不变；其它四题尚未随此版登记。

| 题目 | 本轮正式矩阵 | 当前状态 |
| --- | --- | --- |
| 6283 | noop／gold／validate_construct，实际0／1／0 | 已收尾归档，[非作者CPU核查](../reviews/non_author_6283_cpu_review_20261003.md)通过，已提交普通GPU探针 |
| 5662 | noop／gold／any_only／all_nonmodels_equal，实际0／1／0／0 | R7作业 `pyd5662-formal-20261002203421-07d42` 已自然结束并归档，[非作者CPU核查](../reviews/non_author_5662_cpu_review_20261003.md)通过，固定普通GPU探针已发送 |

[执行脚本](run_formal.py)调用冻结的 `prepare_for_replay`、`ReplayGrader` 和 `SWEGradingManager`，不改registry／consumer／parser／评分算法或正式脚本。默认技术预算、2 CPU／4 GiB和原测试预算保留。每题一个作业、候选串行执行，本包最多占一槽；禁止run槽隐式拉镜像，遇基础设施异常或自动核对失败停止当前矩阵并保留原件。

准备阶段核905成员及每项输入SHA，现场重新生成受信prepared，并比较actor与host的七段脚本、hygiene、参考、安装及材料身份。两题本地只prepare检查已通过，未在本地运行Docker或题目测试。镜像复用前一轮已验证的8公开wheel派生ID，没有私有canary、gold或测试预置层。

每行保留候选导出、完整baseline、原始账本／报告／诊断／eval日志和Docker调用原件。逐ID核全部参考、原／新增分区、新节点实际状态、原始reward、安装失败命令、安装／测试退出及完整性；报告中的0分须来自普通行为断言，不能把安装、收集、超时、baseline或清理失败算成题目失败。

额外的源码/core观察在manager原post观察之后以同一候选用户执行，只记录UID54322、Python3.8、精确core、导入源码及SHA、官方测试恢复／不可写和真实cgroup限制。它不改正式spec或评分输入，不回写reward；其进程和输出另存。候选清理、grader关闭及本run容器／网络残留分别核对。

此前6283错误候选已被原不验证构造护栏拒绝，本轮保留该事实；新增非42目标不是发现新的漏奖。5662的any_only此前获得旧分1，本轮必须由普通matcher新节点拒绝。只在纯私有测试变化范围复用旧公开actor首消息与开发命令，不重做公开阅读。

6283原件与逐项核对见 [results.json](results.json)：三候选运行、安装、40项参考、源码/core、FrozenPatch／完整baseline运输和两层清理的自动检查均通过。作业退出0，候选删除、grader关闭及本run容器／网络残留查询均已收口。非作者已独立确认375原件、逐参考与运输；当前用途为普通GPU探针，尚无模型结果。非参考两节点的parser截断与baseline环境字段null分别保留范围限制，不能宣称全45节点解析完整或训练lineage验收。历史[暂停记录](../pause_checkpoint_20261003.md)不回写；当前状态见[准备入口](../preparation.md)和共享总账。

5662已独立核496份原件、129参考及完整288文件baseline；any_only的旧ANY通过、新普通matcher失败，旧漏奖被拒绝，四行均为普通行为结果。14个含空格非参考节点的同根因parser问题保留，不影响正式参考评分。固定单题快照及请求在各题目录，原始attempt的历史pending状态不回写；两题当前核查与提交状态另列在results的current_reviews／current_probe_submissions。
