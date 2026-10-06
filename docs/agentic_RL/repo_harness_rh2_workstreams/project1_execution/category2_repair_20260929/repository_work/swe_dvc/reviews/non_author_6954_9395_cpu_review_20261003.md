# DVC6954／9395：非作者 CPU 原件读回复核

日期：2026-10-03。范围：6954 `dvc6954-behavior-v1-draft` 与 9395 `dvc9395-behavior-v2-draft` 的现有私有 CPU 诊断。

**结论：未发现新增阻止私有诊断和材料下一步的阻断项。** 6954 新版保留原 13 个参考的行为，并拒绝只支持负整数的候选；9395 当前 v2 的六候选矩阵与预期一致，只有 `c3_frozenfix` 全部 41 个执行节点通过。两题的作者便捷诊断文件与本次独立读回一致；6954 原始 summary 的已知空白 ID 提取遗漏不能用于判断未执行。

本结论仅支持私有诊断和材料的下一步，不授予正式 RH2 reward、actor 入口、环境／训练用途资格或模型探针通过。6954 新建单测文件未出现在 `git diff --binary` 原件中；其应用身份由输入 SHA、应用成功记录及真实 collection／执行日志支持，现存 diff 不能单独证明该文件的全部字节。此限制不能被静默改写为完整应用快照。

## 上下文与方法

核查者未继承作者会话，但阅读了私有材料、已有材料窄核和 v2 修正结论，因此不是 fresh 公开读者验收。6954 材料语义意见复用 `non_author_4166_6954_9395_review_20261003.md`（actual SHA256 `167e90e95475b0b9126d60f21a4e1f9016e54c9046cde57d29ee1d97868f7d9b`）；9395 同时复用 `non_author_4166_9395_v2_review_20261003.md`（actual SHA256 `c6adf3fe5dbf411b694813100b17b5b4db9ffd24e5bbe665259e86986afe0491`），本次只补运行读回及必要矛盾检查。没有重复审查 5839／4166，也未修改作者文件、原件、parser、登记或 pins。

先读取并逐字计算任务入口所列 22 份材料及 107 份原件的 SHA256 与大小，全部一致。入口 actual SHA256 为 `144583d2426f7f45824c2e3126a40a04a40fc28fd97d2f9db950273acf6fe954`。107 份原件含保留的 9395 旧 effective v1 文件；对这些旧文件只核完整性，不计入当前 v2 运行矩阵。之后从完整 `pytest.log` 的进度节点逐行重建状态，与 collection 的完整顺序、原始 summary 的输入及退出、`identity.json`、初始树、应用 diff、commands 的真实返回逐项核对；最后才比较作者 `cpu_diagnostics`，没有用它作为重建来源。

本次只运行纯标准库离线读取／SHA／日志重建，未运行 DVC、pytest、项目维护测试、SSH、Docker、安装或下载。18 行候选共读回 543 次节点执行（重复候选执行分别计数，不是 543 个不同测试），所有参考均唯一命中；skip、missing、ERROR、XFAIL、XPASS 均为 0。单独的 collect-only 原件只存在每种测试版本的 noop 行；其余候选以各自真实 pytest 的 collection 行和完整执行顺序核对，不冒称每候选另跑了 collect-only。

## 版本、基线和依赖身份

| 题目 | 当前 revision | commands 实测 HEAD | 进程读取的 DVC 版本 | pytest |
| --- | --- | --- | --- | --- |
| iterative__dvc-6954 | dvc6954-behavior-v1-draft | 28dd39a1a0d710585ff21bf66199208b1b83cbde | 2.8.4.dev20+g28dd39a1a | 6.2.5 |
| iterative__dvc-9395 | dvc9395-behavior-v2-draft | c75a5583b3840ba90a8e800a0f42c1cb120916db | 2.56.1.dev27+gc75a5583b | 7.4.4 |



所有 18 行的初始 `git status --porcelain && git diff --binary` 输出为空（返回 0），对应 `initial_tree.txt` 为零字节；HEAD 与表中基线一致。Python 3.9.19 的执行器为 `/opt/miniconda3/envs/testbed/bin/python`，DVC 导入自 `/testbed/dvc/__init__.py`，`pygit2==1.14.1` 在全部 identity 中直接确认。6954 identity 为 `pathspec==0.9.0`；9395 original identity 为 `pathspec==0.12.1`，当前 v2 identity 未重复输出 pathspec，v1/v2 使用同一个不可变镜像 ID，因此仅把这个版本列为同镜像既有证据，不称 v2 进程重新直接测得。

- `dvc6954-diagnostic-v1-001`：image inspect 的 Id 与每个 run 命令及 summary 相同，为 `sha256:083832998996245f4f49eaab3f5f9314fe9fe23bafda7fc9641ae8cec6803c30`；tag 为 `rh2-swe-dvc/iterative-dvc-6954:image-v1-003`。summary actual SHA256 `ee1fa42c14dc42ed43d6a2b57c9c8ad5df8b87d82db734ac69a4fecb4cc3b2d4`；commands actual SHA256 `b2cf754f567498786ed8f6c07eca7e3efeff6596e53f60e2794cfa81ecac6c75`。

- `dvc9395-diagnostic-v1-004`：image inspect 的 Id 与每个 run 命令及 summary 相同，为 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`；tag 为 `rh2-swe-dvc/iterative-dvc-9395:image-v2-001`。summary actual SHA256 `b6c89da67bc02b1d6c1d800aeb8ddea5e3934cca9a2626df846939f481ed5360`；commands actual SHA256 `fcdc9c28d523cd4752aaa431fd7eebd0d92406608ab44d0f5060e1f5f859b60e`。

- `dvc9395-diagnostic-v2-002`：image inspect 的 Id 与每个 run 命令及 summary 相同，为 `sha256:c093861f62b8071b3c1e5b3142abd5843888421364e69dd728cb80856f621b60`；tag 为 `rh2-swe-dvc/iterative-dvc-9395:image-v2-001`。summary actual SHA256 `6ededc1ef069ea23ef7ba8b04291a7e2771e35eefd828aa762bc4f6813c97b3c`；commands actual SHA256 `64a5a603f47a0cd9fac803bf1d657875368e24de6c8d9dc194cd1077b125e01c`。



当前原／有效测试补丁、候选和公开基线文件的实际 SHA 见末尾读回清单。9395 旧 original 六行复用所需的 original patch、六候选、两个基线测试文件及依赖镜像身份均与当前 v2 逐项相同；旧 revision／effective patch 的变化不影响这六行原版输入。旧 effective 六行误用 `Repo.odb` 的结果没有被当作当前 v2 结果。本次未独立复核镜像构建过程、完整安装配方执行、pip check 或新宿主部署；作者相应声明不升级为本报告的验证范围。

对 9395 的 12 份 original／v2 `applied.diff`，按文件逐条核添加／删除内容与当前候选＋对应测试补丁一致，无额外修改。6954 的候选源码改动及已有功能文件 diff 同样一致，但新建 `tests/unit/utils/serialize/test_python.py` 是未跟踪文件，六份 diff 都未收录它（original/noop 的 diff 因而为空）。日志显示每行对应 `git apply --check … && git apply …` 成功返回 0，真实 collection 和失败测试体与当前补丁对应；这支持实际运行，但不是新增文件的独立完整字节快照。没有为弥补该诊断快照限制要求全部历史重跑。

## 6954：原版与当前有效版分开核对

### 原版：13 个执行节点／13 个参考

| 候选 | 完整执行 | F2P（原失败应恢复） | P2P（原通过应保持） | 非参考 | pytest 真实退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 12通过／1失败 | 0通过／1失败 | 12通过／0失败 | 0通过／0失败 | 1 |
| gold | 13通过／0失败 | 1通过／0失败 | 12通过／0失败 | 0通过／0失败 | 0 |
| negative_int_only | 13通过／0失败 | 1通过／0失败 | 12通过／0失败 | 0通过／0失败 | 0 |



下表逐参考对应完整进度日志。`P@行号` = PASSED，`F@行号` = FAILED；行号属于本节候选各自的 `pytest.log`，不是作者摘要。

| 分区 | 参考原键 | 实际完整节点 | noop | gold | negative_int_only |
| --- | --- | --- | --- | --- | --- |
| F2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[UNARY_OP` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[UNARY_OP = -1-result9]` | F@17 | P@17 | P@17 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[DICT` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[DICT = {'a': 1, 'b': 2}-result4]` | P@12 | P@12 | P@12 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[SUM` | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[SUM = 1 + 2]` | P@20 | P@20 | P@20 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[SET` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[SET = {1, 2, 3}-result6]` | P@14 | P@14 | P@14 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[CONSTRUCTOR` | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[CONSTRUCTOR = dict(a=1, b=2)]` | P@19 | P@19 | P@19 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[STR` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[STR = 'abc'-result3]` | P@11 | P@11 | P@11 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[LIST` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[LIST = [1, 2, 3]-result5]` | P@13 | P@13 | P@13 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[BOOL` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[BOOL = True-result0]` | P@8 | P@8 | P@8 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[FLOAT` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[FLOAT = 0.001-result2]` | P@10 | P@10 | P@10 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[INT` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[INT = 5-result1]` | P@9 | P@9 | P@9 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[class` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[class TrainConfig:\n\n            EPOCHS = 70\n\n            def __init__(self):\n                self.layers = 5\n                self.layers = 9  # TrainConfig.layers param will be 9\n                bar = 3  # Will NOT be found since it's locally scoped\n            -result10]` | P@18 | P@18 | P@18 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[NONE` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[NONE = None-result8]` | P@16 | P@16 | P@16 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[TUPLE` | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[TUPLE = (10, 100)-result7]` | P@15 | P@15 | P@15 |



- `original/noop`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/original/noop/pytest.log)；运行返回见同批 commands 第 141 行。

- `original/gold`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/original/gold/pytest.log)；运行返回见同批 commands 第 280 行。

- `original/negative_int_only`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/original/negative_int_only/pytest.log)；运行返回见同批 commands 第 427 行。



### 当前有效版：26 个执行节点／15 个参考／11 个非参考

| 候选 | 完整执行 | F2P（原失败应恢复） | P2P（原通过应保持） | 非参考 | pytest 真实退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 23通过／3失败 | 0通过／3失败 | 12通过／0失败 | 11通过／0失败 | 1 |
| gold | 26通过／0失败 | 3通过／0失败 | 12通过／0失败 | 11通过／0失败 | 0 |
| negative_int_only | 24通过／2失败 | 1通过／2失败 | 12通过／0失败 | 11通过／0失败 | 1 |



下表逐参考对应完整进度日志。`P@行号` = PASSED，`F@行号` = FAILED；行号属于本节候选各自的 `pytest.log`，不是作者摘要。

| 分区 | 精确参考节点 | 节点绑定 | noop | gold | negative_int_only |
| --- | --- | --- | --- | --- | --- |
| F2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[negative_int]` | 精确同名 | F@29 | P@29 | P@29 |
| F2P | `tests/unit/utils/serialize/test_python.py::test_parse_negative_float_and_containers` | 精确同名 | F@33 | P@33 | F@33 |
| F2P | `tests/func/params/test_show.py::test_negative_python_params_lock_and_repro` | 精确同名 | F@19 | P@19 | F@19 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[dict]` | 精确同名 | P@24 | P@24 | P@24 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[sum]` | 精确同名 | P@32 | P@32 | P@32 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[set]` | 精确同名 | P@26 | P@26 | P@26 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_invalid_types[constructor]` | 精确同名 | P@31 | P@31 | P@31 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[str]` | 精确同名 | P@23 | P@23 | P@23 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[list]` | 精确同名 | P@25 | P@25 | P@25 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[bool]` | 精确同名 | P@20 | P@20 | P@20 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[float]` | 精确同名 | P@22 | P@22 | P@22 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[int]` | 精确同名 | P@21 | P@21 | P@21 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[class]` | 精确同名 | P@30 | P@30 | P@30 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[none]` | 精确同名 | P@28 | P@28 | P@28 |
| P2P | `tests/unit/utils/serialize/test_python.py::test_parse_valid_types[tuple]` | 精确同名 | P@27 | P@27 | P@27 |



11 个非参考旧功能实例在三候选均 PASSED：

```text

tests/func/params/test_show.py::test_show_empty
tests/func/params/test_show.py::test_show
tests/func/params/test_show.py::test_show_toml
tests/func/params/test_show.py::test_show_py
tests/func/params/test_show.py::test_show_multiple
tests/func/params/test_show.py::test_show_list
tests/func/params/test_show.py::test_show_branch
tests/func/params/test_show.py::test_pipeline_params
tests/func/params/test_show.py::test_show_no_repo
tests/func/params/test_show.py::test_log_errors[dvc.yaml-error_path0]
tests/func/params/test_show.py::test_log_errors[params_other.yaml-error_path1]

```

这些实例是执行分母的一部分，没有加进 15 个参考分母，也没有额外失败。

- `effective/noop`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/effective/noop/pytest.log)；运行返回见同批 commands 第 578 行。

- `effective/gold`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/effective/gold/pytest.log)；运行返回见同批 commands 第 1504 行。

- `effective/negative_int_only`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/effective/negative_int_only/pytest.log)；运行返回见同批 commands 第 2481 行。



原 13 个截断参考逐一唯一映射到实际完整 ID，包括带空格的数值／容器、constructor／sum 以及包含字面 `\n` 的 class ID。UNARY_OP 是原 noop 唯一失败（日志第 55–61 行，期望 `{"UNARY_OP": -1}` 而得到 `{}`）；gold 和整数专修均 13/13 通过。原始 summary 三行 `executed_node_statuses=[]` 是便捷提取器缺陷，不能说三个候选没执行。当前版 3 F2P／12 P2P 没有用截断匹配代替精确节点。

当前 noop 的功能测试在 `dvc.run` 读取 Python 参数时抛 `MissingParamsError`，缺少 `my_int/my_float/nested.v`（第 46、97 行）；整数专修只缺 `my_float/nested.v`（第 46、97 行），其 `[negative_int]` 已通过。两者的负浮点／容器测试均在 `parse_py(...) == {...}` 行返回空字典而失败（noop 第 157–167 行，整数专修第 115–125 行）。这是实际参数解析／run 行为失败，不是导入或 collection 错误。gold 的 26 节点全部通过，功能测试真实涵盖 run→lock 参数值→不变时跳过→修改负浮点后 repro／lock 更新；本报告不把它换算为正式 reward。

## 9395：仅复用未变 original，当前结果来自 v2-002

### 原版：30 个执行节点／29 个参考

| 候选 | 完整执行 | F2P | P2P | 非参考 import | pytest 真实退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 27通过／3失败 | 0通过／2失败 | 27通过／0失败 | FAILED | 1 |
| gold | 30通过／0失败 | 2通过／0失败 | 27通过／0失败 | PASSED | 0 |
| c3_frozenfix | 29通过／1失败 | 1通过／1失败 | 27通过／0失败 | PASSED | 1 |
| c3_missing_only | 29通过／1失败 | 1通过／1失败 | 27通过／0失败 | PASSED | 1 |
| up351_port | 29通过／1失败 | 1通过／1失败 | 27通过／0失败 | PASSED | 1 |
| w_swallow3 | 30通过／0失败 | 2通过／0失败 | 27通过／0失败 | PASSED | 0 |



参考节点均精确同名命中；P/F 与行号定义同上。表内保留所有原参考及新增参考，未只列失败题。

| 分区 | 精确参考节点 | noop | gold | c3_frozenfix | c3_missing_only | up351_port | w_swallow3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F2P | `tests/func/test_run_cache.py::test_restore_pull` | F@39 | P@39 | F@39 | F@39 | F@39 | P@39 |
| F2P | `tests/func/test_repro_multistage.py::test_repro_pulls_mising_data_source` | F@27 | P@27 | P@27 | P@27 | P@27 | P@27 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_out_overlaps_others_stage_outs` | P@17 | P@17 | P@17 | P@17 | P@17 | P@17 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[metrics_no_cache-True]` | P@34 | P@34 | P@34 | P@34 | P@34 | P@34 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_frozen` | P@11 | P@11 | P@11 | P@11 | P@11 | P@11 |
| P2P | `tests/func/test_run_cache.py::test_memory_for_multiple_runs_of_same_stage` | P@37 | P@37 | P@37 | P@37 | P@37 | P@37 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[True]` | P@23 | P@23 | P@23 | P@23 | P@23 | P@23 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[plots_no_cache-True]` | P@35 | P@35 | P@35 | P@35 | P@35 | P@35 |
| P2P | `tests/func/test_repro_multistage.py::test_downstream` | P@12 | P@12 | P@12 | P@12 | P@12 | P@12 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[True]` | P@25 | P@25 | P@25 | P@25 | P@25 | P@25 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_added_does_not_exist` | P@19 | P@19 | P@19 | P@19 | P@19 | P@19 |
| P2P | `tests/func/test_run_cache.py::test_save` | P@32 | P@32 | P@32 | P@32 | P@32 | P@32 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_moved` | P@16 | P@16 | P@16 | P@16 | P@16 | P@16 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[False]` | P@26 | P@26 | P@26 | P@26 | P@26 | P@26 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_lockfile_gets_deleted` | P@20 | P@20 | P@20 | P@20 | P@20 | P@20 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_added_does_not_exist` | P@18 | P@18 | P@18 | P@18 | P@18 | P@18 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_is_added_in_dvcfile` | P@15 | P@15 | P@15 | P@15 | P@15 | P@15 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[False]` | P@24 | P@24 | P@24 | P@24 | P@24 | P@24 |
| P2P | `tests/func/test_run_cache.py::test_restore` | P@31 | P@31 | P@31 | P@31 | P@31 | P@31 |
| P2P | `tests/func/test_run_cache.py::test_memory_runs_of_multiple_stages` | P@38 | P@38 | P@38 | P@38 | P@38 | P@38 |
| P2P | `tests/func/test_repro_multistage.py::test_non_existing_stage_name` | P@10 | P@10 | P@10 | P@10 | P@10 | P@10 |
| P2P | `tests/func/test_run_cache.py::test_do_not_save_on_no_exec_and_dry` | P@33 | P@33 | P@33 | P@33 | P@33 | P@33 |
| P2P | `tests/func/test_repro_multistage.py::test_cyclic_graph_error` | P@21 | P@21 | P@21 | P@21 | P@21 | P@21 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_cmd_changes` | P@13 | P@13 | P@13 | P@13 | P@13 | P@13 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_multiple_params` | P@22 | P@22 | P@22 | P@22 | P@22 | P@22 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[outs_no_cache-False]` | P@36 | P@36 | P@36 | P@36 | P@36 | P@36 |
| P2P | `tests/func/test_run_cache.py::test_push_pull` | P@30 | P@30 | P@30 | P@30 | P@30 | P@30 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_pulls_intermediate_out` | P@29 | P@29 | P@29 | P@29 | P@29 | P@29 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_added_in_dvcfile` | P@14 | P@14 | P@14 | P@14 | P@14 | P@14 |



唯一非参考节点是 `tests/func/test_repro_multistage.py::test_repro_pulls_mising_import`。原版 noop 在第 28 行 FAILED，当前 v2 noop 同样在第 28 行 FAILED；其他各候选两侧均在第 28 行 PASSED。它未计入 29／40 个参考，但失败已保留在完整执行和退出结论中，不能被漏报为全选测试通过。

- `original/noop`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/noop/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 153 行。

- `original/gold`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/gold/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 3796 行。

- `original/c3_frozenfix`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/c3_frozenfix/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 7012 行。

- `original/c3_missing_only`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/c3_missing_only/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 10196 行。

- `original/up351_port`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/up351_port/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 13382 行。

- `original/w_swallow3`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/original/w_swallow3/pytest.log)；运行返回见 `dvc9395-diagnostic-v1-004/commands.log` 第 16733 行。



### 当前 v2：41 个执行节点／40 个参考

| 候选 | 完整执行 | F2P | P2P | 非参考 import | pytest 真实退出 |
| --- | --- | --- | --- | --- | --- |
| noop | 37通过／4失败 | 0通过／3失败 | 37通过／0失败 | FAILED | 1 |
| gold | 30通过／11失败 | 2通过／1失败 | 27通过／10失败 | PASSED | 1 |
| c3_frozenfix | 41通过／0失败 | 3通过／0失败 | 37通过／0失败 | PASSED | 0 |
| c3_missing_only | 40通过／1失败 | 2通过／1失败 | 37通过／0失败 | PASSED | 1 |
| up351_port | 35通过／6失败 | 3通过／0失败 | 31通过／6失败 | PASSED | 1 |
| w_swallow3 | 30通过／11失败 | 2通过／1失败 | 27通过／10失败 | PASSED | 1 |



参考节点均精确同名命中；P/F 与行号定义同上。表内保留所有原参考及新增参考，未只列失败题。

| 分区 | 精确参考节点 | noop | gold | c3_frozenfix | c3_missing_only | up351_port | w_swallow3 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F2P | `tests/func/test_run_cache.py::test_restore_pull` | F@50 | P@50 | P@50 | P@50 | P@50 | P@50 |
| F2P | `tests/func/test_repro_multistage.py::test_repro_pulls_mising_data_source` | F@27 | F@27 | P@27 | P@27 | P@27 | F@27 |
| F2P | `tests/func/test_repro_multistage.py::test_pull_recovers_frozen_stage_for_downstream` | F@30 | P@30 | P@30 | F@30 | P@30 | P@30 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_out_overlaps_others_stage_outs` | P@17 | P@17 | P@17 | P@17 | P@17 | P@17 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[metrics_no_cache-True]` | P@45 | P@45 | P@45 | P@45 | P@45 | P@45 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_frozen` | P@11 | P@11 | P@11 | P@11 | P@11 | P@11 |
| P2P | `tests/func/test_run_cache.py::test_memory_for_multiple_runs_of_same_stage` | P@48 | P@48 | P@48 | P@48 | P@48 | P@48 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[True]` | P@23 | P@23 | P@23 | P@23 | P@23 | P@23 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[plots_no_cache-True]` | P@46 | P@46 | P@46 | P@46 | P@46 | P@46 |
| P2P | `tests/func/test_repro_multistage.py::test_downstream` | P@12 | P@12 | P@12 | P@12 | P@12 | P@12 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[True]` | P@25 | P@25 | P@25 | P@25 | P@25 | P@25 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_added_does_not_exist` | P@19 | P@19 | P@19 | P@19 | P@19 | P@19 |
| P2P | `tests/func/test_run_cache.py::test_save` | P@43 | P@43 | P@43 | P@43 | P@43 | P@43 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_moved` | P@16 | P@16 | P@16 | P@16 | P@16 | P@16 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_raise_and_stops_after_failure[False]` | P@26 | P@26 | P@26 | P@26 | P@26 | P@26 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_lockfile_gets_deleted` | P@20 | P@20 | P@20 | P@20 | P@20 | P@20 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_added_does_not_exist` | P@18 | P@18 | P@18 | P@18 | P@18 | P@18 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_outs_is_added_in_dvcfile` | P@15 | P@15 | P@15 | P@15 | P@15 | P@15 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_list_of_commands_in_order[False]` | P@24 | P@24 | P@24 | P@24 | P@24 | P@24 |
| P2P | `tests/func/test_run_cache.py::test_restore` | P@42 | P@42 | P@42 | P@42 | P@42 | P@42 |
| P2P | `tests/func/test_run_cache.py::test_memory_runs_of_multiple_stages` | P@49 | P@49 | P@49 | P@49 | P@49 | P@49 |
| P2P | `tests/func/test_repro_multistage.py::test_non_existing_stage_name` | P@10 | P@10 | P@10 | P@10 | P@10 | P@10 |
| P2P | `tests/func/test_run_cache.py::test_do_not_save_on_no_exec_and_dry` | P@44 | P@44 | P@44 | P@44 | P@44 | P@44 |
| P2P | `tests/func/test_repro_multistage.py::test_cyclic_graph_error` | P@21 | P@21 | P@21 | P@21 | P@21 | P@21 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_cmd_changes` | P@13 | P@13 | P@13 | P@13 | P@13 | P@13 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_multiple_params` | P@22 | P@22 | P@22 | P@22 | P@22 | P@22 |
| P2P | `tests/func/test_run_cache.py::test_outs_no_cache_deactivate_run_cache[outs_no_cache-False]` | P@47 | P@47 | P@47 | P@47 | P@47 | P@47 |
| P2P | `tests/func/test_run_cache.py::test_push_pull` | P@41 | P@41 | P@41 | P@41 | P@41 | P@41 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_pulls_intermediate_out` | P@29 | P@29 | P@29 | P@29 | P@29 | P@29 |
| P2P | `tests/func/test_repro_multistage.py::test_repro_when_new_deps_is_added_in_dvcfile` | P@14 | P@14 | P@14 | P@14 | P@14 | P@14 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_dry_preserves_workspace_and_cache[source]` | P@31 | F@31 | P@31 | P@31 | F@31 | F@31 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_dry_preserves_workspace_and_cache[output]` | P@32 | F@32 | P@32 | P@32 | F@32 | F@32 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_when_nothing_missing[normal]` | P@33 | F@33 | P@33 | P@33 | F@33 | F@33 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_when_nothing_missing[dry]` | P@34 | F@34 | P@34 | P@34 | F@34 | F@34 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_preserves_modified_source` | P@35 | F@35 | P@35 | P@35 | F@35 | F@35 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_without_remote_still_errors_for_missing_source` | P@36 | F@36 | P@36 | P@36 | F@36 | F@36 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_no_run_cache_does_not_download_runs` | P@37 | F@37 | P@37 | P@37 | P@37 | F@37 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_existing_output_without_hash_can_run` | P@38 | F@38 | P@38 | P@38 | P@38 | F@38 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_changed_dependency_can_recompute` | P@39 | F@39 | P@39 | P@39 | P@39 | F@39 |
| P2P | `tests/func/test_repro_multistage.py::test_pull_restores_from_http_with_local_run_cache` | P@40 | F@40 | P@40 | P@40 | P@40 | F@40 |



唯一非参考节点是 `tests/func/test_repro_multistage.py::test_repro_pulls_mising_import`。原版 noop 在第 28 行 FAILED，当前 v2 noop 同样在第 28 行 FAILED；其他各候选两侧均在第 28 行 PASSED。它未计入 29／40 个参考，但失败已保留在完整执行和退出结论中，不能被漏报为全选测试通过。

- `effective/noop`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/noop/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 167 行。

- `effective/gold`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/gold/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 5674 行。

- `effective/c3_frozenfix`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/c3_frozenfix/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 12015 行。

- `effective/c3_missing_only`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/c3_missing_only/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 17200 行。

- `effective/up351_port`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/up351_port/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 22573 行。

- `effective/w_swallow3`：[完整 pytest.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/effective/w_swallow3/pytest.log)；运行返回见 `dvc9395-diagnostic-v2-002/commands.log` 第 28681 行。



### 失败落点与行为含义

原版 noop 的 source／import 在已有 repro 调用中因 `MissingDataSource(foo)` 传播为 `ReproductionError`；restore 在缺失 bar 的 checkout／repro 路径失败。原版 `c3_frozenfix`、`c3_missing_only`、`up351_port` 都只有 restore 的 checkout 次数断言失败：真实 2 次、原断言要求 3 次（各日志第 74–76 行），不能描述成数据恢复本身失败。原 gold 和 `w_swallow3` 全部 30 节点通过；这仅是旧断言下的私有结果。

当前 v2 所有失败均进入已收集的实际测试体／DVC 行为路径，没有 `Repo.odb` 的 API 访问错误、fixture setup、导入或 collection 错误。异常抛出也按对应测试的预期行为判断，不把异常名称直接当成错解已被有效拒绝。逐项解释如下：

| 候选 | 失败节点／行为 | 最少日志定位 |
| --- | --- | --- |
| noop | source 与非参考 import 缺 foo；新增 frozen 输出 raw 无法恢复供下游；restore 缺 bar。3 个 F2P 全失败，另有 import 额外失败。 | effective/noop：MissingDataSource foo 第161／514行；raw 第891行；bar 第1252行 |
| gold | 强化 source 在用户修改后 repro 返回 []，断言需要重算；dry/source 下载了 runs 改写快照，dry/output 试图下载缺对象；无 remote 的四节点抛 NoRemoteError；run_cache=False 仍下载 runs；新无hash产物及依赖变化的重算路径尝试 checkout、触发 ConfirmRemoveError；HTTP 非必要下载 runs，抛 RunCacheNotSupported。 | effective/gold：第80–85、347、759／893、1174／1345／1514／1686、1758、2086／2501、2803行 |
| c3_missing_only | 唯一区分失败是 frozen stage 缺 raw（workspace 和对象 cache 已删），不能恢复给下游。其他40节点通过。 | effective/c3_missing_only：第164／304行 |
| up351_port | 6个 P2P：dry/source 写入 runs；dry/output DownloadError；无remote normal／dry／modified／required-missing 四节点直接 NoRemoteError，最后一项没有满足测试所需 ReproductionError。3个 F2P和其余31个P2P通过。 | effective/up351_port：第73–81、499／629、916／1091／1264／1440行 |
| w_swallow3 | source repro 声称执行后 foo 仍不存在；两个dry快照均写入runs；4个无remote节点NoRemoteError；run_cache=False仍写runs；无hash产物仍manual而非foo；依赖重算仍before而非after；HTTP抛RunCacheNotSupported。 | effective/w_swallow3：第73／92、253／501、802／971／1138／1309、1380、1553–1556、1683–1686、1854行 |



`c3_frozenfix` 的 3 F2P、37 P2P 及非参考 import 全部 PASSED，pytest 返回 0。当前 CPU 结果支持此前材料所述公开目标／新增断言的区分；本次没有发现需要另增材料 finding 的运行偏差。`up351_port` 等在 required-missing 节点抛错的失败是异常传播边界不符合现有断言，报告保留精确原因，不夸大为无错误返回。

## 退出、清理与残留

每个 pytest 的真实 RC 均从原 commands 中直接读回，与日志终态、原 summary 一致：有失败则 1，全通过则 0。下面 confirmed_absent 是从删除后的精确容器名 `docker ps -aq` 空输出／RC=0 重建的结论，不是把 summary 的 `container_remaining=false` 改名。所有 `docker rm -f` RC=0；没有残留被忽略。

| 批次／版本／候选 | pytest RC（commands行） | 清理 RC（commands行） | 精确名确认 absent（commands行） |
| --- | --- | --- | --- |
| dvc6954-diagnostic-v1-001/original/noop | 1（141） | 0（233） | true；空输出，RC0（237） |
| dvc6954-diagnostic-v1-001/original/gold | 0（280） | 0（380） | true；空输出，RC0（384） |
| dvc6954-diagnostic-v1-001/original/negative_int_only | 0（427） | 0（494） | true；空输出，RC0（498） |
| dvc6954-diagnostic-v1-001/effective/noop | 1（578） | 0（1452） | true；空输出，RC0（1456） |
| dvc6954-diagnostic-v1-001/effective/gold | 0（1504） | 0（2429） | true；空输出，RC0（2433） |
| dvc6954-diagnostic-v1-001/effective/negative_int_only | 1（2481） | 0（3330） | true；空输出，RC0（3334） |
| dvc9395-diagnostic-v1-004/original/noop | 1（153） | 0（3749） | true；空输出，RC0（3753） |
| dvc9395-diagnostic-v1-004/original/gold | 0（3796） | 0（6965） | true；空输出，RC0（6969） |
| dvc9395-diagnostic-v1-004/original/c3_frozenfix | 1（7012） | 0（10149） | true；空输出，RC0（10153） |
| dvc9395-diagnostic-v1-004/original/c3_missing_only | 1（10196） | 0（13335） | true；空输出，RC0（13339） |
| dvc9395-diagnostic-v1-004/original/up351_port | 1（13382） | 0（16686） | true；空输出，RC0（16690） |
| dvc9395-diagnostic-v1-004/original/w_swallow3 | 0（16733） | 0（19768） | true；空输出，RC0（19772） |
| dvc9395-diagnostic-v2-002/effective/noop | 1（167） | 0（5624） | true；空输出，RC0（5628） |
| dvc9395-diagnostic-v2-002/effective/gold | 1（5674） | 0（11965） | true；空输出，RC0（11969） |
| dvc9395-diagnostic-v2-002/effective/c3_frozenfix | 0（12015） | 0（17150） | true；空输出，RC0（17154） |
| dvc9395-diagnostic-v2-002/effective/c3_missing_only | 1（17200） | 0（22523） | true；空输出，RC0（22527） |
| dvc9395-diagnostic-v2-002/effective/up351_port | 1（22573） | 0（28631） | true；空输出，RC0（28635） |
| dvc9395-diagnostic-v2-002/effective/w_swallow3 | 1（28681） | 0（33945） | true；空输出，RC0（33949） |



- `dvc6954-diagnostic-v1-001` 的批次 label 查询第 3337 行返回 0、输出为空，与 summary `remaining_containers=[]` 相符。

- `dvc9395-diagnostic-v1-004` 的批次 label 查询第 51934 行返回 0、输出为空，与 summary `remaining_containers=[]` 相符。

- `dvc9395-diagnostic-v2-002` 的批次 label 查询第 33952 行返回 0、输出为空，与 summary `remaining_containers=[]` 相符。



9395 v1 的 shared commands 还记录了旧 effective 容器的清理，但这些行没有计入当前六候选语义验收。上述确认只覆盖各诊断结束时这些精确容器名／batch label 的容器残留，不是此刻宿主普查，也没有证明进程、卷、镜像和全部临时路径的全局清理。

## 下一步及未验证边界

本次结论是现有私有 CPU 原件的非作者读回，材料意见按对应版本复用。尚未验证正式安装／新宿主身份、共用正式版本发布、正式评分的逐键传输和 parser／reference binding、6954 新文件的正式恢复／保护、actor 入口及训练消费、环境／训练用途资格和模型探针。原版／有效版候选私有 pytest 通过关系不是正式 RH2 reward。当前 revision 中 `not_run/null`、`collection_verified=false` 等草案字段不能被本报告直接改写成正式已验证；正式流程如何发布仍按既有授权执行，本报告没有新增审批闸门。

## 实际读回 SHA256 清单

下列每个 SHA 均由本次直接读取字节计算，不是复制作者摘要。路径相对题目材料根或对应 CPU 原件根；完整路径由任务入口固定（入口 SHA 见上），与入口逐项核对结果均一致。零字节 initial_tree 和 noop 候选的 SHA 为 `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`。

### iterative__dvc-6954：当前材料

| 材料路径（相对题目根） | actual SHA256 | 字节 |
| --- | --- | --- |
| revision.json | `1d6a11a8b8adfcdd4122dcd7a64aecbb6a93c8c51284b2f927157eeea42ee801` | 7797 |
| original_test.patch | `e57dff1329d7ca7842d3d3d639ec1a03d401065f4286ef893af93552196087fa` | 1465 |
| effective_test.patch | `52c6a71bba1b1ca9f067d9846006dc5f2af9ecb0dde107f8a4ee75519c0b33fc` | 3162 |
| effective_install_recipe.json | `86bf3ff0cc0b2d90922cf031ba93b84f30dafa38b39e00ad678956bb286b47d4` | 1500 |
| cpu_diagnostics_v1.json | `999eed776235c306ea78e5d9ed5a5aff236c677d691a75c3e18d7685d4a7d7ef` | 19437 |
| public_tests/tests/func/params/test_show.py | `b4f326a46584b7a6e4eae8462ff5018341dee1bbaf2eaef4c5dca37bbf4436eb` | 4907 |
| candidates/noop.patch | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| candidates/gold.patch | `50ed349f0cad3875991e03a9a4c9a01c0ff286cc18a00f1c221f121bcddb8116` | 2043 |
| candidates/negative_int_only.patch | `4787d6e313bb413600e1f455a123c359339d101e46d4ef4e079516e6a0c2a2f8` | 568 |



### dvc6954-diagnostic-v1-001：原件

[原始 summary.json](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/summary.json)；[完整 commands.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc6954-diagnostic-v1-001/commands.log)。

| 原件路径（相对本批根） | actual SHA256 | 字节 |
| --- | --- | --- |
| commands.log | `b2cf754f567498786ed8f6c07eca7e3efeff6596e53f60e2794cfa81ecac6c75` | 211282 |
| effective/gold/applied.diff | `9da3a3a1c8b93ad9fdfc9598eb7e09c4e976d69e3df1053b96db294943019486` | 3460 |
| effective/gold/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| effective/gold/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/gold/pytest.log | `115d2ef5f0816112528c3ccdfc481bfd801dd44410f9a86aad508561ba676656` | 54952 |
| effective/negative_int_only/applied.diff | `c4f2bca5c745516f03dd0266b22eb7a88b305991e7dea660a249d79347712f56` | 2012 |
| effective/negative_int_only/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| effective/negative_int_only/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/negative_int_only/pytest.log | `6d0ab74f82ad94cffa830695ee080aa23070b2f07e3b8e42940d18f7127bcc9f` | 48012 |
| effective/noop/applied.diff | `27eb5428a097d7420c5ae31d388f1b35294d809ca846b5ddc5f18010f17366d3` | 1383 |
| effective/noop/collection.log | `b77302eed6ba5b11ea0bf7671528649fcf749475b43b9e0aa70924835c656847` | 2257 |
| effective/noop/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| effective/noop/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/noop/pytest.log | `0aa67254a9a64ff2db9c7a43b2df1853c03b31299a43965a90a3d14d1ce9d58b` | 49595 |
| original/gold/applied.diff | `44314e4df30d1904a843a19d630a00d81facc94fbaf8e4f7795c168f0b4b8164` | 2077 |
| original/gold/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| original/gold/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/gold/pytest.log | `b2e852dbbce7b0b1162e3d517b300f69e35c56ff04229e7b007e101a709a495f` | 4316 |
| original/negative_int_only/applied.diff | `984a0bdcc76c9708f80f141c501c5b8dafe15b79b447820d6658b99d8f99d1a6` | 629 |
| original/negative_int_only/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| original/negative_int_only/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/negative_int_only/pytest.log | `bdc20cf45d7e5c7508c91963b9d9cd38efccfac2b0af60925860c819a4c4d8f1` | 4316 |
| original/noop/applied.diff | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/noop/collection.log | `e902b26561a9ecc8d02604e897df1f1fa9df6125a3651b23f376bf7b6bfab467` | 1986 |
| original/noop/identity.json | `eccd27ebbc4c558cdf1c3fdd2f07ccdb44802f45a02348e79cdb9a677a687dbb` | 196 |
| original/noop/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/noop/pytest.log | `c7cdc2e7729f74bcf68fbf2f28522d51e25595ca21ffac13f853bde29eff132f` | 5862 |
| summary.json | `ee1fa42c14dc42ed43d6a2b57c9c8ad5df8b87d82db734ac69a4fecb4cc3b2d4` | 12035 |



### iterative__dvc-9395：当前材料

| 材料路径（相对题目根） | actual SHA256 | 字节 |
| --- | --- | --- |
| revision.json | `fd3cc7ea289803967e41d074fca566418770c88a683589b771eaca60f973981c` | 10847 |
| original_test.patch | `1252952ed15b193e40ef7a61af5122e932a4ef97abac6ec33f48e3cc63909c71` | 2983 |
| effective_test.patch | `964c80ef786b71091fcc722d8b3fdcd8afe8ba7e3f5fb511d6cb9661a25c2777` | 10739 |
| effective_install_recipe.json | `aedc7795f25b87578d1e2e4945fe0d23318d9d16d1188f4eb28de66547757daa` | 1729 |
| cpu_diagnostics_v2.json | `92c6731166ecaf344dbcd6c5381fa06c75489401c7259246e802d19dbd456a6b` | 11492 |
| public_tests/tests/func/test_repro_multistage.py | `ca738a7a94b991881a48abdb02aa1d27565f087e5742511d1fbbd752afde99e1` | 11832 |
| public_tests/tests/func/test_run_cache.py | `0d9bfa7a96c4e29e178c89b96357ec1adae59bfa27027173f07b234b08504960` | 5953 |
| candidates/noop.patch | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| candidates/gold.patch | `4a5017f1dfa6375041fd1a4ce055a5bcc1a7bedc221ccada2cc0732044667d4a` | 974 |
| candidates/c3_frozenfix.patch | `94d448480d67d7e74bc97e90266b69d99a1f58e499992dab45161491b4412040` | 1637 |
| candidates/c3_missing_only.patch | `ac0a90ac6ec289ea632582201224dfd17526b0fa1df636d0772c867d352566c6` | 1620 |
| candidates/up351_port.patch | `ca53ee797f31c61d3412e297e2aad73e0afc2d5dabb3d53bc4fab5b1f1c321c2` | 4270 |
| candidates/w_swallow3.patch | `dcc198d267a8f79072a219e6eea3921d8ce8a49083477f531c4313d411ccce2a` | 1113 |



### dvc9395-diagnostic-v1-004：原件

[原始 summary.json](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/summary.json)；[完整 commands.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v1-004/commands.log)。旧 effective 文件只核完整性，不作为当前 v2 结果。

| 原件路径（相对本批根） | actual SHA256 | 字节 |
| --- | --- | --- |
| commands.log | `fcdc9c28d523cd4752aaa431fd7eebd0d92406608ab44d0f5060e1f5f859b60e` | 2615640 |
| effective/c3_frozenfix/applied.diff | `e72e55d47378267502f4bb845d1368b39ad8ec6411dd66d285ee2ad689f900ce` | 12724 |
| effective/c3_frozenfix/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/c3_frozenfix/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/c3_frozenfix/pytest.log | `e275d9ee5dc5c1e1e162f0ab78bc9340b07f959190013af33617a9a85eb4e51e` | 243511 |
| effective/c3_missing_only/applied.diff | `24071531cfba4de76a0645462de6a7431011b7568133fa4264c4e883b2a9bf49` | 12703 |
| effective/c3_missing_only/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/c3_missing_only/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/c3_missing_only/pytest.log | `bbb3db1c64f4dac98e8a3ac70e487befe4bc94593758058bee1308b2c8ba5de6` | 251290 |
| effective/gold/applied.diff | `d5f0473ba7305666ceef569109d28b0fda63d322db7fa4934578dd0703714573` | 12091 |
| effective/gold/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/gold/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/gold/pytest.log | `548eb2dbe2195a78447eadac9354cf2378a9ea310cdb64e3b056c03465565255` | 255002 |
| effective/noop/applied.diff | `f16f146fd24266cd17a59fc54f0fab9a31d81029537e2dc2266e66d5c21f26af` | 11083 |
| effective/noop/collection.log | `3224e9460ac26e172b5ec218a2996921530b9c63b641a54091402e02a49cdbe6` | 3438 |
| effective/noop/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/noop/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/noop/pytest.log | `1d21f5db9f1defcb2842795fb664af7cd4ba552eabdcf02ee179bc66eb92ffb1` | 255321 |
| effective/up351_port/applied.diff | `36c7e4962c55f8e74087f281a0fb9b6a31a17cb4a23c14dd55f91b3558b2a26c` | 15361 |
| effective/up351_port/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/up351_port/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/up351_port/pytest.log | `0bd08816238f2d80ae95f1ef58ee6b8a594caaf52e84270596febcc38ede1405` | 256935 |
| effective/w_swallow3/applied.diff | `dfdddc8c1fda0982bdbf418a10760887f42ccab130848d117f95c8e69f760bfa` | 12200 |
| effective/w_swallow3/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| effective/w_swallow3/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/w_swallow3/pytest.log | `8d6c0db9ad1397f2960dba64f35889c351e27992b800f2f04a8d78965d3b5a0d` | 235203 |
| original/c3_frozenfix/applied.diff | `1dc0a8d79b5e3de1351a5a71f78ce8e6efa3987bf2968872d149b289b8ce3211` | 4740 |
| original/c3_frozenfix/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/c3_frozenfix/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/c3_frozenfix/pytest.log | `bf5f1a7dbe1634d78b7011a4d844d523e84172f04b4388c45ffb39502107adda` | 152869 |
| original/c3_missing_only/applied.diff | `7edb626e821ed1c948686460a5d6d325b0bd9e53665f38d2f39ec04b1a96be21` | 4719 |
| original/c3_missing_only/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/c3_missing_only/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/c3_missing_only/pytest.log | `33225896c3e3afac63f4e444ea61782382661060a7ddf75fceb4bd6607d78507` | 152916 |
| original/gold/applied.diff | `d1988da13847ea05dcd1279fd3e9a08737dc27dec010b70eca93d4f0dd19bb33` | 4107 |
| original/gold/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/gold/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/gold/pytest.log | `f486997f7a61f270b4ede1fbb5f7ab2df46ca89206085f0ea0470805c5529eff` | 158356 |
| original/noop/applied.diff | `0220f7b3598815176c3a6c7b231d998a78385978355daf50dcd939b71fca90d6` | 3099 |
| original/noop/collection.log | `4e8a3c55aec2c409c7eab18da91d73b62993bf37f0543d7f8fd99d7aa88f172d` | 2481 |
| original/noop/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/noop/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/noop/pytest.log | `4cd925507d3612472335f546615f19515359f8ca92bd68a7934345e6dcddb867` | 173653 |
| original/up351_port/applied.diff | `9b3f5be3d9c0c53b45ba829be7cfa4225c75a3f838b151d501b9766df576bf5f` | 7377 |
| original/up351_port/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/up351_port/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/up351_port/pytest.log | `59f556e93fbb828c7ec8d00a09a7cc733216d028a1365a040e074bdf897fd744` | 160905 |
| original/w_swallow3/applied.diff | `9d1a209b04e8ac0ad113ab168cc8b62c53c64a1e03058602a43d030374a8bff4` | 4216 |
| original/w_swallow3/identity.json | `0716e0ff75906e7691ab6f392991a84fc1cab6d6556d24c5b6c80f4d8fd631d1` | 198 |
| original/w_swallow3/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| original/w_swallow3/pytest.log | `b8c2342faae420d5c2fe31768539a8c9f56f0956d45cd9c9db19b59bb2d1cfbc` | 153373 |
| summary.json | `b6c89da67bc02b1d6c1d800aeb8ddea5e3934cca9a2626df846939f481ed5360` | 51975 |



### dvc9395-diagnostic-v2-002：原件

[原始 summary.json](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/summary.json)；[完整 commands.log](../../../../../../../../runs/category2_repair_20260929/repository_work/swe_dvc/cpu_evidence/dvc9395-diagnostic-v2-002/commands.log)。

| 原件路径（相对本批根） | actual SHA256 | 字节 |
| --- | --- | --- |
| commands.log | `64a5a603f47a0cd9fac803bf1d657875368e24de6c8d9dc194cd1077b125e01c` | 1702343 |
| effective/c3_frozenfix/applied.diff | `fb7ddc6b2cc3ecf812603ce1ccb6e1a83e580a80025a599fc3702cc268b0ac7d` | 12715 |
| effective/c3_frozenfix/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/c3_frozenfix/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/c3_frozenfix/pytest.log | `be582589beee6dc0043e2cdd188068dc44e32f954426ae5619828aeeae7a9f17` | 244540 |
| effective/c3_missing_only/applied.diff | `f54a365e32a3b9e6cd780344b01e72a5d680fa3d8f659fd4abb0ac447317a07d` | 12694 |
| effective/c3_missing_only/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/c3_missing_only/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/c3_missing_only/pytest.log | `c6bf62a4746849d64bf4a3a40c533b43ec4d235d4c5e2bc7022b0b8a965074c8` | 252281 |
| effective/gold/applied.diff | `abe7bfcee24397853e3c048f10ff35b413909900570c32f69d727596e0b32225` | 12082 |
| effective/gold/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/gold/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/gold/pytest.log | `e0302bdfa63d5d2acec33364399dc71dcb8f93fde42aae26019a2522f076d654` | 298215 |
| effective/noop/applied.diff | `9fc58b5b7acc7e4453929be077b3f39c02640e70e7858729ac274f8eaca3b5ce` | 11074 |
| effective/noop/collection.log | `c9a47d2312dc79823143b3c5302f4b9d16d1d8e6f8293ba61aa13f488e6ccddc` | 3438 |
| effective/noop/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/noop/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/noop/pytest.log | `0bb9a1edf962412e9598d3d71be0b3af2f1e3f99b524fe9d4f9f5cd43060d77b` | 255594 |
| effective/up351_port/applied.diff | `6486d74ee8d27048d73147199fbe261300bf3cc25a0972a525aaa1730de0abbd` | 15352 |
| effective/up351_port/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/up351_port/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/up351_port/pytest.log | `d9e2d083ac9e8a0eaa9ef67f4176fdab603a22815f952ac27791d38dffaa7ab5` | 284990 |
| effective/w_swallow3/applied.diff | `a79b17e3dea99e1870db2ed7b5576048f15ce9dd1a69c59a573343c3bcdbb79f` | 12191 |
| effective/w_swallow3/identity.json | `362d3a655697df0908da7a5af2e65faa63ee2691bba52cd755627c392ea4d95e` | 176 |
| effective/w_swallow3/initial_tree.txt | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | 0 |
| effective/w_swallow3/pytest.log | `0ab942e9a545be3594fc15805390f0884f5d839efc2675e7b1ec665584ebc04d` | 255910 |
| summary.json | `6ededc1ef069ea23ef7ba8b04291a7e2771e35eefd828aa762bc4f6813c97b3c` | 30435 |


