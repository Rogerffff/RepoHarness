# getmoto__moto-5885 · 反例期望

- 仓库/版本：`getmoto/moto` @ `67197cb8a566ee5d598905f836c90de8ee9399e1`（version 4.1，python 3.12）
- 镜像：`xingyaoww/sweb.eval.x86_64.getmoto_s_moto-5885:latest`，工作目录 `/testbed`，上游 eval_cmd：`pytest -n0 -rA`
- 判分面：F2P 2 条、P2P 1 条
- 阶段一基线：gold=RESOLVED_FULL、empty=RESOLVED_NO（rc_install=2）

## 1. 断言来源

- 来源包：`L1_moto_2 / records/getmoto__moto-5885.json issues[1]`
- 断言编号：题面无依据的 reward 判据 P2
- 原文摘要：记录『未知模板必须静默接受』这条 P2P 无题面依据且与 hints 的表述方向相反；作为欠明确题面样本。next_experiment 原文是『盲解一次』——不是一个假修复断言，本套件把它改造成一条方向相反的可执行反例。

## 2. 假修复内容

| id | 补丁 | 一句话 | 预期 |
| --- | --- | --- | --- |
| `fake` | `patches/getmoto__moto-5885.fake.diff` | 实现与 gold 相同的 launch template 名/ID 互推，但把 gold 的 `except: pass` 换成对未知模板抛 `ResourceNotFoundException`。 | **not_full** |

## 3. 为什么它能让 F2P∪P2P 全过

**`fake`（预期 not_full）**：2 条 F2P（已知模板按 name / 按 id）会过，但 P2P 的 `test_passing_an_unknown_launchtemplate_is_supported` 要求未知模板静默返回 `{"name": "random"}`，因此必红。这是一条**反向**反例：它证明的是『更严格、更贴近 hints 的实现会被判失败』，而不是『破坏性改动能拿满分』。

## 4. 正确评分器应该抓到什么

题面对『未知模板怎么办』没有规定，hints 的方向是报错，P2P 的方向是静默接受 —— 两者冲突本身就是待拍板项。

本题没有配 `diagnostic_test`（判别点要么需要重量级 fixture，要么就是下面的 blast 运行）。

## 5. 预期结果（当前判分下）

- `fake` → **不满分（至少一条红）**
- `base` → 预期 F2P 红、P2P 绿；`gold` → 预期全绿（该题阶段一已验证 gold=RESOLVED_FULL / empty=RESOLVED_NO）

> 注意：本题不是奖励漏洞样本，纳入套件是为了把『题面-判据冲突』做成可核对的运行证据。
