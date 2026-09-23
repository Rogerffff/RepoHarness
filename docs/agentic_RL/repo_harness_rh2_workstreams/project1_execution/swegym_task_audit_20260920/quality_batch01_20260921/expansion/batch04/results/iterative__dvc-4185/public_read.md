iterative__dvc-4185 公开阅读记录

审查日期：2026-09-21。角色：全新单题公开读者。这里只记录公开要求、静态代码线索和建议验证，不提供修复补丁，不推测隐藏验收或标准答案。

路径约定：ROOT=.；PUBLIC_DIR=ROOT/runs/swegym_quality_batch04_20260921_v1/public/iterative__dvc-4185。下列 user_prompt.txt、public_bundle.json、environment_brief.md、base/... 引用均相对 PUBLIC_DIR；L 表示实际静态文件行号。base_commit 的公开标签为 0899b277c02082ffc24bb732e8a7cf3ef4333948（public_bundle.json:L1），本角色未通过共享镜像或历史另行核验导出身份。

**公开要求与约束分层**

| 类型 | 公开内容 | 应如何理解 |
| --- | --- | --- |
| Issue 目标 | 未改动时，eval.filter_limitup: false 在 dvc status 中反复显示 new；commit 和 repro 未能使其恢复干净状态。另一个仅含普通非假值参数的 get_base_dv，status 未报变化，commit 却提示参数依赖已变（user_prompt.txt:L26-L58、L61-L109）。 | 两个症状均是明示需求。只修复 CLI 显示或只修复 false 的状态误报，并不能自动说明 commit 的独立误报也已解决。 |
| Harness 操作指令 | public_hints 要求探索源码、修改非测试源码、禁止修改测试、允许窄范围测试（public_bundle.json:L1 的 public_hints 字段）。 | 原指令确实可见。当前是否以同样消息位置应用，仍待实际工作流核对；本审查没有授权忽略它。源码层面存在合理实现路径，未见必须修改现有测试文件才能完成修复的要求。 |
| 待验环境声明 | public_hints 称 /testbed 中已有激活的 testbed conda 环境，python/pip/测试工具可用；bundle 声明 bash/edit、镜像标签和摘要（public_bundle.json:L1）。 | 均是公开声明，不是本角色的运行验证结果。镜像摘要不能代替依赖、权限或测试可执行性的检查。 |
| 旧机制说明 | 旧提示称测试改动全部恢复、永不计分；neutral 说明指出目前没有按测试文件名统一排除，仍存在官方文件恢复等具体限制（environment_brief.md:L18-L26）。 | 保留“禁止改测试”的原操作指令，不能把它的旧解释当作当前评分机制事实。若原指令适用，可用临时复现和已有公开测试验证源码修复；若不适用，可以增加回归测试，但行为要求和源码修复范围不因此改变。受影响的具体文件不在本角色调查范围。 |
| 审查与真实环境边界 | prompt 为静态模板渲染，未捕获实际模型请求；base 为指定提交的跟踪文件导出，没有 .git/未来历史；资源、预装包、资产均未验证（environment_brief.md:L3-L16）。 | 不声称已见真实系统消息、工具调用环境、实际模型配置或容器资源。bundle 不在 user_prompt.txt 中，不等于解题者不可见。 |

**需求表**

| 编号 | 目标或应保留行为 | 依据与确定程度 |
| --- | --- | --- |
| R1 | 已记录的 eval.filter_limitup 为 false，工作区值不变时，重新加载阶段后 status 不应把该参数显示为 new 或 modified。 | 明示：user_prompt.txt:L26-L58、L68-L71、L93-L98、L107-L109。 |
| R2 | 普通参数依赖没有变化时，commit 不应无端提示该参数文件已经变化；正常提交后也不应每次重复同样提示。 | 明示：user_prompt.txt:L34-L41、L77-L85、L108。这个要求不限于 false，因为 get_base_dv 跟踪的参数均为非假值。 |
| R3 | 保存、提交、重新读取 dvc.lock，以及复现/恢复运行缓存后，应保留参数已记录状态；不应靠清除追踪信息、强行重跑或只抑制输出规避误报。 | 明示的跨命令症状见 user_prompt.txt:L34-L58；加载和缓存调用链见 base/dvc/stage/loader.py:L25-L45、L70-L74，base/dvc/stage/cache.py:L150-L157。是否命中某个具体运行缓存不是题目指定的唯一成功文案。 |
| R4 | 真正缺失的键、锁文件尚未记录的键、真正改变的值仍应分别产生 deleted、new、modified；缺失整个参数文件仍报告 deleted。相等的已记录值产生空状态。 | 可由现有接口合理推知：base/dvc/dependency/param.py:L56-L77。CLI/JSON 消费此结构，见 base/dvc/command/status.py:L18-L64。 |
| R5 | 参数“有值”不能被当作“值为真”。除了题面明确的 false，对解析器已经支持的 0、null/None、空字符串、空列表、空映射等也应保留“键存在且值被记录”的语义。 | false 是明示；其它假值属于同一语义的合理推广。base/dvc/dependency/param.py:L43-L50、L85-L116 按键读取/检查缺失；base/tests/unit/dependency/test_params.py:L8-L13、L53-L68 已把 None 当作合法记录值。公开材料没有新增类型敏感比较约定，不能要求 false 与 0 的类型变化必然超出现有 != 语义。 |
| R6 | 只比较阶段声明跟踪的参数；默认 params.yaml、自定义文件、点分嵌套路径、列表/映射参数均继续工作。未跟踪字段的独立变更不应仅因整份 YAML 文件字节改变而使该参数依赖变更。 | 可由现有选键代码推知：base/dvc/dependency/param.py:L47-L50、L98-L103，base/dvc/dependency/__init__.py:L88-L113；公开用例见 base/tests/unit/dependency/test_params.py:L16-L44、L91-L96，base/tests/func/test_run_multistage.py:L227-L305，base/tests/func/test_repro_multistage.py:L473-L527。 |
| R7 | 参数文件不存在/参数缺失时的 save_info 错误、无法解析的 YAML 错误保持；锁文件未含某参数不能凭空补成 null；不存在整个 params 区段时允许尚未填值。 | 公开测试约束：base/tests/unit/dependency/test_params.py:L79-L109；base/tests/unit/stage/test_loader_pipeline_file.py:L41-L86、L138-L145。缺键与显式 null 必须区分。 |
| R8 | 普通文件依赖/输出真正变更、缓存缺失、阶段命令变更等原有行为保持；正常变更的 commit 确认/force 机制仍有效。 | base/tests/func/test_commit.py:L19-L38、L62-L97；base/tests/func/test_status.py:L70-L114；base/dvc/repo/commit.py:L30-L48。不能为了消除参数误报而让所有依赖或所有提交都被当作未变。 |

**合理实现范围与公开约定**

可以接受多种等价实现，不应要求某个补丁形状：

- 加载已记录参数时，用键成员关系、明确的缺失哨兵或选定键的映射投影来保留假值，均符合公开语义；须继续区分“未记录该键”和“记录了 null”，并仅引入所声明的参数。
- 参数依赖可以自行提供基于所选参数值的变更判断；也可以通过共享比较逻辑让 status 与 commit 的参数路径保持一致。具体放在哪个方法、是否抽辅助函数不是题面约定。若调整通用 Stage/BaseOutput 路径，必须保持普通文件依赖、缓存和输出检查；参数值映射不能继续被误当成普通文件 md5 元数据。
- 默认文件名 params.yaml、点分路径读取、多个参数文件、状态字符串 new/deleted/modified 及现有状态嵌套结构已有代码和公开测试依据。状态应与实际变化对应，保留既有正常展示格式即可；题面未要求新 CLI 选项、新文件格式或新的报错措辞。
- 保持锁文件按参数文件和参数键组织的现有格式与排序约定；空的尚未填值参数不应被写成凭空存在的参数值。依据：base/dvc/stage/serialize.py:L66-L108、L134-L164；base/tests/unit/stage/test_serialize_pipeline_lock.py:L62-L111。
- 对特定业务键名做例外、把 false 转为字符串/true、忽略所有参数变化、要求用户移除参数追踪，均无法满足明示目标。公开材料不要求 WSL/9p 专用修复、完整业务流水线重跑或云远端访问。

本报告没有提出或运行修复代码，也没有尝试推断官方实现选用的具体方法。

**初态线索、相关调用者与疑义**

静态材料可以定位调查入口：

1. dvc.yaml 中列出参数名后，StageLoader.load_stage 创建依赖，再从 lock_data 取对应文件的参数值交给 fill_values（base/dvc/stage/loader.py:L48-L74、L25-L45）。ParamsDependency.fill_values 使用 values.get(param)，然后仅在 if value 成立时写入 self.info（base/dvc/dependency/param.py:L43-L50）。在值为 false 且 self.info 起初为空的情形下，这条路径会跳过已有记录；status 又把“当前能读到、self.info 中没有”的键判断为 new（同文件:L63-L69）。这是能直接解释 R1 的静态线索，未执行复现。
2. commit 调用 Stage.changed_entries，再对每个依赖调用 changed_checksum（base/dvc/repo/commit.py:L39-L48，base/dvc/stage/__init__.py:L397-L411）。ParamsDependency 沿 LocalDependency/BaseDependency/LocalOutput 继承通用输出行为；通用 checksum 从 self.info 读取文件校验和，changed_checksum 比较它与整文件哈希（base/dvc/output/base.py:L168-L195）。但参数 self.info 存放的是参数名到值的映射（base/dvc/dependency/param.py:L25-L41、L105-L116），不是普通文件 md5 记录。这解释了为何真值参数阶段也可能被 commit 报为已变。
3. status 则走 Repo._local_status → Stage.status → 依赖 status，并由 ParamsDependency 按所选键比较（base/dvc/repo/status.py:L13-L37、L145-L147；base/dvc/stage/__init__.py:L467-L490）。reproduce 的变化判断同样调用依赖 status，保存会重新采集参数，运行缓存恢复再次调用 fill_from_lock（base/dvc/stage/__init__.py:L213-L241、L306-L324、L378-L387；base/dvc/stage/cache.py:L150-L157）。因此应核对持久化和重新加载，不能只检查刚创建的内存对象。
4. CLI 对空状态显示 “Data and pipelines are up to date.”；--quiet 用空/非空状态决定返回码；--show-json 输出原状态结构（base/dvc/command/status.py:L11、L39-L69，base/dvc/command/data_sync.py:L307-L315、L367-L374）。这些调用者允许以 JSON 和仓库 API 判断语义，避免把排版空格当作主要验收标准。

仍需保留的未知：

- Issue 未提供实际 dvc.lock、原业务脚本、输入预测文件、输出报告和完整仓库。因此不能静态证明原作者环境每一步的实际文件状态，或保证复现相同的运行缓存日志。这个缺口影响完整原场景重放，不阻碍通过本地小样例调查已明示的两个症状。
- Issue 没有罗列所有假值、类型切换或重复调用 fill_values 的政策。根据键存在性和当前公开 API 可合理扩大到已有支持的假值；额外的类型严格比较、缓存格式迁移或其它未描述行为变化没有要求依据。
- 公开参数单元测试覆盖 None 的直接装载/导出、嵌套值和缺失错误；已打开的锁加载测试使用真值并保留缺键，未在该用例覆盖 false。运行参数公开样例也以真值为主。这些现有测试即使通过，也不足以单独证明 R1/R2 已修复，需最小复现或针对行为的临时验证。
- CONTRIBUTING.md:L1 和 README.rst:L91-L92、L203-L204 把更完整指南放在外链；本包没有打开该外链内容。本题已有源码/依赖清单/公开测试可定位调查，不需要为当前静态判断获取外网或未来代码。没有发现必须请求公开祖先历史才能继续的理由。
- README.rst:L134 的旧 Conda 版本说明与 setup.py:L163-L169 的 Python >=3.6/3.6–3.8 元数据不完全一致；Issue 报告 Python 3.8.3。不能凭 README 推定实际 Python 版本兼容性，尤其旧依赖和 fixture 使用的 pathlib 内部方法仍需真实解释器验证。
- 真实 actor 的 conda 激活、源码导入位置、依赖完整性、可写目录和 CPU 资源仍未知。没有把这些缺证据直接判成题目不可解。

**开发需求表**

所有命令均为“建议，未执行”。建议工作流在真实 actor 身份、/testbed 指定源码下进行；本角色没有导入项目、安装依赖、运行测试或启动服务。

| 操作/资产/服务 | 公开依据 | 环境说明支持到哪层 | 缺口 | 最小检查/验证建议及预期 |
| --- | --- | --- | --- | --- |
| Python 与目标源码导入 | setup.py:L49-L82、L163-L174；参数代码导入 yaml、dpath、voluptuous；仓库还依赖 funcy 等。 | 仅 bundle 称 testbed conda 已激活。neutral:L12 要求 actor 验证。 | 实际版本、源码是否来自 /testbed、包版本和导入兼容性未知。 | C0（建议，未执行）：解释器/CLI/导入烟测；成功应能导入 Repo、ParamsDependency 并显示目标工作区的 dvc 路径。导入错误属于开发环境缺口，不是 bug 复现结果。 |
| pytest 及公共 fixture 导入依赖 | setup.py:L101-L134；tests/conftest.py:L3-L6 全局导入 dir_helpers 和 remotes；tests/remotes/__init__.py:L5-L37 导入多个远端 helper；tests/remotes/s3.py:L7 顶层导入 moto.mock_s3。 | 未验证测试工具可运行。 | 即使选纯本地测试，收集仍可能需要 moto 等额外 Python 包；不能只检查 pytest 存在就认为够用。 | C1（建议，未执行）先对单个文件 collect-only，再运行窄范围公开用例。成功是可收集且相应用例通过；这些旧用例可能在原 base 就通过。 |
| 临时工作区、参数文件、锁文件、缓存和子进程 | tests/dir_helpers.py:L90-L108、L250-L276、L292-L305；stage 的 save/commit/run 会写输出与缓存。 | neutral:L9 声明工作区/home 可写，L11 给出默认资源但未验证本题。 | actor 的临时目录、锁、缓存、子进程和实际限额未测。 | C2（建议，未执行）使用单独临时目录与本地小文件；预期修复后两阶段状态为空，未变参数提交无误报。基础路径不需要大数据、GPU或模型服务。 |
| Git/系统工具 | setup.py:L53 的 gitpython；fixture 导入 Repo/Git，显式 SCM fixture 调用 git init（tests/dir_helpers.py:L90-L108、L279-L289）。 | 未验证 Git 或 shell 工具实际可达。 | no-scm 可避免最小样例创建 Git 仓库，但 Python 导入链及有 SCM 的公开测试仍应核对 GitPython/系统 Git。 | C0 的 git --version（建议，未执行）；C2 使用 no-scm；扩大到带 git_dir/scm 的测试前再核对 Git 可用性。 |
| 原 Issue 业务资产和外部服务 | user_prompt.txt:L78-L103 引用 ipython、业务脚本、数据、报告；当前源码提供通用本地参数依赖实现。 | neutral:L6 明确未导出额外镜像资产。 | 业务资产不可用；无证据说明需要远端凭证或服务才能重现核心错误。 | C2（建议，未执行）以 shell 输出小文件替代业务命令；验证通用参数语义，不声称重放原业务结果。无需为此启动 Docker、云服务或联网取数据。 |
| 依赖补齐/构建 | README.rst:L136-L154 给 pip 安装方式；setup.py 提供依赖而非完整已验环境锁。 | neutral:L10 不假定可访问公网或下载依赖；解释器/系统包写权限需核对。 | 缺包时能否通过预装资产/离线包补齐、旧依赖是否兼容实际解释器未知。 | 不需要先打包整项目才能做最小复现。若 C0/C1 失败，应在环境准备层记录缺失包/版本并使用已提供的离线资产；本报告不建议联网升级到最新依赖掩盖兼容性问题。 |

C0：导入与工具烟测，建议，未执行（在 /testbed）：

~~~bash
python --version
python -m pip --version
git --version
python -c 'import dvc, yaml, dpath.util, voluptuous, funcy; from dvc.repo import Repo; from dvc.dependency.param import ParamsDependency; print(dvc.__file__)'
dvc --version
~~~

C1：最低公开测试阶梯，建议，未执行。先验证收集，再按实际源码改动选择后续单文件/单测试；不把所有用例列为必须一次性运行的全仓门槛。

~~~bash
python -m pytest --collect-only -q tests/unit/dependency/test_params.py
python -m pytest -q tests/unit/dependency/test_params.py
python -m pytest -q tests/unit/stage/test_loader_pipeline_file.py -k params
python -m pytest -q tests/func/test_commit.py
~~~

这些验证分别覆盖基本参数装载/异常、锁文件参数填充、真实提交/force/正常文件行为。若触及序列化或运行缓存，再按需运行以下建议，未执行：

~~~bash
python -m pytest -q tests/unit/stage/test_serialize_pipeline_lock.py -k params
python -m pytest -q tests/unit/stage/test_cache.py::test_stage_cache_params
python -m pytest -q tests/func/test_repro_multistage.py::test_repro_multiple_params
python -m pytest -q tests/func/test_status.py::test_status_on_pipeline_stages
~~~

预期这些现有公开行为保持通过；没有运行结果，不能声称它们现在可运行或已通过。没有发现本题要求全仓构建或远端集成测试的依据。

C2：同时区分两个症状的最小 CLI 复现，建议，未执行。须先核对 dvc 指向 /testbed 源码；仅写新的临时仓库，不写项目测试。命令选项已在 base/dvc/command/run.py:L95-L129、L232-L235，init.py:L31-L48，repro.py:L127-L133，data_sync.py:L367-L374，commit.py:L44-L49 中核对。

~~~bash
(
  export DVC_TEST=true
  task_repro_dir="$(mktemp -d)"
  cd "$task_repro_dir"
  dvc init --no-scm
  cat > params.yaml <<'YAML'
start: 20200101
eval:
  filter_limitup: false
YAML
  dvc run -n get_base_dv -p start -o base.txt "echo base > base.txt"
  dvc run -n eval -p eval.filter_limitup -o eval.txt "echo eval > eval.txt"
  dvc status --show-json
  printf 'y\n' | dvc commit get_base_dv
  dvc commit -f eval
  dvc status --show-json
  dvc repro -P
  dvc status --show-json
)
~~~

静态预期，未经实际确认：

- 原 base 的首次及后续 status 可能出现 {"eval": [{"changed deps": {"params.yaml": {"eval.filter_limitup": "new"}}}]}；get_base_dv 未改动却仍出现 changed dependencies 确认。给它输入 y 只是让临时复现继续，日志中的误报本身是观察点。
- 合理修复后，各次无变更的 --show-json 应为 {}；get_base_dv 的提交不应要求确认参数变化。repro 在无变更时应跳过；不以是否出现某个特定缓存日志作为唯一标准。
- 在临时样例中继续验证 false→true 产生 modified、提交新值后恢复干净；删除跟踪键产生 deleted；锁文件尚未记录的新增跟踪键仍是 new；修改独立未跟踪字段不使参数依赖变更；删除参数文件仍报告 deleted。对当前解析器支持的其它假值可逐项重建同样小样例，验证与“键缺失”不同。这些也是建议，未执行，且不要求改动仓库测试。
- 这些本地小文件建议无法证明原作者 WSL/9p 场景或完整业务流水线已经重放成功。

**实际阅读范围、未查项与暴露记录**

全文静态打开：

- 角色卡：ROOT/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/roles/public_reader.md。
- PUBLIC_DIR 下：user_prompt.txt、public_bundle.json、environment_brief.md。
- base/dvc/dependency/{param.py,local.py,base.py,__init__.py}；base/dvc/repo/{commit.py,status.py}；base/dvc/stage/{loader.py,cache.py}；base/dvc/command/{status.py,commit.py}。
- base/tests/unit/dependency/test_params.py；base/tests/func/{test_commit.py,test_status.py,conftest.py}；base/tests/conftest.py；base/tests/remotes/__init__.py。
- base/{setup.py,setup.cfg,pyproject.toml,CONTRIBUTING.md}。

按行节选打开（未声称全文审阅）：

- base/dvc/stage/__init__.py:L205-L535、L537-L574；base/dvc/output/base.py:L1-L260；base/dvc/stage/serialize.py:L1-L175。
- base/tests/unit/stage/test_loader_pipeline_file.py:L1-L205；test_cache.py:L1-L105；test_serialize_pipeline_lock.py:L55-L113。
- base/tests/func/test_run_multistage.py:L175-L315；test_repro_multistage.py:L455-L527。
- base/tests/dir_helpers.py:L48-L120、L245-L310；base/README.rst:L85-L158、L198-L208。
- base/dvc/command/run.py:L1-L82、L88-L141、L212-L235；repro.py:L120-L140；init.py:L25-L61；data_sync.py:L292-L374。

另有仅文件名/命中行检索：

- 仅在本题 base 内用 rg --files 查找参数、状态、提交、安装/测试配置及 helper 文件；路径枚举不表示已阅读所有文件内容。
- 对 base/dvc/dependency、base/dvc/stage、base/dvc/output/base.py、base/dvc/output/local.py、base/dvc/dvcfile.py、base/dvc/cli.py、base/dvc/command/base.py 及相关命令文件检索类名、变更判断、参数和选项；输出中涉及 stage/utils.py、stage/run.py 等，未逐一阅读全文。
- 对 base/tests/func、base/tests/unit/stage 检索参数相关用例。搜索也命中过 pytest.mark.parametrize 等无关签名；其中 test_repro.py、test_stage.py、test_lockfile.py、params/test_show.py、params/test_diff.py、test_serialize_pipeline_file.py 及其它函数签名命中项未作完整审阅。
- 对 base/tests/remotes/*.py 只检索顶层 import/from 与 autouse，对 base/tests/__init__.py 只见 import 命中。没有打开任何密钥 fixture 内容，也没有运行远端 helper 或服务。
- 少数路径猜测返回不存在，包括 dvc/stage_cache.py、tests/func/test_run.py、tests/func/run/、tests/remotes.py、tests/dir_helpers/；随后在本题 base 内定位到实际文件。这不是关于真实运行资产缺失的结论。

未查及未做：

- 未读取 private、gold、history、任何既有质量报告、批次聚合、manifest、inventory、其它题或角色卡父目录材料；未读取 base_identity.json 或共享镜像 Git 历史。
- 未网络搜索、访问外链、下载、安装、启动容器/SSH、使用 GPU/模型服务或 quota/reset；未导入执行项目代码、运行测试/构建/业务脚本。
- 未修改 base 源码、测试、评分配置、旧批次或提交。只将本记录写入协调者指定的 public_read.md；保存后不回写。
- 本题私有内容暴露：本角色没有发现或读取私有材料。可见任务元信息限于单题标识、公开目录、角色规则和指定输出路径；这是一项协作范围记录，不是文件权限隔离证明，也不是预训练无污染证明。
- user_prompt.txt 仅是静态渲染，base 导出不是完整运行容器；实际模型消息、运行资源、解释器/依赖、工具授权及开发条件都仍未验证。
