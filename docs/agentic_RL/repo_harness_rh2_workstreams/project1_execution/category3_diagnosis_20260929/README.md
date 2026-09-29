# 第3类题目：具体诊断与验收范围核定

更新：2026-09-29。负责人：Claude（云端会话）。分支：`claude/category3-20260929`（用户 09-29 选定独立分支，交付后由本地挑选或合并）。

## 范围与分工

本目录负责 [120题分类 v2](../task120_status_20260929/README.md) 中的**第3类 67 题：SWE 41、R2E 26**。起始名单见 [fork_worklists.json](../task120_status_20260929/fork_worklists.json) 的 `groups.3`。第1、2类由本地 Codex 线程负责；本目录不修改它们的文件、共享快照、题卡或 HTML，只在本目录和 `rh2/experiments/category3_cloud_20260929/` 下写入。

四种缺口与交付要求如下：

| 缺口 | 题数 | 交付 |
| --- | ---: | --- |
| 公开目标与验收关系需核定 | 22 | 找公开依据，明确哪些要求成立、测试应如何调整；只有真正无法消解的目标选择才交用户 |
| 已有具体疑点，缺辨别实验 | 25 | 执行已设计的对照；确认问题后给出修法，疑点消除时说明依据 |
| 参考修复不可靠，缺正确对照 | 4 | 找到满足公开要求、保留相关旧行为的正确实现，再校准测试 |
| 题目质量调查未完成 | 16 | 在已有材料基础上继续，不重做已完成的环境恢复 |

每题最终落到三种结论之一：

- 疑点已消除，可申请转第1类；
- 问题和修法已明确，转第2类并交接；
- 仍有具体问题，写明缺什么证据、下一条命令或需要谁决定。

规则按[统一标准 v1](../task_screening_standard_v1_20260925.md)执行。v1 已授权的 R-a 至 R-f 修订模板，本目录只起草并做诊断验证；正式修订版本由第2类线程经 D6 入口落地。

## 运行条件

云端机器可以完成真实正式评分链，详见 [environment.md](environment.md)。要点：

- 4 CPU／15 GiB；
- Docker 29.3.1、overlay2；
- 镜像经 `mirror.gcr.io` 按原名拉取，摘要与冻结值一致；
- 派生配方在本机重建并核对 wheel 摘要；
- conan-14177 的 noop 0／gold 1 与 09-19 历史逐项复现。

限制：TCP 22 不通，无法 SSH 到外部机器；盘上只能同时存放约 9 张镜像。重型题（pandas 重编译、MONAI 长测试）需排队，或另行安排。

## 首批试点（8 题，校准判断与证据质量后再扩量）

题目按四种缺口与两个来源选取，并优先选能在云端完整取证的题。8 题的结论如下：

- 8 题均转第2类。其中 coveragepy__5dbbe143 原本待用户决定（P5），用户 09-29 选定 A（按 slug）；
- dvc-9395 经两轮复核改为 v4；同一题连续两轮出现新阻断，触及协作协议的修复循环熔断，按最小充分原则收口，交 Codex 确认。

pillow 首轮的结论是“可转第1类”，被独立复核推翻，改判为转第2类。

| 题目 | 缺口 | 结论 | 要点 | 复核 |
| --- | --- | --- | --- | --- |
| [SWE conan-14177](tasks/conan-io__conan-14177/result.md) | 公开目标核定 | **转第2类** | P2/T1＋T2b：按题面实现的修法得 0，只打印不应用补丁的退化候选得 1。修订 v2 以替代正对照 `pubcand` 验收，15 个候选的诊断评分符合预期 | 复核＋v2 聚焦复核，无阻断 |
| [SWE moto-7584](tasks/getmoto__moto-7584/result.md) | 辨别实验 | **转第2类** | gold 未修题面原例；报错正文超出题面模板导致误拒；两类退化候选得 1。修订 v3 以 `stmt` 作正对照，11 个候选的正式诊断评分符合预期 | 复核＋v2 聚焦复核，无阻断 |
| [SWE dask-9378](tasks/dask__dask-9378/result.md) | 辨别实验 | **转第2类** | 只错 mask 的退化候选得 1。R-c 逐元素比较 mask；“只修顶层”的设计按 P5 第一分支走 R-f，补一句 | 同意，无阻断 |
| [SWE pydantic-9066](tasks/pydantic__pydantic-9066/result.md) | 缺正确对照 | **转第2类** | 替代正对照 `fallback` 与上游式 `upstream271` 在原材料和修订版上都是 1，gold 在修订版上为 0 | 同意，无阻断 |
| [SWE dvc-9395](tasks/iterative__dvc-9395/result.md) | 辨别实验 | **转第2类** | T1：计数断言误拒；N1：“吞掉错误”的退化候选在原测试得 1；N2：用户改过的数据源在 `--pull` 下被覆盖或报错（S1）；N7：只测了 `dvc add` 数据源，补 `dvc import`。R-b＋R-c v4 下 16 个候选中 3 个为 1，gold 等 13 个为 0；正对照改为 `c3_frozenfix`，第二正对照为上游 3.51 移植版。只有私有模拟 | 两轮复核共 4 项阻断，已按 v4 处理；触及熔断，v4 交 Codex 确认 |
| [R2E pillow__3a61c9e9](tasks/pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07/result.md) | 辨别实验 | **转第2类**（首轮“可转第1类”被推翻） | N1：RGBA 调色板加整数透明索引时，gold 的 `remap_palette` 抛 `ValueError`，上游 11.0 才修好，判 S1。R-c v2 新增一键，14 个候选中 6 个合理实现为 1，noop、gold 与 6 个错误候选为 0；正对照改为 C1，上游式 U11 作第二正对照 | 复核不同意首轮，已改判；v2 聚焦复核 1 项阻断（G_small），已按其补法修为 R-c v2 |
| [R2E coveragepy__5dbbe143](tasks/coveragepy__5dbbe1430c16fe15b553e6909be8be5f2b9b71b9/result.md) | 公开目标核定（P5） | **转第2类**（用户 09-29 选定 A） | 按 slug 识别警告：R-f 题面补一句，隐藏测试沿用材料 v5。私有核对：gold、CE3 为 1，CE1、CE4、noop 为 0 | P5 沿用多方已有判定；修订题面已通过新公开读者验收 |
| [R2E coveragepy__016af5f6](tasks/coveragepy__016af5f6352d69206ac8f7537c2b18828767bcae/result.md) | 质量调查 | **转第2类** | P4：题面原例不复现，走 R-f。原测试下 6 个错误候选得 1。R-c v2 下 6 个合理实现得 1，noop 与 7 个错误候选得 0 | 复核部分同意，B1 已按 v2 处理；v2 聚焦复核无阻断 |

独立复核：每题由不继承本会话上下文的新子代理进行，先读原件形成初判，再核对本目录的结论，只针对关键判断寻找反证（v1 §7.3）。复核发现阻断项时，主审修改后再请同一复核者做聚焦复核。

**证据层级**：
- conan、moto、dask、pydantic 的分数来自正式评分链；其中修订版为 `--materials` 诊断评分，尚未经 D6 入库。
- dvc、pillow、coveragepy 的分数是私有模拟（见 [environment.md](environment.md) §3）。
- 所有修订都只是草案，正式版本由第2类经 D6 或 R2E 材料修订机制落地。

### 交给第2类时需要的落地能力

| 题目 | 落地方式 | 云端缺的条件 |
| --- | --- | --- |
| conan-14177 | D6 测试补丁替换，并把 `test_single_patch_description` 从 F2P 移到 P2P（首片以外的两项能力） | — |
| moto-7584 | D6 测试补丁替换 | — |
| dask-9378 | D6 测试补丁替换＋`statement_replace` | — |
| pydantic-9066 | D6 测试补丁替换（或新增 P2P） | 派生镜像为等效重建，入库时应固定 wheel 清单 |
| dvc-9395 | D6 测试补丁替换 | dvc_tail_v1 的 compat-wheels，需在本地正式复验 |
| pillow__3a61c9e9 | R2E `hidden_test_text_replace`＋`expected_file_replace`，接在 v5 之后 | 需用正式评分过的原 C1 补丁复验，它只在本地 `runs/` 中 |
| coveragepy__016af5f6 | R2E `hidden_test_text_replace`＋`statement_text_replace` | 需新公开读者验收修订题面 |

## 第二批（进行中，09-29 起）

用户授权由负责人选题。第二批从 README 下一批建议中选出 10 题，全部可在云端完成主要取证：
- 8 道 SWE 题可走正式评分链；
- 2 道 R2E 题做私有模拟。

作者诊断由子代理并行完成，统一要求见 [batch2_author_brief.md](batch2_author_brief.md)；每题再由不继承上下文的独立复核把关。

| 波次 | 题目 | 缺口 | 评分条件 |
| --- | --- | --- | --- |
| 1 | SWE dask-8801 | 辨别实验（同义措辞是否被误拒） | 直接评分 |
| 1 | SWE conan-13403 | 辨别实验（cwd、命令与恢复） | 直接评分 |
| 1 | SWE pydantic-8567 | 缺正确对照 | pydantic_v1 等效派生镜像 |
| 2 | SWE dask-7305 | 辨别实验（大整数分位点） | 直接评分 |
| 2 | SWE moto-6185 | 辨别实验（合法嵌套值） | install_wave1 重建 |
| 2 | SWE pydantic-8316 | 辨别实验（alias 与数字边界） | pydantic_v1 等效派生镜像 |
| 3 | SWE dask-8597 | 辨别实验（split 部分修复） | compat_v1 重建 |
| 3 | SWE dask-9212 | 辨别实验（pure delayed 的 token） | compat_v2b 重建 |
| 3 | R2E coveragepy__f5eb5f21 | 公开目标核定 | 私有模拟 |
| 3 | R2E pillow__a682ceaf | 质量调查未完成 | 私有模拟 |

## 试点校准（供下一批使用）

**复核发现问题的频率**：7 题做了独立复核（coveragepy__5dbbe143 沿用已有的 P5 判定，未另复核），其中 5 题首轮复核有阻断项：conan、moto、pillow、coveragepy016、dvc。修订后的聚焦复核又在 pillow（1 项）和 dvc（2 项）上发现新问题。主审单独下的结论大约一半需要返工，所以独立复核必须保留。dvc 连续两轮出现新阻断，触及修复循环熔断，最后按最小充分原则收口。

**最常见的漏洞：修订测试仍放过错误候选。** 本批每一处都是复核者另造候选才找到的：

| 题目 | 放过修订测试的错误候选 |
| --- | --- |
| pillow | G_small：受调色板大小限制 |
| dvc（v2） | `w_gold_catch`、`w_gold_swallow`：只在交互路径覆盖用户修改；`w_mine_swallow`：拿不到数据仍报告成功 |
| coveragepy016 | `wr_swallow_flush`、`wr_loop_abort`：吞掉错误 |
| dvc | `w_swallow`、`w_swallow3`：吞掉错误 |

以后主审自己的候选集默认至少覆盖以下几类：
- 吞掉错误、抑制症状；
- 与大小或阈值有关的部分修复；
- 依赖执行顺序的写法；
- 只覆盖编码子集的写法，例如按 Latin-1 判断；
- 只处理示例字面值的写法。

**第二常见：行为矩阵覆盖面太窄。**
- pillow 首轮只测了一类输入，漏掉了函数自己明确处理的 `transparency` 属性；
- dvc 首轮漏掉了“数据已存在但被修改”这种状态。

以后矩阵要覆盖三类情况：函数显式处理的相邻属性、超过阈值的规模、数据存在／缺失／被修改三种状态。

**低成本而有效的证据：上游版本对照。** 用 PyPI 发布包对照上游后来的写法：
- pillow：11.0.0 修好了 N1；
- pydantic：2.7.1 的 `_type_has_config`；
- dvc：3.51.0 改成只拉取缺失数据。

这类对照能快速判断 gold 缺陷是否真实，并提供上游式正对照。它只作佐证，不能当公开依据。

**云端条件**：
- 正式评分链在 conan、moto、dask、pydantic 上可用；
- dvc_tail_v1 与 R2E 派生镜像在云端没有重建，这三题只有私有模拟；
- 盘上约能放 9 张镜像，按摘要拉取的镜像要打标签（见 environment.md）。

## 下一批建议（未决定，供用户与协调者选择）

剩余 59 题的分布：
- SWE：诊断 20、范围 14、正对照 2；
- R2E：未审 15、范围 6、诊断 1、正对照 1。

建议下一批 8–10 题，优先选云端正式评分链可用、镜像不大的题：
- SWE 诊断：dask-8597、dask-8801、dask-7305、dask-9212、moto-6185、conan-13403、pydantic-8316；
- SWE 正对照：pydantic-8567；
- R2E：coveragepy__f5eb5f21（范围题，已有窄 R-b 草案），pillow__a682ceaf 或 scrapy__cfed9b66（未审题）。

下列重型题宜在更大的机器上由本地线程处理：
- pandas：SWE 3 题、R2E 6 题，需要重编译；
- MONAI 3 题：测试时间长；
- numpy 2 题：需要 /tmp 6 GiB、内存 12 GiB 的配方；
- datalad 4 题：需要 git 身份与专门配置。

本容器无法 SSH 出网，租用机器需由本地会话使用。

## 记录

| 时间 | 事项 |
| --- | --- |
| 09-29 | 云端环境核对：Docker 守护进程可启动；Docker Hub 限流后改用镜像源；存储后端切为 overlay2；rh2 评分依赖安装；conan-14177 正式 noop／gold 复现历史 |
| 09-29 | 用户选定独立分支 `claude/category3-20260929`。若需要更多 CPU 可租机，但本容器无法 SSH 出网，首批暂不需要 |
| 09-29 | conan-14177、moto-7584 完成作者实验（私有对照、原材料正式评分、修订草案诊断评分），证据已归档 |
| 09-29 | 8 题主审完成；conan、moto、dask、pydantic 复核无阻断（conan、moto 经 v2 聚焦复核） |
| 09-29 | pillow 独立复核推翻首轮“可转第1类”：发现 gold 的 N1（透明索引下抛 `ValueError`），并证明 I5 有可见后果。已亲自复现，并对照上游 9.2.0–11.0.0，改判 S1，起草 R-c v1 |
| 09-29 | coveragepy016 复核阻断项 B1：吞错类候选在 v1 下得 1。改为 v2，14 个候选私有评分符合预期 |
| 09-29 | pydantic 按复核建议补跑上游式第二正对照 `upstream271`：正式链原材料 1、修订版 1 |
| 09-29 | dvc-9395 聚焦复核又有 2 项阻断：交互路径未保护；正对照的范围不清。已改为 v4：采纳复核的 v3 断言，补 `dvc import` 非示例实例，冻结命令 stage 登记 T3；正对照改为 `c3_frozenfix`，第二正对照为 `up351_port`。触及熔断，交 Codex 确认 |
| 09-29 | 用户选定 coveragepy__5dbbe143 按 A（按 slug）处理，并授权按负责人选题推进第二批 |
| 09-29 | 云端教训：`docker image prune` 曾删掉按摘要拉取、未打标签、复核者正在使用的镜像。之后按摘要拉取的镜像一律打 `c3keep/*` 标签，复核进行期间不做 prune（见 environment.md §1） |
