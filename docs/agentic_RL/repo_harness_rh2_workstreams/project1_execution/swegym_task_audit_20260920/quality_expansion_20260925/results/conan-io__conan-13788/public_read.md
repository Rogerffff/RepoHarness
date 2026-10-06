# conan-io__conan-13788：独立公开阅读

本报告仅作公开材料静态判断，没有运行、导入或修改 Conan，没有执行测试、安装、网络访问，也未读取私有测试、gold、历史或其他角色结果。下文源码路径均相对于 `PUBLIC_DIR/base/`；PUBLIC_DIR 为 `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/conan-io__conan-13788`。这份 base 是静态导出，不是实际 actor 工作树。

## 先由题面建立的目标、合理旧行为和疑义

依据 `user_prompt.txt:1–13`：用户报告 Conan 1.59 生成的锁文件含同名构建依赖的两个版本，一个来自 profile，另一个来自 recipe；询问是否应允许，以及使用锁文件安装时选择哪个版本。公开修复目标应为使这类版本选择可解释、一致，并消除不正确的重复或歧义，而非仅改输出文本。

在读源码前，合理旧行为的候选包括：profile 有明确覆盖优先级，或不同构建用途保留各自版本；锁文件应准确保存有效依赖，安装应遵守相应锁定引用。用户“预期禁止”的说法是问题中的预期，不足以单独确定所有同名版本都须报错。

题面没有提供 recipe、profile、锁文件内容、创建与安装命令、是否同时使用 host/build profile、是否调用 `force_host_context`/`test_requires`、同名节点是否属于同一父节点、版本是否来自范围以及缓存状态。故无法仅凭题面确定具体复现或全局去重规则。题面声明 `/testbed` 和 commit `c1b3978914dd`；它们不是本轮已验证的实际工作目录或 HEAD。

## 公开代码与旧测试消解的部分

1. **同一上下文的 profile 覆盖是已有行为。** `conans/client/graph/graph_manager.py:21–43` 的 `_RecipeBuildRequires` 用 `(name, context)` 存储引用，支持属性形式的 `build_requires`、`tool_requires`；`310–327` 还执行 `build_requirements()`，把 `test_requires()` 转成 host 上下文。`336–367` 根据有无 build profile 决定默认上下文，并将匹配的 profile 引用替换同键 recipe 引用。`conans/test/integration/build_requires/build_requires_test.py:36–50,334–359` 的 `test_profile_override` 明确断言：recipe 的 Tool/0.1 或 Tool/0.2 被 profile 的 Tool/0.3 覆盖，且 profile 版本范围也可解析到 0.3。因此一律因两处声明不同版本报错会破坏公开旧测试。

2. **锁文件出现同名多节点本身不是错误证据。** `conans/model/graph_lock.py:279–328` 为依赖图节点建立锁定节点、用目标节点 ID 记录依赖边；`251–276` 序列化引用和 context。`conans/test/integration/graph_lock/graph_lock_build_requires_test.py:52–92` 的 `test_package_both_contexts` 明确保留 protobuf 在 host 和 build 的两个节点。`179–194` 的 `test_multiple_matching_build_require` 让 pkg1 依赖 cmake/1.0、pkg2 构建依赖 cmake/1.1，创建锁文件后成功安装明确指定的 cmake/1.1，并拒绝该安装入口的版本范围。不能把“整份 lockfile 中同名只能一个版本”作为合理通用修复。

3. **存在值得验证的上下文丢失风险。** `conans/client/graph/graph_builder.py:90–101` 为每项构建依赖设置 `build_require_context`，随后调用 `graph_lock.lock_node`，旁有 “TODO: Add info about context?”。然而 `conans/model/graph_lock.py:535–554` 将当前父节点的锁定依赖按 `ref.name` 构造字典，读取时也只按名字；若该父节点的构建依赖 ID 列表包含同名且不同上下文的节点，字典后遇到的同名项会替换先前项，两个请求可能都取得同一锁定引用。`conans/model/requires.py:28–32` 说明 `Requirement.lock` 随后实际替换 `ref`、`range_ref` 和锁定节点 ID。这是从代码直接得到的局部行为，不是运行复现；未证明题面一定命中了该路径，也未证明最终安装输出。

4. **上下文在建图阶段已有区分。** `graph_manager.py:378–395` 分开递归 build 与 host 构建依赖，并区分 recipe 与新加 profile 依赖的递归；`graph_builder.py:107–113` 用 `build_require_context` 决定上下文切换。修复若涉及锁定匹配，应保持该区分，不能仅删掉合法节点掩盖问题。`graph_lock.py:566–582` 的已锁构建依赖声明检查也只对包名集合检查；这说明校验边界，但本报告不据此扩大为另一个必须修复的问题。

5. **锁文件还保有其他必要约束。** `graph_lock_build_requires_test.py:196–242` 验证 profile 与 recipe 中不同名构建依赖均生效，以及原先由环境条件声明的 recipe 构建依赖消失时须报 locked requirement not found。`build_requires_test.py:317–332` 表明已有二进制包时构建依赖可能不需要重新安装，因此“每次安装都出现全部构建工具”也不是合理验收标准。

## 合理实现范围与剩余疑义

公开证据最支持的方向是：保持现有同上下文覆盖规则；使锁文件创建、消费能按父节点及有效上下文准确关联构建依赖；允许不同上下文或不同消费者确有需要的同名多版本。若复现确认上下文错配，可在锁定构建依赖时使用名字与上下文联合匹配，或先按请求上下文筛选锁定节点再按名字匹配。这两种结构都是公开代码可支持的实现选择，不要求特定补丁形式，也未参考 gold。

仍须验证：题面冲突是否同父节点、是否跨上下文、profile 的匹配模式、单 profile 的兼容语义、旧锁文件未携带 context 时的兼容策略、多个 profile 模式都匹配时的优先级、版本范围/别名/修订的相关边界。本次没有读完相关逻辑，不能替这些条件设定新规范。对于“实际会安装哪个版本”，仅能给条件结论：正常同上下文覆盖路径使用 profile 引用；若同父节点锁定列表出现同名多项，现有名字字典会留下列表中最后遇到的一项。没有用户锁文件和运行记录，不能给具体版本答案。

## 开发需求表

以下命令仅是后续 actor 环境中的建议验证步骤，本轮全部未执行；相对路径命令应在经核验的项目根目录运行。资产是否存在及命令能否运行均不能由静态 base 推断。

| 操作 / 资产 | 公开依据 | 实际证据或 unknown | 最小公开验证命令与预期 |
| --- | --- | --- | --- |
| 确认真实源码起点和允许编辑范围 | user_prompt.txt:1；environment_brief.md:2–7 | 仅读到静态导出；实际 HEAD、初始修改、actor 消息与权限均 unknown | `pwd`、`git rev-parse HEAD`、`git status --short`；预期定位源码根与完整提交、记录初始修改，而非直接假定 `/testbed` 就绪 |
| Python、项目和测试依赖 | README.rst:148–154；三份 requirements；测试 README:11–15,24 | requirements 声明可读；实际 Python 版本、环境激活、依赖安装、导入来源 unknown | `python --version`、`python -m pip check`、`python -m pytest --version`；预期解释器和测试框架可用、依赖无冲突；这些仍不能单独证明导入的是正确源码 |
| 可写临时缓存及工作目录 | `conans/test/utils/tools.py:399–424` 的 TestClient 创建缓存和 current_folder | 实际 HOME/TMP、磁盘、UID、读写权限 unknown | 后述最小 TestClient 测试应能创建与写入缓存、recipe 和 lockfile，不应出现权限/空间错误 |
| 保持 profile 覆盖 | `build_requires_test.py:334–359` | 旧断言已读，未运行 | `python -m pytest conans/test/integration/build_requires/build_requires_test.py -k profile_override -q`；预期各参数形式仍只采用 Tool/0.3，保持范围解析 |
| 保持合法多节点与多版本 | `graph_lock_build_requires_test.py:52–92,179–194` | 旧断言已读，未运行 | `python -m pytest conans/test/integration/graph_lock/graph_lock_build_requires_test.py -k 'package_both_contexts or multiple_matching_build_require' -q`；预期合法 host/build 节点保留且明确版本可安装 |
| 公开最小复现与新增回归 | graph_manager 的上下文键、graph_builder 的上下文属性、graph_lock 名字键 | 用户复现资产未提供；实际根因 unknown | 在授权开发阶段用 TestClient 创建纯 Python 空 recipe，准备 tool/1.0、tool/2.0，以及 recipe 强制 host 与 profile 默认 build 的同名依赖；调用 `lock create conanfile.py -pr:h=host -pr:b=build --build --lockfile-out=conan.lock`，再 `install . --lockfile=conan.lock --build`；预期各父节点边、context、ref 与无锁图一致，两个有效版本各归其上下文。同上下文变体预期 profile 覆盖。需先生成这些公开 fixture，命令并非现成可执行复现 |
| 相关锁定回归 | `graph_lock_build_requires_test.py:146–242` | 静态测试及断言可读，实际执行 unknown | `python -m pytest conans/test/integration/graph_lock/graph_lock_build_requires_test.py -q`；预期保留构建依赖、不丢失不同来源的依赖，缺失原锁定声明仍有预期错误 |

最小复现不需要真实 C++ 编译器、GPU、远端仓库或真实包下载：公开测试文档将 integration 定义为纯 Python，已读测试用本地生成并导出的空 recipe。依赖若尚未安装，其供应方式与网络权限仍 unknown；不把网络访问列为题目必需条件，也未执行安装。

## 真正阅读的范围与未读范围

已完整读取派发卡、`roles/public_reader.md`、`user_prompt.txt:1–13`、`environment_brief.md:1–10`。先列出 PUBLIC_DIR 文件路径；输出被截断，文件路径清单不代表阅读所有文件。

源码与测试实际展开阅读范围（均相对于 base）：

- `conans/client/graph/graph_manager.py:1–60,310–420`，重点 `_RecipeBuildRequires`、`_get_recipe_build_requires`、`_recurse_build_requires`；另对该文件检索 build_requires/build_requirements。
- `conans/client/graph/graph_builder.py:73–135`，重点 `extend_build_requires`；另检索 extend_build_requires/lock_node。
- `conans/model/graph_lock.py:250–329,508–588`，重点序列化、`GraphLock.__init__`、`lock_node`、`check_locked_build_requires`；另检索 build_require/context/profile/override，只读到命中行的其他部分不视为完整上下文。
- `conans/model/requires.py:1–92`，重点 `Requirement.lock` 与上下文属性；另检索 context/force_host_context。
- `conans/test/integration/build_requires/build_requires_test.py:1–100,270–405`，重点 fixtures、`test_build_requires`、`test_profile_override`；末端其他函数仅部分读到。
- `conans/test/integration/build_requires/profile_build_requires_test.py:1–210`，包括重复、递归、profile 与 build mode 测试；210 之后未读。
- `conans/test/integration/graph_lock/graph_lock_build_requires_test.py:1–94,146–245`；94 行和 245 行仅触及下一函数声明，没有读完 `test_package_different_id_both_contexts` 或 `test_test_package_build_require`。
- `conans/test/utils/tools.py:365–426,572–592`，以及 TestClient/临时目录等定位命中行；缓存复制、run_cli 等实现未展开。
- `conans/test/README.md:1–108`（全文）；`README.rst:128–156,182–225`，另检索测试/依赖关键词；`conans/requirements.txt:1–16`、`requirements_server.txt:1–4`、`requirements_dev.txt:1–7`、`pytest.ini:1–3` 全文。

另外在 build_requires 集成测试目录及 graph_lock 指定文件进行过限定关键词搜索，只把实际命中行作为定位材料。曾尝试不存在的 `conans/test/integration/lockfile` 路径，收到不存在错误，随后从公开文件清单定位到 graph_lock；这仅是静态目录命名差异，不是 actor 缺资产证据。

未读：public_bundle.json、base_identity.json；其余大部分源码、文档和旧测试，未展开的 profile 解析、完整依赖图扩展、CLI 安装入口、测试初始化与环境配置；全部私有材料、历史、其他题、其他角色输出及外部链接。实际 actor 的用户消息/system message、HEAD/diff、源码导入、工具/资产/权限和任何运行结果均 unknown。本报告不判断成功率、训练资格或实际 actor 是否具备执行条件。
