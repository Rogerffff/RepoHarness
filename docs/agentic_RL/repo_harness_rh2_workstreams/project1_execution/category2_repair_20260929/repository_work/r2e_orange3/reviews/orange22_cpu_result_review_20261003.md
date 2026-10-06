# orange3 22e98：CPU 执行原件非作者窄核

2026-10-03，Codex 子核查者，按本批指定 GPT-6.1 Sol／high 配置。对象：`orange3__22e98f8f4cccc25f0d0217f9f4251b66d49b4237`、`r2e-mr-064`。**结论：本次范围内未发现阻碍提交统一 GPU 质量／基座诊断探针的实质问题。接受最终 CPU 交付与开发路径证据，接受限定复用历史正式 0／1／0。此报告不授予训练或留出资格，也不表示 GPU 链路已经验收。**

核查者未编写本题材料或执行作业，但继承了负责人交接和作者陈述，并接触私有 gold、评分 expected、历史反例与日志。因此这是 CPU 原件的非作者窄核，**不是 fresh 公开读者盲审**。已有公开阅读和材料语义审查按同摘要复用。本轮仅本地读取、JSON／文本比较与 SHA256 计算；无 SSH、Docker、安装、模型、历史矩阵重跑，也未修改源码、任务材料或公共登记。唯一可提交新增文件为本报告；抽取脚本和摘要留在忽略的 `runs/`。

## 1. 固定版本与历史复用

以[最终收据](../tasks/22e98f8f/cpu_acceptance.json)及[准备产物补收收据](../tasks/22e98f8f/prepared_artifact_receipt.json)为索引，读取对应实际原件。最终收据 SHA256 为 `3acdeea2c958480d13d09a05c9f61e8ebe8c1f17351c52e081a0405966983fd3`；补收收据为 `47e8241ccad199316aada2da7d7a4e95f4bb99ac7a95d767c1cf689cdbe369b4`。

- 第五版入口 `cat2-cpu-r2e078079-swe7-git-20261003-v1` 的 manifest 实算 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`；其全部 **837** 个文件的大小与 SHA 均匹配。registry v17、pins v18 与收据一致。本核查只解释本题，不替其它题或共享代码作全面验收。
- 本题 public／grading／environment／validation 四个 JSONL 任务行与首版逐字相同。grading 内容与064前的 `material_v11_20260929` 父行相比，仅修订号元数据不同；expected 原文、23键、隐藏文件清单／树摘要、run_tests 原文、parser／规则、gold 均未变。expected 23键全部要求 PASSED。
- 最终 CPU 实际镜像为 `sha256:ad9d2a37962ded93e7ec1f41a08a048262e0c0b31918bae6ab1179d1a863689c`，历史评分镜像为 `sha256:1985bc2376c7dbe4b8086c8a7f5cdaf06bb26301f2a632fc388100a1042f535d`。**两者不是同一镜像字节身份。** 可复用的依据是相同来源镜像 digest、base、评分内容和配方身份，加上本次工作树／依赖保持检查；不能写成新旧镜像 ID 相同或已直接比较所有镜像层。
- 从冻结 `recipe_v1.sh` 与 `sysconfig_v1.sh` 重算组合配方，得到 `r2e_derive_v1+sysconfig_v1`／`sha256:e2e17bf12b0edf5d1f77eb315a7c8cd91e36dde70b6a272c81b04976b98a7270`，与三条历史账本和最终 actor overlay 一致。实际 builder SHA 为 `5af7dc214976336ea440674bc4416cfa0a805881463798e05ebbb3e33af19471`。
- 21／21 个 build facts 为通过。另独立比较捕获的 base／derived 原始 integrity 清单：工作树 A 段及 `.venv` B 段逐行相同，runner 摘要一致；私有测试树、base HEAD 和不可读性由捕获 facts 核对。sysconfig 的 LIBDIR／INCLUDEPY 均指向 `/opt/py/`，`bad=[]`。

| 历史正式候选 | 已核账本结果 | 测试进程／段 | 差异键与清理 |
|---|---|---|---|
| noop | 0，22／23 | exec 0、test rc 1、segment completed | 仅 helper；keys equal、missing/skipped 0；removed true |
| gold | 1，23／23 | exec 0、test rc 0、segment completed | 无差异；keys equal、missing/skipped 0；removed true |
| DG | 0，20／23 | exec 0、test rc 1、segment completed | helper、重复离散类值、重复字符串类值，共3键；removed true |

三份历史 ledger 文件 SHA、目标行 SHA、report、verdict diagnostics、test、phases、cleanup 均与收据相等。gold patch SHA 对应当前 validation gold。DG 原始 eval SHA 实算 `b0563e4402a1c0f2d9cf0b82d789805ca7895f9465bde8cf073d844bf32e155d`；由 pytest summary 独立重建23键，20匹配、3失败，与账本相同。

**历史 noop／gold 原始逐测试 eval 的缺件不阻断此次复用。** 对整个 `runs/` 用仅文件名索引查找 `9aa57545`／`a1192ffc` 未命中；当前可读证据是完整账本与 driver log。driver 明确1200秒 grader 准备预算、最终退出0、10／10容器移除，无 halt／cleanup failure。既有非作者[Orange 修订审查](../../../../r2e_lifecycle_20260929/codex_reviews/review_revision_orange3.md)二.2曾核历史三组原日志摘要一致、noop0／gold1，明确允许不因 R-f 重跑；[隔离材料审查](../../../reviews/orange22_isolated_revision_review.md)也确认评分内容不变。本次补齐当前题面／准备／环境身份且没有评分变化或新运行异常，因此无需仅为补档重跑 noop／gold。

这并不等于本核查重新验证了两份缺件日志：**其 eval SHA 只能标“账本记录”，不能标“本轮实算”；本轮不能从这两份原始 pytest 输出重新解析23键，也不能核其中额外 warning、完整 setup 输出和失败堆栈。** 这些是记录完整性与本轮覆盖限制，历史结果仍按历史证据引用。

## 2. 准备产物、HTTP 与实际 CC 命令

补收的是既有远端产物，没有重新生成。五个文件的捕获 SHA 全通过；prepared manifest 实算 `3bfbbaadade56a579f50adb3bd26293b62854efd70d22d7846101a02147b38cc`，host grading 实算 `b428e59db0edc6b9909c36fa9a4c4ec12af43351a943838fdc047a8a5f2c8a9e`，均与 prepare、attempt 相同。任务数和私有行数均1；rollout public 与第五版 public 逐项相同，host grading 与第五版 grading 逐项相同，prepared prompt 与 actor 保存 prompt 逐字相同。

首 HTTP 的首 user 消息包含 CC 日期提醒和一个**逐字等于保存 prompt**的文本块；题面全文 SHA 为 `f8701d3a4322270fde2618cc7cfc094460c9a5f1ec874e400c5bfaeef9ec7199`，prompt SHA 为 `cbb5bef04dc66cc97fcd41eee2fcf2e31cebcb2dd15517a7c1f6e16d01a10697`。五次 gateway／stub 的 messages 与 system 均相等，实际 HTTP max_tokens 均4096；旧答案实现标记不存在。

四次真实 CC Bash tool call 与 stub_script 原文相同；其中三条开发命令在追加状态 echo 前与 `public_development_commands.json` 逐字相等。轨迹 tool result 验证如下：

| 命令 | 内部命令退出码 | 实际结果／覆盖 |
|---|---:|---|
| R2E preflight | 0 | 解释器、隐藏测试、git history 三项输出 ok，无 fail |
| 身份／导入 | 0 | UID/GID54321，`.venv/bin/python` 3.7.9、NumPy1.17.5；Orange 和 widget 从 `/testbed` 工作树导入 |
| 公开 helper 测试 | 0 | 1 passed；原测试通过不能证明一般映射已正确 |
| 重建关系复现 | 1 | 数字输入 `[8,4,6,8,4]` 输出 unique `[8,4,6]`、mapping `[1,2,0,1,2]`，在重建断言失败；符合 base 原缺陷 |

Bash 外层最后执行状态 echo，因此 tool result 没有工具错误不代表内部 Python 返回0；收据按 `RH2_STEP_RC` 保留1是正确的。字符串项因首断言中断未达；完整 widget 文件未运行。公开 brief 如实写明二者未测，没有借“覆盖数字和字符串”的命令目的冒充两例实测。

CPU prompt 没有交付来源 public_hints，也没有交付当前补充 brief；[探针草案](../tasks/22e98f8f/probe_request_draft.json)明确让执行者交付当前中性 brief 并审计真实首 HTTP。实际 solver 为 `stub_script`，上游本地脚本端点；CC 2.1.205 的真实启动／命令执行成立，**模型推理、求解能力成绩、真实 tokens／cost 和本轮正式 grader 均不成立**。

## 3. 原件完整性、限额与清理

收据、HTTP审计、绑定检查和准备补收索引引用的 **34** 个实际文件 SHA 全匹配；actor 捕获32个、derived捕获6个、prepared捕获5个文件清单均匹配。三个 archive 的 SHA 也按索引实算匹配。

actor prelaunch HostConfig 和 cgroup v2 同时证明2 CPU、4 GiB、512进程、swap0、无私有 bind／mount；agent有效权限为非root，外部DNS、禁连目标和直接上游均 denied，relay可达。准备复核容器的2 CPU／4g／512及60秒清理超时由真实CLI与results host事实记录支持；冻结 builder 使用带归属标签的清理并删除后 inspect，失败会抛异常。成功返回0支持其受管理检查容器正常闭合，但本报告没有独立远端 daemon inspect，也不声称 Docker build daemon 有同样限额。

actor termination completed、harness exit0、完整轨迹25738字节。原生 FrozenPatch entry0／empty／frozen export ok，classification projectable、unsafe false；排除区缓存变化如实保留，不能称所有路径未变。容器移除0、actor／relay／network无清理失败和残留；gateway撤销且drained、active_requests0；两个endpoint stop rc均0，收尾残留为空。

旧漏sysconfig首轮仍保留在 `cpu_actor_v1_receipt.json` 及旧 actor／derived 原件；最终当前绑定已更新，首版身份放在 `historical_first_release`。这次更新当前导航不等于把旧运行改写成使用新配方。

## 4. 阻断、非阻断与未覆盖

**阻断：本次范围内无新增阻断。** 可向统一执行者提交固定064版本的质量／基座诊断请求；无新增用户审批事项。

**非阻断：** noop／gold逐测试raw eval当前未索引到，保留上述证据降级和原账本SHA，不把记录摘要写成复算结果；新旧image ID不同，只宣称来源／配方／材料及所测运行条件对齐。当前绑定的历史／最终版本区分已由题主修正。

**未覆盖和执行者原职责：** 字符串单独复现、完整公开文件回归；真实模型求解及候选语义审计；GPU宿主实际image／配方／consumer、真实prompt＋brief交付、实际预算回读、正式评分及全新日志／逐键／终止／清理。历史DG setup303.302106秒使已验1200秒准备预算具有实际依据；CPU求解预算1200秒不能替代GPU grader准备预算生效证明。这些后续职责不应包装成本CPU已完成事项，也不由本报告授予训练资格。

离线脚本及40／40检查摘要：`runs/category2_repair_20260929/repository_work/r2e_orange3/orange22_cpu_non_author_review_20261003/{check.py,summary.json}`。脚本 SHA256 `faa757f7d786da8d785b7988af392f92b9e078a5c87b254363696c2cf35aef3c`；摘要 SHA256 `7149b932d5eafc7ea08bec6b0cd6d7b0ca0d11799078d2aa174a556a1a0a61fc`。检查计数是离线断言数，不是实验／候选数。
