# iterative__dvc-3665 — 历史开放前封存分析

2026-09-21，B3 私有主审。仅静态文件/冻结归档成员读取与 stdlib 日志元数据分析；未运行/导入项目、测试、安装、容器、网络或模型。已读本题公开稿、test/gold、授权环境摘要及双角色原运行，未读本题 history/refs、质量旧记录、reviewer、B1/B2 或批次聚合。本上下文有答案暴露，不能作为 solver；所有下一实验均建议、未执行。

P=`runs/swegym_quality_batch03_20260921_v1/public/iterative__dvc-3665`，V=同批 `private/iterative__dvc-3665`，R=`runs/env_recipe_repair_20260919/dvc_install_v1c/tasks/iterative__dvc-3665`，路径相对权威 ROOT=${REPO_ROOT}。

## 1. 公开目标、身份与初態

base `a2de48bdfbba80a7e41e96a44c67d51ff36f0810`；沿用协调者完整材料身份验收。局部核 test.patch=grading.test_patch、gold.patch=validation.golden_patch；SHA256 分别 `7ce03f809e1158899c243c9d0c09dd47d6077f25d22b3a3b38b52aa05ce0b5a3`、`94e474298491aaa1142674a344416132ac19c5ed44124c1d932cd4e96b2969e4`。

题面要消除相对 cache.dir 在 Windows/Unix 保存分隔符不同造成的 Git 噪声；给出 Windows 手工改成 POSIX 可用。路径输入相对 cwd、保存相对配置目录的公开契约在 P/base/dvc/command/cache.py:53-57。调用路径是 CmdCacheDir.run(:7-11) → Config.edit(:342-357) → _save_paths(:315-326) → dvc.utils.relpath(:315-324)。后者用 os.path.relpath，因此 Windows 反斜杠根因静态成立；没有原生 Windows 实际复现。

实际 noop 并非完全 clean：R/noop/*4ffdaade.eval.log:132-139,186-198 显示 base HEAD 正确，但 setup.py 中 moto==1.3.14.dev464→1.3.14 是镜像初态改动；gold 也保留同改动 (:252-263)。两角色包版本均 0.93.0+a2de48.mod，不能用 .mod 区分 gold 生效。projection 的 noop included=[]、gold 仅 dvc/config.py，说明该 setup.py 差异不是候选补丁。原环境条件须连同这处差异保留，不能将其冒称干净 base。

公开可合理实现于现有 _save_paths 的局部 rel 闭包，不必新建 Config._to_relpath。Config.edit 重写无关配置时仍须保留稳定路径格式。remote URL 不能误改；绝对路径重新格式化、remote 相对路径同步统一有一定合理性，但不是题面独立明示要求。公共 hints/实际消息、禁止测试修改的描述仍按公开稿登记，未宣称其已进入 CC system message。

## 2. 完整需求—断言映射与主要争议

完整读 V/test.patch 的三个文件修改：cache 的绝对/相对断言，remote 相对断言，新增 17 行 unit 参数化；同两份 func 文件全文和全部 18 P2P 均已读。unit 无 Mock/专用 fixture；根 autouse 日志与连接池清理、TestDvc 临时 no_scm repo、tmp_dir/dvc fixture 已沿 tests/conftest.py、basic_env.py、dir_helpers.py 展开。未把 import SSH 库当作本题需要 SSH 服务。

| 需求/约束 | 公开依据 | 测试与关键断言 | 覆盖/冲突 |
| --- | --- | --- | --- |
| 相对 cache.dir 跨平台稳定且仍指向原目录 | 题面；command/cache.py:53-57；base func/test_cache.py:160-178 | 修改后的 TestCmdCacheDir.test_relative_path 比较 rel.replace(backslash,slash)，再 add 文件并核缓存有一个对象 | Linux 实际执行通过，但**不在冻结 P2P**；不触发 Windows 分隔符分支 |
| 原 cache 绝对路径可用 | base func/test_cache.py:152-158 | 修改后 test_abs_path 比较 dname.replace(backslash,slash)，属于 P2P | Linux 有保护；Windows 格式比旧公开测试更强，原题并未明确要求绝对路径归一化 |
| 本地 remote 相对路径；保留 scheme URL | config.py:318-331；func/test_remote.py:41-66 | 修改后的 TestRemote.test_relative_path 为 P2P；SSH unit 输入原样保留；remote://引用 P2P | 本地 remote 统一是共享路径合理扩展，但与只修 cache 的设计范围存在待审边界 |
| cwd 相对 cache 转换 | 原 _save_paths 闭包及 CLI 契约 | F2P `test_to_relpath[cache-../cache]` 与 `[../cache-../../cache]`，调用 `Config._to_relpath("./config", path)` | 断言值是已有相对路径语义；**方法名/签名在 base 与题面不存在** |
| 绝对路径保留；URL 不相对化 | base config.py:318-324 | F2P `test_to_relpath[/testbed-/testbed]`、`[ssh://some/path-ssh://some/path]` | Linux cwd 动态生成 /testbed；直接 helper 要求仍无公开依据 |
| 其他 cache 回归 | 两 func 文件旧行为 | P2P 的 TestCache.all/get、坏 dir-cache、default type、外部 remote reference、无值命令，加 abs 共7项 | 本地缓存/配置、错误出口有实际保护，不验证 Windows |
| remote 回归 | func/test_remote.py | 其余11 P2P：add/list/remove、overwrite/default/show/remove-default、relative/referencing、modify-missing/validation、dir checksum key-order | 均读输入/Mock/断言；checksum mock 比较两种键顺序属真实旧行为，不等于本题跨平台覆盖 |

两项决定性静态问题：

1. **误拒合理实现**：4 个 F2P 全部强制新增私有 helper。把 POSIX 持久化直接加入现有 _save_paths 的闭包可满足题意，却仍没有该方法；noop 日志 :630-687 的 4 个 AttributeError 是方法缺席的实证，不能写成“已复现 Windows bug”。这不是仅与 gold 补丁形状不同的偏好。
2. **漏测实际目标**：Linux 的 29 个旧功能用例在 noop 已全通过，新增4项只测当前平台路径。添加一个未被 _save_paths 调用的 helper（复用旧相对化语义，甚至完全不加 Windows POSIX 转换）静态上可满足4项且保留 Windows bug。未做候选运行，故记录为高置信静态反例路线，未称已验证 reward 假阳性。核心 cache relative 测试还在参考集之外；即便额外普通 pytest 失败，也不能自动视为冻结 reward0。

## 3. gold、回归与执行/解析/计分三本账

gold 只改 dvc/config.py，提取 helper 并用已公开 PathInfo.as_posix。其平台实现按 flavour.sep 替换（P/base/dvc/path_info.py:23-43），避免任意替换 POSIX 合法反斜杠；先保留 scheme URL，relpath 跨盘处理仍来自原 utils:319-324。_load_paths/RelPath 和 edit/save 调用能保持相对配置重写。无新依赖，import 格式调整无行为意义。与公开绝对字符串旧断言的变化需按输出规范审，而不是认定值位置被破坏。没有原生 Windows/UNC/驱动器或 symlink 行为运行证据；不能以 Linux gold33通过认定 Windows 全面正确。

相关公开阅读补充：func/test_config.py 全文（配置层级合并、非法键）；cache.py:1-75 与 remote/local.py:36-84 的实际消费者；command/config.py:1-81、command/remote.py:1-75；path_info.py:1-100 与 unit/test_path_info.py:60-101（已有纯路径 Windows 模拟）。后者既未被本次选择也不验证 Config 接线。全仓、所有 remote 后端与平台回归未查。

本题两 ledger（R/gold/ledger.jsonl:1、R/noop/ledger.jsonl:1，attempt1、run_id er19-dv1-iterative__dvc-3665-gold/noop）：

- **执行**：Linux Python3.8.19、pytest7.4.4；命令分别在 gold :669/noop :604，为两个 func 文件加 unit/test_config.py。实际 collected=33；gold33 passed、RC0（:1705-1742）；noop4 failed+29 passed、RC1（:1713-1750）。4项全部在 helper 缺席失败。含18项P2P的完整状态摘要已逐一对应。
- **解析**：ledger num_parsed_tests=42，不是42个执行测试。已获协调者许可，只读同一 dvc.tar.gz 内精确成员 `src/repoharness2/envpack/swegym_parsers.py` 全111行（SHA256 `995bb6aae58a94f9553946c2f9aea59a158ad4fdf4d7fc0137802c11362b2276`）与 scoring.py 的文档/状态字段、v2和outcome段至309行相关片段（SHA256 `b6c8b9bd3e9cac604bc0d03b0b243ef9646de369e94bb6a65e60eadd3a64f5ab`）。parser :44-55 以状态词 startswith 和第二 token 当键，接受捕获输出的 ERROR/ERROR:。仅用 stdlib 分行/分词对日志做元数据比对：33真实nodeid + 9非测试键 =42，两角色一致。9键为 dir、the、configuration、failed、dvc.remote.base:base.py:304、dvc.cli:cli.py:93、dvc:main.py:51、dvc.remote.base:base.py:568、dvc.remote.local:local.py:540；gold原证据 :786-793,946-953,1091-1098,1362-1494。它们不与本题参考碰撞。没有导入/运行归档代码。
- **冻结计分**：4 F2P+18 P2P=22个引用，missing/skipped=[]、段外0；gold4/4与18/18→reward1；noop0/4与18/18→reward0。scoring.py:250-269 只将引用清单送 report，11项真实额外测试和9项非测试键没有自动加入评分。11额外项包括最相关 TestCmdCacheDir.test_relative_path，以及 ExternalCacheDir.test、SharedCacheDir、CacheLinkType、shared_cache两参数、uppercase remote、partial push/pull、too-many-open-files、no-cache external-dir、push-order。计数差异可解释，但 parser 对业务日志误识别应作为观测限度保留，未发现本题分数被这些伪键改写。

## 4. 开发环境与交付边界

授权 environment_record 的 verified_environment_pair 摘要已见，未追 analysis/history 指针。原输入 `dvc_install_v1c/recipes/iterative__dvc-3665.json` 指定 `pip install -e '.[all,tests]'`，无 compat/trusted追加；前题已读的同一 wrapper:61-86 匹配并替换两个脚本，逐run recipe是输出。逐题实际消费再次核：gold日志:463-466,650-659；noop:398-401,585-594，离线 wheel链接、editable成功、安装RC0，导入观测 /testbed/dvc/__init__.py。Dockerfile仅 COPY wheels；不能从它推出已安装。

| 开发需要 | 公开依据及现有证据 | 缺口/建议（未执行） |
| --- | --- | --- |
| Python、configobj/funcy/voluptuous、DVC CLI与源码注册 | setup.py:49-85,148-175；grader本题安装和收集成功 | actor实际解释器/导入源/PATH待验；打印 sys.executable、dvc.__file__ 后运行公开 Config.edit/CLI |
| 本地可写repo/cache、临时目录、pytest插件/资源限制 | basic_env.py:78-95,153-156；tests/__init__.py:3-36；conftest imports | actor权限/ulimit待验；无需外部服务或云账户；根conftest导入mockssh不等于此测试要开SSH |
| Windows路径语义 | 题面；公开PathInfo Windows用例 | Linux Docker不能自动提供Windows复现；原生Windows优先，或精确控制 ntpath/PathInfo 的窄模拟，并明确不是完整CLI平台验收 |
| 安装资产/网络/资源 | grader54322、deny_all、2CPU/4GiB、64MiB shm；editable成功 | actor54321不继承prefix写权；目标镜像和旧/work重定位待准备，context/wheel payload本地未留；准备依赖可固定，题意本地操作无需运行期公网 |
| 合法交付及评分控制 | gold投影dvc/config.py、ignored=[]；3个官方纯测试路径，恢复旧2个并新增1个，attest OK | 源码不被恢复；additional_exclusions=[]。未验真实actor的Git/镜像/答案可见面，不能声明无泄漏 |

固定grader镜像 `sha256:27e0f845f9702c664a23787619c39469b0ac3bb2c98216e79ed49f7f8558bd7a`，两ledger env_qualification=absent、cleanup removed=true、无stage_error。历史归档成员属于 dvc_install_v1c，当下 ROOT/rh2 不是这些日志的代码身份证据。

八方面范围：公开目标和材料已核；全部新增/修改断言与18 P2P已核；发现私有helper误拒及平台漏测；相关gold/调用者已查而Windows未验；grader与actor分账；官方恢复无业务源码交集、评分计数边界已追；本题为跨平台持久化bug，未审跨题谱系/预训练污染/模型能力与成本。无本题题面答案代码线索，但真实可见资产未知。

暂定 **needs_review/static_review**：有实质题意—测试争议，暂不列普通能力探针候选，也不凭静态推断自动改题/reward或宣判不可恢复。唯一最有区分力下一步：对“在现有 _save_paths 内直接归一化、不新增 _to_relpath”的合理修复，做一组窄 Windows 公开路径行为与冻结RH2评分对照；预期行为正确而4项方法断言仍失败，需实验确认。公开行为检查应包含配置再次编辑后仍保持POSIX与缓存位置；无须全仓测试或额外通用攻击。
