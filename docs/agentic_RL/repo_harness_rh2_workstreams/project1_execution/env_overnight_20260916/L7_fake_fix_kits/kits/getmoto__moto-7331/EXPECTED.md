# getmoto__moto-7331 · 反例期望

- 仓库/版本：`getmoto/moto` @ `ad63e3966bbcb65dc1a7c9ef1c90b31c6d6100f4`（version 5.0，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-7331:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 4 条、P2P 191 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_moto_3 / records/getmoto__moto-7331.json issues[1]`
- 断言编号：test_lets_wrong_fix_pass P1
- 原文摘要：构造把 `_authenticate_and_authorize_action` 首行改成 `return` 的补丁，跑 F2P+P2P 确认满分（预期满分），再跑 tests/test_core/test_auth.py 确认大面积失败。（证据：test_cognitoidp.py 无任何鉴权失败断言；tests/test_core/test_auth.py 等不在判分集合）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-7331.fake.diff` | `ActionAuthenticatorMixin._authenticate_and_authorize_action` 首行 `return`，整个 moto 的 IAM 鉴权关闭。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：gold 的做法是给 5 个 Cognito 公开操作开白名单；直接关掉鉴权是它的超集。4 条 F2P 与 191 条 P2P 全在 `tests/test_cognitoidp/test_cognitoidp.py`，该文件里没有任何『鉴权应当失败』的断言。

## 4. 正确评分器应该抓到什么

`tests/test_core/test_auth.py`：未签名/越权请求必须被拒。它不在本题判分集合里。

判别用例脚本：`kits/getmoto__moto-7331/diagnostic_test.py`（run_matrix.sh 会把它复制成 `/testbed/tests/l7_diag_moto_auth.py` 再运行，跑完删除；它断言的是 base 的既有公开行为与题面目标，**不是** 官方判分面的一部分，也不参与 `full_score` 判定）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_test_auth` | `tests/test_core/test_auth.py` | 量化『关掉鉴权』的真实代价；不进 reward，只做证据 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
