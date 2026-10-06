# DataLad 088 非作者增量审查

2026-10-03。**PASS：088静态增量、新构建／prepared与正式CPU三方原件复核通过；实际raw为0／1／0，未发现新的题级阻断。** 支持题主以固定版本基座诊断（`versioned_baseline_diagnostic_only`）用途按现行流程交GPU执行者核接入与排队；本报告不授予训练／留出资格或formal gate通过。三份baseline的环境包lineage仍为null，这一既有边界在下文明确保留。本审查不是修订作者，但已接触私有测试、gold和对照；不是fresh公开盲读。只读本地原件并做文本、AST与摘要核对，没有SSH、重跑评分、模型或安装。

范围为 `r2e_gym_subset::datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb` 的065→088两项增量及其新CPU结果。独占检查原件保存在 `runs/category2_repair_20260929/r2e_datalad_088_independent_review/` 的 `static_audit.py`／`static_readback.json`、`build_audit.py`／`build_readback.json`、`matrix_audit.py`／`matrix_readback.json`；题主的readback是导航，结论由正式全文、冻结包、真实构建、prepared、ledger、eval log、FrozenPatch及driver原件重建。

## 静态材料与行为依据

对照[原公开读者](../../../../r2e_lifecycle_20260929/results/datalad__6b6fa3898546793fa3517def09f85a74d51ec4bb/public_read.md) §1.2 K7/K8，并直接读公开工作树的 `datalad/support/network.py`、`datalad/crawler/pipeline.py:453–487`：

- `/some/dir:x` 在原解析路径中没有 scheme 或 hostname，且不含 `@`、不以 `//` 开头，属于 `file:implicit`；hostname 会进入 netloc。新断言限定这条明确的绝对本地路径，不恢复065已移除的相对斜杠前缀SSH分类要求。
- 爬虫配置文档明确允许模板采用 URL 式 query，实际 `load_pipeline_from_config` 把模板交给 `parse_url_opts`。`openfmri_s3` 也是已有管线模块。该函数去掉 query／fragment 后用字段重建模板名，并用 `query_dict` 返回参数。因此新要求 `('openfmri_s3', {'_url': 's3://b/k'})` 检查调用方实际使用的输出，有公开依据。

直接核两份原补丁：C-A只在缺省 scheme／hostname 分支增加受前缀字符约束的冒号判断；`/` 或 `?` 在首冒号前时不改成SSH，所以保留上述两项。gold没有这个限制，会把绝对目录当hostname，并把query中冒号当SSH分隔符后触发原有query拒绝。历史真实行为原件 `pcheck_public4_CA.json`／`pcheck_public4_gold.json` 的SHA分别为 `10b036ece2092beb64b13d74fbdfcd243893d9a4c68847929080fc796dcbd4e7`／`53b2cd90f0673be30d61139c2586e2e31c820b8ed67340c790bef15d39b98147`；均实际apply成功，并记录相应file行为／SSH错误及ValueError。这是机制证据，不是088的新评分。

从065全文 `161f9d3b7bafc365932249ad934aa9f17ef12ff90d88b2ee7683605ccd05a3bd` 按草案两处替换得到088全文 `7649b82fb114a9bbdfa3a73148c4d8f1ee8bed926dd2d7853c6385379b88c8b6`。去掉新 `test_parse_url_opts` 的一个表达式和新 `test_url_samples` 的一个表达式后，整个AST与065相同。没有新增测试函数或删除原断言；直接字段helper和从字段重建要求均保留。

## 冻结版本与评分合同

独立回读R7外部manifest：release ID `cat2-cpu-r2e088-swe12-git-20261003-v1`，SHA `f9dfcd16c9c88e4f514512e61781856b7d6f1a71a20b64cd1843d20546c5009b`。905成员集合、逐文件大小和SHA全部匹配；verifier实际SHA为 `fc00b2c9fa46febf0cecc63dbc5edc5f578598ab31233b7e263bba8ca25d52c8`。registry v19及pins v20也按外部manifest核实，pins的各原件摘要逐项匹配。

本题活动修订仅088。原始来源全文 `74675cb6402869b01198b7dc63bac013eb440d988f6d953efe9188fe6e748cb9` 经登记的六处替换，逐字得到正式全文与题主增量全文；不存在叠加065与088的重复消费。隐藏树实际复算为 `2a62382c32a9def6a9ccf42c27fb938b7e4c0c0747805bafeaa605afce6b4724`。

expected原文、runner、`conftest.py` 和 `__init__.py` 与065及原快照逐字相同；expected无重复键，仍17键、16 PASSED＋`test_get_local_file_url_linux` FAILED，yield用例不在评分键中。expected SHA为 `15da45bafd393ca47e0f732decf3079f3fe8c55f43b58359ba4795095d6dccb9`，runner SHA为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`；正式ingest的文本、文件清单与树摘要逐项吻合。公开row与原快照完全相同；原1203字符prompt SHA为 `a0f4c92ea4cc56c9a07670100d75b30dfc828e7c82c6b671b1ba7e8cd38bf233`，开发说明SHA为 `68688ecf3f12e22de138e22f9ecaf28ff7d77fa7f7b8940e58d1c2a9ede888af`，均未变化。

## 新构建与公开证据复用边界

直接核 `r2e_datalad_k7k8_cpu_20261003/cpu_c_evidence/build/` 及 `jobs/.../datalad-6b6f-build-r088-c3/`：实际prepare作业finished／rc0、stderr空；build log实际执行新材料，打印树 `2a62382c…`、导出镜像并以 `[rc=0]` 结束。实际镜像为 `sha256:6cb609c6ef96764ae05e502b535a786aa30e45d594f971f604c881c1cbd2317a`。

实际context三个脚本与R7冻结脚本逐字相同。配方仍为 `r2e_derive_v1+material_v2+sysconfig_v1`，但摘要应更新：用实际 `recipe_v1.sh`、`material_v2.sh`、`manifest.tsv` 的摘要按规范JSON复算基础摘要 `3a878d23931236076c988ef1bd21e1637a4c63130f4619041c5b466b0274737a`；再与 `sysconfig_v1.sh` 摘要组合，得到 `0385a5051574bd15668ddcc8f3d105c74edcaceff6be4a4a942d6a4d8bde46b1`，与facts和overlay相同。它不是065的旧配方摘要。

新构建的来源／派生完整性原清单A（263行）、B（13849行）、C（72行）、D均逐行相同，并与065原清单对应段相同；新派生L/P也与065相同。源码 `network.py` 实际SHA仍 `a23b14c0194ef9fd947119f0c5ceb07cbfea0f13bbb35b331f22e02adb115702`。真实root与双UID facts保持Python可执行、私有目录拒读、隐藏测试不在工作树、Git历史清理；新材料只进入root私有测试树。

新prepared文件摘要与本次summary／manifest逐项吻合；prompt和rollout公开内容与065相同。environment package仅 `grading_bundle_digest` 变化，按规范JSON复算新digest为 `677b5a1a68e360630da23110acc63e7e019fe6ac752977ff96f9ccd1145873fe`，因此整份prepared不能称字节未变。host grading明确消费088及新隐藏树。

上述事实支持复用065真实CC的公开命令／开发条件证据，不要求机械重跑公开actor。复用不包括088模型成绩，也不代替未来GPU首请求的原题面＋开发说明交付核对；旧065的七评分成绩仍只属于旧版本。

## 正式CPU三方结果

原件根目录为 `runs/category2_repair_20260929/r2e_datalad_k7k8_cpu_20261003/cpu_c_evidence/`。直接从三份 `matrix/<候选>/eval_logs/*.eval.log` 的唯一真实Start／End Test Output段，独立解析PASSED／FAILED／ERROR；每份均恰好17键、无重复／缺失／额外键，XFAIL不进评分映射，再与冻结expected逐项比对。

| 候选 | 实际raw | 状态匹配 | 实际目标结果 |
| --- | ---: | ---: | --- |
| noop | 0 | 15/17 | 原例scheme仍是file，`is_url`为假；两个旧目标键失败 |
| C-A | 1 | 17/17 | 新旧全部约束匹配；唯一pytest失败仍是固定`~`兼容项 |
| gold | 0 | 15/17 | 新模板query在`test_1.py:99`触发URL解析ValueError；新绝对路径在`:229`由直接scheme字段断言拒绝SSH分类 |

gold的原trace确实经过 `parse_url_opts('openfmri_s3?_url=s3://b/k')`，异常字段为path=`openfmri_s3`、query=`_url=s3://b/k`；另一trace明确是 `_check_url('/some/dir:x', ...)` 的 `'ssh:implicit' != 'file:implicit'`。因此新增拒绝来自目标回归，不是应用、导入或基础设施失败。三方均保留实际 `file:///a~ != file:///a%7E` 与yield XFAIL，pytest rc均为1；C-A的17/17是精确状态匹配，不能写17个测试全通过。

三份ledger均只有attempt1、regrade0；正式入口固定R7、runtime_cpu_v2、repeat1及1200秒reset预算。setup原log实际打印新树、固定runner摘要、apply0及setup成功，测试段完整结束；新镜像／0385配方与build及overlay逐项相同。无stage_error、infra_failure、部分log或runner改写；UID54322、2CPU／4GiB、PID512、禁网保持。准备约43.4–45.1秒，记录测试段约2.8–3.2秒。

## 新baseline与FrozenPatch身份

按R7 contracts源码的canonical JSON规则独立重算，三份实际baseline digest均为 `4522e69313d6f00787d55b26119183a3a653be4597c8741e27001400e4c678a9`，与各FrozenPatch锚相同。实际baseline均246条初态entry，与065同候选原baseline的评分树逐项相同，但实际镜像已绑定新 `6cb609c6…`，完整新baseline摘要不与旧版混用。policy摘要复算吻合，公开bundle、HEAD／task base、workdir和镜像事实准确。

每份FrozenPatch canonical digest与原projection、ledger分别一致；新physical attempt ID各自唯一。C-A与gold的base64载荷解码后摘要吻合，而且整个entry（操作、路径、类型、mode、实际bytes）与各自065已验有效候选逐字相同；本次input patch与保存的 `candidate.patch` 逐字相同，SHA也与ledger相同。两候选均只改 `datalad/support/network.py`；noop为空entry，排除路径集合未变。这里只复用不变候选内容作交叉证据，未给旧FrozenPatch重绑新baseline。

需要保留一条精确限制：baseline的 `environment_package_digest` 三份实际均为null。R7 `replay_grade.py:388–392` 生成baseline时没有传该字段；`contracts/baseline_manifest.py:178–184` 明确禁止用其它digest伪填，并将尚未接通的环境包lineage称为formal gate blocker。本报告没有把它写成baseline内绑定了新env。当前新env `677b5a1a…` 是prepared／host grading的事实，新私有grading、088隐藏树、实际镜像与grader setup另行核实。现行普通探针规定按这些实际身份和原工件验接入；formal training／留出资格仍不能从本次CPU PASS推出。未改原件，也未将这一公共既有字段误计为gold的0分原因。

## 收尾与可追溯索引

三份候选清理均实际 `removed=true`／`rm:ok`；每份driver末条回执均grader容器1建1清、open／supply／cleanup_failures为空、final exit0。matrix槽作业 `datalad-6b6f-matrix-r088-c1` finished／rc0、stderr空。确认范围为这些登记的候选、grader和供给，不扩写为整个宿主不存在其它作业。

| 候选 | 原ledger SHA256 | 原eval log SHA256 | 重算FrozenPatch digest |
| --- | --- | --- | --- |
| noop | `98a8b31312ba2ef0ec3b3cbeca65826f4d0e5fb401b0960fda5ad4bd99dc75b0` | `24bf6897a3d17c5742ce72cc4ad68cae60c0a65cfb86bf9f31138a37e76fe9e0` | `ee26702b037861b1d3a591a20137996d3011c7177e41c5f851b526ac0bce15b8` |
| C-A | `0cb7748d7ebb56c00d3619c292414714861ee34ec27c37319859f58ee671a4ea` | `0c6ba2d029627770b2c90ebf0f5cd00c8e34c9d8622f63cca60bcc476ee708cc` | `a3fbf4e27f260a8a087868d9350043c13a3c8dde59e9fdffe7ad217b61897634` |
| gold | `a103e8d9cba05a8516d96fe160171c57dc20a0e6bd48d7d00032ebf5f97a2a4c` | `29af8e5e2e1b83e603efd67736fc95a5d632ebcafc11d9f03c7dfc19b8c85b58` | `d189f56449830ae1b32ed58a4634e6ab684703c17b7923884c4b48673371ae41` |

独立检查索引SHA：static为 `917579e3c3b4ba08cf3d63cfd61bf967ed43ae0c7d70efa83cbc09378bcfb80e`，build为 `80906323d6a577cd97af416e4a889cb4473c63a095c6323364a492159849d8ed`，matrix为 `305d2ee99d41e46835324cd1a4590ec99936e57a406f3b891fb3f1b14dc9c989`。新GPU模型尚未由本审查运行；旧065的原GPU输入、CPU报告与历史成绩保持原样。GPU排队、安全取消旧请求、实际首次交付及各模型候选语义分析由题主与执行者按现行流程接续。
