# DataLad 088：增量 CPU 验收

2026-10-03。**新材料三组对照各一次，实际评分为 noop=0、C-A=1、gold=0；原件回读及非作者最终结果复核通过。** C-A仍满足题目要求，gold的两项已知公开行为回归现在能被评分拒绝。没有重跑旧065七组矩阵，也没有运行真实基座模型。

这是固定版本的题目材料／CPU对照证据，尚不授予训练或留出资格。既有CPU replay的 `baseline.environment_package_digest` 及ledger材料身份字段为null；冻结contract明确把未接通的环境血缘列为formal gate blocker，不能把本次对照通过称为完整formal准入。公开／隐藏材料在prepared、实际构建私有树及评分日志中另有绑定；原件没有补写null，GPU实际链路仍由执行者核定。

## 对照结果与目标失败

| 候选 | raw reward | 期望状态匹配 | 原日志的实际结果 |
| --- | ---: | ---: | --- |
| noop | 0 | 15/17 | 原题示例仍为file:implicit，is_url为假 |
| C-A | 1 | 17/17 | 原目标、字段重建及新增绝对路径／模板query全部满足 |
| gold | 0 | 15/17 | test_url_samples的绝对路径误为ssh:implicit；test_parse_url_opts的模板query实际抛ValueError |

题主直接从Start／End Test Output段独立解析PASSED／FAILED／ERROR，再与冻结expected逐键比较；每份恰好同一组17键，没有missing、extra或重复。固定 `test_get_local_file_url_linux` 仍FAILED，yield用例仍XFAIL且不产评分键。全部pytest rc1，因此C-A的17/17表示状态吻合，不是17项都PASSED。

gold原日志确实执行 `/some/dir:x`，报 `'ssh:implicit' != 'file:implicit'`；模板 `openfmri_s3?_url=s3://b/k` 进入原query拒绝分支并抛ValueError。两项负结果均来自行为断言，不是apply、安装、ImportError、运输或超时。完整逐候选摘要及原日志/ledger SHA见[题主评分回读](checks/cpu_matrix_owner_readback.json)。旧C-B／D-eq／D-eq-minus／D-hard只作为065未变机制证据，见[矩阵](acceptance_matrix.json)，不冒称088重新评分。

## 实际发布与构建身份

本轮实际使用R7 `cat2-cpu-r2e088-swe12-git-20261003-v1`（registry v19／pins v20），外部manifest SHA为 `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。本机905成员逐一回读，CPU-c verifier同时核905成员与48 R2E／216 SWE可信消费。有效test全文SHA为 `7649b82fb114a9bbdfa3a73148c4d8f1ee8bed926dd2d7853c6385379b88c8b6`，真实私有树为 `2a62382c32a9def6a9ccf42c27fb938b7e4c0c0747805bafeaa605afce6b4724`。

新build作业 `datalad-6b6f-build-r088-c3` 于CPU-c完成，rc0；此前c1／c2退出75未获槽，不是题目0分。实际镜像ID为 `sha256:6cb609c6ef96764ae05e502b535a786aa30e45d594f971f604c881c1cbd2317a`。配方ID仍 `r2e_derive_v1+material_v2+sysconfig_v1`，配方摘要包含088材料清单，独立规范JSON重算为 `0385a5051574bd15668ddcc8f3d105c74edcaceff6be4a4a942d6a4d8bde46b1`；不能沿用065旧摘要。

直接比较来源／派生完整性A/B/C/D原清单，263个源码等文件、13849个venv非bin文件、72个bin文件及Git初态逐行相同，也与065来源对应段相同。真实双UID facts确认解释器可用、私有目录拒读，test全文仅在root私有树。公开row与prompt同065；新environment package因grading bundle更新为 `677b5a1a68e360630da23110acc63e7e019fe6ac752977ff96f9ccd1145873fe`，整份prepared并非旧文件原样复用。见[构建原件回读](checks/cpu_build_owner_readback.json)。

## 原工件与清理

三份新baseline canonical digest均独立重算为 `4522e69313d6f00787d55b26119183a3a653be4597c8741e27001400e4c678a9`，与各自原FrozenPatch锚一致，且与旧065不同。新FrozenPatch及投影摘要重算吻合；实际image／public／head绑定正确。C-A与gold的原输入、candidate.patch、ledger摘要一致，以agent/54321应用，只投影network.py；冻结后的实际源文字节与065同候选相同。noop为空工件。没有改绑旧baseline或FrozenPatch，详情见[工件身份回读](checks/cpu_artifact_owner_readback.json)。

三次driver exit0、stage_error和infra详情为空，regrade_total=0；候选removed=true，grader／manager容器与供给全部闭合。matrix作业 `datalad-6b6f-matrix-r088-c1` finished／rc0，使用统一runtime_cpu_v2及run槽，候选串行各一次。实际评分profile为UID54322、2 CPU／4GiB／PID512、禁网；env reset预算1200秒，准备约43.4–45.1秒，测试约3.4–4.0秒。

原件根为 `runs/category2_repair_20260929/r2e_datalad_k7k8_cpu_20261003/cpu_c_evidence/`，包含build／prepared／private／matrix及两个job回执。从远端分别归档，传输后核SHA再安全解包：build 29成员、SHA `855ebc0f0dbbd0b5031bfc8afc5531280e83ccadeb0e9768ce78437b8de9b8a1`；matrix 53成员、SHA `e27347fc496f1e3073fe21c1b05891fe0f4e15d60fe0cc1e149907eba38652b9`。

## 公开证据及后续

构建确认公开源码、依赖、题面及中性说明未变，因此复用065真实CC的公开命令、身份预检与原1203字符prompt交付证据；不机械重跑公开actor。旧首次缺torch的零请求infra原件保留，不改作0分。CPU桩既不是模型修复，也不能代替未来GPU首请求核原题面＋中性说明。

[非作者增量核查](independent_review_20261003.md)已独立核完静态材料、实际构建／prepared、三方17键／新工件身份及清理并通过；已接触私有材料，不是fresh公开盲审。其结论限本版CPU材料验收与诊断用途，formal gate限制保留。接下来先登记取消旧065请求，由GPU确认无在途及安全结束，题主核收并清活动指针，再提交088新固定请求。原065输入与报告保持原样。同仓另四题含答案关联、重复／整仓划分和实际GPU输入尚未核的限制继续保留。
