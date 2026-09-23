# iterative__dvc-4185 — B4 独立初判（封存稿）

审查日期：2026-09-21。角色：fresh 独立 reviewer；本稿先于主审、public_read 和本题历史调查的读取。权威根目录为 `.`。

**初判：`needs_review / static_review`，用途仅 `development_diagnostic`。** 假值丢失的根因、gold 的局部修复与 7 个 F2P 一致；但公开题面还有“未变更的 get_base_dv 被 commit 提示依赖变化”这一独立要求。源码显示 gold 没有改到该路径，现有评分也没有覆盖它。优先验证这一具体缺口，再决定探针范围，不能把历史 gold 满分解释为完整修复题面。

## 阅读边界与证据级别

- 原件范围：本题 `public/iterative__dvc-4185` 的题面、bundle、identity、环境说明和下述 base 文件；本题 private 的完整 `test.patch`、`gold.patch`、`grading.json`、`validation.json`、`environment_record.json`。
- 共用方法只读指定 protocol、reviewer、record_template、actor_environment_card；额外使用 verification-before-completion 技能核验本稿保存和散列，不运行项目代码。
- 环境定位只读 B4 `environment_replay_inventory.json` 的 common 与 `tasks[iterative__dvc-4185]`，再读对应 dvc_install_v1c 脚本、recipe、shared bindings 中本题条目、两份 ledger 第 1 行和原始日志。只以 `tarfile.extractfile` 读取 `frozen_sources/dvc.tar.gz` 的 replay CLI、replay adapter、prepared_task_face 相关入口；未解包或执行。
- **不是 result blind**：environment_record 自带已见 gold/noop 结果和旧环境路径，随后复读了本题原日志；未读取其指向的聚合分析、source_refs/run_refs、主审稿、公开读稿、历史调查或其他题。未进行项目 import、pytest、安装、网络、容器或模型实验。
- 本文 `P` = `runs/swegym_quality_batch04_20260921_v1/public/iterative__dvc-4185/base/`；`G` = `runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-4185/`；源码行号均指 P 下精确 base。

## 八方面独立判断

### 1. 公开需求与可推导范围

`user_prompt.txt` 末尾明确列两项问题：commit 的假变更提示；status 把未变的 `eval.filter_limitup: false` 报成 new。嵌套参数键、同一 params.yaml 被多个阶段分别选用、commit/repro 后仍误报，均是题面给出的行为。源码能解释参数值与键存在性应分开判断，无须从隐藏测试倒推“False 也是已记录值”。题面未规定改哪个函数、算法或异常字符串。报告中的 WSL/9p、ipython 和业务数据不是复现参数状态语义的必要条件。

`public_hints` 含 bash/edit、禁止改测试、conda 已激活等说明；环境声明只是静态输入，真实 solver 的最终 rendered messages 未捕获，因此原检查 3 为 unknown，不能用题面可读代替。原检查 23 单独记录题意的双目标，不合并到检查 3。

### 2. 材料与初态

public/private 的 base 均为 `0899b277c02082ffc24bb732e8a7cf3ef4333948`；本次只做文本/散列核对，确认 test.patch 与 grading 内嵌补丁一致、gold.patch 与 validation 一致，7 F2P / 22 P2P。base_identity 报告 422 个 blob 已核验、无 gitlink/LFS 缺项、无 `.git`；未独立重算全部 base blob。

`dvc/dependency/param.py:43–50` 对 `values.get(param)` 作 truthiness 判断，确实跳过已有 False/None/空容器。`status:63–69` 随后将缺少 self.info 的键视为 new。`stage/loader.py:25–44,73` 从 lock 的扁平点号键映射调用 fill_values；`stage/cache.py:154` 的 restore 也调用同一加载器，能解释 repro/run-cache 后再次误报。历史 noop 在真正断言处返回 `{'params.yaml': {'param': 'new'}}`，不只是收集或解析失败。

### 3. 需求—测试双向映射

| 公开要求 / 合理回归 | 依据 | 测试及关键断言 | 判断 |
| --- | --- | --- | --- |
| 未变假值参数不应报 new | 题面 false；param.py fill_values/status | 全部 F2P：`tests/unit/dependency/test_params.py::test_params_with_false_values`，参数后缀依次 `[]`（空测试输入）、`[false]`、`[[]]`、`[{}]`、`[null]`、`[no]`、`[off]`；写 YAML，load_yaml→fill_values，在 `dvc.state` 内断言 status == {} | 直接覆盖 7 个样例；只有 False、None、空列表、空字典四类值。空输入生成 `param: `，是 null，并非引号包裹的空字符串；0/0.0/真正空字符串未直接覆盖。 |
| 原例的嵌套 false、锁文件重载后仍干净、repro 后干净 | 题面；loader/cache 调用链 | F2P 用顶层 `param`、直接 fill_values，未经过阶段重载或 repro。旧 `test_read_params_nested` 是 P2P，但值为非空列表 | 部分；gold 沿共用调用链可解释修复，缺原例端到端断言。 |
| get_base_dv 的未变参数不应让 commit 询问依赖变更 | 题面第 1 项；repo/commit.py:42–45 | 7 F2P 和 22 P2P 均无参数 commit 断言；两个实际执行模块也没有此场景 | 缺失；gold 很可能仍违反，见下节。 |
| 真正新增、修改、删除参数仍需报告，缺失配置/键不能被当作正确值 | param.py:65–70、105–116 | P2P `test_save_info_missing_config`、`test_save_info_missing_param` 只核 save_info 异常；无 status 的 modified/deleted 对照 | 部分。无条件返回空 status 的错误实现会满足所有新增断言；按已读参考测试静态推断也不触及 22 个 P2P 的断言，尚未运行该候选。 |
| 参数加载、序列化、类型、非法输入保留 | 同模块公开旧测试 | 其余相关 P2P 是 loads_params、params_error[params0/1]、loadd_from、dumpd_with/without_info、read_params_nonexistent_file/unsupported_format/nested；另 9 个非法阶段名与 2 个无 cmd 样例 | 覆盖这些原行为；后二类不保护参数状态。 |
| 默认文件、嵌套键的 stage/lock 格式 | test_run_multistage.py:234–258 | test.patch 补上 `assert isinstance(..., ParamsDependency)`；实际运行 `test_run_params_default`，但它不在 F2P/P2P 参考集合 | 是新增有效断言，不能当计分 P2P。custom_file/no_exec 同样执行但未列参考。 |

读完 test.patch 的所有改动；完整读参数单测及全部参考 P2P 的函数/参数定义，追读 `tmp_dir/dvc/run_copy` helper、tests/conftest、remotes 导入、load_yaml；抽查 multistage 的参数与 cache 相关测试。另读公开 `test_repro_multiple_params`：会检查修改 answer 后再执行，但其文件不在此次实际 pytest 命令内，不能算评分回归保护。

### 4. 合法替代解与误拒

合法路线不限 gold 的 `if param in values`：例如对每个声明参数使用 `try: value = values[param]` / `except KeyError: continue`，再无条件保存 value，同样保留缺键不填、只取声明键、已有真值和所有假值。新增测试不检查赋值顺序、Mock 调用或 gold 特有表达式，未发现具体错误拒绝证据。直接调用 fill_values 是已有 loader 的接口契约；不过本判断不证明任意重构路线都被接受，检查 24 不能泛化为“所有合法解 pass”。

### 5. gold 完整性与回归：主要保留项

gold 仅将 param.py:48–50 的真值判断改成键存在判断。非空 lock 映射中嵌套键已被序列化成 `eval.filter_limitup`，故无需另加嵌套查找；保留 `if not values: return` 对空映射也合理。没有看到该局部改动引入具体回归，但状态转换与端到端重载覆盖有限。

**公开第 1 项有独立、未修的静态证据链：** `repo/commit.py:42–45` → `Stage.changed_entries` → `_changed_entries:398–399` 调 `entry.changed_checksum()`；ParamsDependency 没有覆盖它，继承 `output/base.py:194–195` 的 `self.checksum != self.get_checksum()`。`checksum:172–174` 取 `self.info['md5']`，而参数 info 是 benchmark/start/end/universe 等键的值，`LocalRemoteTree.PARAM_CHECKSUM` 为 md5（remote/local.py:44）；现有 params.yaml 的 get_checksum 返回文件哈希（remote/base.py:274–309,759–760）。因此即使参数值全部正确且 status 为 {}，None 与文件哈希仍不同，commit 会询问。PipelineStage 未覆盖 changed_entries，gold 也没有改这里。该结论为**强静态推断，未做原场景运行确认**；不把它标为已复现实验，也不因标题只提 status 而删除题面末尾的明确要求。

### 6. 开发条件与历史运行证据

G 下 gold/noop ledger 各第 1 行，与原日志散列均已核对：gold `732d2c9c49eaa086d5b87eea6e96c123aa88e38b714ea40aa795e3c2e9df7eb1`；noop `fde8fc8ec8982ba668eaaa291f963287df1512d687e100ed81d3be50e67fa050`。以下路径末段分别是 gold 的 `evallog_replay-er19-dv1-iterativ_24d09737.eval.log` 和 noop 的 `evallog_replay-er19-dv1-iterativ_92136cb3.eval.log`，均在对应 `eval_logs/`。

- noop:913 与 gold:930 的实际命令均为 `pytest -rA tests/func/test_run_multistage.py tests/unit/dependency/test_params.py`。noop:945–948 是空输入断言失败，其他六例同型；noop:2174–2185 为 7 failed、42 passed、2 skipped / rc=1。gold:2007–2020 为七例 passed、49 passed、2 skipped / rc=0。ledger 报 7/7 F2P、22/22 P2P、reward 1，noop 0/7、22/22、reward 0。这些都是 09-19 历史 grader 证据。
- 配方先离线安装 `networkx==2.3+rh2.1`，再 `pip install -e '.[all,tests]'`。记录为 Python 3.9.20、pytest 7.4.4、派生镜像 `sha256:fff47cb990a42b0f174cf646d339681682c7538bf3caf6792ea5ceab216e5b96`、rh2grader/54322、2 CPU/4 GiB、deny_all，峰值约 387/482 MiB；日志 actual base diff 另有 setup.py 的 moto 从 1.3.14.dev464 到 1.3.14（gold:500–510）。不能称运行源树与静态公开树逐字相同。
- unit 复现只需本地 YAML、工作区、DVC state 和已准备 Python 依赖；tests/conftest 仍统一导入 remotes，故“测试局部”不等于可省全部收集期依赖。只跑本地参数场景不需要原业务数据、付费资源或公网；准备时需要固定相容依赖。公开窄验证可从 `pytest -q tests/unit/dependency/test_params.py` 开始，另作本地阶段重载/commit 复现。
- 当前正式 actor 是否消费该派生镜像、兼容 wheel、moto 调整、激活脚本与写权限未知。冻结 face 的 `rollout_spec_from_view:345–354` 仍取 public.image，recipe wrapper 只修改 grader spec，不证明 actor 已采用；原构建 context 缺失，目标机镜像是否存在未验。不能把 grader 安装成功或 apply_user=agent/54321 当真实 solver shell 验收。

### 7. 交付与评分边界

gold 的 `dvc/dependency/param.py` 在 ledger projection 的 included_paths，ignored_paths 为空；正常修复不需改测试。test.patch 只触及两个 tests 文件，无业务源码混入。eval_script 恢复这两个文件再应用官方 patch；此事实不支持 public_hints 中“所有测试改动一律恢复”的概括，但对本题正常源代码修复未见交付冲突。共享 parser/隔离未作全面审计。

本题另需 reference-bindings-v1：只将非法阶段名的一个反斜杠参考 ID 映射到 pytest 的完整转义 nodeid。已读本题 binding 与 parse_bound，要求命中对应完整节点，不修改测试体，也未修改 F2P；重放时漏用 `--bindings` 会改变参考解释。原 launcher 对精确本题 ID 添加此参数，recipe 原件和 ledger grader_version 相符。

真实 actor 可见资产、祖先 refs、未跟踪文件和预装包的答案泄漏尚未核验；public 静态导出不带 .git 不是资产安全验收，检查 29 保留 unknown。

### 8. 题目关系与用途

按隔离要求未读其他题或未来历史，不能确认重复题/补丁派生关系。题面提供 false 的诊断线索但未给修法。审查者已暴露 gold、隐藏测试及历史结果，本稿只用于审查和开发诊断，不作为 solver 输入，也不证明模型成功率、学习价值或正式训练/评测准入。

## 处置与唯一优先下一步

保留 `needs_review`：主要原因是**公开双目标与 gold/评分范围不一致的强静态证据**，另有 actor 实际条件缺项。检查语义：3（真实消息）unknown；23（题意）已识别双目标；24（合法替代解）已给可行不同路线、无具体误拒，未穷举；29（真实资产/泄漏）unknown；18–20/25/26/27 记录上述覆盖缺口和未修推断；33–36 未做模型实验。

**唯一优先实验：在对应 dvc_install_v1c CPU 诊断环境中，对 base 与 gold 各运行一次“未改参数的阶段重载后 commit”最小场景。** 用原题 start/end/benchmark/universe 创建本地参数阶段（命令可用 `cat params.yaml > out`），保存并重新加载，先确认 status 为 {}，再对该阶段 commit，记录是否进入 prompt_to_commit 以及 changed_deps；同时保存参数 info 和文件哈希。若 gold 仍报 params.yaml changed，即确认题面第 1 项未修且既有满分不能代表完成原需求。此实验不需要第二个对抗候选、不修改正式材料，也不能替代后续 actor 消费链验收。

封存后等待协调者显式解封；此阶段不读取或写入其它角色文稿。
