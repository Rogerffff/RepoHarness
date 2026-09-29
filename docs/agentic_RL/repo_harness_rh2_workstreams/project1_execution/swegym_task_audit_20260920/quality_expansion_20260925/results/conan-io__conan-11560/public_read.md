# conan-io__conan-11560 公开静态阅读

## 题面先验（阅读源码前形成）

目标：让 Bazel generator 生成的多库包可用于链接；题面用 Linux libcurl 依赖 OpenSSL 举例，称 libcrypto.a 与 libssl.a 链接顺序错误，并明确要求生成的每个示例 `cc_import` 增加 `alwayslink = True,`。合理旧行为包括继续生成每个库的导入目标、保留正确库路径、保留包级依赖入口，以及兼容单库和其他原有包类型。

约束：这是生成器修复，而非直接编辑某次生成的 OpenSSL BUILD 文件。题面没有限定实现文件或测试方法，也没有提供版本化复现工程。`visibility = ["//visibility:public"]` 用于单独使用 libcrypto 被作者明确留作可能的另一问题，不能认定为本题必需变更。任务卡要求的静态审查和工具限制不是原题额外开发要求。

初始疑义：题面的 “bazel generator” 对应哪个实现；属性适用于所有 `cc_import` 还是仅静态库；是否存在不应变化的无库/共享库行为；仅改变顺序能否满足作者明确给出的输出；如何以无需真实 OpenSSL 的公开测试确认生成结果。

## 公开源码和旧测试所能消解的事项

以下源码路径均相对本题公开包 `runs/swegym_quality_expansion_20260925/public/conan-io__conan-11560/base/`。

- 生成器定位清楚：`conans/client/generators/__init__.py:134–136` 将 `BazelDeps` 解析为 `conan.tools.google.BazelDeps`；`conan/tools/google/__init__.py:2` 导出实际类。`conan/tools/google/bazeldeps.py:17–44` 为 host dependencies 生成并保存 `<generators_folder>/<dependency.name>/BUILD`，因此可在共用生成模板解决问题，无需 OpenSSL 专名分支。
- `BazelDeps._get_dependency_buildfile_content`（58–180）含两个模板分支。62–67 的普通 `cc_import` 只有目标名及 `library_type` 对应路径；该路径行当前没有尾逗号。69–75 的分支输出 `interface_library` 和 `shared_library`。两处都没有 `alwayslink`。追加参数时应确保 Starlark 参数间有逗号。
- 151–176 根据 `options.shared` 选择 `shared_library` 或 `static_library`，155–165 将有 `.lib` 与 `.dll` 配对的库放入独立映射。199–233 负责匹配库文件并排除目录，支持多种扩展名及完整 basename；本题没有要求改变此发现机制。
- 109 行先聚合 components，155 行遍历聚合后的 `cpp_info.libs`；模板为每项建立 `<lib>_precompiled`，77–105 再建立公开包级 `cc_library`，把各导入目标及传递依赖放入 `deps`。公开逻辑已支持“多个库的表示”，缺口是题面指定的导入属性；不能从这里证明 Bazel 的最终链接顺序或已修复真实故障。
- 111–112 对无库且无 include 目录的包返回空；只有头文件时保留 `cc_library`。build dependencies 用 `filegroup`（46–56），不是本题 `cc_import` 目标。
- 旧单元测试 `conans/test/unittests/tools/google/test_bazeldeps.py:29–96` 用空文件模拟单库，检查 defines、system libs、basename 和包级依赖；99–152 检查传递依赖。这些不检查 `alwayslink`，因此即使全过也不能独立证明本题修复。
- 同文件 155–176 精确比较只有头文件的输出；179–227 精确比较 `.lib`/`.dll` 共享导入输出。若决定所有导入分支均增加属性，该共享库预期需要随合理规格更新；仅针对静态导入则可保留该旧预期。230–287 检查主依赖文件及 build dependency 的 filegroup。
- 旧集成测试 `conans/test/integration/toolchains/google/test_bazel.py:7–78` 覆盖空包、相对 include 路径、库名同名目录排除，全部通过本地 recipe / 空库文件检查生成结果，不需要真实编译。
- 旧功能测试 `conans/test/functional/toolchains/google/test_bazel.py:86–257` 的 `test_transitive_consuming` 虽使用 OpenSSL 名字，但实际建立仅含一个 `openssl` 库的玩具包，消费生成的 zlib；它不是题面 libcurl→真实 OpenSSL 双静态库的复现。它带 Linux 限制和 bazel 标记，并执行 CMake/Bazel 构建。

## 合理实现范围与剩余不确定性

最低明确要求是：对多静态库包的每个生成 `cc_import` 输出合法的 `alwayslink = True`，同时保留目标名称、库文件位置和包级依赖。单纯重排 `cpp_info.libs` 或硬编码 OpenSSL，不能满足题面明确指定的通用输出方案。

可接受的非唯一设计包括：在静态导入分支条件输出该属性；或按题面 “cc_import libs” 的宽泛文字在两个模板分支统一输出该属性。公开题面的静态示例未明确解决共享库范围，已读包也没有 Bazel `alwayslink` 的权威语义说明，因此不能据此把任一选择冒充唯一指定答案。统一添加会触及已有共享库精确输出，需相应验证；仅静态条件则更窄，但仍应明确解释范围选择。属性顺序、模板上下文组织及测试放在单元层还是纯 Python 集成层没有唯一要求。

建议新增最小回归场景：本地假包声明 `cpp_info.libs = ["ssl", "crypto"]`，提供对应空 `.a` 文件，只生成 BUILD 并逐个检查两个导入块均含属性、正确路径及包级 deps。空文件足够验证生成文本，不能验证链接。真实链接复现仍需有跨档案符号依赖的可编译静态库、Bazel/rules_cc 及编译器；链接是否成功、跨平台兼容性与对产物体积等影响均未实测。题面未提供具体 libcurl/OpenSSL 版本、Bazel 版本或完整报错，不能把其“All”字样当已验证版本矩阵。

## 开发需求表（命令仅为后续建议，本轮均未执行）

命令应在实际 actor 的已确认源码根目录执行；`/testbed` 仅是计划题面的路径声明。

| 操作或资产 | 公开依据 | 当前实际证据 | 最小公开验证命令与预期 |
| --- | --- | --- | --- |
| 取得真实源码初态及可编辑权限 | 题面 commit；`environment_brief.md` 明示静态导出与 actor 不同 | base 身份声明为 `345be91a038e1bda707e07a19889953412d358dc`；实际 HEAD、diff、actor 用户及写权限 unknown | `git rev-parse HEAD`、`git status --short`；核对规定基线及初始差异，另以 actor 工具确认允许修改的路径 |
| 定位修改模板 | `bazeldeps.py:58–180` | 公开文本实际已读；actor 对应内容 unknown | `rg -n 'cc_import|alwayslink|library_type' conan/tools/google/bazeldeps.py`；修复后静态库导入应含题面属性且参数分隔合法 |
| Python 与测试依赖 | `setup.py:55` 声明 Python >=3.6；README 测试说明；开发依赖列表；模板导入 Jinja2 | 文件声明可见；解释器、依赖安装和实际源码导入位置 unknown | `python --version`、`python -m pip check`；再运行下面选定单测以验证能实际导入和执行；前两项不能单独证明兼容 |
| 临时文件/目录与纯 Python 单元验证 | 旧单测以 `temp_folder`、`save` 创建空 `.a`/`.lib`/`.dll` | 测试方案存在；actor 临时目录可写性 unknown | `python -m pytest conans/test/unittests/tools/google/test_bazeldeps.py -q`；预期原有行为通过；新增双静态库逐块属性断言后才可证实本题输出 |
| Conan 集成生成与可写缓存 | 旧集成测试 `TestClient` 的 create/install 及 BUILD 读取 | 本地 recipe 方案可见；实际 HOME、缓存和工具权限 unknown | `python -m pytest conans/test/integration/toolchains/google/test_bazel.py -q`；预期空包、相对路径及目录排除测试通过；可加入双静态库生成回归 |
| 完整编译链接工具链 | 题面 Linux libcurl/OpenSSL 链接场景；旧功能测试 86–257 | Bazel、rules_cc、CMake、编译器、库资产、网络/缓存及版本均 unknown | `bazel --version`、`cmake --version`、`c++ --version` 可核对工具入口；旧 `python -m pytest conans/test/functional/toolchains/google/test_bazel.py::test_transitive_consuming -q` 只验证已有玩具传递消费。题面故障仍需额外双静态库复现工程后运行其 `bazel build`，预期消除对应未解析符号故障 |

生成文本测试无需真实 OpenSSL、libcurl 或 Bazel 运行；完整链接测试的外部资源需求不能上推为最小开发必需条件，也不能由导出包不含二进制判定 actor 镜像缺失资产。

## 阅读范围与边界

完整阅读：派发卡、`roles/public_reader.md`、本题 `user_prompt.txt`、`environment_brief.md`、`base_identity.json`；`base/conan/tools/google/bazeldeps.py:1–277`；`base/conans/test/unittests/tools/google/test_bazeldeps.py:1–287`；`base/conans/test/integration/toolchains/google/test_bazel.py:1–78`；`base/conans/test/README.md:1–108`；`base/pytest.ini`；`base/conans/requirements_dev.txt`。

局部阅读：功能 `test_bazel.py:85–257`；README 的 rg 返回区段，重点 128–225；setup.py 的 `python_requires` 与 `install_requires` 周边；生成器注册和 google 导出中的 Bazel 命中行。另对本题公开包做文件名枚举，以及 Bazel 相关路径/符号搜索；枚举输出被截断，未据其作穷尽性结论。

未读：`public_bundle.json`、其余源码正文、测试工具内部与完整测试配置、仓库外文档、任何私有包/历史/gold/隐藏测试/其他题/角色结果。没有追随链接，没有执行或导入项目、运行测试、安装下载或修改题目。实际 actor 的用户消息、system message、public hints 交付、工具呈现、初态、环境资产与权限均 unknown；静态 base 不代替这些运行事实。本报告不作成功率、训练资格或实际 actor 资格结论。
