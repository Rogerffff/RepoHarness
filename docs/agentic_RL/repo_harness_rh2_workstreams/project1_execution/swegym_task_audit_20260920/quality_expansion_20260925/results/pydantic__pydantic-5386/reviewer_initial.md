# pydantic__pydantic-5386 独立初判

结论：保持 needs_review（static_review）。公开需求有合理修复方向，但官方 F2P 验的是未在题面约定的新 hook 名称与调用序列，且完全不检查字段可用性。存在实质误拒和漏测风险，不宜仅凭历史 gold 得分列为无争议候选。

本稿为 fresh 独立 reviewer 在未读 public_read、主审、其它角色、旧质量结论和根汇总时形成的初判。全程只做静态文件、JSON、AST、hash 检查，未执行/导入项目、测试、安装、网络或容器操作。已读 roles/reviewer.md、record_template.md、actor_environment_card.md、check_number_reference.md、actor_development_validation.md。引用 P=本题 public 目录， V=本题 private 目录， L=run_refs.json 精确指定的原日志；下述 base 行号均指 P/base。包内其它两题仅用于共同方法理解，不作为本题事实证据。

实际 actor 初始 HEAD、porcelain status 输出/退出码/采集阶段、来源初始改动、忽略资产及准备后状态、消息、UID/HOME/cwd/PATH、解释器和文件权限全部 unknown。public/base 是固定 Git blobs；没有 .git 的静态导出不证明 actor 缺件。user_prompt 是计划输入，public_hints 是否实际交付未知。历史 grader 的 source import、安装和成功测试不是当前 actor 开发资格。

### 1. 目标、版本、公开推断和合理路线

base=6cbd8d69609bcc5b4b383830736790f9b8087e36，公开 2.0a1 时期问题：希望在子类定义阶段、无实例时遍历本类字段，检查示例 metadata。题面伪代码缺少 class 关键字，且 checker 调用拼法不完整；可据文字理解目标，不能把该代码原样执行失败归为环境错误。base 的 ModelMetaclass.__new__ 在 main.py:109 调用 type 创建，148 才 set_model_fields，因此标准 __init_subclass__ 在本类字段收集之前运行。_model_construction.py:136–144 确实设置 cls.model_fields；不存在本题要求的新 hook 是静态事实。

可行路线包括提供一个充分初始化后的 class hook 并公开说明，或重构字段准备/类定义流程使现有 __init_subclass__ 能读取正确字段。后者难度和兼容性风险较高，但只要满足公开目标和既有行为，不能因不选择 gold 新 API 名而直接判错。

### 2. 完整新增断言/helper 与需求—断言双向表

已完整读 V/test.patch：仅 test_pydantic_init_subclass 一个新增函数。calls 列表、MyModel 两个 hook、super 调用、MySubModel(a=1) 及最终整个 calls 等值断言均已逐行读；没有外部 fixture/helper。唯一 F2P 即 tests/test_main.py::test_pydantic_init_subclass。

| 需求/旧行为 | 公开依据 | 断言/反向约束 | 判断 |
|---|---|---|---|
| 定义时读取子类自身字段及 metadata，无需实例 | 题面 Description/example | 新测试的两类均没有字段；无 model_fields/metadata 读取 | 缺失；即使 hook 在 set_model_fields 前调用也可能通过 |
| 保留旧 __init_subclass__ 一次、kwargs | 既有 test_custom_init_subclass_params；类扩展协议 | calls 第一项 MySubModel/__init_subclass__/{a:1} | 覆盖该简单类链 |
| 指定新 hook __pydantic_init_subclass__ | 题面未指定；base 无此 API | calls 第二项及 super().__pydantic_init_subclass__ | 对公开需求增加实现接口约束；误拒合理其它路线 |
| 先旧 hook 再新 hook、各一次 | 新接口实现方案 | 整个 calls 列表精确相等 | 覆盖顺序/重复，但不等于字段完成时序 |
| 合作继承、配置关键字剥离 | 旧配置行为、config.py:227 | 新测仅 a=1 与单继承；P2P 配置测试 | 部分，多继承/本类重写链未测 |

不存在遗漏的新增 assertion：唯一 assert 覆盖上述两条记录，但不能反推字段需求已被测试。

### 3. P2P 实读范围及 gold/调用者

已读 P2P 主体：test_custom_init_subclass_params(1338)、test_class_kwargs_config(1667)、test_class_kwargs_config_and_attr_conflict(1683)、test_class_kwargs_custom_config(1693)、test_post_init(1786)、test_parent_sub_model(187)、test_parent_sub_model_fails(195) 及 parent_sub_model_fixture(174)、test_field_order(357)、test_class_var(731)、test_recursive_model(1354)、test_inherited_model_field_copy(1530)、test_type_type_subclass_validation_success(661)、test_mapping_retains_type_subclass(1552)、test_dict_subclasses_bare(1614)、test_dict_subclasses_typed(1622)。除这些主体外，其他 P2P 只核 expected 名与原状态行，未逐断言阅读；没有把 106 数量当覆盖证明。

gold 完整读：main.py 在 set_model_fields/complete_model_class 后执行 super(cls,cls).__pydantic_init_subclass__(**kwargs)，BaseModel 增加 no-op classmethod。定位的 config.build_config 会 pop 已知配置 kwargs，剩余原样传递；该路线能在新 hook 读取已收集字段。super(cls,cls) 跳过当前类本身实现、寻找父类 hook，单继承合理。complete_model_class(147–197) 在 unresolved forward annotation 可返回 False，故 gold 文档“fully initialized”不能理解为所有模型此刻都能实例化；字段 metadata 目标与完整 schema 是不同范围。未见已证 gold 回归，多继承、递归/泛型及新 hook 的行为需窄验证。

### 4. 运行失败归因

历史 noop 日志 591–607：实际失败为 calls 缺第二条记录（2081 行），不是字段读取失败；gold 630 行通过。noop/gold 各收集159项，noop 120 passed/1 failed/29 skipped/9 xfailed，gold 121 passed/29 skipped/9 xfailed。parser 116 身份数与159收集数不同，expected 状态已逐名对账，未据数量差直接判 parser 错。

历史 noop 132–139 的普通 git status 见 pyproject.toml 修改，176–196 diff 加 [tool.pdm] 和 pre-commit>=2.21.0；这不是 actor 初态，也不是 git show 的提交内容。不能声称“干净 base 即运行初态”。

### 5. 漏测、误拒、回归与下一事实需求

最强漏测反例（静态可构造，未运行）：保留 no-op 新方法并在 type.__new__ 返回后、set_model_fields 前调用父 hook；新 F2P 的无字段模型仍得到完全相同 calls，而真实子类字段读取仍错。最强误拒路径：满足字段读取目标的其它 hook 或既有 hook 改良没有指定新 hook，F2P 仍缺记录。不能靠补文档私自改变本题定义；先明确评分范围，保留原任务版本。

优先请任务二取得公开定义时字段读取行为、实际 actor 初态和 shell 可用事实；若需要评估此题是否适合公平求解，应另在私有诊断中验证上述早调用反例/可接受路线，目的为裁定 check24/25，不混入 solver 资料。当前不执行或派发实验。

### 6. 开发操作/资产/权限

| 操作/资产 | 公开依据 | 证据适用范围与缺口 | 最小公开验证/预期 |
|---|---|---|---|
| 工作区 Python/Pydantic 与 pydantic-core | pyproject.toml:1–3,57–60；Makefile install | 历史 grader editable 安装成功，2.0a1；actor 包来源未知 | actor 打印 sys.executable、pydantic.__file__、core版本；应来自工作区 |
| 公开字段访问复现与旧 hook 参数行为 | 题面及上述公开 P2P | 不需模型权重/数据/外部服务的本地类构造；依赖和写权限未核 | 根据题面合法补齐 class 定义，在类 hook 记录自身字段；base 应显示目标缺陷；pytest tests/test_main.py -k 'custom_init_subclass_params or class_kwargs or field_order' 应实际执行 |
| editable 开发、交付非测试源码 | public_hints、Makefile:5–8 | hatchling/编译依赖 wheel供应与 actor 安装权限未知；historical /opt/rh2/build-wheels 非actor资产证明 | 实际入口保存 HEAD/status/diff 与源码生效证据，候选相对实际初态导出；不要求全仓绿 |

### 7. 编号状态、暴露与用途

| checks | status | 证据/边界（by=fresh reviewer） |
|---|---|---|
| 1,2 | pass | 静态版本绑定及该历史noop目标机制；非当前actor身份 |
| 3,4,6,7,8,10,11,29,33 | unknown | 环境卡；真实actor输入/权限/资产/交付未取 |
| 18,19,20,21 | pass | 限已引用历史选择器、逐expected状态与失败位置 |
| 23,24,25 | issue | 上述题面—新hook接口差与无字段assert缺口 |
| 26,27 | unknown | gold目标静态合理；未证完整正确性及所有回归 |
| 40 | unknown | 独立封存不证明无漏检/误杀或抽样偏差 |

其它编号 not_checked。usage.intended_use=development_diagnostic；本 reviewer 已见本包三题 gold/隐藏test/私有grader日志及候选引用，未读模型旧答案、旧质量结论或他人结论。私有审查暴露单列，不据此判 check29 的实际actor泄漏。无训练/正式评测批准，成本/token未知。


### 原运行核对与交付恢复范围

- gold: `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5386/gold/ledger.jsonl:1`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5386/gold/eval_logs/evallog_replay-er19-pyd1-pydanti_9f284c5e.eval.log`。历史 pydantic-install-v1、rh2grader UID 54322、deny_all 网络；image ID `sha256:1342cb8e8c0a223999d7c644d0966dfa1f5d506fe4daf9a02225edc11c31e2ca`。install rc=0，test rc=0；F2P 1/1，P2P fail 0/106。只描述该历史执行。
- noop: `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5386/noop/ledger.jsonl:1`；日志 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/env_recipe_repair_20260919/pydantic_v1/tasks/pydantic__pydantic-5386/noop/eval_logs/evallog_replay-er19-pyd1-pydanti_bb4d29b6.eval.log`。历史 pydantic-install-v1、rh2grader UID 54322、deny_all 网络；image ID `sha256:1342cb8e8c0a223999d7c644d0966dfa1f5d506fe4daf9a02225edc11c31e2ca`。install rc=0，test rc=1；F2P 0/1，P2P fail 0/106。只描述该历史执行。
已用 stdlib 对账所有 expected F2P/P2P nodeid 与日志状态行：两次所有 P2P 均有 PASSED，无 expected 缺失；原账本 parser reference_missing/reference_skipped 为空、outside segment 为 0。不是将总分代替断言审查。已核 ledger/log SHA 与 run_refs 一致，gold candidate.patch 与本题 gold.patch 字节一致；stage HEAD 和 projection included_entry_paths 与本题源码修改对应。源码 diff 出现在 grader 日志；观察字段 import=/testbed/pydantic/__init__.py。

已读 after candidate/eval 脚本：conda testbed、/testbed、editable pip 安装及 testing/testing-extra 依赖、固定测试文件恢复后施加 test patch，再执行指定文件。实际日志含 checkout 与 Applied patch cleanly；账本 cleanup.removed=true。恢复、projection、runner digest 证据仅限该历史正常候选；没有穷举恶意评分控制面或并发/重复一致性，也未独立核实现行 parser 源码、完整 baseline manifest 和全部原 recipe before/build 内容。

初判到此封存，等待明确 cross_review release；不以封存本身作为check40通过证据。
