# getmoto/moto 仓库级共性事实（L1_moto_2，静态）

2026-09-16 夜 · 只读证据，未起容器。以下结论对本包 20 题共同适用，题级 JSON 用 `repo_level_findings.md#<锚>` 引用，不逐题重复抄。

## R1. 配方来源与 `python: 3.12` 是整仓通刷值（非逐版本核对）

`SPECS_MOTO` 对 `0.4 … 5.0` 全部 14 个版本用同一个字典：`python="3.12"`、`install="make init"`、`test_cmd="pytest -n0 -rA"`。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/vendor/swegym_constants_242429c1.py:1703-1718`。
含义：本包 20 题的 `python_version=3.12` 不是按 moto 4.0（2022-08）/4.1（2023-01）实际 CI 校准的结果，只是 SWE-Gym fork 的一刀切值。镜像里确实是 Python 3.12.4（见 R2 日志），因此不是"配方与镜像不一致"，但**它不构成"该版本历史工具链已恢复"的证据**（检查 6）。

## R2. moto 4.1 的 `make init` 在离线下必然 rc=2；4.0 rc=0 —— 原因是 Makefile 换了安装命令

- 4.0（如 5406 base `87683a786f`）`Makefile:init` = `@python setup.py develop` + `@pip install -r requirements-dev.txt`。legacy editable，**无 PEP 517 构建隔离**，不需要联网 → rc=0。
  证据：`87683a786f0d3a0280c92ea01fecce8a3dd4b0fd:Makefile`（init 段）；日志 `runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5406/gold/offline/a1/test_output.txt:613,619-620`（`Legacy editable install of moto[all,server]==4.0.0.dev0 from file:///testbed (setup.py develop)`，`RH2_PHASE_END install ... rc=0`）。
- 4.1（如 5835 base `6da12892a3`）`Makefile:init` = `@pip install -e .` + `@pip install -r requirements-dev.txt`。`pip install -e .` 走 PEP 517 构建隔离，要现下载 `setuptools>=40.6.0`；离线 DNS 解析失败 → `make: *** [Makefile:18: init] Error 1` → rc=2，**第二条 `pip install -r requirements-dev.txt` 根本没执行**。
  证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5835/gold/offline/a1/test_output.txt:431-461`。
- 影响面：本包 12 道 4.1 题（5835/5865/5885/5960/5980/6022/6041/6114/6121/6157/6178/6185）`rc_install=2`；8 道 4.0 题（5406/5478/5502/5620/5699/5737/5752/5794）`rc_install=0`。
  证据：`docs/.../env_overnight_20260916/task_signals_swegym.json` 中各题 `stage1.{empty,gold}.rc_install`。

## R3. 安装失败**不**妨碍候选代码被测（检查 9 的因果证据）

5835 的 empty/gold 两次运行在同一 rc=2 条件下得到不同逐测试结果：empty `...::test_put_parameter_invalid_type = FAILED`（80 PASSED / 1 FAILED），gold 同一 ID `PASSED`（81 PASSED）。
证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5835/{empty,gold}/offline/a1/status_map.json`。
结论：镜像自带的 editable 安装已指向 `/testbed`，`make init` 对结果是冗余步骤；rc=2 是**假报警**。
残余风险（未验证，`not_checked`）：(a) 若候选新增第三方依赖，离线下无法安装且不会有明确报错路径；(b) 若 RH2 把 `install_rc != 0` 当可信归因的负信号，12 道 4.1 题会被系统性判 0 —— 阶段一证据显示当前**没有**这样判（gold 仍 RESOLVED_FULL），但这是配方级风险点，值得用户确认。
建议动作（未实施）：moto 4.1 配方把安装改成 `pip install -e . --no-build-isolation`，或在镜像预置 setuptools wheel；改动只影响 `getmoto/moto` 4.1+，需按检查 39 重验受影响题。

## R4. 仓库含 git 子模块，题面材料不含它

`.gitmodules` 声明 `tests/terraformtests/terraform-provider-aws → https://github.com/hashicorp/terraform-provider-aws/`。
证据：`87683a786f0d3a0280c92ea01fecce8a3dd4b0fd:.gitmodules`。
本包 20 题的 F2P/P2P 全部不在 `tests/terraformtests/` 下，`eval_cmd` 也按文件/ID 选择，所以**当前不影响判分**；但"仓库全量 pytest"或任何递归收集会受影响。逐题记为 `not_applicable` + 理由。

## R5. `setup.cfg` 声明 `network` marker，但 eval 命令不带 `-m "not network"`

证据：`87683a786f0d3a0280c92ea01fecce8a3dd4b0fd:setup.cfg`（`[tool:pytest] markers = network: marks tests which require network connection`）；`eval_cmd = "pytest -n0 -rA"`（各题 `grading.json`）。
逐题已 grep 被改测试文件里的 `mark.network`，本包内命中为 0（详见各题 checks.11）。

## R6. 测试依赖 `sure` 断言库（`.should.have.key(...)`）

`requirements-tests.txt` = pytest / pytest-cov / pytest-xdist / sure / freezegun / pylint（证据：`87683a786f0d3a0280c92ea01fecce8a3dd4b0fd:requirements-tests.txt`）。
含义：候选若"重写测试风格"无意义（测试会被恢复）；但 agent 在开发侧自己写复现脚本时不需要 `sure`。镜像里 `sure` 已装（R2 日志里 requirements-dev 全部 already satisfied）。

## R7. 判分文件边界：本包 20 题的 `test_patch` 全部只碰 `tests/` 下文件

无一例碰到 `moto/` 源码，因此第四组 B 的"`test_files` 由 `test_patch` 全部触碰路径生成会把正常源码恢复覆盖"这一残余风险在本包**未出现**；`additional_exclusions` 逐题均为 `[]`。
唯一需要单独说明的是 `getmoto__moto-5737` 的 `tests/test_cloudfront/cloudfront_test_scaffolding.py`（测试辅助模块，非 `test_*.py`，但确在 `tests/` 下且职责纯为测试脚手架）——仍属测试侧，恢复它是正确行为。

## R8. 参数化测试 ID 被日志解析器按空格截断，多个用例塌缩成同一个键（P1/P2，跨仓库）

**机制。** 上游 parser 逐行 `line.split()` 后用 `test_case[1]` 当测试 ID、`test_case[0]` 当状态：
`docs/agentic_RL/repo_harness_rh2_workstreams/s2/vendor/swegym_log_parsers_242429c1.py:16-25`（`parse_log_pytest`；第 315/319 行 `parse_log_moto = parse_log_pytest`，`"getmoto/moto": parse_log_moto`）。
pytest 参数化 ID 里只要含空格，ID 就在第一个空格处被截断；**同一截断键上后写的状态覆盖先写的**（`test_status_map[test_case[1]] = test_case[0]`）。
SWE-Gym 的 `FAIL_TO_PASS/PASS_TO_PASS` 参考集是用同一个 parser 从官方日志生成的，所以参考集里存的也是截断 ID —— 两边"一致地错"，于是 `p2p_missing/f2p_missing` 都是 0，异常被完全吞掉。

**实证（本包，阶段一离线日志）。**
- `getmoto__moto-5620`：`tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py::test_update_item_with_duplicate_expressions[set` 这一个参考键，对应日志里 2 条真实 ID（`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5620/gold/offline/a1/test_output.txt:885-886`）；`status_map.json` 只有 1 个键、31 条记录（=29 P2P + 2 F2P）。参数化定义见 `80db33cb44:tests/test_dynamodb/exceptions/test_dynamodb_exceptions.py:582-589`。
- `getmoto__moto-6178`：日志 32 条真实结果行被压成 21 个键，恰好等于参考集 2 F2P + 19 P2P = 21。其中 **F2P 键 `...::TestHashAndRangeKey::test_brackets[(job_id` 一个键对应 2 条真实用例**——即 reward 判据本身被塌缩。6 个参考键共吞掉 17→6，11 条用例结果不进账。
- `getmoto__moto-5960`、`getmoto__moto-6185`：各 1 个 P2P 键塌缩 2 条用例。
- `getmoto__moto-5502 / 5752 / 5835`：各 15 个 P2P 键是截断 ID（`test_describe_parameters_invalid_parameter_filters[filters*-...`、`test_put_parameter_invalid_data_type[something`），当前一一对应未塌缩，但 ID 不稳定。
- `getmoto__moto-5865 / 6121 / 6157 / 6041`：F2P/P2P 含截断 ID，当前一一对应。

**影响。** (a) 塌缩键上的失败可被同键的另一条 PASSED 覆盖，**在 F2P 上会产出假阳性 reward**（6178 已具备这个结构）；(b) 逐测试对账数量与真实执行数量不一致，`facts.json` 的"逐 ID 状态表"会少记；(c) 一旦将来换用 JUnit/CTRF 或改 parser，参考集里的截断 ID 会突然全部 `reference_missing`，形成"修 parser 反而全红"的陷阱。

**波及面（全池静态统计）。** 216 题中 **35 题**的 F2P/P2P 含"有 `[` 但不以 `]` 结尾"的截断 ID：getmoto/moto 20、iterative/dvc 5、modin-project/modin 4、pandas-dev/pandas 3、dask/dask 2、conan-io/conan 1（统计脚本按 `grading_bundles_v2_v0.jsonl` 逐题扫描；本包 20 题里命中 11 题）。

**与既有信号的矛盾。** `task_signals_swegym.json` 给本包全部 20 题标 `fragile_reference_id: false`，包括 5620/6178。说明现有"脆弱参考 ID"检测没有覆盖"参数化 ID 含空格被截断/塌缩"这一类，建议把判据补成"参考 ID 含 `[` 但不以 `]` 结尾"或"同一截断键命中多条日志行"。

**建议动作（未实施，属 T0 评分语义，交用户裁定）。** 优先级从低到高：
1. 只做观测：在 facts 里额外记录"日志真实结果行数 vs 参考键数"的差，塌缩时标 `collapsed_ids`，不改 reward。
2. 改 parser 为 `line.split(maxsplit=1)` 取剩余全部作为 ID，并**同步重建参考集**（属检查 37 的"任务修订"，必须与原版分开计分）。
3. 改用 pytest 的 `--junitxml` 逐 ID 结果作为权威，参考集做一次带版本的 ID 映射修订。
方案 2/3 都会改变参考集身份，不能声称与原 benchmark 分数可比。

## R9. 判分按**整个测试文件**执行；离线容器里 `tests/test_s3/test_server.py` 有一条测试必然失败，但因不在参考集而被无声吞掉

**机制。** `eval.sh` 的测试阶段是 `pytest -n0 -rA <test_patch 触碰的文件>`（证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5835/gold/offline/a1/eval.sh` 第 51 行 `pytest -n0 -rA tests/test_ssm/test_ssm_boto3.py`）。文件里不在 F2P/P2P 的测试同样会被执行，只是结果不进对账。

**实证（6121 与 6157，gold 与 empty 四次运行一致）。** `tests/test_s3/test_server.py::test_s3_server_post_cors_multiple_origins` 启动 `ThreadedMotoServer(port="6789")` 并用 `requests` 访问 `http://testcors.localhost:6789/`（`fe1869212f:tests/test_s3/test_server.py:282-347`），在离线容器里因为无法解析 `testcors.localhost` 而失败：
`requests.exceptions.ConnectionError: HTTPConnectionPool(host='testcors.localhost', port=6789): ... NameResolutionError(... [Errno -3] Temporary failure in name resolution)`
（证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-6157/gold/offline/a1/test_output.txt:429-1045`，同目录 6121 的 gold/empty 日志同样 `1 failed, 12 passed`。）

**后果。** 这两题的**测试阶段退出码是 rc=1**（`...getmoto__moto-6157/gold/offline/a1/test_output.txt:`「RH2_PHASE_END test ... rc=1」；6121 的 gold 与 empty 同为 rc=1），但两题仍判 RESOLVED_FULL，因为失败项不在参考集内。这说明：
1. `pytest` 退出码在当前配方下**不能**作为运行健康度信号（与安装 rc 的情况相反：安装 rc 非零是假报警，测试 rc 非零也是假报警）；
2. 存在"参考集外的环境性失败"这一整类不进账的信息，`facts.json` 应单独记录"参考集外失败数/原因"；
3. 若将来把"测试阶段 rc != 0"接进候选执行失败归因，这两题会被系统性判 0。

**建议动作（未实施）。** 容器准备阶段往 `/etc/hosts` 加 `127.0.0.1 testcors.localhost`（或等价的解析配置），使该测试在离线下可通过；改动只影响用到 `*.localhost` 子域的测试，按检查 39 标明适用范围后重验。也可选择保持现状但在事实层显式记录该失败，避免它在换配方时突然变成"新回归"。

## R10. 一刀切的 Python 3.12 在 moto 4.1 上确实制造了真实失败（本轮恰好都在参考集之外）

`tests/test_ec2/test_instances.py::test_create_instance_with_launch_template_id_produces_no_warning[LaunchTemplateId/Name]` 在 5980 的 gold 与 empty 运行里都 FAILED，原因是测试用 `warnings.simplefilter("error")`（`dae4f4947e:tests/test_ec2/test_instances.py:2316`）把 botocore 自己调用 `datetime.datetime.utcnow()` 产生的 `DeprecationWarning` 变成异常——`utcnow()` 正是 Python 3.12 才开始弃用的。
证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-5980/gold/offline/a1/test_output.txt:425-492`（`E DeprecationWarning: datetime.datetime.utcnow() is deprecated ... /botocore/auth.py:419`）。

这两条不在 5980 的参考集内，所以不影响判分；但它把 R1 的风险坐实了：**配方把 python 固定成 3.12 不是按版本校准的结果，它会让为旧 Python 写的测试失败。**

反向核对（全池）：216 题里只有 `getmoto__moto-7495`（moto 5.0，属 L1_moto_3 包）的 P2P 含这两个 ID，而 5.0 的上游已把该测试改写成 `warnings.catch_warnings(record=True)`（`009d0191f9:tests/test_ec2/test_instances.py:2375`），所以它在阶段一是 PASSED。
证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/getmoto__moto-7495/gold/offline/a1/test_output.txt:561-562`。
结论：**当前 216 题的参考集里没有被 python 3.12 直接打坏的 moto 用例**，但这是巧合而非保证；换镜像、换 botocore 版本或扩池时需要重查。

## R11. 本包 20 题的 no-op / gold 逐测试对照（检查 2 与 20 的直接证据）

对全部 20 题读取阶段一 `status_map.json` 得到：**每一题的全部 F2P 在 empty 下都是 FAILED、在 gold 下都是 PASSED；empty 下没有任何 P2P 失败（20 题合计 0 条）。**
证据：`runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/<instance_id>/{empty,gold}/offline/a1/status_map.json`；汇总脚本输出留在 `/tmp/l1moto2_stage1_summary.json`（临时文件，不是证据原件）。
限定：对 R8 里被塌缩的键（5620、5960、6178、6185 的若干键，其中 6178 是 F2P），这条结论只反映"同键最后写入的那条真实用例"，不等于每条参数化用例都被单独核对过。

## R12. agent 可见的 `public_hints` 全池同一份；有两处措辞值得核对（检查 3 / 4 / 10）

216 题的 `public_bundles_v0.jsonl.public_hints` 是同一个字符串（sha256 前缀 `4c44aa0b42`，216/216），`allowed_tools` 全部是 `["bash","edit"]`、`workdir` 全部是 `/testbed`。
证据：`docs/agentic_RL/repo_harness_rh2_workstreams/s2/ingest/public_bundles_v0.jsonl`（本包 20 题快照见 `runs/env_overnight_20260916/L1_moto_2/mat/<id>/public.json`）。

两处措辞（**建议，未定案**）：
1. 原文说 *"grading resets the test files to their original state"*。实际恢复的是**注入 test_patch 之后的状态**，不是 base 的原始状态。对判分结果没有影响（agent 改测试都不算数这一点是准确的），但\"original state\"容易让 agent 以为隐藏测试就是它在 `/testbed` 里看到的那份，从而错误推断验收标准。
2. 原文鼓励 *"You may run tests to verify your fix, but keep runs narrow (a single test file or module)"*。对 `getmoto__moto-6121 / 6157` 这两题，agent 若按建议跑 `tests/test_s3/test_server.py`，会看到一条与它无关的失败（R9 的 `testcors.localhost` 解析失败）；对 `getmoto__moto-5980`，跑 `tests/test_ec2/test_instances.py` 会看到两条与它无关的失败（R10 的 Python 3.12 DeprecationWarning）。这属于检查 10 的\"开发侧验证条件\"问题：agent 拿到的本地信号里混了确定性的环境噪声。修 R9/R10 的环境问题即可消除，无需改提示词。
