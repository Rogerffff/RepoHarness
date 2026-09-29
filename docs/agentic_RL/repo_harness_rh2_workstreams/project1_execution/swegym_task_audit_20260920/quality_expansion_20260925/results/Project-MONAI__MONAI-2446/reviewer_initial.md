# Project-MONAI__MONAI-2446 独立初判

结论：可保留为受限开发诊断静态候选，state=needs_review，scope=static_review。公开问题清楚，gold 对常用 list 的浅拷贝修复与旧随机缓存行为相容；历史修订 grader 有真实分差。仍需实际 actor 公开复现，且现有验收只保护一种输入容器/数据样式。不是 ready_for_probe 或训练/正式评测批准。

## ①身份与②公开需求

base 为 `05b2da61d70324c2f02b5d72429ddb7cc171b9b9`，公开、grading、历史 host grading view 的本题行一致。题面明确要求 shuffle=True 时仅内部打乱，不改原 data_list；既有 API 还承诺 seed、cache_rate 和后续滚动更新。base `monai/data/dataset.py:681–685` 直接把原参数传入 randomize；`:712–716` 对其执行 `self.R.shuffle(data)`，与公开输出的外部列表重排直接对应。Dataset 在 `:70` 保存传入对象，CacheDataset 在 `:548–586` 从 self.data 装载缓存。

## ③需求—断言双向表

下表包含全部 F2P、P2P，测试名均在 `tests/test_smartcachedataset.py::TestSmartCacheDataset`。

|公开需求/原有行为|断言及测试身份|覆盖与反向依据|
|---|---|---|
|外部原列表顺序不变|F2P `test_datalist`（patch新增全体13行）：5个独立单元素 ndarray，copy.copy 备份，默认seed=0，构造后 assert_allclose(data_list, backup)|直接覆盖题面原例；只比较值/顺序，不比较对象身份，且备份与原列表共享元素。没有要求深拷贝元素。|
|内部仍按seed打乱并滚动更新|P2P `test_shuffle`，base :103–127：seed=123，3轮更新后第15项依次为18/13/5|防止简单全局禁用shuffle；是既有确定性序列，不绑定必须使用copy。没有检查所有内部项或新增F2P那一份 ndarray 数据的内部顺序。|
|shuffle=False保持缓存滚动规则|P2P `test_update_cache`，:74–101：比较保留后8项、替换后2项|公开类文档的running-window算法；不测输入别名、其它容器或随机开启时完整窗口。|
|图像变换/线程路径仍工作|额外执行但不列入expected的 `test_shape_0..4`，:24–72|合成NIfTI临时文件、缓存长度/非空、图像与标签相等；共有5组replace_rate/worker/transform。未把它们误写成P2P。|

完整读过新增断言、上述3个expected测试及5组旧测试；决定性helper为 randomize、Randomizable.set_random_state (`transforms/transform.py:138–170`)、Compose(None) (`compose.py:104–115`)、Dataset/CacheDataset访问和SmartCache的start/update/shutdown/替换线程（dataset.py:668–866）。

## ④实现空间、漏测与gold

gold 仅在 shuffle 分支引入 `data = copy(data)`，传给父类的是私有浅副本；同 seed 的 RandomState 与缓存算法均不变。list切片/list(data)、在内部持有索引置换也是合理非gold路线，前提是保存公开/既有seed与窗口语义。深拷贝不是题面要求，会额外增加资源消耗并改变元素别名；测试未强制它。对于任意自定义Sequence的copy语义没有穷举证明；不可把未测tuple/自定义容器行为直接判成gold新增回归。

漏测（check25）：只对array列表禁用shuffle、而dict列表照旧shuffle的错误分支可静态构造为通过F2P及现有P2P，却违背“only shuffle…in dataset”；未做此反例执行。浅备份也不能发现对元素内容的共同原地修改。最有价值的质量补强是同一构造同时检查外部顺序和内部seed序列，而非要求某种拷贝实现。P2P精确seed序列可能拒绝改换随机算法的解，但这是保留既有确定性结果的约束，未见必须按gold代码实现的误拒证据。未发现已证gold新增回归（check26 unknown，不是issue）。

## ⑥公开开发需求与条件

|需要的操作/资产|公开依据|已有证据适用于谁|缺口|最小公开命令/预期|
|---|---|---|---|---|
|从工作树导入numpy/torch/MONAI|requirements.txt、README、题面|历史grader导入`/testbed/monai/__init__.py`|actor解释器/导入源/写权限未知|实际actor打印sys.executable与monai.__file__，接着执行题面构造；base外部顺序变成2,0,1,3,4，合法修复仍0,1,2,3,4。|
|相关窄测试及临时NIfTI写读|CONTRIBUTING.md:97–115；旧test_shape需nibabel/parameterized|compat-v1 grader安装nibabel4.0.2后本模块8项执行|actor是否有兼容依赖、临时路径权限待验|`python -m tests.test_smartcachedataset`（公开base仅7项）或等价窄pytest；修前旧测试应能运行，目标原例另测。|
|修改源码并使其生效|public_hints非测试源码；setup.py默认BUILD_MONAI=0|历史editable develop及import路径|actor实际工作树、包来源未知|保存非测试源码后重复同一公开原例；无需GPU、权重或外部数据下载。|

公开原例只需小数组和CPU；旧模块需本地临时NIfTI，无题目必需网络服务。依赖供应网络属于准备条件；历史deny_all下成功不证明任意actor pip可联网。

## ⑧用途与唯一优先下一步

任务二在正式 actor 入口执行“身份/源码路径记录＋题面原例＋公开窄测试”，明确base目标失败与依赖失败；无需为本题重跑全仓或调用模型/GPU。质量补强建议与actor资格分开保存，不擅改生产验收。检查映射：2/18/19/20仅在下述历史范围有支持；3/6/8/10/13/14/15/26/29–36保留unknown或not_checked；23明确，25存在上述漏测，27仅常用list修复得到支持。未检查编号不记pass。

## 边界与八方面口径

本稿为 fresh reviewer 的独立静态初判，未读任何 public_read、主审初判/card/record/delta、旧质量报告、history、其它包或根汇总。共享目录按允许路径控制暴露，不声称 OS 隔离。只读指定三题公开/私有材料及其精确原件引用；只写本 reviewer_initial.md。没有执行/导入项目、测试、安装、网络、容器、SSH、GPU 或模型，没有修改题目/评分，也没有派发新运行。

八方面分别为：①身份与公开输入；②题意与合法实现；③新增测试及原断言；④gold与相关调用者/回归；⑤历史执行与评分；⑥actor开发条件；⑦泄漏、提交和控制面；⑧用途及下一步。下文逐项覆盖，不以八个 pass 代替范围。

共同限制：base_identity 是明确 base_commit 的跟踪 Git blob 导出，actual_actor_worktree=unknown；计划 user_prompt、public_hints 不等于实际模型消息。实际镜像 HEAD、来源规定初始改动、准备后 porcelain status 的输出/退出码/阶段、忽略资产、UID/HOME/cwd/PATH、源码导入和写权限均未获本轮 actor 证据。历史 grader 日志中的普通 git status 是当时 grader 阶段，不替代上述记录；git show 中的 diff 是提交内容，不是未提交变更。合法解可改非测试源码；未发现需要额外路径排除。审查者已暴露 gold、隐藏测试及本题原 grader 结果，审查资料不可交独立 solver。实际泄漏/控制面抗篡改、全库重复/留出重叠、真实 CC 交付和能力/训练适配没有据此认证。

## ⑤原始运行与评分证据

- gold：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/gold/ledger.jsonl:1`；日志 `runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/gold/eval_logs/evallog_replay-er19-cv1-Project-_0e7de613.eval.log`。test rc=0，F2P 1/1，P2P fail=0/2，parsed=8，outside_segment=0，reference_missing/skipped均空。实际image ID `sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55`；scripts digest `sha256:1301d6363a7c104b8ad1e153fd4d1dbff2d070b30f8620ec6404a3bb99eda207`。资源原字段 `{"mem_peak_mb": 428.621, "mem_peak_unavailable_or_zero": false}`，不外推单位。
- noop：`runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/noop/ledger.jsonl:1`；日志 `runs/env_recipe_repair_20260919/compat_v1/tasks/Project-MONAI__MONAI-2446/noop/eval_logs/evallog_replay-er19-cv1-Project-_d1a9c1c5.eval.log`。test rc=1，F2P 0/1，P2P fail=0/2，parsed=8，outside_segment=0，reference_missing/skipped均空。实际image ID `sha256:c203df7326b9ed001876855ac1e24a6fa5e7d213d07fd395ee4261433f931a55`；scripts digest `sha256:1301d6363a7c104b8ad1e153fd4d1dbff2d070b30f8620ec6404a3bb99eda207`。资源原字段 `{"mem_peak_mb": 485.766, "mem_peak_unavailable_or_zero": false}`，不外推单位。

已核各选中ledger行和日志文件SHA与run_refs一致，gold候选原件逐字节等于本题gold.patch；projection frozen digest与原ledger吻合，baseline仅核授权/task_id，stage核/apply_method=git_apply。未浏览其它ledger行内容。历史tar仅检查授权4个源码成员的名字/size/mode，未读归档源码实现、未据此认证当前scorer。host grading view仅读本题选择行（2446为3，3715为10，5686为18）。

原命令 `pytest -rA tests/test_smartcachedataset.py`：noop日志611/617/637–670/755–763为命令、8项收集、外部列表顺序2,0,1,3,4对0,1,2,3,4失败以及7pass/1fail；gold645/651/740–748为8pass。不是导入失败。compat-v1 recipe明确先离线`--no-index --find-links=/opt/rh2/compat-wheels --no-deps nibabel==4.0.2`，再删requirements-dev中的MONAI git URL、装types-pkg-resources/pytest、pip requirements-dev、setup.py develop。读取gold after脚本和recipe、image.json/build.log；derived image只是保留base层并复制wheel，来源image ID与实际derived ID分开记录。修复后的历史成功不推断未修原镜像可用，也没有本轮重跑。

上述均历史RH2 grader条件：rh2grader UID54322、candidate apply身份agent/54321，policy cpus=2.0、memory_bytes=4294967296、network=deny_all、pids_limit=512，candidate_stage_seconds=900、grading_deadline_seconds=3600。install_rc_last_command=0仅代表最后安装命令；已抽读实际安装/测试段，未声称安装每一步均经fail-fast保障。cleanup记录removed=true、rm:ok；每种候选只引用一次运行，未证明重复稳定、并发/重置健全。来源grader status显示noop clean、gold只改目标源码，是历史评分阶段；不是actor初始工作树采集。测试恢复/patch apply日志RH2_SETUP_OK=1及目标文件匹配支持本次执行身份，但没有审计全部安全边界。

## ⑦实际阅读/未读声明

已读本题公开prompt/bundle/identity/environment brief和私有grading/test.patch/gold.patch/run_refs/environment_record；其JSON字段用stdlib解析。已按上文范围读base目标/调用者/测试与决定性helper；README、CONTRIBUTING、requirements、setup.cfg/setup.py/runtests只读或检索开发相关段落，并非通读全仓。私有validation/source_refs的2446内容已读；其它两题未单独读这两个冗余文件。日志读取为安装命令/身份/可信恢复/测试失败与结果段及检索，不声称逐行通读所有依赖输出。原件hash核对不是项目执行。

未读公开读者或主审输出、旧质量结论、跨包结果；未读整个base所有文件、实际actor消息/镜像和未定位资产；未检查当前控制面源码、网络泄漏路径及模型求解记录。没有本轮CPU/模型验证。八方面中⑦只有静态提交边界和暴露声明，不提供安全认证；⑧只有development_diagnostic建议。
