# getmoto__moto-6470 · 反例预期与证明力

**疑点（`solvability_review_20260909/01_failure_cases.md` §2）：** 题面只说"返回 500"，
没说正确结果是成功还是 400。候选选了"放宽输入、让请求成功"，gold 选了"这类请求非法、抛
ClientException"。判定依据只在 **未进入 prompt 的 `hints_text`** 里。
本反例把两种解释各自的最小用例写出来，再加一条**与分歧无关**的既有校验回退。

## 输入

| 项 | 值 |
| --- | --- |
| 镜像 | `xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6470:latest` |
| workdir | `/testbed`，base_commit `3e11578a7288122e7f2c2a0238c3338f56f8582f` |
| 候选（仅生产代码） | `patches/getmoto__moto-6470.candidate.src_only.diff`（只含 `moto/batch/models.py`） |
| gold | `patches/getmoto__moto-6470.gold.diff` |
| 官方 test_patch | `patches/getmoto__moto-6470.test_patch.diff` |
| 官方 F2P | `tests/test_batch/test_batch_compute_envs.py::test_create_ec2_managed_compute_environment__without_required_params`（1 条） |
| 官方 P2P | 11 条，全在同一文件 |
| 官方 eval_cmd | `pytest -n0 -rA` |
| 关键缺失信息 | `hints_text`（`s2/raw/swe_gym_lite_full_f70b1a29.jsonl:109`）说明 AWS 报 "Instance role is required"；**不在 agent 可见 prompt 内** |

诊断文件放在 `tests/test_batch/` 下，因为它 `from . import _get_clients, _setup`
（复用 base `tests/test_batch/__init__.py` 的夹具，region `eu-central-1`）。

## 逐条预期

### 解释 B（严格必填，= gold = 真实 AWS）

| 用例 | base | gold | candidate | 说明 |
| --- | --- | --- | --- | --- |
| `test_strict_missing_instance_role_raises_client_exception` | **FAIL**（base 抛的是 `KeyError`→500，不是 ClientException） | PASS | **FAIL**（候选直接建成功） | 分歧点本体 |
| `test_strict_missing_minvcpus_raises_client_exception` | FAIL | PASS | **FAIL** | 分歧点的第二个字段 |
| `test_strict_rejects_without_binding_message_text` | **PASS**（500 在 boto3 侧也是 `ClientError`） | PASS | **FAIL** | 不绑文案的版本：证明候选的差异是"是否拒绝"，不是"文案不同" |

### 解释 A（宽松放行，= 候选）

| 用例 | base | gold | candidate | 说明 |
| --- | --- | --- | --- | --- |
| `test_lenient_minimal_ec2_request_succeeds` | FAIL（500） | **FAIL**（400 ClientException） | **PASS** | 候选的目标行为；轨迹 `stream.jsonl:7766-7772` 已用 moto.server 实测过 |
| `test_lenient_minimal_request_is_describable_and_echoes_resources` | FAIL | FAIL | **PASS** | 放宽后的可见后果：非法请求被当成合法资源记录 |

### 与分歧无关的既有校验（候选单方面回退，官方测不到）

| 用例 | base | gold | candidate | 说明 |
| --- | --- | --- | --- | --- |
| `test_preserved_empty_security_group_list_is_rejected` | PASS | PASS | **FAIL** | 候选删掉 `At least 1 security group must be provided`；`git grep` 证明仓库里没有测试覆盖它 |
| `test_preserved_empty_subnet_list_is_rejected` | PASS | PASS | PASS | 对照组：同一函数里的 subnets 校验候选保留了 |
| `test_preserved_unknown_security_group_is_rejected` | PASS | PASS | PASS | 对照组 |
| `test_preserved_fargate_does_not_require_instance_role` | PASS | PASS | PASS | 护栏：严格化不得波及 FARGATE 分支 |

### 官方面

| run | base | gold | candidate |
| --- | --- | --- | --- |
| `official_f2p` | FAIL | PASS | **FAIL** |
| `official_full_file`（12 条） | 1 failed | 全绿 | 11 passed / 1 failed（与 `solvability_review` 记录一致） |
| `base_batch_tests` / `base_batch_simple_tests`（未打 test_patch） | 全绿 | 全绿 | **需实测**：若也全绿，就坐实"空 securityGroupIds 回退无人发现" |

## 这证明什么 / 不证明什么

**能证明（如果结果如表）：**
1. **两种解释都能从题面读通**，而唯一能消歧的材料（`hints_text`）没有给 agent。
   `test_strict_*` 与 `test_lenient_*` 的互斥结果就是这个分歧的可执行证据。
2. `test_strict_rejects_without_binding_message_text` 在 base 上 PASS、candidate 上 FAIL：
   说明候选不是"错误文案不同"，而是把一个被拒绝的请求变成被接受——服务契约发生了实质变化。
   这条堵住"候选只是被 exact-string oracle 误杀"的辩解。
3. `test_preserved_empty_security_group_list_is_rejected` 单独成立：不论采用哪种解释，
   删掉"空 securityGroupIds 要报错"都没有依据，**且官方 12 条用例一条都抓不到**。
   这是一个独立于分歧点的覆盖缺口。

**不能证明：**
- 不能证明 gold 的消息文本是唯一正确答案。`test_strict_*` 里绑文案的两条只用来对齐官方
  oracle；真正的语义判据是不绑文案的那条。
- 不能证明"给 agent 看 `hints_text` 就能解对"。这只能说明 prompt 缺了消歧信息，
  是否补进 public_view 是独立决策。
- 不能用本题结果推广到其它 moto 题。

## 落到筛查记录的字段

- `issues[]`：`{category: "spec_ambiguity_prompt_gap", severity: "P1", note: "题面未给验收方向，判据只在未曝光的 hints_text 里", evidence_refs: ["s2/raw/swe_gym_lite_full_f70b1a29.jsonl:109", "本目录 EXPECTED.md"], proposed_action: "要么把'非法请求应返回 AWS 风格 400'写进 public_view，要么把本题标为 spec_gap 不入训练集", next_experiment: "本 run_matrix.sh"}`
- `issues[]`：`{category: "official_test_coverage_gap", severity: "P2", note: "空 securityGroupIds 校验无任何测试覆盖", proposed_action: "把 test_preserved_empty_security_group_list_is_rejected 补进 P2P"}`
- `proposed_regression_tests[]`：四条 `test_preserved_*`。
- `file_rules.additional_exclusions`：**不新增**（候选没有改测试以外的无关文件）。

## 执行注意

- 需要容器内已有 `pytest` + `boto3` + `botocore`；镜像自带，脚本不安装。
- `tests/test_batch_simple/` 那组用 `TEST_DECORATOR=mock_batch_simple` 语义，若在本镜像里
  收集失败，记 `not_checked`，不影响主结论。
- 三态之间的复位只作用于容器内一次性的 `/testbed`。
