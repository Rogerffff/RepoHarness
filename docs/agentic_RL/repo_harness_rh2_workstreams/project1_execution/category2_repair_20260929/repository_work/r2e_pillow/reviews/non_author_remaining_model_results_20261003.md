# Pillow 剩余两题：双模型首轮非作者结果窄核

2026-10-03 / Codex。**结论：PASS，带下述证据限度。** 四次首轮求解和正式评分均完整，原 reward 可用于本轮普通诊断；两份 Qwen 候选在公开要求及既有合理边界内正确，两份 Coder 候选确有实现缺陷。未发现需要重评分或回到题级 CPU 修订的阻断。这里的 PASS 指原件及解释通过复核，不把错误候选判为正确，也不授予训练、留出或稳定能力资格。

| 题目／模型 | 独立重解析 | 原 reward | 候选行为结论 |
| --- | --- | --- | --- |
| 3a61／Qwen3.6 | 74/74 匹配 | 1 | 保留完整 RGBA 条目及 alpha，像素索引查表仍用 RGB；本次范围正确。 |
| 3a61／Coder | 71/74 匹配 | 0 | 只取 RGBA 的前三字节，输出仍为 RGB；原公开恒等比较及两项合理扩展失败。 |
| a682／Qwen3.6 | 93/93 匹配 | 1 | 在透明值转换处捕获 TypeError，随后继续写 GIF 必需头部；本次范围正确。 |
| a682／Coder | 92/93 匹配 | 0 | 提前返回跳过局部图像描述符和最低码宽；公开满 256 色例写出后无法正常重开。 |

## 1. 身份、范围与接触史

我是本包 CPU 及模型结果的非作者核查者，未编写本轮候选、题级修订或执行入口。本次接续请求仅要求核这两题的四份已返回首轮结果及随后提供的作者派生读回。我已接触三题 CPU 私有正确解、错误对照、隐藏测试、既有审查、执行者审计和题主初读；因此**不是 fresh public reader**，不能把本报告作为干净上下文的公开可理解性盲审。

范围依 `remaining_workflow_20261002.md`、`repository_work_packages_20261002.md` 的既有题级标准：复用已验 CPU 矩阵和材料，不机械重做静态角色链。只读取本地原件，执行 JSON、SHA、tar 成员、纯日志解析和 diff 字节核对；未导入或执行候选 Pillow，未 SSH、启动容器／模型／实验、重评分或修改旧报告。唯一写入为本文件。

两道题的完整 ID 分别为 `pillow__3a61c9e95e5c0a2da5736956e2dbafa57a9ede07` 和 `pillow__a682ceaf47abbe28dc70c6bd4aab06f8f3f4ac90`。本报告不重新判定 2d01 的历史模型结果。

## 2. 原件入口与固定材料

以下路径均相对仓库根目录。独立计算两份总回执原文件 SHA256，与派发值一致：

- `runs/ordinary_gpu_probe_20261002/receipts/r2e-pillow-3a61-cpu-v1-20261003_two_model_v1.json`：`161953141a8ce5a7be3bf8d99d50dc6ea7e858fbf9bca45926aa2c14c5833684`。
- 同目录 `r2e-pillow-a682-cpu-v1-20261003_two_model_v1.json`：`9752ca2f38a12564fb99af97eafc2a1f1431e867cc0d234b7766e6467168fb0e`。

每份回执要求 `qwen36=1, coder=1`，恰有两个不同 job，无未执行项。本次逐项核回执所列 SHA 引用，均匹配；但没有仅凭 `safe_closed` 或作者摘要采信成绩。实际读取的四个原件根为：

| 本文简称 | 原件根（前缀 `runs/ordinary_gpu_probe_20261002/remote/`） |
| --- | --- |
| 3a-Q | `queue_v10/results/gpu1003-pillow3a61-qwen36-a1/` |
| 3a-C | `queue_v16/results/gpu1003-pillow3a61-coder-a1/` |
| a6-Q | `queue_v10/results/gpu1003-pillowa682-qwen36-a1/` |
| a6-C | `queue_v16/results/gpu1003-pillowa682-coder-a1/` |

各根的决定性原件是 `attempt/frozen/{frozen_patch.json,baseline_manifest.json,baseline.tar,baseline_census.txt}`、`attempt/candidate/*.diff`、`attempt/trajectory.jsonl`、`attempt/attempt.json`、`input_check.json` 和 `grading/{projection.json,baseline_rebuild_census.txt,report.json,status.json,eval_logs/*}`。

CPU 依据仍为已验 `rgba_gif_inputs_core_v1/` 与三份 CPU 结果 core，详见原 `reviews/non_author_cpu_results_20261003.md`。两题固定 R5 发布 `runs/category2_repair_20260929/releases_20261003/r2e_078_079_swe7_git_candidate_v1/`，本次再核 `manifest.json` SHA 为 `80ee228dbe7497b65354f817df689e4819497f5b1152d1143e26fa4be2ed42f9`。3a61 的原 C1 正对照和原 gold 负对照、a682 的原 gold／alt_typeerror 等既有结果继续复用，不计入模型成绩。

GPU prepared 原件在 `remote/prepared_r2e_four_v1/{pillow3a61,pillowa682}/`。逐字段比较其 `private/host_grading_views.jsonl` 的整份 `grading` 与 CPU `rgba_gif_inputs_core_v1/prepared/rgba-gif-release-v5/private/host_grading_views.jsonl` 对应行，**完全相同**，包括 base、测试文件 SHA、树摘要、expected 原字符串、入口、parser 和修订号。两题公开 `rollout_task_views.jsonl` 内的整份 `public` 也与 CPU 面完全相同。

| 材料 | 3a61 | a682 |
| --- | --- | --- |
| 修订号／参考键 | mr-070 + mr-071／74 | mr-072／93 |
| expected 原字符串 SHA | `af126a3c513f11efd3f78a89ff5f601a1c9bf401d078d43d569b2dfcc6650304` | `a465b6c99cb3be23e4f9d9a4f602d6caa2ceea228f524532938a535f7401a096` |
| 隐藏测试树 SHA | `9305a1b07a873927dd32d3fca434e5dba43a3f28049b05f9304f47520661cd04` | `2cbad6d046d3b725d4fa33ccc7ba8516236a84fdca735b0644b60b41ac013114` |
| GPU prepared manifest SHA | `2a9ed537f5f19c723fc2bb4614abfa0a4ca95fc000810327028523b70aa9cb8a` | `9de4f4de76e463098e8c5b6dc5d69bd563c0c3cf0b84ef25e6a6b3a7607d1733` |
| GPU host grading 文件 SHA | `631418ee70905e540301364c94acd778472a27a06f01b4d6828b427611b395c7` | `c5c7c66418f828bf648c5f5d328f9510197643c3c8a0022bf1ca9d8594883339` |

两题正式 `run_tests_sh` SHA 同为 `8285765fcf1a4ec23ca55ad4781a064d121b58266ef5c5e22c681f6ece616aaf`。prepared 公／私文件摘要、manifest 行数、各 attempt 的输入摘要也相符。

GPU 实际镜像是新宿主构建的身份：3a61 为 `sha256:66c2d1a2008bf758c940e9a753acb7ce7473af2d29026bfc4ad1bcce558cbc15`，a682 为 `sha256:222f475344dc8da53b6319e1cf8269c7142532d94474875c4dde0ee71bea3ade`。同题两模型一致；构建 facts、overlay、attempt 的 image_identity 与基线记录一致。3a61 的 HEAD 是 `355820742bc2ca8a90d9c25661e8988cbd7cb5de`，a682 是 `7a1e28404d692d4a7fed33dc67019a1d8c4bf9d9`。配方 SHA 分别 `88d9f6ee342c58f19964d41dda99db4b975e364eed58cbbbc68dd9e1f7fda81f`、`6126f09927658ef9a54bc0ea87ecf4b3c2c2d59244172844a6e6e38cef2d9a12`，与请求及已验 CPU 配方一致；未把 CPU image ID 当 GPU ID。

## 3. FrozenPatch、基线和所有候选条目

重算 FrozenPatch canonical digest、每条 base64 内容 SHA、baseline canonical digest／policy digest，并核其 task、image、HEAD、public digest 交叉身份。逐个读取 tar 的**全部成员**，检查成员集、无重复、对象类型、执行位及内容 SHA：3a61 两份各 1517，a682 两份各 1606，全部匹配 manifest。原 census 与 grader 重建 census 的纳入成员也逐条匹配，未以 `baseline_rebuild_passed=true` 代替这一检查。

| 尝试 | FrozenPatch canonical digest（去 `sha256:`） | 基线 tar 原文件 SHA |
| --- | --- | --- |
| 3a-Q | `daab135a618b08edf520de6f5229b06be17285fe0109ef773a1364996d35d780` | `167cd39af96f16b7ff6798223b446975a3a678fedb5b5b0cb9a0b1f727644862` |
| 3a-C | `00567b83fb92e2992decb3c94b2356ce376f1b4306e55b5d769a59f62e58c205` | `f1b5690e8f18bc8fad9fb64480a4344e136e207fc2abadd33cd1bfcf4c7c4045` |
| a6-Q | `bc85c4b5044851dcf53861717ec29bba353a7be1e978f9a4fe65885944151e32` | `5abcb530cd000389dbef618d3797a2ec930855ad25946f818bab7d0744c8c77b` |
| a6-C | `28ab833847bce89eb85e75b0961f51573a0827a254dc9096419c773052f32328` | `8e480720df2ff2804554845c608e9c3020f6ef944f18ea26d6bbb9df716fea8e` |

3a61 两模型 baseline canonical digest 同为 `sha256:1b4c0ba4ab83786ef6a1e5eff6f89aec7f50b61e5aeee3703ecc383493409652`；a682 同为 `sha256:1dbc4bcc8cd4030dc001dd5a6feee7856202b96662a529f1565dfb4e973e8b57`。同题 tar 文件 SHA 不同，但纳入成员内容、类型及执行位相同。

以实际基线字节逐 hunk 核候选 diff，结果与 FrozenPatch 每项逐字节相同；a6-C 的两个 Git binary literal 也独立解码、解压核对。projection 包含全部候选项，按固定 consumer 规则重算的 `applied_entry_set` digest 与 report 相同。不是用作者另造的 source.diff 顶替原候选。

- **3a-Q：1 项**，只修改 `src/PIL/Image.py`，内容 SHA `ca6730046035e52c28e4c30bb6b60ff8e240aeca874e0301c60761d294dd0c3e`。
- **3a-C：16 项**，修改 `src/PIL/Image.py`（SHA `2ff732ab91c25ae311cb51a1e6b1add9fea65fc8c244b5bad0e986f7347c7d2c`），另新增 15 个诊断脚本：`check_getpalette.py`、`debug_detailed.py`、`debug_exact_issue.py`、`debug_palette.py`、`debug_palette2.py`、`debug_palette3.py`、`debug_palette_structure.py`、`debug_remap_step_by_step.py`、`final_debug.py`、`precise_test.py`、`simple_test.py`、`test_fix_final.py`、`test_remap_palette_issue.py`、`trace_remap.py`、`verify_fix.py`。不能写成 FrozenPatch 只有一个条目。
- **a6-Q：1 项**，只修改 `src/PIL/GifImagePlugin.py`，内容 SHA `64e0d0a7dc3e493c81532c3b9e1420a9102dbe1b749a7316e2d4d01c71fa1e56`。
- **a6-C：4 项**，修改该源码（SHA `29b12e6f696c593e651a936e421adec5a6777c9aa1730a94a2e05cba12d884ad`），新增 `comprehensive_test.py`（2634 字节）、`debug.gif`（43 字节）和 `temp_working.gif`（51 字节）。三个新增项均保留在原件和实际评分投影中。

全部候选为常规文件，无 symlink 或控制路径条目；原 `Tests/` 测试、conftest／fixture 未被修改。新增诊断脚本未由固定 `pytest -rA r2e_tests` 入口收集。`excluded_pathset_changed=true` 原值保留：基线政策排除 `.git/`、`.harness/`、`.venv/` 及可再生缓存，不能把此次核对表述为这些命名空间全部内容也已逐字节证明不变。

## 4. 正式日志逐参考重解析

使用固定 code_v4 的纯 `r2e_parsers.py` 去色及键归一化函数，分别解析完整日志和 `Start Test Output`／`End Test Output` 内段，两份 map 相同。每个键逐项与固定 expected 比较；四份均无缺键、额外键、参考跳过或段外评分项。两题 expected 均全部要求 PASSED，不沿用 2d01 的两个期望 FAILED 规则。

| 尝试 | 原日志文件（在各根 `grading/eval_logs/`） | 收集／pytest footer／test RC | 参考不匹配 |
| --- | --- | --- | --- |
| 3a-Q | `evallog_gpu1003-pillow3a61-qwen3_ab8bdf0a.eval.log` | 75；74 passed + 1 skipped；0 | 无 |
| 3a-C | `evallog_gpu1003-pillow3a61-coder_5553a737.eval.log` | 75；71 passed + 3 failed + 1 skipped；1 | `TestImage.test_remap_palette`、`TestImage.test_remap_palette_rgba_reorder`、`TestImage.test_remap_palette_rgba_transparency` |
| a6-Q | `evallog_gpu1003-pillowa682-qwen3_fab6b400.eval.log` | 95；93 passed + 2 skipped；0 | 无 |
| a6-C | `evallog_gpu1003-pillowa682-coder_608bd40b.eval.log` | 95；92 passed + 1 failed + 2 skipped；1 | `test_removed_transparency` |

这些 skip 均为日志保留的非参考环境项：3a61 的 jpg_2000、a682 的 Netpbm。74 和 93 是参考分母，不能改写为完整收集数。log SHA 与 report 的 `eval_log_ref` 字节数及摘要逐一相同：

- 3a-Q：`fe13829992386f73d8382abe28e3228fe8c72fc686412dbc7baa08539ce607e5`。
- 3a-C：`8bb1968938e19ff06459addef346b6581ac1ddbb7c39c37481f2a9e3422ea6c1`。
- a6-Q：`58180ae39d3e6c8ad2652666309abccb441b6af0c5d940b30fef537b7b6aca5e`。
- a6-C：`ec545548ff84e50e7848231fe35c4dead8d06d21a7c761d1dd13eaeac255ffae`。

四份均有真实 `RH2_SETUP_OK=1`、测试段起止、`RH2_TEST_RC` 和 footer。trusted setup apply RC=0，四个保护测试文件齐全、无缺失／不规则文件；安装段为 `RH2_INSTALL_SKIPPED=1`，不能称重新安装成功。diagnostics 的 candidate exec RC=0、segment_completed=true、log_partial=false；test RC 是上表 0/1，不能与 transport RC 混淆。result、status、report 三份同一 grading report 相等，`execution_failure_stage=null`、无 infra detail。

grader 观测导入为 `/testbed/src/PIL/__init__.py`，3a61 `9.2.0.dev0`、a682 `10.1.0.dev0`；解释器保护属主 54322、runner 前后组合摘要 `067c6080788af8288ff8c5d9cf94560b3bf62d24f37833995ec57b7ba74633e9` 不变。`env_qualification=absent` 原值保留，不把本次诊断升级成新增环境资格。

## 5. 候选语义及真实工具事件

以下 `Tn/Lm` 表示独立从原 `attempt/trajectory.jsonl` 枚举出的第 n 个真实工具调用／第 m 行；返回行另列。去除 stream 重复事件后，四条轨迹每次生成最多一个工具调用，所有工具 ID 均有唯一匹配返回。这里只记录本样本串行行为，不评价模型的并行能力。

### 3a61：Qwen 的原 1 成立，Coder 的原 0 是丢 alpha

公开题面直接要求 RGBA 恒等映射后调色板原字节相同。合理交换必须移动整个 RGBA 条目，同时保持像素呈色；整数透明索引应随条目移动。这些范围已在本次模型求解前的 CPU 材料和独立语义意见中固定。

**3a-Q。** 原候选 diff 第 1、5、35、44 行及 FrozenPatch 中 `Image.py:1870–1942` 显示：P 模式读取真实核心 `getpalettemode()`，以两个相同 mode 参数取得完整调色板，再按 3／4 字节 stride 切条目；最终核心和 Python 调色板都使用该真实 mode。像素索引映射的 `RGB;L` 仍使用三通道临时表，透明索引块未改。这里的临时 RGB 表只转换像素索引，并非丢弃真实 RGBA 的 alpha。

基线 tar 的 `src/_imaging.c:1064–1106` 证明 `getpalette` 的两个参数分别控制 mode 和 rawmode，单传 RGBA 不等于输出 RGBA；`src/libImaging/Palette.c:24–31` 的核心 palette 模式只接受 RGB／RGBA。因此 `rstrip("X")` 在该基线真实核心模式下无额外作用，不据其注释假设已支持任意 raw padding。L 分支仍构造 RGB 灰度表，显式 `source_palette` 分支仍按原 RGB 语义使用，未要求显式字节参数自动推断 RGBA。`self.load()` 原本已存在；后续改写在 copy 上进行，未新增源图像就地篡改。

原轨迹提供了从失败到有效修正的证据：T9/L123→127 原例比较 False；T10/L137→141 读到 1024 字节 RGBA；T19/L263 首改误把索引临时表改为 RGBA，T20/L277→281 真实报 `invalid palette size`；T22/L305 的对照定位该错误，T24/L333→337 恢复 RGB 索引表。T25/L347→351 与 T38/L529→533 原公开例比较 True。不是仅从正式分数反推正确。

T29/L403→407 的 L 自测错误来自打印原 L 图 `getpalette()` 的 None 返回后取切片，并非 `remap_palette` 未完成；T30/L417→421 改正后 L 项主要打印尺寸，不能把其“5 tests passed”解释成五个完整断言场景。其他自测有 RGBA 交换、整数透明索引与像素值检查。公开套件的真实 footer 分别为 TestImage 71p/1skip（T28/L389）、GIF 73p/2skip（T33/L459）、getpalette 2p（T32/L445）、convert 23p（T35/L487）；重叠子集不相加。正式 74/74 和候选机制共同支持本次范围的正确结论，不证明所有未测输入都正确。

**3a-C。** 原候选 diff `src/PIL/Image.py` 段从第 777 行起：以 bytes 长度恰为 1024 猜 RGBA，随后用 `4*i:4*i+3` 只取 RGB，最终写回仍走原 RGB 路径。1024 字节公开例丢 alpha，小 RGBA 调色板也落入 RGB fallback。公开要求是调色板字节相同；仅“没有崩溃”或 RGB 分量相同不能满足要求。

T23/L264 首改、T48/L557 最终源码改动均在原件中。T50/L579→583 的最终自测仍明确有失败；T52/L605→609 输出原调色板 1024、结果 768，却以 `SUCCESS: No crash occurred!` 收口。公开原版 remap 和 transparency 子集各 1p 不能覆盖完整 RGBA 要求。正式日志第 46–67、72–88、93–111 行分别在 `test_1.py:617/636/688` 给出恒等、交换、透明索引交集的调色板字节失败；后三键其余参考通过。最终“成功修复”陈述与自身失败和原件不一致。**这三个失败来自候选丢 alpha，未见材料误拒或环境阻断。**

### a682：Qwen 的原 1 成立，Coder 的原 0 是损坏 GIF

公开要求是不能使用该不可表示 tuple 透明色时，保存有效 GIF 且不使用透明度；不是只要创建文件且 `save()` 不抛异常。既有 CPU 材料已检查重开、调用者状态、有效透明色、连续保存及 save_all 等合理边界，不因本次 Coder 0 新增标准。

**a6-Q。** 原 diff 第 5 行开始，唯一变化为 `except (KeyError, ValueError, TypeError)`。基线 `_write_single_frame:546–562` 先量化为 `im_out`，但 `_write_local_header:559` 仍收到原 `im`；原 RGB 图保留 tuple，量化图移除透明度不能自动清掉该 fallback 值。新增 TypeError 捕获只包围取透明值及 `int()`，沿既有不可用透明值路径继续写控制字段、局部图像描述符和最低码宽；没有整个保存早退，也没有宽泛吞掉所有 writer 异常。有效整数透明值和 encoderinfo 优先级仍走原分支，警告生成点及调用者状态没有新增改动。该路线与已验 CPU `alt_typeerror` 正对照机制一致。

T6/L81→85 原公开例真实 TypeError；T18/L253 检查原 RGB info 与量化图 info 的差别。T19 的手工诊断缺 encoderinfo、T23 的脚本 SyntaxError 均为工具诊断错误，后续恢复。T27/L383→387 唯一源码 edit 后，T28/L397 保存成功且原 UserWarning 保留；T29/L411→415 公开 GIF 全文件 92p/2skip。T30/L425→429 **实际重开**原例，记录 P、256×1、GIF，info 只有 version/background，没有 transparency。正式 93/93 进一步覆盖已固定边界。该结论不扩展为无限输入类型或任意异常均已验证。

**a6-C。** 原 diff 第 102 行开始，唯一库源码改动在 `_write_local_header` 中检测原 RGB／RGBA tuple 后直接 `return`。该 caller 传入的是原图，故 guard 在公开满 256 色例实际触发；它不只是跳过透明度，还跳过该函数后部必需的 `b","` descriptor、尺寸／flags 和最低码宽字节（候选逻辑行 744–754）。后续 encoder 仍写压缩数据，文件结构因此损坏。

T19/L232 初次早退后 T22/L271→275 连正常 `test_rgb_transparency` 重开也失败。后来改 guard、曾再现 TypeError（T33/L402），并遇到旧字符串不匹配（T34/L415）；T36/L441→445 最终改成当前模式条件。T39/L480 正常 RGB 透明色 1p、T40/L493 透明度筛选 8p、T45/L554 保存筛选 9p/2skip 均与正式缺陷不矛盾。T41/L506→510 指定两个不存在的 node，没有有效测试执行。T44/L541→545 的 `comprehensive_test.py` 主要检查 save 不报错后删除文件，没有重开；它的“All tests passed”不能验收文件有效性。

正式日志第 34–77 行保留原公开 256 色例的路径：save 后在 `test_1.py:1100` 执行 `Image.open(out)` 即失败，误读尺寸为 **70554×81378**，抛 `DecompressionBombError`。这是破损字节被解释成图像尺寸，**不是内存耗尽、模型超时或仍在 int(tuple) 处失败**。未继续执行的该 test 内后续断言不能单列为本候选已通过／已失败；已足够由公开原例的重开失败判定候选错误。其余 92 个参考键齐全通过，未见材料或环境误拒。

## 6. 公开交付与公私边界

四个实际首 HTTP 请求的原任务文本，与 GPU prepared `prompts.jsonl`、`solver_prompt.txt`、`attempt/prompt.txt` 逐字节相同。3a61 prompt SHA 是 `b301d97d3df7628af3f7af1e10d254495e579bd23cf35eacdd8356f86e3ea271`；a682 是 `3ff66b1d4395d0d19ae8901454dddeac992fc3238fcbe94902523bf86e7d8af5`。二者均 `public_delivery.mode=unchanged`，无新增题级 brief。

**prepared generic public_hints 存在，不等于其全文已进入模型请求。** 独立读取四份首请求的原字符串，均为原题面加 CC 默认 system／日期／环境信息，没有 prepared hints 全文及其虚拟环境、NON-TEST 说明片段。固定 code_v4 解释这一结果：`prepared_task_face.py:559` 调 `render_user_prompt(public)`；`envpack/bundles.py:282–289` 只渲染 repo、workdir、base 和 problem_statement；`ordinary_gpu_probe_20261002/entry.py:61–85` 的 unchanged 直接使用 `spec.prompt`，不追加说明。shared lifecycle 另把公开 bundle 写到 `/rh2/public_task_bundle.json`，这与自动送入首模型消息不同，四条轨迹未读取该文件。

这属于**既有 prompt 构造语义和报告措辞限制，本次不是漏交请求必要指令**：两份不可变请求的 `solver_visibility` 明确为“只投递由固定公开bundle生成的原prompt”，`public_delivery` 也明确 unchanged，没有要求附加 hints 全文。两题实际开发工具、源码导入和正式评分完整；本次普通诊断可按实际原题面交付条件解释。不能凭 prompt SHA 相同声称所有 public 字段已自动交付，也不能把后来的说明追写成旧模型已看到。

四份 prelaunch 原件均记录 UID/GID 54321、CAPPRM/CAPEFF=0、NNP=1、无 bind mount、隔离网络，/root DENIED；R2E hidden tests 与 git history preflight 完整。对全部真实工具输入核读，未见请求隐藏测试、expected map、host grading、gold 或 CPU 私有目录；读取的是源代码、原公开 Tests、自己的诊断脚本和公开 `run_tests.sh`。3a-Q 读到 runner 中 `r2e_tests` 字样不等于读到隐藏内容。候选未修改保护控制面。首请求未含 owner 请求或私有审查材料；该观察仍不构成模型预训练暴露或更宽安全审计的证明。

## 7. 完整执行、预算、身份采集及清理

独立读取每一生成请求、response、SSE 和 adapter turn，按顺序核 usage 配对、HTTP200、attempt=1、无 stream error、完整 message_start/message_stop，最后 end_turn；adapter finish_reason 均 stop，未见长度或 context 中断。count_tokens 单列，不能算新增求解或模型样本。

| 尝试 | HTTP／生成／count_tokens | CC turns／真实工具／工具 error | 最大单次输入／输出 token | solve 秒 |
| --- | --- | --- | --- | --- |
| 3a-Q | 41／41／0 | 41／40／3 | 29759／1722 | 73.773 |
| 3a-C | 61／60／1 | 60／59／1 | 105712／2829 | 374.286 |
| a6-Q | 35／34／1 | 34／33／3 | 35126／754 | 64.453 |
| a6-C | 49／48／1 | 48／47／6 | 39231／713 | 92.180 |

四份完整轨迹分别为 579、697、489、593 行，SHA 为 `5a8744317d1633d279f7f42cfa472e02808f43eef4c9f63a2125db037baae43c`、`4e979795ba3d09979c7f1eb3dfbcef7d1f3bbf9abb036e229573afff5d93a3e6`、`ec124d51b742420c919b0d2ca7b4515e851a8bd20b8cfcf8ccdcbba0a8b8b742`、`796c6b58ba893f24793860a592572f64f3f98036d393764ac589b84c135d1eb8`。`attempt/trajectory.jsonl` 与 `attempt/harness/trajectory.jsonl` 每份相同、JSONL 完整收尾，stderr 为零字节，末事件均 success/completed，harness exit=0。工具 error 是上文的真实失败或诊断错误，全部返回；不能误计为整条轨迹失败或丢返回。

预算仍是 `probe-wide-v1`：196608 context、65536 输出、240 turns、10800 秒、1024 session 请求；first-byte 1800 秒、adapter 声明 TTL 14400 秒；grader whole/setup/apply/test 为 3600/300/120/1800 秒。**实际全部生成 HTTP max_tokens=65536**，CC `modelUsage.maxOutputTokens=32000` 仅元数据，二者不混用。实际最大单次输入最多 105712，本轮不能证明 196K 峰值承载。input 的 `service_readback=config_only`、TTL observed=null 仍保留，不写成这些短臂实测了四小时 TTL。

网关实际送出的 model 为 Qwen3.6-35B-A3B 或 Qwen3-Coder-30B-A3B-Instruct；CC/SSE 的 `slime-actor` 是 alias。Qwen adapter 默认 temperature/top_p/top_k=1.0/0.95/20，Coder 为 0.7/0.8/20 加 repetition_penalty=1.05，全部 HTTP 未带采样 override。不可表述为两模型采样参数完全相同。

入口绑定 `code_v4`，本次核本地 frozen manifest **529 文件 SHA/size 全匹配**（manifest SHA `e3a33fd824021b75c9ed32fe7a82800f4158bfcf5d5a9d0ca8a8329380716469`）；entry SHA `a1efff44dc2cbedfc81d93b2da8d84a92f6c9c88b15c2a10bf96db2026a4e82c`、shared R2E entry SHA `10a71cca67af24c9ab5a6de09cb1845751c643632559842bb61dbce6ebc01d5a`、base parent SHA `00ca849909150de02769f297374a9bbfacf2746347c425474775d9c3e22a04f9` 与原记录相符。`code_snapshot_id=null` 原值不改；这里是外部冻结材料关联，不称每个旧 attempt 自带新 snapshot。

身份采集深度有差异，不能补造历史证据：

- **旧 Qwen 两臂**复用执行者已验模型 revision `995ad96eacd98c81ed38be0c5b274b04031597b0`、services_v7 server readback（SHA `b1530f69948a01d6e744e2a3cb5c523e95407864ebb2b60b440504d6dff848e4`）及 engine/config 关联。本次再核其既有冻结 inventory 67／60 个文件 SHA/size 均未变。server 实际字段为 BF16、TP1、context196608、quantization=null、attention_backend=flashinfer，adapter 服务与原 HTTP 配对。gateway `checkpoint_identity_verified=false`，未保存每生成原始 SGLang sampling_params/backend request ID；本地复核及后来更完整采集不补成这两臂当时已经拥有的 per-arm 证据。
- **Coder 两臂**有 `remote/diagnostics/QUEUE_V16_<job>_before/` 的运行前实际采集。本次读取 engine inspect 前后、server_info、identity binding 和 capture_receipt，engine ID／StartedAt 相同、restart_count=0，read-only model mount 及实际 BF16／TP1／196608／flashinfer 字段相符。capture receipt SHA 分别为 `6bf216e688c789b718ff64168178a6f3d92527cde37a8f530e54250314ecd056`、`1600fb01a8447ca3a35d95da7343afe1f4109652f69f6a0e87d9c9ff3e0e6492`；绑定 Coder revision `b2cff646eb4bb1d68355c01b18ae02e7cf42d120` 及 download manifest SHA `5783533eae085661e3b3cde2e46ee46c9dbce0c05154d6028f6e46aa7260de39`。未在本次重核各 weight 文件或 GPU 内存权重摘要。

Coder 封口原清单 `remote/gpu1003-{pillow3a61,pillowa682}-coder-a1_closed_manifest_v1.json` 的 **139／127 个文件**全部独立核 SHA/size，含运行前采集及收尾；两份 manifest SHA 分别 `7546a8fd22f10d48fa02524b7237b127dc912d18d000408c2f97833607b80279`、`4a008a1c114d1b4ea65d4ca2e71597a4a374007f5f5cb770b273d6da347b874f`。没有用 mutable queue/resource 总状态替代 job 的已冻结证据。

四份 attempt 均先真实 stop，residual=0，再 revoke/drain（active_requests=0），静止屏障以零 agent 进程和工作区双读稳定确认。actor container_rm=0，容器／network／relay 无残留或清理失败；manager 各 created=removed=1、containers_open/supply_open/cleanup_failures 为空、regrade_total=0。grader 与 actor 清理分开核，不从总回执一个 cleanup 布尔值推断。资源观测仍为约 15 秒的离散样本，间隙和缺字段未知；grader `resource_facts=null`，8GiB writable quota `require=false`，不造峰值、强制配额或稳定性结论。

## 8. 作者派生读回窄核及当前用途

题主随后提供 `runs/category2_repair_20260929/r2e_pillow_cpu_b_20261003/remaining_model_analysis_20261003/` 的四份 `*_owner_readback_v1.json`。在形成上述原件结论后，逐工具核其 ordinal、trajectory_line、ID、input、result_line、error 标志、完整 result_text；四份的 40／59／33／47 项均与原轨迹相同。其 source_refs SHA、74／93 参考统计和原 report 也一致。作者行为结论与本次独立判断一致；这些文件仍在作者冻结流程，本报告以原件为判断依据，不依赖其后续状态标签或把派生 source.diff 当实际候选。

**必要修订阻断：无。** Qwen 两份原 1 具有公开行为及合理边界的语义证据；Coder 两份原 0 是实现及自测验收不足，有明确原件因果链，不需要为同机制再跑候选或添加隐藏断言。原分完整保留，可作为固定本轮材料、实际交付、模型配置和预算下的普通诊断样本。

**未证明事项：** 每题每模型仅一个有效样本，不能据此断言稳定成功率、整体模型能力、任务整体难度或 RL 信号；同仓答案包含／既有模型暴露边界继续保留。未重复测试未测输入、196K 峰值、长期 TTL、权重文件全 SHA、模型预训练暴露或正式训练准入。后续用途和是否增加固定条件样本由题主及统一执行流程承担；本报告不启动下一阶段，也不把未执行的后续计划写为 PASS。
