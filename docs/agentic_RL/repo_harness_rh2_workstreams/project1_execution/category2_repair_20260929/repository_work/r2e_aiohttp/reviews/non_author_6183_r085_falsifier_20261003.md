# aiohttp6183：R085 CPU 证据的非作者 Falsifier 窄核

2026-10-03。**本轮没有发现阻断 6183 进入现有探索性单题 GPU 探针的运行缺陷。** 当前证据支持复用旧 v5 六方评分，并与新派生环境的公开行为对照、正式 R085 首请求交付一起作为该题 CPU 验收依据。发现一处 A1／AP2 历史导航标签对调，须按实际补丁 SHA 更正后续引用；它不改变两正对照都为 49／49、reward 1 的事实。

本结论仅适用于 6183 当前 044／045／085 材料和所列版本，不计入仍运行中的 1c1／240d，不授予训练或留出资格。旧六方发生在旧派生镜像；本轮没有重新评分六方，也没有模型实测。

## 上下文与操作范围

按根 `AGENTS.md` 与审查标准 §10.4／§10.5，对旧结果复用条件、正负候选语义和公开 write／终止块边界做一轮反证。输入 `review_handoff_6183_r085_cpu_20261003.json` 实际 SHA256 为 `8c59b154aff8b14b5ed85ae0997db2515fc5b27dd890968506a0d66b6c4281e5`。

本角色读过私有隐藏测试、候选补丁、gold、题主导航和既有审查，**不是 fresh 公开盲审**。没有重新审查 Expected Behavior 文案 finding、公开 wrapper、共同 Git 机制或新增 brief，也没有 SSH、模型、容器、安装或项目测试。仅本地原件读取及标准库离线解析；未修改作者生产文件、题卡或运行证据。

自有摘要为 `runs/category2_repair_20260929/r2e_aiohttp/non_author_6183_r085_falsifier_20261003/offline_summary.json`，SHA256 `7eb9f99277b98d3b25bdcf6d101a7f29f19d88f7c4e37a628d99dd8c021d11a5`。请求固定的 10 份输入和 3 份 receipt 摘要吻合；三个 receipt 的 38／80／59 个原件，合计 177 个，SHA／长度全匹配。这是保存原件复核，不是新运行。

## 六方实际结果与候选语义

直接读取六份完整正式日志及指定 ledger 行，按当前固定 `r2e_parsers.py` 的首个 short summary／去色／键归一化规则离线重算。每份日志只有一对完整测试段和一个摘要，解析结果恰为当前 expected 的 49 个键，无 missing 或 unexpected；与 ledger 的日志 SHA、reward 和计数一致。原日志均标记隐藏树 `23b524a8…`、入口 `8285765f…`，且 runner 前后摘要一致、测试段结束、容器移除。

| 实际候选 | 固定补丁 SHA 前缀／slot | 匹配 expected | reward | 实际语义与失败 |
| --- | --- | --- | --- | --- |
| gold | `ce89afa4…` | 49／49 | 1 | 在 filter 输出转发处抑制空字节；正常 flush 和终止仍保留。 |
| noop | 无补丁 | 45／49 | 0 | 四个 deflate 相关节点失败，未将环境故障转换为 reward 0。 |
| AP1 | `62fb5c2c…`／s1 | 47／49 | 0 | 只在定长 writer 跳过空字节；新增两个 chunked 节点在 `all(chunks)` 失败。 |
| AP1m | `05e094d5…`／s2 | 47／49 | 0 | 定长跳空并合并 chunked 每帧的三次 write；两个新增节点的 `all(chunks)` 已通过，随后因零终止块后仍有数据失败。 |
| AP2 | `0548e104…`／s3 | 49／49 | 1 | 定长和 chunked writer 都跳过空数据；chunked 的 `EofStream` 分支仍写合法末尾零块。 |
| A1 | `5b38357b…`／s4 | 49／49 | 1 | compression filter 仅在 `zcomp.compress` 产生非空数据时 yield，flush 分支保持。 |

已逐件将 AP1、AP1m、AP2、A1 本地补丁 SHA 与 ledger、`remote/slots_manifest.json` 核对；补丁只改 `aiohttp/protocol.py`，语义与上表相符。

最强反证是 AP1m：它没有空 write 参数，但正式堆栈在隐藏 `test_1.py:493` 显示 `data after the terminating chunk`。单写情形零块之后还出现 `6\r\nKI,I\x04\x00\r\n0\r\n\r\n`；多写情形还存在另一个零块和后续压缩载荷。因此拒绝原因是线上提前 EOF，而非 writer 调用次数或分帧布局与 gold 不同。

当前隐藏 helper 遇到 size 0 时要求余下字节恰为 `b'\r\n'`，再将非零数据块载荷解压为 `b'data'`／`b'data1data2'`。它允许完成载荷后的合法最后零块，检查分帧与完整载荷，没有强制正对照的压缩字节或 write 次数。AP2 的跳空发生在捕获 `EofStream` 并输出合法终止之后，A1 仍执行 flush；未找到“正对照通过是因为把真正 EOF 删除”的证据。

### 非阻断标签错误

固定 handoff 和 `results6183_v5_log_readback_20261003.json` 将 s3 称 A1、s4 称 AP2；实际 slots manifest、补丁 SHA 和补丁语义证明相反。处置建议为 `accepted` 的最小文档更正：追加 erratum 并让后续请求按实际 SHA 命名，保留原件和原 SHA。此问题影响追溯说明，不能据此把运行结果改判失败，也不需要新评分、状态机或拒绝路径。

## 旧结果为何可用于当前探索性探针

当前 R6 为 `cat2-cpu-r2e080087-swe8-git-20261003-v1`，外部 manifest SHA `ab0a3a13…`。044 隐藏文件 `test_1.py` 实际 SHA `89702c7c…`，045 expected 文件实际 SHA `3390e85f…`，两者与 v5 staging 逐字节相同。R6 host grading 相比 R4 只有 `material_revisions` 从 `[044,045]` 追加 085；49 键 expected 原文、隐藏文件清单／树、run_tests 入口、base commit、parser／normalization 身份均未改变。实际入口 SHA 重算为 `8285765f…`，当前 parser SHA `339b7c80…` 与旧读回固定 parser 相同。

旧 v5 六行实际镜像 ID 为 `sha256:b93c5d43…`，当前 CPU 派生镜像为 **`sha256:28682e5a…`，不是同一个 ID**。复用依据是同一固定 base manifest `67aefa17…`、同一配方 `r2e_derive_v1+material_v2+sysconfig_v1` 及配方摘要 `70ceace9…`，并有新构建原始 `facts.json` 的实际完整性观测：

- base layers 保留；124 个 testbed 文件、1000 个 venv 非 bin 文件、19 个 bin 文件的完整性通过。
- Git 工作树的 head／status／index／diff 在 base 与派生间相同；head 为 `ff3dec42…`。新 baseline tar 中 `protocol.py` 仍是未修复的原 filter／writer 逻辑。
- 隐藏树与入口分别吻合当前 bundle；没有工作区隐藏测试副本，私有目录 root 所有／0700，agent 与 grader 的读取被拒绝。
- Python 3.9.21 解释器及 sysconfig 重定位完成，agent／grader 可执行，R2E rollout 预检通过。

这足以保留旧六方作为不变评分面的历史验收，并继续当前探索性单题诊断；**它不证明六方已经在新镜像逐项重跑**。新派生环境还提供下述 base／gold 公开行为对照，未见会反转旧正负候选结论的当前证据。共同 wrapper／Git／构建机制已有审查，不为不同 image ID 再发明一轮同矩阵准入闸门。

## 公开行为及 R085 实际交付边界

R4 公开开发原件中，base 和 gold 均经真实 CC Bash、UID/GID 54321、Python 3.9.21 从 `/testbed/aiohttp/` 导入；两段命令实际源码与当前公开复现一致。base 定长例的原 capture 展示两个 `b''` 写入参数并退出 1；chunked 例因 `data after the terminating chunk` 退出 1。gold 两段退出 0，断言检查非空 write 参数、末尾合法零块及完整载荷解压。两者公开 protocol 回归各 47 passed、rc0。公开回归没有单独抓住本题目标，不能拿该 47 项替代两段直接行为证据；gold 的空 stdout 也仅按真实命令退出和完整轨迹认定断言完成，未捏造逐帧输出。

最终 R085 题面全文 SHA `ab73a3ec…` 实际出现在 `delivery6183/stub/requests/messages_000.json` 的首条 user text block 中，不是桩响应回显。prepared 材料绑定 044／045／085，runtime image 与当前 overlay 均为 `28682e5a…`。prelaunch 原件实际 UID 54321、2 CPU、4 GiB、PID 512，身份与解释器检查通过；gateway drained、无活动请求，工作区双读稳定、agent 残留 0、容器／网络清理空，FrozenPatch entries 为空。

该交付只证明真实 CC 加桩接入、题面送达、公开解释器与空工件冻结。它没有实际执行非空候选 direct grade，也没有模型求解。**本次 R085 delivery 没有中性 brief**；brief 的独立文案审查不能冒充实际交付。统一 GPU 探针应继续使用正确题面和已审 brief，并保留实际模型首请求核对，属于现有执行流程的交付检查。

## 比例裁决与停止条件

没有成立的当前运行 `production_observed`／`production_reachable` 阻断。唯一新问题是正对照标签对调，采用追加勘误即可，成本小且不影响样本或 reward 分布。无需重复不变六方矩阵，也无需添加恢复 owner、retry 或 fail-closed 拒绝路径。

推荐结束本题 CPU 窄核，按现有流程进入探索性单题 GPU。仍未知的模型效果、未跑的新镜像逐项六方成绩、非空 FrozenPatch 共用直评范围、HTTP/1.0／gzip／全仓兼容不能计为通过；它们没有本轮错误放行的现实证据，不升级为当前阻断。aiohttp 同仓划分规则、训练／留出准入及 1c1／240d 的各自未完成 gate 保持独立。停止条件已满足：一轮具体反证完成，无需本题补跑或等待其它题结束。
