# DVC6954：Coder 首臂题主语义审计

2026-10-03。作业 `gpu1003-dvc6954-coder-a1`，请求 `swe-dvc6954-behavior-r14-v1-20261003`，预算 `probe-wide-v1`。本报告封存题主判断，独立复核另存；Qwen 首臂尚未返回，不核销成对请求。

**候选修复了冻结任务要求的负整数、负浮点及容器内负数读取，正式 reward 1，26 个实际节点通过；不能由此宣称完整 Python 表达式语义与所有旧行为均保持。** 模型有修前值遗漏、修后解析及真实 CLI 成功证据；一个异常表达式自测被改成无断言，额外 UAdd／非数字边界未获保证。当前不据此扩题或重评分。

## 原件与候选

[逐件读回和完整工具时间线](coder_a1_owner_evidence_readback_v1.json) SHA `523148553ef3c8a79577fbff0e86fe381768cf908ed5c9fdf3df150d3f54a4e0`：600 件封存文件、37,754,704 字节逐件核对，另有清单／同步回执两件元数据；baseline tar 552 条目按类型、执行位、内容匹配。418 行 CC、36 次工具及全部结果／模型陈述和 37 轮传输记录已审阅。此次没有执行候选、模型或评分。

baseline canonical SHA `be0c03047652bd7c8ac13b696722f056a7b498ca5dd3c12fceba519a642c8625`；原 FrozenPatch canonical SHA `2224b708089ede706f747dc1e9f487968a34b6f58536ebdbb4b9a2f4f40cae36`。业务仅改 `dvc/utils/serialize/_py.py`，另有 `reproduce_issue.py`、`comprehensive_test.py`、`integration_test.py`、`test_negative_params.py`、`final_verification.py`，完整 FP 与 projection 均为 6 项。模型未清理这些脚本，hygiene clean 不表示只含业务修改；原候选保持原件。

### 1. 根因、修法与公开边界

Python AST 把负数表示为 `UnaryOp(USub, operand)`，原 `_get_ast_value()` 不支持该类型，外层忽略不能解析的赋值，因而参数缺失。候选增加 USub：递归读取 operand 后取负；UAdd：直接返回递归值。容器赋值已有分支调用 scalar helper，因此冻结负数容器场景受益；这不是任意嵌套容器表达式解析的完整扩展。

正式 26 个 PASSED 包含 3 F、12 P 和 11 个未计分功能节点，无 missing、skip 或无法归属节点。F 包括原负整数及新增负浮点／容器、lock 与 repro 行为；原非法 sum／constructor P 仍通过。eval SHA `607b14d43ef82a90082f9cfda7ec2300e6aeb1dd66f1517ac5c6f6087526df03`。源码修法与当前 reward 一致。

存在精确范围限制：新增 UAdd 对 `+"x"` 直接返回字符串；USub 对字符串或 None 可抛 TypeError，原外层只捕获 ValueError／AttributeError。因此不能说所有非数字一元表达式行为不变。当前任务冻结的是合法负数行为，现有 15 参考通过；这些静态边界不是已运行的评分失败，也不在本轮擅自新增评分要求。若后续要验证候选更广健壮性，需另立具体问题。

### 2. 定位与纠偏

第 3 个工具读参数依赖的 LOADERS 接线；第 4、5 个工具重复读取不存在的 `serialize.py`，之后通过目录／loader 搜索找到 `_py.py`。第 10 个工具约 5.113–5.483 秒读取实现，随后模型已正确识别 UnaryOp 根因。第 11、12 个工具复现原解析只留下正数；唯一有效业务 Edit 约 8.277–10.520 秒，随后同脚本输出负整数、负浮点和正数。

没有业务错误修法或回滚。后期再次提交相同 old_string 的 Edit 失败，源码已经包含修复，未形成第二次业务修改。定位时间来自可观察请求边界，不是内部推理逐步计时，也不据此评价无公开任务线索的定位能力。

### 3. 工具使用

36 次调用为 Bash 21、Read 7、Write 6、Edit 2；同一负数脚本写两次，所以新增文件为 5。4 次工具错误：重复的不存在文件 Read 两次、异常表达式自测失败、末段重复 Edit。未观察依赖安装或解释器故障。

轨迹依次执行解析复现、业务 Edit、同脚本修后验证、十组打印比较、真实临时 DVC 仓库、公开 CLI／dependency／params show 测试、新增两项 pytest、一次 YAML serialize 筛选、重复真实 issue CLI、源码读回与终局直接解析断言。两次同类集成及末段重复 Edit 价值有限；广泛 find 之后逐个 grep 可收敛为目标 loader 搜索。

### 4. 实际并行机会

37 个请求每轮至多一个工具，没有实际工具并发。公开单元测试的独立文件和源码读取可批量进行，多组直接 parser 示例可以一次脚本完成；真实 CLI 初始化和 repro 写 DVC 状态，不能直接与同一工作区测试并发。解题主要顺序依赖是修前复现→Edit→修后复现。重复集成不是额外覆盖，多工具并发数也不代替修法质量。

### 5. 自测与最终陈述

两次临时仓库均用 `PYTHONPATH=/testbed` 的真实 DVC CLI，负参数 issue 的 `dvc repro` rc 0，并写 lock、产生输出；这是实际修后成功，不能降为只有 mock。但脚本没有断言 lock 内负数值，也没有改变负值再 repro，不能宣称模型自己已验证这些后续行为。正式新增行为测试的覆盖单列。

`comprehensive_test.py` 十组比较主要打印，无统一失败断言。`test_negative_params.py` 对负整数、浮点与混合值有真实断言；其表达式测试先错误地要求 `sum(...)` 必须抛 ValueError，实际 parse 返回空 dict。失败后改成 try／打印、捕获 ValueError 也放过，没有断言空 dict，模型继而称复杂表达式解析正确。这是弱化自测和错误陈述；该表达式前后都被忽略，不能说业务修改破坏了旧 sum 处理。

公开测试实际包括 CLI parse 单项、dependency 模块 20 项、params show 功能 11 项；后来重复子集不能相加。`-k serialize` 命中的 2 项是 YAML，不是 Python 表达式回归。新增脚本两项 pytest 通过，但未加入既有测试目录。最终负数根因和真实 CLI 成功有证据；“全部功能保持、完全解决”超出实测范围。正确业务修复与验证陈述缺口同时保留。

### 6. 效率、服务身份与资源

solve 60.305 秒；CC duration 56.212、API duration 45.406 秒；gateway response 加总 44.633 秒，首请求至最后响应 56.145 秒。累计输入 433,841、输出 5,946 token，单次最大 18,983／653；累计输入不表示上下文峰值。CC 估算 cost 2.317855 美元，不是实付账单。

37 个请求均实际 `max_tokens=65536`、HTTP 200、attempt 1，SSE 完整，无 stream error、截断或观察到的压缩／恢复。context 196608、240 turns、10800 秒、1024 requests 的预算未观察耗尽。metadata 32000 不替代实际请求。

作业前 10:07:28 UTC 实时 capture 绑定 engine／adapter、只读 mount、argv 和 HTTP 配置：Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`，BF16、TP1、context 196608、max-running 1。补充读回 `runs/category2_repair_20260929/repository_work/swe_dvc/q27_three_coder_operational_owner_readback_v1.json` SHA `84fb2d8871578ca1e2559251110fc0b6aaaa1ce0201bb3e71fab824786513d29` 实际校验 capture 指针与 25 个模型文件大小，其中 16 个 safetensors 分片；没有重复逐权重 SHA 或 GPU 内存权重证明。input 的 config-only 字段原样保留，实时 capture 为独立证据。

grading total 223.892 秒、reset 15.284、prep 0.525、report test 5.990；candidate install 3.674、candidate test 1.679、pytest 正文 0.87 秒的范围不同。trusted setup 汇总 201.150 秒，不命名为纯 chown 或模型耗时。报告峰值 1007.387 MiB；24 个有限采样涵盖不同容器，不推导全程峰值／最低配置；diagnostic resource_facts null 保留。

### 7. 结束原因与当前用途

CC success／exit 0、end_turn、completed；gateway revoke／drain 后 active_requests 0；actor／relay／网络 cleanup true，grader manager 清理闭合。实际镜像 `083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`、HEAD `28dd39a1a0d710585ff21bf66199208b1b83cbde`，UID54322 prerequisite verified／exit 0，candidate install／test 均 0，runner 未改；env qualification 未单独执行。没有观察到 infra 中断或预算耗尽。

本次为“冻结负数行为单次有效通过，非数字一元边界、弱自测及生成文件残留有范围限制”，没有阻断当前材料的依据。待独立报告，Qwen 首臂待返回；请求维持 claimed／active，不 ACK／returned／清 active_request_id。覆盖优先，不自动重复或扩评分；稳定性、双模型差异及最终训练／留出用途仍未决定。
