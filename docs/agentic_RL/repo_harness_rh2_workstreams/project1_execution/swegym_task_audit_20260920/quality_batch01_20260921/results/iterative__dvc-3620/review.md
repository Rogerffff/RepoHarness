# iterative__dvc-3620 独立 reviewer 复核

2026-09-21，三题统一开放后的第二阶段。初判 `reviewer_initial.md` SHA-256=`dd7fb9dc950bc1617873254f7f18ac4343a89babb315f3344250234f9cdb872a`，保持封存。本轮只静态阅读和核元数据，未执行项目、安装、Docker、SSH、模型或新 CPU 实验。

路径：`R=.`；`P=R/runs/swegym_quality_batch01_20260921_v2/public/iterative__dvc-3620`；`Q=同材料根/private/iterative__dvc-3620`；`E=R/runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3620`。源码行号相对 `P/base`。`GL=E/gold/eval_logs/evallog_replay-er19-dv1-iterativ_9b423984.eval.log`；`NL=E/noop/eval_logs/evallog_replay-er19-dv1-iterativ_cf25aa49.eval.log`。`O` 为本报告所在目录。

## 有界结论

同意主审保留 `needs_review / static_review`，可作已声明范围的 `development_diagnostic` 候选。普通 POSIX symlink 的根因、gold 的先 unlink 后失败回退策略、最新非 root grader 的目标分差相互对应；没有已确认 gold 主例缺陷或必然误拒。历史“root 令功能测试前置失败”的阻塞已不适用于最新引用条件。

主要保留两类独立限制：一是公开 issue 明指 symlink，而新验收同时改变 hardlink 缓存权限的旧期望；二是来源 2 F2P/4 P2P 没有证明输出存在、保留字节并断开共享关系，实际额外执行的 CLI 测试也不是冻结参考。Windows 删除失败回退和实际 actor 条件还未验证。不能把 7 passed 解释成任意候选数据安全、跨平台兼容或 actor 就绪。

与主审的判断强度有一处区别：独立初判更倾向把 hardlink 看作公开通用 unprotect 接口和共享 inode 根因的合理推广，不将它直接判作隐藏扩需；主审更突出旧 hardlink 测试明确允许缓存暂时可写的范围冲突。本轮承认后者是实在的语义解释空间，同时保持“没有已证误拒”的结论。CPU 可以测 symlink-only 解的行为与得分，不能替人裁定其是否已经满足全部公开义务。

## 本轮实际阅读与补记

完整读 O/public_read.md、analysis_before_history.md、old_findings_delta.md、card.md、screening_record.json；读取本题 history/refs.json 唯一指定 `H=R/docs/agentic_RL/repo_harness_rh2_workstreams/project1_execution/env_overnight_20260916/L1_dvc_1/records/iterative__dvc-3620.json`。screening_record 的一次输出有截断，随后单独补读 usage/costs 与前段各 check，未把截断结果当全文阅读。

沿 H 的本题引用读取 `S=R/runs/env_probe_stage1_20260910/ledger/logs/stage1_offline_20260910/iterative__dvc-3620`：gold/empty 的 `offline/a1/status_map.json` 全文；gold `test_output.txt:380–429,475–507,586–602` 和 empty `:446–468,488–497,544–556`；gold `eval.sh:1–18,60–73`。没有打开 3527、其他历史题、prescan、未来 Git clone、acceptance 聚合或其他角色未授权结论。没有独立查询主审说“旧候选账本没有本题行”的检索结果，不把它当自己已核的 UID 证据。

第一阶段已独立逐条读完全部 2 F2P/4 P2P 和额外 CLI、fixture/helper、关键调用者、gold 及指定原始运行，范围详初判。主审另外核对 S2 三份原行 124 和十份配方工件，这是其核验范围，本轮未独立重做。未重建全部 Git tree。

**初判遗漏的运行条件现已补核**：GL:132–140 记录工作区同时有 dvc/utils/fs.py 与 setup.py 修改；GL:211–221、NL:178–189 共同显示环境预先把 `moto==1.3.14.dev464` 改成 `moto==1.3.14`。因此两次运行不是完全未改的源码依赖初态；这项 setup.py 差异是共享环境准备，不能混进 gold 的业务修复或当作 actor 可自行安装成功的证明。gold 候选投影仍只有 dvc/utils/fs.py。初判没有写这一细节，现明确登记，不回写封存文件。

## 公开要求、测试/gold、主审与历史对照

| 主题 | 独立核对与裁定 | 原始依据和限度 |
| --- | --- | --- |
| symlink 主例及公开定位 | 与公开/主审一致：题面已指出 chmod 跟随链接影响缓存，公开代码足以定位 | fs.py:118–143 先 chmod 再 unlink；local.py:412–432 复制→删除链接→rename→设置输出 mode。题面详细根因是原始 issue 内容，不是未来 gold 泄漏，也不据此估模型难度 |
| 数据与解除链接 | 与主审独立发现一致：必须保留输出，复制字节且修改输出不影响缓存 | local.py:417–424 注释与代码，公开 checkout_relink 断言支持该要求；官方七项没有内容/写隔离检查。不能以权限结果代替完整数据后置条件 |
| 新增/修改的所有断言 | 两个 unit F2P 修改最终源权限；CLI 将允许缓存暂时可写及 status 恢复限定到 nt | 非 nt 两类链接源必须仍 0444；nt hardlink 保留例外。没有新增 helper 名、特定源码结构、精确调用数量限制；常量 0444 来自公开 CACHE_MODE |
| hardlink 范围 | 独立初判倾向合理同类修复，主审保留歧义；本轮维持两种依据并禁止报告已证误拒 | CLI 帮助列 hardlink/symlink、同一链接分支和 inode 副作用支持推广；旧 unit :57–61 与 hardlink CLI :27–34 明确容忍缓存可写，issue 没点名推翻它。可用于有限诊断，但不把推广说成逐字明示 |
| H 的“只跳过 symlink chmod 也能全过” | 不成立 | hardlink 路径若保持旧预 chmod，共享 inode 仍变可写，违反 hardlink F2P；NL:654–693 给出 base 相应失败。没有运行该候选，故只推翻静态全过预测，不虚报新得分 |
| 合理非 gold 结构 | 同意无特定 helper 绑定 | 在 remove 原位 try unlink、失败才旧回调的等价安排不需新增 `_unlink`；在 unprotect 层安全替换也有空间。每条路线仍须保留数据和一般删除语义，未逐个实际运行 |
| 四项 P2P | 独立与主审完整核对，范围窄 | download optimization 查 remote.cache_exists 未调用；两个 EPERM/EACCES 和一个 EROFS 查 protect 容错。它们不测 unprotect/delete 的 unlink 首次失败回退，不能按错误名相似就声称覆盖 |
| gold 完整性 | 普通 POSIX 主例有合理修复、历史实证；无新依赖/未交付 helper | 新 `_unlink` 先 os.unlink，OSError 才传 sys.exc_info 给旧 `_chmod`；复制/rename、目录 rmtree、外层 ENOENT 处理保留。未执行 Windows、并发和特殊 FS |
| 旧 root 功能失败 | 失败位置独立确认，当前环境已改变 | S/gold:495–498、empty:462–465 均在 unprotect 之前的 `os.access(self.FOO,W_OK)`；empty:494/551 有 pytest-of-root 线索。仅这些路径不足以独立证明完整 UID 配置；当前 ledger 则明确 rh2grader/54322，NL:631 的失败已移到 unprotect 之后 cache 可写，GL:707 CLI 通过 |
| H 的“安装正常” | 被原件推翻 | S/gold:383–426 有 PyYAML 无包、GitHub 解析失败、两个 requirements 不存在、editable build 无 setuptools；eval.sh:14 连续命令且没有 set -e，后项退出码不证明前项成功。不能把旧测试跑完等同安装全成功 |
| H 的“parser 无污染” | 被两份旧 status_map 推翻 | 都含 `Could: ERROR:`、`No: ERROR:`，九个映射项只有七个真实测试。最新 parser=7 且七个测试逐项出现，是另一环境/运行事实，不把旧伪键外推当前 |
| CLI 为什么不在参考 | 缺席可确认，历史生成动机未证 | Q/grading 只有六个 ID；最新额外 CLI 是实际 F→P。旧双侧前置失败不证明当年因这个原因被“剔除”；若以后纳入，需新参考版本，不能静默改源集合 |
| 通用 remove 与 Windows | 同意 H 提出的回退覆盖风险，拒绝把普通 Linux 增测等同跨平台证明 | Linux 可直接 unlink 只读文件，不触发 NTFS 失败条件。普通 remove/gc 成功不能证明删掉回退会被拒；需后续真实 Windows 或受控首次 unlink 权限失败，当前均无 |
| 3527 关系及同 ID | 本轮未核，不强制归同族 | H 的跨题原件未开放/未读；本题自身已经证明同 ID 随版本改变语义，索引应带 task/version，但这不自动证明另一题的派生/划分关系 |

`screening_record` coverage_limit 中 `remote/local.py:532–538` 的引用是正确的：它定位 `is_protected`，`:533–534` 在路径不存在时返回 False，`:536–538` 才检查 mode==CACHE_MODE。因此 unit 的 `not is_protected(link)` 既不证明输出存在，也不证明其可写。真正 unprotect 入口是 `:440–450`，复制替换是 `:412–432`；两处引用用途不同，不应把前者统一替换成入口行号。

主审提出“父目录权限导致 unlink 失败仍可能 chmod target”时已标作限制，没有声称实测。独立复核补充：通常不可写父目录会先阻止在同目录创建临时副本，不能直接作为能到达 unprotect 删除回退的简单反例；需要可达的失败设置才能确认该路径。当前没有因此确认新的 gold 主例缺陷。

## 运行、冻结参考与静态推断分开

本轮没有新执行。最新两份 ledger 的条件为 local-build image `sha256:820a5c7d4c7b28edebb1886834a74d4cfa1f058137ed76f210737a33f4cd1cc7`、dvc-install-v1、上述 moto 预改、离线 wheelhouse、Python 3.8.19/pytest 7.4.4、rh2grader/54322、deny_all、2 CPU/4 GiB、64 MiB shm。import 指向 /testbed/dvc/__init__.py，cleanup removed=true。apply_user=agent/54321 仍不代表 actor 开发已验证。

| 层 | gold | noop | 含义 |
| --- | --- | --- | --- |
| 实际命令与收集 | GL:620–628 两文件、7 项 | NL:587–595 同两文件、7 项 | 是窄实际执行，不是全仓 |
| 冻结参考 2 F2P/4 P2P | GL:708–713 六项通过 | NL:789–795 四 P2P 过、两 F2P 失败 | 当前 score 参考保护范围；没有 missing/skipped |
| 第七项 CLI | GL:707 通过 | NL:613–634 前置成立，最终 cache 不可写断言失败 | 当前确实执行且 F→P，但不能直接称冻结第三条 F2P |
| 完整退出 | GL:714–718 7 passed、RC0 | NL:796–800 3 failed/4 passed、RC1 | 不是由安装/收集失败制造目标分差 |
| 新错误/替代控制 | 未执行 | 未执行 | 删除后返回、空副本、symlink-only 均只是静态候选，不能写成已证 reward 或误拒 |

## 八方面收口

1. **公开要求**：普通 symlink 缓存权限保持明确；数据保留/可写/断链有公开实现和测试依据；hardlink 推广有合理依据也有旧约定冲突。真实模型消息、public_hints 注入仍未知。
2. **材料与初态**：base `e05157f8e05e856d2e9966c30a3150c26b32b86f`、test/gold、日志 hash 与原始 noop 失败对应；完整树未重建。本轮补足共享 setup.py 环境预改，不能把 base commit 相等当作工作区无差异。
3. **测试命中**：逐条核两 F2P、四 P2P、额外 CLI 所有变更，真实非空 fixture 避开空文件 hardlink 优化；链类型/权限主例可解释。输出存在/内容/写隔离仍缺来源断言。
4. **合理实现接受性**：无 gold helper/调用顺序绑定，等价错误回退可表达；symlink-only 的争点是需求范围，不是自动等于结构误拒。尚无执行过的合法方案被错误拒绝。
5. **gold/回归**：保留复制、重命名与删除失败回退，正常 Linux 两类链接修复得到历史支持；已读 remove/unprotect、output、state、checkout 等调用者和公开回归，不将静态阅读冒充它们被执行。Windows/异常/并发未知。
6. **开发条件**：核心资产为本地非空文本和链接，无业务外网/服务/GPU需求；顶层 conftest 的 mockssh/HTTP 包须能导入。actor 必须核真实非 root 身份、解释器/导入、tmp/工作区权限及链接语义，不能只继承 grader 成功。
7. **交付/评分边界**：普通源码 fs.py/local.py 可表达修复，官方仅恢复两个测试文件，无新增排除依据。旧公开测试包含被 issue 推翻的 symlink 行为，要求 solver 所有旧测试全绿会误导；不得把隐藏新断言送给 solver。镜像答案资产、Git/挂载、共享控制面未验。
8. **关系/用途**：独立初判已核到分配的 5839 base/fs.py:123–140、9395 base/fs.py:55–72 含本题 gold 的 `_unlink` 结构；顺序阅读会暴露未来答案，三个题并非同一 bug。此审核上下文已见私有/历史，不能充当未暴露 solver 或学习收益证据；未跟随未分配的 3527 原件。

## 后续动作取舍（均未执行）

第一步仍是实际 actor 的公开复现：核 UID、sys.executable、dvc.__file__、初态 diff（含 moto 环境差异），在 fresh 临时目录生成固定非空文本 `cache-content-3620\n`、chmod0444，再建 symlink 与 hardlink。记录缓存 mode/字节、输出存在/字节/模式与链接关系，改写输出后确认缓存字节未变；参考 public_read 的普通 symlink 复现即可，不向 solver 提供隐藏材料。旧副作用断言失败需按位置解释，而不是强迫修复回旧行为。

若下一步目的为**评分校准**，独立 reviewer 保留初判的一个优先私有 CPU 对照：同一已核非 root 条件，对照 gold 与“链接分支只 unlink 后返回、不复制/rename”的最小错误控制候选，逐项记录实际七项结果、冻结六项状态、测试退出码及最终 RH2 reward，并用上述数据后置条件检查。预计错误候选能满足 unit 的否定 protection，却令 CLI 的输出可写失败；最终 reward 是否仍为 1 必须由实际评分回答。候选只作用于自建临时测试资产，不是 solver 解法；本轮未生成、应用或执行它。这直接辨别“额外实际执行失败是否影响最终 reward”这一未知，也验证来源否定断言的不足。

这与主审优先 base/gold/symlink-only 的选择有区别：后者能量化 symlink 主例与 hardlink 推广的分差，但静态路径已很清楚，且 CPU 不能裁定公开范围，所以不把它作为有限开发诊断前的必做门槛。若协调者重点是记录范围分差而非评分校准，主审的对照依然有界可做；不需要同时执行两组或先扩大到全仓/跨平台。若只开展人工可复核的窄开发诊断，先完成 actor 与数据后置条件即可，错误控制亦非强制阻断条件。

若以后要强化来源评分，应独立评审纳入 CLI 及内容/断链后置条件的参考变体；若声明 Windows 兼容，再做可达的 unlink 首次失败回退检查。当前无新 CPU 结果、无参考改写、无路径排除或正式训练/评测准入结论。
