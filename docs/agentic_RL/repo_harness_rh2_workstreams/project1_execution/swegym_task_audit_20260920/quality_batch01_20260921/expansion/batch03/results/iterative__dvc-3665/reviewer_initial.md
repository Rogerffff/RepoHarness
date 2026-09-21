# iterative__dvc-3665 独立复核初判（封存后不回写）

记录时间：2026-09-20 21:31 UTC / 2026-09-21 05:31 SGT。B3 DVC fresh 独立 reviewer；权威 ROOT=`.`，路径均相对此根。`state=needs_review, scope=static_review, intended_use=development_diagnostic`。

**独立结论：题目是明确的跨平台配置序列化问题，但原验收含高影响的实现耦合和目标平台漏测，不宜把原版 reward 直接作为修好题面问题的依据。** 四个 F2P 全部调用新私有方法 `_to_relpath`，题面与 base 都没有这个 API 要求。等价地在原 `_save_paths` 闭包内正规化路径的合理解，会因没有该方法而被拒。反过来，仅添加未接入真实保存路径的 helper，静态上可通过这四项和 Linux 旧行为，却仍不修 Windows 保存。后一项目前是有具体依据的静态漏测候选，未执行 RH2 反例；不把它写成已得分。

## 阅读与暴露

本题先读 prompt、bundle、base_identity，再读 base `dvc/config.py` 全文、`dvc/command/cache.py`、PathInfo 实现，然后读 private 七份原件；environment_brief 与已读 6954 版本 SHA256 同为 `428a617a33ab868848d32d8be9af7b5f53b5fd406c1446005290bf433bb79628`，复用其说明。已见 environment_record 内 gold/noop 成功/失败摘要，并复读 run_refs 原日志，不称无结果盲审。已读 test.patch 全部增改、gold 全文、全部 F2P、相关18 P2P与完整被执行的 cache/remote 旧测试、基础 fixture、公开 Config/PathInfo 回归。此时已见6954原件及其 gold；未见任何题的 public_read/主审初稿/旧结论/card/screening_record/review。未追 environment_record.analysis 或 inventory.analysis_reference。只读与 stdlib 文本处理，没有项目导入、测试、安装、网络、Docker或新 CPU 实验。

## 1. 公开要求与合理实现

题面比较 Windows `dvc cache dir ..\xyz` 保存 `..\..\xyz` 与 Linux 保存 `../../xyz`，希望避免 Git 中无意义变化；并说明 Windows 能读 POSIX 形式。公开 CLI `dvc/command/cache.py:7–11,53–57` 明确相对输入相对 cwd 解析、输出相对配置文件；`Config.edit:342–357 → _save_paths:315–326 → _map_dirs:329–331` 是真实写入链。旧闭包直接返回本机 `relpath`，在 Windows 得反斜线，静态根因与题面吻合。这里不需要服务、数据集或新依赖。

合理实现包括在原闭包中、保留 URI 早返回及 RelPath 条件后，将得到的本地路径用现有 `PathInfo(...).as_posix()` 正规化；无需新增 `_to_relpath`，无需改变外部接口或配置布局。`PathInfo:30–43` 依据 os.name 选择 PureWindowsPath/PurePosixPath，现有公开 `tests/unit/test_path_info.py:65–91` 已用 mock os.name 覆盖 Windows 相对路径与不折叠多层 `..`。该公开知识足够设计与 gold 不同结构的修复。

## 2–3. 完整测试、F2P/P2P 与需求映射

test.patch 三个路径：cache 功能测试的导入合并（无语义），绝对/相对缓存配置断言改为斜线；remote 相对路径断言同改；新增17行 unit/test_config.py。新增测试无专用 fixture，参数通过导入时 os.getcwd() 得到当前 cwd；其唯一断言直接调用 `Config._to_relpath(os.path.join('.', 'config'), path)`。这里传入的是目录 `./config`，符合新 helper 的内部签名，却不是原公共配置文件 API。

四个冻结 F2P 都逐项读过：

| F2P | 断言 | 与公开要求关系 |
| --- | --- | --- |
| `tests/unit/test_config.py::test_to_relpath[cache-../cache]` | 新 helper 将相对 cache 变 ../cache | 相对保存语义已有；新 helper 名/签名无公开依据 |
| `...test_to_relpath[../cache-../../cache]` | 新 helper 将 ../cache 变 ../../cache | 同上；Linux 正斜线输入不触发缺陷 |
| `...test_to_relpath[/testbed-/testbed]` | 绝对 cwd 原值（replace 后仍 /testbed） | 合理旧行为，但绑定 /testbed 节点ID；不是 Windows separator 检验 |
| `...test_to_relpath[ssh://some/path-ssh://some/path]` | URI不变 | 合理回归；同样强制新 helper |

受影响行为与其余执行范围：

| 公开要求/旧行为 | 对应测试/依据 | 覆盖判断 |
| --- | --- | --- |
| 写出 POSIX 相对 cache.dir，并仍可缓存数据 | 修改后的 `TestCmdCacheDir::test_relative_path`；base cache.py:160–178 | 有功能断言但此节点**不在18个冻结 P2P**；历史Linux下noop亦通过，未验Windows目标分支 |
| 绝对缓存路径仍有效 | 修改后的 `TestCmdCacheDir::test_abs_path` | 在P2P；Linux输入本就用 `/`，无法证明Windows正规化 |
| local remote相对url统一格式 | 修改后 `TestRemote::test_relative_path`；_map_dirs共用 | 在P2P；同样未模拟Windows。可视共享保存器的合理回归，不必因题面只说cache就判扩需求 |
| URI/remote引用不改写 | `TestRemote::test_referencing_other_remotes`、`TestExternalCacheDir::test_remote_references`；配置regex | 在P2P，ssh/remote scheme按原样保留有直接断言 |
| 配置层级及非法键拒绝 | `tests/func/test_config.py` 全文 | 公开旧测试已读，但该文件不在官方执行命令；层级回归不等于已计分 |
| Windows drive/UNC、Windows相对路径保存、POSIX合法反斜线文件名 | PathInfo与relpath代码 | 新验收没有这些输入或平台切换；不能把字符串后置replace视为真实Windows已测 |

18个P2P均读其测试体：cache端 `TestCache::{test_all,test_get}`、`TestCacheLoadBadDirCache::test`、`TestExternalCacheDir::test_remote_references`、`TestCmdCacheDir::{test,test_abs_path}`、`test_default_cache_type`；remote端 `TestRemote::{test,test_relative_path,test_overwrite,test_referencing_other_remotes}`、`TestRemoteRemove::test`、`TestRemoteDefault::test`、`test_remove_default`、`test_show_default`、`test_dir_checksum_should_be_key_order_agnostic`、`test_modify_missing_remote`、`test_remote_modify_validation`。它们分别保护缓存读取、错误处理、配置管理/引用和checksum等旧行为；不能以18项数目证明Windows分支。

两个被执行文件内另有11个非参考节点，包括最贴近题面的 cache relative、外部/共享缓存、大小写remote、传输失败及顺序；已通读。tests/basic_env.py 的本地临时目录和 no_scm DVC 初始化、tests/dir_helpers.py 的 tmp_dir/dvc/SCM fixture、tests/conftest.py 的 mockssh 导入/日志/连接池均已核。没有拿 mock 的传输失败当本题需要真实SSH服务的证据。

## 4. gold 与旧行为

gold 对 config.py 做导入整理、新增 `_to_relpath`、原闭包改为 partial；其逻辑先放过 URI，保留 RelPath/相对输入的 relpath，再对本地结果调用现有 PathInfo.as_posix。它接入真实 Config.edit 保存链，静态上能修题面并避免 Linux 把合法反斜线字面字符无条件变路径分隔符。未发现必须另交文件或给定普通路径上的 gold 不完整；绝对路径输出也正规化属相关扩展。

已沿 `_load_paths` 的 RelPath 标记、层级合并/validate、remote `_map_dirs`、`dvc.utils.relpath:315–324`（跨驱动器保留路径）及 PathInfo 查回归。已有不同盘符/大小写处理的所有边界未穷举；无本次 Windows 实测，不能宣称 gold 跨平台全部通过。纯名称重构并非修复需求本身，故隐藏 helper 断言不是“公开读者读代码即可必然知道”的合同。

## 5. 版本、原日志、分账

base=`a2de48bdfbba80a7e41e96a44c67d51ff36f0810`、tree=`96a34b54698c9d2acb4c8d2ec1b1091440ecd7f3` 与grading一致；gold SHA `94e474298491aaa1142674a344416132ac19c5ed44124c1d932cd4e96b2969e4` 与原 ledger:1 candidate一致。复用协调者材料验收，未再验全部blob。

原证据均在 `runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3665/`：

- noop ledger:1 开始于2026-09-19 07:41:15 UTC（15:41:15 SGT）；`noop/eval_logs/...4ffdaade.eval.log:585–609` 记录editable安装成功、install_rc0、Python3.8.19/pytest7.4.4/Linux、执行三个patch文件；630–687 四次均是 `AttributeError: Config has no attribute _to_relpath`；1713–1746有29 pass/4 fail。F2P 0/4，P2P fail0/18，reward0。
- gold ledger:1 开始于07:41:52 UTC（15:41:52 SGT）；`gold/eval_logs/...1392f999.eval.log:650–674` 安装成功、同一命令与环境；1705–1738 全33通过，test_rc0；F2P4/4、P2P fail0/18、reward1。
- 两者执行节点=33，diagnostics/ledger `num_parsed_tests=42`，不能写成42个测试。冻结 parser `parse_log_pytest:44–56` 对以 ERROR 等开头的任何日志行按第二token建键。原log额外的9个非测试token为 `configuration, dir, dvc.cli:cli.py:93, dvc.remote.base:base.py:304, dvc.remote.base:base.py:568, dvc.remote.local:local.py:540, dvc:main.py:51, failed, the`。这是对日志文本的静态计数；没有运行项目parser。22个冻结参考均有对应真实摘要节点，missing/skipped=[]；这9键未冒充本题参考通过。
- gold/noop画像ID均 `sha256:27e0f845f9702c664a23787619c39469b0ac3bb2c98216e79ed49f7f8558bd7a`，script digest `sha256:3b598e340e2810c572cbcca3614e0fd8403c81a6952e2527c13ffe0eb559c490`。安装/测试为rh2grader/54322、离线、2CPU/4GiB、shm64MiB；补丁apply用户另为agent/54321。导入观察为/testbed/dvc/__init__.py。env_qualification仍absent；cleanup/driver_close有完成记录。历史replay不是正式actor求解会话，也不是本轮重跑。

原输入 `recipes/iterative__dvc-3665.json` 的新安装是 `pip install -e '.[all,tests]'` 并保留其rc；共用wrapper精确替换安装段，逐run recipe只是输出。setup.py:49–133,147–159 确有all/tests extras；COPY wheel是准备资产手段，实际安装成功由上列log支持。inventory仅取本题exact对象及此前共用部分；目标镜像/原wheel payload在本次执行节点未验，不能直接重放旧/work路径。

## 6. 开发条件

| 需要 | 公开依据 | 历史条件/当前缺口 | 建议最小验证（未执行） |
| --- | --- | --- | --- |
| 可导入工作区 Config/PathInfo与窄测试 | setup.py依赖；tests/conftest含mockssh导入 | 历史grader安装成功；actor激活/可写前缀/工作区导入未知 | actor shell核UID/PATH/python/dvc.__file__，窄跑公开PathInfo或cache测试 |
| 本地缓存CLI与配置文件 | cache CLI、Config.edit | 小临时目录、DVC本地初始化，无新下载/外部服务 | 临时repo执行cache dir相对路径，读取ConfigObj及cache实际写入 |
| 观察Windows语义 | 题面Windows/Linux比较；公开PathInfo测试已有os.name参数化 | Linux历史测试未含Windows；不应要求解题时远程Windows服务或泛开放公网 | 固定CPU诊断使用真实Windows，或明确隔离且完整的ntpath/WindowsPathInfo语义替身；不得只改os.name却仍用posixpath假称WindowsCLI实测 |
| 离线依赖/镜像 | input recipe与build pins | 本地原context未保存；派生镜像当前可用性未知 | 准备阶段恢复并固定依赖，按角色验证，无需解题期网络 |

合法源码修复仅需config.py，公开禁止改测试指令不阻塞；“全部测试都会恢复”的旧提示不能代替精确文件规则。

## 7. 投影与计分边界

复用本 reviewer 已静态读取的冻结 dvc.tar.gz 真实调用链：replay adapter SHA `031046ba444e26a91643ce988c3855e80acb1b4cf90408235d61ff35d87fb896`，face `31ff5145dfa8b71b2a183b14f8a5fbfe4572b71911af54023c8168e534e4f8a3`，spec_vendor `8e0037b27c87268ed7df97ef64d261d0e6dac7375bc85fd5badd0fecdb94d41d`，projection `5ef126803e93e3606123a4aef4389d35bad0551a622020d1dd22f0db32224a60`，scoring `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`，parser `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`。只读成员文本，无解包/执行；不用当前ROOT/rh2代替历史。

官方精确路径为 `tests/func/test_cache.py`、`tests/func/test_remote.py`、`tests/unit/test_config.py`；test_globs空。原diagnostics恢复2个旧文件并应用新增第3个，apply_rc0，3个文件受保护；gold投影config.py且ignored为空。正常候选不需要改恢复文件。非参考节点即使运行失败，不能仅据完整pytest rc1推导reward0；冻结评分依据为F2P4+P2P18，并结合执行失败证据。当前普通日志噪音不改变22参考结果。没有额外自造排除项，也没有验证共享pytest控制面能否被候选操纵。

## 8. 关系、处置与唯一优先实验

6954是参数AST题，不是相同故障；其更晚公开base的 `dvc/config.py:230–250` 已有同名 `_to_relpath`/partial，并在相对路径上as_posix（绝对路径分支与3665 gold不同）。这是后版本公开材料含相关实现线索的具体关系，不证明两个任务应合簇或gold全相同；本包reviewer已暴露，应与solver隔离。此稿尚未审4785，关系留待最终review补证。

保留题面，优先调查/修订验收而非先做能力探针。推荐行为层断言覆盖实际保存器及Windows语义，去掉无公开依据的新增helper必需性；此为建议，未修改任何test/ref/reward材料。

唯一最值得先做的实验（未执行）：构造**仅把gold逻辑内联回base原 `_save_paths` 闭包、没有 `_to_relpath` 的等价候选**，先在明确的Windows语义对照中核公开相对/绝对路径、URI与可用缓存行为，再按同一冻结RH2材料评分；静态预期公开行为与gold相同但4个F2P全因缺helper失败。这一实验可以直接确认误拒并为测试修订提供准则。未强制再写第二候选；“只加游离helper”的漏测风险独立保留，尚未做得分实验。
