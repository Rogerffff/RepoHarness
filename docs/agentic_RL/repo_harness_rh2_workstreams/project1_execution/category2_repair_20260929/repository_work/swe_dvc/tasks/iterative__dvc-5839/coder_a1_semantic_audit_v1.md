# DVC5839：Coder 首臂题主语义审计

2026-10-03 15:10 SGT。请求 `swe-dvc5839-precision-values-r10-v1-20261003`，尝试 `gpu1003-dvc5839-coder-a1`，材料 `dvc5839-precision-values-v1`，预算 `probe-wide-v1`。这是题主对原候选及完整轨迹的审计；独立语义复核尚待封存，当前不核销请求。

**实际业务修复正确，与 Qwen3.6 的业务源码逐字相同，正式评分 23/23 通过；模型自己的验证没有直接证实命令精度生效，最终“所有功能保持完整”的陈述过强。** 这两个判断分别记录。未发现需要改题目、公开说明或评分断言的阻断，但一次通过不支持稳定性或训练资格。

## 原件与候选

[题主逐件核对和完整工具时间线](coder_a1_owner_evidence_readback_v1.json)记录封存清单 152 件、7,657,883 字节的实际 SHA/大小核对、254 行 CC 轨迹、20 次工具和全部结果、21 轮 gateway 请求／响应／adapter 记录。双模型回执中 25 个文件指针均核对；baseline tar 的 547 个条目按类型、执行位及内容逐件匹配。此次没有重跑候选或评分。

baseline canonical SHA 为 `e9062a880a5d58acc4e0edc5f1fb014cc13c0c5c33daef1e70b35b39451942f1`，原 FrozenPatch canonical SHA 为 `cc7022fa9a8215627058c0cdca8c0546d783d1d0f6ab56d4a1e4363dcfc5003c`。严格解码原 FP 内容，与实际基线相比，业务文件仅补 `precision=self.args.precision`。宿主 git diff 仅供审阅，评分直接消费原 FP。

完整 FP 及实际 projection 均为四项：业务文件，以及 `.dvc/tmp/links/cache.db`、`.dvc/tmp/md5s/cache.db`、`.dvc/tmp/updater.lock` 三个生成文件。两份数据库各 32,768 字节、SHA 相同；对捕获字节作只读检查得到 Settings 16 行、Cache 0 行，不推断运行时完整缓存状态。锁文件 6 字节。模型清理了三个临时 Python 脚本，但这些 DVC 生成文件仍被捕获。正式 hygiene clean 表示未触犯当时路径／测试修改约束，不能解释成“完整候选只有一行改动”。保留原 FP，不在题主侧悄悄删文件或重评分。

### 1. 根因、修法与公开边界

`CmdMetricsShow.run()` 的表格分支漏把解析好的 `self.args.precision` 传给已有 `_show_metrics()`；helper 在没有参数时回落到 5。候选只补传参，沿用原有 rounding，没有固定 8 位、数值特判或修改测试；默认、JSON、指标读取及 `metrics diff` 的源码未变。

公开 CLI 定义的是小数点后 n 位，默认 5，不追加科学记数法有效数字要求。Coder 的 helper 示例中默认 mae/mse 为 `1e-05/0.0`、8 位为 `1.483e-05/1e-08`、3 位为 `0.0/0.0`，符合该 rounding 行为。但这些只是 helper 输出；实际命令修复成立的依据是调用路径和正式真实数值评分，不将 helper 示例升级为模型实际 CLI 验证。

原 2 个 F2P 与 21 个 P2P、共 23 参考逐一匹配实际 23 个 PASSED；无 missing、skip 或多余未计节点。新增真实数值 F 覆盖命令解析、默认／3／8 和 Markdown，评分 1 与候选语义一致。没有发现需改材料的高分错修，也不宣称这些测试覆盖所有合理实现。

### 2. 定位与纠偏

第一次 Bash 搜索 `metrics.*show` 的 Python 文件，第四个结果就是目标 command 文件；随后 Read 完整 336 行实现。第 3 轮 API 已正确说明漏传 precision，并使用同文件 `CmdMetricsDiff.run()` 的正确传参作对照。以首 gateway 请求为零点，源码结果进入约 1.449 秒的请求，正确诊断生成区间约 1.449–2.441 秒。Edit 在约 5.900–7.273 秒生成，结果进入约 7.315 秒的下一请求。

模型先读公开单元测试、运行一个 precision helper 测试及公开提示的 helper 对，再作唯一一次 Edit；没有错误修法或回滚。公开入口已给出 metrics show 的任务与测试线索，不能据此评价无提示的大仓库定位能力。上述时间是可观察传输边界，不是内部每一步推理的准确计时。

### 3. 工具使用

20 次调用为 13 Bash、3 Read、1 Edit、3 Write。序列是搜索实现 → Read 实现／单元测试 → 两次 helper 基线测试 → Edit → 重跑 helper 对 → 写／跑 mock 脚本 → 完整 metrics 单元模块 → 再搜索相关功能文件 → precision 筛选 → Read 功能测试 → 两个普通功能测试 → 两份直接 helper 示例 → 清理脚本 → git diff。

唯一工具错误是 `tests/func/metrics/test_show.py -k precision` 返回 exit 5，18 deselected，没有匹配测试。模型之后读取功能测试，跑 `test_show_simple` 与 `test_show`，两项通过；这是改正测试选择，不等于补上 CLI precision 覆盖。路径与解释器可用，没有依赖安装、失败重试循环或错误文件编辑。

再次搜索和编辑后重复 helper 对提供的信息有限：helper 在原实现就通过。三个独立临时脚本可合并，先读功能测试也可避免空筛选。这些效率问题不改变修法正确性。

### 4. 实际并行机会

21 个模型请求每轮至多一个工具，没有观察到多工具并发或后台重叠。实现与测试文件读取可以批量提交；多个 helper 示例可以一次脚本完成。测试／命令会写同一 DVC 工作区与缓存，因此不能笼统声称所有 CLI 和测试安全并发。Edit、结果验证、最终清理有先后依赖。

记录的是本次未使用少量批量机会，不推断模型缺乏并行能力。此题单行修改、主要自测仅毫秒到亚秒，批量收益有限，不以并行数量作解题质量替代指标。

### 5. 自测与最终陈述

模型跑了原公开 metrics 单元模块 22 项，全部通过；两个普通功能测试也通过。其 `test_precision_fix.py` 虽解析 precision 8 并构造真实 command，却只断言返回值 0 和 logger 被调用，没有断言实际数值或传参。旧实现也可以满足这两项条件，因此这个脚本不构成漏传 precision 的回归检测。

`manual_precision_test.py` 和 `scientific_precision_test.py` 直接调用 `_show_metrics()` 并打印默认／3／8 的输出，没有通过真实 `metrics show` 命令，也没有新增数值断言。原 helper 本就支持 precision；不能把打印结果当成命令错误已被模型实测修复。没有修复前 CLI 失败→修复后同路径通过的证据，也没有持久新增回归测试。

最终“22 个 metrics 测试通过”“helper 能处理不同 precision”有原件支持；“科学记数法现在生效”若指 CLI，超出自身验证范围；“所有功能保持完整”不能由 22 个模块测试和两个普通功能测试保证。这是非阻断的验证和报告习惯缺口，不据此把正确业务候选判成错误。grader 的 23 项真实评分覆盖单独记录，不能补写成模型自己执行过。

### 6. 效率、服务身份与资源

solve 33.683 秒；CC 内部 duration 30.139 秒、API duration 24.918 秒，gateway response 耗时加总 24.44 秒，首请求至最后响应约 30.079 秒。范围不同，不能相减后命名为准确工具时间或推理时间。21 轮累计输入 279,091、输出 3,190 token，单次最大输入 18,022、输出 444；累计输入含重复上下文，不代表接近 196,608 上下文上限。

21 个实际请求均 `max_tokens=65536`，HTTP 200、attempt 1，SSE 完整，无 stream error、压缩／恢复或长度终止。CC metadata 的 `maxOutputTokens=32000` 与实际请求不同，不能据此推导截断。CC 估算 cost 1.475205 美元，不是实付账单。

Coder 作业前约 06:36:32 UTC 的原始 capture 绑定实际 engine／adapter 容器、启动时间及 restart 0、只读 model mount、SGLang argv 和 HTTP 服务读回：`Qwen/Qwen3-Coder-30B-A3B-Instruct`，revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`，BF16、TP1、context 196608、max-running 1。28 文件下载清单及 25 个权重文件数／大小已核；没有重复逐权重 SHA 或 GPU 内存权重证明。旧 identity binding 文件的复制与本次实时 before-job inspect 分开，不把复制时间当首次创建时间。gateway 自身 `checkpoint_identity_verified=false` 不覆盖此独立 operational capture，也不升级成完整权重证明。

正式评分 total 253.002 秒、env reset 14.001 秒、prep 0.399 秒、report test 4.686 秒；pytest 正文 0.40 秒。candidate install 3.114 秒、candidate test 1.035 秒来自诊断，计时范围不同。报告峰值 1019.691 MiB 单独保留，不把准备成本归到模型慢，也不从总时间推导未分段 setup 子步骤。

24 个有限资源样本覆盖 actor／relay／grader，按实际 CID 区分；actor 5 个样本最高 873,177,088 字节、grader 17 个样本最高 1,039,114,240 字节，采样中 OOM kill 0。15 秒采样可能漏掉短安装／测试，diagnostic resource_facts 的 null 保留，不声称全程峰值、全程零 OOM 或最低可用配置。

### 7. 结束原因与当前用途

CC success／exit 0、stop_reason end_turn、terminal_reason completed；日志完整。gateway revoke／drain 后 active_requests 0；actor、网络、relay 清理结束，grader manager created 1／removed 1，open 和 cleanup failures 为空。实际 R10 cb175 镜像、UID54322 四 wheel prerequisite verified／exit 0、candidate install 0、test 0，未继承旧 R7–R9 安装成功假设。未观察预算耗尽、infra 中断或输出截断。

当前为“单次候选业务语义通过，验证陈述和生成文件残留有非阻断缺口”。保持材料和公开说明；不需要为了取得通过重采样或改断言。待独立语义报告读回后，可核收这次两模型首轮请求；题级稳定性、必要重复及训练／留出用途继续单独待决。全部运行和历史报告保持原件。
