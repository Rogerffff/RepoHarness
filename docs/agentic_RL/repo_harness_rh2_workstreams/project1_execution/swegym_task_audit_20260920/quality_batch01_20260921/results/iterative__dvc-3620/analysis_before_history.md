# iterative__dvc-3620：历史开放前独立分析

本稿仅静态阅读与元数据校验，保存后封存。未读本题 history refs、旧调查、其它题结论、批次 manifest、主计划或 method_adjustments；未运行项目代码、安装、容器、SSH、CPU 对照或模型。先读取本题已封存 public_read，再独立追公开源码、全部补丁断言、F2P/P2P 与指定原始日志。已读 environment_record 的环境汇总并记录暴露，但没有沿其中 analysis/history 链接提前读取旧汇总。

## 路径与身份

以下缩写均为固定绝对路径，后文 `X/文件:行` 可据此展开：

- R = `.`
- B = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921`
- P = `runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-3620`
- Q = `runs/swegym_quality_batch01_20260921_v2/private/iterative__dvc-3620`
- O = `docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/swegym_task_audit_20260920/quality_batch01_20260921/results/iterative__dvc-3620`
- T = `runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3620`
- GL = `T/gold/eval_logs/evallog_replay-er19-dv1-iterativ_9b423984.eval.log`
- NL = `T/noop/eval_logs/evallog_replay-er19-dv1-iterativ_cf25aa49.eval.log`

base 为 `e05157f8e05e856d2e9966c30a3150c26b32b86f`，导出 tree 为 `d4fa95ff32fb623e4bf12a3bf3098c7cc882fef3`。`P/base_identity.json` 记 360 tracked entries、1,169,927 blob bytes，无 symlink/gitlink/未物化 LFS，未导出 `.git`。本轮没有重建整树哈希，把该导出身份作为材料元数据。公开 image manifest digest `sha256:efb04551ca1c3c1c27a73627f585bba79ebcec841bce034f035034261660c9f0`；来源 Python 3.8、版本 0.92，题面自报 0.91.1 是问题报告上下文，不等于当前 base。

标准库 Python 逐项比较 `Q/source_refs.json` 明确指定的 S2 public/grading/validation JSONL **各第 124 行**，与本题包完全相等；未读相邻任务行。`Q/gold.patch` SHA256 为 `54c21a8c1dbd18cabb0dc1176db6f06aba4c4d41d4282f242f5f658451da22f0`，与 validation 及 gold 账本相同。两份日志及 environment_record 列出的 10 份配方工件哈希均一致。

## 1. 公开需求与初始问题

题面明确指出 `RemoteLOCAL.unprotect` 用副本替换 symlink 时，`remove` 在 unlink 前调用 `_chmod`，`os.chmod(link, mode)` 改到 cache target。合理目标是解除工作区文件保护、保留数据并断开链接，同时不无故改变缓存权限。题面没有要求新增 helper 名、特定调用顺序、修改哪个文件，也没有显式讨论 hardlink。代码块有原始换行粘连（logger/path、mode/try、raise/func），但足以定位真实函数；实际模型请求未捕获，不称渲染已验。

`P/base/dvc/utils/fs.py:118–143` 与题面原因吻合：非目录先 `_chmod(os.unlink, path, None)`；`_chmod` 取 lstat mode，再 chmod(path)，最后才 unlink。`P/base/dvc/remote/local.py:412–432` 先 copyfile 到同目录临时名，再 remove(link)、rename(temp,link)，最后 chmod 工作区副本为 `_file_mode`。CACHE_MODE 为 0444，默认工作区 mode 为 0644，shared group 为 0664（:34–37，`remote/base.py:95–112`）。POSIX symlink 的 lstat 与 target stat 不同，这次预先 chmod 会改 target；hardlink 则直接共享 inode 权限。

公开旧断言与新目标有冲突：`tests/unit/remote/test_local.py:57–61` 允许非 Windows symlink/hardlink 的源文件在 unprotect 后变为非保护状态；`tests/func/test_unprotect.py:27–34` 明确把 hardlink 缓存暂时可写作为既有行为，再调用 status 恢复。对 symlink，issue 已明确否定该旧行为；对 hardlink，公开材料提供“相同根因应一并消除”的合理推断，但没有明确宣布旧行为也必须改变。不能仅因 gold 同时修复两种链接，就把硬链接新要求称为题面明文。

NL:708–747 的 symlink F2P 确实到达最终 `assert remote.is_protected(foo)` 并失败；NL:654–693 的 hardlink 同样失败。不是安装、导入、收集失败制造的 0 分。

## 2. 全部修改断言与 fixture/helper 展开

`Q/test.patch` 只修改两份测试，不新增业务源码或 fixture。

**unit 两个 F2P**：`tests/unit/remote/test_local.py::test_is_protected[symlink]` 与 `[hardlink]` 共用 :34–61。`tmp_dir` 通过 `tests/dir_helpers.py:217–243` 创建并切换临时目录，因请求 dvc fixture，用 `TmpDir.init(...,dvc=True)` → `Repo.init(...,no_scm=True)`（:89–107）；没有外部 remote。写入非空 `foo` 文本，构造 PathInfo，使用真实 `RemoteLOCAL.symlink/hardlink` 建 link；前者调用 `System.symlink`，后者非空路径调用 `System.hardlink`（local.py:170–202；system.py:36–50）。非空输入避免 hardlink 对空文件用独立空文件的优化。

随后依次断言 foo/link 初始均不保护；调用真实 protect(foo) 后二者都保护；unprotect(link) 后 link 不保护。修改仅在源 foo 的最终断言：Windows hardlink 允许源不保护；其它组合要求源保护。`is_protected` 通过 exists 后 stat 精确比较 0444（local.py:532–538），并非 os.access，避免 root 对可写权限的特殊解释。但它对不存在的 path 返回 False，因此 `assert not is_protected(link)` **本身不能证明 link 仍存在**。测试未断言输出字节、不再为链接或修改副本不影响原缓存。

**额外 CLI 测试**：`tests/func/test_unprotect.py::TestUnprotect::test` 的完整原体仅 34 行。TestDvc 经 `tests/basic_env.py:21–113,153–156,191–198` 生成包含 FOO="foo" 的临时目录并 `Repo.init(no_scm=True)`，不是外部下载的数据。CLI 配置 cache.type=hardlink，add foo；断言工作区和 `.dvc/cache/ac/bd18db4cc2f85cedef654fccc4a4d8` 均不可写；unprotect 返回 0、输出可写。补丁把“缓存可写→status 返回 0”限定 Windows，再在所有平台断言 cache 不可写。POSIX 新语义是立即保持 cache 只读。该测试依赖实际非 root 身份的 `os.access`；当前日志为 rh2grader。它在两份命令中执行，**不在 F2P/P2P 参考集**。它补了输出存在/可写的检查，但同样没有读取输出内容或验证断链。

**4 个 P2P，已全部读完测试体**：

- `test_status_download_optimization`（unit local :11–31）：NamedCache 填两个 checksum，mock local cache_exists 为全部已存在，remote 为 mock；download=True 后断言未访问 remote.cache_exists。对应 local.py:250–288 的 shortcut；不是数据真实传输或 unprotect 回归。
- `test_protect_ignore_errors[1]`、`[13]`（:64–76）：创建 foo，先真实 protect，再 mock os.chmod 抛 EPERM/EACCES，调用 protect 不抛并检查 mock 被调用。local.py:452–470 会读真实已为 0444 的文件后容错。这测 protect 的共享缓存权限路径，不测 remove/unlink 失败回退。
- `test_protect_ignore_erofs`（:79–88）：未预先 protect，mock chmod 抛 EROFS，调用 protect 不抛并检查调用。测只读文件系统容错，也不测 unprotect 删除回退。

`tests/conftest.py:1–66` 的顶层 imports 包括 mockssh 与 tests.utils.httpd；后者 :1–6 顶层导入 RangeHTTPServer。即使本地测试也需这些依赖可导入，但此测试选择器不请求 ssh/http fixture，不要求运行外部服务。autouse 设置 DVC_TEST、日志、close_pools，没有把权限断言换成 mock。

## 3. 需求—测试双向映射

| 公开要求或合理旧行为 | 公开依据 | 对应验收与决定性断言 | 程度与证据 |
| --- | --- | --- | --- |
| symlink unprotect 不更改只读 cache | issue 末段；fs.py:118–143 | symlink F2P 最终 foo 为 0444，link 非 0444 | 直接覆盖通常成功路径；NL 最终权限失败，GL 通过 |
| 工作区输出解除保护 | local.py:432；command/unprotect.py:25–37 | 两个 F2P `not is_protected(link)`；额外 CLI `os.access(foo,W_OK)` | 参考断言弱于存在且可写，CLI 补充但不是参考 |
| 复制原数据、断开共享链接 | issue 首段；local.py:417–424；公开 checkout_relink | 官方 7 项均无内容/断链断言 | 缺失；现有实现保留了复制/替换；不能以七绿证任意候选数据完整 |
| POSIX hardlink 也保持 cache 只读 | 同一删除副作用根因、CACHE_MODE；旧 hardlink 测试反向 | hardlink F2P 与额外 CLI 新最终断言 | 属自然推广但有公开范围歧义；symlink-only 合理解法可能被拒，尚未执行 |
| Windows readonly hardlink 仍可删除，状态检查后再保护 | 公开功能测试旧注释；System Windows 分支 | 新测试保留 NT hardlink 例外与 CLI status | 当前 Linux 日志未执行 NT 分支；不可称跨平台已验 |
| 普通/缺失/断链路径 remove 不倒退 | fs.py:132–143；公开 test_remove 与 TestRemoveBrokenSymlink | 本题 4 P2P 均不覆盖这些路径 | 静态追踪、公开回归可用；没有本次执行证据 |
| protect 的 EPERM/EACCES/EROFS 容错、download shortcut 保持 | local.py:250–288,452–470 | 4 P2P 真实状态/Mock 调用断言 | GL/NL 均通过，含义限定于这些方法 |

反向检查：没有隐藏 helper 名、私有新增 API、精确日志或调用次数约束；两个 F2P 都是可观察权限结果。cache 0444 来自公开常量，不是 gold 私有值。硬链接新语义来自根因推广，并与公开旧断言的历史兼容行为冲突，是本题唯一需要先定范围的重点，而不是“唯一实现”绑定。

## 4. 替代解、部分解与 gold

不同于 gold 的充分合理路线：在 remove 的非目录分支内直接 try unlink，仅失败时才走旧 `_chmod`，不新增 `_unlink`，保留 ENOENT 处理。这与 gold 的错误优先回退语义一致，现有测试不要求 helper，可静态预期接受，但没有新运行证明。

范围较窄的另一合理路线是在 remove 中对 symlink 直接 unlink，其它文件保持旧行为。它能消除题面指定 target chmod，保留公开 hardlink 旧行为；静态预期 symlink F2P 通过、hardlink F2P 与额外 CLI 失败。这是**题意边界待裁定**，不是已证误拒；更一般的“unprotect 任意链接不该改缓存”解释也有源码依据。

部分实现风险：若重写 unprotect 时创建空的独立可写文件替换链接、漏复制原字节，两个 F2P 与额外 CLI 的后置权限断言都不足以发现；4 P2P 又未调用 unprotect。若简单删除链接后提前返回，F2P 也可能通过，但额外 CLI 会失败。它们说明缺少数据后置条件，不表示已有自然模型输出如此，也未验证实际评分接受。不要凭这个静态构造把本题排除于有限诊断。

gold 增加 `sys` 和 `_unlink(path,onerror)`，先 os.unlink，遇 OSError 才传真实 sys.exc_info 给旧回调，remove 使用它；其余路径不变。常见 POSIX symlink/hardlink 删除无需 chmod 文件本身，故 cache 0444 保持；copyfile→rename→chmod 的原数据路径未改。无需新第三方依赖。普通文件直接删、目录仍 rmtree(onerror=_chmod)；缺失文件在 unlink→回调 lstat 的 ENOENT 被外层忽略；断链 symlink 直接 unlink；Windows 只读硬链接首次失败时仍旧回退。没有查到本题 gold 明显未修主例或混入无关业务。

限制：失败回退仍可能 chmod target（如目录权限导致 unlink 失败），但题面主例是成功解除保护，未把所有失败原子性规定为需求；本轮不将此泛化成 gold 已证回归。Windows、特殊 FS、并发替换都没有运行证据。

## 5. 相关调用者与回归实际阅读范围

已追 `command/unprotect.py:12–39` → `repo/__init__.py:158–159` → RemoteLOCAL.unprotect；`output/base.py:307–338`、`stage.py:357–379` 的 persist/remove/unprotect_outs，`repo/destroy.py:1–15` 的保留数据再移除元数据；local.py:139–144 复用 remove；remote/base.py:430–445 的 add/save 路径、:755–797 缓存变化与重新保护、:1066–1083 checkout 替换。缓存保持 0444 也维持 changed_cache_file 直接视为未变的优化。

公开回归已静态读：`tests/unit/utils/test_fs.py:163–172` 的 str/PathInfo remove；`tests/func/test_remove.py:14–89` 的文件、缺失 stage、断链 symlink、目录/CLI；`test_checkout.py:488–519` 的 hardlink/symlink 解除后断链及 relink、copy 模式；`test_add.py:617–636` 再 add 保护缓存；`test_run.py:347–458` 的 symlink/hardlink 输出重运行与内容；`test_repo.py:10–29` destroy 保留文件并断链。部分读取外围行，不称全仓或整文件审阅。这些不在本题 6 个来源参考内，当前 7 项命令也未执行它们。

## 6. 原始运行、参考保护与实际阅读分开记录

指定最新记录：`T/gold/ledger.jsonl:1`（candidate=gold, attempt=1）和 `T/noop/ledger.jsonl:1`（noop, attempt=1）。同一 `dvc-install-v1:iterative__dvc-3620`、实际 local-build image `sha256:820a5c7d4c7b28edebb1886834a74d4cfa1f058137ed76f210737a33f4cd1cc7`；grader rh2grader/54322、deny_all、2 CPU/4 GiB、PID512、tmpfs1 GiB、shm64 MiB、可写 conda prefix。两账本 cleanup.removed=true，reference_missing/skipped 为空、parser 7。

GL:132–142 和 NL:132–141 记录 HEAD 就是 base；双方预置未提交 `setup.py` 把 moto==1.3.14.dev464 改为 1.3.14（GL:211–221、NL:177–189）。gold 另有 fs.py 对应修复；这项安装环境差异不是金答案修复，也不是干净 base 的全部运行条件。GL 的 git show autocompletion diff 是 base 自身提交，不是候选额外改动。gold 投影 included_paths 只有 dvc/utils/fs.py，无忽略路径。

配方 `T/gold/recipe/recipe.json:3–13` 将多段在线/缺失 requirements/无效 extras 安装改为 `python -m pip install -e '.[all,tests]'`，保留安装 RC，随后输出版本。GL:414–425、590–610 和 NL:381–396、557–577 显示本地 `/opt/rh2/build-wheels`、editable 安装完成、RC0；相关安装没有报告失败。日志没有证明原公共镜像也具备该修复。GL:224–274、NL:191–234 记录两份官方测试从 base 恢复、patch clean apply、文件数 2；测试补丁未覆盖业务源码。

| 范围 | gold 原始证据 | noop 原始证据 | 解释 |
| --- | --- | --- | --- |
| 实际命令/收集 | GL:620–628，两个测试文件，Linux Python3.8.19、pytest7.4.4、7 items | NL:587–595，同选择器与版本、7 items | 窄套件，非全仓 |
| 来源参考 | GL:708–713：F2P2/P2P4 全过 | NL:789–795：F2P2 失败、P2P4 过 | 与 grading.json 各 ID 对应，无 missing/skip |
| 额外实际执行 | GL:707 的 TestUnprotect 通过 | NL:598–634 的 cache 可写断言失败 | 不在来源参考集，不能说 F2P=3 或“七项全部保护 reward” |
| 完成/退出 | GL:714–721，7 passed，RC0 | NL:796–803，3 failed/4 passed，RC1 | 解析计数7与真实收集7相符，失败来自断言 |

本轮实际阅读：完整 unit local、func unprotect、fs.py、gold/test patch 与上述 fixture 相关块；全部六个参考测试体；两日志的启动身份/HEAD/差异、测试恢复、安装关键段、全部失败栈及逐 ID 终态与末尾退出。依赖长清单只抽读，日志未逐行全读。哈希校验读取日志全字节但不冒称全文人工审阅。没有执行新测试或重新调用 parser。

## 7. actor 开发条件与交付边界

| 需要的操作/资产 | 公开依据 | 已有证据与缺口 | 最小待验路径 |
| --- | --- | --- | --- |
| 实际解释器导入当前 dvc | local.py 的 imports；setup.py:49–85 | grader editable /testbed、Python3.8.19；actor shell/PATH/激活未验 | 实际 agent shell 记录 id、cwd、sys.executable、dvc.__file__、git HEAD 与初态 diff |
| pytest/mocker 与顶层测试 imports | setup.py:110–133，conftest.py:3–8，httpd.py:6 | grader all/tests 已安装；actor 是否消费该派生镜像及 moto 修补未知 | 同身份公开 collect 与窄测试，区分依赖失败和题目预期失败 |
| chmod/unlink/symlink/hardlink 与可写临时目录 | System.py、tmp_dir/TestDvc fixtures | grader Linux 非 root 跑通；actor `/testbed`、tmp、home、文件系统链接能力待验 | 临时目录建立非空 foo 和两类链接，记录 mode、inode/content；不要用 root os.access 结果代证 |
| 资产、编译、网络 | fixture 本地生成小文本；gold 仅 stdlib | 无题目权重/外部服务；准备阶段固定 wheels，候选安装用离线资产；不得默认 actor 可公网下载 | 所需导入可达；本例不需起 SSH/HTTP 服务，也不需 GPU 或业务编译 |
| 提交合法业务修复 | fs.py 或 local.py；test patch 只两测试文件 | gold 已实际投影 fs.py；actor 冻结/提交本轮未验 | 修复在普通源码；不需写系统包或修改受恢复官方测试 |

public_hints 的“conda 已激活”和禁止改测试不是运行证明；当前环境说明区分字段可读与真正 system prompt。旧“测试修改永不计分”解释不能替代逐路径恢复事实，但本题合法修复无需改测试，未发现交付阻断。不给额外排除：`additional_exclusions=[]`。共享 parser/控制面不在本题重审；未发现题目特有控制文件捷径或测试 patch 混合业务文件。真实镜像 `.git`/未跟踪资产的答案可见性与完整工具消息未审，本导出无未来历史不等于容器已防泄漏。

## 8. 暂定处置与唯一优先下一步

`needs_review / static_review`，用途 `development_diagnostic`。通常 symlink 主例、行为断言与 gold 修复相符，现有最新 grader 对照可解释；没有证据把题目拒绝。保留三项限制：① POSIX hardlink 验收扩展与公开旧行为的范围歧义；② 参考六项/实际七项不同，内容与断链后置条件缺失；③ actor 条件、Windows 分支与实际消息未验。不是所有正确解、所有回归或正式训练/评测准入证明。

**唯一优先 CPU 对照（仅提案，尚未执行）**：先在将用于诊断的真实 actor 入口核身份/解释器/源码/权限，然后以同一固定 Linux 非 root 环境、fresh 临时目录，对 base、gold 和仅 symlink 直接 unlink 的窄替代方案作一个对照。每格生成内容 `cache-content-3620\n` 的源文件 chmod0444，分别建 symlink 与 hardlink 工作区输出；unprotect 后记录返回/异常、缓存 exact mode/字节、输出存在/非链接/字节/可写，修改输出后再次确认缓存字节未变；再通过既有 RH2 入口分别记录两个 F2P、四 P2P、额外 CLI 与总分。预期窄替代主 symlink 行为成功但 hardlink 新断言失败，若成立即可明确“修复原例”和“满足推广语义”的区别，仍需人作公开范围判断。不要把它自动称误拒，也不把空文件坏解作为必须先阻塞有限诊断的门槛。

暴露：主审已见本题全部私有补丁、参考、gold、environment_record、最新两角色原始运行与 public_read；历史仍未开放。不得把本稿给未来 solver。未知 token、人工决策成本、当前容器耗时均不猜数；账本旧安装/测试秒数仅为指定 grader 的历史事实。
