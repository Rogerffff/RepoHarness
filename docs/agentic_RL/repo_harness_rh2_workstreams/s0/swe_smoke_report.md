# S0-7 SWE smoke 报告（SweSmokeTaskset × 官方 SWE-bench Verified 镜像 × deepseek-chat）

执行日期：2026-07-07（远程单卡 RTX PRO 6000 vast 实例，Docker 28.1.1，x86_64）。
执行说明：前一线程实现代码后被 session limit 中断，本轮由续跑线程核验、远程执行并收口。
验收结论先行：**8/8 题端到端跑通（rollout 完成且官方评分产出），7/8 题 RESOLVED_FULL（reward=1.0），超过 ≥5/8 的验收底线**。

- 代码：`rh2/src/repoharness2/taskset/swebench_smoke.py`（SweSmokeTaskset）、
  `rh2/experiments/s0_swe_smoke.py`（单题 runner）、`rh2/experiments/s0_swe_smoke_run_all.sh`（顺序驱动）、
  `rh2/experiments/s0_swe_smoke_prep.py`（题单冻结脚本）
- 冻结数据：`rh2/src/repoharness2/taskset/data/swe_smoke_tasks.json`（swebench 4.1.0 生成）
- 逐题 trace dump（已做密钥扫描）：`s0/swe_smoke_dumps/<instance_id>.json`（36~90KB/题，完整 nodes，未触发摘要降级）
- 官方 eval 原始日志：`s0/swe_smoke_dumps/eval_logs/<instance_id>.eval.log`（共 428KB）
- 远程工作目录（用户自管实例电源）：`/workspace/claude-code-verl-stage0h/rh2/swe_smoke_out/`（含 `attempts/` 失败轮归档）

## 1. 题单（初选待用户过目冻结）

**状态：初选 8 题，待用户过目后长期冻结**（C6 流程；选题标准见 `s0_swe_smoke_prep.py` docstring：
官方预构建 x86_64 镜像逐题核对 Docker Hub manifest、Python 主流仓库、单题测试 <5 分钟）。

| # | instance_id | repo | version | F2P | P2P | 镜像 manifest digest（前 12 位） | 官方测试命令族 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | django__django-11099 | django/django | 3.0 | 3 | 19 | sha256:57060beb3096 | runtests.py 按模块 |
| 1 | django__django-11133 | django/django | 3.0 | 1 | 64 | sha256:cf92d32f28cf | runtests.py 按模块 |
| 2 | django__django-16139 | django/django | 4.2 | 1 | 86 | sha256:f8c120d58e3e | runtests.py 按模块 |
| 3 | sympy__sympy-14711 | sympy/sympy | 1.1 | 1 | 2 | sha256:4285e771c489 | bin/test 单文件 |
| 4 | sympy__sympy-15349 | sympy/sympy | 1.4 | 1 | 3 | sha256:b10d13ced1fd | bin/test 单文件 |
| 5 | psf__requests-1142 | psf/requests | 1.1 | 1 | 5 | sha256:9b0b13a4a762 | pytest -rA |
| 6 | psf__requests-2931 | psf/requests | 2.9 | 1 | 84 | sha256:f3c752f9cb9f | pytest -rA |
| 7 | astropy__astropy-14995 | astropy/astropy | 5.2 | 1 | 179 | sha256:b29a3bf3daeb | pytest -rA |

镜像引用形态：`swebench/sweb.eval.x86_64.<instance_id 中 __ 换成 _1776_>:latest`；
运行时 runner 逐题核对本地 RepoDigest 与冻结 manifest digest，8/8 `digest_match=True`。

## 2. 运行配置

- 链路：`EnvConfig(taskset=swebench_smoke, harness=default(bash+edit), runtime=docker)` →
  `Environment.episode(task, ctx, n=1)`；per-task 官方镜像，`workdir=/testbed`。
- 模型端点：EvalClient → `https://api.deepseek.com`，`deepseek-chat`，temperature=0、max_tokens=4096、max_turns=30。
  key 经 ssh stdin 注入远程进程环境变量（不落远程磁盘/不进 argv/不回显）；dump 落盘前 scrub + assert 双重剔除，
  产物回传前后各做一次 `sk-` 形态与 key 字面值全量扫描，均 0 命中。
- agent 环境：taskset.setup 写入 `/root/.rh2_bash_env`（`source /opt/miniconda3/bin/activate testbed`），
  harness env 设 `BASH_ENV=/root/.rh2_bash_env`，使 agent 每次 bash 调用都在 conda testbed 环境。
- 评分：同容器跑官方 eval 脚本（make_test_spec 生成，冻结在题单数据里），swebench 4.1.0 官方 grading 函数解析。
  **S0 不做评分隔离**（agent 用过的容器直接评分，理论上可被篡改），隔离是 S2 验收项。

## 3. 逐题结果

| instance_id | reward | resolution | 轮数 | wall(s) | setup(s) | generation(s) | scoring(s) | F2P/P2P 通过率 | tokens in/out |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| django__django-11099 | 1.0 | RESOLVED_FULL | 7 | 27.1 | 3.9 | 13.1 | 9.2 | 1.00 / 1.000 | 2039 / 784 |
| django__django-11133 | 1.0 | RESOLVED_FULL | 16 | 46.2 | 3.8 | 32.7 | 8.8 | 1.00 / 1.000 | 4419 / 2000 |
| django__django-16139 | 1.0 | RESOLVED_FULL | 28 | 98.5 | 4.0 | 88.0 | 5.8 | 1.00 / 1.000 | 8594 / 5110 |
| sympy__sympy-14711 | 1.0 | RESOLVED_FULL | 18 | 50.6 | 3.4 | 41.9 | 4.6 | 1.00 / 1.000 | 6472 / 2538 |
| sympy__sympy-15349 | 1.0 | RESOLVED_FULL | 9 | 31.3 | 3.5 | 22.8 | 4.4 | 1.00 / 1.000 | 3333 / 1551 |
| psf__requests-1142 | 1.0 | RESOLVED_FULL | 13 | 41.7 | 3.3 | 34.8 | 3.1 | 1.00 / 1.000 | 8263 / 2439 |
| psf__requests-2931 | 0.0 | RESOLVED_NO | 18 | 49.9 | 3.5 | 42.5 | 3.3 | 1.00 / 0.988 | 6662 / 2892 |
| astropy__astropy-14995 | 1.0 | RESOLVED_FULL | 12 | 81.7 | 3.5 | 40.9 | 36.6 | 1.00 / 1.000 | 8281 / 2514 |

- 8/8 `stop_condition=agent_completed`（无超时/无错误终止），`eval_apply_ok` 8/8 为 1.0。
- 均值：wall 53.4s/题（区间 27.1~98.5），轮数 15.1；全程 tokens 48,063 in / 19,828 out。
- 唯一未解出题 psf__requests-2931：agent 的修复（`requests/models.py` 对 bytes 直接返回不做
  native-string 转换）让 F2P 全过，但引入 P2P 回归 `test_params_bytes_are_encoded`（TypeError），
  官方语义下 f2p=1.0 且 p2p<1.0 → RESOLVED_NO、reward=0。这是 reward 判据（仅 RESOLVED_FULL 得 1）
  按预期工作的活案例。

## 4. 计时与资源（关闭 U-D）

- **镜像拉取**：8 镜像并行（xargs -P4）总 wall 52s；单镜像 3~38s；单镜像标称 2.48~2.82GB，
  实际磁盘占用共 **8.13GB**（共享基层，`docker system df`）。执行计划预留 ~50GB 属于大幅高估，
  同家族题目的边际磁盘成本约 0.1~0.7GB/题。
- **env_reset（容器启动 + 物化校验 + BASH_ENV 注入）**：3.3~4.0s/题，非常稳定。
- **官方评分**：2.2~35.7s/题；astropy 最长（scoring 36.6s，其中 eval 35.7s：pip install -e . 重建 + 180 条测试）。
  全部远低于题单静态目标 <5 分钟。
- 端到端：8 题顺序全跑（含评分与 dump 落盘）约 7 分钟纯执行时间。

## 5. 评分日志解析要点（直接喂 S1）

评分链路：eval 脚本 stdout+stderr 合并单流（`2>&1`，官方 harness 同形态）→ `get_logs_eval`
（`MAP_REPO_TO_PARSER` 按 repo 选 parser，切 `>>>>> Start/End Test Output` 标记之间的段）→
`get_eval_tests_report` 对照冻结 F2P/P2P 清单 → `get_resolution_status`。要点：

1. **三种日志形态、三个官方 parser 均已实测**：
   - django：unittest verbose 行 `test_validate (auth_tests.test_validators.XxxTest) ... ok`；
   - sympy：`bin/test` 行 `test_vector_simplify ok  [OK]`；
   - requests/astropy：`pytest -rA` 摘要行 `PASSED/FAILED/ERROR test_requests.py::TestRequests::xxx`。
2. **ANSI 颜色码不碍事**：astropy 的 pytest 输出带 `\x1b[32m` 等颜色码（容器内无 TTY 也带），
   官方 parser 正常解析（180 条 PASSED 全数入账、F2P 命中）。S1 自研解析时必须先剥 ANSI。
3. **清单制记账，不是全日志记账**：psf__requests-2931 日志里有一条不在 P2P 清单内的
   `ERROR test_urlencoded_get_query_multivalued_param`（联网 flaky 测试），对判定零影响；
   判定只看清单内测试的状态。
4. **silent success 语义**：不在日志出现的 F2P/P2P 按通过计（官方 `check_pass_and_fail` 行为，原样沿用未加严）。
   假阳性护栏是 `apply_ok`（patch 应用失败等坏码会置 False）+ 本轮逐题人工核对了 eval 日志确有测试输出。
   S1 若要加严可以对 `num_parsed_tests=0` 追加 fail-closed。
5. **reward 判据**：`reward = 1.0 当且仅当 RESOLVED_FULL`（F2P 全过且 P2P 零失败）；
   f2p_rate/p2p_rate/eval_apply_ok/eval_seconds 全部进 `trace.metrics` 供训练侧塑形选用。

## 6. 发现（S1 需要吸收的接口契约）

1. **verifiers pin 5885ab9c 的本地插件 id 必须是单段模块名**。多段点分 id
   （如 `repoharness2.taskset.swebench_smoke`）会让 loader 的
   `find_spec("verifiers.v1.tasksets.<id>")` 因中间父包不存在直接抛 ModuleNotFoundError
   （fallback 分支永远走不到），首轮 8 题全部秒败于此。修复：taskset 目录加进 sys.path、
   id 用 `swebench_smoke`（与 S0-2/S0-3 fixture 的"模块名即 id"约定一致）。S1 冻结 taskset
   命名时必须沿用单段约定，或给 verifiers 提 loader 补丁。
2. **官方镜像 /testbed 的物化契约是"血缘"不是"HEAD 等值"，也不是"树内容等值"**（两次实证迭代）：
   - HEAD 一律是构建时叠加的 `SWE-bench` 提交，不是 base_commit（django-11099：
     HEAD=2a2861e0…，HEAD^=d26b2424…=base）；
   - 该提交**不保证内容为空**：astropy-14995 里它带 pyproject.toml 1 行官方环境修补
     （diffstat `1 file changed, 1 insertion(+), 1 deletion(-)`），django/sympy/requests 7 题为空 diff。
   - 最终判据（fail-closed）：base_commit 对象存在 且（HEAD==base 或 HEAD^==base）；
     env 修补 diffstat 记入 trace.info 作证据。评分不受影响：官方 eval 脚本自己
     `git checkout <base> -- <测试文件>` 后 apply golden test_patch。
3. **BASH_ENV 注入 conda testbed 环境的方案有效**：agent 的 `python`/`pip`/测试命令全部落在
   testbed 环境（8 题无一出现"装错环境/找不到依赖"型失败）。
4. **deepseek-chat 有明显背题嫌疑**：7/8 秒解（均值 15 轮、53s），多数 diff 与正典修复高度一致
   （如 11099 的 `^[\w.@+-]+$` → `\A[\w.@+-]+\Z`）。smoke 的验收对象是链路（物化/工具循环/评分解析），
   **这些 reward 数字不能当模型能力基准**；S1 换目标模型（Qwen3-30B-A3B）后预期分布完全不同。
5. **EvalClient 文本中继模式下 token_ids/mask/logprobs 为空是预期行为**（dump meta 已注明）；
   token 保真链路走 S0-5 的 TrainClient 路径，与本任务集正交。
6. **评分与 agent 同容器**（S0 声明性风险）：agent 理论上可篡改测试基建；本轮 8 题 agent diff
   均只碰源码文件（finalize 抓取的 git diff/status 在 dump 里可复核）。隔离方案是 S2 验收项。

## 7. 失败轮归档（远程 `swe_smoke_out/attempts/`）

| 轮次 | 结果 | 根因 | 处置 |
| --- | --- | --- | --- |
| attempt1 | 8/8 秒败（EnvConfig 构造抛错） | 发现 1：多段插件 id 撞 loader find_spec | runner 改单段 id + sys.path |
| attempt2 | 8/8 秒败（setup fail-closed） | 发现 2 前半：HEAD 等值假设不成立 | 校验改"内容等值" |
| attempt3 | 7/8 通过；astropy setup fail-closed | 发现 2 后半：SWE-bench 提交带环境修补 | 校验改"血缘判据" |
| attempt4 | astropy 通过（81.7s） | — | 8/8 收齐 |

三次修复均为实验层/任务集层代码，`reference/verifiers` 与 site-packages 零改动。
