# CPU 环境探针方案（今晚可执行版）

> 执行结果见 [env_probe_20260909/README.md](../env_probe_20260909/README.md)（2026-09-09 夜间执行，Codex 审查稿 `b_probe_preparation_20260909/x86_plan_review_20260909.md` 的五处修正已按其执行：24 题起步、R2E gold 用 `parsed_commit_content` 重建并与 git diff 对拍、严格判定要求参考测试全部出现、省 install 单独对照、216 全量作为环境盘点而非"有信号题占比"）。

日期：2026-09-09。作者：Claude（B 线）。性质：**执行方案建议，未租机、未拉镜像、未调用付费 API；需要用户确认 §6 后开工。**

对应的四个问题：探针对哪些题；要不要扩大 24 题；能否用 DeepSeek API 配 Claude Code 顺带测可解性；参考外部资料环境探针要做哪些内容。先给结论，再给依据和清单。

## 0. 结论

| 问题 | 建议 |
| --- | --- |
| 探针对象 | SWE-Gym：Codex 的 12 题核心批作**校准批**（人工逐题看），校准通过后**当晚自动跑完 216 题全量**四门。R2E-Gym：12 核心 + 12 备用共 24 题，只做环境对照，不扩。 |
| 要不要扩大 24 题 | 分开答。**四门扩**（自动化，边际成本是机器时间，216 题本来就是训练候选池，门 1 的判据需要全池数据）；**API 可解性探针不扩**（按题计费，目的是 harness 级 sanity，24 题够）。 |
| DeepSeek + Claude Code | **可以，但只能走 rh2 编排链之外的独立探针**。DeepSeek 有 Anthropic 兼容端点，Claude Code 用 `ANTHROPIC_BASE_URL` 即可接。rh2 的 Anthropic adapter 是把消息渲染成 token 直发 SGLang，没有"上游是外部 API"的模式；rollout 沙箱是隔离网络 + egress relay 只通模型代理，接公网要改 allowlist（降低安全边界，T0）。 |
| 探针内容 | 在 s2_1 计划已定的四门（empty / gold / N=3 确定性 / 探针层）之上，按外部资料补 **6 项执行事实**：install 步在无网络下的行为、官方宽松与严格两份判定、参考 case 覆盖率、分段耗时、root 与 rh2grader 双身份、镜像内 git 历史与网络可见性。 |
| 今晚已能做的 | 官方评分 fork（pin 242429c1）在本机装通；已对 216 题生成官方 eval 脚本并与 rh2 的 `eval_cmd` 逐题对照（§2）。 |

## 1. 今晚之前已经确认的事实

| 事实 | 依据 |
| --- | --- |
| 216 题三份 bundle 齐全：公开面（题面 + 提示词）、评分面（`test_patch`、F2P/P2P、`eval_cmd`、version）、验证面（golden patch） | `s2/ingest/*.jsonl`，manifest 有 sha256 |
| 216 题镜像 digest 已逐题解析并核过 manifest/config blob | `s2/raw/image_registry_evidence.jsonl` |
| 完整 11 列原始行（含 `patch`、`test_patch`、`created_at`）在本地 | `s2/raw/swe_gym_lite_full_f70b1a29.jsonl`，230 行 |
| 四门 runner 与 `grade_controlled_patch` 受控入口**没有代码**；rh2 grader 只有"从 agent workspace 导出 patch"一个入口 | `grading/manager.py`，grep 无 `controlled` |
| rh2 当前 parser 依赖 swebench 4.1.0，对 9 个仓库 `KeyError`；官方 fork 的 `MAP_REPO_TO_PARSER` 含全部 11 仓 | 本机 scratch venv 安装 fork 后实测 |
| R2E 本地元数据只有 4 列（`repo_name / docker_image / commit_hash / problem_statement`），缺 `parsed_commit_content` 与 `expected_output_json` | `data_freeze/meta/fetch_r2e.py` 的 `COLS` |
| R2E 镜像 HEAD = 修复提交的父提交，且修复提交在 git 历史中存在 | `data_freeze/r2e_prefix_check.md`（2026-07-07，3 仓抽样） |
| 本机 Docker 是 linux/arm64；s2_1 计划 O-2 已定：校准与判题必须在同一台 x86 实例，不用 QEMU 校准后换基质 | `docker version`；s2_1 §8 O-2 |
| rh2 grader 正式身份是 `rh2grader/54322`，rollout 是 `agent/54321`；06 计划 W3b T0(a) 未决：四门若用 root 跑，需用同一 profile 重验 | `sandbox_profile.py`；06 计划 §109 |

## 2. 今晚已完成的一步：官方评分契约对照（本机，无 Docker）

在 scratch venv 里安装 `SWE-Gym/SWE-Bench-Fork@242429c1`，对 216 题调用官方 `make_test_spec` 生成 eval 脚本，与 rh2 评分 bundle 的 `eval_cmd` 逐题比较。产物：`official_cmd_contract_216.json`（同目录，216 行）。

| 统计 | 数量 | 含义 |
| --- | ---: | --- |
| rh2 `eval_cmd` 是官方测试命令的前缀 | 216 / 216 | 前缀一致；但官方命令后面还有测试文件列表或 `-k` 表达式，rh2 bundle 里没有 |
| mypy 用 `-k "<case> or <case>"` 表达式 | 40 | 从 `test_patch` 全文提取 `[case NAME]`，例：`pytest -n0 -rA -k "testTypedDictWithClassmethodAlternativeConstructorDoesNotCrash or testCanCreateTypedDictTypeWithUnderscoreItemName"` |
| conan 有 `eval_commands`（`export PYTHONPATH=...:$(pwd)`） | 12 | 只跑 `test_cmd` 会漏掉 |
| **官方 eval 脚本在跑测试前重新执行 install 步** | **216 / 216**（勘误：首版按关键词匹配写成 196，按 `specs["install"]` 精确匹配后是全部 216 题；pydantic 的 install 是 `pdm add pre-commit; make install;`） | moto `make init`、mypy `pip install -r test-requirements.txt; pip install -e .`、pandas `pip install -ve . --no-build-isolation`（重编译）、dvc/MONAI `pip install -r ...`、pydantic `pdm add pre-commit; make install` |

最后一行是今晚最重要的新事实：rh2 grader 的设计是"clean checkout → 写入官方 test_patch → 跑测试命令"，网络 `deny_all`；官方脚本却在测试前跑 install，其中不少要访问 PyPI。两种可能都要用实测回答：(a) 镜像里依赖已装好，install 步是无网络下会失败但被 `set -xo pipefail`（无 `set -e`）吞掉的空转，verdict 不受影响；(b) 某些仓库（pandas 的 Cython、修改了 setup 的题）不重装则候选补丁不生效，verdict 会变。**这是"我们的评分与官方等价"这个主张的核心证据，必须逐仓库记录。**

## 3. 探针对象与规模

### 3.1 SWE-Gym

| 批 | 题 | 目的 | 人工介入 |
| --- | --- | --- | --- |
| 校准批 | Codex 核心 12 题（9 仓全覆盖；mypy ×2、moto ×2、pydantic ×2；含 1 题空 P2P） | 把 runner 跑通，逐题看日志：install 步行为、parser 是否找全参考 case、耗时 | 逐题看 |
| 全量 | 216 题（含备用 12 题） | 门 1 判据（有信号题占比）需要全池；漏斗账按仓库分组 | 只看异常清单 |

不再单独做 s2_1 计划的"50 题分层抽样 T4"：校准批已经覆盖 9 仓 + 全部特殊命令路径，剩余风险靠全量暴露。全量按 pull → 跑 → `docker rmi` 分批，盘不需要装下 480 GiB。

### 3.2 R2E-Gym

24 题（Codex 12 核心 + 12 备用）。今晚只做三件事，不做 R2E 的 rh2 ingestion：

1. 拉镜像、核 digest、记 HEAD 与 `commit_hash` 的父子关系（复现 r2e_prefix_check 的结论到 24 题）。
2. 无修改跑 `/testbed` 里的 `run_tests.sh`，读容器内 `expected_test_output.json`（Prime 笔记：数据字段缺失时 R2E 运行时从容器内读它），按"预期状态映射精确匹配"判 reward；预期 = 0。
3. gold：在容器内 `git diff HEAD <commit_hash> -- <非测试 Python 文件>` 得到参考修复并应用，预期 = 1。**这一步顺带证明修复提交在镜像 git 历史里可达**，是求解探针必须先做 git 清理的直接理由。

`parsed_commit_content` 的官方 gold 与容器内 diff 若有差异，记录不裁决；正式接入 R2E 时再按 HF 冻结 revision 补拉 24 行全字段（约几十 MB）。

## 4. DeepSeek API + Claude Code 可解性探针

### 4.1 可行性

| 项 | 事实 | 来源 |
| --- | --- | --- |
| 端点 | `ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic`，`ANTHROPIC_API_KEY=<key>`（Claude Code 也接受 `ANTHROPIC_AUTH_TOKEN`，rh2 用的就是它） | DeepSeek 官方 Anthropic API 文档 |
| 模型名 | `deepseek-v4-pro`；`claude-opus*` 自动映射到 v4-pro，`claude-sonnet*`/`claude-haiku*` 映射到 v4-flash | 同上 |
| 支持 | streaming、system、tools/tool_choice、temperature/top_p、stop_sequences | 同上 |
| 限制 | thinking 的 `budget_tokens` 被忽略；`disable_parallel_tool_use` 忽略；**`count_tokens` 未说明**。rh2 adapter 的注释：Claude Code 每轮调 count_tokens 但只当提示，返回 0 也行，所以若 DeepSeek 返回 404 需先用 1 题 smoke 看 CC 是否容忍 | DeepSeek 文档；`adapters/anthropic.py` 第 277 行 |
| 价格 | 官网价格页是脚本渲染，本轮没取到数字；按每题 0.3–1.5M 输入 token、20–50K 输出估，24 题一次不超过 20 美元量级。**以实际账单为准。** | 估算 |

### 4.2 为什么不能走 rh2 编排链

- `slime/agent/adapters/anthropic.py`：把 Anthropic 消息渲染成 chat template，以 `input_ids` 发 SGLang `/generate`，再进 TrajectoryManager。没有"上游是 OpenAI/Anthropic HTTP API"的分支。
- `sandbox_profile.py`：每个 attempt 一张 `--internal` 网络，唯一出口是本 run 的 egress relay，relay 只转发到模型代理上游。让容器访问 `api.deepseek.com` 要改 allowlist，按协作协议属"降低安全边界"，T0。
- 结论：今晚走**独立探针**，明确标注它证明的是"该题在 Claude Code 下能被一个强模型解出"，不证明 rh2 链路；结果字段名 `api_reference_run`，永不进训练统计。

### 4.3 独立探针的做法（与 rh2 尽量同条件）

```text
docker run <image@digest>（同一 x86 实例，默认网络，因为要出网调 API）
  → 装 Node 22 + @anthropic-ai/claude-code@2.1.205 的 npm tarball
      （rh2 pin 是 2.1.205，见 bringup.py RH2_CLAUDE_CODE_VERSION；本机的 2.1.263 不要混用）
  → 建 agent 用户，/testbed 归 agent；先跑 rh2/scripts/sandbox_probes/git-sanitize.sh
      （去 remotes、未来 refs、reflog；否则修复提交在历史里可 `git log` 到）
  → 以 agent 在 /testbed 执行：
      claude -p "<public_hints>\n\n<problem_statement>" \
        --permission-mode bypassPermissions --output-format stream-json \
        --include-partial-messages --include-hook-events --verbose
      env: ANTHROPIC_BASE_URL / ANTHROPIC_AUTH_TOKEN / ANTHROPIC_MODEL=deepseek-v4-pro
           CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1  CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1
      （提示词逐字用 public_bundles_v0.jsonl 的 public_hints，与训练一致；不加额外提示）
  → 预算：wall-clock 30 min、turn 上限按 A 线第 1 组原则先取宽（例如 80）；记录结束原因
  → 结束后 `git diff` 导出 patch（含新增文件），保存 stream-json 全文
  → 用 §5 的官方 oracle 在 fresh 容器评分（不在求解容器里评）
```

先用 1 题（建议 `pydantic__pydantic-8500`，最便宜、无 install 步）smoke：确认 count_tokens、工具调用、stream-json 正常，再跑 24 题。每题只跑 1 次；这是"可解性上界参考"，不是成功率测量。

## 5. 环境探针要做的内容（对照外部资料）

s2_1 计划 §3.1 的四门原样保留：硬门 1 empty 必败（前提测试真跑且 parser 解析成功）、硬门 2 gold 必过（F2P 全过 ∧ P2P 零失败）、硬门 4 empty/gold 各 N=3 全新容器、探针层 3a 无关文件 patch 必败 / 3b gold 删末 hunk 四态。幂等键与账本按 §3.1/§3.2。在此之上补以下 6 项，每项注明来源和记录字段。

| # | 项目 | 做什么 | 记录字段 | 来源 |
| --- | --- | --- | --- | --- |
| E1 | **install 步行为** | 官方脚本原样跑一次（默认网络）、再以 `--network none` 跑一次；比较 install 段退出码、耗时、verdict 是否变化；pandas/dvc/MONAI 重点 | `install_exit_online / install_exit_offline / install_secs / verdict_delta` | §2 实测；O04 §7.4（`set -xo pipefail` 无 `set -e`） |
| E2 | **两份判定** | 同一份日志同时算：官方 `get_eval_report`（SKIPPED 出分母、空参考集 FULL）与严格判定（F2P 全 PASSED ∧ P2P 无 FAILED/ERROR ∧ 参考集非空 ∧ 参考 case 无 SKIPPED） | `official_verdict / strict_verdict / skipped_ref_cases / empty_ref_set` | O04 §7.5、§7.8 |
| E3 | **参考 case 覆盖** | parser 解析出的状态映射里，参考 F2P/P2P 有多少 case 完全缺失（参数化名含空格被截断、`-k` 没选中） | `ref_missing_f2p / ref_missing_p2p` | O04 §7.5；Prime §3.3 |
| E4 | **分段耗时** | 容器启动 / trusted setup（checkout + test_patch）/ install / test / 导出 分开计时；按仓库汇总分布 | `t_start / t_setup / t_install / t_test` | O28a §4.5；DeepSWE 300 s 超时不能套用 |
| E5 | **双身份** | gold 各以 root 和 `rh2grader(54322)` 跑一次（24 题）；记录权限类测试、site-packages 写入的差异 | `verdict_root / verdict_grader / diff_cases` | 06 计划 W3b T0(a)；D2-2 |
| E6 | **可见性** | 镜像内：`git log` 是否含修复提交、是否有未来 tag/remote（SWE-Gym `pre_install` 加了 upstream 并 fetch tags）；`conftest.py`/`pytest.ini`/`setup.cfg` 是否在 test_patch 触碰路径之外；默认网络下能否出网 | `fix_commit_reachable / future_refs / control_files_outside_patch / egress_ok` | O04 §7.3；O28b §3.8；Dressage §4.2；Wave3 控制面口径 |

不做的：LLM judge、自动剔题阈值、EnvValidationReport 大 schema（先用 jsonl 一行一次）、R2E ingestion、合法替代解批量生成（只对 4–6 题人工写，放到明天）。

### 5.1 Runner 用什么

今晚用**官方 fork 作库**（`make_test_spec` 生成脚本，我们自己做 docker 编排约 150 行，parser 用 fork 的 `get_logs_eval` + `get_eval_tests_report`）。它是外部 oracle：任何后续 rh2 grader 的结果都要与它逐题对账。

不用 fork 的 `run_evaluation.py` CLI：它会先 `build_env_images`，要按 tag 伪装 base/env/instance 三层镜像才能跳过构建，而且空 patch 会被直接跳过不跑（O04 §7.6 同类问题），不符合门 1 的前提。

rh2 侧的 B1′（把 fork 的 `log_parsers.py` + `grading.py` 像 constants 一样以同一 pin 冻结为 vendor 资产，加 `grade_controlled_patch` 入口）是明天起的代码工作，要 A 复核；今晚不动 rh2。

### 5.2 账本一行的字段

```text
source, instance_id, image_ref, image_digest, gate, fixture_digest, attempt,
network (default|none), exec_user (root|rh2grader),
install_exit, t_start, t_setup, t_install, t_test, test_exit,
official_verdict, strict_verdict, f2p_pass/f2p_fail/f2p_missing, p2p_pass/p2p_fail/p2p_missing,
skipped_ref_cases, log_sha256, log_path, runner_version, fork_commit=242429c1
```

## 6. 今晚顺序、资源与需要你确认的事

| 步 | 内容 | 依赖 | 预计 |
| --- | --- | --- | --- |
| 0 | （已完成）fork 装通、216 题契约对照 | 无 | 已做 |
| 1 | 租 x86 实例（16 核、≥500 GB 盘、Docker、Docker Hub 登录）；起本地 registry 可选 | **你确认租用** | 0.3–0.8 美元/小时 |
| 2 | 拉 24 SWE-Gym + 24 R2E 镜像，核 digest（约 55 + 15 GiB） | 步 1 | 1 小时 |
| 3 | 校准批 12 题：empty/gold 各 1 次，root，默认网络；逐题看日志修 runner | 步 2 | 2–3 小时 |
| 4 | 校准批：N=3、`--network none`、rh2grader 身份、3a/3b 探针 | 步 3 | 2 小时 |
| 5 | 216 全量连夜跑（pull-run-rmi，并发 4–8） | 步 4 | 10–20 小时 |
| 6 | R2E 24 题：digest、HEAD/父提交、无修改 0、容器内 diff gold 1 | 步 2，可与 3 并行 | 2 小时 |
| 7 | DeepSeek + CC：1 题 smoke → 24 题 | 步 2 + **你给 key 与预算** | 3–5 小时墙钟 |

需要你确认的四件事：

1. **租 x86 CPU 实例**（预计总费用 10–20 美元）。
2. **DeepSeek key 与费用上限**（建议 30 美元封顶），以及接受"独立探针不走 rh2 链"的方法论；结果标 `api_reference_run`。
3. **双身份都跑**（root 与 rh2grader），为 W3b T0(a) 提供证据；不在今晚裁决用哪个。
4. **216 全量连夜跑**是否放行；不放行则只跑 24 校准批 + 24 R2E。

## 7. 简历级质量的最低要求

镜像按 digest 引用；runner 与账本 schema 进仓库（`rh2/experiments/` 下新目录，不改 rh2 包）；两份判定并列、不删题；漏斗账按仓库分组呈现；官方 oracle 与 rh2 grader 的逐题对账在 B1′ 后补做；DeepSeek 结果只作参考不进任何成功率；每一次运行的网络与身份条件可追溯。
