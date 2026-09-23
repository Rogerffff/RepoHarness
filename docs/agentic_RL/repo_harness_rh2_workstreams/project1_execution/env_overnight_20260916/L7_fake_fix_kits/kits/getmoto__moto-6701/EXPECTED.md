# getmoto__moto-6701 · 反例期望

- 仓库/版本：`getmoto/moto` @ `5e1b166f2521eacd737f2ccb241fbc0b2e8bb931`（version 4.1，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-6701:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 10 条、P2P 7 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_moto_3 / records/getmoto__moto-6701.json issues[0]`
- 断言编号：grading_cannot_distinguish_blast_radius P2
- 原文摘要：打 hints 里那个全局补丁，跑本题 F2P+P2P（预期全过），再跑 tests/test_s3、tests/test_ec2 若干文件，看是否出现回归——用来量化『判分面 vs 改动面』的差距。（证据：hints 里的全局 `_get_param` 补丁 vs gold 的 iot 局部补丁；两者都能过本题 17 条用例）

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-6701.fake.diff` | 按 issue hints 在 `BaseResponse._get_param` 里对**所有 service** 的 URL 路径参数做 `unquote`（gold 只改 `moto/iot/responses.py`）。 | **full_score** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 full_score）**：10 条 F2P + 7 条 P2P 全在 `tests/test_iot/test_iot_thing_groups.py`；全局 unquote 是 gold 的超集，本题必然满分。本条不是『假修复』而是『改动面远大于判分面』的样本：两种补丁拿到同样的 reward，但一个只影响 iot，另一个影响 moto 所有 service 的路径参数解析。

## 4. 正确评分器应该抓到什么

任何依赖『路径参数保持百分号编码原样』的 service 测试。建议 blast 面：`tests/test_s3`、`tests/test_ec2`。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 附加（blast）运行

只在环境变量 `RUN_BLAST=1` 时执行，不进 reward，只作为『判分面 vs 改动面』的证据：

| 运行名 | pytest 参数 | 用途 |
| --- | --- | --- |
| `blast_s3_ec2` | `tests/test_s3/test_s3.py tests/test_ec2/test_instances.py` | 只在 RUN_BLAST=1 时跑；文件名若在该 base 下不存在，脚本会记 rc 并继续 |

## 6. 预期结果（当前判分下）

- `fake` → **满分（F2P∪P2P 全绿）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）
