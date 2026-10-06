# aiohttp4075：r069 的非作者 CPU 证据复核

2026-10-03。**本次公开复现的 base／ALT2 对照与最终题面交付证据可接受，未发现新增阻断。历史评分仅按身份复用；本轮没有新的正式评分或真实模型成绩。**

这是已接触私有材料的非作者证据审查，不是 fresh 公开盲审或 fresh 求解。只读本地原件、JSON 和源码；没有 SSH、重跑、容器启动、项目测试或实现改动。原件根目录为 `runs/category2_repair_20260929/r2e_aiohttp/cpu-b/public_actor4075_r069_v1/final_artifacts/`，下文路径相对此目录。

## 身份与原件完整性

逐文件计算 `download_receipt.json` 所登记的 **87/87** 份原件 SHA256 和字节数，全部相等，无缺件。回执实际 SHA256 为 `cd6c5e6c9b0437bdc17a925ebdb39c079d35c3aa9c634d8d7496a32ea6156cab`。本地 `releases_20261003/r2e_069_swe6_candidate_v1/manifest.json` 实际 SHA 为 `40ca2914da2be665754175954defe4bbecfdb31efc1ad394153c09acfb5f9f15`，与控制记录、交付证明一致；release 为 `cat2-cpu-r2e069-swe6-20261003-v1`。

`prepared/rollout_task_views.jsonl` 解码后的题面实际 SHA 为 `c3253b921246dcb9c99490b35b129269eb54cf4276f67837a6bd14d73819d731`。实际 base 为 `e181a0e468d4fb35f2c990c604566089a7afe945`；两控制及 delivery 的实际镜像均为 `sha256:db094fc72e61438169c7ea58622637d379e313b243ebcc9e4578825a667246c3`，配方 SHA 为 `e139ba5708390eca37d126e49637de55a69348a572e59f0dc914fba0b4e7db32`。新镜像 ID 不冒充历史镜像 ID。

ALT2 补丁原件实际 SHA 与 `ALT2/attempt.json` 的 `aiohttp_owner_control.host_patch_sha256` 均为 `f3c6056416e15fa36521dd196f66315cee5cc2197a555d4f8087fcc4304c20c2`。wrapper 实际 SHA `fdaa801421ff52a030eac3680603a73a0658e4dba4c1cf9ecb653e4973828263` 与运行记录一致；源码以 `user=self.profile.agent_user` 做 apply-check 和 apply，完成后才进入 actor；补丁文件没有作为 solver 工件交付。它是宿主私有正对照，不是模型生成修复。

## 原始输出与 actor 退出

直接核了两组 `captures/*.out`、harness 原始 JSONL 的 Bash/tool-result/result 事件及 `attempt.json`，没有只依赖作者的 checks 布尔值。

| 核项 | base | ALT2 |
|---|---|---|
| 真实导入／身份 | UID/GID 54321；Python 3.9.21；`/testbed/aiohttp/__init__.py` | 同左 |
| 非 ASCII 字段名原例 | rc1；`the example returned without BadHttpMessage` | rc0；真实 `InvalidHeader` 输出，符合 `BadHttpMessage` 分支 |
| 异常请求行原例 | rc1；`the example returned without BadStatusLine` | rc0；真实 `BadStatusLine` 输出 |
| 公开 parser 回归 | 124 passed／5 skipped／3 deselected，rc0 | 相同计数，rc0 |
| 实际 CC 工具与 footer | 5 次 Bash、5 个结果；最终 `result/success`，harness rc0 | 同左 |
| 13 项检查 | 13/13 true；原输出、preflight、激活和 footer 与之相符 | 同左 |

命令的 `expect=any`／`all_match_expect=true` 本身不证明复现修好，结论来自上述异常输出的正负配对。三类 preflight 均实际打印 ok，BASH_ENV 写入实际为 DENIED。公开测试明确记录 C parser 不可导入，并设置 `AIOHTTP_NO_EXTENSIONS=1`；5 个 skip 均有来源和原因，3 个 deselected 来自 `-m "not dev_mode"`。这证明声明范围内的纯 Python 开发路径，不证明 C 扩展已构建或开发模式已通过。

两个控制的 harness JSONL 各 57 行、末尾均为成功 result，stderr 空；六个 message-start 与桩六次请求一致。内层容器 rm 为 0，network／relay 失败列表为空，stub rc0；外层标签范围的容器、网络及 force 后残留均为空。root post-run 原件确认 agent 进程为 0；base 新文件为 0，ALT2 的变化定位到 `aiohttp/http_parser.py`。作业原 `job/status.json` 为 finished／rc0，stdout 分别记录两个控制与 delivery 完成。

## 单独核实最终公开交付

base／ALT2 首请求实际只有 `Devcheck run: execute exactly the tool calls you are given, then stop.`，没有 `[ISSUE]`，所以不把这两个控制冒称题面交付证明。

单独的 `delivery/stub/requests/messages_000.json` 实际 SHA 为 `f0a3b81bdcf574a4d1263b262fdbd29c02bec96ea4026e9dd4bb490ec5946c78`。直接遍历首个 user 消息的 text blocks，完整最终题面恰好出现一次，内容与 prepared 的上述 `c3253b…` 文本逐字一致；`delivery/attempt/prompt.txt` 也与 prepared prompt 一致。没有依赖 `public_delivery_proof.json.matched` 直接判通过。

delivery 实际执行 2 次 Bash，preflight 与解释器命令都 rc0；原 JSONL 28 行、成功 footer、harness rc0、quiescence 通过。solve cleanup 的 container rm0、剩余列表为空且 cleanup_ok=true，端点停止 `[0,0]`，外层 residuals `_clean=true`。

其冻结工件是空补丁，但 `candidate.excluded_pathset_changed=true`，原 classification 也保留 `runtime_private_pathset_changed=true`。这是已登记的旧 Git／排除路径问题；本次没有运行 grade，不能从空工件、projectable 或交付成功推导评分通过。`run_summary.json.final_revised_statement_delivery_proven=false` 属于两个 devcheck 的较早范围；后续独立 delivery 原件补足交付事实，不静默改写旧 summary。

## 公开开发说明的窄核

新增题主汇总 `results4075_r069_20261003.json` 实际 SHA 为 `d96dc7b8f8cf7ba95a57d58fc0a60c52f124f01d3e3e3a7bc64d7f2df1036186`；其带 path/SHA 的引用已另外逐项核回原件。汇总结论与上面的独立读回一致，未以汇总 status 代替原件审查。

`public/4075_development_brief.md` 实际 SHA 为 `fe294eaf24f7f8a29bb71dcaa614697ae729b2f46144eef818ba5512e5c1b9b3`。初始化公开 `HttpRequestParserPy` 的 loop/mock/缓冲参数，与实际两个 capture 使用的初始化一致；分开运行两个题面函数避免首个异常遮住次例，未提供修法。公开回归使用同一个 `tests/test_http_parser.py`、C 扩展可导入检查、`AIOHTTP_NO_EXTENSIONS=1` 分支，以及实际已执行的 pytest 参数。说明的 echo 文案与首个 import 的字节码环境前缀有表述差异，因此这里核的是已测运行方法和范围，不声称说明全文逐字实跑。

未见私有候选名／补丁、隐藏评分节点／输入、expected 映射或修复提示；没有将 BASH_ENV 写权限诊断、私有预检或宿主控制命令放进 solver 说明。`dev_mode` 与 C 扩展缺失范围均明确，未把公开跳过写成正式评分通过。

## 历史复用与结论边界

只核新 `private/host_grading_views.jsonl` 的身份：隐藏 `test_1.py` SHA 为 `ec2c29858ae4e71575f76864e994116ba2af1ff952a6c70a3df2045e720a8cfa`，树 SHA 为 `3ff70876554bee932635b48cbf85bd988ac5b83df3e46a871b29ca1418d210d4`，expected 文本实际 SHA 为 `fdabd74b34e463b84e09abb2998b33ee5a7906fa2e7d662673ba73d376880491`，仍是 136 键（133 PASSED＋3 FAILED）；测试入口 SHA 为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`。这些与已验收 [历史记录](../../../r2e/aiohttp4075_acceptance.md) 一致，本轮不重复材料审查或七方评分。

可关闭的是最终 R-f 复现的相称 CPU 对照与本入口题面交付证据。桩的 token／费用和私有 ALT2 不是真实基座模型结果；不授予训练／留出资格，也不扩张到 C 扩展、开发模式或完整 HTTP 协议覆盖。
