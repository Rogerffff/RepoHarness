# Project-MONAI__MONAI-5932 — history 解封前独立主审

判断者：e25_main_pack09_monai；日期：2026-09-25。仅静态审查及授权历史 RH2 原运行核读。未执行/导入项目、测试或实验；未联网、派生 agent、修改原题；未读 history 质量结论、reviewer、其他包或聚合。已读 root 封存的本题 public_read.md，并独立核读下列原件。此稿写完并报 SHA 后不再改写。

## 结论与公开目标

公开目标明确：同一 `$` 表达式中的 `@training#num_epochs` 和 `@training#num_epochs_per_validation` 应独立解析，公开算式应返回 4。题面不要求排序或某种具体替换算法。base 的完整匹配收集是正确的，而按出现顺序对全串 `replace` 会先替换短 ID、破坏长 ID。gold 将匹配按长度降序处理，在已定义合法 ID 的情形消除此破坏；历史 no-op/gold 对照与该解释一致。

本题可保留作 development_diagnostic 静态候选，disposition=needs_review/static_review。没有发现新增测试强制 gold 实现；但单个 F2P 不充分覆盖前缀问题的多样输入，也没有当前 actor 可开发证据。没有证明 gold 引入回归，也没有证明其完整修复所有引用边界。唯一优先下一步是取得实际 actor 的公开复现和窄旧测试开发记录，保留初态与导入路径；不建议仅因未知重跑全仓。

## 证据命名与版本

- P = `/Users/roger/Desktop/claude-code-verl-stage0h/runs/swegym_quality_expansion_20260925/public/Project-MONAI__MONAI-5932`，下文源码行号相对 P/base。
- Q = 同级 `private/Project-MONAI__MONAI-5932`。完整读取 user_prompt、public_bundle、base_identity、environment_brief、gold.patch、test.patch、grading.json、validation.json、source_refs.json。
- R = `/Users/roger/Desktop/claude-code-verl-stage0h/runs/full216_rh2_diagnostic_20260919/remote/replay/baseline01/workers/w06-3`。
- L0 = R/eval_logs/evallog_replay-f216-baseline01-w_db67fc33.eval.log；L1 = R/eval_logs/evallog_replay-f216-baseline01-w_3e134533.eval.log。原账本只语义读取 R/ledger.jsonl 的第 3、4 行；没有查看其他题行。机械校验 ledger 文件与两个日志的 SHA 均与 Q/run_refs 相同。

公开/base/grading 都指向 `3c8f6c6b94ba26f8c9df5b7c96089494de6f69cb`（MONAI 1.1 任务）。base_identity 声明跟踪 blob 导出核验，不代表 actor 初态。source_refs 定位原公开/私有 bundle 行 20，未沿该共享文件扩读。gold 文件与授权实际 candidate.patch 字节一致，SHA256 `811f539ac23d7a2a76fb6b541abfaa7912579730f8683574cf08cad634e2534e`。

历史镜像 tag=`xingyaoww/sweb.eval.x86_64.project-monai_s_monai-5932:latest`；expected manifest digest=`sha256:84a4d4afe3f663633da40359ddb8ff5c0e951144e103bed27b907481f9cee6f4`；actual image ID=null。scripts_digest=`sha256:0ccc2f63a519e145066da051a6cfb66f5ad6e9a4365b07b0754b3bd684736f05`。不把 tag、期望 digest、image_identity 字段冒充实际 ID。environment_record 的历史代码快照仅见定位/摘要元数据，未读 archive 成员或重验代码摘要。

## 源码、gold 与行为链

`reference_resolver.py:56` 匹配完整 `@` ID，`:191–209` 收集依赖；`:141–159` 在替换之前处理缺失、递归和循环；`:223–244` 对 `$` 式或整串引用替换。题面短 ID 第一次出现时，`:240` 会把后面的长 ID 改为 `__local_refs['training#num_epochs']_per_validation`；`:162–173` 将新配置交给 ConfigExpression；`config_item.py:331–375` 的 AST 解析于是报错。公开标题虽称“can't get references”，根因不是遗漏依赖或 import 模块。

gold 全部改动只有匹配列表按长度降序排序及两行注释。对相同 ID 重复出现，第一次全串替换已处理所有位置，后续遍历只是无匹配；生成的 `__local_refs['id']` 不含 `@`，合法 `\w/#` ID 不会产生新的可替换引用，因此定义齐全的前缀链可静态解释。整串引用仍返回实际 refs 对象，普通字符串仍不解析，非字符串递归行为未改。

`ConfigParser.parse/get_parsed_content`（248–287）和 `_do_parse`（357–381）为直接调用者；相对 ID 在 319–355、466–501 先规范化，不能混同本次排序。针对 monai 的符号检索只找到该 resolver 内部递归及 ConfigParser 实例化，未宣称所有外部调用者已穷尽。

## 需求—断言双向表

所有 F2P/P2P 的源码方法及 fixture 均已语义阅读。表中 P2P 以 `tests/test_config_parser.py::TestConfigParser::` 为共同前缀；F2P 同此前缀。H 表示授权历史真实 RH2，S 表示静态分析。

| 公开要求或合理旧行为 | 公开依据 | 测试/决定性断言 | 覆盖、缺口及证据 |
|---|---|---|---|
| 同式短长前缀独立解析 | 原题算式；reference_resolver:223–240 | F2P `test_substring_reference_0`：training A=1、A_B=2，`total=$@training#A + @training#A_B + 1`，assertEqual 4 | 直接覆盖原故障同构情形；H no-op SyntaxError、gold pass；没有指定排序 |
| 配置读写、嵌套和整数索引 | ConfigParser 公共 API | `test_config_content`：get/set、字典目标、嵌套路径、list[1] 值 | 旧 API 覆盖；S/H |
| 实例解析、缓存/default 与对象类型 | parse/get_parsed_content 文档 | `test_parse_0`：keys 修改、lazy 缓存相等/不等、五种类型、default=12345 | fixture 引用 Compose/Dataset/DataLoader；torchvision 条件 skip 代码已读，本次 H 实际 pass |
| 函数/partial/方法解析 | `$` 和 `_target_` 已有机制 | `test_function_0`：各方法 (1,2)=3；error_func TypeError | 保留对象和函数而非转成字符串；S/H |
| 相对引用及嵌套表达式 | config_parser:466–501 | `test_relative_id_0`：标量=1，嵌套 value3=[3,4,4,105] | 有相对引用但未组合前缀冲突；S/H |
| `%` 宏及文件读取 | _do_resolve | `test_macro_replace`：临时 JSON 后 D=[3,1,3,4] | 宏隔离；需要临时文件写权限；S/H |
| 允许缺失保留原值，默认缺失报错 | resolver:149–156、230–236 | `test_allow_missing_reference_0`：@D、test@F；恢复 class flag 后 ValueError | 只覆盖非前缀缺失；S/H |
| 表达式列表可调变换 | `$` 文档、对象引用 | `test_list_expressions`：seed 后 [0.7942,1.5885] atol=1e-4 | 对象调用、缓存；S/H |
| contains 不混淆键前缀 | ConfigParser 成员访问 | `test_contains`：value/entry true、value1/entr/array#2 false，错误读取 KeyError | 字典访问语义，与本次表达式替换不同；S/H |
| lambda 引用对象可展开 | 公开表达式机制 | `test_lambda_reference`：reshape (1,8,8) | `*@patch_size`；S/H |
| 非字符串目标/属性访问 | 原有组件表达式 | `test_non_str_target`：`$@model.forward` callable，输出 (1,400) | resnet18 pretrained=False，无权重下载要求；S/H |
| 错误实例与调试行为 | 已有实现 | `test_error_instance` RuntimeError；`test_pdb` BdbQuit 正则及 None | TimedCall helper 为独立进程；历史已 pass，不扩展为 actor 工具保证 |
| 属性式内容访问 | get_parsed_content 行为 | `test_get_via_attributes`：A 嵌套值、dims_1=3、reshape | 普通加法单引用；S/H |
| import 表达式仍工作 | config syntax:105–111 | `test_builtin`：math.isclose True | 无前缀表达式；S/H |
| 三个以上前缀、重复、顶层、交换顺序 | 公开 bug 的同类机制，非新增规格 | 新测试没有对应断言 | 有机制上合理预期；覆盖缺口（25），不是已证 gold 回归（26） |
| 循环引用拒绝和 resolver 实例类型 | reference_resolver 文档/实现 | 额外公开 `test_reference_resolver.py`：types 与 ValueError | 本次授权 grader 未选此文件；只 S，不能并入 14 P2P |

反向核对：唯一新增断言的常量 4 完全来自公开数值语义；不存在新增私有 API、补丁形状或内部变量名断言。新增 TEST_CASE_5、parameterized 装饰器、函数体全读，测试身份后缀 `_0` 与 expected/日志一致。既有 P2P 全部 14 项均在表内，不能把 14 次 pass 表述为前缀组合覆盖。

## 非 gold、误拒、漏测和回归

合理非 gold 可以对原字符串一次性正则 callback 替换完整匹配，或按 match span 构造输出，保留 `$`/整串引用分支、实际对象返回及缺失策略。新增测试只观察结果，不会因算法不同直接拒绝。未运行替代解，因此只能报告未发现静态唯一实现约束，不能证明所有正确解都过关。

具体不完整修复：只对含 `_` 的匹配采用保护逻辑会通过 A/A_B 用例，却仍在 `A` 与 `AB` 的合法前缀失败；只反转匹配出现顺序可通过短在前的新增例，但长在前时会反而先改短引用。当前 P2P 没有这些同式前缀组合，可以漏测，属于 S 级推断，未执行坏补丁。无需把每个建议边界提升成原题明示验收。

允许缺失的前缀组合仍需谨慎：较长引用缺失时 gold 会跳过长项，之后全串替换较短已定义项仍可能改写缺失 token。这是沿未变动 `continue/replace` 路径的风险，旧实现也存在；现有缺失 P2P 不覆盖，不能据此标记 gold 新增回归。引号/转义的语言规格不充分；旧 `$'test'+'@F'` 已表明“引号内永远不解析”不是可任意添加的新规则。

## 原运行、可信恢复与分数解释

L0:130–145 显示 grader 启动时分支 dev，只有 requirements-dev.txt 修改；L0:474–483 的真实 diff 删除 MetricsReloaded 的 git URL。紧邻的 `git show` 是 base 提交内容，不是初态未提交 diff。L1:130–145、475–498 同时显示 gold 源码修改和相同依赖改动。这只适用于历史 grader，实际 actor 的 HEAD/status/diff、源镜像原始初改及忽略资产仍 unknown。

L0:484–524、L1:499–539 用 base 的 tests/test_config_parser.py 恢复、应用 test patch，apply RC=0、恢复/存在 1 个文件、无 absent/irregular。授权 projection/baseline/stage 指针均核读：base 与 materialized_head 相同；no-op included=[]；gold included 仅 monai/bundle/reference_resolver.py，git_apply。raw candidate 字节核对支持绑定，不单凭 gold 标签。

原安装命令：`sed -i '/^git+https:\/\/github.com\/Project-MONAI\//d' requirements-dev.txt`；`python -m pip install types-pkg-resources==0.1.3 pytest`；`pip install -r requirements-dev.txt`；`python setup.py develop`。安装最后命令 RC 两次均 0，未 skip；中间依赖输出未逐行语义审计。实际测试 `pytest -rA tests/test_config_parser.py`，Python 3.8.20/pytest 8.3.3，15 collected；不是全仓测试。

- L0:950–1004 的唯一失败在新增 assert 的 `get_parsed_content`，生成 `__local_refs['training#A']_B`，SyntaxError；:1089–1111 为 14 pass/1 fail，test RC=1。
- L1:1050–1072 为全部 15 pass，test RC=0。逐个 expected ID 与日志状态机械对照无遗漏/额外；没有 skip/xfail。报表 f2p=0/1→1/1、p2p_fail=0 与原日志一致。
- ledger 3/4 的 install_seconds=9.243/7.707、test_seconds=28.145/29.586；mem_peak_mb=1312.125/992.848，原字段名和值保留、未核单位实现。两次 cleanup removed=true；runner integrity changed=false；导入记录 `/testbed/monai/__init__.py`、version `1.1.0+50.g3c8f6c6b.dirty`。这是历史 grader 局部正证据。

历史 policy 为 rh2grader/UID 54322，cpus=2.0、memory_bytes=4294967296、network=deny_all、pids_limit=512、shm_bytes=67108864、tmpfs_bytes=1073741824；candidate apply_user=agent/54321，不能替代真实模型 shell。安装能在该条件完成，不能推导 actor 的 pip、HOME、PATH 或资产可用。未审计整个 parser/控制面代码，不能证明防伪/隔离完备。

## 开发需求（命令只建议，未执行）

| 操作/资产 | 公开依据 | 已有证据适用范围 | 缺口与最小公开验证及预期 |
|---|---|---|---|
| 源码可读写、合法非测试提交 | hints 与公共解析器代码 | 历史 gold 源文件投影成立 | actor 初态/权限 unknown；先 `git rev-parse HEAD`、`git status --porcelain=v1`（各自 RC），保留已有 diff；提交前 diff 应仅含有意源码修订 |
| Python/torch/numpy/MONAI 导入 | requirements.txt、原题 | 历史 Python3.8.20 和 workspace import 成功 | actor 执行 `python -c 'import sys, monai; print(sys.executable, monai.__file__)'`，确认实际源码 |
| 用户 API 核心复现 | 原题内存字典 | 静态根因+历史同构 F2P | actor 运行原题完整配置，base 应出现目标 SyntaxError，合法修后 total_iters=4；无需私有测试 |
| 旧解析/引用回归 | 已读旧测试 | 历史只跑 parser 文件 | `python -m unittest tests.test_config_parser tests.test_reference_resolver`；保留实际收集/skip、RC；pdb 用例需可用子进程/100秒 helper 预算 |
| 临时目录与可选 torchvision | macro test、parse skipUnless | 历史宏文件写入与 torchvision 用例 pass | actor 临时写权限、可选包状态待核；无需为数字复现预置模型数据 |
| 网络、GPU和外部文件 | 原题仅内存标量运算 | 历史 deny_all 窄测试可完成 | 最小 API 无运行期服务/GPU需求；依赖准备供应路径需明确，不能默认允许任意下载 |

唯一优先下一步：任务二用真实 actor 入口保存初态、解释器/导入来源及原题 API+上述窄公开测试的逐命令结果，确认解题路径可用。它可改变当前 actor 条件 unknown 的判断；不以新 CPU 随意扩大规格，也不安排全仓或模型实验。

## 八方面、编号与用途边界

八方面分别已处理：公开目标与歧义；版本/初态；全部新增断言及全 14 P2P；合理非 gold 与具体漏测；gold/调用者与未证明回归；开发依赖/权限/网络资源；合法交付与可信测试恢复；同仓关系/私有暴露/用途。

原编号稀疏结论：1 静态版本及授权绑定 pass（实际 ID unknown）；2 S+H 目标失败 pass；3 actual actor 输入 unknown；4/6/8/9/16/17/18/19/20/21 仅上述历史路径有局部正证据；10/33/34/35/36 unknown；23 公开目标充分；24 未发现唯一实现但普遍误拒 unknown；25 issue（前缀变体缺口）；26 unknown（未证 gold 新回归）；27 局部正确有 S+H、完整性 unknown；28 未新增强制规格；29 actor 泄露 unknown；30/31/32 防取答案及控制面完整性未核；40 漏检/误拒/抽样偏差 unknown，封存流程不证明质量。未列项 not_checked。

与同包另一 MONAI 题的已知关系仅同仓、不同 base/子系统/gold；没有跨题重复/留出集比对证据。审查者已授权看到本题 gold、test patch、原运行及公开阅读，尚未看旧答案/历史结论；这些私有材料不得进入 solver。usage.intended_use=development_diagnostic；additional_exclusions=[]；revision_refs=[]；本轮 token/费用未观测为 null，不产生训练、正式评测或模型成功资格。

## 实际语义阅读清单及未读范围

完整源码/测试：reference_resolver.py:1–301；tests/test_config_parser.py:1–301（14 P2P 的所有 fixture/断言）；tests/test_reference_resolver.py:1–112；requirements.txt、requirements-min.txt；全部 gold/test patch。

区段：config_parser.py:105–120,248–287,302–381,466–501；config_item.py:297–410；docs/source/config_syntax.md:76–112；tests/utils.py:535–635（TimedCall 完整主体；缓存调用的更后实现未读）、730–807（一次宽区段读取，非此题决定性证据）。其余源码未读，未用 public_read 的阅读范围冒充主审阅读。

原件：Q/run_refs 全部按 JSON 解析，语义核读两个 input_identity、candidate binding、原件 selectors；environment_record 只核读 scope/identity/actor/gaps 与 source snapshot 定位元数据，未沿归档/host_grading_view 扩读。授权 ledger 3/4 行及 projection/baseline/stage 的指定 JSON pointers；实际 candidate.patch 全部字节。日志实际语义区段 L0:130–145,474–524,950–1004,1089–1111；L1:130–145,475–539,1050–1072；安装命令/RC/测试选择器/平台/收集行和 RH2 markers 为精确筛选阅读。曾宽筛 `+`/测试状态导致输出截断；截断区不算完整读。未逐行读依赖安装长输出、全部 warning、conda 展开或 git show 的提交正文（早期输出仅见若干加行）。全部状态行经完整再读与机械 expected 对照。

未读项目其他文件、外部包 helper 实现、其余全仓测试、当前 actor 环境/消息、任何 history 质量结论或 reviewer。上述边界使 H 局部成功不能提升成完整环境或无回归证明。
