# DVC5839：非作者材料窄核

2026-10-03。**静态材料可接受，无新增阻塞 finding；私有CPU诊断支持新断言有区分力。** 本次不是fresh公开阅读、正式评分、镜像或训练／留出资格验收。原版固定8的正式成绩与新三方正式矩阵仍待冻结release后执行。

审查身份：已读私有材料的非作者。只做文本／JSON／SHA256／AST与内存补丁重放，没有运行项目、维护测试、SSH、容器、安装或下载。唯一新写文件为本报告，排他创建。

## 审查身份与范围

- [revision.json](../tasks/iterative__dvc-5839/revision.json)：`sha256:997b8d38d0a629bd386273dfa629088ce3ad86112e114dbc0dacb55d751236f1`。
- [cpu_diagnostics_v1.json](../tasks/iterative__dvc-5839/cpu_diagnostics_v1.json)：`sha256:7784148e77ff97128649ea787f66c40fe17ec4b21f46c1b8b6a5d3a697e8b1ea`。
- [effective_install_recipe.json](../tasks/iterative__dvc-5839/effective_install_recipe.json)：`sha256:ab738019fde666e136372f382b5b2ab169747425b575db15de8c89bba750046f`。
- 有效测试补丁：`sha256:1acc81a67bca0511b78f515d0d777a00ceeca3725b7907ee741764d1e623540f`；父基线文件与原补丁摘要均吻合提案。

## 结论依据

公开题面要求metrics show的precision参数生效；科学记法如何解释曾是原题疑问。精确base `dvc/command/metrics.py:251–258` 的公开CLI help明确小数点后n位、默认5，旧公开helper测试已有舍入行为。因此新增默认5／非示例3／8／Markdown8的数值断言有公开依据，未改为有效数字，未新增标量float、负精度或其它输出协议要求。

[新增测试](../templates/dvc5839_tests.py)从真实YAML读数，经 `parse_args()` → `CmdMetricsShow.run()` 检查日志表格数值，没有mock格式化helper，也没有固定传参代码或表格空格。普通小数用于区分默认、3和8位；小科学记法值沿原题输入检查。对基线分别重放原／有效测试补丁后，原全部函数／类AST不变，只新增 `test_metrics_show_precision_real_values`。原1 F2P＋21 P2P保留，新版本为2 F2P＋21 P2P；selector仍是原测试文件。

独立读取诊断根 `runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc5839-diagnostic-v1-001/` 的summary及六份完整pytest.log，重建每行逐节点状态：原版noop原F2P失败、gold／固定8全部22节点通过；新版noop两F2P失败、gold全部23节点通过、固定8只有新增F2P失败。每行键集与对应22／23参考恰好一致，21 P2P均PASSED，无missing/extra。固定8失败堆栈明确在默认配置比较 `[0.12345679, 1.483e-05]` 与 `[0.12346, 1e-05]`，确实检验“固定8覆盖默认5”的目标，未把导入或收集失败当作错解被拒。

原始summary实际SHA为诊断登记的 `sha256:d40c28e14bf45ce13322bb53ce951761177a79f4f7d9f7f88453fd17e0326118`，status为`diagnostics_completed_not_qualified`、remaining_containers为空。这里核的是已有原件，没有在本轮运行诊断；未重审全部资源／安装／候选导出／actor生命周期。不得把原版固定8私测全过写成正式reward1，或把新版诊断0／1／0写成正式成绩。

安装配方的父E13文件SHA与记录一致；`revised_install` 精确等于原安装段开头加 `python -m pip install --no-deps pathspec==0.8.1 || return $?`，其余extras及原install_rc返回保持不变。pin失败会返回非零，未由后续安装成功掩盖。正式环境仍须在actor／grader两侧实际落实该配方并核导入版本，不能用旧无显式pin的recipe冒称已交付一致环境。

## 交接与停止条件

本轮限定材料窄核完成。正式发布者需绑定新有效补丁、F2P、基线保护、安装配方和固定release；新三方正式评分核逐ID、失败归因及清理，另完成actor公开交付。本报告不修改作者材料、诊断记录或正式pins；其它DVC题另存报告，不要求因本次窄核重跑历史全部候选。
