# DVC9395 两模型首轮分析

2026-10-04。材料R20与固定首轮请求不变。本次分析复用已验收的Coder原轨迹及同原FP CPU补评分，新增Qwen首次轨迹／评分读回；没有新增求解、重评分或CPU矩阵。

**两份首次候选均未完成本题契约。** Qwen是部分修复，恢复了普通source和新增frozen场景，但漏仓库导入／远端run-cache，且在源码已修改、没有缺失时强制请求远端。Coder恢复位于缺失检查之后，缺失时不可达；helper也没有新增远端拉取。两者失败模式不同，不能用相同的0概括轨迹质量。

| 结果与范围 | Coder 首次候选 | Qwen 首次候选 |
| --- | --- | --- |
| 原GPU reward／入口／cleanup | null／1／false，求解completed，评分前relay删除超时 | 0／0／true，求解及评分完成 |
| 补充评分 | 同原FP CPU一次评分0；原GPU null保持 | 本轮GPU原评分0，无补评 |
| 正式40参考 | CPU F0/3、P37/37 | GPU F1/3、P36/37 |
| 实际41节点 | CPU37通过／4失败 | GPU37通过／4失败 |
| 未评分原import节点 | 失败 | 失败 |
| 完整FP／评分投影 | 原FP3项：stage＋2根目录脚本；CPU投影包含3项 | 原FP3项：stage＋command帮助＋追加测试；GPU投影仅2源码 |
| solve／独立grading秒 | 215.507／CPU246.473，原GPU未启动grader | 260.000／GPU268.066 |
| 工具／gateway请求／CC回合 | 44／45／45 | 88／88／89 |
| 累计输入／输出token | 779757／6657 | 3068590／16725 |

F是原失败应修复，P是应保持通过；正式引用与实际节点分开。Qwen多通过一个frozen F，同时多失败一个modified-source P，所以两者actual37／4相同不表示通过同一节点。官方parser42项含captured ERROR伪条目，不是41测试之外又执行了一项。

## 候选与七维对照

1. **根因与修法。** 两者都读到data-source／frozen分支缺恢复。Coder先检查缺失，Qwen先恢复；Qwen加入真实cloud.pull和checkout，但用get_used_objs漏repo_import、不获取远端run-cache，并未先筛缺失输出。Qwen复合source F在普通恢复及有远端的modified保护之后、仓库导入子段失败，不能写成普通source恢复全部失败。新增frozen F通过不意味着所有目标已修。
2. **定位与纠偏。** Coder未纠正顺序／远程能力核心错误，只扩异常捕获。Qwen真实复现暴露不存在导入，修正后普通恢复成功；后来仅修追加测试的目标与对象identity断言，业务边界未继续纠正。传输时间是可观测边界，不是内部推理时长。
3. **工具。** Coder两个脚本只看helper存在或吞异常；后台测试stopped和BrokenPipe不给完整回归。Qwen29Read／8Edit文本回放等于最终FP，真实remote、push、删除缓存、repro及内容观察更充分。is_error只标1个，正文另有命令／恢复／追加测试失败；不能把未标错误当成功。
4. **可观察并行。** Coder每请求单工具，后台验证未有效回收。Qwen首请求产生2工具，最后请求纯总结，缺工具精确开始／结束，不能断言物理并行。可以批量源码读取；复用同临时仓库的实验要顺序或隔离。单次成本不足以建立稳定并行收益。
5. **自测与最终陈述。** Coderhasattr不能证明恢复，最终远端拉取声明与候选不符。Qwen最终五组公开测试193项（含追加2）有完成摘要，真实普通source正例及非pull反例成立；但未测repo_import、远端run-cache、modified无远端和frozen边界，完成全部missing修复的判断过宽。对象identity改addressing保留恢复内容断言，不能按删除断言弱化测试描述。最后CLI过滤器抹掉repro输出，内容观察仍有效，退出码未单独确认。
6. **效率／资源。** 两次solve、grading、token与测试时间分别记录。Qwen更多真实测试，Coder主要后台等待但结果stopped；差异不足以给模型稳定速度／能力排名。有限资源样本不等于全程峰值；两个baseline环境lineage null、配额配置与强制生效不同。Coder下载声明28／列出25（16权重），Qwen声明40／列出37（26权重），未重哈希权重或证明GPU内存身份。
7. **结束原因。** Coder原求解正常、原GPU评分前infra失败保持；同原FP CPU补分0有独立执行／清理核收，不是新模型样本。Qwensolve正常、UID预检／安装0／测试1、原FP封存与两层清理完整，是有效行为失败。旧GPUrelay超时根因没有由本次成功评分证明修好。

## 证据与研究用途

[Qwen题主审计](tasks/iterative__dvc-9395/qwen36_a1_semantic_audit_v1.md)、[完整读回](tasks/iterative__dvc-9395/qwen36_a1_owner_evidence_readback_v1.json)及[非作者执行报告](reviews/non_author_dvc9395_pair_execution_review_20261004_v1.md)为新臂证据。[Coder原题主审计](tasks/iterative__dvc-9395/coder_a1_semantic_audit_v1.md)、[原非作者语义报告](reviews/non_author_dvc_three_coder_a1_semantic_review_20261003.md)、[同原FP CPU评分验收](tasks/iterative__dvc-9395/coder_a1_same_original_fp_cpu_grade_acceptance_v1.json)按固定原身份复用；历史pending/null不回写。新[非作者Qwen配对语义报告](reviews/non_author_dvc9395_qwen_pair_semantic_review_20261004_v1.md)和[配对核收](tasks/iterative__dvc-9395/two_model_first_round_acceptance_v1.json)作为后续收口入口，未以本报告写出时间提前宣布核收。

双模型总回执原文件SHA256 `eed35d58c543a7ef411042cbe310b4d5553034658ccbf75166354e6f53bbfe4c`，原Qwen执行回执SHA256 `55f1bfda379232313c6c187af4926d791ad95ec1514542f3c2b8604118ca29fe`。探针线程回告曾误写P37/37；更正原件 `runs/ordinary_gpu_probe_20261002/migration_20261003/dvc9395_Qwen_P2P_summary_correction_v1.json`保留旧摘要并以官方工具更正看板，评分原件始终P fail1/37。不将摘要纠正变成重跑理由。

当前材料无需因有效0放宽。训练信号候选可分别提取“先检查致恢复不可达／误称本地checkout可远端取回”与“真实局部恢复后的范围／非缺失边界漏修”。基于各一次求解不能判定稳定成功率、题目已饱和或最终训练／留出资格。覆盖优先，普通追加采样暂缓；必要的新实验应绑定明确的新问题和版本，而不是机械凑三次。
