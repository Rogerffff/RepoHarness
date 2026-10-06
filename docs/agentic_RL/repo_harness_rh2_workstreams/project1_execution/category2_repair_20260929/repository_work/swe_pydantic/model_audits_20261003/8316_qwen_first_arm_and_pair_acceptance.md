# 8316：Qwen 首臂与两模型首次交接核收

2026-10-03。**Qwen 的通用 `to_snake` 修复有效，144 条正式参考全通过；两模型各首次一次已完成执行与题主核收。** Coder 同样修好目标，但遗留一个实际失败的临时测试文件，这项交付缺陷保持。原分均为 1，不由成对完成推导训练资格、稳定成功率或模型优劣。

题主完整阅读 Qwen 的 221 条原轨迹中所有非重复思考、文本、13 次工具调用及返回，并核收[非作者独立报告](../reviews/non_author_8316_qwen36_first_arm_execution_semantic_review_20261003.md)。[题主读回](../coordination_20261003/8316_qwen_pair_owner_readback_v1.json)绑定原件、固定请求、复核与历史 Coder 结论。当前 Qwen 封存 150 件、10,446,992 字节，451 项 baseline 全部路径、类型、执行位与内容 SHA 相符；actor/grader census 一致，与 Coder 同 baseline 和 `f939c266…` 镜像。原件中的历史 pair 未闭合、owner pending 及 checkpoint false 不回填。

| 诊断方面 | 结论和证据范围 |
| --- | --- |
| 目标语义 | Qwen 添加缩写末尾、大写边界和字母到数字的三段全输入正则；三个 pattern 与顺序同 Coder。Qwen 用 lambda，Coder 用反向引用替换，机制等价但原 AST、文件字节不同。没有示例硬编码、长度上限或只处理串首；`to_camel`、`to_pascal` 原 AST 保持。 |
| 完整候选与自测 | 原 FP 仅 `pydantic/alias_generators.py`；唯一 Edit 从真实 baseline 重建与 FP 字节一致。一次 inline 测试错误期待 `HTTPResponseCode` 直接匹配 `httpResponseCode` 别名，实际失败后正确收窄为当前 `to_snake` 目标，没有失败脚本遗留。P4 附注不升级为评分条件。Coder 的失败临时文件另见[原首臂报告](8316_coder_first_arm_acceptance.md)，本报告不抹去它。 |
| 评分一致性 | 实际 install0/test0，1 F2P 与 143 P2P 全部 PASSED，无参考缺席或 skip。全文件 159 passed/14 skipped 与正式 144 的分母不同；非参考含空格参数 ID 的 parser 截断边界保留。raw reward=1、完整 FP 摘要 `81b15f10…`、baseline `159f3843…` 与有效测试 patch `b248daa2…` 保持。 |
| 公开要求与求解依据 | 首 HTTP 文本与原 2650 字节 prompt 精确相同，保留 CRLF；全部 14 请求中完整私有 patch 和四个非公开标记未出现。模型先误判缩写匹配，再通过实际正则打印修正根因；不把首次读取文件当正确定位。公开自测是所选 17/38 项及 28 项打印检查；最后一组不是失败即退出的断言脚本，不替代可信评分。 |
| 环境与身份 | actor UID54321、grader UID54322，Python3.8.19/core2.14.5，实际导入 `/testbed/pydantic/__init__.py`，版本2.6.0a1。code_v8 与精确本题/v3/f939 的 setup900 政策相符；whole3600/apply120/test1800 未变。既有 CPU wheel 身份关联不扩大为新 GPU 两 UID 完整矩阵。 |
| 效率与并行 | 14 次生成、零 count_tokens、13 工具（10 Bash、2 Read、1 Edit），全串行、无子 agent、一次 inline 错误。累计上报输入110510/输出4665，共115175 token，单次输入峰值13504；不增计 stream 和历史消息。首次 HTTP 至生产 Edit 完成15.807秒，solve34.719秒、CC31.192秒及嵌套API27.838秒，不相加。grader212.699秒主要用于可信环境准备，安装2.027秒、测试1.674秒。与 Coder 单次观察不同，不能据此估计稳定速度差异。 |
| 模型、资源和清理 | 本次派发前13:56:19.706→19.858 UTC实际捕获 engine/adapter CID、PID、restart0与只读 Qwen3.6 revision，配置和真实 HTTP 关联。37 文件集合/大小已核，未重复权重 SHA 或证明显存字节。actor4、grader15个有限采样，grader14个有限内存值；安装/测试各零采样，缺口未知。实际截断 grader name 与 CID、run_id、report suffix 精确匹配。单作业 actor/relay/network 无残留，gateway revoked/drained/active0，manager 创建1/删除1；exact PID1 成功14:00:58.264325 UTC，not-found默认0不作 exit 证明。 |

两模型首次执行 receipt `38c4207c…` 与 Qwen execution receipt `efdc6284…` 已完整读回。原 Coder 133 件和本 Qwen 150 件不与其它任务或历史补证重复计数。执行核收不授予训练/holdout，不证明 typed 训练消费或连续资源效率；后续重复仍遵守全局覆盖门槛。当前没有具体公开源码回归要求新 CPU/材料或模型样本，本轮新调用为零。
