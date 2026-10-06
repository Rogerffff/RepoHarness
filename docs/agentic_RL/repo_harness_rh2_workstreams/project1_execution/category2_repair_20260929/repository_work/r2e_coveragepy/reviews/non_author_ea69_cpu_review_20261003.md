# EA69 固定 R6 CPU 非作者核查

2026-10-03。结论：**通过本题进入标明修订版本的普通基座探针所需的 CPU 条件，未发现题级阻断。** 仅适用于 `cat2-cpu-r2e080087-swe8-git-20261003-v1`、正式修订 073–075、49 键评分面。CPU 桩与固定候选不是模型结果，也不授予训练资格。

我是未编写本题材料的核查者；本轮已接触私有测试和候选，**不是 fresh 公开读者**。仅读取本地原件、做 SHA/JSON/AST、内存 parser 重放和 tar 检查；未用 SSH、Docker、模型或项目测试，未改题目材料、总账、运行原件。只新增本报告及同名 JSON。

## 正式材料与版本

外部 manifest 实算 SHA 为 `ab0a3a13fd65e0ea4cd60541ea3b37b01196170477e25832df246f33ea208828`。R6 registry 中本题仅有 073–075；目标文件与 manifest、作者材料、prepared/private 消费一致：

| 内容 | SHA-256 |
| --- | --- |
| `test_1.py`，open 参数转发 | `30f34e643804fbe5c2575ce8469c1bf4dd5f912f1214ade93fbd9968759e9361` |
| `test_2.py`，真实 Git 忽略、已有内容保留、无数据行为 | `e5fee9fb81700d682e45c5c25cdc18035000e1dd86bf78fb2c8391ee61105497` |
| 49 键期望映射 | `b3482977f4b14e436b61638b92950c68bea93f5cda15cf7854d4c87ff3627527` |
| 实际 setup 隐藏材料树 | `d9860e3e4c82c0d005cc5fdb3027ac0b489128eec2ffafdb306fc33d991c3430` |
| 实际 setup runner | `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf` |

固定 release 的 public/grading ingest 本题行与实际 prepared/public、host/private 行逐字段相等。prepared manifest、两个公开 JSONL、host artifact 的文件摘要重算一致。derived 原 `facts.json` 与作者快照的 facts 相等，source digest、base、recipe、实际 image ID 在公开 actor 与全部 grader 相同；材料树和 runner 也在 8 份原日志中实际回显。

base 为 `7fd1ea39925f0856ff607bb30796bc948a8c829d`；来源镜像 digest 为 `e6069f48a7815401ea56658b9eaeeae97581d0f1c890c31b44b94ca435d34cdf`；实际 CPU image 为 `fc124163bfbbbf914f2106d640d396db75356226036c6f42eda47f71afc7c068`；recipe 为 `r2e_derive_v1+material_v2+sysconfig_v1`，SHA `85b488e5c8a0078f952842c9f5a12f7f949b51029c3f3c80f3f0fec4b14cbb0b`。

题目语义复用[本轮材料非作者核查](non_author_ea69_material_review_20261003.md)。保留已有用户内容沿用当前授权及 inventory，不把它改写成原 ISSUE 明文要求；本轮未发现新的具体反例。共用 855 文件、Git/builder 验证按[发布记录](../../../publication_20261003.md)的固定 R6 适用范围复用，没有机械重跑。

## 逐键评分与负对照

对固定 R6 `r2e_parsers.py` 的纯函数作 AST 提取，在内存使用原 Start/End 完整段重放；8 份日志均只有一个完整段，段外解析数为 0。**392 个键的 expected/observed/match 与作者逐键证据完全一致**，并逐份核 ledger、diagnostics 与作者摘要的计数和失败节点。每份 observed=expected=49，无 missing/unexpected。

| 候选 | match/49 | reward | 失败节点 |
| --- | --- | --- | --- |
| `safe_append` | 49 | 1 | 无 |
| `safe_append_encoding` | 49 | 1 | 无 |
| 原 `gold` | 48 | 0 | 已有内容保留与报告忽略 |
| `CA` | 48 | 0 | 已有内容保留与报告忽略 |
| `CB` | 47 | 0 | 上项；报告真实被 Git 忽略 |
| `CC` | 48 | 0 | 已有内容保留与报告忽略 |
| `RE` | 47 | 0 | 已有内容保留与报告忽略；无数据不创建目录 |
| `noop`，复用本版公开空候选 | 41 | 0 | 6 个原 HTML delta 节点、2 个 Git 节点 |

总计划 8 行，新执行 7 行。原件目录现为 74 文件：原 67 文件加补存的 7 个 `candidate.patch`。每份候选源文件、原运行归档补丁、ledger patch SHA 相同，投影仅含 `coverage/html.py`。原 gold SHA 为 `bd20515f70a5b6732df9a021806fe82dad15bfc2b24d350cd3624814764a7f39`，覆盖用户内容，因此继续作为负对照；草案明确 `original_gold_is_negative=true`，正对照 override 为 host-only。

noop 复用有原件支持：实际 CC 导出 FrozenPatch entries=[]；原正式入口 ledger 为 kind/apply_method=noop、patch SHA=null、included_paths=[]。公开 actor、公开 grader、7 个矩阵 grader 的 baseline manifest 全文相等，prepared/image/overlay 一致，因此没有把非空候选或跨版成绩当 noop。

全部正式行 driver/容器 exec 退出 0，测试 RC 为正对照 0、负对照/noop 1；段完整、log 非 partial。负样本均为 `tests_failed`，没有 stage/infra failure；runner 摘要前后均为 `aaaa6955af211a2091599eb10104fe3a4be05d0ba626e59fd7641fa149dde183`。可信 setup OK、恢复材料数量完整。逐行移除成功，矩阵标签查询成功且 containers/networks 为 0；公开 actor、relay、grader 与标签残留也为 0。

## 实际公开交付与兼容命令

`messages_000.json` 实际首请求含完整题面和完整 rendered prompt；两者分别实算 SHA `8799d0f971a8226d2ddc11ba47e5efdb52a99f8fe396db133a253904b1ab312e` 与 `eb156fad331ac8dcdf370370bfb3eb0480b1a4052f32eb4555b5564c67ff5d3a`。实际 77 行 CC 轨迹含 7 次 Bash tool_use 与 7 个相应 tool_result，成功结束，日志完整；不是只把命令列在 scenario。

运行事实为 agent UID 54321、Python 3.7.9、pytest 6.2.5、coverage 6.1a0；解释器 `/testbed/.venv/bin/python`，从工作树 `/testbed/coverage/__init__.py` 导入。pip 模块缺失是保存的环境事实。预检解释器、隐藏测试和 Git 历史均 OK。

原公开 HTML 测试为 46 passed；原 `FileWriteTracker.open` 的 `encoding=` TypeError、RC=1 完整保留。`public_filewrite_compat_v1.py` 仅在一个进程内增加 `*args, **kwargs` 并转给 builtins.open，保留原 `mode.startswith("w")` 写记录及反斜杠归一化。它没有修改 HTML 实现、公开仓库文件、私有评分或目标。代码体在 source、scenario、brief 与实际 CC 命令中一致；入口移除冗余 `cd /testbed &&`，CC init 的实际 cwd 为 `/testbed`。真实兼容命令 self-check 成功，HTML 测试为 **46 passed, 2 warnings**、RC=0；两条警告是已导入模块的 assert rewriting 警告。正式 encoding 正对照另有 49/49=1，合理 encoding 求解路径不因公开替身签名受阻，也没有降低正式评分要求。

HTML 生成两条公开命令 RC=0，但输出明确 `.gitignore` 缺失、报告文件仍被真实 Git 列出。这仅证明开发命令可用，不能写成修复通过。

[公开开发 brief](../tasks/coveragepy__ea6906b092d9bb09285094eee94e322d2cb413a5/public_devbrief_20261003.md)只提供环境与公开替身事实，没有私有断言、候选或正对照方案。CPU 首 prompt 未附该额外 brief；本轮核的是同命令实际执行及 brief 字节。GPU 执行者仍须按草案固定 SHA 交付最终 brief、核实际首请求和 GPU 身份。这是既有执行范围，不是新审批或 CPU 阻断。

## 完整往返、资源与范围

独立核公开 actor/grader baseline manifest 与 census 逐字节相等，360 条基线 entries、canonical manifest/policy digest 相符；两份 FrozenPatch 都为空。baseline.tar 为 4,198,400 字节，SHA `4713664dffa903c17d2e3705bbb082e80ed8942d9156834f14c8c9b2d2fa1b7d`，全部 360 个文件内容摘要与 Git 文件模式验证一致。`install.sh`、`run_tests.sh` 原 tar POSIX 权限是 0664，manifest 是 Git 语义 100644：都不可执行，不宣称 POSIX 各位相同。运输 digest、排除路径证据及空投影与原 roundtrip 回执相符；actor 的排除区有变化、grader 无变化，baseline 的排除 census 相同，回执没有吞掉该差异。补存清单的本题 16 文件（7 patch、baseline.tar、8 SSE）均独立核 size/SHA。

实际 profile 为 2 CPU、4 GiB、PID 512；actor UID 54321、grader UID 54322。CPU solve wall=1200 秒、max_turns=11、context=32768、new_tokens=4096；grading 候选阶段=900 秒、清理=120 秒、总 deadline=3600 秒、image pull=1800 秒；公开 grading audit setup 前后均为 300 秒、test=1800 秒。未改用推荐值替代原记录。GPU 模型服务、预算、镜像和实际输入交付仍由执行者按固定申请核实。

核查详细路径、每份原件 SHA、候选 SHA、资源原值和独立重放的全部 392 个键见[同名 JSON](non_author_ea69_cpu_review_20261003.json)。本结论只支持固定版本普通基座诊断；不得报无修订说明的原 benchmark 成绩，不替代模型结果分析或训练准入。
