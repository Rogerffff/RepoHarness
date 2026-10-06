# getmoto__moto-7335 · 反例期望

- 仓库/版本：`getmoto/moto` @ `a5a2c22fc8757d956216628371e4b072122d423c`（version 5.0，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7335:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 2 条、P2P 20 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_moto_3 / records/getmoto__moto-7335.json issues[1]`
- 断言编号：test_lets_wrong_fix_pass P1
- 原文摘要：用『首行 return 关闭鉴权』的补丁跑本题确认满分。（证据：test_cognitoidentity.py 无鉴权失败断言；tests/test_core/test_auth.py 不跑）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-7335.fake.diff` | 同 7331：`_authenticate_and_authorize_action` 首行 `return`。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：gold 只是往 `PUBLIC_OPERATIONS` 里加两个 Cognito Identity 操作；2 条 F2P + 20 条 P2P 都在 `tests/test_cognitoidentity/test_cognitoidentity.py`，没有鉴权失败断言。

## 4. 正确评分器应该抓到什么

同 7331：`tests/test_core/test_auth.py`。

判别用例脚本：`kits/getmoto__moto-7335/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_moto_auth.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_auth` | `tests/test_core/test_auth.py` | 同 7331 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
