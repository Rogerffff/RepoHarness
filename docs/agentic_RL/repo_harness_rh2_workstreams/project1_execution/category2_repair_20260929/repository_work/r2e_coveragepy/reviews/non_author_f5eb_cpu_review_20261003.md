# coveragepy f5eb：非作者 CPU 窄核

2026-10-03。**结论：通过。固定 R6、正式 076/077、最终 rb3h 的本题材料满足带版本标注的普通基座探针 CPU 条件，未发现具体阻断。** 不授予训练资格，也不将本版结果记为未注明修订的原 benchmark 成绩。

身份：非作者 Codex subagent `/root/coveragepy_f5eb_cpu_review`（按派发要求 GPT-6.1 Sol/high）。已读本题私有测试、候选与旧独立审查，**不是 fresh 公开读者**。依现行三方流程复用既有采用版语义审查与同版共享验证，不重启用户已选 A、每文件 summary 边界或角色链。本轮仅本地原件读取、SHA/size、JSON/AST、固定 parser 纯函数与文本内存重放；未 SSH、Docker、项目测试、新 CPU 或模型实验。只写本 Markdown 与同名 JSON。

## 固定版本与消费身份

release 为 `cat2-cpu-r2e080087-swe8-git-20261003-v1`，根为 `runs/category2_repair_20260929/releases_20261003/r2e_080_087_swe8_git_candidate_v1`。manifest 实算 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`。855 成员全验、共享 Git/builder 的有效同版证据复用 [016a CPU 核查](non_author_016a_cpu_review_20261003.md)；这里独立核本题目标行、文件 SHA、实际消费与镜像身份，不以其他题私有方案判断语义。

固定 pins 的 registry/raw/rule source/image facts/source revision 文件 SHA 实核；registry 仅有本题 076/077，无 053/054 叠加。076 old 与旧原始 test_1_v0.py 逐字相同，before SHA 正确；new、正式文件、本题材料与旧复核 test_1_rb3h.py 逐字相同。077 原 expected 与固定 raw 相同，原 4 键保留，仅增 4 键。public/private 目标 bundle 的规范 JSON digest、prepared 文件与 replay_summary SHA 均独立重算一致。

| 身份 | SHA-256 |
| --- | --- |
| 原公开 statement | `6a516854b3c59b686b767267e0fe0a49d828934ccabd1a0e4b7159d9b883a88c` |
| 最终 test_1_rb3h.py | `fd4d6ac9ca8e1edbe148e30cc73a1f48c9a3eecb4ffbaef5a388dbd430de2050` |
| expected（8 键） | `e150a338879b6703fba4950e2f3eeb284ea415140a6f68c1c80cf085aca6e0d9` |
| hidden tree | `897dfdc70655175a1155dc7d8f6edd6e506b74f106e79e2a3dc4439dff8429af` |
| run_tests.sh | `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf` |
| public bundle | `2ee3739dacf33472e747c08ce4a907d574727eb1150acd71929871a2d5ece633` |
| grading bundle | `7c80b0e3cc847d888532f23a21a5654e2c5c28c208af8d40a3aa9deabfc2a012` |
| prepared_manifest | `0f8e89800b5678529c5ee852657fc6bff5c95143cb192086d958de8e1df3d79f` |
| host grading 文件 | `78b28860a8019d85dbc96c223eb3a90e79606511dcdc10e1d1482c5e8609c195` |
| derived image ID | `92b4d84d8c80c452cc586695a32cb01ff1b2b540cf98c2c12be73cb18d618d59` |
| recipe digest | `a2000320bdbd7e1808e5986592fdb448caa3929f78d55e29ab63021e16ec7900` |

base 为 `17204597c33db2cc396d32b8f9931c35f2518675`，source digest 为 `fb0335af8820e2f5cda1cc4ed82380546ed36fbd485da4181b8de9ef74b9ae28`。从 076 重建 material manifest.tsv，结合原 context 三脚本实算 base recipe `429ae2b1…` 及最终 `a2000320…`，与 facts/overlay 相同。原 build.log 显示固定来源、test_1.py 应用、897dfdc7…隐藏树及输出 image。integrity 的 368 工作树文件、2829 venv 非 bin 文件、47 bin 行和 Git 状态各段原文相同；变动是解释器软链与 pyvenv home。保存的 agent/grader UID 事实、私有材料隔离、activation 与 sysconfig 检查通过。未从验证容器配置推定 Docker daemon build 限额。

## 正式矩阵：逐键与原件闭合

计划 16 行 = 新跑 15 行 + 同版实际公开空 FrozenPatch 的 noop 1 行。新 job `covf5eb-matrix-r6-cpub-20261003-01` 自然退出 0；这是 CPU 固定候选验证，不是模型结果。

逐份读完整 Start/End Test Output，执行固定 parser 纯函数，另用独立 regex 读取 summary；16 份均解析到完整 8 键、无额外键，逐键与原 ledger/diagnostics/作者 per_key 相同。下表省去共同前缀 `JsonReportTest.test_`，JSON 保留完整键名和 SHA。

| 候选 | 匹配／8 | reward | 不符键 |
| --- | --- | --- | --- |
| noop | 3/8 | 0 | branch_coverage、branch_totals_add_up_across_files、branch_totals_count_branch_arcs、branch_totals_from_saved_branch_data、branch_totals_without_branches |
| gold | 8/8 | 1 | 无 |
| A1 | 8/8 | 1 | 无 |
| C1 | 8/8 | 1 | 无 |
| D0 | 4/8 | 0 | branch_totals_add_up_across_files、branch_totals_count_branch_arcs、branch_totals_from_saved_branch_data、branch_totals_without_branches |
| C2 | 5/8 | 0 | branch_totals_add_up_across_files、branch_totals_count_branch_arcs、branch_totals_from_saved_branch_data |
| W2 | 5/8 | 0 | branch_totals_add_up_across_files、branch_totals_count_branch_arcs、branch_totals_from_saved_branch_data |
| C3 | 7/8 | 0 | branch_totals_from_saved_branch_data |
| LF | 7/8 | 0 | branch_totals_add_up_across_files |
| FC | 7/8 | 0 | branch_totals_add_up_across_files |
| C1swap | 6/8 | 0 | branch_totals_add_up_across_files、branch_totals_count_branch_arcs |
| LM | 5/8 | 0 | context_non_relative、context_relative、simple_line_coverage |
| XP | 7/8 | 0 | branch_coverage |
| NB | 7/8 | 0 | branch_totals_without_branches |
| wr_alldata_proj | 7/8 | 0 | branch_totals_add_up_across_files |
| rv_sym_xml | 8/8 | 1 | 无 |

四个合理路线 8/8=1，11 个错误候选均为 0。具体失败与采用版一致：C3 在 :236 缺保存后数据键；LF 在 :262 为 `1 != 5`；FC 在 :277 的每文件值为 `(5,3) != (1,1)`；wr_alldata_proj 在 :271 子集报告为 `(6,5,3) != (6,4,2)`；NB 在 :296 零分支缺键。C1swap 两键针对每文件错误交换，LM 三键为行模式多出 branch 字段，XP 只错原 branch_coverage 的非规定新增指标。未只看 reward 判机制。

15 份补存实际 candidate.patch 的 size/SHA 与 ledger、原候选源文件、作者摘要逐份相同；均只投影 `coverage/jsonreport.py`。从补存 baseline.tar 的原源码独立内存应用每份 hunk，结果与冻结 source blob/base64/content_digest 相同。gold 的实际补丁 SHA `c8fa460d421020f5230fcf5c776bd85f449bb2d8bbfc4b37d98fa3eff1250e59` 同固定 validation 与固定 raw 的 gold extractor 重建结果。

16 行的 baseline 完整 JSON 相同、image/recipe/base 一致；setup 隐藏树、入口与 runner 前后摘要一致，实际导入 `/testbed/coverage/__init__.py`，coverage 5.0.5a0。完整测试段、exec_exit_code0；正对照 test_rc0，负对照1，负对照保留 tests_failed，无 stage_error、partial log、infra_failure_detail 或 runner integrity 变化。每行 grade footer 创建/移除各1，无开放容器与清理失败；15 行 label 容器/网络查询 rc0、残留0。原件总量为正式139文件＋15补丁=154，公开50文件＋tar/SSE六件=56；补存清单目标21件独立校验size/SHA通过。

## 公开交付与空候选复用

首 messages_000.json SHA `9f467b229321bd260096938b1d5323e4190e07829e07b94fc5bcca4109e17e1d`，含完整原题面与完整 rendered prompt。prompt SHA `c9bb55b0f2b1193db573c4bca8904971a1df0b2ea3a2d050347be5087b34cf6a` 是完整提示词摘要，与原 statement 的 `6a516854…` 不同。本题公开题面字节未变；CPU 首请求未附本轮额外 devbrief，GPU 最终交付须由统一执行者核。

真实 Claude Code 2.1.205 对 CPU 桩执行四个 Bash tool_use，有实际 tool_result 和 SSE 往返，均退出0：预检、环境、临时分支 JSON、原 tests/test_json.py。原公开测试 4 passed /0.27秒；Python3.7.9、pytest4.6.6、UID54321、解释器 `/testbed/.venv/bin/python`、cwd `/testbed`、工作树导入与 activation 原件一致。CC 工具去掉 `cd /testbed &&` 前缀，其余正文与 timeout 相同（120/60/120/240秒）；不以桩的 token/cost 输出当模型结果。

原分支 JSON 可生成且缺 covered/missing totals，吻合公开缺陷。公开旧测试做完整字典比较，合理新增字段后可能需结合题面同步预期，不能单因旧格式断言失败判修法错误。人工核 public_devbrief 仅给公开环境、公开测试命令与上述事实，无私有断言/候选。

补存 baseline.tar 4055040字节、SHA `4cc91ec3bc31d9f9b73922a871c59b9d0db98e1ba45522039b5a13a21499e305`，335 成员逐份内容与 Git 执行位模式核对通过。**模式契约是 Git 的100644/100755；install.sh/run_tests.sh 的 tar 原模式0664、无执行位，不宣称 POSIX 全位相同。** 两端 census 独立重建335 entries 与2978排除路径 digest，与两端 baseline 完整相同，baseline digest `abbe27cf…`。actor FrozenPatch 确实0 entries，digest `32ae4544…`；正式回放 patch SHA 为 null、apply_method 为 noop、included 路径为空。roundtrip 身份、entries、排除证据和运输核对通过；excluded_pathset_changed 原值 true/false 保留，未假称该字段相等。

因此 noop 复用有同 prepared/image/overlay/base/baseline 的实际证据：3/8=0，仅原行模式3键通过，五个分支键失败；它不是另跑第16次，也不能拿不同版本空候选替代。actor/grade 清理成功，两组 label 容器与网络残留0。

profile 与预算原值：rollout digest7442237a…（独立重算），agent54321、2CPU/4GiB/pids512；wall1200秒、max_turns8、context32768、new_tokens4096。grader digest3ec1bfa8…、uid54322；candidate900、cleanup120、grade3600、image pull1800秒。setup audit before/after300秒、test1800秒。完整 profile、预检与预算在 JSON 保存，不代填 GPU 身份与预算。

## 复用与限制

复用 [本轮非作者材料窄核](non_author_f5eb_material_review_20261003.md) 和 2026-09-30 旧独立复核的采用版语义。旧 rb3 只补零分支；最终 rb3h 还核测量文件子集。当前消费的是最终 fd4d6ac9…，不是旧 rb3。每文件 summary 两字段仍可选，出现任一则两者必须成对正确；保存、多文件、子集、零分支及目的地分支弧计数均保留。历史私有模拟没有改记为本轮正式 CPU 通过。

本地未保存 derived context/material 文件及 manifest.tsv，已从正式076和实际脚本独立重建配方摘要并与 build/facts/setup树核对；远端 execution_inputs_r6_v1.json 未另存独立本地原件，已核 driver 摘要及15实际补丁/原源文件/FrozenPatch/日志闭合。现场行为依据保存原件，未登录宿主或重跑容器。未发现会妨碍本题普通探针的新增语义缺陷，无需增加角色链或机械重跑共享检查。

作者 card/cpu_matrix 的旧“运行中/未运行”字样需收口更新并引用本审查，不构成本版 CPU 阻断。题主可据此固定 probe_request；GPU 最终 brief/首请求/镜像/服务/次数/预算由统一执行者核，模型运行与结果语义分析仍待完成。CPU 通过不等于训练资格。

全部逐8键重放、补丁与源 blob 摘要、身份及原件 SHA 在 [同名JSON](non_author_f5eb_cpu_review_20261003.json)；JSON status 为 `passed_for_versioned_ordinary_base_probe`，blockers为空。本轮未改共享代码、任务材料、总账或历史原件。
