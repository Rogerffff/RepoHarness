# DVC9395：Coder 首臂题主语义审计

2026-10-03。作业 `gpu1003-dvc9395-coder-a1`，请求 `swe-dvc9395-behavior-r20-v1-20261003`，预算 `probe-wide-v1`。本报告封存候选／完整轨迹判断，不替代尚未执行的正式评分；独立报告另存，双模型请求未核销。

**解题正常结束，候选业务修复错误；原轮次因评分前 relay 清理超时，正式 reward 仍为 null／not_graded，不能计模型能力 0。** 候选先检查缺失输出再尝试恢复，真正缺失时后段不可达；新增 helper 仅做本地 checkout，没有新增远程拉取。源码判断与 infra 故障分别保留，后续应评分同一个原 FP，不重新求解来覆盖此轨迹。

## 原件与候选

[逐件读回和完整工具时间线](coder_a1_owner_evidence_readback_v1.json) SHA `6589a2b2d549b458d13ed8a945d62ba6eb32a3f8014d55e258369a74498cc3ce`：605 件封存文件、39,816,369 字节逐件核对，另有清单／同步回执两件元数据；baseline tar 615 条目按类型、执行位、内容匹配。558 行 CC、44 个工具全部输入／结果、全部模型陈述及 45 轮传输已审阅；未执行候选、模型、评分或云操作。

baseline canonical SHA `0c75caa0ac9790c739e0250f37125f342241d19d57bb430e6a6c7fa009acf0ec`；原 FrozenPatch canonical SHA `1cad35171d386f0d905859d0232d29d7df9a398872d62e6e71e98ffc8d0cd456`。业务仅改 `dvc/stage/__init__.py`，另新增根目录 `test_pull_fix.py` 与 `test_comprehensive.py`，原 FP 共 3 项。评分未启动，所以没有本题正式 projection、安装结果、测试节点或评分 hygiene 结论；其他作业的 projection 不混用。

### 1. 根因、修法与公开边界

题目要求 `dvc repro --pull` 能恢复普通数据源及 frozen 阶段缺失内容，并保留 dry／非 pull 边界。原 run-cache 路径已有 `repo.cloud.pull`；数据源／frozen 分支只有 `_check_missing_outputs()`。候选在该检查之后插入 `if pull: _pull_missing_outputs()`。基线 `check_missing_outputs()` 在任一 `not out.exists` 时立即抛 `MissingDataSource`，因此目标缺失场景到不了新增恢复逻辑。

新增 helper 再次筛选缺失输出，调用 `out.checkout(allow_missing=True)`，吞 `OutputDoesNotExistError`／`CheckoutError`。基线 Output.checkout 从现有 `self.cache` 取对象并恢复工作区，未执行 `repo.cloud.pull`；allow_missing 还允许 checkout 缺失返回 None。不能把本地 checkout 命名成自动远程 fetch。`out.exists` 本来是 property，不存在“忘写括号”的错误。这些判断依据原 baseline 与真实候选，足以确定修法未完成目标。

当前没有正式 41 节点结果或 F／P 数，不能沿用 CPU 校准的 c3 全通过来替模型候选填分。当前是源码错修判断，正式评分待同原 FP 恢复；没有发现需要改题目或模型公开说明的依据。

### 2. 定位与纠偏

模型读取 repro command、repo／stage 传参和 fetch／run-cache 实现，第 16 个工具约 10.682–11.146 秒已看到 run-cache 的 cloud.pull；随后正确定位数据源分支没有 pull。第 23 个工具约 16.888–17.358 秒明确读到缺失即抛错，却未处理顺序关系。第 26 个工具约 20.628–26.428 秒在检查之后插入调用，第 28 个工具约 27.163–29.638 秒加入 helper，核心错误一直保留。

后来新增 CheckoutError 捕获只是扩大吞错，不是正确纠偏。轨迹没有真实远程和缺失文件的失败→恢复实验，也没有回头检查缺失检查与恢复的先后次序。时间为传输边界，不是内部精确推理时长。

### 3. 工具使用

44 次调用为 Bash 22、Read 17、Edit 3、Write 2；2 次标记工具错误来自猜测不存在的 `test_repro_pull` 与 `test_repro_multistage_force`，均 exit 4／0 collected。模型读了 repo.pull／fetch 的真实 cloud.pull，却选择不会 fetch 的 Output.checkout。

工具 36 广泛功能测试转后台，轨迹第 558 行通知为 stopped，模型没有取得完整结果。工具 40 将 multistage pytest 管到 `head -20`，只留下前 11 项 PASSED，随后 BrokenPipeError；收集 17 项不等于 17 项通过。输出不完整而 Bash 未标错误，说明必须看正文，不能只看工具返回的 is_error。临时 DVC init 成功仅验证初始化，没有建立远程、push、删除数据或执行 repro --pull。

### 4. 实际并行机会

45 个请求每轮一个工具；工具 36 转后台后其他调用继续，但该测试最后 stopped，没有完整回收结果，不能当有效并行验证。此工具调用到下一模型请求约 120 秒，占主要等待；不是把 solve 减去 API 后得到的精确工具时间。实现／测试读取可批量；真实 DVC 变更与共享缓存测试需要隔离，不能一概并发。比增加并行更先需要一个可检查内容恢复的实际复现。

### 5. 自测与最终陈述

公开 reproduce 单元 3 项及 repro command 单元 2 项均通过，它们不检查本题远程恢复。广泛功能测试 stopped；管道测试只确认前 11 个可见 pass，未完整结束；两个不存在节点各自是选择失败，不能算能力测试失败或成功。不能合计成完整 repro 回归通过。

`test_pull_fix.py` 捕获 stage.run 的所有异常，只断言新增方法存在，未断言 checkout 或 cloud.pull 调用，更未断言内容恢复。mock patch 指向 `dvc.stage.utils.check_missing_outputs`，stage 已导入绑定的函数也使该 patch 不保证替换实际调用；无论该 mock 是否生效，hasattr 都能通过。`test_comprehensive.py` 正常 stage 明确打印失败但仍 exit 0；缺失 stage 抛错后又以方法存在打印成功。两个脚本都不能识别先检查后恢复这一错误。

最终“checkout 会按需远程拉取”“所有缺失输出已恢复”“保持全部功能”均超出证据，并与源码不符。模型没有新增既有测试目录的有效回归，两个根目录弱脚本留在原 FP。正式 grader 未运行，不拿未来可能的评分反向补成模型曾自测成功。

### 6. 效率、服务身份与资源

solve 215.507 秒；CC duration 206.557、API duration 56.380 秒；gateway response 加总 55.249 秒，首请求至最后响应 206.489 秒。累计输入 779,757、输出 6,657 token，单次最大 27,538／771。累计不表示上下文峰值；CC 估算 cost 4.06521 美元非实付账单。

45 个实际请求 `max_tokens=65536`、HTTP 200、attempt 1，SSE 完整，无 stream error、长度终止或观察到的压缩／恢复；context 196608、240 turns、10800 秒、1024 requests，未观察耗尽。metadata 32000 不替代实际输出预算。

作业前 10:13:05 UTC 有实时 engine／adapter capture，校验只读 mount、argv、HTTP 配置与 Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120`、BF16、TP1、context 196608、max-running 1。补充读回 `runs/category2_repair_20260929/repository_work/swe_dvc/q27_three_coder_operational_owner_readback_v1.json` SHA `84fb2d8871578ca1e2559251110fc0b6aaaa1ce0201bb3e71fab824786513d29` 核对 25 个模型文件大小，其中 16 个 safetensors 分片；不是重复全权重 SHA 或 GPU 内存证明。input config-only 字段原件保持，实时 capture 独立记录。

25 个有限资源样本截至 10:20:23 UTC；本轮没有 grader 实例化，所以没有 grader 峰值或 setup／test 成本。实际 solver profile 2 CPU／4 GiB／PID512；有限采样不证明全程资源峰值、全程无 OOM 或最低配置。当前绑定 setup budget 900 秒，不代表本轮实际完成过该准备阶段。

### 7. 结束原因与当前用途

解题 harness 0、CC success、end_turn／completed，完整原 FP 已捕获；实际镜像 `c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`、HEAD `c75a5583b3840ba90a8e800a0f42c1cb120916db`。gateway revoke／drain 后 active_requests 0。随后 `docker rm -f` relay 超过 60 秒，cleanup false／relay remaining，入口 exit 1，在评分前停止。不能将 solver 完成、资源后来关闭、正式评分成功混为同一事实。

恢复原件 `q27_dvc9395_cleanup_recovery_v1/readback.json` SHA `c0c5ca097db66ccdcd255987584a346722c2a619ee771fdfbfc57e7a48499c6f` 在 10:27:17／18 UTC 两次实际观察容器／网络消失；systemd MainPID 0、failed、ExecMainStatus 1，原失败及 cleanup false 未覆盖。该读回未执行候选或删除容器，grader 未实例化、grading 目录无结果。资源恢复不产生 reward。

GPU 负责人已安排首覆盖之后评分同一个原 FP，不新增 solve；本报告不自行调度。请求保持 claimed／active，Qwen 首臂及 Coder 原 FP 评分待返回，不 ACK／returned／清 active_request_id。源码错修可先进入训练信号分析，infra/null 单列；暂不扩材料、不普通重复、不把当前错修判断写成已获评分 0。稳定性与最终用途仍待证据及决定。
