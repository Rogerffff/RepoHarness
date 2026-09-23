# python__mypy-15139：独立初判

- 状态：`needs_review`；范围：`static_review`；用途：`development_diagnostic`。本稿在主审、公开审查和旧质量结论暴露前保存，不表示正式训练/评测准入。
- 权威 ROOT：`.`。下文 P=`runs/swegym_quality_batch03_20260921_v1/public/python__mypy-15139`，Q 为同根 `private/python__mypy-15139`，R=`runs/env_recipe_repair_20260919/install_wave1/tasks/python__mypy-15139`，A=`runs/env_recipe_repair_20260919/frozen_sources/baseline.tar.gz`；相对路径均相对 ROOT。
- 暴露：已读四份共用方法、P 的全部顶层原件、Q 的全部顶层原件（含 gold/test/环境 gold-noop 摘要，以及 environment_record 内 history 的路径/批次元数据；未追该 analysis）、本题 inventory exact entry 与 common/install_wave1、这些原件精确指向的本题运行原件。不是无结果盲审。未读任何 `public_read.md`、`analysis_before_history.md`、`old_findings_delta.md`、`card.md`、`screening_record.json`、history 调查正文、其它题结论或批次聚合。仅静态文本/JSON/hash；未 import 项目、执行测试、解包归档、安装、联网或启动容器。

## 判断与优先下一步

**有具体的公开目标—gold—评分覆盖缺口，优先做 gold 对题面原例的定点 CPU 核验。** 公开 issue 要求错误和 note 中统一 `type`/`Type`/`builtins.type`，或保留代码所用别名；新增 F2P 只验赋值错误的 `type[type]`。gold 改 `messages.format_type_inner(TypeType)`，但 `MessageBuilder.reveal_type` 仍走 `TypeStrVisitor.visit_type_type` 的硬编码 `Type[...]`，内部 Instance 仍用 `builtins.type`。因此 gold 历史 reward=1 只能说明所选错误格式通过，不能称题面例子已完整修复。源码证据很强，实际公开例完整输出尚未执行。

`type[type]` 的测试拼写可从 base 已有 Python>=3.9 小写策略合理推出，并非纯粹隐藏要求；然而 issue 明示了选统一别名的自由，测试只接受小写路线。是否把其它统一方案算合理修复，需结合公开既有策略判断，不能仅据一句 OR 判误拒或强行缩窄原需求。

## 八方面与需求—断言映射

| 公开要求/合理回归 | 公开依据/源码 | 断言与覆盖 | 证据/未决 |
|---|---|---|---|
| 现代 Python 下 type 类型在普通错误中采用一致别名 | P/user_prompt.txt:3–21；P/base/mypy/options.py:358–364；同目录 check-lowercase 的 tuple/list/dict/set 成对旧例 | 唯一 F2P `mypy/test/testcheck.py::TypeCheckSuite::check-lowercase.test::testTypeLowercaseSettingOff`：`--python-version 3.9 --no-force-uppercase-builtins`，`x: type[type]; y: int; y=x` 精确要求 expression `type[type]`、variable `int` | 覆盖该错误分支；noop 原日志明确为 `Type[type]`，gold 为通过 |
| 题面 `reveal_type(x)` 的 note 也统一 | P/user_prompt.txt:6–15；messages.py:1630–1632 → types.py:3188–3189，Instance 在 2992–2998 用 fullname | test.patch 无 reveal/assert note | **缺失，gold 未触达该路径**；仍会生成 `Type[builtins.type]` 的静态路径，公开例 CPU 待验 |
| 题面 `reveal_type(type[type])` 的索引错误及 Any note | P/user_prompt.txt:9–10；messages.py:410–424 的 getitem 消息调 `format_type`，FunctionLike 类对象经 2521–2526 转 TypeType | 唯一 F2P 不调用类表达式/索引 | 部分共同 formatter 覆盖；base 相对旧 0.961 的完整行为仍需运行，不把题面旧输出当本 base 实测 |
| 旧 Python/显式 uppercase 配置保持既有输出；嵌套/类对象调用者可用 | options.py:361–364；messages.py:2365–2366 递归及 2521–2526；check-generics.test:503–505 `testTypeApplicationCrash`；check-classes.test:3482–3486、3526–3530 | 冻结 P2P=`[]`；现有相关旧例未被本命令选择 | gold 只对 `use_lowercase_names()` 为真改动，静态看保留 uppercase 路线；未执行回归 |
| 全部类型消息统一 | messages.py:1646–1649 `unsupported_type_type` 还显式拼 `Type[...]`；上述 reveal 分支 | 未新增覆盖 | 进一步边界缺口；该函数的具体现代 Python 可触发输入未执行，不把泛化猜测当已复现 |

1. **公开需求（3/23）**：读了题面、public_hints、环境说明及 base 的 formatter、选项与公开旧测试。issue 报告版本为 0.961，实际 base 是 1.4 开发版，目标仍可在该 base 的 TypeType 硬编码路径成立。现代 Python 的公开小写策略帮助消除部分别名歧义；没有公开依据可把所有 reveal notes 排除在 issue 外。`user_prompt.txt` 是静态渲染，实际 CC 消息和 public_hints 注入未验。
2. **材料/初态（1/2/27）**：base_commit=`16b936c15b074db858729ed218248ef623070e03`。P/base_identity 的 1360 tracked/blob entries、无 gitlinks/LFS/符号链接是冻结验证报告，未重做所有 blob hash。Q/source_refs 三条原始 ingest 第202行 raw SHA 与记录均重新对上；prepared manifest tasks[201] 为本题；原 host_grading_views.jsonl 第202行 SHA=`50810c3505dd848985482d59914863ac1f1463bc095ad797079f78293eebdbe7` 且其 grading 与 Q/grading.json 相等。gold 文件 SHA=`581a925ac3731600ced8561881f41bf083dd569b192dad1ce1f5370c88c9cfc5` 与 validation/运行候选相符。noop 的具体失败是大小写，不是导入/收集错误。
3. **测试测到要求（18–20/25/32）**：已读 test.patch 全文：只新增上述一例，无自定义新增 helper。已有 helper 链已读：mypy/test/data.py:52–107、211–214、518–544 把 `# E:` 变为带行号的期望；testcheck.py:93–184 创建程序/parse flags/build 并对完整输出数组断言；helpers.py:358–395 处理 flags，testcheck.py:128–129 对非 lowercase 文件强制 uppercase。新增例使用默认 lib-stub/builtins.pyi，已读 type/int 定义；没有继承前一 case 的 set fixture。它测语义输出而非文本文件存在或空操作；但只有一个形状，不能排除局部特殊处理。
4. **误拒合理解（24/28）**：精确文案和 int 名称符合已有赋值错误协议；不要求 gold 的函数结构。可把小写/大写命名选择抽成共用 formatter/visitor，也可在另一实现位置保持同样语义。公开统一 alias 路线若选择全局 `Type` 或保留 fully-qualified 名，可能被唯一 `type[type]` 精确断言拒绝；已有小写配置是反向证据，当前标规格解释风险，未构造/运行误拒候选。禁止改测试的 public_hints 对业务源码修复无必然阻碍。
5. **回归/gold（26/27）**：gold 全文仅 messages.py 一处，递归格式化子项且使用既有 options，未改类型检查本身或依赖。抽查了 lowercase 八个旧例、check-generics 的 type application、check-classes 的 Type tuple 不可实例化路径；它们是公开旧测试，**不是冻结 P2P**。reveal、unsupported_type_type 未随 gold 同步是实质漏修线索。未穷举所有 MessageBuilder、所有 reveal 用例、递归 alias、全仓类型输出或每个 Python 版本。
6. **开发条件（6–15）**：见下表；源码与 stub 入口可定位，无新增外部资产/服务需求证据。该问题可用 Python 解释执行；setup.py 默认 USE_MYPYC=False（88–94），编译并非必要修法。正式 actor 可用性未知。
7. **交付/评分边界（4/16–17/21–22/29–31）**：A 内 prepared_task_face.py:185–211 恢复 official test_patch touched 文件，本题仅 `test-data/unit/check-lowercase.test`；:306–330 定义 test_files、test_globs=()。gold 所改 `mypy/messages.py` 在历史 projection.included_paths，ignored_paths=[]。合理源码修改可提交，不需改系统包或被恢复测试。helper/配置属于潜在可控面，但本轮未做攻击或全平台安全审计；没有测试名统一排除的证据。未来镜像/祖先 Git 可见答案资产未验，不能凭静态导出无 .git 声称无泄漏。
8. **题目关系/用途（5/29–30/37–40）**：此为诊断字符串一致性任务，题面未给具体改法。第一题阶段未读后两题，未做跨题历史谱系判定；不因同仓同 formatter 就判重复。已见私有答案与运行结果，不可充当独立公开 solver。未评估模型成功率、训练价值或 token/费用。

## 实际执行、解析与冻结引用分账

下列均为 **2026-09-19 历史 RH2 replay** 的复读，非本轮重跑、非真实模型/正式 actor：

- **输入/配方**：install_wave1/run_install_wave1.py:32–47 仅把 pins 的 wheel COPY 至 `/opt/rh2/build-wheels` 并设 PIP_NO_INDEX/PIP_FIND_LINKS；:53–62 调原 baseline `scripts/replay_grade.py`，无 recipe/materials/reference_bindings 覆盖。R/image.json 与 status.json 核对：derived image=`sha256:5218fb276cd55dcfc1c7d718ac0a14534d61d6b0cb6ec3aebe528264e65cf1f4`，base digest 对上 public 的 `a41d…0037`。pins：setuptools72.1.0、wheel0.43.0、typing-extensions4.12.2、mypy-extensions1.0.0、tomli2.0.1、types-psutil6.0.0.20240621、types-setuptools74.0.0.20240830、types-typed-ast1.5.8.7、packaging24.1。
- **原 spec**：A 用 tarfile.extractfile 仅读成员文本，未解包/import。`envpack/data/swegym_specs_242429c1.json` SHA=`0da8f9caeec18e3b41386fb66e677807335c0fe12c41d811dd9fb65f9bfcc925`；python/mypy 1.4 规定 Python3.11、`python -m pip install -r test-requirements.txt; python -m pip install -e .; hash -r`、`pytest -n0 -rA -k`。A/spec_vendor.py:183–190 从 test_patch 中所有 `[case ...]`（含上下文）拼 -k，不从 F2P/P2P 拼命令。本题刚好一个 case。
- **安装实际证据**：gold 日志 `…bb2c55ae.eval.log`:788、828–852 是两条 pip 命令与 editable build/install 完成；noop `…d3434699.eval.log`:769、809–833 同样完成。不能由 Dockerfile COPY 或最后 `hash -r` 的 RC=0 单独推出完成。ledger/diag 导入路径均 `/testbed/mypy/__init__.py`，不说明全部子模块或正式 actor。
- **实际测试**：gold log:866–884 为完整命令、selected1/deselected11307、唯一节点 PASSED、RC0；noop:847–878 selected1、期望 `type[type]` 实际 `Type[type]`、FAILED、RC1。没有旧例/P2P 被执行的证据。
- **解析/冻结参考**：Q/grading.json 冻结 F2P1、P2P0。A/prepared_task_face.py:308–310 → scoring.py:229–269，仅 Start/End 内调用 mypy pytest parser，再对冻结 F2P/P2P 报告。两份 diagnostics 的 parsed=1、outside=0、missing=[]、skipped=[]；历史 ledger 第1行分别 reward1/F2P1/1 与 reward0/F2P0/1，P2P均0。这与实际摘要一致；未在本轮执行 parser。
- **字节对账**：run_refs 的 log 与 ledger 全文件 SHA 均重新验证匹配；gold log=`ab061cfe5044a9bae09f0c2d03b9d9f14ddf22c2ea02bec174bac461b9a265b4`，noop=`6ca829687361af87c19ab54095536ccd01821b4e4a37a9acf400c64b04f53274`。ledger 为 R/gold/ledger.jsonl:1 和 R/noop/ledger.jsonl:1。baseline 四个 inventory 成员 SHA 均重算相符；另沿调用关系读 scoring.py、swegym_parsers.py 和 pinned spec JSON。
- **身份边界**：候选 git apply 为 agent/54321；grader 为 rh2grader/54322、deny_all、2CPU/4GiB/PID512、tmp1GiB/shm64MiB，可写 conda prefix；env_qualification=`absent`。A/replay_grade.py:294–317 的临时候选容器及评分用户不等于 CC 正式解题验收。A/prepared_task_face.py:336–350 正式 rollout 仍取 public.image；派生镜像未证实被正式 actor 消费。

## 开发条件与最小实验（尚未执行）

| 必要操作/资产 | 公开依据 | 当前证据与缺口 | 后续最小验证 |
|---|---|---|---|
| 运行工作区 mypy，定位 messages/types/options | CONTRIBUTING.md:39–44、73–85；mypy/__main__.py 入口 | grader 离线 editable 安装和工作区导入已记；actor shell/PATH、包来源、写权限未知 | actor 身份记录 UID/HOME/cwd、`python -V`、包来源，再运行题面小程序；仅验证输入代码，不运行隐藏测试 |
| pytest 数据驱动框架与 fixtures/typeshed | test-requirements、test-data/unit/README.md:27–69，base 有 typeshed，无 gitlink | 历史 grader pytest8.3.2/Python3.11.9 收集和唯一例执行；新机 wheel context/payload 未保存、image可用性未知 | 准备时固定依赖，actor 运行公开 `pytest -n0 -k 'testTupleLowercaseSettingOn or testTypeApplicationCrash'`；无需全仓或网络服务 |
| 提交修复 | public_hints 非测试源码；formatter 是 tracked 源文件 | 不需新增模型/网络资产或写系统包；测试恢复只影响上述 .test | 核 candidate 源码进入 frozen projection 与实际 import；无需修改 expected/reward |

**唯一优先实验**：在已准备并确认身份的固定 grader/诊断入口，保留原评分材料，先对 base 与 gold 运行题面两行 reveal（目标 Python3.10、默认配置），另添赋值错误观察；逐条记录 type/Type/builtins.type 输出与原评分 reward。预期可区分“仅错误 formatter 修复”与“公开原例完整一致”，无需先造第二个新候选。若确认 gold 漏修，再讨论扩充验收/公开规格解释，不能先为 gold 收窄问题。该固定 grader 语义诊断不以正式 actor 验收为硬前置；正式模型开发探针仍需另补 actor 实际镜像、激活、工具、可写路径、资源与清理验收。

未来重放须新建重定位 summary/manifest、独立输出和 run_id；原 prepared 内 `/work/...` 是历史地址，原账本不作写目标。本轮未触碰原件、源码、tests、gold、reference、reward、expected；未提交推送。未查范围还包括真实 CC 交互、当前宿主镜像存在性、复现实耗、全部正确替代解与全仓回归。

## 整包独立阶段结束前的关系补记

三题均已有初稿后、任何主审/旧结论暴露前，追加核对自己三题的精确源码：15184 base/messages.py:2519–2521已含15139 gold的lowercase分支；15139和15184各自base/meet.py:300–312均已将Any检查放在非strict optional的Union去None之后，即10174的关键修复结构已经存在。只说明后题base包含前题修复信息，不证明Git谱系/同问题重复，也不合并三种目标。此补记新增暴露范围仅为同包三题这些源码行；无其它题或history读取。三题gold文件hash均已重算，与validation/原ledger相符。
