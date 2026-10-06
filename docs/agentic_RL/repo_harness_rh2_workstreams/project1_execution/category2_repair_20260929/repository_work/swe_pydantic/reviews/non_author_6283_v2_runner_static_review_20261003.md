# 6283 v2：正式 CPU runner 及输入生成器的非作者静态窄核

2026-10-03。**本次增量静态核对通过，未发现新增入口阻断；可以接续实际发布后的输入固定与正式 CPU 工作。** 当前没有 `6283_privateattr_v2/formal_inputs.json`，本报告不预审其内容，也不宣布发布、local prepare、41 参考四行矩阵或真实 PrivateAttr 观察通过。材料语义复用[上一份 v2 窄核](non_author_6283_privateattr_v2_material_review_20261003.md)，不重审原材料或重跑旧矩阵。

我不是 runner、生成器或材料作者；已接触旧私有测试、gold、负对照、Qwen 原 FP／旧评分和审查上下文，不是 fresh 公开读者。本轮只读源码，以本地标准库核 SHA、diff、AST 和独立核对表达式。没有执行 runner、输入生成器、git apply 子进程、Pydantic／core、Docker、SSH、模型或项目 pytest。只写本报告与[JSON 记录](non_author_6283_v2_runner_static_review_20261003.json)。

## 绑定身份与增量

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| [新 runner](../cpu_acceptance_20261003/6283_privateattr_v2/run_formal.py) | 23684 | `40b0460b70c2890a1eb3fbbf2474e10bee906125e3068868079370044d875805` |
| [已审 R14 runner](../cpu_acceptance_20261003/remaining/run_formal.py) | 22791 | `b127f7309ffae3eae2bbe834c595f846104406e2f858b8073ff2182d0a2ce3c5` |
| 输入生成器 `generate_6283_v2_inputs_v1.py` | 8472 | `7a41967b906688086383f6cfeb9466aad95a6ca8d0f023acccbd7c0cdd9a81fe` |

生成器位于 `runs/category2_repair_20260929/swe_pydantic/cpu_preparation_20261003/`。新 runner 的[来源草稿](../cpu_acceptance_20261003/6283_privateattr_v2/runner_provenance_draft.json)与以上两份 runner SHA 一致。接续[既有 R14 入口审查](non_author_remaining_runner_review_20261003.md)；题主报告其已有实际运行，本站静态核查未新增现场证明。

完整 diff 与 AST 核对确认：只改题级 docstring、`6283` CLI 选择及 run_id 匹配、公开 actor 复用范围说明、补充观察 payload 和四条 PrivateAttr 核对语句。将这些明示增量归一后，整份 AST 与旧入口相同。尤其 `execute` 与 `spec_record` 完整 AST 未变，七段正式脚本名称、取法、比对、FrozenPatch 重放和原 binary 评分调用未变。

七段为 eval、trusted setup、candidate test、candidate install、test after install、pre-candidate observation、post-candidate observation。资源／预算设置及清理逻辑未改：2 CPU／4 GiB、PID512 的实际检查，既有 spec／ReplayBudgets 消费、manager close 300 秒和标签残留检查均接续旧入口。保护 300 秒的正式脚本生成／交接路径也没有增量改动；**新 spec 的实际脚本、hygiene 与预算身份仍待正式输入及 prepare 到位后核对**，不能由静态 diff 代替。

host runner 与嵌入的候选观察 Python 均可按 `ast.parse(feature_version=(3,8))` 解析；生成器也通过该语法解析。这是语法检查，不证明整个 host runner 的 Python 3.8 标准库兼容性或目标环境依赖执行。

## PrivateAttr 观察确实使用候选依赖

新观察脚本在 `/testbed` 激活 `conda testbed` 后调用 Python，实际 `import pydantic, pydantic_core`，并从 Pydantic 导入 `RootModel, PrivateAttr`。它定义与私有 P2P 一致的 `RootModel[int]` 子类，再读取普通构造及 `model_construct(42)` 的 `_secret`。没有替身类、源码方法提取或标准库机制模拟。**这是计划中的实际依赖观察路径；本次没有执行它。**

观察同时记录解释器、UID、版本、core、Pydantic 路径、源码／imported module SHA、测试保护状态与 cgroup。原核对继续要求 UID54322、testbed Python3.8、指定 core、`/testbed/pydantic/__init__.py`、候选源码身份和受保护测试身份。生成器固定的 imported module 集合包含 `pydantic.main`、`pydantic.root_model`、`pydantic._internal._model_construction`，覆盖构造、Qwen 修改处及私有初始化机制。当前尚未产生冻结输入或实际 module readback。

候选预期由新输入的 `privateattr_observation_expect` 提供；普通构造始终独立要求 `abc`：

| 行 | 普通读取 | construct 读取 | construct 异常类型 |
| --- | --- | --- | --- |
| base／noop | abc | abc | None |
| gold | abc | abc | None |
| validate_construct | abc | abc | None |
| 原 Qwen 源等价负对照 | abc | None | TypeError |

这些都是未实测预期。新 runner 保存真实异常的 type／message，只匹配类型，不绑定错误文字。普通构造读取位于 try 外，失败会让观察脚本非零／无法产生唯一 audit JSON，阻止自动核对成功；construct 的普通 Exception 被捕获并记录，不吞作成功值。新的核对表达式没有改 formal report 的 reward、outcome、test_rc 或参考 states。

额外观察仍放在正式 `post_candidate_observation` 完成之后、容器清理之前；命令限时 **25 秒**、KILL 宽限 **2 秒**、host `asyncio.wait_for` **30 秒**，与 R14 相同。超时／缺失观察记录导致独立检查失败，保留原件并停止后续候选，不能因此把环境异常计为题目 0 分。正式参考和原评分仍按原 consumer 计算。

我仅将新增两条 AST 核对表达式用于人工构造的 JSON：四种预期形状可匹配，错误普通值、错误异常类型及正负形状互换均被拒绝。该检查只验证表达式的判定逻辑，没有候选执行、时长测量或 Pydantic 结果，不能列入 CPU 实测。

## 输入生成器的静态边界

生成器没有内置伪发布内容。它先要求新的输入文件不存在，再检查 bundle 位于实际 release repo，逐成员核完整 release 文件集合、SHA／大小和无符号链接；核实际回执的指定新 request、cpu-a、safe_closed、release 路径及 manifest SHA。随后匹配已发布 grading 的 revision、完整有序 F2P／P2P、effective patch、base 和安装资产／配方，核 publication 材料清单成员身份。**这些是代码中的条件，尚未实际核收回执或运行生成器。**

候选固定为 noop／gold／validate_construct／qwen36_a1_pop_private，要求 2 F2P＋39 P2P 且唯一新增 P2P 名称正确。对旧 R7 输入只执行读取与相等断言：base、public digest、base／derived image、core 和安装配方相等，F2P 原序相同，P2P 去掉最后一项后与原38项完全相同。公开 actor 的复用仍附有真实旧交付原件的非作者核查与身份等价条件，修改说明本身不构成新 actor 验收。

required_statuses 的静态范围正确：gold 全41通过；noop 两个 F 失败、39 P通过；Qwen 原40通过且新增 P失败；validate_construct 要求两个 F及新增 P通过、原 `test_construct`／`test_construct_nested` 失败，其余参考仍由 runner 要求逐ID有合法终态。对应整题预期 0／1／0／0，未冒作新分数。

有效测试与各候选生产文件只复制到临时目录，两个 subprocess 调用均为该临时目录中的 `git apply`；据应用产物生成新的 source SHA。新输入最终以 `open('x')` 排他创建在独立 v2 目录，防止覆写已有固定输入。代码中没有改旧 formal_inputs、原 GPU FrozenPatch、raw reward 或 GPU 原件的路径，也没有派发／Docker／模型命令。**新 CPU 源等价负对照会使用新材料和 CPU 镜像，不能称为旧 GPU FP 重评分。**

题主所述此前多括号 AST 错误发生在生成器写文件前；本次只确认当前文件 SHA及 AST。没有把该内存失败当作已生成输入或运行结果；当前目标 formal_inputs 仍不存在。

## 当前状态与下一次增量核查

据题主当前交接，新发布请求已提交，旧请求 safe partial 的 ACK／clear 已核收；本轮未重复核查这些控制面回执。旧 GPU 安装修复后的重评分与最小 PrivateAttr 观察**明确尚未执行**，41 参考四行真实 CPU 也仍待；旧 raw reward、FP 和历史材料继续保留。

实际发布到位后，可仅增量核正式 release／bundle／回执与生成的 formal_inputs 的字节和身份、完整原40序列加新 P、四个 source／import SHA／异常预期、七脚本／hygiene／预算及公开 actor 复用条件。之后读取四行真实安装、41参考原件与 PrivateAttr 观察、FP／完整 baseline 运输和清理证据。无需重审已核材料；本报告不授予 CPU／GPU／模型完成或训练资格。
