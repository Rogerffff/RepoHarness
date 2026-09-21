# iterative__dvc-3620 独立复核初判（封存）

2026-09-21。独立 reviewer；按 5839 → 9395 → 3620 顺序审查，前两题 initial 已封存。仅静态原件阅读与文件元数据校验，没有执行项目、安装、Docker、SSH 或模型；本文所有新增 CPU 方案均未执行。保存后不修改，三份 initial 全部完成前没有阅读其他角色结论。

路径约定：`R=.`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-3620`；`Q=同材料根/private/iterative__dvc-3620`；源码行号相对 P/base；`E=R/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3620`。

## 初判与用途

公开故障是 unprotect 在把链接转换成独立可写文件时，删除链接前先 chmod，间接使缓存文件变为可写。base `_unprotect_file → remove → _chmod` 的路径与题面准确对应。gold 让非目录删除先尝试 unlink，失败才走原 chmod 回退；正常 POSIX 文件链接路径上能避免不必要的缓存权限变更，且保留复制内容、删除旧链接、rename 临时文件、设工作文件模式的原顺序。指定历史 Linux 非 root RH2 运行支持这个正常路径：gold 7 passed，noop 在两个权限 F2P 及功能测试失败。

主要问题在评分保证：两项冻结 F2P 使用 `not remote.is_protected(link)`，但 `is_protected` 对文件不存在也返回 False。它们没有断言 unprotect 后输出仍存在、内容正确、可写、已经断开链接。能直接检查输出可写的 `TestUnprotect::test` 虽然执行，却没有进入 2 F2P/4 P2P。因而“把链接直接删除并返回”的破坏性错误实现有静态可通过全部冻结断言的路径。是否真的被 RH2 reward 接受尚未执行，不能声称已证实漏放。

建议为 `static_review / needs_review`；有条件作为 Linux 普通文件链接权限修复的 development_diagnostic 候选，先做该最小错误补丁对照、确认真实输出与评分一致。不可仅据 reward=1 认定 unprotect 功能完整，不能扩展为 NTFS/Windows、异常删除或完整文件系统回归认证。当前未发现 gold 在本题普通 POSIX 路径上的新业务回归，也未据此声称穷举所有正确实现。

## 暴露与材料身份

已读共用 reviewer/method/environment/template 卡，P 的 user_prompt/public_bundle/base_identity/environment_brief，Q 的 test.patch/gold.patch/grading/validation/run_refs/source_refs/environment_record。environment_record 暴露环境 verified_environment_pair、gold/noop 汇总、analysis/history 路径名；没有沿链接读旧汇总。前两题的原件/gold/本人已封存初判为既有暴露；未读公开角色、主审或历史质量结论，未读任何 public_read、analysis_before_history、old_findings_delta、card、screening_record、review、manifest、主计划、method_adjustments。

P/base_identity 声明 commit `e05157f8e05e856d2e9966c30a3150c26b32b86f`、tree `d4fa95ff32fb623e4bf12a3bf3098c7cc882fef3`、360 tracked entries、无 Git 元数据。公开/私有 base 一致；本次未重建整个 tree。标准库元数据校验确认 test.patch 与 grading 中文本完全一致，gold.patch 与 validation 中文本一致且 SHA-256=`54c21a8c1dbd18cabb0dc1176db6f06aba4c4d41d4282f242f5f658451da22f0`；两份指定 eval.log 哈希均与 run_refs 一致。

## 公开要求—断言双向表

| 要求/合理回归 | 公开依据 | 测试/决定性断言 | 覆盖与证据层级 |
| --- | --- | --- | --- |
| unprotect symlink 不把缓存改成可写 | user_prompt；remote/local.py:412–432；utils/fs.py:118–143 | F2P `tests/unit/remote/test_local.py::test_is_protected[symlink]`：foo/link 初始不受保护；protect(foo) 后两者受保护；unprotect(link) 后 link 不受保护、foo 仍受保护 | 真实本地 symlink，Linux 原 noop 最后 foo 断言失败、gold 通过；检查实际 mode，不是字符串/Mock |
| hardlink 的同类缓存权限保持 | CLI unprotect 帮助明确 hardlink/symlink，command/unprotect.py:25–27；同一个 `_unprotect_file` 分支处理二者 | F2P `test_is_protected[hardlink]` 在非 nt 要求 foo 仍受保护；nt 则允许源暂时不受保护 | 题面只举 symlink，但 hardlink 同一共享文件权限问题可从公开接口/源码合理推知；旧公开测试确实曾容忍副作用，此次纠正有技术依据，不直接判隐藏扩需 |
| unprotect 后工作输出存在且可写、缓存仍只读 | 题面复制→替换意图；remote/local.py:422–432；公开 CLI | 修改的 `tests/func/test_unprotect.py::TestUnprotect::test`：配置 hardlink，add，输出/cache 初始 os.access(W_OK)=False，CLI unprotect rc=0，输出可写；非 nt 直接要求 cache 不可写；nt 允许暂时可写再 status 修复 | 已执行，gold pass/noop fail；**不在冻结 F2P/P2P**。检查可写但未断言内容相等/写输出不改缓存；Windows 分支未执行 |
| 输出真的转成独立可写副本 | `_unprotect_file` 复制顺序注释；普通 unprotect 意义 | F2P 只有 not is_protected(link)，remote.is_protected:532–538 对不存在返回 False | 缺存在/内容/写隔离断言；“删除输出”错误候选可满足两 F2P 终态，功能测试能抓到但冻结集未列入 |
| 不破坏 chmod 的既有错误兼容 | remote.protect:452–470 | P2P `test_protect_ignore_errors[1]`、`[13]`：先 protect，再 Mock os.chmod 抛 EPERM/EACCES，再 protect 不抛且尝试 chmod；`test_protect_ignore_erofs` 抛 EROFS 时不抛且尝试 chmod | 三项全部已读；只覆盖 remote.protect，不能称覆盖 gold 新 `_unlink` 的 onerror 分支或 `_chmod` 重试 |
| 已有本地 cache 时 status(download) 不查远端 | `test_status_download_optimization` 自带行为说明 | 第四 P2P：Mock 本地 cache_exists=全部键，other_remote.cache_exists.call_count=0 | 原行为被保护，与链接删除错误路径无关 |
| 普通 remove、PathInfo、checkout/relink/目录内文件依旧工作 | utils/fs.py；remote/base.py:1051–1083；output/base.py:307–338；state.py:468–470 | 公开但未参与本题执行的 `tests/unit/utils/test_fs.py::test_remove`、`test_copyfile`；`tests/func/test_checkout.py::test_checkout_relink[hardlink/symlink]`、`test_checkout_relink_protected[hardlink/symlink/copy]` | 已抽查真实断言；这些不是本题冻结 P2P，不能借用作已执行回归证据 |

所有 test.patch 改动已读：只调整上述 functional 的平台条件与 unit 的源文件保护条件，没有新增 helper，也没有对新 `_unlink` 的函数名/调用次数作断言。冻结两 F2P、四 P2P 已全部逐条核对；原运行总 7 项，不能当成 7 个计分参考项。

## 源码、helper/fixture 与误拒检查

- 读完整 `tests/unit/remote/test_local.py`、`tests/func/test_unprotect.py`、`tests/basic_env.py:1–208`、`tests/conftest.py`；`tests/dir_helpers.py:73–154,203–251`。unit tmp_dir 在临时目录初始化 no_scm DVC；functional TestDvc 自建临时 no_scm repo，预置 foo 内容为 `foo`，并无 fake unprotect。tests/conftest 在收集时即导入 mockssh/SSHConnection/HTTP helper，但相关测试未启动 SSH/HTTP fixture。
- 源码读 `dvc/utils/fs.py:1–211`（unlink gold 对照、copyfile 的 reflink 或逐块复制）、`dvc/remote/local.py:1–90,131–205,398–489,516–538`、`dvc/system.py:1–240` 的创建/检测链接和平台差异；`repo/__init__.py:148–177`、完整 `command/unprotect.py`、`output/base.py:300–344`、`state.py:447–479`、`remote/base.py:1045–1084,1227–1250`。继续 grep 了 remove 的调用者，未声称全仓逐个审完。
- 额外旧测试实际读 `tests/unit/utils/test_fs.py:1–255`、完整 `tests/func/test_fs.py`、checkout.py:478–531；setup.py 的依赖/tests/extras。未执行这些回归测试。`RemoteLOCAL.CACHE_MODE=0o444` 是公开定义，精确模式断言有依据；但 mode 不等于 0444 不足以证明文件可写。
- 合理非 gold 实现可以在 remove 内直接 try/except unlink、只在相应失败条件下 chmod，或在 unprotect 层完成安全替换并保留一般 remove 语义；测试不要求 `_unlink` helper 名，不见确定的结构性误拒。若只对 symlink 分支做特判而放任同源 hardlink 缓存变可写，会被硬链接 F2P 拒绝；这是公开通用接口同类行为，不宜仅凭标题就判误拒。
- Windows 特例既出现在旧代码注释又出现在私有修订：nt hardlink 暂时改变缓存权限并在 status 后恢复。原测试不会接受“所有平台一律源不可写”的替代结果，但当前评分镜像是 Linux，Windows 分支未验。不能用这批日志证明跨平台所有合法实现均接受。

## 八方面覆盖与保留项

1. **公开需求**：题面具体根因/代码已给出；公开 CLI 明确 unprotect 跟踪文件/目录及两种链接。目标同时包含工作区副本可用与缓存权限保持，非只消除一个 mode 副作用。实际 CC 消息/hints 未捕获，环境声明不当作事实。
2. **材料/初始问题**：版本0.92与用户0.91.1的故障路径一致，补丁/原日志元数据一致。原 noop 失败位于 unprotect 后 cache 被改写的断言，而非 setup/权限不足或缺库。
3. **命中与漏测**：两 F2P 对文件权限真实生效；功能测试在执行集不在冻结集。缺存在性和内容可导致删除输出误判；未运行负对照，因此保留为高置信静态缺口。根因修复与 grader 环境有效分开。
4. **合理解误拒**：现有 mode 常量、CLI 两种链接为公开依据；测试没有 gold helper 结构锁定。未发现需要立刻判定的 Linux 误拒；未穷举平台/替代算法。
5. **回归/gold**：正常 POSIX unlink 成功时跳过 chmod，源码维持 copy-before-remove-before-rename 顺序，历史结果支持；失败时仍进入 `_chmod`，目录仍 `rmtree(onerror=_chmod)`，missing path 外层仍只吞 ENOENT。broken symlink、只读普通文件、目录/共享缓存所有权/不可删路径的行为未实测；不能把 remote.protect 的 errno P2P 当成 `_unlink` 覆盖。若 unlink 失败再 chmod，泛化到所有异常场景的缓存不变保证尚未建立，但不是已证实 gold 新回归。
6. **开发条件**：最重要是非 root 身份和真实文件系统能做 hardlink/symlink/chmod，root 的 os.access 会改变功能断言含义。旧 Python 与 pytest 插件/导入依赖需准备；所需文件在本地生成，不需网络资产/服务。actor 仍待验。
7. **交付/评分边界**：官方 patch 只改两份 tests 文件；原日志恢复该两文件再 patch。gold 改 dvc/utils/fs.py，ledger included_paths 正确、ignored_paths=[]；也有普通 local.py 源码替代修法空间，无需改系统包或被恢复文件。共享 parser/镜像答案资产/真实 .git 可见性未核，未设新排除规则。
8. **题目关系/用途**：在本题独立检查后、前两份 initial 已封存的时点，专门检索本包另两题公开原件，确认 **5839 的 base/dvc/utils/fs.py:123–140、9395 的同文件:55–72 已包含与本题 gold 相同的 `_unlink` try-first/fallback 逻辑**。这是“早题修复已出现于后题 base”的具体跨版本答案线索，不表示三题是同一个问题，也不反向修改前两份封存稿。若未来同一 solver 接触本包多个版本，应避免把它们当无交叉暴露的独立样本。本 reviewer 已见三題 gold/隐藏测试，仅用于 development_diagnostic，不是独立求解，不推测能力成功率或收益。

## 原始运行及其适用条件

E/{gold,noop}/ledger.jsonl 第1行：2026-09-19 历史真实 RH2 replay，derived recipe=`dvc-install-v1:iterative__dvc-3620`，实际 image=`sha256:820a5c7d4c7b28edebb1886834a74d4cfa1f058137ed76f210737a33f4cd1cc7`，不是 public manifest 本身。grader=rh2grader/54322、deny_all、2CPU/4GiB、64MiB shm、tmpfs1GiB、PID512；candidate apply_user=agent/54321 不代表 CC actor 验收。两次 observations import=/testbed/dvc/__init__.py，cleanup removed=true，reference missing=0。

- gold 原日志 `evallog_replay-er19-dv1-iterativ_9b423984.eval.log:227–231` 恢复官方两文件；`:603–610` DVC 0.92.1+e05157.mod、安装 rc=0；`:620–625` Python3.8.19/pytest7.4.4 运行 `pytest -rA tests/func/test_unprotect.py tests/unit/remote/test_local.py`，7 collected；`:707–718` 7 passed、2 warnings、test rc=0。ledger F2P2/2、P2P fail0/4、reward=1。
- noop 原日志 `evallog_replay-er19-dv1-iterativ_cf25aa49.eval.log:570–592` 同版本/成功安装/7 collected；`:613–634` functional unprotect 后 cache os.access(W_OK)=True；`:654–693,708–747` hardlink/symlink 两项最后 foo 仍应 protected 的断言失败；`:789–800` 四 P2P passed，三个 failed，rc=1。ledger F2P0/2、P2P fail0/4、reward=0；第三个 functional failure 不能当作另一个冻结 F2P。
- E/gold/recipe/recipe.json 将安装改为 editable `.[all,tests]`，无额外 compat pin，scope 明确 diagnostic spec/原 driver/projection/manager/tests。这里只复读原件；没有独立重跑、Windows 验证或真实 actor 验证。

## 逐题开发需求及后续 CPU（未执行）

| 必要操作/资产 | 公开依据 | 现有证据及范围 | 当前缺口 | 最小验证与预期 |
| --- | --- | --- | --- | --- |
| 非 root、本地链接与权限 | tests/func/test_unprotect 的 os.access；local.py 的 os.stat/os.chmod；System link 函数 | 历史 grader 为54322且权限断言按预期区分 | actor UID/工作区和tmp挂载、capability、链接支持未知 | 统一 actor 入口打印 id/pwd/Python/DVC路径，在临时目录对普通文件建 hardlink/symlink并保护；应有真实 mode/权限差异 |
| 导入旧DVC与测试收集 | setup.py；tests/conftest.py 顶层 mockssh、SSH/HTTP imports | 历史 Python3.8.19、pytest7.4.4、pytest-mock1.11.2 跑完 | actor 是否消费维修和可用解释器；无需真的启动网络fixture | 首先验证 `import dvc` 来源及窄测试收集；不能照当前新版本依赖盲装 |
| 验证正确行为 | 原例、CLI unprotect；同base旧测试 | 公共旧 test_is_protected/TestUnprotect **显式期待原有 cache 可写副作用**，合法修复可能使这些旧断言失败 | 真实 solver 是否理解旧测试预期被issue纠正；hidden patch不可见 | 建非空文件、保留cache内容/mode、链接后unprotect，检查输出存在/内容相等/可写/非链接、写输出不影响cache；不用要求修复后的旧公开测试全部绿 |
| 提交修复 | utils/fs.py 或local.py普通源码 | gold projection 接收fs.py | actor写权限和源文件初态待验 | 可提交源码即可，无需写环境前缀、修改官方测试或提交临时数据 |

**唯一优先下一步**：在适用派生环境且已核非 root 身份的私有 CPU 诊断入口，对照 gold 和“在 `_unprotect_file` 的链接分支只 `os.unlink(path)` 后返回、不复制/rename”的最小错误实现。应分别记录 7 项实际终态、冻结2F2P/4P2P和最终 RH2 reward，并追加原例输出存在/内容/写隔离检查。静态预期错误实现能满足 unit 的两个否定 protection 条件，却使 functional 输出可写断言失败；是否 reward 仍为1必须由实际评分确认。禁止把它作为 solver 解法，且本轮没有生成/执行这个候选。

若证实，应优先使已执行的功能约束进入有效参考集，并用存在性/内容/写隔离检查补足单纯 `not is_protected`；新标准仍需能接受安全复制/替换的合理替代实现。另行最小回归范围是 remove 的正常文件、PathInfo、不存在路径、dangling symlink、只读文件及按实际平台授权的失败回退；不把未经运行的这些检查填 pass。Windows只能在对应原生条件实测或明确保留未知，不能在Linux改 os.name 就声称通过。

本题初判封存。三题 reviewer_initial.md 至此完成；等待协调者统一开放第二阶段材料后才编写各 review.md。
