# iterative__dvc-6954 — 历史开放前封存分析

2026-09-21，B3 私有主审。仅静态文件读取与 stdlib 元数据比对；未运行项目、测试、安装、容器、联网或模型。已读公开稿、gold/隐藏测试、授权 environment_record 与本题两角色运行原件；未读 history/refs、质量旧记录、reviewer 或批次聚合。以下命令均为建议，未执行。本上下文不能用于独立 solver。

路径简写：P=`runs/swegym_quality_batch03_20260921_v1/public/iterative__dvc-6954`；V=同批 `private/iterative__dvc-6954`；R=`runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-6954`。所有路径相对权威 ROOT=${REPO_ROOT}。

## 1. 材料、初态与公开要求

精确 base `28dd39a1a0d710585ff21bf66199208b1b83cbde`；沿用协调者完整身份验收和 P/base_identity.json 的 551 项导出核验。局部确认 V/test.patch 等于 grading.test_patch，gold.patch 等于 validation.golden_patch；gold SHA256 为 `50ed349f0cad3875991e03a9a4c9a01c0ff286cc18a00f1c221f121bcddb8116`，test patch 为 `e57dff1329d7ca7842d3d3d639ec1a03d401065f4286ef893af93552196087fa`。来源行号见 V/source_refs.json:3-20（S2 三包第 143 行）。

题面要求 Python 参数 `my_int = -1` 能用于 dvc run/repro，stage 执行并更新锁文件；YAML 已工作（P/user_prompt.txt:10-14,26-56）。参数名、文件名和日志缩进是示例，未强制某种 AST 实现。公开旧测试已约定 float、容器、注解和类属性读取。负浮点数及这些既有位置中的负数字面量是合理扩展；任意算术、连续符号和动态执行并非题面要求。public_hints 存于 bundle，当前 user_prompt 为静态渲染，实际 CC 请求/附加消息未捕获。

根因可直接定位：P/base/dvc/utils/serialize/_py.py:172-181 的取值器拒绝 UnaryOp，:116-119 略过该赋值；ParamsDependency.read_params/get_hash (:116-138) 因缺键报错。noop 原日志 :132-136 显示 clean、HEAD=base，:213 的 base diff 为空；其前面的 exp diff 补丁是 `git show` 展示本次 base 提交，不能误记作工作区未来补丁。noop 测试在 parse_py 断言真实得到 `{}`（R/noop/eval_logs/*9b69e9e3.eval.log:625-673），为原 bug 提供实际证据，但不是题面 CLI 复现。

## 2. 需求—测试双向映射

新增文件只有 `tests/unit/utils/serialize/test_python.py`，完整 45 行/13 参数用例均已阅读（V/test.patch:6-50），没有 Mock 或自定义 helper。pytest 根 conftest 的 autouse 仅重置日志、启用 UI、结束连接池；这些 fixture 及其远端导入入口已查。冻结 F2P=1、P2P=12。

| 需求/旧行为 | 公开依据 | 决定性断言/参考 ID（统一前缀 tests/unit/utils/serialize/test_python.py::） | 覆盖及证据 |
| --- | --- | --- | --- |
| 普通负整数读取 | user_prompt:3-14,43 | F2P `test_parse_valid_types[UNARY_OP`：`parse_py("UNARY_OP = -1","foo")=={"UNARY_OP":-1}` | 直接覆盖；noop {}，gold 通过 |
| 正数、文本、布尔、None | base/tests/unit/dependency/test_params.py:114-153 | P2P BOOL/INT/FLOAT/STR/NONE，各比较真实 Python 值 | 覆盖五类，无格式/实现形状约束 |
| dict/list/set/tuple | 同上 :122-152 | P2P DICT/LIST/SET/TUPLE，比较完整容器值 | 覆盖原单层正数容器；未覆盖负元素/嵌套 |
| 类常量、self、后赋值覆盖、忽略局部变量 | 同上 :155-176；_py.py:89-120,162-169 | P2P `test_parse_valid_types[class`，EPOCHS=70、layers=9，bar 不出现 | 直接覆盖一个类形状；注解未被本次参考保护 |
| 不执行调用/普通算术 | _py.py:172-181 的既有静态提取边界 | P2P `test_parse_invalid_types[CONSTRUCTOR` 和 `[SUM`：dict(a=1,b=2)、1+2 均输出 {} | 保留旧行为，有公开源码依据；未要求恢复所有 Python 求值 |
| dvc run/repro、参数缺失与值跟踪、锁文件 | user_prompt:26-56；param.py:64-138；stage/serialize.py:109-125,175-187 | 本次 13 项没有 CLI、文件 I/O、ParamsDependency 或 lock 断言 | 部分覆盖：解析器是实际共用入口；未执行这些端到端行为 |
| 负 float、类/注解/容器中的负数；更新路径 | 题名 + base/test_params.py；_py.py:30-86 | 本次参考未覆盖；公开 test_update_py_params 只测原正值更新 | 明确限度，不能把 12 P2P 当作完整回归 |

合理替代解可保留 _get_ast_value 并仅在安全数值字面量上处理 ast.USub；没有断言要求删除 helper 或使用 ast.literal_eval，静态未发现误拒这条路线。仅支持负整数而遗漏负浮点的部分实现可能通过全部参考；这是具体静态漏测线索，尚无实际 RH2 反例，不称已证实假阳性。

## 3. gold 与相关回归

gold 仅改 _py.py 的值读取为 ast.literal_eval 并删除旧 helper，保留赋值筛选和 lineno 构造；负整数/负浮点、既有单层容器负元素都可进入共用值结构，不需新依赖。没有 test patch 混入业务源码或 gold 无关文件。ast.literal_eval 自然扩大到部分嵌套/其他字面量，题面不要求全语言解析；其扩大范围与 _dump 的行内字符串替换组合未被 13 项保护，不能据未测边界直接判 gold 错。

已沿 parse_py → LOADERS → ParamsDependency → stage.save_deps/get_hash → lock 序列化阅读；并读 params.show 加载点、experiments._update_params → MODIFIERS 的调用。相关公开回归实际阅读：test_params.py 全文；tests/func/params/test_show.py:1-88；tests/func/experiments/test_experiments.py:230-335（含完整 test_update_py_params）；没有执行，后两者不是冻结 P2P。未穷举整个参数系统/全仓；未发现已证实新增破坏，不以此声称无回归。

## 4. 固定 grader 运行与安装消费

授权 environment_record 已带 `verified_environment_pair`、gold=1/noop=0 等既有环境摘要；已如实看到，但未追其 analysis_68/history 指针。决定性运行原件是 R/gold/ledger.jsonl:1 与 R/noop/ledger.jsonl:1（run_id 分别 er19-dv1-iterative__dvc-6954-gold/noop、attempt=1）。

- 原输入是 `runs/env_recipe_repair_20260919/dvc_install_v1c/recipes/iterative__dvc-6954.json:3-11`；wrapper :61-86 精确匹配 original_install，替换 eval_script/candidate_test_script，并把含 hash/scope 的 recipe 写成审计输出。逐 run recipe.json 不是启动输入。
- 镜像 `sha256:e54a7bc51b8d4fd9187c6ac0bd2282c52d51ae2e2695bae263adf58a7159a1ed` 的 Dockerfile 只 COPY wheels 和设离线索引；安装消费证据来自实际日志：gold :447-451,650-670；noop :392-396,595-615，均从 /testbed 执行 `pip install -e '.[all,tests]'`，build dependencies/editable 成功，安装 RC=0，后置观测导入 /testbed/dvc/__init__.py。不是把“轮子存在”当“已安装”。
- 真实命令只有 `pytest -rA tests/unit/utils/serialize/test_python.py`（gold :680；noop :625）。gold :685-715 为 13 passed、RC0；noop :630-700 为 1 failed/12 passed、RC1。两者参考 missing/skipped=[]，parser 段外项 0、解析项 13；截断参考名 UNARY_OP 等逐一对应原始 pytest 参数名的独特前缀，未见本次碰撞。
- 冻结评分是 swe_f2p_p2p；两账本 F2P=1/1 与 0/1，P2P 都 12/12，reward=1/0。此题实际执行项恰等于参考项，不将一般“pytest 非零”当额外 reward 规则。
- 该两次条件是 rh2grader/54322、deny_all、2 CPU/4 GiB、shm64MiB，可写 conda prefix；资格均 `absent`。cleanup removed=true、无 stage_error。它们证明历史固定 grader 诊断，不证明正式 actor 配方消费、目标主机镜像存在、消息/工具/权限或稳定重跑。

为核历史执行边界，仅用 tarfile 只读 `frozen_sources/dvc.tar.gz!src/repoharness2/adapters/slime/prepared_task_face.py`。:185-234 解释 profile 使用 attested trusted setup + candidate script，新文件不做不存在的 checkout；:304-338 从 test patch 取官方路径、空 test_globs、标记段 parser。故审计 eval_script.after.sh:10 的新文件 checkout 不是本次实际 profile 的失败证据。历史归档不是当前 ROOT/rh2。

## 5. 开发条件、交付边界与唯一优先下一步

| 必要能力/资产 | 依据与已见条件 | 未验及最小验证（全部未执行） |
| --- | --- | --- |
| Python/DVC/序列化导入 | setup.cfg:28-78、pyproject.toml:1-6；grader editable 安装成功 | actor shell 下打印 sys.executable、dvc.__file__，再 parse_py 公开 -1 示例；不得只验 stdlib ast |
| Git、CLI、临时本地 repo、cache/lock 可写 | 题面无需远端、账户、数据集；run/repro 操作均在本地 | actor 实际 PATH、UID/HOME、/testbed 与临时目录可写待验；公开稿提供完整复现 |
| 窄测试收集 | setup.cfg:117-139，conftest:6-8 导入多种 remotes | grader 13 项可收集；actor 插件及相关依赖未验；建议公开 test_params.py，非全仓门槛 |
| 安装/资源/网络 | 已有 build wheels + 离线安装适用于历史 grader；未新增项目编译需求 | actor 不能继承 grader prefix 写权限；旧 /work 路径需新重定位，context/wheel payload 本地未存，镜像待确认；准备固定资产与解题联网分开 |
| 合法源码交付 | gold projection 仅 _py.py、ignored=[]；官方路径仅新测试文件 | 不要求修改系统包或测试；additional_exclusions=[]，无新增规则依据；实际 actor 可见 Git/镜像答案资产未验 |

八方面状态：公开要求与材料可解释；测试映射完整；未见强制唯一实现；相关回归/目标 gold 静态成立而端到端未验；grader 安装已核、actor 开发条件未验；交付源码未被官方恢复覆盖；跨题修复/holdout 关系未做谱系审计，不能仅按同仓聚类；已暴露私有答案，限定 development_diagnostic。真实模型能力、成本、采样稳定性及 reviewer 未查。

暂定 `needs_review/static_review`：静态可作为开发诊断候选，保留普通负浮点和端到端覆盖限度；不是 ready_for_probe 或正式训练/评测接受。唯一优先下一步：在明确采用的正式 actor 环境中跑公开稿的 -1 repro→lock/不变跳过→改值流程，并把同一复现值换为 -0.5，核其解释器/候选来源与输出。这个窄公开行为验证同时区分“解析单测成功”和“实际开发通路可用”；若出现整数限定实现再做冻结 grader 对照，无需先造通用攻击或全仓门槛。
