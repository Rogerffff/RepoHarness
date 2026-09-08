# 项目一 B 线资产盘点（环境 / 数据 / 评测 / 基座诊断）

- 日期：2026-09-08。仓库根：`.`（分支 `miles-migration`，只读盘点，未改任何仓库文件）。
- 方法：除读文档外，实际执行了 `load_trusted_ingest_outputs`（216 包全部通过 pins/digest 校验）、swebench 4.1.0 的 `make_test_spec` / `MAP_REPO_TO_PARSER` 查表、`build_grading_spec_from_host_view` + `parse_log` 探针（真实 SWE-Gym 题）、`docker images`、HF 缓存目录、sha256 复核。凡标"实测"的都是本次跑出来的结果。
- 状态口径：**有产物** = 文件在仓库里且本次核对通过；**只有代码** = 有可调用实现但没有产出真实数据/运行记录；**只有文档** = 仅存在于计划/报告文字。

---

## 1. 候选任务集（216 题）

**结论**：216 题的四面 bundle 产物真实存在、git 已跟踪、pins 与 digest 本次全部核对通过；但 216 题只覆盖 **9 个仓库**（不是 11 个——hydra/bokeh 作为 held-out 已剔除），且这批题从未在任何容器里跑过评分。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| 来源数据集 `SWE-Gym/SWE-Gym-Lite`，HF revision `f70b1a29ab120eb0a0ee7a1deb029825e735b2b0`，230 行 × 11 列（instance_id/repo/base_commit/version/created_at/problem_statement/hints_text/patch/test_patch/FAIL_TO_PASS/PASS_TO_PASS） | `data_freeze/freeze_manifest_v0.json` `sources`；raw 归档 `docs/agentic_RL/repo_harness_rh2_workstreams/s2/raw/swe_gym_lite_full_f70b1a29.jsonl`（3.5 MB，sha256 `f769d97d…`，git 已跟踪）；HF 本机缓存 `~/.cache/huggingface/hub/datasets--SWE-Gym--SWE-Gym-Lite/snapshots/f70b1a29…/data/train-00000-of-00001.parquet` | 有产物 |
| Lite 230 题的 11 个仓库及题数：getmoto/moto 59、python/mypy 40、iterative/dvc 36、Project-MONAI/MONAI 27、pydantic/pydantic 20、dask/dask 14、conan-io/conan 12、facebookresearch/hydra 11、pandas-dev/pandas 5、modin-project/modin 5、bokeh/bokeh 1 | 实测统计 `data_freeze/meta/swe_gym_lite.jsonl` | 有产物 |
| 静态门漏斗：230 → 剔 held-out 仓库 12（hydra 11 + bokeh 1）→ 剔 test_adequacy fail 1 → 剔题面泄漏 fail 1 → **216** | `data_freeze/freeze_manifest_v0.json` `static_gate_funnel_lite`；`data_freeze/labels/static_gate_survivors.txt`（216 行，sha256 `66400caa…`） | 有产物 |
| **216 题的 9 个仓库**：moto 59、mypy 40、dvc 35、MONAI 26、pydantic 20、dask 14、conan 12、pandas 5、modin 5；78 个不同 (repo, version) 对 | 实测（`load_trusted_ingest_outputs` 返回的 packages 计数） | 有产物 |
| 可信 ingestion 产物（5 数据文件 + 提交记录，全部 git 已跟踪）：`environment_packages_v0.jsonl`（216）、`public_bundles_v0.jsonl`（216）、`grading_bundles_v2_v0.jsonl`（216，2.2 MB）、`validation_bundles_v0.jsonl`（216，含 golden）、`duplicate_clusters_v0.json`（2 簇）、`ingest_manifest_v0.json`（sha256 `3408bab7…`） | `docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/`；`git ls-files` 确认在库 | 有产物 |
| 冻结/防篡改链：代码常量 → pins 文件 → 输入文件。`INGEST_MANIFEST_SHA256_PIN`、`T1_PINS_SHA256`、`VENDOR_REGISTRY[...].json_sha256`、`STRIP_SPEC_SHA256` 四个常量；`t1_input_pins_v1.json` 钉七项输入（raw/keyed manifest/evidence/survivors/image_refs/strip_spec/vendor json）。**本次复核 7/7 pins OK、5/5 数据文件 digest OK、提交记录 digest OK、trusted loader 216/216 通过** | `rh2/src/repoharness2/envpack/ingest_swegym_lite.py:466-467`（pin 常量）、`t1_pins.py:24-25`、`spec_vendor.py:41-53`；`s2/t1_input_pins_v1.json` | 有产物 |
| 上游冻结账本 `freeze_manifest_v0.json` v0.1（24 项 artifact digest，四源 HF revision：Lite f70b1a29 / Full bb94ed9e / R2E-Subset e8b9fcbc / Verified 91aa3ed5） | `data_freeze/freeze_manifest_v0.json`、`data_freeze/meta/*.revision` | 有产物 |
| 每题"四面"字段：<br>**package**（零内容，只有身份+digest）：task_id(`swe_gym_lite::<iid>`)/source/instance_id/repo/repo_key_lower/base_commit/image/image_manifest_digest/public_bundle_digest/grading_bundle_digest/validation_bundle_digest/raw_archive_sha256/image_manifest_keyed_sha256/spec_vendor_json_sha256<br>**public**（模型可见）：instance_id/repo/base_commit/image/image_manifest_digest/workdir(`/testbed`)/allowed_tools(`["bash","edit"]`)/problem_statement/problem_statement_sha256/public_hints（固定 system 提示）<br>**grading v2**（runtime-private，无 golden）：instance_id/repo/repo_key_lower/version/base_commit/test_patch/fail_to_pass/pass_to_pass/eval_cmd/python_version/spec_vendor_id(`swegym_constants_242429c1`)<br>**validation-only**：instance_id/golden_patch/golden_patch_sha256 | `envpack/bundles_v2.py`（三个模型）、`envpack/bundles.py:PublicTaskBundle` | 有产物 |
| strip_spec 归类：instance_id/repo/base_commit/version→env_materialization；problem_statement→model_visible；hints_text→strip；patch→validation_only；test_patch/F2P/P2P→grader_only；created_at→pipeline_meta。hints_text/created_at 实测不进任何 bundle | `data_freeze/strip_spec.yaml`（sha256 `e96af018…`）；`ingest_swegym_lite.py:53-65` | 有产物 |
| 评分面统计（实测）：F2P 条数 min/中位/max = 1/1/16；P2P = 0/20/2836，**22 题 P2P 为空**；eval_cmd 8 种（`pytest -n0 -rA` 76、`pytest -rA` 35、`pytest -n0 -rA -k` 34、`pytest -rA ` 26、pydantic 专用 20、dask `--color=no` 14、`pytest -rA -k` 6、pandas `--tb=long` 5）；python_version 3.12×65/3.8×61/3.9×46/3.10×19/3.11×6/**None×19（dask 14 + pandas 5）** | `s2/ingest/grading_bundles_v2_v0.jsonl` | 有产物 |
| 去重：任务身份 = source-qualified task_id；环境身份 = (repo_lower, base_commit)。两簇同环境不同题（moto-6469/6470、mypy-11824/11857），均 `distinct_tasks_shared_environment`，0 suspected_duplicate；214 唯一镜像 digest / 216 | `s2/ingest/duplicate_clusters_v0.json`；`ingest_swegym_lite.py:build_duplicate_clusters` | 有产物 |
| 静态质量标签（LLM 打标 + 人工校准 15/15）：230 行，三标签 issue_clarity pass 219/warn 11；test_adequacy pass 215/warn 14/fail 1；solution_leakage fail 31/warn 92/pass 107（来源 hints_only 109、problem_statement 14）；leakage_final pass_hints_stripped 109 / pass 107 / warn 13 / fail 1 | `data_freeze/labels/swe_gym_lite_quality_final.jsonl`、`labels/labeling_prompt.md`、`labels/run_labeling.py`、`labels/calibration_human.jsonl` | 有产物 |
| **13 题 leakage warn 的 `leakage_watch` 标记没有进任何 bundle/package 字段**（freeze_manifest 不变量第 7 条要求"带标记进池"）；只能回查 labels 文件 | 对照 `bundles_v2.py` 字段集与 `freeze_manifest_v0.json` `invariants[6]` | 只有文档 |
| ingestion 工具：`fetch_raw_lite.py`（按 pin 下 parquet + 11 列双向校验 + D5）、`resolve_image_digests.py`（registry HEAD/GET + config blob 实证）、`extract_vendor_specs.py`（构建期一次性 exec vendored constants → JSON）、`build_environment_packages.py`（216 题构造 + 回读自检） | `rh2/experiments/s2_1_ingestion/*.py`（git 已跟踪） | 只有代码（可重跑） |
| 另一套 8 题冻结集（**SWE-bench Verified，训练不可用**，只作 bring-up/传输链回归）：django-11099/11133/16139、sympy-14711/15349、requests-1142/2931、astropy-14995；含官方 eval_script 全文（swebench 4.1.0 生成）与 golden（v1 PrivateGradingBundle） | `rh2/src/repoharness2/envpack/data/swe_smoke_tasks.json`、`frozen_v1.json` | 有产物 |
| 216 题未做过：pass-rate 预筛、环境验证门、任何容器内评分（见 §3/§4） | 全仓 grep 无 SWE-Gym instance 的 grading 产物 | 只有文档 |

---

## 2. 镜像

**结论**：216 题逐题镜像 digest 已解析并实证（Docker Hub `xingyaoww` 命名空间，tag 全为 `:latest`，身份靠 manifest digest），但**本机一个 xingyaoww 镜像都没拉过**，也没有任何记录表明远端拉过；总体积只有抽样外推（约 0.48 TiB）。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| `image_refs_swegym.txt` 2438 行 = **SWE-Gym Full 全量**镜像引用（由 `swe_gym_full.jsonl` 按规则生成），Lite 230 ⊂ Full；216 题的镜像是其子集，loader 校验每题 `source_image_ref ∈ 这 2438 条` | `data_freeze/meta/image_refs_swegym.txt`（sha256 `e39da94c…`）；`data_freeze/image_manifest.md` "产物范围"；`ingest_swegym_lite.py:load_trusted_ingest_outputs`（frozen_refs 校验） | 有产物 |
| 命名规则：`xingyaoww/sweb.eval.x86_64.<lower(instance_id) 把 "__" 换成 "_s_">:latest`（不是官方 `_1776_`）；例 `Project-MONAI__MONAI-1121` → `xingyaoww/sweb.eval.x86_64.project-monai_s_monai-1121:latest` | `data_freeze/image_manifest.md`（含 4 正例 3 反例的 Docker Hub 实测）；`ingest_swegym_lite.py:_expected_ref` | 有产物 |
| 216 题键控清单（schema `rh2.s2_1.image_manifest_keyed.v4`，216/216 enriched）：每条 source_image_ref / resolved_manifest_digest / config_digest / platform `linux/amd64`（来自 config blob）/ registry_evidence_ref；evidence 216 行（manifest 字节哈希 + config blob 哈希实证） | `s2/image_manifest_keyed.json`（sha256 `dd1e686c…`）、`s2/raw/image_registry_evidence.jsonl`（sha256 `4c3875c6…`） | 有产物 |
| 全部是单架构 manifest v2（`application/vnd.docker.distribution.manifest.v2+json`），非 manifest list | 同上 `manifest_content_type` 字段 | 有产物 |
| store 实现：`load_state`（只认 v4，严格加载）/`finish_assertions`/`flush_transaction`（双文件事务）/`migrate_v3_manifest`（双 pin 一次性迁移） | `rh2/src/repoharness2/taskset/image_manifest_store.py:205,387,343,281` | 只有代码 |
| **本机 docker（29.4.1，desktop-linux）：0 个 `xingyaoww/*` 镜像**；有 47 个 `swebench/sweb.eval.x86_64.*` 官方 Verified 镜像（旧阶段留下的 sphinx 等），8 题冻结集里只有 `psf_1776_requests-2931` 在本地；另有 38 个 `repo-harness-swebench-verified-agent:*`（V4/V5 时代） | 实测 `docker images` | 有产物（但与 216 无关） |
| 体积：无逐镜像账。抽样 10 个 Full 镜像压缩层均值 2.230 GiB（0.975–3.618）；moto-5752 实测 1,146,016,016 B。外推：Lite 230 ≈ 513 GiB；按同均值 216 ≈ 482 GiB（朴素压缩和，registry 去重后更低；建议 +30~50% 余量） | `data_freeze/image_manifest.md` 抽样体积表与三档外推 | 只有文档（估算） |
| 拉取限额方案与本地 `registry:2` 同步 runbook（pull-tag-push、批 150、断点续传）——**未执行过** | `data_freeze/image_manifest.md` "本地 registry:2 同步 runbook" | 只有文档 |

---

## 3. 评分链状态（T2-c / T2-d / T2-e）

**结论**：T2-c（ingestion）完成；T2-d 只有"eval 脚本渲染 + vendor eval_cmd 互检"两段代码，**SWE-Gym parser 不存在**——实测对真实 216 题构造评分 spec 后 `parse_log` 直接 `KeyError('getmoto/moto')`，manager 会把它判成 `test_log_parse_failed`（infra 族），因此当前代码对 216 题**全部不可评分**；T2-e 四门 runner 零实现；没有任何一题跑过 golden/empty 评分。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| 定义（06 计划）：**T2-d** = v2 grader 正链 "clean checkout → agent frozen patch → official test_patch 后写 → vendor 复核 eval_cmd → SWE-Gym parser → GradingReport"；**T2-e** = 四门 runner；两者"由既有数据线程继续，RH2 Wave1 不重复造"；`05-fully-async-execution-plan.md` 完全没提 T2-c/d/e | `06-first-training-local-execution-plan.md:134`；`CURRENT-STATE-BRIEF.md:75`；grep 05 计划无命中 | 只有文档 |
| T2-c 完成：真实 216 题构造 + strict loader + trusted 入口（§1） | `s2/s2_1_t2_report.md` "T2-c 完成"；本次实测 loader 通过 | 有产物 |
| 已实现的 T2-d 片段 ①：v2 eval 脚本渲染（conda activate testbed → `git checkout <base> <test_files>` → heredoc `git apply` test_patch（后写）→ Start 标记 → `eval_cmd <test_files>` → End 标记 → reset）；F2 拆成 root trusted setup / 候选测试两段脚本 | `rh2/src/repoharness2/adapters/slime/prepared_task_face.py:116-176`（`render_v2_eval_script` 等） | 只有代码（未在真实镜像验证；docstring 明写"归 T2-d/W3a 验证"） |
| 已实现的 T2-d 片段 ②：eval_cmd/python_version 消费期与注册表派生值互检 | `envpack/spec_vendor.py:verify_grading_eval_cmd`；`prepared_task_face.py:73` | 只有代码 |
| **缺失的 T2-d 片段 ③（parser）**：`build_grading_spec_from_host_view` 的 `_parse` 闭包 → `scoring.parse_eval_log(grading, log)` → `parse_official_eval` → swebench `make_test_spec(...)`。**实测**：对 `swe_gym_lite::getmoto__moto-5752` 构造 spec 成功，喂一段带官方标记的日志，`parse_log` 抛 `KeyError('getmoto/moto')` | `prepared_task_face.py:188-189`；`envpack/scoring.py:121-123`；本次探针 | 只有代码（且对 216 题必然失败） |
| manager 对 parser 异常的处置：`except Exception → GradingInfraError(category="test_log_parse_failed")` → `failed_to_grade`、reward None（infra 族，不是 reward 0）→ 组被 drop | `grading/manager.py:2004-2013` | 只有代码 |
| swebench 4.1.0 零覆盖的具体表现：`swebench.harness.log_parsers.MAP_REPO_TO_PARSER` 60 键、`swebench.harness.constants.MAP_REPO_VERSION_TO_SPECS` 66 键，9 个 survivor 仓库（原大小写与小写）**一个都不在**；`make_test_spec` 对任一 SWE-Gym 行 `KeyError`。注意 4.1 里 `MAP_REPO_TO_PARSER` 不在 `constants` 模块（`scoring.py` docstring 按旧名称叙述） | 本次实测；`rh2/.venv`（swebench 4.1.0） | 有产物（负面实证） |
| vendored SWE-Gym fork constants（`SWE-Gym/SWE-Bench-Fork@242429c1`，MIT）→ 包内 JSON：33 仓库 / 808 (repo,version)，键全小写；字段 install/test_cmd/python/packages/pre_install/pip_packages/env_patches/eval_commands/execute_test_as_nonroot/no_use_env/nano_cpus；216/216 (repo,version) 命中；**不含任何 parser 映射**（vendored .py 里无 `MAP_REPO_TO_PARSER`/`log_parsers`） | `s2/vendor/swegym_constants_242429c1.py` + `.provenance.json`；`rh2/src/repoharness2/envpack/data/swegym_specs_242429c1.json`（sha256 `0da8f9ca…`）；本次实测 | 有产物 |
| 216 题 eval_cmd 全是 pytest 变体 → 理论上可用 swebench 的 pytest 类 parser（`log_parsers.python` 的 `parse_log_pytest*`），但**没有任何代码把 (repo→parser) 接上** | 本次 grep `rh2/src` 无 `log_parsers` 引用 | 只有文档（06 计划 T2-d 待办） |
| 渲染脚本的两个未验证边界：(a) **40 题 mypy** 的 eval_cmd 以 `-k` 结尾（`pytest -n0 -rA -k` / `pytest -rA -k`），渲染器直接拼 `-k <test 文件路径>`——`-k` 期望的是表达式不是文件，语义可疑；(b) **12 题 conan** 的 spec 有 `eval_commands: ["export PYTHONPATH=…:$(pwd)"]`，渲染器不消费 `eval_commands`/`pre_install`/`install` | 实测统计 + `prepared_task_face.py:108-113` | 只有代码（未验证） |
| **真实评分记录**：只对 8 题 Verified 冻结集跑过（7a：8/8 golden agent-diff 重放与 S0-7 一致；run6–9 共 ~120 次评分）。**216 题零次**；唯一涉及 216 的"评分性"材料是 W3b 的静态统计（test_patch 形状：新增文件 8 题、删除 0、改名 0）和 crosscheck 的 5 条合成日志探针（django） | `s1/7a_artifacts/t1_regression_report.json`；`miles_spike/wave1/w3b_report.md:394-406`；`miles_spike/external_infra_review_crosscheck_20260906/grading-result.jsonl` | 有产物（仅 Verified 8 题） |
| 与 T2-e 相关的未决 T0：grader 非 root（rh2grader）执行候选测试 vs 四门若以 root 跑出的 F2P/P2P 可能翻转 reward——要求四门用同一 grader profile 重验 | `06-first-training-local-execution-plan.md:103`；`miles_spike/wave1/w3b_report.md:177` | 只有文档 |
| 第三方对当前 parser 缺口的定性："确定的配置不支持，不是 Docker 抖动；应在选定任务适配器后尽早暴露支持范围" | `project1_execution/issue_inventory_20260908/README.md:99-103`、`claims_falsifier.md:154` | 只有文档 |

---

## 4. 四门 runner（T2-e）

**结论**：门的规格写得很细（硬门 empty/golden/determinism N=3 + 探针层假阳性），但 `grade_controlled_patch`、`EnvValidationReport`、runner、fixture 全部零代码；8 题基线（T3）、50 题试运行（T4）、216 全量（T5）、题单冻结（T6）都没发生。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| 规格（2026-07-12 codex 轮次 4 修订后）：硬门 1 **empty patch 必败**（前提 = 测试真实运行且 parser 成功解析，然后 ≥1 F2P 处于失败态；infra/apply 失败不算）；硬门 2 **golden 必过**（RESOLVED_FULL：全部 F2P 通过 ∧ P2P 零失败）；硬门 4 **确定性**（empty 与 golden 各跑 N=3 次，每次全新容器，比较 verdict + F2P/P2P 集合）；探针层 3 假阳性（3a 无关文件 patch 应 FAIL；3b mutation probe 四态 rejected/suspicious_pass/fixture_invalid/infra_failure，只进人工复核不自动剔题） | `s2/s2_1_data_ingestion_execution_plan.md:65-95` §3.1；O-3/O-4 定案 `:176-183` | 只有文档 |
| 早期版本（04 计划）把假阳性也列为硬门、heldout_proposal 写"每题 2 次"——已被 s2_1 计划 O-3/O-4 改掉 | `04-s2-execution-plan.md:51`；`data_freeze/heldout_proposal.md:26-27` | 只有文档（已过时） |
| 执行底座应为 `grading/manager.py` 新增 `grade_controlled_patch(patch_bytes, patch_origin, patch_digest, validation_run_id)`；逐题 `EnvValidationReport`（passed/failed/infra_failed/not_applicable/suspicious + provenance + 透传 leakage_watch）注册 `EXTRA_SCHEMA_REGISTRY`；幂等键 `(instance_id, gate, fixture_digest, image_digest, validator_config_digest, attempt)`；只对 infra 重试 | 同上 §3.1-3.2 | 只有文档 |
| **代码现状**：grep `grade_controlled|controlled_patch|EnvValidation|EnvironmentValidation|four_gate|GateInputs|empty_patch_must_fail|golden_patch_must_pass|determinism` 在 `rh2/src`、`rh2/tests`、`rh2/experiments` **0 命中**；`golden` 只出现在 bundle 字段名/黑名单 (`GOLDEN_FIELD_NAMES`) 和合成测试夹具；`registry.py` 的 EXTRA_SCHEMA_REGISTRY 无 EnvValidationReport | `rh2/src/repoharness2/registry.py:83-110`；本次 grep | 只有文档 |
| 载体估算：216 题 × 8 次 ≈ 1730 次评分运行；本机 ARM/QEMU 不现实；x86 CPU 实例（16 核/1 TB，$0.3–0.8/h）1–2 天、$15–40；T4/T5 必须同一基质 | `s2_1_data_ingestion_execution_plan.md:97-116` §3.3 | 只有文档 |
| 计划的验收产物：`bringup_candidate_v0`（题 id + 镜像 digest + 题面 sha256 + 门证据 ref）、漏斗账、benchmark card 雏形 | 同上 §4 T5/T6 | 只有文档（不存在） |

---

## 5. held-out / 划分

**结论**：只有"按仓库整体切出"的 held-out 规则和 542 题候选清单（元数据级），没有任何 train/dev/test 划分产物；216 题目前就是整个候选池，没有冻结子集。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| 仓库级冻结常量：`HELDOUT_BASENAMES = {"tornado","pyramid","hydra","bokeh"}`（按 basename 判），`EXPECTED_SURVIVOR_COUNT = 216`；`build_task` 内 D5 断言命中即 `IngestError` | `rh2/src/repoharness2/envpack/ingest_swegym_lite.py:70-73,140-141` | 有产物（代码 + 216 产物已过断言） |
| held-out 候选 542 题：tornado 261 + pyramid 189（R2E-Gym-Subset，`namanjain12/*_final:<sha>` 镜像）、hydra 66 + bokeh 26（SWE-Gym Full）；字段只有 source/repo/id/docker_image——**无题面/golden/测试材料**，未 ingestion，0 题冻结 | `data_freeze/meta/heldout_candidates.jsonl`（542 行）；`heldout_proposal.md` | 有产物（仅清单） |
| 互斥断言 PASS：train_pool ∩ Verified = ∅、heldout ∩ Verified = ∅；跨源重复仓库 swe_gym ∩ r2e = {pandas}（两者都在训练侧，不违反互斥） | `data_freeze/meta/repo_disjoint_report.json`；`meta/assert_repo_disjoint.py` | 有产物 |
| 注意：`train_pool ∩ heldout = []` 一行是同义反复（train_pool 定义时已减去 heldout）；真实 survivor 级证明在 T1a 第 3 步 | `s2/s2_1_t0_selfcheck.md` 补注；`s2_1_t1_report.md` T1a | 有产物 |
| held-out 冻结流程（静态门 → 环境门 → GPU pass-rate 中段筛 [0.1,0.8] → 分层冻结 T=50~80）——一步都没执行；O-1 定案：held-out 门不并入 S2-1（R2E 需另一套 ingestion + scaleswe grader） | `heldout_proposal.md`；`s2_1_data_ingestion_execution_plan.md:178` | 只有文档 |
| train/dev/test 划分：**无产物**。`trusted_prep.py --task-ids` 支持逗号子集，但仓库内没有任何冻结的子集/题单文件；grep `train_split|dev_split|test_split|bringup_candidate` 无产物命中 | `rh2/src/repoharness2/envpack/trusted_prep.py:56-60`；本次 grep | 只有代码（子集能力） |
| 时间/PR 派生切分：无。`created_at` 归 pipeline_meta 被剥离出 bundle（raw 归档里仍有）；PR 派生关系只做了"同 base_commit 两对"的环境身份簇 | `strip_spec.yaml`；`duplicate_clusters_v0.json` | 有产物（仅两簇） |
| Verified 500 题元数据（instance_id/repo/base_commit/version）：角色 = 外部参考面独占，训练不可用 | `data_freeze/meta/verified.jsonl`、`freeze_manifest_v0.json` `sources` | 有产物 |
| R2E-Gym-Subset：只抓了 4578 行轻元数据（repo_name/docker_image/commit_hash/problem_statement 截断），无答案字段；R2E ingestion 从未发生 | `data_freeze/meta/r2e_subset.jsonl`（6.3 MB）；`miles_spike/first_training_readiness_alignment_claude.md:18` | 有产物（仅元数据） |

---

## 6. eval 资产

**结论**：所谓 eval 数据只有 1 条（django-11099，SWE-bench Verified）冒烟 prompt，加 8 条同源 GPU spike prompt；没有 SWE-Gym 的 eval 题单，也没有 held-out eval 集。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| `EVAL_SMOKE_DATA = $SCRIPT_DIR/data/eval_smoke_prompts.jsonl`（1 行，sha256 `77e736d1…` 与脚本预注册值一致）；用法 `--eval-prompt-data smoke $EVAL_SMOKE_DATA --n-samples-per-eval-prompt 1 --eval-interval $NUM_ROLLOUT` | `rh2/experiments/miles_gpu_spike/launch.sh:127-128,295-300,429-432` | 有产物 |
| `gpu_spike_prompts.jsonl`（8 行 = frozen_v1 的 8 题 Verified，sha256 `009b34e5…` 与预注册一致），launch.sh 钉 `s1_compat` 模式、`rh2_formal_training_allowed=false` | `rh2/experiments/miles_gpu_spike/data/gpu_spike_prompts.jsonl`；`launch.sh:56-61,125-126` | 有产物 |
| prompts.jsonl 实际形状（v1 legacy，3 键 metadata）：`{"prompt": "Fix the following issue from the \`django/django\` repository (checked out at /testbed, commit d26b2424437d):\n\n<problem_statement 原文>", "label": "django__django-11099", "metadata": {"instance_id": "django__django-11099", "image": "swebench/sweb.eval.x86_64.django_1776_django-11099:latest", "workdir": "/testbed"}}`；由 `make_prompt_data.py` 从 v1 BundlePair 渲染 | `rh2/experiments/s1_7a_bringup/make_prompt_data.py` | 有产物 |
| v2 prompts.jsonl（216 题用）：由 `python -m repoharness2.envpack.trusted_prep --repo-root … --out-dir … --private-dir …` 运行期生成，metadata 恰好 5 键 task_id/source/instance_id/environment_package_digest/public_bundle_digest（`rh2_` 前缀保留键 fail-closed），同时产出 rollout_task_views.jsonl / prepared_manifest.json / 私有 host_grading_views.jsonl（0700/0600）。**仓库内没有任何已生成的 v2 prepared 产物** | `rh2/src/repoharness2/envpack/trusted_prep.py`、`prepared_tasks.py:83-97` | 只有代码 |
| W8 eval 运输链（checkpoint 绑定、身份分离、skip 不洗绿）——06 计划工作包，未开工 | `06-first-training-local-execution-plan.md` W8 行 | 只有文档 |

---

## 7. 基座诊断相关现成资产

**结论**：唯一的真实 Claude Code 实测是 2026-07-08 S1-7a 的 Qwen3-4B × 8 题 Verified（run6–9，每 run 32 rollout）——成功率 5/32 与 1/32、rollout 墙钟中位 ~80 s、失败类型只有评分结果 + 截断/abort 标志，没有"定位/修改/验证"级归因；没有针对 Qwen3-30B-A3B 或 SWE-Gym 题的任何实测；本机没有模型权重也没有 CC linux tarball。

| 事实 | 证据路径:行 或 产物路径 | 状态 |
| --- | --- | --- |
| 环境：vast.ai 单卡 RTX PRO 6000 96 GB（sm_120）；slime pin 镜像 `slimerl/slime@sha256:a7317182…`（sglang 0.5.13）；Claude Code CLI **2.1.202**（linux-x64 平台包直装）；Qwen3-4B dense（HF → torch_dist）；8 题 × n=4 = 32 rollout；top_p 0.95、T 1.0、每轮 max_new_tokens 2048、上下文 32768（run9 改 20480）；agent 预算 600 s、每会话 25 轮；`--disallowedTools Task WebFetch WebSearch` | `s1/bringup_7a_report.md:1-10,86-110`（§2.1） | 有产物 |
| run6：32/32 rollout，10 条交付；训练 OOM；django 8/8 灭于 `ensure_agent_user` 60 s 超时（已修）；多叶 FORK 10 命中 | `bringup_7a_report.md` §2.3；`s1/7a_artifacts/artifacts_run6/bringup_summary.json` | 有产物 |
| run7：32/32；评分 21 = 20 unresolved + 1 注入 infra；27 样本进 batch；**奖励全 0 → loss 0**；checkpoint 53 GB 保存后删除 | 同上；`artifacts_run7/`；`ckpt_discard_run7.log` | 有产物 |
| **run8**：评分 32 = **5 resolved**（django-11099 ×1、11133 ×1、16139 ×3）+ 26 unresolved + 1 failed_to_grade（注入）；60 样本交付；rollout 墙钟 mean 123.8 s / max 555.2 s / 中位 82.4 s；harness_exit_code 0×27 / 1×5；truncated True 21 / False 39；评分 total mean 8.8 s / max 27.5 s；训练 step 在 32768 上下文 OOM | `artifacts_run8/bringup_summary.json`、`bringup_events.jsonl`（32 条，含 wall_seconds/rewards/harness_exit_code/statuses/response_lengths/truncated_meta） | 有产物 |
| **run9**（ctx 20480）：评分 31 = **1 resolved** + 29 unresolved + 1 注入；65 交付 + 1 `adapter_session_empty` abort；墙钟 mean 82.1 s / max 263 s；exit_code 0×22 / 1×10；truncated True 43 / False 22；`pg_loss 0.01073, grad_norm 0.2935, train_rollout_logprob_abs_diff 0.0115` | `artifacts_run9/bringup_summary.json`、`run9_step_metrics.txt` | 有产物 |
| 逐 rollout 完整对象（grading_report / eligibility_report / trajectory_projection / capture_records）**只留了 run8 的 1 条**（django-16139，resolved）；其余只有 summary/events | `artifacts_run8/rollouts/4a25c5a4-…/` | 有产物（样本 1 条） |
| 失败类型口径：只有 grading outcome（resolved/unresolved/failed_to_grade）、`abort_reason`（`rh2_gate_degraded`、`rh2_assemble_failed:SlimeBindingError`）、truncated 标志、harness exit code；**没有"定位/修改/验证/交付"归因，没有 CC 轮数统计**（events 的 `response_lengths` 是交付分支的 mask 段数，不是轮数） | 同上 | 有产物（粒度不够） |
| 7a T1 另一组（deepseek-chat 经 verifiers，非 Qwen）：django-11099 RESOLVED_FULL 12 轮 44.7 s；requests-2931 RESOLVED_NO 30 轮（max_turns）104.9 s；8 题 golden agent-diff 重放 8/8 与 S0-7 一致（7 resolved + 1 unresolved） | `bringup_7a_report.md` §1.1-1.2；`7a_artifacts/django__django-11099.json`、`psf__requests-2931.json`、`t1_regression_report.json` | 有产物 |
| 观察到的 CC 形态：CC 在后续请求剥离历史 thinking 块 → Qwen3 重渲染漂移 → 每条轨迹首轮被 REALIGN 掉落；离线导出器对真实 CC 轨迹全部 fail-closed | `bringup_7a_report.md` §2.7；`s1/implementation-notes.md:151` | 有产物 |
| harness 配置（代码）：`RH2_BRINGUP_HARNESS` 默认 `claude_code`；`SWE_AGENT_TIME_BUDGET_SEC` 默认 600；`RH2_MAX_TURNS_PER_SID` 默认 25；`RH2_EXECUTION_MODE` ∈ s1_compat/fa_audit_only/fa_formal（默认 s1_compat）；`RH2_CLAUDE_CODE_VERSION` 默认 **2.1.205**（容器内 `claude --version` token 精确比对，不符 fail-fast）；tarball 经 `SLIME_AGENT_CC_PLATFORM_TARBALL` 上载后解出自包含二进制装到 `/usr/local/bin/claude` | `rh2/src/repoharness2/adapters/slime/bringup.py:224-229,301-343` | 只有代码 |
| 压缩/重试守卫 env（合并进 `SLIME_AGENT_CC_EXTRA_ENVS`）：`DISABLE_COMPACT=1`、`CLAUDE_CODE_MAX_RETRIES=0`、`CLAUDE_CODE_DISABLE_NONSTREAMING_FALLBACK=1`、`CLAUDE_CODE_UNATTENDED_RETRY=0`；Microcompact/Context Collapse 不受 env 控制，靠装配期收缩检测兜底 | `adapters/slime/generate.py:1036-1056` | 只有代码 |
| 工具面：CC 默认工具减 `Task WebFetch WebSearch`（`SLIME_AGENT_CC_EXTRA_ARGS`）；public bundle 的 `allowed_tools=["bash","edit"]` 只是信息字段 | `launch.sh:107`；`bundles.py:DEFAULT_ALLOWED_TOOLS` | 只有代码 |
| tarball/权重位置约定（远端）：`/root/tarballs/claude-code-linux-x64.tgz`（包 `@anthropic-ai/claude-code-linux-x64@2.1.205`）、`/root/tarballs/docker-cli`、HF `/root/models/Qwen3-30B-A3B`、torch_dist `/root/Qwen3-30B-A3B_torch_dist`、Megatron `/root/Megatron-LM` | `launch.sh:101-108`；`fa/claude_code_retry_timeout_source_guided_validation.md:123-138` | 只有文档/脚本 |
| **本机**：`find ~ -maxdepth 4 -iname 'claude-code-linux-x64*'` 无；HF 缓存 `models--Qwen--Qwen3-30B-A3B/8B/0.6B` 目录仅 ~15 MB（config/tokenizer，无 safetensors）；**没有 Qwen3-4B 缓存** | 实测 | 不存在 |
| "只起推理不起 learner"入口：① `rh2/experiments/p3_preflight/j2_sglang_30b.sh`——裸 `python3 -m sglang.launch_server` 起 Qwen3-30B-A3B（默认 2 引擎 × TP2，ctx 32k，`--attention-backend triton --sampling-backend pytorch --disable-cuda-graph`）+ bench，**不接 harness、不接 rh2**；② `fa_audit_only` 执行模式——在 slime/miles rollout manager 内跑真实 CC rollout 但不评分不交付（仍需 Ray + 训练容器）；③ `rh2/experiments/s0_swe_smoke.py`——verifiers DockerRuntime + default harness(bash+edit) 打 DeepSeek API，**不是 Claude Code**。**没有** "CC + 任意 OpenAI 兼容端点 + rh2 沙箱 + 评分、无 learner" 的独立脚本 | `p3_preflight/j2_sglang_30b.sh:1-25`；`bringup.py:225,256-259`；`generate.py:1965-1969`；`s0_swe_smoke.py:1-20` | 只有代码 |

---

## 8. 外部数据集与工具可用性

**结论**：与 B 线最相关的四个数据源仓库（SWE-smith、R2E-Gym、SWE-Gym 官方仓、swe-rebench）本地都**没有克隆**，只有阅读笔记和 `research-environments` 里的封装；工具链（swebench 4.1.0、huggingface_hub 1.22、datasets 4.6.1、docker）在 `rh2/.venv` 可用；HF 缓存只有数据集，没有模型权重。

| 事实 | 证据路径 或 实测 | 状态 |
| --- | --- | --- |
| `reference/` 下与 B 相关的仓库（本地 git clone，除 verl 外均未被主仓跟踪）：`verifiers` HEAD `5885ab9c5`（= `rh2/pyproject.toml` pin，全仓引用 101 处）；`mini-swe-agent` v2.4.4 `4fe36a38`（引用 21 处，均为文档）；`research-environments` `3093d72a3`（引用 39 处；含 `environments/` 下 swebench_v1 / swebench_verified_v1 / swebench_pro_v1 / r2e_gym_v1 / scaleswe_v1 / swerebench_v2_v1 / multiswe_v1 / openswe_v1 / rlm_swe / swelego_v1）；`terminal-bench-pro` `874af40`（引用 16 处，任务目录形态）；`slime` v0.3.0-72-ge848052a；`miles` `f2b7c7929` + `miles-rh2-integration` `98a0272e4`；`verl` 子模块 `ba8cfb6d`；另有 prime-rl/renderers/ROCK/ROLL/AgentEnv/ProRL-Agent-Server/iflow-cli/lmcache/codex/claude-code-typescript-src | 实测 `git -C reference/<x> rev-parse`；`.gitmodules`；`git ls-files reference` 只含 verl 与 claude-code-docs | 有产物（本地未跟踪） |
| **不存在**：`reference/` 下无 SWE-smith、R2E-Gym、SWE-Gym（官方仓）、swe-rebench 的克隆；只有精读笔记（E5 SWE-smith、O03 R2E-Gym、O11 SWE-rebench V2）和 `project1_design_advice_20260907.md:78` 的链接 | 实测 `find reference -maxdepth 1 -iname ...` 无命中 | 只有文档 |
| `rh2/.venv`（Python 3.12）：swebench 4.1.0、huggingface_hub 1.22.0、datasets 4.6.1、pyarrow、pyyaml（`data` 依赖组）；仓库根 `.venv` 没有这些包 | 实测 import；`rh2/pyproject.toml` dependency-groups | 有产物 |
| HF 缓存数据集：`datasets--SWE-Gym--SWE-Gym-Lite`（f70b1a29，parquet）、`SWE-bench--SWE-bench_Verified`（91aa3ed5）、`princeton-nlp--SWE-Bench_Verified`（c104f840）、`SWE-bench--SWE-bench_Lite`、`princeton-nlp--SWE-bench_Lite`、`ScaleAI--SWE-bench_Pro`（7ab51149）；**无 SWE-Gym Full parquet、无 R2E-Gym-Subset** | 实测 `ls ~/.cache/huggingface/hub` | 有产物 |
| HF 缓存模型：Qwen3-30B-A3B / Qwen3-8B / Qwen3-0.6B / Qwen2.5-Coder-7B-Instruct 只有元数据（各 11–15 MB，无权重）；无 Qwen3-4B；唯一 safetensors 是 whisper | 实测 | 不可用（无权重） |
| Docker 29.4.1（desktop-linux，Apple Silicon）；x86 镜像本机 = QEMU 模拟 | 实测 `docker info` | 有产物 |
| 反作弊/沙箱探针脚本（运行期）：`git-sanitize.sh`、`git-future-probe.sh`、`grader-trusted-init.sh`、`grader-protect-control-surface.sh`、`rollout-*-probe.sh`、`storage-quota-probe.sh`、`h7_boundary_probes.sh` | `rh2/scripts/sandbox_probes/` | 只有代码 |

---

## 9. 环境生产设计文档 vs 代码

**结论**：设计文档定义的 9 阶段流水线里，只有"字段拆分 + 包冻结 + 来源 digest 账本"三段有代码与产物，"静态质量打标"有另一套简化产物；镜像构建、anti-cheat 报告、验证门、质量报告 schema、benchmark card 全部没有对应实现。

文档：`docs/harness_improve/environment_production_and_quality_pipeline_design.md`（148 行）。章节：1 文档定位 / 2 总体流水线 / 3 EnvironmentBuilder·TaskIngestionPipeline（9 项职责）/ 4 TaskQualityEvaluator / 5 验证门槛 / 6 Anti-cheat 准备 / 7 输出物 / 8 不进入高层架构的内容。

| 文档声称的阶段或输出 | 对应代码 / 产物 | 状态 |
| --- | --- | --- |
| Source Intake（PR/issue/fixture/合成/benchmark item） | 只有 HF 数据集拉取：`data_freeze/meta/fetch_meta.sh`、`fetch_r2e.py`、`rh2/experiments/s2_1_ingestion/fetch_raw_lite.py`；无 PR/issue 采集 | 只有代码（仅 benchmark item 一种） |
| Repository Snapshot（固定 base commit、依赖锁） | 依赖数据集自带 base_commit + xingyaoww 预构建镜像；自身只做 digest 解析 | 有产物（借用上游） |
| Diff / Test Split | strip_spec 六类归属 → 三分 bundle（public / grading v2 / validation-only） | 有产物 |
| Task Draft（生成 prompt、公开/隐藏约束） | 题面原样 + 固定 `PUBLIC_SYSTEM_HINTS`；无改写 | 只有代码（固定模板） |
| Dependency And Image Build | 无；不自建镜像 | 不存在 |
| Anti-cheat Preparation（git 历史净化、future refs、remote refs；`AntiCheatSpec` 回写包 digest） | 运行期脚本 `rh2/scripts/sandbox_probes/git-sanitize.sh`、`git-future-probe.sh`、sandbox_profile egress relay；契约只有运行期 `rh2.anti_cheat_finding.v1`；**没有逐包 AntiCheatSpec / git_sanitizer_report 产物** | 只有代码（运行期），无产物 |
| Validation Runs（empty / golden / determinism / 训练 runtime 复验） | 无（T2-e，见 §4） | 只有文档 |
| Task Quality Evaluation（`task_quality_report` 六字段 schema） | 另一套：三标签 LLM 打标 jsonl（issue_clarity / test_adequacy / solution_leakage），无 evaluator_version / evidence_refs / rewrite_suggestion_ref 字段，也没挂到包上 | 有产物（schema 不同） |
| EnvironmentPackage Freeze | `EnvironmentPackageV1`（只有身份 + 三 bundle digest + provenance digest）+ pins 链 | 有产物 |
| 输出物：EnvironmentPackageSpec / TaskPackSpec / EnvConfig / EnvironmentValidationReport / TaskQualityReport / AntiCheatSpec / SWEEnvPackageProfile / benchmark_card_ref / source_digest_manifest | 只有 EnvironmentPackageV1（字段集与 Spec 不同，无 validation/quality/anti_cheat ref）与 source digest 账本（`freeze_manifest_v0.json`、`s2_1_manifest_v0.json`、`t1_input_pins_v1.json`）；其余七项都没有 schema 或产物 | 2/9 有产物 |
| §5 准入条件（empty_patch_must_fail = golden_patch_must_pass = determinism_check = passed ∧ verified_in_training_runtime ∧ 两个 ref 非空） | 216 题没有任何一项达成 | 只有文档 |

---

## 10. 文档声称与实际不符的地方

1. **"216 题 / 11 个仓库"**：Lite 是 11 仓库，216 survivor 只剩 **9 个**（hydra 11 题 + bokeh 1 题被 D5 剔除）。`CURRENT-STATE-BRIEF.md:75`、`s2_1_t2_report.md` T2-a 说"SWE-Gym Lite 全部 11 个仓库零覆盖"对 Lite 成立，但不要把 216 描述成 11 仓库。
2. **T2-a 报告的评分形态推论**："运行期评分 = 容器内 test_cmd + 测试选择器 + 官方 log parser"——官方 parser 对这 9 个仓库没有条目，代码里 `_parse` 仍走 `make_test_spec`，对 216 题必然 `KeyError`（§3 实测）。vendor 决策只覆盖了 eval_cmd，没覆盖 parser。
3. **freeze_manifest 不变量 "ps-warn 存活题带 leakage_watch 标记进池，leakage_evidence 随行保留"**：ingestion 产物里没有这个字段；13 题 warn 无法从 bundle/package 识别。
4. **s2_1 计划 §3.0** 写 PrivateGradingBundleV2 携带 `eval_script`；实际只携带 `eval_cmd`（T2-a 推论后改），计划文字过时。
5. **s2 implementation-notes** 说 `data_freeze/image_manifest.md` "只记录了 `_s_` 替换未写小写化，待回写勘误"——当前 `image_manifest.md` 已写明"整体转成小写"且 jq 用 `ascii_downcase`；要么已回写，要么该 note 本身不准确。
6. **CC 版本**：7a 报告实跑 2.1.202；代码默认与 fa 行为画像验证的是 2.1.205。历史数字对应的 CC 版本与当前 pin 不同。
7. **data_freeze_report "存活 216（后续进 GPU pass-rate 预筛，最终 bring-up 用 100~200）"** 与 guide §10 "待做 1/2"：预筛与环境门都没跑；bring-up 题单不存在。
8. **04 计划的四门（假阳性为硬门）与 heldout_proposal 的"每题 2 次"**：已被 s2_1 计划 O-3（N=3）/O-4（假阳性降为探针）改掉，旧文本未同步。
9. **`scoring.py` docstring** 按 `MAP_REPO_TO_PARSER` 在 `swebench.harness.constants` 叙述；4.1.0 里它在 `swebench.harness.log_parsers`（`constants` 导入会 ImportError）。仅文字，不影响运行（运行路径用 `make_test_spec`）。
10. **`06` 计划 T2-d/T2-e 行"由既有数据线程继续"**：自 2026-07-20（`s2/ingest` 最后修改）之后数据线没有任何新代码或产物；`s2/dev_dialog.md` 最后一条是 2026-07-24 协作方式定案。

## 11. 我没找到 / 不确定的

- **远端是否拉过任何 xingyaoww 镜像**：无记录；本机 0 个。216 镜像总体积只有抽样外推。
- **mypy 40 题 `-k` 结尾的 eval_cmd 与 conan 12 题的 `eval_commands`** 在渲染脚本里是否正确——没有任何容器实跑过，只能标"可疑"。
- **dask 14 + pandas 5 题 `python_version=None`** 是否影响评分（镜像内 conda env 已就位，应无影响，但未验证）。
- **run6–9 的逐 rollout CC 轮数与时长分布**：summary 只有均值/最大；`bringup_events.jsonl` 有 `wall_seconds` 逐条，但轮数需从 trajectory projection 反推，仓库只留 1 条完整 projection。
- **本机 CC linux tarball**：未找到；fa 文档提到 macOS 本地二进制 `~/.local/share/claude/versions/2.1.205` 用于探针，未核对是否仍在。
- **`docs/.../s2/codex_reviews.md`（382 KB）与 `runs/`（2026-05 V4/V5 时代）**：未通读，与本盘点无直接关系。
- **R2E-Gym-Subset 的 golden/测试材料**：从未抓取，held-out 中 450 题（tornado/pyramid）实际可用性无从判断。
- **`research-environments` 里 swebench/r2e_gym/swerebench 封装**是否能直接复用作 parser/评分参考：只列了目录，未读实现。
