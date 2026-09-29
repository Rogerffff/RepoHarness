# v2 材料运输独立复核（2026-09-24）

结论：**本子范围通过，未发现需要修复的具体可达缺陷。** 本结论只覆盖 E16 的摄入、派生材料写入、私有评分面运输与两题既有真实 grader 证据绑定；不等于正式训练准入，也不评价题意与测试质量。

复核依据：`r2e_env_repair_20260924/decisions.md` E16、验收记录第 106–119 行，以及当前未提交代码/材料。没有修改生产代码、测试、正式材料或既有 evidence；没有启动 Docker、执行远端命令或审查 reconcile。

## 已验证

[独立探针](probe_transport.py)与[完整结果](probe_transport.json)可复现以下结论：

| 不变量 | 结果与证据 |
| --- | --- |
| 封板身份能被真实消费入口接受 | `load_trusted_r2e_ingest_outputs` 成功加载 48 题；核 pins v3、修订单 v2、manifest v3 与四类数据文件摘要。 |
| 摄入产物确实由来源材料生成 | 从原始 48 行重新运行 `ingest_r2e_subset`，四份产物的序列化字节与当前 `s2_r2e/ingest/` 完全一致。 |
| 变更只限已批准两题 | 相比 `s2_r2e/ingest_history/material_v1_20260924/`，仅 pandas `4ec87eb9` 与 scrapy `cfed9b66` 的 grading/package 行变动；另 46 题这两类行逐字节不变；public 与 validation/gold 全 48 题逐字节不变。 |
| 整份期望替换仍逐键受约束 | pandas 恰好删 2 键、增 13 键，无状态变动；scrapy 恰好 3 键 FAILED→PASSED，无增删。独立重算与 `expected_change` 完全相同。 |
| 新增文件是新增，内容按 bytes 绑定 | `conftest.py` / `test.egg` 均不在来源清单；修订后文件原始 bytes 的 SHA256 与修订单一致。摄入后的清单和树摘要包含新增项。 |
| 构建消费当前配方与修订单 | 用当前 `recipe_v1.sh`、`material_v2.sh` 和生产 `material_manifest()` 重算两题 recipe SHA256，与 `derived3/*/facts.json` 相同。构建日志分别记录新增 conftest、新增 egg 和替换 test_2；最终树摘要与评分面相同。 |
| 隐藏材料只进入私有树及 grader | 两题构建事实记录 `/rh2_private` 为 root:root 0700；agent/grader 身份均不能读私有树；`/r2e_tests`、`/testbed/r2e_tests` 均不存在。 |
| 准备后的评分面和实际 grader 相同 | `replay_b3/private/host_grading_views.jsonl` 中两题 grading 与当前摄入对象、grading digest 相同。当前生产渲染器生成的 scripts digest 与 8 条账本/sidecar 相同。 |
| grader 恢复并保护了新增文件 | 8/8 日志的 `RH2_SETUP_HIDDEN_TESTS_TREE`、入口 SHA256 与当前评分面相同；可信 setup 与保护自证均成功。pandas 的 3 个 official 文件、scrapy 的 5 个 official 文件全部在位并受保护，缺失/不规则文件均为 0。 |
| 新期望进入真正的判定入口 | 使用 `build_r2e_grading_spec(...).parse_log()` 重读 8 份原始日志，完整 expected_match 与 sidecar 相同，match/total/reward 与账本相同：pandas noop 233/237、gold 237/237，各 2 次；scrapy noop 7/9、gold 9/9，各 2 次。 |

两题最终身份：pandas 镜像 `b4ff94834fe0…`、私有树 `6a8597546224…`；scrapy 镜像 `5e1679ba7a20…`、私有树 `aa727a506d6a…`。完整摘要与 8 份日志路径保存在探针 JSON；没有使用较早的 `derived2` 代替最终 `derived3`。

## 生产链与所有权

`pins v3 → load_trusted_r2e_ingest_outputs → build_one → material_manifest → material_v2.sh → root 私有树 → EnvironmentOverlayV1 → replay_grade._overlay_static_mismatch → build_grading_spec_from_host_view → build_r2e_grading_spec → root trusted_setup → manager 控制面权限布置 → uid 54322 测试 → parse_eval_log_r2e`。

摄入/构建为宿主单次顺序过程，读封板材料、生成新产物；镜像构建期间由 root 修改私有树，构建成功才产出覆盖条目。每次 grader 在独立容器先核镜像身份，root 恢复私有材料并复算摘要，再把所有 official 文件收回 root:root 0644、祖先目录设 sticky，最后用候选 uid 54322 执行来源测试入口。新增文件通过完整清单进入原有保护路径，无新增共享可变运行时状态。

关键代码锚点（仓库相对路径）：

- `rh2/src/repoharness2/envpack/ingest_r2e_subset.py:438–468`：文件替换与前后摘要、逐键差异验证；`:472–502`：新增目标与字节摘要验证；`:733–766`：消费期修订清单、树与期望摘要绑定。
- `rh2/scripts/build_r2e_derived.py:177–196`：材料清单与配方摘要；`:449–459`：构建前再次核修订文件字节；`:503–520`：树和私有权限复核。
- `rh2/scripts/r2e_derive/material_v2.sh:23–39`：源摘要、只新增/替换、root:root 0644 与写后摘要。
- `rh2/src/repoharness2/adapters/slime/r2e_grading_scripts.py:79–113`：official 清单、恢复与运行期摘要；`:249–280`：真实 spec 与 parser 闭包。
- `rh2/src/repoharness2/adapters/slime/replay_grade.py:780–797`：覆盖表与评分面的树/私有位置交叉验证。
- `rh2/src/repoharness2/grading/manager.py:2945–2988` 与 `adapters/slime/sandbox_profile.py:1307–1391`：可信 setup、逐文件保护及其自证消费。

## 失败边界与测试

独立故障注入两类，均为内存副本，不污染正式输入：

1. 在 pandas 整份期望文件增加未声明键，同时更新内容摘要，确保越过 SHA256 检查：在实际逐键差异校验处拒绝（`expected_change 不符`）。因此摘要正确不等于能绕过变更声明。
2. 把 scrapy 的新增 egg 修订目标改成来源已有的 `test_1.py`：在新增检查处拒绝（`在来源清单里已存在`）。

本机两次定向维护测试合计 **13 passed，无 skipped/xfail**。前一命令 11 通过、27 deselected；后一命令专门补齐两个新机制的测试，2 通过：

```sh
# 仓库根目录：独立重摄入、历史字节比较、证据绑定、两类失败注入
rh2/.venv/bin/python docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/r2e_t0_batch2_review_20260924/transport/probe_transport.py

# rh2/ 内：本批定向测试
.venv/bin/python -m pytest -q -p no:cacheprovider tests/envpack/test_ingest_r2e_subset.py tests/envpack/test_build_r2e_derived_material.py -k 'revision or material or real_48 or load_attaches'
.venv/bin/python -m pytest -q -p no:cacheprovider tests/envpack/test_ingest_r2e_subset.py::test_expected_file_replace_may_add_and_remove_keys_only_exactly_as_declared tests/envpack/test_ingest_r2e_subset.py::test_hidden_test_file_add_accepts_binary_content_and_rejects_existing_targets
```

## 维度与验证边界

A/D/F/G/H/N：以上 SHA256、身份、路径、所有权及实际入口验证；B：只核已批准两题的计分材料变更范围，不评估训练分布收益；E：两类失败探针真进目标检查，13 个维护测试通过；M：失败明确归因，材料树摘要与自证在既有构建/评分日志可见。J/K：未发现本批需要额外抽象或修改的具体问题。C/I：没有新增准入闸门建议，T0-6 其它六题仍不在本次修订范围。L：本批离线有限材料处理不引入队列或并发 owner；未做性能测量。

没有新跑容器、远端或全池评分；真实执行结论来自既有两题 8 次 grader 的本机原始 evidence，非本轮新实测。没有独立执行 shell 写入或 OS 权限攻击；脚本行为由静态检查、相同配方摘要的构建成功记录及 grader 保护自证共同支持。未注入 crash/cancel/timeout/retry/restart/artifact sink/queue full：它们属于原有构建/执行生命周期，本批没有修改这些机制；本子审仅按分工覆盖材料运输的两类新增失败边界。没有复核 fixture 的题意适配性或 reconcile 版本识别，交主审/对应子审。
