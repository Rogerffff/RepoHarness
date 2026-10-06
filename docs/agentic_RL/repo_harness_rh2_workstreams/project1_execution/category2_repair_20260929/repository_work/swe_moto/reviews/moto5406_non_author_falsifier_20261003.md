# Moto5406：非作者 Falsifier／Simplifier 实际结果窄核

2026-10-03。结论：**本轮没有发现阻断 CPU 结果提交或继续版本化基座诊断的缺陷。** 三行真实矩阵、真实 Claude Code 加桩的公开操作／冻结、原 actor 工件 fresh grade 的主张均有保存原件支持。这不是训练或留出准入，也没有取得基座模型能力结果。

## 范围与审查上下文

本角色按根 `AGENTS.md` 和审查标准 §10.4／§10.5，尝试推翻本轮结果及阻断必要性。输入为 `moto5406_cpu_actor_review_request_20261003.json`。已读题主导航、私有 gold／错误修复补丁、评分测试与旧 consumer／tools 审查；因此不是 fresh 公开盲读者，也不是材料作者。旧公开阅读、consumer 和共同 Git 机制结论仅在各自范围内复用。

全部操作为本地保存证据读取与 Python 标准库离线校验。未 SSH、Docker、安装、运行项目测试或模型，未改源代码、材料、原作业或题卡。新增产物仅本报告和 ignored 摘要：`runs/category2_repair_20260929/moto_cpu_20261003/non_author_falsifier_20261003/offline_summary.json`，SHA256 `9a021080ff7e7c85e815ed3362039dd46e25c76f0ac889ce0954db151b6c1f3d`。

## 具体反证结果

### 新旧 producer、基线或证据混用

请求固定的报告、三个 owner readback、tools、材料 manifest 与公开开发说明 SHA 全匹配。R5 外部 manifest 实际 SHA 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`；其 837 个文件逐件 SHA／长度匹配。tools 清单实际 SHA 为 `09f7b6de626c00fba904137b763c8c4c66777cbe1551fbd41812dbce46d2c86c`，9 个成员逐件匹配。SWE7 producer 实际 SHA 为 `84e82a8219c215ce5f8711bbd7e3306d4af6217dc9c809ee1dc436bcc52352fd`。

新矩阵 `status.json` 记录上述 R5／SWE7、材料 manifest `d5ca5786…` 和原运行镜像 `sha256:808c60d9…`；actor 及 a2g 的 `input_check.json` 同样绑定 R5。三个新作业分别有 410、37、100 个运输成员，合计 547 个，保存原件全部与各自运输清单 SHA／字节数相符。旧记录没有被拿来填补新矩阵。

### 0／1／0 是否只是摘要，错误修复是否被相关断言拒绝

直接从三份正式 `.eval.log` 提取的 `PASSED`／`FAILED` 节点与保存结果逐项相等，每行恰为 28 个、实际收集 28 个，无跳过或缺失。三个正式 reward 为 0／1／0；安装退出码均为 0，测试退出码为 1／0／1。

| 候选 | 原 East2 F2P | 原 26 P2P | 新增 East1 P2P | 可核的实际失败 |
| --- | --- | --- | --- | --- |
| noop | 失败 | 全通过 | 通过 | `TableArn` 实际 East1、期望 East2；均为 `table/messages`。 |
| gold | 通过 | 全通过 | 通过 | 无失败。 |
| constant_east2 | 通过 | 全通过 | 失败 | `test_create_table_standard` 第 43 行的 `TableArn` 实际 East2、期望 East1；均为 `table/messages`。 |

所以已知错误修复确实通过了原评分面，而新增节点正是用地区断言将其拒绝；不是无关测试偶然失败。错误补丁把 `_generate_arn` 常量由 East1 改成 East2，gold 则保存 `region_name` 并用它生成 ARN。实际导入的 `/testbed/moto/dynamodb/models/__init__.py` SHA 分别为 `87a55876…`、`2fd7febd…`、`4bd4d645…`，与本行 baseline／FrozenPatch 内容匹配；两个非空工件各只有该源码文件，base64 内容 SHA 也独立重算一致。

辅助原例／修订例与正式 reward 分开：原例三行仍为退出 1；修订例为 1／0／0。它说明修订公开例能够定位地区问题，但不能单独筛掉常量 East2，筛除职责由正式 East1 P2P 承担。不能把公开复现通过误称为评分通过。

原测试补丁字节保持；实际 `trusted_setup_script.sh` 从固定 base 恢复两份测试，校验既有 East1 文件原 SHA，再应用原补丁。三份正式日志均有 `RH2_SETUP_RESTORED=2`、`EXPECTED_TEST_FILES=2`、`TEST_FILES=2`、`ABSENT_TEST_FILES=0`、`SETUP_OK=1`。逐行保存的源码／保护观测显示 grader UID 54322，两个测试文件 UID 0、不可写，SHA 为 `d612bbf8…` 与 `a0543ad1…`。这支持本轮实际恢复与保护；针对恶意候选的完整机制边界仍沿用先前 consumer 审查，不在本轮重新穷举。

### 原 actor 工件是否重新导入或改绑

actor 的原 FrozenPatch 文件 SHA 为 `34ca1b7a…`；按固定实现的 canonical JSON 规则离线重算语义摘要为 `sha256:6db18cb77ebdf6fb1ef0852e4bfb73ff28388126fb3f276fc0edd2635fa6ee58`，与 projection、join 和 a2g 输入相符。工件为空，baseline 为 `sha256:74377437…`。

a2g `input_check.json` 的 `actor_files` 与 actor `recordmanifest.json` 的 33 成员清单逐项相等，固定 actor manifest SHA `2de05ad2…` 与原件匹配；分派与 actor `dispatch.json` 逐项相等，包含 physical attempt `miles_g0_m0#p1-c34887ab`、公开身份及环境身份。

实际使用的 tools `actor_to_grader.py` 第 124–137 行从原三个 JSON 读取 baseline／FrozenPatch／projection，构造 `FrozenDeltaSource`；第 309 行以 `workspace=None, frozen_delta=source` 调用正式 `manager.grade`。该路径没有 candidate patch 重导入或新 actor。保存 `status.json` 的 `grade_invocations=1`、`baseline_rebuild_passed=true`；报告 reward 0、F2P 0／1、P2P 27／27，唯一失败仍是原 East2 ARN 用例，导入源码 SHA 与 actor 基线相同。

### 真实 CC 的公开命令失败是否被外层退出 0 掩盖

实际首请求 `messages_000.json` 的用户消息含通用 system reminder 与题面两个 text block；题面 block 与本次 prepared prompt 逐字相等，SHA `03414c3f…`。轨迹有真实 CC 2.1.205 初始化、3 个 Bash 调用及完整 result；模型响应来源是桩。

三个 capture 原件与轨迹对应，字节数分别为 1039／4945／2258，命令退出 0／1／0。公开复现完整收集一条 pytest，用例的 `table/test_table` 实际 ARN 为 East1、期望 East2；公开既有 East1 节点完整通过。命令退出 1 和断言均保留，CC 外层退出 0 表示该桩驱动流程完成。题主报告没有将它表述为模型解题成功或公开复现通过。

### 生命周期、历史失败及未运行部分

actor `quiescence.json` 记录进程残留 0、工作区摘要双读稳定；driver 已返回，桩退出 0，relay 无关闭失败。文件持久化冻结后释放容器，`cleanup` 无错误、本 run 容器与网络查询空，分派已释放且旧 attempt 解析被拒绝。该 receipt 明确只覆盖独立直连桩消息源，不冒充训练 capture/session drain receipt。

矩阵 manager 创建／移除各 3 个 grader，无开放容器或 supply，label 查询零残留；a2g 单 grader 清理确认、容器和网络查询空。它们支持本 run 清理，不外推整台宿主没有其他资源。

旧 R3 作业 `moto5406-cpu-74541fbf7460` 的原状态仍为 `failed_halted`、rows 为空，stderr 留有 `baseline_digest_mismatch` 及不同旧 baseline／rebuilt 摘要。它不是本轮成功矩阵。review request 与报告均声明模型 probe attempts 为 0、真实 CC 使用桩、尚未获得训练／留出资格，未把这些阶段混为一谈。

## 比例裁决与停止条件

本轮没有成立的当前 `production_observed` 或 `production_reachable` 阻断 finding。无需新增 owner、状态机、retry、fallback、拒绝路径或重新运行 CPU；推荐以当前固定 R5／tools／材料版本继续提交基座诊断。

未知边界仍保留：28 节点仅证明该评分面与已知常量 East2 反例，不保证所有地区、所有表名或所有投机补丁都被区分；桩不证明模型能力；保存清理查询不证明今后所有 CLI 异常都能收口。这些没有本轮可达错误放行的证据，不应转化为当前阻断。后续若更换代码、材料、运行身份或取得新失败证据，应按对应 gate 复核，不能沿用此报告给另一版本背书。

停止条件已达成：请求范围内完成一轮具体反证，关键主张有原件支持，无必需补证项；不继续穷举 CLI／评分反例，不等待 GPU，也不授予训练准入。最终由根审查者独立核关键证据、去重裁决。
