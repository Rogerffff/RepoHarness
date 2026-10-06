# Conan 13403：GNU 环境与公开 actor 诊断范围复核

2026-10-03。非作者 Falsifier / Simplifier；本次配置为 GPT-6.1 Sol / high。**本次公开开发缺口可以收口：v3 已排除工具缺席与默认 profile 缺席，真实 Conan CLI 到达原 issue 的 `Autotools.autoreconf()`，观察到缺少 `configure.ac` 的原目录行为。没有发现需要增加新环境或重跑历史矩阵的阻断项。** 此结论仅覆盖固定 GNU 镜像及公开 baseline devcheck，不是 cloud-v4 测试、正式评分、完整 solver 输入或训练资格的验收。

## 上下文与核查范围

按根 AGENTS、协作协议及 review-standards §10.4/§10.5 执行。收到的限定任务已说明 cloud-v4 有效补丁字节不变，以及这次仅诊断公开开发路径；该说明不作为本次发现的证据。先读取公开 `user_prompt.txt`、base 的 `autotools.py`、CLI `build.py`、ProfilesAPI 与 ProfileLoader，再读取 v3 命令和原输出，随后核对环境层、v2 环境对比与作者 audit。没有参与这些材料的生成，未重审 cloud41 候选或私有测试语义；不是对全部题目材料的 fresh 盲审。

只读本地原件与源码，未运行 GNU/Conan 实验、Docker、远端作业或外部搜索，未修改输入和历史 evidence；唯一写入是本报告。另执行了本地静态解析、文件 SHA 比较。主要读取入口：

- 公开要求及源码：`runs/swegym_quality_expansion_20260925/public/conan-io__conan-13403/user_prompt.txt` 与其 `base/` 中的 GNU、CLI、profile、build 执行和 subprocess 包装代码。
- v3 固定命令：`runs/category2_repair_20260929/conan_cpu_20261003/baseline_actor_13403_r5_gnu_v3/public_commands.json`；相应 `_evidence/baseline_actor_13403_r5_gnu_v3/` 的 `output/captures/{public_gnu_cli.out,identity.out}`、plan、preflight、prepared_identity、attempt、activation、命令桩和实际 messages 请求。
- GNU 层：同运行根目录的 `image_prepare_13403_gnu_v2_evidence/image_prepare_13403_gnu_v2/` 内计划、Dockerfile、准备脚本、deb manifest 与 receipt/download/build 原件。
- v2 对比：`baseline_actor_13403_r5_gnu_v2_evidence/baseline_actor_13403_r5_gnu_v2/environment_identity.py` 及 `environment_identity/` 的比较、两边原输出和清理证据；v2/v3 与环境层 audit。
- 当批题卡、actor 接续和 preparation 仅用于识别历史口径与剩余边界；其中“v3 尚未运行”的旧文字不覆盖这次已完成的 v3 原件。

## 事实与对抗性核查

### 1. 工具与 profile 缺席已排除，CLI 失败符合原问题

**标签：`test_only`，限定为 RH2 固定命令桩的公开 baseline devcheck；其中真实 CC 与 Conan CLI 确已执行并观察到目标失败，但未覆盖完整 solver 或正式评分入口。处置：`accepted`，接受该窄诊断收口。**

原 issue 要求是在 build 目录放 `configure.ac`，即使调用者先 `chdir(self, self.build_folder)`，`autoreconf()` 仍错误地去 source 目录；用户不希望靠修改 recipe 的 source_folder 解决。v3 临时 recipe 保留同一 `build()` 调用，另用公开 `layout()` 将 source/build 分开，只向 build 放入 `configure.ac` 和 marker；没有引入修复 API、私有断言或答案信息。

原日志依次给出：

| 对照 | 原输出 | 能排除什么 |
| --- | --- | --- |
| 实际 GNU | `/usr/bin/autoreconf`、Autoconf 2.71；Automake 1.16.5 | actor 路径中的工具完全缺席 |
| 直接在 build 执行 GNU | `DIRECT_GNU_END 0`，命令还要求 `build/configure` 实际存在 | 当前 fixture 不能运行 autoreconf 的解释 |
| Conan install | 显式 `-pr:h native-profile -pr:b native-profile`，两组 settings 打印，退出 0 | 工具链生成与 profile 解析的前置失败 |
| Conan build | 同一组显式 profiles 已打印；`Calling build()` → `RUN: autoreconf --force --install` → `autoreconf: error: 'configure.ac' is required` → CLI 退出 1 | v2 漏 profile 时未到目标调用的解释 |

源码链是 `commands/build.py` → `local.build()` → `run_build_method()`（先进入 build_folder）→ recipe 的公开 `chdir(build_folder)` → base `Autotools.autoreconf()`（再次硬编码 `chdir(source_folder)`）→ `ConanFile.run()` → `conan_run()` → `subprocess.Popen(cwd=None)`。`chdir` 通过 `os.chdir` 生效，`finally` 恢复调用者目录。因 fixture 的 source 为空，目标调用报缺 `configure.ac` 与这条链一致；直接正对照已证明 build 中的输入可供同一 GNU 工具处理。

这里的目录归因来自**原日志加固定源码调用链**，未直接记录 GNU 子进程的 `getcwd()`。不能把它描述成另做了一次 cwd 系统调用探针。现有证据已足以证明原路径可达；只为增加目录打印再跑一轮并非本次收口的必要条件。

v2 的 build 缺默认 profile 是诊断准备错误，不是 Conan 13403 原缺陷。v3 GNU 命令与 v2 的逐行差异只是在 build 参数补 host/build profiles；同时省去已通过的旧单测。v2 的失败应保留，不与 v3 的目标失败合并为同一类证据。v3 外层包装退出 0 表示正对照与**预期 baseline 失败**都满足诊断断言，不能写成原实现已修复。

### 2. 环境改变有边界，源码与 Python 版本清单证据充分

**处置：`rejected_with_evidence`，驳回“这是换源码或更新 Python 依赖后才出现的不相关失败”的当前解释；不声明整个环境完全不变。**

环境计划固定原 manifest digest 与 source config `sha256:dffa4bbcef5c3bae8ff2328524c4d70bebb0e6d45d6067ac064f12881987c383`。APT 原输出为 `0 upgraded, 5 newly installed, 0 to remove`；新增包是 Autoconf 2.71-2、Automake 1:1.16.5-1.3、m4 1.4.18-5ubuntu2，以及 autotools-dev 20220109.1、libsigsegv2 2.13-1ubuntu3。两个附加包由依赖解析引入，不是诊断错误后继续试装的无关工具。离线 Dockerfile 仅复制 deb、`dpkg -i`、要求 `dpkg --audit` 为空并删除该目录，没有源码覆盖或 pip 操作。下载容器实际状态退出 0，离线构建退出 0。

v2 的两个无挂载、断网 root 容器对比得到相同 HEAD、干净工作树、960 个 Git 跟踪文件内容摘要和完整 `pip freeze --all`：

- 跟踪内容 SHA：`ea1a479dc6dd1d0dd3518f775e96c3ab97108b34766f6de99b8ffdd970768e98`。
- freeze SHA：`db12cb8fcc4a16153a0c100d97788a2633ffd0e9a575d556572385d82aa2ed1d`。

这足以支持“Git 跟踪源码内容与 Python 包版本清单不变”。freeze 不是包文件逐字哈希，检查也未覆盖所有忽略文件、权限及完整原生依赖树，因此“全部依赖字节不变”或“全文件系统只有五处变化”都超出证据。root 对比不替代 actor 权限证明；v3 的独立 identity 原输出确认 UID54321、Python 3.10.14、Conan 2.1.0-dev 从 `/testbed/` 导入、固定 HEAD 与干净状态，activation 检查通过。

v3 plan/preflight/attempt 均固定派生 config `sha256:b40849e11f0b85cc14a243ede47148c2b9bd7f49a8898640879ad724dd7ff4ff`，可复用该 v2 环境对比。第五版 release manifest 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`，preflight 核 837 成员；prepared_identity 绑定本次 attempt。上述身份没有替代尚空的正式环境登记。

本审查重新计算环境层 17 件、v2 52 件、v3 34 件回传文件的 SHA，均与各自 remote audit 相符；三组属于不同证据范围，不能相加为唯一测试总数。v3 本地命令与回传命令字节相同，SHA 为 `48038d3a0c2a32054856cf484cefe312b2fd5358d8e54cad51fdca4a38b359df`。清理字段显示相关下载/对比容器删除成功、查询无残留；v3 actor 的容器、stub 和残留记录也已收尾。这是原件静态核对，没有重新实测机器状态。

### 3. 公开范围没有被改成更强的产品要求

显式 Linux profile、临时无依赖 recipe、分离 layout 与最小 Autoconf 输入是让原 issue 示例在指定 base 可执行的诊断支撑，没有改变“autoreconf 应能选择目录”的要求，也没有向 solver 提供新的私有答案。profile 的 gcc 11 与 issue 所述 gcc 8.5 不同，但此输入没有编译步骤，不能声称复现了原作者完整系统。Python/Conan 版本也按指定 base 与镜像运行，不是原 issue 所述 3.6.8/2.0.1 的逐项复刻。

实际 messages_000 的用户内容是固定 devcheck 指令，命令由桩安排；prepared/prompts 中保存原 issue 不等于原 issue 已送给求解模型。本次没有验证完整 issue/hints 的真实输入交付、模型自主求解、正确修法或 cloud-v4 私有测试。`interpreter_in_tool_result` 和 `bashenv_denied_for_agent` 两个泛用 marker 仍为 false；本报告只用实际 identity/activation 支持解释器身份，不将它们改写成全部权限检查通过。

## 更小充分方案、代价与建议

| 选项 | 判断与代价 |
| --- | --- |
| 删除真实 GNU 开发能力 | 只保留记录器测试可省环境层，但无法验证原 issue 的真实 CLI 开发路径，不足以满足这次已授权目的。 |
| 递延到正式验收 | 正式登记和评分应留到共同 consumer 的闸门；已有 v3 窄证据现在可收口，不必将开发缺口继续挂起。 |
| 进程 fail-stop | 工具或 profile 真缺席时立即失败是合适的诊断保护；两项已被 v3 排除，不能单靠外层退出替代原问题证明。 |
| 最小局部处理 | **推荐：接受现有固定层与 v3 证据，记录边界，停止扩实验。** 本轮只补 build 的 profile，既有环境和通过的旧单测可复用；没有新增恢复 owner、状态机或 fallback。 |
| 完整恢复或更大环境 | 新增自动 detect、网络补装、重建完整工具链或历史 41 项重跑都会增加漂移与成本；当前没有需要这些机制的证据。 |

五 deb 是此次“Autoconf＋Automake＋m4”请求的依赖闭包，不等于原问题理论上最少包数。该极简输入未用 `AM_*` 宏，仅装 Autoconf/m4 及所需依赖可能足够；本次未实验，不能宣布三包方案已验证。为减少两个小系统包重新构建与审查，无助于当前缺口收口。保留既有固定层的代价是约 4.2 MB 的 APT 所报新增空间及额外工具可用性；若正式登记要主张“最小配方”，应把它限定为当前请求的闭包，不需现在扩大工作。

一项非阻断性简化点按 `no_fix_accept_residual_risk` 处理：自动断言目前是 CLI rc1 加包含 `autoreconf`/`configure.ac`，单看该断言不足以排除未来其他错误；当前完整原输出明确给出 GNU 的缺文件错误，静态调用链也吻合，因此不足以阻断本次。以后自动消费结果时保留同一段完整输出即可，不必新增 runner 或恢复机制。

**事实更正（2026-10-03）：** 本报告初版关于 fixture 含字面反斜杠 `n` 的 finding 判断错误，现已撤回。重新读取 v3 本地及回传的 `public_commands.json`，先 `json.loads` 取得 GNU 命令，再去掉 Python heredoc 边界、`ast.parse` 并对 `write_text` 的 Constant 作 `ast.literal_eval`：`configure.ac` 字符串包含 3 个实际换行、0 个字面反斜杠 `n`；marker 包含 1 个实际换行、0 个字面反斜杠 `n`。两份命令 SHA 均为上列 `48038d3a0c2a32054856cf484cefe312b2fd5358d8e54cad51fdca4a38b359df`，无需修改 fixture 或追加实验。JSON 文本中的转义表示不能当作最终写入文件的字节。

## 停止条件与仍未知内容

本次可停止在“固定 GNU 环境下，UID54321 的真实 Conan CLI 开发路径可达原目录失败”；原 v2 profile 缺口已由 v3 收口，不建议新环境、重复旧单测或 cloud41 全量重跑。当前无阻断性 P0/P1 finding，也未改变 reward、mask、分组或样本拒绝分布。

仍未知且不由本报告补齐：完整 solver issue/hints 交付；正确修法在真实 GNU 下的表现；cloud-v4 私有断言与正式 consumer 的评分；正式环境登记、正式 CPU 题级矩阵及训练准入。GNU 子进程 cwd 未直接采样，Python 包文件逐字完整性也未检查。应保留这些边界，不将窄开发诊断升级为整题完成。
