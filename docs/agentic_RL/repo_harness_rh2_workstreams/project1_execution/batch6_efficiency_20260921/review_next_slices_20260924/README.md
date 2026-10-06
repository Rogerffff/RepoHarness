# #5、E1 实现及网络 / E5 / E2-E4 Brief 聚焦复核

2026-09-25，Codex。对象：`2cdc7314`、`2226c961` 的实现，以及 `f764df93`、`5f5320d2` 的设计文档。主仓库 HEAD `2226c961b87d45b44ee792d176b999e89d450ce1`；miles fork HEAD `275e31eb21ecceeb27cb0d1a522c6a59f348dc2e`。B 在 `manager.py`、`baseline_census.py`、任务面等处的未提交改动纳入消费者阅读，未修改、提交或回退它们。

**结论：E5 可以推进，E2 批量化方向成立；#5 有两处解析边界要修，E1 优化本身可接受但漏了观测运输；网络与 E4 先按下面的具体接缝修订 Brief。无需重开第六组方向决定，也不把所有切片串行挡住。**

| 对象 | 结论 | 下一步 |
| --- | --- | --- |
| #5 parse wire | 主路径正控通过，R1/R2 尚未收口 | 按真实 EOS 事实裁剪；缩窄悬空调用判据 |
| E1 权限初始化 | 当前生产初始化 / 复用顺序未见权限回归；R3 是观测遗漏 | 补 launch facts → audit → JSON 的运输后收口 |
| 网络 Brief | 1A+2A 已选；独立包 relay、宿主 token、断开网络、保留安装 shell 状态的方向合理 | 先修 R4/R5；网关本身可独立开发，grader 联网先不要按原稿落地 |
| E5 Brief | `--use-rollout-logprobs` 的窄配置方向成立 | 可实施无 GPU 部分；按 §4 收紧证据口径和范围 |
| E2/E4 Brief | E2 可准备批量实现；E4 的退役细节欠缺 | R6 写清后实施；R2E 可信命令入口修复与 B 顺序落地 |

## 1. #5：两处新判据超过了它能证明的事实

### R1 — P2：可见 EOS 字面量不等于实际 EOS token

- **现状 / 位置**：[parse_wire.py](../../../../../../rh2/src/repoharness2/adapters/slime/parse_wire.py) 第 28–38 行只看 `raw_output.rstrip().endswith(eos)`；第 10 行声称这等价于 `finish=stop` 且最后一个 ID 是 EOS。包装函数实际拿不到 ID 和 finish。
- **违反的范围**：已批范围是去掉真实终止 token 的可见表现；正文由普通 token 拼出的同名字面量仍应保留。
- **证据**：[HTTP 探针](probe_parse_boundary.py) / [结果](probe_parse_boundary.json)。使用本地真实 Qwen3.6 tokenizer、真实 RH2 adapter HTTP 入口、解析与 `record_turn`；仅引擎返回固定 token。普通 token 序列拼成 `The token is <|im_end|>`，全序列不含 EOS ID `248046`，finish 为 `length`。旧接口返回完整文本，新接口只返回 `The token is`，同时仍报告 `max_tokens`。真实 EOS 的正控正常剥除。
- **可达性 / 影响**：`production_reachable`，普通词表能生成该序列；不是实测模型发生率。它改变 CC 看到的内容及回放历史，不能因捕获 ID 未变就说交互未变。频率未知，不上升为普遍掉轮或 loss 错误。
- **最小修法**：在已经拥有 `TurnRecord` 和 tokenizer 的调用边界确认真实末尾终止 ID，再让解析使用去掉该终止表现的文本；原始捕获与训练 token 不变。不为保持 vendored 零改动复制整个 `_run_turn`，必要时登记一个窄接口补丁；不要用字符串猜测替代采样事实。
- **验收 / 分期**：本片收口前修；上面的普通 token + length 反例保持正文，真实 EOS 正控继续剥除，工具调用及原始 IDs/logprob/mask 不变。无需模型/GPU实验。

### R2 — P2：`ill_formed` 既有误报，也漏掉混合输出

- **现状 / 位置**：同文件第 42–44 行，原文任意处含 `<tool_call>` 且解析出的调用数为零，就标记格式错误。
- **证据**：同一 HTTP 探针中，`Use the literal tag <tool_call> in a parser test.` 被标为 `ill_formed=True`；一条完整 Bash 调用后跟一个悬空 `<tool_call>`，反而仍是 False。单独悬空调用和正常工具调用正控均通过。
- **可达性 / 影响**：`production_reachable`；目前只污染 `TurnRecord` / sample metadata 及计数，RH2 不据此新增拒样，故不是当前 reward 或准入 bug。
- **建议 / 验收**：围绕实际解析后的可见残余及已支持工具语法识别明确未闭合片段，不扫描全部原始 reasoning/普通正文。正常文本提到标签不能算格式错误；已经解析出一个有效调用也不能掩盖后续明确的悬空片段。若仅支持本次真实反例的窄形态，明确记录覆盖范围，不宣称完整坏调用检测。保持只改事实、不拒样、不纠正动作。

## 2. E1：核心优化接受，补一个实际运输遗漏

### R3 — P2：两项初始化信息没有随 audit 落盘

- **现状 / 位置**：[bringup.py](../../../../../../rh2/src/repoharness2/adapters/slime/bringup.py) 第 462、644 行分别写 `agent_user_init_launch` / `agent_user_init_bootstrap`。但 [generate.py](../../../../../../rh2/src/repoharness2/adapters/slime/generate.py) 第 3081、3955 行只吸收 `harness_log`，`RolloutAudit` 和 `write_execution_audit_record` 也没有两项字段。不是写进 ContextVar 就会自动进入审计。
- **证据**：[真实编排与 writer 的 CPU 探针](tracer_e1_audit_probe.py) / [结果](tracer_e1_audit_probe.json)。driver 发出两项，最终 audit 对象与落盘 JSON 均缺失；`harness_log` 正控保留。主审在 [main_e1_recheck/](main_e1_recheck/) 独立复跑一致。
- **可达性 / 影响**：`production_reachable`，通过真实编排与 writer、假 Docker/driver 验证运输；实际完成态的复用次数和耗时在生产证据中丢失，影响 E5 成本解释，不影响 chown 优化生效。
- **修法 / 验收**：沿现有 `finally` 复制这两项白名单事实到 audit，再由现有 writer 落盘；未执行的阶段保持缺失，不补零。验证正常结束与在已完成初始化后取消各一次即可，不需要一轮新的完整容器对抗测试。

接受的实现边界：正式 profile 固定用户/UID，可信清理及首次 chown 先于 root 标记；随后现有 CLI 安装和配置写入不改变 `/testbed` 的属主。复核失败仍用原初始化；不影响其它直接使用 vendored harness 的入口。driver 保持一次 exec、原 timeout/失败归因是合理偏离。E1+ 首次 copy-up 的收益仍未测。

文案顺手修正即可：核对分支仍执行 `git config --system --add`，不宜称整个脚本“纯只读”或该 `--add` 幂等；bringup 上方旧的“id 短路后 chown no-op”解释应删除。它们不构成额外阻塞项。

## 3. 网络：维持 1A+2A，修订两处实施接缝

### R4 — P1 设计阻塞：安装后不能让 root 执行候选解释器的 `pip list`

- **位置 / 现状**：[网络 Brief](../network_supply_brief_20260924.md) 第 85 行打算用 root 执行 `pip list` 并称沿用 S1-m。当前 [manager.py](../../../../../../rh2/src/repoharness2/grading/manager.py) 第 3003–3008、3067–3070 行已经按 I1 把前后观测改成候选 UID。
- **不变量 / 可达性**：`conditional_future`，拟议联网实现会重新引入已修的身份越界。候选能修改环境、激活脚本、可导入代码/包；root 启动 Python 或 pip 会执行这些内容。命令叫“观测”不使它成为可信读取。
- **修法 / 代价**：直接复用现有候选 UID 的观测入口；root 只做可信静态读取、网络和宿主控制操作。不加新 owner、重试或安全平台。安装观测仍只是诊断，不把它当不可伪造的包安装证明。
- **验收 / 分期**：实施 grader 联网前改 Brief；执行 pip/导入观测时 UID 必须为候选，失败不产生新 reward 判据。与 B 已修 I1 保持同一入口即可。

### R5 — P2 设计修订：单 shell 闸门的保证和异步收口要写实

- **位置 / 现状**：网络 Brief 第 59–73 行用候选 shell 的 `[ -e /rh2/net_withdrawn ]` 等待 root 文件；宿主另起轮询，失败主要依赖 shell 两分钟后退出 97。当前 `_run_eval` 是单次 await 候选脚本，新方案尚未说明并行 exec / 轮询的共同 owner。
- **证据 / 限制**：[Bash 与生命周期探针](falsifier_e4_gate_probe.py) / [结果](falsifier_e4_gate_probe.json)，主审[独立复跑](main_e4_gate_recheck.json)。没有放行文件，普通脚本退出 97；同 shell 加入 `function [ { return 1; }` 后直接进入后续命令。候选可写的激活脚本若被 source 能引入此状态；**普通 pip 子进程本身不能改变父 shell 函数**。这是拟议方案的边界，不是当前离线 grader 已遭绕过。
- **建议**：保留同 shell 所需的安装状态，但不要把 root 文件权限说成对候选 shell 的完整控制。`[[ … ]]` 可以消除该具体覆盖例，不能据此声称对任意候选代码都可靠。2A 已允许安装阶段读取或运行私有测试；我们仍要求宿主掌握正式测试的放行事实。若要保证正式脚本一定在断网后启动，优先评估“断网核对成功后，宿主才交付测试段/启动测试进程”，而非继续堆候选 shell 守卫；保留哪些 shell 状态及如何保留用一份小 Bash/exec 探针证明，不重做通用 shell 序列化。
- **必须补清的三个终点**：候选在安装信号前退出；撤网/核对失败；外层取消/期限到点。由同一评分 owner 终止并收齐 exec 与监控，消费同一实际剩余期限；撤网失败由宿主直接记 typed infra，不假定 shell 的 97 一定先于预算到期出现。未确认放行的作业不能按正常完成的离线评分交付。
- **分期 / 验收**：`conditional_future`，只阻塞 grader 联网切片按原稿实施。网关可先做。加上上述三个 CPU/假 runner 收口及一次 Docker 正常交接，无需重跑 216 题或增加正式训练闸门。

其余网络设计接受但需补入具体接口清单：

- `contracts/sandbox.py` 的 `NetworkPolicy` 枚举和 grading 只能 `deny_all` 的 validator 也必须迁移，不能只改 manager/profile。1A+2A 已授权相应窄契约演进，不需要再次询问同一个政策；旧默认仍离线。
- 索引与文件入口必须使用宿主绑定的同一包政策；验收包含已知文件 URL 直接访问、路径归一化和固定 release 例外，不只测 `/simple/<dist>` 404。缓存不等于冻结，下载/候选安装观测不等于环境终态精确重建。
- 取消、退出、评分结束都收掉 token/网络绑定；不要把每次 attempt 的网关状态永久留到 run 末尾。
- 沿用现有 P-A 的候选归因条件和资格基线。“编译错误归候选”不能扩成任何构建失败都给 0；网关自身故障同样不能仅凭候选声称取包失败来证明因果。资格与新评分脚本摘要如何对应应列入 B 接线。
- 每 0.5 秒一个 docker exec 不是必须固定的机制。实施时量其进程成本；若能复用已有输出流通知，可以减少轮询，不为此新增通用消息总线。

## 4. E5：可实施，保留证据能力的区别

我对照了当前 fork `actor.train_actor`、`compute_advantages_and_returns`、`get_grpo_returns`、参数校验、RH2 faithful DIS 和 G1/run_report 消费者。**效率档只加 `--use-rollout-logprobs` 这一选择正确；本配方不能使用 `--skip-actor-forward-only`。**

主审原样重跑 [09-06 CPU 探针](../../../miles_spike/external_infra_review_crosscheck_20260906/extra_actor_zero_probe.py)，新结果在 [e5_existing_cpu_probe.json](e5_existing_cpu_probe.json)：受测的优势、loss、抵消与非零梯度两种情况保持一致，非零梯度两档均为 `[-0.5, 0.5]`；从当前 actor 提取的原函数体显示额外 forward / 对拍消失，训练仍进入 `replay_backward`。这是 CPU 数值和替身控制流证据，**不是 Megatron/GPU、两步、多 PP、router 内部状态均已验收**；Brief 已安排的这些增量仍由实施者完成。

写码时做四个收紧，无需新用户决定：

1. 这里的 `rewards` 是 `_normalize_rewards_by_rollout` 处理后的训练列，不能将“逐 token 优势等于 reward”读成直接使用原始 0/1 评分。非末级 PP 等价探针与两步控制流继续保留。
2. 三态来自**有效配置和真实生产者**：诊断档缺事件仍是缺证据；效率档主动关闭才是“按配置不可用”。训练 replay 的 fill/consume/exhausted 仍必须检查，不能连同 logprob forward 一起跳过。效率档不能借 unavailable 得到“完整 G1 parity 已通过”的结论；首轮完整 G1 仍用诊断档。
3. 两种配置不需要为已有作业新增强制 profile 选择。建议保留诊断默认或在两份作业模板显式填写；依据最终 args 写证据，避免 profile 字符串与实际 flags 成为两套事实来源。旧 `launch.sh` 只作配方参考，不冒充已经按当前决定写好的八卡启动方案。
4. 先做配置、现有报告聚合与 GPU 核验清单；事件时间戳只能重建时间线，不能自行推出重算 token 数或 cache 命中。缺 producer 的量保持不可用。逐阶段显存 fork patch、心跳和外部采样器按实际缺口分别落地，不让整套新观测变成配置切片的前置。

## 5. E2/E4：实现方向可用，退役细节不能省

### R6 — P2 设计修订：完成记录按完成顺序退役，避开 GC 正在遍历的列表

- **位置**：[E2/E4 Brief](../e2_e4_consumers_brief_20260924.md) 第 60、68 行把成功 remove 作为裁剪点，保留“最近 256 条”，未定义顺序或 list 更新方式；当前 [manager.py](../../../../../../rh2/src/repoharness2/grading/manager.py) 第 2035–2042 行直接遍历 `_records` 并 await `_remove_container`。
- **设计反例**：以上生命周期探针使用真实 `close/gc/_remove_container`，只添加明确标为拟议的裁剪。256 条历史加 3 条活动记录，若 `_records[:] = kept`，close 只删除 `active_0` / `active_2`，留下 `active_1`；替换列表对象的正控清完。按创建序保留最近 256 条时，早启动而最后完成的任务也可能刚完成即被丢弃；按完成序保留则不会。
- **不夸大现状**：`conditional_future`。当前还没有这个 trim bug；当前 B 的每个 manager 串行评分，正常清理返回后同步读详情，中间没有新 await，**未证明 B 当前会丢读**。不因此建设消费确认平台。
- **最小修法 / 验收**：明确按完成顺序保留近期诊断；GC 用快照或在遍历后裁剪，活动/未确认删除的资源永远保留。覆盖上面两案、启动失败记录、取消/晚清成功和累计数。序列执行 N+50 例不足以覆盖遍历问题。
- **leases 也要说明释放**：当前第 1513、2233 行只有 list 初始化与 append。只加 `leases_total` 不会释放旧租约。可随确认删除的记录退役或限量留摘要；无日志的启动失败不能因永远等“有日志引用”而永久保留。`cleanup_failures`、queue events、audits 若本片不释放，就把内存平台期限定在本片被裁剪的容器历史，不能宣称整个 manager/run 内存已稳定。

**E2 批量 coreutils 方向没有发现必然语义冲突。** 私下收集并验证整批结果，成功才输出；失败回退不能先输出半批再追加旧路径。真实 Linux 差分应包括空树、空格/反斜线/TAB/LF 文件名、权限位、软链、单个摘要失败与缓存/排除区；保留脚本关键字让旧替身通过只能证明接线，不能作为等价证明。不要强制把 B 的无关工作全部做完才开工，按相关文件/函数交接即可。

E4b 先索引事件但不删，可避免反复全表扫描，不等于内存有界；终局释放若只是落实已批的“消费者完成后回收”，属于具体接线，不必天然另立 T0。audits 大对象先测量，维持原分期。

## 6. 三项所谓“新拍板”如何处理

| 项 | 本轮意见 |
| --- | --- |
| #4 匹配规则 | **deferred T0**：维持已批 I01 B、接下一轮 B 的覆盖观测，不需要为了“暂不修改”再拍一次。改模型实际可见历史时再讨论。W1/W0 的已存结果已对上 5/2 行、16785/6842 输入；未重跑 CC。撤回“空白只影响文本，因此语义等价”和“键序零风险、一半收益”两句泛化：源码/字符串/测试可依赖空白，键序变化也改变模型 token；该剧本不能证明普遍收益。 |
| R2E root PATH | **false-positive T0**：恢复“root 不执行候选可写程序”的既有边界是修 bug；不应等待一次新的安全放宽决定。绝对 shell 路径加可信工具 PATH 仅用于 root 的可信操作，不能把 agent 的 `.venv` 激活也一起禁掉。与 B E09 对齐，R2E 正式运行前修；不必等 E2 吞吐测量。当前证据是 B 的实际 PATH/可写性加调用链，本轮未做 Docker 攻击。 |
| `0x01` 路径停批 | 建议先按**既有不支持候选工件的处置补漏**：在具体的候选路径解析边界给 typed 不支持原因，复用已批 unsafe 通道，保留事实、无 reward、按完整组规则处理。不要把整个 `ValidationError` 兜底降成单题损耗；我方身份/摘要/契约矛盾继续 fatal。如果要改成 reward 0、支持新的文件名协议或新增处置通道，才是新的 T0。当前末段 fatal 仍标源码可达，不冒充完整真机复现，实施验收须补正常文件、该控制字符和我方契约矛盾三个对照。 |

网络 1A+2A 已按用户 09-24 答复登记，不再询问同一选择。机器继续按用户授权保留；本轮没有登录或销毁，也没有向 B 任务发送消息。B 接线仍由已有 handoff 交接；#5 接口修订后同步其示例。

## 7. 本轮验证、修改与停止条件

- 相关维护测试：从 `rh2/` 执行 `.venv/bin/pytest -q tests/adapters/test_parse_wire.py tests/adapters/test_e1_agent_user_init.py tests/adapters/test_startup_fix_1_activation.py tests/adapters/test_startup_fix_2_host_collected.py`，**87 passed**，包含 E1 的本机真实 Docker 用例。未跑全库、双 lane、216 题或远端/GPU。
- 独立探针：真实 tokenizer/adapter 六组新旧解析对照；E1 真实编排与 audit writer；E4 拟议裁剪及本机 Bash 闸门正反控；当前 fork 的既有 CPU loss/actor 控制流探针。每个工件均标明替身边界；历史事实只回读、不改写。
- 按审查标准 §10.4 用一对有界 tracer/falsifier 检查权限、网络和生命周期；主审独立核对及复跑关键证据。重点 A/D/E/F/G/H/I/K/L/M/N；B 只核本次没有新增 reward/mask/准入改变，未扩成算法审计。
- 本轮仅新增本目录审查/探针工件、各 Brief 的复核指针与 `infra.md` 记录；未改生产代码、配置、测试 oracle、fork、部署或网络边界，未提交/push。
- **停止条件**：#5 修 R1/R2、E1 修 R3 的窄回归即可收口，不重审全部启动链。网络先改 R4/R5 再进入 grader 联网切片；E4 补清 R6 后可实施；E5 和不碰候选执行身份的 E2 准备不等前两片全部结束。新证据未显示其它当前训练语义回归，不追加整池/GPU验证要求。
